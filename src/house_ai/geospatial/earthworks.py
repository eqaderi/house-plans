"""Exact 2.5D integration of a piecewise planar survey TIN.

Each triangle is clipped to a footprint and a horizontal design plane. An
affine height integrates as area times height at the polygon centroid. This
works for holes and irregular footprints, without a sampling grid. Results
are inferred from the TIN, not construction quantities. Unknown coverage is
kept separate, and overlapping floor projections are counted only once.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

from house_ai.domain.model import HouseModel, SlabKind
from house_ai.domain.site import TinSurface

EPS = 1e-9


def parts(geometry, kind="Polygon"):
    if geometry.is_empty:
        return []
    if geometry.geom_type == kind:
        return [geometry]
    return [p for g in getattr(geometry, "geoms", []) for p in parts(g, kind)]


def plane(a, b, c):
    """Return affine z(x,y), rejecting a vertical/degenerate terrain face."""
    ux, uy, uz = (b[i] - a[i] for i in range(3))
    vx, vy, vz = (c[i] - a[i] for i in range(3))
    det = ux * vy - uy * vx
    if abs(det) < 1e-12:
        raise ValueError("degenerate XY triangle in terrain")
    gx, gy = (uz * vy - uy * vz) / det, (ux * vz - uz * vx) / det
    return lambda x, y: a[2] + gx * (x - a[0]) + gy * (y - a[1])


def facets(surface: TinSurface):
    _validate_tin(tuple(surface.vertices), tuple(surface.triangles))
    for ids in surface.triangles:
        points = [surface.vertices[i] for i in ids]
        triangle = Polygon([p[:2] for p in points])
        if triangle.area < 1e-10:
            continue
        yield triangle, plane(*points), points


@lru_cache(maxsize=64)
def _validate_tin(vertices, triangles):
    shapes = [Polygon([vertices[i][:2] for i in tri]) for tri in triangles]
    tree = STRtree(shapes)
    for i, shape in enumerate(shapes):
        for j in tree.query(shape):
            if j < i and shape.intersection(shapes[j]).area > 1e-8:
                raise ValueError(f"terrain triangles {j} and {i} overlap in XY")


def support(surface: TinSurface):
    """Actual triangles, including holes/disconnected support, never convex hull."""
    return unary_union([p for p, _, _ in facets(surface)])


def _above(points, z):
    """Convex triangle clipped at z >= target; XY polygon of the upper part."""
    out = []
    for a, b in zip(points, points[1:] + points[:1], strict=True):
        if a[2] >= z:
            out.append(a[:2])
        if (a[2] > z > b[2]) or (b[2] > z > a[2]):
            t = (z - a[2]) / (b[2] - a[2])
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return Polygon(out) if len(out) >= 3 else Polygon()


@dataclass(frozen=True)
class VolumeResult:
    area_m2: float
    known_area_m2: float
    cut_m3: float | None
    below_plane_m3: float | None
    max_cut_m: float | None
    max_below_m: float | None
    ground_min_m: float | None
    ground_max_m: float | None


def integrate(surface: TinSurface | None, footprint, elevation_m: float) -> VolumeResult:
    """Cut above, and available space below a proposed horizontal plane."""
    if surface is None:
        return VolumeResult(footprint.area, 0, None, None, None, None, None, None)
    cut = below = known = 0.0
    heights = []
    for triangle, z_at, vertices in facets(surface):
        hit = unary_union(parts(triangle.intersection(footprint)))
        if hit.area <= EPS:
            continue
        known += hit.area
        above = _above(vertices, elevation_m)
        upper = hit.intersection(above) if not above.is_empty else Polygon()
        lower = hit.difference(upper)
        for geometry, sign in ((upper, 1), (lower, -1)):
            if geometry.area > EPS:
                c = geometry.centroid
                volume = max(0.0, sign * (z_at(c.x, c.y) - elevation_m) * geometry.area)
                if sign == 1:
                    cut += volume
                else:
                    below += volume
        for p in parts(hit):
            heights.extend(z_at(x, y) for x, y in p.exterior.coords)
    if not heights:
        return VolumeResult(footprint.area, 0, None, None, None, None, None, None)
    low, high = min(heights), max(heights)
    return VolumeResult(
        footprint.area,
        known,
        cut,
        below,
        max(0.0, high - elevation_m),
        max(0.0, elevation_m - low),
        low,
        high,
    )


def floor_regions(model: HouseModel):
    """Nonoverlapping lowest finished-floor regions, ascending by elevation."""
    covered = Polygon()
    for level in sorted(model.levels, key=lambda lv: (lv.elevation_m, lv.id)):
        shape = unary_union(
            [s.boundary.to_shapely() for s in model.spaces if s.level_id == level.id]
            + [
                s.boundary.to_shapely()
                for s in model.slabs
                if s.level_id == level.id and s.kind in {SlabKind.FLOOR, SlabKind.TERRACE}
            ]
        )
        region = shape.difference(covered)
        if region.area > EPS:
            yield level, region
        covered = covered.union(shape)


def ground_planes(model: HouseModel):
    """Lowest physical slab underside; missing slabs use a labelled floor-plane bound."""
    for level, region in floor_regions(model):
        covered = Polygon()
        slabs = sorted(
            (
                s
                for s in model.slabs
                if s.level_id == level.id and s.kind in {SlabKind.FLOOR, SlabKind.TERRACE}
            ),
            key=lambda s: s.top_offset_m - s.thickness_m,
        )
        for slab in slabs:
            # A slab touching the region along an edge also returns that line; keep the area.
            hit = unary_union(parts(region.intersection(slab.boundary.to_shapely())))
            hit = hit.difference(covered)
            if hit.area > EPS:
                z = level.elevation_m + slab.top_offset_m - slab.thickness_m
                yield level.id, z, hit, f"underside:{slab.id}"
                covered = covered.union(hit)
        remainder = region.difference(covered)
        if remainder.area > EPS:
            yield level.id, level.elevation_m, remainder, "finished_floor_bound_no_slab"


def earthworks(model: HouseModel, surface: TinSurface | None) -> dict:
    """Three distinct quantities. Fill exists only for explicit proposed pads.

    Floors use slab undersides when defined, otherwise finished-floor bounds.
    Working space, bulking,
    compaction, footings, battered sides and temporary works are not estimated.
    A pad is a proposed formation surface and must not overlap another pad.
    """
    pads = model.earthwork_pads
    for i, a in enumerate(pads):
        for b in pads[i + 1 :]:
            if a.boundary.to_shapely().intersection(b.boundary.to_shapely()).area > EPS:
                raise ValueError(f"earthwork pads {a.id} and {b.id} overlap")
    pad_union = unary_union([p.boundary.to_shapely() for p in pads])
    rows = []
    cut = void = fill = known = total = 0.0
    max_cut = max_void = 0.0
    for level_id, floor_z, region, basis in ground_planes(model):
        r = integrate(surface, region, floor_z)
        total += r.area_m2
        known += r.known_area_m2
        bare = integrate(surface, region.difference(pad_union), floor_z)
        max_cut = max(max_cut, bare.max_cut_m or 0)
        max_void = max(max_void, bare.max_below_m or 0)
        region_cut = bare.cut_m3 or 0
        region_void = bare.below_plane_m3 or 0
        region_max_void = bare.max_below_m or 0
        for pad in pads:
            hit = region.intersection(pad.boundary.to_shapely())
            if hit.area <= EPS:
                continue
            if pad.elevation_m > floor_z + EPS:
                raise ValueError(f"pad {pad.id} is above floor/slab underside {level_id}")
            formation = integrate(surface, hit, pad.elevation_m)
            region_cut += formation.cut_m3 or 0
            region_void += formation.known_area_m2 * (floor_z - pad.elevation_m)
            max_cut = max(max_cut, formation.max_cut_m or 0)
            if formation.known_area_m2:
                region_max_void = max(region_max_void, floor_z - pad.elevation_m)
                max_void = max(max_void, region_max_void)
        cut += region_cut
        void += region_void
        rows.append(
            {
                "level_id": level_id,
                "calculation_plane_m": floor_z,
                "floor_basis": basis,
                **r.__dict__,
                "cut_m3": region_cut,
                "underfloor_void_volume_m3": region_void if r.known_area_m2 else None,
                "max_void_height_m": region_max_void if r.known_area_m2 else None,
                "footprint": region.__geo_interface__,
            }
        )
    # Include explicit pads outside the building, without double counting.
    building = unary_union([g for _, g in floor_regions(model)])
    pad_known = pad_total = 0.0
    for pad in pads:
        hit = pad.boundary.to_shapely()
        r = integrate(surface, hit, pad.elevation_m)
        pad_known += r.known_area_m2
        pad_total += r.area_m2
        fill += r.below_plane_m3 or 0
        outside = integrate(surface, hit.difference(building), pad.elevation_m)
        cut += outside.cut_m3 or 0
        max_cut = max(max_cut, outside.max_cut_m or 0)
    return {
        "method": "exact_clipped_tin_affine_integration",
        "status": "inferred" if known > EPS else "not_checked",
        "footprint_area_m2": total,
        "known_area_m2": known,
        "unknown_area_m2": max(0.0, total - known),
        "coverage_pct": 100 * known / total if total else 0,
        "excavation_volume_m3": cut if known else None,
        "engineered_fill_volume_m3": fill if pad_known else None,
        "known_pad_area_m2": pad_known,
        "unknown_pad_area_m2": max(0.0, pad_total - pad_known),
        "underfloor_void_volume_m3": void if known else None,
        "max_cut_m": max_cut if known else None,
        "max_underfloor_void_height_m": max_void if known else None,
        "regions": rows,
        "note": "Partial quantities cover surveyed support only. Slab undersides when present; "
        "finished-floor upper bounds when slab thickness/geometry is absent. Explicit pad "
        "planes; conceptual geometric quantities, not a construction estimate. "
        "Engineered fill is not specified unless explicit earthwork pads are present.",
    }


def terrain_profile(surface: TinSurface | None, line: LineString) -> list[dict]:
    """Piecewise linear true section with explicit gaps in surveyed support."""
    breaks = {0.0, line.length}
    if surface is not None:
        for tri, _, _ in facets(surface):
            for seg in parts(tri.intersection(line), "LineString"):
                breaks.update(line.project(Point(p)) for p in seg.coords)
    from house_ai.domain.terrain import elevation_at

    output = []
    distances = sorted(breaks)
    for a, b in zip(distances, distances[1:], strict=False):
        if b - a < EPS:
            continue
        mid = line.interpolate((a + b) / 2)
        known = surface is not None and elevation_at(surface, (mid.x, mid.y)) is not None
        za = zb = None
        if known:
            pa, pb = line.interpolate(a), line.interpolate(b)
            za = elevation_at(surface, (pa.x, pa.y))
            zb = elevation_at(surface, (pb.x, pb.y))
        output.append(
            {
                "start_m": a,
                "end_m": b,
                "start_z_m": za,
                "end_z_m": zb,
                "status": "inferred" if known else "unknown",
            }
        )
    return output


def retained_face(surface: TinSurface | None, start, end, floor_z: float) -> dict:
    profile = terrain_profile(surface, LineString([start, end]))
    area = known = maximum = 0.0
    for part in profile:
        if part["status"] == "unknown":
            continue
        length = part["end_m"] - part["start_m"]
        a, b = part["start_z_m"] - floor_z, part["end_z_m"] - floor_z
        known += length
        maximum = max(maximum, a, b)
        if min(a, b) >= 0:
            area += length * (a + b) / 2
        elif max(a, b) > 0:
            area += length * max(a, b) ** 2 / (2 * abs(b - a))
    return {
        "length_m": math.dist(start, end),
        "known_length_m": known,
        "max_retained_height_m": maximum if known else None,
        "mean_retained_height_m": area / known if known else None,
        "face_area_m2": area if known else None,
    }
