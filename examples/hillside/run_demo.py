"""Reproducible S8 synthetic hillside section/earthwork/strategy demonstration.

No project store or approvals are written. Run with the project Python.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from house_ai.domain.program import SpaceProgram
from house_ai.domain.site import Site
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.generation.terrain_levels import SECTIONAL_STRATEGIES
from house_ai.render2d.hillside_export import export_hillside_views
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.storage.hashing import load_document

ROOT = Path(__file__).resolve().parents[2]


def run(out: Path):
    folder = ROOT / "examples/projects/synthetic-hillside"
    site = Site.model_validate(load_document(folder / "site.yaml"))
    program = SpaceProgram.model_validate(load_document(folder / "space_program.yaml"))
    rows = []
    for mode in SECTIONAL_STRATEGIES:
        candidate = CpSatPlanGenerator().candidates(
            GenerationRequest(
                site=site,
                program=program,
                constraints=None,
                site_ref=None,
                program_ref=None,
                created_at=datetime(2026, 10, 19, tzinfo=UTC),
                strategies=["split_level" if mode == "split_level" else "split_walkout"],
                sectional_strategy=mode,
                deterministic_time=4,
            )
        )[0]
        if candidate.plan is None:
            rows.append(
                {"sectional_strategy": mode, "status": "infeasible", "reason": candidate.reason}
            )
            continue
        plan = candidate.plan
        path = out / mode
        path.mkdir(parents=True, exist_ok=True)
        (path / "plan.json").write_text(plan.model_dump_json(indent=2) + "\n", encoding="utf-8")
        (path / "plan.svg").write_text(
            render_plan_svg(plan, site, banner="SYNTHETIC EXPLORATORY"), encoding="utf-8"
        )
        report = export_hillside_views(plan.model, site, path)
        works = report["earthworks"]
        rows.append(
            {
                "sectional_strategy": mode,
                "status": "generated",
                "integrity_valid": candidate.valid,
                "integrity_findings": [f.code for f in candidate.findings],
                "elevations_m": [lv.elevation_m for lv in plan.model.levels],
                "excavation_m3": works["excavation_volume_m3"],
                "engineered_fill_m3": works["engineered_fill_volume_m3"],
                "void_m3": works["underfloor_void_volume_m3"],
                "max_void_m": works["max_underfloor_void_height_m"],
                "retaining_candidates_count": len(report["retaining_candidates"]),
                "status_of_quantities": "inferred",
                "needs_professional_count": len(report["risks"]),
            }
        )
    out.mkdir(parents=True, exist_ok=True)
    (out / "comparison.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    text = [
        "# Synthetic sectional alternatives",
        "",
        "Exploratory concepts, no approvals. "
        "Cut, fill and void are separate inferred quantities, not construction estimates. "
        "No excavation/elevation preference or single ranking score.",
        "",
        "| Intent | Status | Floors (LOCAL m) | Cut m³ | Void m³ | Max void m | Integrity |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        if row["status"] == "infeasible":
            text.append(
                f"| {row['sectional_strategy']} | infeasible: {row['reason']} | — | — | — | — | — |"
            )
        else:
            text.append(
                f"| {row['sectional_strategy']} | generated | {row['elevations_m']} | "
                f"{row['excavation_m3']:.2f} | {row['void_m3']:.2f} | "
                f"{row['max_void_m']:.2f} | {row['integrity_valid']} |"
            )
    (out / "comparison.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "project-data/s8-demo")
    args = parser.parse_args()
    for row in run(args.out):
        print(json.dumps(row))
