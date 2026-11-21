"""Synthetic regression cases from the independent S7 working-tree review."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from house_ai.constants.placement2d import L_SHAPE_MIN_RECESS_DM
from house_ai.constraints.compiler import compile_constraints
from house_ai.domain.benchmark import BenchmarkFixture
from house_ai.domain.constraints import Constraint, ConstraintSource, MinAreaRule, MinDimensionRule
from house_ai.domain.integrity import check_model, circulation_graph, errors
from house_ai.domain.program import SpaceProgram, SpaceRelationship, SpaceRequirement
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import Actor, ActorKind, Provenance
from house_ai.domain.relations import is_relation_satisfied
from house_ai.generation.assemble2d import assemble_2d
from house_ai.generation.frame import Ground, design_frame
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.generation.solver2d import (
    PlacementOptions,
    extract_placement_rooms,
    solve_2d_placement,
)

WHEN = datetime(2026, 10, 18, tzinfo=UTC)
ACTOR = Actor(kind=ActorKind.AGENT, id="codex")


def fixture(name="flat-simple"):
    return BenchmarkFixture.model_validate_json(
        Path(f"examples/benchmarks/fixtures/{name}.json").read_text()
    )


def small_program(*, relation=None, quantity=1):
    return SpaceProgram(
        id="program-review",
        project_id="proj-demo",
        storeys=2,
        space_requirements=[
            SpaceRequirement(
                id="pi-entry",
                name="Entry",
                function="entry",
                privacy="public",
                min_area_m2=9,
                target_area_m2=9,
                min_width_m=3,
            ),
            SpaceRequirement(
                id="pi-bed",
                name="Bedroom",
                function="bedroom",
                privacy="private",
                min_area_m2=9,
                target_area_m2=12,
                min_width_m=3,
                quantity=quantity,
            ),
            SpaceRequirement(
                id="pi-living",
                name="Living",
                function="living",
                privacy="public",
                min_area_m2=16,
                target_area_m2=20,
                min_width_m=3,
            ),
        ],
        space_relationships=[relation] if relation else [],
        provenance=Provenance(created_at=WHEN, created_by=ACTOR, method="synthetic_fixture"),
    )


def solve_model(program, *, site=None, proposal=None, opts=None, strategy="corridor_free"):
    site = site or fixture().site
    frame = design_frame(site)
    sol = solve_2d_placement(
        program,
        site,
        frame,
        opts or PlacementOptions(seed=42, deterministic_time=2),
        proposal=proposal,
        strategy=strategy,
    )
    model = assemble_2d(sol, site, frame, Ground(site, frame), program, ACTOR)
    return sol, model


def test_quantity_uses_canonical_instance_ids():
    rooms = extract_placement_rooms(small_program(quantity=3))
    assert {r.space_id for r in rooms if r.item_id == "pi-bed"} == {
        "sp-bed-1",
        "sp-bed-2",
        "sp-bed-3",
    }


@pytest.mark.parametrize(
    "rule",
    [
        MinAreaRule(program_item_id="pi-living", min_area_m2=45),
        MinDimensionRule(program_item_id="pi-living", min_width_m=4.5),
    ],
    ids=["area", "width"],
)
def test_compiled_bounds_reach_the_2d_generator(rule):
    # Without the rule living gets about its 20 m2 target as a 3 m wide room, so each rule,
    # alone, must change the layout to hold.
    program, site = small_program(), fixture().site
    cs = compile_constraints(program, site, created_at=WHEN, actor=ACTOR).constraints
    cs.constraints.append(
        Constraint(
            id="review-bound", strength="hard", rule=rule, source=ConstraintSource(kind="user")
        )
    )
    [candidate] = CpSatPlanGenerator().candidates(
        GenerationRequest(
            site=site,
            program=program,
            constraints=cs,
            site_ref=None,
            program_ref=None,
            created_at=WHEN,
            strategies=["corridor_free"],
            seed=42,
            deterministic_time=4,
        )
    )
    assert candidate.plan is not None, candidate.reason
    room = candidate.plan.model.space("sp-living")
    if isinstance(rule, MinAreaRule):
        assert room.area_m2 >= 45 - 1e-6
    else:
        x0, y0, x1, y1 = room.boundary.to_shapely().bounds
        assert min(x1 - x0, y1 - y0) >= 4.5 - 1e-6


@pytest.mark.parametrize("kind", ["separated", "acoustic_separation", "connected", "near"])
def test_hard_relation_agrees_with_canonical_geometry(kind):
    adj = SpaceRelationship(
        id="review-rel", a="pi-living", b="pi-bed", kind=kind, strength="hard"
    )
    p = small_program(relation=adj)
    _, model = solve_model(p)
    ok, _ = is_relation_satisfied(
        adj.kind, model, circulation_graph(model), ["sp-living"], ["sp-bed"]
    )
    assert ok is True
    assert not errors(check_model(model, fixture().site, p))


def test_hard_exterior_connection_is_real_door():
    adj = SpaceRelationship(
        id="review-ext", a="pi-living", b="exterior", kind="connected", strength="hard"
    )
    _, model = solve_model(small_program(relation=adj))
    assert "exterior" in circulation_graph(model)["sp-living"]


@pytest.mark.parametrize("name", ["concave", "narrow-deep"])
def test_irregular_envelope_is_enforced(name):
    # Both benchmark envelopes have room for their program: a solve that fails is a defect.
    f = fixture(name)
    _, model = solve_model(f.program, site=f.site)
    assert {s.program_item_id for s in model.spaces} >= {
        i.id for i in f.program.space_requirements
    }
    assert [e.code for e in errors(check_model(model, f.site, f.program))] == []


def test_lower_levels_zones_and_outdoor_links_are_applied():
    p = small_program()
    prop = ConceptProposal.model_validate(
        {
            "id": "review-prop",
            "project_id": p.project_id,
            "name": "Lower bedrooms",
            "intent": "Lower bedroom, private zone and living terrace",
            "level_assignments": [
                {
                    "program_item_id": i.id,
                    "level_id": "lv-lower" if i.id == "pi-bed" else "lv-entry",
                }
                for i in p.space_requirements
            ],
            "stair_cores": [
                {
                    "id": "sc-review",
                    "position": "entry",
                    "connects_levels": ["lv-entry", "lv-lower"],
                }
            ],
            "zones": [
                {
                    "id": "review-zone",
                    "name": "Private",
                    "privacy": "private",
                    "program_item_ids": ["pi-bed"],
                }
            ],
            "outdoor_links": [
                {"id": "ol-review", "program_item_id": "pi-living", "kind": "terrace"}
            ],
        }
    )
    _, model = solve_model(p, proposal=prop)
    bed = model.space("sp-bed")
    assert bed.level_id == "lv-lower"
    assert model.level(bed.level_id).elevation_m < model.level("lv-entry").elevation_m
    assert bed.zone_id == "review-zone"
    assert next(z for z in model.zones if z.id == bed.zone_id).privacy.value == "private"
    terraces = {s.id for s in model.spaces if s.function.value == "terrace"}
    assert terraces & circulation_graph(model)["sp-living"]
    assert not errors(check_model(model, fixture().site, p))


def test_level_revision_uses_space_id():
    p = small_program()
    _, model = solve_model(
        p, opts=PlacementOptions(seed=42, deterministic_time=2, level_prefs={"sp-bed": "lower"})
    )
    assert model.space("sp-bed").level_id == "lv-lower"


def test_entry_elevation_preserves_known_terrain():
    f = fixture("steep-reference")
    _, model = solve_model(f.program, site=f.site)
    frame = design_frame(f.site)
    ground = Ground(f.site, frame)
    entrance = next(o for o in model.openings if o.is_passable and "exterior" in o.connects)
    wall = model.wall(entrance.host_wall_id)
    mid = ((wall.start[0] + wall.end[0]) / 2, (wall.start[1] + wall.end[1]) / 2)
    terrain = ground.at(*frame.to_design(mid))
    assert abs(model.level("lv-entry").elevation_m - terrain) < 1.0


def test_two_wing_has_actual_reentrant_corner():
    """The day wing (entry, living) and the night wing (bedroom) meet at a shared wall, and
    one sticks out past the other by at least the recess along each axis: an L whose
    corner at the far end of both wings is empty (solver grid units, dm)."""
    p = small_program()
    sol, _ = solve_model(p, strategy="two_wing")
    rooms = {r.space_id: box(r.u0, r.v0, r.u1, r.v1) for r in sol.rooms}
    assert set(rooms) == {"sp-entry", "sp-living", "sp-bed"}
    day = unary_union([rooms["sp-entry"], rooms["sp-living"]])
    night = rooms["sp-bed"]
    assert day.intersection(night).length > 0  # a shared wall, not a gap or a corner point
    (_, _, xd, yd), (_, _, xn, yn) = day.bounds, night.bounds
    # Exactly one wing reaches further in x, and the other further in y.
    assert (xd - xn >= L_SHAPE_MIN_RECESS_DM and yn - yd >= L_SHAPE_MIN_RECESS_DM) or (
        xn - xd >= L_SHAPE_MIN_RECESS_DM and yd - yn >= L_SHAPE_MIN_RECESS_DM
    )
    footprint = unary_union(list(rooms.values()))
    notch = box(min(xd, xn), min(yd, yn), max(xd, xn), max(yd, yn))
    assert notch.area >= L_SHAPE_MIN_RECESS_DM**2
    assert footprint.intersection(notch).area == 0


def test_pinned_proposal_preserved_during_ordinary_revision(tmp_path):
    from house_ai.domain.provenance import ArtifactKind
    from house_ai.orchestration.plans import PlanService

    from .conftest import AGENT
    from .test_plan_workflow import _approve_site_and_program, _load

    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    inp = svc.inputs(exploratory=False)
    prop = ConceptProposal.model_validate(
        {
            "id": "review-prop-pin",
            "project_id": store.manifest().id,
            "name": "Pinned Compact Proposal",
            "intent": "Pin kitchen-living direct connection",
            "level_assignments": [
                {"program_item_id": i.id, "level_id": "lv-entry"}
                for i in inp.program.space_requirements
            ],
            "adjacency_graph": [
                {
                    "id": "padj-kitchen-living",
                    "a": "pi-kitchen",
                    "b": "pi-living",
                    "kind": "connected",
                    "strength": "hard",
                }
            ],
            "target_strategy": "compact",
        }
    )
    # Feasible at a quarter of the default time; the checks below hold for any layout that
    # meets the hard constraints, and the revision inherits the time.
    outcome = svc.propose(AGENT, prop, deterministic_time=1.0)
    opt_id = outcome.options[0].candidate.option_id
    plan_v1 = outcome.options[0].candidate.plan
    assert plan_v1.generation.parameters.get("proposal_id") == prop.id
    assert any(r.kind is ArtifactKind.CONCEPT_PROPOSAL for r in plan_v1.provenance.inputs)

    # Ordinary revision with no ops: proposal and topology survive
    rev_res = svc.revise(
        opt_id,
        "Keep the topology exactly as it is.",
        AGENT,
        ops=[],
    )
    plan_v2 = rev_res.option.candidate.plan
    assert plan_v2 is not None
    assert rev_res.option.plan_ref.version == 2
    assert plan_v2.generation.parameters.get("proposal_id") == prop.id
    (proposal_ref,) = [
        r for r in plan_v1.provenance.inputs if r.kind is ArtifactKind.CONCEPT_PROPOSAL
    ]
    assert [r for r in plan_v2.provenance.inputs if r.kind is ArtifactKind.CONCEPT_PROPOSAL] == [
        proposal_ref
    ]
    assert "sp-living" in circulation_graph(plan_v2.model)["sp-kitchen"]
    # The revision re-solves the same request with the same seed on one worker, so with no
    # operation the layout comes back unchanged.
    assert [(sp.id, sp.level_id, sp.boundary) for sp in plan_v2.model.spaces] == [
        (sp.id, sp.level_id, sp.boundary) for sp in plan_v1.model.spaces
    ]


def test_open_plan_three_functions_composite_space():
    program = SpaceProgram(
        id="prog-open-3",
        project_id="proj-demo",
        storeys=1,
        space_requirements=[
            SpaceRequirement(
                id="pi-entry",
                name="Entry",
                function="entry",
                privacy="public",
                min_area_m2=6,
                min_width_m=2,
            ),
            SpaceRequirement(
                id="pi-living",
                name="Living",
                function="living",
                privacy="public",
                min_area_m2=20,
                min_width_m=4,
            ),
            SpaceRequirement(
                id="pi-dining",
                name="Dining",
                function="dining",
                privacy="public",
                min_area_m2=12,
                min_width_m=3,
            ),
            SpaceRequirement(
                id="pi-kitchen",
                name="Kitchen",
                function="kitchen",
                privacy="public",
                min_area_m2=10,
                min_width_m=3,
            ),
        ],
        space_relationships=[
            SpaceRelationship(
                id="adj-live-dine",
                a="pi-living",
                b="pi-dining",
                kind="connected",
                strength="hard",
            ),
            SpaceRelationship(
                id="adj-dine-kitch",
                a="pi-dining",
                b="pi-kitchen",
                kind="connected",
                strength="hard",
            ),
        ],
        provenance=Provenance(created_at=WHEN, created_by=ACTOR, method="synthetic"),
    )
    sol, model = solve_model(program, strategy="open_plan")
    assert len(model.composite_spaces) == 1
    comp = model.composite_spaces[0]
    assert set(comp.space_ids) == {"sp-living", "sp-dining", "sp-kitchen"}
    # The union of three rooms that share walls has exactly their summed area.
    rooms = sum(model.space(i).area_m2 for i in ("sp-living", "sp-dining", "sp-kitchen"))
    assert comp.boundary.area_m2 == pytest.approx(rooms, abs=1e-6)
    assert not errors(check_model(model, fixture().site, program))
