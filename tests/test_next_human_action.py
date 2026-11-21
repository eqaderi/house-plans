"""The next human action: carried by the gate status, rendered once, accepted by the parser.

ADR 0029. The gate status says what a human does next (approve this version,
confirm these site facts); ``house_ai.cli.human.command_for`` is the one place
that turns it into a command line.
"""

from __future__ import annotations

import json
import re
import shlex

import pytest

from house_ai.cli.human import command_for
from house_ai.cli.main import build_parser, main
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.workflow import Blocker, BlockerKind, Gate, WorkflowState
from house_ai.orchestration.interview import InterviewLocked, InterviewService
from house_ai.orchestration.site import SiteService
from house_ai.orchestration.workflow import HumanAction, NextHumanAction, Workflow
from house_ai.storage.importer import import_folder

from .conftest import AGENT, EXAMPLE, HUMAN, example_doc

#: A value for every placeholder a rendered command may hold; any other fails the test.
PLACEHOLDERS = {
    "<your-name>": "owner",
    "<epsg-code>": "25832",
    "<unit>": "m",
    "<datum>": "DHHN2016",
    "<why>": "redo",
    "<version>": "3",
    "<site-id>": "site",
    "<program-id>": "program",
    "<option-id>": "concept-compact",
    "<model-id>": "build-blender",
}

ALL_SITE_FACTS = tuple(
    Blocker(kind=BlockerKind.SITE_FACT, code=code, message=code)
    for code in (
        "source_units",
        "horizontal_crs",
        "elevation_units",
        "vertical_datum",
        "local_frame",
        "boundary_unverified",
    )
) + (Blocker(kind=BlockerKind.SITE_ISSUE, code="iss-gap", subject_ids=["iss-gap"], message="x"),)

ACTIONS = [
    *(NextHumanAction(HumanAction.APPROVE, g, "an-id", 2) for g in Gate),
    *(NextHumanAction(HumanAction.APPROVE, g) for g in Gate),  # templates
    *(NextHumanAction(HumanAction.REOPEN, g) for g in Gate),
    NextHumanAction(HumanAction.CONFIRM_SITE, Gate.SITE, "site", clears=ALL_SITE_FACTS),
    NextHumanAction(HumanAction.CONFIRM_SITE, Gate.SITE),  # template
    NextHumanAction(HumanAction.REJECT_PROGRAM, Gate.PROGRAM),
]


def _parse(command: str):
    def fill(match: re.Match) -> str:
        assert match.group(0) in PLACEHOLDERS, f"unknown placeholder in: {command}"
        return PLACEHOLDERS[match.group(0)]

    program, *argv = shlex.split(re.sub(r"<[^>]+>", fill, command))
    assert program == "house-ai"
    try:
        return build_parser().parse_args(argv)
    except SystemExit:
        raise AssertionError(f"the CLI does not accept: {command}") from None


@pytest.mark.parametrize("action", ACTIONS, ids=lambda a: f"{a.action.value}-{a.gate.value}")
def test_every_rendered_next_human_command_is_accepted_by_the_parser(action):
    args = _parse(command_for(action, "my-project"))

    assert args.dir == "my-project"
    if action.action is HumanAction.APPROVE:
        assert (args.sub, args.gate, args.approver) == ("approve", action.gate.value, "owner")
        if action.artifact_id:
            assert (args.id, args.version) == (action.artifact_id, action.version)
        else:  # a template names the version too
            assert args.version == 3
    elif action.action is HumanAction.CONFIRM_SITE:
        assert (args.sub, args.id, args.confirmer) == ("confirm", "site", "owner")
    else:  # reopen and program reject name a human actor and a reason
        assert (args.actor.kind.value, args.actor.id) == ("human", "owner")
        assert args.reason == "redo"


def test_a_site_confirmation_asks_for_what_its_blockers_need():
    action = NextHumanAction(HumanAction.CONFIRM_SITE, Gate.SITE, "site", clears=ALL_SITE_FACTS)
    args = _parse(command_for(action, "p"))
    assert (args.units, args.epsg, args.elevation_units) == ("m", 25832, "m")
    assert (args.vertical_datum, args.boundary_verified, args.accept_issue) == (
        "DHHN2016",
        True,
        ["iss-gap"],
    )


def test_the_approve_command_pins_the_version():
    action = NextHumanAction(HumanAction.APPROVE, Gate.PLAN, "concept-compact", 4)
    assert command_for(action, "my-house", who="owner") == (
        "house-ai workflow approve my-house plan --id concept-compact --version 4 "
        "--approver owner"
    )


# ------------------------------------------------------- carried by the gate status


@pytest.fixture
def example(store):
    import_folder(store, EXAMPLE, AGENT)
    return store


def test_an_approvable_gate_says_approve_this_version(example):
    site = example.latest(ArtifactKind.SITE, "site")
    SiteService(example).assess(site, AGENT)

    status = Workflow(example).gate_status(Gate.SITE, site)

    assert status.next_action == NextHumanAction(HumanAction.APPROVE, Gate.SITE, "site", 1)


def test_a_site_that_needs_confirmation_says_confirm_its_blockers(example):
    doc = example_doc("site.yaml")
    doc["coordinates"]["horizontal_crs"] = {"status": "declared_in_source", "declared_epsg": 32632}
    unsure = example.put(ArtifactKind.SITE, "site", doc, AGENT)
    SiteService(example).assess(unsure, AGENT)
    wf = Workflow(example)
    assert wf.state is WorkflowState.SITE_NEEDS_CONFIRMATION

    status = wf.current_gate_status()

    assert status is not None and status.artifact == unsure
    action = status.next_action
    assert (action.action, action.artifact_id) == (HumanAction.CONFIRM_SITE, "site")
    assert [b.code for b in action.clears] == ["horizontal_crs"]


def test_a_blocked_gate_has_no_next_human_action(example):
    site = example.latest(ArtifactKind.SITE, "site")
    SiteService(example).assess(site, AGENT)
    Workflow(example).approve(Gate.SITE, site, HUMAN, "ok")
    program = example.latest(ArtifactKind.SPACE_PROGRAM, "program")
    # Not in program review: the gate is blocked by the workflow state.
    assert Workflow(example).gate_status(Gate.PROGRAM, program).next_action is None


def test_project_status_shows_the_next_human_command(example, capsys):
    doc = example_doc("site.yaml")
    doc["coordinates"]["horizontal_crs"] = {"status": "declared_in_source", "declared_epsg": 32632}
    SiteService(example).assess(example.put(ArtifactKind.SITE, "site", doc, AGENT), AGENT)

    assert main(["project", "status", str(example.root), "--json"]) == 0
    info = json.loads(capsys.readouterr().out)

    assert info["next_human_command"] == (
        f"house-ai site confirm {example.root} --id site --epsg <epsg-code> "
        "--confirmer <your-name>"
    )
    action = info["gate_status"]["next_action"]
    assert (action["action"], [b["code"] for b in action["clears"]]) == (
        "confirm_site",
        ["horizontal_crs"],
    )


def test_a_locked_interview_names_the_reopening_only_a_human_can_do(example):
    site = example.latest(ArtifactKind.SITE, "site")
    SiteService(example).assess(site, AGENT)
    wf = Workflow(example)
    wf.approve(Gate.SITE, site, HUMAN, "ok")
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "review")
    wf.approve(Gate.PROGRAM, example.latest(ArtifactKind.SPACE_PROGRAM, "program"), HUMAN, "ok")

    with pytest.raises(InterviewLocked) as exc:
        interview = InterviewService(example)
        interview.start(AGENT)
        interview.answer("Four bedrooms.", HUMAN)

    assert exc.value.next_action == NextHumanAction(HumanAction.REOPEN, Gate.PROGRAM)
