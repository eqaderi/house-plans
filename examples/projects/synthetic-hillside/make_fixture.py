"""Write the SYNTHETIC steep hillside example: site, design brief and space program.

Everything here is invented so Milestone D can be developed and tested on a
steep site without private survey data. The parcel is rotated 12 degrees
against the local axes (to exercise non-axis-aligned frontage), sits below a
road on its south-west edge and falls away from the road by roughly 36 %.
The space program is produced by the real Milestone C builder from the brief.

    .venv/bin/python examples/projects/synthetic-hillside/make_fixture.py [--check]
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import yaml

from house_ai.domain.brief import DesignBrief
from house_ai.domain.interview import slot_fact_id
from house_ai.domain.provenance import ArtifactKind, ArtifactRef
from house_ai.domain.site import Site
from house_ai.orchestration.site_context import site_context_for
from house_ai.program.builder import build_program
from house_ai.storage.hashing import content_hash

HERE = Path(__file__).resolve().parent
PROJECT = "synthetic-hillside"
ROTATION_DEG = 12.0
CREATED = "2026-10-17T10:00:00Z"
AUTHOR = {"kind": "human", "id": "example-author"}

#: Parcel and envelope in plot coordinates (p along the road, q into the plot), metres.
PARCEL = [(0.0, 0.0), (24.0, 0.0), (25.0, 30.0), (-1.0, 29.0)]
ENVELOPE = [(2.0, 3.0), (22.0, 3.0), (22.0, 27.0), (2.0, 27.0)]
ROAD = [(-6.0, -8.0), (30.0, -8.0), (30.0, 0.0), (-6.0, 0.0)]


def to_local(p: float, q: float) -> list[float]:
    r = math.radians(ROTATION_DEG)
    return [
        round(p * math.cos(r) - q * math.sin(r), 3),
        round(p * math.sin(r) + q * math.cos(r), 3),
    ]


def ground(p: float, q: float) -> float:
    """Invented terrain: falls about 0.36 m per metre away from the road, with a gentle roll."""
    return round(12.0 - 0.36 * q + 0.04 * p + 0.35 * math.sin(q / 5.0), 2)


def site_doc() -> dict:
    spots = []
    for q in (-2.0, 0.0, 6.0, 12.0, 18.0, 24.0, 30.0):
        for p in (-1.0, 6.0, 12.0, 18.0, 25.0):
            spots.append(
                {
                    "id": f"spot-p{int(p + 1):02d}-q{int(q + 2):02d}",
                    "xy": to_local(p, q),
                    "z_m": ground(p, q),
                }
            )
    return {
        "schema_version": "0.1.0",
        "id": "site",
        "project_id": PROJECT,
        "name": "Synthetic steep hillside below a road",
        "classification": "synthetic",
        "coordinates": {
            "source_units": {"unit": "m", "status": "user_confirmed"},
            "elevation_units": {"unit": "m", "status": "user_confirmed"},
            "horizontal_crs": {
                "status": "user_confirmed",
                "epsg": 32633,
                "name": "WGS 84 / UTM zone 33N (synthetic coordinates)",
            },
            "vertical_datum": {
                "status": "local_only_confirmed",
                "name": "synthetic benchmark BM-H (elevation 500.00)",
            },
            "local": {
                "id": "lcs-site",
                "name": "Plot frame, origin at the west road corner",
                "origin": [610000.0, 4200000.0, 500.0],
                "rotation_deg": 0.0,
            },
        },
        "boundary": {"outer": [to_local(p, q) for p, q in PARCEL]},
        "boundary_status": "verified_fact",
        "buildable_envelope": {
            "polygon": {"outer": [to_local(p, q) for p, q in ENVELOPE]},
            "status": "assumption",
            "basis": "synthetic setbacks (3 m road side, 2 m sides, 3 m rear) invented for the "
            "example; not a zoning rule",
            "max_height_m": 10.0,
        },
        "terrain": {"status": "surveyed_points", "spot_elevations": spots},
        "features": [
            {
                "id": "road-uphill",
                "kind": "road",
                "name": "Synthetic hillside road",
                "geometry": {
                    "type": "polygon",
                    "polygon": {"outer": [to_local(p, q) for p, q in ROAD]},
                },
            },
            {
                "id": "access-road",
                "kind": "access_point",
                "geometry": {"type": "point", "xy": to_local(12.0, 0.0)},
            },
        ],
        "provenance": {
            "created_at": CREATED,
            "created_by": AUTHOR,
            "method": "hand_authored",
            "notes": "Synthetic fixture for Milestone D; not a real survey.",
        },
    }


#: (slot, value) pairs the synthetic household "said"; recorded as owner answers.
ANSWERS: list[tuple[str, str, object]] = [
    ("household", "adults", 2),
    ("household", "children", 2),
    ("bedrooms_bathrooms", "children_own_rooms", True),
    ("bedrooms_bathrooms", "bedrooms", 3),
    ("bedrooms_bathrooms", "bathrooms", 2),
    ("bedrooms_bathrooms", "ensuite", True),
    ("privacy", "bedrooms_separate", True),
    ("kitchen_type", "open_plan", True),
    ("vehicles", "cars", 2),
    ("vehicles", "parking_type", "garage"),
    ("site_response", "entry_at_road", True),
    ("levels", "storeys", 2),
    ("laundry", "laundry_room", True),
    ("work_study", "workspaces", 1),
    ("work_study", "office_quiet", True),
    ("outdoor_living", "outdoor", ["terrace"]),
    ("site_response", "slope_strategy", "step down the slope"),
    ("budget", "budget", "not decided"),
    ("target_area", "target_area", "about 190 m²"),
]


def brief_doc() -> dict:
    facts = [
        {
            "id": slot_fact_id(key),
            "topic": topic,
            "key": key,
            "statement": f"Synthetic household answer for {key.replace('_', ' ')}.",
            "value": value
            if not isinstance(value, str) or key in ("parking_type", "slope_strategy")
            else None,
            "status": "preference",
            "source": {"kind": "owner_answer", "ref": f"q-{key}"},
        }
        for topic, key, value in ANSWERS
    ]
    return {
        "schema_version": "0.1.0",
        "id": "brief",
        "project_id": PROJECT,
        "household": [
            {"id": "hh-adult-1", "role": "adult", "label": "Adult 1"},
            {"id": "hh-adult-2", "role": "adult", "label": "Adult 2"},
            {"id": "hh-child-1", "role": "child", "label": "Child 1"},
            {"id": "hh-child-2", "role": "child", "label": "Child 2"},
        ],
        "facts": facts,
        "interview_rounds_completed": 5,
        "provenance": {
            "created_at": CREATED,
            "created_by": AUTHOR,
            "method": "hand_authored",
            "notes": "Synthetic brief standing in for a finished owner interview.",
        },
    }


def documents() -> dict[str, str]:
    site = Site.model_validate(site_doc())
    brief = DesignBrief.model_validate(brief_doc())
    site_ref = ArtifactRef(kind=ArtifactKind.SITE, id="site", version=1, sha256=content_hash(site))
    brief_ref = ArtifactRef(
        kind=ArtifactKind.DESIGN_BRIEF, id="brief", version=1, sha256=content_hash(brief)
    )
    result = build_program(
        brief,
        site=site_context_for(site, site_ref, None),
        brief_ref=brief_ref,
        created_at=brief.provenance.created_at,
    )
    header = "# SYNTHETIC example generated by make_fixture.py; do not edit by hand.\n"

    def dump(model) -> str:
        return header + yaml.safe_dump(
            model.model_dump(mode="json"), sort_keys=False, allow_unicode=True, width=100
        )

    return {
        "site.yaml": dump(site),
        "design_brief.yaml": dump(brief),
        "space_program.yaml": dump(result.program),
        "assumptions.yaml": dump(result.assumptions),
        "open_questions.yaml": dump(result.open_questions),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a file is stale")
    args = parser.parse_args(argv)
    stale = []
    for name, text in documents().items():
        path = HERE / name
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path}")
    if stale:
        print(f"stale: {', '.join(stale)}; run {Path(__file__).name}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
