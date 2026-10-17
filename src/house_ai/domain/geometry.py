"""2D geometry primitives in the local project frame (metres).

Milestone A plans use orthogonal rectangles, but the types are general
polygons with holes so courtyards and non-orthogonal rooms fit later without
changing the domain model. Shapely does the robust predicates.
"""

from __future__ import annotations

import math
from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator
from shapely.geometry import LineString
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry.polygon import orient
from shapely.validation import explain_validity

from .base import EPS_M, StrictModel

Point2 = tuple[float, float]
Point3 = tuple[float, float, float]

#: Smallest polygon area we accept, in m².
MIN_POLYGON_AREA_M2 = 1e-4


def _strip_closing_point(ring: list[Point2]) -> list[Point2]:
    if len(ring) >= 2 and math.dist(ring[0], ring[-1]) <= EPS_M:
        return ring[:-1]
    return ring


def _normalise_ring(value: object) -> object:
    if isinstance(value, list | tuple):
        return _strip_closing_point([tuple(p) for p in value])  # type: ignore[arg-type]
    return value


Ring = Annotated[list[Point2], BeforeValidator(_normalise_ring), Field(min_length=3)]


class Polygon2D(StrictModel):
    """A simple polygon, optionally with holes. Rings are not closed explicitly."""

    outer: Ring
    holes: list[Ring] = Field(default_factory=list)

    @model_validator(mode="after")
    def _valid(self) -> Polygon2D:
        poly = self.to_shapely()
        if not poly.is_valid:
            raise ValueError(f"invalid polygon: {explain_validity(poly)}")
        if poly.area < MIN_POLYGON_AREA_M2:
            raise ValueError(f"degenerate polygon: area {poly.area:.6f} m²")
        return self

    def to_shapely(self) -> ShapelyPolygon:
        return ShapelyPolygon(self.outer, self.holes)

    def oriented(self) -> Polygon2D:
        """Return an equivalent polygon with CCW outer ring and CW holes."""
        poly = orient(self.to_shapely(), sign=1.0)
        return Polygon2D(
            outer=list(poly.exterior.coords[:-1]),
            holes=[list(interior.coords[:-1]) for interior in poly.interiors],
        )

    @property
    def area_m2(self) -> float:
        return float(self.to_shapely().area)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return tuple(self.to_shapely().bounds)  # type: ignore[return-value]

    @classmethod
    def rectangle(cls, x0: float, y0: float, x1: float, y1: float) -> Polygon2D:
        return cls(outer=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    @classmethod
    def rotated_rectangle(
        cls, centre: Point2, width_m: float, depth_m: float, rotation_deg: float = 0.0
    ) -> Polygon2D:
        """Construct a rectangle centered at ``centre`` rotated CCW by ``rotation_deg``."""
        cx, cy = centre
        hw, hd = width_m / 2.0, depth_m / 2.0
        rad = math.radians(rotation_deg)
        c, s = math.cos(rad), math.sin(rad)
        local_corners = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
        outer = [(cx + c * dx - s * dy, cy + s * dx + c * dy) for dx, dy in local_corners]
        return cls(outer=outer)


class Polyline2D(StrictModel):
    points: list[Point2] = Field(min_length=2)
    closed: bool = False

    def to_shapely(self) -> LineString:
        pts = [*self.points, self.points[0]] if self.closed else self.points
        return LineString(pts)

    @property
    def length_m(self) -> float:
        return float(self.to_shapely().length)


def segment_length(a: Point2, b: Point2) -> float:
    return math.dist(a, b)


def unit_direction(a: Point2, b: Point2) -> Point2:
    length = segment_length(a, b)
    return ((b[0] - a[0]) / length, (b[1] - a[1]) / length)


def left_normal(direction: Point2) -> Point2:
    return (-direction[1], direction[0])

