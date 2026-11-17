"""Regression tests for all human-only commands (S1-01, S1-02, S1-03, S1-04).

Human-only commands:
- house-ai workflow approve
- house-ai workflow reopen
- house-ai site confirm
- house-ai interview consent
- house-ai program reject

Invariants tested:
1. Non-TTY execution exits 2 (EXIT_USAGE) and appends nothing.
2. Agent actors or agent-looking ids are refused with exit 2 (EXIT_USAGE) and append nothing.
3. Mismatched confirmation phrases exit 1 (EXIT_FAIL) and append nothing.
4. Leaving PROGRAM_REVIEW back to INTERVIEWING refuses agent actors with exit 2.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from house_ai.cli.main import EXIT_FAIL, EXIT_OK, EXIT_USAGE, main
from house_ai.domain.provenance import Actor, ActorKind
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.site import Site
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore

HUMAN = Actor(kind=ActorKind.HUMAN, id="test-owner")
AGENT = Actor(kind=ActorKind.AGENT, id="claude-code")


@pytest.fixture
def clean_project(tmp_path: Path):
    store = ProjectStore.init(
        tmp_path / "proj",
        project_id="synthetic-bungalow",
        name="Gate Test",
        classification="synthetic",  # type: ignore[arg-type]
        actor=HUMAN,
    )
    return store


def test_approve_refuses_non_tty(clean_project, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    before_events = len(clean_project.events())
    ret = main([
        "workflow", "approve", str(clean_project.root), "site",
        "--id", "site", "--approver", "test-owner",
    ])
    assert ret == EXIT_USAGE
    assert "interactive terminal" in capsys.readouterr().err
    assert len(clean_project.events()) == before_events


def test_approve_refuses_agent_looking_approver(clean_project, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    before_events = len(clean_project.events())
    ret = main([
        "workflow", "approve", str(clean_project.root), "site",
        "--id", "site", "--approver", "agent:gemini",
    ])
    assert ret == EXIT_USAGE
    assert "disallowed approver" in capsys.readouterr().err
    assert len(clean_project.events()) == before_events

    ret2 = main([
        "workflow", "approve", str(clean_project.root), "site",
        "--id", "site", "--approver", "codex",
    ])
    assert ret2 == EXIT_USAGE
    assert len(clean_project.events()) == before_events


def test_approve_refuses_wrong_phrase(clean_project, monkeypatch, capsys):
    from .conftest import example_doc
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    wf = Workflow(clean_project)
    wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "ingesting")
    site = Site.model_validate(example_doc("site.yaml"))
    clean_project.put(K.SITE, "site", site, HUMAN)

    monkeypatch.setattr("builtins.input", lambda _: "wrong confirmation phrase")
    before_events = len(clean_project.events())
    ret = main([
        "workflow", "approve", str(clean_project.root), "site",
        "--id", "site", "--approver", "test-owner",
    ])
    assert ret == EXIT_FAIL
    assert "confirmation did not match" in capsys.readouterr().err
    assert len(clean_project.events()) == before_events


def test_reopen_refuses_non_tty(clean_project, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    before_events = len(clean_project.events())
    ret = main([
        "workflow", "reopen", str(clean_project.root), "site",
        "--reason", "testing reopen", "--actor", "human:owner",
    ])
    assert ret == EXIT_USAGE
    assert "interactive terminal" in capsys.readouterr().err
    assert len(clean_project.events()) == before_events


def test_reopen_refuses_agent_actor(clean_project, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    before_events = len(clean_project.events())
    ret = main([
        "workflow", "reopen", str(clean_project.root), "site",
        "--reason", "testing reopen", "--actor", "agent:claude-code",
    ])
    assert ret == EXIT_USAGE
    assert "cannot reopen gates" in capsys.readouterr().err
    assert len(clean_project.events()) == before_events


def test_reopen_refuses_wrong_phrase_and_succeeds_with_correct_phrase(
    clean_project, monkeypatch, capsys
):
    from .conftest import example_doc
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    wf = Workflow(clean_project)
    wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "ingesting")
    site = Site.model_validate(example_doc("site.yaml"))
    s_ref = clean_project.put(K.SITE, "site", site, HUMAN)
    wf.approve(Gate.SITE, s_ref, HUMAN, "approved site")

    # Wrong phrase
    monkeypatch.setattr("builtins.input", lambda _: "not the phrase")
    before_events = len(clean_project.events())
    ret_fail = main([
        "workflow", "reopen", str(clean_project.root), "site",
        "--reason", "needs changes", "--actor", "human:owner",
    ])
    assert ret_fail == EXIT_FAIL
    assert len(clean_project.events()) == before_events

    # Correct phrase
    monkeypatch.setattr("builtins.input", lambda _: "reopen site site")
    ret_ok = main([
        "workflow", "reopen", str(clean_project.root), "site",
        "--reason", "needs changes", "--actor", "human:owner",
    ])
    assert ret_ok == EXIT_OK
    assert len(clean_project.events()) == before_events + 1
    assert wf.state is WorkflowState.SITE_INGESTION


def test_site_confirm_refuses_non_tty(clean_project, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    before_events = len(clean_project.events())
    ret = main([
        "site", "confirm", str(clean_project.root), "--id", "site",
        "--confirmer", "owner", "--units", "m",
    ])
    assert ret == EXIT_USAGE
    assert "site confirmation needs an interactive terminal" in capsys.readouterr().err
    assert len(clean_project.events()) == before_events


def test_site_confirm_refuses_agent_looking_confirmer(clean_project, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    before_events = len(clean_project.events())
    ret = main([
        "site", "confirm", str(clean_project.root), "--id", "site",
        "--confirmer", "agent:gemini", "--units", "m",
    ])
    assert ret == EXIT_USAGE
    assert "disallowed confirmer" in capsys.readouterr().err
    assert len(clean_project.events()) == before_events


def test_interview_consent_refuses_non_tty_and_agent(clean_project, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    before_events = len(clean_project.events())
    ret = main([
        "interview", "consent", str(clean_project.root), "anthropic",
        "--actor", "human:owner",
    ])
    assert ret == EXIT_USAGE
    assert len(clean_project.events()) == before_events

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    ret_agent = main([
        "interview", "consent", str(clean_project.root), "anthropic",
        "--actor", "agent:claude-code",
    ])
    assert ret_agent == EXIT_USAGE
    assert "cannot grant provider consent" in capsys.readouterr().err
    assert len(clean_project.events()) == before_events


def test_program_reject_refuses_non_tty_and_agent(clean_project, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    before_events = len(clean_project.events())
    ret = main([
        "program", "reject", str(clean_project.root),
        "--reason", "needs changes", "--actor", "human:owner",
    ])
    assert ret == EXIT_USAGE
    assert len(clean_project.events()) == before_events

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    ret_agent = main([
        "program", "reject", str(clean_project.root),
        "--reason", "needs changes", "--actor", "agent:claude-code",
    ])
    assert ret_agent == EXIT_USAGE
    assert "cannot reject the space program" in capsys.readouterr().err
    assert len(clean_project.events()) == before_events


@pytest.mark.parametrize("actor", ["agent:claude-code", "human:owner"])
def test_workflow_transition_program_review_to_interviewing_refuses_bypass(
    clean_project, capsys, actor
):
    from .conftest import example_doc
    wf = Workflow(clean_project)
    wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "ingest")
    site = Site.model_validate(example_doc("site.yaml"))
    s_ref = clean_project.put(K.SITE, "site", site, HUMAN)
    wf.approve(Gate.SITE, s_ref, HUMAN, "site approved")
    wf.transition(WorkflowState.INTERVIEWING, HUMAN, "interviewing")
    from house_ai.domain.program import SpaceProgram
    prog = SpaceProgram.model_validate(example_doc("space_program.yaml"))
    clean_project.put(K.SPACE_PROGRAM, "program", prog, HUMAN)
    wf.transition(WorkflowState.PROGRAM_REVIEW, HUMAN, "review")

    # Agent actor must be refused when attempting transition back to INTERVIEWING
    before_events = len(clean_project.events())
    ret = main([
        "workflow", "transition", str(clean_project.root), "INTERVIEWING",
        "--reason", "bypassing reject", "--actor", actor,
    ])
    assert ret == EXIT_USAGE
    err = capsys.readouterr().err
    assert "requires 'program reject' in a human terminal" in err
    assert len(clean_project.events()) == before_events


@pytest.mark.parametrize("command", ["site", "consent", "reject"])
def test_remaining_human_commands_refuse_wrong_phrase(clean_project, monkeypatch, command):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "wrong phrase")
    commands = {
        "site": ["site", "confirm", str(clean_project.root), "--id", "site",
                 "--confirmer", "owner", "--units", "m"],
        "consent": ["interview", "consent", str(clean_project.root), "anthropic",
                    "--actor", "human:owner"],
        "reject": ["program", "reject", str(clean_project.root), "--reason", "revise",
                   "--actor", "human:owner"],
    }
    before = (clean_project.root / "events.jsonl").read_bytes()
    assert main(commands[command]) == EXIT_FAIL
    assert (clean_project.root / "events.jsonl").read_bytes() == before


def test_program_reject_records_reason_only_after_correct_phrase(clean_project, monkeypatch):
    from house_ai.orchestration.interview import InterviewService

    from .conftest import example_doc

    wf = Workflow(clean_project)
    wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "ingest")
    site = Site.model_validate(example_doc("site.yaml"))
    ref = clean_project.put(K.SITE, "site", site, AGENT)
    wf.approve(Gate.SITE, ref, HUMAN, "site reviewed")
    svc = InterviewService(clean_project)
    svc.start(AGENT)
    svc.build_program(AGENT)
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "review")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "reject program")
    reason = "The kitchen needs more storage."
    assert main(["program", "reject", str(clean_project.root), "--reason", reason,
                 "--actor", "human:owner"]) == EXIT_OK
    assert wf.state is WorkflowState.INTERVIEWING
    assert any(f.key == "program_rejection" and f.statement == reason for f in svc.brief().facts)


def test_program_v2_after_approval_marks_gate_stale(clean_project, capsys):
    import json

    from .conftest import example_doc
    wf = Workflow(clean_project)
    wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "ingest")
    site = Site.model_validate(example_doc("site.yaml"))
    s_ref = clean_project.put(K.SITE, "site", site, HUMAN)
    wf.approve(Gate.SITE, s_ref, HUMAN, "site approved")
    wf.transition(WorkflowState.INTERVIEWING, HUMAN, "interviewing")

    from house_ai.domain.program import SpaceProgram
    prog = SpaceProgram.model_validate(example_doc("space_program.yaml"))
    p_ref = clean_project.put(K.SPACE_PROGRAM, "program", prog, HUMAN)
    wf.transition(WorkflowState.PROGRAM_REVIEW, HUMAN, "review")
    wf.approve(Gate.PROGRAM, p_ref, HUMAN, "program approved")

    # Verify initially not stale
    assert main(["project", "status", str(clean_project.root), "--json"]) == 0
    status1 = json.loads(capsys.readouterr().out)
    assert status1["approvals"]["program"]["stale"] is False

    # Write program v2 after approval
    new_area = (prog.target_gross_area_m2 or 100.0) + 50.0
    p2 = prog.model_copy(update={"target_gross_area_m2": new_area})
    ref2 = clean_project.put(K.SPACE_PROGRAM, "program", p2, HUMAN)
    assert ref2.version == 2

    # project status --json shows the gate status's staleness, as before (ADR 0029).
    assert main(["project", "status", str(clean_project.root), "--json"]) == 0
    status2 = json.loads(capsys.readouterr().out)
    assert status2["approvals"]["program"]["stale"] is True
    assert status2["approvals"]["program"]["latest_version"] == 2
    assert status2["stale_approvals"] == ["program"]
