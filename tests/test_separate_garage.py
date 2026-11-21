"""S10-19 (ISS-36, DEC-12): the garage is a separate road-level volume that holds its cars."""

from __future__ import annotations

import math

import pytest

from house_ai.domain.integrity import check_model, errors
from house_ai.domain.model import Operation
from house_ai.domain.program import SpaceFunction as S
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.usability import FurnitureUsabilityEvaluator
from house_ai.generation.rooms import garage_dims_dm

STRATEGIES = ["compact", "split_level", "two_wing"]


@pytest.fixture
def concepts(hillside):
    """The shared exploratory synthetic-hillside plans (conftest `hillside`), copied per test."""
    return hillside.models(STRATEGIES), hillside.inputs()


def test_garage_size_follows_the_program_cars(concepts):
    _, inp = concepts
    # Two typical cars: 0.9 (house side) + 1.8 + 0.6 + 1.8 + 0.6 + 0.3 walls = 6.0 m wide;
    # 4.5 + 0.9 front + 0.3 back + 0.3 walls = 6.0 m deep.
    assert len(inp.program.usability.vehicles) == 2
    assert garage_dims_dm(inp.program) == (60, 60)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_separate_garage_holds_its_cars_beside_the_house(concepts, strategy):
    models, inp = concepts
    assert strategy in models, "split concepts stay feasible with a separate garage"
    model = models[strategy]
    assert not errors(check_model(model, inp.site, inp.program))
    (garage,) = [s for s in model.spaces if s.function is S.GARAGE]
    ring = list(garage.boundary.to_shapely().minimum_rotated_rectangle.exterior.coords)
    sides = sorted(math.dist(ring[i], ring[i + 1]) for i in range(2))
    depth, width = garage_dims_dm(inp.program)
    assert sides == pytest.approx(sorted((depth / 10, width / 10)), abs=1e-6)
    doors = [o for o in model.openings if garage.id in o.connects]
    vehicle = [o for o in doors if "exterior" in o.connects]
    person = [o for o in doors if "exterior" not in o.connects]
    assert len(vehicle) == 1 and vehicle[0].operation is Operation.SLIDING
    assert len(person) == 1  # into the house
    result = FurnitureUsabilityEvaluator().evaluate(
        EvaluationContext(model, inp.site, inp.program, None)
    )
    fit = next(m for m in result.metrics if m.metric == "garage_sampled_fit")
    assert fit.value is True
