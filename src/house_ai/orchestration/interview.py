"""The owner interview against a project store (ADR 0008).

Every owner turn writes a new ``interview_session`` version and the design
brief derived from it. The program is built from the brief on request. Only a
human can answer, revise, confirm, reject, resolve or consent; agents may start
the session, read it, and build and check the program. Nothing here approves a
gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from house_ai.domain.brief import DesignBrief, FactValue
from house_ai.domain.interview import (
    InterviewSession,
    InterviewTurn,
    SessionStatus,
    SiteContext,
    TurnKind,
    Understood,
)
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, ArtifactRef, Provenance
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.interview import parsing
from house_ai.interview.brief_builder import build_brief, describe
from house_ai.interview.questions import OPPORTUNISTIC, QUESTION_BY_ID, SLOTS, question_for
from house_ai.interview.rules import Finding
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
from house_ai.program.validation import ProgramFinding, validate_program
from house_ai.providers.base import DataFlowPolicy, PrivateDataFlowError, ProviderError
from house_ai.storage import ProjectStore, StoreError

from .interview_llm import LlmAssist
from .site_context import latest_site_context
from .statements import owner_statements
from .workflow import ApprovalRequiresHuman, TransitionNotAllowed, Workflow, WorkflowError

SESSION_ID = "interview"
BRIEF_ID = "brief"
PROGRAM_ID = "program"
#: An answer nothing can be read from is asked again this many times, then recorded
#: as unknown so the interview moves on.
MAX_ATTEMPTS = 2


class InterviewLocked(WorkflowError):
    pass


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

    def message(self) -> str:
        lines = list(self.notes)
        if self.understood:
            lines.append("I understood:")
            lines += [f"  - {SLOTS[u.slot].label}: {describe(u.value)}" for u in self.understood]
        return "\n".join(lines)


#: Shown with any AI wording while the site gate is not approved (added by code, not the AI).
UNCONFIRMED_SITE_LABEL = (
    "(Site figures here come from the survey; you have not confirmed the site yet.)"
)


_SITE_WORDS = ("site", "land", "plot", "parcel", "slope", "steep", "terrain", "road", "drop")


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


def _require_human(actor: Actor, what: str) -> None:
    if actor.kind is not ActorKind.HUMAN:
        raise ApprovalRequiresHuman(
            f"{actor.kind.value} {actor.id!r} cannot {what}; only the owner can. An agent must "
            "never answer, confirm or decide for the owner."
        )


class InterviewService:
    def __init__(
        self,
        store: ProjectStore,
        *,
        assist: LlmAssist | None = None,
        session_id: str = SESSION_ID,
    ) -> None:
        self.store = store
        self.assist = assist
        self.session_id = session_id
        self.workflow = Workflow(store)

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

    def pending(self) -> Prompt | None:
        s = self.session()
        if s.pending_question_id is None:
            return None
        prompt = next_prompt(fold(s), s.site)
        if prompt is not None and prompt.id == s.pending_question_id:
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

    def ai_context(self) -> str:
        """What the AI may know when wording a question: site values with their status, the
        owner's own statements and what has been understood so far."""
        session = self.session()
        site = session.site
        context: dict = {}
        if site is not None and site.site_ref is not None:
            context["site"] = {
                "status": "confirmed by the owner" if site.verified
                else "from the survey; NOT yet confirmed by the owner",
                "parcel_area_m2": site.parcel_area_m2,
                "relief_m": site.relief_m,
                "mean_slope_pct": site.mean_slope_pct,
                "frontage_m": site.frontage_m,
            }  # fmt: skip
        statements = owner_statements(self.store)
        if statements:
            context["owner_said"] = [{"about": st.subject, "words": st.words} for st in statements]
        state = fold(session)
        context["understood_so_far"] = {
            SLOTS[k].label: describe(v.value) for k, v in sorted(state.slots.items())
        }
        return json.dumps(context, ensure_ascii=False, sort_keys=True)

    def _live_assist(self) -> LlmAssist | None:
        """The assist with the consent recorded in the session right now."""
        if self.assist is not None:
            self.assist.policy = self.policy()
        return self.assist

    def _provider_failed(self, exc: ProviderError, what: str) -> str:
        if exc.fatal:
            self.assist = None
            return f"The AI could not {what} ({exc}); it is off for the rest of this session."
        return f"The AI could not {what} ({exc}); I used the built-in one instead."

    def ask(self, prompt: Prompt) -> AskedQuestion:
        """The pending question, worded by the AI when one is allowed; else as planned.

        Contradiction choices keep their exact numbered wording.
        """
        assist = self._live_assist()
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
        site = self.session().site
        about_site = any(c.isdigit() for c in phrased.text) or any(
            w in phrased.text.lower() for w in _SITE_WORDS
        )
        notes = (
            [UNCONFIRMED_SITE_LABEL]
            if site is not None and site.site_ref is not None and not site.verified and about_site
            else []
        )
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
                "the program gate is approved; the owner must reopen it "
                "(`house-ai workflow reopen <dir> program`) before answers can change"
            )

    def _write(
        self, session: InterviewSession, actor: Actor, reason: str
    ) -> tuple[ArtifactRef, ArtifactRef]:
        state = fold(session)
        site = self.site()
        prompt = next_prompt(state, site)
        moved = prompt is None or prompt.id != session.pending_question_id
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
        assist = self._live_assist()
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

    def answer(self, text: str, actor: Actor, shown: AskedQuestion | None = None) -> TurnResult:
        """Record the owner's answer to the pending question. ``shown`` is the question as the
        owner saw it (e.g. worded by the AI); it is kept with the answer."""
        _require_human(actor, "answer interview questions")
        self._check_open()
        text = text.strip()
        if not text:
            raise ValueError("an answer cannot be empty")
        s = self.session()
        prompt = self.pending()
        if prompt is None:
            raise WorkflowError("all questions are answered; use `interview revise` to change one")
        state = fold(s)
        if prompt.kind == "resolve":
            return self._resolve(prompt, text, actor, s)
        understood, ai_notes, read_model = self._read(prompt, text, state)
        if shown is not None and shown.prompt_id != prompt.id:
            shown = None  # shown for another question; record the planned wording
        provider = shown.provider if shown else None
        model = shown.model if shown else None
        if read_model is not None and self.assist is not None:
            provider, model = self.assist.provider.name, read_model
        q, slot = question_for(prompt.id)
        wanted = [slot] if slot else list(q.slots)
        got_any = any(u.slot in wanted for u in understood)
        if not got_any and s.pending_attempts + 1 >= MAX_ATTEMPTS:
            understood += [Understood(slot=w, value=None, method="unparsed") for w in wanted
                           if all(u.slot != w for u in understood)]  # fmt: skip
        session = self._append(
            {"kind": TurnKind.ANSWER, "question_id": prompt.id,
             "question_text": shown.text if shown else prompt.text, "text": text,
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

    def _resolve(
        self, prompt: Prompt, text: str, actor: Actor, s: InterviewSession
    ) -> TurnResult:
        cid = prompt.id.removeprefix(RESOLVE_PREFIX)
        finding = next((f for f in open_contradictions(fold(s)) if f.id == cid), None)
        if finding is None:
            raise WorkflowError(f"contradiction {cid} is no longer open")
        choice = pick_option(text, finding.options)
        if choice is None and not parsing.is_unknown(text):
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
        session = self._append(
            {"kind": TurnKind.RESOLUTION, "contradiction_id": cid, "question_id": prompt.id,
             "question_text": prompt.text, "text": text, "option": choice,
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

    def revise(self, question_id: str, text: str, actor: Actor) -> TurnResult:
        """Change an earlier answer. The old answer stays in the session history."""
        _require_human(actor, "revise the owner's answers")
        self._check_open()
        if question_id.partition("#")[0] not in QUESTION_BY_ID:
            known = ", ".join(QUESTION_BY_ID)
            raise ValueError(f"unknown question {question_id!r}; questions are: {known}")
        state = self.state()
        q, slot = question_for(question_id)
        prompt = Prompt(question_id, q.render(state.values, self.session().site)
                        if not slot else SLOTS[slot].followup, "question")  # fmt: skip
        understood, notes, read_model = self._read(prompt, text, state)
        ai = read_model is not None and self.assist is not None
        session = self._append(
            {"kind": TurnKind.REVISION, "question_id": question_id, "question_text": prompt.text,
             "text": text.strip(), "understood": understood,
             "provider": self.assist.provider.name if ai else None,
             "model": read_model if ai else None},
            actor,
        )  # fmt: skip
        s_ref, b_ref = self._write(session, actor, f"owner revised {question_id}")
        if not understood:
            notes.append("I could not read a new value; nothing else changed.")
        return TurnResult(s_ref, b_ref, understood=understood, prompt=self.pending(),
                          contradictions=open_contradictions(fold(self.session())),
                          notes=notes)  # fmt: skip

    def confirm(self, actor: Actor, slots: list[str] | None = None) -> list[str]:
        """The owner confirms what was understood (all pending interpretations by default)."""
        _require_human(actor, "confirm interpretations")
        self._check_open()
        pending = self.state().unconfirmed()
        chosen = pending if slots is None else [s for s in slots if s in pending]
        unknown = set(slots or []) - set(pending)
        if unknown:
            raise ValueError(f"nothing to confirm for: {', '.join(sorted(unknown))}")
        if not chosen:
            return []
        session = self._append({"kind": TurnKind.CONFIRMATION, "slots": chosen}, actor)
        self._write(session, actor, "owner confirmed interpretations")
        return chosen

    def reject(self, actor: Actor, slots: list[str], text: str | None = None) -> TurnResult:
        """The owner says an interpretation is wrong; it is removed and asked again."""
        _require_human(actor, "reject interpretations")
        self._check_open()
        state = self.state()
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
        _require_human(actor, "allow an AI provider to receive private data")
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

    def review_program(self, actor: Actor) -> tuple[ProgramBuild, list[str]]:
        """Build the program, move to PROGRAM_REVIEW and ask the owner to review it."""
        state = self.workflow.state
        if state is not WorkflowState.INTERVIEWING:
            hint = (
                " The site is not approved yet: the interview and the program can be built "
                "and checked now, but review and approval wait for the site gate."
                if Gate.SITE not in self.workflow.status().approvals
                else ""
            )
            raise TransitionNotAllowed(
                f"program review starts from INTERVIEWING; the project is in {state.value}."
                + hint
            )
        build = self.build_program(actor)
        self.workflow.transition(WorkflowState.PROGRAM_REVIEW, actor,
                                 "space program ready for the owner's review")  # fmt: skip
        event = self.workflow.request_approval(Gate.PROGRAM, build.program_ref, actor)
        return build, list(event.payload["open_reasons"])

    def reject_program(self, actor: Actor, text: str) -> ArtifactRef:
        """The owner rejects the program at review; their words are kept verbatim."""
        _require_human(actor, "reject the space program")
        if self.workflow.state is not WorkflowState.PROGRAM_REVIEW:
            raise TransitionNotAllowed(
                f"a program can be rejected in PROGRAM_REVIEW, not {self.workflow.state.value}"
            )
        if not text.strip():
            raise ValueError("say what is wrong with the program")
        session = self._append({"kind": TurnKind.PROGRAM_REJECTION, "text": text.strip()}, actor)
        _, b_ref = self._write(session, actor, "owner rejected the space program")
        self.workflow.transition(WorkflowState.INTERVIEWING, actor,
                                 f"owner rejected the program: {text.strip()}")  # fmt: skip
        return b_ref
