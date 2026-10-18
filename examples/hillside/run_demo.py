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
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.evaluators import CirculationEvaluator, ProgramEvaluator
from house_ai.evaluation.usability import DaylightOpportunityEvaluator
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.generation.terrain_levels import SECTIONAL_STRATEGIES
from house_ai.render2d.hillside_export import export_hillside_views
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.storage.hashing import load_document

ROOT = Path(__file__).resolve().parents[2]


def architectural_comparison(model, site, program, hillside):
    ctx = EvaluationContext(model, site, program, None)
    function = ProgramEvaluator().evaluate(ctx)
    circulation = CirculationEvaluator().evaluate(ctx)
    daylight = DaylightOpportunityEvaluator().evaluate(ctx)
    circ_values = {m.metric: m.value for m in circulation.metrics}
    capable = [m for m in daylight.metrics if m.metric == "window_capable_external_length_m"]
    total_capable = (
        sum(m.value for m in capable)
        if capable and all(m.value is not None for m in capable)
        else None
    )
    return {
        "comfort": {"status": "not_checked", "reason": "Thermal/acoustic comfort study required"},
        "function": {
            "status": "measured",
            "method": "program_vs_canonical_space_geometry",
            "program_area_m2": next(
                m.value for m in function.metrics if m.metric == "net_program_area_m2"
            ),
            "missing_item_ids": [
                sid
                for v in function.violations
                if v.code == "program_item_missing"
                for sid in v.subject_ids
            ],
            "note": "Area and completeness do not establish architectural quality",
        },
        "beauty": {
            "status": "not_checked",
            "reason": "Homeowner/architect aesthetic review required",
        },
        "circulation": {
            "status": "measured",
            "circulation_ratio": circ_values["circulation_ratio"],
            "stair_count": len(model.stairs),
            "total_stair_rise_m": sum(
                abs(
                    model.level(s.to_level_id).elevation_m
                    - model.level(s.from_level_id).elevation_m
                )
                for s in model.stairs
            ),
            "metrics": [m.model_dump(mode="json") for m in circulation.metrics],
            "note": "Path claims retain measured/inferred/not_checked status individually",
        },
        "daylight": {
            "status": "inferred" if total_capable is not None else "not_checked",
            "window_capable_facade_total_m": total_capable,
            "metrics": [m.model_dump(mode="json") for m in daylight.metrics],
            "note": "Terrain/window opportunity only; illumination and orientation unchecked",
        },
        "construction_complexity": {
            "status": "inferred",
            "method": "geometric_proxies_only",
            "wall_count": len(model.walls),
            "level_count": len(model.levels),
            "retaining_candidate_count": len(hillside["retaining_candidates"]),
            "known_retaining_face_area_m2": sum(
                r["face_area_m2"] or 0 for r in hillside["retaining_candidates"]
            ),
            "cost_or_feasibility": "not_checked",
        },
        "engineering_risk": {
            "status": "inferred",
            "risks": hillside["risks"],
            "note": "Triggers needing professional review; no risk ranking",
        },
    }


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
        comparison = architectural_comparison(plan.model, site, program, report)
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
                "architectural_comparison": comparison,
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
    text += [
        "",
        "Architectural trade-offs (no single ranking):",
        "",
        "| Intent | Program area m² (measured) | Circulation share (measured) | "
        "Stairs / total rise m (measured) | Window-capable facade m (inferred) | "
        "Retaining candidates / professional triggers |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        if row["status"] != "generated":
            continue
        c = row["architectural_comparison"]
        day = c["daylight"]["window_capable_facade_total_m"]
        daylight_text = f"{day:.2f}" if day is not None else "not checked (incomplete terrain)"
        text.append(
            f"| {row['sectional_strategy']} | {c['function']['program_area_m2']:.2f} | "
            f"{c['circulation']['circulation_ratio']:.3f} | "
            f"{c['circulation']['stair_count']} / {c['circulation']['total_stair_rise_m']:.2f} | "
            f"{daylight_text} | {row['retaining_candidates_count']} / "
            f"{row['needs_professional_count']} |"
        )
    text += [
        "",
        "Comfort: **not checked** — thermal/acoustic study required. "
        "Beauty: **not checked** — homeowner/architect judgment required. "
        "Function: program area/completeness only; architectural usability still needs review. "
        "Construction complexity: wall/level/retaining counts are proxies; cost and feasibility "
        "**not checked**. Engineering risk: every triggered discipline **needs professional**. "
        "Per-element daylight and circulation methods/statuses are in comparison.json.",
    ]
    (out / "comparison.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "project-data/s8-demo")
    args = parser.parse_args()
    for row in run(args.out):
        print(json.dumps(row))
