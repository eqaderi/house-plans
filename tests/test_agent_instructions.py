"""Every coding agent reads one entry file that loads one shared contract (ADR 0005, ADR 0034)."""

from __future__ import annotations

import os
import re

import pytest

from .conftest import REPO

CONTRACT = REPO / "docs" / "AGENT_CONTRACT.md"
ENTRY = REPO / "AGENTS.md"
#: Antigravity limits a rules file to 12,000 characters.
CONTRACT_MAX_CHARS = 12_000
ENTRY_MAX_CHARS = 1_000


def test_contract_fits_the_smallest_tool_limit():
    assert len(CONTRACT.read_text(encoding="utf-8")) < CONTRACT_MAX_CHARS


@pytest.mark.parametrize("name", ["CLAUDE.md", "GEMINI.md"])
def test_tool_entry_files_are_relative_links_to_agents_md(name):
    path = REPO / name
    assert path.is_symlink()
    assert os.readlink(path) == "AGENTS.md"


def test_entry_file_imports_the_contract_with_the_syntax_both_importers_document():
    # Claude Code and Gemini CLI both expand `@./path` relative to the importing file.
    assert "@./docs/AGENT_CONTRACT.md" in ENTRY.read_text(encoding="utf-8").splitlines()


def test_entry_file_tells_codex_to_read_the_contract():
    text = ENTRY.read_text(encoding="utf-8")
    assert "Read [docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md) in full" in text


def test_entry_file_stays_a_pointer():
    text = ENTRY.read_text(encoding="utf-8")
    assert len(text) < ENTRY_MAX_CHARS
    # Rules live in the contract; the entry file has no sections of its own.
    assert "\n## " not in text


@pytest.mark.parametrize("path", [CONTRACT, ENTRY])
def test_relative_links_resolve(path):
    links = re.findall(r"\]\(([^)#]+)\)", path.read_text(encoding="utf-8"))
    assert links
    missing = [link for link in links if not (path.parent / link).exists()]
    assert missing == []
