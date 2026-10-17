---
name: generate-concepts
description: Generate solver-backed residential floor-plan concepts using CP-SAT across six massing strategies, report feasibility, perform structured revisions, and prepare for the plan approval gate.
---

# Generate Concepts

## Purpose
Guide the agent through generating solver-backed, geometrically valid floor-plan concepts from an approved space program and verified site model. The generator evaluates layout options across six massing strategies, reports feasibility reasons for rejected layouts, applies structured revision operations, and prepares concepts for the plan approval gate.

## When to invoke
- When generating initial floor-plan concepts from an approved program and site.
- When generating an uncommitted exploratory preview (`--exploratory`) during earlier design exploration.
- When testing massing strategies (`compact`, `split_level`, `split_walkout`, `linear`, `two_wing`, `courtyard`).
- When revising a concept based on homeowner feedback (`--area`, `--separate`, `--adjacent`, `--level`, `--rethink`).
- When comparing alternative concepts side-by-side or requesting review at the plan approval gate.

## Inputs
- Project identifier (`<project-id>`).
- Approved site model and space program (for gated generation).
- Target massing strategies or revision operations.
- Homeowner feedback statements for revisions.

## Outputs
- Concept records stored in `ProjectStore` (`artifacts/plan/...`).
- Evaluated concepts with 2D floor-plan geometry and schematic terrain sections (`plan.svg`).
- Metric summaries, constraint violations, and evaluator findings.
- Comparison matrix across generated options (`comparison.md`).

## Exact commands

1. **List available generator strategies:**
   ```bash
   .venv/bin/house-ai plan strategies
   ```

2. **Exploratory preview (read-only, no approval required, stores nothing):**
   ```bash
   .venv/bin/house-ai plan generate <project-id> --exploratory --out /tmp/preview \
     --actor agent:gemini
   ```

3. **Gated concept generation (stores concepts in ProjectStore):**
   *(Requires approved site and program gates)*
   ```bash
   # Generate across all strategies:
   .venv/bin/house-ai plan generate <project-id> --actor agent:gemini

   # Or generate for a specific strategy with a chosen seed:
   .venv/bin/house-ai plan generate <project-id> --strategy split_walkout --seed 42 \
     --actor agent:gemini
   ```

4. **List and compare generated concepts:**
   ```bash
   .venv/bin/house-ai plan list <project-id>
   .venv/bin/house-ai plan compare <project-id>
   ```

5. **Export concept artifacts for inspection:**
   ```bash
   .venv/bin/house-ai plan export <project-id> <concept-id> --out projects/<project-id>/design/concepts/<concept-id>
   ```

6. **Revise a concept based on homeowner instructions:**
   ```bash
   # Adjust room area and acoustic separation:
   .venv/bin/house-ai plan revise <project-id> <concept-id> "<verbatim owner words>" \
     --area pi-kitchen=16 --separate pi-bed-main,pi-bed-child-1 --actor agent:gemini

   # Rethink an entire zone or change level:
   .venv/bin/house-ai plan revise <project-id> <concept-id> "<verbatim owner words>" \
     --rethink z-night --level pi-office=entry --actor agent:gemini

   # Restart a concept from the approved space program:
   .venv/bin/house-ai plan revise <project-id> <concept-id> "<verbatim owner words>" \
     --kind restart_from_program --actor agent:gemini
   ```

7. **Request review at the plan approval gate:**
   ```bash
   .venv/bin/house-ai plan review <project-id> <concept-id> --actor agent:gemini
   ```

## Required validations
- Gated generation strictly refuses on unapproved real projects (e.g. `projects/my-house` before site and program gate approvals).
- Geometry is generated deterministically by CP-SAT solver and validated with `house_ai.domain.integrity.check_model`. Never edit room coordinates by hand.
- Every metric must report its epistemic status: `measured`, `inferred`, `simulated`, or `not_checked`.
- Every revision must store the homeowner's verbatim feedback and explicit structured operations.

## Human-approval boundaries
- **NEVER** approve the plan gate: `house-ai workflow approve <project-id> plan` is strictly human-only.
- If the owner selects a preferred concept, the agent prepares the review package and prompts the owner to run:
  ```bash
  .venv/bin/house-ai workflow approve <project-id> plan --id <concept-id> --version <v> --approver <name>
  ```

## Failure handling
- **Infeasible strategy**: If CP-SAT reports a strategy is infeasible (e.g. `linear` requires more frontage than parcel width), explain the geometric contradiction plainly. Never hide infeasibility.
- **Unapproved gate blocker**: If `plan generate` refuses because gates are unapproved, use `--exploratory` for previews and explain which human gate must be approved.
- **Constraint violations**: If evaluators detect blocking violations (e.g. missing exterior access or elongated rooms), diagnose the root constraint and formulate revision operations.
