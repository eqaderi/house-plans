from __future__ import annotations

import copy
import math
from pathlib import Path

import pytest
from shapely.geometry import Point, Polygon, box

from examples.usability.scenarios import (
    door,
    flat_site,
    furniture,
    model,
    rectangle,
    seeded_pairs,
    space,
    stair_model,
    wall,
)
from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.integrity import check_model
from house_ai.domain.model import HouseModel
from house_ai.domain.program import SpaceProgram
from house_ai.domain.usability import FurnitureTemplate
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.routes import RouteNetwork, shortest_in_polygon
from house_ai.evaluation.templates import TEMPLATES, UsabilityPolicy
from house_ai.evaluation.usability import (
    USABILITY_EVALUATORS,
    DaylightOpportunityEvaluator,
    DoorClearanceEvaluator,
    FurnitureUsabilityEvaluator,
    NetAreaEvaluator,
    PrivacyUsabilityEvaluator,
    RouteUsabilityEvaluator,
    StairUsabilityEvaluator,
    VehicleArrivalEvaluator,
)
from house_ai.evaluation.usability_geometry import door_geometry, net_floor
from house_ai.storage.hashing import load_document


def ctx(doc, site=None, program=None):
    house = doc if isinstance(doc, HouseModel) else HouseModel.model_validate(doc)
    return EvaluationContext(house, site, program, None)


def metric(result, name, subject=None):
    return next(
        m
        for m in result.metrics
        if m.metric == name and (subject is None or subject in m.subject_ids)
    )


def program(**requirements):
    from tests.conftest import EXAMPLE

    doc = load_document(EXAMPLE / "space_program.yaml")
    doc["usability"] = requirements
    return SpaceProgram.model_validate(doc)


@pytest.mark.parametrize("case", list(seeded_pairs()), ids=lambda c: c[0])
def test_seeded_defects_and_clean_twins(case):
    _, critic_name, bad, clean, code, subject, pair_program = case
    critic = next(e for e in USABILITY_EVALUATORS if e.name == critic_name)
    bad_result = critic.evaluate(ctx(bad, program=pair_program))
    clean_result = critic.evaluate(ctx(clean, program=pair_program))
    assert any(v.code == code and subject in v.subject_ids for v in bad_result.violations)
    assert code not in {v.code for v in clean_result.violations}
    # A clean twin passes on a measured or inferred value, never on a missing one.
    cited = [m for m in clean_result.metrics if subject in m.subject_ids]
    assert all(m.status != ClaimStatus.NOT_CHECKED for m in cited)
    for result in [bad_result, clean_result]:
        assert all(v.method and v.assumption_basis and v.subject_ids for v in result.violations)
        assert all(v.strength.value == "soft" for v in result.violations)


def _missing_input_cases():
    """(case, critic, plan with the input, same plan without it, code, metric, reason)."""
    car = dict(id="car", width_m=1.8, length_m=4.5, door_side_clearance_m=0.6, source="synthetic")
    yield (
        "dining-seats", FurnitureUsabilityEvaluator,
        ctx(model(0.8, 0.8, "dining"), program=program(household_seats=4)),
        ctx(model(0.8, 0.8, "dining")),
        "dining_no_sampled_fit", "dining_sampled_fit", "household_seats_unknown",
    )  # fmt: skip
    yield (
        "garage-vehicles", FurnitureUsabilityEvaluator,
        ctx(model(2, 3, "garage"), program=program(vehicles=[car])),
        ctx(model(2, 3, "garage")),
        "garage_no_sampled_fit", "garage_sampled_fit", "vehicle_count_or_size_unknown",
    )  # fmt: skip
    headroom = stair_model(defect="headroom").model_dump(mode="json")
    no_line = copy.deepcopy(headroom)
    no_line["stairs"][0].pop("walking_line")
    yield (
        "stair-walking-line", StairUsabilityEvaluator, ctx(headroom), ctx(no_line),
        "stair_low_headroom", "stair_min_headroom_m", "missing_walking_line",
    )  # fmt: skip
    short = stair_model(defect="run").model_dump(mode="json")
    no_risers = copy.deepcopy(short)
    no_risers["stairs"][0]["riser_count"] = None
    yield (
        "stair-risers", StairUsabilityEvaluator, ctx(short), ctx(no_risers),
        "stair_run_does_not_fit", "stair_run_fit", "missing_riser_count_or_going",
    )  # fmt: skip
    swing = model(4, 6, doors=True)
    swing["furniture"] = [furniture("bed", position=(1.4, 1.1))]
    no_side = copy.deepcopy(swing)
    no_side["openings"][0].pop("opens_into")
    yield (
        "door-swing-side", DoorClearanceEvaluator, ctx(swing), ctx(no_side),
        "door_object_conflict", "door_swing_checked", "missing_swing_side",
    )  # fmt: skip
    dim = model(4, 4, "living")
    dim["openings"] = [
        dict(id="win", kind="window", host_wall_id="south", offset_m=1, width_m=0.6,
             height_m=1.0, sill_m=0.9, connects=("room", "exterior"), operation="casement")
    ]  # fmt: skip
    yield (
        "daylight-terrain", DaylightOpportunityEvaluator, ctx(dim, flat_site()), ctx(dim),
        "low_daylight_opportunity", "unburied_glazing_to_net_area",
        "three_point_tin_window_area_ratio",
    )  # fmt: skip


@pytest.mark.parametrize("case", list(_missing_input_cases()), ids=lambda c: c[0])
def test_missing_input_is_reported_not_checked_never_as_a_pass(case):
    """A bad plan whose deciding input is missing is not silently clean: the critic names
    the unchecked metric and why, and claims no value for it."""
    _, critic, with_input, without_input, code, name, reason = case
    assert code in {v.code for v in critic().evaluate(with_input).violations}
    result = critic().evaluate(without_input)
    assert code not in {v.code for v in result.violations}
    unchecked = [m for m in result.metrics if m.metric == name]
    assert unchecked and all(
        m.status == ClaimStatus.NOT_CHECKED and m.value is None and m.method == reason
        for m in unchecked
    )


def test_vehicle_arrival_without_a_drive_or_path_is_not_checked():
    car = dict(id="car", width_m=1.8, length_m=4.5, door_side_clearance_m=0.6,
               turning_radius_m=5, source="synthetic")  # fmt: skip
    result = VehicleArrivalEvaluator().evaluate(ctx(model(), flat_site(), program(vehicles=[car])))
    assert [(m.value, m.status, m.method) for m in result.metrics] == [
        (None, ClaimStatus.NOT_CHECKED, "road_drive_polygon_arrival_path_or_vehicle_unknown")
    ]
    assert result.violations == []


def test_net_area_analytical_partition_room_and_door_recess():
    doc = model(4, 3)
    for w in doc["walls"]:
        w["kind"] = "interior"
    house = HouseModel.model_validate(doc)
    assert net_floor(house, house.spaces[0]).area == pytest.approx(3.85 * 2.85)
    result = NetAreaEvaluator().evaluate(ctx(house))
    assert metric(result, "net_area_m2").value == pytest.approx(3.85 * 2.85, abs=0.001)
    assert metric(result, "gross_area_m2").value == 12
    assert metric(result, "net_extent_short_m").value == 2.85
    doc["openings"] = [door()]
    house = HouseModel.model_validate(doc)
    assert net_floor(house, house.spaces[0]).area == pytest.approx(3.85 * 2.85 + 0.9 * 0.075)
    doc["openings"][0]["sill_m"] = 0.5
    house = HouseModel.model_validate(doc)
    assert net_floor(house, house.spaces[0]).area == pytest.approx(3.85 * 2.85)


@pytest.mark.parametrize(
    "operation,area",
    [
        ("swing_left", math.pi * 0.9**2 / 4),
        ("swing_right", math.pi * 0.9**2 / 4),
        ("double_swing", math.pi * 0.9**2 / 8),
        ("sliding", 0),
    ],
)
def test_door_geometry_area_handing_leaf_and_both_approaches(operation, area):
    doc = model(4, 3)
    doc["openings"] = [door(operation=operation, opens_into="room")]
    house = HouseModel.model_validate(doc)
    g = door_geometry(house, house.openings[0])
    assert g.swept.area == pytest.approx(area, abs=2e-5)
    assert g.approaches["room"].area == pytest.approx(0.9 * 0.9)
    if operation != "sliding":
        assert g.swept.centroid.y > 0
        assert all(
            leaf.length == pytest.approx(0.9 / (2 if operation == "double_swing" else 1))
            for leaf in g.leaves
        )
    doc["spaces"].append(space("hall", "hall", (0, -2, 4, 0)))
    doc["openings"][0]["connects"] = ("hall", "room")
    house = HouseModel.model_validate(doc)
    assert set(door_geometry(house, house.openings[0]).approaches) == {"room", "hall"}


def test_door_wall_conflict_and_unknown_swing():
    doc = model(4, 3, doors=True)
    doc["walls"].append(wall("wall-end", (1.5, 0.3), (1.5, 1)))
    result = DoorClearanceEvaluator().evaluate(ctx(doc))
    assert any(
        v.code == "door_wall_conflict" and "wall-end" in v.subject_ids for v in result.violations
    )
    # door_door_conflict: test_door_door_conflict_names_both_doors_and_clean_twin.
    doc["openings"][0].pop("opens_into")
    result = DoorClearanceEvaluator().evaluate(ctx(doc))
    assert metric(result, "door_swing_checked", "front-door").status == ClaimStatus.NOT_CHECKED


def test_templates_are_cited_assumptions_and_schema_valid():
    assert {
        "bed-double",
        "bed-single",
        "wardrobe",
        "desk",
        "chair",
        "dining",
        "sofa-group",
        "kitchen-run",
        "appliance",
        "wc",
        "basin",
        "shower",
        "bath",
        "vehicle",
    } <= TEMPLATES.keys()
    for t in TEMPLATES.values():
        assert FurnitureTemplate.model_validate_json(t.model_dump_json()) == t
        for key in ("width", "depth", "left", "right", "front", "back"):
            d = getattr(t, key)
            assert d.status == "assumption" and d.source and d.rationale
    from pydantic import ValidationError

    invalid = TEMPLATES["desk"].model_dump(mode="json")
    invalid["width"]["unit"] = "ft"
    with pytest.raises(ValidationError):
        FurnitureTemplate.model_validate(invalid)
    invalid["width"]["unit"] = "m"
    invalid["width"]["value"] = 0
    with pytest.raises(ValidationError):
        FurnitureTemplate.model_validate(invalid)


def test_stair_analytical_headroom_and_unknown_orientation():
    result = StairUsabilityEvaluator().evaluate(ctx(stair_model()))
    assert metric(result, "stair_min_headroom_m").value == pytest.approx(2.157, abs=0.001)
    assert metric(result, "stair_required_run_m").value == 4.2
    assert metric(result, "stair_landing_clear").value is True
    doc = stair_model().model_dump(mode="json")
    doc["stairs"][0].pop("walking_line")
    assert (
        metric(StairUsabilityEvaluator().evaluate(ctx(doc)), "stair_run_fit").status
        == ClaimStatus.NOT_CHECKED
    )


def test_stair_thresholds_configurable_and_landings_hit_by_doors():
    doc = stair_model().model_dump(mode="json")
    doc["stairs"][0]["riser_height_m"] = 0.23
    result = StairUsabilityEvaluator().evaluate(ctx(doc))
    assert "stair_rise_assumption" in {v.code for v in result.violations}
    relaxed = StairUsabilityEvaluator(UsabilityPolicy(max_rise_m=0.24)).evaluate(ctx(doc))
    assert "stair_rise_assumption" not in {v.code for v in relaxed.violations}
    doc["walls"].append(wall("landing-wall", (2.1, 6.4), (3.5, 6.4), level="upper"))
    doc["openings"].append(
        door(
            "landing-door",
            "landing-wall",
            0,
            connects=("exterior", "upper-room"),
            operation="swing_left",
            opens_into="upper-room",
        )
    )
    assert "door_stair_conflict" in {
        v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations
    }


def test_furniture_integrity_ids_references_overlap_and_round_trip():
    doc = model()
    doc["furniture"] = [furniture("bed"), furniture("wardrobe", "wardrobe", width=1.2, depth=0.6)]
    doc["clearance_zones"] = [
        dict(
            id="bed-access",
            element_id="bed",
            space_id="room",
            boundary=rectangle(1, 1, 3, 4),
            purpose="access",
            basis="synthetic",
        )
    ]
    house = HouseModel.model_validate(doc)
    assert HouseModel.model_validate_json(house.model_dump_json()) == house
    assert {"bed", "wardrobe", "bed-access"} <= set(house.all_ids())
    assert "fixture_overlap" in {v.code for v in check_model(house)}
    house.furniture[0].space_id = "missing"
    assert "dangling_reference" in {v.code for v in check_model(house)}


@pytest.mark.parametrize(
    "function,width,depth,label",
    [
        ("study", 3, 3, "desk_chair"),
        ("living", 4, 4, "living"),
        ("kitchen", 4, 4, "kitchen"),
        ("bathroom", 3, 3, "bathroom"),
        ("storage", 2, 3, "storage"),
        ("laundry", 3, 3, "laundry_folding"),
    ],
)
def test_furniture_studies_fit_clean_rooms_and_fail_tiny_rooms(function, width, depth, label):
    result = FurnitureUsabilityEvaluator().evaluate(ctx(model(width, depth, function)))
    assert metric(result, label + "_sampled_fit").value is True
    tiny = FurnitureUsabilityEvaluator().evaluate(ctx(model(0.8, 0.8, function)))
    assert metric(tiny, label + "_sampled_fit").value is False


def test_dining_size_depends_on_household_seats_and_unknown_is_explicit():
    doc = model(3.5, 3, "dining")
    evaluator = FurnitureUsabilityEvaluator()
    assert (
        metric(evaluator.evaluate(ctx(doc)), "dining_sampled_fit").status == ClaimStatus.NOT_CHECKED
    )
    assert (
        metric(
            evaluator.evaluate(ctx(doc, program=program(household_seats=4))), "dining_sampled_fit"
        ).value
        is True
    )
    assert (
        metric(
            evaluator.evaluate(ctx(doc, program=program(household_seats=12))), "dining_sampled_fit"
        ).value
        is False
    )


def test_garage_uses_vehicle_count_size_and_door_space():
    vehicle = dict(
        id="car", width_m=1.8, length_m=4.5, door_side_clearance_m=0.6, source="synthetic"
    )
    doc = model(3.4, 6.2, "garage")
    evaluator = FurnitureUsabilityEvaluator()
    assert (
        metric(
            evaluator.evaluate(ctx(doc, program=program(vehicles=[vehicle]))), "garage_sampled_fit"
        ).value
        is True
    )
    assert (
        metric(
            evaluator.evaluate(
                ctx(doc, program=program(vehicles=[vehicle, {**vehicle, "id": "car-2"}]))
            ),
            "garage_sampled_fit",
        ).value
        is False
    )
    assert (
        metric(evaluator.evaluate(ctx(doc)), "garage_sampled_fit").status == ClaimStatus.NOT_CHECKED
    )


def test_l_shaped_geodesic_and_obstacle_paths_hand_computed():
    poly = Polygon([(0, 0), (6, 0), (6, 2), (2, 2), (2, 6), (0, 6)])
    assert shortest_in_polygon(poly, (5, 1), (1, 5)) == pytest.approx(2 * math.sqrt(10))
    obstacle = box(0, 0, 6, 6).difference(box(2, 2, 4, 4))
    assert shortest_in_polygon(obstacle, (1, 3), (5, 3)) == pytest.approx(2 * math.sqrt(2) + 2)
    assert shortest_in_polygon(box(0, 0, 1, 1), (-1, 0), (1, 1)) is None


def test_explicit_floor_void_is_not_counted_or_walked_across():
    doc = model(6, 6)
    doc["slabs"] = [
        dict(
            id="floor",
            level_id="ground",
            kind="floor",
            thickness_m=0.2,
            boundary={
                "outer": rectangle(0, 0, 6, 6)["outer"],
                "holes": [rectangle(2, 2, 4, 4)["outer"]],
            },
        )
    ]
    house = HouseModel.model_validate(doc)
    floor = net_floor(house, house.spaces[0])
    assert floor.area == pytest.approx(5.85**2 - 4)
    assert shortest_in_polygon(floor, (1, 3), (5, 3)) == pytest.approx(2 * math.sqrt(2) + 2)


def test_portals_do_not_teleport_between_floors_or_outside():
    doc = model(4, 6, doors=True)
    doc["levels"].append(dict(id="upper", name="Upper", elevation_m=3))
    doc["spaces"].append(space("up", "family", (0, 0, 4, 6), "upper"))
    network = RouteNetwork(HouseModel.model_validate(doc))
    # Door centre (1.45, 0) to the room point (2, 3): the representative point sits on the
    # scanline midway between the vertex heights around the centre (0.075 and 5.925).
    route = network.from_entrance("room")
    assert route.length_m == pytest.approx(math.hypot(0.55, 3))
    assert route.element_ids == ("front-door", "room") and route.level_changes == 0
    assert network.from_entrance("up") is None
    doc = stair_model().model_dump(mode="json")
    doc["openings"] = [door()]
    route = RouteNetwork(HouseModel.model_validate(doc)).between("room", "upper-room")
    assert route.level_changes == 1 and "stair" in route.element_ids and not route.estimated
    doc["stairs"][0].pop("walking_line")
    # Without a walking line the flight is an estimated edge; routes using it are inferred.
    estimated = RouteNetwork(HouseModel.model_validate(doc)).between("room", "upper-room")
    assert estimated.estimated and estimated.level_changes == 1
    doc["stairs"][0]["riser_count"] = None
    assert RouteNetwork(HouseModel.model_validate(doc)).between("room", "upper-room") is None


def test_daily_routes_and_private_crossing_name_rooms():
    doc = model(4, 4, "entry", doors=True)
    doc["spaces"] += [
        space("private", "bedroom", (4, 0, 8, 4)),
        space("shared", "living", (8, 0, 12, 4)),
        space("garage", "garage", (12, 0, 16, 4)),
        space("kitchen", "kitchen", (16, 0, 20, 4)),
    ]
    doc["walls"] = [w for w in doc["walls"] if w["id"] != "east"]
    doc["zones"] = [dict(id="night", name="Night", privacy="private", space_ids=["private"])]
    doc["spaces"][1]["zone_id"] = "night"
    for i, (a, b) in enumerate(
        [("room", "private"), ("private", "shared"), ("shared", "garage"), ("garage", "kitchen")],
        start=1,
    ):
        doc["walls"].append(wall("p" + str(i), (4 * i, 0), (4 * i, 4)))
        doc["openings"].append(door("d" + str(i), "p" + str(i), 1, connects=(a, b)))
    result = RouteUsabilityEvaluator().evaluate(ctx(doc))
    assert any(
        v.code == "guest_route_crosses_private"
        and "private" in v.subject_ids
        and "shared" in v.subject_ids
        for v in result.violations
    )
    assert metric(result, "garage_to_kitchen_level_changes").value == 0
    assert metric(result, "garage_to_kitchen_rooms_crossed").value == "garage,kitchen"
    # Its length is hand computed in test_daily_route_length_hand_computed_and_long_route_flagged.


def test_vertical_acoustic_stack_and_clean_shift():
    doc = model(4, 4)
    doc["levels"].append(dict(id="upper", name="Upper", elevation_m=3))
    doc["spaces"].append(space("noisy", "laundry", (0, 0, 4, 4), "upper"))
    result = PrivacyUsabilityEvaluator().evaluate(ctx(doc))
    assert any(
        v.code == "bedroom_noise_stacking" and set(v.subject_ids) == {"room", "noisy"}
        for v in result.violations
    )
    doc["spaces"][-1]["boundary"] = rectangle(5, 0, 9, 4)
    assert not PrivacyUsabilityEvaluator().evaluate(ctx(doc)).violations


def test_daylight_retaining_buried_windows_cross_ventilation_and_missing_terrain():
    doc = model(4, 4, "living")
    doc["openings"] = [
        dict(
            id="win",
            kind="window",
            host_wall_id="south",
            offset_m=1,
            width_m=2,
            height_m=1.5,
            sill_m=0.9,
            connects=("room", "exterior"),
            operation="casement",
        )
    ]
    site = flat_site()
    evaluator = DaylightOpportunityEvaluator()
    clean = evaluator.evaluate(ctx(doc, site))
    # Clean twin: 2 x 1.5 m of glazing, sill 0.9 m over flat ground at the floor level.
    assert not {"window_buried", "low_daylight_opportunity"} & {v.code for v in clean.violations}
    assert metric(clean, "unburied_glazing_to_net_area").status == ClaimStatus.INFERRED
    assert metric(clean, "unburied_glazing_to_net_area").value == pytest.approx(
        3 / (3.85**2), abs=0.001
    )
    assert metric(clean, "window_capable_external_length_m").value == 16
    assert metric(clean, "cross_ventilation_opportunity").value is False
    doc["openings"].append({**doc["openings"][0], "id": "win-2", "host_wall_id": "north"})
    assert metric(evaluator.evaluate(ctx(doc, site)), "cross_ventilation_opportunity").value is True
    doc["walls"][0]["kind"] = "retaining"
    result = evaluator.evaluate(ctx(doc, site))
    assert [v.subject_ids for v in result.violations if v.code == "window_buried"] == [
        ["win", "south", "room"]
    ]
    assert metric(result, "window_capable_external_length_m").value == 12
    doc["walls"][0]["kind"] = "exterior"
    site.terrain.surface.vertices = [(x, y, 2) for x, y, _ in site.terrain.surface.vertices]
    # Ground 2 m up covers the 0.9..2.4 m window up to 2 m: both windows partly buried.
    buried = evaluator.evaluate(ctx(doc, site))
    assert [v.subject_ids for v in buried.violations if v.code == "window_buried"] == [
        ["win", "south", "room"],
        ["win-2", "north", "room"],
    ]
    assert (
        metric(evaluator.evaluate(ctx(doc)), "unburied_glazing_to_net_area").status
        == ClaimStatus.NOT_CHECKED
    )
    site.coordinates.local.id = "other"
    assert (
        metric(evaluator.evaluate(ctx(doc, site)), "unburied_glazing_to_net_area").status
        == ClaimStatus.NOT_CHECKED
    )


def test_outdoor_door_1_5m_above_and_below_grade_and_clean_twin():
    doc = model(4, 4, "entry", doors=True)
    site = flat_site()
    assert "outdoor_door_grade_mismatch" not in {
        v.code for v in DaylightOpportunityEvaluator().evaluate(ctx(doc, site)).violations
    }
    for elevation in (1.5, -1.5):
        doc["levels"][0]["elevation_m"] = elevation
        result = DaylightOpportunityEvaluator().evaluate(ctx(doc, site))
        assert metric(result, "outdoor_door_grade_delta_m").value == elevation
        assert any(
            v.code == "outdoor_door_grade_mismatch" and "front-door" in v.subject_ids
            for v in result.violations
        )


def test_vehicle_arrival_conservative_sweep_and_missing_road():
    vehicle = dict(
        id="car",
        width_m=1.8,
        length_m=4.5,
        door_side_clearance_m=0.6,
        turning_radius_m=5,
        source="synthetic",
    )
    req = program(vehicles=[vehicle], arrival_path=[(0, 0), (0, 8)])
    site = flat_site()
    site.features = []
    evaluator = VehicleArrivalEvaluator()
    assert (
        metric(evaluator.evaluate(ctx(model(), site, req)), "vehicle_swept_path").status
        == ClaimStatus.NOT_CHECKED
    )
    from house_ai.domain.site import SiteFeature

    site.features = [
        SiteFeature.model_validate(
            dict(
                id="drive",
                kind="driveway",
                geometry=dict(type="polygon", polygon=rectangle(-5, -5, 5, 13)),
            )
        )
    ]
    clear = evaluator.evaluate(ctx(model(), site, req))
    assert metric(clear, "vehicle_swept_path").value is True
    assert "vehicle_arrival_conflict" not in {v.code for v in clear.violations}
    site.features[0].geometry.polygon = HouseModel.model_validate(model(2, 12)).spaces[0].boundary
    assert "vehicle_arrival_conflict" in {
        v.code for v in evaluator.evaluate(ctx(model(), site, req)).violations
    }


def test_wardrobe_and_desk_pullout_conflict_with_door_and_clean_move():
    for ident, template_id, width, depth in [
        ("wardrobe", "wardrobe", 1.2, 0.6),
        ("desk", "desk", 1.2, 0.6),
    ]:
        doc = model(4, 6, "study", doors=True)
        doc["furniture"] = [furniture(ident, template_id, (1.4, 1.2), width, depth)]
        result = DoorClearanceEvaluator().evaluate(ctx(doc))
        assert any(
            v.code == "door_object_conflict" and ident in v.subject_ids for v in result.violations
        )
        doc["furniture"][0]["position"] = (2.8, 4)
        assert "door_object_conflict" not in {
            v.code for v in DoorClearanceEvaluator().evaluate(ctx(doc)).violations
        }


def test_declared_clearance_zone_is_grounded_in_door_conflict():
    doc = model(4, 6, doors=True)
    doc["furniture"] = [furniture("bed", position=(2.8, 4))]
    doc["clearance_zones"] = [
        dict(
            id="access",
            element_id="bed",
            space_id="room",
            boundary=rectangle(1, 0.1, 2, 1),
            purpose="access",
            basis="synthetic",
        )
    ]
    assert any(
        v.code == "door_clearance_zone_conflict"
        and set(v.subject_ids) == {"front-door", "access", "bed"}
        for v in DoorClearanceEvaluator().evaluate(ctx(doc)).violations
    )


def test_residual_space_excess_corridor_and_policy_threshold():
    doc = model(0.7, 5, "other")
    result = RouteUsabilityEvaluator().evaluate(ctx(doc))
    assert any(v.code == "residual_space" and "room" in v.subject_ids for v in result.violations)
    assert metric(result, "residual_area_m2").value == pytest.approx(0.55 * 4.85, abs=0.001)
    doc = model(2, 10, "corridor", doors=True)
    result = RouteUsabilityEvaluator().evaluate(ctx(doc))
    assert metric(result, "level_circulation_ratio").value == 1
    assert "excess_circulation" in {v.code for v in result.violations}
    assert "long_dead_end" not in {
        v.code
        for v in RouteUsabilityEvaluator(UsabilityPolicy(max_dead_end_m=20))
        .evaluate(ctx(doc))
        .violations
    }


def test_through_kitchen_and_seating_zone_clean_twin_with_one_door():
    for function, code in [
        ("kitchen", "kitchen_through_traffic"),
        ("living", "living_through_traffic"),
    ]:
        doc = model(4, 4, function)
        doc["spaces"] += [
            space("hall-a", "hall", (0, -2, 4, 0)),
            space("hall-b", "hall", (0, 4, 4, 6)),
        ]
        doc["openings"] = [
            door("a", "south", 1.5, connects=("hall-a", "room")),
            door("b", "north", 1.5, connects=("room", "hall-b")),
        ]
        assert any(
            v.code == code and "room" in v.subject_ids
            for v in RouteUsabilityEvaluator().evaluate(ctx(doc)).violations
        )
        doc["openings"].pop()
        assert code not in {v.code for v in RouteUsabilityEvaluator().evaluate(ctx(doc)).violations}


def test_invalid_threshold_configuration_rejected():
    with pytest.raises(ValueError):
        UsabilityPolicy(min_headroom_m=-1)
    with pytest.raises(ValueError):
        UsabilityPolicy(min_rise_m=0.3, max_rise_m=0.2)
    with pytest.raises(ValueError):
        UsabilityPolicy(min_headroom_m=float("nan"))


def test_additive_fields_preserve_legacy_canonical_hashes():
    from house_ai.storage.hashing import content_hash

    house = stair_model()
    # The pre-S6 canonical document has no added collections or walking-line key.
    house.stairs[0].walking_line = None
    legacy = house.model_dump(mode="json")
    assert "furniture" not in legacy and "clearance_zones" not in legacy
    assert "walking_line" not in legacy["stairs"][0]
    assert content_hash(HouseModel.model_validate(legacy)) == content_hash(legacy)
    old_program = program().model_dump(mode="json")
    assert "usability" not in old_program
    assert content_hash(SpaceProgram.model_validate(old_program)) == content_hash(old_program)
    changed = house.model_copy(deep=True)
    changed.furniture = [
        HouseModel.model_validate({**model(), "furniture": [furniture("bed")]}).furniture[0]
    ]
    assert content_hash(changed) != content_hash(legacy)


def test_all_critics_run_over_r2_cases_and_match_declared_expectations():
    from pathlib import Path

    from house_ai.domain.benchmark import BenchmarkFixture

    paths = sorted((Path(__file__).parents[2] / "examples/benchmarks/fixtures").glob("*.json"))
    assert len(paths) == 18
    count = 0
    covered, positive = set(), set()
    for path in paths:
        fixture = BenchmarkFixture.model_validate_json(path.read_text())
        # Runner outcomes: test_every_current_observation_matches_declared_expectations.
        assert not any(e.pending_stage == "S6" for e in fixture.expectations)
        for case in fixture.cases:
            count += 1
            expected = [
                e for e in fixture.expectations if e.source == "evaluation" and e.target == case.id
            ]
            for critic in USABILITY_EVALUATORS:
                result = critic.evaluate(
                    EvaluationContext(case.model, fixture.site, fixture.program, None)
                )
                assert result.run.status.value == "ran"
                assert all(
                    m.evaluator == critic.name
                    and m.method
                    and ((m.value is None) == (m.status == ClaimStatus.NOT_CHECKED))
                    for m in result.metrics
                )
                names = {m.metric for m in result.metrics}
                codes = {v.code for v in result.violations}
                for e in expected:
                    if e.metric in names or e.code in codes:
                        covered.add(critic.name)
                    if e.code in codes and e.value:
                        positive.add(critic.name)
    assert count >= 13
    # Every critic has a checked R2 expectation; all but the arrival and net-area critics
    # (no drive geometry; a net area is a metric) have an expected finding.
    assert covered == {e.name for e in USABILITY_EVALUATORS}
    assert positive == covered - {"VehicleArrivalEvaluator", "NetAreaEvaluator"}


def test_program_builder_seats_count_elders_and_keep_unknown_children():
    from datetime import UTC, datetime

    from house_ai.domain.brief import DesignBrief
    from house_ai.program.builder import build_program
    from tests.conftest import REPO

    brief = DesignBrief.model_validate(
        load_document(REPO / "examples/projects/synthetic-hillside/design_brief.yaml")
    )
    kwargs = dict(site=None, brief_ref=None, created_at=datetime(2026, 10, 18, tzinfo=UTC))
    assert build_program(brief, **kwargs).program.usability.household_seats == 4
    # Two parents, two children and a grandparent sit five at the table.
    adults = next(f for f in brief.facts if f.key == "adults")
    elders = adults.model_copy(update={"id": "f-elders", "key": "elders", "value": 1})
    brief.facts = [*brief.facts, elders]
    assert build_program(brief, **kwargs).program.usability.household_seats == 5
    brief.facts = [f for f in brief.facts if f.key != "children"]
    assert build_program(brief, **kwargs).program.usability.household_seats is None


def test_kitchen_actual_run_length():
    doc = model(4, 4, "kitchen")
    doc["furniture"] = [furniture("counter", "kitchen-run", (2, 3.5), 2, 0.6)]
    result = FurnitureUsabilityEvaluator().evaluate(ctx(doc))
    assert metric(result, "kitchen_counter_run_m").value == 2
    assert "kitchen_counter_run_short" in {v.code for v in result.violations}
    doc["furniture"][0]["width_m"] = 3
    assert "kitchen_counter_run_short" not in {
        v.code for v in FurnitureUsabilityEvaluator().evaluate(ctx(doc)).violations
    }


def test_stair_without_walking_line_is_unknown_and_reversed_levels_are_flagged():
    doc = stair_model().model_dump(mode="json")
    doc["stairs"][0]["kind"] = "u_shaped"
    doc["stairs"][0]["walking_line"] = None
    result = StairUsabilityEvaluator().evaluate(ctx(doc))
    assert metric(result, "stair_min_headroom_m").status == ClaimStatus.NOT_CHECKED
    assert RouteNetwork(ctx(doc).model).between("room", "upper-room").estimated
    doc["stairs"][0]["walking_line"] = [(2.5, 1.5), (2.5, 5.7)]
    doc["stairs"][0]["kind"] = "straight"
    doc["levels"][1]["elevation_m"] = -3
    assert "stair_nonascending_levels" in {
        v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations
    }


def _u_stair_doc(hole_y1: float):
    """A U-shaped flight, 3.0 m rise in 16 risers: two 2.0 m flights joined by a 1.3 m level
    half landing (ADR 0023). The upper floor is open over y 2..``hole_y1``."""
    doc = stair_model().model_dump(mode="json")
    doc["stairs"][0].update(
        kind="u_shaped",
        footprint=rectangle(1, 2, 3.4, 6),
        width_m=1.1,
        walking_line=[(1.55, 6), (1.55, 4), (2.85, 4), (2.85, 6)],
        landing_segments=[1],
    )
    doc["slabs"][0]["boundary"]["holes"] = [rectangle(1, 2, 3.4, hole_y1)["outer"]]
    return doc


def test_u_shaped_flight_is_measured_along_its_walking_line():
    doc = _u_stair_doc(6)
    house = HouseModel.model_validate(doc)
    assert house.stairs[0].vertex_heights(3.0) == [0.0, 1.5, 1.5, 3.0]
    result = StairUsabilityEvaluator().evaluate(ctx(doc))
    # (16 risers - 2 flights) x 0.28 m = 3.92 m of going within 4.0 m of flights.
    assert metric(result, "stair_required_run_m").value == pytest.approx(3.92)
    assert metric(result, "stair_run_fit").value is True
    # Open over the whole footprint: nothing overhead within the storey.
    assert metric(result, "stair_min_headroom_m").status == ClaimStatus.NOT_CHECKED
    net = RouteNetwork(ctx(doc).model)
    assert not net.between("room", "upper-room").estimated
    # Flights 2 x hypot(2.0, 1.5) = 5.0 m plus the 1.3 m level landing.
    stair_edges = {round(x, 9) for edges in net.edges.values() for _, x, s, _ in edges if s}
    assert stair_edges == {6.3}


def test_u_shaped_flight_headroom_follows_the_landing():
    # The upper floor covers y 5.5..6 over both flights' corridor ends.
    result = StairUsabilityEvaluator().evaluate(ctx(_u_stair_doc(5.5)))
    # Flight 2 reaches 3.0 m at y 6 under the 0.2 m slab at 3.0 m: 2.8 - 3.0 = -0.2 m.
    assert metric(result, "stair_min_headroom_m").value == pytest.approx(-0.2)
    assert "stair_low_headroom" in {v.code for v in result.violations}


def test_maximum_vehicle_id_and_bed_requirement_references():
    from pydantic import ValidationError

    vehicle = dict(
        id="v" * 64, width_m=1.8, length_m=4.5, door_side_clearance_m=0.6, source="synthetic"
    )
    result = FurnitureUsabilityEvaluator().evaluate(
        ctx(model(3.4, 6.2, "garage"), program=program(vehicles=[vehicle]))
    )
    assert metric(result, "garage_sampled_fit").value is True
    with pytest.raises(ValidationError):
        program(double_bed_space_requirement_ids=["nonexistent"])
    with pytest.raises(ValidationError):
        program(vehicles=[vehicle, vehicle])


_DEMO = Path(__file__).parents[2] / "examples/usability/demonstration/report.json"


def _demo_inputs():
    from house_ai.domain.site import Site

    folder = Path(__file__).parents[2] / "examples/projects/synthetic-hillside"
    site = Site.model_validate(load_document(folder / "site.yaml"))
    return site, SpaceProgram.model_validate(load_document(folder / "space_program.yaml"))


def test_committed_demo_is_grounded_and_has_three_integrity_checked_concepts():
    """Each claim in the report is re-derived: integrity from the committed models, the
    seeded-defect table from the scenarios; the critics' output is compared in
    test_committed_demo_report_matches_a_fresh_evaluation."""
    import json

    from house_ai.storage.hashing import content_hash

    report = json.loads(_DEMO.read_text())
    assert report["exploratory"] and not report["site_approved"] and not report["program_approved"]
    assert [r["strategy"] for r in report["options"]] == ["compact", "split_level", "linear"]
    for row in report["options"]:
        house = HouseModel.model_validate(row["model"])
        assert content_hash(house) == row["model_hash"]
        assert check_model(house) == [] and row["integrity_clean"] is True
        assert [r["name"] for r in row["critics"]] == [e.name for e in USABILITY_EVALUATORS]
        assert all(set(v["subject_ids"]) <= set(house.all_ids()) for v in row["findings"])
        # Real geometric integrity does not imply architectural usability.
        assert len(row["findings"]) > 0
    recomputed = []
    for ident, name, bad, clean, code, subject, pair_program in seeded_pairs():
        critic = next(e for e in USABILITY_EVALUATORS if e.name == name)
        found, twin = (
            critic.evaluate(EvaluationContext(m, None, pair_program, None)).violations
            for m in (bad, clean)
        )
        recomputed.append(
            dict(
                id=ident,
                code=code,
                subject=subject,
                defect_detected=any(v.code == code and subject in v.subject_ids for v in found),
                clean_twin_passes=code not in {v.code for v in twin},
            )
        )
    assert all(r["defect_detected"] and r["clean_twin_passes"] for r in recomputed)
    assert report["defects"] == recomputed


def test_committed_demo_report_matches_a_fresh_evaluation():
    """A stale report must fail: same inputs, and the critics' output recomputed."""
    import json

    from house_ai.storage.hashing import content_hash

    report = json.loads(_DEMO.read_text())
    site, hillside = _demo_inputs()
    assert report["input_hashes"] == dict(site=content_hash(site), program=content_hash(hillside))
    for row in report["options"]:
        house = HouseModel.model_validate(row["model"])
        results = [
            e.evaluate(EvaluationContext(house, site, hillside, None, False))
            for e in USABILITY_EVALUATORS
        ]
        assert row["critics"] == [r.run.model_dump(mode="json") for r in results]
        assert row["findings"] == [v.model_dump(mode="json") for r in results for v in r.violations]
        assert row["metrics"] == [m.model_dump(mode="json") for r in results for m in r.metrics]


# ---------------------------------------------------------------- S6 review 1 regressions


def _rotated(doc, degrees):
    a = math.radians(degrees)

    def r(p):
        return (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a))

    doc = {**doc}
    doc["spaces"] = [
        {**s, "boundary": {"outer": [r(p) for p in s["boundary"]["outer"]]}} for s in doc["spaces"]
    ]
    doc["walls"] = [{**w, "start": r(w["start"]), "end": r(w["end"])} for w in doc["walls"]]
    return doc


@pytest.mark.parametrize("degrees", [0, 12, 45])
def test_furniture_verdict_does_not_depend_on_plan_rotation(degrees):
    # 3.4 m wide rooms hold the 2.8 x 2.75 m double-bed envelope; 2.6 m rooms do not.
    for width, fits in [(3.4, True), (2.6, False)]:
        doc = _rotated(model(width, 5), degrees)
        result = FurnitureUsabilityEvaluator().evaluate(ctx(doc))
        assert metric(result, "bed_double_sampled_fit").value is fits


def test_door_on_wall_with_generator_coordinate_noise_still_routes():
    # The shared wall sits 4e-7 m off both room edges, as rotated generated plans do.
    doc = model(4, 4, "entry", doors=True)
    doc["spaces"].append(space("next", "living", (4, 0, 8, 4)))
    doc["walls"] = [w for w in doc["walls"] if w["id"] != "east"] + [
        wall("north-2", (8, 4), (4, 4), kind="exterior"),
        wall("east-2", (8, 0), (8, 4), kind="exterior"),
        wall("south-2", (4, 0), (8, 0), kind="exterior"),
        wall("shared", (4 + 4e-7, 0), (4 + 4e-7, 4)),
    ]
    doc["openings"].append(door("inner", "shared", 1, connects=("room", "next")))
    house = HouseModel.model_validate(doc)
    # Front door (1.45, 0) -> inner door (4, 1.45) -> next's point (6, 2.9125), the 4e-7 m
    # offset aside: the scanline sits midway between the vertex heights 1.9 and 3.925.
    route = RouteNetwork(house).from_entrance("next")
    assert route.length_m == pytest.approx(math.hypot(2.55, 1.45) + math.hypot(2, 1.4625))
    assert route.element_ids == ("front-door", "inner", "next")
    result = NetAreaEvaluator().evaluate(ctx(house))
    assert metric(result, "net_wall_basis_complete", "next").value is True


def test_fit_search_is_bounded_and_identical_vehicles_are_interchangeable(monkeypatch):
    from house_ai.evaluation import usability_geometry
    from house_ai.evaluation.usability import FurnitureUsabilityEvaluator as F
    from house_ai.evaluation.usability_geometry import _dimensions

    car = dict(id="car", width_m=1.8, length_m=4.5, door_side_clearance_m=0.6, source="synthetic")
    cars = [car, {**car, "id": "car-2"}, {**car, "id": "car-3"}]
    # Vehicles differ by ID only: their placement identity is equal, so they are interchangeable.
    from house_ai.evaluation.usability import _CriticOut

    garage = ctx(model(7, 6.5, "garage"), program=program(vehicles=cars))
    templates = F()._studies(garage, garage.model.spaces[0], _CriticOut("study"))
    assert len({_dimensions(t) for t in templates[0][1]}) == 1
    evaluator = F()
    two = program(vehicles=cars[:2])
    doc = model(7, 6.5, "garage")
    assert metric(evaluator.evaluate(ctx(doc, program=two)), "garage_sampled_fit").value is True
    # End to end, IDs and sources do not change the verdict or which bodies are placed.
    renamed = [{**c, "id": f"other-{i}", "source": "other synthetic"} for i, c in enumerate(cars)]
    for vehicles in (renamed[:2], cars[1::-1]):
        again = evaluator.evaluate(ctx(doc, program=program(vehicles=vehicles)))
        assert [(m.metric, m.value, m.method) for m in again.metrics] == [
            (m.metric, m.value, m.method)
            for m in evaluator.evaluate(ctx(doc, program=two)).metrics
        ]
    # 5.4 m: three 1.8 m bodies with 0.6 m door zones need 7.8 m; decided as no fit.
    narrow = evaluator.evaluate(ctx(model(5.4, 6.5, "garage"), program=program(vehicles=cars)))
    assert metric(narrow, "garage_sampled_fit").value is False
    assert "garage_no_sampled_fit" in {v.code for v in narrow.violations}
    # 7 m: still undecided within the search budget; reported as not checked, not as a failure.
    # The bound is a count of candidate placements tried, not a clock.
    assert usability_geometry.FIT_BUDGET == 200_000
    result = evaluator.evaluate(ctx(doc, program=program(vehicles=cars)))
    fit = metric(result, "garage_sampled_fit")
    assert (fit.status, fit.method) == (
        ClaimStatus.NOT_CHECKED,
        "search_budget_exhausted_before_decision",
    )
    assert "garage_no_sampled_fit" not in {v.code for v in result.violations}
    # With a 10-placement budget even the decidable two-car case stops undecided.
    monkeypatch.setattr(usability_geometry, "FIT_BUDGET", 10)
    usability_geometry._fit_cached.cache_clear()
    try:
        tiny = metric(evaluator.evaluate(ctx(doc, program=two)), "garage_sampled_fit")
    finally:
        usability_geometry._fit_cached.cache_clear()
    assert (tiny.status, tiny.method) == (
        ClaimStatus.NOT_CHECKED,
        "search_budget_exhausted_before_decision",
    )


def test_riser_heights_rounded_to_four_places_are_not_a_mismatch():
    doc = stair_model().model_dump(mode="json")
    # 3 m in 17 risers is stored as 0.1765 m: 17 x 0.1765 = 3.0005 m.
    doc["stairs"][0]["riser_count"] = 17
    doc["stairs"][0]["riser_height_m"] = round(3 / 17, 4)
    result = StairUsabilityEvaluator().evaluate(ctx(doc))
    assert metric(result, "stair_rise_error_m").value == pytest.approx(0.0005, abs=1e-3)
    assert "stair_height_mismatch" not in {v.code for v in result.violations}
    doc["stairs"][0]["riser_height_m"] = 0.18
    assert "stair_height_mismatch" in {
        v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations
    }


def test_floor_to_floor_is_only_compared_for_a_stair_to_the_next_level():
    doc = stair_model().model_dump(mode="json")
    doc["levels"][0]["floor_to_floor_m"] = 3.2
    assert any(
        v.code == "floor_connection_height_mismatch" and "stair" in v.subject_ids
        for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations
    )
    # A mezzanine between the stair's levels: the stair spans two storeys.
    doc["levels"][0]["floor_to_floor_m"] = 1.5
    doc["levels"].append(dict(id="mezzanine", name="Mezzanine", elevation_m=1.5))
    assert "floor_connection_height_mismatch" not in {
        v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations
    }


def test_floor_to_floor_is_not_compared_beside_a_lower_storey():
    """ADR 0023: a split-level stair arriving beside the lower storey says nothing about its
    height; the same stair arriving over it (stacked) still does."""
    doc = stair_model().model_dump(mode="json")
    doc["levels"][0]["floor_to_floor_m"] = 3.2  # stacked: 3.2 m declared, 3.0 m rise
    assert "floor_connection_height_mismatch" in {
        v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations
    }
    # The upper room moves beside the lower one (y 8..16) and the flight crosses into it:
    # it arrives beyond the lower storey, as between split-level bars.
    upper = next(s for s in doc["spaces"] if s["id"] == "upper-room")
    upper["boundary"] = rectangle(0, 8, 5, 16)
    flight = doc["stairs"][0]
    flight["footprint"] = rectangle(2, 4, 3, 9.2)
    flight["walking_line"] = [(2.5, 4), (2.5, 9.2)]
    doc["slabs"] = []
    codes = {v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations}
    assert "floor_connection_height_mismatch" not in codes
    # Arriving over the lower room (stacked again), the rule still applies.
    upper["boundary"] = rectangle(0, 0, 5, 16)
    flight["footprint"] = rectangle(2, 1.5, 3, 5.7)
    flight["walking_line"] = [(2.5, 1.5), (2.5, 5.7)]
    codes = {v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations}
    assert "floor_connection_height_mismatch" in codes
    # The rise itself is still checked against the level elevations.
    doc["stairs"][0]["riser_height_m"] = 0.2
    codes = {v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations}
    assert "stair_height_mismatch" in codes


def test_flight_through_a_wall_clashes_unless_an_opening_clears_the_band():
    """ADR 0023: a wall across the walking line must stay out of the clear band."""
    doc = stair_model().model_dump(mode="json")
    # 16 x 0.1875 m over 4.2 m; a wall across y = 3.6 meets the pitch at 1.5 m.
    doc["walls"].append(
        dict(id="w-cross", level_id="ground", start=(0, 3.6), end=(5, 3.6),
             thickness_m=0.15, height_m=2.8, kind="interior")
    )  # fmt: skip
    result = StairUsabilityEvaluator().evaluate(ctx(doc))
    clash = [v for v in result.violations if v.code == "stair_wall_clash"]
    assert len(clash) == 1 and clash[0].subject_ids == ["stair", "w-cross"]
    assert "between 1.500 and 2.800 m" in clash[0].message
    assert metric(result, "stair_wall_clashes").value == 1
    # A wall that starts above the band (pitch 1.5 + 2.0 = 3.5 m) does not clash.
    doc["walls"][-1]["base_offset_m"] = 3.6
    assert "stair_wall_clash" not in {
        v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations
    }
    # Nor does an opening spanning the flight's 1 m width and the band.
    doc["walls"][-1]["base_offset_m"] = 0.0
    doc["openings"].append(
        dict(id="o-cross", kind="opening", host_wall_id="w-cross", offset_m=1.9,
             width_m=1.2, height_m=2.8, connects=("room", "exterior"))
    )  # fmt: skip
    result = StairUsabilityEvaluator().evaluate(ctx(doc))
    assert "stair_wall_clash" not in {v.code for v in result.violations}
    assert metric(result, "stair_wall_clashes").value == 0


def test_stair_flight_is_not_walkable_floor_on_either_level():
    doc = stair_model().model_dump(mode="json")
    house = HouseModel.model_validate(doc)
    network = RouteNetwork(house)
    flight = house.stairs[0].footprint.to_shapely()
    for sid in ("room", "upper-room"):
        assert not flight.contains(Point(network.nodes["space:" + sid][1]))
    # West to east across the flight (x 2..3, y 1.5..5.7) must go round it.
    from house_ai.evaluation.usability_geometry import free_floor

    floor = free_floor(house, house.space("room"))
    assert shortest_in_polygon(floor, (1, 3), (4, 3)) > 3 + 1e-6


def test_estimated_stair_route_is_inferred_not_measured():
    doc = stair_model().model_dump(mode="json")
    doc["openings"] = [door()]
    doc["stairs"][0].pop("walking_line")
    result = RouteUsabilityEvaluator().evaluate(ctx(doc))
    upper = metric(result, "entrance_route_length_m", "upper-room")
    assert upper.status == ClaimStatus.INFERRED and "estimated" in upper.method
    assert metric(result, "entrance_route_length_m", "room").status == ClaimStatus.MEASURED


def test_doors_with_a_threshold_still_join_routes():
    doc = model(4, 4, "entry", doors=True)
    doc["openings"][0]["sill_m"] = 0.02
    # A raised threshold adds no floor recess, so the door joins the floor at its finish
    # face y = 0.075: (1.45, 0.075) to the room point (2, 2).
    route = RouteNetwork(HouseModel.model_validate(doc)).from_entrance("room")
    assert route.length_m == pytest.approx(math.hypot(0.55, 1.925))
    assert route.element_ids == ("front-door", "room")


def test_route_network_is_shared_between_critics_for_one_model():
    house = HouseModel.model_validate(model(4, 4, doors=True))
    assert RouteNetwork.for_model(house) is RouteNetwork.for_model(house.model_copy(deep=True))
    changed = house.model_copy(deep=True)
    changed.openings = []
    assert RouteNetwork.for_model(changed) is not RouteNetwork.for_model(house)


def test_dead_end_twins_are_both_measured_hand_computed():
    from examples.usability.scenarios import corridor_model

    # Door centre (10, 1.45); farthest finish-face corner (11.925, L - 0.075).
    for length, expected in [(10, math.hypot(1.925, 8.475)), (4, math.hypot(1.925, 2.475))]:
        result = RouteUsabilityEvaluator().evaluate(ctx(corridor_model(length)))
        dead_end = metric(result, "dead_end_length_m", "corridor")
        assert dead_end.status == ClaimStatus.MEASURED
        assert dead_end.value == pytest.approx(expected, abs=1e-3)
        assert "excess_circulation" not in {v.code for v in result.violations}


def test_daily_route_length_hand_computed_and_long_route_flagged():
    doc = model(4, 4, "entry", doors=True)
    doc["spaces"] += [
        space("garage", "garage", (4, 0, 8, 4)),
        space("kitchen", "kitchen", (8, 0, 40, 4)),
    ]
    doc["walls"] = [w for w in doc["walls"] if w["id"] != "east"]
    for i, (a, b) in enumerate([("room", "garage"), ("garage", "kitchen")], start=1):
        doc["walls"].append(wall("p" + str(i), (4 * i, 0), (4 * i, 4)))
        doc["openings"].append(door("d" + str(i), "p" + str(i), 1, connects=(a, b)))
    result = RouteUsabilityEvaluator().evaluate(ctx(doc))
    # Room points sit on the scanline midway between the vertex heights nearest the centre:
    # garage (6, (1.9 + 3.925) / 2), kitchen (24.0375, (1.9 + 4) / 2). Door d2 is at (8, 1.45).
    expected = math.hypot(2, 2.9125 - 1.45) + math.hypot(16.0375, 2.95 - 1.45)
    assert metric(result, "garage_to_kitchen_length_m").value == pytest.approx(expected, abs=1e-3)
    assert any(
        v.code == "daily_route_long" and {"garage", "kitchen", "d2"} <= set(v.subject_ids)
        for v in result.violations
    )


def test_door_door_conflict_names_both_doors_and_clean_twin():
    doc = model(4, 3, doors=True)
    doc["openings"].append(door("second", offset=1.8, operation="swing_right", opens_into="room"))
    conflicts = [
        v
        for v in DoorClearanceEvaluator().evaluate(ctx(doc)).violations
        if v.code == "door_door_conflict"
    ]
    assert conflicts and set(conflicts[0].subject_ids) == {"front-door", "second"}
    doc["openings"][1]["offset_m"] = 3
    assert "door_door_conflict" not in {
        v.code for v in DoorClearanceEvaluator().evaluate(ctx(doc)).violations
    }


def test_desk_pullout_zone_not_body_hits_door_sweep():
    doc = model(4, 6, "study", doors=True)
    # Door sweep reaches y = 0.9; desk body spans y 1.3-1.9, its 0.9 m pull-out y 0.4-1.3.
    doc["furniture"] = [furniture("desk", "desk", (1.45, 1.6), 1.2, 0.6)]
    house = HouseModel.model_validate(doc)
    sweep = door_geometry(house, house.openings[0]).swept
    assert sweep.intersection(house.furniture[0].footprint_polygon().to_shapely()).area == 0
    assert any(
        v.code == "door_object_conflict" and "desk" in v.subject_ids
        for v in DoorClearanceEvaluator().evaluate(ctx(house)).violations
    )


def test_door_approach_blocked_by_object_body():
    doc = model(4, 6, "study", doors=True)
    doc["openings"][0]["operation"] = "sliding"
    # Approach zone is 0.9 m from the finish face at y = 0.075; a wardrobe sits in it.
    doc["furniture"] = [furniture("wardrobe", "wardrobe", (1.45, 0.6), 1.2, 0.6)]
    assert any(
        v.code == "door_approach_blocked" and "wardrobe" in v.subject_ids
        for v in DoorClearanceEvaluator().evaluate(ctx(doc)).violations
    )
    doc["furniture"][0]["position"] = (2.8, 5)
    assert "door_approach_blocked" not in {
        v.code for v in DoorClearanceEvaluator().evaluate(ctx(doc)).violations
    }


def test_door_approach_is_measured_from_the_finish_face():
    doc = model(4, 3)
    doc["openings"] = [door(operation="sliding")]
    house = HouseModel.model_validate(doc)
    zone = door_geometry(house, house.openings[0], 0.9).approaches["room"]
    assert zone.bounds == pytest.approx((1, 0.075, 1.9, 0.975))


def test_kitchen_aisle_between_facing_runs():
    doc = model(4, 4, "kitchen")
    # Fronts are local -Y: the north run is rotated 0 (faces south), the south run 180.
    doc["furniture"] = [
        furniture("north-run", "kitchen-run", (2, 3.625), 3, 0.6),
        furniture("south-run", "kitchen-run", (2, 1.375), 3, 0.6, rotation_deg=180),
    ]
    result = FurnitureUsabilityEvaluator().evaluate(ctx(doc))
    assert metric(result, "kitchen_aisle_width_m").value == pytest.approx(1.65)
    assert "kitchen_aisle_narrow" not in {v.code for v in result.violations}
    doc["furniture"][1]["position"] = (2, 1.825)
    result = FurnitureUsabilityEvaluator().evaluate(ctx(doc))
    assert metric(result, "kitchen_aisle_width_m").value == pytest.approx(1.2)
    assert any(
        v.code == "kitchen_aisle_narrow" and {"north-run", "south-run"} <= set(v.subject_ids)
        for v in result.violations
    )


def test_garage_pedestrian_route_blocked_by_vehicle_body():
    from house_ai.evaluation.usability import _CriticOut

    doc = model(3.4, 6.2, "garage")
    doc["spaces"].append(space("hall", "hall", (3.4, 0, 6, 6.2)))
    doc["walls"] = [w for w in doc["walls"] if w["id"] != "east"] + [
        wall("east", (3.4, 0), (3.4, 6.2))
    ]
    doc["openings"] = [door("house-door", "east", 1, connects=("room", "hall"))]
    house = HouseModel.model_validate(doc)
    evaluator = FurnitureUsabilityEvaluator()
    # Net floor x 0.075-3.325. A body across the full width cuts the clear zone beyond it
    # (y 4-6.125) off from the house door at y 1.45; a 0.825 m side gap reconnects it.
    for body, blocked in [(box(0.075, 2, 3.325, 4), True), (box(0.075, 2, 2.5, 4), False)]:
        out = _CriticOut(evaluator.name)
        env = box(0.075, 2, 3.325, 6.125)
        evaluator._garage_route(out, house, house.space("room"), [(body, env)])
        result = out.result()
        assert metric(result, "garage_pedestrian_route").value is (not blocked)
        assert blocked == any(
            v.code == "garage_pedestrian_route_blocked" and "house-door" in v.subject_ids
            for v in result.violations
        )


def test_accessible_turning_space_missing_in_narrow_room():
    doc = load_document(Path_examples() / "projects/synthetic-bungalow/space_program.yaml")
    item = next(i for i in doc["items"] if i["id"] == "pi-bath")
    item["accessible"] = True
    prog = SpaceProgram.model_validate(doc)
    narrow = model(1.5, 4, "bathroom")
    narrow["spaces"][0]["program_item_id"] = "pi-bath"
    result = FurnitureUsabilityEvaluator().evaluate(ctx(narrow, program=prog))
    assert metric(result, "accessible_turning_space").value is False
    assert "accessible_turning_space_missing" in {v.code for v in result.violations}
    wide = model(2, 3, "bathroom")
    wide["spaces"][0]["program_item_id"] = "pi-bath"
    result = FurnitureUsabilityEvaluator().evaluate(ctx(wide, program=prog))
    assert metric(result, "accessible_turning_space").value is True


def Path_examples():
    from pathlib import Path

    return Path(__file__).parents[2] / "examples"


def test_stair_width_going_and_invalid_walking_line_findings():
    doc = stair_model().model_dump(mode="json")
    doc["stairs"][0]["width_m"] = 0.8
    doc["stairs"][0]["tread_depth_m"] = 0.2
    codes = {v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations}
    assert {"stair_width_assumption", "stair_going_assumption"} <= codes
    clean = {v.code for v in StairUsabilityEvaluator().evaluate(ctx(stair_model())).violations}
    assert not {"stair_width_assumption", "stair_going_assumption"} & clean
    doc = stair_model().model_dump(mode="json")
    doc["stairs"][0]["walking_line"] = [(2.5, 1.5), (2.5, 1.5)]
    assert any(
        v.code == "stair_walking_line_invalid" and "stair" in v.subject_ids
        for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations
    )


def test_low_daylight_opportunity_ratio_hand_computed():
    doc = model(4, 4, "living")
    doc["openings"] = [
        dict(
            id="win",
            kind="window",
            host_wall_id="south",
            offset_m=1,
            width_m=0.6,
            height_m=1.0,
            sill_m=0.9,
            connects=("room", "exterior"),
            operation="casement",
        )
    ]
    result = DaylightOpportunityEvaluator().evaluate(ctx(doc, flat_site()))
    # 0.6 m² of glazing over 3.85² m² of net floor is about 4 %, below the 10 % assumption.
    assert metric(result, "unburied_glazing_to_net_area").value == pytest.approx(
        0.6 / 3.85**2, abs=1e-3
    )
    assert [v.subject_ids for v in result.violations if v.code == "low_daylight_opportunity"] == [
        ["room"]
    ]
    # Clean twin: a 1.6 x 1.0 m window gives 1.6 / 14.8225 = 10.8 % >= 10 %.
    doc["openings"][0]["width_m"] = 1.6
    result = DaylightOpportunityEvaluator().evaluate(ctx(doc, flat_site()))
    ratio = metric(result, "unburied_glazing_to_net_area")
    assert ratio.status == ClaimStatus.INFERRED
    assert ratio.value == pytest.approx(1.6 / 3.85**2, abs=1e-3)
    assert "low_daylight_opportunity" not in {v.code for v in result.violations}


def test_net_area_from_incomplete_walls_is_inferred_and_tiny_rooms_do_not_crash():
    doc = model(4, 3)
    doc["walls"] = doc["walls"][:2]
    result = NetAreaEvaluator().evaluate(ctx(doc))
    assert metric(result, "net_area_m2").status == ClaimStatus.INFERRED
    assert metric(result, "net_wall_basis_complete").value is False
    result = NetAreaEvaluator().evaluate(ctx(model(0.1, 0.1)))
    assert metric(result, "net_area_m2").value == 0
    assert metric(result, "net_extent_short_m").status == ClaimStatus.NOT_CHECKED


def test_reflex_corner_wall_junction_is_not_floor():
    doc = model(6, 6, "living")
    doc["spaces"][0]["boundary"] = {"outer": [(0, 0), (6, 0), (6, 2), (2, 2), (2, 6), (0, 6)]}
    doc["walls"] = [
        wall("w1", (0, 0), (6, 0), kind="exterior", thickness=0.3),
        wall("w2", (6, 0), (6, 2), kind="exterior", thickness=0.3),
        wall("w3", (6, 2), (2, 2), kind="exterior", thickness=0.3),
        wall("w4", (2, 2), (2, 6), kind="exterior", thickness=0.3),
        wall("w5", (2, 6), (0, 6), kind="exterior", thickness=0.3),
        wall("w6", (0, 6), (0, 0), kind="exterior", thickness=0.3),
    ]
    house = HouseModel.model_validate(doc)
    floor = net_floor(house, house.spaces[0])
    # L of arm width 2 minus 0.15 m wall halves: 5.7 x 1.7 + 1.7 x 4.0.
    assert floor.area == pytest.approx(5.7 * 1.7 + 1.7 * 4.0)
    assert not floor.contains(Point(2.1, 2.1))


def test_floor_slab_voids_count_at_any_top_offset():
    doc = model(4, 4)
    doc["slabs"] = [
        dict(
            id="floor",
            level_id="ground",
            kind="floor",
            thickness_m=0.2,
            top_offset_m=0.05,
            boundary={
                "outer": rectangle(0, 0, 4, 4)["outer"],
                "holes": [rectangle(1, 1, 3, 3)["outer"]],
            },
        )
    ]
    house = HouseModel.model_validate(doc)
    assert net_floor(house, house.spaces[0]).area == pytest.approx(3.85**2 - 4)


def test_vehicle_corner_fillet_must_fit_its_legs_and_stay_on_the_drive():
    from house_ai.domain.site import SiteFeature
    from house_ai.evaluation.usability import filleted_path

    # A right-angle corner with radius r has tangent length r: it fits 6 m legs, not 3 m.
    assert filleted_path([(0, 0), (6, 0), (6, 6)], 5.5) is not None
    assert filleted_path([(0, 0), (3, 0), (3, 3)], 5.5) is None
    arc = filleted_path([(0, 0), (6, 0), (6, 6)], 5.5)
    assert all(math.dist(p, (0.5, 5.5)) == pytest.approx(5.5) for p in arc[1:-1])
    vehicle = dict(
        id="car",
        width_m=1.8,
        length_m=4.5,
        door_side_clearance_m=0.6,
        turning_radius_m=5.5,
        source="synthetic",
    )
    site = flat_site()
    req = program(vehicles=[vehicle], arrival_path=[(0, 0), (20, 0), (20, 20)])
    # L-shaped drive 6 m wide: the filleted corner sweep stays on it.
    drive = Polygon([(-3, -3), (23, -3), (23, 23), (17, 23), (17, 3), (-3, 3)])
    site.features = [
        SiteFeature.model_validate(
            dict(
                id="drive",
                kind="driveway",
                geometry=dict(type="polygon", polygon={"outer": list(drive.exterior.coords)[:-1]}),
            )
        )
    ]
    evaluator = VehicleArrivalEvaluator()
    assert metric(evaluator.evaluate(ctx(model(), site, req)), "vehicle_swept_path").value is False
    vehicle["turning_radius_m"] = 25
    req = program(vehicles=[vehicle], arrival_path=[(0, 0), (20, 0), (20, 20)])
    assert any(
        v.code == "vehicle_arrival_conflict"
        for v in evaluator.evaluate(ctx(model(), site, req)).violations
    )


def test_undesignated_bedroom_needs_a_single_bed_only():
    result = FurnitureUsabilityEvaluator().evaluate(ctx(model(2.6, 5)))
    assert metric(result, "bed_double_sampled_fit").value is False
    assert metric(result, "bed_single_sampled_fit").value is True
    assert not {v.code for v in result.violations} & {
        "bed_double_no_sampled_fit",
        "bed_single_no_sampled_fit",
    }
    result = FurnitureUsabilityEvaluator().evaluate(ctx(model(1.2, 5)))
    assert "bed_single_no_sampled_fit" in {v.code for v in result.violations}


def test_hillside_concepts_reference_the_current_program():
    import json

    from house_ai.storage.hashing import content_hash

    root = Path_examples() / "projects/synthetic-hillside"
    current = content_hash(SpaceProgram.model_validate(load_document(root / "space_program.yaml")))
    plans = sorted(root.glob("concepts/*/exploratory/plan.json"))
    assert plans
    for path in plans:
        inputs = json.loads(path.read_text())["provenance"]["inputs"]
        assert next(i for i in inputs if i["kind"] == "space_program")["sha256"] == current
