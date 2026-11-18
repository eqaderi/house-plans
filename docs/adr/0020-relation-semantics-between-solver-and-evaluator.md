# ADR 0020: Space relationship semantics shared by solver and evaluator

Status: accepted (Stage S7, closed 2026-10-18)

## Context

Before Stage S7 the CP-SAT solver (`generation/solver.py`, `rooms.py`,
`assemble.py`) and the evaluators (`AdjacencyEvaluator`, `CirculationEvaluator`,
`PrivacyEvaluator` in `evaluation/evaluators.py`) each had their own meaning for
every space relationship kind (ISS-12). The solver read `ADJACENT` as two units
touching in one row, the evaluator as a shared wall of at least 1.0 m; `NEAR` was
"same bar" to one and "at most 2 hops" to the other; touching `CONNECTED` spaces
in different clusters got no door; `SEPARATED` was checked only within a row;
`VISUAL`, `EXTERIOR`, `hall` and same-cluster pairs were skipped or handled ad
hoc. A plan the solver called optimal could receive violations for the very
relationships it optimised, and the reverse.

## Decision

One definition of each space relationship kind lives in
`src/house_ai/domain/relations.py`, with its thresholds in
`src/house_ai/constants/relations.py`. The solver, the assembler and the
evaluators all use it.

### 1. Definitions

- **`ADJACENT`**:
  - Two indoor spaces share a partition wall segment with clear shared contact
    length >= `SHARED_WALL_MIN_M` (0.9 m).
  - An indoor space and `EXTERIOR` share an exterior envelope wall segment with
    length >= `EXTERIOR_SHARED_WALL_MIN_M` (1.0 m).
  - In solver models (1D bars or 2D floor plans): spaces required to be adjacent
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
  - In solver models: spaces in the same bar or accessible off the same corridor
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
  - Sightline relation. Requires unobstructed line of sight (e.g. between parts of an
    open-plan space or through cased/glazed interior apertures). If sightline analysis is
    not supported for the plan geometry, it is explicitly reported as
    `not_checked` (`ClaimStatus.NOT_CHECKED`, method `line_of_sight_analysis`).
- **`hall` pairs**:
  - Circulation connections. A space with `CONNECTED` to `hall` receives a door
    connecting it to the level's hall/corridor.
- **Intra-cluster pairs**:
  - Relationships between spaces in the same cluster (e.g. bedroom and ensuite) are
    validated with the exact same shared logic; clustering must ensure internal
    slots satisfy `ADJACENT` or `CONNECTED` and never violate `SEPARATED`.

### 2. Implementation boundaries

- `src/house_ai/domain/relations.py` provides:
  - `shared_wall_length(model, space_a, space_b) -> float`
  - `exterior_wall_length(model, space) -> float`
  - `is_relation_satisfied(kind, model, graph, a_spaces, b_spaces) -> tuple[bool | None, str]`
- `AdjacencyEvaluator` delegates directly to `is_relation_satisfied()`.
- `assemble.py` inspects soft and hard `CONNECTED` space relationships, placing
  inter-space doors for touching spaces that require connection.
- `rooms.py` and `solver.py` encode relationships honoring `EXTERIOR`, `hall`, and
  intra-cluster constraints consistently.

## Consequences

- Eliminates false positive and false negative discrepancies between solver
  scores and evaluator findings.
- CodePack rules and space relationships produce consistent violations
  when unmet and consistent passes when satisfied.
- Preserves backwards compatibility: existing models remain valid under
  `check_model`, and existing evaluation reports retain identical schema output.
