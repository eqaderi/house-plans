"""Ground-truth benchmark regressions, independent of any private project."""

from __future__ import annotations

import copy
import json
import math
import runpy
from pathlib import Path

import pytest
from pydantic import ValidationError

from house_ai.benchmarks.runner import category_table, main, run_fixture
from house_ai.domain.benchmark import AcceptanceCategory, BenchmarkFixture, ExpectedFinding
from house_ai.domain.integrity import check_model, errors
from house_ai.domain.terrain import elevation_at
from house_ai.geospatial.terrain import build_tin
from house_ai.storage.hashing import content_hash

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "examples/benchmarks"
PATHS = sorted((HERE / "fixtures").glob("*.json"))


def load(name):
    return BenchmarkFixture.model_validate_json((HERE / "fixtures" / f"{name}.json").read_text())


def test_generated_fixtures_are_current_and_no_unexpected_files():
    module = runpy.run_path(str(HERE / "make_fixtures.py"))
    documents = module["documents"]()
    assert set(documents) == {p.name for p in PATHS}
    for name, text in documents.items():
        assert (HERE / "fixtures" / name).read_text() == text


@pytest.mark.parametrize("path", PATHS, ids=lambda p: p.stem)
def test_every_current_observation_matches_declared_expectations(path):
    fixture = BenchmarkFixture.model_validate_json(path.read_text())
    results = run_fixture(fixture)
    assert len(results) == len(fixture.expectations)
    assert all(r.outcome in ("PASS", "NOT_CHECKED") for r in results), results
    for r in results:
        if r.outcome == "PASS":
            assert r.method
            assert r.claim_status


def test_steep_reference_analytical_ground_truth_and_local_frame():
    f = load("steep-reference")
    assert f.site.boundary.area_m2 == 600
    assert f.site.coordinates.local.origin == (0, 0, 0)
    assert f.site.coordinates.horizontal_crs.epsg is None
    assert not f.site.geometry_frame_verified
    spots = f.site.terrain.spot_elevations
    assert max(s.z_m for s in spots) - min(s.z_m for s in spots) == 12.5
    surface = build_tin(spots, []).surface
    assert elevation_at(surface, (9.6, 15.625)) == 6.25
    assert elevation_at(surface, (100, 100)) is None
    result = next(r for r in run_fixture(f) if r.check == "slope")
    assert result.observed == pytest.approx(40, abs=1e-10)
    assert result.claim_status == "measured"


@pytest.mark.parametrize("name,front,rear", [("road-high", 15, 0), ("road-low", 0, 15)])
def test_opposite_road_elevation_scenarios(name, front, rear):
    points = {s.id: s.z_m for s in load(name).site.terrain.spot_elevations}
    assert points["spot-sw"] == front
    assert points["spot-nw"] == rear


def test_slope_directions_and_concave_envelope():
    cross = load("cross-slope")
    s = build_tin(cross.site.terrain.spot_elevations, []).surface
    assert elevation_at(s, (0, 15)) == 0
    assert elevation_at(s, (20, 15)) == 8
    diagonal = load("diagonal-slope")
    assert next(r for r in run_fixture(diagonal) if r.check == "slope").observed == 50
    concave = load("concave")
    polygon = concave.site.boundary.to_shapely()
    assert polygon.area == 576
    assert polygon.convex_hull.area > polygon.area
    assert concave.site.buildable_envelope.polygon.area_m2 == 318


def test_conflicting_near_duplicates_refuse_surface_and_breakline_intent_retained():
    fixture = load("breakline-noise")
    result = build_tin(fixture.site.terrain.spot_elevations, [])
    assert result.surface is None
    assert len(result.conflicts) == 1
    line = next(f for f in fixture.site.features if f.id == "retaining-breakline")
    assert line.geometry.line.points == [(10, 0), (10, 30)]
    sliver = load("sliver-tin")
    surface = build_tin(sliver.site.terrain.spot_elevations, []).surface
    areas = []
    for ia, ib, ic in surface.triangles:
        a, b, c = (surface.vertices[i] for i in (ia, ib, ic))
        areas.append(abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2)
    assert min(areas) == pytest.approx(0.001)
    assert len(surface.vertices) == 5  # noisy point is not silently discarded


def test_unknown_north_all_implemented_orientation_claims_have_no_value():
    results = [
        r
        for r in run_fixture(load("unknown-north"))
        if r.check == "north-unknown" or r.check.startswith("bearing-")
    ]
    assert len(results) == 5
    assert all(
        r.outcome == "PASS" and r.observed is None and r.claim_status == "not_checked"
        for r in results
    )


def test_references_are_pinned_and_nonnegative_cases_pass_integrity():
    for path in PATHS:
        f = BenchmarkFixture.model_validate_json(path.read_text())
        for case in f.cases:
            assert case.model.site_ref.sha256 == content_hash(f.site)
            assert case.model.program_ref.sha256 == content_hash(f.program)
            if not case.seeded_defect:
                assert errors(check_model(case.model, f.site, f.program)) == []


def test_seeded_bath_disconnect_reports_one_real_failure_and_clean_case_is_reachable():
    f = load("multigenerational")
    clean, defect = f.cases
    assert not errors(check_model(clean.model, f.site, f.program))
    findings = check_model(defect.model, f.site, f.program)
    assert [v.subject_ids for v in findings if v.code == "space_unreachable"] == [["sp-bath"]]
    items = {i.id: i for i in f.program.items}
    assert items["pi-bed-parents"].accessible and items["pi-bath"].accessible
    assert items["pi-bed-parents"].level_preference == items["pi-bath"].level_preference == "entry"


def test_preferences_reverse_on_same_candidates_and_preserve_area_tradeoff():
    social, quiet = load("social-cooking"), load("quiet-cooking")
    assert content_hash(social.site) == content_hash(quiet.site)
    a, b = run_fixture(social), run_fixture(quiet)
    def obs(rows, check):
        return next(r.observed for r in rows if r.check == check)
    assert obs(a, "priority-open-layout") is True
    assert obs(b, "priority-open-layout") is False
    assert obs(a, "priority-isolated-layout") is False
    assert obs(b, "priority-isolated-layout") is True
    assert obs(a, "kitchen-area-open-layout") == obs(b, "kitchen-area-open-layout") == 30
    assert obs(a, "kitchen-area-isolated-layout") == obs(b, "kitchen-area-isolated-layout") == 17.5
    # Real topology difference, not labels or the household score.
    graph_edges = [sum(o.is_passable for o in c.model.openings) for c in social.cases]
    assert graph_edges == [7, 6]


def test_wrong_numbers_missing_or_ambiguous_probes_and_stale_references_fail():
    fixture = load("flat-simple")
    fixture.expectations[0].value = 601
    assert run_fixture(fixture)[0].outcome == "FAIL"
    fixture.expectations[0].metric = "nonexistent_metric"
    assert run_fixture(fixture)[0].outcome == "FAIL"
    fixture = load("social-cooking")
    # Room-area metrics need a subject selector; accepting any would hide wrong-room results.
    next(e for e in fixture.expectations if e.id == "kitchen-area-open-layout").subject_ids = []
    assert (
        next(r for r in run_fixture(fixture) if r.check == "kitchen-area-open-layout").outcome
        == "FAIL"
    )
    fixture.site.name = "changed input"
    with pytest.raises(ValueError, match="stale or mismatched"):
        run_fixture(fixture)


@pytest.mark.parametrize(
    "edit",
    [
        {"metric": None},
        {"code": "wrong"},
        {"status": "not_checked", "value": 10},
        {"tolerance": -1},
        {"value": math.inf},
        {"value": math.nan},
        {"source": "future"},
        {"pending_stage": "S6"},
        {"typo": "reject"},
        {"metric": None, "code": "defect", "value": True},
    ],
)
def test_expected_finding_schema_rejects_ambiguous_or_untrustworthy_data(edit):
    value = load("flat-simple").expectations[0].model_dump(mode="json")
    value.update(edit)
    with pytest.raises(ValidationError):
        ExpectedFinding.model_validate(value)


def test_fixture_rejects_private_sites_unknown_targets_and_duplicate_expectations():
    doc = load("flat-simple").model_dump(mode="json")
    bad = copy.deepcopy(doc)
    bad["site"]["classification"] = "private"
    with pytest.raises(ValidationError, match="synthetic"):
        BenchmarkFixture.model_validate(bad)
    bad = copy.deepcopy(doc)
    bad["expectations"][0]["target"] = "missing-case"
    with pytest.raises(ValidationError, match="unknown expectation target"):
        BenchmarkFixture.model_validate(bad)
    doc["expectations"].append(doc["expectations"][0])
    with pytest.raises(ValidationError, match="unique"):
        BenchmarkFixture.model_validate(doc)


def test_runner_table_all_categories_and_incomplete_gate(capsys):
    assert main([str(HERE / "fixtures")]) == 0
    table = capsys.readouterr().out
    assert all(category.value in table for category in AcceptanceCategory)
    assert "NOT_CHECKED" in table
    assert main([str(HERE / "fixtures"), "--require-complete"]) == 1
    capsys.readouterr()
    assert main([str(HERE / "fixtures/social-cooking.json"), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert all(row["method"] and row["claim_status"] for row in rows)
    assert "versioned_revisions" in category_table([])


def test_runner_rejects_empty_or_invalid_inputs(tmp_path):
    with pytest.raises(SystemExit) as empty:
        main([str(tmp_path)])
    assert empty.value.code == 2
    (tmp_path / "bad.json").write_text('{"not": "a fixture"}')
    with pytest.raises(SystemExit) as invalid:
        main([str(tmp_path)])
    assert invalid.value.code == 2
