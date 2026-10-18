from __future__ import annotations

import math

import pytest
from shapely.geometry import Polygon, box

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
    _, critic_name, bad, clean, code, subject = case
    critic = next(e for e in USABILITY_EVALUATORS if e.name == critic_name)
    defects = critic.evaluate(ctx(bad)).violations
    assert any(v.code == code and subject in v.subject_ids for v in defects)
    assert code not in {v.code for v in critic.evaluate(ctx(clean)).violations}
    for result in [critic.evaluate(ctx(bad)), critic.evaluate(ctx(clean))]:
        assert all(v.method and v.assumption_basis and v.subject_ids for v in result.violations)
        assert all(v.strength.value == "soft" for v in result.violations)


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


def test_door_wall_door_conflict_and_unknown_swing():
    doc = model(4, 3, doors=True)
    doc["walls"].append(wall("wall-end", (1.5, 0.3), (1.5, 1)))
    result = DoorClearanceEvaluator().evaluate(ctx(doc))
    assert any(
        v.code == "door_wall_conflict" and "wall-end" in v.subject_ids for v in result.violations
    )
    doc["openings"].append(door("second", offset=1.8, operation="swing_right", opens_into="room"))
    assert "door_door_conflict" in {
        v.code for v in DoorClearanceEvaluator().evaluate(ctx(doc)).violations
    }
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
    assert network.from_entrance("room") is not None
    assert network.from_entrance("up") is None
    doc = stair_model().model_dump(mode="json")
    doc["openings"] = [door()]
    route = RouteNetwork(HouseModel.model_validate(doc)).between("room", "upper-room")
    assert route.level_changes == 1 and "stair" in route.element_ids
    doc["stairs"][0].pop("walking_line")
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
    assert metric(result, "garage_to_kitchen_length_m").value > 4


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
    assert metric(clean, "unburied_glazing_to_net_area").value == pytest.approx(
        3 / (3.85**2), abs=0.001
    )
    assert metric(clean, "window_capable_external_length_m").value == 16
    assert metric(clean, "cross_ventilation_opportunity").value is False
    doc["openings"].append({**doc["openings"][0], "id": "win-2", "host_wall_id": "north"})
    assert metric(evaluator.evaluate(ctx(doc, site)), "cross_ventilation_opportunity").value is True
    doc["walls"][0]["kind"] = "retaining"
    result = evaluator.evaluate(ctx(doc, site))
    assert any(v.code == "window_buried" and "win" in v.subject_ids for v in result.violations)
    assert metric(result, "window_capable_external_length_m").value == 12
    doc["walls"][0]["kind"] = "exterior"
    site.terrain.surface.vertices = [(x, y, 2) for x, y, _ in site.terrain.surface.vertices]
    assert "window_buried" in {v.code for v in evaluator.evaluate(ctx(doc, site)).violations}
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
    assert metric(evaluator.evaluate(ctx(model(), site, req)), "vehicle_swept_path").value is True
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


def test_bathroom_privacy_ray_occluded_by_screen():
    doc = model(4, 4, "entry", doors=True)
    doc["spaces"].append(space("bath", "bathroom", (4, 0, 7, 4)))
    doc["openings"].append(door("bath-door", "east", 1.5, connects=("room", "bath")))
    result = PrivacyUsabilityEvaluator().evaluate(ctx(doc))
    assert any(
        v.code == "bathroom_entrance_visible" and "bath-door" in v.subject_ids
        for v in result.violations
    )
    doc["walls"].append(wall("screen", (3, 0.1), (3, 3.9)))
    assert "bathroom_entrance_visible" not in {
        v.code for v in PrivacyUsabilityEvaluator().evaluate(ctx(doc)).violations
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

    from house_ai.benchmarks.runner import run_fixture
    from house_ai.domain.benchmark import BenchmarkFixture

    paths = sorted((Path(__file__).parents[2] / "examples/benchmarks/fixtures").glob("*.json"))
    assert len(paths) == 17
    count = 0
    for path in paths:
        fixture = BenchmarkFixture.model_validate_json(path.read_text())
        assert all(r.outcome in {"PASS", "NOT_CHECKED"} for r in run_fixture(fixture))
        assert not any(e.pending_stage == "S6" for e in fixture.expectations)
        for case in fixture.cases:
            count += 1
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
    assert count >= 9


def test_program_builder_seats_need_both_counts_and_keep_unknown_children():
    from datetime import UTC, datetime

    from house_ai.domain.brief import DesignBrief
    from house_ai.program.builder import build_program
    from tests.conftest import REPO

    brief = DesignBrief.model_validate(
        load_document(REPO / "examples/projects/synthetic-hillside/design_brief.yaml")
    )
    kwargs = dict(site=None, brief_ref=None, created_at=datetime(2026, 10, 18, tzinfo=UTC))
    assert build_program(brief, **kwargs).program.usability.household_seats == 4
    brief.facts = [f for f in brief.facts if f.key != "children"]
    assert build_program(brief, **kwargs).program.usability.household_seats is None


def test_kitchen_actual_run_length_and_appliance_access():
    doc = model(4, 4, "kitchen")
    doc["furniture"] = [furniture("counter", "kitchen-run", (2, 3.5), 2, 0.6)]
    result = FurnitureUsabilityEvaluator().evaluate(ctx(doc))
    assert metric(result, "kitchen_counter_run_m").value == 2
    assert "kitchen_counter_run_short" in {v.code for v in result.violations}
    doc["furniture"][0]["width_m"] = 3
    assert "kitchen_counter_run_short" not in {
        v.code for v in FurnitureUsabilityEvaluator().evaluate(ctx(doc)).violations
    }


def test_complex_stair_pitch_is_unknown_and_reversed_levels_are_flagged():
    doc = stair_model().model_dump(mode="json")
    doc["stairs"][0]["kind"] = "u_shaped"
    result = StairUsabilityEvaluator().evaluate(ctx(doc))
    assert metric(result, "stair_min_headroom_m").status == ClaimStatus.NOT_CHECKED
    assert RouteNetwork(ctx(doc).model).between("room", "upper-room") is None
    doc["stairs"][0]["kind"] = "straight"
    doc["levels"][1]["elevation_m"] = -3
    assert "stair_nonascending_levels" in {
        v.code for v in StairUsabilityEvaluator().evaluate(ctx(doc)).violations
    }


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
        program(double_bed_program_item_ids=["nonexistent"])
    with pytest.raises(ValidationError):
        program(vehicles=[vehicle, vehicle])


def test_committed_demo_is_grounded_and_has_three_integrity_checked_concepts():
    import json
    from pathlib import Path

    from house_ai.storage.hashing import content_hash

    root = Path(__file__).parents[2]
    report = json.loads((root / "examples/usability/demonstration/report.json").read_text())
    assert report["exploratory"] and not report["site_approved"] and not report["program_approved"]
    assert len(report["options"]) == 3
    assert all(r["defect_detected"] and r["clean_twin_passes"] for r in report["defects"])
    for row in report["options"]:
        house = HouseModel.model_validate(row["model"])
        assert content_hash(house) == row["model_hash"]
        assert row["integrity_clean"]
        assert {r["name"] for r in row["critics"]} == {e.name for e in USABILITY_EVALUATORS}
        assert all(set(v["subject_ids"]) <= set(house.all_ids()) for v in row["findings"])
        assert row["findings"]  # Real geometric integrity does not imply architectural usability.
