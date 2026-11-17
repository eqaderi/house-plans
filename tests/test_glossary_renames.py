"""S11: saved names renamed to GLOSSARY.md terms (ADR 0025).

Records written before the rename load unchanged and keep their hashes; new
records use the new names. The fixture store was written by the pre-rename
code (tests/fixtures/pre_adr0025/README.md).
"""

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from house_ai.cli.main import main
from house_ai.domain.brief import DesignBrief
from house_ai.domain.interview import InterviewSession, current_question_id, current_slot
from house_ai.domain.model import HouseModel, Level
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.workflow import EventType, WorkflowState
from house_ai.interview.state import fold
from house_ai.orchestration.interview import InterviewService
from house_ai.orchestration.plans import PlanService
from house_ai.program.builder import Facts
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import content_hash

from .conftest import AGENT, HUMAN
from .test_plan_workflow import _approve_site_and_program, _load

FIXTURE = Path(__file__).parent / "fixtures" / "pre_adr0025" / "store"
OLD_PROGRAM_KEYS = {"items", "adjacencies", "levels", "site_verified"}
NEW_PROGRAM_KEYS = {"space_requirements", "space_relationships", "storeys", "site_approved"}


@pytest.fixture
def old_store(tmp_path) -> ProjectStore:
    root = tmp_path / "pre-adr0025"
    shutil.copytree(FIXTURE, root)
    return ProjectStore(root)


def _files(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_pre_rename_records_load_unchanged_and_keep_their_hashes(old_store):
    before = _files(old_store.root)
    assert old_store.verify() == []
    refs = [ref for kind in ArtifactKind for ref in old_store.refs(kind)]
    assert len(refs) == 17
    for ref in refs:
        assert content_hash(old_store.get(ref)) == ref.sha256
    assert _files(old_store.root) == {k: v for k, v in before.items() if k != ".lock"}


def test_an_old_space_program_reads_with_the_glossary_names(old_store):
    (ref,) = old_store.refs(ArtifactKind.SPACE_PROGRAM)
    program = old_store.get(ref, SpaceProgram)
    assert program.schema_version == "0.1.0"
    assert len(program.space_requirements) == 11
    assert len(program.space_relationships) == 6
    assert program.storeys == 2
    assert program.site_approved is False
    assert program.usability.double_bed_space_requirement_ids == ["pi-bed-main"]
    assert program.usability.single_bed_space_requirement_ids == [
        "pi-bed-child-1",
        "pi-bed-child-2",
    ]
    saved = program.model_dump(mode="json")
    assert OLD_PROGRAM_KEYS <= set(saved) and not NEW_PROGRAM_KEYS & set(saved)
    assert "double_bed_program_item_ids" in saved["usability"]


def test_a_new_space_program_is_written_with_the_glossary_names(old_store):
    (ref,) = old_store.refs(ArtifactKind.SPACE_PROGRAM)
    old = old_store.get(ref, SpaceProgram)
    fields = {name: getattr(old, name) for name in SpaceProgram.model_fields}
    new = SpaceProgram(**{**fields, "schema_version": "0.2.0"})
    saved = new.model_dump(mode="json")
    assert NEW_PROGRAM_KEYS <= set(saved) and not OLD_PROGRAM_KEYS & set(saved)
    assert "double_bed_space_requirement_ids" in saved["usability"]
    assert content_hash(SpaceProgram.model_validate(saved)) == content_hash(new)
    assert content_hash(new) != ref.sha256


def test_a_program_cannot_give_a_field_under_both_names(old_store):
    (ref,) = old_store.refs(ArtifactKind.SPACE_PROGRAM)
    doc = old_store.get(ref, SpaceProgram).model_dump(mode="json")
    with pytest.raises(ValidationError, match="not both"):
        SpaceProgram.model_validate({**doc, "storeys": 2})


def test_old_state_names_read_as_the_current_states(old_store):
    events = old_store.events()
    assert [e.to_state for e in events if e.type is EventType.TRANSITION] == [
        WorkflowState.SITE_INGESTION,
        WorkflowState.SITE_NEEDS_CONFIRMATION,
        WorkflowState.SITE_INGESTION,
        WorkflowState.INTERVIEWING,
        WorkflowState.PLAN_GENERATION,
        WorkflowState.PLAN_REVIEW,
        WorkflowState.INTERVIEWING,
    ]
    lines = (old_store.root / "events.jsonl").read_text().splitlines()
    assert '"to_state":"CONCEPT_REVIEW"' in lines[-2]
    assert json.loads(lines[-2])["to_state"] == events[-2].model_dump(mode="json")["to_state"]
    assert json.loads(lines[-1])["from_state"] == events[-1].model_dump(mode="json")["from_state"]
    assert WorkflowState("SITE_NEEDS_VERIFICATION") is WorkflowState.SITE_NEEDS_CONFIRMATION


def test_new_events_use_the_new_state_names_and_the_chain_holds(old_store):
    old_store.append_event(
        EventType.TRANSITION,
        AGENT,
        from_state=WorkflowState("CONCEPT_REVIEW"),
        to_state=WorkflowState.PLAN_GENERATION,
        reason="synthetic",
    )
    last = (old_store.root / "events.jsonl").read_text().splitlines()[-1]
    assert '"from_state":"PLAN_REVIEW"' in last and '"to_state":"PLAN_GENERATION"' in last
    assert old_store.verify() == []


def test_the_cli_accepts_an_old_state_name(store):
    store.append_event(
        EventType.TRANSITION, AGENT, from_state=WorkflowState.NEW_PROJECT,
        to_state=WorkflowState.SITE_INGESTION, reason="synthetic",
    )  # fmt: skip
    code = main(
        ["workflow", "transition", str(store.root), "SITE_NEEDS_VERIFICATION",
         "--reason", "synthetic", "--actor", "agent:claude-code"]
    )  # fmt: skip
    assert code == 0
    assert store.events()[-1].to_state is WorkflowState.SITE_NEEDS_CONFIRMATION
    assert '"to_state":"SITE_NEEDS_CONFIRMATION"' in (store.root / "events.jsonl").read_text()


def test_an_old_interview_reads_the_floors_slot_as_storeys(old_store):
    ref = old_store.latest(ArtifactKind.INTERVIEW_SESSION, "interview")
    state = fold(old_store.get(ref, InterviewSession))
    assert "floors" not in state.slots
    assert state.slots["storeys"].value == 2
    assert state.slots["storeys"].status == "confirmed"
    assert state.answered("q-storeys")
    brief = old_store.get(old_store.latest(ArtifactKind.DESIGN_BRIEF, "brief"), DesignBrief)
    assert [f.key for f in brief.facts if f.id == "f-floors"] == ["floors"]
    assert Facts(brief).get("storeys") == 2


def test_old_slot_and_question_names_are_accepted_as_input(old_store):
    assert current_slot("floors") == "storeys"
    assert current_question_id("q-floors") == "q-storeys"
    assert current_question_id("q-floors#floors") == "q-storeys#storeys"
    svc = InterviewService(old_store)
    svc.revise("floors", "Three storeys after all.", HUMAN)
    assert svc.state().slots["storeys"].value == 3
    session = svc.session()
    assert session.turns[-1].question_id == "q-storeys"
    assert [u.slot for u in session.turns[-1].understood] == ["storeys"]


def test_storeys_are_counted_from_level_elevations():
    def count(*elevations):
        levels = [Level(id=f"l{i}", name=f"L{i}", elevation_m=z) for i, z in enumerate(elevations)]
        model = HouseModel(id="m", name="m", coordinate_system_id="local", levels=levels)
        return model.storey_count

    assert count(0.0) == 1
    assert count(0.0, -3.0) == 2
    assert count(0.0, 2.8) == 2  # within the 0.3 m tolerance of a whole storey
    assert count(0.0, -1.4) == 1  # a split level shares the storey
    assert count(0.0, -1.5, -3.0, -4.5) == 2  # four split levels in two storeys
    assert count(0.0, 3.0, 6.0) == 3


def test_the_program_asks_for_storeys_and_the_plan_derives_its_levels(tmp_path):
    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    program = svc.inputs(exploratory=True).program
    assert program.provenance.method == "program_from_brief"
    assert program.storeys == 2
    outcome = svc.generate(AGENT, strategies=["split_walkout"], exploratory=True)
    (generated,) = outcome.generated
    model = generated.candidate.plan.model
    assert len(model.levels) == 3
    assert model.storey_count == 2
    metrics = {m.metric: m.value for m in generated.report.metrics}
    assert metrics["level_count"] == 3 and metrics["storey_count"] == 2
    assert "storey_count_differs" not in {v.code for v in generated.report.violations}
    assert not [a for a in model.assumptions if a.id == "asm-gen-requested-storeys"]
