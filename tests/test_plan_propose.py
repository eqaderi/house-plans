"""Workflow and CLI tests for `house-ai plan propose` (Task S7-08)."""

from __future__ import annotations

import contextlib
import io
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from house_ai.cli.main import main
from house_ai.domain.integrity import circulation_graph
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.plans import PlanService
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore

OWNER = Actor(kind=ActorKind.HUMAN, id="example-owner")
AGENT = Actor(kind=ActorKind.AGENT, id="gemini")
#: CP-SAT deterministic time for solves whose test asserts only ids, versions and provenance:
#: the 2D proposal solve at the default 4.0 takes about 7 s, at 1.0 about 2.5 s. The solver
#: runs one worker with a fixed seed, so a feasible solve here is feasible on every rerun.
QUICK = 1.0


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


def _snapshot(root: Path) -> dict[Path, bytes]:
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _cli(argv: list[str]) -> tuple[int, str]:
    """Run the CLI, returning its exit code and stdout (module fixtures have no capsys)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


@dataclass(frozen=True)
class Template:
    """A project folder built once per module. Never write to it: copy it with `copy`."""

    root: Path

    @property
    def store(self) -> ProjectStore:
        return ProjectStore(self.root / "synthetic-hillside")

    def copy(self, tmp_path: Path) -> ProjectStore:
        shutil.copytree(self.root, tmp_path / "copy")
        return ProjectStore(tmp_path / "copy" / "synthetic-hillside")


@pytest.fixture(scope="module")
def stored_proposal(tmp_path_factory):
    """`plan propose` of the valid proposal on an approved project, at the default time."""
    tmp = tmp_path_factory.mktemp("stored-proposal")
    store = _load_project(tmp)
    _approve_site_and_program(store)
    proposal_file = _make_valid_proposal(store, tmp)
    code, out = _cli(
        [
            "plan",
            "propose",
            str(store.root),
            str(proposal_file),
            "--out",
            str(tmp / "stored-concepts"),
            "--json",
            "--actor",
            "agent:gemini",
        ]
    )
    return Template(tmp), code, json.loads(out)


def test_plan_propose_exploratory_mode(tmp_path):
    store = _load_project(tmp_path)
    proposal_file = _make_valid_proposal(store, tmp_path)
    out = tmp_path / "exploratory-concepts"
    before = _snapshot(store.root)

    code = main(
        [
            "plan",
            "propose",
            str(store.root),
            str(proposal_file),
            "--out",
            str(out),
            "--exploratory",
            "--time",
            str(QUICK),
            "--json",
            "--actor",
            "agent:gemini",
        ]
    )
    assert code == 0

    # Exploratory: nothing recorded in the project store, not one byte.
    assert _snapshot(store.root) == before
    assert store.latest_of_kind(ArtifactKind.CONCEPT_PROPOSAL) == []
    assert store.latest_of_kind(ArtifactKind.PLAN) == []

    # Exported to disk
    plan_file = out / "concept-linear-prop-linear-day-night" / "exploratory" / "plan.json"
    assert plan_file.is_file()
    plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
    assert plan_data["generation"]["parameters"]["proposal_id"] == "prop-linear-day-night"


def test_plan_propose_stored_workflow(stored_proposal):
    template, code, out = stored_proposal
    store = template.store
    assert code == 0
    assert out["proposal_id"] == "prop-linear-day-night"
    assert [o["option_id"] for o in out["options"]] == ["concept-linear-prop-linear-day-night"]

    # Workflow moved to PLAN_REVIEW
    assert Workflow(store).state is WorkflowState.PLAN_REVIEW

    # Proposal stored as artifact
    proposals = store.latest_of_kind(ArtifactKind.CONCEPT_PROPOSAL)
    assert len(proposals) == 1
    stored_prop = store.get(proposals[0], ConceptProposal)
    assert stored_prop.id == "prop-linear-day-night"

    # Exactly one plan, from the proposal's target strategy, recording the proposal artifact.
    (plan_ref,) = store.latest_of_kind(ArtifactKind.PLAN)
    assert (plan_ref.id, plan_ref.version) == ("concept-linear-prop-linear-day-night", 1)
    plan = store.get(plan_ref, PlanVersion)
    assert plan.strategy == "linear"
    assert plan.generation.parameters["proposal_id"] == "prop-linear-day-night"
    assert [r for r in plan.provenance.inputs if r.kind is ArtifactKind.CONCEPT_PROPOSAL] == [
        proposals[0]
    ]

    # The proposal was applied: one Space per program item, every one on lv-entry (its level
    # assignments), and living connected to the terrace (its hard outdoor link).
    program = store.get(store.latest(ArtifactKind.SPACE_PROGRAM, "program"), SpaceProgram)
    model = plan.model
    assert {s.program_item_id for s in model.spaces} == {i.id for i in program.space_requirements}
    assert len(model.spaces) == len(program.space_requirements)
    assert [lv.id for lv in model.levels] == ["lv-entry"]
    assert {s.level_id for s in model.spaces} == {"lv-entry"}
    terraces = {s.id for s in model.spaces if s.function.value == "terrace"}
    assert terraces == {"sp-terrace"}
    assert "sp-terrace" in circulation_graph(model)["sp-living"]

    # Integrity check clean
    assert store.verify() == []


def test_plan_propose_refused_on_invalid_proposal(tmp_path, capsys):
    store = _load_project(tmp_path)
    _approve_site_and_program(store)

    before = _snapshot(store.root)

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
    assert _snapshot(store.root) == before


def test_plan_propose_refused_before_program_gate_unless_exploratory(tmp_path, capsys):
    store = _load_project(tmp_path)
    proposal_file = _make_valid_proposal(store, tmp_path)
    before = _snapshot(store.root)
    capsys.readouterr()

    # Without gates approved, non-exploratory propose is refused and writes nothing; the
    # exploratory run of the same proposal is test_plan_propose_exploratory_mode.
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
    out = capsys.readouterr().out
    assert out.startswith(
        "refused: plan generation needs the owner's approved site and program "
        "(PROGRAM_APPROVED or later); the project is in SITE_INGESTION."
    )
    assert "Use --exploratory to preview plan options without storing them." in out
    assert _snapshot(store.root) == before
    assert Workflow(store).status().approvals == {}


def test_proposal_never_replaces_an_owner_revised_concept(tmp_path):
    """S10-04 (ISS-31 c): a proposal targeting a revised strategy gets its own option."""
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
    res = svc.propose(AGENT, proposal, deterministic_time=QUICK)
    (opt,) = res.generated
    assert opt.plan_ref.id == "concept-linear-prop-linear-day-night"
    assert opt.plan_ref.version == 1

    assert [r.version for r in store.refs(ArtifactKind.PLAN, "concept-linear")] == [1, 2]
    latest = store.get(store.latest(ArtifactKind.PLAN, "concept-linear"), PlanVersion)
    assert latest.change_request.text == "Bigger kitchen please."
    assert latest.generation.revision_ops == ["area:pi-kitchen=14"]
    assert store.verify() == []


def test_proposal_option_ids_stay_valid_and_distinct():
    from house_ai.generation.generator import option_id_for

    assert option_id_for("two_wing") == "concept-two-wing"
    assert option_id_for("two_wing", "prop-a") == "concept-two-wing-prop-a"
    long_a, long_b = "p-" + "a" * 60, "p-" + "a" * 59 + "b"
    a, b = option_id_for("corridor_free", long_a), option_id_for("corridor_free", long_b)
    assert len(a) <= 64 and len(b) <= 64 and a != b
    assert a.startswith("concept-corridor-free-p-aaa")


PROPOSED_ID = "concept-linear-prop-linear-day-night"


def _valid_proposal(store: ProjectStore, tmp_path: Path) -> ConceptProposal:
    path = _make_valid_proposal(store, tmp_path)
    return ConceptProposal.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def _alternative(first: ConceptProposal) -> ConceptProposal:
    """The same topology under another proposal id."""
    return first.model_copy(update={"id": "prop-linear-alt", "name": "Alternative concept"})


@pytest.fixture(scope="module")
def proposed(tmp_path_factory) -> Template:
    """An approved project with one option generated from the valid proposal, at QUICK time
    (revisions inherit it); the ISS-42 tests assert provenance only, never the layout."""
    tmp = tmp_path_factory.mktemp("proposed")
    store = _load_project(tmp)
    _approve_site_and_program(store)
    (opt,) = PlanService(store).propose(
        AGENT, _valid_proposal(store, tmp), deterministic_time=QUICK
    ).generated
    assert opt.plan_ref.id == PROPOSED_ID
    return Template(tmp)


@pytest.fixture(scope="module")
def revised_to_alternative(proposed, tmp_path_factory) -> Template:
    """`proposed`, then a revision naming the alternative proposal's file."""
    tmp = tmp_path_factory.mktemp("revised-to-alternative")
    store = proposed.copy(tmp)
    alt_file = _proposal_file(tmp, _alternative(_valid_proposal(store, tmp)))
    PlanService(store).revise(
        PROPOSED_ID, "Try the alternative concept.", AGENT, ops=[f"proposal:{alt_file}"]
    )
    return Template(tmp / "copy")


def _proposal_file(tmp_path: Path, proposal: ConceptProposal) -> Path:
    path = tmp_path / f"{proposal.id}-{proposal.name.replace(' ', '-')}.yaml"
    path.write_text(yaml.safe_dump(proposal.model_dump(mode="json")), encoding="utf-8")
    return path


def _proposal_inputs(plan: PlanVersion) -> list:
    return [r for r in plan.provenance.inputs if r.kind is ArtifactKind.CONCEPT_PROPOSAL]


def test_revision_from_a_proposal_file_records_that_proposal(revised_to_alternative):
    """ISS-42: a proposal file in a revision replaces the base's proposal in the new
    version's provenance; it is stored, and the base's proposal is no longer an input."""
    store = revised_to_alternative.store
    assert [r.version for r in store.refs(ArtifactKind.PLAN, PROPOSED_ID)] == [1, 2]
    base = store.get(store.refs(ArtifactKind.PLAN, PROPOSED_ID)[0], PlanVersion)
    assert [r.id for r in _proposal_inputs(base)] == ["prop-linear-day-night"]

    plan = store.get(store.latest(ArtifactKind.PLAN, PROPOSED_ID), PlanVersion)
    assert plan.change_request.text == "Try the alternative concept."
    (alt_ref,) = _proposal_inputs(plan)
    assert (alt_ref.id, alt_ref.version) == ("prop-linear-alt", 1)
    assert plan.generation.parameters["proposal_id"] == "prop-linear-alt"
    assert store.get(alt_ref, ConceptProposal).name == "Alternative concept"
    stored = {r.id for r in store.latest_of_kind(ArtifactKind.CONCEPT_PROPOSAL)}
    assert stored == {"prop-linear-day-night", "prop-linear-alt"}
    assert store.verify() == []


def test_revision_from_a_changed_proposal_with_the_same_id_records_the_new_version(
    proposed, tmp_path
):
    """ISS-42: a proposal file that keeps the base's proposal id but changes its content is
    stored as version 2 of that proposal, and the revision records version 2."""
    store = proposed.copy(tmp_path)
    first = _valid_proposal(store, tmp_path)
    changed = first.model_copy(update={"name": "Day-night concept, renamed"})
    revised = PlanService(store).revise(
        PROPOSED_ID,
        "Use the renamed concept.",
        AGENT,
        ops=[f"proposal:{_proposal_file(tmp_path, changed)}"],
    )

    plan = store.get(revised.option.plan_ref, PlanVersion)
    (ref,) = _proposal_inputs(plan)
    assert (ref.id, ref.version) == ("prop-linear-day-night", 2)
    assert store.get(ref, ConceptProposal).name == "Day-night concept, renamed"
    assert [r.version for r in store.refs(ArtifactKind.CONCEPT_PROPOSAL, first.id)] == [1, 2]
    assert store.verify() == []


def test_revising_a_version_that_records_the_wrong_proposal_is_refused(
    revised_to_alternative, tmp_path
):
    """ISS-42: a version stored before the fix, generated from one proposal but recording
    another, is not silently revised from the recorded one; naming the file again works."""
    from house_ai.orchestration.plans import PlanWorkflowError

    store = revised_to_alternative.copy(tmp_path)
    svc = PlanService(store)
    alt_file = _proposal_file(tmp_path, _alternative(_valid_proposal(store, tmp_path)))
    base_ref, revised_ref = store.refs(ArtifactKind.PLAN, PROPOSED_ID)
    plan = store.get(revised_ref, PlanVersion)
    assert [r.id for r in _proposal_inputs(plan)] == ["prop-linear-alt"]
    # What the defect stored: the file's proposal generated it, the base's is recorded.
    (base_proposal,) = _proposal_inputs(store.get(base_ref, PlanVersion))
    wrong = plan.model_copy(
        update={
            "provenance": plan.provenance.model_copy(
                update={
                    "inputs": [
                        base_proposal if r.kind is ArtifactKind.CONCEPT_PROPOSAL else r
                        for r in plan.provenance.inputs
                    ]
                }
            )
        }
    )
    wrong_ref = store.put(ArtifactKind.PLAN, PROPOSED_ID, wrong, AGENT, reason="as stored")
    before = _snapshot(store.root)

    with pytest.raises(PlanWorkflowError, match="generated from proposal 'prop-linear-alt'"):
        svc.revise(PROPOSED_ID, "Make the kitchen bigger.", AGENT, ops=["area:pi-kitchen=14"])
    assert store.refs(ArtifactKind.PLAN, PROPOSED_ID)[-1] == wrong_ref
    assert _snapshot(store.root) == before

    again = svc.revise(PROPOSED_ID, "Keep the alternative.", AGENT, ops=[f"proposal:{alt_file}"])
    assert again.option.plan_ref.version == 4
    fixed = store.get(again.option.plan_ref, PlanVersion)
    assert [r.id for r in _proposal_inputs(fixed)] == ["prop-linear-alt"]
    assert store.verify() == []
