"""S12: the cached route graph and vectorised furniture search give the plain results.

`shortest_in_polygon` reuses one visibility graph per floor, and the furniture search
tests every candidate position of a rotation in one array call (ADR 0035). These tests
pin both to hand-computed lengths and to the straightforward one-at-a-time versions.
"""

from __future__ import annotations

import heapq
import math
from itertools import combinations

import pytest
import shapely
from shapely.geometry import LineString, Point, Polygon, box

from house_ai.evaluation.routes import shortest_in_polygon
from house_ai.evaluation.templates import TEMPLATES
from house_ai.evaluation.usability_geometry import EPS, shifted, template_shapes

L_FLOOR = Polygon([(0, 0), (6, 0), (6, 2), (2, 2), (2, 6), (0, 6)])
SQUARE = box(0, 0, 6, 6)
RING = box(0, 0, 6, 6).difference(box(2, 2, 4, 4))


def plain_shortest(poly, a, b):
    """The all-pairs visibility graph, built afresh for every query."""
    cover = poly.buffer(EPS)
    if not cover.covers(Point(a)) or not cover.covers(Point(b)):
        return None
    if cover.covers(LineString([a, b])):
        return math.dist(a, b)
    parts = [poly] if poly.geom_type == "Polygon" else list(poly.geoms)
    vertices = [a, b]
    for part in parts:
        vertices.extend(list(part.exterior.coords)[:-1])
        for ring in part.interiors:
            vertices.extend(list(ring.coords)[:-1])
    graph = {i: [] for i in range(len(vertices))}
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


def test_one_cached_graph_per_floor_never_mixes_floors():
    # Same outer corners, different floors, queried in turn: each keeps its own graph.
    for _ in range(2):
        assert shortest_in_polygon(L_FLOOR, (5, 1), (1, 5)) == pytest.approx(2 * math.sqrt(10))
        assert shortest_in_polygon(SQUARE, (5, 1), (1, 5)) == pytest.approx(math.sqrt(32))
        # Around the 2 m hole: two diagonals of sqrt(2) and a 2 m straight.
        assert shortest_in_polygon(RING, (1, 3), (5, 3)) == pytest.approx(2 * math.sqrt(2) + 2)
        assert shortest_in_polygon(RING, (3, 3), (5, 3)) is None


@pytest.mark.parametrize("floor", [L_FLOOR, RING], ids=["l-shape", "ring"])
def test_cached_graph_equals_a_fresh_graph_for_every_query(floor):
    xmin, ymin, xmax, ymax = floor.bounds
    points = [
        (xmin + (xmax - xmin) * i / 7, ymin + (ymax - ymin) * j / 7)
        for i in range(1, 7)
        for j in range(1, 7)
    ]
    inside = [p for p in points if floor.covers(Point(p))]
    assert len(inside) >= 20
    for a, b in combinations(inside[:20], 2):
        assert shortest_in_polygon(floor, a, b) == plain_shortest(floor, a, b)


@pytest.mark.parametrize("template_id", sorted(TEMPLATES))
def test_shifted_candidates_equal_template_shapes_exactly(template_id):
    t = TEMPLATES[template_id]
    shifts = [(0.0, 0.0), (0.1, 0.2), (1.35, -0.4), (2.7000000000000002, 3.3)]
    for angle in (0, 90, 180, 270):
        base = template_shapes(t, (0, 0), angle)
        for i in (0, 1):
            moved = shifted(base[i], shifts)
            for k, p in enumerate(shifts):
                expected = template_shapes(t, p, angle)[i]
                assert shapely.get_coordinates(moved[k]).tolist() == [
                    list(c) for c in expected.exterior.coords
                ]
