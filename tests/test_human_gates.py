"""Regression tests for all human-only commands (S1-01, S1-02, S1-03, S1-04).

Human-only commands:
- house-ai workflow approve
- house-ai workflow reopen
- house-ai site confirm
- house-ai interview consent
- house-ai program reject

Invariants tested, each on a project where the command applies (PROGRAM_REVIEW, site
approved, interview started), so the human check is the only thing that stops it:
1. Non-TTY execution exits 2 (EXIT_USAGE) and writes nothing.
2. Agent actors or agent-looking ids are refused with exit 2 (EXIT_USAGE), before any
   question is asked, and write nothing.
3. Mismatched confirmation phrases exit 1 (EXIT_FAIL) and write nothing.
4. Leaving PROGRAM_REVIEW back to INTERVIEWING by transition is refused with exit 2.

"Writes nothing" compares the bytes of every file and the set of folders in the project
tree, so an orphan artifact or an edited manifest fails as surely as a new event.
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
from house_ai.orchestration.interview import InterviewService
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore

from .conftest import example_doc

HUMAN = Actor(kind=ActorKind.HUMAN, id="test-owner")
AGENT = Actor(kind=ActorKind.AGENT, id="claude-code")


def tree(root: Path) -> dict[str, bytes | None]:
    """Every path under ``root``: a file's bytes, ``None`` for a folder."""
    return {
        p.relative_to(root).as_posix(): (p.read_bytes() if p.is_file() else None)
        for p in sorted(root.rglob("*"))
    }


@pytest.fixture
def clean_project(tmp_path: Path):
    return ProjectStore.init(
        tmp_path / "proj",
        project_id="synthetic-bungalow",
        name="Gate Test",
        classification="synthetic",  # type: ignore[arg-type]
        actor=HUMAN,
    )


@pytest.fixture
def site_project(clean_project):
    """A site waiting for the site gate in SITE_INGESTION: `workflow approve site` applies."""
    Workflow(clean_project).transition(WorkflowState.SITE_INGESTION, HUMAN, "ingest")
    clean_project.put(K.SITE, "site", Site.model_validate(example_doc("site.yaml")), AGENT)
    return clean_project


@pytest.fixture
def review_project(clean_project):
    """Site approved, interview started, program built, waiting in PROGRAM_REVIEW."""
    wf = Workflow(clean_project)
    wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "ingest")
    ref = clean_project.put(K.SITE, "site", Site.model_validate(example_doc("site.yaml")), AGENT)
    wf.approve(Gate.SITE, ref, HUMAN, "site reviewed")
    svc = InterviewService(clean_project)
    svc.start(AGENT)
    svc.build_program(AGENT)
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "review")
    return clean_project


def _commands(d: str, who: dict[str, str]) -> dict[str, list[str]]:
    """The five human-only commands on project ``d``; ``who`` overrides the human."""
    return {
        "approve": ["workflow", "approve", d, "site", "--id", "site", "--version", "1",
                    "--approver", who.get("approve", "test-owner")],
        "reopen": ["workflow", "reopen", d, "site", "--reason", "needs changes",
                   "--actor", who.get("reopen", "human:owner")],
        "site": ["site", "confirm", d, "--id", "site", "--units", "m",
                 "--confirmer", who.get("site", "owner")],
        "consent": ["interview", "consent", d, "anthropic",
                    "--actor", who.get("consent", "human:owner")],
        "reject": ["program", "reject", d, "--reason", "needs changes",
                   "--actor", who.get("reject", "human:owner")],
    }  # fmt: skip


COMMANDS = ["approve", "reopen", "site", "consent", "reject"]


@pytest.fixture
def ready(request, command):
    """The project on which ``command`` applies: the site gate waits for approval, or the
    program waits in review (site approved, interview started) for the other four."""
    return request.getfixturevalue("site_project" if command == "approve" else "review_project")

#: The noun each command's terminal refusal names (``house_ai.cli.human``).
NO_TTY = {
    "approve": "approval needs an interactive terminal",
    "reopen": "reopening a gate needs an interactive terminal",
    "site": "site confirmation needs an interactive terminal",
    "consent": "provider consent needs an interactive terminal",
    "reject": "program rejection needs an interactive terminal",
}


@pytest.mark.parametrize("command", COMMANDS)
def test_every_human_command_refuses_without_a_terminal(ready, monkeypatch, capsys, command):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("asked for a phrase"))
    before = tree(ready.root)
    assert main(_commands(str(ready.root), {})[command]) == EXIT_USAGE
    assert NO_TTY[command] in capsys.readouterr().err
    assert tree(ready.root) == before


#: An agent identity per command, and the refusal it gets at a real terminal.
AGENT_IDS = [
    ("approve", "agent:gemini", "disallowed approver 'agent:gemini'"),
    ("approve", "codex", "disallowed approver 'codex'"),
    ("reopen", "agent:claude-code", "cannot reopen gates"),
    ("site", "agent:gemini", "disallowed confirmer 'agent:gemini'"),
    ("consent", "agent:claude-code", "cannot grant provider consent"),
    ("reject", "agent:claude-code", "cannot reject the space program"),
]


@pytest.mark.parametrize(("command", "who", "refusal"), AGENT_IDS)
def test_every_human_command_refuses_an_agent_at_a_terminal(
    ready, monkeypatch, capsys, command, who, refusal
):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("asked an agent for a phrase"))
    before = tree(ready.root)
    assert main(_commands(str(ready.root), {command: who})[command]) == EXIT_USAGE
    assert refusal in capsys.readouterr().err
    assert tree(ready.root) == before


#: What did not happen, as each command reports a wrong phrase.
UNDONE = {
    "approve": "nothing approved",
    "reopen": "nothing reopened",
    "site": "nothing confirmed",
    "consent": "not allowed",
    "reject": "nothing rejected",
}


@pytest.mark.parametrize("command", COMMANDS)
def test_every_human_command_refuses_a_wrong_phrase(ready, monkeypatch, capsys, command):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "wrong phrase")
    before = tree(ready.root)
    assert main(_commands(str(ready.root), {})[command]) == EXIT_FAIL
    assert f"confirmation did not match; {UNDONE[command]}" in capsys.readouterr().err
    assert len(asked) == 1  # the human was asked, once
    assert tree(ready.root) == before


def test_reopen_succeeds_only_with_the_correct_phrase(clean_project, monkeypatch, capsys):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    wf = Workflow(clean_project)
    wf.transition(WorkflowState.SITE_INGESTION, HUMAN, "ingesting")
    s_ref = clean_project.put(K.SITE, "site", Site.model_validate(example_doc("site.yaml")), HUMAN)
    wf.approve(Gate.SITE, s_ref, HUMAN, "approved site")
    before = len(clean_project.events())

    monkeypatch.setattr("builtins.input", lambda _: "reopen site site")
    ret_ok = main([
        "workflow", "reopen", str(clean_project.root), "site",
        "--reason", "needs changes", "--actor", "human:owner",
    ])  # fmt: skip
    assert ret_ok == EXIT_OK
    (event,) = clean_project.events()[before:]
    assert (event.actor.kind, event.actor.id) == (ActorKind.HUMAN, "owner")
    assert wf.state is WorkflowState.SITE_INGESTION
    assert wf.status().approvals == {}


@pytest.mark.parametrize("actor", ["agent:claude-code", "human:owner"])
def test_workflow_transition_program_review_to_interviewing_refuses_bypass(
    review_project, capsys, actor
):
    before = tree(review_project.root)
    ret = main([
        "workflow", "transition", str(review_project.root), "INTERVIEWING",
        "--reason", "bypassing reject", "--actor", actor,
    ])  # fmt: skip
    assert ret == EXIT_USAGE
    assert "only the owner's program reject" in capsys.readouterr().err
    assert tree(review_project.root) == before
    assert Workflow(review_project).state is WorkflowState.PROGRAM_REVIEW


def test_program_reject_records_reason_only_after_correct_phrase(review_project, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "reject program")
    reason = "The kitchen needs more storage."
    assert main(["program", "reject", str(review_project.root), "--reason", reason,
                 "--actor", "human:owner"]) == EXIT_OK  # fmt: skip
    assert Workflow(review_project).state is WorkflowState.INTERVIEWING
    facts = InterviewService(review_project).brief().facts
    assert [f.statement for f in facts if f.key == "program_rejection"] == [reason]


def test_the_review_fixture_is_a_real_program_review(review_project):
    """The refusals above stop a command that would otherwise apply: the program waits."""
    status = Workflow(review_project).status()
    assert status.state is WorkflowState.PROGRAM_REVIEW
    assert list(status.approvals) == [Gate.SITE]
    assert review_project.latest(K.SPACE_PROGRAM, "program").version == 1
