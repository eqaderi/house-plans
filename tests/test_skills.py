"""Tests for canonical agent skills layout, authoring template, and provider discovery."""

from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path

import pytest

from house_ai.cli.main import build_parser
from house_ai.constants.skills import (
    CANONICAL_SKILL_NAMES,
    CANONICAL_SKILLS_DIR,
    PROVIDER_SKILLS_DIRS,
    REQUIRED_SKILL_SECTIONS,
)
from house_ai.evaluation.grounding import (
    collect_canonical_ids,
    extract_entity_ids_from_text,
    validate_critique_grounding,
)
from tools.sync_skills import get_canonical_skills, sync_skills, validate_skill_content

REPO = Path(__file__).resolve().parent.parent


def test_canonical_skills_exist():
    canonical = get_canonical_skills(REPO)
    for name in CANONICAL_SKILL_NAMES:
        assert name in canonical, f"Missing canonical skill: {name}"
    assert len(canonical) == len(CANONICAL_SKILL_NAMES)


@pytest.mark.parametrize("skill_name", CANONICAL_SKILL_NAMES)
def test_skill_structure_and_frontmatter(skill_name: str):
    skill_dir = REPO / CANONICAL_SKILLS_DIR / skill_name
    assert skill_dir.is_dir()

    skill_file = skill_dir / "SKILL.md"
    assert skill_file.is_file()

    errors = validate_skill_content(skill_dir)
    assert errors == [], f"Validation errors for {skill_name}: {errors}"

    text = skill_file.read_text(encoding="utf-8")
    for section in REQUIRED_SKILL_SECTIONS:
        assert f"## {section}" in text, f"Skill {skill_name} missing section '{section}'"


@pytest.mark.parametrize("provider_dir", PROVIDER_SKILLS_DIRS)
def test_provider_skills_symlinks_and_drift(provider_dir: str):
    target_dir = REPO / provider_dir
    assert target_dir.is_dir(), f"Provider directory {provider_dir} missing"

    for skill_name in CANONICAL_SKILL_NAMES:
        link = target_dir / skill_name
        assert link.exists(), f"Provider skill link {link} missing"
        assert link.is_symlink(), f"Provider skill {link} is not a symlink"

        # Check target is relative symlink pointing to ../../skills/<skill_name>
        raw_target = os.readlink(link)
        expected_raw_target = f"../../skills/{skill_name}"
        assert raw_target == expected_raw_target, (
            f"Link {link} points to {raw_target}, expected {expected_raw_target}"
        )

        # Verify content identity (zero drift)
        canonical_content = (REPO / CANONICAL_SKILLS_DIR / skill_name / "SKILL.md").read_bytes()
        provider_content = (link / "SKILL.md").read_bytes()
        assert provider_content == canonical_content, f"Content drift detected in {link}"


def test_sync_skills_check_mode_clean():
    err_count, errors = sync_skills(REPO, check_only=True)
    assert err_count == 0, f"sync_skills --check reported errors: {errors}"


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


def test_human_approval_boundaries_documented_in_all_skills():
    """All skills must explicitly prohibit automated gate approval."""
    for skill_name in CANONICAL_SKILL_NAMES:
        skill_file = REPO / CANONICAL_SKILLS_DIR / skill_name / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8")
        assert "NEVER" in text
        assert "human" in text.lower()


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


@pytest.mark.parametrize("skill_name", CANONICAL_SKILL_NAMES)
def test_skills_link_the_agent_contract(skill_name: str):
    assert "](../../docs/AGENT_CONTRACT.md)" in _skill_text(skill_name)
    assert (REPO / "docs" / "AGENT_CONTRACT.md").is_file()


def test_sync_keeps_local_skills_unless_pruned(tmp_path: Path):
    shutil.copytree(REPO / CANONICAL_SKILLS_DIR, tmp_path / CANONICAL_SKILLS_DIR)
    local = tmp_path / ".claude" / "skills" / "my-local-skill"
    local.mkdir(parents=True)
    (local / "SKILL.md").write_text("mine\n", encoding="utf-8")

    _, errors = sync_skills(tmp_path)
    assert local.is_dir()
    assert errors == [
        f"Non-canonical provider skill entry: {local} "
        "(left in place; rerun with --prune to remove)"
    ]
    for provider_dir in PROVIDER_SKILLS_DIRS:
        for name in CANONICAL_SKILL_NAMES:
            assert os.readlink(tmp_path / provider_dir / name) == f"../../skills/{name}"

    assert sync_skills(tmp_path, prune=True) == (0, [])
    assert not local.exists()


def test_sync_never_replaces_a_real_copy(tmp_path: Path):
    shutil.copytree(REPO / CANONICAL_SKILLS_DIR, tmp_path / CANONICAL_SKILLS_DIR)
    copy = tmp_path / ".agents" / "skills" / CANONICAL_SKILL_NAMES[0]
    copy.mkdir(parents=True)
    (copy / "SKILL.md").write_text("edited copy\n", encoding="utf-8")

    count, errors = sync_skills(tmp_path, prune=True)
    assert count == 1 and "is a real copy, not a symlink" in errors[0]
    assert (copy / "SKILL.md").read_text(encoding="utf-8") == "edited copy\n"


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
    errors = validate_critique_grounding(["pi-kitchen=18", "lv-entry", "level-entry"], plan)
    assert errors == [
        "Unknown entity ID 'level-entry' in critique. "
        "Must reference an existing space, space requirement, zone, or level in the plan."
    ]
