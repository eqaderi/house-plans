"""`plan revise` reports which Findings about the targeted ids disappeared, remain or are new.

Through the CLI and ``PlanService.revise`` with a store and the solver (#35, ADR 0033). Solver
output differs between platforms (ISS-21, ISS-28), so the lists are checked against the two
stored Evaluations rather than against fixed geometry; ``compare_findings`` itself is checked
against hand-built models in ``test_findings_change.py``.
"""

from __future__ import annotations

import json

from house_ai.cli.main import main
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import ArtifactKind
from house_ai.evaluation.findings import compare_findings
from house_ai.evaluation.report import report_id
from house_ai.orchestration.plans import PlanService

from .conftest import AGENT
from .test_plan_workflow import _approve_site_and_program, _load

#: ``area:pi-kitchen=16`` names the requirement, which means its one Space.
TARGETS = ("pi-kitchen", "sp-kitchen")


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

    # The report compares the two stored Evaluations about exactly the targeted ids.
    expected = compare_findings(
        parent_report.violations,
        child_report.violations,
        targets=set(TARGETS),
        before_model=parent_model,
        after_model=child.model,
    )
    assert out["findings"] == expected.to_json()
    assert out["findings"]["targets"] == list(TARGETS)
    assert {"plan_ref", "revision", "export_dir"} <= set(out)
    assert out["plan_ref"] == child_ref.model_dump(mode="json")
    revision_md = next((tmp_path / "out").rglob("revision.md")).read_text("utf-8")
    assert "## Findings about pi-kitchen, sp-kitchen" in revision_md
