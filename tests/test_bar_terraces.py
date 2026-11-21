"""S10-11 (ISS-33): bar strategies place the program's terrace outside its room."""

from __future__ import annotations

import math

import pytest
from shapely.geometry import LineString

from house_ai.domain.integrity import check_model, errors
from house_ai.domain.model import Operation, SlabKind, WallKind
from house_ai.domain.program import SpaceFunction as S
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.evaluators import ProgramEvaluator


@pytest.fixture
def concepts(hillside):
    """The shared exploratory synthetic-hillside plans (conftest `hillside`), copied per test."""
    return hillside.models(["compact", "two_wing"]), hillside.inputs()


@pytest.mark.parametrize("strategy", ["compact", "two_wing"])
def test_terrace_opens_from_its_room_with_parapets_and_no_roof(concepts, strategy):
    models, inp = concepts
    model = models[strategy]
    assert not errors(check_model(model, inp.site, inp.program))
    (terrace,) = [s for s in model.spaces if s.function is S.TERRACE]
    item = next(i for i in inp.program.space_requirements if i.function is S.TERRACE)
    assert terrace.program_item_id == item.id
    poly = terrace.boundary.to_shapely()
    # At least 1.5 m deep, and inside the buildable envelope.
    ring = list(poly.minimum_rotated_rectangle.exterior.coords)
    assert min(math.dist(ring[0], ring[1]), math.dist(ring[1], ring[2])) >= 1.5 - 1e-6
    envelope = inp.site.buildable_envelope.polygon.to_shapely()
    assert envelope.buffer(1e-6).covers(poly)
    # A sliding door from a room on the same level.
    (door,) = [o for o in model.openings if terrace.id in o.connects]
    host = model.space(next(c for c in door.connects if c != terrace.id))
    assert door.operation is Operation.SLIDING and host.level_id == terrace.level_id
    # Open edges are parapets; the edge to the house is its exterior wall.
    outline = poly.exterior.buffer(0.01)
    edges = [
        w
        for w in model.walls
        if w.level_id == terrace.level_id and outline.covers(LineString([w.start, w.end]))
    ]
    kinds = {w.kind for w in edges}
    assert WallKind.PARAPET in kinds and WallKind.EXTERIOR in kinds
    assert all(w.height_m == pytest.approx(1.0) for w in edges if w.kind is WallKind.PARAPET)
    # A terrace slab and no roof over it.
    slabs = [s for s in model.slabs if s.boundary.to_shapely().intersection(poly).area > 1e-3]
    assert {s.kind for s in slabs if s.level_id == terrace.level_id} == {SlabKind.TERRACE}


def test_placed_terrace_is_measured_and_its_relation_checked(concepts):
    models, inp = concepts
    result = ProgramEvaluator().evaluate(
        EvaluationContext(models["compact"], inp.site, inp.program, None)
    )
    item = next(i for i in inp.program.space_requirements if i.function is S.TERRACE)
    placed = next(
        m for m in result.metrics if m.metric == "outdoor_item_placed" and item.id in m.subject_ids
    )
    assert placed.value is True and placed.status.value == "measured"
