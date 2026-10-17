"""Milestone B end to end: synthetic survey -> cad_import + site -> report, SVG, gate."""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from house_ai.cad.dwg_oda import OdaDwgAdapter, find_oda_converter
from house_ai.cad.layers import LayerMapping, load_layer_mapping
from house_ai.cli.main import main
from house_ai.domain.codepack import find_prohibited_claims
from house_ai.domain.epistemics import ConfirmationStatus as C
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.provenance import DataClassification
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
from house_ai.orchestration.site_ingestion import SiteConfirmation, confirm_site, ingest_site
from house_ai.orchestration.survey_inspection import inspect_file, inspection_markdown
from house_ai.orchestration.workflow import ApprovalRequiresHuman, GateBlocked, Workflow
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


def test_millimetre_drawing_gives_the_same_site(ingest, make_survey):
    store_m, res_m = ingest()
    store_mm, res_mm = ingest(make_survey(unit="mm"))
    a, b = _site(store_m, res_m.site_ref), _site(store_mm, res_mm.site_ref)
    assert b.coordinates.source_units.unit is LengthUnit.MILLIMETRE
    assert b.coordinates.local.origin == pytest.approx(a.coordinates.local.origin)
    assert validate_site(b).boundary.area_m2 == pytest.approx(1400.0, abs=1e-6)
    za = sorted(s.z_m for s in a.terrain.spot_elevations)
    zb = sorted(s.z_m for s in b.terrain.spot_elevations)
    assert zb == pytest.approx(za, abs=1e-9)


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
    store, result = ingest(make_survey(geodata=False))
    crs = _site(store, result.site_ref).coordinates.horizontal_crs
    assert crs.status is C.UNKNOWN and crs.declared_epsg is None
    assert any("horizontal CRS is unknown" in b for b in result.blockers)


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


def test_ingested_site_stops_at_needs_verification(ingest):
    store, result = ingest()
    wf = Workflow(store)
    wf.transition(WorkflowState.SITE_INGESTION, AGENT, "survey received")
    assert wf.assess_site(result.site_ref, AGENT) == result.blockers
    assert wf.state is WorkflowState.SITE_NEEDS_VERIFICATION


def test_agents_cannot_confirm_site_facts(ingest):
    store, _ = ingest()
    with pytest.raises(ApprovalRequiresHuman):
        confirm_site(store, "site", AGENT, FULL)


def test_human_confirmation_clears_blockers_and_the_human_approves(ingest):
    store, result = ingest()
    wf = Workflow(store)
    wf.transition(WorkflowState.SITE_INGESTION, AGENT, "survey received")
    wf.assess_site(result.site_ref, AGENT)
    ref = confirm_site(store, "site", HUMAN, FULL)
    site = _site(store, ref)
    assert ref.version == 2 and site_verification_blockers(site) == []
    assert site.provenance.created_by == HUMAN
    assert site.coordinates.horizontal_crs.epsg == 25832
    assert site.coordinates.local.grid_to_true_north_deg == pytest.approx(-0.00103, abs=5e-5)
    wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "verified")
    assert wf.assess_site(ref, AGENT) == []
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


def test_cli_pipeline(tmp_path, capsys):
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
                "workflow",
                "transition",
                p,
                "SITE_INGESTION",
                "--reason",
                "go",
                "--actor",
                "agent:claude-code",
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
    assert main(["workflow", "assess-site", p, "--id", "site", "--actor", "agent:claude-code"]) == 0
    out = tmp_path / "out"
    assert main(["site", "report", p, "--id", "site", "--out", str(out)]) == 0
    names = sorted(f.name for f in out.iterdir())
    assert names == [
        "cad-import.json",
        "site-report.json",
        "site-report.md",
        "site.json",
        "site.svg",
    ]
    assert main(["project", "verify", p]) == 0
    assert "SITE_NEEDS_VERIFICATION" in capsys.readouterr().out


def test_cli_site_confirm_refuses_a_non_interactive_shell(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "house_ai.cli.main",
            "site",
            "confirm",
            str(tmp_path),
            "--confirmer",
            "owner",
            "--units",
            "m",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        cwd=REPO,
    )
    assert result.returncode == 2
    assert "interactive terminal" in result.stderr


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
