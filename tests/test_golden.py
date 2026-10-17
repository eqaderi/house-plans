"""The golden synthetic project stays internally consistent."""

from __future__ import annotations

import runpy

from .conftest import EXAMPLE


def test_golden_plan_matches_its_generator():
    """plans/plan-a.json is exactly what build_plan.py produces from the current inputs."""
    build_plan = runpy.run_path(str(EXAMPLE / "build_plan.py"))
    assert build_plan["main"](["--check"]) == 0
