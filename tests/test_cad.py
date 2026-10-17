"""CAD layer: format detection, the ezdxf adapter, layer roles, raw extraction."""

from __future__ import annotations

import pytest

from house_ai.cad.dwg_oda import DwgConversionError, adapter_for
from house_ai.cad.dxf_ezdxf import DxfReadError, EzdxfAdapter
from house_ai.cad.formats import FileFormat, detect_format
from house_ai.cad.layers import LayerMapping, LayerRole, load_layer_mapping, suggest_roles

from .conftest import SURVEY_DXF, SURVEY_LAYERS


@pytest.mark.parametrize(
    ("head", "expected", "version"),
    [
        (b"AC1032\x00\x00\x00\x00", FileFormat.DWG, "AC1032"),
        (b"AC1015rest", FileFormat.DWG, "AC1015"),
        (
            b"  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1027\n",
            FileFormat.DXF_ASCII,
            "AC1027",
        ),
        (b"AutoCAD Binary DXF\r\n\x1a\x00", FileFormat.DXF_BINARY, None),
        (b"%PDF-1.7\n", FileFormat.PDF, "1.7"),
        (b"PK\x03\x04....", FileFormat.ZIP, None),
        (b'<?xml version="1.0"?><LandXML>', FileFormat.LANDXML, None),
        (b"id,x,y,z\n1,500000.0,5400000.0,101.2\n", FileFormat.TEXT, None),
        (b"\x00\x01\x02garbage", FileFormat.UNKNOWN, None),
    ],
)
def test_format_is_detected_from_bytes_not_extension(tmp_path, head, expected, version):
    path = tmp_path / "survey.dwg"  # the extension is deliberately misleading
    path.write_bytes(head)
    fmt = detect_format(path)
    assert fmt.format is expected
    assert fmt.version == version


def test_synthetic_fixture_is_a_dxf_2018():
    fmt = detect_format(SURVEY_DXF)
    assert (fmt.format, fmt.version) == (FileFormat.DXF_ASCII, "AC1032")
    assert fmt.is_cad and "AutoCAD 2018" in fmt.label


def test_inspection_reports_what_the_file_declares():
    insp = EzdxfAdapter().inspect_cad(SURVEY_DXF)
    assert insp.parser == "ezdxf" and insp.parser_version
    assert insp.declared_insunits == 6
    assert insp.declared_epsg == 25832
    assert insp.geodata["coordinate_type"] == "projected grid"
    assert insp.source_format == "dxf AC1032"
    assert insp.layers["SPOT_HEIGHTS"] == 10
    assert insp.layer_entity_types["SPOT_HEIGHTS"] == {"INSERT": 1, "POINT": 8, "TEXT": 1}
    assert insp.entity_counts["SPLINE"] == 1
    # Template defaults that look like a location are not reported.
    assert "$LATITUDE" not in insp.header and "$LONGITUDE" not in insp.header


def test_raw_extraction_keeps_source_coordinates_and_handles(survey):
    ext = EzdxfAdapter().extract_cad(SURVEY_DXF, {})
    e0, n0 = survey["E0"], survey["N0"]
    spot = next(p for p in ext.points if p.xy == (e0 + 20.0, n0 + 15.0))
    assert spot.z == pytest.approx(survey["plane_z"](20.0, 15.0))
    assert spot.entity_type == "POINT" and spot.layer == "SPOT_HEIGHTS" and spot.handle
    boundary = next(pl for pl in ext.polylines if pl.layer == "PARCEL_BOUNDARY" and pl.closed)
    assert boundary.points == [(e0 + x, n0 + y) for x, y in survey["PARCEL"]]
    assert ext.unsupported_entities == {"SPLINE": 1}
    breakline = next(pl for pl in ext.polylines if pl.entity_type == "POLYLINE")
    assert breakline.elevation is None and breakline.zs == [100.5, 101.0, 101.9]


def test_inspection_extents_are_raw_source_numbers(survey):
    insp = EzdxfAdapter().inspect_cad(SURVEY_DXF)
    x0, y0, x1, y1 = insp.extents
    assert x0 == survey["E0"] - 10.0 and y0 == survey["N0"] - 12.5
    # The SPLINE (to x = 75) is unsupported, so it is not part of the extents.
    assert x1 == survey["E0"] + 70.0 and y1 == survey["N0"] + 70.0


def test_unitless_drawing_declares_no_unit(make_survey):
    path = make_survey(declare_units=False)
    assert EzdxfAdapter().inspect_cad(path).declared_insunits == 0


def test_malformed_dxf_is_refused(tmp_path):
    bad = tmp_path / "broken.dxf"
    bad.write_text("this is not\na drawing\n")
    with pytest.raises(DxfReadError):
        EzdxfAdapter().inspect_cad(bad)


def test_truncated_dxf_is_not_silently_empty(tmp_path):
    cut = tmp_path / "truncated.dxf"
    cut.write_text("  0\nSECTION\n  2\nENTITIES\n  0\nLINE\n  8\n")
    insp = EzdxfAdapter().inspect_cad(cut)
    assert insp.entity_counts == {}
    assert any("no entities" in w for w in insp.warnings)


def test_non_cad_file_gets_no_adapter(tmp_path):
    pdf = tmp_path / "survey.dwg"
    pdf.write_bytes(b"%PDF-1.4\n%binary")
    with pytest.raises(ValueError, match="pdf"):
        adapter_for(pdf)


def test_dwg_without_a_converter_is_reported(tmp_path, monkeypatch):
    import house_ai.cad.dwg_oda as dwg

    monkeypatch.setattr(dwg, "find_oda_converter", lambda: None)
    fake = tmp_path / "survey.dwg"
    fake.write_bytes(b"AC1032" + b"\x00" * 100)
    with pytest.raises(DwgConversionError, match="no DWG reader"):
        adapter_for(fake)


def test_layer_mapping_file_and_case_insensitive_roles():
    mapping = load_layer_mapping(SURVEY_LAYERS)
    assert mapping.role_of("parcel_boundary") is LayerRole.BOUNDARY
    assert mapping.role_of("MISC_XREF") is None
    with pytest.raises(ValueError):
        LayerMapping.model_validate({"layers": {"X": "not-a-role"}})


def test_role_suggestions_are_hints_from_names_only():
    hints = suggest_roles(["GRENZE", "Hoehenlinien", "Defpoints", "SLAB", "0", "TREES"])
    assert hints["GRENZE"][0] is LayerRole.BOUNDARY
    assert hints["Hoehenlinien"][0] is LayerRole.CONTOUR
    assert hints["TREES"][0] is LayerRole.TREE
    assert "Defpoints" not in hints and "SLAB" not in hints and "0" not in hints
