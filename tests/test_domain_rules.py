"""Validation rules of the brief, program, constraints, code packs and records."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from house_ai.domain.brief import BriefTopic, DesignBrief
from house_ai.domain.codepack import (
    CodePack,
    ComplianceStatus,
    compliance_statement,
    find_prohibited_claims,
)
from house_ai.domain.constraints import Constraint, ConstraintSet, SoftObjective
from house_ai.domain.evaluation import MetricClaim
from house_ai.domain.plan import ChangeRequest, PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import Actor
from house_ai.domain.records import AssumptionsFile, OpenQuestion, OpenQuestionsFile

from .conftest import example_doc

# ---------------------------------------------------------------------- brief

SPEC_INTERVIEW_TOPICS = """household members; ages; future children; multigenerational living;
long-term guests; accessibility and aging in place; lifestyle; waking/sleeping patterns;
entertaining; privacy; cultural practices; religious/ritual needs; guest/family separation;
cooking habits; kitchen type; dining; bedrooms/bathrooms; work/study; hobbies; gym; storage;
laundry; mechanical/service spaces; pets; vehicles; EV charging; outdoor living; garden; pool;
views; undesirable views; noise; security; smart-home requirements; materials/style;
maintenance tolerance; climate/comfort preferences; daylight; natural ventilation;
sustainability; budget; target area; schedule; future expansion; priorities and trade-offs"""


def test_brief_topics_cover_every_spec_interview_topic():
    spec_topics = [t.strip() for t in SPEC_INTERVIEW_TOPICS.replace("\n", " ").split(";")]
    assert len(spec_topics) == 45
    assert len(BriefTopic) == len(spec_topics)


def test_golden_brief_is_valid_and_keeps_unknowns_unknown():
    brief = DesignBrief.model_validate(example_doc("design_brief.yaml"))
    child_2 = next(m for m in brief.household if m.id == "hh-child-2")
    assert child_2.age_years is None
    assert brief.facts_for(BriefTopic.KITCHEN_TYPE)[0].key == "kitchen_layout"


def test_an_agent_inference_cannot_be_recorded_as_a_fact():
    doc = example_doc("design_brief.yaml")
    fact = next(f for f in doc["facts"] if f["id"] == "f-guest-sleep-living")
    fact["status"] = "verified_fact"
    with pytest.raises(ValidationError, match="agent inference cannot be recorded"):
        DesignBrief.model_validate(doc)


def test_an_owner_answer_is_not_an_inference():
    doc = example_doc("design_brief.yaml")
    doc["facts"][0]["status"] = "inference"
    with pytest.raises(ValidationError, match="not an inference"):
        DesignBrief.model_validate(doc)


def test_contradictions_must_cite_existing_facts():
    doc = example_doc("design_brief.yaml")
    doc["contradictions"] = [{"id": "ct", "statement": "x", "fact_ids": ["f-bedrooms", "f-nope"]}]
    with pytest.raises(ValidationError, match="f-nope"):
        DesignBrief.model_validate(doc)


# -------------------------------------------------------------------- program


def test_golden_program_totals():
    program = SpaceProgram.model_validate(example_doc("space_program.yaml"))
    assert program.net_target_area_m2 == pytest.approx(120.0)


def test_program_area_bounds_must_be_ordered():
    doc = example_doc("space_program.yaml")
    doc["items"][0]["min_area_m2"] = 40
    with pytest.raises(ValidationError, match="min_area <= target_area"):
        SpaceProgram.model_validate(doc)


def test_adjacency_must_reference_known_items():
    doc = example_doc("space_program.yaml")
    doc["adjacencies"][1]["b"] = "pi-garage"
    with pytest.raises(ValidationError, match="pi-garage"):
        SpaceProgram.model_validate(doc)


def test_adjacency_to_itself_is_rejected():
    doc = example_doc("space_program.yaml")
    doc["adjacencies"][1]["b"] = doc["adjacencies"][1]["a"]
    with pytest.raises(ValidationError, match="to itself"):
        SpaceProgram.model_validate(doc)


@pytest.mark.parametrize(
    ("strength", "weight", "message"),
    [("soft", None, "need a weight"), ("hard", 1.0, "must not carry a weight")],
)
def test_adjacency_weight_matches_strength(strength, weight, message):
    doc = example_doc("space_program.yaml")
    doc["adjacencies"][1].update(strength=strength, weight=weight)
    with pytest.raises(ValidationError, match=message):
        SpaceProgram.model_validate(doc)


def test_unknown_target_area_makes_total_unknown():
    doc = example_doc("space_program.yaml")
    doc["items"][0]["target_area_m2"] = None
    assert SpaceProgram.model_validate(doc).net_target_area_m2 is None


# ---------------------------------------------------------------- constraints


def test_golden_constraint_set_splits_hard_and_soft():
    cs = ConstraintSet.model_validate(example_doc("constraints.yaml"))
    assert len(cs.hard()) == 8 and len(cs.soft()) == 2


def test_soft_objectives_cover_the_spec_list():
    assert len(SoftObjective) == 21


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            {"strength": "soft", "rule": {"kind": "no_overlap"}, "source": {"kind": "system"}},
            "need a weight",
        ),
        (
            {
                "strength": "hard",
                "weight": 1,
                "rule": {"kind": "no_overlap"},
                "source": {"kind": "system"},
            },
            "must not carry a weight",
        ),
        (
            {
                "strength": "hard",
                "rule": {"kind": "objective", "objective": "views"},
                "source": {"kind": "brief"},
            },
            "soft by definition",
        ),
        (
            {"strength": "hard", "rule": {"kind": "no_overlap"}, "source": {"kind": "codepack"}},
            "cite a code rule",
        ),
        (
            {"strength": "hard", "rule": {"kind": "teleport"}, "source": {"kind": "system"}},
            "teleport",
        ),
    ],
)
def test_constraint_rules(data, message):
    with pytest.raises(ValidationError, match=message):
        Constraint.model_validate({"id": "c-x", **data})


# ------------------------------------------------------------------ codepacks


def _codepack(**update) -> CodePack:
    doc = example_doc("codepacks/synthetic-codepack.yaml")
    doc.update(update)
    return CodePack.model_validate(doc)


def test_no_codepack_means_not_checked():
    assert compliance_statement(None).label == "not checked"


def test_best_practice_checks_without_a_codepack_say_so():
    s = compliance_statement(None, ["r-anything"])
    assert s.status is ComplianceStatus.CONCEPTUAL_BEST_PRACTICE_ONLY
    assert s.label == "conceptual best-practice check only"


def test_unverified_codepack_cannot_produce_a_code_check():
    s = compliance_statement(_codepack(), ["r-min-bedroom-area"])
    assert s.status is ComplianceStatus.CONCEPTUAL_BEST_PRACTICE_ONLY
    assert "compliant" not in s.label


def test_verified_codepack_produces_a_scoped_statement():
    pack = _codepack(
        verification_status="verified_by_professional",
        verified_by={"kind": "human", "id": "architect-x"},
        verified_at="2026-10-01T00:00:00Z",
    )
    s = compliance_statement(pack, ["r-min-bedroom-area"])
    assert s.status is ComplianceStatus.CHECKED_AGAINST_CODEPACK
    assert "Nowhere (synthetic) 0.0-test" in s.label
    assert "not a permit determination" in s.label


def test_only_a_human_can_verify_a_codepack():
    with pytest.raises(ValidationError, match="only a human"):
        _codepack(
            verification_status="verified_by_professional",
            verified_by={"kind": "agent", "id": "claude"},
            verified_at="2026-10-01T00:00:00Z",
        )


def test_codepack_rule_ids_must_match_rules():
    with pytest.raises(ValidationError, match="rule_ids"):
        _codepack(rule_ids=["r-min-bedroom-area", "r-ghost"])


def test_checking_rules_outside_the_pack_is_an_error():
    with pytest.raises(ValueError, match="r-ghost"):
        compliance_statement(_codepack(), ["r-ghost"])


def test_prohibited_professional_claims_are_found():
    text = "Option B is code-compliant and permit ready. It is not structurally certified."
    assert find_prohibited_claims(text) == ["code-compliant", "permit ready"]
    assert find_prohibited_claims("This concept is not code compliant or construction-ready.") == []


# -------------------------------------------------------- evaluation and plans


def test_metric_claims_carry_honest_status():
    MetricClaim(
        metric="guest_private_crossings",
        value=0,
        method="graph_analysis",
        status="measured",
        evaluator="PrivacyEvaluator",
        evaluator_version="0",
    )
    with pytest.raises(ValidationError, match="cannot carry a value"):
        MetricClaim(
            metric="daylight_factor",
            value=2.1,
            method="none",
            status="not_checked",
            evaluator="DaylightEvaluator",
            evaluator_version="0",
        )
    with pytest.raises(ValidationError, match="needs a value"):
        MetricClaim(
            metric="daylight_factor",
            value=None,
            method="sim",
            status="simulated",
            evaluator="DaylightEvaluator",
            evaluator_version="0",
        )


def test_combine_request_needs_two_bases(plan):
    ref = {"kind": "plan", "id": "plan-a", "version": 1, "sha256": "a" * 64}
    base = {
        "id": "cr-1",
        "text": "combine the entrance of B with the courtyard of A",
        "kind": "combine",
        "requested_by": {"kind": "human", "id": "owner"},
        "requested_at": "2026-10-17T10:00:00Z",
    }
    with pytest.raises(ValidationError, match="at least two"):
        ChangeRequest.model_validate({**base, "base_versions": [ref]})
    ChangeRequest.model_validate({**base, "base_versions": [ref, {**ref, "id": "plan-b"}]})


def test_plan_parent_must_be_a_plan(plan_doc):
    plan_doc["parent"] = {"kind": "site", "id": "site", "version": 1, "sha256": "a" * 64}
    with pytest.raises(ValidationError, match="parent must be a plan"):
        PlanVersion.model_validate(plan_doc)


# --------------------------------------------------------------------- records


def test_answered_question_needs_an_answer():
    with pytest.raises(ValidationError):
        OpenQuestion(id="q", question="?", status="answered")


def test_golden_records_validate():
    assert len(AssumptionsFile.model_validate(example_doc("assumptions.yaml")).assumptions) == 2
    questions = OpenQuestionsFile.model_validate(example_doc("open_questions.yaml"))
    assert questions.blocking_open() == []


def test_actor_parsing_and_provider_fields():
    assert Actor.parse("agent:claude-code").id == "claude-code"
    with pytest.raises(ValueError):
        Actor.parse("claude-code")
    with pytest.raises(ValidationError, match="only be set on agent"):
        Actor(kind="human", id="owner", model="gpt")


def test_scene_manifest_validation():
    from house_ai.domain.build import SceneManifest

    plan_ref = {"kind": "plan", "id": "plan-a", "version": 1, "sha256": "a" * 64}
    build_ref = {"kind": "build_record", "id": "build-blender", "version": 1, "sha256": "b" * 64}
    prov = {
        "created_at": "2026-10-17T10:00:00Z",
        "created_by": {"kind": "agent", "id": "blender-agent"},
        "method": "blender_export",
    }
    manifest = SceneManifest.model_validate(
        {
            "id": "manifest-1",
            "plan_ref": plan_ref,
            "blender_build_ref": build_ref,
            "coordinate_system_id": "lcs-site",
            "materials": [{"id": "m-oak", "name": "Oak", "texture_scale_m": 1.0}],
            "objects": [
                {
                    "id": "obj-door-1",
                    "semantic_type": "door",
                    "domain_id": "d-front",
                    "material_ids": ["m-oak"],
                    "interaction": {"kind": "door", "max_angle_deg": 90.0},
                }
            ],
            "provenance": prov,
        }
    )
    assert manifest.objects[0].interaction.kind.value == "door"
    with pytest.raises(ValidationError, match="unknown material_id"):
        SceneManifest.model_validate(
            {
                "id": "manifest-1",
                "plan_ref": plan_ref,
                "blender_build_ref": build_ref,
                "coordinate_system_id": "lcs-site",
                "objects": [
                    {"id": "obj-1", "semantic_type": "wall", "material_ids": ["m-missing"]}
                ],
                "provenance": prov,
            }
        )

