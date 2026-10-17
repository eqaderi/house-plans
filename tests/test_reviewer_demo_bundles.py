"""Test that synthetic demonstration reviewer bundles match their generator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "examples" / "reviewer" / "make_bundles.py"


def test_synthetic_demonstration_bundles_match_generator() -> None:
    """make_bundles.py --check verifies committed bundles match current generation."""
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    msg = f"Drift detected in demonstration bundles:\n{res.stderr}\n{res.stdout}"
    assert res.returncode == 0, msg
    assert "OK: all synthetic demonstration bundles up to date" in res.stdout
