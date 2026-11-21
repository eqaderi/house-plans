"""Tests for the agent skills folder, authoring template, and Claude Code's link to it."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import pytest

from house_ai.cli.main import build_parser
from house_ai.constants.skills import (
    CANONICAL_SKILL_NAMES,
    CANONICAL_SKILLS_DIR,
    CLAUDE_SKILLS_LINK,
    REQUIRED_SKILL_FRONTMATTER,
    REQUIRED_SKILL_SECTIONS,
)
from house_ai.validation.grounding import (
    collect_canonical_ids,
    extract_entity_ids_from_text,
    validate_cited_ids,
)

REPO = Path(__file__).resolve().parent.parent


def validate_skill_content(skill_path: Path) -> list[str]:
    """Template errors in a skill folder's SKILL.md: front matter fields and sections."""
    skill_file = skill_path / "SKILL.md"
    if not skill_file.is_file():
        return [f"Missing SKILL.md in {skill_path}"]
    text = skill_file.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if not text.startswith("---") or len(parts) < 3:
        return [f"{skill_file}: Must start with closed YAML frontmatter"]
    errors = [
        f"{skill_file}: Frontmatter missing required field '{field}:'"
        for field in REQUIRED_SKILL_FRONTMATTER
        if f"{field}:" not in parts[1]
    ]
    errors += [
        f"{skill_file}: Missing required section '## {section}'"
        for section in REQUIRED_SKILL_SECTIONS
        if f"## {section}" not in text
    ]
    return errors


def test_skills_folder_holds_exactly_the_canonical_skills_as_real_folders():
    skills_dir = REPO / CANONICAL_SKILLS_DIR
    entries = {p.name: p for p in skills_dir.iterdir() if not p.name.startswith(".")}
    assert sorted(entries) == sorted(CANONICAL_SKILL_NAMES)
    for path in entries.values():
        assert path.is_dir() and not path.is_symlink(), f"{path} must be a real folder"


def test_claude_skills_is_a_relative_link_to_the_whole_skills_folder():
    link = REPO / CLAUDE_SKILLS_LINK
    assert link.is_symlink()
    assert os.readlink(link) == "../.agents/skills"
    assert link.resolve() == (REPO / CANONICAL_SKILLS_DIR).resolve()
    assert sorted(p.name for p in link.iterdir()) == sorted(CANONICAL_SKILL_NAMES)


@pytest.mark.parametrize("skill_name", CANONICAL_SKILL_NAMES)
def test_skill_structure_and_frontmatter(skill_name: str):
    assert validate_skill_content(REPO / CANONICAL_SKILLS_DIR / skill_name) == []


def test_drift_detector_catches_invalid_frontmatter(tmp_path: Path):
    bad_skill = tmp_path / "bad-skill"
    bad_skill.mkdir()
    (bad_skill / "SKILL.md").write_text("No frontmatter here\n", encoding="utf-8")
    errors = validate_skill_content(bad_skill)
    assert any("frontmatter" in err.lower() for err in errors)


def test_drift_detector_catches_missing_section(tmp_path: Path):
    bad_skill = tmp_path / "bad-skill"
    bad_skill.mkdir()
    content = "---\nname: bad-skill\ndescription: test\n---\n# Title\n## Purpose\n"
    (bad_skill / "SKILL.md").write_text(content, encoding="utf-8")
    errors = validate_skill_content(bad_skill)
    assert any("Missing required section" in err for err in errors)


#: The human-only commands each skill's workflow reaches, as its **NEVER** lines name them.
HUMAN_ONLY_NEVER = {
    "architectural-programming": [
        "house-ai workflow approve <project> program",
        "house-ai program reject",
        "house-ai interview consent",
    ],
    "critique-plan": ["house-ai workflow approve <project> plan"],
    "generate-plan-options": ["house-ai workflow approve <project> plan"],
    "site-survey-review": [
        "house-ai site confirm",
        "house-ai workflow approve <project> site",
    ],
    "visual-review": ["house-ai workflow approve <project> plan"],
}


def _never_commands(text: str) -> list[str]:
    """The backticked `house-ai ...` commands on the skill's **NEVER** lines, in order."""
    lines = [line for line in text.splitlines() if "**NEVER**" in line]
    return [cmd for line in lines for cmd in re.findall(r"`(house-ai [^`]+)`", line)]


def test_every_skill_names_a_never_rule_for_each_human_only_command_it_reaches():
    """Each skill forbids, by name, running the human-only commands of its gate."""
    assert sorted(HUMAN_ONLY_NEVER) == sorted(CANONICAL_SKILL_NAMES)
    for skill_name, commands in HUMAN_ONLY_NEVER.items():
        assert _never_commands(_skill_text(skill_name)) == commands, skill_name


def test_the_never_rule_check_reads_only_never_lines():
    text = (
        "Run `house-ai workflow request-approval <project> plan`.\n"
        "- **NEVER** run `house-ai program reject` or `house-ai interview consent`.\n"
        "- Never run `house-ai site confirm` yourself.\n"
    )
    assert _never_commands(text) == ["house-ai program reject", "house-ai interview consent"]


def _skill_text(skill_name: str) -> str:
    return (REPO / CANONICAL_SKILLS_DIR / skill_name / "SKILL.md").read_text(encoding="utf-8")


def _subcommands(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(action.choices)
    return {}


def _skill_commands(text: str) -> list[list[str]]:
    """Every `.venv/bin/house-ai ...` command in a skill, continuation lines joined."""
    joined = re.sub(r"\\\n\s*", " ", text)
    return [m.split() for m in re.findall(r"\.venv/bin/house-ai ([^\n`#]+)", joined)]


@pytest.mark.parametrize("skill_name", CANONICAL_SKILL_NAMES)
def test_every_skill_command_and_flag_exists_in_the_cli(skill_name: str):
    groups = _subcommands(build_parser())
    commands = _skill_commands(_skill_text(skill_name))
    assert commands, f"{skill_name} names no house-ai commands"
    for words in commands:
        assert words[0] in groups, f"{skill_name}: unknown command group {words[0]!r}"
        subs = _subcommands(groups[words[0]])
        parser = groups[words[0]]
        if subs:
            assert words[1] in subs, f"{skill_name}: unknown command {words[:2]}"
            parser = subs[words[1]]
        known = {opt for action in parser._actions for opt in action.option_strings}
        for flag in (w.split("=")[0] for w in words if w.startswith("--")):
            assert flag in known, f"{skill_name}: `{' '.join(words[:2])}` has no {flag}"


@pytest.mark.parametrize("skill_name", CANONICAL_SKILL_NAMES)
def test_skills_never_hardcode_an_agent_identity(skill_name: str):
    text = _skill_text(skill_name)
    assert re.findall(r"agent:(?!<tool>)[a-z]", text) == []
    assert "--actor agent:<tool>" in text


def test_grounding_extracts_only_backticked_ids():
    text = (
        "The z-axis and a w-shaped plan are prose. `sp-kitchen` sits on `lv-entry` in "
        "`z-day`; `adj-02-kitchen-living` is met. Fix: `house-ai plan revise p concept-a "
        '"words" --area pi-kitchen=18 --separate pi-bed-main,pi-bed-child-1 '
        "--level pi-study-1=entry`. Again `sp-kitchen`, and `level-entry`."
    )
    assert extract_entity_ids_from_text(text) == [
        "sp-kitchen",
        "lv-entry",
        "z-day",
        "adj-02-kitchen-living",
        "pi-kitchen",
        "pi-bed-main",
        "pi-bed-child-1",
        "pi-study-1",
        "level-entry",
    ]


def test_grounding_reads_a_plan_json_and_the_references_of_its_spaces():
    plan = {
        "option_id": "concept-a",
        "model": {
            "levels": [{"id": "lv-entry"}],
            "zones": [{"id": "z-day"}],
            "spaces": [
                {
                    "id": "sp-kitchen",
                    "program_item_id": "pi-kitchen",
                    "zone_id": "z-day",
                    "level_id": "lv-entry",
                }
            ],
            "units": "m",
        },
    }
    assert collect_canonical_ids(plan) == {"lv-entry", "z-day", "sp-kitchen", "pi-kitchen"}
    errors = validate_cited_ids(["pi-kitchen=18", "lv-entry", "level-entry"], plan)
    assert errors == [
        "Unknown entity ID 'level-entry' in critique. "
        "Must reference an existing space, space requirement, zone, or level in the plan."
    ]
