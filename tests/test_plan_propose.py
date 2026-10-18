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
            {"program_item_id": item.id, "level_id": "lv-entry"} for item in program.items
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
    plan_file = out / "concept-linear" / "exploratory" / "plan.json"
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

    # Workflow moved to CONCEPT_REVIEW
    wf = Workflow(store)
    assert wf.state is WorkflowState.CONCEPT_REVIEW

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
