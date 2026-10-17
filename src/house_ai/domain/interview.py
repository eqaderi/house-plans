"""Interview session state (interview_session artifact, ADR 0008).

The session is the record of the conversation: every question shown, the
owner's words verbatim, what the system understood from them, and every
confirmation, rejection, revision and resolution. The design brief is derived
from it; nothing in the brief exists that a turn does not explain.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, StrictModel, UtcDatetime
from .brief import FactValue
from .provenance import Actor, ActorKind, ArtifactRef, Provenance


class TurnKind(StrEnum):
    #: The owner answered the pending question.
    ANSWER = "answer"
    #: The owner changed an earlier answer.
    REVISION = "revision"
    #: The owner confirmed what the system understood.
    CONFIRMATION = "confirmation"
    #: The owner said an interpretation is wrong.
    REJECTION = "rejection"
    #: The owner chose how to resolve a contradiction.
    RESOLUTION = "resolution"
    #: The owner allowed an AI provider to receive interview content.
    CONSENT = "consent"
    #: The owner rejected a space program at review.
    PROGRAM_REJECTION = "program_rejection"


class Understood(StrictModel):
    """One value the system read from an answer (an inference until confirmed)."""

    slot: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    #: None means the owner said it is unknown or undecided.
    value: FactValue = None
    #: "parser" (deterministic) or "llm:<provider>".
    method: str = "parser"


class InterviewTurn(StrictModel):
    seq: int = Field(ge=1)
    kind: TurnKind
    at: UtcDatetime
    actor: Actor
    question_id: str | None = None
    #: The question exactly as shown to the owner.
    question_text: str | None = None
    #: The owner's words, verbatim.
    text: str | None = None
    understood: list[Understood] = Field(default_factory=list)
    #: Slots confirmed or rejected by this turn.
    slots: list[str] = Field(default_factory=list)
    contradiction_id: str | None = None
    #: Index of the chosen resolution option, when one was chosen.
    option: int | None = Field(default=None, ge=0)
    #: Consent: the provider allowed. Answer or revision: the AI provider that worded the
    #: question or read the answer, if one did.
    provider: str | None = None
    #: The AI model behind ``provider`` on an answer or revision.
    model: str | None = None

    @model_validator(mode="after")
    def _owner_turns_are_human(self) -> InterviewTurn:
        if self.actor.kind is not ActorKind.HUMAN:
            raise ValueError(
                f"{self.kind.value} turns record the owner's words or decisions; "
                f"{self.actor.kind.value} {self.actor.id!r} cannot make them"
            )
        if self.kind in (TurnKind.ANSWER, TurnKind.REVISION) and not (
            self.text and self.question_id
        ):
            raise ValueError("an answer needs the question id and the owner's words")
        if self.kind is TurnKind.RESOLUTION and not self.contradiction_id:
            raise ValueError("a resolution names the contradiction it resolves")
        if self.kind is TurnKind.CONSENT and not self.provider:
            raise ValueError("a consent names the provider")
        return self


class SiteContext(StrictModel):
    """Site values the interview may mention. Unverified until the site gate is approved."""

    site_ref: ArtifactRef | None = None
    #: True only when the site gate approval pins exactly this site version.
    verified: bool = False
    parcel_area_m2: float | None = Field(default=None, gt=0)
    #: Elevation difference across the parcel's surveyed points, metres.
    relief_m: float | None = Field(default=None, ge=0)
    mean_slope_pct: float | None = Field(default=None, ge=0)
    frontage_m: float | None = Field(default=None, ge=0)


class SessionStatus(StrEnum):
    ACTIVE = "active"
    #: Every question has been asked; answers can still be revised.
    COMPLETE = "complete"


class InterviewSession(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    project_id: Id
    status: SessionStatus = SessionStatus.ACTIVE
    #: Id of the design brief artifact this session maintains.
    brief_id: Id = "brief"
    turns: list[InterviewTurn] = Field(default_factory=list)
    #: The question waiting for an answer, if any.
    pending_question_id: str | None = None
    #: How many times the pending question has been asked without a usable answer.
    pending_attempts: int = Field(default=0, ge=0)
    site: SiteContext | None = None
    provenance: Provenance

    @model_validator(mode="after")
    def _turns_in_order(self) -> InterviewSession:
        for i, turn in enumerate(self.turns, start=1):
            if turn.seq != i:
                raise ValueError(f"turn {i} has seq {turn.seq}")
        return self

    @property
    def allowed_providers(self) -> frozenset[str]:
        return frozenset(
            t.provider for t in self.turns if t.kind is TurnKind.CONSENT and t.provider
        )
