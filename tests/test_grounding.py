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
    """A space's space requirement, zone and level are citable in both kinds (ADR 0027)."""
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


# --- Measured values must match the evaluator (stated value vs MetricClaim.value) ---------


def _eval_report(*metrics: MetricClaim) -> EvaluationReport:
    actor = Actor(kind="agent", id="agent:gemini")
    prov = Provenance(created_at="2026-10-18T00:00:00Z", created_by=actor, method="test")
    return EvaluationReport(
        id="eval-compact-1",
        plan_ref=ArtifactRef(
            kind=ArtifactKind.PLAN, id="concept-compact", version=1, sha256="0" * 64
        ),
        provenance=prov,
        evaluators=[
            EvaluatorRun(name="geometry", version="0.1.0", status=EvaluatorRunStatus.RAN)
        ],
        compliance={"status": "conceptual_best_practice_only"},
        metrics=list(metrics),
    )


def _metric(name: str, value, unit: str | None, subjects: list[str] | None = None) -> MetricClaim:
    return MetricClaim(
        evaluator="eval:geometry",
        evaluator_version="0.1.0",
        metric=name,
        value=value,
        unit=unit,
        status=ClaimStatus.MEASURED if value is not None else ClaimStatus.NOT_CHECKED,
        method="geometry_polygon_sum",
        subject_ids=subjects or [],
    )


#: The sample plan's two spaces: 6 x 5 + 4 x 4 = 46.0 m² (centre-line polygons).
_GIA = _metric("gross_internal_area_m2", 46.0, "m2")


def _text_claim(text: str, ops: list[RevisionOp] | None = None) -> VisualCritiqueFile:
    return VisualCritiqueFile(
        project="synthetic-bungalow",
        option="concept-compact",
        plan_version=1,
        author="agent:reviewer",
        screenshot_hash="e" * 64,
        claims=[
            VisualClaim(
                id="vc-num", element_ids=["sp-living"], claim_text=text, suggested_ops=ops or []
            )
        ],
    )


def _issues(text: str, *metrics: MetricClaim, ops: list[RevisionOp] | None = None) -> list[str]:
    report = validate_critique_grounding(
        _text_claim(text, ops), _plan_for_text(), evaluation=_eval_report(*metrics)
    )
    assert report.is_grounded is (not report.findings)
    return [f.issue for f in report.findings]


def _plan_for_text() -> PlanVersion:
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
            )
        ],
    )
    return PlanVersion(option_id="concept-compact", label="Compact", provenance=prov, model=model)


def test_a_cited_metric_with_the_wrong_value_is_rejected():
    """Naming a metric used to license any number: 99 m² passed for a 46 m² plan."""
    assert _issues("gross_internal_area_m2 of 99 m² is too generous", _GIA) == [
        "Claim states gross_internal_area_m2 = 99 m2 but the evaluator measured 46.0 m2 "
        "(tolerance ±0.5, half a unit of the stated last digit)"
    ]


def test_a_cited_metric_with_the_right_value_passes_at_the_stated_precision():
    # 46.0 stated as 46, 46.0 and 46.00 all agree; 45.9 is 0.1 off at 0.05 precision.
    for text in ("gross_internal_area_m2 is 46 m²", "gross_internal_area_m2 = 46.0 m2"):
        assert _issues(text, _GIA) == [], text
    assert _issues("gross_internal_area_m2 is 45.9 sqm", _GIA) == [
        "Claim states gross_internal_area_m2 = 45.9 m2 but the evaluator measured 46.0 m2 "
        "(tolerance ±0.05, half a unit of the stated last digit)"
    ]
    # A metric stored at 3 decimals, read to 1: 12.346 rounds to 12.3.
    width = _metric("min_corridor_width_m", 12.346, "m")
    assert _issues("min_corridor_width_m of 12.3 m", width) == []
    assert _issues("min_corridor_width_m of 12.4 m", width) == [
        "Claim states min_corridor_width_m = 12.4 m but the evaluator measured 12.346 m "
        "(tolerance ±0.05, half a unit of the stated last digit)"
    ]


def test_suggested_ops_do_not_excuse_a_wrong_measured_value():
    ops = [RevisionOp(op_type="area", target="sp-living", value=20)]
    assert _issues("gross_internal_area_m2 of 99 m², shrink the living room", _GIA, ops=ops) == [
        "Claim states gross_internal_area_m2 = 99 m2 but the evaluator measured 46.0 m2 "
        "(tolerance ±0.5, half a unit of the stated last digit)"
    ]
    # A correct value plus a proposal target (20 m²) is fine: the target is the op's value.
    assert _issues("gross_internal_area_m2 of 46 m²; resize living to 20 m²", _GIA, ops=ops) == []


def test_a_second_unbacked_number_is_still_a_measurable_claim():
    assert _issues("gross_internal_area_m2 of 46 m² leaves a 3 m foyer", _GIA) == [
        "Measurable quantity '3 m' asserted without citing an evaluation metric "
        "or providing structured revision operations"
    ]


def test_wrong_unit_and_unchecked_metric_are_rejected():
    assert _issues("gross_internal_area_m2 of 46 m wide", _GIA) == [
        "Claim states gross_internal_area_m2 in m but the metric is in m2"
    ]
    unchecked = _metric("daylight_factor_pct", None, "%")
    assert _issues("daylight_factor_pct of 2 % is fine", unchecked) == [
        "Claim states daylight_factor_pct = 2 % but the evaluator did not measure it "
        "(status not_checked)"
    ]


def test_percent_against_a_unitless_ratio_and_per_space_metrics():
    ratio = _metric("circulation_ratio", 0.182, None)
    assert _issues("circulation_ratio of 18 % is high", ratio) == []
    assert _issues("circulation_ratio of 25 % is high", ratio) == [
        "Claim states circulation_ratio = 25 % but the evaluator measured 0.182 "
        "(tolerance ±0.5, half a unit of the stated last digit)"
    ]
    # Two spaces share a metric name; the claim's element_ids pick sp-living's value.
    per_space = (
        _metric("room_area_vs_target_pct", -12.5, "%", ["sp-living"]),
        _metric("room_area_vs_target_pct", 30.0, "%", ["sp-kitchen"]),
    )
    assert _issues("room_area_vs_target_pct is -12.5 % here", *per_space) == []
    assert _issues("room_area_vs_target_pct is 30 % here", *per_space) == [
        "Claim states room_area_vs_target_pct = 30 % but the evaluator measured -12.5 % "
        "(tolerance ±0.5, half a unit of the stated last digit)"
    ]


def test_bare_metres_and_percent_are_measurable_quantities():
    """`\\b` after `%` and the missing bare `m` let "3 m" and "35 %" claims slip through."""
    report = validate_critique_grounding(
        _text_claim("Corridor is 3 m wide and takes 35 % of the floor"), _plan_for_text()
    )
    assert [f.issue for f in report.findings] == [
        "Measurable quantity '3 m' asserted without citing an evaluation metric "
        "or providing structured revision operations",
        "Measurable quantity '35 %' asserted without citing an evaluation metric "
        "or providing structured revision operations",
    ]


def test_a_metric_name_inside_a_longer_name_is_not_a_citation():
    """`area_m2` is not cited by the text `gross_internal_area_m2`."""
    short = _metric("area_m2", 99.0, "m2")
    assert _issues("gross_internal_area_m2 of 46 m²", _GIA, short) == []


# --- Header checks: screenshot hash, plan version, empty element_ids ----------------------


def test_screenshot_hash_mismatch_is_rejected(sample_plan):
    report = validate_critique_grounding(
        _one_claim(["sp-kitchen"]), sample_plan, expected_screenshot_hash="f" * 64
    )
    assert [(f.claim_id, f.issue) for f in report.findings] == [
        ("screenshot_hash", "Screenshot hash mismatch: critique claims cccccccccccc, "
         "expected ffffffffffff")
    ]  # fmt: skip
    matching = validate_critique_grounding(
        _one_claim(["sp-kitchen"]), sample_plan, expected_screenshot_hash="c" * 64
    )
    assert matching.findings == []


def test_a_claim_without_element_ids_cannot_be_built_or_validated(sample_plan):
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="element_ids"):
        VisualClaim(id="vc-empty", element_ids=[], claim_text="Feels dark")
    # A file loaded without validation still gets the grounding check.
    claim = VisualClaim.model_construct(
        id="vc-empty", element_ids=[], claim_text="Feels dark", suggested_ops=[]
    )
    critique = _one_claim(["sp-kitchen"]).model_copy(update={"claims": [claim]})
    report = validate_critique_grounding(critique, sample_plan)
    assert [(f.claim_id, f.issue) for f in report.findings] == [
        ("vc-empty", "Claim contains no element_ids (must cite at least one canonical ID)")
    ]


@pytest.mark.xfail(
    strict=True,
    reason="product gap: PlanVersion has no `version` field, so the validator's plan-version "
    "check (hasattr(plan, 'version')) never runs; the stored version is only on the ArtifactRef",
)
def test_plan_version_mismatch_is_rejected(sample_plan):
    critique = _one_claim(["sp-kitchen"]).model_copy(update={"plan_version": 7})
    report = validate_critique_grounding(critique, sample_plan)
    assert not report.is_grounded
