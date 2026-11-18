"""Project status: what an agent reads first about a project (``project status --json``).

A view, so it lives here and not in the domain package. Blockers, staleness and
the next human action come from the gate status (ADR 0029); the site comes from
the one site summary the interview also reads. The command line renders the next
human action: this module never holds flag names, so :meth:`ProjectStatus.to_json`
takes the renderer from its caller.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from house_ai.domain.provenance import ArtifactKind, ArtifactRef
from house_ai.domain.workflow import Approval, Gate, ProjectManifest, WorkflowState
from house_ai.storage import ProjectStore

from .interview import InterviewService
from .site_context import SiteSummary
from .statements import owner_statements
from .workflow import GateStatus, NextHumanAction, Workflow


@dataclass(frozen=True)
class InterviewProgress:
    """How far the owner interview has come."""

    exists: bool
    status: str
    turn_count: int
    unconfirmed_slots: int

    def to_json(self) -> dict[str, Any]:
        return {
            "exists": self.exists,
            "status": self.status,
            "turn_count": self.turn_count,
            "unconfirmed_slots": self.unconfirmed_slots,
        }


@dataclass(frozen=True)
class ProjectStatus:
    manifest: ProjectManifest
    state: WorkflowState
    allowed_transitions: list[WorkflowState]
    #: The gate that can be approved from the current state, if any.
    gate_available: Gate | None
    #: Each current approval with its gate status (whether it is stale).
    approvals: dict[Gate, tuple[Approval, GateStatus]]
    #: The gate the project works towards now, for its pinned version.
    gate_status: GateStatus | None
    superseded: list[Approval]
    pending_requests: dict[Gate, ArtifactRef]
    latest_artifacts: dict[ArtifactKind, list[ArtifactRef]]
    site: SiteSummary
    owner_statements_count: int
    interview: InterviewProgress

    @property
    def next_action(self) -> NextHumanAction | None:
        return self.gate_status.next_action if self.gate_status else None

    @property
    def stale_approvals(self) -> list[Gate]:
        return sorted((g for g, (_, gs) in self.approvals.items() if gs.stale), key=str)

    def to_json(self, render: Callable[[NextHumanAction], str]) -> dict[str, Any]:
        """The one serialisation; ``render`` turns the next human action into a command."""
        approvals: dict[str, dict] = {}
        for gate, (approval, status) in self.approvals.items():
            data = approval.model_dump(mode="json")
            data["stale"] = status.stale
            if status.stale_against is not None:
                data["latest_version"] = status.stale_against.version
            approvals[gate.value] = data
        action = self.next_action
        return {
            "project": self.manifest.model_dump(mode="json"),
            "state": self.state.value,
            "allowed_transitions": [s.value for s in self.allowed_transitions],
            "gate_available": self.gate_available.value if self.gate_available else None,
            "approvals": approvals,
            "stale_approvals": [g.value for g in self.stale_approvals],
            "gate_status": self.gate_status.to_json() if self.gate_status else None,
            "next_human_command": render(action) if action else None,
            "superseded_approvals": [a.id for a in self.superseded],
            "pending_approval_requests": {
                g.value: r.model_dump(mode="json") for g, r in self.pending_requests.items()
            },
            "latest_artifacts": {
                kind.value: [r.model_dump(mode="json") for r in refs]
                for kind, refs in self.latest_artifacts.items()
            },
            "site": self.site.to_json() if self.site.exists else None,
            "owner_statements_count": self.owner_statements_count,
            "interview": self.interview.to_json(),
        }


def project_status(store: ProjectStore) -> ProjectStatus:
    """Read where the project stands; writes nothing."""
    wf = Workflow(store)
    status = wf.status()
    svc = InterviewService(store)
    latest: dict[ArtifactKind, list[ArtifactRef]] = {}
    for kind in ArtifactKind:
        if refs := store.latest_of_kind(kind):
            latest[kind] = list(refs)
    if svc.exists():
        session = svc.session()
        interview = InterviewProgress(True, session.status.value, len(session.turns),
                                      len(svc.state().unconfirmed()))  # fmt: skip
    else:
        interview = InterviewProgress(False, "not_started", 0, 0)
    return ProjectStatus(
        manifest=store.manifest(),
        state=status.state,
        allowed_transitions=wf.allowed_transitions(),
        gate_available=wf.gate_available(),
        approvals={g: (a, wf.gate_status(g, a.artifact)) for g, a in status.approvals.items()},
        gate_status=wf.current_gate_status(),
        superseded=list(status.superseded),
        pending_requests=dict(status.pending_requests),
        latest_artifacts=latest,
        site=svc.site_summary(),
        owner_statements_count=len(owner_statements(store)),
        interview=interview,
    )
