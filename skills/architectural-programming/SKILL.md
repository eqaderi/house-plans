---
name: architectural-programming
description: Conduct an adaptive owner interview (English, Persian, or mixed), record verbatim answers and interpretations, resolve contradictions, build the space program, and request program gate review.
---

# Architectural Programming

Follow [docs/AGENT_CONTRACT.md](../../docs/AGENT_CONTRACT.md) (§4 provenance,
§6 epistemic status, §9 interview). In every command, `agent:<tool>` is your
own tool name: `claude-code`, `codex` or `gemini`.

## Purpose
Guide the agent through an adaptive, high-information architectural interview with the owner, recording verbatim answers in English, Persian, or mixed language, recording interpretations as unconfirmed inferences, resolving trade-offs and contradictions, building the validated space program, and requesting the human program gate.

## When to invoke
- When starting or resuming the owner interview for a project.
- When capturing household, lifestyle, space, relationship and hillside wishes.
- When resolving contradictions between wishes, budget and the site.
- When compiling `design_brief.yaml` and `space_program.yaml`.
- When requesting review at the program approval gate.

## Inputs
- Project folder or name under `projects/` (`<project>`).
- Site context from `interview status --json` (relief, slope, frontage; marked unconfirmed until the site gate is approved).
- The owner's answers in their own words (Persian, English, or mixed).

## Outputs
- Interview events in the project store (`owner_answer` text and `inference` interpretations).
- `design_brief.yaml`, `space_program.yaml`, `assumptions.yaml`, `open_questions.yaml`.
- `interview-summary.md` and `program-review.md`.

## Exact commands

1. **Inspect, then start or resume:**
   ```bash
   .venv/bin/house-ai project status <project> --json
   .venv/bin/house-ai interview status <project> --json      # coverage, site context, contradictions
   .venv/bin/house-ai interview checklist <project> --json   # the 30 checklist questions and their slots
   .venv/bin/house-ai interview start <project> --json --actor agent:<tool>
   ```
   `interview start` works while the site is still in `SITE_NEEDS_CONFIRMATION`.

2. **Ask in rounds.** Each round asks 2–4 open, high-information questions,
   chosen from the slots `interview status` reports as missing, in the
   owner's language. Prefer one question that fills several slots (for
   example household, bedrooms and step-free needs together) over a slot-by-slot
   script. Wait for the answer before the next round.

   **Hillside questions** (ask early on a steep site; record with `--topic site`):
   - Should the entrance and parking sit at road level, with the house stepping down the slope? (`entry_at_road`)
   - Split levels following the ground, a walk-out lower storey, or a compact stacked house? How many storeys? (`slope_strategy`, `storeys`)
   - Does anyone need to avoid stairs now or later; would a lift be acceptable? (`elder_step_free`, `accessibility`, `lift`)
   - Which rooms should open to the downhill view or garden, and which may be partly below ground? (`outdoor`, `light_wishes`)
   - Is earthwork and retaining walls cost a concern compared with keeping the garden level? (`budget`, `priorities`)

3. **Record each answer verbatim, with your interpretations as `--set`:**
   ```bash
   # Checklist question (or a multi-slot answer):
   .venv/bin/house-ai interview answer <project> "<verbatim owner words>" \
     --question <qid|slot> --set <slot1>=<val1> --set <slot2>=<val2> --actor agent:<tool>

   # Adaptive follow-up outside the checklist:
   .venv/bin/house-ai interview answer <project> "<verbatim owner words>" \
     --question q-followup-<slug> --question-text "<your question>" --topic site \
     --set <slot>=<val> --actor agent:<tool>

   # The owner has not decided yet:
   .venv/bin/house-ai interview answer <project> "<verbatim owner words>" \
     --question <qid> --unknown <slot> --actor agent:<tool>
   ```

4. **Confirm interpretations with the owner.** Show each interpretation; once the owner confirms in chat:
   ```bash
   .venv/bin/house-ai interview confirm <project> [slot1 slot2 ...] \
     --text "<owner's confirmation words>" --actor agent:<tool>
   ```

5. **Reject or revise:**
   ```bash
   .venv/bin/house-ai interview reject <project> --slot <slot> \
     --text "<owner's words>" --actor agent:<tool>
   .venv/bin/house-ai interview revise <project> <qid|slot> "<owner's new words>" \
     --set <slot>=<new-val> --actor agent:<tool>
   ```

6. **Resolve contradictions.** Explain the trade-off and the options listed by `interview status --json`, then record the owner's choice, or defer it:
   ```bash
   .venv/bin/house-ai interview resolve <project> <contradiction-id> "<owner's words>" \
     --option <1..N> --actor agent:<tool>
   .venv/bin/house-ai interview resolve <project> <contradiction-id> "<owner's words>" \
     --defer --actor agent:<tool>
   ```

7. **Build and validate the space program:**
   ```bash
   .venv/bin/house-ai program build <project> --out projects/<project>/design --actor agent:<tool>
   ```

8. **Request the program gate review** (needs the site gate approved, no blocking findings and no unconfirmed inferences):
   ```bash
   .venv/bin/house-ai program review <project> --actor agent:<tool>
   ```
   From `SITE_APPROVED` (or `INTERVIEWING`) it moves the project to
   `PROGRAM_REVIEW` itself; no `workflow transition` is needed.

## Required validations
- The owner's words are stored verbatim: never translated away, tidied or truncated.
- Every `--set` value stays an `inference` until the owner confirms it with `interview confirm`.
- `program build` reports no blocking findings before `program review`.
- Program size is plausible for the site; on a steep site never assume the whole parcel is buildable.

## Human-approval boundaries
- **NEVER** run `house-ai workflow approve <project> program`: the program gate is human-only.
- **NEVER** run `house-ai program reject` or `house-ai interview consent`: both are human-only terminal commands.
- Never confirm an inference the owner has not confirmed in their own words.
- Present `program-review.md` and ask the human to run, in their own terminal:
  ```bash
  .venv/bin/house-ai workflow approve <project> program --id program --version <v> --approver <name>
  ```

## Failure handling
- **Unconfirmed inferences block review**: show them to the owner and confirm, reject or revise each.
- **Blocking program findings**: ask the owner the questions that resolve them, record the answers, rebuild.
- **Open contradictions**: resolve or defer each with `interview resolve`.
- **`program review` refused because the site gate is not approved**: stop; the owner must finish the site gate first.
