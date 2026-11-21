"""Tests for 2D room placement engine (S7-10 through S7-25).

Verifies:
1. S7-10: Rooms placed in x and y with shared wall length >= 0.9 m,
   canonical model assembled and check_model clean.
2. S7-11: Corridor-free circulation with low circulation share.
3. S7-12: Open-plan living/dining/kitchen arrangement with wide opening.
4. S7-13: Solver performance, determinism, and reproducibility budget.
5. S7-14: L-shaped and multi-wing layout with free wing positioning.
6. S7-15: Courtyard geometry with open court enclosed on >= 3 sides.
7. S7-16: Multi-level floor organisation with alternative stair cores.
8. S7-17: Privacy-driven zoning separating family, guest, and service zones.
9. S7-19/S7-20: Terrace geometry and indoor/outdoor relationships.
10. S7-25: Adversarial inputs fail with the right reason.

Each (fixture, strategy) layout is solved once per process (`_solved`) and handed to the
tests as a deep copy, so no test can change another test's layout.
"""

from __future__ import annotations

import copy
import functools
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from house_ai.constants.evaluations import (
    METRIC_ROOM_TERRACE_DOOR_COUNT,
    METRIC_ROOM_TERRACE_LEVEL_DELTA,
    METRIC_TERRACE_GROUND_DELTA,
    VIOLATION_TERRACE_NO_DOOR,
)
from house_ai.constants.placement2d import (
    COURTYARD_SPACE_ID,
    LEVEL_ENTRY,
    LEVEL_UPPER,
    OPEN_PLAN_SHARED_WALL_MIN_M,
    PARAPET_HEIGHT_M,
    PARAPET_THICKNESS_M,
    STAIR_CORE_SPACE_ID_ENTRY,
    STAIR_CORE_SPACE_ID_UPPER,
    TERRACE_DOOR_DEFAULT_WIDTH_M,
    TERRACE_SLAB_THICKNESS_M,
    ZONE_FAMILY,
    ZONE_GUEST,
    ZONE_PUBLIC,
    ZONE_SERVICE,
)
from house_ai.constants.proposals import (
    STAIR_CORE_ENTRY,
)
from house_ai.constants.relations import SHARED_WALL_MIN_M
from house_ai.constants.strategies import (
    STRATEGY_CORRIDOR_FREE,
    STRATEGY_COURTYARD,
    STRATEGY_OPEN_PLAN,
    STRATEGY_TWO_WING,
)
from house_ai.domain.base import EXTERIOR
from house_ai.domain.benchmark import BenchmarkFixture
from house_ai.domain.integrity import check_model, errors
from house_ai.domain.model import (
    HouseModel,
    OpeningKind,
    SlabKind,
    SpaceFunction,
    StairKind,
    WallKind,
)
from house_ai.domain.program import (
    DaylightNeed,
    Priority,
    Privacy,
    ProgramZone,
    SpaceProgram,
    SpaceRelationship,
    SpaceRelationshipKind,
    SpaceRequirement,
    Strength,
)
from house_ai.domain.proposal import (
    ConceptProposal,
    StairCoreProposal,
)
from house_ai.domain.provenance import (
    Actor,
    ActorKind,
    ArtifactKind,
    ArtifactRef,
    Provenance,
)
from house_ai.domain.site import Site
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.evaluators import (
    AdjacencyEvaluator,
    CirculationEvaluator,
    SiteEvaluator,
)
from house_ai.generation import engines
from house_ai.generation.assemble2d import assemble_2d
from house_ai.generation.frame import DesignFrame, Ground, design_frame
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.generation.solver2d import (
    PlacementOptions,
    Solution2D,
    Solve2DFailed,
    solve_2d_placement,
)

FIXTURE_PATH = Path("examples/benchmarks/fixtures/flat-simple.json")
ACTOR = Actor(kind=ActorKind.AGENT, id="gemini")
SEED, BUDGET = 42, 4.0
#: The flat-simple program: one room per Space requirement, ids "sp-" + item id.
FLAT_SIMPLE_ROOMS = {
    "sp-hall",
    "sp-living",
    "sp-kitchen",
    "sp-bed-parents",
    "sp-bed-children",
    "sp-bath",
}
#: The six court sizes the solver may choose (solver2d.compute_candidate_dimensions).
COURT_SIZES_DM = {(30, 30), (30, 40), (40, 30), (40, 40), (30, 50), (50, 30)}


def _load_benchmark_fixture(name: str = "flat-simple") -> BenchmarkFixture:
    path = Path(f"examples/benchmarks/fixtures/{name}.json")
    return BenchmarkFixture.model_validate_json(path.read_text(encoding="utf-8"))


def _opts() -> PlacementOptions:
    return PlacementOptions(seed=SEED, deterministic_time=BUDGET)


def _assemble(sol: Solution2D, site: Site, frame: DesignFrame, program: SpaceProgram):
    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )
    return assemble_2d(
        sol,
        site,
        frame,
        Ground(site, frame),
        program,
        ACTOR,
        site_ref=site_ref,
        program_ref=program_ref,
    )


@dataclass
class Case:
    site: Site
    program: SpaceProgram
    frame: DesignFrame
    sol: Solution2D
    model: HouseModel


@functools.cache
def _solved(fixture: str, strategy: str) -> Case:
    fix = _load_benchmark_fixture(fixture)
    frame = design_frame(fix.site)
    sol = solve_2d_placement(fix.program, fix.site, frame, _opts(), strategy=strategy)
    return Case(fix.site, fix.program, frame, sol, _assemble(sol, fix.site, frame, fix.program))


def _case(fixture: str, strategy: str) -> Case:
    """A private copy of the one solve of (fixture, strategy) with seed 42 and budget 4.0."""
    return copy.deepcopy(_solved(fixture, strategy))


def _door_pairs(model: HouseModel) -> set[frozenset[str]]:
    return {frozenset(o.connects) for o in model.openings if o.is_passable}


def _overlap_dm(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def test_2d_placement_basic_and_check_model_clean():
    """S7-10: Test 2D room placement and verify that the model passes check_model cleanly."""
    case = _case("flat-simple", STRATEGY_CORRIDOR_FREE)
    sol, model, program = case.sol, case.model, case.program
    assert sol.status in ("OPTIMAL", "FEASIBLE")
    rooms = {r.space_id: r for r in sol.rooms}
    assert set(rooms) == FLAT_SIMPLE_ROOMS

    items = program.space_requirements
    targets = {"sp-" + i.id.removeprefix("pi-"): i.target_area_m2 for i in items}
    for r in sol.rooms:
        assert r.width_dm >= 15 and r.depth_dm >= 15, r.space_id
        # Candidate sizes lie between 85 % and 125 % of the target area.
        assert 0.85 * targets[r.space_id] - 1e-9 <= r.area_m2 <= 1.25 * targets[r.space_id] + 1e-9
    for a, b in [(a, b) for a in sol.rooms for b in sol.rooms if a.space_id < b.space_id]:
        assert box(a.u0, a.v0, a.u1, a.v1).intersection(box(b.u0, b.v0, b.u1, b.v1)).area == 0

    # Every reported shared wall is where the two rectangles really meet, over their overlap.
    for sw in sol.shared_walls:
        ra, rb = rooms[sw.room_a], rooms[sw.room_b]
        if sw.orientation == "v":
            assert sw.coord_dm in {ra.u0, ra.u1} and sw.coord_dm in {rb.u0, rb.u1}
            assert sw.length_dm == _overlap_dm(ra.v0, ra.v1, rb.v0, rb.v1)
        else:
            assert sw.coord_dm in {ra.v0, ra.v1} and sw.coord_dm in {rb.v0, rb.v1}
            assert sw.length_dm == _overlap_dm(ra.u0, ra.u1, rb.u0, rb.u1)
        assert sw.length_m >= SHARED_WALL_MIN_M

    assert {s.id for s in model.spaces} == FLAT_SIMPLE_ROOMS
    # The three hard CONNECTED relations of the program are passable openings.
    doors = _door_pairs(model)
    for pair in ({"sp-hall", EXTERIOR}, {"sp-living", "sp-kitchen"}, {"sp-hall", "sp-bath"}):
        assert frozenset(pair) in doors, pair

    model_errors = errors(check_model(model, case.site, program))
    assert not model_errors, f"Unexpected integrity errors: {[e.message for e in model_errors]}"


def test_corridor_free_circulation_pattern():
    """S7-11: Test corridor-free layout with minimal circulation share."""
    case = _case("flat-simple", STRATEGY_CORRIDOR_FREE)
    sol = case.sol
    # No corridor room, and the share is the hall's area over all rooms, below 15 %.
    assert not [r for r in sol.rooms if r.function is SpaceFunction.CORRIDOR]
    total = sum(r.area_m2 for r in sol.rooms)
    hall = next(r for r in sol.rooms if r.space_id == "sp-hall")
    assert sol.circulation_share == pytest.approx(hall.area_m2 / total, abs=1e-12)
    assert sol.circulation_share <= 0.15
    assert len(sol.shared_walls) >= 3

    # The hall is the entry room: it holds the front door and touches a room.
    (entry,) = [r for r in sol.rooms if r.function in (SpaceFunction.ENTRY, SpaceFunction.HALL)]
    assert frozenset({entry.space_id, EXTERIOR}) in _door_pairs(case.model)
    assert any(entry.space_id in (sw.room_a, sw.room_b) for sw in sol.shared_walls)

    assert not errors(check_model(case.model, case.site, case.program))


def test_open_plan_living_arrangement():
    """S7-12: Test open-plan strategy with composite living space and wide opening."""
    case = _case("flat-simple", STRATEGY_OPEN_PLAN)
    sol, model = case.sol, case.model
    assert sol.status in ("OPTIMAL", "FEASIBLE")

    # flat-simple has living and kitchen (no dining): they form one composite space.
    (composite,) = model.composite_spaces
    assert set(composite.space_ids) == {"sp-living", "sp-kitchen"}
    assert composite.boundary.area_m2 == pytest.approx(
        sum(model.space(s).area_m2 for s in composite.space_ids), abs=1e-4
    )
    # The whole shared wall between them is open: one cased opening as long as that wall.
    (cased,) = [op for op in model.openings if op.kind is OpeningKind.OPENING]
    assert set(cased.connects) == {"sp-living", "sp-kitchen"}
    (wall,) = [
        sw for sw in sol.shared_walls if {sw.room_a, sw.room_b} == {"sp-living", "sp-kitchen"}
    ]
    assert cased.width_m == pytest.approx(wall.length_m, abs=1e-6)
    assert cased.width_m >= OPEN_PLAN_SHARED_WALL_MIN_M

    assert not errors(check_model(model, case.site, case.program))


def test_solver_reproducibility_budget():
    """S7-13: Test that solver runs within budget and produces identical results across runs."""
    shared = _case("flat-simple", STRATEGY_CORRIDOR_FREE).sol
    fix = _load_benchmark_fixture()
    fresh = solve_2d_placement(
        fix.program, fix.site, design_frame(fix.site), _opts(), strategy=STRATEGY_CORRIDOR_FREE
    )
    # CP-SAT may overrun its deterministic budget slightly between checks, never by 10 %.
    assert fresh.deterministic_time <= BUDGET * 1.1
    assert fresh.objective == shared.objective
    coords = lambda s: [(r.space_id, r.u0, r.v0, r.u1, r.v1) for r in s.rooms]  # noqa: E731
    assert coords(fresh) == coords(shared)
    walls = lambda s: [(w.room_a, w.room_b, w.coord_dm, w.length_dm) for w in s.shared_walls]  # noqa: E731
    assert walls(fresh) == walls(shared)


def test_two_wing_l_shaped_arrangement_free_positioning():
    """S7-14: Test L-shaped massing with free wing positions on the 2D engine."""
    case = _case("flat-simple", STRATEGY_TWO_WING)
    sol = case.sol
    assert sol.status in ("OPTIMAL", "FEASIBLE")

    # Rooms partitioned into day and night wings
    day = {SpaceFunction.ENTRY, SpaceFunction.LIVING, SpaceFunction.DINING}
    day |= {SpaceFunction.KITCHEN, SpaceFunction.HALL}
    day_ids = {r.space_id for r in sol.rooms if r.function in day}
    night_ids = {r.space_id for r in sol.rooms} - day_ids
    assert day_ids == {"sp-hall", "sp-living", "sp-kitchen"}
    assert night_ids == {"sp-bed-parents", "sp-bed-children", "sp-bath"}

    # Verify junction: at least one shared wall connects day wing to night wing
    assert any({sw.room_a, sw.room_b} & day_ids and {sw.room_a, sw.room_b} & night_ids
               for sw in sol.shared_walls)  # fmt: skip

    # The footprint is one polygon with a re-entrant corner: an L (or more) and not a
    # rectangle, so it covers less than its bounding box and has at least six true corners.
    fp = unary_union([box(r.u0, r.v0, r.u1, r.v1) for r in sol.rooms]).simplify(0)
    assert fp.geom_type == "Polygon"
    assert fp.area == pytest.approx(sum(r.width_dm * r.depth_dm for r in sol.rooms))
    assert fp.area < fp.envelope.area - 1
    assert len(fp.exterior.coords) - 1 >= 6

    assert not errors(check_model(case.model, case.site, case.program))


def test_courtyard_geometry_with_open_court():
    """S7-15: Test courtyard layout with an open court enclosed on >= 3 sides."""
    case = _case("flat-simple", STRATEGY_COURTYARD)
    sol, model = case.sol, case.model
    assert sol.status in ("OPTIMAL", "FEASIBLE")
    assert sol.has_courtyard

    court = next(r for r in sol.rooms if r.space_id == COURTYARD_SPACE_ID)
    assert (court.width_dm, court.depth_dm) in COURT_SIZES_DM

    # Rooms of the house line at least three of the court's four sides.
    sides = set()
    for sw in sol.shared_walls:
        if COURTYARD_SPACE_ID not in (sw.room_a, sw.room_b):
            continue
        assert {sw.room_a, sw.room_b} - {COURTYARD_SPACE_ID} <= FLAT_SIMPLE_ROOMS
        if sw.orientation == "v":
            sides.add({court.u0: "west", court.u1: "east"}[sw.coord_dm])
        else:
            sides.add({court.v0: "south", court.v1: "north"}[sw.coord_dm])
    assert len(sides) >= 3, sides

    # Courtyard is present as a terrace space
    court_space = model.space(COURTYARD_SPACE_ID)
    assert court_space.function is SpaceFunction.TERRACE

    assert not errors(check_model(model, case.site, case.program))


def test_multi_level_alternative_stair_cores():
    """S7-16: Test multi-level layout with alternative stair core locations."""
    fix = _load_benchmark_fixture()
    site = fix.site
    program = fix.program
    frame = design_frame(site)

    prop = ConceptProposal(
        id="prop-multi",
        project_id="proj-demo",
        name="Multi-level with Entry Stair",
        intent="Two-storey layout with day on entry and night on upper",
        stair_cores=[
            StairCoreProposal(
                id="sc-entry",
                position=STAIR_CORE_ENTRY,
                connects_levels=[LEVEL_ENTRY, LEVEL_UPPER],
            )
        ],
    )

    sol = solve_2d_placement(
        program,
        site,
        frame,
        _opts(),
        strategy=STRATEGY_CORRIDOR_FREE,
        proposal=prop,
        multi_level=True,
    )
    assert sol.status in ("OPTIMAL", "FEASIBLE")
    assert sol.has_stairs
    assert len(sol.levels) == 2

    # Stair core rooms on entry and upper level have identical vertical coordinates
    stair_e = next(r for r in sol.rooms if r.space_id == STAIR_CORE_SPACE_ID_ENTRY)
    stair_u = next(r for r in sol.rooms if r.space_id == STAIR_CORE_SPACE_ID_UPPER)
    assert stair_e.u0 == stair_u.u0
    assert stair_e.v0 == stair_u.v0
    assert stair_e.u1 == stair_u.u1
    assert stair_e.v1 == stair_u.v1

    model = _assemble(sol, site, frame, program)

    assert len(model.levels) == 2
    assert len(model.stairs) == 1
    st = model.stairs[0]
    assert st.from_level_id == LEVEL_ENTRY
    assert st.to_level_id == LEVEL_UPPER
    assert st.kind is StairKind.U_SHAPED

    findings = check_model(model, site, program)
    assert not errors(findings)


def _zoned_program() -> SpaceProgram:
    zones = [
        ProgramZone(id=ZONE_PUBLIC, name="Public Zone", privacy=Privacy.PUBLIC),
        ProgramZone(id=ZONE_FAMILY, name="Family Private Zone", privacy=Privacy.PRIVATE),
        ProgramZone(id=ZONE_GUEST, name="Guest Suite Zone", privacy=Privacy.SEMI_PRIVATE),
        ProgramZone(id=ZONE_SERVICE, name="Service Zone", privacy=Privacy.SERVICE),
        ProgramZone(id="z-circulation", name="Circulation Zone", privacy=Privacy.SEMI_PRIVATE),
    ]

    def item(ident, name, function, area, zone, privacy, daylight, priority=Priority.MUST):
        return SpaceRequirement(
            id=ident,
            name=name,
            function=function,
            target_area_m2=area,
            zone_id=zone,
            privacy=privacy,
            daylight=daylight,
            priority=priority,
        )

    F, P, D = SpaceFunction, Privacy, DaylightNeed
    items = [
        item("pi-entry", "Entry", F.ENTRY, 6.0, ZONE_PUBLIC, P.PUBLIC, D.NOT_NEEDED),
        item("pi-hall", "Hall", F.HALL, 6.0, "z-circulation", P.SEMI_PRIVATE, D.NOT_NEEDED),
        item("pi-living", "Living Room", F.LIVING, 24.0, ZONE_PUBLIC, P.PUBLIC, D.REQUIRED),
        item("pi-kitchen", "Kitchen", F.KITCHEN, 12.0, ZONE_PUBLIC, P.PUBLIC, D.REQUIRED),
        item("pi-master", "Master Bedroom", F.BEDROOM, 16.0, ZONE_FAMILY, P.PRIVATE, D.REQUIRED),
        item("pi-bed2", "Child Bedroom", F.BEDROOM, 12.0, ZONE_FAMILY, P.PRIVATE, D.REQUIRED),
        item(
            "pi-guest",
            "Guest Bedroom",
            F.BEDROOM,
            12.0,
            ZONE_GUEST,
            P.SEMI_PRIVATE,
            D.REQUIRED,
            Priority.SHOULD,
        ),
        item(
            "pi-laundry",
            "Laundry",
            F.LAUNDRY,
            6.0,
            ZONE_SERVICE,
            P.SERVICE,
            D.NOT_NEEDED,
            Priority.SHOULD,
        ),
    ]
    return SpaceProgram(
        id="prog-zoned",
        project_id="proj-demo",
        zones=zones,
        space_requirements=items,
        space_relationships=[],
        provenance=Provenance(created_at=datetime.now(UTC), created_by=ACTOR, method="test"),
    )


@functools.cache
def _zoned_solved() -> Case:
    site = _load_benchmark_fixture().site
    frame = design_frame(site)
    program = _zoned_program()
    sol = solve_2d_placement(program, site, frame, _opts(), strategy=STRATEGY_CORRIDOR_FREE)
    return Case(site, program, frame, sol, _assemble(sol, site, frame, program))


def test_privacy_driven_zoning():
    """S7-17: Test privacy-driven zoning separating family, guest, and service zones."""
    case = copy.deepcopy(_zoned_solved())
    sol, model = case.sol, case.model
    assert sol.status in ("OPTIMAL", "FEASIBLE")
    assert {s.id for s in model.spaces} == {
        "sp-entry",
        "sp-hall",
        "sp-living",
        "sp-kitchen",
        "sp-master",
        "sp-bed2",
        "sp-guest",
        "sp-laundry",
    }

    # Ground truth from solver2d.is_privacy_separated: a family bedroom never opens straight
    # into a public-zone room (entry, living, kitchen) or the guest bedroom, touching or not.
    family = {"sp-master", "sp-bed2"}
    barred = {"sp-entry", "sp-living", "sp-kitchen", "sp-guest"}
    doors = _door_pairs(model)
    assert not [p for p in doors if p & family and p & barred], doors
    for sw in sol.shared_walls:
        if {sw.room_a, sw.room_b} & family and {sw.room_a, sw.room_b} & barred:
            assert not sw.door_candidate

    assert not errors(check_model(model, case.site, case.program))


#: ISS-52 shows on the layout CP-SAT returns for this model and seed on macOS arm64. Linux
#: x86-64 gets another layout from the same model and seed (ISS-21) whose routes happen to
#: stay out of the family rooms (CI run 44936702603), so there the test runs unmarked: it
#: passes today, and fails with the gap's own assertion if a layout there ever shows it.
ISS_52_SHOWS_HERE = (platform.system(), platform.machine()) == ("Darwin", "arm64")


@pytest.mark.xfail(
    ISS_52_SHOWS_HERE,
    strict=True,
    reason="product gap (ISS-52): S7-17 zoning only bars direct doors; seed 42 reaches the hall "
    "through laundry, the child bedroom and the master bedroom (guest_private_crossings 2)",
)
def test_privacy_zoning_routes_avoid_family_rooms():
    """Every route from the front door to a public or semi-private room avoids family rooms."""
    case = copy.deepcopy(_zoned_solved())
    ctx = EvaluationContext(case.model, case.site, case.program, None)
    circulation = CirculationEvaluator().evaluate(ctx)
    crossings = next(m for m in circulation.metrics if m.metric == "guest_private_crossings")
    assert crossings.value == 0
    assert "private_space_crossed" not in {v.code for v in circulation.violations}


def test_generator_candidates_supports_2d_strategies(monkeypatch):
    """Test CpSatPlanGenerator candidate generation with 2D strategies.

    The generator must hand the 2D solver exactly the inputs the shared layouts were solved
    with; the solver is deterministic for them (test_solver_reproducibility_budget), so the
    stub returns those solves instead of solving each strategy a second time.
    """
    fix = _load_benchmark_fixture()
    calls = []

    def solve(program, site, frame, opts, strategy, proposal=None, multi_level=False):
        assert program == fix.program and site == fix.site
        assert frame == design_frame(fix.site)
        assert opts == _opts()
        assert proposal is None and multi_level is False
        calls.append(strategy)
        return _case("flat-simple", strategy).sol

    monkeypatch.setattr(engines, "solve_2d_placement", solve)
    req = GenerationRequest(
        site=fix.site,
        program=fix.program,
        constraints=None,
        strategies=[STRATEGY_CORRIDOR_FREE, STRATEGY_OPEN_PLAN],
        site_ref=ArtifactRef(kind=ArtifactKind.SITE, id=fix.site.id, version=1, sha256="0" * 64),
        program_ref=ArtifactRef(
            kind=ArtifactKind.SPACE_PROGRAM, id=fix.program.id, version=1, sha256="0" * 64
        ),
        created_at=datetime.now(UTC),
        seed=SEED,
        deterministic_time=BUDGET,
    )
    cands = CpSatPlanGenerator().candidates(req)
    assert calls == [STRATEGY_CORRIDOR_FREE, STRATEGY_OPEN_PLAN]
    assert [c.strategy for c in cands] == calls
    for c in cands:
        assert c.status == "generated"
        assert c.valid
        assert c.plan is not None
        assert not errors(c.findings)
        shared = _case("flat-simple", c.strategy)
        assert c.plan.generation.solver_status == shared.sol.status
        assert {s.id for s in c.plan.model.spaces} == FLAT_SIMPLE_ROOMS
        assert _door_pairs(c.plan.model) == _door_pairs(shared.model)


def test_terrace_geometry_and_placement_s7_19():
    """S7-19: Test terrace geometry and placement with TERRACE slabs and PARAPET walls."""
    case = _case("large-terrace", STRATEGY_CORRIDOR_FREE)
    model = case.model
    assert case.sol.status in ("OPTIMAL", "FEASIBLE")
    assert not errors(check_model(model, case.site, case.program))

    # The program's one terrace has one TERRACE slab under it.
    (terrace,) = [s for s in model.spaces if s.function is SpaceFunction.TERRACE]
    assert terrace.id == "sp-terrace"
    (t_slab,) = [sl for sl in model.slabs if sl.kind is SlabKind.TERRACE]
    assert t_slab.thickness_m == TERRACE_SLAB_THICKNESS_M
    t_poly = terrace.boundary.to_shapely()
    assert t_slab.boundary.to_shapely().symmetric_difference(t_poly).area < 1e-6

    # Parapet walls run along the terrace outline only.
    outline = t_poly.exterior.buffer(0.01)
    parapets = [w for w in model.walls if w.kind is WallKind.PARAPET]
    assert parapets
    for pw in parapets:
        assert pw.height_m == PARAPET_HEIGHT_M
        assert pw.thickness_m == PARAPET_THICKNESS_M
        assert outline.covers(LineString([pw.start, pw.end])), pw.id

    # The hard living-terrace connection is a terrace door; all terrace doors are full width.
    terrace_doors = [
        op for op in model.openings if op.kind is OpeningKind.DOOR and "sp-terrace" in op.connects
    ]
    assert frozenset({"sp-living", "sp-terrace"}) in {frozenset(d.connects) for d in terrace_doors}
    for td in terrace_doors:
        assert td.width_m == TERRACE_DOOR_DEFAULT_WIDTH_M


def test_indoor_outdoor_relationships_evaluated_s7_20():
    """S7-20: Test indoor/outdoor relationships evaluated with door connections and level deltas."""
    case = _case("large-terrace", STRATEGY_CORRIDOR_FREE)
    model, site = case.model, case.site
    ctx = EvaluationContext(model=model, site=site, program=case.program, constraints=None)

    se = SiteEvaluator().evaluate(ctx)
    by_name: dict[str, list] = {}
    for m in se.metrics:
        by_name.setdefault(m.metric, []).append(m)

    terrace = model.space("sp-terrace")
    t_doors = [o for o in model.openings if o.is_passable and terrace.id in o.connects]
    (door_count,) = by_name[METRIC_ROOM_TERRACE_DOOR_COUNT]
    assert door_count.value == len(t_doors) >= 1

    # One level-delta claim per terrace door, each 0: the 2D layout has a single level.
    deltas = by_name[METRIC_ROOM_TERRACE_LEVEL_DELTA]
    assert len(deltas) == len(t_doors)
    assert all(m.value == 0.0 for m in deltas)

    # The analytical plane of large-terrace is z = 12 - 0.4 y, so the terrace floor stands
    # its level elevation minus that plane at the mean of its boundary vertices.
    pts = terrace.boundary.outer
    cy = sum(p[1] for p in pts) / len(pts)
    (ground_delta,) = by_name[METRIC_TERRACE_GROUND_DELTA]
    expected = model.level(terrace.level_id).elevation_m - (12.0 - 0.4 * cy)
    assert ground_delta.value == pytest.approx(expected, abs=1e-3)

    # No unreached terrace violation
    assert not any(v.code == VIOLATION_TERRACE_NO_DOOR for v in se.violations)

    # Evaluate AdjacencyEvaluator: hard connected adjacency adj-terrace-living is satisfied
    ae = AdjacencyEvaluator().evaluate(ctx)
    adj_claims = [m for m in ae.metrics if "adj-terrace-living" in m.subject_ids]
    assert adj_claims
    assert all(m.value is True for m in adj_claims)


def test_adversarial_generation_s7_25():
    """S7-25: Adversarial generation tests for contradictory, oversized, and pathological inputs.

    Each case must fail for its own reason: a proven-infeasible CP-SAT model or a room no
    candidate size can hold, never a timeout or an unrelated error.
    """
    fix = _load_benchmark_fixture("large-terrace")
    site = fix.site
    frame = design_frame(site)
    infeasible = r"^CP-SAT found no contained connected layout \(INFEASIBLE\)$"

    def generated(program):
        req = GenerationRequest(
            site=site,
            program=program,
            constraints=None,
            site_ref=None,
            program_ref=None,
            created_at=fix.program.provenance.created_at,
            strategies=[STRATEGY_CORRIDOR_FREE],
        )
        (cand,) = CpSatPlanGenerator().candidates(req)
        assert cand.status == "infeasible" and cand.plan is None
        return cand.reason

    # 1. Contradictory hard requirements: room A and room B simultaneously
    # MUST be adjacent AND separated
    contra_adj = [
        SpaceRelationship(
            id="adj-contra-1",
            a="pi-living",
            b="pi-kitchen",
            kind=SpaceRelationshipKind.ADJACENT,
            strength=Strength.HARD,
            rationale="adversarial test: hard adjacent",
        ),
        SpaceRelationship(
            id="adj-contra-2",
            a="pi-living",
            b="pi-kitchen",
            kind=SpaceRelationshipKind.SEPARATED,
            strength=Strength.HARD,
            rationale="adversarial test: hard separated",
        ),
    ]
    contra_program = fix.program.model_copy(update={"space_relationships": contra_adj})
    with pytest.raises(Solve2DFailed, match=infeasible):
        solve_2d_placement(contra_program, site, frame, _opts(), strategy=STRATEGY_CORRIDOR_FREE)
    # Via CpSatPlanGenerator: candidate is marked infeasible without producing
    # an invalid model or crashing
    assert generated(contra_program) == (
        "2D placement infeasible: CP-SAT found no contained connected layout (INFEASIBLE)"
    )

    # 2. Oversized program: six times every target. Each room alone fits the 28 m x 28 m
    # (784 m2) envelope, but the smallest sizes (85 % of 6 x 180 m2 = 918 m2) cannot all.
    width = fix.site.buildable_envelope.polygon.to_shapely().bounds
    assert (width[2] - width[0]) * (width[3] - width[1]) == pytest.approx(784.0)
    assert 0.85 * 6 * sum(i.target_area_m2 for i in fix.program.space_requirements) > 784.0
    oversized_items = [
        item.model_copy(update={"target_area_m2": item.target_area_m2 * 6.0})
        for item in fix.program.space_requirements
    ]
    oversized_program = fix.program.model_copy(update={"space_requirements": oversized_items})
    with pytest.raises(Solve2DFailed, match=infeasible):
        solve_2d_placement(
            oversized_program, site, frame, _opts(), strategy=STRATEGY_CORRIDOR_FREE
        )
    assert generated(oversized_program).endswith("(INFEASIBLE)")

    # 3. A room larger than the envelope: twenty times the terrace (1200 m2) has no size.
    huge_items = [
        item.model_copy(update={"target_area_m2": item.target_area_m2 * 20.0, "min_area_m2": 150.0})
        for item in fix.program.space_requirements
    ]
    huge_program = fix.program.model_copy(update={"space_requirements": huge_items})
    no_size = r"^no dimensions for sp-terrace within envelope and hard bounds$"
    with pytest.raises(Solve2DFailed, match=no_size):
        solve_2d_placement(huge_program, site, frame, _opts(), strategy=STRATEGY_CORRIDOR_FREE)
    assert generated(huge_program) == (
        "2D placement infeasible: no dimensions for sp-terrace within envelope and hard bounds"
    )

    # 4. Impossible dimension bounds: room minimum width exceeds envelope width (80 m > 28 m)
    impossible_item = SpaceRequirement(
        id="pi-gigantic",
        name="Gigantic Hall",
        function=SpaceFunction.LIVING,
        target_area_m2=500.0,
        min_width_m=80.0,
        priority=Priority.MUST,
        privacy=Privacy.PUBLIC,
    )
    impossible_program = fix.program.model_copy(update={"space_requirements": [impossible_item]})
    with pytest.raises(
        Solve2DFailed, match=r"^no dimensions for sp-gigantic within envelope and hard bounds$"
    ):
        solve_2d_placement(
            impossible_program, site, frame, _opts(), strategy=STRATEGY_CORRIDOR_FREE
        )
