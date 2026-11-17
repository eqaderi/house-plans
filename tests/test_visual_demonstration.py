"""Tests for the synthetic hillside visual plan review demonstration (Stage S5, Task S5-12)."""

from __future__ import annotations

import json
from pathlib import Path

from house_ai.domain.visual_critique import VisualCritiqueFile
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
    assert str(claim.suggested_ops[0]) == "rethink:sp-study-1"


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
