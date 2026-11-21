"""Regressions from the Milestone D independent architectural review (synthetic only)."""

from __future__ import annotations

import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from house_ai.constants.evaluations import (
    METRIC_EXCAVATION_VOLUME,
    METRIC_EXTERIOR_DOOR_GROUND_DELTA,
    METRIC_FILL_VOLUME,
    METRIC_MAX_CUT,
    METRIC_MAX_FILL,
    VIOLATION_BLOCKING_PLAN_ISSUE,
    VIOLATION_ELEVATED_FLOOR_SUPPORT,
    VIOLATION_ELONGATED_ROOM,
    VIOLATION_REQUIRED_DAYLIGHT_NO_WINDOW,
    VIOLATION_TERRAIN_COVERAGE_INCOMPLETE,
)
from house_ai.domain.integrity import check_model, errors
from house_ai.domain.model import OpeningKind, SlabKind, WallKind
from house_ai.domain.records import Issue, Severity
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.evaluators import ProgramEvaluator, SiteEvaluator
from house_ai.generation.frame import design_frame
from house_ai.generation.massing import FLOOR_TO_FLOOR_M

from .test_plan_generation import HILLSIDE, _load, all_hillside_candidates


@pytest.fixture(scope="module")
def concepts():
    site, program = _load(HILLSIDE)
    candidates = all_hillside_candidates()
    return site, program, {c.strategy: c.plan for c in candidates if c.plan is not None}


def test_hybrid_reuses_entry_footprint_and_reports_cut_void_tradeoff(concepts):
    site, program, plans = concepts
    hybrid = plans["split_walkout"]
    assert errors(check_model(hybrid.model, site, program)) == []
    assert len(hybrid.model.levels) == 3
    assert len(hybrid.model.stairs) == 2
    entry = hybrid.model.level("lv-entry").elevation_m
    assert any(lvl.elevation_m == entry - FLOOR_TO_FLOOR_M for lvl in hybrid.model.levels)
    metrics = {}
    for strategy in ("split_level", "split_walkout", "compact"):
        result = SiteEvaluator().evaluate(
            EvaluationContext(plans[strategy].model, site, program, None)
        )
        metrics[strategy] = {m.metric: m.value for m in result.metrics}
    # A concrete comparison, not a universal optimization objective.
    assert metrics["split_walkout"][METRIC_FILL_VOLUME] < metrics["split_level"][METRIC_FILL_VOLUME]
    assert metrics["split_walkout"][METRIC_EXCAVATION_VOLUME] > 0
    # Since S8 the joint level solve has tied optima (DEC-04 keeps earthworks out of the
    # objective), so a strict max-fill ordering compares an arbitrary, platform-dependent
    # tie-break. Require a reported, positive void under both: each steps over the fall.
    assert metrics["split_walkout"][METRIC_MAX_FILL] > 0
    assert metrics["split_level"][METRIC_MAX_FILL] > 0
    assert sum(s.area_m2 for s in hybrid.model.spaces) > sum(
        s.area_m2 for s in plans["compact"].model.spaces
    )  # hybrid's additional area is a real disadvantage


def test_required_daylight_gap_is_visible_without_claiming_daylight_simulation(concepts):
    site, program, plans = concepts
    model = plans["compact"].model
    # A study with no exterior window, whatever the layout gave it.
    model = model.model_copy(
        update={
            "openings": [
                o
                for o in model.openings
                if not ("sp-study-1" in o.connects and o.kind.value == "window")
            ]
        }
    )
    result = ProgramEvaluator().evaluate(EvaluationContext(model, site, program, None))
    gap = next(
        v
        for v in result.violations
        if "sp-study-1" in v.subject_ids and v.code == VIOLATION_REQUIRED_DAYLIGHT_NO_WINDOW
    )
    assert gap.strength.value == "soft"
    assert gap.status.value == "measured"
    assert "not checked" in gap.message
    assert (
        next(
            m.value
            for m in result.metrics
            if m.metric == "required_daylight_exterior_windows" and "sp-study-1" in m.subject_ids
        )
        == 0
    )


def test_elevated_support_and_existing_ground_access_are_explicit(concepts):
    site, program, plans = concepts
    result = SiteEvaluator().evaluate(EvaluationContext(plans["linear"].model, site, program, None))
    support = next(v for v in result.violations if v.code == VIOLATION_ELEVATED_FLOOR_SUPPORT)
    assert support.status.value == "inferred"
    assert "not specified engineered fill" in support.message
    # One inferred ground-delta claim for each exterior door: front door and garage door.
    model = plans["linear"].model
    exterior_doors = {o.id for o in model.openings if o.is_passable and "exterior" in o.connects}
    assert exterior_doors == {"d-front-entry-ext", "d-garage-garage-ext"}
    deltas = [m for m in result.metrics if m.metric == METRIC_EXTERIOR_DOOR_GROUND_DELTA]
    assert sorted(i for m in deltas for i in m.subject_ids) == sorted(exterior_doors)
    assert all(m.status.value == "inferred" and m.value is not None for m in deltas)


def test_terrain_wholly_outside_building_is_unknown_not_zero(concepts):
    site, program, plans = concepts
    terrain = site.terrain.model_copy(
        update={
            "surface": None,
            "spot_elevations": [
                s.model_copy(update={"xy": (s.xy[0] + 1000, s.xy[1] + 1000)})
                for s in site.terrain.spot_elevations
            ],
        }
    )
    away = site.model_copy(update={"terrain": terrain})
    result = SiteEvaluator().evaluate(
        EvaluationContext(plans["linear"].model, away, program, None)
    )
    for m in result.metrics:
        if m.metric in {
            METRIC_EXCAVATION_VOLUME,
            METRIC_FILL_VOLUME,
            METRIC_MAX_CUT,
            METRIC_MAX_FILL,
        }:
            assert m.value is None and m.status.value == "not_checked"
    assert any(v.code == VIOLATION_TERRAIN_COVERAGE_INCOMPLETE for v in result.violations)


def test_upper_floor_has_stair_flight_openings_and_retains_a_landing(concepts):
    _, _, plans = concepts
    for plan in plans.values():
        for st in plan.model.stairs:
            floors = unary_union(
                [
                    s.boundary.to_shapely()
                    for s in plan.model.slabs
                    if s.kind is SlabKind.FLOOR and s.level_id == st.to_level_id
                ]
            )
            flight = st.footprint.to_shapely()
            assert flight.difference(floors).area > flight.area / 2
            top = plan.model.space(st.top_space_id).boundary.to_shapely()
            assert top.intersection(floors).area > 1  # landing remains, not a floorless room


def test_windows_use_distinct_selected_facades_and_garages_face_road(concepts):
    site, _, plans = concepts
    frame = design_frame(site)
    for plan in plans.values():
        for sid in {s.id for s in plan.model.spaces}:
            windows = [
                o for o in plan.model.openings if o.kind is OpeningKind.WINDOW and sid in o.connects
            ]
            assert len({o.host_wall_id for o in windows}) == len(windows)
        # The one vehicle door lies on the garage's road-side edge: in the design frame the
        # road runs along v = 0, so that edge is the garage's lowest v.
        (o,) = [
            o
            for o in plan.model.openings
            if o.id.startswith("d-garage") and "exterior" in o.connects
        ]
        (garage_id,) = set(o.connects) - {"exterior"}
        garage = plan.model.space(garage_id)
        road_v = min(frame.to_design(p)[1] for p in garage.boundary.outer)
        w = plan.model.wall(o.host_wall_id)
        a, b = frame.to_design(w.start), frame.to_design(w.end)
        assert a[1] == pytest.approx(road_v, abs=1e-5), plan.strategy
        assert b[1] == pytest.approx(road_v, abs=1e-5), plan.strategy
        assert w.kind is WallKind.EXTERIOR


def test_open_blocking_plan_issue_is_an_integrity_failure(concepts):
    _, _, plans = concepts
    plan = plans["linear"].model.model_copy(deep=True)
    plan.issues.append(
        Issue(id="iss-access", title="Garage vehicle access missing", severity=Severity.BLOCKING)
    )
    assert any(f.code == VIOLATION_BLOCKING_PLAN_ISSUE for f in errors(check_model(plan)))


def test_proportion_warning_works_in_both_axes(concepts):
    site, program, plans = concepts
    from house_ai.domain.geometry import Polygon2D
    from house_ai.domain.program import SpaceFunction

    model = plans["linear"].model.model_copy(deep=True)
    sp = next(s for s in model.spaces if s.function is SpaceFunction.STUDY)
    for width, depth in ((2, 8), (8, 2)):
        sp.boundary = Polygon2D(outer=list(box(0, 0, width, depth).exterior.coords)[:-1])
        result = ProgramEvaluator().evaluate(EvaluationContext(model, site, program, None))
        assert any(
            v.code == VIOLATION_ELONGATED_ROOM and sp.id in v.subject_ids for v in result.violations
        )
