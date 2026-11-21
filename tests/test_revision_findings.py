"""`plan revise` reports which Findings about the targeted ids disappeared, remain or are new.

Through the CLI and ``PlanService.revise`` with a store and the solver (#35, ADR 0033). Solver
output differs between platforms (ISS-21, ISS-28), so the three lists are derived here, by set
arithmetic, from the two stored Evaluations rather than from fixed geometry, and never from
``compare_findings``, which is what `plan revise` calls; that function's rules are checked
against hand-built models in ``test_findings_change.py``.
"""

from __future__ import annotations

import json

from house_ai.cli.main import main
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import ArtifactKind
from house_ai.evaluation.report import report_id
from house_ai.orchestration.plans import PlanService

from .conftest import AGENT
from .test_plan_workflow import _approve_site_and_program, _load

#: ``area:pi-kitchen=16`` names the requirement, which means its one Space.
TARGETS = ("pi-kitchen", "sp-kitchen")


Key = tuple[str, tuple[str, ...]]


def _about(report: EvaluationReport) -> set[Key]:
    """What makes a Finding the same Finding (code and cited ids), for those about the kitchen."""
    return {
        (v.code, tuple(sorted(v.subject_ids)))
        for v in report.violations
        if set(TARGETS) & set(v.subject_ids)
    }


def _keys(rows: list[dict]) -> list[Key]:
    return sorted((r["code"], tuple(sorted(r["subject_ids"]))) for r in rows)


def test_a_revision_reports_the_findings_about_what_it_targeted(tmp_path, capsys):
    store = _load(tmp_path)
    _approve_site_and_program(store)
    (parent,) = PlanService(store).generate(AGENT, strategies=["compact"]).generated
    capsys.readouterr()
    code = main(
        [
            "plan",
            "revise",
            str(store.root),
            "concept-compact",
            "Please enlarge the kitchen.",
            "--area",
            "pi-kitchen=16",
            "--json",
            "--out",
            str(tmp_path / "out"),
            "--actor",
            "agent:claude-code",
        ]
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)

    child_ref = store.latest(ArtifactKind.PLAN, "concept-compact")
    assert child_ref.version == 2
    child = store.get(child_ref, PlanVersion)
    (child_report,) = [
        r
        for r in (
            store.get(ref, EvaluationReport)
            for ref in store.refs(ArtifactKind.EVALUATION_REPORT, report_id(child_ref.id))
        )
        if r.plan_ref == child_ref
    ]
    parent_report = store.get(parent.report_ref, EvaluationReport)
    parent_model = store.get(parent.plan_ref, PlanVersion).model
    # The kitchen's target went from 12 to 16 m2: its geometry changed, so any Finding about
    # it that the new Evaluation lacks counts as gone.
    assert child.model.space("sp-kitchen") != parent_model.space("sp-kitchen")

    # Every Finding about the kitchen in either stored Evaluation is in exactly one list. The
    # kitchen changed, so each one the new Evaluation lacks cites changed geometry and has
    # disappeared; none of those remains.
    before, after = _about(parent_report), _about(child_report)
    assert before and after  # the kitchen has Findings in both Evaluations
    assert set(out["findings"]) == {"targets", "disappeared", "remaining", "new"}
    assert _keys(out["findings"]["disappeared"]) == sorted(before - after)
    assert _keys(out["findings"]["remaining"]) == sorted(before & after)
    assert _keys(out["findings"]["new"]) == sorted(after - before)
    assert out["findings"]["targets"] == list(TARGETS)
    assert {"plan_ref", "revision", "export_dir"} <= set(out)
    assert out["plan_ref"] == child_ref.model_dump(mode="json")
    revision_md = next((tmp_path / "out").rglob("revision.md")).read_text("utf-8")
    assert "## Findings about pi-kitchen, sp-kitchen" in revision_md
