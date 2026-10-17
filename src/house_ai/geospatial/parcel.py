"""Parcel measurements and road frontage, computed from the canonical site.

Bearings are clockwise in degrees. ``bearing_local_deg`` is measured from
local +y; ``bearing_grid_deg`` from grid north (needs the local frame); and
``bearing_true_deg`` from true north, only when grid-to-true-north is known.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.geometry import LineString, MultiLineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from house_ai.domain.coordinates import LocalCoordinateSystem
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.geometry import Point2, Polygon2D, Polyline2D
from house_ai.domain.site import PolylineGeometry, SiteFeature, SiteFeatureKind

#: A boundary edge within this distance of a road counts as frontage.
FRONTAGE_TOL_M = 0.5
#: Frontage pieces shorter than this are ignored: an edge that meets a road
#: only at a corner still enters the tolerance zone for up to ``tol`` metres.
MIN_FRONTAGE_M = 2 * FRONTAGE_TOL_M


@dataclass(frozen=True)
class Edge:
    index: int
    start: Point2
    end: Point2
    length_m: float
    bearing_local_deg: float
    bearing_grid_deg: float | None
    bearing_true_deg: float | None


@dataclass(frozen=True)
class ParcelMetrics:
    area_m2: float
    perimeter_m: float
    vertex_count: int
    edges: list[Edge]
    #: Sides of the minimum-area enclosing rectangle, longer first.
    oriented_extent_m: tuple[float, float]
    is_valid: bool
    is_ccw: bool


def _bearing(a: Point2, b: Point2) -> float:
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360.0


def parcel_metrics(
    boundary: Polygon2D, local: LocalCoordinateSystem | None, *, grid_north_known: bool
) -> ParcelMetrics:
    """Measurements of the parcel. Grid and true bearings are given only when a
    human-confirmed CRS establishes grid north (``grid_north_known``)."""
    poly = boundary.to_shapely()
    ring = boundary.outer
    edges = []
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        local_b = _bearing(a, b)
        grid_b = (
            (local_b + local.project_north_deg) % 360.0 if local and grid_north_known else None
        )
        g2t = local.grid_to_true_north_deg if local else None
        true_b = (grid_b - g2t) % 360.0 if grid_b is not None and g2t is not None else None
        edges.append(Edge(i, a, b, math.dist(a, b), local_b, grid_b, true_b))
    rect = poly.minimum_rotated_rectangle
    corners = list(rect.exterior.coords)[:3]
    sides = sorted((math.dist(corners[0], corners[1]), math.dist(corners[1], corners[2])))
    signed = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))
    return ParcelMetrics(
        area_m2=float(poly.area),
        perimeter_m=float(poly.exterior.length),
        vertex_count=len(ring),
        edges=edges,
        oriented_extent_m=(sides[1], sides[0]),
        is_valid=bool(poly.is_valid),
        is_ccw=signed > 0,
    )


def derive_frontage(
    boundary: Polygon2D | None, features: list[SiteFeature], tol_m: float = FRONTAGE_TOL_M
) -> list[SiteFeature]:
    """Boundary pieces that lie within ``tol_m`` of a road feature.

    The result is a geometric inference (status ``inference``): it says where
    the parcel adjoins drawn road geometry, not where legal access exists.
    """
    if boundary is None:
        return []
    roads = [f for f in features if f.kind is SiteFeatureKind.ROAD]
    if not roads:
        return []
    road_zone = unary_union([_shape(f).buffer(tol_m) for f in roads])
    out = []
    ring = boundary.outer
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        piece = LineString([a, b]).intersection(road_zone)
        lines = (
            list(piece.geoms)
            if isinstance(piece, MultiLineString)
            else [piece] if isinstance(piece, LineString) else []
        )
        for j, line in enumerate(ln for ln in lines if ln.length >= MIN_FRONTAGE_M):
            out.append(
                SiteFeature(
                    id=f"frontage-e{i}" + (f"-{j}" if j else ""),
                    kind=SiteFeatureKind.FRONTAGE,
                    name=f"frontage along boundary edge {i}",
                    geometry=PolylineGeometry(line=Polyline2D(points=list(line.coords))),
                    status=Epistemic.INFERENCE,
                    source_ref=f"derived: boundary edge {i} within {tol_m} m of a road",
                )
            )
    return out


def _shape(feature: SiteFeature) -> BaseGeometry:
    g = feature.geometry
    if g.type == "polygon":
        return g.polygon.to_shapely()
    if g.type == "polyline":
        return g.line.to_shapely()
    return Point(g.xy)
