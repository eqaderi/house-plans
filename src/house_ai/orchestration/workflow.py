"""Workflow state machine with explicit human approval gates.

State is never stored; it is replayed from the project's event log, so the
log is the single source of truth (ADR 0003).

Two kinds of moves exist:

* ``transition``: an ordinary step along the table below. Agents and humans
  may request it; some steps have guards (e.g. a program must exist before
  program review).
* ``approve``: crosses one of the four gates (site, program, plan, model).
  Only a human actor can approve, the approval pins the exact artifact
  version by content hash, and the gate's deterministic checks are re-run
  on that artifact at approval time.

``reopen`` steps back to a gate's review state and supersedes that gate's
approval and every approval downstream of it.

:meth:`Workflow.gate_status` says where a gate stands for one pinned artifact
version: its typed Blockers and attention items (ADR 0029).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from house_ai.constants.evaluations import PLAN_GATE_BLOCKING_CODES, PLAN_REVIEW_ATTENTION_CODES
from house_ai.domain.brief import DesignBrief
from house_ai.domain.build import BuildRecord, BuildTarget
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.integrity import check_model, errors
from house_ai.domain.interview import slot_fact_id
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram, Strength
from house_ai.domain.provenance import Actor, ArtifactKind, ArtifactRef, refuse_non_human
from house_ai.domain.records import OpenQuestionsFile
from house_ai.domain.site import Site, site_blockers
from house_ai.domain.workflow import (
    GATE_ARTIFACT_KIND,
    Approval,
    Blocker,
    BlockerKind,
    EventType,
    Gate,
    WorkflowEvent,
    WorkflowState,
)
from house_ai.program.validation import ProgramFinding, blocking, validate_program
from house_ai.storage import ProjectStore, StoreError

from .site_context import site_context_for

S = WorkflowState

#: Ordinary (non-gate) transitions. PROGRAM_REVIEW has none: leaving it backwards is the
#: Owner's ``program reject`` (``InterviewService.reject_program``, ADR 0029), never a
#: transition, and forwards is the program gate.
TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    S.NEW_PROJECT: frozenset({S.SITE_INGESTION}),
    S.SITE_INGESTION: frozenset({S.SITE_NEEDS_CONFIRMATION}),
    S.SITE_NEEDS_CONFIRMATION: frozenset({S.SITE_INGESTION}),
    S.SITE_APPROVED: frozenset({S.INTERVIEWING}),
    S.INTERVIEWING: frozenset({S.PROGRAM_REVIEW}),
    S.PROGRAM_APPROVED: frozenset({S.PLAN_GENERATION}),
    S.PLAN_GENERATION: frozenset({S.PLAN_REVIEW}),
    S.PLAN_REVIEW: frozenset({S.PLAN_GENERATION}),
    S.PLAN_APPROVED: frozenset({S.BLENDER_BUILD}),
    S.BLENDER_BUILD: frozenset({S.BLENDER_REVIEW}),
    S.BLENDER_REVIEW: frozenset({S.BLENDER_BUILD}),
    S.MODEL_APPROVED: frozenset({S.UNREAL_BUILD}),
    S.UNREAL_BUILD: frozenset({S.UNREAL_REVIEW}),
    S.UNREAL_REVIEW: frozenset({S.UNREAL_BUILD}),
}


@dataclass(frozen=True)
class GateSpec:
    gate: Gate
    review_state: WorkflowState
    approved_state: WorkflowState
    artifact_kind: ArtifactKind


GATES: dict[Gate, GateSpec] = {
    Gate.SITE: GateSpec(Gate.SITE, S.SITE_INGESTION, S.SITE_APPROVED, ArtifactKind.SITE),
    Gate.PROGRAM: GateSpec(
        Gate.PROGRAM, S.PROGRAM_REVIEW, S.PROGRAM_APPROVED, ArtifactKind.SPACE_PROGRAM
    ),
    Gate.PLAN: GateSpec(Gate.PLAN, S.PLAN_REVIEW, S.PLAN_APPROVED, ArtifactKind.PLAN),
    Gate.MODEL: GateSpec(Gate.MODEL, S.BLENDER_REVIEW, S.MODEL_APPROVED, ArtifactKind.BUILD_RECORD),
}
assert all(spec.artifact_kind is GATE_ARTIFACT_KIND[g] for g, spec in GATES.items())

GATE_ORDER: list[Gate] = [Gate.SITE, Gate.PROGRAM, Gate.PLAN, Gate.MODEL]
STATE_ORDER: list[WorkflowState] = list(WorkflowState)


class HumanAction(StrEnum):
    """What only a human can do next (agent contract §8)."""

    APPROVE = "approve"
    CONFIRM_SITE = "confirm_site"
    REOPEN = "reopen"
    REJECT_PROGRAM = "reject_program"


@dataclass(frozen=True)
class NextHumanAction:
    """The next thing a human must do at a gate, without any command syntax (ADR 0029).

    The CLI renders it as a command line (``house_ai.cli.human.command_for``);
    orchestration never holds flag names. ``artifact_id`` and ``version`` are
    ``None`` when the caller does not know which version (a template).
    """

    action: HumanAction
    gate: Gate
    artifact_id: str | None = None
    version: int | None = None
    #: For a site confirmation: the site Blockers the confirmation must clear.
    clears: tuple[Blocker, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "gate": self.gate.value,
            "artifact_id": self.artifact_id,
            "version": self.version,
            "clears": [b.model_dump(mode="json") for b in self.clears],
        }


class WorkflowError(Exception):
    def __init__(self, *args: object, next_action: NextHumanAction | None = None) -> None:
        super().__init__(*args)
        #: What a human can do about the refusal, when only a human can.
        self.next_action = next_action


class TransitionNotAllowed(WorkflowError):
    pass


class UseProgramReject(TransitionNotAllowed):
    """Leaving PROGRAM_REVIEW for INTERVIEWING undoes a program review: only the
    Owner's ``program reject`` does that, for every actor (ADR 0029)."""

    def __init__(self) -> None:
        super().__init__(
            "leaving PROGRAM_REVIEW for INTERVIEWING undoes the program review; only the "
            "owner's program reject, in their own terminal, does that",
            next_action=NextHumanAction(HumanAction.REJECT_PROGRAM, Gate.PROGRAM),
        )


class GateBlocked(WorkflowError):
    def __init__(self, gate: Gate, blockers: list[Blocker]) -> None:
        self.gate = gate
        self.blockers = blockers
        self.reasons = [b.message for b in blockers]
        super().__init__(f"{gate.value} gate blocked: " + "; ".join(self.reasons))


@dataclass(frozen=True)
class GateStatus:
    """Where one gate stands for one pinned artifact version (ADR 0029)."""

    gate: Gate
    artifact: ArtifactRef
    #: Whether the project is in the state this gate is approved from.
    in_review_state: bool
    #: Every reason the gate cannot be approved for this version now.
    blockers: list[Blocker]
    #: Findings the Approver should see that do not block (plan gate, ADR 0024).
    attention: list[str]
    #: The gate's current approval, if any (whatever version it pins).
    approval: Approval | None = None
    #: The newer version of the approved artifact, when the approval is stale.
    stale_against: ArtifactRef | None = None
    #: What a human does next at this gate, if anything: approve this version
    #: when nothing blocks it, or confirm the site facts that block the site gate.
    next_action: NextHumanAction | None = None

    @property
    def stale(self) -> bool:
        """An approval exists and a newer version of what it approved has been written."""
        return self.stale_against is not None

    @property
    def open_reasons(self) -> list[str]:
        """The Blockers as the sentences saved in the approval-requested event."""
        return [b.message for b in self.blockers]

    @property
    def approvable(self) -> bool:
        return self.in_review_state and not self.blockers

    def to_json(self) -> dict[str, Any]:
        return {
            "gate": self.gate.value,
            "artifact": self.artifact.model_dump(mode="json"),
            "in_review_state": self.in_review_state,
            "approvable": self.approvable,
            "open_reasons": self.open_reasons,
            "blockers": [b.model_dump(mode="json") for b in self.blockers],
            "attention": list(self.attention),
            "stale": self.stale,
            "stale_against": (
                self.stale_against.model_dump(mode="json") if self.stale_against else None
            ),
            "next_action": self.next_action.to_json() if self.next_action else None,
        }


def _blocker(kind: BlockerKind, code: str, message: str, *subject_ids: str) -> Blocker:
    return Blocker(kind=kind, code=code, subject_ids=list(subject_ids), message=message)


def _program_check_blockers(finding: ProgramFinding, asked: set[str]) -> list[Blocker]:
    """The Blocker for one blocking program check, unless an Open question covers it."""
    if finding.code == "missing_information" and set(finding.subject_ids) <= asked:
        return []  # its blocking Open question is the Blocker
    if finding.code == "contradiction":
        cid = finding.subject_ids[0]
        message = f"unresolved contradiction {cid}: {finding.message}"
        return [_blocker(BlockerKind.CONTRADICTION, cid, message, *finding.subject_ids)]
    message = f"program check {finding.code}: {finding.message}"
    return [_blocker(BlockerKind.PROGRAM_CHECK, finding.code, message, *finding.subject_ids)]


def _uncited_brief_blockers(program: SpaceProgram, briefs: list[DesignBrief]) -> list[Blocker]:
    """Contradictions and unknown fact ids across several briefs, none cited by the program."""
    out = [
        _blocker(
            BlockerKind.CONTRADICTION, c.id, f"unresolved contradiction {c.id}: {c.statement}", c.id
        )
        for brief in briefs
        for c in brief.unresolved_contradictions()
    ]
    known = {f.id for brief in briefs for f in brief.facts}
    cited = [*program.space_requirements, *program.space_relationships]
    unknown = sorted({fid for item in cited for fid in item.source_fact_ids} - known)
    if unknown:
        message = f"program check unknown_fact: the program cites facts in no brief: {unknown}"
        out.append(_blocker(BlockerKind.PROGRAM_CHECK, "unknown_fact", message, *unknown))
    return out


@dataclass
class WorkflowStatus:
    state: WorkflowState
    approvals: dict[Gate, Approval] = field(default_factory=dict)
    superseded: list[Approval] = field(default_factory=list)
    pending_requests: dict[Gate, ArtifactRef] = field(default_factory=dict)


def replay(events: list[WorkflowEvent]) -> WorkflowStatus:
    """Fold the event log into the current workflow status."""
    if not events or events[0].type is not EventType.PROJECT_CREATED:
        raise WorkflowError("event log must start with project_created")
    status = WorkflowStatus(state=S.NEW_PROJECT)
    for ev in events[1:]:
        if ev.type is EventType.TRANSITION:
            if ev.from_state is not status.state or ev.to_state is None:
                raise WorkflowError(
                    f"event {ev.seq}: transition from {ev.from_state} but state was {status.state}"
                )
            status.state = ev.to_state
        elif ev.type is EventType.APPROVAL_REQUESTED:
            status.pending_requests[Gate(ev.payload["gate"])] = ArtifactRef.model_validate(
                ev.payload["artifact"]
            )
        elif ev.type is EventType.APPROVAL_GRANTED:
            approval = Approval.model_validate(ev.payload["approval"])
            spec = GATES[approval.gate]
            if status.state is not spec.review_state or ev.to_state is not spec.approved_state:
                raise WorkflowError(f"event {ev.seq}: approval out of sequence")
            status.approvals[approval.gate] = approval
            status.pending_requests.pop(approval.gate, None)
            status.state = spec.approved_state
        elif ev.type is EventType.GATE_REOPENED:
            gate = Gate(ev.payload["gate"])
            for g in GATE_ORDER[GATE_ORDER.index(gate) :]:
                if g in status.approvals:
                    status.superseded.append(status.approvals.pop(g))
                status.pending_requests.pop(g, None)
            status.state = GATES[gate].review_state
    return status


def _same(a: ArtifactRef, b: ArtifactRef | None) -> bool:
    return b is not None and a.model_dump() == b.model_dump()


class Workflow:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store

    # ----------------------------------------------------------------- status

    def status(self) -> WorkflowStatus:
        return replay(self.store.events())

    @property
    def state(self) -> WorkflowState:
        return self.status().state

    def allowed_transitions(self) -> list[WorkflowState]:
        return sorted(TRANSITIONS.get(self.state, frozenset()), key=STATE_ORDER.index)

    def gate_available(self) -> Gate | None:
        """The gate that can be approved from the current state, if any."""
        state = self.state
        return next((g for g, spec in GATES.items() if spec.review_state is state), None)

    # ------------------------------------------------------------ transitions

    def transition(self, to: WorkflowState, actor: Actor, reason: str) -> WorkflowEvent:
        current = self.state
        if any(spec.approved_state is to for spec in GATES.values()):
            raise TransitionNotAllowed(
                f"{to.value} is behind an approval gate; it can only be reached by a human "
                "approval (approve), never by a transition"
            )
        if current is S.PROGRAM_REVIEW and to is S.INTERVIEWING:
            raise UseProgramReject()
        if to not in TRANSITIONS.get(current, frozenset()):
            allowed = ", ".join(s.value for s in self.allowed_transitions()) or "none"
            raise TransitionNotAllowed(
                f"cannot go from {current.value} to {to.value}; allowed: {allowed}"
            )
        if not reason.strip():
            raise TransitionNotAllowed("a transition needs a reason")
        problems = self._transition_guard(current, to)
        if problems:
            raise TransitionNotAllowed(f"{current.value} -> {to.value}: " + "; ".join(problems))
        return self.store.append_event(
            EventType.TRANSITION, actor, from_state=current, to_state=to, reason=reason
        )

    def _transition_guard(self, current: WorkflowState, to: WorkflowState) -> list[str]:
        if to is S.PROGRAM_REVIEW and not self.store.refs(ArtifactKind.SPACE_PROGRAM):
            return ["no space program has been written yet"]
        if to is S.PLAN_REVIEW and not self.store.refs(ArtifactKind.PLAN):
            return ["no plan has been written yet"]
        if to in (S.BLENDER_REVIEW, S.UNREAL_REVIEW):
            target = BuildTarget.BLENDER if to is S.BLENDER_REVIEW else BuildTarget.UNREAL
            plan = self.status().approvals.get(Gate.PLAN)
            for ref in self.store.latest_of_kind(ArtifactKind.BUILD_RECORD):
                rec = self.store.get(ref, BuildRecord)
                if rec.target is target and plan and _same(rec.input_plan, plan.artifact):
                    return []
            return [f"no {target.value} build record generated from the approved plan"]
        return []

    # ------------------------------------------------------------------ gates

    def gate_status(self, gate: Gate, ref: ArtifactRef) -> GateStatus:
        """Where ``gate`` stands for one pinned artifact version now (ADR 0029)."""
        status = self.status()
        approval = status.approvals.get(gate)
        in_review = status.state is GATES[gate].review_state
        blockers = self._blockers(gate, ref, status)
        return GateStatus(
            gate=gate,
            artifact=ref,
            in_review_state=in_review,
            blockers=blockers,
            attention=self._plan_attention(ref) if gate is Gate.PLAN else [],
            approval=approval,
            stale_against=self._newer_than(approval) if approval else None,
            next_action=self._next_action(gate, ref, status, in_review and not blockers),
        )

    def current_gate_status(self) -> GateStatus | None:
        """The gate the project is working towards now, for its pinned version.

        The site gate while the site is ingested or needs confirmation; else the
        gate approved from the current state. The pinned version is the one a
        review was requested for, or the newest version when only one artifact
        of the gate's kind exists. ``None`` when there is no such gate or version.
        """
        status = self.status()
        if status.state in (S.SITE_INGESTION, S.SITE_NEEDS_CONFIRMATION):
            gate: Gate | None = Gate.SITE
        else:
            gate = next((g for g, s in GATES.items() if s.review_state is status.state), None)
        if gate is None:
            return None
        ref = status.pending_requests.get(gate)
        if ref is None:
            latest = self.store.latest_of_kind(GATES[gate].artifact_kind)
            ref = latest[0] if len(latest) == 1 else None
        return self.gate_status(gate, ref) if ref is not None else None

    def _next_action(
        self, gate: Gate, ref: ArtifactRef, status: WorkflowStatus, approvable: bool
    ) -> NextHumanAction | None:
        if approvable:
            return NextHumanAction(HumanAction.APPROVE, gate, ref.id, ref.version)
        site_states = (S.SITE_INGESTION, S.SITE_NEEDS_CONFIRMATION)
        if gate is Gate.SITE and status.state in site_states and ref.kind is ArtifactKind.SITE:
            try:
                clears = site_blockers(self.store.get(ref, Site))
            except StoreError:
                return None
            if clears:
                return NextHumanAction(HumanAction.CONFIRM_SITE, gate, ref.id, clears=tuple(clears))
        return None

    def _newer_than(self, approval: Approval) -> ArtifactRef | None:
        """The latest version of the approved artifact, if it is not the approved one."""
        latest = self.store.latest(GATES[approval.gate].artifact_kind, approval.artifact.id)
        approved = approval.artifact
        if latest and (latest.version > approved.version or latest.sha256 != approved.sha256):
            return latest
        return None

    def _blockers(self, gate: Gate, ref: ArtifactRef, status: WorkflowStatus) -> list[Blocker]:
        """Every reason the gate cannot be approved for this artifact version now."""
        spec = GATES[gate]
        if status.state is not spec.review_state:
            return [
                _blocker(
                    BlockerKind.WORKFLOW_STATE,
                    "wrong_state",
                    f"the {gate.value} gate is approved from {spec.review_state.value}; "
                    f"the project is in {status.state.value}",
                )
            ]
        if ref.kind is not spec.artifact_kind:
            return [
                _blocker(
                    BlockerKind.ARTIFACT,
                    "wrong_kind",
                    f"the {gate.value} gate approves a {spec.artifact_kind.value}, not {ref.kind}",
                    ref.id,
                )
            ]
        try:
            artifact = self.store.get(ref)
        except StoreError as exc:
            return [_blocker(BlockerKind.ARTIFACT, "not_in_store", str(exc), ref.id)]
        check = {
            Gate.SITE: self._check_site_gate,
            Gate.PROGRAM: self._check_program_gate,
            Gate.PLAN: self._check_plan_gate,
            Gate.MODEL: self._check_model_gate,
        }[gate]
        return check(artifact, ref, status)

    def _upstream(self, status: WorkflowStatus, *gates: Gate) -> list[Blocker]:
        return [
            _blocker(
                BlockerKind.UPSTREAM_GATE, g.value, f"the {g.value} gate has no valid approval"
            )
            for g in gates
            if g not in status.approvals
        ]

    def _check_site_gate(
        self, site: Site, ref: ArtifactRef, status: WorkflowStatus
    ) -> list[Blocker]:
        return site_blockers(site)

    def _check_program_gate(
        self, program: SpaceProgram, ref: ArtifactRef, status: WorkflowStatus
    ) -> list[Blocker]:
        """One cause, one Blocker (ADR 0029).

        The program checks are the one source; the gate adds what they do not
        cover: the site gate's approval, blocking Open questions (a missing
        blocking answer is its Open question, not also the check's
        ``missing_information``), and a brief the program cites but the store
        lacks. With several stored briefs and none cited, the checks cannot
        run, and the gate reports each brief's Contradictions and unknown fact
        ids itself.
        """
        blockers = self._upstream(status, Gate.SITE)
        asked: set[str] = set()  # fact ids a blocking Open question already stands for
        for q_ref in self.store.latest_of_kind(ArtifactKind.OPEN_QUESTIONS):
            for q in self.store.get(q_ref, OpenQuestionsFile).blocking_open():
                if q.topic:
                    asked.add(slot_fact_id(q.topic))
                blockers.append(
                    _blocker(
                        BlockerKind.OPEN_QUESTION,
                        q.id,
                        f"blocking open question {q.id}: {q.question}",
                        q.id,
                    )
                )
        # The cited brief, or every stored brief's latest version if none is cited.
        brief_refs = (
            [program.brief_ref]
            if program.brief_ref
            else self.store.latest_of_kind(ArtifactKind.DESIGN_BRIEF)
        )
        briefs: list[DesignBrief] = []
        for b_ref in brief_refs:
            try:
                briefs.append(self.store.get(b_ref, DesignBrief))
            except StoreError as exc:
                blockers.append(
                    _blocker(
                        BlockerKind.ARTIFACT,
                        "brief_not_in_store",
                        f"program cites a brief that is not in the store: {exc}",
                        b_ref.id,
                    )
                )
        if len(brief_refs) == 1 and briefs:
            site = None
            if Gate.SITE in status.approvals:
                site_ref = status.approvals[Gate.SITE].artifact
                site = site_context_for(
                    self.store.get(site_ref, Site), site_ref, status.approvals[Gate.SITE]
                )
            for finding in blocking(validate_program(program, briefs[0], site)):
                blockers += _program_check_blockers(finding, asked)
        elif briefs:
            blockers += _uncited_brief_blockers(program, briefs)
        return blockers

    def _check_plan_gate(
        self, plan: PlanVersion, ref: ArtifactRef, status: WorkflowStatus
    ) -> list[Blocker]:
        blockers = self._upstream(status, Gate.SITE, Gate.PROGRAM)
        if blockers:
            return blockers
        site_approval = status.approvals[Gate.SITE]
        program_approval = status.approvals[Gate.PROGRAM]
        if not _same(site_approval.artifact, plan.model.site_ref):
            blockers.append(
                _blocker(
                    BlockerKind.PINNED_INPUT,
                    "site_version",
                    "plan is not drawn on the approved site version",
                    site_approval.artifact.id,
                )
            )
        if not _same(program_approval.artifact, plan.model.program_ref):
            blockers.append(
                _blocker(
                    BlockerKind.PINNED_INPUT,
                    "program_version",
                    "plan is not derived from the approved program version",
                    program_approval.artifact.id,
                )
            )
        site = self.store.get(site_approval.artifact, Site)
        program = self.store.get(program_approval.artifact, SpaceProgram)
        for finding in errors(check_model(plan.model, site, program)):
            blockers.append(
                _blocker(
                    BlockerKind.INTEGRITY,
                    finding.code,
                    f"integrity {finding.code}: {finding.message}",
                    *finding.subject_ids,
                )
            )
        for report in self._evaluations_of(ref):
            for v in report.hard_violations:
                blockers.append(
                    _blocker(
                        BlockerKind.HARD_VIOLATION,
                        v.code,
                        f"hard violation {v.id} ({report.id}): {v.message}",
                        *v.subject_ids,
                    )
                )
            for v in report.violations:
                # Unbuildable or unwalkable as drawn, whatever its strength (ADR 0024).
                if v.strength is not Strength.HARD and v.code in PLAN_GATE_BLOCKING_CODES:
                    blockers.append(
                        _blocker(
                            BlockerKind.UNBUILDABLE,
                            v.code,
                            f"unbuildable {v.code} ({report.id}): {v.message}",
                            *v.subject_ids,
                        )
                    )
        return blockers

    def _evaluations_of(self, ref: ArtifactRef) -> list[EvaluationReport]:
        """The newest version of each Evaluation of this plan version."""
        latest_for_plan: dict[str, EvaluationReport] = {}
        for e_ref in self.store.refs(ArtifactKind.EVALUATION_REPORT):
            report = self.store.get(e_ref, EvaluationReport)
            if _same(report.plan_ref, ref):
                latest_for_plan[report.id] = report
        return list(latest_for_plan.values())

    def _plan_attention(self, ref: ArtifactRef) -> list[str]:
        """Findings the owner should see at plan review that do not block it (ADR 0024)."""
        out = []
        for e_ref in self.store.refs(ArtifactKind.EVALUATION_REPORT):
            report = self.store.get(e_ref, EvaluationReport)
            if not _same(report.plan_ref, ref):
                continue
            for v in report.violations:
                if v.strength is not Strength.HARD and v.code in PLAN_REVIEW_ATTENTION_CODES:
                    out.append(f"{v.code} ({report.id}): {v.message}")
        return sorted(set(out))

    def _check_model_gate(
        self, record: BuildRecord, ref: ArtifactRef, status: WorkflowStatus
    ) -> list[Blocker]:
        blockers = self._upstream(status, Gate.PLAN)
        if blockers:
            return blockers
        if record.target is not BuildTarget.BLENDER:
            blockers.append(
                _blocker(
                    BlockerKind.PINNED_INPUT,
                    "build_target",
                    f"the model gate approves a Blender build, not {record.target.value}",
                    ref.id,
                )
            )
        plan_approval = status.approvals[Gate.PLAN]
        if not _same(record.input_plan, plan_approval.artifact):
            blockers.append(
                _blocker(
                    BlockerKind.PINNED_INPUT,
                    "plan_version",
                    "build was not generated from the approved plan version",
                    plan_approval.artifact.id,
                )
            )
        return blockers

    def request_approval(self, gate: Gate, ref: ArtifactRef, actor: Actor) -> GateStatus:
        """Ask a human to review; anyone (including an agent) may do this.

        The event keeps its saved shape (ADR 0003): ``open_reasons`` are the
        Blockers' messages, and a plan request adds ``attention``.
        """
        gate_status = self.gate_status(gate, ref)
        reasons = gate_status.open_reasons
        payload: dict[str, Any] = {
            "gate": gate.value,
            "artifact": ref.model_dump(mode="json"),
            "open_reasons": reasons,
        }
        if gate is Gate.PLAN:
            payload["attention"] = gate_status.attention
        self.store.append_event(
            EventType.APPROVAL_REQUESTED,
            actor,
            reason=f"{gate.value} ready for human review" if not reasons else "review requested",
            payload=payload,
        )
        return gate_status

    def approve(
        self,
        gate: Gate,
        ref: ArtifactRef,
        approver: Actor,
        statement: str,
        conditions: list[str] | None = None,
    ) -> Approval:
        refuse_non_human(approver, f"approve the {gate.value} gate")
        blockers = self.gate_status(gate, ref).blockers
        if blockers:
            raise GateBlocked(gate, blockers)
        spec = GATES[gate]
        seq = len(self.store.events()) + 1
        approval = Approval(
            id=f"approval-{gate.value}-{seq}",
            gate=gate,
            artifact=ref,
            approved_by=approver,
            approved_at=self.store.clock(),
            statement=statement,
            conditions=conditions or [],
        )
        self.store.append_event(
            EventType.APPROVAL_GRANTED,
            approver,
            from_state=spec.review_state,
            to_state=spec.approved_state,
            reason=statement,
            payload={"approval": approval.model_dump(mode="json")},
        )
        return approval

    def reopen(self, gate: Gate, actor: Actor, reason: str) -> WorkflowEvent:
        """Go back to a gate's review state; supersede it and every later approval."""
        refuse_non_human(actor, f"reopen the {gate.value} gate")
        status = self.status()
        if gate not in status.approvals:
            raise TransitionNotAllowed(f"the {gate.value} gate is not approved; nothing to reopen")
        if not reason.strip():
            raise TransitionNotAllowed("reopening a gate needs a reason")
        return self.store.append_event(
            EventType.GATE_REOPENED,
            actor,
            from_state=status.state,
            to_state=GATES[gate].review_state,
            reason=reason,
            payload={"gate": gate.value},
        )
