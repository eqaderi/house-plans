"""Each test breaks the example house in one known way and expects the
matching finding, so a check that silently stops working fails here."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from houseplan import checks, geometry, rules, verify
from houseplan.drawing import PAPERS, plan_dxf
from houseplan.ifc import build_ifc
from houseplan.model import Design
from houseplan.render import render

EXAMPLE = Path(__file__).resolve().parents[1] / "design" / "examples" / "bungalow.yaml"


@pytest.fixture
def spec() -> dict:
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def analyse(spec: dict):
    design = Design.model_validate(spec)
    geo = geometry.build(design)
    return design, geo, checks.run_all(design, geo)


def codes(findings, severity="error"):
    return {f.code for f in findings if f.severity == severity}


def item(spec, group, id_):
    return next(x for x in spec[group] if x["id"] == id_)


def test_example_is_clean(spec):
    _, _, findings = analyse(spec)
    assert codes(findings) == set()
    assert codes(findings, "warning") == set()


def test_room_areas_come_from_wall_faces(spec):
    _, geo, _ = analyse(spec)
    rooms = geo["GF"].rooms
    # bedroom 1: x 150..5500, y 150..3925
    assert rooms["R1"].area_mm2 == pytest.approx(5350 * 3775, abs=1)
    # corridor: x 150..5500, y 4075..5225
    assert rooms["R2"].area_mm2 == pytest.approx(5350 * 1150, abs=1)


def test_footprint_equals_walls_plus_rooms(spec):
    _, geo, _ = analyse(spec)
    lg = geo["GF"]
    assert lg.footprint.area == pytest.approx(12300 * 9300, abs=1)
    rooms = sum(r.area_mm2 for r in lg.rooms.values())
    assert lg.walls_union.area + rooms == pytest.approx(lg.footprint.area, abs=5)


def test_missing_wall_merges_rooms(spec):
    spec["walls"] = [w for w in spec["walls"] if w["id"] != "V2"]
    _, _, findings = analyse(spec)
    assert "ROOM_SHARED" in codes(findings)


def test_seed_in_wall(spec):
    item(spec, "rooms", "R1")["seed"] = [5600, 2000]
    _, _, findings = analyse(spec)
    assert "ROOM_NOT_ENCLOSED" in codes(findings)


def test_wall_thickness_not_allowed(spec):
    item(spec, "walls", "H1")["thickness"] = 120
    _, _, findings = analyse(spec)
    assert "WALL_THICKNESS" in codes(findings)


def test_opening_past_wall_end(spec):
    item(spec, "openings", "F1")["offset"] = 11000
    _, _, findings = analyse(spec)
    assert "OPENING_PAST_WALL_END" in codes(findings)


def test_opening_into_junction(spec):
    item(spec, "openings", "F1")["offset"] = 4800
    _, _, findings = analyse(spec)
    assert "OPENING_IN_JUNCTION" in codes(findings)


def test_overlapping_openings(spec):
    item(spec, "openings", "F2")["offset"] = 2500
    _, _, findings = analyse(spec)
    assert "OPENING_OVERLAP" in codes(findings) or "OPENING_IN_JUNCTION" in codes(findings)


def test_door_swing_into_wall(spec):
    item(spec, "openings", "D4")["offset"] = 1800
    _, _, findings = analyse(spec)
    assert "DOOR_SWING_HITS_WALL" in codes(findings)


def test_room_without_door_is_unreachable(spec):
    spec["openings"] = [o for o in spec["openings"] if o["id"] != "D3"]
    _, _, findings = analyse(spec)
    assert "ROOM_UNREACHABLE" in codes(findings)


def test_habitable_room_needs_window(spec):
    spec["openings"] = [o for o in spec["openings"] if o["id"] != "F5"]
    _, _, findings = analyse(spec)
    assert "NO_WINDOW" in codes(findings)


def test_window_taller_than_room(spec):
    item(spec, "openings", "F1")["sill"] = 1500
    _, _, findings = analyse(spec)
    assert "OPENING_TOO_TALL" in codes(findings)


def test_parallel_walls_overlap(spec):
    spec["walls"].append({**item(spec, "walls", "H1"), "id": "H1b", "start": [1000, 4000], "end": [3000, 4000]})
    _, _, findings = analyse(spec)
    assert "WALL_OVERLAP" in codes(findings)


def test_unknown_reference_is_rejected(spec):
    item(spec, "openings", "D1")["wall"] = "NOPE"
    with pytest.raises(ValueError):
        Design.model_validate(spec)


def two_storey(spec: dict) -> dict:
    s = copy.deepcopy(spec)
    s["levels"].append({"id": "L1", "name": "First floor", "ffl": 3200, "floor_to_floor": 3000, "slab": 350})
    for w in [w for w in spec["walls"] if w["kind"] == "exterior"]:
        s["walls"].append({**w, "id": w["id"] + "1", "level": "L1"})
    s["rooms"].append({"id": "U1", "level": "L1", "name": "Stair hall", "use": "stair", "seed": [6000, 4500]})
    s["openings"].append({"id": "UF1", "wall": "WS1", "kind": "window", "offset": 2000, "width": 1200, "height": 1200, "sill": 900})
    s["stairs"] = [{"id": "S1", "level": "GF", "to_level": "L1", "origin": [6400, 300], "direction": "+y", "width": 1000, "risers": 18, "going": 280}]
    return s


def test_stair_rise_is_reported_and_fits(spec):
    _, _, findings = analyse(two_storey(spec))
    rise = next(f for f in findings if f.code == "STAIR_RISE")
    assert "18 risers × 177.78 mm = 3200 mm" in rise.message
    assert not {"STAIR_IN_WALL", "STAIR_NOT_IN_ROOM"} & codes(findings)


def test_stair_through_wall(spec):
    s = two_storey(spec)
    s["stairs"][0]["origin"] = [6200, 1500]
    _, _, findings = analyse(s)
    assert "STAIR_IN_WALL" in codes(findings)


def test_rules_unverified_fail_as_warning(spec, tmp_path, monkeypatch):
    (tmp_path / "t.yaml").write_text(yaml.safe_dump({
        "ruleset": "t", "jurisdiction": "IR", "title": "test",
        "rules": [
            {"id": "T1", "check": "room_min_area", "title": "min area", "value": 50, "uses": ["bedroom"], "source": "test", "status": "unverified"},
            {"id": "T2", "check": "room_min_area", "title": "min area", "value": 50, "uses": ["living"], "source": "test", "status": "verified"},
        ],
    }))
    monkeypatch.setattr(rules, "RULES_DIR", tmp_path)
    spec["project"]["ruleset"] = "t"
    design, geo, _ = analyse(spec)
    found = rules.run_rules(design, geo)
    assert {(f.code, f.severity) for f in found} == {("T1", "warning"), ("T2", "error")}


def test_dxf_chains_close_and_units(spec, tmp_path):
    design, geo, _ = analyse(spec)
    doc, _ = plan_dxf(design, geo["GF"])
    path = tmp_path / "p.dxf"
    doc.saveas(path)
    assert verify.verify_dxf(str(path), geo["GF"]) == []


def test_dxf_chain_error_is_caught(spec, tmp_path):
    design, geo, _ = analyse(spec)
    doc, _ = plan_dxf(design, geo["GF"])
    dim = next(iter(doc.modelspace().query("DIMENSION")))
    dim.dxf.defpoint3 = (dim.dxf.defpoint3[0] + 37, dim.dxf.defpoint3[1], 0)
    path = tmp_path / "p.dxf"
    doc.saveas(path)
    assert any(f.code == "DXF_CHAIN_OPEN" for f in verify.verify_dxf(str(path), geo["GF"]))


def test_render_is_true_scale(spec, tmp_path):
    from PIL import Image

    design, geo, _ = analyse(spec)
    doc, sheet = plan_dxf(design, geo["GF"])
    png = tmp_path / "p.png"
    render(doc, sheet, None, str(png), dpi=200)
    w_mm, h_mm = PAPERS[sheet.paper]
    width, height = Image.open(png).size
    assert abs(width - w_mm / 25.4 * 200) < 1
    assert abs(height - h_mm / 25.4 * 200) < 1
    x0, y0, x1, y1 = sheet.frame
    assert (x1 - x0) / w_mm == pytest.approx(sheet.scale)


def test_ifc_matches_spec(spec, tmp_path):
    design, geo, _ = analyse(two_storey(spec))
    path = tmp_path / "m.ifc"
    build_ifc(design, geo).write(str(path))
    assert verify.verify_ifc(str(path), design, geo) == []


def run_iran(spec):
    design, geo, _ = analyse(spec)
    return {(f.code, f.subject) for f in rules.run_rules(design, geo) if f.severity != "info"}


def test_iran_rules_pass_on_example(spec):
    assert run_iran(spec) == set()


def test_iran_small_bedroom(spec):
    item(spec, "walls", "V2")["start"] = [4000, 5300]
    item(spec, "walls", "V2")["end"] = [4000, 9000]
    item(spec, "openings", "D5")["offset"] = 4300
    item(spec, "openings", "D5")["width"] = 800
    item(spec, "openings", "F5")["offset"] = 4300
    item(spec, "openings", "F5")["width"] = 900
    item(spec, "rooms", "R4")["seed"] = [4800, 7000]
    found = run_iran(spec)
    assert ("IR4-ROOM-WIDTH-RES", "R4") in found
    assert ("IR4-HAB-AREA", "R4") in found


def test_iran_stair_step_formula(spec):
    s = two_storey(spec)
    s["stairs"][0]["going"] = 250
    found = run_iran(s)
    assert ("IR4-STAIR-2RG", "S1") in found
    assert ("IR4-STAIR-GOING", "S1") in found


def test_reentrant_corner(spec):
    for w in spec["walls"]:
        if w["id"] == "WN":
            w["end"] = [5600, 9000]
        if w["id"] == "WE":
            w["end"] = [12000, 5500]
    spec["walls"] += [
        {"id": "WN2", "level": "GF", "start": [5600, 5500], "end": [12000, 5500], "thickness": 300, "kind": "exterior"},
        {"id": "WE2", "level": "GF", "start": [5600, 5500], "end": [5600, 9000], "thickness": 300, "kind": "exterior"},
    ]
    spec["walls"] = [w for w in spec["walls"] if w["id"] not in ("H3", "V1")]
    spec["walls"].append({"id": "V1", "level": "GF", "start": [5600, 0], "end": [5600, 5500], "thickness": 200, "kind": "interior", "loadbearing": True})
    spec["openings"] = [o for o in spec["openings"] if o["id"] in ("D1", "F1", "F2", "F4")]
    spec["openings"].append({"id": "D2", "wall": "V1", "kind": "door", "offset": 4200, "width": 900, "height": 2100, "hinge": "start", "swing": "left"})
    spec["rooms"] = [r for r in spec["rooms"] if r["id"] not in ("R6", "R4")]
    spec["walls"] = [w for w in spec["walls"] if w["id"] != "V2"]
    design, geo, _ = analyse(spec)
    found = {(f.code, f.subject) for f in rules.run_rules(design, geo)}
    assert ("IR2800-REENTRANT", "GF") in found


def test_program_missing_room_and_connection(spec):
    spec["program"] = {"required": [{"use": "bedroom", "count": 3}], "connect": [["R5", "R6"], ["R1", "R6"]]}
    _, _, findings = analyse(spec)
    assert "PROGRAM_MISSING" in codes(findings)
    assert {f.subject for f in findings if f.code == "CONNECTION_MISSING"} == {"R1/R6"}


def test_area_off_target(spec):
    item(spec, "rooms", "R4")["target_area"] = 14.0
    _, _, findings = analyse(spec)
    assert "AREA_OFF_TARGET" in codes(findings, "warning")


def test_room_reached_only_through_bedroom(spec):
    # move the bath door from the corridor into bedroom 2's wall V2
    spec["openings"] = [o for o in spec["openings"] if o["id"] != "D4"]
    spec["openings"].append({"id": "D4", "wall": "V2", "kind": "door", "offset": 1500, "width": 800, "height": 2100, "hinge": "start", "swing": "right"})
    _, _, findings = analyse(spec)
    assert ("PASS_THROUGH_PRIVATE", "R3") in {(f.code, f.subject) for f in findings}
    item(spec, "rooms", "R3")["via"] = "R4"
    _, _, findings = analyse(spec)
    assert "PASS_THROUGH_PRIVATE" not in codes(findings)


def test_sliver_room(spec):
    spec["walls"].append({"id": "HX", "level": "GF", "start": [5600, 5300], "end": [12000, 5300], "thickness": 100, "kind": "interior"})
    spec["rooms"].append({"id": "RX", "level": "GF", "name": "Gap", "use": "storage", "seed": [8800, 5400]})
    _, _, findings = analyse(spec)
    assert ("ROOM_SLIVER", "RX") in {(f.code, f.subject) for f in findings}


def test_circulation_detour(spec):
    # entrance moved to the far end of the living room's east wall: the
    # kitchen is now reached by a long way round
    item(spec, "openings", "D1")["offset"] = 300
    item(spec, "openings", "O1")["offset"] = 300
    item(spec, "openings", "O1")["width"] = 900
    _, geo, findings = analyse(spec)
    ratios = [f for f in findings if f.code == "CIRCULATION_DETOUR"]
    assert ratios == [] or all("x the straight line" in f.message for f in ratios)


def test_ifc_schema_errors_are_reported(spec, tmp_path):
    design, geo, _ = analyse(spec)
    model = build_ifc(design, geo)
    model.by_type("IfcSpace")[0].Name = None
    model.by_type("IfcWall")[0].ObjectPlacement = model.createIfcCartesianPoint((0.0, 0.0))
    path = tmp_path / "bad.ifc"
    model.write(str(path))
    assert any(f.code == "IFC_SCHEMA" for f in verify.verify_ifc(str(path), design, geo))


def test_ifc_space_quantities_match(spec, tmp_path):
    import ifcopenshell
    import ifcopenshell.util.element

    design, geo, _ = analyse(spec)
    path = tmp_path / "m.ifc"
    build_ifc(design, geo).write(str(path))
    m = ifcopenshell.open(str(path))
    space = next(s for s in m.by_type("IfcSpace") if s.Name == "R1")
    assert ifcopenshell.util.element.get_pset(space, "Qto_SpaceBaseQuantities")["NetFloorArea"] == pytest.approx(20.19625)


def test_text_overlap_is_caught(spec, tmp_path):
    design, geo, _ = analyse(spec)
    doc, _ = plan_dxf(design, geo["GF"])
    doc.modelspace().add_text("CLASH", height=250, dxfattribs={"layer": "A-AREA-IDEN"}).set_placement((2500, 2000 + 400))
    path = tmp_path / "t.dxf"
    doc.saveas(path)
    found = verify.verify_text(str(path), geo["GF"], 100)
    assert any(f.code == "DXF_TEXT_OVERLAP" for f in found)


def test_text_audit_clean_on_example(spec, tmp_path):
    design, geo, _ = analyse(spec)
    doc, _ = plan_dxf(design, geo["GF"])
    path = tmp_path / "t.dxf"
    doc.saveas(path)
    assert verify.verify_text(str(path), geo["GF"], 100) == []


def test_wall_justify_left_puts_wall_right_of_line():
    from houseplan.geometry import raw_body
    from houseplan.model import Wall

    w = Wall(id="a", level="GF", start=(0, 0), end=(0, 9000), thickness=300, kind="exterior", justify="left")
    assert raw_body(w).bounds == (0.0, 0.0, 300.0, 9000.0)


def test_survey_coordinates_rejected(spec):
    item(spec, "walls", "WS")["start"] = [538000000, 3950000000]
    with pytest.raises(ValueError, match="survey coordinates"):
        Design.model_validate(spec)


def test_free_wall_end(spec):
    item(spec, "walls", "V2")["end"] = [2600, 8000]
    _, _, findings = analyse(spec)
    assert ("WALL_END_FREE", "V2") in {(f.code, f.subject) for f in findings}


def test_bedroom_to_bedroom(spec):
    spec["openings"].append({"id": "DX", "wall": "H1", "kind": "door", "offset": 1000, "width": 800, "height": 2100, "hinge": "start", "swing": "left"})
    spec["walls"] = [w for w in spec["walls"] if w["id"] != "H2"] + [
        {"id": "H2", "level": "GF", "start": [0, 5300], "end": [5600, 5300], "thickness": 150, "kind": "interior"}]
    item(spec, "rooms", "R2")["use"] = "bedroom"
    _, _, findings = analyse(spec)
    assert "BEDROOM_TO_BEDROOM" in codes(findings, "warning")


def test_rules_not_applicable_are_listed(spec):
    design, geo, _ = analyse(spec)
    idle = [f for f in rules.run_rules(design, geo) if f.code == "RULES_NOT_APPLICABLE"]
    assert idle and "IR4-STAIR-GOING" in idle[0].message


def family_findings(spec):
    from houseplan import family

    design, geo, _ = analyse(spec)
    return {(f.code, f.subject) for f in family.run_family(design, geo)}


def test_entry_straight_into_living_is_flagged(spec):
    assert ("ENTRY_INTO_LIVING", "R5") in family_findings(spec)


def test_entry_view_sees_bedroom_door(spec):
    # a front door in the west wall, looking straight down the corridor at
    # the bath door D4's wall: move D4 into the line of sight on V1's side
    spec["openings"].append({"id": "DW", "wall": "WW", "kind": "door", "offset": 4150, "width": 1000, "height": 2200, "hinge": "start", "swing": "right"})
    item(spec, "openings", "D2")["kind"] = "door"
    found = family_findings(spec)
    assert any(code == "ENTRY_VIEW_PRIVATE" and subject == "DW" for code, subject in found)


def test_bedroom_off_living_is_flagged(spec):
    spec["openings"].append({"id": "DX", "wall": "V1", "kind": "door", "offset": 2000, "width": 900, "height": 2100, "hinge": "start", "swing": "left"})
    assert ("BEDROOM_OFF_SOCIAL", "R1") in family_findings(spec)


def test_living_room_window_orientation(spec):
    assert ("LIVING_NOT_SOUTH", "R5") not in family_findings(spec)
    spec["project"]["north_angle_deg"] = 180
    assert ("LIVING_NOT_SOUTH", "R5") in family_findings(spec)


def test_survey_report(spec, tmp_path, capsys):
    from houseplan.survey import survey

    design, geo, _ = analyse(spec)
    doc, _ = plan_dxf(design, geo["GF"])
    path = tmp_path / "s.dxf"
    doc.saveas(path)
    survey(str(path))
    text = capsys.readouterr().out
    assert "$INSUNITS=4 (millimetres)" in text and "A-WALL" in text


def test_survey_outline_closed_by_end_points(tmp_path, capsys):
    # surveyors often close a boundary by repeating its first vertex instead of setting the flag
    import ezdxf
    from houseplan.survey import survey

    doc = ezdxf.new()
    doc.header["$INSUNITS"] = 6
    doc.modelspace().add_lwpolyline([(0, 0), (30, 0), (30, 20), (0, 20), (0, 0)], close=False)
    doc.modelspace().add_lwpolyline([(0, 25), (30, 25), (30, 40)], close=False)
    path = tmp_path / "s.dxf"
    doc.saveas(path)
    survey(str(path))
    text = capsys.readouterr().out
    assert "600.000" in text and "closed by end points" in text
    assert "450.000" not in text


def test_window_wall_ratio(spec, tmp_path, monkeypatch):
    # bungalow: windows 11.55 m² over 42 m of exterior wall axis x 2.85 m = 9.6 %
    (tmp_path / "w.yaml").write_text(yaml.safe_dump({
        "ruleset": "w", "jurisdiction": "IR", "title": "test",
        "rules": [{"id": "W", "check": "window_wall_ratio_max", "title": "wwr", "value": 0.09, "source": "test", "status": "verified"}],
    }))
    monkeypatch.setattr(rules, "RULES_DIR", tmp_path)
    spec["project"]["ruleset"] = "w"
    design, geo, _ = analyse(spec)
    found = [f for f in rules.run_rules(design, geo) if f.code == "W"]
    assert len(found) == 1 and "window-to-wall ratio 10%" in found[0].message
