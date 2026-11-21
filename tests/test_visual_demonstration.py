"""Tests for the synthetic hillside visual plan review demonstration (Stage S5, Task S5-12)."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from house_ai.domain.model import Opening, OpeningKind, WallKind
from house_ai.domain.plan import PlanVersion
from house_ai.domain.revision_ops import RevisionOpsFile
from house_ai.domain.site import Site
from house_ai.domain.visual_critique import VisualCritiqueFile
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.usability import DaylightOpportunityEvaluator
from house_ai.storage.hashing import load_document
from house_ai.validation.semantic_map import compare_image_bytes

from .test_rasterize import png_pixels, png_size

REPO = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO / "examples" / "reviewer" / "demonstration"
HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"
#: The seeded defect and its hand-edited move, as README.md documents them.
SEEDED_WINDOW, RETAINING_WALL, MOVED_TO = "win-buried-001", "w-down-300-001", "w-down-300-013"


def _base() -> tuple[PlanVersion, Site]:
    plan = load_document(HILLSIDE / "concepts/concept-split-walkout/exploratory/plan.json")
    site = load_document(HILLSIDE / "site.yaml")
    return PlanVersion.model_validate(copy.deepcopy(plan)), Site.model_validate(copy.deepcopy(site))


def _with_window_on(plan: PlanVersion, wall_id: str) -> PlanVersion:
    seeded = plan.model_copy(deep=True)
    seeded.model.openings.append(
        Opening(
            id=SEEDED_WINDOW,
            host_wall_id=wall_id,
            kind=OpeningKind.WINDOW,
            offset_m=1.0,
            width_m=1.2,
            height_m=1.2,
            connects=("sp-study", "exterior"),
        )
    )
    return seeded


def _buried(plan: PlanVersion, site: Site) -> list[list[str]]:
    """Subjects of the Evaluation's window_buried findings that name the seeded window."""
    ctx = EvaluationContext(plan.model, site, None, None)
    result = DaylightOpportunityEvaluator().evaluate(ctx)
    return [
        v.subject_ids
        for v in result.violations
        if v.code == "window_buried" and SEEDED_WINDOW in v.subject_ids
    ]


def _svg_elements(name: str) -> list[str]:
    return re.findall(r"<[^>]*>[^<]*", (DEMO_DIR / name).read_text("utf-8"))


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
    assert claim.element_ids == [SEEDED_WINDOW, RETAINING_WALL]
    assert claim.status.value == "ai_judgment"
    assert [str(op) for op in claim.suggested_ops] == ["rethink:sp-study-1"]

    # Grounding: the wall and the room the claim and its operation name are in the plan
    # option, and the wall is a retaining wall; only the window is the seeded one.
    base, _ = _base()
    walls = {w.id: w for w in base.model.walls}
    assert walls[RETAINING_WALL].kind is WallKind.RETAINING
    assert walls[MOVED_TO].kind is not WallKind.RETAINING
    assert "sp-study-1" in {s.id for s in base.model.spaces}
    assert SEEDED_WINDOW not in {o.id for o in base.model.openings}

    # The critique names the screenshot it judged, and the revision file carries its operation.
    assert critique.screenshot_hash == hashlib.sha256(
        (DEMO_DIR / "before.png").read_bytes()
    ).hexdigest()
    ops = RevisionOpsFile.model_validate_json((DEMO_DIR / "revision_ops.json").read_text("utf-8"))
    assert (ops.option, ops.plan_version) == (critique.option, critique.plan_version)
    assert ops.operations == claim.suggested_ops


def test_the_seeded_window_is_buried_before_and_not_after():
    """The Evaluation measures the critique's defect in the seeded plan, and not once the
    window is moved to the wall the after drawing shows."""
    base, site = _base()
    assert _buried(base, site) == []
    before = _buried(_with_window_on(base, RETAINING_WALL), site)
    assert before == [[SEEDED_WINDOW, RETAINING_WALL, "sp-study"]]
    assert _buried(_with_window_on(base, MOVED_TO), site) == []


def test_after_drawing_differs_from_before_only_by_the_version_and_one_window():
    before, after = _svg_elements("before.svg"), _svg_elements("after.svg")
    assert len(before) == len(after)
    changed = [i for i, (b, a) in enumerate(zip(before, after, strict=True)) if b != a]
    title, *window = changed
    assert "concept-split-walkout v1 " in before[title]
    assert after[title] == before[title].replace(" v1 ", " v2 ")
    # One window symbol: its white sash and three glazing lines, drawn consecutively.
    assert window == list(range(window[0], window[0] + 4))
    assert 'fill="#ffffff"' in before[window[0]] and 'fill="#ffffff"' in after[window[0]]
    for i in window[1:]:
        assert 'stroke="#2a6fb0"' in before[i] and 'stroke="#2a6fb0"' in after[i]


def test_demonstration_screenshots_valid_and_distinct():
    """Before and after screenshots are 800 x 600 PNGs differing in a few pixels only."""
    before_png = (DEMO_DIR / "before.png").read_bytes()
    after_png = (DEMO_DIR / "after.png").read_bytes()
    assert png_size(before_png) == png_size(after_png) == (800, 600)

    before, after = png_pixels(before_png), png_pixels(after_png)
    changed = sum(
        a != b
        for row_b, row_a in zip(before, after, strict=True)
        for a, b in zip(row_a, row_b, strict=True)
    )
    # The version in the title and one small window symbol: far under 0.1 % of the image.
    assert 0 < changed < 800 * 600 // 1000
    assert not compare_image_bytes(before_png, after_png, max_diff_ratio=0.0)[0]
