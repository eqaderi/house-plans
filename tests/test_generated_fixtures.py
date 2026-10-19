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
from house_ai.orchestration.plans import PlanService

from .conftest import AGENT
from .test_plan_workflow import _approve_site_and_program, _load


@pytest.fixture(scope="module")
def compact(tmp_path_factory):
    store = _load(tmp_path_factory.mktemp("fixtures"))
    _approve_site_and_program(store)
    svc = PlanService(store)
    (opt,) = svc.generate(AGENT, strategies=["compact"], exploratory=True).generated
    return opt.candidate.plan.model, svc.inputs(exploratory=True)


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
            assert space.boundary.to_shapely().covers(f.footprint_polygon().to_shapely())


def test_critics_measure_the_placed_fixtures(compact):
    model, inp = compact
    result = FurnitureUsabilityEvaluator().evaluate(
        EvaluationContext(model, inp.site, inp.program, None)
    )
    codes = {v.code for v in result.violations}
    assert "object_clearance_blocked" not in codes
    assert "kitchen_no_sampled_fit" not in codes
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
