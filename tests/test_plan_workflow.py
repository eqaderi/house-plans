"""Milestone D: plan concepts in a project store, behind the human gates."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
from pathlib import Path

import pytest

from house_ai.cli.main import main
from house_ai.constants.strategies import STRATEGY_ORDER
from house_ai.domain.codepack import find_prohibited_claims
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import PlanVersion, RevisionReport
from house_ai.domain.provenance import Actor, ActorKind, ApprovalRequiresHuman, ArtifactKind
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.plans import PlanService, PlanWorkflowError
from house_ai.orchestration.workflow import HumanAction, NextHumanAction, Workflow
from house_ai.storage import ProjectStore

from .conftest import AGENT, HUMAN

OWNER = Actor(kind=ActorKind.HUMAN, id="example-owner")
SHIPPED_CONCEPTS = (
    Path(__file__).resolve().parents[1] / "examples/projects/synthetic-hillside/concepts"
)
STRATEGY_OPTION_IDS = [f"concept-{s.replace('_', '-')}" for s in STRATEGY_ORDER]
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
    """Every default strategy generated and stored once; tests that write use ``_copy``.

    Returns (store, export folder, the rows `plan generate --json` printed).
    """
    tmp = tmp_path_factory.mktemp("plans")
    store = _load(tmp)
    _approve_site_and_program(store)
    out = tmp / "concepts"
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
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
    return store, out, json.loads(printed.getvalue())["options"]


def _copy(generated, tmp_path: Path) -> ProjectStore:
    """A private copy of the generated store, for a test that writes to it."""
    store, _, _ = generated
    return ProjectStore(shutil.copytree(store.root, tmp_path / store.root.name))


def _stored_ids(store: ProjectStore) -> set[str]:
    return {ref.id for ref in store.latest_of_kind(ArtifactKind.PLAN)}


def test_generate_stores_versions_evaluations_and_moves_to_concept_review(generated):
    store, out, rows = generated
    assert Workflow(store).state is WorkflowState.PLAN_REVIEW
    # One row per default strategy: a stored v1 when feasible, else a reason and nothing stored.
    assert [(r["option_id"], r["strategy"]) for r in rows] == list(
        zip(STRATEGY_OPTION_IDS, STRATEGY_ORDER, strict=True)
    )
    feasible = {r["option_id"] for r in rows if r["status"] == "generated"}
    # The envelope has no room for a courtyard's second pavilion (a geometric fact, not a
    # time limit); the other five are the options the shipped exploratory concepts show.
    assert feasible == {p.name for p in SHIPPED_CONCEPTS.iterdir() if p.is_dir()}
    assert feasible == set(STRATEGY_OPTION_IDS) - {"concept-courtyard"}
    (courtyard,) = [r for r in rows if r["option_id"] == "concept-courtyard"]
    assert courtyard["status"] == "infeasible" and courtyard["plan_ref"] is None
    assert "no room for a second pavilion behind a garden court" in courtyard["reason"]
    for r in rows:
        assert (r["plan_ref"] is not None) is (r["option_id"] in feasible), r
    plans = store.latest_of_kind(ArtifactKind.PLAN)
    assert {ref.id for ref in plans} == feasible
    assert {ref.version for ref in plans} == {1}
    # Exactly one Evaluation per stored Plan version.
    reports = sorted(
        store.get(r, EvaluationReport).plan_ref.model_dump_json()
        for r in store.refs(ArtifactKind.EVALUATION_REPORT)
    )
    assert reports == sorted(ref.model_dump_json() for ref in plans)
    for ref in plans:
        plan = store.get(ref, PlanVersion)
        approved_site = Workflow(store).status().approvals[Gate.SITE].artifact
        assert plan.model.site_ref == approved_site
        kinds = {i.kind for i in plan.provenance.inputs}
        assert {ArtifactKind.SITE, ArtifactKind.SPACE_PROGRAM, ArtifactKind.CONSTRAINT_SET} <= kinds
    assert store.latest(ArtifactKind.CONSTRAINT_SET, "constraints") is not None
    assert store.verify() == []


def test_each_candidate_is_exported_with_the_six_files(generated):
    store, out, _ = generated
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
    res = PlanService(store).generate(AGENT, strategies=["compact"], out_dir=out, exploratory=True)
    assert len(store.events()) == before
    assert store.refs(ArtifactKind.PLAN) == []
    assert [opt.candidate.option_id for opt in res.generated] == ["concept-compact"]
    for opt in res.generated:
        assert opt.plan_ref is None
        assert "EXPLORATORY" in (opt.export_dir / "explanation.md").read_text("utf-8")
        assert "EXPLORATORY" in (opt.export_dir / "plan.svg").read_text("utf-8")
    assert "EXPLORATORY" in (out / "comparison.md").read_text("utf-8")


def test_revision_creates_a_child_version_with_a_report(generated, tmp_path):
    store = _copy(generated, tmp_path)
    out = tmp_path / "concepts"
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
    parent = store.get(base, PlanVersion)
    assert kitchen.before_m2 == pytest.approx(parent.model.space("sp-kitchen").area_m2, abs=0.01)
    assert kitchen.after_m2 == pytest.approx(new.model.space("sp-kitchen").area_m2, abs=0.01)
    assert kitchen.after_m2 > kitchen.before_m2
    # The parent is untouched and still loadable.
    assert store.get(base, PlanVersion).generation.revision_ops == []
    assert Workflow(store).state is WorkflowState.PLAN_REVIEW
    assert (res.export_dir / "revision.md").is_file()
    assert store.verify() == []


def test_revision_below_the_program_minimum_is_refused_without_writes(generated):
    store, _, _ = generated
    before = len(store.events())
    with pytest.raises(PlanWorkflowError, match="below the approved program minimum"):
        PlanService(store).revise(
            "concept-compact", "Tiny kitchen please", AGENT, ops=["area:pi-kitchen=2"]
        )
    assert len(store.events()) == before


def test_unsupported_revision_kinds_are_refused(generated):
    from house_ai.domain.plan import ChangeRequestKind

    store, _, _ = generated
    before = len(store.events())
    with pytest.raises(PlanWorkflowError, match="not supported"):
        PlanService(store).revise(
            "concept-compact", "Generate alternatives", AGENT, kind=ChangeRequestKind.ALTERNATIVES
        )
    assert len(store.events()) == before


def test_plan_gate_stays_human_only_and_freezes_the_plan(generated, tmp_path):
    store = _copy(generated, tmp_path)
    wf = Workflow(store)
    ref = store.latest(ArtifactKind.PLAN, "concept-compact")
    assert (
        main(["plan", "review", str(store.root), "concept-compact", "--actor", "agent:claude-code"])
        == 0
    )
    with pytest.raises(ApprovalRequiresHuman):
        wf.approve(Gate.PLAN, ref, AGENT, "looks good")
    assert wf.gate_status(Gate.PLAN, ref).blockers == []
    wf.approve(Gate.PLAN, ref, HUMAN, "this is the one")
    assert wf.state is WorkflowState.PLAN_APPROVED
    before = len(store.events())
    with pytest.raises(PlanWorkflowError, match="frozen") as frozen:
        PlanService(store).revise(
            "concept-compact", "bigger living room", AGENT, ops=["area:pi-living=40"]
        )
    assert frozen.value.next_action == NextHumanAction(HumanAction.REOPEN, Gate.PLAN)
    with pytest.raises(PlanWorkflowError):
        PlanService(store).generate(AGENT)
    assert len(store.events()) == before


def test_cli_list_compare_and_strategies(generated, capsys):
    store, _, _ = generated
    assert main(["plan", "list", str(store.root), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert sorted(r["option_id"] for r in rows) == sorted(_stored_ids(store))
    assert main(["plan", "compare", str(store.root)]) == 0
    assert "How different the plan options are" in capsys.readouterr().out
    assert main(["plan", "strategies"]) == 0
    assert "split_level" in capsys.readouterr().out


def test_cli_cannot_approve_the_plan_gate_without_a_terminal(generated, capsys):
    store, _, _ = generated
    before = len(store.events())
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
    assert "approval needs an interactive terminal" in capsys.readouterr().err
    assert len(store.events()) == before
    assert Gate.PLAN not in Workflow(store).status().approvals
