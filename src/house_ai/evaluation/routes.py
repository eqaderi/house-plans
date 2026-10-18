"""Shortest point paths inside net-floor polygons through explicit portals.

Visibility graph includes concave corners and obstacle vertices. No exterior
shortcuts, no coincident-level links, and no link across an unknown stair.
This measures a point route, not an accessibility/body-width certificate.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from itertools import combinations

from shapely.geometry import LineString, Point

from house_ai.domain.base import EXTERIOR
from house_ai.domain.model import HouseModel, StairKind
from house_ai.domain.program import SpaceFunction

from .usability_geometry import EPS, free_floor, opening_segment


@dataclass(frozen=True)
class Route:
    length_m: float
    space_ids: tuple[str, ...]
    element_ids: tuple[str, ...]
    level_changes: int


def shortest_in_polygon(poly, a, b):
    """Visibility graph gives exact polygonal geodesic length, including holes."""
    if not poly.buffer(EPS).covers(Point(a)) or not poly.buffer(EPS).covers(Point(b)):
        return None
    if poly.buffer(EPS).covers(LineString([a, b])):
        return math.dist(a, b)
    parts = [poly] if poly.geom_type == "Polygon" else list(getattr(poly, "geoms", []))
    vertices = [a, b]
    for part in parts:
        if part.geom_type == "Polygon":
            vertices.extend(list(part.exterior.coords)[:-1])
            for ring in part.interiors:
                vertices.extend(list(ring.coords)[:-1])
    graph = {i: [] for i in range(len(vertices))}
    cover = poly.buffer(EPS)
    for i, j in combinations(graph, 2):
        if cover.covers(LineString([vertices[i], vertices[j]])):
            d = math.dist(vertices[i], vertices[j])
            graph[i].append((j, d))
            graph[j].append((i, d))
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


class RouteNetwork:
    def __init__(self, model: HouseModel):
        self.model = model
        self.nodes = {}  # key -> (space, point, element)
        self.edges = {}
        self.entrances = []
        self.unknown_stairs = []
        floors = {s.id: free_floor(model, s) for s in model.spaces}

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
            if not o.is_passable or o.sill_m > EPS:
                continue
            xy = opening_segment(model, o).interpolate(0.5, normalized=True).coords[0]
            ends = []
            for sid in o.connects:
                if sid != EXTERIOR:
                    k = node(f"door:{o.id}:{sid}", sid, xy, o.id)
                    if k:
                        ends.append(k)
            if len(ends) == 2:
                self.link(*ends, 0.0)
            elif o.id in entrances:
                self.entrances.extend(ends)
        for st in model.stairs:
            if (
                st.walking_line is None
                or st.kind != StairKind.STRAIGHT
                or len(st.walking_line) != 2
            ):
                self.unknown_stairs.append(st.id)
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
                self.link(*ends, math.hypot(line.length, rise), stair=True)
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

    def link(self, a, b, length, stair=False):
        self.edges[a].append((b, length, stair))
        self.edges[b].append((a, length, stair))

    def route(self, starts, end):
        if end not in self.nodes:
            return None
        starts = sorted(k for k in starts if k in self.nodes)
        dist = {k: 0.0 for k in starts}
        parents = {k: None for k in starts}
        changes = {k: 0 for k in starts}
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
                return Route(d, tuple(spaces), tuple(elements), changes[end])
            for other, length, stair in self.edges[k]:
                nd = d + length
                if nd < dist.get(other, math.inf):
                    dist[other] = nd
                    parents[other] = k
                    changes[other] = changes[k] + int(stair)
                    heapq.heappush(queue, (nd, other))
        return None

    def from_entrance(self, space_id):
        return self.route(self.entrances, "space:" + space_id)

    def between(self, a, b):
        return self.route(["space:" + a], "space:" + b)

    def entrance_distances(self):
        return {
            s.id: route.length_m
            for s in self.model.spaces
            if (route := self.from_entrance(s.id)) is not None
        }

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
