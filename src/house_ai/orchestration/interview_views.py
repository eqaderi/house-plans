"""What agents read from the interview: one JSON shape per glossary term.

Views, so they live in orchestration and not in the domain package. An
Interpretation and a Contradiction each have one shape wherever an agent meets
them (turn result, checklist); a pending question has one shape too. Existing
keys keep their names and meaning; outputs may gain keys and lose none
(ADR 0011 §5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from house_ai.domain.brief import FactValue
from house_ai.domain.interview import Understood, current_slot
from house_ai.domain.records import OwnerStatement
from house_ai.interview.brief_builder import describe
from house_ai.interview.questions import SLOTS
from house_ai.interview.rules import Finding
from house_ai.interview.slot_types import BOOL, CHOICE, INT, OUTDOOR
from house_ai.interview.state import Prompt

from .site_context import SiteSummary


def slot_kind_and_choices(slot: str) -> tuple[str, list[str]]:
    """The kind of value a slot takes, and its legal choices if it has a fixed set."""
    if slot in INT:
        return "int", []
    if slot in BOOL:
        return "bool", []
    if slot in CHOICE:
        return "choice", sorted(CHOICE[slot])
    if slot == "outdoor":
        return "list", sorted(OUTDOOR)
    if slot in ("relationships", "room_sizes", "priorities"):
        return "list", []
    if slot == "target_area":
        return "number", []
    if slot == "budget":
        return "money", []
    return "text", []


def _label(slot: str) -> str:
    return SLOTS[slot].label if slot in SLOTS else slot


@dataclass(frozen=True)
class Interpretation:
    """What was understood for one slot, and its status (unconfirmed until confirmed)."""

    slot: str
    value: FactValue
    method: str
    #: "inference", "unknown" or "confirmed".
    status: str

    @classmethod
    def of(cls, understood: Understood) -> Interpretation:
        """An Interpretation as read from one answer (never confirmed yet)."""
        status = "unknown" if understood.value is None else "inference"
        return cls(current_slot(understood.slot), understood.value, understood.method, status)

    def to_json(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "label": _label(self.slot),
            "value": self.value,
            "display": describe(self.value),
            "method": self.method,
            "status": self.status,
        }


def contradiction_json(finding: Finding) -> dict[str, Any]:
    """The one shape of an open Contradiction; ``options`` are numbered as ``--option`` takes."""
    return {
        "id": finding.id,
        "statement": finding.statement,
        "tradeoff": finding.tradeoff,
        "slots": list(finding.slots),
        "options": [
            {"option": i + 1, "label": o.label, "updates": dict(o.updates)}
            for i, o in enumerate(finding.options)
        ],
    }


def prompt_json(prompt: Prompt | None) -> dict[str, Any] | None:
    """The one shape of the question to ask next."""
    if prompt is None:
        return None
    return {"id": prompt.id, "kind": prompt.kind, "text": prompt.text}


@dataclass(frozen=True)
class SlotCoverage:
    """One slot of a checklist question: whether and how it is answered."""

    slot: str
    required: bool
    #: "unanswered", or the slot's status.
    status: str
    value: FactValue = None
    method: str | None = None

    def to_json(self) -> dict[str, Any]:
        kind, choices = slot_kind_and_choices(self.slot)
        answered = self.status != "unanswered"
        return {
            "slot": self.slot,
            "label": _label(self.slot),
            "kind": kind,
            "choices": choices,
            "required": self.required,
            "status": self.status,
            "value": self.value,
            "display": describe(self.value) if answered else None,
            "method": self.method,
        }


@dataclass(frozen=True)
class ChecklistItem:
    """One of the checklist questions and how far it is covered."""

    id: str
    topic: str
    applicable: bool
    answered: bool
    covered: bool
    question: str
    slots: list[SlotCoverage]

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "applicable": self.applicable,
            "answered": self.answered,
            "covered": self.covered,
            "question": self.question,
            "slots": [s.to_json() for s in self.slots],
        }


@dataclass(frozen=True)
class CustomTurn:
    """An answer to an adaptive follow-up question outside the checklist."""

    seq: int
    question_id: str
    question_text: str | None
    text: str | None
    understood: list[Interpretation]

    def to_json(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "question_id": self.question_id,
            "question_text": self.question_text,
            "text": self.text,
            "understood": [u.to_json() for u in self.understood],
        }


@dataclass(frozen=True)
class Checklist:
    """The interview's completeness checklist with its context (``interview checklist``)."""

    project_id: str
    workflow_state: str
    #: "not_started", or the session's status.
    session_status: str
    turn_count: int
    site: SiteSummary
    owner_statements: list[OwnerStatement]
    items: list[ChecklistItem]
    custom_turns: list[CustomTurn]
    missing_required_slots: list[str]
    unconfirmed: list[Interpretation]
    contradictions: list[Finding]
    suggested_next: Prompt | None
    confirmed_slots: int = 0
    unknown_slots: int = 0

    def counts(self) -> dict[str, int]:
        applicable = [i for i in self.items if i.applicable]
        covered = [i for i in applicable if i.covered]
        return {
            "total_checklist_questions": len(self.items),
            "applicable_questions": len(applicable),
            "covered_questions": len(covered),
            "remaining_questions": len(applicable) - len(covered),
            "confirmed_slots": self.confirmed_slots,
            "unconfirmed_slots": len(self.unconfirmed),
            "unknown_slots": self.unknown_slots,
            "open_contradictions": len(self.contradictions),
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "workflow_state": self.workflow_state,
            "session_status": self.session_status,
            "turn_count": self.turn_count,
            "site": self.site.to_json(),
            "owner_statements": [
                {"id": st.id, "subject": st.subject, "words": st.words, "stated_by": st.stated_by}
                for st in self.owner_statements
            ],
            "counts": self.counts(),
            "missing_required_slots": list(self.missing_required_slots),
            "unconfirmed": [u.to_json() for u in self.unconfirmed],
            "contradictions": [contradiction_json(f) for f in self.contradictions],
            "custom_turns": [t.to_json() for t in self.custom_turns],
            "suggested_next": prompt_json(self.suggested_next),
            "checklist": [i.to_json() for i in self.items],
        }
