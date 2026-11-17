"""Enclosure: walls, openings, slabs and ceilings derived around hand-written rectangles.

No project, no solver: each rule is checked on rectangles in the design frame (decimetres)
and a fixed terrain whose ground values are worked out by hand in the comments.
"""

from __future__ import annotations

import pytest

from house_ai.domain.model import Level, WallKind
from house_ai.domain.program import SpaceFunction as S
from house_ai.generation.enclosure import EnclosedSpace, Enclosure, Rect
from house_ai.generation.frame import DesignFrame

FRAME = DesignFrame((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), "test frame", None, None)
ENTRY = Level(id="lv-entry", name="Entry", elevation_m=0.0, floor_to_floor_m=3.0)


class Flat:
    """Ground everywhere at a fixed height (design-frame metres)."""

    def __init__(self, z: float = 0.0) -> None:
        self.z = z

    def mean_along(self, pts):
        return self.z if pts else None

    def mean_line(self, a, b, n: int = 9):
        return self.z


class RisingAway:
    """Ground rising 0.5 m per metre away from the road (+v); 0 at the road (v = 0)."""

    def mean_along(self, pts):
        return sum(0.5 * v for _, v in pts) / len(pts)

    def mean_line(self, a, b, n: int = 9):
        return 0.5 * (a[1] + b[1]) / 2


def space(sid, function, rect, level="lv-entry", **kw) -> EnclosedSpace:
    return EnclosedSpace(id=sid, level_id=level, rect=Rect(*rect), function=function, **kw)


def wall(enc: Enclosure, a, b, orient=None):
    found = [
        w for w in enc.walls if w.sides() == {a, b} and (orient is None or w.orient == orient)
    ]
    assert len(found) == 1, found
    return found[0]


def test_two_rooms_share_one_interior_wall_and_have_exterior_walls_around():
    enc = Enclosure(
        [ENTRY],
        [space("sp-a", S.LIVING, (0, 0, 40, 30)), space("sp-b", S.BEDROOM, (40, 0, 70, 30))],
        FRAME,
        Flat(),
    )
    # Front and back lines split where the room changes: 2 + 2, plus three cross lines.
    assert len(enc.walls) == 7
    shared = wall(enc, "sp-a", "sp-b")
    assert (shared.orient, shared.c, shared.a, shared.b) == ("v", 40, 0, 30)
    assert shared.kind is WallKind.INTERIOR and shared.thickness == 0.15
    outside = [w for w in enc.walls if None in w.sides()]
    assert len(outside) == 6
    assert {w.kind for w in outside} == {WallKind.EXTERIOR}
    assert {w.thickness for w in outside} == {0.30}
    # Every wall knows the space on each side: room A has a front and a back wall.
    assert sorted(w.c for w in outside if w.sides() == {"sp-a", None} and w.orient == "h") == [
        0,
        30,
    ]


def test_wall_models_carry_ids_per_level_local_coordinates_and_materials():
    enc = Enclosure([ENTRY], [space("sp-a", S.LIVING, (0, 0, 40, 30))], FRAME, Flat())
    models = enc.wall_models()
    assert [w.id for w in models] == ["w-entry-001", "w-entry-002", "w-entry-003", "w-entry-004"]
    front = models[0]
    assert (front.start, front.end) == ((0.0, 0.0), (4.0, 0.0))
    assert front.height_m == 2.8 and front.material_id == "m-ext-wall"
    assert {m.id for m in enc.materials()} >= {"m-ext-wall", "m-int-wall", "m-retaining"}


def test_exterior_walls_holding_back_ground_are_retaining():
    # One 4 m x 3 m room at z = 0 on ground rising 0.5 m/m away from the road.
    enc = Enclosure([ENTRY], [space("sp-a", S.LIVING, (0, 0, 40, 30))], FRAME, RisingAway())
    back = next(w for w in enc.walls if w.orient == "h" and w.c == 30)
    front = next(w for w in enc.walls if w.orient == "h" and w.c == 0)
    side = next(w for w in enc.walls if w.orient == "v" and w.c == 0)
    # Back face: ground sampled 0.6 m outside, at v = 3.6 m -> 1.8 m above the floor.
    assert back.kind is WallKind.RETAINING
    assert back.retained_m == pytest.approx(1.8)
    # Front face: ground at v = -0.6 m is below the floor -> nothing retained.
    assert front.kind is WallKind.EXTERIOR and front.retained_m == 0.0
    # Side face: four samples at v = 0.375, 1.125, 1.875, 2.625 m -> mean 0.75 m > 0.6 m.
    assert side.kind is WallKind.RETAINING
    assert side.retained_m == pytest.approx(0.75)
    assert enc.wall_models()[[w.id for w in enc.walls].index(back.id)].material_id == (
        "m-retaining"
    )


def test_ground_less_than_the_threshold_above_the_floor_is_not_retained():
    enc = Enclosure([ENTRY], [space("sp-a", S.LIVING, (0, 0, 40, 30))], FRAME, Flat(0.6))
    assert {w.kind for w in enc.walls} == {WallKind.EXTERIOR}
    assert [w.retained_m for w in enc.walls] == pytest.approx([0.6] * 4)


def test_unknown_terrain_retains_nothing():
    class Unknown:
        def mean_along(self, pts):
            return None

    enc = Enclosure([ENTRY], [space("sp-a", S.LIVING, (0, 0, 40, 30))], FRAME, Unknown())
    assert {w.kind for w in enc.walls} == {WallKind.EXTERIOR}


def test_face_against_a_higher_level_is_a_party_wall_not_a_window_wall():
    up = Level(id="lv-up-150", name="Up", elevation_m=1.5, floor_to_floor_m=3.0)
    enc = Enclosure(
        [ENTRY, up],
        [
            space("sp-low", S.LIVING, (0, 0, 40, 30)),
            space("sp-high", S.BEDROOM, (0, 30, 40, 60), level="lv-up-150"),
        ],
        FRAME,
        Flat(),
    )
    back = next(w for w in enc.walls if w.level_id == "lv-entry" and w.c == 30 and w.orient == "h")
    assert back.sides() == {"sp-low", None}
    assert back.kind is WallKind.INTERIOR and back.party
    model = next(m for m in enc.wall_models() if m.id == back.id)
    assert model.material_id == "m-ext-wall"
    # The lower storey, 3 m high, also stands against the higher room's front face.
    high_front = next(w for w in enc.walls if w.level_id == "lv-up-150" and w.c == 30)
    assert high_front.kind is WallKind.INTERIOR and high_front.party
    high_back = next(w for w in enc.walls if w.level_id == "lv-up-150" and w.c == 60)
    assert high_back.kind is WallKind.EXTERIOR and not high_back.party
    assert [w.id for w in enc.walls if w.level_id == "lv-up-150"][0] == "w-up-150-001"


def test_terrace_edges_are_parapets_and_its_wall_to_the_room_is_exterior():
    enc = Enclosure(
        [ENTRY],
        [
            space("sp-living", S.LIVING, (0, 0, 40, 30)),
            space("sp-terrace", S.TERRACE, (0, 30, 40, 50)),
        ],
        FRAME,
        Flat(),
    )
    inner = wall(enc, "sp-living", "sp-terrace")
    assert inner.kind is WallKind.EXTERIOR and inner.thickness == 0.30
    edges = [w for w in enc.walls if w.sides() == {"sp-terrace", None}]
    assert len(edges) == 3
    assert {(w.kind, w.thickness, w.height_m) for w in edges} == {(WallKind.PARAPET, 0.2, 1.0)}

