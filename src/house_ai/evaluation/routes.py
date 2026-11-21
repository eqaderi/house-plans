"""Shortest point paths inside net-floor polygons through explicit portals.

Visibility graph includes concave corners and obstacle vertices. No exterior
shortcuts and no coincident-level links. A stair with a declared straight walking
line is a measured pitch-line edge; a stair without one is an *estimated* edge
between the free-floor points nearest its footprint centroid on each connected
floor, of length hypot((risers - 1) x going, rise), and any
route using it is inferred rather than measured. A stair without riser data is
not linked. This measures a point route, not an accessibility/body-width certificate.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations

import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points

from house_ai.domain.base import EXTERIOR
from house_ai.domain.model import HouseModel
from house_ai.domain.program import SpaceFunction

from .usability_geometry import EPS, free_floor, opening_segment


@dataclass(frozen=True)
class Route:
    length_m: float
    space_ids: tuple[str, ...]
    element_ids: tuple[str, ...]
    level_changes: int
    estimated: bool = False


def _segments_covered(cover, starts, ends):
    """Whether each straight segment starts[k]–ends[k] lies inside the prepared ``cover``."""
    if not len(starts):
        return np.zeros(0, dtype=bool)
    lines = shapely.linestrings(np.stack([np.asarray(starts), np.asarray(ends)], axis=1))
    return shapely.covers(cover, lines)


@lru_cache(maxsize=512)
def _floor_visibility(poly_wkb):
    """The polygon's corners, its prepared EPS cover, and which corner pairs see each other.

    Depends only on the floor, so every route query on the same floor reuses it.
    """
    poly = shapely.from_wkb(poly_wkb)
    parts = [poly] if poly.geom_type == "Polygon" else list(getattr(poly, "geoms", []))
    corners = []
    for part in parts:
        if part.geom_type == "Polygon":
            corners.extend(list(part.exterior.coords)[:-1])
            for ring in part.interiors:
                corners.extend(list(ring.coords)[:-1])
    cover = poly.buffer(EPS)
    shapely.prepare(cover)
    pairs = list(combinations(range(len(corners)), 2))
    seen = _segments_covered(
        cover, [corners[i] for i, _ in pairs], [corners[j] for _, j in pairs]
    )
    return corners, cover, [pair for pair, ok in zip(pairs, seen, strict=True) if ok]


def shortest_in_polygon(poly, a, b):
    """Visibility graph gives exact polygonal geodesic length, including holes."""
    corners, cover, corner_pairs = _floor_visibility(poly.wkb)
    if not cover.covers(Point(a)) or not cover.covers(Point(b)):
        return None
    if cover.covers(LineString([a, b])):
        return math.dist(a, b)
    # Node 0 is a, node 1 is b, corner k is node k + 2. Every neighbour list is in
    # ascending node order, as an all-pairs scan in index order would build it.
    vertices = [a, b, *corners]
    graph = {i: [] for i in range(len(vertices))}
    sees_a = _segments_covered(cover, [a] * len(corners), corners)
    sees_b = _segments_covered(cover, [b] * len(corners), corners)
    for end, sees in ((0, sees_a), (1, sees_b)):
        for k, ok in enumerate(sees):
            if ok:
                graph[end].append((k + 2, math.dist(vertices[end], corners[k])))
    for k in range(len(corners)):
        for end, sees in ((0, sees_a), (1, sees_b)):
            if sees[k]:
                graph[k + 2].append((end, math.dist(vertices[end], corners[k])))
    for i, j in corner_pairs:
        d = math.dist(corners[i], corners[j])
        graph[i + 2].append((j + 2, d))
        graph[j + 2].append((i + 2, d))
    dist, queue = {0: 0.0}, [(0.0, 0)]
    while queue:
        d, i = heapq.heappop(queue)
        if i == 1:
            return d
        if d > dist[i]:
            continue
        for j, w in graph[i]:
            if d + w < dist.get(j, math.inf):
                dist[j] = d + w
                heapq.heappush(queue, (d + w, j))
    return None


_CACHE: tuple[str, RouteNetwork] | None = None


class RouteNetwork:
    @classmethod
    def for_model(cls, model: HouseModel) -> RouteNetwork:
        """Reuse the network built for an identical model (one entry, content keyed)."""
        global _CACHE
        key = model.model_dump_json()
        if _CACHE is None or _CACHE[0] != key:
            _CACHE = (key, cls(model))
        return _CACHE[1]

    def __init__(self, model: HouseModel):  # noqa: C901
        self.model = model
        self.nodes = {}  # key -> (space, point, element)
        self.edges = {}
        self.entrances = []
        self.unknown_stairs = []
        self.estimated_stairs = []
        floors = {s.id: free_floor(model, s) for s in model.spaces}
        #: Spaces to walk to. A stair space with no floor beside its flight (a stairwell or
        #: stair hall, ADR 0023) is walked through on the flight, not walked to.
        self.destinations = [
            s.id
            for s in model.spaces
            if not (s.function is SpaceFunction.STAIR and floors[s.id].is_empty)
        ]

        def node(key, sid, xy, element):
            if not floors[sid].buffer(EPS).covers(Point(xy)):
                return None
            self.nodes[key] = (sid, tuple(xy), element)
            self.edges[key] = []
            return key

        for s in model.spaces:
            if not floors[s.id].is_empty:
                c = floors[s.id].representative_point()
                node("space:" + s.id, s.id, (c.x, c.y), s.id)
        from .evaluators import _pedestrian_entrances

        entrances, self.entrance_basis = _pedestrian_entrances(model)
        for o in model.openings:
            if not o.is_passable:
                continue
            mid = opening_segment(model, o).interpolate(0.5, normalized=True)
            reach = model.wall(o.host_wall_id).thickness_m / 2 + EPS
            ends = []
            for sid in o.connects:
                if sid == EXTERIOR:
                    continue
                # A threshold leaves the wall solid under the door: step to the finish face.
                floor = floors[sid]
                xy = mid.coords[0]
                if not floor.is_empty and reach >= floor.distance(mid) > EPS:
                    xy = nearest_points(floor, mid)[0].coords[0]
                k = node(f"door:{o.id}:{sid}", sid, xy, o.id)
                if k:
                    ends.append(k)
            if len(ends) == 2:
                self.link(*ends, math.dist(self.nodes[ends[0]][1], self.nodes[ends[1]][1]))
            elif o.id in entrances:
                self.entrances.extend(ends)
        for st in model.stairs:
            if st.walking_line is None:
                self._estimated_stair(st, node, floors)
                continue
            line = LineString(st.walking_line)
            rise = (
                model.level(st.to_level_id).elevation_m - model.level(st.from_level_id).elevation_m
            )
            ends = [
                node(f"stair:{st.id}:{sid}", sid, xy, st.id)
                for sid, xy in (
                    (st.bottom_space_id, st.walking_line[0]),
                    (st.top_space_id, st.walking_line[-1]),
                )
            ]
            if (
                all(ends)
                and rise > 0
                and line.length > EPS
                and line.is_simple
                and st.footprint.to_shapely().buffer(EPS).covers(line)
            ):
                # Pitch-line 3D length: flights rise, landings stay level (ADR 0023).
                zs = st.vertex_heights(rise)
                pts = st.walking_line
                length = sum(
                    math.hypot(math.dist(a, b), z1 - z0)
                    for (a, b), z0, z1 in zip(
                        zip(pts, pts[1:], strict=False), zs, zs[1:], strict=False
                    )
                )
                self.link(*ends, length, stair=True)
            else:
                self.unknown_stairs.append(st.id)
        by_space = {}
        for key, (sid, _, _) in self.nodes.items():
            by_space.setdefault(sid, []).append(key)
        for sid, keys in by_space.items():
            for a, b in combinations(keys, 2):
                d = shortest_in_polygon(floors[sid], self.nodes[a][1], self.nodes[b][1])
                if d is not None:
                    self.link(a, b, d)

    def _estimated_stair(self, st, node, floors):
        rise = (
            self.model.level(st.to_level_id).elevation_m
            - self.model.level(st.from_level_id).elevation_m
        )
        c = st.footprint.to_shapely().centroid
        ends = []
        for sid in (st.bottom_space_id, st.top_space_id):
            # A stairwell void can cover the centroid: attach at the nearest free floor.
            floor = floors[sid]
            xy = (c.x, c.y) if floor.is_empty else nearest_points(floor, c)[0].coords[0]
            ends.append(node(f"stair:{st.id}:{sid}", sid, xy, st.id))
        if all(ends) and rise > 0 and st.riser_count and st.tread_depth_m:
            run = max(1, st.riser_count - 1) * st.tread_depth_m
            self.link(*ends, math.hypot(run, rise), stair=True, estimated=True)
            self.estimated_stairs.append(st.id)
        else:
            self.unknown_stairs.append(st.id)

    def link(self, a, b, length, stair=False, estimated=False):
        self.edges[a].append((b, length, stair, estimated))
        self.edges[b].append((a, length, stair, estimated))

    def route(self, starts, end):
        if end not in self.nodes:
            return None
        starts = sorted(k for k in starts if k in self.nodes)
        dist = {k: 0.0 for k in starts}
        parents = {k: None for k in starts}
        changes = {k: 0 for k in starts}
        guessed = {k: False for k in starts}
        queue = [(0.0, k) for k in starts]
        heapq.heapify(queue)
        while queue:
            d, k = heapq.heappop(queue)
            if d > dist[k]:
                continue
            if k == end:
                path = []
                while k is not None:
                    path.append(k)
                    k = parents[k]
                path.reverse()
                spaces, elements = [], []
                for key in path:
                    sid, _, element = self.nodes[key]
                    if not spaces or spaces[-1] != sid:
                        spaces.append(sid)
                    if element not in elements:
                        elements.append(element)
                return Route(d, tuple(spaces), tuple(elements), changes[end], guessed[end])
            for other, length, stair, estimated in self.edges[k]:
                nd = d + length
                if nd < dist.get(other, math.inf):
                    dist[other] = nd
                    parents[other] = k
                    changes[other] = changes[k] + int(stair)
                    guessed[other] = guessed[k] or estimated
                    heapq.heappush(queue, (nd, other))
        return None

    def from_entrance(self, space_id):
        return self.route(self.entrances, "space:" + space_id)

    def between(self, a, b):
        return self.route(["space:" + a], "space:" + b)

    def entrance_routes(self):
        return {
            s.id: route
            for s in self.model.spaces
            if (route := self.from_entrance(s.id)) is not None
        }

    def entrance_distances(self):
        return {sid: route.length_m for sid, route in self.entrance_routes().items()}

    def daily_routes(self):
        pairs = [
            (SpaceFunction.GARAGE, SpaceFunction.KITCHEN),
            (SpaceFunction.ENTRY, SpaceFunction.KITCHEN),
            (SpaceFunction.ENTRY, SpaceFunction.FAMILY),
            (SpaceFunction.KITCHEN, SpaceFunction.FAMILY),
        ]
        for a, b in pairs:
            sources = [s for s in self.model.spaces if s.function == a]
            targets = [s for s in self.model.spaces if s.function == b]
            yield a, b, [(s, t, self.between(s.id, t.id)) for s in sources for t in targets]
