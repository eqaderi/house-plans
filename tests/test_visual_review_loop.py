"""Tests for visual review loop and fix verification (Stage S5, Tasks S5-09 and S5-10)."""

from __future__ import annotations

import pytest

from house_ai.domain.geometry import Polygon2D
from house_ai.domain.model import (
    HouseModel,
    Level,
    Opening,
    OpeningKind,
    Space,
    Wall,
    WallKind,
)
from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import Actor, Provenance
from house_ai.domain.revision_ops import RevisionOp
from house_ai.domain.visual_critique import VisualClaim, VisualCritiqueFile
from house_ai.orchestration.visual_review import (
    VisualFixVerificationError,
    verify_visual_critique_fixes,
)


@pytest.fixture
def plan_with_buried_window() -> PlanVersion:
    actor = Actor(kind="agent", id="agent:gemini")
    prov = Provenance(created_at="2026-10-18T00:00:00Z", created_by=actor, method="test")

    model = HouseModel(
        id="model-hillside-v1",
        name="Hillside Model v1",
        coordinate_system_id="local",
        levels=[Level(id="lvl-0", name="Ground", elevation_m=0.0)],
        spaces=[
            Space(
                id="sp-living",
                name="Living Room",
                function="living",
                level_id="lvl-0",
                boundary=Polygon2D(outer=[[0, 0], [6, 0], [6, 5], [0, 5]]),
            )
        ],
        walls=[
            Wall(
                id="w-ret-1",
                level_id="lvl-0",
                kind=WallKind.RETAINING,
                start=[0, 5],
                end=[6, 5],
                thickness_m=0.4,
                height_m=2.8,
            ),
            Wall(
                id="w-ext-front",
                level_id="lvl-0",
                kind=WallKind.EXTERIOR,
                start=[0, 0],
                end=[6, 0],
                thickness_m=0.3,
                height_m=2.8,
            ),
        ],
        openings=[
            Opening(
                id="win-buried-1",
                host_wall_id="w-ret-1",  # Buried on retaining wall
                kind=OpeningKind.WINDOW,
                offset_m=2.0,
                width_m=1.5,
                height_m=1.2,
                connects=("sp-living", "exterior"),
            )
        ],
    )

    return PlanVersion(
        option_id="concept-hillside",
        label="Hillside",
        strategy="split_walkout",
        provenance=prov,
        model=model,
    )


def test_verified_fix_passes(plan_with_buried_window):
    """When a revision removes or relocates the defective opening, verification succeeds."""
    critique = VisualCritiqueFile(
        project="synthetic-hillside",
        option="concept-hillside",
        plan_version=1,
        author="agent:reviewer",
        screenshot_hash="f" * 64,
        claims=[
            VisualClaim(
                id="vc-01",
                element_ids=["win-buried-1", "w-ret-1"],
                claim_text="Window win-buried-1 is hosted on retaining wall w-ret-1 facing earth.",
                suggested_ops=[RevisionOp(op_type="separate", target="win-buried-1,w-ret-1")],
            )
        ],
    )

    # Construct revised plan where window is moved to the exterior front wall
    revised_model = plan_with_buried_window.model.model_copy(deep=True)
    revised_model.openings = [
        Opening(
            id="win-relocated-1",
            host_wall_id="w-ext-front",
            kind=OpeningKind.WINDOW,
            offset_m=2.0,
            width_m=1.5,
            height_m=1.2,
            connects=("sp-living", "exterior"),
        )
    ]

    revised_plan = PlanVersion(
        option_id="concept-hillside",
        label="Hillside v2",
        strategy="split_walkout",
        provenance=plan_with_buried_window.provenance,
        model=revised_model,
    )

    report = verify_visual_critique_fixes(plan_with_buried_window, revised_plan, critique)
    assert report.all_resolved is True
    assert len(report.results) == 1
    assert report.results[0].is_resolved is True
    assert critique.verified is True
    # Should not raise
    report.raise_if_unverified()


def test_fake_fix_rejected_when_defect_still_present(plan_with_buried_window):
    """When a revision claims to fix an issue but the defect is still present, it is rejected."""
    critique = VisualCritiqueFile(
        project="synthetic-hillside",
        option="concept-hillside",
        plan_version=1,
        author="agent:reviewer",
        screenshot_hash="f" * 64,
        claims=[
            VisualClaim(
                id="vc-01",
                element_ids=["win-buried-1", "w-ret-1"],
                claim_text="Window win-buried-1 is on retaining wall w-ret-1.",
                suggested_ops=[RevisionOp(op_type="separate", target="win-buried-1,w-ret-1")],
            )
        ],
    )

    # Fake revision where buried window is still on retaining wall
    fake_revised_model = plan_with_buried_window.model.model_copy(deep=True)
    fake_revised_plan = PlanVersion(
        option_id="concept-hillside",
        label="Hillside v2 (fake)",
        strategy="split_walkout",
        provenance=plan_with_buried_window.provenance,
        model=fake_revised_model,
    )

    report = verify_visual_critique_fixes(plan_with_buried_window, fake_revised_plan, critique)
    assert report.all_resolved is False
    assert report.results[0].is_resolved is False
    assert "Defect still present" in report.results[0].evidence

    with pytest.raises(VisualFixVerificationError, match="could not be verified"):
        report.raise_if_unverified()
