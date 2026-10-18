"""Tests for the synthetic hillside visual plan review demonstration (Stage S5, Task S5-12)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from house_ai.domain.visual_critique import VisualCritiqueFile
from house_ai.orchestration.visual_review import (
    VisualFixVerificationError,
    verify_visual_critique_fixes,
)
from house_ai.validation.semantic_map import compare_image_bytes

REPO = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO / "examples" / "reviewer" / "demonstration"


def test_demonstration_artifacts_exist():
    """Verify all required demonstration artifacts are present."""
    required_files = [
        "before.svg",
        "before.png",
        "visual_critique.json",
        "revision_ops.json",
        "after.svg",
        "after.png",
        "revision_report.json",
        "README.md",
    ]
    for filename in required_files:
        path = DEMO_DIR / filename
        assert path.is_file(), f"Missing demonstration artifact: {filename}"
        assert path.stat().st_size > 0, f"Empty artifact: {filename}"


def test_demonstration_critique_schema_and_grounding():
    """Verify visual_critique.json matches schema and is grounded in canonical elements."""
    critique_data = json.loads((DEMO_DIR / "visual_critique.json").read_text("utf-8"))
    critique = VisualCritiqueFile.model_validate(critique_data)

    assert critique.project == "synthetic-hillside"
    assert critique.option == "concept-split-walkout"
    assert len(critique.claims) == 1

    claim = critique.claims[0]
    assert claim.id == "vc-001"
    assert "win-buried-001" in claim.element_ids
    assert "w-down-300-001" in claim.element_ids
    assert claim.status.value == "ai_judgment"
    assert len(claim.suggested_ops) == 1
    assert claim.suggested_ops[0].op_type == "connect"


def test_demonstration_screenshots_valid_and_distinct():
    """Verify before and after screenshots are valid PNGs with visual differences."""
    before_png = (DEMO_DIR / "before.png").read_bytes()
    after_png = (DEMO_DIR / "after.png").read_bytes()

    png_hdr = b"\x89PNG\r\n\x1a\n"
    assert before_png.startswith(png_hdr)
    assert after_png.startswith(png_hdr)

    # Before and after must have visual difference
    is_match, ratio, msg = compare_image_bytes(before_png, after_png, max_diff_ratio=0.0)
    assert not is_match, "Before and after screenshots should differ"
    assert ratio > 0.0


def test_demonstration_revision_report_resolved():
    """Verify revision report confirms defect resolution."""
    report_data = json.loads((DEMO_DIR / "revision_report.json").read_text("utf-8"))
    assert report_data["all_resolved"] is True
    assert len(report_data["results"]) == 1
    assert report_data["results"][0]["is_resolved"] is True
    assert report_data["results"][0]["claim_id"] == "vc-001"


def test_demonstration_replay_detects_fake_fix():
    """Replaying critique against unrevised base plan strictly raises VisualFixVerificationError."""
    # Import the make_demonstration logic to reconstruct the models
    import sys

    sys.path.insert(0, str(DEMO_DIR))
    try:
        from examples.reviewer.demonstration.make_demonstration import (
            HILLSIDE,
            Opening,
            OpeningKind,
            PlanVersion,
            load_document,
        )
    finally:
        sys.path.pop(0)

    plan_dict = load_document(
        HILLSIDE / "concepts" / "concept-split-walkout" / "exploratory" / "plan.json"
    )
    base_plan = PlanVersion.model_validate(plan_dict)

    # Seed the defect
    base_plan.model.openings.append(
        Opening(
            id="win-buried-001",
            host_wall_id="w-down-300-001",
            kind=OpeningKind.WINDOW,
            offset_m=1.0,
            width_m=1.2,
            height_m=1.2,
            connects=("sp-study", "exterior"),
        )
    )

    critique_data = json.loads((DEMO_DIR / "visual_critique.json").read_text("utf-8"))
    critique = VisualCritiqueFile.model_validate(critique_data)

    # Attempt fake fix: comparing base_plan to itself
    fake_report = verify_visual_critique_fixes(base_plan, base_plan, critique)
    assert fake_report.all_resolved is False

    with pytest.raises(
        VisualFixVerificationError, match="Visual critique fixes could not be verified"
    ):
        fake_report.raise_if_unverified()
