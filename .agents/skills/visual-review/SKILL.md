---
name: visual-review
description: Perform grounded visual inspection and critique of floor-plan options, detecting visual and spatial findings against canonical element IDs, proposing structured revisions, and verifying fixes.
---

# Visual Plan Review

## Purpose
Guide the agent through visual inspection and grounded visual critique of plan options rendered in the 2D plan viewer. Agents inspect semantic SVG elements, identify layout findings (such as door-swing collisions, window-wall misalignments, label collisions, and stair landing issues), cite elements strictly by their canonical IDs, propose structured revisions, and verify that fixes actually resolve them.

## When to invoke
- When visually inspecting rendered plan SVGs or interactive reviewer bundles.
- When checking for visual and physical spatial collisions that pure metric checks may not fully capture.
- When evaluating door clearances, label readability, or window placements against retaining walls.
- When verifying that a requested revision successfully resolved a previously reported visual finding.

## Inputs
- Exported plan option directory containing `plan.json`, `plan.svg`, and `metrics.json`:
  - From `plan export <project> <option-id> --out <dir>`; or
  - From `plan generate <project> --exploratory --out <dir>`.
- Or a reviewer bundle generated via `plan export-bundle <project> --out <bundle-dir>`.
- The space program (`projects/<project>/design/space_program.yaml`).

## Outputs
- A grounded visual critique record (`visual_critique.json` or Markdown report) with findings labelled `ai_judgment` and citing canonical IDs in backticks.
- Structured revision operations (`revision_ops.json` or CLI flags).
- Re-rendered verification confirming that each finding has been resolved.

## Exact commands

1. **Export the plan option or bundle for visual review:**
   ```bash
   # Export plan option files for inspection:
   .venv/bin/house-ai plan export <project> <option-id> --out <scratch-dir>/review
   # Or export an interactive bundle for browser capture:
   .venv/bin/house-ai plan export-bundle <project> --out <scratch-dir>/bundle
   ```

2. **Ground every cited element ID against the canonical plan:**
   Every cited element must be read directly from `plan.json` (`sp-*`, `w-*`, `d-*`, `win-*`, `st-*`, `site-*`):
   ```bash
   .venv/bin/house-ai plan ground <scratch-dir>/review/plan.json <critique.md> \
     --program projects/<project>/design/space_program.yaml
   ```

3. **Apply structured revisions from feedback:**
   Apply revision operations directly using CLI flags or replaying from an exported operations file:
   ```bash
   .venv/bin/house-ai plan revise <project> <option-id> "<owner's words>" \
     --area pi-kitchen=18 --actor agent:<tool>
   .venv/bin/house-ai plan revise-from-file <project> <scratch-dir>/revision_ops.json \
     --option <option-id> --actor agent:<tool>
   ```

4. **Verify fixes from the revise report, then request gate review:**
   Run the revision with `--json` and read its `findings` object. For the ids the request targeted (`findings.targets`), it lists the Findings of the parent plan version's Evaluation that `disappeared`, those that are `remaining`, and the `new` ones; a Finding about elements whose geometry did not change is never listed as disappeared. The same lists are in `revision.md` under "Findings about ...". Then re-export and inspect the new plan version before requesting the owner's gate review:
   ```bash
   .venv/bin/house-ai plan revise <project> <option-id> "<owner's words>" \
     --rethink sp-study-1 --json --actor agent:<tool>
   .venv/bin/house-ai plan export <project> <option-id> --out <scratch-dir>/fixed
   .venv/bin/house-ai plan review <project> <option-id> --actor agent:<tool>
   ```
   Label collisions are reported in the Evaluation as `label_collision`, measured on the drawing's own layout.

## Required validations
- **Strict canonical grounding**: every visual claim must cite valid canonical element IDs (`sp-*`, `w-*`, `d-*`, `win-*`, `st-*`, `site-*`) existing in the target plan. Ungrounded or hallucinatory element references are strictly rejected.
- **Epistemic status discipline**:
  - Visual critique observations carry epistemic status `ai_judgment`.
  - Geometric dimensions and areas carry `measured` status and must cite model values.
  - Earthwork cut/fill and retaining estimates carry `inferred` status.
- **Fix verification**: a claimed fix counts only when the revise report lists the Finding under `findings.disappeared`. A Finding under `remaining` or `new` keeps the critique item open, and so does a claim no Finding backs when its cited elements did not change.
- Never state that a plan is code-compliant, structurally sound, or construction-ready.

## Human-approval boundaries
- Visual reviews and critique reports are proposals for the owner.
- Agents must **NEVER** execute `house-ai workflow approve <project> plan`.
- Gate approval is strictly reserved for the human owner in their own terminal.

## Failure handling
- **Ungrounded element ID**: if `plan ground` or the grounding validator reports an unknown ID, verify the identifier against `plan.json` under `model.spaces`, `model.walls`, or `model.openings` and correct the critique.
- **Fix not resolved**: if the revise report lists the finding under `remaining` or a Finding under `new`, do not close the critique item; propose a different revision operation.
- **Infeasible revision**: when the constraint solver cannot satisfy the revision constraints, inspect the solver diagnosis and report other space allocations.
