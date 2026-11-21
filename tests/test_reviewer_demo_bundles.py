"""Test that synthetic demonstration reviewer bundles match their generator.

The bundles hold committed plans only (synthetic-bungalow's hand-authored plan-a and the
shipped synthetic-hillside exploratory concepts), so `make_bundles.py --check` compares exact
output without running the solver, whose output may differ by platform.
"""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pytest

from house_ai.generation.generator import CpSatPlanGenerator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "examples" / "reviewer" / "make_bundles.py"
BUNDLES = REPO_ROOT / "examples" / "reviewer" / "bundles"
HILLSIDE_CONCEPTS = REPO_ROOT / "examples" / "projects" / "synthetic-hillside" / "concepts"


def _no_solver(*args, **kwargs):
    raise AssertionError("make_bundles.py must not run the plan solver")


def test_synthetic_demonstration_bundles_match_generator(monkeypatch, capsys) -> None:
    """make_bundles.py --check verifies committed bundles match current generation."""
    make_bundles = runpy.run_path(str(SCRIPT))  # not __main__: defines, does not run
    monkeypatch.setattr(CpSatPlanGenerator, "candidates", _no_solver)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--check"])
    code = make_bundles["main_cli"]()
    out = capsys.readouterr()
    assert code == 0, f"Drift detected in demonstration bundles:\n{out.err}\n{out.out}"
    assert "OK: all synthetic demonstration bundles up to date" in out.out


@pytest.mark.parametrize(
    ("project", "expected"),
    [
        ("synthetic-bungalow", [("plan-a", 1, False)]),
        (
            "synthetic-hillside",
            [
                (p.name, None, True)  # exploratory: never stored, so no version
                for p in sorted(HILLSIDE_CONCEPTS.iterdir())
                if (p / "exploratory" / "plan.json").is_file()
            ],
        ),
    ],
)
def test_bundles_hold_only_committed_plans(project: str, expected: list) -> None:
    bundle = json.loads((BUNDLES / project / "bundle.json").read_text(encoding="utf-8"))
    assert len(expected) >= 1
    assert [(p["option_id"], p["version"], p["is_exploratory"]) for p in bundle["plans"]] == (
        expected
    )
