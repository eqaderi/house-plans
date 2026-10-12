# House plans: agent instructions

This repo produces house plans that must be dimensionally exact and checkable.
It is used from Claude Code on one laptop and Codex on another, so everything
here works for both. Before any design work, load the `house-plan` skill
(`.agents/skills/house-plan/SKILL.md`; in Claude Code it is also at
`.claude/skills/house-plan`).

## Every session

1. `git pull`, then `bin/doctor --quiet`. If it reports anything missing,
   tell the owner what and how to fix it before relying on that tool
   (Claude Code runs the doctor for you at session start).
2. Read `docs/STATUS.md`, `docs/brief.md`, `docs/open-questions.md` and the
   newest `docs/feedback/rev-*.md`.
3. Work. End by updating `docs/STATUS.md`, then commit and push, so the next
   session, on either laptop and in either tool, starts from here.

The repo is the memory; the procedure is in `docs/workflow.md`.

## The one rule

**You never draw and you never do arithmetic.** You edit the design spec
(`design/<name>.yaml`, integer millimetres). Deterministic code derives the
geometry, areas, drawings and IFC from it, and measures them back out of the
written files. If you want a number (an area, a rise, a clearance), run the
tools and quote their output.

## Commands

```sh
bin/hp doctor                      # which tools are available on this machine
bin/hp check design/<name>.yaml    # schema + geometry + rules; exit 1 on any error
bin/hp sketch design/<name>.yaml   # sketch stage: checks + one PDF/PNG per level, nothing else
bin/hp build design/<name>.yaml    # final stage: DXF/PDF/PNG per level, IFC, report, read-back checks
bin/hp dwg2dxf sources/<f>.dwg derived/survey/   # survey DWG to DXF, original untouched
hooks/gate.sh                      # the done-gate; must exit 0 before you say "done"
PYTHONPATH=src ~/.venvs/architecture-ai/bin/python -m pytest -q tests
```

`bin/hp` runs `~/.venvs/architecture-ai/bin/python` (override with `HP_PYTHON`).
External tool paths are in `config/tools.toml`, with per-machine overrides in
the untracked `config/tools.local.toml` or `HP_<TOOL>` environment variables.

## Folders

| Folder | What | Who writes it |
|---|---|---|
| `sources/` | Authoritative originals: survey DWG, deeds, municipal permits. Checksums in `sources/MANIFEST.sha256`. | The user. **Never modify.** |
| `derived/` | Conversions of sources (DXF from DWG, survey point tables). | Scripts only, reproducibly. |
| `design/` | The design specs. `design/examples/` holds test fixtures, not real designs. | You. |
| `rules/` | Jurisdiction rules with numeric limits and their sources. | You, only with a cited source. |
| `out/` | Generated drawings, IFC and reports. | `bin/hp build` only. Never hand-edit. |
| `src/houseplan/` | The kit: schema, geometry, checks, drawings, IFC, verification. | You, test-first. |
| `docs/` | Brief, decisions, research. | You. |

## Non-negotiables

- Do not modify anything in `sources/`. Convert into `derived/`.
- Do not invent survey, legal, geotechnical, structural or planning facts.
  Missing information is written down in `docs/open-questions.md` and left
  unset in the spec (`null`), never guessed.
- When tracing an existing drawing or survey, that source is the truth. Flag
  conflicts. Don't "improve" it silently.
- Never change the brief to fit the design: `program`, `target_area`, `via`
  and `docs/brief.md` change only when the owner asks, recorded in
  `docs/decisions.md`. If the brief cannot be met, say so and show why.
- Never weaken a check, a rule value or a test so that a design passes. A
  rule value changes only when you have its source; cite it in `rules/`.
- A rule marked `unverified` stays a warning until someone confirms it
  against the regulation text.
- Read every PNG you generate. A run that "passed" but looks wrong is wrong.
- Nothing in this repo is permit-ready until it has been reviewed and signed by a
  licensed engineer (مهندس دارای پروانه اشتغال، نظام مهندسی). Never claim
  otherwise.
- Write code to match the surrounding code; add a test for every new check
  that first fails on a broken fixture.

## Two stages: spend effort where it pays

- **Sketch** (`project.stage: sketch`, the default): the owner is choosing
  between layouts and will reject most of them. Produce exact plans and
  nothing more: `bin/hp sketch`, show the PNGs, report room areas and failing
  rules in a few lines, add one line to `docs/STATUS.md`. No reports, IFC,
  feedback files or prose documents.
- **Final** (`project.stage: final`, set only when the owner picks a layout):
  `bin/hp build`, the full audit, revisions tagged and reviewed through
  `docs/feedback/`.

Accuracy is the same in both: every sketch passes the same checks.

## Done means

`hooks/gate.sh` exits 0 and the PNGs were looked at. In the final stage also:
`out/<name>/report.md` has no errors, and every warning is fixed or explained
in `docs/decisions.md`.
