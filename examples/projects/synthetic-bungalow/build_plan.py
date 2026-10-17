"""Author the golden plan, plans/plan-a.json, for the synthetic bungalow.

The plan pins the content hashes of site.yaml and space_program.yaml. After
editing either, regenerate it:

    .venv/bin/python examples/projects/synthetic-bungalow/build_plan.py

and check it is current with ``--check`` (the test suite does this too).

Layout: a 12 x 10 m single-storey bar. Day rooms face the road (south),
bedrooms face north, a 1.5 m hall runs between them. Space polygons are
drawn to wall centerlines.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.site import Site
from house_ai.storage.hashing import content_hash, load_document, pretty_json

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "plans" / "plan-a.json"

EXTERIOR_WALL_M = 0.3
INTERIOR_WALL_M = 0.15
WALL_HEIGHT_M = 2.8


def rect(x0: float, y0: float, x1: float, y1: float) -> dict:
    return {"outer": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


def wall(ident: str, start: list, end: list, exterior: bool) -> dict:
    return {
        "id": ident,
        "level_id": "l0",
        "start": start,
        "end": end,
        "thickness_m": EXTERIOR_WALL_M if exterior else INTERIOR_WALL_M,
        "height_m": WALL_HEIGHT_M,
        "kind": "exterior" if exterior else "interior",
        "material_id": "m-render" if exterior else "m-plaster",
    }


def door(
    ident, host, offset, a, b, width=0.9, operation="swing_left", kind="door", opens_into=None
) -> dict:
    out = {
        "id": ident,
        "kind": kind,
        "host_wall_id": host,
        "offset_m": offset,
        "width_m": width,
        "height_m": 2.1,
        "sill_m": 0.0,
        "connects": [a, b],
        "operation": operation,
    }
    if opens_into is not None:
        out["opens_into"] = opens_into
    return out


def window(ident, host, offset, space, width, height=1.2, sill=0.9) -> dict:
    return {
        "id": ident,
        "kind": "window",
        "host_wall_id": host,
        "offset_m": offset,
        "width_m": width,
        "height_m": height,
        "sill_m": sill,
        "connects": [space, "exterior"],
        "operation": "tilt_turn",
        "material_id": "m-glass",
    }


SPACES = [
    # id, name, function, boundary, program item, zone
    ("sp-living", "Living", "living", rect(10, 12, 16, 17), "pi-living", "z-day"),
    ("sp-kitchen", "Kitchen and dining", "kitchen", rect(16, 12, 22, 17), "pi-kitchen", "z-day"),
    ("sp-hall", "Hall", "hall", rect(10, 17, 22, 18.5), "pi-hall", "z-circulation"),
    ("sp-bed-parents", "Parents' bedroom", "bedroom", rect(10, 18.5, 14, 22), "pi-bed-parents",
     "z-night"),
    ("sp-bath", "Bathroom", "bathroom", rect(14, 18.5, 17, 22), "pi-bath", "z-night"),
    ("sp-bed-children", "Children's bedroom", "bedroom", rect(17, 18.5, 22, 22),
     "pi-bed-children", "z-night"),
]


def build() -> PlanVersion:
    site = Site.model_validate(load_document(HERE / "site.yaml"))
    program = SpaceProgram.model_validate(load_document(HERE / "space_program.yaml"))
    site_ref = {"kind": "site", "id": "site", "version": 1, "sha256": content_hash(site)}
    program_ref = {
        "kind": "space_program", "id": "program", "version": 1, "sha256": content_hash(program),
    }
    model = {
        "id": "house-a",
        "name": "Synthetic bungalow, option A",
        "coordinate_system_id": "lcs-site",
        "site_ref": site_ref,
        "program_ref": program_ref,
        "levels": [{"id": "l0", "name": "Ground floor", "elevation_m": 0.6,
                    "floor_to_floor_m": 3.1}],
        "spaces": [
            {"id": i, "name": n, "function": f, "level_id": "l0", "boundary": b,
             "program_item_id": p, "zone_id": z, "floor_material_id": "m-oak"}
            for i, n, f, b, p, z in SPACES
        ],
        "walls": [
            wall("w-ext-s", [10, 12], [22, 12], exterior=True),
            wall("w-ext-e", [22, 12], [22, 22], exterior=True),
            wall("w-ext-n", [22, 22], [10, 22], exterior=True),
            wall("w-ext-w", [10, 22], [10, 12], exterior=True),
            wall("w-living-kitchen", [16, 12], [16, 17], exterior=False),
            wall("w-hall-s", [10, 17], [22, 17], exterior=False),
            wall("w-hall-n", [10, 18.5], [22, 18.5], exterior=False),
            wall("w-bed-bath", [14, 18.5], [14, 22], exterior=False),
            wall("w-bath-bed", [17, 18.5], [17, 22], exterior=False),
        ],
        "openings": [
            door("d-front", "w-ext-w", 3.8, "exterior", "sp-hall", width=1.0),
            door("d-hall-living", "w-hall-s", 2.0, "sp-hall", "sp-living"),
            door("d-hall-kitchen", "w-hall-s", 7.0, "sp-hall", "sp-kitchen"),
            door("d-hall-bed-parents", "w-hall-n", 1.5, "sp-hall", "sp-bed-parents"),
            door("d-hall-bath", "w-hall-n", 4.8, "sp-hall", "sp-bath", width=0.8),
            door("d-hall-bed-children", "w-hall-n", 8.5, "sp-hall", "sp-bed-children"),
            door("o-living-kitchen", "w-living-kitchen", 1.5, "sp-living", "sp-kitchen",
                 width=1.6, operation="none", kind="opening"),
            window("win-living-s", "w-ext-s", 2.0, "sp-living", 2.0, height=2.1, sill=0.0),
            window("win-living-w", "w-ext-w", 6.5, "sp-living", 1.5),
            window("win-kitchen-s", "w-ext-s", 8.0, "sp-kitchen", 1.5),
            window("win-kitchen-e", "w-ext-e", 1.5, "sp-kitchen", 1.2),
            window("win-bed-parents-n", "w-ext-n", 9.0, "sp-bed-parents", 1.5),
            window("win-bath-n", "w-ext-n", 5.4, "sp-bath", 0.6, height=0.6, sill=1.5),
            window("win-bed-children-n", "w-ext-n", 1.5, "sp-bed-children", 1.5),
        ],
        "slabs": [
            {"id": "slab-l0", "level_id": "l0", "kind": "floor", "boundary": rect(10, 12, 22, 22),
             "thickness_m": 0.25, "material_id": "m-concrete"},
            {"id": "slab-roof", "level_id": "l0", "kind": "roof",
             "boundary": rect(9.5, 11.5, 22.5, 22.5), "thickness_m": 0.3, "top_offset_m": 3.1,
             "material_id": "m-concrete"},
        ],
        "ceilings": [
            {"id": f"ceil-{ident[3:]}", "space_id": ident, "height_m": 2.7,
             "material_id": "m-plaster"}
            for ident, *_ in SPACES
        ],
        "stairs": [],
        "zones": [
            {"id": "z-day", "name": "Day zone", "privacy": "public",
             "space_ids": ["sp-living", "sp-kitchen"]},
            {"id": "z-night", "name": "Night zone", "privacy": "private",
             "space_ids": ["sp-bed-parents", "sp-bath", "sp-bed-children"]},
            {"id": "z-circulation", "name": "Circulation", "privacy": "semi_private",
             "space_ids": ["sp-hall"]},
        ],
        "fixtures": [
            {"id": "fx-wc", "space_id": "sp-bath", "fixture_type": "wc", "position": [14.6, 21.4],
             "rotation_deg": 180, "width_m": 0.4, "depth_m": 0.65},
            {"id": "fx-basin", "space_id": "sp-bath", "fixture_type": "basin",
             "position": [15.6, 21.6], "rotation_deg": 180, "width_m": 0.6, "depth_m": 0.45},
            {"id": "fx-shower", "space_id": "sp-bath", "fixture_type": "shower",
             "position": [16.4, 19.6], "width_m": 0.9, "depth_m": 0.9},
            {"id": "fx-kitchen-sink", "space_id": "sp-kitchen", "fixture_type": "kitchen_sink",
             "position": [21.4, 14.5], "rotation_deg": 90, "width_m": 0.8, "depth_m": 0.6},
            {"id": "fx-bed-parents", "space_id": "sp-bed-parents", "fixture_type": "bed_double",
             "position": [12.0, 20.7], "rotation_deg": 0, "width_m": 1.6, "depth_m": 2.0},
        ],
        "relationships": [
            {"id": "rel-living-kitchen", "a": "sp-living", "b": "sp-kitchen",
             "kind": "connected", "requirement_id": "adj-living-kitchen"},
        ],
        "materials": [
            {"id": "m-render", "name": "Exterior render, off-white", "category": "wall",
             "base_color_hex": "#EDE8DF"},
            {"id": "m-plaster", "name": "Interior plaster, white", "category": "wall",
             "base_color_hex": "#F4F4F2"},
            {"id": "m-oak", "name": "Oak floorboards", "category": "floor",
             "base_color_hex": "#B98E5A"},
            {"id": "m-concrete", "name": "Concrete", "category": "floor",
             "base_color_hex": "#9A9A96"},
            {"id": "m-glass", "name": "Clear double glazing", "category": "glazing"},
        ],
        "assumptions": [
            {"id": "as-plan-centerlines",
             "statement": "Room areas are measured to wall centerlines.",
             "basis": "Milestone A convention", "affects": ["sp-living", "sp-kitchen"]},
        ],
        "issues": [
            {"id": "iss-guest",
             "title": "No guest room; visiting grandparent sleeps in the living room",
             "severity": "warning", "subject_ids": ["sp-living"]},
        ],
    }
    return PlanVersion.model_validate(
        {
            "option_id": "plan-a",
            "label": "Option A: compact bar, bedrooms north",
            "strategy": "hand_authored",
            "provenance": {
                "created_at": "2026-10-17T09:30:00Z",
                "created_by": {"kind": "human", "id": "example-author"},
                "method": "hand_authored",
                "inputs": [site_ref, program_ref],
                "notes": "Golden synthetic plan for Milestone A tests; not generated by a solver.",
            },
            "model": model,
        }
    )


def render() -> str:
    return pretty_json(build())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if plan-a.json is stale")
    args = parser.parse_args(argv)
    text = render()
    if args.check:
        if OUTPUT.read_text(encoding="utf-8") != text:
            print(f"{OUTPUT} is stale; run {Path(__file__).name} to regenerate", file=sys.stderr)
            return 1
        print(f"{OUTPUT.name} is current")
        return 0
    OUTPUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
