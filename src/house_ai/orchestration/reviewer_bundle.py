"""Read-only export bundle generator for the 2D plan option reviewer."""

from __future__ import annotations

import json
from collections.abc import Callable
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
from house_ai.domain.site import Site, site_blockers
from house_ai.domain.workflow import GATE_ARTIFACT_KIND, Gate
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import content_hash

from .plans import EXPLORATORY_BANNER, PlanService
from .workflow import HumanAction, NextHumanAction, Workflow

#: Reviewer card text per gate; the commands come from the CLI's renderer.
_GATE_CARDS: dict[str, dict[str, str]] = {
    GATE_SITE: {
        "name": "Site Gate",
        "description": "Requires human confirmation of horizontal/vertical CRS and human approval.",
    },
    GATE_PROGRAM: {
        "name": "Program Gate",
        "description": "Requires human review of space program and architectural brief.",
    },
    GATE_PLAN: {
        "name": "Plan Gate",
        "description": "Requires human approval of a specific evaluated plan version.",
    },
    GATE_MODEL: {
        "name": "Model Gate",
        "description": "Requires human approval of 3D Blender/BIM model.",
    },
}


def gate_actions(store: ProjectStore) -> dict[Gate, dict[str, NextHumanAction]]:
    """The human actions the reviewer shows for each gate, without command syntax (ADR 0029).

    Site and program name their newest stored version; plan and model are
    templates, since the Approver picks the option or build in the reviewer.
    The site confirmation asks for what the newest Site's Blockers need.
    """
    out: dict[Gate, dict[str, NextHumanAction]] = {}
    for gate in Gate:
        refs = store.latest_of_kind(GATE_ARTIFACT_KIND[gate])
        pinned = refs[-1] if refs and gate in (Gate.SITE, Gate.PROGRAM) else None
        approve = NextHumanAction(
            HumanAction.APPROVE,
            gate,
            pinned.id if pinned else None,
            pinned.version if pinned else None,
        )
        out[gate] = {"approve_command": approve}
    site_refs = store.latest_of_kind(ArtifactKind.SITE)
    site = site_refs[-1] if site_refs else None
    clears = tuple(site_blockers(store.get(site, Site))) if site else ()
    out[Gate.SITE]["confirm_command"] = NextHumanAction(
        HumanAction.CONFIRM_SITE, Gate.SITE, site.id if site else None, clears=clears
    )
    return out


def build_reviewer_bundle(
    store: ProjectStore,
    *,
    render: Callable[[NextHumanAction], str],
    plan_options_dir: Path | None = None,
    exploratory: bool = False,
) -> dict[str, Any]:
    """Construct a complete, read-only JSON bundle for the 2D plan option reviewer.

    ``render`` turns a next human action into the command line the reviewer
    shows; the command that builds the bundle passes the CLI's renderer.
    Never mutates the ProjectStore, appends events, or modifies artifacts.
    """
    wf = Workflow(store)
    status = wf.status()
    project_name = store.project_id

    # 1. Project metadata & gate status
    approvals_summary: dict[str, Any] = {}
    actions = gate_actions(store)

    for g in APPROVAL_GATES:
        gate_enum = Gate(g)
        is_approved = gate_enum in status.approvals
        approval_obj = status.approvals.get(gate_enum)
        approvals_summary[g] = {
            "approved": is_approved,
            "approved_at": approval_obj.approved_at.isoformat() if approval_obj else None,
            "approved_by": approval_obj.approved_by.id if approval_obj else None,
            "artifact": approval_obj.artifact.model_dump(mode="json") if approval_obj else None,
            **_GATE_CARDS[g],
            **{key: render(action) for key, action in actions[gate_enum].items()},
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
    render: Callable[[NextHumanAction], str],
    plan_options_dir: Path | None = None,
    exploratory: bool = False,
) -> Path:
    """Build and write the reviewer bundle JSON to out_dir/bundle.json."""
    bundle_data = build_reviewer_bundle(
        store,
        render=render,
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
