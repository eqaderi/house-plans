"""Tests for canonical agent skills layout, authoring template, and provider discovery."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from house_ai.constants.skills import (
    CANONICAL_SKILL_NAMES,
    CANONICAL_SKILLS_DIR,
    PROVIDER_SKILLS_DIRS,
    REQUIRED_SKILL_SECTIONS,
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
