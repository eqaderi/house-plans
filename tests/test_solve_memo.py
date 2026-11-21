"""The solve memo of `tests/conftest.py` (ADR 0035): an identical CP-SAT model is solved once.

The real solves are counted where ortools hands the model to the solver, underneath the memo,
so these tests do not take the memo's own word for what it did.
"""

from __future__ import annotations

import pytest
from ortools.sat.python import cp_model


def _problem(limit: int = 7, seed: int = 3):
    """Maximise 3x + 2y with x + y <= limit and x <= 4: x = 4, y = limit - 4."""
    model = cp_model.CpModel()
    x, y = model.NewIntVar(0, 10, "x"), model.NewIntVar(0, 10, "y")
    model.Add(x + y <= limit)
    model.Add(x <= 4)
    model.Maximize(3 * x + 2 * y)
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = seed
    return model, solver, x, y


@pytest.fixture
def real_solves(monkeypatch) -> list[int]:
    """One entry per model ortools actually solves."""
    calls: list[int] = []
    wrapper = cp_model.cmh.SolveWrapper

    class Counted:
        def __init__(self) -> None:
            self.inner = wrapper()

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def solve(self, proto):
            calls.append(1)
            return self.inner.solve(proto)

    monkeypatch.setattr(cp_model.cmh, "SolveWrapper", Counted)
    return calls


def test_an_identical_model_is_solved_once_and_replayed(real_solves, solve_memo):
    model, first, x, y = _problem()
    assert first.Solve(model) == cp_model.OPTIMAL
    assert (first.Value(x), first.Value(y), first.ObjectiveValue()) == (4, 3, 18)
    assert (len(real_solves), first.from_memo) == (1, False)

    # The same problem built again, in another solver object: no second solve, same answer.
    again_model, again, ax, ay = _problem()
    replays = solve_memo.replayed
    assert again.Solve(again_model) == cp_model.OPTIMAL
    assert (again.Value(ax), again.Value(ay), again.ObjectiveValue()) == (4, 3, 18)
    assert (len(real_solves), again.from_memo) == (1, True)
    assert solve_memo.replayed == replays + 1
    assert again.WallTime() == first.WallTime()  # the first solve's own response


def test_another_model_or_other_parameters_are_solved(real_solves):
    model, solver, _, _ = _problem()
    solver.Solve(model)
    solved = len(real_solves)

    other_model, other, x, y = _problem(limit=9)
    assert other.Solve(other_model) == cp_model.OPTIMAL
    assert (other.Value(x), other.Value(y), other.ObjectiveValue()) == (4, 5, 22)
    assert (len(real_solves), other.from_memo) == (solved + 1, False)

    same_model, reseeded, _, _ = _problem(seed=4)
    assert reseeded.Solve(same_model) == cp_model.OPTIMAL
    assert (len(real_solves), reseeded.from_memo) == (solved + 2, False)


def test_a_solution_callback_always_sees_a_real_search(real_solves):
    class Seen(cp_model.CpSolverSolutionCallback):
        def __init__(self) -> None:
            super().__init__()
            self.objectives: list[float] = []

        def on_solution_callback(self) -> None:
            self.objectives.append(self.ObjectiveValue())

    model, solver, _, _ = _problem()
    solver.Solve(model)
    solved = len(real_solves)
    model, solver, _, _ = _problem()
    seen = Seen()
    assert solver.Solve(model, seen) == cp_model.OPTIMAL
    assert len(real_solves) == solved + 1
    assert seen.objectives[-1] == 18


@pytest.mark.fresh_solves
def test_a_test_marked_fresh_solves_solves_again(real_solves, solve_memo):
    assert solve_memo.fresh is True
    for expected in (1, 2):
        model, solver, x, y = _problem()
        assert solver.Solve(model) == cp_model.OPTIMAL
        assert (solver.Value(x), solver.Value(y), solver.from_memo) == (4, 3, False)
        assert len(real_solves) == expected


def test_the_marker_ends_with_its_test(solve_memo):
    assert solve_memo.fresh is False
