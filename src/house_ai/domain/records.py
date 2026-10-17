"""Assumptions, open questions, issues and contradictions.

These are first-class records so that nothing the system is unsure about is
hidden in prose.
"""

from __future__ import annotations

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
    #: The owner's choice, in their words, when resolved.
    resolution: str | None = None
    #: What each way out costs, in plain language.
    tradeoff: str | None = None
    #: Ways to resolve it, for the owner to choose from; none is applied silently.
    options: list[str] = Field(default_factory=list)


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
