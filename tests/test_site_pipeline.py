"""Milestone B end to end: synthetic survey -> cad_import + site -> report, SVG, gate."""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from house_ai.cad.dwg_oda import OdaDwgAdapter, find_oda_converter
from house_ai.cad.layers import LayerMapping, load_layer_mapping
from house_ai.cli.main import main
from house_ai.domain.codepack import find_prohibited_claims
from house_ai.domain.coordinates import SurveyTransform
from house_ai.domain.epistemics import ConfirmationStatus as C
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.provenance import ApprovalRequiresHuman, DataClassification
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.records import IssueStatus
from house_ai.domain.site import (
    CadImportProvenance,
    Site,
    SiteFeatureKind,
    site_verification_blockers,
)
from house_ai.domain.units import LengthUnit
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.geospatial.crs import CrsValidationError
from house_ai.geospatial.terrain import elevation_at
from house_ai.geospatial.validation import report_markdown, validate_site
from house_ai.orchestration.site import SiteService
from house_ai.orchestration.site_ingestion import SiteConfirmation, confirm_site, ingest_site
from house_ai.orchestration.survey_inspection import (
    inspect_file,
    inspect_files,
    inspection_markdown,
)
from house_ai.orchestration.workflow import GateBlocked, Workflow
from house_ai.render2d.site_svg import render_site_svg
from house_ai.storage.hashing import file_sha256

from .conftest import AGENT, HUMAN, REPO, SURVEY_DXF, SURVEY_LAYERS

FULL = SiteConfirmation(
    units=LengthUnit.METRE,
    elevation_units=LengthUnit.METRE,
    epsg=25832,
    vertical_datum="DHHN2016",
    vertical_epsg=7837,
    boundary_verified=True,
)


@pytest.fixture
def mapping() -> LayerMapping:
    return load_layer_mapping(SURVEY_LAYERS)


@pytest.fixture
def ingest(new_store, mapping):
    """Store a survey file and ingest it; returns (store, IngestResult)."""

    def run(path: Path = SURVEY_DXF, mapping: LayerMapping = mapping):
        store = new_store("synthetic-survey")
        doc = store.add_source(path, HUMAN, classification=DataClassification.SYNTHETIC)
        return store, ingest_site(store, doc.id, mapping, AGENT)

    return run


def _site(store, ref) -> Site:
    return store.get(ref, Site)


# ---------------------------------------------------------------- ground truth


def test_boundary_area_dimensions_and_origin_match_ground_truth(ingest, survey):
    store, result = ingest()
    site = _site(store, result.site_ref)
    assert site.coordinates.local.origin == (survey["E0"], survey["N0"], 0.0)
    # Origin at vertex A, rotation 0: local boundary == the ground-truth parcel.
    ring = site.boundary.outer
    assert sorted(ring) == sorted(survey["PARCEL"])
    report = validate_site(site, result.site_ref)
    assert report.boundary.area_m2 == pytest.approx(1400.0, abs=1e-6)
    assert report.boundary.perimeter_m == pytest.approx(
        40 + 30 + math.sqrt(1000) + math.sqrt(200) + 30, abs=1e-6
    )
    assert sorted(round(e.length_m, 4) for e in report.boundary.edges) == [
        14.1421,
        30.0,
        30.0,
        31.6228,
        40.0,
    ]


def test_grid_coordinates_are_recoverable_from_local(ingest, survey):
    store, result = ingest()
    local = _site(store, result.site_ref).coordinates.local
    for x, y in survey["PARCEL"]:
        e, n, _ = local.local_to_grid((x, y, 0.0))
        assert (e, n) == pytest.approx((survey["E0"] + x, survey["N0"] + y), abs=1e-9)


def test_terrain_matches_the_ground_truth_plane(ingest, survey):
    store, result = ingest()
    terrain = _site(store, result.site_ref).terrain
    assert terrain.status.value == "surface_built"
    assert len(terrain.spot_elevations) == 8  # 7 points + 1 block, ambiguous ones excluded
    assert sorted(c.z_m for c in terrain.contours) == [101.0, 102.0, 103.0, 104.0]
    for s in terrain.spot_elevations:
        assert s.z_m == pytest.approx(survey["plane_z"](*s.xy), abs=1e-9)
    for x, y in [(5.0, 5.0), (20.0, 20.0), (35.0, 28.0), (12.5, 37.0)]:
        assert elevation_at(terrain.surface, (x, y)) == pytest.approx(survey["plane_z"](x, y))


def test_features_frontage_and_access(ingest, survey):
    store, result = ingest()
    site = _site(store, result.site_ref)
    kinds = {f.kind for f in site.features}
    assert kinds == {
        SiteFeatureKind.ROAD,
        SiteFeatureKind.EXISTING_STRUCTURE,
        SiteFeatureKind.TREE,
        SiteFeatureKind.ACCESS_POINT,
        SiteFeatureKind.FRONTAGE,
    }
    building = next(f for f in site.features if f.kind is SiteFeatureKind.EXISTING_STRUCTURE)
    assert building.geometry.polygon.area_m2 == pytest.approx(48.0)
    tree = next(f for f in site.features if f.kind is SiteFeatureKind.TREE)
    assert tree.geometry.xy == pytest.approx(survey["TREE_AT"])
    report = validate_site(site)
    assert report.frontage.length_m == pytest.approx(40.0)
    assert len(report.frontage.access_points_on_frontage) == 1
    assert all(f.status is Epistemic.INFERENCE for f in site.features)


def test_millimetre_drawing_gives_the_same_site(ingest, make_survey, survey):
    store_m, res_m = ingest()
    store_mm, res_mm = ingest(make_survey(unit="mm"))
    a, b = _site(store_m, res_m.site_ref), _site(store_mm, res_mm.site_ref)
    assert b.coordinates.source_units.unit is LengthUnit.MILLIMETRE
    assert b.coordinates.local.origin == pytest.approx(a.coordinates.local.origin)
    assert validate_site(b).boundary.area_m2 == pytest.approx(1400.0, abs=1e-6)
    za = sorted(s.z_m for s in a.terrain.spot_elevations)
    zb = sorted(s.z_m for s in b.terrain.spot_elevations)
    assert zb == pytest.approx(za, abs=1e-9)
    # LOCAL -> SOURCE gives back the raw millimetre CAD numbers: (E0 + x, N0 + y, z) x 1000.
    to_source = SurveyTransform(0.001, 0.001, b.coordinates.local)
    for x, y in b.boundary.outer:
        assert to_source.local_to_source((x, y, 0.0)) == pytest.approx(
            ((survey["E0"] + x) * 1000, (survey["N0"] + y) * 1000, 0.0), abs=1e-6
        )
    # Flat lists: pytest.approx compares numbers, not nested points.
    assert [c for p in b.boundary.outer for c in p[:2]] == pytest.approx(
        [c for p in survey["PARCEL"] for c in p], abs=1e-9
    )
    for spot in b.terrain.spot_elevations:
        x, y = spot.xy
        assert to_source.local_to_source((x, y, spot.z_m)) == pytest.approx(
            ((survey["E0"] + x) * 1000, (survey["N0"] + y) * 1000, spot.z_m * 1000), abs=1e-6
        )


# ----------------------------------------------------- unknowns and ambiguity


def test_nothing_is_confirmed_by_ingestion(ingest):
    store, result = ingest()
    c = _site(store, result.site_ref).coordinates
    assert c.source_units.status is C.DECLARED_IN_SOURCE
    assert c.elevation_units.status is C.DECLARED_IN_SOURCE
    assert c.horizontal_crs.status is C.DECLARED_IN_SOURCE
    assert c.horizontal_crs.epsg is None and c.horizontal_crs.declared_epsg == 25832
    assert c.vertical_datum.status is C.UNKNOWN
    assert c.local.grid_to_true_north_deg is None
    assert _site(store, result.site_ref).boundary_status is Epistemic.INFERENCE
    assert len(result.blockers) == 5


def test_utm_like_numbers_without_geodata_leave_the_crs_unknown(ingest, make_survey):
    """E 500 100, N 5 400 200 look like UTM metres; without a declaration nothing follows."""
    path = make_survey(geodata=False)
    store, result = ingest(path)
    site = _site(store, result.site_ref)
    crs = site.coordinates.horizontal_crs
    assert crs.status is C.UNKNOWN and crs.declared_epsg is None and crs.epsg is None
    assert any("horizontal CRS is unknown" in b for b in result.blockers)
    report = validate_site(site)
    # No geographic position, no convergence, no true bearing is derived from magnitudes.
    assert report.coordinates.origin_lon_lat is None
    assert report.coordinates.grid_to_true_north_deg is None
    assert site.coordinates.local.grid_to_true_north_deg is None
    assert report.boundary.edges and all(e.bearing_true_deg is None for e in report.boundary.edges)
    # The only CRS wording is "unknown" and the question to the owner; no zone is named.
    def crs_lines(text):
        # The file's own path (pytest names it after this test) is not a CRS statement.
        lines = [ln for ln in text.splitlines() if not ln.startswith("- Path:")]
        return [ln for ln in lines if {"utm", "zone", "epsg"} & set(_words(ln))]

    assert crs_lines(report_markdown(report)) == [
        "- horizontal CRS is unknown; a human must confirm the EPSG code or confirm the survey "
        "is local-only"
    ]
    assert crs_lines(inspection_markdown(inspect_files([path]))) == [
        "- Declared EPSG: none",
        "- Coordinate magnitudes are not evidence of a CRS, zone or unit.",
        "- [ ] State the horizontal CRS as an EPSG code (for UTM: zone, hemisphere and datum, "
        "e.g. ETRS89 / UTM 32N = EPSG:25832), or confirm the survey is local-only.",
    ]


def _words(line: str) -> list[str]:
    return re.findall(r"[a-z]+", line.lower())


def test_unitless_drawing_produces_no_geometry(ingest, make_survey):
    store, result = ingest(make_survey(declare_units=False))
    site = _site(store, result.site_ref)
    assert site.boundary is None and site.coordinates.local is None
    assert site.terrain.spot_elevations == [] and site.features == []
    assert any("drawing units are unknown" in b for b in result.blockers)


def test_a_unitless_drawing_can_be_fully_confirmed(ingest, make_survey):
    store, _ = ingest(make_survey(declare_units=False))
    # Only the horizontal unit: elevations stay out, never converted with a guessed unit.
    ref = confirm_site(store, "site", HUMAN, SiteConfirmation(units=LengthUnit.METRE))
    site = _site(store, ref)
    assert validate_site(site).boundary.area_m2 == pytest.approx(1400.0)
    assert site.terrain.spot_elevations == [] and site.terrain.contours == []
    assert any("elevation unit" in b for b in site_verification_blockers(site))
    ref = confirm_site(store, "site", HUMAN, FULL)
    site = _site(store, ref)
    assert site_verification_blockers(site) == []
    assert len(site.terrain.spot_elevations) == 8 and site.terrain.surface is not None


def test_ambiguous_entities_are_listed_with_reasons(ingest):
    store, result = ingest()
    cad = store.get(result.cad_ref, CadImportProvenance)
    reasons = sorted(
        (a.layer, a.entity_type, a.reason.split(";")[0]) for a in cad.ambiguous_entities
    )
    assert reasons == [
        ("CONTOURS", "LWPOLYLINE", "contour elevation is 0, which may mean 'not set'"),
        ("CONTOURS", "POLYLINE", "z varies along the line, so it is not a contour"),
        ("PARCEL_BOUNDARY", "LINE", "open linework on a boundary layer, not part of it"),
        ("ROAD", "TEXT", "text label on a road layer"),
        ("SPOT_HEIGHTS", "POINT", "point elevation is 0, which may mean 'not set'"),
        ("SPOT_HEIGHTS", "TEXT", "height label text is not linked to a surveyed point"),
    ]
    assert cad.unrecognized_layers == ["MISC_XREF"]
    assert cad.unrecognized_entities["SPLINE"] == 1


def test_two_boundary_candidates_block_until_one_is_named(ingest, make_survey, mapping):
    path = make_survey(extra_boundary=True)
    store, result = ingest(path)
    site = _site(store, result.site_ref)
    assert site.boundary is None
    assert any(i.id == "iss-boundary-ambiguous" for i in site.issues)
    cad = store.get(result.cad_ref, CadImportProvenance)
    chosen = next(
        a.handle
        for a in cad.ambiguous_entities
        if a.layer == "PARCEL_BOUNDARY" and a.entity_type == "LWPOLYLINE"
    )
    named = mapping.model_copy(update={"boundary_handle": chosen})
    store2, result2 = ingest(path, named)
    assert _site(store2, result2.site_ref).boundary is not None


def test_zero_elevations_are_used_only_when_a_human_says_so(ingest, mapping):
    store, result = ingest(mapping=mapping.model_copy(update={"zero_elevation_is_valid": True}))
    terrain = _site(store, result.site_ref).terrain
    assert len(terrain.spot_elevations) == 9
    assert len(terrain.contours) == 5


def test_crossing_contours_and_conflicting_spots_block(ingest, make_survey):
    store, result = ingest(make_survey(crossing_contour=True))
    assert any("cross" in b for b in result.blockers)
    store, result = ingest(make_survey(conflicting_spot=True))
    site = _site(store, result.site_ref)
    assert any("share a position" in b for b in result.blockers)
    # Both conflicting spots are left out; no elevation is picked between them.
    assert len(site.terrain.spot_elevations) == 7


# ------------------------------------------------------------------ provenance


def test_cad_import_provenance(ingest):
    store, result = ingest()
    cad = store.get(result.cad_ref, CadImportProvenance)
    assert cad.sha256 == file_sha256(SURVEY_DXF)
    assert cad.original_filename == "survey.dxf"
    assert cad.parser == "ezdxf" and cad.parser_version
    assert cad.drawing_units.unit is LengthUnit.METRE
    assert cad.horizontal_crs_status is C.DECLARED_IN_SOURCE and cad.epsg is None
    assert cad.declared_epsg == 25832
    assert cad.layer_roles["PARCEL_BOUNDARY"] == "boundary"
    assert cad.local_origin is not None


def test_every_site_value_traces_to_a_cad_entity(ingest):
    store, result = ingest()
    site = _site(store, result.site_ref)
    kinds = [r.kind for r in site.provenance.inputs]
    assert kinds == [K.SOURCE_DOCUMENT, K.CAD_IMPORT]
    assert site.boundary_source_ref.startswith("src-survey#")
    assert "(layer PARCEL_BOUNDARY)" in site.boundary_source_ref
    for s in site.terrain.spot_elevations:
        assert s.source_ref.startswith("src-survey#") and "SPOT_HEIGHTS" in s.source_ref
    for c in site.terrain.contours:
        assert "CONTOURS" in c.source_ref


def test_original_survey_is_never_modified(ingest):
    before = file_sha256(SURVEY_DXF)
    store, _ = ingest()
    assert file_sha256(SURVEY_DXF) == before
    assert store.verify() == []


def test_inspection_is_read_only_and_answers_the_owner_questions(survey):
    report = inspect_file(SURVEY_DXF)
    assert report.unchanged_after_inspection and report.sha256 == file_sha256(SURVEY_DXF)
    assert report.insunits_code == 6 and report.declared_epsg == 25832
    assert "needs your confirmation" in report.crs_status
    assert [c.area_m2_if_declared_unit for c in report.boundary_candidates] == [
        pytest.approx(1400.0)
    ]
    text = inspection_markdown(type("I", (), {"note": "n", "files": [report]})())
    for heading in [
        "1. File format",
        "2. Drawing units",
        "3. CAD layers",
        "4. Coordinate metadata",
        "5. CRS verification status",
        "6. Candidate parcel boundary",
        "7. Contours and spot elevations",
        "8. Unknown or ambiguous information",
        "9. Provenance",
        "10. Needs your confirmation",
    ]:
        assert heading in text


def test_inspection_with_a_mapping_lists_ambiguities(mapping):
    report = inspect_file(SURVEY_DXF, mapping)
    assert len(report.ambiguous) == 6
    assert report.unmapped_layers == ["MISC_XREF"]


def test_inspection_of_an_unreadable_file(tmp_path):
    fake = tmp_path / "plan.dwg"
    fake.write_bytes(b"%PDF-1.4 not a drawing")
    report = inspect_file(fake)
    assert not report.readable and report.detected_format.startswith("pdf")
    assert report.needs_confirmation


# --------------------------------------------------------------- approval gate


def test_human_confirmation_clears_blockers_and_the_human_approves(ingest):
    store, result = ingest()
    wf = Workflow(store)
    sites = SiteService(store)
    sites.assess(result.site_ref, AGENT)
    confirmed = sites.confirm("site", HUMAN, FULL)
    ref = confirmed.site_ref
    site = _site(store, ref)
    assert ref.version == 2 and confirmed.blockers == []
    assert confirmed.state is WorkflowState.SITE_INGESTION
    assert site.provenance.created_by == HUMAN
    assert site.coordinates.horizontal_crs.epsg == 25832
    assert site.coordinates.local.grid_to_true_north_deg == pytest.approx(-0.00103, abs=5e-5)
    with pytest.raises(ApprovalRequiresHuman):
        wf.approve(Gate.SITE, ref, AGENT, "agent tries")
    with pytest.raises(GateBlocked):
        wf.approve(Gate.SITE, result.site_ref, HUMAN, "the unconfirmed v1")
    wf.approve(Gate.SITE, ref, HUMAN, "owner approves the confirmed site")
    assert wf.state is WorkflowState.SITE_APPROVED


def test_partial_confirmation_keeps_the_rest_blocked(ingest):
    store, _ = ingest()
    ref = confirm_site(store, "site", HUMAN, SiteConfirmation(units=LengthUnit.METRE))
    blockers = site_verification_blockers(_site(store, ref))
    assert not any("drawing units" in b for b in blockers)
    assert any("horizontal CRS" in b for b in blockers)
    # A later confirmation keeps the earlier one and the verified boundary.
    ref = confirm_site(store, "site", HUMAN, SiteConfirmation(boundary_verified=True))
    ref = confirm_site(store, "site", HUMAN, SiteConfirmation(epsg=25832))
    site = _site(store, ref)
    assert site.coordinates.source_units.status is C.USER_CONFIRMED
    assert site.boundary_status is Epistemic.VERIFIED_FACT


def test_correcting_the_unit_rescales_the_whole_site(ingest):
    store, _ = ingest()
    ref = confirm_site(store, "site", HUMAN, SiteConfirmation(units=LengthUnit.FOOT))
    report = validate_site(_site(store, ref))
    assert report.boundary.area_m2 == pytest.approx(1400.0 * 0.3048**2, rel=1e-9)


def test_a_crs_that_does_not_cover_the_site_is_blocked(ingest):
    store, _ = ingest()
    ref = confirm_site(store, "site", HUMAN, SiteConfirmation(epsg=27700))  # British Grid
    site = _site(store, ref)
    assert any(i.id == "iss-crs-area-of-use" for i in site.issues)
    assert any("area of use" in b for b in site_verification_blockers(site))


def test_a_wrong_utm_zone_cannot_be_detected_from_coordinates(ingest):
    """Easting 500 100 is valid in every UTM zone, so only the human can catch this."""
    store, _ = ingest()
    site = _site(store, confirm_site(store, "site", HUMAN, SiteConfirmation(epsg=32633)))
    assert not any(i.id == "iss-crs-area-of-use" for i in site.issues)
    lon, _ = validate_site(site).coordinates.origin_lon_lat
    assert lon == pytest.approx(15.0, abs=0.01)  # placed at zone 33's meridian, not 9°E


def test_invalid_confirmations_are_refused(ingest):
    store, _ = ingest()
    with pytest.raises(CrsValidationError):
        confirm_site(store, "site", HUMAN, SiteConfirmation(epsg=4326))
    with pytest.raises(ValueError, match="either"):
        confirm_site(store, "site", HUMAN, SiteConfirmation(epsg=25832, local_only=True))
    with pytest.raises(ValueError, match="unknown issue"):
        confirm_site(store, "site", HUMAN, SiteConfirmation(accept_issues=["iss-nope"]))
    with pytest.raises(ValueError, match="nothing to confirm"):
        confirm_site(store, "site", HUMAN, SiteConfirmation())


def test_a_human_can_accept_a_blocking_issue_and_it_stays_visible(ingest, make_survey):
    store, _ = ingest(make_survey(crossing_contour=True))
    site = _site(store, store.latest(K.SITE, "site"))
    crossing = next(i.id for i in site.issues if "cross" in i.title)
    ref = confirm_site(store, "site", HUMAN, SiteConfirmation(accept_issues=[crossing]))
    issue = next(i for i in _site(store, ref).issues if i.id == crossing)
    assert issue.status is IssueStatus.ACCEPTED


def test_local_only_survey_has_no_north(ingest):
    store, _ = ingest()
    conf = SiteConfirmation(
        units=LengthUnit.METRE,
        elevation_units=LengthUnit.METRE,
        local_only=True,
        vertical_datum="benchmark BM1 = 100.00",
        vertical_local=True,
        boundary_verified=True,
    )
    site = _site(store, confirm_site(store, "site", HUMAN, conf))
    assert site_verification_blockers(site) == []
    assert site.coordinates.local.grid_to_true_north_deg is None
    assert "unknown" in validate_site(site).coordinates.grid_north


# ------------------------------------------------------------------- outputs


def test_site_svg_is_deterministic_and_states_what_is_unknown(ingest):
    store, result = ingest()
    site = _site(store, result.site_ref)
    report = validate_site(site, result.site_ref)
    svg = render_site_svg(site, report)
    assert svg == render_site_svg(site, report)
    assert svg.startswith("<svg") and "north not established" in svg
    assert "1400.00 m²" in svg and "40.00 m" in svg and "101.00" in svg
    assert "a human must confirm" in svg
    assert find_prohibited_claims(svg) == []
    confirmed = _site(store, confirm_site(store, "site", HUMAN, FULL))
    svg2 = render_site_svg(confirmed, validate_site(confirmed))
    assert ">GN<" in svg2 and ">TN<" in svg2 and "north not established" not in svg2


def test_validation_report_markdown(ingest):
    store, result = ingest()
    text = report_markdown(validate_site(_site(store, result.site_ref), result.site_ref))
    assert "Area: 1400.00 m²" in text
    assert "Frontage length: 40.000 m" in text
    assert "approves nothing" in text
    assert find_prohibited_claims(text) == []


# ----------------------------------------------------------------------- CLI


def test_cli_pipeline(tmp_path):
    p = str(tmp_path / "proj")
    assert (
        main(
            [
                "project",
                "init",
                p,
                "--id",
                "demo",
                "--name",
                "Demo",
                "--classification",
                "synthetic",
                "--actor",
                "human:owner",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "source",
                "add",
                p,
                str(SURVEY_DXF),
                "--classification",
                "synthetic",
                "--actor",
                "human:owner",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "site",
                "ingest",
                p,
                "--source",
                "src-survey",
                "--layers",
                str(SURVEY_LAYERS),
                "--actor",
                "agent:claude-code",
            ]
        )
        == 0
    )
    # Re-assessment still works (the state it leaves is pinned in test_site_service).
    assert main(["workflow", "assess-site", p, "--id", "site", "--actor", "agent:claude-code"]) == 0
    out = tmp_path / "out"
    assert main(["site", "report", p, "--id", "site", "--out", str(out)]) == 0
    assert (out / "site-report.md").is_file()  # the file list is pinned in test_site_service
    assert main(["project", "verify", p]) == 0


def test_cli_site_confirm_refuses_a_non_interactive_shell(tmp_path, monkeypatch, capsys):
    # A real non-terminal stdin (no faked isatty), as an agent's shell has; in process.
    with open(os.devnull) as devnull:
        monkeypatch.setattr(sys, "stdin", devnull)
        code = main(["site", "confirm", str(tmp_path), "--confirmer", "owner", "--units", "m"])
    assert code == 2
    assert "interactive terminal" in capsys.readouterr().err


def test_cli_inspect_writes_reports(tmp_path, capsys):
    out = tmp_path / "inspection"
    assert (
        main(
            ["site", "inspect", str(SURVEY_DXF), "--layers", str(SURVEY_LAYERS), "--out", str(out)]
        )
        == 0
    )
    assert (out / "inspection.md").read_text().count("Needs your confirmation") == 1
    assert main(["site", "inspect", str(tmp_path / "inspection" / "inspection.md")]) == 1


def test_cli_crs_lookup(capsys):
    assert main(["crs", "utm-candidates", "32", "N"]) == 0
    assert "EPSG:25832" in capsys.readouterr().out
    assert main(["crs", "describe", "4326"]) == 0


# --------------------------------------------------------------- DWG via ODA


oda = find_oda_converter()


@pytest.mark.skipif(oda is None, reason="ODA File Converter not installed")
def test_dwg_is_read_through_a_private_copy(tmp_path, ingest):
    src_dir, dwg_dir = tmp_path / "dxf", tmp_path / "dwg"
    src_dir.mkdir()
    dwg_dir.mkdir()
    shutil.copyfile(SURVEY_DXF, src_dir / "survey.dxf")
    subprocess.run(
        [str(oda.executable), str(src_dir), str(dwg_dir), "ACAD2018", "DWG", "0", "1", "*.DXF"],
        check=True,
        capture_output=True,
        timeout=300,
    )
    dwg = tmp_path / "Vermessung نقشه.dwg"  # non-ASCII name, as real files have
    (dwg_dir / "survey.dwg").rename(dwg)
    before = file_sha256(dwg)
    insp = OdaDwgAdapter(oda).inspect_cad(dwg)
    assert insp.source_format == "dwg AC1032"
    assert insp.converter == "ODA File Converter" and insp.converted_sha256
    assert insp.declared_insunits == 6 and insp.declared_epsg == 25832
    store, result = ingest(dwg)
    site = _site(store, result.site_ref)
    assert validate_site(site).boundary.area_m2 == pytest.approx(1400.0, abs=1e-6)
    cad = store.get(result.cad_ref, CadImportProvenance)
    assert cad.source_format == "dwg AC1032" and cad.converter_version == oda.version
    assert file_sha256(dwg) == before


def test_committed_example_outputs_match_the_pipeline():
    """examples/surveys/synthetic/expected/ is exactly what the pipeline produces."""
    import runpy

    make_expected = runpy.run_path(str(REPO / "examples/surveys/synthetic/make_expected.py"))
    assert make_expected["main"](["--check"]) == 0


def test_committed_fixture_matches_its_generator(tmp_path, survey):
    """survey.dxf holds the same entities make_survey.py writes (headers carry GUIDs/dates)."""
    from house_ai.cad.dxf_ezdxf import EzdxfAdapter

    fresh = survey["build_survey"](tmp_path / "fresh.dxf")
    a = EzdxfAdapter().extract_cad(SURVEY_DXF, {})
    b = EzdxfAdapter().extract_cad(fresh, {})
    assert a.points == b.points and a.polylines == b.polylines
    assert a.inspection.geodata == b.inspection.geodata


# ------------------------------------------------------- several survey files

BOUNDARY_LAYERS = {"PARCEL_BOUNDARY", "ROAD", "EXIST_BUILDING", "TREES", "ACCESS", "TEXT_ANNO"}
HEIGHT_LAYERS = {"CONTOURS", "SPOT_HEIGHTS"}


@pytest.fixture
def ingest_many(new_store, mapping):
    def run(paths: list[Path], mapping: LayerMapping = mapping):
        store = new_store("synthetic-survey")
        ids = [
            store.add_source(p, HUMAN, classification=DataClassification.SYNTHETIC).id
            for p in paths
        ]
        return store, ingest_site(store, ids, mapping, AGENT)

    return run


def test_a_survey_split_over_two_files_gives_the_same_site(ingest, ingest_many, make_survey):
    store1, single = ingest()
    split = [make_survey(layers=BOUNDARY_LAYERS), make_survey(layers=HEIGHT_LAYERS)]
    store2, result = ingest_many(split)
    a, b = _site(store1, single.site_ref), _site(store2, result.site_ref)
    assert b.coordinates.local.origin == a.coordinates.local.origin
    assert sorted(b.boundary.outer) == sorted(a.boundary.outer)
    assert len(b.terrain.spot_elevations) == 8 and len(b.terrain.contours) == 4
    assert validate_site(b).frontage.length_m == pytest.approx(40.0)
    ids = [s.id for s in b.terrain.spot_elevations] + [f.id for f in b.features]
    assert len(ids) == len(set(ids))  # DXF handles restart per file; ids must not collide
    assert [r.kind for r in b.provenance.inputs].count(K.CAD_IMPORT) == 2
    assert result.blockers == single.blockers
    ref = confirm_site(store2, "site", HUMAN, FULL)
    assert site_verification_blockers(_site(store2, ref)) == []


def test_files_that_declare_different_units_block(ingest_many, make_survey):
    store, result = ingest_many(
        [make_survey(layers=BOUNDARY_LAYERS), make_survey(unit="mm", layers=HEIGHT_LAYERS)]
    )
    site = _site(store, result.site_ref)
    assert any(i.id == "iss-sources-disagree-units" for i in site.issues)
    ref = confirm_site(store, "site", HUMAN, FULL)
    assert any("different units" in b for b in site_verification_blockers(_site(store, ref)))


def test_a_boundary_in_two_files_is_ambiguous(ingest_many, make_survey):
    store, result = ingest_many([make_survey(), make_survey(layers=BOUNDARY_LAYERS)])
    site = _site(store, result.site_ref)
    assert site.boundary is None
    assert any(i.id == "iss-boundary-in-several-files" for i in site.issues)


# -------------------------------------------------------- Milestone B review regressions


def test_unitless_drawing_preserves_cad_import_provenance_and_updates_on_confirm(
    ingest, make_survey
):
    store, result = ingest(make_survey(declare_units=False))
    cad_v1 = store.get(result.cad_ref, CadImportProvenance)
    assert len(cad_v1.ambiguous_entities) == 6
    assert cad_v1.unrecognized_layers == ["MISC_XREF"]
    assert cad_v1.unrecognized_entities["SPLINE"] == 1
    assert cad_v1.local_origin is None

    site_ref = confirm_site(store, "site", HUMAN, FULL)
    site_v2 = _site(store, site_ref)
    cad_ref_v2 = next(r for r in site_v2.provenance.inputs if r.kind is K.CAD_IMPORT)
    assert cad_ref_v2.version == 2
    cad_v2 = store.get(cad_ref_v2, CadImportProvenance)
    assert cad_v2.drawing_units.status is C.USER_CONFIRMED
    assert cad_v2.horizontal_crs_status is C.USER_CONFIRMED
    assert cad_v2.epsg == 25832
    assert cad_v2.vertical_datum_status is C.USER_CONFIRMED
    assert cad_v2.local_origin == site_v2.coordinates.local.origin
    assert len(cad_v2.ambiguous_entities) == 6


def test_site_svg_renders_easement_utility_water_holes_and_buildable_envelope(ingest):
    from house_ai.domain.geometry import Polygon2D, Polyline2D
    from house_ai.domain.site import (
        BuildableEnvelope,
        PolygonGeometry,
        PolylineGeometry,
        SiteFeature,
    )

    store, result = ingest()
    site = _site(store, result.site_ref).model_copy(
        update={
            "buildable_envelope": BuildableEnvelope(
                polygon=Polygon2D(outer=[(3, 3), (37, 3), (37, 27), (3, 27)]),
                status=Epistemic.ASSUMPTION,
                basis="3 m setback assumed",
            ),
            "features": [
                *_site(store, result.site_ref).features,
                SiteFeature(
                    id="esmt-1",
                    kind=SiteFeatureKind.EASEMENT,
                    geometry=PolygonGeometry(
                        polygon=Polygon2D(
                            outer=[(0, 0), (40, 0), (40, 3), (0, 3)],
                            holes=[[(5, 1), (10, 1), (10, 2), (5, 2)]],
                        )
                    ),
                ),
                SiteFeature(
                    id="util-1",
                    kind=SiteFeatureKind.UTILITY,
                    geometry=PolylineGeometry(line=Polyline2D(points=[(0, 5), (40, 5)])),
                ),
                SiteFeature(
                    id="water-1",
                    kind=SiteFeatureKind.WATER,
                    geometry=PolygonGeometry(
                        polygon=Polygon2D(outer=[(20, 20), (25, 20), (25, 25), (20, 25)])
                    ),
                ),
            ],
        }
    )
    svg = render_site_svg(site, validate_site(site))
    assert "esmt-1 (easement)" in svg
    assert 'fill-rule="evenodd"' in svg
    assert "util-1 (utility)" in svg
    assert "water-1 (water)" in svg
    assert "buildable envelope (assumption): 3 m setback assumed" in svg


def test_geodata_transform_on_projected_grid_and_invalid_epsg_block(tmp_path, new_store, mapping):
    import ezdxf

    from examples.surveys.synthetic.make_survey import GEODATA_XML, PARCEL

    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 6
    doc.layers.add("PARCEL_BOUNDARY")
    msp = doc.modelspace()
    msp.add_lwpolyline(PARCEL, close=True, dxfattribs={"layer": "PARCEL_BOUNDARY"})
    geo = msp.new_geodata()
    geo.dxf.coordinate_type = 2  # projected grid, but with non-zero reference point & bad EPSG
    geo.dxf.design_point = (0.0, 0.0, 0.0)
    geo.dxf.reference_point = (500_000.0, 5_400_000.0, 0.0)
    geo.dxf.horizontal_unit_scale = 1.0
    geo.dxf.vertical_unit_scale = 0.3048  # vertical scale disagrees with $INSUNITS=6 (metres)
    geo.coordinate_system_definition = GEODATA_XML.format(epsg=4326)  # geographic, not projected
    path = tmp_path / "bad_geodata.dxf"
    doc.saveas(path)

    store = new_store("bad-geodata")
    src = store.add_source(path, HUMAN, classification=DataClassification.SYNTHETIC)
    res = ingest_site(store, src.id, mapping, AGENT)
    site = _site(store, res.site_ref)
    issue_ids = {i.id for i in site.issues}
    assert any(i.startswith("iss-geodata-crs-invalid-") for i in issue_ids)
    assert any(i.startswith("iss-geodata-unit-conflict-") for i in issue_ids)
    assert any(i.startswith("iss-geodata-transform-") for i in issue_ids)


def test_multifile_boundary_handle_with_source_prefix_and_report_outputs(
    tmp_path, ingest_many, make_survey, mapping
):
    a = make_survey(extra_boundary=False)
    b = make_survey(layers=BOUNDARY_LAYERS)
    store0, res0 = ingest_many([a, b])
    site0 = _site(store0, res0.site_ref)
    assert site0.boundary is None

    # Use source_id#handle from the first file to disambiguate across two files.
    doc_a_id = store0.get(res0.cad_refs[0], CadImportProvenance).source_document_id
    named = mapping.model_copy(update={"boundary_handle": f"{doc_a_id}#40"})
    store1, res1 = ingest_many([a, b], mapping=named)
    site1 = _site(store1, res1.site_ref)
    assert site1.boundary is not None
    assert site1.boundary.area_m2 == pytest.approx(1400.0)
    assert not any(i.id.startswith("iss-conflict-") for i in site1.issues)

    out_dir = tmp_path / "multi-report"
    package = SiteService(store1).write_review_package(res1.site_ref, out_dir)
    written = sorted(f.name for f in package.files)
    assert "cad-import.json" in written
    assert sum(name.startswith("cad-src-") for name in written) == 2


def test_partial_confirm_preserves_human_origin_and_rechecks_changed_issues(ingest):
    store, _ = ingest()
    custom_origin = (500_105.0, 5_400_205.0, 0.0)
    ref1 = confirm_site(
        store,
        "site",
        HUMAN,
        SiteConfirmation(units=LengthUnit.METRE, origin=custom_origin, epsg=27700),
    )
    site1 = _site(store, ref1)
    assert site1.coordinates.local.origin == custom_origin
    assert any(i.id == "iss-crs-area-of-use" for i in site1.issues)

    # Accept the area-of-use issue for EPSG:27700 and confirm boundary without repeating origin.
    ref2 = confirm_site(
        store,
        "site",
        HUMAN,
        SiteConfirmation(boundary_verified=True, accept_issues=["iss-crs-area-of-use"]),
    )
    site2 = _site(store, ref2)
    assert site2.coordinates.local.origin == custom_origin
    assert (
        next(i for i in site2.issues if i.id == "iss-crs-area-of-use").status
        is IssueStatus.ACCEPTED
    )

    # Changing to a different wrong EPSG (2154, RGF93 / Lambert-93) produces a new description
    # and must NOT inherit the acceptance granted for EPSG:27700.
    ref3 = confirm_site(store, "site", HUMAN, SiteConfirmation(epsg=2154))
    site3 = _site(store, ref3)
    assert (
        next(i for i in site3.issues if i.id == "iss-crs-area-of-use").status
        is IssueStatus.OPEN
    )


def test_open_segment_boundary_assembly_flags_dangling_lines(tmp_path, new_store):
    import ezdxf

    from house_ai.cad.layers import LayerRole

    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 6
    doc.layers.add("BOUNDARY")
    msp = doc.modelspace()
    s1 = msp.add_line((0, 0), (20, 0), dxfattribs={"layer": "BOUNDARY"})
    s2 = msp.add_line((20, 0), (20, 10), dxfattribs={"layer": "BOUNDARY"})
    s3 = msp.add_line((20, 10), (0, 10), dxfattribs={"layer": "BOUNDARY"})
    s4 = msp.add_line((0, 10), (0, 0), dxfattribs={"layer": "BOUNDARY"})
    dangling = msp.add_line((30, 30), (35, 35), dxfattribs={"layer": "BOUNDARY"})
    path = tmp_path / "open_boundary.dxf"
    doc.saveas(path)

    store = new_store("open-boundary")
    src = store.add_source(path, HUMAN, classification=DataClassification.SYNTHETIC)
    mapping = LayerMapping(layers={"BOUNDARY": LayerRole.BOUNDARY})
    res = ingest_site(store, src.id, mapping, AGENT)
    site = _site(store, res.site_ref)
    assert site.boundary is not None and site.boundary.area_m2 == pytest.approx(200.0)
    for h in (s1.dxf.handle, s2.dxf.handle, s3.dxf.handle, s4.dxf.handle):
        assert h in site.boundary_source_ref
    assert dangling.dxf.handle not in site.boundary_source_ref
    cad = store.get(res.cad_ref, CadImportProvenance)
    assert [a.handle for a in cad.ambiguous_entities] == [dangling.dxf.handle]


def test_degenerate_polylines_do_not_crash_inspection_or_extraction(tmp_path, new_store):
    import ezdxf

    from house_ai.cad.layers import LayerRole

    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 6
    for layer in ("BOUNDARY", "CONTOURS"):
        doc.layers.add(layer)
    msp = doc.modelspace()
    # 3 vertices where first == last -> 2 distinct vertices after closing-point removal.
    msp.add_lwpolyline([(0, 0), (10, 0), (0, 0)], close=True, dxfattribs={"layer": "BOUNDARY"})
    # Valid boundary alongside it.
    valid = msp.add_lwpolyline(
        [(0, 0), (20, 0), (20, 15), (0, 15)], close=True, dxfattribs={"layer": "BOUNDARY"}
    )
    # 1-vertex contour polyline.
    msp.add_lwpolyline([(5, 5)], dxfattribs={"layer": "CONTOURS", "elevation": 100.0})
    path = tmp_path / "degenerate.dxf"
    doc.saveas(path)

    mapping = LayerMapping(
        layers={"BOUNDARY": LayerRole.BOUNDARY, "CONTOURS": LayerRole.CONTOUR},
        boundary_handle=valid.dxf.handle,
    )
    insp = inspect_file(path, mapping)
    assert insp.readable
    assert [c.handle for c in insp.boundary_candidates] == [valid.dxf.handle]

    store = new_store("degenerate")
    src = store.add_source(path, HUMAN, classification=DataClassification.SYNTHETIC)
    res = ingest_site(store, src.id, mapping, AGENT)
    site = _site(store, res.site_ref)
    assert site.boundary is not None and site.boundary.area_m2 == pytest.approx(300.0)


def test_long_source_ids_and_point_on_area_layer(tmp_path, new_store):
    import ezdxf

    from house_ai.cad.layers import LayerRole

    def make_file(name: str, z: float) -> Path:
        doc = ezdxf.new("R2018")
        doc.header["$INSUNITS"] = 6
        for la in ("BOUNDARY", "SPOTS", "EXIST_BUILDING"):
            doc.layers.add(la)
        msp = doc.modelspace()
        if "part_1" in name:
            msp.add_lwpolyline(
                [(0, 0), (20, 0), (20, 20), (0, 20)],
                close=True,
                dxfattribs={"layer": "BOUNDARY"},
            )
            msp.add_point((5, 5, 0), dxfattribs={"layer": "EXIST_BUILDING"})
        msp.add_point((10, 10, z), dxfattribs={"layer": "SPOTS"})
        p = tmp_path / name
        doc.saveas(p)
        return p

    f1 = make_file("project_survey_package_2026_part_1.dxf", 101.0)
    f2 = make_file("project_survey_package_2026_part_2.dxf", 102.0)
    store = new_store("long-names")
    s1 = store.add_source(f1, HUMAN, classification=DataClassification.SYNTHETIC)
    s2 = store.add_source(f2, HUMAN, classification=DataClassification.SYNTHETIC)
    mapping = LayerMapping(
        layers={
            "BOUNDARY": LayerRole.BOUNDARY,
            "SPOTS": LayerRole.SPOT_ELEVATION,
            "EXIST_BUILDING": LayerRole.EXISTING_STRUCTURE,
        }
    )
    res = ingest_site(store, [s1.id, s2.id], mapping, AGENT)
    site = _site(store, res.site_ref)
    spot_ids = [s.id for s in site.terrain.spot_elevations]
    assert len(spot_ids) == 2 and len(set(spot_ids)) == 2
    assert site.features == []  # POINT on EXIST_BUILDING is flagged as ambiguous, not a point bldg
    cad1 = store.get(res.cad_refs[0], CadImportProvenance)
    assert any("existing_structure layer" in a.reason for a in cad1.ambiguous_entities)
