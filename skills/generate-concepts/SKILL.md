---
name: generate-concepts
description: Generate solver-backed residential floor-plan concepts using CP-SAT across six massing strategies, report feasibility, perform structured revisions, and prepare for the plan approval gate.
---

# Generate Concepts

Follow [docs/AGENT_CONTRACT.md](../../docs/AGENT_CONTRACT.md) (§3 one model,
§9b plan concepts, §10 professional boundary). In every command,
`agent:<tool>` is your own tool name: `claude-code`, `codex` or `gemini`.

## Purpose
Guide the agent through generating solver-backed, geometrically checked floor-plan concepts from an approved space program and site. The generator tries six massing strategies, reports why rejected strategies are infeasible, applies structured revision operations, and prepares concepts for the human plan gate.

## When to invoke
- When generating concepts from an approved program and site.
- When previewing concepts before the gates are approved (`--exploratory`).
- When testing massing strategies (`compact`, `split_level`, `linear`, `two_wing`, `courtyard`, `split_walkout`).
- When revising a concept from homeowner feedback (`--area`, `--separate`, `--adjacent`, `--near`, `--level`, `--rethink`).
- When comparing concepts or requesting review at the plan gate.

## Inputs
- Project folder or name under `projects/` (`<project>`).
- Approved site and space program (for stored generation).
- Strategies, or the owner's revision words.

## Outputs
- Stored plan versions (`artifacts/plan/...`), only after the site and program gates.
- Per concept: `plan.json`, `plan.svg`, `metrics.json`, `violations.json`, `assumptions.json`, `explanation.md`.
- `comparison.md` across concepts, including infeasible strategies with their reasons.

## Exact commands

1. **List the strategies:**
   ```bash
   .venv/bin/house-ai plan strategies
   ```

2. **Exploratory preview (any state; stores nothing; never call it validated):**
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
   .venv/bin/house-ai plan export <project> <concept-id> --out projects/<project>/design/concepts/<concept-id>
   ```

5. **Revise from the owner's words** (room and zone IDs come from the program, e.g. on synthetic-hillside `pi-kitchen`, `pi-bed-main`, `pi-study-1`, `z-night`; `--level` takes `entry`, `not_entry`, `upper` or `lower`):
   ```bash
   .venv/bin/house-ai plan revise <project> <concept-id> "<verbatim owner words>" \
     --area pi-kitchen=16 --separate pi-bed-main,pi-bed-child-1 --actor agent:<tool>

   .venv/bin/house-ai plan revise <project> <concept-id> "<verbatim owner words>" \
     --rethink z-night --level pi-study-1=entry --actor agent:<tool>

   .venv/bin/house-ai plan revise <project> <concept-id> "<verbatim owner words>" \
     --kind restart_from_program --actor agent:<tool>
   ```

6. **Request the plan gate review:**
   ```bash
   .venv/bin/house-ai plan review <project> <concept-id> --actor agent:<tool>
   ```

## Required validations
- Stored generation refuses before the site and program gates; on an unapproved project only `--exploratory` runs.
- Geometry comes from the CP-SAT solver and is checked with `house_ai.domain.integrity.check_model`. Never edit coordinates by hand.
- Report every metric with how it was obtained (`measured`, `inferred`, `simulated`, `not_checked`).
- Every revision stores the owner's verbatim words and explicit operations.
- Present several concepts with their trade-offs; never present one as "the answer".

## Human-approval boundaries
- **NEVER** run `house-ai workflow approve <project> plan`: the plan gate is human-only.
- When the owner prefers a concept, run `plan review` and ask them to run, in their own terminal:
  ```bash
  .venv/bin/house-ai workflow approve <project> plan --id <concept-id> --version <v> --approver <name>
  ```

## Failure handling
- **Infeasible strategy**: quote the solver's reason from `comparison.md` (e.g. not enough envelope depth for a courtyard). Never hide infeasibility.
- **Refused because gates are not approved**: use `--exploratory` and name the human gate still open.
- **Constraint violations**: find the constraint behind each violation and propose explicit revision operations.
