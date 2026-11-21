"""Ground-truth benchmark regressions, independent of any private project."""

from __future__ import annotations

import copy
import json
import math
import runpy
import shutil
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
    fixture = load(name)
    surface = build_tin(fixture.site.terrain.spot_elevations, []).surface
    # A plane from the road edge (y = 0, z = front) to the rear (y = 30, z = rear):
    # z = front + (rear - front) * y / 30, so 3 m in from the road and mid-depth are
    # interpolated, not read from a survey point.
    assert elevation_at(surface, (10, 3)) == pytest.approx(front + (rear - front) * 0.1)
    assert elevation_at(surface, (5, 15)) == pytest.approx(7.5)
    # 15 m over 30 m of depth is a 50 % slope, whichever way the plot falls.
    slope = next(r for r in run_fixture(fixture) if r.check == "slope")
    assert slope.observed == pytest.approx(50) and slope.outcome == "PASS"


def test_slope_directions_and_concave_envelope():
    cross = load("cross-slope")
    s = build_tin(cross.site.terrain.spot_elevations, []).surface
    # Cross-fall z = 0.4 x (0 m west, 8 m east over 20 m), constant along y.
    for xy, z in [((0, 15), 0), ((20, 15), 8), ((10, 15), 4), ((5, 25), 2), ((15, 3), 6)]:
        assert elevation_at(s, xy) == pytest.approx(z)
    diagonal = load("diagonal-slope")
    assert next(r for r in run_fixture(diagonal) if r.check == "slope").observed == 50
    concave = load("concave")
    polygon = concave.site.boundary.to_shapely()
    # A 30 x 30 m square less its 18 x 18 m north-east corner: 900 - 324.
    assert polygon.area == 576
    assert polygon.convex_hull.area == 900 - 18 * 18 / 2
    # Envelope: a 26 x 7 m bar (x 2..28, y 3..10) plus an 8 x 17 m bar (x 2..10, y 10..27).
    assert concave.site.buildable_envelope.polygon.area_m2 == 26 * 7 + 8 * 17 == 318


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
    cases = {c.id: c for c in f.cases}
    clean, defect = cases["step-free-graph"], cases["bath-unreachable"]
    # The S6 door and stair cases are integrity-clean reference geometry as well.
    for c in [clean, cases["door-into-hall"], cases["door-into-bedroom"], cases["stair-clear"]]:
        assert not errors(check_model(c.model, f.site, f.program))
    findings = check_model(defect.model, f.site, f.program)
    assert [v.subject_ids for v in findings if v.code == "space_unreachable"] == [["sp-bath"]]
    items = {i.id: i for i in f.program.space_requirements}
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


def test_committed_fixtures_are_complete():
    """Static equivalent of ``main([fixtures, "--require-complete"]) == 0``.

    ``main`` returns 1 only for a FAIL or, with ``--require-complete``, a NOT_CHECKED
    outcome, and exits 2 on duplicate fixture IDs. ``_check`` gives NOT_CHECKED to
    exactly the ``source: future`` expectations; FAIL is excluded fixture by fixture in
    ``test_every_current_observation_matches_declared_expectations``.
    """
    fixtures = [BenchmarkFixture.model_validate_json(p.read_text()) for p in PATHS]
    assert len({f.id for f in fixtures}) == len(fixtures) == 18
    assert [(f.id, e.id) for f in fixtures for e in f.expectations if e.source == "future"] == []


def _table(counts: dict[str, tuple[int, int, int]]) -> list[str]:
    rows = ["| Category | PASS | FAIL | NOT_CHECKED |", "|---|---:|---:|---:|"]
    for category in AcceptanceCategory:
        p, f, n = counts.get(category.value, (0, 0, 0))
        rows.append(f"| {category.value} | {p} | {f} | {n} |")
    return rows


#: flat-simple's nine expectations by category (all PASS).
FLAT_SIMPLE = {
    "geometric_feasibility": (2, 0, 0),
    "terrain_compatibility": (2, 0, 0),
    "metric_accuracy": (2, 0, 0),
    "visual_consistency": (1, 0, 0),
    "versioned_revisions": (2, 0, 0),
}


def test_runner_table_counts_each_category_and_incomplete_gate(capsys, tmp_path):
    flat = HERE / "fixtures/flat-simple.json"
    complete = tmp_path / "complete"
    complete.mkdir()
    shutil.copy(flat, complete)
    assert main([str(complete)]) == 0
    assert capsys.readouterr().out.splitlines() == _table(FLAT_SIMPLE)
    assert main([str(complete), "--require-complete"]) == 0
    capsys.readouterr()

    doc = json.loads(flat.read_text())
    doc["id"] = "synthetic-incomplete"
    doc["expectations"].append(
        {
            "id": "stale-future",
            "category": "practical_usability",
            "source": "future",
            "metric": "future_probe",
            "value": None,
            "status": "not_checked",
            "pending_stage": "S99",
            "basis": "synthetic future probe",
        }
    )
    both = tmp_path / "both"
    both.mkdir()
    shutil.copy(flat, both)
    (both / "incomplete.json").write_text(json.dumps(doc))
    # NOT_CHECKED is reported, counted in its own column, and is not a failure...
    assert main([str(both)]) == 0
    doubled = {k: (2 * p, f, n) for k, (p, f, n) in FLAT_SIMPLE.items()}
    assert capsys.readouterr().out.splitlines() == [
        *_table({**doubled, "practical_usability": (0, 0, 1)}),
        "NOT_CHECKED: synthetic-incomplete/stale-future: expected=None observed=None; "
        "S99: synthetic future probe",
    ]
    # ...until completeness is required.
    assert main([str(both), "--require-complete"]) == 1
    capsys.readouterr()

    assert main([str(flat), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 9
    assert all(r["outcome"] == "PASS" and r["method"] and r["claim_status"] for r in rows)
    assert category_table([]).splitlines() == _table({})


def test_runner_rejects_empty_or_invalid_inputs(tmp_path):
    with pytest.raises(SystemExit) as empty:
        main([str(tmp_path)])
    assert empty.value.code == 2
    (tmp_path / "bad.json").write_text('{"not": "a fixture"}')
    with pytest.raises(SystemExit) as invalid:
        main([str(tmp_path)])
    assert invalid.value.code == 2
