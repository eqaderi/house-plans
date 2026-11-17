# ADR 0032: An engine seam inside the plan generator

Status: accepted (2026-11-17).

## Context

`CpSatPlanGenerator._strategy` held two engines in one function
([ADR 0013](0013-solver-backed-plan-generation.md)). The **bar engine** expands
the Space program into bar rooms, builds a strategy's massing for a few
row-depth patterns, solves each with CP-SAT and assembles each solution
([ADR 0023](0023-stairs-between-split-levels.md)). The **2D engine** places
the Spaces as no-overlap rectangles on fixed stacked Levels and assembles
that. Both then built a generation record and a Plan version, twice, with
small differences. Which engine ran was decided inline by a condition that
mixed the strategy, a topology proposal, a stair position, outdoor links and
a `force_2d` flag that `compile_revision` stored in the solver options next
to the options themselves. The routing rule could not be tested without
solving a plan.

[ADR 0027](0027-deep-modules-at-the-human-and-private-data-seams.md) deleted
the `generation.base.PlanGenerator` protocol and said "a generator protocol
returns when a second generator exists". That sentence is about the whole
generator (what `PlanService` calls); there is still one. The two engines are
a seam *inside* that one generator, not a second generator.

## Decision

- `house_ai.generation.engines` holds one interface, `Engine.lay_out(strategy,
  ctx)`: a strategy and its `EngineContext` (Site, Space program, design frame
  and limit, ground, options, proposal, sectional strategy, names for the
  model) go in; a list of `Layout`s comes out (a house model plus the engine's
  part of the generation record: solver, status, objective, parameters,
  placements and the provenance method), or `NoLayout` with the reason the
  strategy is infeasible.
- Two adapters: `BarEngine` and `TwoDEngine`. Each owns its Space-requirement
  expansion, its solve and its assembly call. The bar engine returns one
  layout per row-depth pattern that solved; the 2D engine returns one.
- The generator keeps strategy ordering, option ids, the integrity check
  (it checks every layout and keeps the integrity-clean one with the lowest
  objective), provenance and the storey-count Assumption. The generation
  record and the Plan version are built in one place for both engines.
- Engine choice is one explicit function, `generator.route(strategy,
  request)`: the 2D engine takes `corridor_free` and `open_plan`, every
  topology proposal, and any request for a stair position or an outdoor link;
  the bar engine takes the rest. `SolverOptions.force_2d` is deleted.
  `CpSatPlanGenerator(engines=...)` accepts other engines, so the rule is
  tested with a stub engine and no solve (`tests/test_plan_engines.py`).
- The stored generation record is unchanged, including 2D placements written
  under the single main bar id (`wing-main`).
- Each engine owns its options and its generation parameters. The shared
  options bag is split: `solver.BarOptions` and `solver2d.PlacementOptions`
  hold only what their solver reads. The generator passes what the Owner
  asked (`engines.OwnerRequests`: area targets, level preferences, Space
  relationships, stair position, outdoor links, and for a revision the
  parent's generation record and the rethought Spaces), seed, time budget,
  objective weights and hard minimums; each engine builds its own options.
  `revision.compile_revision` returns `OwnerRequests`, not solver options.
- The bar engine writes `<bar>_start_m` and `<bar>_length_m` and is the only
  reader of a parent's placements and bar starts
  (`BarEngine.position_hints`). Position hints are computed only for it: the
  2D solver reads none (tracker ISS-41 records that 2D revisions ignore the
  parent's positions). The 2D engine writes `engine` and
  `optimised_objectives`; `engines.optimised_objectives(record)` reads them,
  and the caller passes the result to `explanation_markdown(optimised=...)`,
  so the evaluation package still depends on the domain only.

## Consequences

- Generated output for every strategy on the synthetic fixtures is
  byte-identical before and after (house model, generation record,
  provenance, infeasible reasons, explanation documents and a set of
  revisions through both engines).
- Deleted as dead: the merge of a proposal's adjacency graph into the Space
  program before bar expansion (a proposal always goes to the 2D engine,
  which reads the adjacency graph itself); the copy of a proposal's level
  assignments into the level preferences (the 2D solver reads the
  assignments itself, with the same precedence); and `Candidate.attempts`,
  which nothing read except the reason built from it.
- A third engine is one more adapter and one more branch in `route`.
