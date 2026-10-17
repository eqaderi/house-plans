# ADR 0013: Solver-backed plan concepts on a bar/row topology with OR-Tools CP-SAT

Status: accepted (Milestone D, 2026-10-17)

## Context

Milestone D must turn an approved space program into at least three
genuinely different floor-plan concepts, with valid vector geometry, no
invented coordinates, deterministic checks, honest metrics and versioned
revisions. The primary project is a steep hillside parcel with road access on
one side, so the concepts must handle split levels, walk-out levels,
road-level parking and earth-retaining walls. No paid model API may be needed.

## Decision

1. **Hybrid pipeline, no LLM coordinates.** A *strategy* fixes the topology;
   a formal solver fixes the dimensions; deterministic code assembles and
   checks the canonical model. Coding agents choose strategies and translate
   the owner's revision requests into structured operations; they never
   write geometry.
2. **Topology: double-loaded bars.** A massing is a set of orthogonal bars,
   each a room row on either side of a corridor, in a *design frame* whose
   u axis runs along the parcel edge facing the road and whose v axis runs
   into the site. Every room touches its corridor (reachability by
   construction) and walls follow from shared edges. Strategies differ in
   topology, not seed: `linear` (one bar on the contours), `compact`
   (identical bars stacked, walk-out below the entry when the ground falls
   away), `split_level` (parallel bars stepping in half-storey increments
   from the surveyed ground), `two_wing` (an L whose night wing runs into the
   site and steps with it), `courtyard` (two pavilions and a gallery).
3. **Solver: Google OR-Tools CP-SAT** (`ortools`, Apache-2.0). Integers on a
   10 cm grid. HARD: rows tiled exactly (units plus optional filler), room
   minimum areas and widths, entry and garage on the road row, step-free
   rooms on the entry level, aligned stairs and links, hard near/separation
   between clusters. SOFT, integer-weighted: target areas (oversizing
   penalised), filler area, level preferences, zone-to-bar fit, daylight for
   rooms that need it, soft adjacencies and separations, bar length, and in
   revisions closeness to the parent. Objective weights scale with the
   compiled soft objectives (privacy, acoustic zoning, daylight, envelope
   simplicity, ...).
4. **Clusters for hard connections.** Rooms joined by HARD `connected`
   requirements form a cluster laid out by exhaustive search as slots of one
   room or two stacked rooms (corridor side / exterior side), so a triangle
   such as open living-kitchen-dining is satisfiable in a row.
5. **Determinism.** One worker, a fixed seed and a deterministic-time budget
   (never wall-clock). The same inputs give the same plan on the same
   platform; tests assert properties (integrity, minima, adjacencies,
   diversity, determinism within a run), not byte-exact solver output, which
   may differ between platforms. Hand-authored `plan-a` has a byte-exact SVG
   golden file.
6. **Terrain-aware levels without flattening the site.** Level elevations,
   earth contact and retaining walls come from the surveyed TIN (inferred),
   never from extrapolation. Unknown terrain places levels at the local
   datum and says so; split levels are refused when the ground is flat or
   unknown. Cut, fill and retained earth are reported as metrics.
7. **Honest invalidity and refusal.** A candidate failing `check_model` is
   stored and reported as invalid; a strategy that cannot be laid out is
   listed with the reason. Gated generation works only on the approved site
   and program and writes nothing when refused. `--exploratory` previews
   unapproved inputs and writes nothing to the store.
8. **Reproducibility record.** `PlanVersion.generation` (optional, so
   hand-authored plans and earlier artifacts stay valid) records solver,
   versions, status, objective, seed, parameters and room placements.

## Consequences

- Plans are orthogonal and built from rectangular rooms; polygons and
  non-orthogonal or courtyard-with-hole geometry fit the domain model but
  need further strategies.
- Corridors are generous (every bar has one), and rows are closed with
  flexible space when the program does not fill them; both are measured
  (`circulation_ratio`, `unprogrammed_area_m2`) rather than hidden.
- `combine` revisions ("the entrance of B with the courtyard of A") are not
  supported yet; the CLI refuses them and asks for explicit operations.
- OR-Tools adds a binary wheel dependency (with protobuf and pandas); it has
  wheels for Python 3.11 and 3.13 on Linux and macOS.
