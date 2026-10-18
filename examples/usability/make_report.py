"""Generate a read-only critic report on fictional solver-backed hillside concepts.

Run: .venv/bin/python -m examples.usability.make_report --out /tmp/usability-demo
No ProjectStore is opened and no gate is approved by this demonstration.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from house_ai.constraints.compiler import compile_constraints
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import Actor, ActorKind
from house_ai.domain.site import Site
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.templates import TEMPLATES, UsabilityPolicy
from house_ai.evaluation.usability import USABILITY_EVALUATORS
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.storage.hashing import content_hash, load_document

from .scenarios import seeded_pairs

CREATED = datetime(2026, 10, 18, 12, tzinfo=UTC)


def build_report():
    folder = Path(__file__).parents[1] / "projects/synthetic-hillside"
    site = Site.model_validate(load_document(folder / "site.yaml"))
    program = SpaceProgram.model_validate(load_document(folder / "space_program.yaml"))
    actor = Actor(kind=ActorKind.AGENT, id="agent:codex")
    constraints = compile_constraints(program, site, created_at=CREATED, actor=actor).constraints
    request = GenerationRequest(
        site=site,
        program=program,
        constraints=constraints,
        site_ref=None,
        program_ref=None,
        created_at=CREATED,
        strategies=["compact", "split_level", "linear"],
        seed=0,
    )
    report = dict(
        classification="synthetic",
        exploratory=True,
        site_approved=False,
        program_approved=False,
        input_hashes=dict(site=content_hash(site), program=content_hash(program)),
        policy=asdict(UsabilityPolicy()),
        policy_basis={k: UsabilityPolicy().basis(k) for k in asdict(UsabilityPolicy())},
        templates=[t.model_dump(mode="json") for t in TEMPLATES.values()],
        options=[],
        defects=[],
    )
    for candidate in CpSatPlanGenerator().candidates(request):
        row = dict(
            strategy=candidate.strategy,
            status=candidate.status,
            reason=candidate.reason,
            integrity_clean=candidate.valid,
        )
        if candidate.plan:
            model = candidate.plan.model
            row["model"] = model.model_dump(mode="json")
            row["model_hash"] = content_hash(model)
            results = [
                e.evaluate(EvaluationContext(model, site, program, constraints, False))
                for e in USABILITY_EVALUATORS
            ]
            row["critics"] = [r.run.model_dump(mode="json") for r in results]
            row["metrics"] = [m.model_dump(mode="json") for r in results for m in r.metrics]
            row["findings"] = [v.model_dump(mode="json") for r in results for v in r.violations]
        report["options"].append(row)
    for ident, name, bad, clean, code, subject in seeded_pairs():
        critic = next(e for e in USABILITY_EVALUATORS if e.name == name)
        results = [critic.evaluate(EvaluationContext(m, None, None, None)) for m in (bad, clean)]
        report["defects"].append(
            dict(
                id=ident,
                code=code,
                subject=subject,
                defect_detected=any(
                    v.code == code and subject in v.subject_ids for v in results[0].violations
                ),
                clean_twin_passes=not any(v.code == code for v in results[1].violations),
            )
        )
    return report


def markdown(report):
    lines = [
        "# Synthetic hillside usability report",
        "",
        "Exploratory software demonstration; no homeowner or professional approvals.",
        "",
        "All planning thresholds are assumptions; every finding cites canonical IDs.",
        "",
        "| Strategy | Generated | Integrity clean | Usability findings | Not checked |",
        "|---|---|---|---:|---:|",
    ]
    for row in report["options"]:
        lines.append(
            f"| {row['strategy']} | {row['status']} | {row['integrity_clean']} | "
            f"{len(row.get('findings', []))} | "
            f"{sum(m['status'] == 'not_checked' for m in row.get('metrics', []))} |"
        )
    lines += [
        "",
        "Furniture uses a 0.1 m, four-rotation search. A failure means no sampled fit,",
        "not continuous infeasibility. Routes are point paths through net-floor polygons;",
        "they do not certify wheelchair width. Unknown stair direction, vehicle dimensions,",
        "and terrain coverage remain not checked. Solar/daylight and airflow are not simulated.",
        "",
        "## Findings",
        "",
    ]
    for row in report["options"]:
        lines += [f"### {row['strategy']}", ""]
        for finding in row.get("findings", []):
            lines.append(
                f"- `{finding['code']}` ({', '.join(finding['subject_ids'])}): "
                f"{finding['message']} [{finding['status']}]"
            )
        if row["reason"]:
            lines.append(row["reason"])
        lines.append("")
    lines += ["## Seeded defects", "", "| Defect | Detected | Clean twin passes |", "|---|---|---|"]
    for row in report["defects"]:
        lines.append(f"| {row['id']} | {row['defect_detected']} | {row['clean_twin_passes']} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_report()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.out / "report.md").write_text(markdown(report))
    print(args.out / "report.md")
    return (
        0 if all(r["defect_detected"] and r["clean_twin_passes"] for r in report["defects"]) else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
