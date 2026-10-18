"""Hand-authored geometry with deliberately simple, independently checkable twins."""

from __future__ import annotations

import copy

from house_ai.domain.model import HouseModel
from house_ai.domain.program import SpaceProgram
from house_ai.domain.site import Site
from house_ai.storage.hashing import load_document


def rectangle(x0, y0, x1, y1):
    return {"outer": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]}


def space(ident="room", function="bedroom", bounds=(0, 0, 4, 6), level="ground"):
    return dict(
        id=ident, name=ident, function=function, boundary=rectangle(*bounds), level_id=level
    )


def wall(ident, start, end, *, level="ground", kind="interior", thickness=0.15):
    return dict(
        id=ident,
        level_id=level,
        start=start,
        end=end,
        thickness_m=thickness,
        height_m=2.8,
        kind=kind,
    )


def door(ident="front-door", host="south", offset=1, connects=("exterior", "room"), **kw):
    return dict(
        id=ident,
        kind="door",
        host_wall_id=host,
        offset_m=offset,
        width_m=0.9,
        height_m=2.1,
        connects=connects,
        **kw,
    )


def model(width=4, depth=6, function="bedroom", *, doors=False):
    return dict(
        id="analytical",
        name="Synthetic analytical twin",
        coordinate_system_id="local",
        levels=[dict(id="ground", name="Ground", elevation_m=0, floor_to_floor_m=3)],
        spaces=[space(function=function, bounds=(0, 0, width, depth))],
        walls=[
            wall("south", (0, 0), (width, 0), kind="exterior"),
            wall("east", (width, 0), (width, depth), kind="exterior"),
            wall("north", (width, depth), (0, depth), kind="exterior"),
            wall("west", (0, depth), (0, 0), kind="exterior"),
        ],
        openings=[door(operation="swing_left", opens_into="room")] if doors else [],
    )


def furniture(ident, template="bed-double", position=(2, 3), width=1.6, depth=2, **kw):
    return dict(
        id=ident,
        space_id="room",
        template_id=template,
        position=position,
        width_m=width,
        depth_m=depth,
        **kw,
    )


def stair_model(*, defect=None):
    doc = model(5, 8, "stair")
    doc["levels"].append(dict(id="upper", name="Upper", elevation_m=3))
    doc["spaces"].append(space("upper-room", "stair", (0, 0, 5, 8), "upper"))
    doc["stairs"] = [
        dict(
            id="stair",
            kind="straight",
            from_level_id="ground",
            to_level_id="upper",
            bottom_space_id="room",
            top_space_id="upper-room",
            footprint=rectangle(2, 1.5, 3, 5.7),
            width_m=1,
            riser_count=16,
            riser_height_m=0.1875,
            tread_depth_m=0.28,
            walking_line=[(2.5, 1.5), (2.5, 5.7)],
        )
    ]
    doc["slabs"] = [
        dict(
            id="upper-slab",
            level_id="upper",
            kind="floor",
            thickness_m=0.2,
            boundary={
                "outer": rectangle(0, 0, 5, 8)["outer"],
                "holes": [rectangle(1.9, 2.4, 3.1, 5.7)["outer"]],
            },
        )
    ]
    if defect == "headroom":
        doc["slabs"][0]["boundary"]["holes"] = []
    elif defect == "run":
        doc["stairs"][0]["walking_line"][-1] = (2.5, 4)
    elif defect == "arrival":
        doc["furniture"] = [
            dict(
                id="arrival-block",
                space_id="upper-room",
                template_id="desk",
                position=(2.5, 6.3),
                width_m=1.2,
                depth_m=0.6,
            )
        ]
    elif defect == "height":
        doc["stairs"][0]["riser_height_m"] = 0.2
    return HouseModel.model_validate(doc)


def double_bed_program():
    """Synthetic bungalow program with its parents' bedroom designated for a double bed."""
    from pathlib import Path

    path = Path(__file__).parents[1] / "projects/synthetic-bungalow/space_program.yaml"
    doc = load_document(path)
    doc["usability"] = {"double_bed_program_item_ids": ["pi-bed-parents"]}
    return SpaceProgram.model_validate(doc)


def bedroom_model(width, depth):
    doc = model(width, depth)
    doc["spaces"][0]["program_item_id"] = "pi-bed-parents"
    return HouseModel.model_validate(doc)


def corridor_model(length):
    """Living room whose only door to a 2 m wide corridor is near the corridor's south end."""
    shared = min(8, length)
    walls = [
        wall("south", (0, 0), (10, 0), kind="exterior"),
        wall("north", (10, 8), (0, 8), kind="exterior"),
        wall("west", (0, 8), (0, 0), kind="exterior"),
        wall("shared", (10, 0), (10, shared)),
        wall("c-south", (10, 0), (12, 0), kind="exterior"),
        wall("c-east", (12, 0), (12, length), kind="exterior"),
        wall("c-north", (12, length), (10, length), kind="exterior"),
    ]
    if length < 8:
        walls.append(wall("east-upper", (10, length), (10, 8), kind="exterior"))
    if length > 8:
        walls.append(wall("c-west-upper", (10, 8), (10, length), kind="exterior"))
    return HouseModel.model_validate(
        dict(
            id="analytical",
            name="Synthetic analytical twin",
            coordinate_system_id="local",
            levels=[dict(id="ground", name="Ground", elevation_m=0, floor_to_floor_m=3)],
            spaces=[
                space("room", "living", (0, 0, 10, 8)),
                space("corridor", "corridor", (10, 0, 12, length)),
            ],
            walls=walls,
            openings=[
                door(operation="sliding"),
                door("hall-door", "shared", 1, ("room", "corridor"), operation="sliding"),
            ],
        )
    )


def seeded_pairs():
    """(case ID, critic, defect, clean twin, expected code, cited element, program or None)."""
    yield (
        "headroom",
        "StairUsabilityEvaluator",
        stair_model(defect="headroom"),
        stair_model(),
        "stair_low_headroom",
        "stair",
        None,
    )
    yield (
        "short-run",
        "StairUsabilityEvaluator",
        stair_model(defect="run"),
        stair_model(),
        "stair_run_does_not_fit",
        "stair",
        None,
    )
    yield (
        "arrival",
        "StairUsabilityEvaluator",
        stair_model(defect="arrival"),
        stair_model(),
        "stair_landing_blocked",
        "stair",
        None,
    )
    yield (
        "height",
        "StairUsabilityEvaluator",
        stair_model(defect="height"),
        stair_model(),
        "stair_height_mismatch",
        "stair",
        None,
    )
    clean = model(4, 6, doors=True)
    clean["furniture"] = [furniture("bed", position=(2.8, 3))]
    bad = copy.deepcopy(clean)
    bad["furniture"][0]["position"] = (1.4, 1.1)
    yield (
        "door-bed",
        "DoorClearanceEvaluator",
        HouseModel.model_validate(bad),
        HouseModel.model_validate(clean),
        "door_object_conflict",
        "bed",
        None,
    )
    clean = model(4, 6, function="bathroom")
    clean["fixtures"] = [
        dict(id="wc", space_id="room", fixture_type="wc", position=(2, 3), width_m=0.4, depth_m=0.7)
    ]
    bad = copy.deepcopy(clean)
    bad["fixtures"][0]["position"] = (2, 0.5)
    yield (
        "wc-front",
        "FurnitureUsabilityEvaluator",
        HouseModel.model_validate(bad),
        HouseModel.model_validate(clean),
        "object_clearance_blocked",
        "wc",
        None,
    )
    yield (
        "bed-width",
        "FurnitureUsabilityEvaluator",
        bedroom_model(2.6, 5),
        bedroom_model(3.4, 5),
        "bed_double_no_sampled_fit",
        "room",
        double_bed_program(),
    )
    # Both twins have one portal, so both dead ends are measured: about 8.6 m and 3.1 m.
    yield (
        "dead-end",
        "RouteUsabilityEvaluator",
        corridor_model(10),
        corridor_model(4),
        "long_dead_end",
        "corridor",
        None,
    )


def flat_site():
    """Invented local surface, deliberately larger than all analytical rooms."""
    from pathlib import Path

    doc = load_document(Path(__file__).parents[1] / "benchmarks/fixtures/flat-simple.json")["site"]
    doc["coordinates"]["local"]["id"] = "local"
    doc["terrain"] = dict(
        status="surface_built",
        surface=dict(
            vertices=[(-50, -50, 0), (50, -50, 0), (50, 50, 0), (-50, 50, 0)],
            triangles=[(0, 1, 2), (0, 2, 3)],
        ),
    )
    return Site.model_validate(doc)
