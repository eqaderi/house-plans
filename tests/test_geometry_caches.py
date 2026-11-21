"""S12: the cached route graph and vectorised furniture search give the plain results.

`shortest_in_polygon` reuses one visibility graph per floor, and the furniture search
tests every candidate position of a rotation in one array call (ADR 0035). These tests
pin both to hand-computed lengths and to the straightforward one-at-a-time versions, and
the search's three array tests (envelope inside the floor, envelope clear of door swings,
body clear of door approaches) to rooms sized by hand from the double-bed template.
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
from house_ai.evaluation.usability_geometry import EPS, _fit_cached, shifted, template_shapes

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


# The double bed is 1.6 x 2.0 m with 0.6 m clear on both sides and 0.75 m at the foot, so
# its envelope is (0.6 + 1.6 + 0.6) x (2.0 + 0.75) = 2.8 x 2.75 m.
BED = TEMPLATES["bed-double"]
BED_ROOM = box(0, 0, 2.8, 2.75)


def _fit_bed(floor, swings=None, approaches=None):
    """The furniture search for one double bed, in the room's own frame."""
    nothing = shapely.GeometryCollection()
    _fit_cached.cache_clear()
    return _fit_cached(
        floor.wkb, (swings or nothing).wkb, (approaches or nothing).wkb, (BED.model_dump_json(),)
    )


def test_the_double_bed_template_has_the_dimensions_the_rooms_below_are_sized_from():
    assert [BED.width.value, BED.depth.value] == [1.6, 2.0]
    assert [BED.left.value, BED.right.value, BED.front.value, BED.back.value] == [0.6, 0.6, 0.75, 0]


def test_a_double_bed_fits_a_room_exactly_the_size_of_its_envelope():
    ((body, envelope),) = _fit_bed(BED_ROOM)
    # The envelope fills the room; the body keeps 0.6 m on both sides and is 2.0 m long, with
    # its head on one 2.8 m wall and 0.75 m clear at the other.
    assert envelope == pytest.approx((0, 0, 2.8, 2.75))
    assert (body[0], body[2]) == pytest.approx((0.6, 2.2))
    assert (body[1], body[3]) in (pytest.approx((0.75, 2.75)), pytest.approx((0, 2.0)))
    # 10 cm narrower or shorter and no rotation has room for the envelope.
    assert _fit_bed(box(0, 0, 2.7, 2.75)) is None
    assert _fit_bed(box(0, 0, 2.8, 2.65)) is None


def test_a_double_bed_does_not_fit_an_l_shaped_room_with_narrow_arms():
    """The envelope must lie inside the floor, not only inside its bounding box."""

    def l_room(arm):
        return Polygon([(0, 0), (6, 0), (6, arm), (arm, arm), (arm, 6), (0, 6)])

    # 1.2 m arms: 6 x 1.2 + 1.2 x 4.8 = 12.96 m² of floor and 6 x 6 m of bounds, both more
    # than the bed needs, but neither arm is 2.75 m wide.
    assert l_room(1.2).area == pytest.approx(12.96)
    assert _fit_bed(l_room(1.2)) is None
    assert _fit_bed(l_room(2.7)) is None
    # 2.75 m arms take the envelope lengthways: it lies inside one arm.
    ((body, envelope),) = _fit_bed(l_room(2.75))
    assert l_room(2.75).buffer(EPS).covers(box(*envelope))
    assert box(*envelope).area == pytest.approx(2.8 * 2.75)
    assert box(*body).area == pytest.approx(1.6 * 2.0)


def test_door_swings_keep_the_envelope_out_and_door_approaches_keep_the_body_out():
    # In the exact-fit room the envelope is the whole floor, so any door swing overlaps it.
    assert _fit_bed(BED_ROOM, swings=box(0, 0, 0.5, 0.5)) is None
    # A door approach may lie in the clear zone: a 0.5 m strip along one 2.8 m wall leaves
    # the rotation with the foot of the bed at that wall.
    ((body, _),) = _fit_bed(BED_ROOM, approaches=box(0, 0, 2.8, 0.5))
    assert (body[1], body[3]) == pytest.approx((0.75, 2.75))
    # In either rotation the body covers y 0.75..2.0 across x 0.6..2.2, so an approach in the
    # middle of the room leaves no place for it.
    assert _fit_bed(BED_ROOM, approaches=box(1.0, 1.0, 1.8, 1.75)) is None
