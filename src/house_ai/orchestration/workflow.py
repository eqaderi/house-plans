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
"""

from __future__ import annotations

from dataclasses import dataclass, field

from house_ai.domain.brief import DesignBrief
from house_ai.domain.build import BuildRecord, BuildTarget
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.integrity import check_model, errors
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, ArtifactRef
from house_ai.domain.records import OpenQuestionsFile
from house_ai.domain.site import Site, site_verification_blockers
from house_ai.domain.workflow import (
    GATE_ARTIFACT_KIND,
    Approval,
    EventType,
    Gate,
    WorkflowEvent,
    WorkflowState,
)
from house_ai.program.validation import blocking, validate_program
from house_ai.storage import ProjectStore, StoreError

from .site_context import site_context_for

S = WorkflowState

#: Ordinary (non-gate) transitions.
TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    S.NEW_PROJECT: frozenset({S.SITE_INGESTION}),
    S.SITE_INGESTION: frozenset({S.SITE_NEEDS_VERIFICATION}),
    S.SITE_NEEDS_VERIFICATION: frozenset({S.SITE_INGESTION}),
    S.SITE_APPROVED: frozenset({S.INTERVIEWING}),
    S.INTERVIEWING: frozenset({S.PROGRAM_REVIEW}),
    S.PROGRAM_REVIEW: frozenset({S.INTERVIEWING}),
    S.PROGRAM_APPROVED: frozenset({S.CONCEPT_GENERATION}),
    S.CONCEPT_GENERATION: frozenset({S.CONCEPT_REVIEW}),
    S.CONCEPT_REVIEW: frozenset({S.CONCEPT_GENERATION}),
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
    Gate.PLAN: GateSpec(Gate.PLAN, S.CONCEPT_REVIEW, S.PLAN_APPROVED, ArtifactKind.PLAN),
    Gate.MODEL: GateSpec(Gate.MODEL, S.BLENDER_REVIEW, S.MODEL_APPROVED, ArtifactKind.BUILD_RECORD),
}
assert all(spec.artifact_kind is GATE_ARTIFACT_KIND[g] for g, spec in GATES.items())

GATE_ORDER: list[Gate] = [Gate.SITE, Gate.PROGRAM, Gate.PLAN, Gate.MODEL]
STATE_ORDER: list[WorkflowState] = list(WorkflowState)


class WorkflowError(Exception):
    pass


class TransitionNotAllowed(WorkflowError):
    pass


class GateBlocked(WorkflowError):
    def __init__(self, gate: Gate, reasons: list[str]) -> None:
        self.gate = gate
        self.reasons = reasons
        super().__init__(f"{gate.value} gate blocked: " + "; ".join(reasons))


class ApprovalRequiresHuman(WorkflowError):
    pass


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
        if to is S.CONCEPT_REVIEW and not self.store.refs(ArtifactKind.PLAN):
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

    def assess_site(self, site_ref: ArtifactRef, actor: Actor) -> list[str]:
        """During site ingestion, stop at SITE_NEEDS_VERIFICATION if the site is ambiguous.

        Returns the blockers; an empty list means the site is ready for a human
        to review and approve.
        """
        if self.state is not S.SITE_INGESTION:
            raise TransitionNotAllowed(f"site assessment runs in SITE_INGESTION, not {self.state}")
        blockers = site_verification_blockers(self.store.get(site_ref, Site))
        if blockers:
            self.store.append_event(
                EventType.TRANSITION,
                actor,
                from_state=S.SITE_INGESTION,
                to_state=S.SITE_NEEDS_VERIFICATION,
                reason="site needs human verification before anything else",
                payload={"site": site_ref.model_dump(mode="json"), "blockers": blockers},
            )
        return blockers

    # ------------------------------------------------------------------ gates

    def check_gate(self, gate: Gate, ref: ArtifactRef) -> list[str]:
        """Every reason the gate cannot be approved for this artifact version now."""
        spec = GATES[gate]
        status = self.status()
        if status.state is not spec.review_state:
            return [
                f"the {gate.value} gate is approved from {spec.review_state.value}; "
                f"the project is in {status.state.value}"
            ]
        if ref.kind is not spec.artifact_kind:
            return [f"the {gate.value} gate approves a {spec.artifact_kind.value}, not {ref.kind}"]
        try:
            artifact = self.store.get(ref)
        except StoreError as exc:
            return [str(exc)]
        check = {
            Gate.SITE: self._check_site_gate,
            Gate.PROGRAM: self._check_program_gate,
            Gate.PLAN: self._check_plan_gate,
            Gate.MODEL: self._check_model_gate,
        }[gate]
        return check(artifact, ref, status)

    def _upstream(self, status: WorkflowStatus, *gates: Gate) -> list[str]:
        return [
            f"the {g.value} gate has no valid approval" for g in gates if g not in status.approvals
        ]

    def _check_site_gate(self, site: Site, ref: ArtifactRef, status: WorkflowStatus) -> list[str]:
        return site_verification_blockers(site)

    def _check_program_gate(
        self, program: SpaceProgram, ref: ArtifactRef, status: WorkflowStatus
    ) -> list[str]:
        reasons = self._upstream(status, Gate.SITE)
        for q_ref in self.store.latest_of_kind(ArtifactKind.OPEN_QUESTIONS):
            for q in self.store.get(q_ref, OpenQuestionsFile).blocking_open():
                reasons.append(f"blocking open question {q.id}: {q.question}")
        # The cited brief, or every stored brief's latest version if none is cited.
        brief_refs = (
            [program.brief_ref]
            if program.brief_ref
            else self.store.latest_of_kind(ArtifactKind.DESIGN_BRIEF)
        )
        known_facts: set[str] = set()
        loaded_any_brief = False
        for b_ref in brief_refs:
            try:
                brief = self.store.get(b_ref, DesignBrief)
            except StoreError as exc:
                reasons.append(f"program cites a brief that is not in the store: {exc}")
                continue
            loaded_any_brief = True
            known_facts.update(f.id for f in brief.facts)
            for c in brief.unresolved_contradictions():
                reasons.append(f"unresolved contradiction {c.id}: {c.statement}")
        if loaded_any_brief and len(brief_refs) == 1:
            site = None
            if Gate.SITE in status.approvals:
                site_ref = status.approvals[Gate.SITE].artifact
                site = site_context_for(
                    self.store.get(site_ref, Site), site_ref, status.approvals[Gate.SITE]
                )
            for finding in blocking(validate_program(program, brief, site)):
                if finding.code != "contradiction":  # reported above
                    reasons.append(f"program check {finding.code}: {finding.message}")
        if loaded_any_brief:
            for item in program.items:
                for fid in item.source_fact_ids:
                    if fid not in known_facts:
                        reasons.append(f"program item {item.id} cites unknown brief fact {fid!r}")
            for adj in program.adjacencies:
                for fid in adj.source_fact_ids:
                    if fid not in known_facts:
                        reasons.append(f"adjacency {adj.id} cites unknown brief fact {fid!r}")
        return reasons

    def _check_plan_gate(
        self, plan: PlanVersion, ref: ArtifactRef, status: WorkflowStatus
    ) -> list[str]:
        reasons = self._upstream(status, Gate.SITE, Gate.PROGRAM)
        if reasons:
            return reasons
        site_approval = status.approvals[Gate.SITE]
        program_approval = status.approvals[Gate.PROGRAM]
        if not _same(site_approval.artifact, plan.model.site_ref):
            reasons.append("plan is not drawn on the approved site version")
        if not _same(program_approval.artifact, plan.model.program_ref):
            reasons.append("plan is not derived from the approved program version")
        site = self.store.get(site_approval.artifact, Site)
        program = self.store.get(program_approval.artifact, SpaceProgram)
        for finding in errors(check_model(plan.model, site, program)):
            reasons.append(f"integrity {finding.code}: {finding.message}")
        latest_for_plan: dict[str, EvaluationReport] = {}
        for e_ref in self.store.refs(ArtifactKind.EVALUATION_REPORT):
            report = self.store.get(e_ref, EvaluationReport)
            if _same(report.plan_ref, ref):
                latest_for_plan[report.id] = report
        for report in latest_for_plan.values():
            for v in report.hard_violations:
                reasons.append(f"hard violation {v.id} ({report.id}): {v.message}")
        return reasons

    def _check_model_gate(
        self, record: BuildRecord, ref: ArtifactRef, status: WorkflowStatus
    ) -> list[str]:
        reasons = self._upstream(status, Gate.PLAN)
        if reasons:
            return reasons
        if record.target is not BuildTarget.BLENDER:
            reasons.append(f"the model gate approves a Blender build, not {record.target.value}")
        if not _same(record.input_plan, status.approvals[Gate.PLAN].artifact):
            reasons.append("build was not generated from the approved plan version")
        return reasons

    def request_approval(self, gate: Gate, ref: ArtifactRef, actor: Actor) -> WorkflowEvent:
        """Ask a human to review; anyone (including an agent) may do this."""
        reasons = self.check_gate(gate, ref)
        return self.store.append_event(
            EventType.APPROVAL_REQUESTED,
            actor,
            reason=f"{gate.value} ready for human review" if not reasons else "review requested",
            payload={
                "gate": gate.value,
                "artifact": ref.model_dump(mode="json"),
                "open_reasons": reasons,
            },
        )

    def approve(
        self,
        gate: Gate,
        ref: ArtifactRef,
        approver: Actor,
        statement: str,
        conditions: list[str] | None = None,
    ) -> Approval:
        if approver.kind is not ActorKind.HUMAN:
            raise ApprovalRequiresHuman(
                f"{approver.kind.value} {approver.id!r} cannot approve the {gate.value} gate; "
                "only a human can"
            )
        reasons = self.check_gate(gate, ref)
        if reasons:
            raise GateBlocked(gate, reasons)
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
        if actor.kind is not ActorKind.HUMAN:
            raise ApprovalRequiresHuman(
                f"{actor.kind.value} {actor.id!r} cannot reopen the {gate.value} gate; "
                "only a human can supersede a human approval"
            )
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

