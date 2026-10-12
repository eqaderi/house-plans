"""Balconies outside the walls, lifts and parked cars: each test breaks the
example in one known way and expects the matching finding."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from houseplan import checks, family, geometry, rules, verify
from houseplan.checks import access_graph
from houseplan.drawing import plan_dxf
from houseplan.family import _window_bearings
from houseplan.ifc import build_ifc
from houseplan.model import Design

EXAMPLE = Path(__file__).resolve().parents[1] / "design" / "examples" / "bungalow.yaml"

# in front of the living room R5, on the outer face of the south wall WS (y = -150)
BALCONY = {"id": "B1", "level": "GF", "name": "Balcony", "outline": [[6000, -1650], [11500, -1650], [11500, -150], [6000, -150]]}
BALCONY_DOOR = {"id": "D9", "wall": "WS", "kind": "door", "offset": 10200, "width": 900, "height": 2200, "hinge": "end", "swing": "right"}


@pytest.fixture
def spec() -> dict:
    s = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    s["balconies"] = [dict(BALCONY)]
    s["openings"].append(dict(BALCONY_DOOR))
    return s


def analyse(spec):
    design = Design.model_validate(spec)
    geo = geometry.build(design)
    findings = checks.run_all(design, geo) + family.run_family(design, geo) + rules.run_rules(design, geo)
    return design, geo, findings


def codes(findings, severity="error"):
    return {f.code for f in findings if f.severity == severity}


def test_balcony_with_door_is_clean(spec):
    _, geo, findings = analyse(spec)
    assert codes(findings) == set()
    assert not {c for c in codes(findings, "warning") if c.startswith("BALCONY")}
    graph = access_graph(geo["GF"])
    assert "B1" in graph["R5"] and "R5" in graph["B1"]


def test_balcony_does_not_change_the_footprint_or_window_bearings(spec):
    _, geo, _ = analyse(spec)
    lg = geo["GF"]
    assert lg.footprint.area == pytest.approx(12300 * 9300, abs=1)
    assert 180 in [round(b) for b in _window_bearings(lg, "R5", 0)]
    assert lg.balconies["B1"].area == pytest.approx(5500 * 1500)


def test_balcony_detached(spec):
    spec["balconies"][0]["outline"] = [[6000, -2150], [11500, -2150], [11500, -650], [6000, -650]]
    _, _, findings = analyse(spec)
    assert "BALCONY_DETACHED" in codes(findings)


def test_balcony_overlaps_building(spec):
    spec["balconies"][0]["outline"] = [[6000, -1650], [11500, -1650], [11500, 500], [6000, 500]]
    _, _, findings = analyse(spec)
    assert "BALCONY_OVERLAPS_BUILDING" in codes(findings)


def test_balcony_without_door(spec):
    spec["openings"] = [o for o in spec["openings"] if o["id"] != "D9"]
    _, _, findings = analyse(spec)
    assert "BALCONY_NO_DOOR" in codes(findings, "warning")


def test_balcony_guard_is_not_checked_and_says_so(spec):
    _, _, findings = analyse(spec)
    assert "BALCONY_GUARD_UNCHECKED" in codes(findings, "info")


def test_balcony_counts_for_the_site(spec):
    spec["site"] = {"source": "test", "boundary": [[-1000, -1000], [20000, -1000], [20000, 20000], [-1000, 20000]]}
    _, _, findings = analyse(spec)
    assert "SITE_OUTSIDE_BOUNDARY" in codes(findings)


def test_balcony_unknown_level_rejected(spec):
    spec["balconies"][0]["level"] = "NOPE"
    with pytest.raises(ValueError):
        Design.model_validate(spec)


def test_balcony_drawn_labelled_and_in_ifc(spec, tmp_path):
    import ifcopenshell

    design, geo, _ = analyse(spec)
    doc, sheet = plan_dxf(design, geo["GF"])
    texts = [e.dxf.text for e in doc.modelspace().query("TEXT")]
    assert "BALCONY" in texts and "8.25 m²" in texts
    path = tmp_path / "p.dxf"
    doc.saveas(path)
    assert verify.verify_text(str(path), geo["GF"], sheet.scale) == []
    ifc_path = tmp_path / "m.ifc"
    build_ifc(design, geo).write(str(ifc_path))
    assert [s.Name for s in ifcopenshell.open(str(ifc_path)).by_type("IfcSlab")] == ["B1"]
    assert verify.verify_ifc(str(ifc_path), design, geo) == []


# --- lift ---------------------------------------------------------------------

def lift_spec() -> dict:
    """The bungalow's bath R3 (2.40 x 3.48 m net) becomes a lift shaft, and
    an upper level repeats its walls: shaft U2 above R3, hall U1 beside it.
    The upper level has no stair, so U1 is reached by the lift alone."""
    s = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    r3 = next(r for r in s["rooms"] if r["id"] == "R3")
    r3.update(name="Lift", use="lift")
    s["levels"].append({"id": "L1", "name": "First floor", "ffl": 3200, "floor_to_floor": 3000, "slab": 350})
    for w in [w for w in s["walls"] if w["kind"] == "exterior" or w["id"] in ("H2", "V2")]:
        s["walls"].append({**w, "id": w["id"] + "u", "level": "L1"})
    s["rooms"] += [
        {"id": "U1", "level": "L1", "name": "Hall", "use": "hall", "seed": [8000, 4500]},
        {"id": "U2", "level": "L1", "name": "Lift", "use": "lift", "seed": [1300, 7000]},
    ]
    s["openings"].append({"id": "UO", "wall": "H2u", "kind": "opening", "offset": 1200, "width": 900, "height": 2100})
    s["openings"].append({"id": "UF", "wall": "WSu", "kind": "window", "offset": 2000, "width": 1200, "height": 1200, "sill": 900})
    s["lifts"] = [{"id": "LF", "shafts": ["R3", "U2"], "car": [1100, 1400]}]
    return s


def test_lift_is_clean_and_serves_the_upper_level():
    _, geo, findings = analyse(lift_spec())
    assert not {c for c in codes(findings) if c.startswith("LIFT")}
    assert "ROOM_UNREACHABLE" not in codes(findings)


def test_lift_shaft_not_stacked():
    s = lift_spec()
    next(w for w in s["walls"] if w["id"] == "V2u").update(start=[2000, 5300], end=[2000, 9000])
    _, _, findings = analyse(s)
    assert "LIFT_NOT_STACKED" in codes(findings)


def test_lift_without_landing_door():
    s = lift_spec()
    s["openings"] = [o for o in s["openings"] if o["id"] != "UO"]
    _, _, findings = analyse(s)
    assert "LIFT_NO_DOOR" in codes(findings)


def test_lift_car_bigger_than_shaft():
    s = lift_spec()
    s["lifts"][0]["car"] = [1100, 3600]  # shaft is 2400 x 3475
    _, _, findings = analyse(s)
    assert "LIFT_CAR_IN_SHAFT" in codes(findings)


def test_lift_shaft_room_must_have_lift_use():
    s = lift_spec()
    next(r for r in s["rooms"] if r["id"] == "U2")["use"] = "storage"
    _, _, findings = analyse(s)
    assert "LIFT_ROOM_USE" in codes(findings)


def test_lift_room_not_listed():
    s = lift_spec()
    del s["lifts"]
    _, _, findings = analyse(s)
    assert "LIFT_UNLISTED" in codes(findings, "warning")


def test_lift_rules(tmp_path, monkeypatch):
    (tmp_path / "l.yaml").write_text(yaml.safe_dump({
        "ruleset": "l", "jurisdiction": "IR", "title": "test",
        "rules": [
            {"id": "CAR", "check": "lift_car_min", "title": "car", "value": 1100, "params": {"depth": 1500}, "source": "test", "status": "unverified"},
            {"id": "SHAFT", "check": "lift_shaft_min", "title": "shaft", "value": 2500, "params": {"depth": 3000}, "source": "test", "status": "verified"},
            {"id": "ENTRY", "check": "lift_entrance_min_width", "title": "entrance", "value": 900, "source": "test", "status": "verified"},
        ],
    }))
    monkeypatch.setattr(rules, "RULES_DIR", tmp_path)
    s = lift_spec()
    s["project"]["ruleset"] = "l"
    design, geo, _ = analyse(s)
    found = {(f.code, f.severity, f.subject) for f in rules.run_rules(design, geo)}
    assert ("CAR", "warning", "LF") in found  # 1400 deep < 1500
    assert ("SHAFT", "error", "LF") in found  # 2400 wide < 2500
    entry = {f[2] for f in found if f[0] == "ENTRY"}
    assert entry == {"R3"}  # D4 is 800 wide; U2's opening UO is 900


# --- cars in the garage ---------------------------------------------------------


def garage_spec(monkeypatch, tmp_path, stall=2500, length=5000) -> dict:
    """Living room R5 (6.15 x 5.28 m net) used as a garage for two cars."""
    (tmp_path / "g.yaml").write_text(yaml.safe_dump({
        "ruleset": "g", "jurisdiction": "IR", "title": "test",
        "rules": [{"id": "GAR", "check": "garage_stalls_min", "title": "stalls", "value": stall, "params": {"length": length}, "source": "test", "status": "verified"}],
    }))
    monkeypatch.setattr(rules, "RULES_DIR", tmp_path)
    s = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    s["project"]["ruleset"] = "g"
    next(r for r in s["rooms"] if r["id"] == "R5")["use"] = "garage"
    s.setdefault("program", {})["vehicles"] = [
        {"name": "car A", "length": 4900, "width": 1900, "source": "test"},
        {"name": "car B", "length": 4400, "width": 1700, "source": "test"},
    ]
    return s


def gar(spec):
    design, geo, _ = analyse(spec)
    return [f for f in rules.run_rules(design, geo) if f.code == "GAR"]


def test_stalls_fit_side_by_side(monkeypatch, tmp_path):
    assert gar(garage_spec(monkeypatch, tmp_path)) == []  # 2 x 2500 = 5000 <= 6150; 5000 <= 5275


def test_stalls_do_not_fit(monkeypatch, tmp_path):
    found = gar(garage_spec(monkeypatch, tmp_path, stall=3100))  # 6200 > 6150
    assert len(found) == 1 and "6200" in found[0].message


def test_no_garage_for_the_cars_is_not_passed(monkeypatch, tmp_path):
    s = garage_spec(monkeypatch, tmp_path)
    next(r for r in s["rooms"] if r["id"] == "R5")["use"] = "living"
    design, geo, _ = analyse(s)
    idle = [f for f in rules.run_rules(design, geo) if f.code == "RULES_NOT_APPLICABLE"]
    assert idle and "GAR" in idle[0].message


def test_car_body_longer_than_the_garage(monkeypatch, tmp_path):
    s = garage_spec(monkeypatch, tmp_path)
    s["program"]["vehicles"][0]["length"] = 6200  # garage is 5275 x 6150 net
    _, _, findings = analyse(s)
    assert "GARAGE_TOO_SMALL" in codes(findings)


def test_car_bodies_fit(monkeypatch, tmp_path):
    _, _, findings = analyse(garage_spec(monkeypatch, tmp_path))
    assert "GARAGE_TOO_SMALL" not in codes(findings)


def test_garage_entrance_must_pass_the_cars(monkeypatch, tmp_path):
    s = garage_spec(monkeypatch, tmp_path)
    s["program"]["vehicles"][0]["height"] = 1925
    _, _, findings = analyse(s)  # D1, R5's only exterior door, is 1000 wide
    assert "GARAGE_ENTRANCE" in codes(findings)
    next(o for o in s["openings"] if o["id"] == "D1").update(kind="opening", width=2400, height=2100)
    del next(o for o in s["openings"] if o["id"] == "D1")["hinge"]
    del next(o for o in s["openings"] if o["id"] == "D1")["swing"]
    _, _, findings = analyse(s)
    assert "GARAGE_ENTRANCE" not in codes(findings)
