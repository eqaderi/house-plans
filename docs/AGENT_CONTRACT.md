# Agent contract

The single set of engineering and operating rules for every coding agent working
on this repository: Claude Code, OpenAI Codex, and Google Gemini CLI. The one
entry file, `AGENTS.md` (`CLAUDE.md` and `GEMINI.md` are symlinks to it), only
loads this file ([ADR 0034](adr/0034-one-entry-file-and-one-skills-folder.md)).
Write every rule here.

## 1. Objectives and sources of truth

HOUSE DESIGN AI exists first to design the owner's own house on their own
land (`projects/my-house/`), and stays reusable for other projects. It turns a
survey and an owner interview into an approved site, an approved program, floor
plans, then Blender and Unreal models, all from one canonical semantic model
with human approval gates in between. Project facts live in project data, never
in application code.

The owner works through the coding agents themselves, which drive the
`house-ai` CLI; the core workflow needs no paid model API key
([ADR 0011](adr/0011-agent-first-interview-interface.md)). The SDK adapter in
`providers/claude.py` ([ADR 0010](adr/0010-claude-adapter-for-the-interview.md))
is optional.

Authorities: [MASTER_SPEC.md](MASTER_SPEC.md) (wins every conflict),
[ARCHITECTURE.md](ARCHITECTURE.md), [DOMAIN_MODEL.md](DOMAIN_MODEL.md),
[adr/](adr/), [milestones/](milestones/) (history). Roadmap, stages:
[PROJECT_TRACKER.md](PROJECT_TRACKER.md). Terms: [GLOSSARY.md](../GLOSSARY.md).

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
- Owner answers are recorded verbatim (`source.kind: owner_answer`). Every
  interpretation you propose (`--set slot=value`) is recorded as an `inference`
  (`method: agent:<tool>`) until the owner confirms it (`interview confirm`).

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
  the owner confirms it.
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
  unconfirmed:** exact UTM zone, hemisphere, horizontal datum/EPSG, vertical
  datum, and the formal legal boundary. Keep `my-house` in
  `SITE_NEEDS_CONFIRMATION` until the owner's `site confirm` clears the
  blockers; the owner then approves the site gate. Plan options on `my-house`
  must account for split-level layouts, hillside construction, road-level parking/access, excavation, retaining walls,
  drainage, and structure without assuming all 600 m² is buildable.
- Before any `my-house` layout work, read
  `projects/my-house/design/OWNER_DESIGN_RULES.md`. Each rule is a hard check:
  never show a design that breaks one.

## 8. Workflow and human approval gates

States: `NEW_PROJECT → SITE_INGESTION ⇄ SITE_NEEDS_CONFIRMATION → [site gate]
SITE_APPROVED → INTERVIEWING ⇄ PROGRAM_REVIEW → [program gate] PROGRAM_APPROVED
→ PLAN_GENERATION ⇄ PLAN_REVIEW → [plan gate] PLAN_APPROVED →
BLENDER_BUILD ⇄ BLENDER_REVIEW → [model gate] MODEL_APPROVED → UNREAL_BUILD ⇄
UNREAL_REVIEW`.

- **Never approve a gate, confirm site facts, grant provider consent, or reject
  a reviewed program on the owner's behalf.** `workflow approve`, `workflow
  reopen`, `site confirm`, `interview consent`, and `program reject` require a
  human in an interactive terminal (exit code 2 in an agent's shell). Never
  bypass this with a fake TTY or `--actor human:...`. Run `workflow
  request-approval` (or `program review` / `plan review`), then give the human
  the exact command the CLI printed on its `next:` line to run in their own
  terminal, where they type the confirmation phrase it shows.

## 9. Owner interview (Milestone C)

Run the owner interview, from `interview start` to `program review`, with the
`architectural-programming` skill. It works while the site is still in
`SITE_NEEDS_CONFIRMATION`; the 30 `interview checklist` questions are a
completeness check, not a script.

## 9b. Plan options (Milestone D, [ADR 0013](adr/0013-solver-backed-plan-generation.md))

Generate, revise, compare and review plan options with the
`generate-plan-options` skill; critique them with `critique-plan` and
`visual-review`. Stored generation runs only after the human approved site and
program; before that only `--exploratory`, which stores nothing and is never
called validated. Report metrics with their status and infeasible strategies
with reasons; never present one plan option as "the answer".
Whenever you show the owner two or more options, include a comparison view: a
table of only what differs, plus the same floor of each option side by side
with differing rooms outlined (`OWNER_DESIGN_RULES.md` rule 8.5; reference
`projects/my-house/design/claude-c09/compare.py`).

## 10. Professional boundary, conventions, tests, and Git

- Never call output permit-ready, construction-ready, structurally certified,
  code-compliant, MEP-engineered or geotechnically verified without a recorded
  professional approval ([PROFESSIONAL_HANDOFF.md](PROFESSIONAL_HANDOFF.md)).
- Use the project venv (`.venv/bin/python`, `.venv/bin/house-ai`). Python
  3.13 only (ADR 0026), `ruff` line length 100, Pydantic `StrictModel`,
  canonical units metres/degrees. External tools and vendor SDKs sit behind
  optional adapters.
- Project skills live in `.agents/skills/<name>/SKILL.md`; `.claude/skills`
  is a symlink to that folder. `tests/test_skills.py` enforces their template.
- Every behaviour change or bug fix has a deterministic offline test asserting
  ground-truth numbers. Record architectural decisions in `docs/adr/NNNN-*.md`.
- Owner commands "Project status", "Next stage", "Review stage <ID>" and
  "Close stage <ID>" follow the tracker protocol (§O): one stage per branch
  `stage/<ID>-<slug>`, stop for independent review, no DONE without evidence.
  Merge into `main` only on "Close stage" after an APPROVED review, or when
  the owner authorises it. Never rewrite pushed history.
- Before saying a task is finished, run and report:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests examples tools
.venv/bin/house-ai schemas check
.venv/bin/python tools/leak_scan.py
.venv/bin/python tools/check_tracker.py
```
