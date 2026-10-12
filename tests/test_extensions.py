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
