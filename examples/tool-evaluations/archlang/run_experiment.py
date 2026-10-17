"""Run the pinned ArchLang experiment; the npm install lives outside this repository."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from export_fixture import OUT, main
from shapely.geometry import Polygon

from house_ai.domain.model import HouseModel

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
EXPECTED = {
    "clean": [],
    "unreachable": ["W_ROOM_DISCONNECTED"],
    "windowless": ["W_BEDROOM_NO_WINDOW"],
    "blocked-entry": [
        "W_DOORWAY_BLOCKED",
        "W_PATH_TOO_NARROW",
        "W_PATH_TOO_NARROW",
        "W_SWING_OBSTRUCTED",
    ],
}


def run(binary: Path, *args: str) -> tuple[int, dict]:
    result = subprocess.run([str(binary), *args], cwd=ROOT, capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout)


def compare(plan: dict, description: dict, canonical: HouseModel) -> dict:
    """Compare independent compiler facts to canonical ground truth in metres."""
    diffs = []
    for space in canonical.spaces:
        room = next(r for r in description["rooms"] if r["id"] == space.id)
        ring = [(p["x"] / 1000, -p["y"] / 1000) for p in room["floor_polygon"]]
        assert Polygon(ring).symmetric_difference(space.boundary.to_shapely()).area == 0
        assert room["area_m2"] == space.area_m2
        assert room["uses"] == [space.function.value]
        assert room["label"] == space.name
    for wall in canonical.walls:
        other = next(w for w in plan["walls"] if w["id"] == wall.id)
        points = [(p["x"] / 1000, -p["y"] / 1000) for p in other["points"]]
        assert points == [wall.start, wall.end]
        diffs.extend(
            [
                abs(other["thickness"] / 1000 - wall.thickness_m),
                abs(other["height"] / 1000 - wall.height_m),
            ]
        )
    for opening in canonical.openings:
        other = next(op for op in plan["openings"] if op["id"] == opening.id)
        wall = canonical.wall(opening.host_wall_id)
        distance = opening.offset_m + opening.width_m / 2
        center = tuple(
            a + (b - a) * distance / wall.length_m
            for a, b in zip(wall.start, wall.end, strict=True)
        )
        diffs.extend(
            [
                abs(other["x"] / 1000 - center[0]),
                abs(-other["y"] / 1000 - center[1]),
                abs(other["width"] / 1000 - opening.width_m),
                abs(other["head"] / 1000 - opening.height_m - opening.sill_m),
            ]
        )
        if opening.kind.value == "door":
            door = next(d for d in description["doors"] if d["id"] == opening.id)
            assert set(door["between"]) == set(opening.connects)
        else:
            window = next(w for w in description["windows"] if w["id"] == opening.id)
            assert window["room"] == next(c for c in opening.connects if c != "exterior")
            diffs.append(abs(window["sill"] / 1000 - opening.sill_m))
    assert max(diffs) < 1e-12
    assert description["totals"]["floor_area_m2"] == 28
    assert all(room["reachable"] for room in description["access"]["rooms"])
    return {
        "method": "measured",
        "rooms": 2,
        "walls": 5,
        "openings": 4,
        "max_dimension_or_opening_center_error_m": max(diffs),
        "room_polygon_symmetric_difference_m2": 0,
        "canonical_centerline_floor_area_m2": 28,
        "archlang_centerline_floor_area_m2": description["totals"]["floor_area_m2"],
        "archlang_derived_net_floor_area_m2": description["totals"]["net_floor_area_m2"],
        "room_ids_labels_functions_and_door_connections_match": True,
        "archlang_extra_room_classification": {
            r["id"]: r["room_type"] for r in description["rooms"]
        },
        "not_compared": [
            "door handedness convention",
            "window operation semantics",
            "physical clear widths",
            "cardinal orientation",
            "site/terrain",
        ],
    }


def experiment() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archlang",
        type=Path,
        default=Path("/tmp/house-ai-s3-archlang/node_modules/.bin/archlang"),
    )
    args = parser.parse_args()
    binary = args.archlang.resolve()
    version = subprocess.check_output([str(binary), "--version"], text=True).strip()
    assert version == "1.43.1", f"Expected pinned 1.43.1, got {version}"
    main()
    RESULTS.mkdir(exist_ok=True)
    summary = {"package": "@chanmeng666/archlang", "version": version, "cases": {}}
    for case, expected in EXPECTED.items():
        file = f"fixtures/{case}.arch"
        compiled, compile_result = run(
            binary, "compile", file, "-o", f"results/{case}.svg", "--json"
        )
        assert compiled == 0 and compile_result["diagnostics"] == []
        described, description = run(binary, "describe", file, "--json")
        assert described == 0
        linted, lint = run(binary, "lint", file, "--json")
        strict, validated = run(binary, "validate", file, "--strict", "--json")
        codes = sorted(d["code"] for d in lint["diagnostics"])
        assert codes == expected, (case, codes)
        assert linted == 0  # non-strict lint intentionally does not fail on warnings
        assert strict == (0 if case == "clean" else 2)
        assert validated["ok"] == (case == "clean")
        for name, data in [("describe", description), ("lint", lint), ("strict", validated)]:
            (RESULTS / f"{case}-{name}.json").write_text(json.dumps(data, indent=2) + "\n")
        summary["cases"][case] = {
            "compile_exit": compiled,
            "lint_exit": linted,
            "strict_validate_exit": strict,
            "lint_codes": codes,
        }
        if case == "clean":
            status, _ = run(
                binary, "compile", file, "-f", "json", "-o", "results/clean-plan.json", "--json"
            )
            assert status == 0
            plan = json.loads((RESULTS / "clean-plan.json").read_text())
            canonical = HouseModel.model_validate_json((OUT / "clean.json").read_text())
            summary["geometry_and_semantics"] = compare(plan, description, canonical)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    experiment()
