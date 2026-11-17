---
name: visual-review
description: Perform grounded visual inspection and critique of floor-plan options, detecting visual and spatial findings against canonical element IDs, proposing structured revisions, and verifying fixes.
---

# Visual Plan Review

Follow [docs/AGENT_CONTRACT.md](../../docs/AGENT_CONTRACT.md) (§3 one model,
§6 epistemic status, §10 professional boundary). In every command,
`agent:<tool>` is your own tool name: `claude-code`, `codex` or `gemini`.

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

4. **Verify fixes and request gate review:**
   Re-export the revised plan option, inspect the new plan version, and confirm the finding is resolved before requesting the owner's gate review:
   ```bash
   .venv/bin/house-ai plan export <project> <option-id> --out <scratch-dir>/fixed
   .venv/bin/house-ai plan review <project> <option-id> --actor agent:<tool>
   ```

## Required validations
- **Strict canonical grounding**: every visual claim must cite valid canonical element IDs (`sp-*`, `w-*`, `d-*`, `win-*`, `st-*`, `site-*`) existing in the target plan. Ungrounded or hallucinatory element references are strictly rejected.
- **Epistemic status discipline**:
  - Visual critique observations carry epistemic status `ai_judgment`.
  - Geometric dimensions and areas carry `measured` status and must cite model values.
  - Earthwork cut/fill and retaining estimates carry `inferred` status.
- **Fix verification**: any claimed fix must be checked against the revised plan geometry. Fake fixes that do not change geometry or do not resolve the finding must remain open.
- Never state that a plan is code-compliant, structurally sound, or construction-ready.

## Human-approval boundaries
- Visual reviews and critique reports are proposals for the owner.
- Agents must **NEVER** execute `house-ai workflow approve <project> plan`.
- Gate approval is strictly reserved for the human owner in their own terminal.

## Failure handling
- **Ungrounded element ID**: if `plan ground` or the grounding validator reports an unknown ID, verify the identifier against `plan.json` under `model.spaces`, `model.walls`, or `model.openings` and correct the critique.
- **Fix not resolved**: if the revised plan version still shows the finding or introduces a new violation, do not close the critique item; propose a different revision operation.
- **Infeasible revision**: when the constraint solver cannot satisfy the revision constraints, inspect the solver diagnosis and report other space allocations.
