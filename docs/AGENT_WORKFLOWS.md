# Agent workflows: worked command examples

Companion to [AGENT_CONTRACT.md](AGENT_CONTRACT.md), which holds the rules.
Use the project venv (`.venv/bin/house-ai`) and identify yourself with
`--actor agent:<tool>`.

## Owner interview (Milestone C, `projects/my-house`)

```bash
.venv/bin/house-ai project status my-house --json
.venv/bin/house-ai interview start my-house --json --actor agent:claude-code

# Owner: "I want a modern house on my steep land, with parking from the road and a large living room."
.venv/bin/house-ai interview answer my-house \
  "I want a modern house on my steep land, with parking from the road and a large living room." \
  --set "style=modern hillside" --set slope_strategy=step_down --set entry_at_road=true \
  --set cars=2 --set parking_type=garage --set room_sizes=living=35 \
  --json --actor agent:claude-code

# Adaptive hillside follow-up with Persian/English answer:
.venv/bin/house-ai interview answer my-house \
  "ورودی اصلی و پارکینگ هم‌سطح جاده باشد و نشیمن یک طبقه پایین‌تر رو به منظره." \
  --question q-follow-section \
  --question-text "Should the main living level sit one level below the road-level garage?" \
  --topic site --set floors=2 --json --actor agent:claude-code

# After the owner confirms in chat:
.venv/bin/house-ai interview confirm my-house --text "بله، تایید است." --json --actor agent:claude-code
.venv/bin/house-ai program build my-house --out projects/my-house/design --actor agent:claude-code
```

## Plan concepts (Milestone D)

On the synthetic steep hillside (no private data). Loading the example does
not approve anything; a preview needs no approval because it stores nothing:

```bash
.venv/bin/house-ai example load /tmp/hill --name synthetic-hillside \
  --project-id synthetic-hillside --actor human:example
.venv/bin/house-ai plan strategies
.venv/bin/house-ai plan generate /tmp/hill --exploratory --out /tmp/hill-preview \
  --actor agent:claude-code
```

After the human has approved the site and program gates in their own
terminal, the gated run stores everything and moves to CONCEPT_REVIEW:

```bash
.venv/bin/house-ai plan generate <project> --actor agent:claude-code
.venv/bin/house-ai plan list <project>
.venv/bin/house-ai plan compare <project>

# Owner: "The kitchen is too small; keep our bedroom away from the kids."
.venv/bin/house-ai plan revise <project> concept-split-level \
  "The kitchen is too small; keep our bedroom away from the kids." \
  --area pi-kitchen=16 --separate pi-bed-main,pi-bed-child-1 --actor agent:claude-code

# Owner: "Keep the rest, but completely rethink the bedroom wing."
.venv/bin/house-ai plan revise <project> concept-two-wing \
  "Keep the rest, but completely rethink the bedroom wing." \
  --rethink z-night --seed 7 --actor agent:claude-code

# Owner: "I hate this option; start again from the approved program."
.venv/bin/house-ai plan revise <project> concept-compact \
  "I hate this option; start again from the approved program." \
  --kind restart_from_program --actor agent:claude-code

.venv/bin/house-ai plan review <project> concept-split-level --actor agent:claude-code
# The owner, in their own terminal:
#   .venv/bin/house-ai workflow approve <project> plan --id concept-split-level --version 2 --approver <name>
```

"Generate three alternatives" maps to `plan generate` (all strategies, or a
new `--seed`). "Combine the entrance of B with the courtyard of A" is not
supported yet: ask the owner which parts matter and express them as `--area`,
`--level`, `--adjacent`, `--separate`, `--near` and `--strategy` operations.

## `projects/my-house` today

The site is in `SITE_NEEDS_VERIFICATION` and no interview has been recorded,
so there is no space program: `plan generate my-house` (gated or
`--exploratory`) refuses and writes nothing. The order is: the owner confirms
the site facts (`site confirm`) and approves the site gate; the agent runs the
interview and `program build`/`program review`; the owner approves the
program gate; then `plan generate my-house`.
