"""Assumptions, open questions, issues and contradictions.

These are first-class records so that nothing the system is unsure about is
hidden in prose.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, StrictModel
from .epistemics import Epistemic
from .provenance import Actor, Provenance


class Assumption(StrictModel):
    id: Id
    statement: str = Field(min_length=1)
    #: Why it was assumed.
    basis: str | None = None
    status: Epistemic = Epistemic.ASSUMPTION
    #: Ids of things that depend on this assumption.
    affects: list[Id] = Field(default_factory=list)
    #: Who should confirm or reject it (e.g. "owner", "surveyor", "structural engineer").
    confirm_with: str | None = None
    made_by: Actor | None = None


class QuestionStatus(StrEnum):
    OPEN = "open"
    ANSWERED = "answered"
    DROPPED = "dropped"


class OpenQuestion(StrictModel):
    id: Id
    question: str = Field(min_length=1)
    topic: str | None = None
    why_it_matters: str | None = None
    #: A blocking question must be answered before the program can be approved.
    blocking: bool = False
    status: QuestionStatus = QuestionStatus.OPEN
    answer: str | None = None
    asked_in_round: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _answer_matches_status(self) -> OpenQuestion:
        if self.status is QuestionStatus.ANSWERED and not self.answer:
            raise ValueError("an answered question needs an answer")
        return self


class Severity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class IssueStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    #: Knowingly accepted by a human; stays visible.
    ACCEPTED = "accepted"


class Issue(StrictModel):
    """An unresolved problem attached to a site, program or plan."""

    id: Id
    title: str = Field(min_length=1)
    description: str | None = None
    severity: Severity
    status: IssueStatus = IssueStatus.OPEN
    subject_ids: list[Id] = Field(default_factory=list)
    raised_by: Actor | None = None


class Contradiction(StrictModel):
    """Two or more brief facts that cannot all hold."""

    id: Id
    statement: str = Field(min_length=1)
    fact_ids: list[Id] = Field(min_length=2)
    resolved: bool = False
    resolution: str | None = None


class AssumptionsFile(StrictModel):
    """assumptions.yaml"""

    schema_version: str = SCHEMA_VERSION
    project_id: Id
    assumptions: list[Assumption] = Field(default_factory=list)
    provenance: Provenance


class OpenQuestionsFile(StrictModel):
    """open_questions.yaml"""

    schema_version: str = SCHEMA_VERSION
    project_id: Id
    questions: list[OpenQuestion] = Field(default_factory=list)
    provenance: Provenance

    def blocking_open(self) -> list[OpenQuestion]:
        return [q for q in self.questions if q.blocking and q.status is QuestionStatus.OPEN]


class OwnerStatement(StrictModel):
    """Something the owner said about the project, in their words, and who wrote it down.

    A statement is evidence, not a confirmation: it changes no confirmation status and
    clears no blocker. Units, CRS, datum and boundary are confirmed only by the owner
    with ``house-ai site confirm``; gates only with ``house-ai workflow approve``.
    """

    id: Id
    #: What it is about, e.g. "horizontal_crs", "elevation_units", "relief".
    subject: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    #: The owner's words, verbatim.
    words: str = Field(min_length=1)
    #: Who said it, e.g. "owner".
    stated_by: str = Field(min_length=1)
    #: How it reached the project, e.g. "chat with agent:claude-code on 2026-10-17".
    channel: str = Field(min_length=1)
    recorded_by: Actor
    recorded_at: datetime
    #: What would make it formal, e.g. the command the owner runs.
    pending_confirmation: str | None = None


class OwnerStatementsFile(StrictModel):
    """Everything the owner said that is not an interview answer, oldest first."""

    schema_version: str = SCHEMA_VERSION
    project_id: Id
    statements: list[OwnerStatement] = Field(default_factory=list)
    provenance: Provenance

    @model_validator(mode="after")
    def _unique_ids(self) -> OwnerStatementsFile:
        ids = [st.id for st in self.statements]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate statement ids: {dupes}")
        return self
