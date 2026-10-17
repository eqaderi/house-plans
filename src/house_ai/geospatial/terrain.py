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

from shapely import MultiPoint, delaunay_triangles
from shapely.geometry import Polygon as ShapelyPolygon

from house_ai.domain.geometry import Point2, Point3, Polygon2D
from house_ai.domain.site import Contour, SpotElevation, Terrain, TinSurface
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


def build_tin(spots: list[SpotElevation], contours: list[Contour]) -> TinResult:
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
    return result


def _cross(a: Point3, b: Point3, c: Point3) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def terrain_from_survey(
    spots: list[SpotElevation], contours: list[Contour]
) -> tuple[Terrain, TinResult]:
    tin = build_tin(spots, contours)
    return build_terrain(spots, contours, surface=tin.surface), tin


class DelaunayTerrainBuilder:
    """:class:`house_ai.geospatial.base.TerrainBuilder` using :func:`build_tin`."""

    def build_surface(
        self, spot_elevations: list[SpotElevation], contours: list[Contour]
    ) -> Terrain:
        return terrain_from_survey(spot_elevations, contours)[0]


def triangle_slope_pct(a: Point3, b: Point3, c: Point3) -> float:
    """Steepest slope of the triangle's plane, in percent."""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    if nz == 0:
        return math.inf
    return 100.0 * math.hypot(nx, ny) / abs(nz)


def hull_polygon(surface: TinSurface) -> ShapelyPolygon:
    return MultiPoint([(x, y) for x, y, _ in surface.vertices]).convex_hull


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
