"""Read-only export bundle generator for the 2D plan option reviewer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from house_ai.constants.reviewer import (
    APPROVAL_GATES,
    GATE_MODEL,
    GATE_PLAN,
    GATE_PROGRAM,
    GATE_SITE,
    REVIEWER_BUNDLE_FILENAME,
    REVIEWER_BUNDLE_SCHEMA_VERSION,
)
from house_ai.domain.brief import DesignBrief
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import PlanVersion, RevisionReport
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.site import Site
from house_ai.domain.workflow import Gate
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import content_hash

from .plans import EXPLORATORY_BANNER, PlanService
from .workflow import Workflow


def _format_gate_commands(project_name: str) -> dict[str, dict[str, Any]]:
    """Format human-only CLI approval commands for each workflow gate."""
    return {
        GATE_SITE: {
            "name": "Site Gate",
            "confirm_command": (
                f"house-ai site confirm {project_name} "
                "--epsg <epsg-code> --vertical-datum <datum> --confirmer <your-name>"
            ),
            "approve_command": (
                f"house-ai workflow approve {project_name} site --id site --approver <your-name>"
            ),
            "description": (
                "Requires human confirmation of horizontal/vertical CRS and human approval."
            ),
        },
        GATE_PROGRAM: {
            "name": "Program Gate",
            "approve_command": (
                f"house-ai workflow approve {project_name} program "
                "--id program --approver <your-name>"
            ),
            "description": "Requires human review of space program and architectural brief.",
        },
        GATE_PLAN: {
            "name": "Plan Gate",
            "approve_command": (
                f"house-ai workflow approve {project_name} plan "
                "--id <option-id> --version <version> --approver <your-name>"
            ),
            "description": "Requires human approval of a specific evaluated plan version.",
        },
        GATE_MODEL: {
            "name": "Model Gate",
            "approve_command": (
                f"house-ai workflow approve {project_name} model "
                "--id <model-id> --approver <your-name>"
            ),
            "description": "Requires human approval of 3D Blender/BIM model.",
        },
    }


def build_reviewer_bundle(
    store: ProjectStore,
    *,
    plan_options_dir: Path | None = None,
    exploratory: bool = False,
) -> dict[str, Any]:
    """Construct a complete, read-only JSON bundle for the 2D plan option reviewer.

    Never mutates the ProjectStore, appends events, or modifies artifacts.
    """
    wf = Workflow(store)
    status = wf.status()
    project_name = store.project_id

    # 1. Project metadata & gate status
    approvals_summary: dict[str, Any] = {}
    gate_commands = _format_gate_commands(project_name)

    for g in APPROVAL_GATES:
        gate_enum = Gate(g)
        is_approved = gate_enum in status.approvals
        approval_obj = status.approvals.get(gate_enum)
        approvals_summary[g] = {
            "approved": is_approved,
            "approved_at": approval_obj.approved_at.isoformat() if approval_obj else None,
            "approved_by": approval_obj.approved_by.id if approval_obj else None,
            "artifact": approval_obj.artifact.model_dump(mode="json") if approval_obj else None,
            **gate_commands[g],
        }

    # 2. Canonical Site
    site_dict: dict[str, Any] | None = None
    site_obj: Site | None = None
    site_refs = store.latest_of_kind(ArtifactKind.SITE)
    if site_refs:
        site_obj = store.get(site_refs[-1], Site)
        site_dict = site_obj.model_dump(mode="json")

    # 3. Canonical Space Program
    program_dict: dict[str, Any] | None = None
    program_obj: SpaceProgram | None = None
    prog_refs = store.latest_of_kind(ArtifactKind.SPACE_PROGRAM)
    if prog_refs:
        program_obj = store.get(prog_refs[-1], SpaceProgram)
        program_dict = program_obj.model_dump(mode="json")

    # 4. Canonical Design Brief
    brief_dict: dict[str, Any] | None = None
    brief_refs = store.latest_of_kind(ArtifactKind.DESIGN_BRIEF)
    if brief_refs:
        brief_obj = store.get(brief_refs[-1], DesignBrief)
        brief_dict = brief_obj.model_dump(mode="json")

    # 5. Stored Plans & Evaluations
    plan_service = PlanService(store)
    plans_list: list[dict[str, Any]] = []

    # Map all revision reports by target version ref
    revision_reports_by_to: dict[str, RevisionReport] = {}
    for r_ref in store.latest_of_kind(ArtifactKind.REVISION_REPORT):
        rr = store.get(r_ref, RevisionReport)
        key = f"{rr.to_version.id}:v{rr.to_version.version}"
        revision_reports_by_to[key] = rr

    # Collect all versions of all stored plans
    for opt_ref in store.latest_of_kind(ArtifactKind.PLAN):
        for ref in store.refs(ArtifactKind.PLAN, opt_ref.id):
            plan_ver = store.get(ref, PlanVersion)
            report = plan_service._report_for(ref)
            rev_key = f"{ref.id}:v{ref.version}"
            rev_report = revision_reports_by_to.get(rev_key)

            # Pre-render SVG
            svg_content: str | None = None
            try:
                svg_content = render_plan_svg(
                    plan_ver,
                    site_obj,
                    report,
                    version=ref.version,
                )
            except Exception:
                svg_content = None

            plans_list.append(
                {
                    "option_id": plan_ver.option_id,
                    "label": plan_ver.label,
                    "strategy": plan_ver.strategy,
                    "version": ref.version,
                    "is_exploratory": False,
                    "plan": plan_ver.model_dump(mode="json"),
                    "plan_ref": ref.model_dump(mode="json"),
                    "evaluation": report.model_dump(mode="json") if report else None,
                    "revision": rev_report.model_dump(mode="json") if rev_report else None,
                    "svg": svg_content,
                }
            )

    # 6. Exploratory plan options from plan_options_dir (if provided or requested)
    if plan_options_dir is not None and plan_options_dir.exists():
        for opt_dir in sorted(plan_options_dir.iterdir()):
            if not opt_dir.is_dir():
                continue
            for v_dir in sorted(opt_dir.iterdir()):
                if not v_dir.is_dir():
                    continue
                plan_file = v_dir / "plan.json"
                if not plan_file.exists():
                    continue
                try:
                    plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
                    plan_ver = PlanVersion.model_validate(plan_data)
                    metrics_file = v_dir / "metrics.json"
                    eval_data = (
                        json.loads(metrics_file.read_text(encoding="utf-8"))
                        if metrics_file.exists()
                        else None
                    )
                    eval_report = (
                        EvaluationReport.model_validate(eval_data) if eval_data else None
                    )
                    svg_file = v_dir / "plan.svg"
                    svg_text = svg_file.read_text(encoding="utf-8") if svg_file.exists() else None
                    rev_file = v_dir / "revision.json"
                    rev_data = (
                        json.loads(rev_file.read_text(encoding="utf-8"))
                        if rev_file.exists()
                        else None
                    )
                    rev_report = RevisionReport.model_validate(rev_data) if rev_data else None

                    # Only add if not already in plans_list
                    already_stored = any(
                        p["option_id"] == plan_ver.option_id
                        and p.get("version") == (1 if v_dir.name.startswith("v") else None)
                        for p in plans_list
                    )
                    if not already_stored:
                        plans_list.append(
                            {
                                "option_id": plan_ver.option_id,
                                "label": plan_ver.label,
                                "strategy": plan_ver.strategy,
                                "version": 1 if v_dir.name.startswith("v") else None,
                                "is_exploratory": True,
                                "exploratory_warning": EXPLORATORY_BANNER,
                                "plan": plan_ver.model_dump(mode="json"),
                                "plan_ref": {
                                    "kind": ArtifactKind.PLAN.value,
                                    "id": plan_ver.option_id,
                                    "version": 1,
                                    "sha256": content_hash(plan_ver),
                                },
                                "evaluation": (
                                    eval_report.model_dump(mode="json") if eval_report else None
                                ),
                                "revision": (
                                    rev_report.model_dump(mode="json") if rev_report else None
                                ),
                                "svg": svg_text,
                            }
                        )
                except Exception:
                    continue

    # 7. Comparison matrix
    comparison_text = ""
    try:
        comparison_text = plan_service.compare()
    except Exception:
        comparison_text = ""

    return {
        "schema_version": REVIEWER_BUNDLE_SCHEMA_VERSION,
        "project": {
            "name": project_name,
            "state": status.state.value,
            "manifest": store.manifest().model_dump(mode="json"),
        },
        "gates": approvals_summary,
        "site": site_dict,
        "program": program_dict,
        "brief": brief_dict,
        "plans": plans_list,
        "comparison_markdown": comparison_text,
    }


def export_reviewer_bundle(
    store: ProjectStore,
    out_dir: Path,
    *,
    plan_options_dir: Path | None = None,
    exploratory: bool = False,
) -> Path:
    """Build and write the reviewer bundle JSON to out_dir/bundle.json."""
    bundle_data = build_reviewer_bundle(
        store,
        plan_options_dir=plan_options_dir,
        exploratory=exploratory,
    )
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    bundle_file = out_path / REVIEWER_BUNDLE_FILENAME
    bundle_file.write_text(
        json.dumps(bundle_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return bundle_file
