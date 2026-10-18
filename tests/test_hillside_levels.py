"""The same CP-SAT model couples bar location, terrain and level elevations."""

from types import SimpleNamespace

import pytest
from ortools.sat.python import cp_model

from house_ai.domain.site import TinSurface
from house_ai.generation.frame import DesignFrame, Ground
from house_ai.generation.massing import Bar, Massing, Row, _step
from house_ai.generation.terrain_levels import joint_level_variables

from .test_hillside_views import site_for


@pytest.mark.parametrize("sign", [-1, 1])
def test_joint_levels_follow_road_high_and_road_low_without_three_metre_clamp(sign):
    tin = TinSurface(
        vertices=[
            (0, -2, -2 * sign),
            (12, -2, 1.2 - 2 * sign),
            (12, 24, 1.2 + 24 * sign),
            (0, 24, 24 * sign),
        ],
        triangles=[(0, 1, 2), (0, 2, 3)],
    )
    frame = DesignFrame((0, 0), (1, 0), (0, 1), "synthetic", None, None)
    ctx = SimpleNamespace(ground=Ground(site_for(tin), frame))
    bars = [
        Bar(
            "entry",
            "u",
            0,
            [Row("e-front", "front", 0, 30), Row("e-back", "back", 30, 30)],
            0,
            120,
            entry=True,
        ),
        Bar(
            "rear",
            "u",
            120,
            [Row("r-front", "front", 0, 30), Row("r-back", "back", 30, 30)],
            0,
            120,
            elevation_m=12 * sign,
        ),
    ]
    m = Massing("split_level", bars, [], 12, 0, 1)

    def solve(start_value, length_value):
        md = cp_model.CpModel()
        start = {b.id: md.NewIntVar(0, 60, f"start-{b.id}") for b in bars}
        length = {b.id: md.NewIntVar(40, 60, f"length-{b.id}") for b in bars}
        for b in bars:
            md.Add(start[b.id] == start_value)
            md.Add(length[b.id] == length_value)
        levels, _, _ = joint_level_variables(md, m, start, length, ctx)
        solver = cp_model.CpSolver()
        assert solver.Solve(md) == cp_model.OPTIMAL
        return {k: solver.Value(v) / 100 for k, v in levels.items()}

    a, b = solve(0, 40), solve(40, 60)
    assert a["rear"] - a["entry"] == 12 * sign
    assert b["rear"] - b["entry"] == 12 * sign
    assert a["entry"] == pytest.approx(0.2 - 0.5 * sign)
    assert b["entry"] == pytest.approx(0.7 - 0.5 * sign)
    assert _step(12 * sign) == 12 * sign


def test_sectional_alternatives_are_solver_generated_and_compared(tmp_path):
    from examples.hillside.run_demo import run

    rows = run(tmp_path)
    assert len(rows) == 5
    produced = [r for r in rows if r["status"] == "generated"]
    assert {r["sectional_strategy"] for r in produced} == {
        "walkout",
        "split_level",
        "stepped",
        "elevated",
        "hybrid",
    }
    assert all(r["integrity_valid"] for r in produced)
    assert len({tuple(round(z, 2) for z in r["elevations_m"]) for r in produced}) >= 3
    assert all(r["engineered_fill_m3"] is None for r in produced)
    assert all((tmp_path / r["sectional_strategy"] / "sections.svg").is_file() for r in produced)
    assert "no excavation/elevation preference" in (tmp_path / "comparison.md").read_text().lower()


@pytest.mark.parametrize("gradient", [-3.0, 3.0])
def test_extreme_slope_quantities_are_finite_and_risks_explicit(gradient):
    from house_ai.geospatial.hillside import hillside_report

    from .test_hillside_earthworks import model

    tin = TinSurface(
        vertices=[(0, 0, 0), (10, 0, 0), (10, 6, 6 * gradient), (0, 6, 6 * gradient)],
        triangles=[(0, 1, 2), (0, 2, 3)],
    )
    r = hillside_report(model(0), site_for(tin))
    w = r["earthworks"]
    assert w["excavation_volume_m3"] == pytest.approx(540 if gradient > 0 else 0)
    assert w["underfloor_void_volume_m3"] == pytest.approx(540 if gradient < 0 else 0)
    assert any(risk["discipline"] == "slope_stability" for risk in r["risks"])
    assert r["terrain_quality"]
