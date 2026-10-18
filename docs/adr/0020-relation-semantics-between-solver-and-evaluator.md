# ADR 0020 — Shared relation semantics between solver and evaluator

Date: 2026-10-18. Status: proposed (for Stage S7).

## Context

Prior to Stage S7, plan generation (the CP-SAT solver in `generation/solver.py`,
`rooms.py`, and `assemble.py`) and plan evaluation (`AdjacencyEvaluator`,
`CirculationEvaluator`, and `PrivacyEvaluator` in `evaluation/evaluators.py`)
diverged significantly on spatial relationship semantics (ISS-12):

1. **`ADJACENT`**:
   - Solver checked 1D collinear touching of room units in the same row
     (`touch == 1`).
   - Evaluator checked 2D shared partition wall length >= 1.0 m (`SHARED_WALL_M`).
   - Exterior pairs (`(item, EXTERIOR)`): solver ignored them; evaluator
     evaluated them as `False` because `EXTERIOR` was filtered out of pairs.
2. **`CONNECTED`**:
   - Solver rewarded or enforced touching in the same row.
   - However, `assemble.py` only placed doors between rooms within the same
     initial cluster (`cl.connections`). If rooms were in separate clusters, no
     door was created even when they touched, causing `AdjacencyEvaluator` to
     fail `CONNECTED` (as no door existed in `circulation_graph`).
3. **`NEAR`**:
   - Solver enforced rooms being placed in the same bar (`same_bar == 1`).
   - Evaluator required graph distance <= 2 hops (`hops <= 2`).
4. **`SEPARATED` and `ACOUSTIC_SEPARATION`**:
   - Solver checked `touch == 0` within the same row only.
   - Evaluator checked that no direct door connects them and shared wall
     length is <= 0.1 m (`SEPARATION_TOUCH_TOLERANCE_M`).
5. **`VISUAL`**:
   - Solver ignored `VISUAL` relations completely.
   - Evaluator returned `None` (`not_checked`).
6. **`hall` and `EXTERIOR` pairs**:
   - Handled ad-hoc or skipped in solver; evaluator handled `EXTERIOR` partially
     for doors but not for wall boundaries.
7. **Intra-cluster pairs**:
   - Skipped by solver `_relation()` when both rooms belonged to the same unit
     (`ua is ub`).

These discrepancies meant that a plan judged optimal or compliant by the CP-SAT
solver could receive violations from `AdjacencyEvaluator` for the exact same
relations, and vice versa.

## Decision

Establish a single, authoritative definition of relation semantics in
`src/house_ai/domain/relations.py` with canonical constants in
`src/house_ai/constants/relations.py`. Both the solver/generator pipeline and
the evaluators import and obey these shared semantics.

### 1. Canonical Relation Definitions

- **`ADJACENT`**:
  - Two indoor spaces share a partition wall segment with clear shared contact
    length >= `SHARED_WALL_MIN_M` (0.9 m).
  - An indoor space and `EXTERIOR` share an exterior envelope wall segment with
    length >= `EXTERIOR_SHARED_WALL_MIN_M` (1.0 m).
  - In solver models (1D bars or 2D floor plans): rooms required to be adjacent
    must have overlapping shared boundaries of at least 0.9 m on the same level.
- **`CONNECTED`**:
  - A direct passable opening (hinged door, sliding door, or cased opening)
    connects the two spaces, creating an edge in `circulation_graph(model)`.
  - When paired with `EXTERIOR`, a direct exterior door connects the space to
    the outside.
  - In solver/assembly: when a `CONNECTED` relation (hard or soft) exists between
    spaces that share a boundary >= 0.8 m (`MIN_DOOR_WALL_LENGTH_M`), `assemble.py`
    places a connecting opening. If touching spaces cannot receive an opening or
    do not touch, the relation is reported unmet by both solver and evaluator.
- **`NEAR`**:
  - The spaces are accessible from one another with a short walk:
    circulation graph hops <= `NEAR_MAX_HOPS` (2 hops) AND path route distance
    <= `NEAR_MAX_DISTANCE_M` (12.0 m).
  - When paired with `EXTERIOR`, the space has an exterior route <= 2 hops.
  - In solver models: rooms in the same bar or accessible off the same corridor
    segment satisfy the near proxy; evaluated against the circulation network.
- **`SEPARATED`**:
  - The two spaces must NOT share a wall (shared contact length <=
    `SEPARATION_TOUCH_TOLERANCE_M` = 0.1 m) AND must NOT be connected by a
    direct opening (0 hops).
  - When paired with `EXTERIOR`, the space is fully internal (exterior contact
    <= 0.1 m, no direct exterior doors).
- **`ACOUSTIC_SEPARATION`**:
  - The two spaces must NOT share a wall (shared contact length <=
    `SEPARATION_TOUCH_TOLERANCE_M` = 0.1 m) AND must NOT share a direct door.
- **`VISUAL`**:
  - Sightline relation. Requires unobstructed line of sight (e.g. between open-plan
    zones or through cased/glazed interior apertures). If sightline analysis is
    not supported for the concept geometry, it is explicitly reported as
    `not_checked` (`ClaimStatus.NOT_CHECKED`, method `line_of_sight_analysis`).
- **`hall` pairs**:
  - Circulation connections. A room with `CONNECTED` to `hall` receives a door
    connecting it to the level's hall/corridor.
- **Intra-cluster pairs**:
  - Relations between rooms in the same cluster (e.g. bedroom and ensuite) are
    validated with the exact same shared logic; clustering must ensure internal
    slots satisfy `ADJACENT` or `CONNECTED` and never violate `SEPARATED`.

### 2. Implementation Boundaries

- `src/house_ai/domain/relations.py` provides:
  - `shared_wall_length(model, space_a, space_b) -> float`
  - `exterior_wall_length(model, space) -> float`
  - `is_relation_satisfied(kind, model, graph, a_spaces, b_spaces) -> tuple[bool | None, str]`
- `AdjacencyEvaluator` delegates directly to `is_relation_satisfied()`.
- `assemble.py` inspects soft and hard `CONNECTED` program adjacencies, placing
  inter-space doors for touching rooms that require connection.
- `rooms.py` and `solver.py` encode relations honoring `EXTERIOR`, `hall`, and
  intra-cluster constraints consistently.

## Consequences

- Eliminates false positive and false negative discrepancies between solver
  scores and evaluator findings.
- Verified CodePack rules and program adjacencies produce consistent violations
  when unmet and consistent passes when satisfied.
- Preserves backwards compatibility: existing models remain valid under
  `check_model`, and existing evaluation reports retain identical schema output.
