"""Tests for critique grounding validator (Stage S5, Task S5-06)."""

from __future__ import annotations

import pytest

from house_ai.domain.evaluation import (
    ClaimStatus,
    EvaluationReport,
    EvaluatorRun,
    EvaluatorRunStatus,
    MetricClaim,
)
from house_ai.domain.geometry import Polygon2D
from house_ai.domain.model import HouseModel, Level, Opening, OpeningKind, Space, Wall, WallKind
from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import Actor, ArtifactKind, ArtifactRef, Provenance
from house_ai.domain.revision_ops import RevisionOp
from house_ai.domain.visual_critique import VisualClaim, VisualCritiqueFile
from house_ai.validation.grounding import (
    CANONICAL_PLAN_TARGETS,
    GroundingError,
    collect_canonical_ids,
    collect_plan_element_ids,
    validate_cited_ids,
    validate_critique_grounding,
)


@pytest.fixture
def sample_plan() -> PlanVersion:
    actor = Actor(kind="agent", id="agent:gemini")
    prov = Provenance(created_at="2026-10-18T00:00:00Z", created_by=actor, method="test")

    model = HouseModel(
        id="model-test",
        name="Test Model",
        coordinate_system_id="local",
        levels=[Level(id="lvl-ground", name="Ground", elevation_m=0.0)],
        spaces=[
            Space(
                id="sp-living",
                name="Living Room",
                function="living",
                level_id="lvl-ground",
                boundary=Polygon2D(outer=[[0, 0], [6, 0], [6, 5], [0, 5]]),
            ),
            Space(
                id="sp-kitchen",
                name="Kitchen",
                function="kitchen",
                level_id="lvl-ground",
                boundary=Polygon2D(outer=[[6, 0], [10, 0], [10, 4], [6, 4]]),
            ),
        ],
        walls=[
            Wall(
                id="w-ext-1",
                level_id="lvl-ground",
                kind=WallKind.EXTERIOR,
                start=[0, 0],
                end=[10, 0],
                thickness_m=0.3,
                height_m=2.8,
            )
        ],
        openings=[
            Opening(
                id="d-entry",
                host_wall_id="w-ext-1",
                kind=OpeningKind.DOOR,
                offset_m=2.0,
                width_m=1.0,
                height_m=2.1,
                connects=("sp-living", "exterior"),
            )
        ],
    )

    return PlanVersion(
        option_id="concept-compact",
        label="Compact",
        strategy="compact",
        provenance=prov,
        model=model,
    )


def test_valid_grounded_critique_passes(sample_plan):
    """A critique referencing existing IDs passes grounding validation."""
    critique = VisualCritiqueFile(
        project="synthetic-bungalow",
        option="concept-compact",
        plan_version=1,
        author="agent:reviewer",
        screenshot_hash="a" * 64,
        claims=[
            VisualClaim(
                id="vc-01",
                element_ids=["sp-kitchen", "sp-living"],
                claim_text=(
                    "Kitchen and living room feel too directly connected in this perspective"
                ),
                suggested_ops=[RevisionOp(op_type="separate", target="sp-kitchen,sp-living")],
            ),
            VisualClaim(
                id="vc-02",
                element_ids=["d-entry"],
                claim_text=(
                    "Entry door d-entry swing appears tight against the exterior wall corner"
                ),
            ),
        ],
    )

    report = validate_critique_grounding(critique, sample_plan, expected_screenshot_hash="a" * 64)
    assert report.is_grounded is True
    assert len(report.findings) == 0
    # Should not raise
    report.raise_if_ungrounded()


def test_ungrounded_element_id_is_rejected(sample_plan):
    """A critique citing hallucinated / nonexistent element IDs is flagged as ungrounded."""
    critique = VisualCritiqueFile(
        project="synthetic-bungalow",
        option="concept-compact",
        plan_version=1,
        author="agent:reviewer",
        screenshot_hash="b" * 64,
        claims=[
            VisualClaim(
                id="vc-bad-1",
                element_ids=["sp-nonexistent-pantry", "w-ghost-wall"],
                claim_text="Pantry window overlaps with ghost wall",
            )
        ],
    )

    report = validate_critique_grounding(critique, sample_plan)
    assert report.is_grounded is False
    assert len(report.findings) == 2
    assert "sp-nonexistent-pantry" in report.findings[0].issue
    assert "w-ghost-wall" in report.findings[1].issue

    with pytest.raises(GroundingError, match="sp-nonexistent-pantry"):
        report.raise_if_ungrounded()


def test_unsupported_measurable_claim_is_rejected(sample_plan):
    """Asserting unverified numerical measurements without evaluation metrics or ops is rejected."""
    critique = VisualCritiqueFile(
        project="synthetic-bungalow",
        option="concept-compact",
        plan_version=1,
        author="agent:reviewer",
        screenshot_hash="c" * 64,
        claims=[
            VisualClaim(
                id="vc-meas-1",
                element_ids=["sp-living"],
                claim_text="Living room measures 45.5 m² which exceeds the guideline",
                suggested_ops=[],  # no structured op or metric citation
            )
        ],
    )

    report = validate_critique_grounding(critique, sample_plan)
    assert report.is_grounded is False
    assert any("Measurable quantity '45.5 m²'" in f.issue for f in report.findings)


def test_measurable_claim_with_eval_metric_is_accepted(sample_plan):
    """A measurable claim citing an evaluation report metric passes grounding."""
    actor = Actor(kind="agent", id="agent:gemini")
    prov = Provenance(created_at="2026-10-18T00:00:00Z", created_by=actor, method="test")
    eval_rep = EvaluationReport(
        id="eval-compact-1",
        plan_ref=ArtifactRef(
            kind=ArtifactKind.PLAN, id="concept-compact", version=1, sha256="0" * 64
        ),
        provenance=prov,
        evaluators=[
            EvaluatorRun(name="geometry", version="0.1.0", status=EvaluatorRunStatus.RAN)
        ],
        compliance={"status": "conceptual_best_practice_only"},
        metrics=[
            MetricClaim(
                evaluator="eval:geometry",
                evaluator_version="0.1.0",
                metric="gross_internal_area_m2",
                value=45.5,
                unit="m²",
                status=ClaimStatus.MEASURED,
                method="geometry_polygon_sum",
            )
        ],
    )

    critique = VisualCritiqueFile(
        project="synthetic-bungalow",
        option="concept-compact",
        plan_version=1,
        author="agent:reviewer",
        screenshot_hash="d" * 64,
        claims=[
            VisualClaim(
                id="vc-meas-2",
                element_ids=["sp-living"],
                claim_text=(
                    "Reported gross_internal_area_m2 of 45.5 m² "
                    "leaves room for a larger entry foyer"
                ),
            )
        ],
    )

    report = validate_critique_grounding(critique, sample_plan, evaluation=eval_rep)
    assert report.is_grounded is True


def _one_claim(element_ids: list[str], target: str | None = None) -> VisualCritiqueFile:
    ops = [RevisionOp(op_type="rethink", target=target)] if target else []
    return VisualCritiqueFile(
        project="synthetic-bungalow",
        option="concept-compact",
        plan_version=1,
        author="agent:reviewer",
        screenshot_hash="c" * 64,
        claims=[
            VisualClaim(
                id="vc-01", element_ids=element_ids, claim_text="Feels cramped", suggested_ops=ops
            )
        ],
    )


def test_visual_and_written_critiques_share_one_set_of_ids(sample_plan):
    """A space's program item, zone and level references are citable in both kinds (ADR 0027)."""
    space = sample_plan.model.spaces[1].model_copy(
        update={"program_item_id": "pi-kitchen", "zone_id": "z-day"}
    )
    model = sample_plan.model.model_copy(update={"spaces": [sample_plan.model.spaces[0], space]})
    plan = sample_plan.model_copy(update={"model": model})
    assert collect_plan_element_ids(plan) == CANONICAL_PLAN_TARGETS | collect_canonical_ids(plan)
    report = validate_critique_grounding(_one_claim(["pi-kitchen", "z-day", "lvl-ground"]), plan)
    assert report.is_grounded, report.findings
    assert validate_cited_ids(["pi-kitchen", "z-day", "lvl-ground"], plan) == []


def test_a_revision_op_may_not_target_a_zone_the_plan_lacks(sample_plan):
    """Zone targets used to pass on their ``z-`` prefix alone."""
    report = validate_critique_grounding(_one_claim(["sp-kitchen"], "z-imaginary"), sample_plan)
    assert [(f.element_id, f.issue) for f in report.findings] == [
        ("z-imaginary", "Suggested revision op 'rethink' targets nonexistent element 'z-imaginary'")
    ]
