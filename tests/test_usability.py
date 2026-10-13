"""Everyday use tested cheaply on the plan (owner, docs/brief.md "Everyday
use"): walking routes, what can be seen from the living room and the front
door, and living rooms over bedrooms. Each test breaks the example bungalow
in one known way."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from houseplan import geometry, usability
from houseplan.model import Design

EXAMPLE = Path(__file__).resolve().parents[1] / "design" / "examples" / "bungalow.yaml"


@pytest.fixture
def spec() -> dict:
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def run(spec):
    design = Design.model_validate(spec)
    return usability.run_usability(design, geometry.build(design))


def codes(findings, severity=None):
    return {f.code for f in findings if severity is None or f.severity == severity}


def opening(spec, oid):
    return next(o for o in spec["openings"] if o["id"] == oid)


def make_open(o, width=None):
    o["kind"] = "opening"
    o.pop("hinge", None)
    o.pop("swing", None)
    if width:
        o["width"] = width


def test_route_reports_length_and_rooms(spec):
    spec["program"] = {"scenarios": [{"name": "bed to kitchen", "route": ["R1", "R6"]}]}
    found = [f for f in run(spec) if f.code == "ROUTE"]
    assert len(found) == 1
    msg = found[0].message
    assert "R1 → R2 → R5 → R6" in msg and " m" in msg


def test_route_through_a_bedroom_is_flagged(spec):
    # bedroom 1 gets doors to both the living room and the corridor
    spec["openings"] = [o for o in spec["openings"] if o["id"] != "D3"]  # R1's door to the corridor
    spec["openings"].append({"id": "D9", "wall": "V1", "kind": "door", "offset": 1500, "width": 900, "height": 2100, "hinge": "start", "swing": "left"})  # R1 to living
    spec["openings"].append({"id": "D10", "wall": "H1", "kind": "door", "offset": 1000, "width": 900, "height": 2100, "hinge": "start", "swing": "right"})  # R1 to corridor again, west
    spec["program"] = {"scenarios": [{"name": "living to bath", "route": ["R5", "R3"]}]}
    # route R5 -> R2 -> R3 does not need R1, so nothing flagged
    assert "ROUTE_THROUGH_PRIVATE" not in codes(run(spec))
    spec["openings"] = [o for o in spec["openings"] if o["id"] != "D2"]  # living to corridor closed: only via R1
    assert "ROUTE_THROUGH_PRIVATE" in codes(run(spec), "warning")


def test_route_without_a_way_is_a_warning(spec):
    spec["openings"] = [o for o in spec["openings"] if o["id"] != "O1"]  # kitchen sealed off
    spec["program"] = {"scenarios": [{"name": "dinner", "route": ["R6", "R5"]}]}
    assert "ROUTE_NONE" in codes(run(spec), "warning")


def test_wc_door_seen_from_the_living_room(spec):
    assert "LIVING_SEES_WC" not in codes(run(spec))  # D2 is a door: closed, so solid
    make_open(opening(spec, "D2"))
    assert "LIVING_SEES_WC" in codes(run(spec), "warning")


def test_kitchen_seen_from_the_living_room(spec):
    assert "KITCHEN_SEEN" in codes(run(spec), "warning")  # O1 is a 2.4 m opening
    o = opening(spec, "O1")
    o.update(kind="door", width=900, hinge="start", swing="left")
    assert "KITCHEN_SEEN" not in codes(run(spec), "warning")


def test_front_door_sees_the_living_room(spec):
    assert "ENTRY_SEES_LIVING" in codes(run(spec), "warning")  # D1 opens straight into living


def test_living_over_a_bedroom(spec):
    upper = yaml.safe_load(yaml.safe_dump(spec))
    spec["levels"].append({"id": "L1", "name": "Upper", "ffl": 3200, "floor_to_floor": 3200, "slab": 350})
    for w in upper["walls"]:
        spec["walls"].append({**w, "id": w["id"] + "u", "level": "L1"})
    for r in upper["rooms"]:
        spec["rooms"].append({**r, "id": r["id"] + "u", "level": "L1", "entrance": False, "use": "living" if r["id"] == "R1" else r["use"]})
    for o in upper["openings"]:
        spec["openings"].append({**o, "id": o["id"] + "u", "wall": o["wall"] + "u"})
    found = [f for f in run(spec) if f.code == "LIVING_OVER_BEDROOM"]
    assert found and "R1u" in found[0].subject and "R1" in found[0].message
