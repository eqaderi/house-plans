"""Regressions for defects found when verifying the Milestone B review commit (ec25922)
and when processing a real two-file survey. All data here is synthetic."""

from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest

from house_ai.cad.base import CadInspection
from house_ai.cad.dwg_oda import OdaConverter, OdaDwgAdapter
from house_ai.cad.layers import LayerMapping, LayerRole, load_layer_mapping, suggest_roles
from house_ai.domain.epistemics import ConfirmationStatus as C
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.provenance import DataClassification
from house_ai.domain.site import CadImportProvenance, Site, SpotElevation
from house_ai.domain.units import LengthUnit
from house_ai.geospatial.validation import report_markdown, validate_site
from house_ai.orchestration.site_ingestion import SiteConfirmation, confirm_site, ingest_site
from house_ai.orchestration.survey_inspection import inspect_file

from .conftest import AGENT, HUMAN, SURVEY_LAYERS

BOUNDARY_LAYERS = {"PARCEL_BOUNDARY", "ROAD", "EXIST_BUILDING", "TREES", "ACCESS", "TEXT_ANNO"}
HEIGHT_LAYERS = {"CONTOURS", "SPOT_HEIGHTS"}


@pytest.fixture
def mapping() -> LayerMapping:
    return load_layer_mapping(SURVEY_LAYERS)


def _add(store, path: Path) -> str:
    return store.add_source(path, HUMAN, classification=DataClassification.SYNTHETIC).id


def _parcel_handle(path: Path) -> str:
    return next(
        e.dxf.handle
        for e in ezdxf.readfile(path).modelspace()
        if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "PARCEL_BOUNDARY"
    )


# ------------------------------------------------------------ confirmation


def test_a_failed_confirmation_writes_nothing(new_store, make_survey, mapping):
    store = new_store("synthetic-survey")
    sid = _add(store, make_survey())
    ingest_site(store, sid, mapping, AGENT)
    before = store.refs()
    with pytest.raises(ValueError, match="iss-typo"):
        confirm_site(
            store,
            "site",
            HUMAN,
            SiteConfirmation(units=LengthUnit.METRE, accept_issues=["iss-typo"]),
        )
    assert store.refs() == before  # no cad_import claims a confirmation that never happened


# ------------------------------------------------- handles across several files


def test_bare_handles_are_refused_when_several_files_are_ingested(new_store, make_survey, mapping):
    a, b = make_survey(layers=BOUNDARY_LAYERS), make_survey(layers=HEIGHT_LAYERS)
    handle = _parcel_handle(a)
    store = new_store("synthetic-survey")
    ids = [_add(store, a), _add(store, b)]
    bare_boundary = mapping.model_copy(update={"boundary_handle": handle})
    with pytest.raises(ValueError, match="source_id#handle"):
        ingest_site(store, ids, bare_boundary, AGENT)
    bare_role = mapping.model_copy(update={"handle_roles": {handle: LayerRole.TREE}})
    with pytest.raises(ValueError, match="source_id#handle"):
        ingest_site(store, ids, bare_role, AGENT)
    assert store.refs(K.SITE) == []

    named = mapping.model_copy(update={"boundary_handle": f"{ids[0]}#{handle}"})
    site = store.get(ingest_site(store, ids, named, AGENT).site_ref, Site)
    assert site.boundary is not None and site.boundary.area_m2 == pytest.approx(1400.0)
    assert not [i for i in site.issues if i.id.startswith("iss-conflict")]
    assert len(site.terrain.spot_elevations) == 8  # nothing taken from the other file


def test_a_handle_prefix_must_name_an_ingested_file(new_store, make_survey, mapping):
    path = make_survey()
    store = new_store("synthetic-survey")
    sid = _add(store, path)
    typo = mapping.model_copy(update={"boundary_handle": f"src-typo#{_parcel_handle(path)}"})
    with pytest.raises(ValueError, match="src-typo"):
        ingest_site(store, sid, typo, AGENT)
    typo_role = mapping.model_copy(update={"handle_roles": {"src-typo#40": LayerRole.TREE}})
    with pytest.raises(ValueError, match="src-typo"):
        ingest_site(store, sid, typo_role, AGENT)


def test_each_cad_import_states_its_own_files_units(new_store, make_survey, mapping):
    store = new_store("synthetic-survey")
    ids = [
        _add(store, make_survey(layers=BOUNDARY_LAYERS)),
        _add(store, make_survey(unit="mm", layers=HEIGHT_LAYERS)),
    ]
    result = ingest_site(store, ids, mapping, AGENT)
    a, b = (store.get(r, CadImportProvenance) for r in result.cad_refs)
    assert (a.drawing_units.unit, a.drawing_units.status) == (
        LengthUnit.METRE,
        C.DECLARED_IN_SOURCE,
    )
    assert (b.drawing_units.unit, b.drawing_units.status) == (
        LengthUnit.MILLIMETRE,
        C.DECLARED_IN_SOURCE,
    )
    ref = confirm_site(
        store,
        "site",
        HUMAN,
        SiteConfirmation(units=LengthUnit.METRE, elevation_units=LengthUnit.METRE),
    )
    cads = [
        store.get(r, CadImportProvenance)
        for r in store.get(ref, Site).provenance.inputs
        if r.kind is K.CAD_IMPORT
    ]
    by_id = {c.source_document_id: c for c in cads}
    assert by_id[ids[0]].drawing_units.status is C.USER_CONFIRMED
    # The human confirmed metres for the site; the file that says millimetres still says so.
    assert by_id[ids[1]].drawing_units.unit is LengthUnit.MILLIMETRE
    assert by_id[ids[1]].drawing_units.status is C.DECLARED_IN_SOURCE


# ------------------------------------------------------------------- ids


def test_similar_long_source_ids_give_distinct_entity_ids(new_store, make_survey, mapping):
    store = new_store("synthetic-survey")
    ids = []
    for part, layers in (("north", {"SPOT_HEIGHTS"}), ("south", HEIGHT_LAYERS)):
        doc = store.add_source(
            make_survey(layers=layers),
            HUMAN,
            classification=DataClassification.SYNTHETIC,
            source_id=f"src-site-survey-2026-{part}-part-final",
        )
        ids.append(doc.id)
    # Both files hold the same spot heights; every entity must still get its own id.
    result = ingest_site(store, [ids[0]], mapping, AGENT)
    one = store.get(result.site_ref, Site)
    result = ingest_site(store, ids, mapping, AGENT)
    both = store.get(result.site_ref, Site)
    spot_ids = [s.id for s in both.terrain.spot_elevations]
    contour_ids = [c.id for c in both.terrain.contours]
    assert len(set(spot_ids)) == len(spot_ids) == 2 * len(one.terrain.spot_elevations)
    assert len(set(contour_ids)) == len(contour_ids)


def test_a_site_with_duplicate_ids_is_rejected(site):
    spot = SpotElevation(id="spot-a", xy=(1.0, 1.0), z_m=1.0)
    terrain = site.terrain.model_copy(update={"spot_elevations": [spot, spot]})
    with pytest.raises(ValueError, match="duplicate"):
        Site.model_validate({**site.model_dump(), "terrain": terrain.model_dump()})


# ------------------------------------------------------------ inspection


def test_point_layers_are_hinted_by_what_they_hold():
    hints = suggest_roles(["TREE_POINTS", "UTILITY_POINT", "SPOT_POINTS", "ACCESS_POINT"])
    assert hints["TREE_POINTS"][0] is LayerRole.TREE
    assert hints["ACCESS_POINT"][0] is LayerRole.ACCESS_POINT
    assert hints["UTILITY_POINT"][0] is LayerRole.UTILITY
    assert hints["SPOT_POINTS"][0] is LayerRole.SPOT_ELEVATION


def test_inspection_understands_source_prefixed_handles(make_survey, mapping, tmp_path):
    path = make_survey()
    named = tmp_path / "survey.dxf"
    named.write_bytes(path.read_bytes())
    m = mapping.model_copy(update={"boundary_handle": f"src-survey#{_parcel_handle(named)}"})
    report = inspect_file(named, m)
    assert not [a for a in report.ambiguous if "not chosen" in a.reason]


def test_dwg_inspection_reports_the_dwg_release_not_the_converted_one(tmp_path):
    dwg = tmp_path / "x.dwg"
    dwg.write_bytes(b"AC1021" + b"\0" * 64)
    adapter = OdaDwgAdapter(OdaConverter(Path("/nonexistent"), "27.9"))
    dxf = tmp_path / "x.dxf"
    dxf.write_text("0\nEOF\n")
    converted = CadInspection(
        parser="ezdxf", parser_version="1", declared_insunits=6, header={"$ACADVER": "AC1032"}
    )
    out = adapter._annotate(dwg, dxf, converted)
    assert out.source_format == "dwg AC1021"
    assert out.header.get("$ACADVER") == "AC1021"


# -------------------------------------------- height labels as a cross-check


def _labelled_spots(path: Path, labels: list[tuple[tuple[float, float, float], str]]) -> Path:
    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 6
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (30, 0), (30, 20), (0, 20)], close=True)
    for (x, y, z), text in labels:
        msp.add_point((x, y, z))
        msp.add_mtext(text, dxfattribs={"insert": (x, y)})
    doc.saveas(path)
    return path


def test_height_labels_at_a_point_cross_check_its_elevation(tmp_path, new_store):
    path = _labelled_spots(
        tmp_path / "labels.dxf",
        [
            ((5, 5, 101.234), "Pt1\\P101.234"),  # agrees
            ((10, 5, 102.5), "Pt2\\P102.500"),  # agrees
            ((20, 10, 103.0), "Pt3"),  # name only
        ],
    )
    store = new_store("labels")
    sid = _add(store, path)
    mapping = LayerMapping(layers={"0": LayerRole.SPOT_ELEVATION})
    mapping = mapping.model_copy(update={"boundary_handle": f"{sid}#{_first_polyline(path)}"})
    result = ingest_site(store, sid, mapping, AGENT)
    site = store.get(result.site_ref, Site)
    cad = store.get(result.cad_ref, CadImportProvenance)
    assert len(site.terrain.spot_elevations) == 3
    assert sorted(c.label_value for c in cad.height_label_checks) == [101.234, 102.5]
    assert all(c.agrees for c in cad.height_label_checks)
    reasons = [a.reason for a in cad.ambiguous_entities]
    assert len(reasons) == 1 and "point name" in reasons[0]
    assert not [i for i in site.issues if i.severity.value == "blocking" and "label" in i.title]


def test_a_height_label_that_disagrees_with_its_point_blocks(tmp_path, new_store):
    path = _labelled_spots(
        tmp_path / "bad-label.dxf",
        [((5, 5, 101.234), "Pt1\\P101.334"), ((10, 5, 102.0), "Pt2\\P102.000")],
    )
    store = new_store("labels")
    sid = _add(store, path)
    mapping = LayerMapping(
        layers={"0": LayerRole.SPOT_ELEVATION}, boundary_handle=f"{sid}#{_first_polyline(path)}"
    )
    result = ingest_site(store, sid, mapping, AGENT)
    site = store.get(result.site_ref, Site)
    assert len(site.terrain.spot_elevations) == 1  # the disputed point is not used
    assert any(
        i.severity.value == "blocking" and "101.334" in i.title and "101.234" in i.title
        for i in site.issues
    )


def _first_polyline(path: Path) -> str:
    return next(
        e.dxf.handle for e in ezdxf.readfile(path).modelspace() if e.dxftype() == "LWPOLYLINE"
    )


# ------------------------------------------------------------ steep terrain


def test_slope_report_distinguishes_survey_hull_from_clipped_parcel(site):
    from house_ai.domain.geometry import Polygon2D
    from house_ai.domain.site import Terrain, TinSurface

    # Two planes: 10% over 1 m² and 100% over 4 m². Only 0.75 m² of the
    # first triangle intersects the parcel. No private survey data is used.
    surface = TinSurface(
        vertices=[(0, 0, 0), (2, 0, 0.2), (0, 1, 0),
                  (10, 0, 0), (14, 0, 4), (10, 2, 0)],
        triangles=[(0, 1, 2), (3, 4, 5)],
    )
    site = site.model_copy(update={
        "boundary": Polygon2D(outer=[(0, 0), (1, 0), (1, 1), (0, 1)]),
        "terrain": Terrain(surface=surface),
    })
    report = validate_site(site)
    assert report.terrain.mean_slope_pct == pytest.approx(82.0)
    assert report.terrain.parcel_mean_slope_pct == pytest.approx(10.0)
    assert report.terrain.parcel_tin_area_m2 == pytest.approx(0.75)
    assert "whole survey TIN" in report_markdown(report)
    assert "parcel intersection" in report_markdown(report)
    from house_ai.domain.provenance import ArtifactRef
    from house_ai.orchestration.site_context import site_context_for

    ref = ArtifactRef(kind=K.SITE, id="site", version=1, sha256="0" * 64)
    assert site_context_for(site, ref, None).mean_slope_pct == pytest.approx(10.0)
    # Unknown or uncovered boundary cannot silently substitute the whole survey.
    no_boundary = site.model_copy(update={"boundary": None})
    assert validate_site(no_boundary).terrain.parcel_mean_slope_pct is None
    assert site_context_for(no_boundary, ref, None).mean_slope_pct is None
    outside = site.model_copy(update={
        "boundary": Polygon2D(outer=[(20, 0), (21, 0), (21, 1), (20, 1)]),
    })
    assert validate_site(outside).terrain.parcel_mean_slope_pct is None
    assert validate_site(outside).terrain.parcel_tin_area_m2 == 0


def test_source_audit_replays_synthetic_entities_without_writing_store(tmp_path, new_store):
    import runpy
    import shutil

    from .conftest import REPO

    path = _labelled_spots(tmp_path / "audit.dxf", [
        ((2, 2, 100.0), "A\\P100.000"),
        ((28, 2, 100.0), "B\\P100.000"),
        ((15, 18, 108.0), "C\\P108.000"),
    ])
    store = new_store("audit-synthetic")
    sid = _add(store, path)
    mapping = LayerMapping(
        layers={"0": LayerRole.SPOT_ELEVATION}, boundary_handle=f"{sid}#{_first_polyline(path)}"
    )
    ingest_site(store, sid, mapping, AGENT)
    (store.root / "site").mkdir()
    (store.root / "site/layers.yaml").write_text(mapping.model_dump_json())
    (store.root / "surveys").mkdir()
    shutil.copyfile(path, store.root / "surveys" / path.name)
    events_before = (store.root / "events.jsonl").read_bytes()
    audit = runpy.run_path(str(REPO / "tools/audit_site.py"))["audit"]
    first = audit(store.root)
    assert first["semantic_sha256"] == audit(store.root)["semantic_sha256"]
    assert len(first["points"]) == 3
    assert len(first["sources"][0]["label_checks"]) == 3
    assert first["fresh_geometry_matches_stored"]
    assert first["metrics"]["all_spot_relief_m"] == pytest.approx(8.0)
    assert first["metrics"]["arithmetic_triangle_mean_pct"] == pytest.approx(50.0)
    assert (store.root / "events.jsonl").read_bytes() == events_before
    assert store.verify() == []


def test_implausibly_steep_tin_triangles_are_reported(tmp_path, new_store):
    path = _labelled_spots(
        tmp_path / "steep.dxf",
        [
            ((2, 2, 100.0), "A\\P100.000"),
            ((28, 2, 100.5), "B\\P100.500"),
            ((15, 18, 101.0), "C\\P101.000"),
            ((15.5, 18, 103.0), "D\\P103.000"),  # 2 m rise over 0.5 m: a wall or an error
        ],
    )
    store = new_store("steep")
    sid = _add(store, path)
    mapping = LayerMapping(
        layers={"0": LayerRole.SPOT_ELEVATION}, boundary_handle=f"{sid}#{_first_polyline(path)}"
    )
    site = store.get(ingest_site(store, sid, mapping, AGENT).site_ref, Site)
    report = validate_site(site)
    steep = [f for f in report.findings if f.code == "steep_terrain"]
    assert len(steep) == 1 and steep[0].severity.value == "warning"
    assert "spot-steep-" in steep[0].message
    assert report.terrain.max_slope_pct > 100


def test_each_steep_triangle_is_listed_with_its_measurements(tmp_path, new_store):
    path = _labelled_spots(
        tmp_path / "steep.dxf",
        [
            ((2, 2, 100.0), "A\\P100.000"),
            ((28, 2, 100.5), "B\\P100.500"),
            ((15, 18, 101.0), "C\\P101.000"),
            ((15.5, 18, 103.0), "D\\P103.000"),
        ],
    )
    store = new_store("steep")
    sid = _add(store, path)
    mapping = LayerMapping(
        layers={"0": LayerRole.SPOT_ELEVATION}, boundary_handle=f"{sid}#{_first_polyline(path)}"
    )
    site = store.get(ingest_site(store, sid, mapping, AGENT).site_ref, Site)
    by_xy = {tuple(round(v, 6) for v in s.xy): s.id for s in site.terrain.spot_elevations}
    origin = site.coordinates.local.origin
    ids = {
        k: by_xy[(round(x - origin[0], 6), round(y - origin[1], 6))]
        for k, (x, y) in {"A": (2, 2), "B": (28, 2), "C": (15, 18), "D": (15.5, 18)}.items()
    }
    report = validate_site(site)
    steep = report.terrain.steep_triangles
    # Whichever diagonal Delaunay picks, exactly one triangle holds C and D (2 m over
    # 0.5 m). By hand: plane A-C-D has gradient sqrt(32² + 25.5²) / 8 = 511.5 %, plane
    # B-C-D sqrt(32² + 26.25²) / 8 = 517.4 %; A-B-C and A-B-D are under 20 %.
    assert len(steep) == 1
    t = steep[0]
    third = ({ids["A"], ids["B"]} & set(t.vertices)).pop()
    expected = 511.5 if third == ids["A"] else 517.4
    assert t.slope_pct == pytest.approx(expected, abs=0.1)
    assert t.pair == (ids["D"], ids["C"])
    assert t.pair_distance_m == pytest.approx(0.5)
    assert t.pair_dz_m == pytest.approx(2.0)
    assert t.sources == [sid]
    assert t.edge_rise_pct == pytest.approx(400.0)
    assert {"sliver", "close pair", "on survey edge"} <= set(t.traits)
    assert "mixes sources" not in t.traits and "no steep edge" not in t.traits
    assert report.terrain.tin_triangles == 2  # nothing removed or smoothed
    assert "steep triangles" in report_markdown(report).lower()


def test_a_thin_triangle_can_be_steep_although_none_of_its_edges_is(tmp_path, new_store):
    # Edges rise 1 m over 15 m (6.7 %) at most, but across its 0.2 m width the plane
    # through the three points rises 1 m: 500 %. The shape, not a surveyed pair, makes it steep.
    path = _labelled_spots(
        tmp_path / "sliver.dxf",
        [((0, 5, 100.0), "A"), ((30, 5, 100.0), "B"), ((15, 5.2, 101.0), "C")],
    )
    store = new_store("sliver")
    sid = _add(store, path)
    mapping = LayerMapping(
        layers={"0": LayerRole.SPOT_ELEVATION}, boundary_handle=f"{sid}#{_first_polyline(path)}"
    )
    site = store.get(ingest_site(store, sid, mapping, AGENT).site_ref, Site)
    (t,) = validate_site(site).terrain.steep_triangles
    assert t.slope_pct == pytest.approx(500.0)
    assert t.edge_rise_pct == pytest.approx(100 / 15.0013, rel=1e-3)
    assert {"sliver", "no steep edge"} <= set(t.traits) and "close pair" not in t.traits


# ------------------------------------------------------------ review package


def test_road_lines_running_parallel_report_their_separation(new_store, make_survey, mapping):
    import ezdxf as _ezdxf

    path = make_survey()
    doc = _ezdxf.readfile(path)
    doc.modelspace().add_lwpolyline(
        [(0, -9), (60, -9)], dxfattribs={"layer": "ROAD"}
    )  # placed relative to nothing: only the separation from another road line matters
    doc.modelspace().add_lwpolyline([(0, -18), (60, -18)], dxfattribs={"layer": "ROAD"})
    doc.saveas(path)
    store = new_store("synthetic-survey")
    site = store.get(ingest_site(store, _add(store, path), mapping, AGENT).site_ref, Site)
    widths = validate_site(site).frontage.road_widths
    nine = [w for w in widths if abs(w.min_m - 9.0) < 1e-6 and abs(w.max_m - 9.0) < 1e-6]
    assert len(nine) == 1


def test_terrain_svg_shades_slope_and_labels_calculated_contours(new_store, mapping):
    from house_ai.render2d.terrain_svg import render_terrain_svg, slope_class

    from .conftest import SURVEY_DXF

    store = new_store("synthetic-survey")
    site = store.get(ingest_site(store, _add(store, SURVEY_DXF), mapping, AGENT).site_ref, Site)
    report = validate_site(site)
    svg = render_terrain_svg(site, report)
    assert svg == render_terrain_svg(site, report)  # deterministic
    # The synthetic plane z = 100 + 0.05x + 0.1y has slope 11.18 %: one class only.
    assert slope_class(11.18) == 1 and "5–15 %: 100 % of TIN area" in svg
    assert "interpolated from the TIN, not surveyed" in svg
    assert "north not established" in svg
    assert svg.count("calculated contour") >= 3


def test_review_page_labels_how_each_value_is_known(tmp_path, capsys):
    from house_ai.cli.main import main

    from .conftest import SURVEY_DXF

    p = tmp_path / "proj"
    actor = ["--actor", "human:example-owner"]
    assert (
        main(
            [
                "project",
                "init",
                str(p),
                "--id",
                "demo",
                "--name",
                "Demo <x>",
                "--classification",
                "synthetic",
                *actor,
            ]
        )
        == 0
    )
    assert (
        main(["source", "add", str(p), str(SURVEY_DXF), "--classification", "synthetic", *actor])
        == 0
    )
    assert (
        main(
            [
                "site",
                "ingest",
                str(p),
                "--source",
                "src-survey",
                "--layers",
                str(SURVEY_LAYERS),
                *actor,
            ]
        )
        == 0
    )
    out = tmp_path / "report"
    assert main(["site", "report", str(p), "--id", "site", "--out", str(out)]) == 0
    html = (out / "index.html").read_text()
    assert (out / "terrain.svg").is_file()
    for heading in (
        "1. Parcel boundary drawing",
        "4. Surveyed elevation points",
        "6. Terrain slope",
        "9. Coordinate system",
    ):
        assert heading in html
    for tag in ("measured", "calculated", "interpretation", "unknown"):
        assert f'class="tag {tag}"' in html
    assert "Demo &lt;x&gt;" in html and "Demo <x>" not in html
    assert "<b>Not approved.</b>" in html
    assert "<script" not in html and "http://" not in html.replace(
        'xmlns="http://www.w3.org/2000/svg"', ""
    )


def test_elevation_labels_with_inline_units_point_names_and_point_id_lines():
    from house_ai.cad.site_extract import has_numeric_elevation_label, numeric_label_values

    assert has_numeric_elevation_label("1664.0 m")
    assert numeric_label_values("1664.0 m")[0][0] == pytest.approx(1664.0)
    assert has_numeric_elevation_label("Pt1 101.25")
    assert numeric_label_values("Pt1 101.25")[0][0] == pytest.approx(101.25)
    assert has_numeric_elevation_label("EL=1665.378 m")
    assert numeric_label_values("EL=1665.378 m")[0][0] == pytest.approx(1665.378)
    assert not has_numeric_elevation_label("Pt\n12")
    assert numeric_label_values("Pt\n12") == []
    assert numeric_label_values("Pt\n12\n1664.884")[0][0] == pytest.approx(1664.884)


def test_inspection_boundary_candidates_honor_handle_roles_and_case_insensitive_layers(tmp_path):
    from house_ai.orchestration.survey_inspection import inspect_file

    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 6
    doc.layers.add("PARCEL_LAYER")
    msp = doc.modelspace()
    c1 = msp.add_lwpolyline(
        [(0, 0), (20, 0), (20, 30), (0, 30)], close=True, dxfattribs={"layer": "0"}
    )
    c2 = msp.add_lwpolyline(
        [(0, 0), (50, 0), (50, 50), (0, 50)], close=True, dxfattribs={"layer": "PARCEL_LAYER"}
    )
    path = tmp_path / "seperated.dxf"
    doc.saveas(path)

    # 1. boundary_handle with source_id#handle selects only c1 on layer "0"
    m_handle = LayerMapping(
        layers={"0": LayerRole.SPOT_ELEVATION},
        boundary_handle=f"src-seperated#{c1.dxf.handle}",
    )
    insp_h = inspect_file(path, m_handle)
    assert [c.handle for c in insp_h.boundary_candidates] == [c1.dxf.handle]
    assert "boundary_handle" in insp_h.boundary_candidate_basis

    # 2. Case-insensitive layer name in mapping selects c2 on "PARCEL_LAYER"
    m_layer = LayerMapping(layers={"parcel_layer": LayerRole.BOUNDARY})
    insp_l = inspect_file(path, m_layer)
    assert [c.handle for c in insp_l.boundary_candidates] == [c2.dxf.handle]


def test_site_svg_renders_point_features_with_colour_and_title(new_store, mapping):
    from house_ai.domain.site import PointGeometry, SiteFeature, SiteFeatureKind
    from house_ai.render2d.site_svg import COLOURS, render_site_svg

    from .conftest import SURVEY_DXF

    store = new_store("synthetic-survey")
    site = store.get(ingest_site(store, _add(store, SURVEY_DXF), mapping, AGENT).site_ref, Site)
    site_with_pts = site.model_copy(
        update={
            "features": [
                *site.features,
                SiteFeature(
                    id="util-pole-1",
                    kind=SiteFeatureKind.UTILITY,
                    geometry=PointGeometry(xy=(12.0, 8.0)),
                ),
                SiteFeature(
                    id="well-1",
                    kind=SiteFeatureKind.WATER,
                    geometry=PointGeometry(xy=(18.0, 12.0)),
                ),
            ]
        }
    )
    svg = render_site_svg(site_with_pts, validate_site(site_with_pts))
    assert f'fill="{COLOURS["utility"]}"><title>util-pole-1 (utility)</title></circle>' in svg
    assert f'fill="{COLOURS["water"]}"><title>well-1 (water)</title></circle>' in svg


def test_multifile_crs_disagreement_includes_rejected_geodata_epsg(tmp_path, new_store, mapping):
    from examples.surveys.synthetic.make_survey import GEODATA_XML, PARCEL

    from .conftest import SURVEY_DXF

    doc = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 6
    doc.layers.add("PARCEL_BOUNDARY")
    msp = doc.modelspace()
    msp.add_lwpolyline(PARCEL, close=True, dxfattribs={"layer": "PARCEL_BOUNDARY"})
    geo = msp.new_geodata()
    geo.dxf.coordinate_type = 2
    geo.coordinate_system_definition = GEODATA_XML.format(epsg=4326)  # geographic -> rejected
    bad_crs_path = tmp_path / "part2_4326.dxf"
    doc.saveas(bad_crs_path)

    store = new_store("crs-disagree")
    s1 = _add(store, SURVEY_DXF)  # declares EPSG:25832
    s2 = _add(store, bad_crs_path)  # declares EPSG:4326 (rejected as non-projected)
    res = ingest_site(store, [s1, s2], mapping, AGENT)
    site = store.get(res.site_ref, Site)
    issue_ids = {i.id for i in site.issues}
    assert "iss-sources-disagree-crs" in issue_ids
    assert any(i.startswith("iss-geodata-crs-invalid-") for i in issue_ids)

