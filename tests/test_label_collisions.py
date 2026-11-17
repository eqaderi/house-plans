"""Colliding room labels are a Finding of the Evaluation, from the drawing's own layout (#34)."""

from __future__ import annotations

from examples.usability.scenarios import flat_site, rectangle, space
from house_ai.constants.evaluations import PLAN_GATE_BLOCKING_CODES
from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.geometry import Polygon2D
from house_ai.domain.model import HouseModel, Level
from house_ai.domain.program import Strength
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.drawing import LabelCollisionEvaluator


def _house(*spaces: dict) -> HouseModel:
    return HouseModel.model_validate(
        dict(
            id="labels",
            name="Label twins",
            coordinate_system_id="local",
            levels=[dict(id="ground", name="Ground", elevation_m=0, floor_to_floor_m=3)],
            spaces=list(spaces),
        )
    )


def _evaluate(model: HouseModel, site=None):
    return LabelCollisionEvaluator().evaluate(EvaluationContext(model, site, None, None))


def _collisions(result) -> list[set[str]]:
    return [set(v.subject_ids) for v in result.violations if v.code == "label_collision"]


def test_two_closets_whose_labels_overlap_on_the_drawing_are_a_measured_soft_finding():
    # Drawing extent: spaces x -2.5..13.5 m (16 m) -> 488 px / 16 m = 30.5 px/m. The closet
    # label anchors are 0.5 m = 15.25 px apart, and each one's "1.00 × 0.50" line is about
    # 42 px wide: the labels overlap.
    model = _house(
        space("sp-living", "living", (0, 0, 6, 5)),
        space("sp-closet-a", "storage", (10, 0, 10.5, 1)),
        space("sp-closet-b", "storage", (10.5, 0, 11, 1)),
    )
    result = _evaluate(model)
    assert _collisions(result) == [{"sp-closet-a", "sp-closet-b"}]
    (finding,) = result.violations
    assert finding.status is ClaimStatus.MEASURED
    assert finding.method == "drawing_label_layout"
    # A drawing defect never closes the plan gate (ADR 0024).
    assert finding.strength is Strength.SOFT
    assert finding.code not in PLAN_GATE_BLOCKING_CODES
    count = next(m for m in result.metrics if m.metric == "label_collisions")
    assert (count.value, count.status) == (1, ClaimStatus.MEASURED)


def test_labels_far_apart_on_the_drawing_do_not_collide():
    model = _house(
        space("sp-bed-a", "bedroom", (0, 0, 4, 3)),
        space("sp-bed-b", "bedroom", (4, 0, 8, 3)),
    )
    result = _evaluate(model)
    assert _collisions(result) == []
    assert next(m for m in result.metrics if m.metric == "label_collisions").value == 0


def test_the_collision_check_uses_the_drawing_scale_with_the_site_boundary_shown():
    # Without a site the two bedrooms are drawn at 488 / 13 m = 37.5 px/m: anchors 150 px
    # apart. A 100 m parcel shrinks the drawing to 488 / 105 m = 4.65 px/m: anchors 18.6 px
    # apart, and each "4.00 × 3.00" line is about 42 px wide.
    model = _house(
        space("sp-bed-a", "bedroom", (0, 0, 4, 3)),
        space("sp-bed-b", "bedroom", (4, 0, 8, 3)),
    )
    site = flat_site()
    site = site.model_copy(
        update={"boundary": Polygon2D.model_validate(rectangle(-50, -50, 50, 50))}
    )
    assert _collisions(_evaluate(model, site)) == [{"sp-bed-a", "sp-bed-b"}]


def test_labels_on_different_levels_never_collide():
    # The closets of the first test, one on each Level: each Level is its own panel.
    model = _house(
        space("sp-living", "living", (0, 0, 6, 5)),
        space("sp-closet-a", "storage", (10, 0, 10.5, 1)),
        space("sp-closet-b", "storage", (10.5, 0, 11, 1), level="upper"),
    )
    model.levels.append(Level(id="upper", name="Upper", elevation_m=3, floor_to_floor_m=3))
    assert _collisions(_evaluate(model)) == []
