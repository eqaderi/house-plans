"""Workflow states, gates, approvals and the append-only event record.

The state machine logic lives in ``house_ai.orchestration.workflow``; this
module only defines the data so it can be exported as JSON Schema.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, PrivateAttr, model_serializer, model_validator

from .base import SCHEMA_VERSION, Id, Sha256, StrictModel, UtcDatetime
from .provenance import Actor, ActorKind, ArtifactKind, ArtifactRef, DataClassification


class WorkflowState(StrEnum):
    NEW_PROJECT = "NEW_PROJECT"
    SITE_INGESTION = "SITE_INGESTION"
    #: Awaiting the owner's confirmation of site facts and the site gate.
    SITE_NEEDS_CONFIRMATION = "SITE_NEEDS_CONFIRMATION"
    SITE_APPROVED = "SITE_APPROVED"
    INTERVIEWING = "INTERVIEWING"
    PROGRAM_REVIEW = "PROGRAM_REVIEW"
    PROGRAM_APPROVED = "PROGRAM_APPROVED"
    PLAN_GENERATION = "PLAN_GENERATION"
    PLAN_REVIEW = "PLAN_REVIEW"
    PLAN_APPROVED = "PLAN_APPROVED"
    BLENDER_BUILD = "BLENDER_BUILD"
    BLENDER_REVIEW = "BLENDER_REVIEW"
    MODEL_APPROVED = "MODEL_APPROVED"
    UNREAL_BUILD = "UNREAL_BUILD"
    UNREAL_REVIEW = "UNREAL_REVIEW"

    @classmethod
    def _missing_(cls, value: object) -> WorkflowState | None:
        """Accept state names saved before ADR 0025."""
        new = RENAMED_STATES.get(value) if isinstance(value, str) else None
        return cls(new) if new else None


#: ADR 0025: state names saved before the glossary rename -> current names.
RENAMED_STATES: dict[str, str] = {
    "SITE_NEEDS_VERIFICATION": "SITE_NEEDS_CONFIRMATION",
    "CONCEPT_GENERATION": "PLAN_GENERATION",
    "CONCEPT_REVIEW": "PLAN_REVIEW",
}


class Gate(StrEnum):
    """The four things a human must explicitly approve."""

    SITE = "site"
    PROGRAM = "program"
    PLAN = "plan"
    MODEL = "model"


#: Which artifact kind each gate approves.
GATE_ARTIFACT_KIND: dict[Gate, ArtifactKind] = {
    Gate.SITE: ArtifactKind.SITE,
    Gate.PROGRAM: ArtifactKind.SPACE_PROGRAM,
    Gate.PLAN: ArtifactKind.PLAN,
    Gate.MODEL: ArtifactKind.BUILD_RECORD,
}


class Approval(StrictModel):
    id: Id
    gate: Gate
    artifact: ArtifactRef
    approved_by: Actor
    approved_at: UtcDatetime
    #: What the human attested to, in their words or as confirmed by them.
    statement: str = Field(min_length=1)
    conditions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _human_and_right_kind(self) -> Approval:
        if self.approved_by.kind is not ActorKind.HUMAN:
            raise ValueError("only a human can approve a gate")
        expected = GATE_ARTIFACT_KIND[self.gate]
        if self.artifact.kind is not expected:
            raise ValueError(
                f"the {self.gate.value} gate approves {expected.value}, "
                f"not {self.artifact.kind.value}"
            )
        return self


class EventType(StrEnum):
    PROJECT_CREATED = "project_created"
    SOURCE_ADDED = "source_added"
    ARTIFACT_WRITTEN = "artifact_written"
    TRANSITION = "transition"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    GATE_REOPENED = "gate_reopened"


class WorkflowEvent(StrictModel):
    """One line of events.jsonl. ``hash`` chains each event to the previous one.

    An event saved with an old state name (ADR 0025) reads as the current state
    and is written back with the name it was saved with, so its hash holds.
    """

    seq: int = Field(ge=1)
    at: UtcDatetime
    actor: Actor
    type: EventType
    from_state: WorkflowState | None = None
    to_state: WorkflowState | None = None
    reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    prev_hash: Sha256 | None = None
    hash: Sha256

    #: Field -> old state name this event was saved with.
    _old_states: dict[str, str] = PrivateAttr(default_factory=dict)

    @model_validator(mode="wrap")
    @classmethod
    def _accept_old_states(cls, data: Any, handler: Any) -> Any:
        event = handler(data)
        if isinstance(data, dict):
            event._old_states = {
                f: data[f] for f in ("from_state", "to_state") if data.get(f) in RENAMED_STATES
            }
        return event

    @model_serializer(mode="wrap")
    def _write_old_states(self, handler: Any) -> dict[str, Any]:
        data = handler(self)
        for field, old in self._old_states.items():
            if field in data:
                data[field] = old
        return data


class ProjectManifest(StrictModel):
    """project.json: identity only. Workflow state is replayed from events.jsonl."""

    schema_version: str = SCHEMA_VERSION
    id: Id
    name: str = Field(min_length=1)
    description: str | None = None
    classification: DataClassification
    created_at: UtcDatetime
    created_by: Actor
