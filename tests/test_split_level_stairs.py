"""S10-05 (ISS-29, ADR 0023): flights between bars at different levels can be walked.

Generated on the synthetic steep hillside, every straight flight between bars must
keep the clear band above its pitch line free of slabs and walls, sit in an opening of
the higher floor, and belong to a stair volume on both levels.
"""

from __future__ import annotations

import pytest
from shapely.geometry import LineString

from house_ai.domain.model import StairKind, WallKind
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.usability import StairUsabilityEvaluator
from house_ai.orchestration.plans import PlanService

from .conftest import AGENT
from .test_plan_workflow import _approve_site_and_program, _load

#: Strategies whose bars join side by side: split_level by a row link, two_wing by an end link.
STRATEGIES = ["split_level", "two_wing"]
#: compact stacks its bars and joins them with a U-shaped flight (S10-06).
GENERATED = [*STRATEGIES, "compact"]


@pytest.fixture(scope="module")
def concepts(tmp_path_factory):
    store = _load(tmp_path_factory.mktemp("stairs"))
    _approve_site_and_program(store)
    svc = PlanService(store)
    out = svc.generate(AGENT, strategies=GENERATED, exploratory=True)
    inp = svc.inputs(exploratory=True)
    return {o.candidate.strategy: o.candidate.plan for o in out.generated}, inp


def _metric(result, name, subject):
    return next(m for m in result.metrics if m.metric == name and subject in m.subject_ids)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_split_level_flight_keeps_headroom_and_no_wall_in_its_band(concepts, strategy):
    plans, inp = concepts
    plan = plans[strategy]
    model = plan.model
    flights = [st for st in model.stairs if st.kind is StairKind.STRAIGHT]
    assert flights, f"{strategy} has no straight flight between bars"
    result = StairUsabilityEvaluator().evaluate(
        EvaluationContext(model, inp.site, inp.program, None)
    )
    codes = {v.code for v in result.violations}
    stair_faults = {"stair_low_headroom", "stair_wall_clash", "floor_connection_height_mismatch"}
    assert not codes & stair_faults
    for st in flights:
        low = model.level(st.from_level_id).elevation_m
        high = model.level(st.to_level_id).elevation_m
        # Ground truth: the rise is the elevation difference, in whole risers.
        total = st.riser_count * st.riser_height_m
        assert total == pytest.approx(high - low, abs=st.riser_count * 5e-5)
        # 2.0 m clear above the pitch line, with margin for 4-decimal riser heights.
        headroom = _metric(result, "stair_min_headroom_m", st.id)
        assert headroom.value >= 2.0 + 0.05
        assert _metric(result, "stair_wall_clashes", st.id).value == 0
        # The higher floor is open over the flight: no slab of that level covers the line.
        line = LineString(st.walking_line)
        upper_floor = [
            s for s in model.slabs if s.level_id == st.to_level_id and s.kind.value == "floor"
        ]
        for slab in upper_floor:
            assert line.intersection(slab.boundary.to_shapely()).length < 1e-6
        # The stair volume exists on both levels: stairwell below, stair hall above.
        names = {(s.level_id, s.name) for s in model.spaces if s.id.endswith(st.id[3:])}
        assert (st.from_level_id, "Stairwell") in names
        assert (st.to_level_id, "Stair hall") in names


def test_stairwell_walls_span_from_floor_to_the_slab_above(concepts):
    """Walls of the stairwell under the higher bar stop at that bar's floor slab; the stair
    hall's walls run from the lower roof slab's underside to the higher storey's wall head."""
    plans, _ = concepts
    model = plans["split_level"].model
    st = next(s for s in model.stairs if s.kind is StairKind.STRAIGHT)
    rise = model.level(st.to_level_id).elevation_m - model.level(st.from_level_id).elevation_m
    tagged = [
        w
        for w in model.walls
        if w.kind is not WallKind.PARAPET
        and (w.base_offset_m != 0.0 or abs(w.height_m - 2.8) > 1e-9)
    ]
    below = [w for w in tagged if w.level_id == st.from_level_id]
    above = [w for w in tagged if w.level_id == st.to_level_id]
    assert below and above
    assert {round(w.height_m, 4) for w in below} == {round(rise - 0.25, 4)}
    assert {round(w.base_offset_m, 4) for w in above} == {round(3.0 - 0.25 - rise, 4)}
    assert {round(w.base_offset_m + w.height_m, 4) for w in above} == {2.8}


def test_u_shaped_flight_has_a_measured_walking_line(concepts):
    """S10-06 (ISS-29, ADR 0023): the stacked U-shaped flight is laid out and measured."""
    plans, inp = concepts
    model = plans["compact"].model
    (st,) = [s for s in model.stairs if s.kind is StairKind.U_SHAPED]
    assert len(st.walking_line) == 4 and st.landing_segments == [1]
    rise = model.level(st.to_level_id).elevation_m - model.level(st.from_level_id).elevation_m
    heights = st.vertex_heights(rise)
    # Equal lanes: the half landing sits at half the rise, level across.
    assert heights[1] == pytest.approx(rise / 2) and heights[2] == pytest.approx(rise / 2)
    # Both flights meet the corridor-side line: bottom and top ends are side by side.
    (x0, y0), (x3, y3) = st.walking_line[0], st.walking_line[3]
    lane_gap = ((x3 - x0) ** 2 + (y3 - y0) ** 2) ** 0.5
    assert lane_gap == pytest.approx(
        ((st.walking_line[2][0] - st.walking_line[1][0]) ** 2
         + (st.walking_line[2][1] - st.walking_line[1][1]) ** 2) ** 0.5
    )  # fmt: skip
    result = StairUsabilityEvaluator().evaluate(
        EvaluationContext(model, inp.site, inp.program, None)
    )
    assert _metric(result, "stair_run_fit", st.id).value is True
    assert _metric(result, "stair_min_headroom_m", st.id).value >= 2.0 + 0.05
    assert _metric(result, "stair_wall_clashes", st.id).value == 0
    clear = [
        m for m in result.metrics if m.metric == "stair_landing_clear" and st.id in m.subject_ids
    ]
    assert len(clear) == 2 and all(m.value is True for m in clear)
