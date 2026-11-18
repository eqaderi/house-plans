"""Workflow and CLI tests for `house-ai plan propose` (Task S7-08)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from house_ai.cli.main import main
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore

OWNER = Actor(kind=ActorKind.HUMAN, id="example-owner")
AGENT = Actor(kind=ActorKind.AGENT, id="gemini")


def _load_project(tmp_path: Path, name: str = "synthetic-hillside") -> ProjectStore:
    d = tmp_path / name
    assert (
        main(
            [
                "example",
                "load",
                str(d),
                "--name",
                name,
                "--project-id",
                name,
                "--actor",
                "human:example",
            ]
        )
        == 0
    )
    return ProjectStore(d)


def _approve_site_and_program(store: ProjectStore) -> Workflow:
    wf = Workflow(store)
    wf.approve(Gate.SITE, store.latest(ArtifactKind.SITE, "site"), OWNER, "synthetic site ok")
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview done (synthetic)")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "program ready")
    wf.approve(Gate.PROGRAM, store.latest(ArtifactKind.SPACE_PROGRAM, "program"), OWNER, "ok")
    return wf


def _make_valid_proposal(store: ProjectStore, tmp_path: Path) -> Path:
    program = store.get(store.latest_of_kind(ArtifactKind.SPACE_PROGRAM)[-1], SpaceProgram)
    # Target linear or two_wing strategy
    doc = {
        "schema_version": "0.1.0",
        "id": "prop-linear-day-night",
        "project_id": store.manifest().id,
        "name": "Linear Day-Night Concept",
        "intent": "Linear bar orienting day spaces along the contour with master suite separated",
        "zones": [
            {
                "id": "z-day",
                "name": "Day zone",
                "program_item_ids": ["pi-entry", "pi-living", "pi-dining", "pi-kitchen"],
            }
        ],
        "level_assignments": [
            {"program_item_id": item.id, "level_id": "lv-entry"}
            for item in program.space_requirements
        ],
        "adjacency_graph": [
            {
                "id": "padj-living-dining",
                "a": "pi-living",
                "b": "pi-dining",
                "kind": "connected",
                "strength": "soft",
                "weight": 2.0,
            }
        ],
        "outdoor_links": [
            {
                "id": "ol-living-terrace",
                "program_item_id": "pi-living",
                "kind": "terrace",
            }
        ],
        "target_strategy": "linear",
    }
    p_path = tmp_path / "valid_proposal.yaml"
    p_path.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return p_path


def test_plan_propose_exploratory_mode(tmp_path):
    store = _load_project(tmp_path)
    proposal_file = _make_valid_proposal(store, tmp_path)
    out = tmp_path / "exploratory-concepts"

    code = main(
        [
            "plan",
            "propose",
            str(store.root),
            str(proposal_file),
            "--out",
            str(out),
            "--exploratory",
            "--json",
            "--actor",
            "agent:gemini",
        ]
    )
    assert code == 0

    # Exploratory: nothing recorded in project store
    assert store.latest_of_kind(ArtifactKind.CONCEPT_PROPOSAL) == []
    assert store.latest_of_kind(ArtifactKind.PLAN) == []

    # Exported to disk
    assert out.is_dir()
    plan_file = out / "concept-linear-prop-linear-day-night" / "exploratory" / "plan.json"
    assert plan_file.is_file()
    plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
    assert plan_data["generation"]["parameters"]["proposal_id"] == "prop-linear-day-night"


def test_plan_propose_stored_workflow(tmp_path):
    store = _load_project(tmp_path)
    _approve_site_and_program(store)
    proposal_file = _make_valid_proposal(store, tmp_path)
    out = tmp_path / "stored-concepts"

    code = main(
        [
            "plan",
            "propose",
            str(store.root),
            str(proposal_file),
            "--out",
            str(out),
            "--json",
            "--actor",
            "agent:gemini",
        ]
    )
    assert code == 0

    # Workflow moved to PLAN_REVIEW
    wf = Workflow(store)
    assert wf.state is WorkflowState.PLAN_REVIEW

    # Proposal stored as artifact
    proposals = store.latest_of_kind(ArtifactKind.CONCEPT_PROPOSAL)
    assert len(proposals) == 1
    stored_prop = store.get(proposals[0], ConceptProposal)
    assert stored_prop.id == "prop-linear-day-night"

    # Plan stored and its provenance inputs reference the proposal artifact
    plans = store.latest_of_kind(ArtifactKind.PLAN)
    assert len(plans) >= 1
    plan = store.get(plans[0], PlanVersion)
    assert plan.generation.parameters["proposal_id"] == "prop-linear-day-night"
    input_kinds = {i.kind for i in plan.provenance.inputs}
    assert ArtifactKind.CONCEPT_PROPOSAL in input_kinds

    # Integrity check clean
    assert store.verify() == []


def test_plan_propose_refused_on_invalid_proposal(tmp_path, capsys):
    store = _load_project(tmp_path)
    _approve_site_and_program(store)

    # Proposal with unknown program item
    bad_proposal = tmp_path / "bad_proposal.yaml"
    bad_proposal.write_text(
        yaml.safe_dump(
            {
                "schema_version": "0.1.0",
                "id": "prop-bad",
                "project_id": store.manifest().id,
                "name": "Bad Proposal",
                "intent": "Uses invalid item",
                "level_assignments": [
                    {"program_item_id": "pi-nonexistent-room", "level_id": "lv-entry"}
                ],
            }
        ),
        encoding="utf-8",
    )

    code = main(
        [
            "plan",
            "propose",
            str(store.root),
            str(bad_proposal),
            "--actor",
            "agent:gemini",
        ]
    )
    assert code == 1
    out, _ = capsys.readouterr()
    assert "refused: proposal validation failed: unknown_program_item" in out
    assert store.latest_of_kind(ArtifactKind.CONCEPT_PROPOSAL) == []


def test_plan_propose_refused_before_program_gate_unless_exploratory(tmp_path):
    store = _load_project(tmp_path)
    proposal_file = _make_valid_proposal(store, tmp_path)

    # Without gates approved, non-exploratory propose is refused
    code = main(
        [
            "plan",
            "propose",
            str(store.root),
            str(proposal_file),
            "--actor",
            "agent:gemini",
        ]
    )
    assert code == 1


def test_proposal_never_replaces_an_owner_revised_concept(tmp_path):
    """S10-04 (ISS-31 c): a proposal targeting a revised strategy gets its own option."""
    from house_ai.orchestration.plans import PlanService

    store = _load_project(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    svc.generate(AGENT, strategies=["linear"])
    revised = svc.revise(
        "concept-linear", "Bigger kitchen please.", AGENT, ops=["area:pi-kitchen=14"]
    )
    assert revised.option.plan_ref.version == 2

    proposal = ConceptProposal.model_validate(
        yaml.safe_load(_make_valid_proposal(store, tmp_path).read_text(encoding="utf-8"))
    )
    res = svc.propose(AGENT, proposal)
    (opt,) = res.generated
    assert opt.plan_ref.id == "concept-linear-prop-linear-day-night"
    assert opt.plan_ref.version == 1

    latest = store.get(store.latest(ArtifactKind.PLAN, "concept-linear"), PlanVersion)
    assert latest.change_request.text == "Bigger kitchen please."
    assert "area:pi-kitchen=14" in latest.generation.revision_ops
    assert store.verify() == []


def test_proposal_option_ids_stay_valid_and_distinct():
    from house_ai.generation.generator import option_id_for

    assert option_id_for("two_wing") == "concept-two-wing"
    assert option_id_for("two_wing", "prop-a") == "concept-two-wing-prop-a"
    long_a, long_b = "p-" + "a" * 60, "p-" + "a" * 59 + "b"
    a, b = option_id_for("corridor_free", long_a), option_id_for("corridor_free", long_b)
    assert len(a) <= 64 and len(b) <= 64 and a != b
    assert a.startswith("concept-corridor-free-p-aaa")


def test_revision_from_a_proposal_file_records_that_proposal(tmp_path):
    """A proposal file in a revision replaces the base's proposal in the new version's
    provenance; it is stored, and the base's proposal is no longer an input."""
    from house_ai.orchestration.plans import PlanService

    store = _load_project(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    proposal_file = _make_valid_proposal(store, tmp_path)
    first = ConceptProposal.model_validate(
        yaml.safe_load(proposal_file.read_text(encoding="utf-8"))
    )
    (opt,) = svc.propose(AGENT, first).generated

    alt = first.model_copy(update={"id": "prop-linear-alt", "name": "Alternative concept"})
    alt_file = tmp_path / "alt_proposal.yaml"
    alt_file.write_text(yaml.safe_dump(alt.model_dump(mode="json")), encoding="utf-8")
    revised = svc.revise(
        opt.plan_ref.id, "Try the alternative concept.", AGENT, ops=[f"proposal:{alt_file}"]
    )

    plan = store.get(revised.option.plan_ref, PlanVersion)
    assert plan.generation.parameters["proposal_id"] == "prop-linear-alt"
    proposal_inputs = [
        r.id for r in plan.provenance.inputs if r.kind is ArtifactKind.CONCEPT_PROPOSAL
    ]
    assert proposal_inputs == ["prop-linear-alt"]
    stored = {r.id for r in store.latest_of_kind(ArtifactKind.CONCEPT_PROPOSAL)}
    assert stored == {"prop-linear-day-night", "prop-linear-alt"}
    assert store.verify() == []
