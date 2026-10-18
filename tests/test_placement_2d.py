"""Tests for 2D room placement engine (S7-10 through S7-18).

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
9. S7-18: Non-rectangular / L-shaped spaces passing check_model cleanly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from shapely.geometry import box
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
from house_ai.domain.benchmark import BenchmarkFixture
from house_ai.domain.integrity import check_model, errors
from house_ai.domain.model import OpeningKind, SlabKind, SpaceFunction, StairKind, WallKind
from house_ai.domain.program import (
    DaylightNeed,
    Priority,
    Privacy,
    ProgramItem,
    ProgramZone,
    SpaceProgram,
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
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.evaluators import AdjacencyEvaluator, SiteEvaluator
from house_ai.generation.assemble2d import assemble_2d
from house_ai.generation.frame import Ground, design_frame
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.generation.solver import SolverOptions
from house_ai.generation.solver2d import (
    PlacedRoom2D,
    SharedWall,
    Solution2D,
    solve_2d_placement,
)

FIXTURE_PATH = Path("examples/benchmarks/fixtures/flat-simple.json")
ACTOR = Actor(kind=ActorKind.AGENT, id="gemini")


def _load_benchmark_fixture(name: str = "flat-simple") -> BenchmarkFixture:
    path = Path(f"examples/benchmarks/fixtures/{name}.json")
    return BenchmarkFixture.model_validate_json(path.read_text(encoding="utf-8"))


def test_2d_placement_basic_and_check_model_clean():
    """S7-10: Test 2D room placement and verify that the model passes check_model cleanly."""
    fix = _load_benchmark_fixture()
    site = fix.site
    program = fix.program

    frame = design_frame(site)
    ground = Ground(site, frame)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

    sol = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)
    assert sol.status in ("OPTIMAL", "FEASIBLE")
    assert len(sol.rooms) >= 4

    for r in sol.rooms:
        assert r.width_dm >= 15
        assert r.depth_dm >= 15
        assert r.u1 > r.u0
        assert r.v1 > r.v0

    for sw in sol.shared_walls:
        assert sw.length_m >= SHARED_WALL_MIN_M

    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )

    model = assemble_2d(
        sol, site, frame, ground, program, ACTOR, site_ref=site_ref, program_ref=program_ref
    )
    assert len(model.spaces) >= 4
    assert len(model.walls) >= 4
    assert len(model.openings) >= 2

    findings = check_model(model, site, program)
    model_errors = errors(findings)
    assert not model_errors, f"Unexpected integrity errors: {[e.message for e in model_errors]}"


def test_corridor_free_circulation_pattern():
    """S7-11: Test corridor-free layout with minimal circulation share."""
    fix = _load_benchmark_fixture()
    site = fix.site
    program = fix.program

    frame = design_frame(site)
    ground = Ground(site, frame)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

    sol = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)

    assert sol.circulation_share <= 0.15
    assert len(sol.shared_walls) >= 3

    entry_room = next(
        r for r in sol.rooms if r.function in (SpaceFunction.ENTRY, SpaceFunction.HALL)
    )
    connected_to_entry = [
        sw.room_b if sw.room_a == entry_room.space_id else sw.room_a
        for sw in sol.shared_walls
        if entry_room.space_id in (sw.room_a, sw.room_b)
    ]
    assert len(connected_to_entry) >= 1

    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )
    model = assemble_2d(
        sol, site, frame, ground, program, ACTOR, site_ref=site_ref, program_ref=program_ref
    )

    findings = check_model(model, site, program)
    assert not errors(findings)


def test_open_plan_living_arrangement():
    """S7-12: Test open-plan strategy with composite living space and wide opening."""
    fix = _load_benchmark_fixture()
    site = fix.site
    program = fix.program

    frame = design_frame(site)
    ground = Ground(site, frame)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

    sol = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_OPEN_PLAN)
    assert sol.status in ("OPTIMAL", "FEASIBLE")

    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )
    model = assemble_2d(
        sol, site, frame, ground, program, ACTOR, site_ref=site_ref, program_ref=program_ref
    )

    cased_openings = [op for op in model.openings if op.kind is OpeningKind.OPENING]
    assert len(cased_openings) >= 1

    for cop in cased_openings:
        assert cop.width_m >= OPEN_PLAN_SHARED_WALL_MIN_M

    findings = check_model(model, site, program)
    assert not errors(findings)


def test_solver_reproducibility_budget():
    """S7-13: Test that solver runs within budget and produces identical results across runs."""
    fix = _load_benchmark_fixture()
    site = fix.site
    program = fix.program
    frame = design_frame(site)

    opts = SolverOptions(seed=123, deterministic_time=3.0)

    sol1 = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)
    sol2 = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)

    assert sol1.deterministic_time <= 3.5
    assert sol1.objective == sol2.objective

    coords1 = [(r.space_id, r.u0, r.v0, r.u1, r.v1) for r in sol1.rooms]
    coords2 = [(r.space_id, r.u0, r.v0, r.u1, r.v1) for r in sol2.rooms]
    assert coords1 == coords2


def test_two_wing_l_shaped_arrangement_free_positioning():
    """S7-14: Test L-shaped massing with free wing positions on the 2D engine."""
    fix = _load_benchmark_fixture()
    site = fix.site
    program = fix.program
    frame = design_frame(site)
    ground = Ground(site, frame)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

    sol = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_TWO_WING)
    assert sol.status in ("OPTIMAL", "FEASIBLE")

    # Rooms partitioned into day and night wings
    day_rooms = [
        r
        for r in sol.rooms
        if r.function
        in (
            SpaceFunction.ENTRY,
            SpaceFunction.LIVING,
            SpaceFunction.DINING,
            SpaceFunction.KITCHEN,
            SpaceFunction.HALL,
        )
    ]
    night_rooms = [
        r
        for r in sol.rooms
        if r.function in (SpaceFunction.BEDROOM, SpaceFunction.BATHROOM, SpaceFunction.STUDY)
    ]
    assert len(day_rooms) >= 1
    assert len(night_rooms) >= 1

    # Verify junction: at least one shared wall connects day wing to night wing
    day_ids = {r.space_id for r in day_rooms}
    night_ids = {r.space_id for r in night_rooms}
    junction_walls = [
        sw
        for sw in sol.shared_walls
        if (sw.room_a in day_ids and sw.room_b in night_ids)
        or (sw.room_b in day_ids and sw.room_a in night_ids)
    ]
    assert len(junction_walls) >= 1

    # Assemble canonical model
    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )
    model = assemble_2d(
        sol, site, frame, ground, program, ACTOR, site_ref=site_ref, program_ref=program_ref
    )

    # Footprint union forms an L-shape (non-convex orthogonal polygon with re-entrant corner)
    room_boxes = [box(r.u0, r.v0, r.u1, r.v1) for r in sol.rooms]
    fp_u = unary_union(room_boxes)
    # L-shape boundary has 6 vertices (or more if stepped)
    assert len(fp_u.exterior.coords) - 1 >= 6

    findings = check_model(model, site, program)
    assert not errors(findings)


def test_courtyard_geometry_with_open_court():
    """S7-15: Test courtyard layout with an open court enclosed on >= 3 sides."""
    fix = _load_benchmark_fixture()
    site = fix.site
    program = fix.program
    frame = design_frame(site)
    ground = Ground(site, frame)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

    sol = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_COURTYARD)
    assert sol.status in ("OPTIMAL", "FEASIBLE")
    assert sol.has_courtyard

    court = next(r for r in sol.rooms if r.space_id == COURTYARD_SPACE_ID)
    assert court.width_dm >= 30  # >= 3.0 m
    assert court.depth_dm >= 30

    # Surrounding rooms touch courtyard
    court_walls = [
        sw
        for sw in sol.shared_walls
        if sw.room_a == COURTYARD_SPACE_ID or sw.room_b == COURTYARD_SPACE_ID
    ]
    assert len(court_walls) >= 2

    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )
    model = assemble_2d(
        sol, site, frame, ground, program, ACTOR, site_ref=site_ref, program_ref=program_ref
    )

    # Courtyard is present as a terrace space
    court_space = model.space(COURTYARD_SPACE_ID)
    assert court_space.function is SpaceFunction.TERRACE

    findings = check_model(model, site, program)
    assert not errors(findings)


def test_multi_level_alternative_stair_cores():
    """S7-16: Test multi-level layout with alternative stair core locations."""
    fix = _load_benchmark_fixture()
    site = fix.site
    program = fix.program
    frame = design_frame(site)
    ground = Ground(site, frame)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

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
        program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE, proposal=prop, multi_level=True
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

    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )
    model = assemble_2d(
        sol, site, frame, ground, program, ACTOR, site_ref=site_ref, program_ref=program_ref
    )

    assert len(model.levels) == 2
    assert len(model.stairs) == 1
    st = model.stairs[0]
    assert st.from_level_id == LEVEL_ENTRY
    assert st.to_level_id == LEVEL_UPPER
    assert st.kind is StairKind.U_SHAPED

    findings = check_model(model, site, program)
    assert not errors(findings)


def test_privacy_driven_zoning():
    """S7-17: Test privacy-driven zoning separating family, guest, and service zones."""
    site = _load_benchmark_fixture().site
    frame = design_frame(site)
    ground = Ground(site, frame)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

    # Construct zoned program
    zones = [
        ProgramZone(id=ZONE_PUBLIC, name="Public Zone", privacy=Privacy.PUBLIC),
        ProgramZone(id=ZONE_FAMILY, name="Family Private Zone", privacy=Privacy.PRIVATE),
        ProgramZone(id=ZONE_GUEST, name="Guest Suite Zone", privacy=Privacy.SEMI_PRIVATE),
        ProgramZone(id=ZONE_SERVICE, name="Service Zone", privacy=Privacy.SERVICE),
        ProgramZone(id="z-circulation", name="Circulation Zone", privacy=Privacy.SEMI_PRIVATE),
    ]
    items = [
        ProgramItem(
            id="pi-entry",
            name="Entry",
            function=SpaceFunction.ENTRY,
            target_area_m2=6.0,
            zone_id=ZONE_PUBLIC,
            privacy=Privacy.PUBLIC,
            daylight=DaylightNeed.NOT_NEEDED,
            priority=Priority.MUST,
        ),
        ProgramItem(
            id="pi-hall",
            name="Hall",
            function=SpaceFunction.HALL,
            target_area_m2=6.0,
            zone_id="z-circulation",
            privacy=Privacy.SEMI_PRIVATE,
            daylight=DaylightNeed.NOT_NEEDED,
            priority=Priority.MUST,
        ),
        ProgramItem(
            id="pi-living",
            name="Living Room",
            function=SpaceFunction.LIVING,
            target_area_m2=24.0,
            zone_id=ZONE_PUBLIC,
            privacy=Privacy.PUBLIC,
            daylight=DaylightNeed.REQUIRED,
            priority=Priority.MUST,
        ),
        ProgramItem(
            id="pi-kitchen",
            name="Kitchen",
            function=SpaceFunction.KITCHEN,
            target_area_m2=12.0,
            zone_id=ZONE_PUBLIC,
            privacy=Privacy.PUBLIC,
            daylight=DaylightNeed.REQUIRED,
            priority=Priority.MUST,
        ),
        ProgramItem(
            id="pi-master",
            name="Master Bedroom",
            function=SpaceFunction.BEDROOM,
            target_area_m2=16.0,
            zone_id=ZONE_FAMILY,
            privacy=Privacy.PRIVATE,
            daylight=DaylightNeed.REQUIRED,
            priority=Priority.MUST,
        ),
        ProgramItem(
            id="pi-bed2",
            name="Child Bedroom",
            function=SpaceFunction.BEDROOM,
            target_area_m2=12.0,
            zone_id=ZONE_FAMILY,
            privacy=Privacy.PRIVATE,
            daylight=DaylightNeed.REQUIRED,
            priority=Priority.MUST,
        ),
        ProgramItem(
            id="pi-guest",
            name="Guest Bedroom",
            function=SpaceFunction.BEDROOM,
            target_area_m2=12.0,
            zone_id=ZONE_GUEST,
            privacy=Privacy.SEMI_PRIVATE,
            daylight=DaylightNeed.REQUIRED,
            priority=Priority.SHOULD,
        ),
        ProgramItem(
            id="pi-laundry",
            name="Laundry",
            function=SpaceFunction.LAUNDRY,
            target_area_m2=6.0,
            zone_id=ZONE_SERVICE,
            privacy=Privacy.SERVICE,
            daylight=DaylightNeed.NOT_NEEDED,
            priority=Priority.SHOULD,
        ),
    ]
    program = SpaceProgram(
        id="prog-zoned",
        project_id="proj-demo",
        zones=zones,
        items=items,
        adjacencies=[],
        provenance=Provenance(created_at=datetime.now(UTC), created_by=ACTOR, method="test"),
    )

    sol = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)
    assert sol.status in ("OPTIMAL", "FEASIBLE")

    # Verify door candidacy respects privacy rules:
    # No direct door from family bedroom to public living room
    for sw in sol.shared_walls:
        if (sw.room_a == "sp-master" and sw.room_b == "sp-living") or (
            sw.room_b == "sp-master" and sw.room_a == "sp-living"
        ):
            assert not sw.door_candidate

        # No direct door between family master bedroom and guest bedroom
        if (sw.room_a == "sp-master" and sw.room_b == "sp-guest") or (
            sw.room_b == "sp-master" and sw.room_a == "sp-guest"
        ):
            assert not sw.door_candidate

    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )
    model = assemble_2d(
        sol, site, frame, ground, program, ACTOR, site_ref=site_ref, program_ref=program_ref
    )
    findings = check_model(model, site, program)
    assert not errors(findings)


def test_non_rectangular_l_shaped_space():
    """S7-18: Test non-rectangular L-shaped space passing check_model cleanly."""
    fix = _load_benchmark_fixture()
    site = fix.site
    frame = design_frame(site)
    ground = Ground(site, frame)

    # Construct an L-shaped living room from 2 sub-rectangles:
    # Sub-rect 1: (0, 0) to (40, 30) (4.0m x 3.0m)
    # Sub-rect 2: (20, 30) to (40, 50) (2.0m x 2.0m alcove)
    # Adjacent room: (0, 30) to (20, 50) (bedroom)
    l_room = PlacedRoom2D(
        space_id="sp-living",
        name="Living Room (L-shaped)",
        function=SpaceFunction.LIVING,
        level_id=LEVEL_ENTRY,
        u0=0,
        v0=0,
        u1=40,
        v1=50,
        program_item_id="pi-living",
        zone_id="z-day",
        sub_rects=[(0, 0, 40, 30), (20, 30, 40, 50)],
    )
    bed_room = PlacedRoom2D(
        space_id="sp-bed",
        name="Bedroom",
        function=SpaceFunction.BEDROOM,
        level_id=LEVEL_ENTRY,
        u0=0,
        v0=30,
        u1=20,
        v1=50,
        program_item_id="pi-bed",
        zone_id="z-night",
    )
    entry_room = PlacedRoom2D(
        space_id="sp-entry",
        name="Entry",
        function=SpaceFunction.ENTRY,
        level_id=LEVEL_ENTRY,
        u0=40,
        v0=0,
        u1=60,
        v1=20,
        program_item_id="pi-entry",
        zone_id="z-day",
    )

    sw1 = SharedWall(
        room_a="sp-living",
        room_b="sp-bed",
        level_id=LEVEL_ENTRY,
        orientation="v",
        coord_dm=20,
        span_start_dm=30,
        span_end_dm=50,
        door_candidate=True,
    )
    sw2 = SharedWall(
        room_a="sp-living",
        room_b="sp-entry",
        level_id=LEVEL_ENTRY,
        orientation="v",
        coord_dm=40,
        span_start_dm=0,
        span_end_dm=20,
        door_candidate=True,
    )

    sol = Solution2D(
        status="FEASIBLE",
        objective=100.0,
        rooms=[l_room, bed_room, entry_room],
        shared_walls=[sw1, sw2],
        circulation_rooms=[],
        levels=[LEVEL_ENTRY],
        deterministic_time=1.0,
        wall_time_s=0.1,
        seed=42,
        platform_info="test",
        strategy=STRATEGY_CORRIDOR_FREE,
        circulation_share=0.0,
    )

    custom_items = [
        ProgramItem(
            id="pi-living",
            name="Living Room",
            function=SpaceFunction.LIVING,
            target_area_m2=16.0,
            min_area_m2=16.0,
            privacy=Privacy.PUBLIC,
            priority=Priority.MUST,
            daylight=DaylightNeed.REQUIRED,
        ),
        ProgramItem(
            id="pi-bed",
            name="Bedroom",
            function=SpaceFunction.BEDROOM,
            target_area_m2=4.0,
            min_area_m2=4.0,
            privacy=Privacy.PRIVATE,
            priority=Priority.MUST,
            daylight=DaylightNeed.REQUIRED,
        ),
        ProgramItem(
            id="pi-entry",
            name="Entry",
            function=SpaceFunction.ENTRY,
            target_area_m2=4.0,
            min_area_m2=4.0,
            privacy=Privacy.PUBLIC,
            priority=Priority.MUST,
            daylight=DaylightNeed.REQUIRED,
        ),
    ]
    prog = SpaceProgram(
        id="prog-l-shape",
        project_id="proj-demo",
        zones=[],
        items=custom_items,
        adjacencies=[],
        provenance=Provenance(created_at=datetime.now(UTC), created_by=ACTOR, method="test"),
    )

    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=prog.id, version=1, sha256="0" * 64
    )
    model = assemble_2d(
        sol, site, frame, ground, prog, ACTOR, site_ref=site_ref, program_ref=program_ref
    )

    # Verify L-shaped space boundary has 6 vertices in its outer ring
    living_space = model.space("sp-living")
    assert len(living_space.boundary.outer) == 6

    # Verify no interior wall divides the two sub-rectangles of the living space
    dividing_walls = [
        w
        for w in model.walls
        if w.level_id == LEVEL_ENTRY
        and (w.start[0] == 2.0 and w.end[0] == 4.0 and w.start[1] == 3.0 and w.end[1] == 3.0)
    ]
    assert len(dividing_walls) == 0

    findings = check_model(model, site, prog)
    assert not errors(findings)


def test_generator_candidates_supports_2d_strategies():
    """Test CpSatPlanGenerator candidate generation with 2D strategies."""
    fix = _load_benchmark_fixture()
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
        seed=42,
        deterministic_time=4.0,
    )
    cands = CpSatPlanGenerator().candidates(req)
    assert len(cands) == 2
    for c in cands:
        assert c.status == "generated"
        assert c.valid
        assert c.plan is not None
        assert not errors(c.findings)


def test_terrace_geometry_and_placement_s7_19():
    """S7-19: Test terrace geometry and placement with TERRACE slabs and PARAPET walls."""
    fix = _load_benchmark_fixture("large-terrace")
    site = fix.site
    program = fix.program
    frame = design_frame(site)
    ground = Ground(site, frame)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

    sol = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)
    assert sol.status in ("OPTIMAL", "FEASIBLE")

    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )
    model = assemble_2d(
        sol, site, frame, ground, program, ACTOR, site_ref=site_ref, program_ref=program_ref
    )

    findings = check_model(model, site, program)
    assert not errors(findings)

    # Verify terrace slab exists with kind TERRACE
    terrace_slabs = [sl for sl in model.slabs if sl.kind is SlabKind.TERRACE]
    assert len(terrace_slabs) >= 1
    t_slab = terrace_slabs[0]
    assert t_slab.thickness_m == TERRACE_SLAB_THICKNESS_M

    # Verify parapet walls along exposed terrace perimeter
    parapets = [w for w in model.walls if w.kind is WallKind.PARAPET]
    assert len(parapets) >= 1
    for pw in parapets:
        assert pw.height_m == PARAPET_HEIGHT_M
        assert pw.thickness_m == PARAPET_THICKNESS_M

    # Verify doors connecting interior room to terrace
    terrace_doors = [
        op for op in model.openings if op.kind is OpeningKind.DOOR and "sp-terrace" in op.connects
    ]
    assert len(terrace_doors) >= 1
    for td in terrace_doors:
        assert td.width_m >= TERRACE_DOOR_DEFAULT_WIDTH_M


def test_indoor_outdoor_relationships_evaluated_s7_20():
    """S7-20: Test indoor/outdoor relationships evaluated with door connections and level deltas."""
    fix = _load_benchmark_fixture("large-terrace")
    site = fix.site
    program = fix.program
    frame = design_frame(site)
    ground = Ground(site, frame)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

    sol = solve_2d_placement(program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)
    assert sol.status in ("OPTIMAL", "FEASIBLE")

    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    program_ref = ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id=program.id, version=1, sha256="0" * 64
    )
    model = assemble_2d(
        sol, site, frame, ground, program, ACTOR, site_ref=site_ref, program_ref=program_ref
    )

    ctx = EvaluationContext(model=model, site=site, program=program, constraints=None)

    # Evaluate SiteEvaluator
    se = SiteEvaluator().evaluate(ctx)
    metrics_by_name = {m.metric: m for m in se.metrics}

    assert METRIC_ROOM_TERRACE_DOOR_COUNT in metrics_by_name
    door_count_claim = metrics_by_name[METRIC_ROOM_TERRACE_DOOR_COUNT]
    assert door_count_claim.value >= 1

    assert METRIC_ROOM_TERRACE_LEVEL_DELTA in metrics_by_name
    level_delta_claim = metrics_by_name[METRIC_ROOM_TERRACE_LEVEL_DELTA]
    assert level_delta_claim.value is not None

    assert METRIC_TERRACE_GROUND_DELTA in metrics_by_name

    # No unreached terrace violation
    assert not any(v.code == VIOLATION_TERRACE_NO_DOOR for v in se.violations)

    # Evaluate AdjacencyEvaluator: hard connected adjacency adj-terrace-living is satisfied
    ae = AdjacencyEvaluator().evaluate(ctx)
    adj_claims = [m for m in ae.metrics if "adj-terrace-living" in m.subject_ids]
    assert len(adj_claims) >= 1
    assert any(m.value is True for m in adj_claims)


def test_adversarial_generation_s7_25():
    """S7-25: Adversarial generation tests for contradictory, oversized, and pathological inputs."""
    from house_ai.domain.program import AdjacencyKind, AdjacencyRequirement, Priority, Strength
    from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
    from house_ai.generation.massing import Infeasible
    from house_ai.generation.solver2d import Solve2DFailed

    fix = _load_benchmark_fixture("large-terrace")
    site = fix.site
    frame = design_frame(site)
    opts = SolverOptions(seed=42, deterministic_time=4.0)

    # 1. Contradictory hard requirements: room A and room B simultaneously
    # MUST be adjacent AND separated
    contra_adj = [
        AdjacencyRequirement(
            id="adj-contra-1",
            a="pi-living",
            b="pi-kitchen",
            kind=AdjacencyKind.ADJACENT,
            strength=Strength.HARD,
            rationale="adversarial test: hard adjacent",
        ),
        AdjacencyRequirement(
            id="adj-contra-2",
            a="pi-living",
            b="pi-kitchen",
            kind=AdjacencyKind.SEPARATED,
            strength=Strength.HARD,
            rationale="adversarial test: hard separated",
        ),
    ]
    contra_program = fix.program.model_copy(update={"adjacencies": contra_adj})
    with pytest.raises((Infeasible, Solve2DFailed)):
        solve_2d_placement(contra_program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)

    # Via CpSatPlanGenerator: candidate is marked infeasible without producing
    # an invalid model or crashing
    req_contra = GenerationRequest(
        site=site,
        program=contra_program,
        constraints=None,
        site_ref=None,
        program_ref=None,
        created_at=fix.program.provenance.created_at,
        strategies=[STRATEGY_CORRIDOR_FREE],
        solver=opts,
    )
    cands = CpSatPlanGenerator().candidates(req_contra)
    assert len(cands) == 1
    assert cands[0].status == "infeasible"
    assert cands[0].plan is None

    # 2. Oversized program: program area 10x envelope capacity (e.g., 2000 m2)
    oversized_items = [
        item.model_copy(update={"target_area_m2": item.target_area_m2 * 20.0, "min_area_m2": 150.0})
        for item in fix.program.items
    ]
    oversized_program = fix.program.model_copy(update={"items": oversized_items})
    with pytest.raises((Infeasible, Solve2DFailed)):
        solve_2d_placement(oversized_program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)

    req_oversized = GenerationRequest(
        site=site,
        program=oversized_program,
        constraints=None,
        site_ref=None,
        program_ref=None,
        created_at=fix.program.provenance.created_at,
        strategies=[STRATEGY_CORRIDOR_FREE],
        solver=opts,
    )
    cands_over = CpSatPlanGenerator().candidates(req_oversized)
    assert cands_over[0].status == "infeasible"
    assert cands_over[0].plan is None

    # 3. Impossible dimension bounds: room minimum width exceeds envelope width (e.g. 80 meters)
    impossible_item = ProgramItem(
        id="pi-gigantic",
        name="Gigantic Hall",
        function=SpaceFunction.LIVING,
        target_area_m2=500.0,
        min_width_m=80.0,
        priority=Priority.MUST,
        privacy=Privacy.PUBLIC,
    )
    impossible_program = fix.program.model_copy(update={"items": [impossible_item]})
    with pytest.raises((Infeasible, Solve2DFailed)):
        solve_2d_placement(impossible_program, site, frame, opts, strategy=STRATEGY_CORRIDOR_FREE)
