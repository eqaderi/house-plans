"""The design frame: an orthogonal grid aligned with the road frontage.

Generated geometry is solved on a 10 cm integer grid in a (u, v) frame whose
u axis runs along the parcel edge facing the road and whose v axis points
into the parcel, away from the road. Every coordinate is converted to the
site's LOCAL frame by one function, so two spaces sharing an edge share the
exact same LOCAL vertices.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.geometry import LineString, Point
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union

from house_ai.domain.geometry import Point2, Polygon2D
from house_ai.domain.site import (
    PointGeometry,
    PolygonGeometry,
    PolylineGeometry,
    Site,
    SiteFeature,
    SiteFeatureKind,
)
from house_ai.domain.terrain import elevation_at, site_surface

#: Grid step in metres. All solver lengths are integers in this unit (decimetres).
GRID_M = 0.1
#: Inward safety margin applied to the envelope before fitting bars, metres.
ENVELOPE_MARGIN_M = 0.01


def to_dm(metres: float) -> int:
    return round(metres / GRID_M)


def from_dm(dm: int | float) -> float:
    return round(dm * GRID_M, 6)


class FrameError(Exception):
    """The site does not provide what the generator needs (boundary, local frame)."""


@dataclass(frozen=True)
class DesignFrame:
    origin: Point2
    u_dir: Point2
    v_dir: Point2
    #: How the frame was chosen, for the plan's assumptions.
    basis: str
    #: Road-facing parcel edge in LOCAL coordinates, if one was identified.
    road_edge: tuple[Point2, Point2] | None
    #: Id of the site feature the road edge was matched to, if any.
    road_feature_id: str | None

    def to_local(self, u_dm: int, v_dm: int) -> Point2:
        u, v = u_dm * GRID_M, v_dm * GRID_M
        return (
            round(self.origin[0] + u * self.u_dir[0] + v * self.v_dir[0], 6),
            round(self.origin[1] + u * self.u_dir[1] + v * self.v_dir[1], 6),
        )

    def to_local_m(self, u: float, v: float) -> Point2:
        return (
            self.origin[0] + u * self.u_dir[0] + v * self.v_dir[0],
            self.origin[1] + u * self.u_dir[1] + v * self.v_dir[1],
        )

    def to_design(self, xy: Point2) -> tuple[float, float]:
        dx, dy = xy[0] - self.origin[0], xy[1] - self.origin[1]
        return (dx * self.u_dir[0] + dy * self.u_dir[1], dx * self.v_dir[0] + dy * self.v_dir[1])

    def polygon_to_design(self, poly: ShapelyPolygon) -> ShapelyPolygon:
        return ShapelyPolygon(
            [self.to_design(p) for p in poly.exterior.coords],
            [[self.to_design(p) for p in ring.coords] for ring in poly.interiors],
        )

    def rect(self, u0: int, v0: int, u1: int, v1: int) -> Polygon2D:
        return Polygon2D(
            outer=[
                self.to_local(u0, v0),
                self.to_local(u1, v0),
                self.to_local(u1, v1),
                self.to_local(u0, v1),
            ]
        )


def _feature_shape(f: SiteFeature):
    g = f.geometry
    if isinstance(g, PolygonGeometry):
        return g.polygon.to_shapely()
    if isinstance(g, PolylineGeometry):
        return g.line.to_shapely()
    if isinstance(g, PointGeometry):
        return Point(g.xy)
    return None


def limit_polygon(site: Site) -> tuple[ShapelyPolygon, str, str]:
    """Where the building may stand: (polygon, label, epistemic status)."""
    if site.buildable_envelope is not None:
        env = site.buildable_envelope
        return env.polygon.to_shapely(), f"buildable envelope ({env.basis})", env.status.value
    if site.boundary is not None:
        return site.boundary.to_shapely(), "parcel boundary (no buildable envelope)", "unknown"
    raise FrameError("the site has neither a buildable envelope nor a parcel boundary")


def design_frame(site: Site) -> DesignFrame:
    if site.coordinates.local is None:
        raise FrameError("the site has no local coordinate system; ingest and frame it first")
    outline = site.boundary.to_shapely() if site.boundary is not None else limit_polygon(site)[0]
    ring = list(outline.exterior.coords)[:-1]
    edges = [(ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring))]

    def length(e: tuple[Point2, Point2]) -> float:
        return math.dist(e[0], e[1])

    frontage = [f for f in site.features if f.kind is SiteFeatureKind.FRONTAGE]
    roads = [f for f in site.features if f.kind is SiteFeatureKind.ROAD]
    access = [f for f in site.features if f.kind is SiteFeatureKind.ACCESS_POINT]
    edge: tuple[Point2, Point2]
    feature_id: str | None = None
    if frontage:
        shape = unary_union([_feature_shape(f) for f in frontage]).buffer(0.5)
        edge = max(edges, key=lambda e: (LineString(e).intersection(shape).length, length(e)))
        feature_id = frontage[0].id
        basis = f"u axis along the parcel edge matching frontage feature {feature_id}"
    elif roads or access:
        pool = roads or access
        shapes = [(f.id, _feature_shape(f)) for f in pool]

        near = unary_union([s for _, s in shapes]).buffer(1.0)

        def score(e: tuple[Point2, Point2]) -> tuple[float, float, float]:
            line = LineString(e)
            # Run along the road first: an edge only touching it at a corner loses.
            return (
                round(line.intersection(near).length, 6),
                -min(line.distance(s) for _, s in shapes),
                length(e),
            )

        edge = max(edges, key=score)
        feature_id = min(shapes, key=lambda fs: LineString(edge).distance(fs[1]))[0]
        kind = "road" if roads else "access point"
        basis = f"u axis along the parcel edge nearest {kind} {feature_id}"
    else:
        edge = max(edges, key=length)
        basis = "no road on record: u axis along the longest parcel edge (assumption)"
    (x0, y0), (x1, y1) = edge
    d = math.dist(edge[0], edge[1])
    u_dir = ((x1 - x0) / d, (y1 - y0) / d)
    v_dir = (-u_dir[1], u_dir[0])
    centroid = outline.centroid
    if (centroid.x - x0) * v_dir[0] + (centroid.y - y0) * v_dir[1] < 0:
        v_dir = (-v_dir[0], -v_dir[1])
    probe = DesignFrame((x0, y0), u_dir, v_dir, basis, None, None)
    limit = probe.polygon_to_design(limit_polygon(site)[0])
    umin, vmin, _, _ = limit.bounds
    origin = probe.to_local_m(math.floor(umin), math.floor(vmin))
    road_edge = (edge[0], edge[1]) if (frontage or roads or access) else None
    return DesignFrame(origin, u_dir, v_dir, basis, road_edge, feature_id)


def free_intervals(
    poly: ShapelyPolygon, cross_lo: float, cross_hi: float, axis: str
) -> list[tuple[float, float]]:
    """Ranges along ``axis`` ("u" or "v") where a strip spanning [cross_lo, cross_hi]
    on the other axis lies entirely inside ``poly`` (design-frame metres)."""
    coords = [c for ring in [poly.exterior, *poly.interiors] for c in ring.coords]
    ci = 1 if axis == "u" else 0
    crit = sorted({cross_lo, cross_hi, *(c[ci] for c in coords if cross_lo < c[ci] < cross_hi)})
    minx, miny, maxx, maxy = poly.bounds
    span = (minx - 1.0, maxx + 1.0) if axis == "u" else (miny - 1.0, maxy + 1.0)
    current: list[tuple[float, float]] | None = None
    for c in crit:
        line = (
            LineString([(span[0], c), (span[1], c)])
            if axis == "u"
            else LineString([(c, span[0]), (c, span[1])])
        )
        hit = line.intersection(poly)
        parts = getattr(hit, "geoms", [hit])
        ivals: list[tuple[float, float]] = []
        for p in parts:
            if p.is_empty or p.geom_type != "LineString":
                continue
            vals = [q[0] if axis == "u" else q[1] for q in p.coords]
            ivals.append((min(vals), max(vals)))
        ivals.sort()
        if current is None:
            current = ivals
        else:
            current = [
                (max(a0, b0), min(a1, b1))
                for a0, a1 in current
                for b0, b1 in ivals
                if min(a1, b1) > max(a0, b0)
            ]
        if not current:
            return []
    return current or []


def best_interval_dm(
    poly: ShapelyPolygon, cross_lo_dm: int, cross_hi_dm: int, axis: str
) -> tuple[int, int] | None:
    """Longest free range, snapped inward to the grid, or None."""
    shrunk = poly.buffer(-ENVELOPE_MARGIN_M)
    if shrunk.is_empty or shrunk.geom_type != "Polygon":
        shrunk = poly
    ivals = free_intervals(shrunk, from_dm(cross_lo_dm), from_dm(cross_hi_dm), axis)
    best: tuple[int, int] | None = None
    for lo, hi in ivals:
        a, b = math.ceil(lo / GRID_M - 1e-9), math.floor(hi / GRID_M + 1e-9)
        if b > a and (best is None or b - a > best[1] - best[0]):
            best = (a, b)
    return best


class Ground:
    """Surveyed terrain sampled in the design frame. None means unknown."""

    def __init__(self, site: Site, frame: DesignFrame) -> None:
        self.frame = frame
        self.surface = site_surface(site)
        self.from_stored_surface = site.terrain.surface is not None

    @property
    def known(self) -> bool:
        return self.surface is not None

    def at(self, u: float, v: float) -> float | None:
        if self.surface is None:
            return None
        return elevation_at(self.surface, self.frame.to_local_m(u, v))

    def mean_along(self, pts: list[tuple[float, float]]) -> float | None:
        zs = [z for z in (self.at(u, v) for u, v in pts) if z is not None]
        return sum(zs) / len(zs) if zs else None

    def mean_line(self, a: tuple[float, float], b: tuple[float, float], n: int = 9):
        pts = [
            (a[0] + (b[0] - a[0]) * i / (n - 1), a[1] + (b[1] - a[1]) * i / (n - 1))
            for i in range(n)
        ]
        return self.mean_along(pts)
