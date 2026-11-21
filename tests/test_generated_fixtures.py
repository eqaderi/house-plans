"""S10-08/S10-09 (ISS-30): generated kitchens and wet rooms carry usable fixtures."""

from __future__ import annotations

import math

import pytest

from house_ai.domain.integrity import check_model, errors
from house_ai.domain.model import HouseModel
from house_ai.domain.program import SpaceFunction as S
from house_ai.domain.usability_templates import TEMPLATES
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.usability import FurnitureUsabilityEvaluator
from house_ai.generation.fixtures import FIXTURE_SETS, layout_fixtures

# DEC-13 (ISS-37): support linear, opposite-wall, and L-shaped fixture arrangements
# with approved program areas and existing fixture clearances unchanged.


@pytest.fixture(scope="module")
def compact(hillside):
    """The compact plan option on synthetic-hillside (solved once per worker, a copy)."""
    plan = hillside.option("compact").candidate.plan
    assert plan is not None
    return plan.model, hillside.inputs()


def _room_angle(space) -> float:
    """The direction of a room's first edge, in degrees: the room's own frame."""
    (x0, y0), (x1, y1) = space.boundary.outer[:2]
    return math.degrees(math.atan2(y1 - y0, x1 - x0))


def _rotations_in_room(model, space_id: str) -> list[int]:
    """Each fixture's rotation in its room's frame, in whole degrees modulo 360."""
    space = next(s for s in model.spaces if s.id == space_id)
    fixtures = sorted((f for f in model.fixtures if f.space_id == space_id), key=lambda f: f.id)
    return [round(f.rotation_deg - _room_angle(space)) % 360 for f in fixtures]


def test_kitchens_and_wet_rooms_get_their_template_sets(compact):
    model, inp = compact
    assert not errors(check_model(model, inp.site, inp.program))
    for space in model.spaces:
        expected = FIXTURE_SETS.get(space.function)
        if expected is None:
            continue
        placed = [f for f in model.fixtures if f.space_id == space.id]
        assert sorted(f.fixture_type for f in placed) == sorted(
            t.replace("-", "_") for t in expected
        ), space.id
        for f in placed:
            t = TEMPLATES[f.fixture_type.replace("_", "-")]
            assert (f.width_m, f.depth_m) == (t.width.value, t.depth.value)
            # Fronts face into the room: rotation is a multiple of 90° in the room frame.
            turn = (f.rotation_deg - _room_angle(space)) % 90
            assert min(turn, 90 - turn) < 1e-3, (f.id, f.rotation_deg)
            assert space.boundary.to_shapely().covers(f.footprint_polygon().to_shapely())


def test_critics_measure_the_placed_fixtures(compact):
    model, inp = compact
    result = FurnitureUsabilityEvaluator().evaluate(
        EvaluationContext(model, inp.site, inp.program, None)
    )
    assert [v.code for v in result.violations] == []  # no blocked clearance, no missing fit
    kitchen = next(s for s in model.spaces if s.function is S.KITCHEN)
    run = next(
        m
        for m in result.metrics
        if m.metric == "kitchen_counter_run_m" and kitchen.id in m.subject_ids
    )
    assert run.value == pytest.approx(3.0) and run.status.value == "measured"
    # A placed design is checked as placed; no second sampled set is fitted.
    assert not [m for m in result.metrics if m.metric == "kitchen_sampled_fit"]


def test_a_room_that_cannot_hold_its_set_gets_none():
    """All or nothing: a 1.5 x 1.5 m bathroom cannot hold shower, basin and WC."""
    from examples.usability.scenarios import model as room_model

    doc = room_model(1.5, 1.5, "bathroom")
    house = HouseModel.model_validate(doc)
    fixtures, missed = layout_fixtures(house)
    assert fixtures == [] and missed == [house.spaces[0].id]
    # A 3.0 x 2.4 m bathroom can.
    house = HouseModel.model_validate(room_model(3.0, 2.4, "bathroom"))
    fixtures, missed = layout_fixtures(house)
    assert missed == [] and len(fixtures) == 3
    for f in fixtures:
        assert math.isclose(f.rotation_deg % 90, 0, abs_tol=1e-6)


def test_l_shaped_and_opposite_wall_arrangements_pass_and_clear(compact):
    """DEC-13: the ensuite puts its fixtures on three walls (shower on one, basin on the
    perpendicular wall: L-shaped; WC opposite the shower), bath 1 lines all three up on one
    wall, and every placement passes the integrity and clearance checks."""
    model, inp = compact
    assert [f.id for f in model.fixtures if f.space_id == "sp-bath-ensuite"] == [
        "fx-bath-ensuite-1", "fx-bath-ensuite-2", "fx-bath-ensuite-3",
    ]  # fmt: skip
    # shower, basin, WC: 0° (one wall), 270° (perpendicular: L), 180° (opposite the shower)
    assert _rotations_in_room(model, "sp-bath-ensuite") == [0, 270, 180]
    assert _rotations_in_room(model, "sp-bath-1") == [270, 270, 270]  # linear, one wall
    assert errors(check_model(model, inp.site, inp.program)) == []
    result = FurnitureUsabilityEvaluator().evaluate(
        EvaluationContext(model, inp.site, inp.program, None)
    )
    assert result.violations == []
