---
name: critique-plan
description: Perform grounded architectural critique of floor-plan concepts across geometry, circulation, privacy, and hillside metrics, separating measured facts from AI judgment and proposing structured revision operations.
---

# Critique Plan

Follow [docs/AGENT_CONTRACT.md](../../docs/AGENT_CONTRACT.md) (§3 one model,
§6 epistemic status, §10 professional boundary). In every command,
`agent:<tool>` is your own tool name: `claude-code`, `codex` or `gemini`.

For `projects/my-house/`, read and obey
[projects/my-house/design/OWNER_DESIGN_RULES.md](../../projects/my-house/design/OWNER_DESIGN_RULES.md)
first; check every design against it before showing anything to the owner.

## Purpose
Guide the agent through an evidence-grounded architectural critique of generated floor plans: functional quality, zoning, circulation, daylight, privacy, and hillside relationships. Every claim carries its epistemic status, every cited element is a canonical ID that exists in the plan, and every proposed change is an explicit `plan revise` operation.

## When to invoke
- When reviewing a new concept or comparing alternatives.
- When evaluating circulation, acoustic privacy, room proportions, or the relation of levels to the ground.
- When turning flaws or owner feedback into `plan revise` operations.

## Inputs
- A concept folder with `plan.json`, `plan.svg`, `metrics.json`, `violations.json`, `explanation.md`:
  - before the gates: from `plan generate <project> --exploratory --out <dir>` (`<dir>/<concept-id>/exploratory/`);
  - after the gates: from `plan export <project> <concept-id> --out <dir>`.
- The space program (`projects/<project>/design/space_program.yaml`) and design brief.

## Outputs
- A critique (Markdown) grouped by dimension, every observation labelled `measured`, `inferred`, `ai_judgment` or `not_checked`, every element cited by ID in backticks.
- A passing `plan ground` check for that critique.
- Proposed `plan revise` commands (run only after the owner agrees, and only on stored concepts).

## Exact commands

1. **Get the concept files:**
   ```bash
   # Before the site and program gates (stores nothing):
   .venv/bin/house-ai plan generate <project> --exploratory --out <scratch-dir>/preview --actor agent:<tool>
   # After them:
   .venv/bin/house-ai plan export <project> <concept-id> --out <scratch-dir>/critique
   ```
   Read `metrics.json`, `violations.json`, `explanation.md` and `plan.svg`; `comparison.md` sits next to the exploratory concepts, or run `plan compare <project>` for stored ones.

2. **Look up the canonical IDs.** In `plan.json` under `model`: spaces `sp-*`
   (each with its `program_item_id` `pi-*`, `zone_id` `z-*`, `level_id` `lv-*`),
   levels `lv-*` (e.g. `lv-entry`, `lv-down-300`), zones `z-*`, relationships `rel-*`,
   walls `w-*`, doors `d-*`, windows `win-*`, stairs `st-*`. Program items and
   adjacencies (`pi-*`, `adj-*`) are in `space_program.yaml`. Never write
   an ID you did not read in these files.

3. **Write the critique to a file, citing every element in backticks, then ground it:**
   ```bash
   .venv/bin/house-ai plan ground <concept-folder>/plan.json <critique.md> \
     --program projects/<project>/design/space_program.yaml
   ```
   Exit 0 means every cited ID exists; exit 1 lists each unknown ID. Fix the critique until it passes.

4. **Propose grounded revisions** (`--area`, `--separate`, `--adjacent`, `--near` and `--level` take program item IDs `pi-*` or space IDs `sp-*`; `--rethink` also takes a zone `z-*` or `all`):
   ```bash
   .venv/bin/house-ai plan revise <project> <concept-id> "<owner's words>" \
     --area pi-kitchen=18 --actor agent:<tool>
   .venv/bin/house-ai plan revise <project> <concept-id> "<owner's words>" \
     --separate pi-bed-main,pi-bed-child-1 --adjacent pi-kitchen,pi-dining --actor agent:<tool>
   .venv/bin/house-ai plan revise <project> <concept-id> "<owner's words>" \
     --level pi-study-1=entry --rethink z-night --actor agent:<tool>
   ```
   `plan revise` works only on stored concepts. For an exploratory concept, put the operations in the critique as proposals.

## Required validations
- **Grounding**: `plan ground` passes for the critique. Citing an ID that is not in the plan or program is forbidden.
- **Epistemic status**:
  - `measured`: areas, dimensions, room counts, corridor lengths read from `metrics.json` or `plan.json`.
  - `inferred`: cut/fill volumes, retaining wall heights, underfloor voids (schematic).
  - `ai_judgment`: spatial quality, flow, furniture usability.
  - `not_checked`: structure, MEP, daylight, wind, cost, code compliance.
- Never call a plan permit-ready, construction-ready, code-compliant or structurally certified.

## Human-approval boundaries
- Critiques and revisions are proposals. Only the homeowner chooses a concept, and only the homeowner's words go into `plan revise`.
- **NEVER** run `house-ai workflow approve <project> plan`.

## Failure handling
- **`plan ground` reports an unknown ID**: look the element up in `plan.json` or `space_program.yaml` and correct the critique; never drop the check.
- **`plan revise` reports an unknown room**: use a `pi-*` ID from the program or an `sp-*` ID from `plan.json`, as the error says.
- **A revision becomes infeasible**: report the solver's reason and suggest a feasible alternative.
