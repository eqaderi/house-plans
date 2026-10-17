"""Terrain queries every pipeline package may use (LOCAL frame, metres).

Elevations come only from surveyed data: a stored TIN, or a Delaunay
triangulation of the site's spot elevations and contour vertices when no
surface was stored. Outside the surveyed hull the elevation is unknown
(None), never extrapolated.
"""

from __future__ import annotations

from shapely import MultiPoint, delaunay_triangles

from .geometry import Point2, Point3
from .site import Site, TinSurface


def _cross(a: Point3, b: Point3, c: Point3) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def elevation_at(surface: TinSurface, xy: Point2) -> float | None:
    """Linear interpolation on the TIN; None outside the surveyed hull."""
    x, y = xy
    for ia, ib, ic in surface.triangles:
        a, b, c = surface.vertices[ia], surface.vertices[ib], surface.vertices[ic]
        det = _cross(a, b, c)
        if det == 0:
            continue
        w_b = ((x - a[0]) * (c[1] - a[1]) - (y - a[1]) * (c[0] - a[0])) / det
        w_c = ((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])) / det
        w_a = 1.0 - w_b - w_c
        if min(w_a, w_b, w_c) >= -1e-9:
            return w_a * a[2] + w_b * b[2] + w_c * c[2]
    return None


def site_surface(site: Site) -> TinSurface | None:
    """The site's stored TIN, or one triangulated from its surveyed points.

    Points sharing a position keep the first elevation seen; the site
    ingestion pipeline reports such conflicts, this query does not resolve them.
    """
    if site.terrain.surface is not None:
        return site.terrain.surface
    seen: dict[tuple[int, int], Point3] = {}
    for s in site.terrain.spot_elevations:
        seen.setdefault((round(s.xy[0] * 1e6), round(s.xy[1] * 1e6)), (*s.xy, s.z_m))
    for c in site.terrain.contours:
        for p in c.line.points:
            seen.setdefault((round(p[0] * 1e6), round(p[1] * 1e6)), (*p, c.z_m))
    pts = list(seen.values())
    if len(pts) < 3:
        return None
    tris = delaunay_triangles(MultiPoint([(x, y) for x, y, _ in pts]))
    if tris.is_empty:
        return None
    index = {(round(x * 1e6), round(y * 1e6)): i for i, (x, y, _) in enumerate(pts)}
    triangles: list[tuple[int, int, int]] = []
    for tri in tris.geoms:
        a, b, c = (index[(round(x * 1e6), round(y * 1e6))] for x, y in tri.exterior.coords[:3])
        if _cross(pts[a], pts[b], pts[c]) < 0:
            b, c = c, b
        triangles.append((a, b, c))
    triangles.sort()
    return TinSurface(vertices=pts, triangles=triangles, source_ids=[])
