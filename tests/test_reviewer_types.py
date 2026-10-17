"""Test for TypeScript types drift check (Stage S4 Task S4-03)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "generate_reviewer_types.py"


def test_reviewer_typescript_types_match_schemas() -> None:
    """generate_reviewer_types.py --check verifies TS types match schemas."""
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, f"TypeScript schema drift detected:\n{res.stderr}\n{res.stdout}"
    assert "OK: TypeScript schema types are up to date" in res.stdout
