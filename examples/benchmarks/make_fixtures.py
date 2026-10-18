"""Generate fictional, CRS-free benchmark inputs. No private project is read.

.venv/bin/python examples/benchmarks/make_fixtures.py [--check]
"""

from __future__ import annotations

import argparse
import copy
import math
from pathlib import Path

from house_ai.domain.benchmark import BenchmarkFixture
from house_ai.domain.integrity import check_model, errors
from house_ai.domain.model import HouseModel
from house_ai.domain.program import SpaceProgram
from house_ai.domain.site import Site
from house_ai.storage.hashing import content_hash, load_document

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUNGALOW = ROOT / "examples/projects/synthetic-bungalow"
GENERATOR = "examples/benchmarks/make_fixtures.py"
PROVENANCE = {
    "created_at": "2026-10-17T00:00:00Z",
    "created_by": {"kind": "agent", "id": "codex"},
    "method": "synthetic_benchmark_generation",
    "notes": "Fictional analytical inputs, not owner facts or approvals.",
}


def rect(x0, y0, x1, y1):
    return {"outer": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


def site_doc(name, width=20, depth=30, dx=0.0, dy=0.0, base=0.0):
    """Road is y=0, terrain z=base+dx*x+dy*y; no geographic north."""
    return {
        "id": "site",
        "project_id": f"benchmark-{name}",
        "name": name,
        "classification": "synthetic",
        "coordinates": {
            "source_units": {"unit": "m", "status": "declared_in_source"},
            "elevation_units": {"unit": "m", "status": "declared_in_source"},
            "horizontal_crs": {"status": "unknown"},
            "vertical_datum": {"status": "unknown"},
            "local": {
                "id": "lcs-site",
                "name": "Fictional Cartesian metres; north unknown",
                "origin": [0, 0, 0],
            },
        },
        "boundary": rect(0, 0, width, depth),
        "boundary_status": "assumption",
        "buildable_envelope": {
            "polygon": rect(2, 3, width - 2, depth - 3),
            "status": "assumption",
            "basis": "Invented benchmark offsets: 2 m sides, 3 m front/rear; not regulation",
        },
        "terrain": {
            "status": "surveyed_points",
            "spot_elevations": [
                {
                    "id": ident,
                    "xy": [x, y],
                    "z_m": base + dx * x + dy * y,
                    "source_ref": "analytical-plane",
                }
                for ident, x, y in (
                    ("spot-sw", 0, 0),
                    ("spot-se", width, 0),
                    ("spot-ne", width, depth),
                    ("spot-nw", 0, depth),
                )
            ],
        },
        "features": [
            {
                "id": "road",
                "kind": "road",
                "status": "assumption",
                "geometry": {"type": "polygon", "polygon": rect(-2, -6, width + 2, 0)},
            },
            {
                "id": "access",
                "kind": "access_point",
                "status": "assumption",
                "geometry": {"type": "point", "xy": [width / 2, 0]},
            },
        ],
        "provenance": copy.deepcopy(PROVENANCE),
    }


def program_doc(project_id):
    p = load_document(BUNGALOW / "space_program.yaml")
    p.update(project_id=project_id, provenance=copy.deepcopy(PROVENANCE), site_verified=False)
    for item in p["items"]:
        item.pop("source_fact_ids", None)
    for adj in p["adjacencies"]:
        adj.pop("source_fact_ids", None)
    return p


def metric(
    ident,
    category,
    name,
    value,
    *,
    source="site",
    target="site",
    subjects=(),
    status="measured",
    tolerance=1e-6,
    basis,
):
    return dict(
        id=ident,
        category=category,
        target=target,
        source=source,
        metric=name,
        value=value,
        subject_ids=list(subjects),
        status=status,
        tolerance=tolerance,
        basis=basis,
    )


def finding(ident, category, code, count, *, target, subjects=(), source="integrity", basis):
    return dict(
        id=ident,
        category=category,
        target=target,
        source=source,
        code=code,
        value=count,
        subject_ids=list(subjects),
        basis=basis,
    )


def future(ident, category, name, stage, *, target="site", basis):
    return dict(
        id=ident,
        category=category,
        target=target,
        source="future",
        metric=name,
        value=None,
        status="not_checked",
        pending_stage=stage,
        basis=basis,
    )


def fixture(name, site, ground_truth, *, program=None, cases=(), expectations=()):
    return dict(
        id=name,
        description=name.replace("-", " "),
        generator=GENERATOR,
        ground_truth=ground_truth,
        site=site,
        program=program or program_doc(site["project_id"]),
        cases=list(cases),
        expectations=list(expectations),
    )


def terrain_fixture(name, *, width=20, depth=30, dx=0, dy=0, base=0):
    site = site_doc(name, width, depth, dx, dy, base)
    area, relief = width * depth, abs(dx) * width + abs(dy) * depth
    # Ground truth comes from the plane equation, not a triangulation or report.
    slope = 100 * (dx * dx + dy * dy) ** 0.5
    return fixture(
        name,
        site,
        f"Rectangle {width} x {depth} m; z={base}+{dx}x+{dy}y. "
        f"Analytical area={area}; relief={relief}; gradient magnitude={slope}%.",
        expectations=[
            metric("parcel-area", "metric_accuracy", "parcel_area_m2", area, basis="width*depth"),
            metric(
                "envelope-area",
                "geometric_feasibility",
                "envelope_area_m2",
                (width - 4) * (depth - 6),
                basis="(width-4)*(depth-6)",
            ),
            metric(
                "envelope-contained",
                "geometric_feasibility",
                "envelope_inside_parcel",
                True,
                basis="rectangle inset by positive offsets",
            ),
            metric(
                "relief",
                "terrain_compatibility",
                "survey_relief_m",
                relief,
                basis="abs(dx)*width+abs(dy)*depth, extrema at corners",
            ),
            metric(
                "slope",
                "terrain_compatibility",
                "parcel_mean_slope_pct",
                slope,
                basis="100*sqrt(dx^2+dy^2); every nondegenerate triangle lies on plane",
            ),
            metric(
                "tin-area",
                "metric_accuracy",
                "parcel_tin_area_m2",
                area,
                basis="four corner observations cover rectangle exactly",
            ),
        ],
    )


def model_doc(site, program):
    model = load_document(BUNGALOW / "plans/plan-a.json")["model"]
    for key, kind, doc in (
        ("site_ref", "site", Site.model_validate(site)),
        ("program_ref", "space_program", SpaceProgram.model_validate(program)),
    ):
        model[key] = dict(kind=kind, id=doc.id, version=1, sha256=content_hash(doc))
    model["issues"] = []  # The original subjective guest-room note is unrelated to these scenarios.
    return model


def stair_case(model, void_start_x):
    """Add an upper room over the living room, reached by a straight stair inside it.

    15 risers of round(3.1/15, 4) m and 0.28 m goings: a 3.92 m run along x at y=14.5,
    from x=11.1 (0.6 m) to x=15.02 (3.7 m). The upper slab (underside 3.5 m) has a void
    from `void_start_x` to the top, so the pitch-line headroom where the slab ends is
    2.9 - 3.1 * (void_start_x - 11.1) / 3.92 m.
    """
    model = copy.deepcopy(model)
    model["levels"].append(dict(id="l1", name="Upper floor", elevation_m=3.7))
    model["spaces"].append(
        dict(
            id="sp-upper",
            name="Upper room",
            function="family",
            level_id="l1",
            boundary=rect(10, 12, 16, 17),
        )
    )
    model["slabs"] = [sl for sl in model["slabs"] if sl["id"] != "slab-roof"] + [
        dict(
            id="slab-l1",
            level_id="l1",
            kind="floor",
            thickness_m=0.2,
            boundary={
                **rect(10, 12, 16, 17),
                "holes": [rect(void_start_x, 14, 15.02, 15)["outer"]],
            },
        )
    ]
    model["stairs"] = [
        dict(
            id="st-living",
            kind="straight",
            from_level_id="l0",
            to_level_id="l1",
            bottom_space_id="sp-living",
            top_space_id="sp-upper",
            footprint=rect(11.1, 14, 15.02, 15),
            width_m=1.0,
            riser_count=15,
            riser_height_m=round(3.1 / 15, 4),
            tread_depth_m=0.28,
            walking_line=[(11.1, 14.5), (15.02, 14.5)],
        )
    ]
    return model


def case(ident, model, *, defect=False, description=None):
    return dict(id=ident, description=description or ident, model=model, seeded_defect=defect)


def households():
    out = []
    # Existing human-authored synthetic geometry is reused, not newly invented room coordinates.
    site = site_doc("family-privacy", width=32, depth=34)
    program = program_doc(site["project_id"])
    program["adjacencies"].append(
        dict(
            id="adj-guest-family",
            a="pi-living",
            b="pi-bed-parents",
            kind="separated",
            strength="hard",
            rationale="Fictional family requires guest/family separation",
        )
    )
    clean = model_doc(site, program)
    defect = copy.deepcopy(clean)
    # Reclassify hall as entry to expose bedroom doors opening directly on the entrance.
    next(s for s in defect["spaces"] if s["id"] == "sp-hall")["function"] = "entry"
    out.append(
        fixture(
            "family-privacy",
            site,
            "Golden bungalow guest living area and parents room share no wall; "
            "seeded entry hall has two bedroom doors. No privacy score is asserted.",
            program=program,
            cases=[case("separated", clean), case("entry-bedroom-doors", defect, defect=True)],
            expectations=[
                metric(
                    "guest-separated",
                    "privacy",
                    "adjacency_satisfied",
                    True,
                    source="evaluation",
                    target="separated",
                    subjects=["adj-guest-family"],
                    basis="living and parents room separated by 1.5 m hall",
                ),
                metric(
                    "entry-exposure",
                    "privacy",
                    "bedroom_doors_on_entrance",
                    2,
                    source="evaluation",
                    target="entry-bedroom-doors",
                    basis="two existing bedroom doors connect to hall reclassified as entry",
                ),
                metric(
                    "guest-paths",
                    "privacy",
                    "guest_routes_crossing_private_count",
                    0,
                    source="evaluation",
                    target="separated",
                    basis="shortest measured route to living crosses hall, no private bedroom",
                ),
                metric(
                    "net-area-children",
                    "metric_accuracy",
                    "net_area_m2",
                    15.706,
                    source="evaluation",
                    target="separated",
                    subjects=["sp-bed-children"],
                    tolerance=1e-3,
                    basis="(21.85-17.075)*(21.85-18.575) between finish faces "
                    "+ 0.9*0.075 doorway recess = 15.7056",
                ),
                finding(
                    "kitchen-desire-line",
                    "circulation",
                    "kitchen_through_traffic",
                    1,
                    source="evaluation",
                    target="separated",
                    subjects=["sp-kitchen", "d-hall-kitchen", "o-living-kitchen"],
                    basis="hall door (17.45,17) to living opening (16,14.3) crosses the "
                    "kitchen floor inset 0.75 m",
                )
                | {"status": "inferred"},
                finding(
                    "bath-door-hidden",
                    "privacy",
                    "bathroom_entrance_visible",
                    0,
                    source="evaluation",
                    target="separated",
                    basis="hall is not an entrance/living space; no sightline source",
                ),
                finding(
                    "bath-door-visible",
                    "privacy",
                    "bathroom_entrance_visible",
                    1,
                    source="evaluation",
                    target="entry-bedroom-doors",
                    subjects=["d-hall-bath", "sp-hall", "sp-bath"],
                    basis="unobstructed ray inside the hall reclassified as entry",
                )
                | {"status": "inferred"},
                metric(
                    "front-door-step",
                    "terrain_compatibility",
                    "outdoor_door_grade_delta_m",
                    0.6,
                    source="evaluation",
                    target="separated",
                    subjects=["d-front"],
                    status="inferred",
                    basis="floor at 0.6 m on flat grade z=0",
                ),
                finding(
                    "front-door-step-flagged",
                    "terrain_compatibility",
                    "outdoor_door_grade_mismatch",
                    1,
                    source="evaluation",
                    target="separated",
                    subjects=["d-front"],
                    basis="0.6 m step exceeds the 0.2 m conceptual warning",
                )
                | {"status": "inferred"},
            ],
        )
    )
    site = site_doc("multigenerational", width=32, depth=34)
    program = program_doc(site["project_id"])
    for item in program["items"]:
        if item["id"] in ("pi-bed-parents", "pi-bath"):
            item.update(accessible=True, level_preference="entry")
    clean = model_doc(site, program)
    defect = copy.deepcopy(clean)
    defect["openings"] = [o for o in defect["openings"] if o["id"] != "d-hall-bath"]
    swings = {}
    for side in ("sp-bed-parents", "sp-hall"):
        swings[side] = copy.deepcopy(clean)
        door = next(o for o in swings[side]["openings"] if o["id"] == "d-hall-bed-parents")
        door["opens_into"] = side
    out.append(
        fixture(
            "multigenerational",
            site,
            "Older resident requires an entry-level bedroom and bathroom; remove bathroom door "
            "to seed an unreachable room. Widths, thresholds and turning space remain unmeasured.",
            program=program,
            cases=[
                case("step-free-graph", clean),
                case("bath-unreachable", defect, defect=True),
                case("door-into-bedroom", swings["sp-bed-parents"], defect=True),
                case("door-into-hall", swings["sp-hall"]),
                case("stair-clear", stair_case(clean, 12.0)),
                case("stair-low-headroom", stair_case(clean, 12.6), defect=True),
            ],
            expectations=[
                metric(
                    "bedroom-required-accessible",
                    "practical_usability",
                    "accessible",
                    True,
                    source="program",
                    target="program",
                    subjects=["pi-bed-parents"],
                    basis="declared fictional household requirement",
                ),
                finding(
                    "bath-disconnected",
                    "circulation",
                    "space_unreachable",
                    1,
                    target="bath-unreachable",
                    subjects=["sp-bath"],
                    basis="bathroom has no passable opening",
                ),
                finding(
                    "bath-access-fails",
                    "practical_usability",
                    "accessible_not_step_free",
                    1,
                    source="evaluation",
                    target="bath-unreachable",
                    subjects=["sp-bath"],
                    basis="graph-only step-free check has no path to bathroom",
                ),
                metric(
                    "turning-clearance",
                    "practical_usability",
                    "accessible_turning_space",
                    True,
                    source="evaluation",
                    target="step-free-graph",
                    subjects=["sp-bath"],
                    status="inferred",
                    basis="2.85 x 3.275 m net bathroom keeps a 1.5 m circle clear of its "
                    "wc, basin and shower",
                ),
                finding(
                    "bedroom-turning-missing",
                    "practical_usability",
                    "accessible_turning_space_missing",
                    1,
                    source="evaluation",
                    target="step-free-graph",
                    subjects=["sp-bed-parents"],
                    basis="1.6x2 m bed leaves 1.05-1.125 m strips; every 0.75 m radius centre "
                    "is within 0.75 m of a bed corner or wall",
                )
                | {"status": "inferred"},
                finding(
                    "door-hits-bed-access",
                    "practical_usability",
                    "door_object_conflict",
                    1,
                    source="evaluation",
                    target="door-into-bedroom",
                    subjects=["d-hall-bed-parents", "fx-bed-parents"],
                    basis="0.9 m sweep to y=19.4 enters the bed's 0.75 m foot zone from y=18.95",
                )
                | {"status": "inferred"},
                metric(
                    "door-sweep-area",
                    "metric_accuracy",
                    "door_swing_area_m2",
                    math.pi * 0.9**2 / 4,
                    source="evaluation",
                    target="door-into-hall",
                    subjects=["d-hall-bed-parents"],
                    tolerance=1e-3,
                    basis="quarter circle of the 0.9 m leaf",
                ),
                finding(
                    "door-into-hall-clear",
                    "practical_usability",
                    "door_object_conflict",
                    0,
                    source="evaluation",
                    target="door-into-hall",
                    basis="sweep stays in the empty hall",
                ),
                metric(
                    "stair-headroom-clear",
                    "geometric_feasibility",
                    "stair_min_headroom_m",
                    2.9 - 3.1 * 0.9 / 3.92,
                    source="evaluation",
                    target="stair-clear",
                    subjects=["st-living"],
                    tolerance=1e-3,
                    basis="2.9 - 3.1*(12.0-11.1)/3.92 = 2.188 m at the void edge",
                ),
                finding(
                    "stair-headroom-low",
                    "geometric_feasibility",
                    "stair_low_headroom",
                    1,
                    source="evaluation",
                    target="stair-low-headroom",
                    subjects=["st-living", "slab-l1"],
                    basis="2.9 - 3.1*(12.6-11.1)/3.92 = 1.714 m, below the 2 m assumption",
                )
                | {"status": "inferred"},
                metric(
                    "stair-run-fits",
                    "geometric_feasibility",
                    "stair_run_fit",
                    True,
                    source="evaluation",
                    target="stair-clear",
                    subjects=["st-living"],
                    basis="(15-1)*0.28 = 3.92 m walking line inside a 1 m wide footprint",
                ),
                finding(
                    "stair-rounding-consistent",
                    "geometric_feasibility",
                    "stair_height_mismatch",
                    0,
                    source="evaluation",
                    target="stair-clear",
                    basis="15*0.2067 = 3.1005 m; within half a 4 dp unit per riser",
                ),
            ],
        )
    )
    site = site_doc("heavy-cooking", width=32, depth=34)
    program = program_doc(site["project_id"])
    program["items"].extend(
        [
            dict(
                id="pi-garage",
                name="Two parking bays",
                function="garage",
                quantity=2,
                target_area_m2=18,
                privacy="service",
                level_preference="entry",
            ),
            dict(
                id="pi-heavy-kitchen",
                name="Separate heavy-cooking kitchen",
                function="kitchen",
                target_area_m2=14,
                privacy="service",
            ),
        ]
    )
    program["adjacencies"].extend(
        [
            dict(
                id="adj-heavy-separated",
                a="pi-heavy-kitchen",
                b="pi-living",
                kind="separated",
                strength="hard",
                rationale="Separate smells/noise",
            ),
            dict(
                id="adj-garage-groceries",
                a="pi-garage",
                b="pi-heavy-kitchen",
                kind="near",
                strength="soft",
                weight=3,
                rationale="Short grocery carrying route",
            ),
        ]
    )
    model = model_doc(site, program)
    out.append(
        fixture(
            "heavy-cooking",
            site,
            "Two parking bays and a separate 14 m2 heavy kitchen with a near garage route; "
            "seed golden bungalow lacking both program items. No car dimensions assumed.",
            program=program,
            cases=[case("missing-service", model, defect=True)],
            expectations=[
                metric(
                    "two-vehicles",
                    "practical_usability",
                    "garage_vehicle_capacity",
                    2,
                    source="program",
                    target="program",
                    basis="two explicitly declared parking bays",
                ),
                finding(
                    "heavy-kitchen-missing",
                    "practical_usability",
                    "program_item_missing",
                    1,
                    source="evaluation",
                    target="missing-service",
                    subjects=["pi-heavy-kitchen"],
                    basis="golden bungalow has only its ordinary kitchen",
                ),
                finding(
                    "garage-missing",
                    "circulation",
                    "program_item_missing",
                    1,
                    source="evaluation",
                    target="missing-service",
                    subjects=["pi-garage"],
                    basis="golden bungalow has no garage",
                ),
                metric(
                    "grocery-route",
                    "circulation",
                    "garage_to_kitchen_length_m",
                    None,
                    source="evaluation",
                    target="missing-service",
                    status="not_checked",
                    basis="missing garage: route is explicitly not checked",
                ),
                metric(
                    "vehicle-arrival",
                    "circulation",
                    "vehicle_swept_path",
                    None,
                    source="evaluation",
                    target="missing-service",
                    status="not_checked",
                    basis="no vehicle dimensions, arrival path or drive polygon are modelled",
                ),
            ],
        )
    )
    f = terrain_fixture("large-terrace", dy=-0.4, base=12)
    f["program"]["items"].append(
        dict(
            id="pi-terrace",
            name="Large living terrace",
            function="terrace",
            target_area_m2=60,
            privacy="semi_private",
            level_preference="outdoor",
        )
    )
    f["program"]["adjacencies"].append(
        dict(
            id="adj-terrace-living",
            a="pi-living",
            b="pi-terrace",
            kind="connected",
            strength="hard",
            rationale="Living space opens onto hillside terrace",
        )
    )
    f["expectations"].append(
        metric(
            "terrace-area",
            "practical_usability",
            "target_area_m2",
            60,
            source="program",
            target="program",
            subjects=["pi-terrace"],
            basis="declared 60 m2 terrace preference",
        )
    )
    f["expectations"].append(
        future(
            "terrace-support",
            "terrain_compatibility",
            "terrace_support_geometry",
            "S8",
            basis="steep-site terrace geometry and support are not measured by S3",
        )
    )
    out.append(f)
    return out


def preferences():
    out = []
    # Byte-identical site for both households, two checked geometric layouts.
    site = site_doc("preference-comparison", width=32, depth=34)
    for ident, kind in (("social-cooking", "connected"), ("quiet-cooking", "separated")):
        program = program_doc(site["project_id"])
        program["adjacencies"] = [
            dict(
                id="adj-cooking-priority",
                a="pi-living",
                b="pi-kitchen",
                kind=kind,
                strength="soft",
                weight=3,
                rationale=f"Fictional household prefers {kind} kitchen",
            )
        ]
        # Reduce kitchen minimum for the smaller, isolated existing room.
        next(i for i in program["items"] if i["id"] == "pi-kitchen").update(
            min_area_m2=14, target_area_m2=17.5
        )
        open_model = model_doc(site, program)
        open_model["relationships"] = []
        isolated = copy.deepcopy(open_model)
        isolated["openings"] = [o for o in isolated["openings"] if o["id"] != "o-living-kitchen"]
        kitchen = next(s for s in isolated["spaces"] if s["id"] == "sp-kitchen")
        bedroom = next(s for s in isolated["spaces"] if s["id"] == "sp-bed-children")
        for key in ("function", "program_item_id", "zone_id", "name"):
            kitchen[key], bedroom[key] = bedroom[key], kitchen[key]
        for zone in isolated["zones"]:
            zone["space_ids"] = [s["id"] for s in isolated["spaces"] if s["zone_id"] == zone["id"]]
        isolated["fixtures"] = [fx for fx in isolated["fixtures"] if fx["id"] != "fx-kitchen-sink"]
        isolated["relationships"] = []
        # These are valid reference layouts; only identified negative cases may contain errors.
        for model in (open_model, isolated):
            failures = errors(
                check_model(
                    HouseModel.model_validate(model),
                    Site.model_validate(site),
                    SpaceProgram.model_validate(program),
                )
            )
            if failures:
                raise ValueError(f"preference reference layout invalid: {failures}")
        expectations = [
            metric(
                f"priority-{target}",
                "spatial_topological_diversity",
                "adjacency_satisfied",
                desired,
                source="evaluation",
                target=target,
                subjects=["adj-cooking-priority"],
                basis=f"{kind} preference on fixed layout {target}",
            )
            for target, desired in (
                ("open-layout", kind == "connected"),
                ("isolated-layout", kind == "separated"),
            )
        ]
        expectations.extend(
            metric(
                f"kitchen-area-{target}",
                "metric_accuracy",
                "room_area_m2",
                area,
                source="evaluation",
                target=target,
                subjects=["pi-kitchen"],
                basis="rectangular room dimensions; smaller isolated kitchen is a trade-off",
            )
            for target, area in (("open-layout", 30), ("isolated-layout", 17.5))
        )
        expectations.extend(
            finding(
                f"bedroom-noise-{target}",
                "privacy",
                "bedroom_noise_adjacency",
                count,
                source="evaluation",
                target=target,
                subjects=["sp-kitchen", "sp-living"] if count else [],
                basis=basis,
            )
            | ({"status": "inferred"} if count else {})
            for target, count, basis in (
                ("open-layout", 0, "bedrooms are across the hall from living and kitchen"),
                ("isolated-layout", 1, "front room used as a bedroom shares the 5 m wall x=16"),
            )
        )
        out.append(
            fixture(
                ident,
                site,
                "Same site and candidates: open 30 m2 kitchen shares wall/door with living; "
                "isolated 17.5 m2 kitchen uses existing rear room, no shared wall with living. "
                "Opposite soft adjacency requirements reverse satisfaction; no overall score.",
                program=program,
                cases=[case("open-layout", open_model), case("isolated-layout", isolated)],
                expectations=expectations,
            )
        )
    return out


def fixtures():
    out = [
        terrain_fixture("flat-simple"),
        terrain_fixture("narrow-deep", width=10, depth=60),
        terrain_fixture("steep-reference", width=19.2, depth=31.25, dy=-0.4, base=12.5),
        terrain_fixture("road-high", dy=-0.5, base=15),
        terrain_fixture("road-low", dy=0.5),
        terrain_fixture("cross-slope", dx=0.4),
        terrain_fixture("diagonal-slope", dx=0.3, dy=-0.4, base=12),
    ]
    for f, back in ((out[3], 0), (out[4], 15)):
        f["expectations"].extend(
            [
                metric(
                    "road-corner-level",
                    "terrain_compatibility",
                    "spot_elevation_m",
                    15 - back,
                    subjects=["spot-sw"],
                    basis="plane equation evaluated at road y=0",
                ),
                metric(
                    "rear-corner-level",
                    "terrain_compatibility",
                    "spot_elevation_m",
                    back,
                    subjects=["spot-nw"],
                    basis="plane equation evaluated at rear y=30",
                ),
            ]
        )
    s = site_doc("concave")
    s["boundary"] = {"outer": [[0, 0], [30, 0], [30, 12], [12, 12], [12, 30], [0, 30]]}
    s["buildable_envelope"]["polygon"] = {
        "outer": [[2, 3], [28, 3], [28, 10], [10, 10], [10, 27], [2, 27]]
    }
    s["terrain"]["spot_elevations"] = [
        dict(id=f"spot-{i}", xy=p, z_m=0) for i, p in enumerate(s["boundary"]["outer"])
    ]
    out.append(
        fixture(
            "concave",
            s,
            "L parcel =30*12+12*18=576 m2; L envelope=26*7+8*17=318 m2.",
            expectations=[
                metric("l-area", "metric_accuracy", "parcel_area_m2", 576, basis="30*12+12*18"),
                metric(
                    "l-envelope",
                    "geometric_feasibility",
                    "envelope_area_m2",
                    318,
                    basis="26*7+8*17",
                ),
                metric(
                    "l-containment",
                    "geometric_feasibility",
                    "envelope_inside_parcel",
                    True,
                    basis="explicit inset L polygon, concave notch excluded",
                ),
            ],
        )
    )
    s = site_doc("breakline-noise")
    s["features"].append(
        dict(
            id="retaining-breakline",
            kind="other",
            status="assumption",
            name="Retaining wall survey breakline (not a road or contour)",
            geometry=dict(type="polyline", line=dict(points=[[10, 0], [10, 30]])),
            notes="Discontinuous ground intent; current Delaunay builder is unconstrained",
        )
    )
    s["terrain"]["spot_elevations"].extend(
        [
            dict(id="spot-wall-low", xy=[10, 15], z_m=0),
            dict(id="spot-wall-high", xy=[10.0000001, 15], z_m=2),
        ]
    )
    out.append(
        fixture(
            "breakline-noise",
            s,
            "Retaining-wall trace at x=10; near duplicate XY 1e-7 m apart differs by 2 m Z. "
            "Builder must report conflict and refuse a TIN; no smoothing or deletion.",
            expectations=[
                metric(
                    "conflict",
                    "terrain_compatibility",
                    "elevation_conflicts",
                    1,
                    basis="one near-duplicate point pair within builder tolerance",
                ),
                metric(
                    "surface-refused",
                    "unknowns",
                    "tin_present",
                    False,
                    basis="conflicting elevations prevent trustworthy interpolation",
                ),
                future(
                    "retaining-breakline",
                    "terrain_compatibility",
                    "breakline_preserved",
                    "S8",
                    basis="current TIN has no constrained breakline support",
                ),
            ],
        )
    )
    s = site_doc("sliver-tin")
    s["terrain"]["spot_elevations"].append(dict(id="spot-near-edge", xy=[10, 0.0001], z_m=1))
    out.append(
        fixture(
            "sliver-tin",
            s,
            "Point 0.1 mm from road edge with +1 m noise makes one 0.001 m2 sliver. "
            "All observations retained; no claim that this noisy surface is true.",
            expectations=[
                metric(
                    "surface-built",
                    "terrain_compatibility",
                    "tin_present",
                    True,
                    basis="distinct XY permit triangulation",
                ),
                future(
                    "sliver-reported",
                    "terrain_compatibility",
                    "sliver_triangle_count",
                    "S8",
                    basis="surface quality acceptance remains an S8 task",
                ),
            ],
        )
    )
    f = terrain_fixture("unknown-north", width=32, depth=34, dx=0.1)
    f["cases"] = [case("unoriented", model_doc(f["site"], f["program"]))]
    f["expectations"].extend(
        [
            metric(
                "north-unknown",
                "unknowns",
                "true_north_deg",
                None,
                status="not_checked",
                basis="CRS unknown; local axes do not establish geographic north",
            ),
            *[
                metric(
                    f"bearing-{i}",
                    "unknowns",
                    "edge_grid_bearing_deg",
                    None,
                    subjects=[f"edge-{i}"],
                    status="not_checked",
                    basis="unconfirmed CRS cannot establish grid bearings",
                )
                for i in range(1, 5)
            ],
            metric(
                "daylight",
                "unknowns",
                "daylight_orientation",
                None,
                source="evaluation",
                target="unoriented",
                status="not_checked",
                basis="orientation simulation is not performed; north is unknown",
            ),
            *[
                finding(
                    f"buried-{window}",
                    "terrain_compatibility",
                    "window_buried",
                    1,
                    source="evaluation",
                    target="unoriented",
                    subjects=[window],
                    basis=f"grade z=0.1x is above the sill (floor 0.6 m) {where}",
                )
                | {"status": "inferred"}
                for window, where in (
                    ("win-living-s", "+0 m along x 12-14"),
                    ("win-kitchen-s", "+0.9 m along x 18-19.5"),
                    ("win-kitchen-e", "+0.9 m at x=22"),
                    ("win-bed-children-n", "+0.9 m along x 19-20.5"),
                )
            ],
            finding(
                "unburied-living-w",
                "terrain_compatibility",
                "window_buried",
                0,
                source="evaluation",
                target="unoriented",
                subjects=["win-living-w"],
                basis="grade 1.0 m at x=10 is below the 1.5 m sill",
            ),
        ]
    )
    out.append(f)
    out.extend(households())
    out.extend(preferences())
    out[0]["expectations"].extend(
        [
            future(
                "plan-visual",
                "visual_consistency",
                "svg_model_consistency",
                "S5",
                basis="viewer and agent screenshot review are later stages",
            ),
            future(
                "revision-history",
                "versioned_revisions",
                "versioned_revision_integrity",
                "S7",
                basis="scenario revision checks will exercise the improved solver",
            ),
        ]
    )
    return [BenchmarkFixture.model_validate(f) for f in out]


def documents():
    return {f"{f.id}.json": f.model_dump_json(indent=2) + "\n" for f in fixtures()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    generated = HERE / "fixtures"
    docs = documents()
    stale = []
    if not args.check:
        generated.mkdir(parents=True, exist_ok=True)
    for name, text in docs.items():
        path = generated / name
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.write_text(text, encoding="utf-8")
    extras = {p.name for p in generated.glob("*.json")} - docs.keys()
    stale.extend(sorted(extras))
    if stale:
        print("Stale/unexpected fixtures: " + ", ".join(stale))
        return 1
    print(f"{len(docs)} synthetic fixtures {'current' if args.check else 'written'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
