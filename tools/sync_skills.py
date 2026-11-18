#!/usr/bin/env python3
"""Sync project skills to provider discovery directories (.claude/skills, .agents/skills).

Canonical source of truth is skills/<name>/SKILL.md.
Creates and validates relative symlinks:
  .claude/skills/<name> -> ../../skills/<name>
  .agents/skills/<name> -> ../../skills/<name>
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from house_ai.constants.skills import (  # noqa: E402
    CANONICAL_SKILL_NAMES,
    CANONICAL_SKILLS_DIR,
    PROVIDER_SKILLS_DIRS,
    REQUIRED_SKILL_FRONTMATTER,
    REQUIRED_SKILL_SECTIONS,
)


def get_canonical_skills(repo_root: Path = REPO_ROOT) -> dict[str, Path]:
    skills_dir = repo_root / CANONICAL_SKILLS_DIR
    if not skills_dir.exists():
        return {}
    skills: dict[str, Path] = {}
    for item in sorted(skills_dir.iterdir()):
        if item.is_dir() and (item / "SKILL.md").is_file():
            skills[item.name] = item
    return skills


def validate_skill_content(skill_path: Path) -> list[str]:
    """Validate that SKILL.md adheres to the canonical layout and frontmatter."""
    skill_file = skill_path / "SKILL.md"
    if not skill_file.is_file():
        return [f"Missing SKILL.md in {skill_path}"]

    errors: list[str] = []
    text = skill_file.read_text(encoding="utf-8")

    # Validate frontmatter
    if not text.startswith("---"):
        errors.append(f"{skill_file}: Must start with YAML frontmatter delimiter '---'")
    else:
        parts = text.split("---", 2)
        if len(parts) < 3:
            errors.append(f"{skill_file}: Unclosed YAML frontmatter")
        else:
            frontmatter = parts[1]
            for field in REQUIRED_SKILL_FRONTMATTER:
                if f"{field}:" not in frontmatter:
                    errors.append(f"{skill_file}: Frontmatter missing required field '{field}:'")

    # Validate required sections
    for section in REQUIRED_SKILL_SECTIONS:
        expected_header = f"## {section}"
        if expected_header not in text:
            errors.append(f"{skill_file}: Missing required section '{expected_header}'")

    return errors


def sync_skills(  # noqa: C901
    repo_root: Path = REPO_ROOT, check_only: bool = False, prune: bool = False
) -> tuple[int, list[str]]:
    """Synchronize canonical skills to provider directories via relative symlinks.

    Entries in a provider directory that are not canonical skills (for
    example a developer's own local skill) are reported, and removed only
    when ``prune`` is true.
    """
    canonical_skills = get_canonical_skills(repo_root)
    errors: list[str] = []

    # Validate content of all canonical skills
    for skill_path in canonical_skills.values():
        errors.extend(validate_skill_content(skill_path))

    # Verify all expected canonical skills exist
    for expected_name in CANONICAL_SKILL_NAMES:
        if expected_name not in canonical_skills:
            errors.append(f"Missing required canonical skill: {expected_name}")

    for provider_dir_name in PROVIDER_SKILLS_DIRS:
        target_dir = repo_root / provider_dir_name
        if not check_only:
            target_dir.mkdir(parents=True, exist_ok=True)
        elif not target_dir.exists():
            errors.append(f"Provider skills directory does not exist: {provider_dir_name}")
            continue

        # Check existing entries in target_dir
        if target_dir.exists():
            for existing in target_dir.iterdir():
                if existing.name not in canonical_skills:
                    if check_only or not prune:
                        errors.append(
                            f"Non-canonical provider skill entry: {existing} "
                            "(left in place; rerun with --prune to remove)"
                        )
                    elif existing.is_symlink() or existing.is_file():
                        existing.unlink()
                    else:
                        shutil.rmtree(existing)

        # Ensure symlinks for all canonical skills
        for skill_name, skill_path in canonical_skills.items():
            link_path = target_dir / skill_name
            # Relative target from target_dir to skill_path
            relative_target = Path(os.path.relpath(skill_path, target_dir))

            if link_path.is_symlink():
                current_target = Path(os.readlink(link_path))
                if current_target != relative_target:
                    if check_only:
                        errors.append(
                            f"Symlink mismatch for {link_path}: points to {current_target}, "
                            f"expected {relative_target}"
                        )
                    else:
                        link_path.unlink()
                        link_path.symlink_to(relative_target)
                elif not link_path.exists():
                    errors.append(f"Broken symlink at {link_path} -> {current_target}")
            elif link_path.exists():
                errors.append(
                    f"{link_path} is a real copy, not a symlink; "
                    "remove it by hand after checking it has no unsynced edits"
                )
            else:
                if check_only:
                    errors.append(
                        f"Missing provider symlink for {skill_name} in {provider_dir_name}"
                    )
                else:
                    link_path.symlink_to(relative_target)

    return len(errors), errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check synchronization and content validation without modifying files",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove non-canonical entries from provider skill directories",
    )
    args = parser.parse_args()

    error_count, errors = sync_skills(check_only=args.check, prune=args.prune)
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    action = "verified" if args.check else "synced"
    print(f"Skills successfully {action} across providers ({len(CANONICAL_SKILL_NAMES)} skills).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
