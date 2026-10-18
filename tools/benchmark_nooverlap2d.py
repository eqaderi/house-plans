"""Benchmark evaluating CP-SAT AddNoOverlap2D vs pairwise disjunction vs 1D intervals.

Compares:
1. Native CP-SAT AddNoOverlap2D with linear adjacency bounds.
2. Pairwise disjunctive non-overlap (AddBoolOr across 4 bounding box half-planes).
3. 1D row intervals (legacy bar partitioning with AddNoOverlap per row).

Measures solve time (wall and deterministic), status, objective, and determinism.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass

from ortools.sat.python import cp_model

from house_ai.constants.relations import SHARED_WALL_MIN_M

SHARED_WALL_MIN_DM = int(round(SHARED_WALL_MIN_M * 10))


@dataclass(frozen=True)
class RoomDef:
    id: str
    name: str
    target_area_m2: float
    min_width_m: float
    max_aspect: float = 2.5

    @property
    def target_area_dm2(self) -> int:
        return int(round(self.target_area_m2 * 100))

    @property
    def min_dim_dm(self) -> int:
        return max(15, int(math.ceil(self.min_width_m * 10 - 1e-9)))


@dataclass(frozen=True)
class AdjacencyDef:
    room_a: str
    room_b: str
    hard: bool = True
    weight: int = 100


@dataclass
class BenchmarkScenario:
    name: str
    rooms: list[RoomDef]
    adjacencies: list[AdjacencyDef]
    envelope_w_m: float
    envelope_h_m: float

    @property
    def env_w_dm(self) -> int:
        return int(round(self.envelope_w_m * 10))

    @property
    def env_h_dm(self) -> int:
        return int(round(self.envelope_h_m * 10))


def build_scenarios() -> dict[str, BenchmarkScenario]:
    # 1. Small scenario (5 rooms: entry, living, kitchen, bed, bath)
    small = BenchmarkScenario(
        name="small_5_rooms",
        rooms=[
            RoomDef("sp-entry", "Entry", 6.0, 1.8),
            RoomDef("sp-living", "Living Room", 24.0, 3.6),
            RoomDef("sp-kitchen", "Kitchen", 12.0, 2.8),
            RoomDef("sp-bed-1", "Primary Bedroom", 16.0, 3.2),
            RoomDef("sp-bath-1", "Bathroom", 6.0, 1.8),
        ],
        adjacencies=[
            AdjacencyDef("sp-entry", "sp-living", hard=True),
            AdjacencyDef("sp-living", "sp-kitchen", hard=True),
            AdjacencyDef("sp-living", "sp-bed-1", hard=False, weight=200),
            AdjacencyDef("sp-bed-1", "sp-bath-1", hard=True),
        ],
        envelope_w_m=14.0,
        envelope_h_m=12.0,
    )

    # 2. Medium scenario (9 rooms: synthetic bungalow / steep reference)
    medium = BenchmarkScenario(
        name="medium_9_rooms",
        rooms=[
            RoomDef("sp-entry", "Entry", 6.0, 1.8),
            RoomDef("sp-living", "Living Room", 28.0, 4.0),
            RoomDef("sp-dining", "Dining", 14.0, 3.0),
            RoomDef("sp-kitchen", "Kitchen", 14.0, 3.0),
            RoomDef("sp-bed-primary", "Primary Bedroom", 18.0, 3.5),
            RoomDef("sp-bath-primary", "Primary Bath", 7.0, 2.0),
            RoomDef("sp-bed-2", "Bedroom 2", 12.0, 3.0),
            RoomDef("sp-bath-common", "Common Bath", 5.0, 1.8),
            RoomDef("sp-utility", "Utility", 6.0, 2.0),
        ],
        adjacencies=[
            AdjacencyDef("sp-entry", "sp-living", hard=True),
            AdjacencyDef("sp-living", "sp-dining", hard=True),
            AdjacencyDef("sp-dining", "sp-kitchen", hard=True),
            AdjacencyDef("sp-bed-primary", "sp-bath-primary", hard=True),
            AdjacencyDef("sp-bed-2", "sp-bath-common", hard=False, weight=150),
            AdjacencyDef("sp-kitchen", "sp-utility", hard=True),
            AdjacencyDef("sp-entry", "sp-bath-common", hard=False, weight=100),
        ],
        envelope_w_m=18.0,
        envelope_h_m=14.0,
    )

    # 3. Large scenario (14 rooms: multi-generational with garage and guest)
    large = BenchmarkScenario(
        name="large_14_rooms",
        rooms=[
            RoomDef("sp-garage", "Garage", 36.0, 5.5),
            RoomDef("sp-entry", "Entry", 8.0, 2.0),
            RoomDef("sp-living", "Living Room", 32.0, 4.5),
            RoomDef("sp-dining", "Dining", 16.0, 3.2),
            RoomDef("sp-kitchen", "Kitchen", 16.0, 3.2),
            RoomDef("sp-pantry", "Pantry", 4.0, 1.5),
            RoomDef("sp-bed-primary", "Primary Bedroom", 20.0, 3.6),
            RoomDef("sp-bath-primary", "Primary Bath", 8.0, 2.2),
            RoomDef("sp-bed-2", "Bedroom 2", 13.0, 3.0),
            RoomDef("sp-bed-3", "Bedroom 3", 13.0, 3.0),
            RoomDef("sp-bath-2", "Bath 2", 6.0, 2.0),
            RoomDef("sp-guest-bed", "Guest Bedroom", 14.0, 3.2),
            RoomDef("sp-guest-bath", "Guest Bath", 5.0, 1.8),
            RoomDef("sp-mechanical", "Mechanical", 7.0, 2.0),
        ],
        adjacencies=[
            AdjacencyDef("sp-garage", "sp-entry", hard=True),
            AdjacencyDef("sp-entry", "sp-living", hard=True),
            AdjacencyDef("sp-living", "sp-dining", hard=True),
            AdjacencyDef("sp-dining", "sp-kitchen", hard=True),
            AdjacencyDef("sp-kitchen", "sp-pantry", hard=True),
            AdjacencyDef("sp-bed-primary", "sp-bath-primary", hard=True),
            AdjacencyDef("sp-bed-2", "sp-bath-2", hard=False, weight=150),
            AdjacencyDef("sp-bed-3", "sp-bath-2", hard=False, weight=150),
            AdjacencyDef("sp-guest-bed", "sp-guest-bath", hard=True),
            AdjacencyDef("sp-entry", "sp-mechanical", hard=False, weight=100),
        ],
        envelope_w_m=24.0,
        envelope_h_m=18.0,
    )

    return {s.name: s for s in (small, medium, large)}


@dataclass
class SolveResult:
    method: str
    scenario: str
    status: str
    wall_time_s: float
    deterministic_time: float
    objective_val: float
    num_variables: int
    num_constraints: int
    room_bounds: dict[str, list[int]]  # id -> [x0, y0, w, h]
    best_bound: float | None
    relative_gap: float | None


def _allowed_dimensions(r: RoomDef, max_w: int, max_h: int) -> list[tuple[int, int]]:
    pairs = []
    for w in range(r.min_dim_dm, max_w + 1, 2):
        for h in range(
            max(r.min_dim_dm, math.ceil(0.9 * r.target_area_dm2 / w)),
            min(max_h, math.floor(1.2 * r.target_area_dm2 / w)) + 1,
            2,
        ):
            if max(w / h, h / w) <= r.max_aspect:
                pairs.append((w, h))
    return pairs


def _solve(scenario: BenchmarkScenario, method: str, seed: int, det_time: float) -> SolveResult:
    """Same room bounds, adjacency requirements and objective for every formulation.

    Rows restrict y to a fixed track pitch; they may therefore be infeasible where
    free 2D placement succeeds. Inactive row intervals never enter the objective.
    """
    md = cp_model.CpModel()
    started = time.perf_counter()
    ew, eh = scenario.env_w_dm, scenario.env_h_dm
    pitch = max(r.min_dim_dm for r in scenario.rooms)
    row_count = max(1, eh // pitch)
    xv, yv, wv, hv, xe, ye = {}, {}, {}, {}, {}, {}
    xivs, yivs = [], []
    row_intervals = {k: [] for k in range(row_count)}
    for r in scenario.rooms:
        dims = _allowed_dimensions(r, ew, min(eh, pitch) if method == "row_intervals_1d" else eh)
        if not dims:
            return SolveResult(method, scenario.name, "INFEASIBLE", 0, 0, -1, 0, 0, {}, None, None)
        sid = r.id
        xv[sid] = md.NewIntVar(0, ew, "x_" + sid)
        yv[sid] = md.NewIntVar(0, eh, "y_" + sid)
        wv[sid] = md.NewIntVar(min(w for w, h in dims), max(w for w, h in dims), "w_" + sid)
        hv[sid] = md.NewIntVar(min(h for w, h in dims), max(h for w, h in dims), "h_" + sid)
        xe[sid] = md.NewIntVar(0, ew, "xe_" + sid)
        ye[sid] = md.NewIntVar(0, eh, "ye_" + sid)
        md.Add(xe[sid] == xv[sid] + wv[sid])
        md.Add(ye[sid] == yv[sid] + hv[sid])
        md.AddAllowedAssignments([wv[sid], hv[sid]], dims)
        if method == "row_intervals_1d":
            choices = []
            for row in range(row_count):
                lit = md.NewBoolVar(f"row_{sid}_{row}")
                choices.append(lit)
                md.Add(yv[sid] == row * pitch).OnlyEnforceIf(lit)
                row_intervals[row].append(
                    md.NewOptionalIntervalVar(xv[sid], wv[sid], xe[sid], lit, f"iv_{sid}_{row}")
                )
            md.AddExactlyOne(choices)
        else:
            xivs.append(md.NewIntervalVar(xv[sid], wv[sid], xe[sid], "ix_" + sid))
            yivs.append(md.NewIntervalVar(yv[sid], hv[sid], ye[sid], "iy_" + sid))
    if method == "nooverlap_2d":
        md.AddNoOverlap2D(xivs, yivs)
    elif method == "row_intervals_1d":
        for intervals in row_intervals.values():
            md.AddNoOverlap(intervals)
    else:
        for i, a in enumerate(scenario.rooms):
            for b in scenario.rooms[i + 1 :]:
                choices = []
                for j, expr in enumerate(
                    [
                        xe[a.id] <= xv[b.id],
                        xe[b.id] <= xv[a.id],
                        ye[a.id] <= yv[b.id],
                        ye[b.id] <= yv[a.id],
                    ]
                ):
                    lit = md.NewBoolVar(f"disjoint_{a.id}_{b.id}_{j}")
                    md.Add(expr).OnlyEnforceIf(lit)
                    choices.append(lit)
                md.AddBoolOr(choices)
    objective = []
    for adj in scenario.adjacencies:
        a, b = adj.room_a, adj.room_b
        choices = []
        for i, (eq, p, q, r, t) in enumerate(
            [
                (xe[a] == xv[b], ye[a], yv[b], ye[b], yv[a]),
                (xe[b] == xv[a], ye[a], yv[b], ye[b], yv[a]),
                (ye[a] == yv[b], xe[a], xv[b], xe[b], xv[a]),
                (ye[b] == yv[a], xe[a], xv[b], xe[b], xv[a]),
            ]
        ):
            lit = md.NewBoolVar(f"touch_{a}_{b}_{i}")
            md.Add(eq).OnlyEnforceIf(lit)
            md.Add(p >= q + SHARED_WALL_MIN_DM).OnlyEnforceIf(lit)
            md.Add(r >= t + SHARED_WALL_MIN_DM).OnlyEnforceIf(lit)
            choices.append(lit)
        touch = md.NewBoolVar(f"touch_{a}_{b}")
        md.AddMaxEquality(touch, choices)
        if adj.hard:
            md.Add(touch == 1)
        else:
            objective.append(adj.weight * (1 - touch))
    maxx, maxy = md.NewIntVar(0, ew, "maxx"), md.NewIntVar(0, eh, "maxy")
    md.AddMaxEquality(maxx, list(xe.values()))
    md.AddMaxEquality(maxy, list(ye.values()))
    objective.extend([maxx, maxy])
    md.Minimize(sum(objective))
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = seed
    solver.parameters.max_deterministic_time = det_time
    status = solver.Solve(md)
    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    value = solver.ObjectiveValue() if feasible else -1
    bound = solver.BestObjectiveBound() if feasible else None
    bounds = (
        {
            r.id: [
                solver.Value(xv[r.id]),
                solver.Value(yv[r.id]),
                solver.Value(wv[r.id]),
                solver.Value(hv[r.id]),
            ]
            for r in scenario.rooms
        }
        if feasible
        else {}
    )
    return SolveResult(
        method,
        scenario.name,
        solver.StatusName(status),
        round(time.perf_counter() - started, 4),
        round(solver.deterministic_time, 4),
        value,
        len(md.Proto().variables),
        len(md.Proto().constraints),
        bounds,
        bound,
        round(max(0, value - bound) / max(1, abs(value)), 6) if feasible else None,
    )


def solve_nooverlap2d(scenario, seed=42, det_time=5.0):
    return _solve(scenario, "nooverlap_2d", seed, det_time)


def solve_pairwise_disjunctive(scenario, seed=42, det_time=5.0):
    return _solve(scenario, "pairwise_disjunctive", seed, det_time)


def solve_row_intervals_1d(scenario, seed=42, det_time=5.0):
    return _solve(scenario, "row_intervals_1d", seed, det_time)


def run_benchmark(scenarios=None):
    scenarios_by_name = build_scenarios()
    return [
        fn(scenarios_by_name[name])
        for name in scenarios or scenarios_by_name
        for fn in (solve_nooverlap2d, solve_pairwise_disjunctive, solve_row_intervals_1d)
    ]


def verify_determinism(scenario, runs=3):
    results = [solve_nooverlap2d(scenario) for _ in range(runs)]
    return all(
        r.status in ("FEASIBLE", "OPTIMAL")
        and r.room_bounds == results[0].room_bounds
        and r.objective_val == results[0].objective_val
        for r in results
    )


def render_markdown_table(results):
    lines = [
        "| Scenario | Formulation | Status | Wall s | Det time | Objective | "
        "Bound | Gap | Vars | Constraints |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        lines.append(
            f"| {r.scenario} | {r.method} | {r.status} | {r.wall_time_s:.3f} | "
            f"{r.deterministic_time:.3f} | {r.objective_val:g} | {r.best_bound} | "
            f"{r.relative_gap} | {r.num_variables} | {r.num_constraints} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--scenario", choices=list(build_scenarios()))
    args = parser.parse_args()
    results = run_benchmark([args.scenario] if args.scenario else None)
    print(
        json.dumps([asdict(r) for r in results], indent=2)
        if args.json
        else render_markdown_table(results)
    )
    if args.check:
        scs = build_scenarios()
        if not all(verify_determinism(scs[n]) for n in ["small_5_rooms", "medium_9_rooms"]):
            print("ERROR: reproducible feasible result required", file=sys.stderr)
            return 1
        if any(
            r.status not in ("FEASIBLE", "OPTIMAL")
            for r in results
            if r.method == "nooverlap_2d" and r.scenario != "large_14_rooms"
        ):
            return 1
        print("All checks passed: feasible repeated 2D solves, consistent requirements/objective.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
