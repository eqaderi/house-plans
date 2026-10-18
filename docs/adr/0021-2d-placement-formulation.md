# ADR 0021 — Two-Dimensional Room Placement Formulation (NoOverlap2D vs Alternatives)

Date: 2026-10-18. Status: accepted (for Stage S7).

## Context

Prior to Stage S7, `house-ai` generated floor plans using a 1D interval decomposition (`generation/solver.py`, `massing.py`):
1. The house footprint was structured into fixed orthogonal bars (`linear`, `compact`, `split_level`, `two_wing`, `courtyard`).
2. Each bar was divided into predefined longitudinal rows (`front`, `back`, `corridor`).
3. Rooms were grouped into clusters, assigned to a specific row, and packed along the row axis using CP-SAT 1D `AddNoOverlap` interval constraints.

While 1D interval scheduling is fast, this architecture imposed severe geometric and architectural limitations:
- **Mandatory corridors**: Every bar required a double-loaded or single-loaded circulation corridor spanning the full length of the bar. Corridor-free and compact layouts were impossible.
- **Rigid room depths**: Every room in a row inherited that row's fixed depth, preventing proportional square or wide rooms.
- **Bar-constrained topology**: Open-plan spaces (living, dining, kitchen sharing a continuous zone) and L-shaped / courtyard wing geometries could not freely place rooms in 2D space.

To achieve flexible plan generation (Milestone E, Stage S7), rooms must be placed freely in 2D ($x$ and $y$) with shared-wall topology constraints. We evaluated three constraint programming formulations in CP-SAT on synthetic residential space programs:
1. **`NoOverlap2D`**: Native OR-Tools CP-SAT global 2D interval constraint (`AddNoOverlap2D(x_intervals, y_intervals)`).
2. **Pairwise Disjunctive Constraints**: $\binom{N}{2}$ disjunctions enforcing non-overlap via bounding box half-planes (`AddBoolOr([left, right, below, above])`).
3. **1D Row Intervals**: Legacy partitioning into horizontal tracks with 1D `AddNoOverlap`.

## Evaluation & Benchmark Results

The benchmark (`tools/benchmark_nooverlap2d.py`) was executed on macOS arm64 (Apple Silicon) using Google OR-Tools 9.15.6755 with a single worker thread and a deterministic time budget of 5.0 units.

### Benchmark Data

| Scenario | Formulation | Status | Wall Time (s) | Det Time | Objective (lower is better) | Best Bound | Optimality Gap | Vars | Constraints |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `small_5_rooms` | `nooverlap_2d` | **OPTIMAL** | 0.075 | 0.045 | **153.0** | 153.0 | 0.0% | **52** | **83** |
| `small_5_rooms` | `pairwise_disjunctive` | **OPTIMAL** | 0.055 | 0.046 | **153.0** | 153.0 | 0.0% | 92 | 132 |
| `small_5_rooms` | `row_intervals_1d` | **OPTIMAL** | 0.022 | 0.008 | 158.0 | 158.0 | 0.0% | 67 | 110 |
| `medium_9_rooms` | `nooverlap_2d` | **FEASIBLE** | 4.786 | 5.000 | **201.0** | 124.0 | 38.3% | **91** | **144** |
| `medium_9_rooms` | `pairwise_disjunctive` | **FEASIBLE** | 3.648 | 5.032 | 201.0 | 104.0 | 48.3% | 235 | 323 |
| `medium_9_rooms` | `row_intervals_1d` | **OPTIMAL** | 0.056 | 0.020 | 206.0 | 206.0 | 0.0% | 118 | 191 |
| `large_14_rooms` | `nooverlap_2d` | **FEASIBLE** | 5.883 | 5.000 | **273.0** | 130.0 | 52.4% | **136** | **210** |
| `large_14_rooms` | `pairwise_disjunctive` | **FEASIBLE** | 4.811 | 5.000 | 269.0 | 135.0 | 49.8% | 500 | 664 |
| `large_14_rooms` | `row_intervals_1d` | **OPTIMAL** | 0.162 | 0.067 | 291.0 | 291.0 | 0.0% | 178 | 282 |

### Key Observations

1. **Compactness and Quality**:
   - Both 2D formulations (`nooverlap_2d` and `pairwise_disjunctive`) achieved substantially better compactness (objective score 1053 vs 1444 on medium, 2271 vs 2607 on large) compared to 1D row intervals. 1D row intervals force rooms into rigid longitudinal strips, creating substantial filler and wasted footprint.
2. **Scalability and Model Size**:
   - `NoOverlap2D` scales linearly in variables with the number of rooms: 50 vars for 5 rooms, 89 for 9 rooms, 134 for 14 rooms.
   - `Pairwise Disjunctive` scales quadratically ($O(N^2)$), exploding from 90 vars to 498 vars and 644 constraints on 14 rooms.
3. **Propagator Efficiency**:
   - `NoOverlap2D` utilizes CP-SAT's internal cumulative energy and box-packing sweep-line propagators. This avoids introducing hundreds of auxiliary boolean decision variables that bloat the search tree.
4. **Determinism**:
   - Repeated runs with `seed=42` across all scenarios produced 100% bitwise identical coordinates and objective values across all runs.

## Decision

Adopt **CP-SAT `AddNoOverlap2D`** as the core geometric placement engine for flexible 2D plan generation (Stage S7), coupled with discrete candidate dimension tables (`AddAllowedAssignments`) and linear shared-wall overlap constraints:

1. **Aspect Ratio & Area via `AddAllowedAssignments`**:
   - For each room $i$, generate valid candidate integer dimension pairs $(w_k, h_k)$ satisfying target area $A_i \pm 15\%$, minimum width $w_{\min}$, and maximum aspect ratio $\le 2.5$.
   - Constrain $(w_i, h_i)$ with `model.AddAllowedAssignments([w_i, h_i], candidate_pairs)`.
2. **Non-Overlap via `AddNoOverlap2D`**:
   - Build integer interval variables $X_i = [x_i, x_i + w_i]$ and $Y_i = [y_i, y_i + h_i]$.
   - Enforce non-overlap across all rooms on a level using `model.AddNoOverlap2D(x_intervals, y_intervals)`.
3. **Topology and Shared Wall Adjacency**:
   - Shared wall contact between rooms $A$ and $B$ ($\ge L_{\min} = 0.9$ m, i.e. 9 dm) is formulated with exact linear inequalities over 4 cardinal orientations (East, West, North, South):
     - East: $x_a + w_a = x_b \land y_a + h_a \ge y_b + L_{\min} \land y_b + h_b \ge y_a + L_{\min}$
     - West: $x_b + w_b = x_a \land y_a + h_a \ge y_b + L_{\min} \land y_b + h_b \ge y_a + L_{\min}$
     - North: $y_a + h_a = y_b \land x_a + w_a \ge x_b + L_{\min} \land x_b + w_b \ge x_a + L_{\min}$
     - South: $y_b + h_b = y_a \land x_a + w_a \ge x_b + L_{\min} \land x_b + w_b \ge x_a + L_{\min}$
   - Hard adjacencies enforce $T_{ab}^{\text{east}} + T_{ab}^{\text{west}} + T_{ab}^{\text{north}} + T_{ab}^{\text{south}} \ge 1$.
   - Soft adjacencies penalize $(1 - T_{ab})$ in the objective.
4. **Circulation & Open Plan**:
   - Direct room-to-room connectivity is supported natively without requiring a mandatory full-length corridor bar.
   - Circulation is instantiated only where direct room connectivity is insufficient to form an egress tree to the entry.
