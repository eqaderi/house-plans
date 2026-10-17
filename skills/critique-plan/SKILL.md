---
name: critique-plan
description: Perform grounded architectural critique of floor-plan concepts across geometry, circulation, privacy, and hillside metrics, separating measured facts from AI judgment and proposing structured revision operations.
---

# Critique Plan

## Purpose
Guide the agent through conducting a rigorous, evidence-grounded architectural critique of generated floor plans. The critique evaluates functional quality, zoning, circulation, daylight, privacy, and hillside relationships while separating measured facts from agent opinions, strictly referencing canonical entity IDs, and formulating structured revision operations.

## When to invoke
- When reviewing a newly generated floor-plan concept or comparing alternatives.
- When an agent needs to evaluate circulation efficiency, acoustic privacy, or room aspect ratios.
- When evaluating hillside excavation, underfloor void, retaining walls, or entrance levels.
- When formulating structured revision commands (`plan revise`) in response to architectural flaws or homeowner feedback.

## Inputs
- Concept artifacts (`plan.json`, `plan.svg`, `metrics.json`, `violations.json`, `explanation.md`).
- Approved space program (`space_program.yaml`) and design brief (`design_brief.yaml`).
- Evaluator outputs across Geometry, Program, Adjacency, Circulation, Privacy, and Site evaluators.

## Outputs
- Structured critique report categorized by architectural dimension.
- Epistemic status labels for every observation (`measured`, `inferred`, `ai_judgment`, `not_checked`).
- Concrete, executable `house-ai plan revise` commands referencing valid canonical IDs.

## Exact commands

1. **Inspect concept metrics and evaluator violations:**
   ```bash
   .venv/bin/house-ai plan export <project-id> <concept-id> --out /tmp/critique-export
   cat /tmp/critique-export/metrics.json
   cat /tmp/critique-export/violations.json
   ```

2. **Compare concept against peer alternatives:**
   ```bash
   .venv/bin/house-ai plan compare <project-id>
   ```

3. **Verify entity IDs in the approved space program:**
   ```bash
   cat projects/<project-id>/design/space_program.yaml | grep "id:"
   ```

4. **Formulate grounded revision commands:**
   ```bash
   # Resize an elongated or undersized space:
   .venv/bin/house-ai plan revise <project-id> <concept-id> \
     "<critique explanation>" --area pi-kitchen=18 --actor agent:gemini

   # Enforce acoustic privacy or physical adjacency:
   .venv/bin/house-ai plan revise <project-id> <concept-id> \
     "<critique explanation>" --separate pi-bed-main,pi-bed-child-1 \
     --adjacent pi-kitchen,pi-dining --actor agent:gemini

   # Move room to road-entry level or re-solve a whole zone:
   .venv/bin/house-ai plan revise <project-id> <concept-id> \
     "<critique explanation>" --level pi-office=entry --rethink z-night \
     --actor agent:gemini
   ```

## Required validations
- **Strict canonical ID grounding**: Every room, zone, and level cited in the critique must exist in the canonical model (e.g. `pi-kitchen`, `pi-bed-main`, `z-day`, `z-night`, `level-entry`, `level-lower`). Citing hallucinated or nonexistent IDs is strictly forbidden.
- **Epistemic status separation**:
  - `measured`: geometric dimensions, polygon areas, room counts, centerline hallway lengths.
  - `inferred`: cut/fill volumes, retaining wall heights, schematic underfloor void.
  - `ai_judgment`: aesthetic impression, functional flow perception, furniture usability.
  - `not_checked`: structural load paths, MEP runs, wind/microclimate, cost estimates.
- **Never claim regulatory compliance**: Outputs are never permit-ready, construction-ready, or certified.

## Human-approval boundaries
- Critiques and revisions are proposals. Only the homeowner can select a concept or approve the plan gate.
- The agent must **NEVER** approve a concept at the plan gate (`workflow approve <project-id> plan`).

## Failure handling
- **Unknown entity ID error**: If a proposed revision references an invalid room ID, consult `space_program.yaml` and correct the identifier before submitting.
- **Contradictory revision request**: If a revision makes the layout infeasible (e.g. requesting room sizes exceeding the parcel footprint), report the contradiction to the user and suggest viable alternatives.
