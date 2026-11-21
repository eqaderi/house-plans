"""Safety and integrity invariants (S1-08): where each one is tested.

1. INV-CONSENT: private homeowner data needs a human's consent before it reaches a provider.
2. INV-SOURCE-IMMUTABLE: raw source documents under source/ are read-only and checked.
3. INV-ARTIFACT-WRITE-ONCE: a stored artifact version is never overwritten.
4. INV-HASH-CHAIN: the event log is hash-chained; editing or deleting an event is detected.
5. INV-HEAD-ANCHOR: truncating the event log tail is detected and blocks further writes.
6. INV-HUMAN-GATES: gate approval and reopening, site confirmation, provider consent and
   program rejection need a human at an interactive terminal.
7. INV-SCHEMA-DRIFT: the committed JSON Schemas match the canonical models.
8. INV-PRIVATE-DATA-ISOLATION: tests use synthetic data only and never read the owner's
   private project folder (agent contract section 5).

Invariants 1-7 are tested where their code is (``COVERED_BY``); this module checks that
those tests still exist and tests invariant 8 itself.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent

#: Each invariant and the tests that would fail if it broke.
COVERED_BY = {
    "INV-CONSENT": [
        "test_providers_agents.py::test_private_data_is_refused_by_default",
        "test_providers_agents.py::test_private_data_flows_only_to_the_provider_a_human_allowed",
        "test_providers_agents.py::test_an_agent_cannot_grant_private_data_flow",
        "test_provider_boundary.py::test_only_send_calls_a_provider",
        "test_human_gates.py::test_every_human_command_refuses_without_a_terminal",
    ],
    "INV-SOURCE-IMMUTABLE": [
        "test_storage.py::test_add_source_preserves_bytes_and_hash",
        "test_storage.py::test_verify_detects_a_modified_source",
    ],
    "INV-ARTIFACT-WRITE-ONCE": [
        "test_storage.py::test_artifact_files_are_read_only",
        "test_storage.py::test_existing_version_file_cannot_be_overwritten",
        "test_storage.py::test_a_change_is_a_new_version_never_an_overwrite",
        "test_storage.py::test_get_detects_a_tampered_artifact",
    ],
    "INV-HASH-CHAIN": [
        "test_storage.py::test_verify_detects_an_edited_event",
        "test_storage.py::test_verify_detects_a_deleted_event",
    ],
    "INV-HEAD-ANCHOR": [
        "test_storage.py::test_verify_detects_truncated_event_log_tail",
        "test_storage.py::test_writes_cannot_reanchor_a_truncated_log",
    ],
    "INV-HUMAN-GATES": [
        "test_human_gates.py::test_every_human_command_refuses_without_a_terminal",
        "test_human_gates.py::test_every_human_command_refuses_an_agent_at_a_terminal",
        "test_human_gates.py::test_every_human_command_refuses_a_wrong_phrase",
        "test_human_only.py::test_no_terminal_refuses_even_a_human",
    ],
    "INV-SCHEMA-DRIFT": [
        "test_schemas.py::test_committed_schemas_match_the_code",
        "test_cli.py::test_schemas_check_fails_on_drift",
    ],
    "INV-PRIVATE-DATA-ISOLATION": [
        "test_safety_invariants.py::test_no_test_refers_to_the_private_project_folder",
    ],
}


def _test_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def test_every_invariant_names_tests_that_exist():
    assert len(COVERED_BY) == 8
    missing = [
        node
        for nodes in COVERED_BY.values()
        for node in nodes
        if node.split("::")[1] not in _test_functions(TESTS / node.split("::")[0])
    ]
    assert missing == []


# ----------------------------------------------------- INV-PRIVATE-DATA-ISOLATION

# Built from parts so this file's own constants never match what it looks for.
PRIVATE_DIR = "proj" + "ects"
PRIVATE_NAMES = ("my-" + "house", "seper" + "ated")
#: The private folder as a path component, unless it is the synthetic examples' folder.
_PATH = re.compile(rf"(?<!examples/)\b{PRIVATE_DIR}(?=/|$)")
#: An expression that ends in the examples folder: ``REPO / "examples"``, ``EXAMPLES()``.
_EXAMPLES = re.compile(r"examples?\W*$", re.I)


def _flagged_anywhere(text: str) -> bool:
    """A cheap first pass: a string constant can only match if its words are in the file."""
    return any(word in text for word in (PRIVATE_DIR, *PRIVATE_NAMES))


def _flagged(text: str) -> bool:
    return bool(_PATH.search(text)) or any(name in text for name in PRIVATE_NAMES)


def private_references(tests_dir: Path) -> set[tuple[str, str]]:
    """``(file, string)`` for every string constant in a test module that names the
    private project folder or the owner's project, except paths under the examples folder.
    """
    found = set()
    for path in sorted(tests_dir.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if not _flagged_anywhere(text):
            continue
        tree = ast.parse(text)
        under_examples = {
            id(node.right)
            for node in ast.walk(tree)
            if isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Div)
            and isinstance(node.right, ast.Constant)
            and _EXAMPLES.search(ast.unparse(node.left))
        }
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in under_examples
                and _flagged(node.value)
            ):
                found.add((path.relative_to(tests_dir).as_posix(), node.value))
    return found


#: Legitimate mentions, each with why it reads no private data.
ALLOWED = {
    ("test_leak_scan.py", PRIVATE_DIR):
        "builds a fabricated private project under tmp_path, the layout the scanner reads",
    ("test_project_tracker.py", f"../{PRIVATE_DIR}/"):
        "skips tracker links into the private folder when it is absent; checks existence only",
    ("test_project_tracker.py", f"../{PRIVATE_DIR}"):
        "the existence check of the previous entry",
    ("test_providers_agents.py",
     rf"^{PRIVATE_DIR}/[a-z0-9][a-z0-9-]*/(surveys|source)/[^/]+\.dwg$"):
        "matches tracked file names from `git ls-files`; never opens a file",
    ("test_providers_agents.py", "Owner surveys are committed only in "
     f"{PRIVATE_DIR}/<name>/ (ADR 0009); project-data/ stays\n    private, and no lock, "
     "partial write or credential file is ever tracked."):
        "the docstring of that file-name check",
    ("test_next_human_action.py", PRIVATE_NAMES[0]):
        "a project name rendered into a command string; no path is opened",
    ("test_next_human_action.py", f"house-ai workflow approve {PRIVATE_NAMES[0]} plan --id "
     "concept-compact --version 4 --approver owner"):
        "the rendered command the previous entry produces",
    ("test_plan_generation.py", PRIVATE_NAMES[0]):
        "asserts the synthetic hillside fixture does not mention the owner's project",
    ("test_plan_generation.py", PRIVATE_NAMES[1]):
        "the same assertion for the owner's survey file name",
    ("test_site_review_fixes.py", f"{PRIVATE_NAMES[1]}.dxf"):
        "names a synthetic DXF it writes under tmp_path after the survey's file name",
    ("test_site_review_fixes.py", f"src-{PRIVATE_NAMES[1]}#"):
        "the source id of that synthetic DXF",
}  # fmt: skip


def test_no_test_refers_to_the_private_project_folder():
    """A test that read the owner's project would have to name its folder; none does.

    Every allowed mention must still be there, so the list cannot outlive its reason.
    """
    assert private_references(TESTS) == set(ALLOWED)


@pytest.mark.parametrize(
    "source",
    [
        f'REPO / "{PRIVATE_DIR}" / "x" / "site.yaml"',
        f'Path("{PRIVATE_DIR}/x/project.json")',
        f'Path("../{PRIVATE_DIR}")',
        f'"{PRIVATE_NAMES[0]}"',
        f'f"{{REPO}}/{PRIVATE_DIR}/{{name}}"',
    ],
)
def test_the_private_folder_check_catches_a_reference(tmp_path, source):
    (tmp_path / "test_reads_private.py").write_text(f"x = {source}\n", encoding="utf-8")
    assert len(private_references(tmp_path)) == 1


@pytest.mark.parametrize(
    "source",
    [
        f'REPO / "examples" / "{PRIVATE_DIR}" / "synthetic-hillside"',
        f'path_examples() / "{PRIVATE_DIR}/synthetic-bungalow/site.yaml"',
        f'"examples/{PRIVATE_DIR}/synthetic-hillside"',
        '"several private projects."',
    ],
)
def test_the_private_folder_check_allows_the_synthetic_examples(tmp_path, source):
    (tmp_path / "test_synthetic.py").write_text(f"x = {source}\n", encoding="utf-8")
    assert private_references(tmp_path) == set()
