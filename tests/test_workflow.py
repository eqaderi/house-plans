"""Workflow state machine and the four human approval gates."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from house_ai.domain.build import BuildRecord
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.provenance import ApprovalRequiresHuman, ArtifactKind, ArtifactRef
from house_ai.domain.workflow import Approval, EventType, Gate, WorkflowState
from house_ai.orchestration.site import SiteService
from house_ai.orchestration.workflow import (
    GATES,
    TRANSITIONS,
    GateBlocked,
    TransitionNotAllowed,
    Workflow,
    WorkflowError,
    replay,
)
from house_ai.storage import ProjectStore
from house_ai.storage.importer import import_folder
from house_ai.storage.project_store import HEAD_ANCHOR_REQUIRED

from .conftest import AGENT, EXAMPLE, HUMAN, SYSTEM, example_doc

S = WorkflowState
K = ArtifactKind
PROV = {
    "created_at": "2026-10-17T10:00:00Z",
    "created_by": {"kind": "agent", "id": "claude-code"},
    "method": "test",
}


class Project:
    """A store loaded with the golden example, plus helpers to walk the workflow."""

    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self.wf = Workflow(store)
        import_folder(store, EXAMPLE, AGENT)

    def ref(self, kind: K, ident: str) -> ArtifactRef:
        ref = self.store.latest(kind, ident)
        assert ref is not None
        return ref

    @property
    def site(self) -> ArtifactRef:
        return self.ref(K.SITE, "site")

    @property
    def program(self) -> ArtifactRef:
        return self.ref(K.SPACE_PROGRAM, "program")

    @property
    def plan(self) -> ArtifactRef:
        return self.ref(K.PLAN, "plan-a")

    def to_site_review(self) -> None:
        assert SiteService(self.store).assess(self.site, AGENT).blockers == []

    def to_site_approved(self) -> None:
        self.to_site_review()
        self.wf.approve(Gate.SITE, self.site, HUMAN, "site truth confirmed")

    def to_program_review(self) -> None:
        self.to_site_approved()
        self.wf.transition(S.INTERVIEWING, AGENT, "start interview")
        self.wf.transition(S.PROGRAM_REVIEW, AGENT, "program drafted")

    def to_program_approved(self) -> None:
        self.to_program_review()
        self.wf.approve(Gate.PROGRAM, self.program, HUMAN, "program approved")

    def to_concept_review(self) -> None:
        self.to_program_approved()
        self.wf.transition(S.PLAN_GENERATION, AGENT, "generate concepts")
        self.wf.transition(S.PLAN_REVIEW, AGENT, "concepts ready")

    def to_plan_approved(self) -> None:
        self.to_concept_review()
        self.wf.approve(Gate.PLAN, self.plan, HUMAN, "final plan approved")

    def put_build(self, target: str = "blender", plan: ArtifactRef | None = None) -> ArtifactRef:
        rec = BuildRecord(
            id=f"build-{target}",
            target=target,
            input_plan=plan or self.plan,
            tool=target,
            provenance=PROV,
        )
        return self.store.put(K.BUILD_RECORD, rec.id, rec, AGENT)

    def to_blender_review(self) -> ArtifactRef:
        self.to_plan_approved()
        self.wf.transition(S.BLENDER_BUILD, AGENT, "build scene")
        ref = self.put_build()
        self.wf.transition(S.BLENDER_REVIEW, AGENT, "scene built")
        return ref


@pytest.fixture
def project(store) -> Project:
    return Project(store)


# ---------------------------------------------------------------- happy path


def test_full_happy_path_with_four_human_approvals(project):
    build = project.to_blender_review()
    project.wf.approve(Gate.MODEL, build, HUMAN, "model approved for Unreal")
    project.wf.transition(S.UNREAL_BUILD, AGENT, "export")
    project.put_build("unreal")
    project.wf.transition(S.UNREAL_REVIEW, AGENT, "walkthrough built")

    status = project.wf.status()
    assert status.state is S.UNREAL_REVIEW
    assert set(status.approvals) == set(Gate)
    assert all(a.approved_by == HUMAN for a in status.approvals.values())
    assert status.approvals[Gate.PLAN].artifact == project.plan
    assert project.store.verify() == []


def test_state_is_replayed_from_events_not_stored(project):
    project.to_program_review()
    manifest = (project.store.root / "project.json").read_text()
    assert "PROGRAM_REVIEW" not in manifest and "state" not in manifest
    reopened = Workflow(ProjectStore(project.store.root))
    assert reopened.state is S.PROGRAM_REVIEW


# ---------------------------------------------------------- no silent skipping


@pytest.mark.parametrize("gate", list(Gate))
def test_gated_states_cannot_be_reached_by_transition(project, gate):
    with pytest.raises(TransitionNotAllowed, match="behind an approval gate"):
        project.wf.transition(GATES[gate].approved_state, HUMAN, "skip it")


def test_cannot_jump_ahead(project):
    with pytest.raises(TransitionNotAllowed, match="allowed: SITE_INGESTION"):
        project.wf.transition(S.PLAN_GENERATION, AGENT, "let's just design")
    assert project.wf.state is S.NEW_PROJECT


def test_transition_requires_a_reason(project):
    with pytest.raises(TransitionNotAllowed, match="reason"):
        project.wf.transition(S.SITE_INGESTION, AGENT, "  ")


def test_transition_table_never_targets_a_gated_state():
    gated = {spec.approved_state for spec in GATES.values()}
    assert all(not (targets & gated) for targets in TRANSITIONS.values())


@pytest.mark.parametrize("actor", [AGENT, SYSTEM])
@pytest.mark.parametrize("gate", list(Gate))
def test_only_humans_can_approve(project, gate, actor):
    with pytest.raises(ApprovalRequiresHuman):
        project.wf.approve(gate, project.site, actor, "I approve")


def test_approval_record_rejects_non_human_even_if_built_directly(project):
    with pytest.raises(ValidationError, match="only a human"):
        Approval(
            id="approval-x",
            gate=Gate.SITE,
            artifact=project.site,
            approved_by=AGENT,
            approved_at="2026-10-17T10:00:00Z",
            statement="sneaky",
        )


def _codes(status_or_error) -> list[tuple[str, str]]:
    """(kind, code) of each Blocker in a gate status or a GateBlocked refusal."""
    return [(b.kind.value, b.code) for b in status_or_error.blockers]


def _refusal(approve) -> list[tuple[str, str]]:
    with pytest.raises(GateBlocked) as exc:
        approve()
    return _codes(exc.value)


def test_approval_from_the_wrong_state_is_blocked(project):
    refusal = _refusal(lambda: project.wf.approve(Gate.SITE, project.site, HUMAN, "too early"))
    assert refusal == [("workflow_state", "wrong_state")]


def test_gate_rejects_the_wrong_artifact_kind(project):
    project.to_site_review()
    refusal = _refusal(lambda: project.wf.approve(Gate.SITE, project.program, HUMAN, "wrong"))
    assert refusal == [("artifact", "wrong_kind")]


def test_gate_rejects_a_hash_that_does_not_match(project):
    project.to_site_review()
    forged = project.site.model_copy(update={"sha256": "0" * 64})
    refusal = _refusal(lambda: project.wf.approve(Gate.SITE, forged, HUMAN, "approve"))
    assert refusal == [("artifact", "not_in_store")]


def test_gate_status_of_an_approvable_gate(project):
    project.to_site_review()
    status = project.wf.gate_status(Gate.SITE, project.site)
    assert (status.gate, status.artifact, status.in_review_state) == (Gate.SITE, project.site, True)
    assert (status.blockers, status.attention) == ([], [])


def test_gate_status_outside_the_review_state(project):
    status = project.wf.gate_status(Gate.PROGRAM, project.program)
    assert status.in_review_state is False
    assert _codes(status) == [("workflow_state", "wrong_state")]
    assert status.open_reasons == [
        "the program gate is approved from PROGRAM_REVIEW; the project is in NEW_PROJECT"
    ]


def test_the_approval_request_keeps_its_saved_shape(project):
    doc = example_doc("open_questions.yaml")
    doc["questions"][0]["blocking"] = True
    project.store.put(K.OPEN_QUESTIONS, "open-questions", doc, AGENT)
    project.to_program_review()

    status = project.wf.request_approval(Gate.PROGRAM, project.program, AGENT)

    event = project.store.events()[-1]
    assert event.type is EventType.APPROVAL_REQUESTED
    assert set(event.payload) - {HEAD_ANCHOR_REQUIRED} == {"gate", "artifact", "open_reasons"}
    assert event.payload["open_reasons"] == [b.message for b in status.blockers]
    assert _codes(status) == [("open_question", "q-study")]
    assert project.store.verify() == []


# ------------------------------------------------------------------- site gate


def test_ambiguous_site_stops_at_needs_verification(project):
    doc = example_doc("site.yaml")
    doc["coordinates"]["horizontal_crs"] = {"status": "declared_in_source", "declared_epsg": 32632}
    doc["coordinates"]["source_units"] = {"unit": "mm", "status": "declared_in_source"}
    unsure = project.store.put(K.SITE, "site", doc, AGENT)

    blockers = SiteService(project.store).assess(unsure, AGENT).blockers
    assert len(blockers) == 2
    assert project.wf.state is S.SITE_NEEDS_CONFIRMATION
    last = project.store.events()[-1]
    assert last.payload["blockers"] == [b.message for b in blockers]

    # Nothing can be approved, and no way forward except back to ingestion.
    with pytest.raises(GateBlocked):
        project.wf.approve(Gate.SITE, unsure, HUMAN, "looks fine")
    assert project.wf.allowed_transitions() == [S.SITE_INGESTION]

    # A human confirms units and CRS; that is a new site version.
    doc["coordinates"]["horizontal_crs"] = {"status": "user_confirmed", "epsg": 32632}
    doc["coordinates"]["source_units"] = {"unit": "m", "status": "user_confirmed"}
    confirmed = project.store.put(K.SITE, "site", doc, HUMAN)
    assert confirmed.version == unsure.version + 1
    project.wf.transition(S.SITE_INGESTION, HUMAN, "units and CRS confirmed")
    assert SiteService(project.store).assess(confirmed, AGENT).blockers == []

    # The ambiguous version still cannot be approved; the confirmed one can.
    assert _refusal(lambda: project.wf.approve(Gate.SITE, unsure, HUMAN, "old version")) == [
        ("site_fact", "source_units"),
        ("site_fact", "horizontal_crs"),
    ]
    approval = project.wf.approve(Gate.SITE, confirmed, HUMAN, "site truth confirmed")
    assert approval.artifact == confirmed
    assert project.wf.state is S.SITE_APPROVED


# ---------------------------------------------------------------- program gate


def test_program_review_needs_a_program(store):
    wf = Workflow(store)
    store.put(K.SITE, "site", example_doc("site.yaml"), AGENT)
    wf.transition(S.SITE_INGESTION, AGENT, "x")
    wf.approve(Gate.SITE, store.latest(K.SITE, "site"), HUMAN, "ok")
    wf.transition(S.INTERVIEWING, AGENT, "x")
    with pytest.raises(TransitionNotAllowed, match="no space program"):
        wf.transition(S.PROGRAM_REVIEW, AGENT, "x")


def test_blocking_open_question_blocks_the_program(project):
    doc = example_doc("open_questions.yaml")
    doc["questions"][0]["blocking"] = True
    project.store.put(K.OPEN_QUESTIONS, "open-questions", doc, AGENT)
    project.to_program_review()
    refusal = _refusal(lambda: project.wf.approve(Gate.PROGRAM, project.program, HUMAN, "ok"))
    assert refusal == [("open_question", "q-study")]


def test_unresolved_contradiction_in_the_cited_brief_blocks_the_program(project):
    brief = example_doc("design_brief.yaml")
    brief["contradictions"] = [
        {
            "id": "ct-1",
            "statement": "One level only, but the budget only fits a 2-storey footprint",
            "fact_ids": ["f-single-storey", "f-bedrooms"],
        }
    ]
    brief_ref = project.store.put(K.DESIGN_BRIEF, "brief", brief, AGENT)
    program = example_doc("space_program.yaml")
    program["brief_ref"] = brief_ref.model_dump(mode="json")
    program_ref = project.store.put(K.SPACE_PROGRAM, "program", program, AGENT)
    project.to_program_review()
    status = project.wf.gate_status(Gate.PROGRAM, program_ref)
    assert _codes(status) == [("contradiction", "ct-1")]
    assert status.blockers[0].subject_ids == ["ct-1"]
    with pytest.raises(GateBlocked):
        project.wf.approve(Gate.PROGRAM, program_ref, HUMAN, "approve")


# ------------------------------------------------------------------- plan gate


def test_plan_gate_reruns_integrity_checks(project):
    doc = example_doc("plans/plan-a.json")
    doc["option_id"] = "plan-b"
    living = next(s for s in doc["model"]["spaces"] if s["id"] == "sp-living")
    living["boundary"]["outer"] = [[10, 12], [17, 12], [17, 17], [10, 17]]
    broken = project.store.put(K.PLAN, "plan-b", doc, AGENT)
    project.to_concept_review()
    refusal = _refusal(lambda: project.wf.approve(Gate.PLAN, broken, HUMAN, "approve"))
    assert ("integrity", "space_overlap") in refusal
    project.wf.approve(Gate.PLAN, project.plan, HUMAN, "approve the valid one")


def test_plan_must_be_drawn_on_the_approved_site_and_program(project):
    project.to_concept_review()
    # A plan that pins a site version nobody approved, and no program at all.
    doc = example_doc("plans/plan-a.json")
    doc["option_id"] = "plan-c"
    doc["model"]["site_ref"]["sha256"] = "f" * 64
    doc["model"]["program_ref"] = None
    stale = project.store.put(K.PLAN, "plan-c", doc, AGENT)
    status = project.wf.gate_status(Gate.PLAN, stale)
    assert _codes(status)[:2] == [
        ("pinned_input", "site_version"),
        ("pinned_input", "program_version"),
    ]


def test_hard_violation_in_an_evaluation_blocks_the_plan(project):
    project.to_concept_review()
    report = EvaluationReport(
        id="eval-1",
        plan_ref=project.plan,
        evaluators=[{"name": "ProgramEvaluator", "version": "0", "status": "ran"}],
        violations=[
            {
                "id": "v-1",
                "code": "min_area",
                "strength": "hard",
                "message": "bath below minimum",
                "status": "measured",
                "evaluator": "ProgramEvaluator",
            }
        ],
        compliance={"status": "not_checked"},
        provenance=PROV,
    )
    project.store.put(K.EVALUATION_REPORT, "eval-1", report, AGENT)
    refusal = _refusal(lambda: project.wf.approve(Gate.PLAN, project.plan, HUMAN, "approve"))
    assert refusal == [("hard_violation", "min_area")]


# ------------------------------------------------------------------ model gate


def test_blender_review_needs_a_build_from_the_approved_plan(project):
    project.to_plan_approved()
    project.wf.transition(S.BLENDER_BUILD, AGENT, "build")
    with pytest.raises(TransitionNotAllowed, match="no blender build record"):
        project.wf.transition(S.BLENDER_REVIEW, AGENT, "done?")


def test_model_gate_rejects_a_build_of_another_plan(project):
    doc = example_doc("plans/plan-a.json")
    doc["option_id"] = "plan-b"
    other_plan = project.store.put(K.PLAN, "plan-b", doc, AGENT)
    project.to_blender_review()
    wrong = project.put_build("blender", plan=other_plan)
    refusal = _refusal(lambda: project.wf.approve(Gate.MODEL, wrong, HUMAN, "approve"))
    assert refusal == [("pinned_input", "plan_version")]


# ---------------------------------------------------------------------- reopen


def test_reopening_the_plan_supersedes_plan_and_model_only(project):
    build = project.to_blender_review()
    project.wf.approve(Gate.MODEL, build, HUMAN, "model ok")
    project.wf.reopen(Gate.PLAN, HUMAN, "make the kitchen larger")

    status = project.wf.status()
    assert status.state is S.PLAN_REVIEW
    assert set(status.approvals) == {Gate.SITE, Gate.PROGRAM}
    assert {a.gate for a in status.superseded} == {Gate.PLAN, Gate.MODEL}
    # Revising and re-approving works; the history keeps both approvals.
    project.wf.approve(Gate.PLAN, project.plan, HUMAN, "approved again")
    assert project.wf.state is S.PLAN_APPROVED
    granted = [e for e in project.store.events() if e.type is EventType.APPROVAL_GRANTED]
    assert [e.payload["approval"]["gate"] for e in granted].count("plan") == 2


def test_reopening_the_site_supersedes_everything(project):
    project.to_plan_approved()
    project.wf.reopen(Gate.SITE, HUMAN, "surveyor corrected the boundary")
    status = project.wf.status()
    assert status.state is S.SITE_INGESTION
    assert status.approvals == {}
    assert len(status.superseded) == 3


def test_cannot_reopen_an_unapproved_gate(project):
    project.to_site_approved()
    with pytest.raises(TransitionNotAllowed, match="not approved"):
        project.wf.reopen(Gate.PLAN, HUMAN, "why")


# ------------------------------------------------------------- misc behaviour


def test_agents_may_request_approval(project):
    project.to_site_review()
    status = project.wf.request_approval(Gate.SITE, project.site, AGENT)
    event = project.store.events()[-1]
    assert event.actor == AGENT and status.blockers == []
    assert project.wf.status().pending_requests[Gate.SITE] == project.site
    project.wf.approve(Gate.SITE, project.site, HUMAN, "ok")
    assert project.wf.status().pending_requests == {}


def test_replay_rejects_an_out_of_sequence_log(project):
    project.to_site_review()
    events = project.store.events()
    bogus = events[-1].model_copy(
        update={
            "type": EventType.TRANSITION,
            "from_state": S.PLAN_REVIEW,
            "to_state": S.PLAN_APPROVED,
        }
    )
    with pytest.raises(WorkflowError, match="transition from"):
        replay([*events, bogus])


def test_revision_concept_loop_is_allowed(project):
    project.to_concept_review()
    project.wf.transition(S.PLAN_GENERATION, HUMAN, "I hate this option; start again")
    project.wf.transition(S.PLAN_REVIEW, AGENT, "new options ready")
    assert project.wf.status().approvals.keys() == {Gate.SITE, Gate.PROGRAM}


def test_contradiction_in_an_uncited_brief_still_blocks_the_program(project):
    brief = example_doc("design_brief.yaml")
    brief["contradictions"] = [
        {"id": "ct-2", "statement": "Budget vs area", "fact_ids": ["f-bedrooms", "f-single-storey"]}
    ]
    project.store.put(K.DESIGN_BRIEF, "brief", brief, AGENT)
    project.to_program_review()
    refusal = _refusal(lambda: project.wf.approve(Gate.PROGRAM, project.program, HUMAN, "ok"))
    assert refusal == [("contradiction", "ct-2")]


def test_agents_cannot_reopen_a_gate(project):
    project.to_site_approved()
    with pytest.raises(ApprovalRequiresHuman, match="cannot reopen"):
        project.wf.reopen(Gate.SITE, AGENT, "agent wants to reopen")


def test_program_gate_rejects_unknown_source_fact_ids(project):
    program = example_doc("space_program.yaml")
    program["items"][0]["source_fact_ids"] = ["f-nonexistent"]
    prog_ref = project.store.put(K.SPACE_PROGRAM, "program", program, AGENT)
    project.to_program_review()
    status = project.wf.gate_status(Gate.PROGRAM, prog_ref)
    assert _codes(status) == [("program_check", "unknown_fact")]
    assert status.blockers[0].subject_ids == ["f-nonexistent"]


def test_plan_gate_blocks_program_min_area_without_evaluation_report(project):
    doc = example_doc("plans/plan-a.json")
    doc["option_id"] = "plan-small-bath"
    bath = next(s for s in doc["model"]["spaces"] if s["id"] == "sp-bath")
    # Shrink sp-bath to 1.0 x 3.5 = 3.5 m² (program min_area_m2 is 6.0 m²)
    bath["boundary"]["outer"] = [[14, 18.5], [15, 18.5], [15, 22], [14, 22]]
    doc["model"]["fixtures"] = [
        fx for fx in doc["model"]["fixtures"] if fx["space_id"] != "sp-bath"
    ]
    small = project.store.put(K.PLAN, "plan-small-bath", doc, AGENT)
    project.to_concept_review()
    refusal = _refusal(lambda: project.wf.approve(Gate.PLAN, small, HUMAN, "approve"))
    assert ("integrity", "min_area_violation") in refusal

