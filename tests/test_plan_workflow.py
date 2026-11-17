"""Milestone D: plan concepts in a project store, behind the human gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from house_ai.cli.main import main
from house_ai.domain.codepack import find_prohibited_claims
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import PlanVersion, RevisionReport
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.plans import PlanService, PlanWorkflowError
from house_ai.orchestration.workflow import ApprovalRequiresHuman, Workflow
from house_ai.storage import ProjectStore

from .conftest import AGENT, HUMAN

OWNER = Actor(kind=ActorKind.HUMAN, id="example-owner")
FILES = {
    "plan.json",
    "plan.svg",
    "metrics.json",
    "violations.json",
    "assumptions.json",
    "explanation.md",
}


def _load(tmp_path: Path, name: str = "synthetic-hillside") -> ProjectStore:
    d = tmp_path / name
    assert (
        main(
            [
                "example",
                "load",
                str(d),
                "--name",
                name,
                "--project-id",
                name,
                "--actor",
                "human:example",
            ]
        )
        == 0
    )
    return ProjectStore(d)


def _approve_site_and_program(store: ProjectStore) -> Workflow:
    wf = Workflow(store)
    wf.approve(Gate.SITE, store.latest(ArtifactKind.SITE, "site"), OWNER, "synthetic site ok")
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview done (synthetic)")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "program ready")
    wf.approve(Gate.PROGRAM, store.latest(ArtifactKind.SPACE_PROGRAM, "program"), OWNER, "ok")
    return wf


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("plans")
    store = _load(tmp)
    _approve_site_and_program(store)
    out = tmp / "concepts"
    code = main(
        [
            "plan",
            "generate",
            str(store.root),
            "--out",
            str(out),
            "--json",
            "--actor",
            "agent:claude-code",
        ]
    )
    assert code == 0
    return store, out


def test_generate_stores_versions_evaluations_and_moves_to_concept_review(generated):
    store, out = generated
    assert Workflow(store).state is WorkflowState.PLAN_REVIEW
    plans = store.latest_of_kind(ArtifactKind.PLAN)
    assert len(plans) >= 3
    reports = {
        store.get(r, EvaluationReport).plan_ref.model_dump_json()
        for r in store.refs(ArtifactKind.EVALUATION_REPORT)
    }
    for ref in plans:
        assert ref.model_dump_json() in reports
        plan = store.get(ref, PlanVersion)
        approved_site = Workflow(store).status().approvals[Gate.SITE].artifact
        assert plan.model.site_ref == approved_site
        kinds = {i.kind for i in plan.provenance.inputs}
        assert {ArtifactKind.SITE, ArtifactKind.SPACE_PROGRAM, ArtifactKind.CONSTRAINT_SET} <= kinds
    assert store.latest(ArtifactKind.CONSTRAINT_SET, "constraints") is not None
    assert store.verify() == []


def test_each_candidate_is_exported_with_the_six_files(generated):
    store, out = generated
    for ref in store.latest_of_kind(ArtifactKind.PLAN):
        folder = out / ref.id / f"v{ref.version:04d}"
        assert {p.name for p in folder.iterdir()} >= FILES
        assert find_prohibited_claims((folder / "explanation.md").read_text("utf-8")) == []
        violations = json.loads((folder / "violations.json").read_text("utf-8"))
        assert violations["plan"]["sha256"] == ref.sha256
    assert (out / "comparison.md").is_file()


def test_generation_is_refused_before_the_gates_and_writes_nothing(tmp_path, capsys):
    store = _load(tmp_path)
    before = len(store.events())
    code = main(["plan", "generate", str(store.root), "--actor", "agent:claude-code"])
    assert code == 1
    assert "approved site and program" in capsys.readouterr().out
    assert len(store.events()) == before
    assert not (store.root / "design").exists()


def test_exploratory_preview_stores_nothing_and_says_so(tmp_path):
    store = _load(tmp_path)
    before = len(store.events())
    out = tmp_path / "preview"
    res = PlanService(store).generate(
        AGENT, strategies=["compact", "linear", "split_level"], out_dir=out, exploratory=True
    )
    assert len(store.events()) == before
    assert len(res.generated) == 3
    for opt in res.generated:
        assert opt.plan_ref is None
        assert "EXPLORATORY" in (opt.export_dir / "explanation.md").read_text("utf-8")
        assert "EXPLORATORY" in (opt.export_dir / "plan.svg").read_text("utf-8")
    assert "EXPLORATORY" in (out / "comparison.md").read_text("utf-8")


def test_revision_creates_a_child_version_with_a_report(generated):
    store, out = generated
    svc = PlanService(store)
    base = store.latest(ArtifactKind.PLAN, "concept-split-level")
    words = "The kitchen is too small; keep our bedroom away from the kids."
    res = svc.revise(
        "concept-split-level",
        words,
        AGENT,
        out_dir=out,
        ops=["area:pi-kitchen=16", "separate:pi-bed-main,pi-bed-child-1"],
    )
    new = store.get(res.option.plan_ref, PlanVersion)
    assert res.option.plan_ref.version == base.version + 1
    assert new.parent == base
    assert new.change_request.text == words
    assert new.generation.revision_ops == [
        "area:pi-kitchen=16",
        "separate:pi-bed-main,pi-bed-child-1",
    ]
    rev = store.get(res.revision_ref, RevisionReport)
    assert rev.requested_change == words and rev.from_version == base
    assert "sp-kitchen" in rev.rooms_changed
    kitchen = next(c for c in rev.area_changes if c.space_id == "sp-kitchen")
    assert kitchen.after_m2 > kitchen.before_m2
    # The parent is untouched and still loadable.
    assert store.get(base, PlanVersion).generation.revision_ops == []
    assert Workflow(store).state is WorkflowState.PLAN_REVIEW
    assert (res.export_dir / "revision.md").is_file()
    assert store.verify() == []


def test_revision_below_the_program_minimum_is_refused_without_writes(generated):
    store, _ = generated
    before = len(store.events())
    with pytest.raises(PlanWorkflowError, match="below the approved program minimum"):
        PlanService(store).revise(
            "concept-compact", "Tiny kitchen please", AGENT, ops=["area:pi-kitchen=2"]
        )
    assert len(store.events()) == before


def test_unsupported_revision_kinds_are_refused(generated):
    from house_ai.domain.plan import ChangeRequestKind

    store, _ = generated
    with pytest.raises(PlanWorkflowError, match="not supported"):
        PlanService(store).revise(
            "concept-compact", "Generate alternatives", AGENT, kind=ChangeRequestKind.ALTERNATIVES
        )


def test_plan_gate_stays_human_only_and_freezes_the_plan(tmp_path):
    store = _load(tmp_path)
    wf = _approve_site_and_program(store)
    PlanService(store).generate(AGENT, strategies=["compact", "two_wing"])
    ref = store.latest(ArtifactKind.PLAN, "concept-compact")
    assert (
        main(["plan", "review", str(store.root), "concept-compact", "--actor", "agent:claude-code"])
        == 0
    )
    with pytest.raises(ApprovalRequiresHuman):
        wf.approve(Gate.PLAN, ref, AGENT, "looks good")
    assert wf.check_gate(Gate.PLAN, ref) == []
    wf.approve(Gate.PLAN, ref, HUMAN, "this is the one")
    assert wf.state is WorkflowState.PLAN_APPROVED
    before = len(store.events())
    with pytest.raises(PlanWorkflowError, match="frozen"):
        PlanService(store).revise(
            "concept-compact", "bigger living room", AGENT, ops=["area:pi-living=40"]
        )
    with pytest.raises(PlanWorkflowError):
        PlanService(store).generate(AGENT)
    assert len(store.events()) == before


def test_cli_list_compare_and_strategies(generated, capsys):
    store, out = generated
    assert main(["plan", "list", str(store.root), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert {r["option_id"] for r in rows} >= {"concept-compact", "concept-split-level"}
    assert main(["plan", "compare", str(store.root)]) == 0
    assert "How different the plan options are" in capsys.readouterr().out
    assert main(["plan", "strategies"]) == 0
    assert "split_level" in capsys.readouterr().out


def test_cli_cannot_approve_the_plan_gate_without_a_terminal(generated, capsys):
    store, _ = generated
    code = main(
        [
            "workflow",
            "approve",
            str(store.root),
            "plan",
            "--id",
            "concept-compact",
            "--approver",
            "someone",
        ]
    )
    assert code == 2
