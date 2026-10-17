"""The coding-agent entry files load one shared contract and stay small (ADR 0005)."""

from __future__ import annotations

import re

import pytest

from .conftest import REPO

CONTRACT = REPO / "docs" / "AGENT_CONTRACT.md"
#: Antigravity limits a rules file to 12,000 characters.
CONTRACT_MAX_CHARS = 12_000
ENTRY_MAX_CHARS = 1_500


def test_contract_fits_the_smallest_tool_limit():
    assert len(CONTRACT.read_text(encoding="utf-8")) < CONTRACT_MAX_CHARS


def test_claude_md_imports_the_contract():
    lines = (REPO / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
    assert "@docs/AGENT_CONTRACT.md" in lines


def test_gemini_md_imports_the_contract_with_the_documented_syntax():
    lines = (REPO / "GEMINI.md").read_text(encoding="utf-8").splitlines()
    assert "@./docs/AGENT_CONTRACT.md" in lines


def test_agents_md_tells_codex_to_read_the_contract():
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "read\n[docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md)" in text


@pytest.mark.parametrize("name", ["AGENTS.md", "CLAUDE.md", "GEMINI.md"])
def test_entry_files_stay_minimal(name):
    text = (REPO / name).read_text(encoding="utf-8")
    assert len(text) < ENTRY_MAX_CHARS
    # Rules live in the contract; entry files must not grow their own sections of them.
    assert "## " not in text.replace("## Claude Code specifics", "").replace(
        "## Gemini specifics", ""
    )


def test_contract_relative_links_resolve():
    text = CONTRACT.read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)#]+)\)", text)
    assert links
    missing = [link for link in links if not (CONTRACT.parent / link).exists()]
    assert missing == []
