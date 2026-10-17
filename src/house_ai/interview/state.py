"""Fold an interview session into its current state, and choose what to ask next.

Pure functions over :class:`~house_ai.domain.interview.InterviewSession`: the
session's turns are the only input, so the same session always gives the same
state, questions and brief.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from house_ai.domain.brief import Priority
from house_ai.domain.interview import InterviewSession, InterviewTurn, SiteContext, TurnKind

from . import parsing
from .questions import QUESTIONS, SLOTS, followup_id, question_for
from .rules import Finding, Option, contradictions

SlotStatus = Literal["inference", "confirmed", "unknown"]

RESOLVE_PREFIX = "resolve:"


@dataclass
class SlotState:
    value: Any
    status: SlotStatus
    #: Turn that last set the value.
    seq: int
    #: Brief fact id of the owner's words the value came from.
    answer_fact: str
    method: str = "parser"
    priority: Priority | None = None
    #: For values set by resolving a contradiction.
    resolution: str | None = None


@dataclass
class State:
    slots: dict[str, SlotState] = field(default_factory=dict)
    #: Pending-question id -> latest answer/revision turn for it.
    answers: dict[str, InterviewTurn] = field(default_factory=dict)
    #: Contradiction id -> (resolution turn, slot values it was resolved for).
    resolutions: dict[str, tuple[InterviewTurn, dict[str, Any]]] = field(default_factory=dict)
    #: Contradiction id -> slot values for which the owner deferred deciding.
    deferred: dict[str, dict[str, Any]] = field(default_factory=dict)
    #: Slots the owner rejected and that have not been answered again.
    rejected_open: list[str] = field(default_factory=list)
    program_rejections: list[InterviewTurn] = field(default_factory=list)

    @property
    def values(self) -> dict[str, Any]:
        return {k: s.value for k, s in self.slots.items()}

    def answered(self, question_id: str) -> bool:
        return any(qid.partition("#")[0] == question_id for qid in self.answers)

    def unconfirmed(self) -> list[str]:
        return [k for k, s in self.slots.items() if s.status == "inference"]


def answer_fact_id(turn: InterviewTurn) -> str:
    qid = (turn.question_id or "x").replace("#", "-").replace(":", "-")
    return f"ans-{qid}-{turn.seq}"[:64].rstrip("-_")


def fold(session: InterviewSession) -> State:
    state = State()
    for t in session.turns:
        if t.kind in (TurnKind.ANSWER, TurnKind.REVISION):
            assert t.question_id is not None
            state.answers[t.question_id] = t
            fact = answer_fact_id(t)
            prio = parsing.priority(t.text or "")
            for u in t.understood:
                state.slots[u.slot] = SlotState(
                    value=u.value,
                    status="unknown" if u.value is None else "inference",
                    seq=t.seq,
                    answer_fact=fact,
                    method=u.method,
                    priority=prio,
                )
                if u.slot in state.rejected_open:
                    state.rejected_open.remove(u.slot)
        elif t.kind is TurnKind.CONFIRMATION:
            for s in t.slots:
                if s in state.slots and state.slots[s].status == "inference":
                    state.slots[s].status = "confirmed"
        elif t.kind is TurnKind.REJECTION:
            for s in t.slots:
                state.slots.pop(s, None)
                if s not in state.rejected_open:
                    state.rejected_open.append(s)
        elif t.kind is TurnKind.RESOLUTION:
            assert t.contradiction_id is not None
            fact = answer_fact_id(t)
            for u in t.understood:
                state.slots[u.slot] = SlotState(
                    value=u.value,
                    status="confirmed",
                    seq=t.seq,
                    answer_fact=fact,
                    method="resolution",
                    resolution=t.contradiction_id,
                )
            signature = {s: state.slots[s].value for s in t.slots if s in state.slots}
            if t.option is None and parsing.is_unknown(t.text or ""):
                state.deferred[t.contradiction_id] = signature
            else:
                state.resolutions[t.contradiction_id] = (t, signature)
                state.deferred.pop(t.contradiction_id, None)
        elif t.kind is TurnKind.PROGRAM_REJECTION:
            state.program_rejections.append(t)
    return state


def _signature(state: State, finding: Finding) -> dict[str, Any]:
    return {s: state.slots[s].value for s in finding.slots if s in state.slots}


def open_contradictions(state: State) -> list[Finding]:
    """Contradictions the owner has not resolved for the current values."""
    out = []
    for f in contradictions(state.values):
        resolved = state.resolutions.get(f.id)
        if resolved is not None and resolved[1] == _signature(state, f):
            continue
        out.append(f)
    return out


def resolved_contradictions(state: State) -> list[tuple[Finding | None, InterviewTurn]]:
    current = {f.id: f for f in contradictions(state.values)}
    return [(current.get(cid), turn) for cid, (turn, _) in state.resolutions.items()]


@dataclass(frozen=True)
class Prompt:
    id: str
    text: str
    kind: Literal["question", "followup", "resolve"]
    options: tuple[Option, ...] = ()
    hint: str = ""


def next_prompt(state: State, site: SiteContext | None) -> Prompt | None:
    """The single most useful thing to ask now, or None when nothing is left."""
    for f in open_contradictions(state):
        if state.deferred.get(f.id) == _signature(state, f):
            continue
        lines = [f.statement, f.tradeoff, "Which do you prefer?"]
        lines += [f"  {i + 1}. {o.label}" for i, o in enumerate(f.options)]
        return Prompt(RESOLVE_PREFIX + f.id, "\n".join(lines), "resolve", f.options)
    values = state.values
    for slot in state.rejected_open:
        q = next((q for q in QUESTIONS if slot in q.slots and q.when(values, site)), None)
        if q is not None:
            return Prompt(
                followup_id(q.id, slot),
                f"Sorry I got that wrong. {SLOTS[slot].followup}",
                "followup",
            )
    for q in QUESTIONS:
        if not q.when(values, site):
            continue
        if not state.answered(q.id):
            if all(s in state.slots for s in q.slots):
                continue  # already known from another answer: do not repeat
            return Prompt(q.id, q.render(values, site), "question", hint=q.hint)
        if not any(s in state.slots for s in q.slots):
            # Answered, but nothing could be read from it: ask again, with the hint.
            text = q.render(values, site)
            hint = q.hint or "I did not quite understand. Could you say it another way?"
            return Prompt(q.id, f"{hint}\n{text}", "question", hint=q.hint)
        for slot in q.required:
            if slot not in state.slots:
                return Prompt(followup_id(q.id, slot), SLOTS[slot].followup, "followup")
    return None


def prompt_by_id(prompt_id: str, state: State, site: SiteContext | None) -> Prompt:
    """Rebuild the prompt a session is waiting on (for resuming)."""
    if prompt_id.startswith(RESOLVE_PREFIX):
        cid = prompt_id.removeprefix(RESOLVE_PREFIX)
        f = next((f for f in open_contradictions(state) if f.id == cid), None)
        if f is not None:
            lines = [f.statement, f.tradeoff, "Which do you prefer?"]
            lines += [f"  {i + 1}. {o.label}" for i, o in enumerate(f.options)]
            return Prompt(prompt_id, "\n".join(lines), "resolve", f.options)
    else:
        q, slot = question_for(prompt_id)
        if slot:
            return Prompt(prompt_id, SLOTS[slot].followup, "followup")
        return Prompt(q.id, q.render(state.values, site), "question", hint=q.hint)
    raise KeyError(prompt_id)


def pick_option(text: str, options: tuple[Option, ...]) -> int | None:
    """Which option the owner chose: a number, or words only one option contains."""
    m = re.search(r"\b(\d+)\b", text)
    if m and 1 <= int(m.group(1)) <= len(options):
        return int(m.group(1)) - 1
    words = {w for w in re.findall(r"[a-z]{4,}", text.lower())}
    hits = [
        i
        for i, o in enumerate(options)
        if words & ({w for w in re.findall(r"[a-z]{4,}", o.label.lower())} - _COMMON)
    ]
    return hits[0] if len(hits) == 1 else None


_COMMON = {"keep", "with", "that", "this", "plan", "have", "will", "them", "they", "house"}
