---
name: architectural-programming
description: Conduct an adaptive homeowner interview (English, Persian, or mixed), record verbatim answers and slot inferences, resolve contradictions, build the space program, and request program gate review.
---

# Architectural Programming

## Purpose
Guide the agent through conducting an adaptive, high-information architectural interview with the homeowner, recording verbatim statements in English, Persian, or mixed language, interpreting structured slots as provisional inferences, resolving trade-offs and contradictions, building the validated space program, and preparing for the human program gate.

## When to invoke
- When starting or resuming the homeowner interview for a project.
- When capturing homeowner lifestyle preferences, room counts, sizes, relationships, and hillside strategies.
- When resolving contradictions between space desires, budget, site slope, or zoning constraints.
- When compiling the architectural brief (`design_brief.yaml`) and space program (`space_program.yaml`).
- When requesting review at the program approval gate.

## Inputs
- Project identifier (`<project-id>`).
- Current site context (parcel relief, slope, road frontage, access orientation).
- Homeowner answers in natural language (Persian, English, or mixed).

## Outputs
- Recorded interview turns in project store (`events.jsonl` with `owner_answer` and `inference`).
- `design_brief.yaml` containing household profile, spatial priorities, and architectural brief.
- `space_program.yaml` detailing rooms, target areas, levels, daylight requirements, and adjacencies.
- `assumptions.yaml` and `open_questions.yaml`.
- `interview-summary.md` and `program-review.md`.

## Exact commands

1. **Start or resume interview session:**
   ```bash
   # Transition project to INTERVIEWING if in SITE_APPROVED:
   .venv/bin/house-ai workflow transition <project-id> INTERVIEWING --reason "starting interview" --actor agent:gemini

   # Start or resume interview:
   .venv/bin/house-ai interview start <project-id> --json --actor agent:gemini
   ```


2. **Check interview status, coverage checklist, and open contradictions:**
   ```bash
   .venv/bin/house-ai interview status <project-id> --json
   ```

3. **Record homeowner answer with verbatim words and structured inferences:**
   ```bash
   # Checklist question or multi-slot response:
   .venv/bin/house-ai interview answer <project-id> "<verbatim owner words>" \
     --question <qid> --set <slot1>=<val1> --set <slot2>=<val2> \
     --actor agent:gemini

   # Adaptive hillside or site-specific follow-up:
   .venv/bin/house-ai interview answer <project-id> "<verbatim owner words>" \
     --question q-followup-<slug> --question-text "<question text>" \
     --topic site --set <slot>=<val> \
     --actor agent:gemini
   ```

4. **Confirm interpretations with the owner:**
   Show inferred slot values in conversation. When the owner confirms:
   ```bash
   .venv/bin/house-ai interview confirm <project-id> [slot1 slot2...] \
     --text "<verbatim confirmation words>" --actor agent:gemini
   ```

5. **Reject or revise an interpretation:**
   ```bash
   # Reject an interpretation:
   .venv/bin/house-ai interview reject <project-id> --slot <slot> \
     --text "<verbatim rejection words>" --actor agent:gemini

   # Revise an earlier answer while keeping history:
   .venv/bin/house-ai interview revise <project-id> <qid|slot> "<new words>" \
     --set <slot>=<new-val> --actor agent:gemini
   ```

6. **Resolve contradictions:**
   Explain trade-offs clearly, present options, and record the owner's choice:
   ```bash
   .venv/bin/house-ai interview resolve <project-id> <contradiction-id> "<owner words>" \
     --option <1..N> --actor agent:gemini
   ```

7. **Build and validate the space program:**
   ```bash
   .venv/bin/house-ai program build <project-id> --out projects/<project-id>/design \
     --actor agent:gemini
   ```

8. **Request program approval gate review:**
   ```bash
   .venv/bin/house-ai program review <project-id> --actor agent:gemini
   ```

## Required validations
- Always store the owner's **verbatim words** without sanitizing, translating away, or truncating Persian or English phrases.
- Proposed slot values remain strictly `inference` until confirmed by the owner via `interview confirm`.
- Validate spatial program sizing against site buildable area and steep-slope footprint limits.
- Check required room adjacencies (e.g. kitchen to dining, garage to pantry/mudroom, primary bedroom acoustics).
- Run deterministic validation during `program build`; ensure zero blocking errors before requesting review.

## Human-approval boundaries
- **NEVER** run `house-ai workflow approve <project-id> program`: the program approval gate is strictly human-only.
- **NEVER** run `house-ai program reject`: program rejection at review is strictly human-only.
- The agent must present `program-review.md` to the homeowner and ask them to run in their own terminal:
  ```bash
  .venv/bin/house-ai workflow approve <project-id> program --id program --version <v> --approver <name>
  ```

## Failure handling
- **Unconfirmed inferences blocking review**: If unconfirmed inferences remain, prompt the homeowner to review and confirm or correct them.
- **Program validation errors**: If `program build` reports validation failures (such as missing mandatory zones or contradictory adjacencies), ask clarifying questions to resolve the defects before building again.
- **Unresolved contradictions**: Address each contradiction in `interview status` using `interview resolve`.
