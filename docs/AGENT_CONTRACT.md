# Agent contract

The single set of engineering and operating rules for every coding agent working
on this repository: Claude Code, OpenAI Codex, and Google Gemini CLI.
`AGENTS.md`, `CLAUDE.md` and `GEMINI.md` only load this file
([ADR 0005](adr/0005-shared-coding-agent-instructions.md)). Never copy these
rules into a tool-specific file.

## 1. Objectives, agent-first workflow, and sources of truth

HOUSE DESIGN AI exists first to design the homeowner's own house on their own
land (`projects/my-house/`), and stays reusable for other projects. It turns a
survey and an owner interview into a verified site, an approved program, floor
plans, then Blender and Unreal models, all from one canonical semantic model
with human approval gates in between. Project facts live in project data, never
in application code.

**Agent-first architecture (no API key required, [ADR 0011](adr/0011-agent-first-interview-interface.md)):**
The homeowner works directly with **Claude Code**, **Gemini CLI**, and **OpenAI
Codex** as the primary AI interfaces:
`Homeowner → Claude Code / Gemini CLI / Codex → house-ai CLI & ProjectStore → Structured Requirements & Validation → Floor Plans → Blender / IFC → Unreal Engine`.
No separately billed Anthropic, OpenAI, or Gemini API key is required for the
core workflow. The SDK adapter in `providers/claude.py` ([ADR 0010](adr/0010-claude-adapter-for-the-interview.md))
is strictly optional.

Authorities: [MASTER_SPEC.md](MASTER_SPEC.md) (wins every conflict),
[ARCHITECTURE.md](ARCHITECTURE.md), [DOMAIN_MODEL.md](DOMAIN_MODEL.md),
[adr/](adr/), [milestones/](milestones/).

## 2. Repository architecture

`src/house_ai/` is layered: `domain` (canonical Pydantic schemas, units,
geometry, integrity checks) ← `storage` ← `orchestration` (workflow, site,
interview) ← `cli`. Pipeline packages (`cad`, `geospatial`, `interview`,
`program`, `render2d`, later `constraints`, `generation`, `evaluation`,
`blender`, `unreal`) depend on `domain` only. No AI vendor SDK, CAD backend or
game engine may become a dependency of `domain`; each sits behind an adapter.

## 3. One model, many views

- The canonical semantic house model (`house_ai.domain`) is the only source of
  truth. Plans, SVGs, IFC, Blender and Unreal output are derived from it.
- Never treat an image, render or prose as the design. A design change is a new
  version in `ProjectStore`.
- Never invent room coordinates and trust them. Geometry comes from a solver or
  a human and is always checked with `house_ai.domain.integrity.check_model`.
- Extend the domain model rather than forking it; run `house-ai schemas export`
  and update `DOMAIN_MODEL.md`.

## 4. Writing project state

- A project is `projects/<name>/` ([ADR 0009](adr/0009-personal-first-project-folders.md)).
  Its record (`project.json`, `events.jsonl`, `source/`, `artifacts/`) changes
  only through the library or `house-ai` CLI: artifacts are write-once, the log
  is hash-chained (`project verify`). `surveys/ site/ reviews/ design/` hold
  inputs and generated exports.
- Identify yourself on state-changing commands: `--actor agent:<tool>`
  (`agent:claude-code`, `agent:gemini`, `agent:codex`).
- Homeowner answers are recorded verbatim (`source.kind: owner_answer`). Every
  slot value you propose (`--set slot=value`) is recorded as an `inference`
  (`method: agent:<tool>`) until the homeowner confirms it (`interview confirm`).

## 5. Private data and providers

- The owner committed `projects/my-house/` (`seperated.dwg` and `elevation.dwg`;
  `final.dwg` is excluded) to this **private** repository
  ([ADR 0009](adr/0009-personal-first-project-folders.md)). Before pushing,
  verify `gh repo view --json visibility` is `PRIVATE`; else stop and ask.
  Never copy real project data into `examples/`, `tests/` or public docs, and
  never modify survey originals. `project-data/` stays git-ignored. Never
  commit API keys or `.env` files.
- Every external provider call goes through `providers.base.send`, which
  enforces `DataFlowPolicy`. Tests and examples use synthetic data only.

## 6. Unknowns, assumptions and evidence

- Unknown architectural or site facts are recorded as `null` / `unknown`. Never
  invent a value to unblock the pipeline.
- Label claims with their epistemic status: `verified_fact`, `inference`,
  `assumption`, `preference`, `simulation_result`, `professional_approval`,
  `unknown`. An agent inference is never recorded as a fact or preference until
  the homeowner confirms it.
- Evaluator output states how each metric was obtained (`measured`, `inferred`,
  `simulated`, `ai_judgment`, `not_checked`). Assumptions go in
  `assumptions.yaml`, unanswered questions in `open_questions.yaml`.

## 7. CAD, units, coordinate systems, and `projects/my-house/`

- DWG and DXF are file formats; UTM is a coordinate system. Never infer a CRS,
  UTM zone, hemisphere, datum or unit from coordinate magnitudes. Only a source
  file can *declare* them and only a human can *confirm* them (`site confirm`).
- Raw CAD extraction stays in SOURCE coordinates and units; conversion to GRID
  metres and LOCAL frame is reversible (`domain/coordinates.py`).
- **`projects/my-house/` facts:** The owner reported UTM coordinates, elevations
  in metres above sea level, and a real ~12–12.5 m drop on genuinely steep land.
  CAD extraction measures ~600 m² parcel area, ~21 m frontage on a ~9 m road,
  and 27 elevation points (`seperated.dwg` + `elevation.dwg`). **Still
  unverified:** exact UTM zone, hemisphere, horizontal datum/EPSG, vertical
  datum, and formal legal boundary verification. Keep `my-house` in
  `SITE_NEEDS_VERIFICATION` until the owner runs `site confirm` and approves the
  site gate. Future designs on `my-house` must account for split-level layouts,
  hillside construction, road-level parking/access, excavation, retaining walls,
  drainage, and structure without assuming all 600 m² is buildable.

## 8. Workflow and human approval gates

States: `NEW_PROJECT → SITE_INGESTION ⇄ SITE_NEEDS_VERIFICATION → [site gate]
SITE_APPROVED → INTERVIEWING ⇄ PROGRAM_REVIEW → [program gate] PROGRAM_APPROVED
→ CONCEPT_GENERATION ⇄ CONCEPT_REVIEW → [plan gate] PLAN_APPROVED →
BLENDER_BUILD ⇄ BLENDER_REVIEW → [model gate] MODEL_APPROVED → UNREAL_BUILD ⇄
UNREAL_REVIEW`.

- **Never approve a gate, confirm site facts, grant provider consent, or reject
  a reviewed program on the homeowner's behalf.** `workflow approve`, `workflow
  reopen`, `site confirm`, `interview consent`, and `program reject` require a
  human in an interactive terminal (exit code 2 otherwise). Never bypass this
  with a fake TTY or `--actor human:...`. Run `workflow request-approval` (or
  `program review`) and ask the human to run the approval command in their own
  terminal.

## 9. Agent-operated homeowner interview (Milestone C)

1. **Select and inspect the project & site:**
   `house-ai project list`, `house-ai project status my-house --json`, and
   `house-ai interview status my-house --json` (shows site measurements,
   verification blockers, owner statements, checklist coverage, unconfirmed
   inferences, and open contradictions).
2. **Start or resume the interview:**
   `house-ai interview start my-house --json --actor agent:<tool>`. Works while
   the site is in `SITE_NEEDS_VERIFICATION` (site values are marked unconfirmed).
3. **Conduct an adaptive conversation (English, Persian, or mixed):**
   Use the 30 questions in `interview checklist` as a completeness checklist,
   not a rigid script. Ask natural architectural follow-ups tailored to the
   owner's answers and the steep site.
4. **Record exact homeowner words + proposed interpretations (`inference`):**
   Always pass the homeowner's **exact verbatim words** (Persian, English, or
   mixed) as `text`, and pass structured slot interpretations via `--set`:
   - Checklist question/slot or multi-slot free-form answer:
     `house-ai interview answer my-house "<verbatim words>" [--question <qid|slot>] --set slot=value --actor agent:<tool>`
   - Adaptive follow-up question outside the 30-question checklist:
     `house-ai interview answer my-house "<verbatim words>" --question q-followup-road --question-text "<your question>" --topic site --set entry_at_road=true --actor agent:<tool>`
   - Mark undecided slots with `--unknown <slot>`.
5. **Confirm, correct, or revise interpretations:**
   Show interpreted values (`inference`) to the homeowner and ask them to
   confirm or correct. Once they confirm in chat:
   `house-ai interview confirm my-house [slots...] --text "<owner's words>" --actor agent:<tool>`.
   To reject an interpretation or revise an earlier answer (preserving history):
   `house-ai interview reject my-house --slot <slot> --text "<owner's words>" --actor agent:<tool>`
   or `house-ai interview revise my-house <qid|slot> "<new words>" --set slot=new_value --actor agent:<tool>`.
6. **Resolve contradictions:**
   Explain the trade-off and options from `interview status --json`, then record
   the owner's choice:
   `house-ai interview resolve my-house <contradiction-id> "<owner's words>" --option <1..N> [--defer] --actor agent:<tool>`.
7. **Build, validate, and request human approval of the space program:**
   `house-ai program build my-house --out projects/my-house/design --actor agent:<tool>`
   writes `design_brief.yaml`, `space_program.yaml`, `assumptions.yaml`,
   `open_questions.yaml`, `interview-summary.md`, and `program-review.md` and
   runs deterministic validation. Once the site gate is approved and no blocking
   findings or unconfirmed inferences remain, run `house-ai program review my-house --actor agent:<tool>`
   and ask the human to run `house-ai workflow approve my-house program --id program --approver <name>`
   in their terminal.

### Practical example (`projects/my-house`)

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

## 10. Professional boundary, conventions, tests, and Git

- Never call output permit-ready, construction-ready, structurally certified,
  code-compliant, MEP-engineered or geotechnically verified without a recorded
  professional approval ([PROFESSIONAL_HANDOFF.md](PROFESSIONAL_HANDOFF.md)).
- Python ≥ 3.11 (3.11 and 3.13), `ruff` line length 100, Pydantic `StrictModel`,
  canonical units metres/degrees. External tools and vendor SDKs sit behind
  optional adapters.
- Every behaviour change or bug fix has a deterministic offline test asserting
  ground-truth numbers. Record architectural decisions in `docs/adr/NNNN-*.md`.
- One branch per milestone (`milestone-a`, `milestone-b`, ...). Never rewrite
  pushed history. Merge into `main` and push only when the owner authorises it.
- Before saying a task is finished, run and report:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests examples
.venv/bin/house-ai schemas check
```
