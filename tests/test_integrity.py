"""Deterministic integrity checks on the canonical house model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from house_ai.domain.base import EXTERIOR
from house_ai.domain.integrity import (
    FindingSeverity,
    check_model,
    circulation_graph,
    errors,
    opening_sides,
    reachable_from,
)
from house_ai.domain.model import HouseModel
from house_ai.domain.plan import PlanVersion
from house_ai.domain.site import Site


def model_from(plan_doc: dict) -> HouseModel:
    return PlanVersion.model_validate(plan_doc).model


def codes(findings) -> list[str]:
    return [f.code for f in findings]


def find(items: list[dict], ident: str) -> dict:
    return next(i for i in items if i["id"] == ident)


def test_golden_plan_is_clean(plan, site):
    assert check_model(plan.model, site) == []


def test_space_areas(plan):
    areas = {s.id: s.area_m2 for s in plan.model.spaces}
    assert areas == pytest.approx(
        {
            "sp-living": 30.0,
            "sp-kitchen": 30.0,
            "sp-hall": 18.0,
            "sp-bed-parents": 14.0,
            "sp-bath": 10.5,
            "sp-bed-children": 17.5,
        }
    )
    assert sum(areas.values()) == pytest.approx(120.0)


def test_golden_plan_meets_program_minimum_areas(plan, example_dir):
    from house_ai.domain.program import SpaceProgram
    from house_ai.storage.hashing import load_document

    program = SpaceProgram.model_validate(load_document(example_dir / "space_program.yaml"))
    minima = {i.id: i.min_area_m2 for i in program.items}
    for space in plan.model.spaces:
        assert space.area_m2 >= minima[space.program_item_id]


def test_opening_sides_are_detected_geometrically(plan):
    model = plan.model
    by_id = {o.id: o for o in model.openings}
    assert set(opening_sides(model, by_id["d-front"])) == {EXTERIOR, "sp-hall"}
    assert set(opening_sides(model, by_id["d-hall-bath"])) == {"sp-hall", "sp-bath"}
    assert set(opening_sides(model, by_id["win-bath-n"])) == {"sp-bath", EXTERIOR}


def test_circulation_graph(plan):
    graph = circulation_graph(plan.model)
    assert graph[EXTERIOR] == {"sp-hall"}
    assert graph["sp-hall"] == {
        EXTERIOR,
        "sp-living",
        "sp-kitchen",
        "sp-bed-parents",
        "sp-bath",
        "sp-bed-children",
    }
    assert "sp-kitchen" in graph["sp-living"]  # cased opening
    # Windows are not circulation.
    assert all(EXTERIOR not in graph[s] for s in ("sp-living", "sp-bath"))
    assert reachable_from(graph, EXTERIOR) == set(graph)


def test_overlapping_spaces(plan_doc):
    find(plan_doc["model"]["spaces"], "sp-living")["boundary"]["outer"] = [
        [10, 12],
        [17, 12],
        [17, 17],
        [10, 17],
    ]
    findings = check_model(model_from(plan_doc))
    overlap = [f for f in findings if f.code == "space_overlap"]
    assert len(overlap) == 1
    assert set(overlap[0].subject_ids) == {"sp-living", "sp-kitchen"}
    assert "5.000 m²" in overlap[0].message


def test_spaces_sharing_an_edge_do_not_overlap(plan):
    assert "space_overlap" not in codes(check_model(plan.model))


def test_dangling_host_wall(plan_doc):
    find(plan_doc["model"]["openings"], "d-front")["host_wall_id"] = "w-missing"
    findings = check_model(model_from(plan_doc))
    assert codes(findings) == ["dangling_reference"]
    assert "w-missing" in findings[0].message


def test_opening_beyond_wall_end(plan_doc):
    find(plan_doc["model"]["openings"], "win-kitchen-e")["offset_m"] = 9.5
    assert "opening_outside_wall" in codes(check_model(model_from(plan_doc)))


def test_opening_taller_than_wall(plan_doc):
    find(plan_doc["model"]["openings"], "win-living-w")["sill_m"] = 2.0
    assert "opening_taller_than_wall" in codes(check_model(model_from(plan_doc)))


def test_door_that_claims_the_wrong_room(plan_doc):
    # The door sits in the hall/bath wall but says it opens into the bedroom.
    find(plan_doc["model"]["openings"], "d-hall-bath")["connects"] = ["sp-hall", "sp-bed-parents"]
    findings = check_model(model_from(plan_doc))
    mismatch = [f for f in findings if f.code == "opening_sides_mismatch"]
    assert len(mismatch) == 1
    assert "sp-bath" in mismatch[0].message


def test_door_moved_off_its_room(plan_doc):
    # Same claim, but the door slides along the hall wall into the next room.
    find(plan_doc["model"]["openings"], "d-hall-bath")["offset_m"] = 7.5
    assert "opening_sides_mismatch" in codes(check_model(model_from(plan_doc)))


def test_unreachable_room(plan_doc):
    plan_doc["model"]["openings"] = [
        o for o in plan_doc["model"]["openings"] if o["id"] != "d-hall-bed-children"
    ]
    findings = check_model(model_from(plan_doc))
    assert codes(findings) == ["space_unreachable"]
    assert findings[0].subject_ids == ["sp-bed-children"]
    assert findings[0].severity is FindingSeverity.ERROR


def test_duplicate_ids_across_entity_types(plan_doc):
    find(plan_doc["model"]["walls"], "w-hall-s")["id"] = "sp-hall"
    findings = check_model(model_from(plan_doc))
    assert "duplicate_id" in codes(findings)


def test_reserved_exterior_id(plan_doc):
    plan_doc["model"]["materials"][0]["id"] = "exterior"
    plan_doc["model"]["walls"] = [
        {**w, "material_id": None} if w["material_id"] == "m-render" else w
        for w in plan_doc["model"]["walls"]
    ]
    assert "reserved_id" in codes(check_model(model_from(plan_doc)))


def test_fixture_outside_its_space(plan_doc):
    find(plan_doc["model"]["fixtures"], "fx-wc")["position"] = [12.0, 14.0]
    assert codes(check_model(model_from(plan_doc))) == ["fixture_outside_space"]


def test_footprint_outside_the_buildable_envelope(plan_doc, site):
    for space in plan_doc["model"]["spaces"]:
        space["boundary"]["outer"] = [[x + 7, y] for x, y in space["boundary"]["outer"]]
    for wall in plan_doc["model"]["walls"]:
        wall["start"] = [wall["start"][0] + 7, wall["start"][1]]
        wall["end"] = [wall["end"][0] + 7, wall["end"][1]]
    for fx in plan_doc["model"]["fixtures"]:
        fx["position"] = [fx["position"][0] + 7, fx["position"][1]]
    findings = check_model(model_from(plan_doc), site)
    outside = {f.subject_ids[0] for f in findings if f.code == "outside_envelope"}
    # Envelope ends at x = 28; the east rooms now reach x = 29.
    assert outside == {"sp-kitchen", "sp-hall", "sp-bed-children"}
    assert len(errors(findings)) == len(findings)


def test_falls_back_to_parcel_boundary_with_a_warning(plan, site_doc):
    site_doc["buildable_envelope"] = None
    findings = check_model(plan.model, Site.model_validate(site_doc))
    assert codes(findings) == ["envelope_unknown"]
    assert errors(findings) == []


def test_model_in_a_different_coordinate_system(plan_doc, site):
    plan_doc["model"]["coordinate_system_id"] = "lcs-other"
    assert "coordinate_system_mismatch" in codes(check_model(model_from(plan_doc), site))


def test_schema_level_geometry_rules(plan_doc):
    find(plan_doc["model"]["openings"], "d-front")["connects"] = ["exterior", "exterior"]
    with pytest.raises(ValidationError, match="two different sides"):
        model_from(plan_doc)


def test_degenerate_wall_is_rejected(plan_doc):
    wall = find(plan_doc["model"]["walls"], "w-hall-s")
    wall["end"] = wall["start"]
    with pytest.raises(ValidationError, match="shorter than 1 cm"):
        model_from(plan_doc)


def test_opening_straddling_two_rooms_is_rejected(plan_doc):
    # w-hall-n runs from x=10 to x=22; sp-bed-parents is [10, 14] and sp-bath is [14, 17].
    # Place d-hall-bath at offset 3.1 with width 2.0 (x=13.1 to x=15.1, midpoint x=14.1 in sp-bath).
    door = find(plan_doc["model"]["openings"], "d-hall-bath")
    door["offset_m"] = 3.1
    door["width_m"] = 2.0
    findings = check_model(model_from(plan_doc))
    assert "opening_sides_mismatch" in codes(findings)


def test_overlapping_openings_on_same_wall(plan_doc):
    # Move d-hall-bath to overlap d-hall-bed-parents (offset 1.5, width 0.9) on w-hall-n.
    door = find(plan_doc["model"]["openings"], "d-hall-bath")
    door["offset_m"] = 1.8
    door["connects"] = ["sp-hall", "sp-bed-parents"]
    findings = check_model(model_from(plan_doc))
    assert "opening_overlap" in codes(findings)


def test_unattached_wall_is_rejected(plan_doc):
    plan_doc["model"]["walls"].append(
        {
            "id": "w-floating",
            "level_id": "l0",
            "start": [0.0, 0.0],
            "end": [5.0, 0.0],
            "thickness_m": 0.2,
            "height_m": 2.8,
            "kind": "exterior",
        }
    )
    assert "unattached_wall" in codes(check_model(model_from(plan_doc)))


def test_fixture_protruding_outside_space_despite_interior_center(plan_doc):
    # Center is at x=14.05 inside sp-bath [14, 17], but width_m=0.4 extends to x=13.85.
    find(plan_doc["model"]["fixtures"], "fx-wc")["position"] = [14.05, 21.4]
    assert "fixture_outside_space" in codes(check_model(model_from(plan_doc)))


def test_overlapping_fixtures_in_same_space(plan_doc):
    find(plan_doc["model"]["fixtures"], "fx-basin")["position"] = [14.6, 21.4]
    assert "fixture_overlap" in codes(check_model(model_from(plan_doc)))


def test_stair_level_and_footprint_checks(plan_doc):
    plan_doc["model"]["levels"].append({"id": "l1", "name": "Upper", "elevation_m": 3.7})
    plan_doc["model"]["stairs"].append(
        {
            "id": "st-main",
            "kind": "straight",
            "from_level_id": "l0",
            "to_level_id": "l1",
            "footprint": {"outer": [[0, 0], [3, 0], [3, 1], [0, 1]]},
            "bottom_space_id": "sp-hall",
            "top_space_id": "sp-living",  # on l0, not l1
            "width_m": 1.0,
        }
    )
    findings = check_model(model_from(plan_doc))
    assert "stair_level_mismatch" in codes(findings)
    assert "stair_outside_connected_space" in codes(findings)


def test_opening_opens_into_must_match_connects(plan_doc):
    find(plan_doc["model"]["openings"], "d-hall-bath")["opens_into"] = "sp-kitchen"
    with pytest.raises(ValidationError, match="opens_into"):
        model_from(plan_doc)

