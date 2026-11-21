"""Seeded defects for Finding codes that had no seeded test, each with a clean twin.

Every case is a small hand-built synthetic model (``examples/usability/scenarios.py``)
where the defect is obvious by inspection. The bad twin must raise exactly that code,
citing exactly the right element IDs; the clean twin differs by one change and must not
raise it, on a checked value rather than a missing one. Where a code cannot be decided
without data, the test asserts the critic says so (``not_checked`` or ``not_run`` with
its reason) instead of passing.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from examples.usability.scenarios import corridor_model, door, flat_site, model, space, wall
from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.integrity import check_model
from house_ai.domain.model import HouseModel
from house_ai.domain.program import SpaceProgram
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.evaluators import (
    CirculationEvaluator,
    PrivacyEvaluator,
    ProgramEvaluator,
    SiteEvaluator,
)
from house_ai.evaluation.usability import (
    FurnitureUsabilityEvaluator,
    PrivacyUsabilityEvaluator,
    RouteUsabilityEvaluator,
)
from house_ai.storage.hashing import load_document

BUNGALOW_PROGRAM = (
    Path(__file__).parents[1] / "examples/projects/synthetic-bungalow/space_program.yaml"
)


def ctx(doc, site=None, program=None) -> EvaluationContext:
    house = doc if isinstance(doc, HouseModel) else HouseModel.model_validate(doc)
    return EvaluationContext(house, site, program, None)


def findings(result, code: str) -> list[list[str]]:
    """The subject IDs of every Finding with ``code``, in report order."""
    return [v.subject_ids for v in result.violations if v.code == code]


def metric(result, name: str):
    (m,) = [m for m in result.metrics if m.metric == name]
    return m


def program(**usability) -> SpaceProgram:
    doc = load_document(BUNGALOW_PROGRAM)
    if usability:
        doc["usability"] = usability
    return SpaceProgram.model_validate(doc)


def assert_valid(doc) -> None:
    """The defect is architectural, not geometric: the model itself is integrity-clean."""
    assert check_model(HouseModel.model_validate(doc)) == []


# ------------------------------------------------------------- PrivacyEvaluator


def _entry_hall_bedroom(hall_function: str) -> dict:
    """Entry 0..4, hall 4..6, bedroom 6..10 (x), 4 m deep; doors entry-hall, hall-bedroom."""
    doc = model(10, 4, "entry", doors=True)
    doc["spaces"] = [
        space("room", "entry", (0, 0, 4, 4)),
        space("hall", hall_function, (4, 0, 6, 4)),
        space("bed", "bedroom", (6, 0, 10, 4)),
    ]
    doc["walls"] += [wall("p1", (4, 0), (4, 4)), wall("p2", (6, 0), (6, 4))]
    doc["openings"] += [
        door("d-hall", "p1", 1, connects=("room", "hall")),
        door("d-bed", "p2", 1, connects=("hall", "bed")),
    ]
    return doc


def test_bedroom_opens_on_entrance_and_clean_twin_behind_a_hall():
    # The one change: the room between the entry and the bedroom is a second entry.
    bad, clean = _entry_hall_bedroom("entry"), _entry_hall_bedroom("hall")
    assert_valid(bad)
    bad_result = PrivacyEvaluator().evaluate(ctx(bad))
    assert findings(bad_result, "bedroom_opens_on_entrance") == [["bed"]]
    assert metric(bad_result, "bedroom_doors_on_entrance").value == 1
    clean_result = PrivacyEvaluator().evaluate(ctx(clean))
    assert findings(clean_result, "bedroom_opens_on_entrance") == []
    on_entry = metric(clean_result, "bedroom_doors_on_entrance")
    assert (on_entry.value, on_entry.status) == (0, ClaimStatus.MEASURED)


# ---------------------------------------------------------- CirculationEvaluator


def _shared_behind_private(clean: bool) -> dict:
    """Entry (0..4, 0..4) and a bedroom (4..8, 0..4) below a living room (0..8, 4..8).

    The bad twin reaches the living room only through the bedroom; the clean twin has
    the living-room door on the entry instead.
    """
    doc = model(8, 8, "entry", doors=True)
    doc["spaces"] = [
        space("room", "entry", (0, 0, 4, 4)),
        space("private", "bedroom", (4, 0, 8, 4)),
        space("shared", "living", (0, 4, 8, 8)),
    ]
    doc["walls"] += [
        wall("p-rp", (4, 0), (4, 4)),
        wall("p-top-w", (0, 4), (4, 4)),
        wall("p-top-e", (4, 4), (8, 4)),
    ]
    doc["zones"] = [
        dict(id="day", name="Day", privacy="public", space_ids=["room", "shared"]),
        dict(id="night", name="Night", privacy="private", space_ids=["private"]),
    ]
    for s in doc["spaces"]:
        s["zone_id"] = "night" if s["id"] == "private" else "day"
    doc["openings"].append(door("d-rp", "p-rp", 1, connects=("room", "private")))
    if clean:
        doc["openings"].append(door("d-rs", "p-top-w", 1, connects=("room", "shared")))
    else:
        doc["openings"].append(door("d-ps", "p-top-e", 1, connects=("private", "shared")))
    return doc


def test_private_space_crossed_and_clean_twin_with_a_direct_door():
    bad = _shared_behind_private(clean=False)
    assert_valid(bad)
    result = CirculationEvaluator().evaluate(ctx(bad))
    # The Finding cites the shared room whose route crosses the bedroom.
    assert findings(result, "private_space_crossed") == [["shared"]]
    crossings = metric(result, "guest_private_crossings")
    assert (crossings.value, crossings.subject_ids) == (1, ["shared"])
    clean = CirculationEvaluator().evaluate(ctx(_shared_behind_private(clean=True)))
    assert findings(clean, "private_space_crossed") == []
    crossings = metric(clean, "guest_private_crossings")
    assert (crossings.value, crossings.status) == (0, ClaimStatus.MEASURED)


@pytest.mark.xfail(
    strict=True,
    reason="product gap: with no Zones every room's privacy is unknown, yet "
    "guest_private_crossings is reported as a measured 0 instead of not_checked",
)
def test_private_crossing_without_zones_is_not_checked():
    doc = _shared_behind_private(clean=False)
    doc.pop("zones")
    for s in doc["spaces"]:
        s.pop("zone_id")
    result = CirculationEvaluator().evaluate(ctx(doc))
    assert metric(result, "guest_private_crossings").status is ClaimStatus.NOT_CHECKED


# -------------------------------------------------------------- ProgramEvaluator


def _living_with_window(host: str | None) -> dict:
    """A 5 x 6 m living room placed for ``pi-living`` (daylight: required)."""
    doc = model(5, 6, "living", doors=True)
    doc["spaces"][0]["program_item_id"] = "pi-living"
    if host == "retaining":
        doc["walls"][2]["kind"] = "retaining"  # the north wall holds back earth
    if host is not None:
        doc["openings"].append(
            dict(id="win", kind="window", host_wall_id="north", offset_m=1, width_m=2,
                 height_m=1.5, sill_m=0.9, connects=("room", "exterior"))
        )  # fmt: skip
    return doc


@pytest.mark.parametrize("host", [None, "retaining"], ids=["no-window", "window-in-retaining"])
def test_required_daylight_without_exterior_window(host):
    """A window in a retaining wall is not an exterior window: earth is behind it."""
    result = ProgramEvaluator().evaluate(ctx(_living_with_window(host), program=program()))
    assert findings(result, "required_daylight_no_exterior_window") == [["room", "pi-living"]]
    count = metric(result, "required_daylight_exterior_windows")
    assert (count.value, count.subject_ids) == (0, ["room", "pi-living"])


def test_required_daylight_clean_twin_and_missing_program():
    doc = _living_with_window("exterior")
    assert_valid(doc)
    result = ProgramEvaluator().evaluate(ctx(doc, program=program()))
    assert findings(result, "required_daylight_no_exterior_window") == []
    count = metric(result, "required_daylight_exterior_windows")
    assert (count.value, count.status) == (1, ClaimStatus.MEASURED)
    # Without a program nothing says the room needs daylight: the critic does not run.
    run = ProgramEvaluator().evaluate(ctx(_living_with_window(None))).run
    assert (run.status.value, run.reason) == ("not_run", "no program")


# ------------------------------------------------------- RouteUsabilityEvaluator


def test_long_dead_end_cites_only_the_corridor():
    # One portal at the south end; 10 m corridor ~8.7 m return, 4 m corridor ~3.1 m (limit 6).
    bad = RouteUsabilityEvaluator().evaluate(ctx(corridor_model(10)))
    assert findings(bad, "long_dead_end") == [["corridor"]]
    clean = RouteUsabilityEvaluator().evaluate(ctx(corridor_model(4)))
    assert findings(clean, "long_dead_end") == []
    assert metric(clean, "dead_end_length_m").status is ClaimStatus.MEASURED


def test_excess_circulation_cites_level_and_corridors_and_clean_twin():
    # A level that is only a 2 x 10 m corridor: circulation share 1.0 > 0.25.
    alone = RouteUsabilityEvaluator().evaluate(ctx(model(2, 10, "corridor", doors=True)))
    assert findings(alone, "excess_circulation") == [["ground", "room"]]
    assert metric(alone, "level_circulation_ratio").value == 1
    # The same corridor serving a 10 x 8 m living room. Net floors (0.15 m walls):
    # corridor 1.85 x 9.85 + door recess 0.9 x 0.075 = 18.29 m²; living 9.85 x 7.85 +
    # two recesses = 77.4575 m²; 18.29 / 95.7475 = 0.191 <= 0.25.
    served = RouteUsabilityEvaluator().evaluate(ctx(corridor_model(10)))
    assert findings(served, "excess_circulation") == []
    ratio = metric(served, "level_circulation_ratio")
    assert ratio.status is ClaimStatus.MEASURED
    assert ratio.value == pytest.approx(18.29 / 95.7475, abs=1e-3)


# ----------------------------------------------------- PrivacyUsabilityEvaluator


def test_bedroom_noise_adjacency_and_clean_gap():
    doc = model(4, 4)  # bedroom "room" 0..4
    doc["spaces"].append(space("noisy", "laundry", (4, 0, 7, 4)))
    result = PrivacyUsabilityEvaluator().evaluate(ctx(doc))
    assert findings(result, "bedroom_noise_adjacency") == [["room", "noisy"]]
    # 1 m apart: no shared boundary, no Finding of any kind.
    doc["spaces"][-1]["boundary"] = {"outer": [(5, 0), (8, 0), (8, 4), (5, 4)]}
    assert PrivacyUsabilityEvaluator().evaluate(ctx(doc)).violations == []


def test_bathroom_entrance_visible_and_screen_clean_twin():
    doc = model(4, 4, "entry", doors=True)
    doc["spaces"].append(space("bath", "bathroom", (4, 0, 7, 4)))
    doc["openings"].append(door("bath-door", "east", 1.5, connects=("room", "bath")))
    result = PrivacyUsabilityEvaluator().evaluate(ctx(doc))
    assert findings(result, "bathroom_entrance_visible") == [["bath-door", "room", "bath"]]
    # A screen wall across the entry blocks the ray from the entry's point to the door.
    doc["walls"].append(wall("screen", (3, 0.1), (3, 3.9)))
    screened = PrivacyUsabilityEvaluator().evaluate(ctx(doc))
    assert findings(screened, "bathroom_entrance_visible") == []


# --------------------------------------------------- FurnitureUsabilityEvaluator


def _garage_beside_hall(width: float) -> dict:
    """Garage ``width`` x 6.2 m with its house door on the east wall into a hall."""
    doc = model(width, 6.2, "garage")
    doc["spaces"].append(space("hall", "hall", (width, 0, width + 2, 6.2)))
    doc["walls"] = [w for w in doc["walls"] if w["id"] != "east"] + [
        wall("east", (width, 0), (width, 6.2))
    ]
    doc["openings"] = [door("house-door", "east", 2, connects=("room", "hall"))]
    return doc


def test_garage_pedestrian_route_through_the_evaluator():
    """End to end the blocked case cannot occur: every sampled body sits strictly inside
    its clear envelope (door-side clearance > 0, front 0.9 m, back 0.3 m) and no body may
    enter another's envelope, so bodies are disjoint holes in a connected floor and a
    point path always reaches the house door. ``garage_pedestrian_route_blocked`` is only
    seeded through the helper (tests/benchmarks/test_usability.py)."""
    car = dict(id="car", width_m=1.8, length_m=4.5, door_side_clearance_m=0.05, source="synthetic")
    # Tightest pack: two cars 0.05 m apart in a 3.85 m net width (1.8 + 0.05 + 1.8 + 0.1).
    two = program(vehicles=[car, {**car, "id": "car-2"}])
    result = FurnitureUsabilityEvaluator().evaluate(ctx(_garage_beside_hall(4.0), program=two))
    assert metric(result, "garage_sampled_fit").value is True
    route = metric(result, "garage_pedestrian_route")
    assert (route.value, route.status, route.subject_ids) == (True, ClaimStatus.INFERRED, ["room"])
    assert findings(result, "garage_pedestrian_route_blocked") == []
    # No house door: nothing to reach, so the route is not checked rather than passed.
    no_door = _garage_beside_hall(4.0)
    no_door["openings"] = []
    route = metric(FurnitureUsabilityEvaluator().evaluate(ctx(no_door, program=two)),
                   "garage_pedestrian_route")  # fmt: skip
    assert (route.value, route.status) == (None, ClaimStatus.NOT_CHECKED)
    # No vehicles declared: the garage study itself is not checked, with its reason.
    fit = metric(FurnitureUsabilityEvaluator().evaluate(ctx(_garage_beside_hall(4.0))),
                 "garage_sampled_fit")  # fmt: skip
    assert (fit.status, fit.method) == (ClaimStatus.NOT_CHECKED, "vehicle_count_or_size_unknown")


# ----------------------------------------------------------------- SiteEvaluator


def _site_with_ground(slope: float, rise: float = 0.0):
    """The flat analytical site tilted to the plane z = rise + slope * y (exact on its TIN)."""
    site = flat_site()
    site.terrain.surface.vertices = [
        (x, y, rise + slope * y) for x, y, _ in site.terrain.surface.vertices
    ]
    return site


def test_buried_habitable_face_names_each_uphill_wall():
    # Ground z = 0.25 y over a 4 x 4 m living room on z = 0: the north wall retains
    # 1.0 m, the east and west walls up to 1.0 m at their north ends (> 0.6 m trigger),
    # the south wall 0 m.
    house = model(4, 4, "living", doors=True)
    result = SiteEvaluator().evaluate(ctx(house, _site_with_ground(0.25)))
    assert findings(result, "buried_habitable_face") == [
        ["east", "room"],
        ["north", "room"],
        ["west", "room"],
    ]


def test_buried_habitable_face_clean_twins():
    house = model(4, 4, "living", doors=True)
    # Ground z = 0.1 y retains at most 0.4 m, under the 0.6 m trigger.
    gentle = SiteEvaluator().evaluate(ctx(house, _site_with_ground(0.1)))
    assert findings(gentle, "buried_habitable_face") == []
    # Ground 2 m above the floor buries every wall, but a store is not habitable.
    store = model(4, 4, "storage", doors=True)
    raised = SiteEvaluator().evaluate(ctx(store, _site_with_ground(0, rise=2)))
    assert findings(raised, "buried_habitable_face") == []
    assert len(findings(raised, "needs_professional_retaining")) == 4
    # The same 2 m rise around the living room buries all four faces.
    living = SiteEvaluator().evaluate(ctx(house, _site_with_ground(0, rise=2)))
    assert sorted(findings(living, "buried_habitable_face")) == [
        ["east", "room"],
        ["north", "room"],
        ["south", "room"],
        ["west", "room"],
    ]


def test_buried_face_without_terrain_is_reported_unknown_not_clean():
    house = model(4, 4, "living", doors=True)
    run = SiteEvaluator().evaluate(ctx(house)).run
    assert (run.status.value, run.reason) == ("not_run", "no site")
    # A site in another frame gives no usable terrain: the faces are unknown, and said so.
    site = _site_with_ground(0, rise=2)
    site.coordinates.local.id = "other"
    result = SiteEvaluator().evaluate(ctx(house, site))
    assert findings(result, "buried_habitable_face") == []
    assert len(findings(result, "terrain_coverage_incomplete")) == 1
    assert metric(result, "terrain_coverage_pct").value == 0
    assert metric(result, "retaining_wall_length_m").status is ClaimStatus.NOT_CHECKED


def test_twins_differ_only_by_the_seeded_change():
    """Guard against a clean twin that is clean for an unrelated reason."""
    a, b = _entry_hall_bedroom("entry"), _entry_hall_bedroom("hall")
    b2 = copy.deepcopy(b)
    b2["spaces"][1]["function"] = "entry"
    assert a == b2
    bad, clean = _shared_behind_private(False), _shared_behind_private(True)
    assert bad["openings"][:-1] == clean["openings"][:-1]
    assert bad["spaces"] == clean["spaces"] and bad["walls"] == clean["walls"]
