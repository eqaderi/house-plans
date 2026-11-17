"""The owner interview against a project store (ADR 0008, ADR 0011).

Every turn writes a new ``interview_session`` version and the design brief
derived from it. The program is built from the brief on request. Coding agents
(Claude Code, Gemini CLI, Codex) or the owner in an interactive terminal
may record the owner's verbatim answers, propose structured slot
interpretations (always stored as ``inference`` until confirmed), record
confirmations/corrections/revisions, and resolve contradictions. Only a human
may grant external provider consent, reject a reviewed program, or approve a
workflow gate.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from house_ai.domain.brief import DesignBrief, FactValue
from house_ai.domain.interview import (
    InterviewSession,
    InterviewTurn,
    SessionStatus,
    SiteContext,
    TurnKind,
    Understood,
    current_question_id,
    current_slot,
)
from house_ai.domain.provenance import (
    Actor,
    ActorKind,
    ArtifactKind,
    ArtifactRef,
    Provenance,
    refuse_non_human,
)
from house_ai.domain.workflow import EventType, Gate, WorkflowState
from house_ai.interview import parsing
from house_ai.interview.brief_builder import build_brief, describe
from house_ai.interview.questions import (
    OPPORTUNISTIC,
    QUESTION_BY_ID,
    QUESTIONS,
    SLOTS,
    question_for,
)
from house_ai.interview.rules import Finding
from house_ai.interview.slot_types import InvalidValue, check
from house_ai.interview.state import (
    RESOLVE_PREFIX,
    Prompt,
    State,
    fold,
    next_prompt,
    open_contradictions,
    pick_option,
    prompt_by_id,
)
from house_ai.interview.summary import summary_markdown
from house_ai.program.builder import ProgramResult, build_program
from house_ai.program.report import program_markdown
from house_ai.program.validation import ProgramFinding, validate_program
from house_ai.providers.base import (
    DataFlowPolicy,
    ModelProvider,
    PrivateDataFlowError,
    ProviderError,
)
from house_ai.storage import ProjectStore, StoreError

from .interview_llm import LlmAssist
from .interview_views import (
    Checklist,
    ChecklistItem,
    CustomTurn,
    Interpretation,
    SlotCoverage,
    contradiction_json,
    prompt_json,
    slot_kind_and_choices,
)
from .site_context import SiteSummary, latest_site_context, site_summary
from .statements import owner_statements
from .workflow import (
    GateStatus,
    HumanAction,
    NextHumanAction,
    TransitionNotAllowed,
    Workflow,
    WorkflowError,
)

SESSION_ID = "interview"
BRIEF_ID = "brief"
PROGRAM_ID = "program"
#: An answer nothing can be read from is asked again this many times, then recorded
#: as unknown so the interview moves on.
MAX_ATTEMPTS = 2

_CHOICE_ALIASES: dict[tuple[str, str], str] = {
    ("slope_strategy", "split_level"): "step_down",
    ("slope_strategy", "split"): "step_down",
    ("slope_strategy", "flat"): "platform",
    ("slope_strategy", "flat_pad"): "platform",
}


class InterviewLocked(WorkflowError):
    pass


def parse_slot_value(slot: str, raw: Any) -> FactValue:
    """Coerce and validate an explicit slot value (from CLI ``--set`` or JSON)."""
    if slot not in SLOTS:
        raise ValueError(f"unknown slot {slot!r}; valid slots are: {', '.join(SLOTS)}")
    if raw is None:
        return None
    kind, choices = slot_kind_and_choices(slot)
    val: Any = raw
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.lower() in ("unknown", "undecided", "null", "none"):
            return None
        if kind == "int":
            try:
                val = int(stripped)
            except ValueError as exc:
                raise InvalidValue(f"{raw!r} is not an integer for {slot}") from exc
        elif kind == "number":
            try:
                fval = float(stripped)
                val = int(fval) if fval.is_integer() else fval
            except ValueError as exc:
                raise InvalidValue(f"{raw!r} is not a number for {slot}") from exc
        elif kind == "bool":
            low = stripped.lower()
            if low in ("true", "yes", "y", "1"):
                val = True
            elif low in ("false", "no", "n", "0"):
                val = False
            else:
                raise InvalidValue(f"{raw!r} is not true/false for {slot}")
        elif kind == "choice":
            cand = stripped.lower().replace("-", "_").replace(" ", "_")
            cand = _CHOICE_ALIASES.get((slot, cand), cand)
            val = cand if cand in choices else stripped
        elif kind == "list":
            if stripped.startswith("["):
                try:
                    val = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise InvalidValue(f"{raw!r} is not valid JSON list for {slot}") from exc
            else:
                val = [item.strip() for item in stripped.split(",") if item.strip()]
            if slot == "outdoor":
                val = [str(item).lower().replace("-", "_").replace(" ", "_") for item in val]
            elif slot == "room_sizes":
                val = [str(item).replace(":", "=") for item in val]
        elif kind == "money":
            val = stripped
            try:
                check(slot, val)
            except InvalidValue:
                parsed_money = SLOTS["budget"].parse(stripped).get("budget")
                if parsed_money is not None:
                    val = parsed_money
        else:
            val = stripped
    elif isinstance(raw, list) and slot == "room_sizes":
        val = [str(item).replace(":", "=") for item in raw]
    check(slot, val)
    return val


def resolve_question_id(question_or_slot: str) -> str:
    """Map a slot name (e.g. ``bedrooms``) to its canonical question id, or keep ``question_id``.

    Old slot names and question ids (ADR 0025) give the current question id.
    """
    question_or_slot = current_question_id(current_slot(question_or_slot))
    if question_or_slot in SLOTS:
        return next(q.id for q in QUESTIONS if question_or_slot in q.slots)
    return question_or_slot


def _sanitize_custom_qid(raw: str, topic: str | None = None) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:#-]+", "-", raw.strip()).strip("-")
    if not cleaned:
        cleaned = "followup"
    if topic and topic.lower() not in cleaned.lower():
        return f"followup-{topic.lower()}-{cleaned}"[:64].rstrip("-_")
    return cleaned[:64].rstrip("-_")


def _normalize_interpreted(
    interpreted: dict[str, Any] | None, actor: Actor
) -> list[Understood]:
    if not interpreted:
        return []
    method = f"agent:{actor.id}" if actor.kind is ActorKind.AGENT else "explicit"
    return [
        Understood(slot=current_slot(slot), value=parse_slot_value(current_slot(slot), raw),
                   method=method)
        for slot, raw in interpreted.items()
    ]


@dataclass
class TurnResult:
    session_ref: ArtifactRef
    brief_ref: ArtifactRef
    understood: list[Understood] = field(default_factory=list)
    #: True when the same question is asked again.
    asked_again: bool = False
    prompt: Prompt | None = None
    contradictions: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        """The one serialisation of a turn result (``interview answer --json`` and friends)."""
        return {
            "session_ref": self.session_ref.model_dump(mode="json"),
            "brief_ref": self.brief_ref.model_dump(mode="json"),
            "understood": [Interpretation.of(u).to_json() for u in self.understood],
            "asked_again": self.asked_again,
            "notes": list(self.notes),
            "contradictions": [contradiction_json(f) for f in self.contradictions],
            "next_prompt": prompt_json(self.prompt),
        }

    def message(self) -> str:
        lines = list(self.notes)
        if self.understood:
            lines.append("I understood (status: inference — ask the owner to confirm or correct):")
            lines += [f"  - {SLOTS[u.slot].label}: {describe(u.value)}" for u in self.understood]
        return "\n".join(lines)


#: Shown with every AI wording while the site gate is not approved (added by code, not the AI).
UNCONFIRMED_SITE_LABEL = (
    "(Anything said here about your site comes from the survey; you have not confirmed the "
    "site yet.)"
)


@dataclass
class AskedQuestion:
    """A question as shown to the owner, and who worded it."""

    prompt_id: str
    text: str
    provider: str | None = None
    model: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class ProgramBuild:
    result: ProgramResult
    program_ref: ArtifactRef
    assumptions_ref: ArtifactRef
    open_questions_ref: ArtifactRef
    findings: list[ProgramFinding]

    def to_json(self) -> dict[str, Any]:
        """The one serialisation of a program build (``program build --json``)."""
        return {
            "program_ref": self.program_ref.model_dump(mode="json"),
            "assumptions_ref": self.assumptions_ref.model_dump(mode="json"),
            "open_questions_ref": self.open_questions_ref.model_dump(mode="json"),
            "findings": [f.to_json() for f in self.findings],
        }


class InterviewService:
    def __init__(
        self,
        store: ProjectStore,
        *,
        provider: ModelProvider | None = None,
        session_id: str = SESSION_ID,
    ) -> None:
        self.store = store
        self.assist: LlmAssist | None = None
        self.session_id = session_id
        self.workflow = Workflow(store)
        if provider is not None:
            self.use_ai(provider)

    def use_ai(self, provider: ModelProvider) -> None:
        """Let ``provider`` word questions and read answers, within the owner's consent.

        The assist reads :meth:`policy` from the session on every request, so a
        consent recorded later applies at once and nothing is sent without one.
        """
        self.assist = LlmAssist(provider, self.policy)

    # ----------------------------------------------------------------- read

    def exists(self) -> bool:
        return self.store.latest(ArtifactKind.INTERVIEW_SESSION, self.session_id) is not None

    def session(self) -> InterviewSession:
        ref = self.store.latest(ArtifactKind.INTERVIEW_SESSION, self.session_id)
        if ref is None:
            raise StoreError("no interview yet; run `house-ai interview start` first")
        return self.store.get(ref, InterviewSession)

    def state(self) -> State:
        return fold(self.session())

    def site(self) -> SiteContext | None:
        return latest_site_context(self.store, self.workflow.status().approvals.get(Gate.SITE))

    def site_summary(self) -> SiteSummary:
        """The one site summary agents read (project status, checklist, AI context)."""
        return site_summary(self.store, self.workflow.status().approvals.get(Gate.SITE))

    def pending(self) -> Prompt | None:
        s = self.session()
        if s.pending_question_id is None:
            return None
        prompt = next_prompt(fold(s), s.site)
        if prompt is not None and prompt.id == current_question_id(s.pending_question_id):
            return prompt
        try:
            return prompt_by_id(s.pending_question_id, fold(s), s.site)
        except KeyError:
            return prompt

    def summary(self) -> str:
        s = self.session()
        return summary_markdown(s, s.site)

    def brief(self) -> DesignBrief:
        ref = self.store.latest(ArtifactKind.DESIGN_BRIEF, self.session().brief_id)
        if ref is None:
            raise StoreError("no design brief yet")
        return self.store.get(ref, DesignBrief)

    def checklist(self) -> Checklist:
        """Structured completeness checklist and context for coding agents and humans."""
        exists = self.exists()
        session = self.session() if exists else None
        state = fold(session) if session else State()
        summary = self.site_summary()
        site = summary.context if summary.exists else None
        sloped = bool(site and (site.relief_m or 0.0) >= 2.0)
        items: list[ChecklistItem] = []
        for q in QUESTIONS:
            answered = state.answered(q.id)
            slots = []
            for s_name in q.slots:
                st = state.slots.get(s_name)
                slots.append(SlotCoverage(
                    s_name, s_name in q.required, st.status if st else "unanswered",
                    st.value if st else None, st.method if st else None,
                ))  # fmt: skip
            items.append(ChecklistItem(
                q.id, q.topic.value, bool(q.when(state.values, site)), answered,
                answered or all(s in state.slots for s in q.slots), q.render(state.values, site),
                slots,
            ))  # fmt: skip
        custom_turns = [
            CustomTurn(t.seq, qid, t.question_text, t.text,
                       [Interpretation.of(u) for u in t.understood])  # fmt: skip
            for qid, t in state.answers.items()
            if qid.partition("#")[0] not in QUESTION_BY_ID
        ]
        required_slots = ["adults", "bedrooms", "bathrooms"] + (
            ["slope_strategy"] if sloped else []
        )
        missing_required = [
            s for s in required_slots if s not in state.slots or state.slots[s].value is None
        ]
        unconfirmed = [
            Interpretation(s, state.slots[s].value, state.slots[s].method, state.slots[s].status)
            for s in state.unconfirmed()
        ]
        return Checklist(
            project_id=self.store.project_id,
            workflow_state=self.workflow.state.value,
            session_status=session.status.value if session else "not_started",
            turn_count=len(session.turns) if session else 0,
            site=summary,
            owner_statements=owner_statements(self.store),
            items=items,
            custom_turns=custom_turns,
            missing_required_slots=missing_required,
            unconfirmed=unconfirmed,
            contradictions=open_contradictions(state),
            suggested_next=self.pending() if exists else next_prompt(state, site),
            confirmed_slots=sum(1 for st in state.slots.values() if st.status == "confirmed"),
            unknown_slots=sum(1 for st in state.slots.values() if st.status == "unknown"),
        )

    def ai_context(self) -> str:
        """What the AI may know when wording a question: site values with their status, the
        owner's own statements and what has been understood so far."""
        session = self.session()
        summary = self.site_summary()
        context: dict = {}
        if summary.exists:
            context["site"] = summary.ai_json()
        statements = owner_statements(self.store)
        if statements:
            context["owner_said"] = [{"about": st.subject, "words": st.words} for st in statements]
        state = fold(session)
        context["understood_so_far"] = {
            SLOTS[k].label: describe(v.value) for k, v in sorted(state.slots.items())
        }
        return json.dumps(context, ensure_ascii=False, sort_keys=True)

    def _provider_failed(self, exc: ProviderError, what: str) -> str:
        if exc.fatal:
            self.assist = None
            return f"The AI could not {what} ({exc}); it is off for the rest of this session."
        return f"The AI could not {what} ({exc}); I used the built-in one instead."

    def ask(self, prompt: Prompt) -> AskedQuestion:
        """The pending question, worded by the AI when one is allowed; else as planned.

        Contradiction choices keep their exact numbered wording.
        """
        assist = self.assist
        if assist is None or prompt.kind == "resolve":
            return AskedQuestion(prompt.id, prompt.text)
        try:
            phrased = assist.phrase(prompt.text, self.ai_context())
        except PrivateDataFlowError:
            return AskedQuestion(prompt.id, prompt.text, notes=[
                f"(You have not allowed {assist.provider.name} to receive your answers, so I "
                "use my standard questions.)"])  # fmt: skip
        except ProviderError as exc:
            note = self._provider_failed(exc, "word the question")
            return AskedQuestion(prompt.id, prompt.text, notes=[note])
        if phrased.model is None:
            return AskedQuestion(prompt.id, prompt.text)
        # The AI saw the site values, so any wording it gives may use them.
        summary = self.site_summary()
        unconfirmed = summary.exists and not summary.context.verified
        notes = [UNCONFIRMED_SITE_LABEL] if unconfirmed else []
        return AskedQuestion(prompt.id, phrased.text, assist.provider.name, phrased.model, notes)

    def policy(self) -> DataFlowPolicy:
        """Providers the owner allowed to receive interview content, from the session."""
        turns = [t for t in self.session().turns if t.kind is TurnKind.CONSENT]
        if not turns:
            return DataFlowPolicy()
        return DataFlowPolicy(
            allowed_private_providers=frozenset(t.provider for t in turns if t.provider),
            granted_by=turns[-1].actor,
        )

    # ---------------------------------------------------------------- write

    def _check_open(self) -> None:
        if Gate.PROGRAM in self.workflow.status().approvals:
            raise InterviewLocked(
                "the program gate is approved; the owner must reopen it before answers can change",
                next_action=NextHumanAction(HumanAction.REOPEN, Gate.PROGRAM),
            )

    def _write(
        self, session: InterviewSession, actor: Actor, reason: str
    ) -> tuple[ArtifactRef, ArtifactRef]:
        state = fold(session)
        site = self.site()
        prompt = next_prompt(state, site)
        moved = prompt is None or prompt.id != current_question_id(
            session.pending_question_id or ""
        )
        session = session.model_copy(
            update={
                "site": site,
                "pending_question_id": prompt.id if prompt else None,
                "pending_attempts": 0 if moved else session.pending_attempts,
                "status": SessionStatus.COMPLETE if prompt is None else SessionStatus.ACTIVE,
            }
        )
        session = InterviewSession.model_validate(session.model_dump())
        s_ref = self.store.put(
            ArtifactKind.INTERVIEW_SESSION, self.session_id, session, actor, reason=reason
        )
        brief = build_brief(session, session_ref=s_ref, created_at=self.store.clock())
        b_ref = self.store.put(ArtifactKind.DESIGN_BRIEF, session.brief_id, brief, actor,
                               reason="derived from the interview")  # fmt: skip
        return s_ref, b_ref

    def _append(self, turn_fields: dict, actor: Actor) -> InterviewSession:
        s = self.session()
        turn = InterviewTurn(seq=len(s.turns) + 1, at=self.store.clock(), actor=actor,
                             **turn_fields)  # fmt: skip
        return s.model_copy(update={"turns": [*s.turns, turn]})

    def start(self, actor: Actor) -> TurnResult:
        """Create the session, or resume the existing one."""
        if self.exists():
            s = self.session()
            ref = self.store.latest(ArtifactKind.INTERVIEW_SESSION, self.session_id)
            b_ref = self.store.latest(ArtifactKind.DESIGN_BRIEF, s.brief_id)
            assert ref is not None and b_ref is not None
            return TurnResult(ref, b_ref, prompt=self.pending(),
                              notes=["Resuming the interview where it stopped."])  # fmt: skip
        session = InterviewSession(
            id=self.session_id,
            project_id=self.store.project_id,
            brief_id=BRIEF_ID,
            provenance=Provenance(
                created_at=self.store.clock(), created_by=actor, method="owner_interview",
                tool="house-ai interview",
            ),
        )  # fmt: skip
        s_ref, b_ref = self._write(session, actor, "interview started")
        notes = ["Hello! I will ask one question at a time. 'Not sure' is always a fine answer."]
        site = self.session().site
        if site is not None and site.site_ref is not None and not site.verified:
            notes.append(
                "Your site is not confirmed yet, so anything I say about it comes from the "
                "survey and may change."
            )
        return TurnResult(s_ref, b_ref, prompt=self.pending(), notes=notes)

    def _read(
        self, prompt: Prompt, text: str, state: State
    ) -> tuple[list[Understood], list[str], str | None]:
        """What the answer says, notes for the owner, and the AI model that helped, if any."""
        q, slot = question_for(prompt.id)
        slots = [slot] if slot else list(q.slots)
        parsed: dict[str, FactValue] = (
            {k: v for k, v in SLOTS[slot].parse(text).items() if k == slot}
            if slot
            else q.parse(text)
        )
        method = {k: "parser" for k in parsed}
        notes: list[str] = []
        model: str | None = None
        for extra, parser in OPPORTUNISTIC.items():
            if extra not in parsed and extra not in state.slots:
                for k, v in parser(text).items():
                    parsed[k] = v
                    method[k] = "parser"
        assist = self.assist
        if not any(s in parsed for s in slots) and assist is not None:
            try:
                for k, v in assist.extract(prompt.text, slots, text).items():
                    parsed[k] = v
                    method[k] = assist.method
                model = assist.last_model
            except PrivateDataFlowError:
                pass  # the owner has not allowed this provider; the parser result stands
            except ProviderError as exc:
                notes.append(self._provider_failed(exc, "read your answer"))
        if parsing.is_unknown(text):
            for s in slots:
                parsed.setdefault(s, None)
        understood = [Understood(slot=k, value=v, method=method.get(k, "parser"))
                      for k, v in parsed.items()]  # fmt: skip
        return understood, notes, model

    def answer(
        self,
        text: str,
        actor: Actor,
        shown: AskedQuestion | None = None,
        *,
        question_id: str | None = None,
        question_text: str | None = None,
        topic: str | None = None,
        interpreted: dict[str, Any] | None = None,
        option: int | None = None,
    ) -> TurnResult:
        """Record the owner's answer (to the pending question, a named checklist question/slot,
        or an adaptive follow-up question) and any structured slot interpretations."""
        self._check_open()
        text = text.strip()
        if not text:
            raise ValueError("an answer cannot be empty")
        s = self.session()
        state = fold(s)
        explicit = _normalize_interpreted(interpreted, actor)

        if question_id is not None:
            resolved_qid = resolve_question_id(question_id)
            if resolved_qid.startswith(RESOLVE_PREFIX) or any(
                f.id == resolved_qid for f in open_contradictions(state)
            ):
                return self.resolve(
                    resolved_qid.removeprefix(RESOLVE_PREFIX), text, actor, option=option
                )
            if resolved_qid.partition("#")[0] in QUESTION_BY_ID:
                q_obj, slot_name = question_for(resolved_qid)
                prompt = Prompt(
                    resolved_qid,
                    question_text
                    or (
                        SLOTS[slot_name].followup
                        if slot_name
                        else q_obj.render(state.values, s.site)
                    ),
                    "followup" if slot_name else "question",
                    hint=q_obj.hint,
                )
            else:
                custom_qid = _sanitize_custom_qid(resolved_qid, topic)
                prompt = Prompt(custom_qid, question_text or custom_qid, "followup")
        elif topic is not None and not explicit:
            custom_qid = _sanitize_custom_qid(f"q-{len(s.turns) + 1}", topic)
            prompt = Prompt(custom_qid, question_text or custom_qid, "followup")
        else:
            prompt = self.pending()
            if prompt is None:
                if explicit:
                    first_q = next(
                        (q for q in QUESTIONS if any(u.slot in q.slots for u in explicit)),
                        QUESTIONS[0],
                    )
                    prompt = Prompt(
                        first_q.id,
                        question_text or first_q.render(state.values, s.site),
                        "question",
                        hint=first_q.hint,
                    )
                elif question_text is not None or topic is not None:
                    custom_qid = _sanitize_custom_qid(f"q-{len(s.turns) + 1}", topic)
                    prompt = Prompt(custom_qid, question_text or custom_qid, "followup")
                else:
                    raise WorkflowError(
                        "all questions are answered; use `interview revise` to change one"
                    )
            elif prompt.kind == "resolve":
                cid = prompt.id.removeprefix(RESOLVE_PREFIX)
                finding = next((f for f in open_contradictions(state) if f.id == cid), None)
                if explicit and (
                    finding is None or not any(u.slot in finding.slots for u in explicit)
                ):
                    first_q = next(
                        (q for q in QUESTIONS if any(u.slot in q.slots for u in explicit)),
                        QUESTIONS[0],
                    )
                    prompt = Prompt(
                        first_q.id,
                        question_text or first_q.render(state.values, s.site),
                        "question",
                        hint=first_q.hint,
                    )
                else:
                    return self._resolve(prompt, text, actor, s, option=option)

        is_checklist_q = prompt.id.partition("#")[0] in QUESTION_BY_ID
        if is_checklist_q:
            if interpreted is not None:
                understood, ai_notes, read_model = explicit, [], None
            else:
                understood, ai_notes, read_model = self._read(prompt, text, state)
            q, slot = question_for(prompt.id)
            wanted = [slot] if slot else list(q.slots)
            got_any = any(u.slot in wanted for u in understood)
            if not got_any and question_id is None and understood:
                matched_q = next(
                    (mq for mq in QUESTIONS if any(u.slot in mq.slots for u in understood)),
                    None,
                )
                if matched_q is not None:
                    prompt = Prompt(
                        matched_q.id,
                        question_text or matched_q.render(state.values, s.site),
                        "question",
                        hint=matched_q.hint,
                    )
                    got_any = True
            if not got_any and s.pending_attempts + 1 >= MAX_ATTEMPTS:
                understood += [
                    Understood(slot=w, value=None, method="unparsed")
                    for w in wanted
                    if all(u.slot != w for u in understood)
                ]
        else:
            understood, ai_notes, read_model = explicit, [], None
            got_any = True

        if shown is not None and shown.prompt_id != prompt.id:
            shown = None  # shown for another question; record the planned wording
        provider = shown.provider if shown else None
        model = shown.model if shown else None
        if read_model is not None and self.assist is not None:
            provider, model = self.assist.provider.name, read_model
        recorded_q_text = question_text or (shown.text if shown else prompt.text)
        session = self._append(
            {"kind": TurnKind.ANSWER, "question_id": prompt.id,
             "question_text": recorded_q_text, "text": text,
             "understood": understood, "provider": provider, "model": model},
            actor,
        )  # fmt: skip
        if not got_any:
            session = session.model_copy(update={"pending_attempts": s.pending_attempts + 1})
        s_ref, b_ref = self._write(session, actor, f"owner answered {prompt.id}")
        new_state = fold(self.session())
        notes = list(ai_notes)
        if not got_any and s.pending_attempts + 1 < MAX_ATTEMPTS:
            notes.append("I could not read that clearly; let me ask again.")
        elif not got_any:
            notes.append("I have noted your words and marked this as not known for now.")
        return TurnResult(
            s_ref, b_ref, understood=understood,
            asked_again=not got_any and s.pending_attempts + 1 < MAX_ATTEMPTS,
            prompt=self.pending(), contradictions=open_contradictions(new_state), notes=notes,
        )  # fmt: skip

    def resolve(
        self,
        contradiction_id: str,
        text: str,
        actor: Actor,
        *,
        option: int | None = None,
        defer: bool = False,
    ) -> TurnResult:
        """Resolve or defer an open contradiction by ID."""
        self._check_open()
        cid = contradiction_id.removeprefix(RESOLVE_PREFIX)
        s = self.session()
        finding = next((f for f in open_contradictions(fold(s)) if f.id == cid), None)
        if finding is None:
            raise WorkflowError(f"contradiction {cid} is no longer open")
        lines = [finding.statement, finding.tradeoff, "Which do you prefer?"]
        lines += [f"  {i + 1}. {o.label}" for i, o in enumerate(finding.options)]
        prompt = Prompt(RESOLVE_PREFIX + cid, "\n".join(lines), "resolve", finding.options)
        return self._resolve(prompt, text.strip(), actor, s, option=option, defer=defer)

    def _resolve(
        self,
        prompt: Prompt,
        text: str,
        actor: Actor,
        s: InterviewSession,
        *,
        option: int | None = None,
        defer: bool = False,
    ) -> TurnResult:
        cid = prompt.id.removeprefix(RESOLVE_PREFIX)
        finding = next((f for f in open_contradictions(fold(s)) if f.id == cid), None)
        if finding is None:
            raise WorkflowError(f"contradiction {cid} is no longer open")
        if defer:
            choice = None
        elif option is not None:
            if not 1 <= option <= len(finding.options):
                raise ValueError(
                    f"option for {cid} must be between 1 and {len(finding.options)}, got {option}"
                )
            choice = option - 1
        else:
            choice = pick_option(text, finding.options)
        if choice is None and not defer and not parsing.is_unknown(text):
            s_ref = self.store.latest(ArtifactKind.INTERVIEW_SESSION, self.session_id)
            b_ref = self.store.latest(ArtifactKind.DESIGN_BRIEF, s.brief_id)
            assert s_ref and b_ref
            return TurnResult(s_ref, b_ref, asked_again=True, prompt=prompt,
                              contradictions=[finding],
                              notes=["Please answer with the number of the option you prefer, "
                                     "or say 'not sure' to decide later."])  # fmt: skip
        updates = finding.options[choice].updates if choice is not None else {}
        understood = [Understood(slot=k, value=v, method="resolution")
                      for k, v in updates.items()]  # fmt: skip
        recorded_text = "not sure yet" if (defer and not parsing.is_unknown(text)) else text
        session = self._append(
            {"kind": TurnKind.RESOLUTION, "contradiction_id": cid, "question_id": prompt.id,
             "question_text": prompt.text, "text": recorded_text, "option": choice,
             "slots": sorted({*finding.slots, *updates}), "understood": understood},
            actor,
        )  # fmt: skip
        s_ref, b_ref = self._write(session, actor, f"owner resolved {cid}")
        note = (
            f"Noted: {finding.options[choice].label}." if choice is not None
            else "Fine, we will come back to this later. It stays open until you decide."
        )
        return TurnResult(s_ref, b_ref, understood=understood, prompt=self.pending(),
                          contradictions=open_contradictions(fold(self.session())),
                          notes=[note])  # fmt: skip

    def revise(
        self,
        question_id: str,
        text: str,
        actor: Actor,
        *,
        question_text: str | None = None,
        interpreted: dict[str, Any] | None = None,
    ) -> TurnResult:
        """Change an earlier answer. The old answer stays in the session history."""
        self._check_open()
        resolved_qid = resolve_question_id(question_id)
        state = self.state()
        base_qid = resolved_qid.partition("#")[0]
        if base_qid in QUESTION_BY_ID:
            q, slot = question_for(resolved_qid)
            default_q_text = (
                q.render(state.values, self.session().site)
                if not slot
                else SLOTS[slot].followup
            )
            prompt = Prompt(resolved_qid, question_text or default_q_text, "question")
            if interpreted is not None:
                understood = _normalize_interpreted(interpreted, actor)
                notes: list[str] = []
                read_model = None
            else:
                understood, notes, read_model = self._read(prompt, text, state)
        elif resolved_qid in state.answers or interpreted is not None:
            prev_turn = state.answers.get(resolved_qid)
            default_q_text = (
                question_text
                or (prev_turn.question_text if prev_turn else None)
                or resolved_qid
            )
            prompt = Prompt(resolved_qid, default_q_text, "followup")
            understood = _normalize_interpreted(interpreted, actor)
            notes = []
            read_model = None
        else:
            known = ", ".join(QUESTION_BY_ID)
            raise ValueError(f"unknown question {question_id!r}; questions are: {known}")
        ai = read_model is not None and self.assist is not None
        session = self._append(
            {"kind": TurnKind.REVISION, "question_id": resolved_qid, "question_text": prompt.text,
             "text": text.strip(), "understood": understood,
             "provider": self.assist.provider.name if ai else None,
             "model": read_model if ai else None},
            actor,
        )  # fmt: skip
        s_ref, b_ref = self._write(session, actor, f"owner revised {resolved_qid}")
        if not understood and base_qid in QUESTION_BY_ID:
            notes.append("I could not read a new value; nothing else changed.")
        return TurnResult(s_ref, b_ref, understood=understood, prompt=self.pending(),
                          contradictions=open_contradictions(fold(self.session())),
                          notes=notes)  # fmt: skip

    def confirm(
        self, actor: Actor, slots: list[str] | None = None, *, text: str | None = None
    ) -> list[str]:
        """The owner confirms what was understood (all pending interpretations by default)."""
        self._check_open()
        pending = self.state().unconfirmed()
        slots = None if slots is None else [current_slot(s) for s in slots]
        chosen = pending if slots is None else [s for s in slots if s in pending]
        unknown = set(slots or []) - set(pending)
        if unknown:
            raise ValueError(f"nothing to confirm for: {', '.join(sorted(unknown))}")
        if not chosen:
            return []
        turn_fields: dict[str, Any] = {"kind": TurnKind.CONFIRMATION, "slots": chosen}
        if text is not None and text.strip():
            turn_fields["text"] = text.strip()
        session = self._append(turn_fields, actor)
        self._write(session, actor, "owner confirmed interpretations")
        return chosen

    def reject(self, actor: Actor, slots: list[str], text: str | None = None) -> TurnResult:
        """The owner says an interpretation is wrong; it is removed and asked again."""
        self._check_open()
        state = self.state()
        slots = [current_slot(s) for s in slots]
        missing = [s for s in slots if s not in state.slots]
        if missing or not slots:
            raise ValueError(f"no current value for: {', '.join(missing) or '(none given)'}")
        session = self._append(
            {"kind": TurnKind.REJECTION, "slots": slots, "text": text}, actor
        )
        s_ref, b_ref = self._write(session, actor, "owner rejected an interpretation")
        return TurnResult(s_ref, b_ref, prompt=self.pending(),
                          notes=["Thank you. I removed it; let me ask again."])  # fmt: skip

    def consent(self, actor: Actor, provider: str) -> None:
        """The owner allows ``provider`` to receive interview content (private data)."""
        refuse_non_human(actor, "allow an AI provider to receive private data")
        session = self._append(
            {"kind": TurnKind.CONSENT, "provider": provider,
             "text": f"I allow {provider} to receive my interview answers."},
            actor,
        )  # fmt: skip
        self._write(session, actor, f"owner allowed provider {provider}")

    # -------------------------------------------------------------- program

    def build_program(self, actor: Actor) -> ProgramBuild:
        """Derive and store the space program, assumptions and open questions, and check them."""
        brief_ref = self.store.latest(ArtifactKind.DESIGN_BRIEF, self.session().brief_id)
        if brief_ref is None:
            raise StoreError("no design brief yet; run the interview first")
        brief = self.store.get(brief_ref, DesignBrief)
        site = self.site()
        open_prompts = 0 if next_prompt(self.state(), site) is None else 1
        result = build_program(brief, site=site, brief_ref=brief_ref,
                               created_at=self.store.clock(), program_id=PROGRAM_ID,
                               open_prompts=open_prompts)  # fmt: skip
        p_ref = self.store.put(ArtifactKind.SPACE_PROGRAM, PROGRAM_ID, result.program, actor,
                               reason="program derived from the design brief")  # fmt: skip
        a_ref = self.store.put(ArtifactKind.ASSUMPTIONS, "assumptions", result.assumptions, actor)
        q_ref = self.store.put(
            ArtifactKind.OPEN_QUESTIONS, "open-questions", result.open_questions, actor
        )
        findings = validate_program(result.program, brief, site)
        return ProgramBuild(result, p_ref, a_ref, q_ref, findings)

    def design_export(self, build: ProgramBuild) -> dict[str, str]:
        """The six design files for a program build, by file name; writes nothing."""

        def dump(model) -> str:
            return yaml.safe_dump(model.model_dump(mode="json"), sort_keys=False,
                                  allow_unicode=True)  # fmt: skip

        brief = self.brief()
        result = build.result
        return {
            "design_brief.yaml": dump(brief),
            "space_program.yaml": dump(result.program),
            "assumptions.yaml": dump(result.assumptions),
            "open_questions.yaml": dump(result.open_questions),
            "interview-summary.md": self.summary(),
            "program-review.md": program_markdown(
                result.program, brief, build.findings, result.assumptions, result.open_questions
            ),
        }

    def write_design_export(self, build: ProgramBuild, out: Path) -> list[Path]:
        """Write :meth:`design_export` into ``out``; the files are exports, not project state."""
        out.mkdir(parents=True, exist_ok=True)
        written = []
        for name, text in self.design_export(build).items():
            (out / name).write_text(text, encoding="utf-8")
            written.append(out / name)
        return written

    def review_program(self, actor: Actor) -> tuple[ProgramBuild, GateStatus]:
        """Build the program, move to PROGRAM_REVIEW and ask the owner to review it.

        From SITE_APPROVED this module makes its own move to INTERVIEWING first
        (ADR 0028); before the site gate is approved the review still waits.
        """
        state = self.workflow.state
        if state not in (WorkflowState.SITE_APPROVED, WorkflowState.INTERVIEWING):
            hint = (
                " The site is not approved yet: the interview and the program can be built "
                "and checked now, but review and approval wait for the site gate."
                if Gate.SITE not in self.workflow.status().approvals
                else ""
            )
            raise TransitionNotAllowed(
                "program review starts from SITE_APPROVED or INTERVIEWING; the project is in "
                f"{state.value}." + hint
            )
        build = self.build_program(actor)
        if state is WorkflowState.SITE_APPROVED:
            self.workflow.transition(WorkflowState.INTERVIEWING, actor,
                                     "program review: the interview stage begins")  # fmt: skip
        self.workflow.transition(WorkflowState.PROGRAM_REVIEW, actor,
                                 "space program ready for the owner's review")  # fmt: skip
        return build, self.workflow.request_approval(Gate.PROGRAM, build.program_ref, actor)

    def reject_program(self, actor: Actor, text: str) -> ArtifactRef:
        """The owner rejects the program at review; their words are kept verbatim."""
        refuse_non_human(actor, "reject the space program")
        if self.workflow.state is not WorkflowState.PROGRAM_REVIEW:
            raise TransitionNotAllowed(
                f"a program can be rejected in PROGRAM_REVIEW, not {self.workflow.state.value}"
            )
        if not text.strip():
            raise ValueError("say what is wrong with the program")
        session = self._append({"kind": TurnKind.PROGRAM_REJECTION, "text": text.strip()}, actor)
        _, b_ref = self._write(session, actor, "owner rejected the space program")
        # The program-reject operation is the only move out of PROGRAM_REVIEW; the
        # generic transition refuses it for every actor (ADR 0029).
        self.store.append_event(
            EventType.TRANSITION,
            actor,
            from_state=WorkflowState.PROGRAM_REVIEW,
            to_state=WorkflowState.INTERVIEWING,
            reason=f"owner rejected the program: {text.strip()}",
        )
        return b_ref
