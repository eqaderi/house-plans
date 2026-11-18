"""Terrain from surveyed data only: a Delaunay TIN, its queries and checks.

The TIN is built from spot elevations and contour vertices in the LOCAL
frame. It covers their convex hull and nothing else: :func:`elevation_at`
returns None outside it rather than extrapolating. Known limitation: a TIN
over contour vertices alone can contain flat triangles between two vertices
of the same contour (e.g. across a ridge); spot heights reduce this.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations

from shapely import MultiPoint, constrained_delaunay_triangles, delaunay_triangles
from shapely.geometry import LineString, Point
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import split, unary_union

from house_ai.domain.geometry import Point2, Point3, Polygon2D
from house_ai.domain.site import Contour, SpotElevation, Terrain, TerrainBreakline, TinSurface
from house_ai.domain.terrain import elevation_at  # noqa: F401  (re-exported)

from .base import build_terrain

#: Vertices closer than this (metres) are the same vertex.
VERTEX_TOL_M = 1e-6


@dataclass
class TinResult:
    surface: TinSurface | None
    #: Same position, different elevation (spot vs contour vertex, ...).
    conflicts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _key(xy: Point2) -> tuple[int, int]:
    return (round(xy[0] / VERTEX_TOL_M), round(xy[1] / VERTEX_TOL_M))


def build_tin(
    spots: list[SpotElevation],
    contours: list[Contour],
    breaklines: list[TerrainBreakline] | None = None,
) -> TinResult:
    result = TinResult(surface=None)
    vertices: dict[tuple[int, int], tuple[Point3, str]] = {}

    def add(xy: Point2, z: float, source: str) -> None:
        k = _key(xy)
        if k in vertices:
            (_, _, z0), src0 = vertices[k]
            if abs(z0 - z) > VERTEX_TOL_M:
                result.conflicts.append(
                    f"{source} and {src0} share position ({xy[0]:.3f}, {xy[1]:.3f}) but differ "
                    f"in elevation ({z:.3f} m vs {z0:.3f} m)"
                )
            return
        vertices[k] = ((xy[0], xy[1], z), source)

    for s in spots:
        add(s.xy, s.z_m, s.id)
    for c in contours:
        for p in c.line.points:
            add(p, c.z_m, c.id)
    for line in breaklines or []:
        for x, y, z in line.vertices:
            add((x, y), z, line.id)
    if result.conflicts:
        result.warnings.append("no terrain surface built while elevations conflict")
        return result
    pts = [v for v, _ in vertices.values()]
    if len(pts) < 3:
        result.warnings.append(f"{len(pts)} elevation point(s); a surface needs at least 3")
        return result
    tris_geom = delaunay_triangles(MultiPoint([(x, y) for x, y, _ in pts]))
    if tris_geom.is_empty:
        result.warnings.append("elevation points are collinear; no surface can be built")
        return result
    index = {_key((x, y)): i for i, (x, y, _) in enumerate(pts)}
    triangles: list[tuple[int, int, int]] = []
    for tri in tris_geom.geoms:
        a, b, c = (index[_key((x, y))] for x, y in list(tri.exterior.coords)[:3])
        if _cross(pts[a], pts[b], pts[c]) < 0:
            b, c = c, b
        triangles.append((a, b, c))
    triangles.sort()
    sources = sorted({src for _, src in vertices.values()})
    result.surface = TinSurface(vertices=pts, triangles=triangles, source_ids=sources)
    if breaklines:
        _constrain(result, breaklines)
    return result


def _constrain(result: TinResult, breaklines: list[TerrainBreakline]) -> None:  # noqa: C901
    """Split TIN cells at mapped edges, then triangulate each constrained cell.

    New edge intersections take the surveyed line's interpolated Z. Endpoint
    points were inserted before triangulation, so even dangling segments cut
    whole cells. Crossings must have consistent Z; vertical discontinuities
    cannot be represented by a 2.5D surface and are refused explicitly.
    """
    from .earthworks import facets, plane

    assert result.surface is not None
    surface = result.surface
    segments = [
        (LineString([a[:2], b[:2]]), a, b, line.id)
        for line in breaklines
        for a, b in zip(line.vertices, line.vertices[1:], strict=False)
    ]

    def z_line(segment, a, b, xy):
        return a[2] + (b[2] - a[2]) * segment.project(Point(xy)) / segment.length

    def add_conflict(message):
        result.conflicts.append(message)
        result.surface = None

    for i, (seg, a, b, identifier) in enumerate(segments):
        for other, c, d, oid in segments[i + 1 :]:
            hit = seg.intersection(other)
            if hit.is_empty:
                continue
            points = [hit] if hit.geom_type == "Point" else [Point(p) for p in hit.coords]
            for p in points:
                if (
                    abs(z_line(seg, a, b, p.coords[0]) - z_line(other, c, d, p.coords[0]))
                    > VERTEX_TOL_M
                ):
                    add_conflict(f"breaklines {identifier} and {oid} cross at inconsistent heights")
        for x, y, z in surface.vertices:
            if (
                seg.distance(Point(x, y)) < VERTEX_TOL_M
                and abs(z_line(seg, a, b, (x, y)) - z) > VERTEX_TOL_M
            ):
                add_conflict(f"breakline {identifier} contradicts surveyed vertex {(x, y)}")
    if result.conflicts:
        return
    # Split on whole segments in sequence; crossings become cell-boundary vertices.
    all_segments = [s for s, _, _, _ in segments]
    vertices, triangles, indices = [], [], {}
    for triangle, z_at, _ in facets(surface):
        cells = [triangle]
        for segment in all_segments:
            cells = [part for cell in cells for part in split(cell, segment).geoms]
        for cell in cells:
            for tri in constrained_delaunay_triangles(cell).geoms:
                ids = []
                coords = list(tri.exterior.coords)[:3]
                if not tri.exterior.is_ccw:
                    coords.reverse()
                for x, y in coords:
                    z = z_at(x, y)
                    for seg, a, b, _ in segments:
                        if seg.distance(Point(x, y)) < VERTEX_TOL_M:
                            z = z_line(seg, a, b, (x, y))
                            break
                    k = _key((x, y))
                    if k not in indices:
                        indices[k] = len(vertices)
                        vertices.append((x, y, z))
                    ids.append(indices[k])
                # Force a plane check now, so degenerate input fails clearly.
                plane(*(vertices[i] for i in ids))
                triangles.append(tuple(ids))
    # Constraint edges must really exist in the result, including dangling lines.
    edge_union = unary_union(
        [
            LineString([vertices[a][:2], vertices[b][:2]])
            for tri in triangles
            for a, b in zip(tri, (*tri[1:], tri[0]), strict=True)
        ]
    )
    for segment, _, _, identifier in segments:
        if segment.difference(edge_union.buffer(1e-7)).length > 1e-6:
            add_conflict(f"could not enforce mapped breakline {identifier}; no surface built")
            return
    result.surface = TinSurface(
        method="constrained_tin",
        vertices=vertices,
        triangles=triangles,
        source_ids=sorted(set(surface.source_ids)|{line.id for line in breaklines}),
    )


def _cross(a: Point3, b: Point3, c: Point3) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def terrain_from_survey(
    spots: list[SpotElevation],
    contours: list[Contour],
    breaklines: list[TerrainBreakline] | None = None,
) -> tuple[Terrain, TinResult]:
    tin = build_tin(spots, contours, breaklines)
    terrain = build_terrain(spots, contours, surface=tin.surface)
    terrain.breaklines = breaklines or []
    return terrain, tin


def triangle_slope_pct(a: Point3, b: Point3, c: Point3) -> float:
    """Steepest slope of the triangle's plane, in percent."""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    if nz == 0:
        return math.inf
    return 100.0 * math.hypot(nx, ny) / abs(nz)


def hull_polygon(surface: TinSurface) -> ShapelyPolygon:
    from .earthworks import support

    return support(surface)


def boundary_coverage(surface: TinSurface, boundary: Polygon2D) -> float:
    """Share of the parcel area (0..1) that the surveyed surface covers."""
    parcel = boundary.to_shapely()
    return float(hull_polygon(surface).intersection(parcel).area / parcel.area)


def crossing_contours(contours: list[Contour]) -> list[tuple[str, str]]:
    """Pairs of contours with different elevations that cross: impossible terrain."""
    out = []
    for a, b in combinations(contours, 2):
        if a.z_m != b.z_m and a.line.to_shapely().intersects(b.line.to_shapely()):
            out.append((a.id, b.id))
    return out


def contour_interval(contours: list[Contour]) -> float | None:
    """The common spacing of contour levels, if they are evenly spaced."""
    levels = sorted({round(c.z_m, 6) for c in contours})
    if len(levels) < 2:
        return None
    steps = [round(b - a, 6) for a, b in zip(levels, levels[1:], strict=False)]
    return steps[0] if all(abs(s - steps[0]) < 1e-6 for s in steps) else None
