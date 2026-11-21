"""Tests for Stage S4: reviewer bundle export, revision ops round-trip, and gate boundaries."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from house_ai.cli.human import command_for, renderer
from house_ai.cli.main import main
from house_ai.constants.evaluations import REQUEST_NOT_MET_PREFIX, REQUESTED_AREA_TOLERANCE_M2
from house_ai.constants.reviewer import (
    APPROVAL_GATES,
    GATE_PLAN,
    GATE_PROGRAM,
    GATE_SITE,
    REVIEWER_BUNDLE_FILENAME,
    REVIEWER_BUNDLE_SCHEMA_VERSION,
)
from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind
from house_ai.domain.revision_ops import (
    RevisionComment,
    RevisionOp,
    RevisionOpsFile,
    RevisionVerb,
)
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.plans import PlanService
from house_ai.orchestration.reviewer_bundle import (
    build_reviewer_bundle,
    export_reviewer_bundle,
    gate_actions,
)
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore

OWNER = Actor(kind=ActorKind.HUMAN, id="test-owner")
AGENT = Actor(kind=ActorKind.AGENT, id="agent:gemini")


def _setup_project(tmp_path: Path) -> ProjectStore:
    """Create a synthetic project store with approved site and program, and generated plan."""
    project_dir = tmp_path / "synthetic-hillside"
    assert (
        main(
            [
                "example",
                "load",
                str(project_dir),
                "--name",
                "synthetic-hillside",
                "--project-id",
                "synthetic-hillside",
                "--actor",
                "human:test-owner",
            ]
        )
        == 0
    )
    store = ProjectStore(project_dir)
    wf = Workflow(store)
    wf.approve(Gate.SITE, store.latest(ArtifactKind.SITE, "site"), OWNER, "site verified")
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview started")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "program ready")
    prog_ref = store.latest(ArtifactKind.SPACE_PROGRAM, "program")
    wf.approve(Gate.PROGRAM, prog_ref, OWNER, "program ok")

    # Generate at least one plan
    plan_service = PlanService(store)
    plan_service.generate(AGENT, strategies=["compact"], seed=42)
    return store


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> ProjectStore:
    """`_setup_project` once per module. Tests that write work on ``_copy``; the others
    assert the store is unchanged."""
    return _setup_project(tmp_path_factory.mktemp("bundle"))


def _copy(store: ProjectStore, tmp_path: Path) -> ProjectStore:
    return ProjectStore(shutil.copytree(store.root, tmp_path / store.root.name))


def test_revision_ops_model_and_cli_conversion() -> None:
    """RevisionOpsFile validates structured ops and converts them to CLI strings."""
    ops_file = RevisionOpsFile(
        project="synthetic-hillside",
        option="compact",
        plan_version=1,
        verbatim_request="Make the kitchen 18m2 and keep it separated from living",
        author="homeowner:alice",
        operations=[
            RevisionOp(op_type=RevisionVerb.AREA, target="pi-kitchen", value=18.0),
            RevisionOp(op_type=RevisionVerb.SEPARATE, target="pi-kitchen,pi-living"),
        ],
        comments=[
            RevisionComment(
                id="c-001",
                element_id="sp-kitchen-1",
                element_kind="space",
                text="Kitchen should face the morning light",
            )
        ],
    )

    cli_ops = ops_file.to_cli_ops()
    assert cli_ops == ["area:pi-kitchen=18.0", "separate:pi-kitchen,pi-living"]

    data = ops_file.model_dump(mode="json")
    assert data["schema_version"] == REVIEWER_BUNDLE_SCHEMA_VERSION
    assert len(data["operations"]) == 2
    assert len(data["comments"]) == 1

    restored = RevisionOpsFile.model_validate(data)
    assert restored.project == "synthetic-hillside"
    assert restored.plan_version == 1
    assert restored.operations[0].value == 18.0


def test_reviewer_bundle_is_strictly_read_only(project: ProjectStore, tmp_path: Path) -> None:
    """Building and exporting the bundle never alters the ProjectStore or event log."""
    store = project

    # Record baseline store state
    initial_verification = store.verify()
    assert initial_verification == []
    initial_event_count = len(store.events())
    initial_plan_count = len(store.latest_of_kind(ArtifactKind.PLAN))

    # Build bundle in memory
    bundle = build_reviewer_bundle(store, render=renderer(store.project_id))
    assert bundle["schema_version"] == REVIEWER_BUNDLE_SCHEMA_VERSION
    assert bundle["project"]["name"] == "synthetic-hillside"
    assert bundle["site"] is not None
    assert bundle["program"] is not None
    assert [(p["option_id"], p["version"]) for p in bundle["plans"]] == [("concept-compact", 1)]

    # Verify store is untouched
    mid_verification = store.verify()
    assert mid_verification == []
    assert len(store.events()) == initial_event_count
    assert len(store.latest_of_kind(ArtifactKind.PLAN)) == initial_plan_count

    # Export bundle to disk
    out_dir = tmp_path / "bundle_export"
    bundle_file = export_reviewer_bundle(store, out_dir, render=renderer(store.project_id))
    assert bundle_file.exists()
    assert bundle_file.name == REVIEWER_BUNDLE_FILENAME

    # Re-verify store remains untouched after file export
    post_verification = store.verify()
    assert post_verification == []
    assert len(store.events()) == initial_event_count
    assert len(store.latest_of_kind(ArtifactKind.PLAN)) == initial_plan_count


def test_reviewer_bundle_shows_the_commands_the_cli_renders(new_store) -> None:
    """The bundle receives each human command from the CLI's one renderer (ADR 0029).

    That every rendered command parses is tested in test_next_human_action.py.
    """
    store = new_store("synthetic-hillside")
    gates = build_reviewer_bundle(store, render=renderer("synthetic-hillside"))["gates"]

    shown = {
        (name, key): gate[key]
        for name, gate in gates.items()
        for key in ("confirm_command", "approve_command")
        if key in gate
    }
    assert shown == {
        (gate.value, key): command_for(action, "synthetic-hillside")
        for gate, keyed in gate_actions(store).items()
        for key, action in keyed.items()
    }
    assert len(shown) == 5  # site confirm, and one approve per gate
    assert gates[GATE_SITE]["confirm_command"] == (
        "house-ai site confirm synthetic-hillside --id site "
        "--epsg <epsg-code> --vertical-datum <datum> --confirmer <your-name>"
    )


def test_reviewer_bundle_approval_commands_and_no_mutation(project: ProjectStore) -> None:
    """Reviewer bundle includes CLI commands for human gates and no mutation endpoints (S4-23)."""
    store = project
    events = len(store.events())
    bundle = build_reviewer_bundle(store, render=renderer(store.project_id))
    assert len(store.events()) == events

    gates = bundle["gates"]
    for gate_name in APPROVAL_GATES:
        assert gate_name in gates
        assert "approve_command" in gates[gate_name]
        assert "house-ai workflow approve" in gates[gate_name]["approve_command"]
        assert "description" in gates[gate_name]

    # Site gate and program gate are approved in this fixture
    assert gates[GATE_SITE]["approved"] is True
    assert gates[GATE_PROGRAM]["approved"] is True
    assert gates[GATE_PLAN]["approved"] is False

    # Check plans in bundle
    plans = bundle["plans"]
    assert len(plans) == 1
    first_plan = plans[0]
    assert first_plan["option_id"] == "concept-compact"
    assert first_plan["version"] == 1
    assert first_plan["is_exploratory"] is False
    assert "plan" in first_plan
    assert "evaluation" in first_plan
    assert "svg" in first_plan
    assert first_plan["svg"] is not None
    assert "<svg" in first_plan["svg"]


def test_cli_reviewer_export_and_plan_export_bundle(project: ProjectStore, tmp_path: Path) -> None:
    """CLI export commands write valid bundle.json without modifying the store."""
    store = project
    events_before = len(store.events())

    out_1 = tmp_path / "export_1"
    assert main(["reviewer", "export", str(store.root), "--out", str(out_1)]) == 0
    bundle_file_1 = out_1 / REVIEWER_BUNDLE_FILENAME
    assert bundle_file_1.exists()

    data_1 = json.loads(bundle_file_1.read_text(encoding="utf-8"))
    assert data_1["schema_version"] == REVIEWER_BUNDLE_SCHEMA_VERSION
    assert data_1["project"]["name"] == "synthetic-hillside"

    out_2 = tmp_path / "export_2"
    assert main(["plan", "export-bundle", str(store.root), "--out", str(out_2)]) == 0
    bundle_file_2 = out_2 / REVIEWER_BUNDLE_FILENAME
    assert bundle_file_2.exists()
    # Both commands export the same bundle.
    assert json.loads(bundle_file_2.read_text(encoding="utf-8")) == data_1

    # Store must not have any new events
    reloaded_store = ProjectStore(store.root)
    assert len(reloaded_store.events()) == events_before
    assert reloaded_store.verify() == []


def test_cli_plan_revise_from_file_round_trip(project: ProjectStore, tmp_path: Path) -> None:
    """Exported revision ops file replays through plan revise-from-file (S4-22)."""
    store = _copy(project, tmp_path)

    # 1. Create a revision ops file targeting the compact plan v1
    ops_file = RevisionOpsFile(
        project=store.project_id,
        option="concept-compact",
        plan_version=1,
        verbatim_request="Increase kitchen to 18 m2",
        author="homeowner:owner",
        operations=[
            RevisionOp(op_type=RevisionVerb.AREA, target="pi-kitchen", value=18.0),
        ],
    )
    ops_path = tmp_path / "my_ops.json"
    ops_path.write_text(ops_file.model_dump_json(indent=2), encoding="utf-8")

    # 2. Run plan revise-from-file
    out_dir = tmp_path / "revised_out"
    cmd = [
        "plan",
        "revise-from-file",
        str(store.root),
        str(ops_path),
        "--out",
        str(out_dir),
        "--actor",
        "agent:gemini",
    ]
    ret = main(cmd)
    assert ret == 0, "plan revise-from-file failed"

    # 3. Verify a new plan version v2 was generated and stored
    plan_refs = store.refs(ArtifactKind.PLAN, "concept-compact")
    assert [r.version for r in plan_refs] == [1, 2]
    v1, v2 = (store.get(r, PlanVersion) for r in plan_refs)
    assert v2.parent == plan_refs[0]
    assert v2.change_request.text == "Increase kitchen to 18 m2"
    assert v2.generation.revision_ops == ops_file.to_cli_ops() == ["area:pi-kitchen=18.0"]

    # Check revision report exists
    rev_refs = store.latest_of_kind(ArtifactKind.REVISION_REPORT)
    assert [r.id for r in rev_refs] == ["rev-concept-compact-v2"]
    rev_report = store.get(rev_refs[-1])
    assert rev_report.requested_change == "Increase kitchen to 18 m2"
    before = v1.model.space("sp-kitchen").area_m2
    after = v2.model.space("sp-kitchen").area_m2
    (kitchen,) = [c for c in rev_report.area_changes if c.space_id == "sp-kitchen"]
    assert kitchen.before_m2 == pytest.approx(before, abs=0.01)
    assert kitchen.after_m2 == pytest.approx(after, abs=0.01)
    assert after > before
    # Met within the tolerance, or reported as not met with the measured area.
    not_met = [v for v in rev_report.new_violations if v.startswith(REQUEST_NOT_MET_PREFIX)]
    if after >= 18 - REQUESTED_AREA_TOLERANCE_M2:
        assert not_met == []
    else:
        assert not_met == [
            f"{REQUEST_NOT_MET_PREFIX}'area:pi-kitchen=18.0' "
            f"(sp-kitchen area {after:.1f} m² < requested 18 m²)"
        ]


class _FakeServer:
    """Stands in for the TCP server: records the directory served, then stops like Ctrl+C."""

    served: list[str] = []

    def __init__(self, address, handler) -> None:
        _FakeServer.served.append(handler.keywords["directory"])

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def serve_forever(self) -> None:
        raise KeyboardInterrupt


def test_cli_reviewer_serve_exports_bundle_and_prints_loadable_url(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """S10-01 (ISS-32): `reviewer serve` names the project and links to its bundle."""
    import house_ai.cli.reviewer_cmds as reviewer_cmds

    project = tmp_path / "proj"
    load = ["example", "load", str(project), "--name", "synthetic-hillside"]
    assert main([*load, "--project-id", "synthetic-hillside", "--actor", "agent:test"]) == 0
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html>", encoding="utf-8")
    monkeypatch.setattr(reviewer_cmds.socketserver, "TCPServer", _FakeServer)
    _FakeServer.served = []

    assert main(["reviewer", "serve", str(project), "--dist", str(dist), "--port", "5199"]) == 0
    out = capsys.readouterr().out
    assert "for project example: synthetic-hillside at" in out
    assert "http://127.0.0.1:5199/?bundle=bundle.json" in out
    assert _FakeServer.served == [str(dist)]
    data = json.loads((dist / REVIEWER_BUNDLE_FILENAME).read_text(encoding="utf-8"))
    assert data["project"]["name"] == "synthetic-hillside"


def test_cli_reviewer_serve_refuses_without_built_app(tmp_path: Path, monkeypatch, capsys) -> None:
    """S10-01: without a built reviewer there is nothing to serve; say how to build it."""
    import house_ai.cli.reviewer_cmds as reviewer_cmds

    project = tmp_path / "proj"
    load = ["example", "load", str(project), "--name", "synthetic-hillside"]
    assert main([*load, "--project-id", "synthetic-hillside", "--actor", "agent:test"]) == 0
    monkeypatch.setattr(reviewer_cmds.socketserver, "TCPServer", _FakeServer)
    _FakeServer.served = []

    empty = tmp_path / "no-dist"
    assert main(["reviewer", "serve", str(project), "--dist", str(empty)]) == 1
    assert "pnpm install && pnpm build" in capsys.readouterr().out
    assert _FakeServer.served == []
    assert not empty.exists()
