"""`plan revise` reports which Findings about the targeted ids disappeared, remain or are new.

Through ``PlanService.revise`` with a store and the solver (#35, ADR 0033). Solver output
differs between platforms (ISS-21, ISS-28), so the lists are checked against the two stored
Evaluations rather than against fixed geometry.
"""

from __future__ import annotations

import json

from house_ai.cli.main import main
from house_ai.orchestration.plans import PlanService

from .conftest import AGENT
from .test_plan_workflow import _approve_site_and_program, _load

TARGETS = ("pi-kitchen", "sp-kitchen")


def _key(v) -> tuple[str, tuple[str, ...]]:
    return (v.code, tuple(sorted(v.subject_ids)))


def _about(report, targets) -> set[tuple[str, tuple[str, ...]]]:
    return {_key(v) for v in report.violations if set(targets) & set(v.subject_ids)}


def test_a_revision_reports_the_findings_about_what_it_targeted(tmp_path):
    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    (parent,) = svc.generate(AGENT, strategies=["compact"]).generated
    res = svc.revise(
        "concept-compact", "Please enlarge the kitchen.", AGENT, ops=["area:pi-kitchen=16"]
    )
    change = res.findings
    assert change.targets == TARGETS

    before, after = _about(parent.report, TARGETS), _about(res.option.report, TARGETS)
    assert before and after  # the kitchen has Findings in both Evaluations
    gone = {_key(v) for v in change.disappeared}
    kept = {_key(v) for v in change.remaining}
    new = {_key(v) for v in change.new}
    # Every Finding about the kitchen in either Evaluation is in exactly one list.
    assert gone | kept | new == before | after
    assert not (gone & kept) and not (gone & new) and not (kept & new)
    assert new == after - before
    assert gone <= before - after
    assert before & after <= kept
    # The kitchen was enlarged, so anything that left the Evaluation was about changed geometry.
    assert gone == before - after


def test_cli_plan_revise_json_carries_the_three_lists(tmp_path, capsys):
    store = _load(tmp_path)
    _approve_site_and_program(store)
    PlanService(store).generate(AGENT, strategies=["compact"])
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
    assert set(out["findings"]) == {"targets", "disappeared", "remaining", "new"}
    assert out["findings"]["targets"] == list(TARGETS)
    assert {"plan_ref", "revision", "export_dir"} <= set(out)
    revision_md = next((tmp_path / "out").rglob("revision.md")).read_text("utf-8")
    assert "## Findings about pi-kitchen, sp-kitchen" in revision_md
