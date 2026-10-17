# Milestone D: plan concepts, evaluation and versioning

Date: 2026-10-17. Branch: `milestone-d`, created from `main` after PR #1
(survey evidence correction) was merged. Not merged into `main`. Design:
[ADR 0013](../adr/0013-solver-backed-plan-generation.md). Agent instructions:
[AGENT_CONTRACT.md §9b](../AGENT_CONTRACT.md), worked commands:
[AGENT_WORKFLOWS.md](../AGENT_WORKFLOWS.md).

## What works

- **Constraint compilation** (`house_ai.constraints.compiler`): the approved
  program, the brief, the site and an optional CodePack become an explicit
  `ConstraintSet`. HARD: geometric validity, no overlap, openings on walls,
  doors between the spaces they name, every space reachable, inside the
  buildable envelope (or, with no envelope, inside the parcel, flagged as
  not the buildable area), program minimum areas and widths, hard
  adjacencies. SOFT (weighted): soft adjacencies and objectives taken from
  what the owner said (privacy, acoustic zoning, slope response, ...) plus
  labelled system defaults. CodePack rules become constraints only when their
  parameters are understood (`function` + `min_area_m2`/`min_width_m`); an
  unverified pack yields soft guidance and the label "conceptual best-practice
  check only"; anything else is reported as not checked. No regulation is
  invented.
- **Solver-backed generator** (`house_ai.generation`, OR-Tools CP-SAT): five
  structural strategies (`compact`, `split_level`, `linear`, `two_wing`,
  `courtyard`) laid out on a 10 cm grid in a frame aligned with the road
  frontage, so rotated parcels work. Hard-connected rooms (e.g. an open
  living-kitchen-dining triangle, a bedroom with its en-suite) are placed as
  clusters whose every required pair shares a wall. The entry and garage sit
  on the road row; step-free rooms stay on the entry level. A strategy that
  cannot be laid out is reported with the reason; a layout failing
  `check_model` is kept and reported as invalid.
- **Steep sites.** Level elevations come from the surveyed TIN: the entry
  level at the ground along the road-side face; `compact` puts the other
  floors below as a walk-out when the ground falls away; `split_level` and
  `two_wing` step in half-storey increments chosen from the ground under each
  bar; split levels are refused on flat or unknown terrain. Exterior faces
  with ground more than 0.6 m above their floor become retaining walls (no
  windows); faces against a neighbouring split level are party walls. Cut,
  fill/void, retaining-wall length and retained earth face are reported, all
  marked `inferred`.
- **Canonical output.** Each concept is a `PlanVersion` with a full
  `HouseModel`: levels, spaces, walls derived from shared edges, doors (swing,
  sliding garage door), cased openings, windows, stairs with riser counts,
  floor and roof slabs, ceilings, zones, relationships to the program,
  materials (placeholders), assumptions and issues, plus a `GenerationRecord`
  for reproduction and revision.
- **Six evaluators** (`house_ai.evaluation`): Geometry (`check_model`, minimum
  dimensions, areas, footprint, compactness), Program (counts, areas against
  targets, level preferences, step-free rooms, level count), Adjacency (each
  requirement measured by graph or shared boundary), Circulation
  (reachability, circulation share, depth, straight-line walking distance,
  routes through private rooms), Privacy (bedrooms off the entrance, private /
  public shared walls, entrance sightline), Site (envelope, clearance,
  coverage, road distance of entrance and garage, terrain fit). Every metric
  carries method and status; the nine future evaluators are listed as not run.
  No single score.
- **Plan SVG** (`render2d/plan_svg.py`): one panel per level at a common
  scale with parcel, envelope, road, walls by kind, door swings, windows,
  stairs with direction and rise, room names, areas and dimensions, overall
  dimensions, the circulation tree from the front door, the north arrow only
  when the CRS is confirmed, and a schematic section against the terrain.
- **Versioning and revisions** (`orchestration/plans.py`, `house-ai plan`):
  gated generation stores the constraint set, each plan and its evaluation
  and moves PROGRAM_APPROVED → CONCEPT_GENERATION → CONCEPT_REVIEW. A
  revision records the owner's words verbatim and the agent's explicit
  operations (`--area`, `--level`, `--separate`, `--adjacent`, `--near`,
  `--rethink`, `--strategy`, `--kind restart_from_program`), solves close to
  the parent (only the affected rooms move), stores a new version with its
  parent and a `RevisionReport` (rooms and areas changed, metric changes,
  new and resolved violations, assumptions). `plan review` requests the plan
  gate; only a human can approve it, and an approved plan is frozen.
- **Exploratory preview** (`plan generate --exploratory`): same pipeline on
  unapproved inputs, writes nothing to the project, every file stamped.
- **Exports** per concept and version: `plan.json`, `plan.svg`,
  `metrics.json`, `violations.json`, `assumptions.json`, `explanation.md`;
  `comparison.md` across concepts with measured diversity (footprint overlap,
  rooms on a different level, levels/stairs).

## Demonstration

Synthetic steep hillside (`examples/projects/synthetic-hillside/`, about
36 % fall away from the road, rotated parcel, assumed setbacks):

```bash
.venv/bin/house-ai example load /tmp/hill --name synthetic-hillside --project-id synthetic-hillside --actor human:example
.venv/bin/house-ai plan generate /tmp/hill --exploratory --out /tmp/hill-preview --actor agent:claude-code
```

Result (committed in `examples/projects/synthetic-hillside/concepts/`):
four concepts with no hard violations and 2 to 4 soft violations each;
`courtyard` is reported infeasible (the 24 m deep envelope cannot hold two
pavilions and a court).

| | compact | split_level | linear | two_wing |
|---|---|---|---|---|
| Floor levels | 2 | 2 | 1 | 2 |
| Gross area (centreline) | 240 m² | 222 m² | 210 m² | 202 m² |
| Excavation (inferred) | 104 m³ | 0 | 0 | 0 |
| Fill / void under floors (inferred) | 40 m³ | 649 m³ | 485 m³ | 552 m³ |
| Retaining walls | 22 m | 0 | 0 | 0 |
| Longest walk from the door (inferred) | 19.9 m | 31.0 m | 20.0 m | 27.8 m |

The trade-off is visible rather than scored: the compact walk-out digs in and
needs retaining walls; the stepped and linear concepts sit over the slope.
The full gated flow (approvals by a human, then `plan generate`, `plan
revise`, `plan review`) is exercised by `tests/test_plan_workflow.py`.

On the synthetic flat bungalow all strategies except `split_level` (refused:
"a split level is not warranted") produce valid concepts, and the unverified
synthetic CodePack yields "conceptual best-practice check only".

## `projects/my-house`

Untouched by this milestone (`project verify my-house`: intact, 13 events,
10 artifact versions). It is in `SITE_NEEDS_VERIFICATION` and has no
interview, brief or program yet, so `plan generate my-house` refuses (gated
and exploratory) and writes nothing. Next steps for the owner are in
[AGENT_WORKFLOWS.md](../AGENT_WORKFLOWS.md#projectsmy-house-today).

## Tests

```bash
.venv/bin/python -m pytest -q          # 465 passed (Python 3.13); 464 passed, 1 skipped on 3.11
.venv/bin/ruff check src tests examples # all checks passed
.venv/bin/house-ai schemas check        # 22 schemas up to date
.venv/bin/house-ai project verify my-house  # intact: 13 events, 10 artifact versions
```

New: `test_plan_generation.py` (validity, minima, hard connections, the
open-plan triangle, rotated frame, terrain-following levels, walk-out
retaining walls, determinism, refusals), `test_plan_evaluation.py` (compiler
hard/soft split, brief objectives, CodePack handling, ground-truth metrics of
the hand-authored plan, claim status, no professional claims),
`test_plan_workflow.py` (store, gates, refusal without writes, exploratory,
revisions, human-only plan gate, CLI), `test_plan_svg.py` (byte-exact golden
of plan-a, north arrow rules, fixture currency).

## Known limitations

- Rooms are rectangles on orthogonal bars with a corridor in every bar;
  courtyards with holes, non-orthogonal rooms and corridor-free open plans
  need further strategies (the domain model already supports them).
- Rows are closed with flexible space when the program does not fill them,
  and corridors are generous; both are reported, not optimised away.
- Concepts that keep a whole bar at road level sit over a falling slope; the
  void beneath is reported as fill/void, not turned into rooms. Combining
  split-level stepping with walk-out floors is a natural next strategy.
- Stair, wall, floor-to-floor and garage dimensions are typical placeholders
  (assumptions); nothing is structurally, geotechnically or code checked.
- Daylight, views, orientation, acoustics beyond shared walls, cost and
  structure are not evaluated (evaluators listed as not run).
- `combine` revisions are refused; express them as explicit operations.
- CP-SAT results are deterministic per platform but may differ slightly
  between operating systems; tests check properties, not solver bytes.
- Fixtures and furniture are not placed; outdoor items (terrace, garden) are
  not placed and their adjacencies are reported as not checked.

## Next milestone

Milestone E (reviewer): inspect concepts side by side, show the stored
metrics and violations, compare versions using the revision reports, and
capture the owner's change requests for `plan revise`. Not started.
