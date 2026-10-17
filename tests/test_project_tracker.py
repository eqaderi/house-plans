"""docs/PROJECT_TRACKER.md stays consistent (ADR 0014); tools/check_tracker.py enforces it."""

from __future__ import annotations

import re
import runpy

import pytest

from .conftest import REPO

TRACKER = REPO / "docs" / "PROJECT_TRACKER.md"
CHECK = runpy.run_path(str(REPO / "tools" / "check_tracker.py"))["check"]

STAGE = """\
### Stage X.1 — Example stage

| Field | Value |
|---|---|
| Kind | implementation |
| Status | {status} |
| Review | {review} |
| Branch | `stage/X.1-example` |
| Depends on | none |
| Tasks | X.1-01 |
| Objective | o |
| Scope | s |
| Acceptance | a |
| Tests | t |
| Demonstration | d |
| Artifacts | a |
| Review requirements | r |
| Evidence | e |

- [{box}] **X.1-01** Example task — `{task_status}` · P1 · deps: {deps}
  - Accept: a
  - Verify: v
  - Evidence: {evidence}
"""


def _errors(**overrides: str) -> list[str]:
    fields = {
        "status": "NOT_STARTED",
        "review": "NOT_REQUESTED",
        "box": " ",
        "task_status": "NOT_STARTED",
        "deps": "none",
        "evidence": "pending",
    }
    fields.update(overrides)
    return CHECK("## F. Register\n\n" + STAGE.format(**fields))[0]


def test_the_committed_tracker_is_consistent():
    errors, counts = CHECK(TRACKER.read_text(encoding="utf-8"))
    assert errors == []
    assert sum(counts["tasks"].values()) >= 100
    # At most one implementation stage is under way at a time.
    assert counts["stages"]["IN_PROGRESS"] <= 1


def test_a_valid_example_passes():
    assert _errors() == []


@pytest.mark.parametrize("evidence", ["—", "-", "pending", "pending — later", "TBD", ""])
def test_done_without_evidence_is_rejected(evidence):
    errors = _errors(box="x", task_status="DONE", evidence=evidence)
    assert any("DONE without evidence" in e or "missing 'Evidence'" in e for e in errors)


def test_done_with_evidence_passes():
    assert _errors(box="x", task_status="DONE", evidence="commit `abc1234`") == []


def test_checkbox_must_match_status():
    assert any("checkbox" in e for e in _errors(box="x"))
    assert any("checkbox" in e for e in _errors(task_status="DONE", evidence="`abc1234`"))


def test_unknown_status_dependency_and_review_are_rejected():
    assert any("bad status" in e for e in _errors(task_status="FINISHED"))
    assert any("unknown dependency" in e for e in _errors(deps="Z.9-01"))
    assert any("bad review status" in e for e in _errors(review="PASSED"))


def test_stage_rules_are_enforced():
    assert any(
        "DONE without APPROVED review" in e
        for e in _errors(status="DONE", box="x", task_status="DONE", evidence="`abc1234`")
    )
    assert any("requires status IN_PROGRESS" in e for e in _errors(review="PENDING"))
    assert any("BLOCKED without a Notes line" in e for e in _errors(task_status="BLOCKED"))


def test_duplicate_ids_and_missing_rows_are_rejected():
    text = "## F\n\n" + STAGE.format(
        status="NOT_STARTED", review="NOT_REQUESTED", box=" ",
        task_status="NOT_STARTED", deps="none", evidence="pending",
    )
    assert any("duplicate stage id" in e for e in CHECK(text + "\n" + text)[0])
    no_objective = text.replace("| Objective | o |\n", "")
    assert any("missing 'Objective'" in e for e in CHECK(no_objective)[0])


def test_tracker_relative_links_resolve():
    text = TRACKER.read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text)
    missing = [
        link for link in links
        if not link.startswith("http")
        and not (link.startswith("../projects/") and not (TRACKER.parent / "../projects").exists())
        and not (TRACKER.parent / link).exists()
    ]
    assert missing == []
