"""Derive the design brief from an interview session (ADR 0008).

* The owner's words: one ``owner_answer`` fact per answer, recorded verbatim.
* What the system understood: one fact per slot, id ``f-<slot>``. It is an
  ``inference`` (source ``agent_inference``) until the owner confirms it, then
  an ``owner_answer`` (``verified_fact`` for household facts, otherwise a
  ``preference``). "Don't know" is recorded as status ``unknown``.
* Contradictions with their trade-off and options; resolved ones keep the
  owner's choice in their words.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from house_ai.domain.brief import (
    BriefFact,
    BriefTopic,
    DesignBrief,
    FactSource,
    FactSourceKind,
    HouseholdMember,
    MemberRole,
    Money,
)
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.interview import InterviewSession, TurnKind, current_slot, slot_fact_id
from house_ai.domain.provenance import Actor, ActorKind, ArtifactRef, Provenance
from house_ai.domain.records import Contradiction

from .questions import QUESTION_BY_ID, SLOTS
from .rules import contradictions
from .state import SlotState, State, answer_fact_id, fold, open_contradictions

TOOL_ACTOR = Actor(kind=ActorKind.SYSTEM, id="house-ai-interview")


def describe(value: Any) -> str:
    if value is None:
        return "unknown / not decided"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(v).replace("|", " ") for v in value) if value else "none"
    return str(value).replace("_", " ")


def _slot_fact(slot: str, st: SlotState) -> BriefFact:
    spec = SLOTS[slot]
    statement = f"{spec.label}: {describe(st.value)}"
    if st.status == "confirmed":
        status = Epistemic.VERIFIED_FACT if spec.is_fact else Epistemic.PREFERENCE
        ref = f"resolution:{st.resolution}" if st.resolution else f"confirmed:{st.answer_fact}"
        source = FactSource(kind=FactSourceKind.OWNER_ANSWER, ref=ref, interview_round=st.seq)
    elif st.status == "unknown":
        status = Epistemic.UNKNOWN
        source = FactSource(
            kind=FactSourceKind.OWNER_ANSWER, ref=st.answer_fact, interview_round=st.seq
        )
    else:
        status = Epistemic.INFERENCE
        statement += " (understood from your answer; please confirm)"
        source = FactSource(
            kind=FactSourceKind.AGENT_INFERENCE,
            ref=f"{st.answer_fact} via {st.method}",
            interview_round=st.seq,
        )
    return BriefFact(
        id=slot_fact_id(slot),
        topic=spec.topic,
        key=slot,
        statement=statement,
        value=st.value,
        status=status,
        priority=st.priority,
        source=source,
    )


def _household(state: State) -> list[HouseholdMember]:
    """Members only from confirmed counts; ages stay unknown unless stated."""
    out: list[HouseholdMember] = []
    for slot, role, label in (
        ("adults", MemberRole.ADULT, "Adult"),
        ("children", MemberRole.CHILD, "Child"),
        ("elders", MemberRole.ELDER, "Older relative"),
    ):
        st = state.slots.get(slot)
        if st and st.status == "confirmed" and isinstance(st.value, int):
            out += [
                HouseholdMember(id=f"hh-{role.value.replace('_', '-')}-{i}", role=role,
                                label=f"{label} {i}")
                for i in range(1, st.value + 1)
            ]  # fmt: skip
    return out


def _confirmed(state: State, slot: str) -> Any:
    st = state.slots.get(slot)
    return st.value if st and st.status == "confirmed" else None


def _topic_for_turn(qid: str, turn_slots: list[str]) -> tuple[BriefTopic, bool]:
    base_id, _, slot = qid.partition("#")
    if slot and slot in SLOTS:
        return SLOTS[slot].topic, SLOTS[slot].is_fact
    base = QUESTION_BY_ID.get(base_id)
    if base is not None:
        return base.topic, all(SLOTS[s].is_fact for s in base.slots)
    valid_slots = [current_slot(s) for s in turn_slots if current_slot(s) in SLOTS]
    if valid_slots:
        return SLOTS[valid_slots[0]].topic, all(SLOTS[s].is_fact for s in valid_slots)
    for topic in BriefTopic:
        if topic.value in base_id.lower():
            return topic, False
    return BriefTopic.OTHER, False


def build_brief(
    session: InterviewSession,
    *,
    session_ref: ArtifactRef | None,
    created_at: datetime,
) -> DesignBrief:
    state = fold(session)
    facts: list[BriefFact] = []
    for qid, turn in state.answers.items():
        topic, is_fact = _topic_for_turn(qid, [u.slot for u in turn.understood])
        facts.append(
            BriefFact(
                id=answer_fact_id(turn),
                topic=topic,
                key="answer",
                statement=turn.text or "",
                status=Epistemic.VERIFIED_FACT if is_fact else Epistemic.PREFERENCE,
                source=FactSource(
                    kind=FactSourceKind.OWNER_ANSWER, ref=qid, interview_round=turn.seq
                ),
            )
        )
    for cid, (turn, _) in state.resolutions.items():
        facts.append(
            BriefFact(
                id=answer_fact_id(turn),
                topic=BriefTopic.PRIORITIES,
                key="resolution",
                statement=turn.text or "",
                status=Epistemic.PREFERENCE,
                source=FactSource(
                    kind=FactSourceKind.OWNER_ANSWER, ref=f"resolve:{cid}",
                    interview_round=turn.seq,
                ),
            )
        )  # fmt: skip
    for turn in state.program_rejections:
        facts.append(
            BriefFact(
                id=f"rej-program-{turn.seq}",
                topic=BriefTopic.PRIORITIES,
                key="program_rejection",
                statement=turn.text or "",
                status=Epistemic.PREFERENCE,
                source=FactSource(
                    kind=FactSourceKind.OWNER_ANSWER, ref="program review",
                    interview_round=turn.seq,
                ),
            )
        )  # fmt: skip
    facts += [_slot_fact(slot, st) for slot, st in sorted(state.slots.items())]
    fact_ids = {f.id for f in facts}

    def cite(slots: tuple[str, ...], extra: list[str]) -> list[str]:
        ids = [slot_fact_id(s) for s in slots if slot_fact_id(s) in fact_ids]
        for e in extra:
            if len(ids) >= 2:
                break
            if e in fact_ids and e not in ids:
                ids.append(e)
        return ids

    found: list[Contradiction] = []
    for f in open_contradictions(state):
        answers = [state.slots[s].answer_fact for s in f.slots if s in state.slots]
        ids = cite(f.slots, answers)
        if len(ids) < 2:
            continue
        found.append(
            Contradiction(
                id=f.id, statement=f.statement, fact_ids=ids, tradeoff=f.tradeoff,
                options=[o.label for o in f.options],
            )
        )  # fmt: skip
    current = {f.id: f for f in contradictions(state.values)}
    open_ids = {c.id for c in found}
    for cid, (turn, _) in state.resolutions.items():
        if cid in open_ids:
            continue
        ids = cite(tuple(turn.slots), [answer_fact_id(turn)])
        if len(ids) < 2:
            ids = [*ids, answer_fact_id(turn)][:2] if answer_fact_id(turn) not in ids else ids
        if len(ids) < 2:
            continue
        f = current.get(cid)
        option = f"option {turn.option + 1}: " if turn.option is not None else ""
        found.append(
            Contradiction(
                id=cid,
                statement=f.statement if f else f"Resolved by the owner ({cid})",
                fact_ids=ids,
                resolved=True,
                resolution=f"{option}{turn.text}",
                tradeoff=f.tradeoff if f else None,
            )
        )
    budget = _confirmed(state, "budget")
    money = None
    if isinstance(budget, str) and " " in budget:
        amount, currency = budget.split(" ", 1)
        money = Money(amount=float(amount), currency=currency)
    area = _confirmed(state, "target_area")
    return DesignBrief(
        id=session.brief_id,
        project_id=session.project_id,
        household=_household(state),
        facts=facts,
        budget=money,
        target_gross_area_m2=float(area) if isinstance(area, int | float) and area > 0 else None,
        contradictions=found,
        interview_rounds_completed=sum(
            t.kind in (TurnKind.ANSWER, TurnKind.REVISION) for t in session.turns
        ),
        provenance=Provenance(
            created_at=created_at,
            created_by=TOOL_ACTOR,
            method="owner_interview",
            tool="house-ai interview",
            inputs=[session_ref] if session_ref else [],
            notes="Derived from the interview session; the owner's words are kept verbatim.",
        ),
    )
