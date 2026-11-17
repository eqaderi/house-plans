"""Enclosure: walls, openings, slabs and ceilings derived around hand-written rectangles.

No project, no solver: each rule is checked on rectangles in the design frame (decimetres)
and a fixed terrain whose ground values are worked out by hand in the comments.
"""

from __future__ import annotations

import pytest

from house_ai.domain.geometry import Polygon2D
from house_ai.domain.integrity import check_model, errors
from house_ai.domain.model import Level, OpeningKind, Stair, StairKind, WallKind
from house_ai.domain.program import Privacy, ProgramZone, SpaceProgram, SpaceRelationship
from house_ai.domain.program import SpaceFunction as S
from house_ai.domain.site import Site
from house_ai.generation.assemble2d import assemble_2d
from house_ai.generation.enclosure import EnclosedSpace, Enclosure, Rect
from house_ai.generation.frame import DesignFrame
from house_ai.generation.solver2d import PlacedRoom2D, SharedWall, Solution2D
from house_ai.storage.hashing import load_document

from .conftest import AGENT, REPO

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


# --------------------------------------------------------------------- openings


def pair(fa=S.BEDROOM, fb=S.CORRIDOR, depth=30, gap=0) -> Enclosure:
    """Room A (4 m wide) beside room B (3 m wide); the shared wall is ``depth`` dm long."""
    return Enclosure(
        [ENTRY],
        [space("sp-a", fa, (0, 0, 40, depth)), space("sp-b", fb, (40 + gap, 0, 70 + gap, depth))],
        FRAME,
        Flat(),
    )


def test_a_door_is_centred_and_the_next_one_cannot_overlap_it():
    enc = pair(depth=15)
    door = enc.place("lv-entry", "sp-a", "sp-b", OpeningKind.DOOR, 0.9)
    assert door is not None
    # (1.5 m - 0.9 m) / 2 from the wall's start, 0.3 m clear of either end.
    assert (door.offset_m, door.width_m) == (0.3, 0.9)
    assert door.connects == ("sp-a", "sp-b") and door.id == "d-a-b"
    # Even shrunk to 0.7 m and 0.1 m from the ends, a second door would overlap the first.
    assert enc.place("lv-entry", "sp-a", "sp-b", OpeningKind.DOOR, 0.9) is None
    assert len(enc.openings) == 1


def test_a_door_shrinks_to_its_minimum_width_before_a_wall_is_given_up():
    enc = pair(depth=10)
    door = enc.place("lv-entry", "sp-a", "sp-b", OpeningKind.DOOR, 0.9, min_width_m=0.7)
    # 0.9 m does not fit 0.3 m clear of both ends of a 1.0 m wall; 0.7 m does 0.1 m clear.
    assert door is not None and (door.offset_m, door.width_m) == (0.1, 0.7)
    narrow = pair(depth=8)
    assert narrow.place("lv-entry", "sp-a", "sp-b", OpeningKind.DOOR, 0.9) is None


@pytest.mark.parametrize("function", [S.KITCHEN, S.GARAGE])
def test_kitchen_and_garage_doors_keep_to_a_corner(function):
    enc = pair(fa=function)
    door = enc.place("lv-entry", "sp-a", "sp-b", OpeningKind.DOOR, 0.8)
    # 0.3 m from the wall's start, not centred at 1.1 m: the rest stays one run.
    assert door is not None and (door.offset_m, door.width_m) == (0.3, 0.8)
    centred = pair(fa=S.BEDROOM).place("lv-entry", "sp-a", "sp-b", OpeningKind.DOOR, 0.8)
    assert centred is not None and centred.offset_m == 1.1


def test_a_corner_door_narrows_to_leave_a_door_approach_beside_it():
    enc = pair(fa=S.KITCHEN, depth=19)
    door = enc.place("lv-entry", "sp-a", "sp-b", OpeningKind.DOOR, 0.8)
    # 1.9 m - 0.3 m clear - 0.9 m approach leaves a 0.7 m door at the corner.
    assert door is not None and (door.offset_m, door.width_m) == (0.3, 0.7)


def test_a_garage_opening_to_the_outside_is_centred():
    enc = Enclosure([ENTRY], [space("sp-garage", S.GARAGE, (0, 0, 60, 60))], FRAME, Flat())
    front = next(w for w in enc.walls if w.orient == "h" and w.c == 0)
    door = enc.place("lv-entry", "sp-garage", None, OpeningKind.DOOR, 2.6, walls=[front])
    assert door is not None and (door.offset_m, door.width_m) == (1.7, 2.6)
    assert door.connects == ("sp-garage", "exterior") and door.id == "d-garage-ext"


def test_preferred_direction_picks_the_road_face_first():
    enc = Enclosure([ENTRY], [space("sp-a", S.ENTRY, (0, 0, 30, 60))], FRAME, Flat())
    door = enc.place("lv-entry", "sp-a", None, OpeningKind.DOOR, 1.0, prefer=(0, -1))
    # The 3 m road face (outward -v) wins over the longer 6 m side faces.
    host = next(w for w in enc.walls if w.id == door.host_wall_id)
    assert (host.orient, host.c) == ("h", 0)


def test_no_exterior_opening_across_a_crevice_with_a_room_just_beyond():
    # A 0.1 m gap between A and B does not clear a 0.15 m half wall plus the 0.05 m probe.
    enc = pair(fa=S.KITCHEN, fb=S.LIVING, gap=1)
    crevice = next(w for w in enc.walls if w.orient == "v" and w.c == 40)
    assert crevice.sides() == {"sp-a", None} and crevice.length_m == 3.0
    assert enc.place("lv-entry", "sp-a", None, OpeningKind.WINDOW, 1.2, walls=[crevice]) is None
    window = enc.place("lv-entry", "sp-a", None, OpeningKind.WINDOW, 1.2, min_width_m=0.6)
    assert window is not None and window.host_wall_id != crevice.id


def test_retaining_and_party_walls_take_no_exterior_opening():
    enc = Enclosure([ENTRY], [space("sp-a", S.LIVING, (0, 0, 40, 30))], FRAME, RisingAway())
    # Back and both sides hold back ground; only the road face can take a window.
    windows = [
        enc.place("lv-entry", "sp-a", None, OpeningKind.WINDOW, 1.2, min_width_m=0.6)
        for _ in range(3)
    ]
    hosts = {next(w for w in enc.walls if w.id == o.host_wall_id).c for o in windows if o}
    assert hosts == {0}
    assert all(w.kind is WallKind.EXTERIOR for w in enc.walls if w.c == 0 and w.orient == "h")


# --------------------------------------------- slabs, ceilings, Zones, relationships

UPPER = Level(id="lv-upper", name="Upper", elevation_m=3.0, floor_to_floor_m=3.0)


def stacked() -> Enclosure:
    """A 4 m x 3 m room, half of it built over by a 2 m x 3 m room, and a terrace beside it."""
    return Enclosure(
        [UPPER, ENTRY],
        [
            space("sp-living", S.LIVING, (0, 0, 40, 30), zone_id="z-day", program_item_id="pi-a"),
            space("sp-terrace", S.TERRACE, (40, 0, 60, 30), zone_id="z-x", program_item_id="pi-t"),
            space("sp-bed", S.BEDROOM, (0, 0, 20, 30), "lv-upper", zone_id="z-night"),
            space("sp-stair", S.STAIR, (20, 0, 40, 10), "lv-upper", program_item_id="pi-a"),
        ],
        FRAME,
        Flat(),
    )


def flight(to_level="lv-upper") -> Stair:
    return Stair(
        id="st-1",
        kind=StairKind.STRAIGHT,
        from_level_id="lv-entry",
        to_level_id=to_level,
        footprint=Polygon2D(outer=[(0.5, 0.5), (1.5, 0.5), (1.5, 2.5), (0.5, 2.5)]),
        bottom_space_id="sp-living",
        top_space_id="sp-bed",
        width_m=1.0,
    )


def test_slabs_floor_each_level_roof_what_nothing_covers_and_void_each_arriving_flight():
    slabs = {s.id: s for s in stacked().slabs([flight()])}
    # Terrace slabs first, then the levels from the lowest up.
    assert list(slabs) == [
        "slab-terrace-terrace",
        "slab-floor-entry",
        "slab-roof-entry",
        "slab-floor-upper",
        "slab-roof-upper",
    ]
    area = {k: s.boundary.to_shapely().area for k, s in slabs.items()}
    assert area["slab-terrace-terrace"] == pytest.approx(6.0)
    assert area["slab-floor-entry"] == pytest.approx(12.0)
    # The upper rooms (2 m x 3 m and 2 m x 1 m) cover 8 m² of the 12 m² below.
    assert area["slab-roof-entry"] == pytest.approx(4.0)
    # The 1 m x 2 m flight arriving on the upper level leaves a hole in its floor.
    assert area["slab-floor-upper"] == pytest.approx(8.0 - 2.0)
    assert len(slabs["slab-floor-upper"].boundary.holes) == 1
    assert area["slab-roof-upper"] == pytest.approx(8.0)
    assert slabs["slab-roof-upper"].top_offset_m == 3.0
    assert slabs["slab-terrace-terrace"].thickness_m == 0.15
    assert {s.thickness_m for k, s in slabs.items() if "terrace" not in k} == {0.25}
    assert {s.material_id for s in slabs.values()} == {"m-slab"}


def test_slab_slivers_under_half_a_square_metre_are_dropped():
    enc = Enclosure(
        [ENTRY, UPPER],
        [
            space("sp-a", S.LIVING, (0, 0, 40, 30)),
            space("sp-b", S.BEDROOM, (0, 0, 40, 29), "lv-upper"),
        ],
        FRAME,
        Flat(),
    )
    # The 4 m x 0.1 m strip not built over is 0.4 m²: no roof slab on the entry level.
    assert "slab-roof-entry" not in {s.id for s in enc.slabs([])}


def test_ceilings_everywhere_but_over_stairs_and_terraces():
    ceilings = stacked().ceilings()
    assert [(c.id, c.space_id, c.height_m) for c in ceilings] == [
        ("ceil-living", "sp-living", 2.7),
        ("ceil-bed", "sp-bed", 2.7),
    ]
    enc = Enclosure(
        [ENTRY], [space("sp-well", S.STAIR, (0, 0, 20, 30), ceiling=True)], FRAME, Flat()
    )
    assert [c.space_id for c in enc.ceilings()] == ["sp-well"]


def test_zones_are_those_the_spaces_use_and_someone_defines():
    zones = stacked().zones(
        [
            ProgramZone(id="z-day", name="Day", privacy=Privacy.PUBLIC),
            ProgramZone(id="z-night", name="Night", privacy=Privacy.PRIVATE),
            ProgramZone(id="z-day", name="Second definition", privacy=Privacy.PRIVATE),
            ProgramZone(id="z-unused", name="Unused", privacy=Privacy.SERVICE),
        ]
    )
    # Sorted by id; the first definition counts; z-x has no definition and is left out.
    assert [(z.id, z.name, z.space_ids) for z in zones] == [
        ("z-day", "Day", ["sp-living"]),
        ("z-night", "Night", ["sp-bed"]),
    ]


def test_relationships_join_the_first_space_of_each_item():
    required = [
        SpaceRelationship(id="adj-1", a="pi-a", b="pi-t", kind="connected", strength="hard"),
        SpaceRelationship(id="adj-2", a="pi-t", b="exterior", kind="connected", strength="hard"),
        SpaceRelationship(
            id="adj-3", a="pi-a", b="pi-t", kind="acoustic_separation", strength="hard"
        ),
    ]
    rels = stacked().relationships(required)
    # pi-a is met by sp-living and sp-stair; the first one listed stands for it.
    assert [(r.id, r.a, r.b, r.kind.value, r.requirement_id) for r in rels] == [
        ("rel-1", "sp-living", "sp-terrace", "connected", "adj-1"),
        ("rel-3", "sp-living", "sp-terrace", "separated", "adj-3"),
    ]


# --------------------------------------------------------------- the 2D adapter

HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"


def hillside() -> tuple[Site, SpaceProgram]:
    site = Site.model_validate(load_document(HILLSIDE / "site.yaml"))
    program = SpaceProgram.model_validate(load_document(HILLSIDE / "space_program.yaml"))
    return site, program


def placed(sid, function, rect, item, zone, level="lv-entry") -> PlacedRoom2D:
    return PlacedRoom2D(sid, sid.removeprefix("sp-").title(), function, level, *rect, item, zone)


def solution(rooms, shared=(), *, strategy="corridor_free", levels=("lv-entry",)) -> Solution2D:
    return Solution2D(
        status="FEASIBLE",
        objective=0.0,
        rooms=list(rooms),
        shared_walls=list(shared),
        levels=list(levels),
        deterministic_time=0.0,
        wall_time_s=0.0,
        seed=0,
        platform_info="test",
        strategy=strategy,
        circulation_share=0.0,
        level_elevations_m={lv: 0.0 for lv in levels},
    )


def test_2d_plan_on_a_slope_has_retaining_walls_where_the_ground_is_held_back():
    site, program = hillside()
    # A 4 m x 2 m entry at the road and a 4 m x 3 m living room behind it, floor at z = 0,
    # on ground rising 0.5 m per metre away from the road.
    rooms = [
        placed("sp-entry", S.ENTRY, (0, 0, 40, 20), "pi-entry", "z-circulation"),
        placed("sp-living", S.LIVING, (0, 20, 40, 50), "pi-living", "z-day"),
    ]
    shared = [SharedWall("sp-entry", "sp-living", "lv-entry", "h", 20, 0, 40)]
    model = assemble_2d(solution(rooms, shared), site, FRAME, RisingAway(), program, AGENT)
    retaining = {(w.start, w.end) for w in model.walls if w.kind is WallKind.RETAINING}
    # Living: back face (ground 2.8 m above the floor 0.6 m outside it) and both side
    # faces (mean of 1.1875, 1.5625, 1.9375, 2.3125 = 1.75 m) hold back ground. The entry's
    # sides (mean 0.5 m) and the front face (ground below the floor) do not.
    assert retaining == {
        ((0.0, 5.0), (4.0, 5.0)),
        ((0.0, 2.0), (0.0, 5.0)),
        ((4.0, 2.0), (4.0, 5.0)),
    }
    assert {w.material_id for w in model.walls if w.kind is WallKind.RETAINING} == {"m-retaining"}
    exterior = {(w.start, w.end) for w in model.walls if w.kind is WallKind.EXTERIOR}
    assert exterior == {
        ((0.0, 0.0), (4.0, 0.0)),
        ((0.0, 0.0), (0.0, 2.0)),
        ((4.0, 0.0), (4.0, 2.0)),
    }
    # No opening is cut into a wall that holds back ground.
    retaining_ids = {w.id for w in model.walls if w.kind is WallKind.RETAINING}
    assert not [o for o in model.openings if o.host_wall_id in retaining_ids]
    assert not errors(check_model(model))


def test_2d_kitchen_door_keeps_to_a_corner_like_a_bar_plan():
    site, program = hillside()
    rooms = [
        placed("sp-kitchen", S.KITCHEN, (0, 0, 40, 30), "pi-kitchen", "z-day"),
        placed("sp-bed", S.BEDROOM, (40, 0, 70, 30), "pi-bed-main", "z-night"),
    ]
    shared = [SharedWall("sp-kitchen", "sp-bed", "lv-entry", "v", 40, 0, 30)]
    model = assemble_2d(solution(rooms, shared), site, FRAME, Flat(), program, AGENT)
    (door,) = [o for o in model.openings if set(o.connects) == {"sp-kitchen", "sp-bed"}]
    # 0.3 m from the end of the 3 m wall, where a centred door would sit at 1.1 m.
    assert (door.offset_m, door.width_m) == (0.3, 0.8)
    assert not errors(check_model(model))


def test_2d_plan_records_its_space_relationships_zones_and_slabs():
    site, program = hillside()
    rooms = [
        placed("sp-kitchen", S.KITCHEN, (0, 0, 40, 30), "pi-kitchen", "z-day"),
        placed("sp-living", S.LIVING, (40, 0, 80, 30), "pi-living", "z-day"),
        placed("sp-terrace", S.TERRACE, (0, 30, 80, 50), "pi-terrace", "z-unknown"),
    ]
    shared = [
        SharedWall("sp-kitchen", "sp-living", "lv-entry", "v", 40, 0, 30),
        SharedWall("sp-living", "sp-terrace", "lv-entry", "h", 30, 40, 80),
    ]
    model = assemble_2d(solution(rooms, shared), site, FRAME, Flat(), program, AGENT)
    # The program asks for kitchen-living (adj-02) and terrace-living (adj-13).
    assert {(r.id, r.a, r.b) for r in model.relationships} == {
        ("rel-02-kitchen-living", "sp-kitchen", "sp-living"),
        ("rel-13-terrace-living", "sp-terrace", "sp-living"),
    }
    assert [(z.id, z.space_ids) for z in model.zones] == [("z-day", ["sp-kitchen", "sp-living"])]
    assert model.space("sp-terrace").zone_id is None
    assert [c.space_id for c in model.ceilings] == ["sp-kitchen", "sp-living"]
    assert [(s.id, s.material_id, s.thickness_m) for s in model.slabs] == [
        ("slab-terrace-terrace", "m-slab", 0.15),
        ("slab-floor-entry", "m-slab", 0.25),
        ("slab-roof-entry", "m-slab", 0.25),
    ]
    assert not errors(check_model(model))
