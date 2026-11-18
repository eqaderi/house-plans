---
name: generate-plan-options
description: Generate solver-backed residential floor-plan options using CP-SAT across six massing strategies, report feasibility, make structured revisions as new plan versions, and prepare for the plan approval gate.
---

# Generate Plan Options

## Purpose
Guide the agent through generating solver-backed, geometrically checked plan options from an approved space program and site. The generator tries six massing strategies, reports why rejected strategies are infeasible, applies structured revision operations (each makes the next plan version), and prepares a plan version for the human plan gate.

## When to invoke
- When generating plan options from an approved program and site.
- When previewing plan options before the gates are approved (`--exploratory`).
- When testing massing strategies (`compact`, `split_level`, `linear`, `two_wing`, `courtyard`, `split_walkout`).
- When revising a plan option from the owner's feedback (`--area`, `--separate`, `--adjacent`, `--near`, `--level`, `--rethink`).
- When comparing plan options or requesting review at the plan gate.

## Inputs
- Project folder or name under `projects/` (`<project>`).
- Approved site and space program (for stored generation).
- Strategies, or the owner's revision words.

## Outputs
- Stored plan versions (`artifacts/plan/...`), only after the site and program gates.
- Per plan option: `plan.json`, `plan.svg`, `metrics.json`, `violations.json`, `assumptions.json`, `explanation.md`.
- `comparison.md` across plan options, including infeasible strategies with their reasons.

## Exact commands

1. **List the strategies:**
   ```bash
   .venv/bin/house-ai plan strategies
   ```

2. **Exploratory preview (any workflow state; stores nothing; never call it validated):**
   ```bash
   .venv/bin/house-ai plan generate <project> --exploratory --out <scratch-dir>/preview --actor agent:<tool>
   ```

3. **Stored generation (requires PROGRAM_APPROVED or later):**
   ```bash
   .venv/bin/house-ai plan generate <project> --actor agent:<tool>
   .venv/bin/house-ai plan generate <project> --strategy split_walkout --seed 1 --actor agent:<tool>
   ```

4. **List, compare and export:**
   ```bash
   .venv/bin/house-ai plan list <project>
   .venv/bin/house-ai plan compare <project>
   .venv/bin/house-ai plan export <project> <option-id> --out projects/<project>/design/plan-options/<option-id>
   ```
   Option ids keep their saved form `concept-<strategy>` (e.g. `concept-split-walkout`).

5. **Revise from the owner's words** (space requirement and zone IDs come from the program, e.g. on synthetic-hillside `pi-kitchen`, `pi-bed-main`, `pi-study-1`, `z-night`; `--level` takes `entry`, `not_entry`, `upper` or `lower`):
   ```bash
   .venv/bin/house-ai plan revise <project> <option-id> "<verbatim owner words>" \
     --area pi-kitchen=16 --separate pi-bed-main,pi-bed-child-1 --actor agent:<tool>

   .venv/bin/house-ai plan revise <project> <option-id> "<verbatim owner words>" \
     --rethink z-night --level pi-study-1=entry --actor agent:<tool>

   .venv/bin/house-ai plan revise <project> <option-id> "<verbatim owner words>" \
     --kind restart_from_program --actor agent:<tool>
   ```
   "Three more alternatives" is `plan generate` with a new `--seed`. Combining
   features of several plan options ("the entrance of B with the courtyard of
   A") is `plan combine`, which needs the owner's words confirming the feature
   mapping (`.venv/bin/house-ai plan combine --help`).

6. **Request the plan gate review:**
   ```bash
   .venv/bin/house-ai plan review <project> <option-id> --actor agent:<tool>
   ```

## Required validations
- Stored generation refuses before the site and program gates; on an unapproved project only `--exploratory` runs.
- Geometry comes from the CP-SAT solver and is checked with `house_ai.domain.integrity.check_model`. Never edit coordinates by hand.
- Report every metric with how it was obtained (`measured`, `inferred`, `simulated`, `not_checked`).
- Every revision stores the owner's verbatim words and explicit operations.
- Present several plan options with their trade-offs; never present one as "the answer".

## Human-approval boundaries
- **NEVER** run `house-ai workflow approve <project> plan`: the plan gate is human-only.
- When the owner prefers a plan option, run `plan review` and ask them to run, in their own terminal:
  ```bash
  .venv/bin/house-ai workflow approve <project> plan --id <option-id> --version <v> --approver <name>
  ```
  Give the owner the exact command the CLI printed on its `next:` line, or
  `next_human_command` from `project status --json`: it is rendered in one place,
  pins the version and names the human (ADR 0029).

## Failure handling
- **Infeasible strategy**: quote the solver's reason from `comparison.md` (e.g. not enough envelope depth for a courtyard). Never hide infeasibility.
- **Refused because gates are not approved**: use `--exploratory` and name the human gate still open.
- **`OPEN unbuildable …` at plan review**: the plan version cannot be approved as drawn (ADR 0024). Do not ask the owner to approve it; explain the finding and revise. Show `ATTENTION …` lines to the owner; they do not block.
- **Constraint violations**: find the constraint behind each violation and propose explicit revision operations.
