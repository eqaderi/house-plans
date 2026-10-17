"""Milestone D: constraint compilation and the six evaluators, against ground truth."""

from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest

from house_ai.constraints.compiler import compile_constraints
from house_ai.domain.brief import DesignBrief
from house_ai.domain.codepack import CodePack, find_prohibited_claims
from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.evaluation import EvaluatorRunStatus
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram, Strength
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, ArtifactRef
from house_ai.domain.site import Site
from house_ai.evaluation.base import FUTURE_EVALUATORS, REQUIRED_EVALUATORS
from house_ai.evaluation.explain import comparison_markdown, explanation_markdown
from house_ai.evaluation.report import evaluate_plan
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.storage.hashing import content_hash, load_document

from .conftest import EXAMPLE, REPO

HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"
WHEN = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
TOOL = Actor(kind=ActorKind.SYSTEM, id="test")


def _doc(folder, name):
    return copy.deepcopy(load_document(folder / name))


def _bungalow():
    site = Site.model_validate(_doc(EXAMPLE, "site.yaml"))
    program = SpaceProgram.model_validate(_doc(EXAMPLE, "space_program.yaml"))
    plan = PlanVersion.model_validate(_doc(EXAMPLE, "plans/plan-a.json"))
    pack = CodePack.model_validate(_doc(EXAMPLE, "codepacks/synthetic-codepack.yaml"))
    return site, program, plan, pack


def _ref(plan: PlanVersion) -> ArtifactRef:
    return ArtifactRef(
        kind=ArtifactKind.PLAN, id=plan.option_id, version=1, sha256=content_hash(plan)
    )


def _metric(report, name, subject=None):
    for m in report.metrics:
        if m.metric == name and (subject is None or subject in m.subject_ids):
            return m
    raise AssertionError(f"no metric {name} {subject or ''}")


# ------------------------------------------------------------------ constraints


def test_compiler_separates_hard_requirements_from_soft_objectives():
    site, program, _, _ = _bungalow()
    cs = compile_constraints(program, site, created_at=WHEN, actor=TOOL).constraints
    hard = {c.id for c in cs.hard()}
    assert {
        "c-valid-geometry",
        "c-no-overlap",
        "c-openings-on-walls",
        "c-doors-connect",
        "c-reach-all",
        "c-within-envelope",
        "c-min-area-pi-living",
        "c-min-width-pi-bath",
        "c-adj-entry",
        "c-adj-living-kitchen",
        "c-adj-hall-bath",
    } <= hard
    soft = {c.id: c for c in cs.soft()}
    assert soft["c-adj-kitchen-beds"].weight == 2.0
    obj = soft["c-obj-privacy"]
    assert obj.source.kind.value == "system" and "default" in (obj.rationale or "")


def test_brief_answers_become_weighted_objectives_with_their_source():
    site = Site.model_validate(_doc(HILLSIDE, "site.yaml"))
    program = SpaceProgram.model_validate(_doc(HILLSIDE, "space_program.yaml"))
    brief = DesignBrief.model_validate(_doc(HILLSIDE, "design_brief.yaml"))
    cs = compile_constraints(program, site, created_at=WHEN, actor=TOOL, brief=brief).constraints
    by_id = {c.id: c for c in cs.constraints}
    acoustic = by_id["c-obj-acoustic-zoning"]
    assert acoustic.weight == 2.0 and acoustic.source.kind.value == "brief"
    assert acoustic.source.ref in ("f-bedrooms_separate", "f-office_quiet")
    assert by_id["c-obj-site-response"].source.ref == "f-slope_strategy"


def test_unverified_codepack_rules_only_guide_and_unknown_rules_are_not_checked():
    site, program, _, pack = _bungalow()
    res = compile_constraints(program, site, created_at=WHEN, actor=TOOL, codepack=pack)
    code = [c for c in res.constraints.constraints if c.code_rule is not None]
    assert {c.rule.program_item_id for c in code} == {"pi-bed-parents", "pi-bed-children"}
    assert all(c.strength is Strength.SOFT for c in code)
    assert res.code_rules_compiled == ["r-min-bedroom-area"]
    doc = _doc(EXAMPLE, "codepacks/synthetic-codepack.yaml")
    doc["rule_ids"].append("r-stair-pitch")
    doc["rules"].append(
        {
            "id": "r-stair-pitch",
            "title": "Stair pitch (invented)",
            "summary": "x",
            "citation": "synthetic §2",
            "parameters": {"max_pitch_deg": 42},
        }
    )
    res = compile_constraints(
        program, site, created_at=WHEN, actor=TOOL, codepack=CodePack.model_validate(doc)
    )
    assert res.code_rules_not_checked == ["r-stair-pitch"]


def test_verified_codepack_rules_are_hard():
    site, program, _, _ = _bungalow()
    doc = _doc(EXAMPLE, "codepacks/synthetic-codepack.yaml")
    doc.update(
        verification_status="verified_by_professional",
        verified_by={"kind": "human", "id": "test-architect"},
        verified_at="2026-10-17T12:00:00Z",
    )
    res = compile_constraints(
        program, site, created_at=WHEN, actor=TOOL, codepack=CodePack.model_validate(doc)
    )
    code = [c for c in res.constraints.constraints if c.code_rule is not None]
    assert code and all(c.strength is Strength.HARD for c in code)


def test_missing_envelope_is_compiled_as_parcel_only_and_noted():
    site, program, _, _ = _bungalow()
    bare = site.model_copy(update={"buildable_envelope": None})
    res = compile_constraints(program, bare, created_at=WHEN, actor=TOOL)
    env = next(c for c in res.constraints.constraints if c.id == "c-within-envelope")
    assert "parcel boundary only" in (env.rationale or "")
    assert any("setbacks" in n for n in res.notes)


# ------------------------------------------------------------------- evaluation


@pytest.fixture(scope="module")
def plan_a_report():
    site, program, plan, pack = _bungalow()
    cs = compile_constraints(program, site, created_at=WHEN, actor=TOOL, codepack=pack)
    return evaluate_plan(
        plan,
        _ref(plan),
        site=site,
        program=program,
        constraints=cs.constraints,
        codepack=pack,
        created_at=WHEN,
        site_verified=True,
    )


def test_plan_a_ground_truth_metrics(plan_a_report):
    r = plan_a_report
    assert _metric(r, "gross_floor_area_m2").value == pytest.approx(120.0)
    assert _metric(r, "footprint_area_m2").value == pytest.approx(120.0)
    assert _metric(r, "footprint_perimeter_m").value == pytest.approx(44.0)
    assert _metric(r, "level_count").value == 1
    assert _metric(r, "integrity_errors").value == 0
    assert _metric(r, "room_area_m2", "sp-bed-parents").value == pytest.approx(14.0)
    assert _metric(r, "circulation_ratio").value == pytest.approx(18.0 / 120.0)
    assert _metric(r, "unreachable_spaces").value == 0
    assert _metric(r, "max_depth_from_entrance").value == 1
    assert _metric(r, "guest_private_crossings").value == 0
    assert _metric(r, "private_public_shared_walls").value == 0
    assert _metric(r, "adjacency_satisfied", "adj-living-kitchen").value is True
    assert _metric(r, "adjacency_satisfied", "adj-kitchen-beds").value is True
    assert _metric(r, "soft_adjacency_score").value == pytest.approx(1.0)
    assert _metric(r, "within_envelope").value is True
    assert _metric(r, "min_clearance_to_envelope_m").value == pytest.approx(6.0)
    assert _metric(r, "parcel_coverage_pct").value == pytest.approx(100 * 120 / (32 * 34), abs=1e-3)
    assert _metric(r, "entrance_to_road_m").value == pytest.approx(17.7)
    assert r.hard_violations == []


def test_every_claim_says_how_it_was_obtained(plan_a_report):
    r = plan_a_report
    assert [
        e.name for e in r.evaluators if e.status is EvaluatorRunStatus.RAN
    ] == REQUIRED_EVALUATORS
    assert {e.name for e in r.evaluators if e.status is EvaluatorRunStatus.NOT_RUN} == set(
        FUTURE_EVALUATORS
    )
    for m in r.metrics:
        assert m.method and m.evaluator and m.evaluator_version
        assert (m.value is None) == (m.status is ClaimStatus.NOT_CHECKED)
    for name in ("excavation_volume_m3", "fill_volume_m3", "max_cut_m"):
        assert _metric(r, name).status is ClaimStatus.INFERRED  # interpolated terrain
    assert _metric(r, "max_walk_from_entrance_m").status is ClaimStatus.INFERRED


def test_unverified_codepack_never_yields_a_code_check(plan_a_report):
    assert plan_a_report.compliance.status.value == "conceptual_best_practice_only"
    assert plan_a_report.compliance.label == "conceptual best-practice check only"


def test_without_codepack_compliance_is_not_checked():
    site, program, plan, _ = _bungalow()
    cs = compile_constraints(program, site, created_at=WHEN, actor=TOOL).constraints
    r = evaluate_plan(
        plan, _ref(plan), site=site, program=program, constraints=cs, codepack=None, created_at=WHEN
    )
    assert r.compliance.label == "not checked"


def test_program_minima_violations_are_hard_and_mapped_to_constraints():
    site, program, plan, _ = _bungalow()
    doc = _doc(EXAMPLE, "space_program.yaml")
    for item in doc["items"]:
        if item["id"] == "pi-living":
            item["min_area_m2"] = 40
            item["target_area_m2"] = 40
        if item["id"] == "pi-bath":
            item["min_width_m"] = 3.2
    tight = SpaceProgram.model_validate(doc)
    cs = compile_constraints(tight, site, created_at=WHEN, actor=TOOL).constraints
    r = evaluate_plan(
        plan, _ref(plan), site=site, program=tight, constraints=cs, codepack=None, created_at=WHEN
    )
    hard = {(v.code, v.constraint_id) for v in r.hard_violations}
    assert ("min_area_violation", "c-min-area-pi-living") in hard
    assert ("min_dimension_violation", "c-min-width-pi-bath") in hard


@pytest.fixture(scope="module")
def hillside_reports():
    site = Site.model_validate(_doc(HILLSIDE, "site.yaml"))
    program = SpaceProgram.model_validate(_doc(HILLSIDE, "space_program.yaml"))
    cs = compile_constraints(program, site, created_at=WHEN, actor=TOOL).constraints
    req = GenerationRequest(
        site=site,
        program=program,
        constraints=cs,
        site_ref=None,
        program_ref=None,
        created_at=WHEN,
        strategies=["compact", "split_level", "linear"],
    )
    out = []
    for c in CpSatPlanGenerator().candidates(req):
        rep = evaluate_plan(
            c.plan,
            _ref(c.plan),
            site=site,
            program=program,
            constraints=cs,
            codepack=None,
            created_at=WHEN,
        )
        out.append((c.plan, rep, program))
    return out


def test_hillside_site_metrics_expose_cut_fill_and_retaining(hillside_reports):
    by = {p.strategy: r for p, r, _ in hillside_reports}
    compact, split = by["compact"], by["split_level"]
    assert _metric(compact, "retaining_wall_length_m").value > 0
    assert _metric(compact, "max_cut_m").value > 1.0  # the walk-out level is dug in
    assert _metric(split, "terrain_coverage_pct").value == pytest.approx(100.0)
    assert _metric(by["linear"], "level_count").value == 1
    # A one-level concept for a two-storey program is flagged, not hidden.
    codes = {v.code for v in by["linear"].violations}
    assert "level_count_differs" in codes
    assert all(
        v.strength is Strength.SOFT
        for v in by["linear"].violations
        if v.code == "program_item_missing"
    )


def test_explanations_and_comparison_make_no_professional_claims(hillside_reports):
    texts = [explanation_markdown(p, 1, r, prog) for p, r, prog in hillside_reports]
    texts.append(
        comparison_markdown([(p, 1, r) for p, r, _ in hillside_reports], [("courtyard", "no room")])
    )
    for text in texts:
        assert find_prohibited_claims(text) == []
        assert "not checked" in text or "no permit" in text or "None is reviewed" in text


def _route_model(*, stacked=False, garage=False):
    """Two simple rectangles, with exact horizontal route distances."""
    from house_ai.domain.model import HouseModel

    second_level = "l1" if stacked else "l0"
    second_bounds = [[0, 0], [4, 0], [4, 2], [0, 2]] if stacked else [
        [4, 0], [14, 0], [14, 2], [4, 2]
    ]
    doc = {
        "id": "route-model", "name": "Synthetic route", "coordinate_system_id": "local",
        "levels": [{"id": "l0", "name": "Entry", "elevation_m": 0}],
        "spaces": [
            {"id": "entry", "name": "Entry", "function": "entry", "level_id": "l0",
             "boundary": {"outer": [[0, 0], [4, 0], [4, 2], [0, 2]]}},
            {"id": "other", "name": "Other", "function": "garage" if garage else "living",
             "level_id": second_level, "boundary": {"outer": second_bounds}},
        ],
        "walls": [], "openings": [],
    }
    if stacked:
        doc["levels"].append({"id": "l1", "name": "Upper", "elevation_m": 2})
        doc["stairs"] = [{
            "id": "stairs", "kind": "straight", "from_level_id": "l0", "to_level_id": "l1",
            "bottom_space_id": "entry", "top_space_id": "other", "width_m": 1,
            "riser_count": 11, "tread_depth_m": 0.28,
            "footprint": {"outer": [[2.5, 0.5], [3.5, 0.5], [3.5, 1.5], [2.5, 1.5]]},
        }]
    portals = [
        ("d-front", "l0", 0, "entry", "exterior"),
        ("d-garage" if garage else "d-rear", second_level,
         0 if stacked else 14, "other", "exterior"),
    ]
    if not stacked:
        portals.append(("d-internal", "l0", 4, "entry", "other"))
    for ident, level, x, a, b in portals:
        doc["walls"].append({
            "id": "w-" + ident, "level_id": level, "start": [x, 0], "end": [x, 2],
            "thickness_m": 0.2, "height_m": 2.8, "kind": "exterior",
        })
        doc["openings"].append({
            "id": ident, "host_wall_id": "w-" + ident, "kind": "door",
            "offset_m": 0.5, "width_m": 1, "height_m": 2.1, "connects": [a, b],
        })
    return HouseModel.model_validate(doc)


def test_walking_routes_preserve_stacked_levels_and_include_the_stair_run():
    from house_ai.evaluation.evaluators import CirculationEvaluator

    distances = CirculationEvaluator._walk(_route_model(stacked=True))
    assert distances["entry"] == pytest.approx(2)
    # 3 m from entrance to stair centre + 10 treads x 0.28 m + 1 m to room centre.
    assert distances["other"] == pytest.approx(6.8)


@pytest.mark.parametrize("garage", [False, True])
def test_routes_start_at_front_door_without_external_or_vehicle_shortcuts(garage):
    from house_ai.evaluation.base import EvaluationContext
    from house_ai.evaluation.evaluators import CirculationEvaluator

    model = _route_model(garage=garage)
    assert CirculationEvaluator._walk(model)["other"] == pytest.approx(9)
    result = CirculationEvaluator().evaluate(EvaluationContext(model, None, None, None))
    assert _metric(result, "max_depth_from_entrance").value == 1
    assert _metric(result, "entrance_route_basis").value == "front_door_identifier"


def test_hand_authored_entrance_fallback_is_explicit_and_excludes_garage():
    from house_ai.evaluation.base import EvaluationContext
    from house_ai.evaluation.evaluators import CirculationEvaluator

    model = _route_model(garage=True)
    model.openings[0] = model.openings[0].model_copy(update={"id": "pedestrian-door"})
    result = CirculationEvaluator().evaluate(EvaluationContext(model, None, None, None))
    assert _metric(result, "entrance_route_basis").value == "inferred_from_entry_space"
    assert CirculationEvaluator._walk(model)["other"] == pytest.approx(9)


def test_unlabelled_pedestrian_fallback_is_reported_as_an_assumption():
    from house_ai.domain.program import SpaceFunction
    from house_ai.evaluation.base import EvaluationContext
    from house_ai.evaluation.evaluators import CirculationEvaluator

    model = _route_model(garage=True)
    model.openings[0] = model.openings[0].model_copy(update={"id": "pedestrian-door"})
    model.spaces[0] = model.spaces[0].model_copy(update={"function": SpaceFunction.HALL})
    result = CirculationEvaluator().evaluate(EvaluationContext(model, None, None, None))
    assert _metric(result, "entrance_route_basis").value == "assumed_first_pedestrian_door"
    assert CirculationEvaluator._walk(model)["other"] == pytest.approx(9)
