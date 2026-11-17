"""Milestone C: owner interview -> design brief -> space program -> program gate.

All households, answers and sites here are synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from house_ai.cad.layers import load_layer_mapping
from house_ai.domain.brief import DesignBrief, FactSourceKind
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.interview import InterviewSession, SiteContext, TurnKind
from house_ai.domain.program import (
    SpaceFunction,
    SpaceProgram,
    SpaceRelationship,
    SpaceRelationshipKind,
    Strength,
)
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.provenance import DataClassification
from house_ai.domain.units import LengthUnit
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.interview import parsing
from house_ai.interview.questions import QUESTIONS, SLOTS
from house_ai.interview.slot_types import InvalidValue, check
from house_ai.interview.state import pick_option
from house_ai.orchestration.interview import InterviewLocked, InterviewService
from house_ai.orchestration.interview_llm import LlmAssist
from house_ai.orchestration.site_ingestion import SiteConfirmation, confirm_site, ingest_site
from house_ai.orchestration.workflow import (
    ApprovalRequiresHuman,
    GateBlocked,
    TransitionNotAllowed,
    Workflow,
)
from house_ai.program.validation import blocking, validate_program
from house_ai.providers.base import DataFlowPolicy, PrivateDataFlowError
from house_ai.providers.scripted import ScriptedProvider

from .conftest import AGENT, HUMAN, REPO, SURVEY_DXF, SURVEY_LAYERS

EXAMPLE = REPO / "examples" / "interviews" / "synthetic-family"
ANSWERS = yaml.safe_load((EXAMPLE / "answers.yaml").read_text())["answers"]
FULL = SiteConfirmation(
    units=LengthUnit.METRE, elevation_units=LengthUnit.METRE, epsg=25832,
    vertical_datum="DHHN2016", vertical_epsg=7837, boundary_verified=True,
)  # fmt: skip


def _project(new_store, *, approve_site: bool = True):
    """A synthetic project with the synthetic survey; site approved by a scripted human."""
    store = new_store("family")
    doc = store.add_source(SURVEY_DXF, HUMAN, classification=DataClassification.SYNTHETIC)
    wf = Workflow(store)
    wf.transition(WorkflowState.SITE_INGESTION, AGENT, "survey received")
    result = ingest_site(store, doc.id, load_layer_mapping(SURVEY_LAYERS), AGENT)
    wf.assess_site(result.site_ref, AGENT)
    if approve_site:
        ref = confirm_site(store, "site", HUMAN, FULL)
        wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "verified")
        assert wf.assess_site(ref, AGENT) == []
        wf.approve(Gate.SITE, ref, HUMAN, "synthetic owner approves the synthetic site")
        wf.transition(WorkflowState.INTERVIEWING, AGENT, "start the interview")
    return store


def _run(svc: InterviewService, answers=ANSWERS, until: str | None = None):
    for step in answers:
        if until and step["question"] == until:
            return
        prompt = svc.pending()
        assert prompt is not None, f"interview ended before {step['question']}"
        assert prompt.id == step["question"], f"expected {step['question']}, asked {prompt.id}"
        svc.answer(step["answer"], HUMAN)


def _fact(brief: DesignBrief, fact_id: str):
    return next(f for f in brief.facts if f.id == fact_id)


@pytest.fixture
def svc(new_store):
    service = InterviewService(_project(new_store))
    service.start(AGENT)  # an agent may open the session; only the owner answers
    return service


# ------------------------------------------------------------ normal interview


def test_normal_interview_produces_a_confirmed_brief_and_a_valid_program(svc):
    _run(svc)
    assert svc.pending() is None
    session = svc.session()
    assert session.status.value == "complete"
    brief = svc.brief()
    # The owner's words are kept verbatim as owner_answer facts.
    words = {f.statement for f in brief.facts if f.key == "answer"}
    assert {a["answer"] for a in ANSWERS} <= words
    assert all(
        f.source.kind is FactSourceKind.OWNER_ANSWER for f in brief.facts if f.key == "answer"
    )
    # What was understood is an inference until the owner confirms it.
    bedrooms = _fact(brief, "f-bedrooms")
    assert (bedrooms.value, bedrooms.status) == (3, Epistemic.INFERENCE)
    assert bedrooms.source.kind is FactSourceKind.AGENT_INFERENCE
    assert brief.household == []  # only confirmed counts become members

    confirmed = svc.confirm(HUMAN)
    assert "bedrooms" in confirmed and svc.state().unconfirmed() == []
    brief = svc.brief()
    assert _fact(brief, "f-adults").status is Epistemic.VERIFIED_FACT
    assert _fact(brief, "f-open_plan").status is Epistemic.PREFERENCE
    assert len(brief.household) == 4 and brief.target_gross_area_m2 == 180.0
    assert brief.budget is not None and brief.budget.amount == 450000

    build = svc.build_program(AGENT)
    program = build.result.program
    assert blocking(build.findings) == [], [f.message for f in build.findings]
    funcs = [i.function for i in program.space_requirements]
    assert funcs.count(SpaceFunction.BEDROOM) == 3
    assert funcs.count(SpaceFunction.BATHROOM) == 2
    assert SpaceFunction.STAIR in funcs and SpaceFunction.GARAGE in funcs
    assert program.storeys == 2 and program.site_approved
    living = next(i for i in program.space_requirements if i.id == "pi-living")
    assert living.target_area_m2 == 30.0  # the owner's size, not the typical 25
    kinds = {(a.a, a.b, a.kind) for a in program.space_relationships}
    assert ("pi-kitchen", "pi-living", SpaceRelationshipKind.CONNECTED) in kinds  # open plan
    assert ("pi-bed-main", "pi-bath-ensuite", SpaceRelationshipKind.CONNECTED) in kinds
    assert ("pi-kitchen", "exterior", SpaceRelationshipKind.NEAR) in kinds  # kitchen next to garden
    # Every program item that came from an answer cites a fact that is in the brief.
    fact_ids = {f.id for f in svc.brief().facts}
    assert all(fid in fact_ids for i in program.space_requirements for fid in i.source_fact_ids)

    build, reasons = svc.review_program(AGENT)
    assert reasons == []
    wf = svc.workflow
    assert wf.state is WorkflowState.PROGRAM_REVIEW
    wf.approve(Gate.PROGRAM, build.program_ref, HUMAN, "synthetic owner approves")
    assert wf.state is WorkflowState.PROGRAM_APPROVED
    assert svc.store.verify() == []


def test_questions_are_asked_one_at_a_time_and_never_repeated(svc):
    asked = []
    for step in ANSWERS:
        prompt = svc.pending()
        asked.append(prompt.id)
        assert "\n" not in prompt.text or prompt.kind == "resolve"
        svc.answer(step["answer"], HUMAN)
    assert len(asked) == len(set(asked))
    # Questions whose condition does not hold are skipped (no lift question: nobody needs one).
    assert "q-lift" not in asked and "q-dining" not in asked


def test_an_answer_that_already_covers_a_later_question_is_not_asked_again(svc):
    svc.answer("Two adults, one child; we need 3 bedrooms and two floors.", HUMAN)
    state = svc.state()
    assert state.values["bedrooms"] == 3 and state.values["storeys"] == 2
    asked = []
    while (p := svc.pending()) is not None and len(asked) < 6:
        asked.append(p.id)
        svc.answer("not sure", HUMAN)
    assert "q-bedrooms" not in asked and "q-storeys" not in asked


# ----------------------------------------------------------- incomplete answers


def test_unknown_and_unreadable_answers_are_recorded_not_invented(svc):
    svc.answer("Two adults.", HUMAN)
    assert svc.pending().id == "q-bedrooms"
    first = svc.answer("hmm, we'll see what feels right", HUMAN)
    assert first.asked_again and svc.pending().id == "q-bedrooms"
    second = svc.answer("whatever", HUMAN)
    assert not second.asked_again and svc.pending().id != "q-bedrooms"
    st = svc.state().slots["bedrooms"]
    assert st.value is None and st.status == "unknown"
    svc.answer("Not sure yet.", HUMAN)  # bathrooms
    brief = svc.brief()
    assert _fact(brief, "f-bedrooms").status is Epistemic.UNKNOWN
    assert _fact(brief, "f-bathrooms").value is None
    build = svc.build_program(AGENT)
    codes = {f.code for f in blocking(build.findings)}
    assert "missing_information" in codes
    questions = {q.id: q for q in build.result.open_questions.questions}
    assert questions["oq-bedrooms"].blocking and questions["oq-bathrooms"].blocking
    reqs = build.result.program.space_requirements
    assert not any(i.function is SpaceFunction.BEDROOM for i in reqs)


def test_missing_room_sizes_use_typical_sizes_recorded_as_assumptions(svc):
    _run(svc, [*ANSWERS[:18], {"question": "q-sizes", "answer": "Usual is fine."}])
    svc.confirm(HUMAN)
    build = svc.build_program(AGENT)
    typical = next(a for a in build.result.assumptions.assumptions if a.id == "asm-typical-sizes")
    assert "pi-living" in typical.affects and "not building-code minimums" in typical.statement
    living = next(i for i in build.result.program.space_requirements if i.id == "pi-living")
    assert living.target_area_m2 == 25.0 and living.min_area_m2 == 16.0


# ------------------------------------------------------------- contradictions


def test_a_contradiction_is_explained_and_resolved_only_by_the_owner(svc):
    svc.answer("Me and my wife.", HUMAN)
    svc.answer("Two bedrooms.", HUMAN)
    svc.answer("One bathroom, with an en-suite.", HUMAN)
    svc.answer("One level, a bungalow. We need a lift for later.", HUMAN)
    prompt = svc.pending()
    assert prompt.kind == "resolve" and prompt.id == "resolve:c-lift-one-level"
    assert "Which do you prefer?" in prompt.text and "1." in prompt.text
    brief = svc.brief()
    c = next(c for c in brief.contradictions if c.id == "c-lift-one-level")
    assert not c.resolved and len(c.options) == 2 and c.tradeoff
    unclear = svc.answer("hmm", HUMAN)
    assert unclear.asked_again and svc.pending().id == prompt.id  # nothing applied
    svc.answer("1 - keep it on one floor", HUMAN)
    state = svc.state()
    assert state.values["lift"] is False and state.slots["lift"].status == "confirmed"
    brief = svc.brief()
    c = next(c for c in brief.contradictions if c.id == "c-lift-one-level")
    assert c.resolved and "keep it on one floor" in c.resolution
    from house_ai.domain.provenance import Actor, ActorKind

    system_actor = Actor(id="cron", kind=ActorKind.SYSTEM)
    with pytest.raises(ValueError, match="only the owner"):
        svc.answer("2", system_actor)


def test_too_few_bedrooms_for_the_household_offers_choices(svc):
    svc.answer("Two adults and three children.", HUMAN)
    svc.answer("Yes, each child gets their own room.", HUMAN)
    svc.answer("Three bedrooms.", HUMAN)
    prompt = svc.pending()
    assert prompt.id == "resolve:c-too-few-bedrooms"
    labels = [o.label for o in prompt.options]
    assert labels[0] == "Plan 4 bedrooms" and "share" in labels[1]
    svc.answer("2", HUMAN)  # let the children share
    assert svc.state().values["children_own_rooms"] is False
    assert svc.state().values["bedrooms"] == 3  # the owner's number is not changed silently


def test_deferring_a_contradiction_keeps_it_open_and_blocks_the_gate(svc):
    svc.answer("Two adults.", HUMAN)
    svc.answer("One bedroom.", HUMAN)
    svc.answer("One bathroom, en-suite please.", HUMAN)
    svc.answer("One floor. We want a lift too.", HUMAN)
    assert svc.pending().kind == "resolve"
    svc.answer("not sure yet", HUMAN)
    assert svc.pending().kind == "question"  # the interview moves on
    brief = svc.brief()
    assert [c.id for c in brief.unresolved_contradictions()] == ["c-lift-one-level"]
    build = svc.build_program(AGENT)
    assert "contradiction" in {f.code for f in blocking(build.findings)}


# ------------------------------------------------------------------ revisions


def test_changing_an_earlier_answer_keeps_the_history(svc):
    _run(svc)
    svc.confirm(HUMAN)
    before = svc.session()
    result = svc.revise("q-bedrooms", "Actually four bedrooms.", HUMAN)
    assert [u.value for u in result.understood if u.slot == "bedrooms"] == [4]
    session = svc.session()
    assert len(session.turns) == len(before.turns) + 1
    assert session.turns[-1].kind is TurnKind.REVISION
    old = [t for t in session.turns if t.question_id == "q-bedrooms"]
    assert [t.text for t in old] == ["Three bedrooms.", "Actually four bedrooms."]
    brief = svc.brief()
    assert _fact(brief, "f-bedrooms").value == 4
    assert _fact(brief, "f-bedrooms").status is Epistemic.INFERENCE  # reconfirm the change
    svc.confirm(HUMAN, ["bedrooms"])
    build = svc.build_program(AGENT)
    reqs = build.result.program.space_requirements
    beds = [i for i in reqs if i.function is SpaceFunction.BEDROOM]
    assert len(beds) == 4


def test_rejecting_an_interpretation_asks_again(svc):
    svc.answer("Two adults and two kids.", HUMAN)
    svc.reject(HUMAN, ["children"], "No, three kids.")
    prompt = svc.pending()
    assert prompt.id == "q-household#children" and prompt.text.startswith("Sorry")
    svc.answer("Three.", HUMAN)
    assert svc.state().values["children"] == 3
    rejection = next(t for t in svc.session().turns if t.kind is TurnKind.REJECTION)
    assert rejection.text == "No, three kids."
    # Coding agents can also record the owner's rejection of a proposed interpretation.
    svc.reject(AGENT, ["children"], "Actually two children.")
    assert svc.pending().id == "q-household#children"


# ------------------------------------------------------ adjacencies and areas


def test_conflicting_room_adjacencies_are_detected(svc):
    _run(svc, until="q-relationships")
    prompt = svc.pending()
    assert prompt.id == "q-relationships"
    svc.answer("The office next to the kitchen; the office away from the kitchen.", HUMAN)
    assert svc.pending().id == "resolve:c-near-and-apart"
    svc.answer("2", HUMAN)
    assert svc.state().values["relationships"] == ["office|apart|kitchen"]


def test_conflicting_hard_adjacencies_in_a_program_block(svc):
    _run(svc)
    svc.confirm(HUMAN)
    program = svc.build_program(AGENT).result.program
    clash = SpaceRelationship(
        id="adj-clash", a="pi-kitchen", b="pi-living",
        kind=SpaceRelationshipKind.SEPARATED, strength=Strength.HARD,
    )  # fmt: skip
    doc = program.model_dump()
    bad = SpaceProgram.model_validate(
        {**doc, "space_relationships": [*doc["space_relationships"], clash.model_dump()]}
    )
    found = [f for f in validate_program(bad, svc.brief()) if f.code == "adjacency_conflict"]
    assert found and found[0].severity.value == "blocking" and len(found[0].options) == 2


def test_an_unrealistic_total_area_is_infeasible_with_options(svc):
    answers = [dict(a) for a in ANSWERS]
    next(a for a in answers if a["question"] == "q-area")["answer"] = "60 m2 in total."
    _run(svc, answers)
    svc.confirm(HUMAN)
    build = svc.build_program(AGENT)
    infeasible = next(f for f in build.findings if f.code == "area_infeasible")
    assert infeasible.severity.value == "blocking"
    assert any("Raise the total" in o for o in infeasible.options)
    assert build.result.program.target_gross_area_m2 == 60.0  # not silently raised
    tiny = SiteContext(parcel_area_m2=50.0, verified=True)
    over = next(f for f in validate_program(build.result.program, svc.brief(), tiny)
                if f.code == "exceeds_parcel")  # fmt: skip
    assert over.severity.value == "blocking" and "Add a storey" in over.options


# --------------------------------------------------------- interrupt / resume


def test_an_interrupted_interview_resumes_from_the_store(new_store):
    store = _project(new_store)
    first = InterviewService(store)
    first.start(AGENT)
    _run(first, ANSWERS[:4])
    pending = first.pending().id
    # A new process: fresh store object and service.
    from house_ai.storage import ProjectStore

    again = InterviewService(ProjectStore(store.root))
    result = again.start(AGENT)
    assert "Resuming" in result.notes[0]
    assert again.pending().id == pending == ANSWERS[4]["question"]
    assert again.state().values["bedrooms"] == 3
    _run(again, ANSWERS[4:])
    assert again.pending() is None


# ------------------------------------------------------------ program review


def test_a_rejected_program_goes_back_to_the_interview_with_the_owners_words(svc):
    _run(svc)
    svc.confirm(HUMAN)
    build, _ = svc.review_program(AGENT)
    with pytest.raises(ApprovalRequiresHuman):
        svc.reject_program(AGENT, "agent tries")
    words = "No: the study must be on the garden level, not upstairs."
    svc.reject_program(HUMAN, words)
    wf = svc.workflow
    assert wf.state is WorkflowState.INTERVIEWING
    assert wf.status().approvals.get(Gate.PROGRAM) is None
    assert any(f.statement == words for f in svc.brief().facts if f.key == "program_rejection")
    last = svc.store.events()[-1]
    assert last.to_state is WorkflowState.INTERVIEWING and words in last.reason
    with pytest.raises(GateBlocked):  # not in review any more
        wf.approve(Gate.PROGRAM, build.program_ref, HUMAN, "too late")


def test_an_ai_cannot_approve_the_program(svc, tmp_path):
    _run(svc)
    svc.confirm(HUMAN)
    build, _ = svc.review_program(AGENT)
    wf = svc.workflow
    with pytest.raises(ApprovalRequiresHuman):
        wf.approve(Gate.PROGRAM, build.program_ref, AGENT, "agent approves")
    from house_ai.cli.main import main

    code = main(["workflow", "approve", str(svc.store.root), "program", "--id", "program",
                 "--approver", "claude"])  # fmt: skip
    assert code == 2  # needs an interactive terminal and a typed phrase
    assert wf.state is WorkflowState.PROGRAM_REVIEW


def test_unconfirmed_interpretations_block_the_program_gate(svc):
    _run(svc)  # nothing confirmed
    build, reasons = svc.review_program(AGENT)
    assert any("unconfirmed_interpretation" in r for r in reasons)
    with pytest.raises(GateBlocked):
        svc.workflow.approve(Gate.PROGRAM, build.program_ref, HUMAN, "too early")


def test_answers_cannot_change_once_the_program_is_approved(svc):
    _run(svc)
    svc.confirm(HUMAN)
    build, _ = svc.review_program(AGENT)
    svc.workflow.approve(Gate.PROGRAM, build.program_ref, HUMAN, "approved")
    with pytest.raises(InterviewLocked):
        svc.revise("q-bedrooms", "Five bedrooms.", HUMAN)


# ------------------------------------------------------------ unverified site


def test_the_interview_runs_before_the_site_is_approved_but_review_waits(new_store):
    store = _project(new_store, approve_site=False)
    assert Workflow(store).state is WorkflowState.SITE_NEEDS_CONFIRMATION
    svc = InterviewService(store)
    result = svc.start(AGENT)
    assert any("not confirmed" in n for n in result.notes)
    site = svc.session().site
    assert site is not None and not site.verified and site.parcel_area_m2 == pytest.approx(1400)
    _run(svc, until="q-slope")
    assert "not confirmed the site yet" in svc.pending().text
    _run(svc, ANSWERS[5:])
    svc.confirm(HUMAN)
    build = svc.build_program(AGENT)
    assert not build.result.program.site_approved
    assert any(a.id == "asm-site-unverified" for a in build.result.assumptions.assumptions)
    with pytest.raises(TransitionNotAllowed, match="site is not approved"):
        svc.review_program(AGENT)


# ---------------------------------------------------------------- AI provider


def test_llm_values_are_used_only_with_consent_and_only_if_valid(svc):
    provider = ScriptedProvider(
        [json.dumps({"values": [{"slot": "adults", "value": 2}, {"slot": "children",
                                                                   "value": "many"}]})]
    )  # fmt: skip
    svc.assist = LlmAssist(provider, svc.policy())
    # Without the owner's consent nothing is sent; the parser result stands.
    result = svc.answer("The two of us, plus our little ones", HUMAN)
    assert provider.requests == [] and result.asked_again is False
    svc.consent(HUMAN, "scripted")
    svc.assist = LlmAssist(provider, svc.policy())
    svc.reject(HUMAN, ["children"])
    svc.answer("our little ones, you know", HUMAN)
    assert len(provider.requests) == 1
    with pytest.raises(ApprovalRequiresHuman):
        svc.consent(AGENT, "scripted")


def test_llm_output_is_validated_and_stays_an_inference(svc):
    svc.consent(HUMAN, "scripted")
    provider = ScriptedProvider([
        json.dumps({"values": [{"slot": "adults", "value": 2}, {"slot": "elders", "value": -1}]}),
    ])  # fmt: skip
    svc.assist = LlmAssist(provider, svc.policy())
    result = svc.answer("Just us, the happy pair.", HUMAN)  # the parser cannot read this
    got = {u.slot: (u.value, u.method) for u in result.understood}
    assert got["adults"] == (2, "llm:scripted") and "elders" not in got  # -1 is invalid
    assert _fact(svc.brief(), "f-adults").status is Epistemic.INFERENCE
    request = provider.requests[0]
    assert request.classification is None or request.classification.value == "private"


def test_private_data_never_reaches_a_provider_without_consent():
    provider = ScriptedProvider(['{"values": []}'])
    assist = LlmAssist(provider, DataFlowPolicy())
    with pytest.raises(PrivateDataFlowError):
        assist.extract("How many bedrooms?", ["bedrooms"], "three")
    assert provider.requests == []


def test_garbage_from_the_llm_is_ignored(svc):
    svc.consent(HUMAN, "scripted")
    svc.assist = LlmAssist(ScriptedProvider(["not json at all"]), svc.policy())
    result = svc.answer("the usual crowd", HUMAN)
    assert result.asked_again and result.understood == []


# ------------------------------------------------------------------- parsers


SAMPLES = {
    "q-household": ["2 adults and 3 children", "my husband, me and my father", "just me"],
    "q-bathrooms": ["three bathrooms, no en-suite", "2"],
    "q-kitchen": ["we rarely cook; smells must stay out; a pantry please"],
    "q-parking": ["no car", "two cars in a garage with an EV charger"],
    "q-outdoor": ["terrace, roof terrace and a pool", "none"],
    "q-accessibility": ["my mother uses a wheelchair; we need a lift"],
    "q-relationships": ["guest room away from the main bedroom; office near the entrance"],
    "q-sizes": ["kitchen 18 m2 and bigger bedrooms"],
    "q-budget": ["€ 1.200.000", "300,000 dollars"],
    "q-area": ["about 220 m²"],
}


def test_deterministic_parsers_only_produce_valid_slot_values():
    by_id = {q.id: q for q in QUESTIONS}
    for qid, texts in SAMPLES.items():
        for text in texts:
            for slot, value in by_id[qid].parse(text).items():
                check(slot, value)
    assert by_id["q-household"].parse("my husband, me and my father")["elders"] == 1
    assert by_id["q-relationships"].parse(SAMPLES["q-relationships"][0])["relationships"] == [
        "guest|apart|main_bedroom",
        "office|near|entry",
    ]
    assert by_id["q-budget"].parse("€ 1.200.000")["budget"] == "1200000 EUR"
    with pytest.raises(InvalidValue):
        check("bedrooms", "three")
    assert parsing.is_unknown("I don't know yet") and not parsing.is_unknown("four")
    assert set(SLOTS) >= {s for q in QUESTIONS for s in q.slots}


# ------------------------------------------------------------------------ CLI


def test_cli_interview_commands(tmp_path, capsys, new_store, monkeypatch):
    from house_ai.cli.main import main

    store = _project(new_store)
    d = str(store.root)
    assert main(["interview", "start", d, "--actor", "agent:claude-code"]) == 0
    out = capsys.readouterr().out
    assert "Who will live in the house?" in out
    # Agent can record owner answers in a non-interactive shell, while consent and approvals
    # still require an interactive human terminal (exit code 2).
    assert main(["interview", "consent", d, "anthropic", "--actor", "human:owner"]) == 2
    assert main(["interview", "answer", d, "Two adults.", "--actor", "agent:claude-code"]) == 0
    assert "Adults: 2" in capsys.readouterr().out
    assert main(["interview", "next", d]) == 0
    assert "bedrooms" in capsys.readouterr().out
    assert main(["interview", "summary", d]) == 0
    assert "understood from your answer, please confirm" in capsys.readouterr().out
    out_dir = tmp_path / "export"
    assert main(["program", "build", d, "--actor", "agent:claude-code", "--out",
                 str(out_dir)]) == 0  # fmt: skip
    for name in ("design_brief.yaml", "space_program.yaml", "assumptions.yaml",
                 "open_questions.yaml", "interview-summary.md", "program-review.md"):
        assert (out_dir / name).is_file(), name  # fmt: skip
    DesignBrief.model_validate(yaml.safe_load((out_dir / "design_brief.yaml").read_text()))
    assert main(["project", "verify", d]) == 0
    session = InterviewSession.model_validate_json(
        Path(store.root / "artifacts" / "interview_session" / "interview" / "v0002.json")
        .read_text()
    )
    assert session.turns[0].text == "Two adults."
    assert store.refs(K.INTERVIEW_SESSION)


def test_committed_example_outputs_match_the_pipeline():
    import runpy

    example = runpy.run_path(str(EXAMPLE / "run_example.py"))
    assert example["main"](["--check"]) == 0


def test_cli_interactive_run_confirms_each_answer_and_can_stop(new_store, monkeypatch, capsys):
    from house_ai.cli.main import main

    store = _project(new_store)
    replies = iter(["Two adults and one child.", "y", "Three bedrooms.", "n", "Two.", "y",
                    ":summary", ":quit"])  # fmt: skip
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *_: next(replies))
    assert main(["interview", "run", str(store.root), "--owner", "example-owner"]) == 0
    out = capsys.readouterr().out
    assert "Did I understand that correctly?" not in out  # asked via input(), not printed
    svc = InterviewService(store)
    state = svc.state()
    assert state.slots["adults"].status == "confirmed" and state.values["children"] == 1
    assert state.values["bedrooms"] == 2 and state.slots["bedrooms"].status == "confirmed"
    rejected = [t for t in svc.session().turns if t.kind is TurnKind.REJECTION]
    assert rejected and rejected[0].slots == ["bedrooms"]
    assert "Your answers are saved" in out


def test_an_empty_confirmation_confirms_nothing(svc, monkeypatch):
    svc.answer("Two adults.", HUMAN)
    assert svc.confirm(HUMAN, []) == []
    assert svc.state().slots["adults"].status == "inference"


def test_cli_run_never_confirms_more_than_the_owner_was_shown(new_store, monkeypatch, capsys):
    from house_ai.cli.main import main

    store = _project(new_store)
    replies = iter(["Two adults.", "ok", "not sure", "y", ":quit"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *_: next(replies))
    assert main(["interview", "run", str(store.root), "--owner", "example-owner"]) == 0
    assert InterviewService(store).state().slots["adults"].status == "inference"


def test_a_number_inside_the_reply_is_not_taken_as_the_option(svc):
    svc.answer("Two adults and two children.", HUMAN)
    svc.answer("Each child their own room.", HUMAN)
    svc.answer("Two bedrooms.", HUMAN)
    assert svc.pending().id == "resolve:c-too-few-bedrooms"
    svc.answer("keep 2 bedrooms", HUMAN)  # the words of option 3, not "option 2"
    state = svc.state()
    assert state.values["children_own_rooms"] is True  # option 2 was not applied
    assert state.resolutions["c-too-few-bedrooms"][0].option == 2
    assert pick_option("1 - keep it on one floor", state_options()) == 0
    assert pick_option("bedrooms", state_options()) is None  # ambiguous: ask again


def state_options():
    from house_ai.interview.rules import Option

    return (Option("Plan 3 bedrooms"), Option("Let the children share bedrooms"),
            Option("Keep 2 bedrooms; we will manage"))  # fmt: skip


# --------------------------------------------------- agent-first CLI workflow


def test_agent_first_end_to_end_workflow_with_persian_english_and_mixed_answers(
    tmp_path, capsys, new_store
):
    """End-to-end agent-driven interview without any API key, covering English, Persian,
    mixed-language answers, custom follow-up questions, confirmations, revisions,
    contradiction resolution, program generation, and human approval gates.
    """
    from house_ai.cli.main import main

    store = _project(new_store)
    d = str(store.root)

    # 1. Agent inspects project status and starts interview.
    assert main(["project", "status", d, "--json"]) == 0
    proj_status = json.loads(capsys.readouterr().out)
    assert proj_status["state"] == "INTERVIEWING"
    assert proj_status["site"]["verified"] is True

    assert main(["interview", "start", d, "--json", "--actor", "agent:gemini"]) == 0
    start_payload = json.loads(capsys.readouterr().out)
    assert start_payload["next_prompt"]["id"] == "q-household"

    # 2. Owner gives the free-form opening statement out of checklist order;
    #    the agent records the exact words and proposes structured interpretations.
    opening_words = (
        "I want a modern house on my steep land, with parking from the road "
        "and a large living room."
    )
    assert (
        main(
            [
                "interview",
                "answer",
                d,
                opening_words,
                "--set",
                "style=modern hillside architecture",
                "--set",
                "slope_strategy=split_level",
                "--set",
                "entry_at_road=true",
                "--set",
                "cars=2",
                "--set",
                "parking_type=garage",
                "--set",
                "room_sizes=living=36",
                "--json",
                "--actor",
                "agent:gemini",
            ]
        )
        == 0
    )
    ans1 = json.loads(capsys.readouterr().out)
    understood_slots = {u["slot"]: (u["value"], u["method"]) for u in ans1["understood"]}
    assert understood_slots["slope_strategy"] == ("step_down", "agent:gemini")
    assert understood_slots["room_sizes"] == (["living=36"], "agent:gemini")

    # 3. Agent asks an adaptive follow-up question outside the 30-question checklist and
    #    records the owner's mixed Persian/English answer verbatim.
    followup_q = "How should the road-level garage connect to the main living level on the slope?"
    followup_a = (
        "پارکینگ هم‌سطح جاده در بالا باشد و با پله داخلی و آسانسور به نشیمن پایین وصل شود "
        "(entry from road level with internal stairs and lift)."
    )
    assert (
        main(
            [
                "interview",
                "answer",
                d,
                followup_a,
                "--question",
                "q-follow-road-parking",
                "--question-text",
                followup_q,
                "--topic",
                "site",
                "--set",
                "lift=true",
                "--set",
                "storeys=2",
                "--json",
                "--actor",
                "agent:gemini",
            ]
        )
        == 0
    )
    capsys.readouterr()

    # 4. Agent records Persian household answer via --set without requiring the deterministic
    #    regex parser to parse Persian words.
    persian_household = "ما ۴ نفر هستیم: من و همسرم و دو فرزند، هر بچه اتاق خودش را می‌خواهد."
    assert (
        main(
            [
                "interview",
                "answer",
                d,
                persian_household,
                "--question",
                "q-household",
                "--set",
                "adults=2",
                "--set",
                "children=2",
                "--set",
                "elders=0",
                "--set",
                "household_size=4",
                "--set",
                "children_own_rooms=true",
                "--json",
                "--actor",
                "agent:gemini",
            ]
        )
        == 0
    )
    capsys.readouterr()

    # 5. Owner initially says 2 bedrooms -> triggers contradiction c-too-few-bedrooms!
    assert (
        main(
            [
                "interview",
                "answer",
                d,
                "فعلاً ۲ اتاق خواب",
                "--question",
                "q-bedrooms",
                "--set",
                "bedrooms=2",
                "--json",
                "--actor",
                "agent:gemini",
            ]
        )
        == 0
    )
    ans_bed = json.loads(capsys.readouterr().out)
    assert ans_bed["next_prompt"]["id"] == "resolve:c-too-few-bedrooms"

    # 6. Agent resolves the contradiction after asking the owner, recording their choice.
    assert (
        main(
            [
                "interview",
                "resolve",
                d,
                "c-too-few-bedrooms",
                "حق با شماست، ۳ اتاق خواب در نظر بگیرید (Plan 3 bedrooms).",
                "--option",
                "1",
                "--json",
                "--actor",
                "agent:gemini",
            ]
        )
        == 0
    )
    res_payload = json.loads(capsys.readouterr().out)
    assert res_payload["understood"][0]["value"] == 3

    # 7. Fill remaining checklist slots via agent CLI and test confirm + revise.
    remaining_text = (
        "سه سرویس بهداشتی و حمام مستر، لاندری جدا، آشپزخانه کثیف و تمیز، "
        "دفتر کار، تراس رو به منظره، حدود ۲۴۰ متر."
    )
    assert (
        main(
            [
                "interview",
                "answer",
                d,
                remaining_text,
                "--question",
                "q-bathrooms",
                "--set",
                "bathrooms=3",
                "--set",
                "ensuite=true",
                "--set",
                "open_plan=true",
                "--set",
                "cooking=frequent",
                "--set",
                "kitchen_layout=semi_open",
                "--set",
                "kitchen_smell_separate=true",
                "--set",
                "pantry=true",
                "--set",
                "dining=separate_room",
                "--set",
                "guest_accommodation=none",
                "--set",
                "guest_frequency=sometimes",
                "--set",
                "workspaces=1",
                "--set",
                "office_quiet=true",
                "--set",
                "laundry_room=true",
                "--set",
                "storage_room=true",
                "--set",
                "ev_charging=true",
                "--set",
                "outdoor=terrace,garden",
                "--set",
                "accessibility=future_ready",
                "--set",
                "accessible_ground_suite=false",
                "--set",
                "privacy=high",
                "--set",
                "bedrooms_separate=true",
                "--set",
                "relationships=kitchen|near|dining,office|apart|living",
                "--set",
                "light_wishes=morning sun in kitchen and south views in living",
                "--set",
                "cross_ventilation=true",
                "--set",
                "target_area=240",
                "--set",
                "budget=unknown",
                "--set",
                "priorities=views,daylight,privacy",
                "--set",
                "future_expansion=false",
                "--set",
                "prayer_room=false",
                "--set",
                "gathering_space=true",
                "--json",
                "--actor",
                "agent:gemini",
            ]
        )
        == 0
    )
    capsys.readouterr()

    # Check checklist status: all 30 questions should be covered!
    assert main(["interview", "checklist", d, "--json"]) == 0
    cl = json.loads(capsys.readouterr().out)
    assert cl["counts"]["remaining_questions"] == 0

    # 8. Owner confirms interpretations, then revises bedrooms to 4.
    assert (
        main(
            [
                "interview",
                "confirm",
                d,
                "--text",
                "بله، همه موارد درست است (Yes, confirmed).",
                "--json",
                "--actor",
                "agent:gemini",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        main(
            [
                "interview",
                "revise",
                d,
                "q-bedrooms",
                "در واقع ۴ اتاق خواب می‌خواهیم که یکی برای مهمان باشد.",
                "--set",
                "bedrooms=4",
                "--set",
                "guest_accommodation=room",
                "--json",
                "--actor",
                "agent:gemini",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "interview",
                "confirm",
                d,
                "bedrooms",
                "guest_accommodation",
                "--text",
                "بله، ۴ اتاق خواب تایید است.",
                "--json",
                "--actor",
                "agent:gemini",
            ]
        )
        == 0
    )
    capsys.readouterr()

    # Verify history preserved both the original answer and the revision, plus the custom follow-up.
    svc = InterviewService(store)
    brief = svc.brief()
    assert any(
        f.source.ref == "followup-site-q-follow-road-parking" and f.statement == followup_a
        for f in brief.facts
    )
    bed_turns = [t for t in svc.session().turns if t.question_id == "q-bedrooms"]
    assert len(bed_turns) == 2

    # 9. Build and request review of the space program.
    assert main(["program", "review", d, "--actor", "agent:gemini"]) == 0
    capsys.readouterr()
    assert Workflow(store).state is WorkflowState.PROGRAM_REVIEW

    # 10. Agent must NEVER be able to approve the program gate.
    assert (
        main(
            [
                "workflow",
                "approve",
                d,
                "program",
                "--id",
                "program",
                "--approver",
                "agent:gemini",
            ]
        )
        == 2
    )
    assert Workflow(store).state is WorkflowState.PROGRAM_REVIEW


def test_steep_hillside_site_records_engineering_assumptions_and_warns_on_flat_pad(new_store):
    """On a steep unverified site like projects/my-house (~600 m2, ~12.4 m relief),
    the space program builder records hillside engineering assumptions and warns if a flat
    pad is chosen.
    """
    store = _project(new_store, approve_site=False)
    svc = InterviewService(store)
    svc.start(AGENT)
    _run(svc)
    # Override site context on the latest session to match a steep synthetic relief parcel.
    steep_site = SiteContext(
        site_ref=store.latest(K.SITE, "site"),
        verified=False,
        parcel_area_m2=520.0,
        relief_m=14.5,
        mean_slope_pct=55.0,
        frontage_m=18.5,
    )
    svc.revise(
        "q-slope",
        "Keep it on a flat pad even though the land is steep.",
        AGENT,
        interpreted={"slope_strategy": "flat"},
    )
    svc.confirm(AGENT)
    brief = svc.brief()
    brief_ref = store.latest(K.DESIGN_BRIEF, "brief")
    assert brief_ref is not None
    from house_ai.program.builder import build_program

    result = build_program(
        brief, site=steep_site, brief_ref=brief_ref, created_at=store.clock()
    )
    asm_ids = {a.id for a in result.assumptions.assumptions}
    assert "asm-site-unverified" in asm_ids
    assert "asm-hillside-engineering" in asm_ids
    hillside_asm = next(
        a for a in result.assumptions.assumptions if a.id == "asm-hillside-engineering"
    )
    for keyword in (
        "split-level",
        "road-level",
        "excavation",
        "retaining walls",
        "drainage",
        "structural",
    ):
        assert keyword in hillside_asm.statement

    findings = validate_program(result.program, brief, steep_site)
    codes = {f.code for f in findings}
    assert "steep_site_flat_pad" in codes


def test_agent_inspects_synthetic_project_without_modifying_it(tmp_path, capsys):
    """Verify status and blockers report an unverified steep site in
    SITE_NEEDS_CONFIRMATION without modifying any files in the project.
    """
    from house_ai.cli.main import main
    from house_ai.domain.geometry import Polygon2D
    from house_ai.domain.site import Epistemic, Site, SiteCoordinates
    from house_ai.domain.workflow import WorkflowState
    from house_ai.orchestration.workflow import Workflow
    from house_ai.storage import ProjectStore

    proj_dir = tmp_path / "synthetic-steep"
    store = ProjectStore.init(
        proj_dir,
        project_id="synthetic-steep",
        name="Synthetic Steep Project",
        classification="synthetic",  # type: ignore[arg-type]
        actor=HUMAN,
    )
    wf = Workflow(store)
    wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "ingesting")
    # Put a site that needs verification (unverified boundary, local coords only)
    site = Site(
        id="site",
        project_id="synthetic-steep",
        name="Synthetic Steep Site",
        classification="synthetic",  # type: ignore[arg-type]
        coordinates=SiteCoordinates(),
        boundary=Polygon2D.rectangle(0, 0, 20, 26),
        boundary_status=Epistemic.INFERENCE,
        provenance={"created_at": store.clock(), "created_by": HUMAN, "method": "test"},  # type: ignore[arg-type]
    )
    s_ref = store.put(K.SITE, "site", site, HUMAN)
    wf.assess_site(s_ref, HUMAN)

    before_events = len(store.events())
    assert main(["project", "status", str(proj_dir), "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["state"] == "SITE_NEEDS_CONFIRMATION"
    assert status["site"]["verified"] is False
    assert len(status["site"]["verification_blockers"]) >= 1
    assert main(["interview", "status", str(proj_dir), "--json"]) == 0
    istatus = json.loads(capsys.readouterr().out)
    assert istatus["session_status"] == "not_started"
    assert len(store.events()) == before_events

