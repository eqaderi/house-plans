"""What agents read: project status, the site summary, the interview turn result and checklist.

Key-set tests pin the ``--json`` shapes at the orchestration interface (ADR 0011 §5):
existing keys keep their names; outputs may gain keys and lose none. All data is synthetic.
"""

from __future__ import annotations

import pytest

from house_ai.cad.layers import load_layer_mapping
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.provenance import DataClassification
from house_ai.domain.units import LengthUnit
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.interview import InterviewService
from house_ai.orchestration.project_status import project_status
from house_ai.orchestration.site import SiteService
from house_ai.orchestration.site_ingestion import SiteConfirmation
from house_ai.orchestration.workflow import Workflow

from .conftest import AGENT, HUMAN, SURVEY_DXF, SURVEY_LAYERS, example_doc

FULL = SiteConfirmation(
    units=LengthUnit.METRE, elevation_units=LengthUnit.METRE, epsg=25832,
    vertical_datum="DHHN2016", vertical_epsg=7837, boundary_verified=True,
)  # fmt: skip

#: ``project status --json`` keys before part 4 (ADR 0011 §5: none may be lost).
PROJECT_STATUS_KEYS = {
    "allowed_transitions", "approvals", "gate_available", "gate_status", "interview",
    "latest_artifacts", "next_human_command", "owner_statements_count",
    "pending_approval_requests", "project", "site", "stale_approvals", "state",
    "superseded_approvals",
}  # fmt: skip
INTERVIEW_KEYS = {"exists", "status", "turn_count", "unconfirmed_slots"}
#: The site summary: the checklist's keys, which include project status's.
SITE_SUMMARY_KEYS = {
    "site_ref", "verified", "parcel_area_m2", "relief_m", "mean_slope_pct", "frontage_m",
    "verification_blockers", "blockers", "steep_hillside", "hillside_considerations",
}  # fmt: skip
SURVEY_BLOCKER_CODES = [
    "source_units", "horizontal_crs", "elevation_units", "vertical_datum", "boundary_unverified",
]  # fmt: skip


def _render(action) -> str:
    return f"<{action.action.value} {action.gate.value}>"


@pytest.fixture
def ingested(new_store):
    """The synthetic survey ingested, its facts not yet confirmed."""
    store = new_store("family")
    doc = store.add_source(SURVEY_DXF, HUMAN, classification=DataClassification.SYNTHETIC)
    SiteService(store).ingest(doc.id, load_layer_mapping(SURVEY_LAYERS), AGENT)
    return store


def test_project_status_keeps_every_key_and_reads_the_site_summary(ingested):
    info = project_status(ingested).to_json(_render)

    assert set(info) == PROJECT_STATUS_KEYS
    assert set(info["interview"]) == INTERVIEW_KEYS
    assert info["interview"] == {"exists": False, "status": "not_started", "turn_count": 0,
                                 "unconfirmed_slots": 0}  # fmt: skip
    assert (info["state"], info["gate_available"]) == ("SITE_NEEDS_CONFIRMATION", None)
    site = info["site"]
    assert set(site) == SITE_SUMMARY_KEYS
    assert (site["parcel_area_m2"], site["relief_m"], site["mean_slope_pct"]) == (
        1400.0, 5.0, 11.18,
    )
    assert (site["frontage_m"], site["verified"], site["steep_hillside"]) == (40.0, False, False)
    assert [b["code"] for b in site["blockers"]] == SURVEY_BLOCKER_CODES
    assert site["verification_blockers"] == [b["message"] for b in site["blockers"]]
    # Blockers and the next human action come from the gate status.
    assert info["gate_status"]["gate"] == "site"
    assert info["next_human_command"] == "<confirm_site site>"


def test_project_status_without_a_site_has_no_site_summary(new_store):
    info = project_status(new_store()).to_json(_render)

    assert set(info) == PROJECT_STATUS_KEYS
    assert info["site"] is None
    assert (info["gate_status"], info["next_human_command"]) == (None, None)


def test_project_status_reports_a_stale_approval_from_the_gate_status(new_store):
    store = new_store()
    wf = Workflow(store)
    s_ref = store.put(K.SITE, "site", example_doc("site.yaml"), HUMAN)
    SiteService(store).assess(s_ref, AGENT)
    wf.approve(Gate.SITE, s_ref, HUMAN, "site approved")
    program = SpaceProgram.model_validate(example_doc("space_program.yaml"))
    p_ref = store.put(K.SPACE_PROGRAM, "program", program, HUMAN)
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "review")
    wf.approve(Gate.PROGRAM, p_ref, HUMAN, "program approved")
    assert project_status(store).to_json(_render)["approvals"]["program"]["stale"] is False

    v2 = program.model_copy(update={"target_gross_area_m2": 300.0})
    store.put(K.SPACE_PROGRAM, "program", v2, HUMAN)

    info = project_status(store).to_json(_render)
    assert info["approvals"]["program"]["stale"] is True
    assert info["approvals"]["program"]["latest_version"] == 2
    assert info["stale_approvals"] == ["program"]


def test_status_checklist_and_ai_context_read_one_site_summary(ingested):
    svc = InterviewService(ingested)
    svc.start(AGENT)  # the session records the site while it is unconfirmed
    site_ref = SiteService(ingested).confirm("site", HUMAN, FULL).site_ref
    Workflow(ingested).approve(Gate.SITE, site_ref, HUMAN, "synthetic owner approves")

    status_site = project_status(ingested).to_json(_render)["site"]
    checklist_site = svc.checklist().to_json()["site"]

    assert status_site == checklist_site
    assert status_site["verified"] is True and status_site["blockers"] == []
    assert status_site["site_ref"]["version"] == site_ref.version
    assert '"status": "confirmed by the owner"' in svc.ai_context()


# ------------------------------------------------- interview turn result and checklist

TURN_KEYS = {
    "session_ref", "brief_ref", "understood", "asked_again", "notes", "contradictions",
    "next_prompt",
}  # fmt: skip
PROMPT_KEYS = {"id", "kind", "text"}
#: The richest of today's shapes (the turn result's).
INTERPRETATION_KEYS = {"slot", "label", "value", "display", "method", "status"}
#: The richest of today's shapes (the checklist's).
CONTRADICTION_KEYS = {"id", "statement", "tradeoff", "slots", "options"}
CHECKLIST_KEYS = {
    "checklist", "contradictions", "counts", "custom_turns", "missing_required_slots",
    "owner_statements", "project_id", "session_status", "site", "suggested_next", "turn_count",
    "unconfirmed", "workflow_state",
}  # fmt: skip
COUNT_KEYS = {
    "total_checklist_questions", "applicable_questions", "covered_questions",
    "remaining_questions", "confirmed_slots", "unconfirmed_slots", "unknown_slots",
    "open_contradictions",
}  # fmt: skip
ITEM_KEYS = {"answered", "applicable", "covered", "id", "question", "slots", "topic"}
SLOT_ENTRY_KEYS = {
    "choices", "display", "kind", "label", "method", "required", "slot", "status", "value",
}  # fmt: skip
CUSTOM_TURN_KEYS = {"seq", "question_id", "question_text", "text", "understood"}
TOO_FEW_BEDROOMS_OPTIONS = [
    {"option": 1, "label": "Plan 3 bedrooms", "updates": {"bedrooms": 3}},
    {"option": 2, "label": "Let the children share bedrooms",
     "updates": {"children_own_rooms": False}},
    {"option": 3, "label": "Keep 2 bedrooms; we will manage", "updates": {}},
]  # fmt: skip


@pytest.fixture
def interview(ingested):
    svc = InterviewService(ingested)
    svc.start(AGENT)
    return svc


def test_the_checklist_before_the_interview_starts(ingested):
    info = InterviewService(ingested).checklist().to_json()

    assert set(info) == CHECKLIST_KEYS
    assert (info["session_status"], info["turn_count"]) == ("not_started", 0)
    assert set(info["counts"]) == COUNT_KEYS
    assert (info["counts"]["total_checklist_questions"],
            info["counts"]["applicable_questions"]) == (30, 24)  # fmt: skip
    assert set(info["site"]) == SITE_SUMMARY_KEYS
    assert info["suggested_next"] == {"id": "q-household", "kind": "question",
                                      "text": info["checklist"][0]["question"]}  # fmt: skip


def test_the_turn_result_and_the_checklist_keep_their_keys(interview):
    turn = interview.answer("Two adults and two children.", HUMAN).to_json()

    assert set(turn) == TURN_KEYS
    assert set(turn["next_prompt"]) == PROMPT_KEYS
    info = interview.checklist().to_json()
    assert set(info) == CHECKLIST_KEYS
    assert (info["session_status"], info["turn_count"]) == ("active", 1)
    assert all(set(item) == ITEM_KEYS for item in info["checklist"])
    assert all(set(s) == SLOT_ENTRY_KEYS for item in info["checklist"] for s in item["slots"])
    household = next(i for i in info["checklist"] if i["id"] == "q-household")
    adults = next(s for s in household["slots"] if s["slot"] == "adults")
    assert (adults["value"], adults["status"], adults["kind"], adults["required"]) == (
        2, "inference", "int", True,
    )
    assert info["suggested_next"] == turn["next_prompt"]


def test_a_contradiction_has_one_shape_wherever_it_appears(interview):
    interview.answer("Two adults and two children.", HUMAN)
    interview.answer("Each child their own room.", HUMAN)
    turn = interview.answer("Two bedrooms.", HUMAN).to_json()

    listed = interview.checklist().to_json()["contradictions"]
    assert turn["contradictions"] == listed
    (contradiction,) = listed
    assert set(contradiction) == CONTRADICTION_KEYS
    assert contradiction["id"] == "c-too-few-bedrooms"
    assert contradiction["options"] == TOO_FEW_BEDROOMS_OPTIONS
    assert contradiction["slots"] == [
        "bedrooms", "adults", "children", "elders", "children_own_rooms",
    ]  # fmt: skip


def test_an_interpretation_has_one_shape_wherever_it_appears(interview):
    turn = interview.answer("Two adults.", HUMAN).to_json()
    interview.answer("We need a lift.", AGENT, question_id="q-follow-access",
                     question_text="How do you reach the upper level?", topic="access",
                     interpreted={"lift": "true"})  # fmt: skip

    info = interview.checklist().to_json()
    adults_in_turn = next(u for u in turn["understood"] if u["slot"] == "adults")
    adults_unconfirmed = next(u for u in info["unconfirmed"] if u["slot"] == "adults")
    (custom,) = info["custom_turns"]
    (lift,) = custom["understood"]
    assert set(custom) == CUSTOM_TURN_KEYS
    for item in (adults_in_turn, adults_unconfirmed, lift):
        assert set(item) == INTERPRETATION_KEYS
    assert adults_in_turn == adults_unconfirmed == {
        "slot": "adults", "label": "Adults", "value": 2, "display": "2", "method": "parser",
        "status": "inference",
    }  # fmt: skip
    assert (lift["value"], lift["method"], lift["status"]) == (True, "agent:claude-code",
                                                              "inference")  # fmt: skip


def test_a_slot_marked_unknown_is_an_interpretation_with_status_unknown(interview):
    turn = interview.answer("Not sure yet.", AGENT, question_id="q-budget",
                            interpreted={"budget": None}).to_json()  # fmt: skip

    (budget,) = turn["understood"]
    assert (budget["slot"], budget["value"], budget["status"]) == ("budget", None, "unknown")
