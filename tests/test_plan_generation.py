"""Milestone D: solver-backed concept generation on synthetic sites only."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

import pytest

from house_ai.domain.integrity import check_model, errors
from house_ai.domain.model import OpeningKind, WallKind
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram, SpaceRelationshipKind, Strength
from house_ai.domain.site import Site
from house_ai.domain.terrain import elevation_at, site_surface
from house_ai.evaluation.explain import concept_signature, footprint_iou, zoning_difference
from house_ai.generation.base import PlanGenerator
from house_ai.generation.frame import design_frame
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.generation.massing import FLOOR_TO_FLOOR_M, HALF_STOREY_M
from house_ai.generation.rooms import expand_program, slot_adjacency
from house_ai.storage.hashing import canonical_json, load_document

from .conftest import REPO

HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"
BUNGALOW = REPO / "examples" / "projects" / "synthetic-bungalow"
WHEN = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


def _load(folder: Path) -> tuple[Site, SpaceProgram]:
    site = Site.model_validate(load_document(folder / "site.yaml"))
    program = SpaceProgram.model_validate(load_document(folder / "space_program.yaml"))
    return site, program


def _generate(site: Site, program: SpaceProgram, **kw):
    req = GenerationRequest(
        site=site,
        program=program,
        constraints=None,
        site_ref=None,
        program_ref=None,
        created_at=WHEN,
        **kw,
    )
    return CpSatPlanGenerator().candidates(req)


@pytest.fixture(scope="module")
def hillside():
    return _load(HILLSIDE)


@pytest.fixture(scope="module")
def hillside_candidates(hillside):
    return _generate(*hillside)


@pytest.fixture(scope="module")
def hillside_plans(hillside_candidates) -> dict[str, PlanVersion]:
    return {c.strategy: c.plan for c in hillside_candidates if c.plan is not None}


def test_fixture_is_synthetic_and_not_the_real_project():
    site, _ = _load(HILLSIDE)
    assert site.classification.value == "synthetic"
    assert site.project_id == "synthetic-hillside"
    assert site.boundary.area_m2 == pytest.approx(737.5, rel=1e-2)
    text = (HILLSIDE / "site.yaml").read_text(encoding="utf-8")
    assert "my-house" not in text and "seperated" not in text


def test_generator_meets_the_plan_generator_protocol(hillside):
    gen: PlanGenerator = CpSatPlanGenerator()
    plans = gen.generate(hillside[0], hillside[1], None, strategies=["linear"], seed=0)  # type: ignore[arg-type]
    assert [p.strategy for p in plans] == ["linear"]


def test_steep_site_gets_at_least_three_valid_structurally_different_concepts(
    hillside, hillside_plans
):
    site, program = hillside
    assert len(hillside_plans) >= 3
    for strategy, plan in hillside_plans.items():
        assert errors(check_model(plan.model, site, program)) == [], strategy
    plans = list(hillside_plans.values())
    for a, b in combinations(plans, 2):
        distinct = (
            concept_signature(a.model) != concept_signature(b.model)
            or footprint_iou(a.model, b.model) < 0.75
            or zoning_difference(a.model, b.model) >= 0.15
        )
        assert distinct, (a.strategy, b.strategy)
    # Not just cosmetic: single-level and multi-level, stacked and stepped concepts all exist.
    levels = {s: len(p.model.levels) for s, p in hillside_plans.items()}
    assert levels["linear"] == 1 and levels["compact"] >= 2 and levels["split_level"] >= 2


def test_every_room_meets_its_program_minimum_and_width(hillside, hillside_plans):
    _, program = hillside
    items = {i.id: i for i in program.space_requirements}
    for plan in hillside_plans.values():
        for s in plan.model.spaces:
            item = items.get(s.program_item_id or "")
            if item is None:
                continue
            if item.min_area_m2:
                assert s.area_m2 >= item.min_area_m2 - 1e-6, (plan.strategy, s.id)
            if item.min_width_m:
                r = s.boundary.to_shapely().minimum_rotated_rectangle
                pts = list(r.exterior.coords)
                side = min(math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2]))
                assert side >= item.min_width_m - 1e-6, (plan.strategy, s.id)


def test_hard_connections_are_doors_or_openings(hillside, hillside_plans):
    _, program = hillside
    hard = [
        a
        for a in program.space_relationships
        if a.strength is Strength.HARD and a.kind is SpaceRelationshipKind.CONNECTED
    ]
    assert hard, "the fixture should exercise hard connections (open-plan living)"
    for plan in hillside_plans.values():
        codes = {f.code for f in check_model(plan.model, None, program)}
        assert "hard_adjacency_violation" not in codes, plan.strategy


def test_open_plan_triangle_is_laid_out_so_every_pair_touches(hillside):
    _, program = hillside
    rooms = expand_program(program)
    lkd = next(
        c for c in rooms.clusters if {"sp-living", "sp-kitchen"} <= {m.space_id for m in c.members}
    )
    adj = slot_adjacency(lkd.slots)
    assert all(frozenset(p) in adj for p in lkd.connections)
    assert lkd.unsatisfied == []


def test_design_frame_follows_the_rotated_road_edge(hillside):
    site, _ = hillside
    frame = design_frame(site)
    assert frame.road_feature_id == "road-uphill"
    # The fixture is rotated 12 degrees from the local axes.
    assert math.degrees(math.atan2(frame.u_dir[1], frame.u_dir[0])) == pytest.approx(12.0, abs=1e-3)


def test_entry_level_sits_on_the_road_side_ground(hillside, hillside_plans):
    site, _ = hillside
    surface = site_surface(site)
    for plan in hillside_plans.values():
        entry = plan.model.level("lv-entry")
        entrance = next(s for s in plan.model.spaces if s.function.value == "entry")
        assert entrance.level_id == "lv-entry"
        garage = next(s for s in plan.model.spaces if s.function.value == "garage")
        assert garage.level_id == "lv-entry", plan.strategy
        # The entry floor is within half a storey of the ground at the entrance.
        c = entrance.boundary.to_shapely().centroid
        assert abs(elevation_at(surface, (c.x, c.y)) - entry.elevation_m) < HALF_STOREY_M


def test_split_level_steps_follow_the_terrain(hillside_plans):
    plan = hillside_plans["split_level"]
    zs = sorted(lv.elevation_m for lv in plan.model.levels)
    entry = plan.model.level("lv-entry").elevation_m
    assert len(zs) >= 2
    for z in zs:
        steps = (z - entry) / HALF_STOREY_M
        assert steps == pytest.approx(round(steps))
        assert abs(z - entry) <= 2 * FLOOR_TO_FLOOR_M
    assert min(zs) < entry  # the site falls away from the road, so the house steps down
    assert plan.model.stairs and all(
        st.riser_count and st.riser_height_m <= 0.18 + 1e-9 for st in plan.model.stairs
    )


def test_walk_out_level_has_retaining_walls_and_no_windows_in_them(hillside_plans):
    plan = hillside_plans["compact"]
    lower = [lv for lv in plan.model.levels if lv.id != "lv-entry"]
    assert lower and all(lv.elevation_m < plan.model.level("lv-entry").elevation_m for lv in lower)
    retaining = {w.id for w in plan.model.walls if w.kind is WallKind.RETAINING}
    assert retaining
    for o in plan.model.openings:
        if o.kind is OpeningKind.WINDOW:
            assert plan.model.wall(o.host_wall_id).kind is WallKind.EXTERIOR
    assert any(i.id == "iss-hillside-engineering" for i in plan.model.issues)


def test_generation_is_deterministic(hillside):
    a = _generate(*hillside, strategies=["split_level", "two_wing"])
    b = _generate(*hillside, strategies=["split_level", "two_wing"])
    assert [canonical_json(c.plan) for c in a] == [canonical_json(c.plan) for c in b]


def test_plan_records_how_it_was_generated(hillside_plans):
    plan = hillside_plans["two_wing"]
    g = plan.generation
    assert g is not None and g.solver == "ortools-cp-sat"
    assert g.solver_status in ("OPTIMAL", "FEASIBLE")
    # Every room the solver placed is recorded; stairs, terraces (S10-11) and the separate
    # garage (S10-19) are laid out by the assembler around them.
    assert {p.space_id for p in g.placements} >= {
        s.id
        for s in plan.model.spaces
        if s.program_item_id and s.function.value not in ("stair", "terrace", "garage")
    }
    assert plan.provenance.created_by.kind.value == "system"


def test_split_level_is_refused_on_a_flat_site_with_a_reason():
    site, program = _load(BUNGALOW)
    cands = {c.strategy: c for c in _generate(site, program)}
    assert cands["split_level"].plan is None
    assert "not warranted" in (cands["split_level"].reason or "")
    valid = [c for c in cands.values() if c.valid]
    assert len(valid) >= 3


def test_unknown_strategy_is_reported_not_raised(hillside):
    [c] = _generate(*hillside, strategies=["pagoda"])
    assert c.plan is None and "unknown strategy" in (c.reason or "")


def test_site_without_envelope_uses_parcel_and_says_so(hillside):
    site, program = hillside
    bare = site.model_copy(update={"buildable_envelope": None})
    [c] = _generate(bare, program, strategies=["linear"])
    assert c.valid
    asm = next(a for a in c.plan.model.assumptions if a.id == "asm-gen-envelope")
    assert asm.status.value == "unknown" and "not the buildable area" in asm.statement
    assert any(i.id == "iss-envelope-unknown" for i in c.plan.model.issues)


def test_site_without_local_frame_is_refused(hillside):
    site, program = hillside
    coords = site.coordinates.model_copy(update={"local": None})
    [c] = _generate(site.model_copy(update={"coordinates": coords}), program, strategies=["linear"])
    assert c.plan is None and "local coordinate system" in (c.reason or "")


def test_unknown_terrain_still_generates_but_refuses_split_level(hillside):
    site, program = hillside
    flat = site.model_copy(
        update={
            "terrain": site.terrain.model_copy(update={"spot_elevations": [], "status": "unknown"})
        }
    )
    cands = {c.strategy: c for c in _generate(flat, program, strategies=["linear", "split_level"])}
    assert cands["linear"].valid
    assert any("local datum" in a.statement for a in cands["linear"].plan.model.assumptions)
    assert cands["split_level"].plan is None and "terrain" in (cands["split_level"].reason or "")
