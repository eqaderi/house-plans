# Milestone D Handoff (Floor-Plan Generation, Evaluation, and Versioning)

Target audience: **Claude Code** (primary developer), **Google Gemini CLI**, and
**OpenAI Codex**.

Before starting Milestone D, read [`docs/AGENT_CONTRACT.md`](AGENT_CONTRACT.md)
and [`docs/MASTER_SPEC.md`](MASTER_SPEC.md). Create a new branch `milestone-d`
from `main` (`git checkout -b milestone-d main`). Do not commit directly to
`main`.

---

## 1. What is Completed in Milestones A, B, and C

Milestones A, B, and C are finalized, verified on Python 3.11 and Python 3.13,
and merged into `main`:

- **Milestone A — Domain Foundation ([`docs/milestones/A.md`](milestones/A.md)):**
  - Canonical Pydantic `StrictModel` schemas (`src/house_ai/domain/`) and 22
    generated JSON Schemas in `schemas/` (`house-ai schemas check`).
  - Write-once content-addressed `ProjectStore` (`src/house_ai/storage/`) with
    SHA-256 hash-chained `events.jsonl` and tamper detection
    (`house-ai project verify <dir>`).
  - Workflow state machine (`src/house_ai/orchestration/workflow.py`) with four
    strictly human-only approval gates (`site`, `program`, `plan`, `model`) and
    geometric/topological integrity checks (`src/house_ai/domain/integrity.py`).
- **Milestone B — Site Ingestion & Terrain ([`docs/milestones/B.md`](milestones/B.md)):**
  - Format detection, DXF (`ezdxf`) and DWG (`ODA File Converter`) adapters, raw
    SOURCE-frame extraction, human layer mapping (`layers.yaml`), reversible
    `SurveyTransform` (`SOURCE → GRID → LOCAL`), boundary extraction, spot/label
    elevation matching (including inline units `1664.0 m` and point-name labels),
    Delaunay TIN terrain, road frontage measurement, and static SVG/HTML site
    review output (`src/house_ai/render2d/site_svg.py`).
  - Per-project workspaces under `projects/<name>/` ([ADR 0009](adr/0009-personal-first-project-folders.md))
    and verbatim owner statement recording (`house-ai statement add|list`).
- **Milestone C — Agent-First Owner Interview & Space Program ([`docs/milestones/C.md`](milestones/C.md), [ADR 0011](adr/0011-agent-first-interview-interface.md)):**
  - **Agent-first architecture (no API key required):** Claude Code, Gemini CLI,
    and OpenAI Codex operate the entire interview and programming workflow via
    documented `house-ai` CLI commands (`--actor agent:<tool> --json`) without
    requiring any paid API key. The Anthropic SDK adapter (`providers/claude.py`,
    [ADR 0010](adr/0010-claude-adapter-for-the-interview.md)) remains strictly
    optional.
  - Adaptive conversational interview with a 30-question completeness checklist
    plus custom adaptive follow-up questions (`--question`, `--question-text`,
    `--topic`), supporting Persian, English, and mixed-language homeowner
    answers (`--set SLOT=VALUE`, `--unknown SLOT`, `--interpret-json`).
  - Strict separation between the homeowner's verbatim words (`owner_answer`)
    and agent/parser slot readings (`inference` until confirmed via
    `house-ai interview confirm`).
  - Deterministic contradiction detection and resolution (`interview resolve`),
    requirement revision with full turn history (`interview revise`), space
    program synthesis (`src/house_ai/program/builder.py`), and deterministic
    program validation (`src/house_ai/program/validation.py`) including steep
    hillside engineering assumptions (`asm-hillside-engineering`) and flat-pad
    warnings (`steep_site_flat_pad`).

---

## 2. Current State of `projects/my-house`

- Location: `projects/my-house/` (committed to this private GitHub repository
  per explicit homeowner authorization).
- Workflow state: `SITE_NEEDS_VERIFICATION` (13 events, 10 artifact versions;
  `house-ai project verify my-house` is intact).
- Stored survey sources:
  - `surveys/seperated.dwg` (`src-seperated`, SHA-256 `27624ba14003...`): parcel
    boundary, ~9 m road, and 6 elevation points.
  - `surveys/elevation.dwg` (`src-elevation`, SHA-256 `9689880c47d9...`): 21
    interior/edge elevation points.
  - (`final.dwg` was the wrong survey and is permanently excluded via
    `.gitignore`.)
- Extracted site measurements (`site/v1`, unconfirmed survey values):
  - Parcel candidate `src-seperated#D7`: **600.004 m²**, 4 vertices,
    perimeter **107.140 m**.
  - Frontage: **21.000 m**, on the lower-X (drawing-west) side beside
    road candidates `BC` and `C5`, **9.000 m** apart. Geographic north is unknown.
  - Surveyed elevation points: **27 points**, coordinate Z **1664.884–1680.071 m**
    (all-survey relief **15.187 m**, including points outside the parcel).
  - Inside-parcel spot range: **1664.884–1677.438 m**, relief **12.554 m**.
    The TIN clipped to the parcel has interpolated relief **12.712 m**.
  - Mean slope: **38.87% over the whole survey TIN**; **40.68% over its parcel
    intersection**, each weighted by horizontal area. These are preliminary
    calculations, not verified ground truth between survey points.
  - The earlier hashes, elevations, northern-road claim and 65.2% value in this
    handoff were unsupported. See the [source audit](../projects/my-house/reviews/survey-audit/REPORT.md).
- Confirmed by the homeowner (recorded in `owner_statements` `v1`–`v4`):
  1. Coordinates are UTM (`stmt-001`).
  2. Elevations are in metres above sea level (`stmt-002`).
  3. The ~12–12.5 m drop across the parcel is real (`stmt-003`).
  4. The land is genuinely steep (`stmt-004`).

---

## 3. Unresolved Site Verification Items (`projects/my-house`)

The following items in `projects/my-house/` remain **unresolved** and block the
`site` gate (see [`projects/my-house/reviews/CONFIRM-SITE.md`](../projects/my-house/reviews/CONFIRM-SITE.md)):

1. **Exact UTM zone** (not declared in the DWG headers).
2. **Hemisphere** (North vs South, unless independently established by the
   homeowner).
3. **Horizontal datum / EPSG code** (e.g. WGS 84 vs local datum).
4. **Precise vertical datum** (specific national levelling datum / benchmark
   beyond "metres above sea level").
5. **Formal verification of the legal parcel boundary** (`--boundary-verified`)
   and review of the two steep-edge TIN artifact warnings (`steep_triangle`,
   `xy_duplicate_z_mismatch`).

**Critical rules:**
- Never invent any of the missing coordinate/datum facts above.
- Never run `site confirm` or `workflow approve` on behalf of the homeowner.
- Keep `projects/my-house` in `SITE_NEEDS_VERIFICATION` until the homeowner runs
  `house-ai site confirm my-house ...` and `house-ai workflow approve my-house site --id site --approver <name>`
  in their own interactive terminal.

---

## 4. How the Agent-Operated Interview Works

Coding agents (Claude Code, Gemini CLI, Codex) conduct or resume the homeowner
interview directly using the CLI:

1. **Inspect project, site context, and checklist:**
   ```bash
   .venv/bin/house-ai project status my-house --json
   .venv/bin/house-ai interview status my-house --json
   ```
2. **Start or resume the interview:**
   ```bash
   .venv/bin/house-ai interview start my-house --json --actor agent:claude-code
   ```
3. **Record verbatim homeowner answers (English, Persian, or mixed) and
   propose structured slot interpretations (`--set`):**
   ```bash
   .venv/bin/house-ai interview answer my-house "<owner's exact words>" \
       [--question <qid|slot|custom-followup-id>] \
       [--question-text "<adaptive follow-up question wording>"] \
       [--topic <BriefTopic>] \
       --set slot1=value1 --set slot2=value2 \
       [--unknown undecided_slot] \
       --json --actor agent:claude-code
   ```
4. **Confirm, reject, revise, or resolve contradictions after asking the
   homeowner:**
   ```bash
   .venv/bin/house-ai interview confirm my-house [slots...] --text "<owner's confirmation>" --json --actor agent:claude-code
   .venv/bin/house-ai interview reject my-house --slot <slot> --text "<owner's correction>" --json --actor agent:claude-code
   .venv/bin/house-ai interview revise my-house <qid|slot> "<new verbatim words>" --set slot=new_value --json --actor agent:claude-code
   .venv/bin/house-ai interview resolve my-house <contradiction-id> "<owner's choice>" --option <1..N> [--defer] --json --actor agent:claude-code
   ```
5. **Build and validate the space program:**
   ```bash
   .venv/bin/house-ai program build my-house --out projects/my-house/design --actor agent:claude-code
   ```
   Once the site is approved and no blocking findings remain:
   ```bash
   .venv/bin/house-ai program review my-house --actor agent:claude-code
   ```

---

## 5. What Milestone D Must Implement

Per [`docs/MASTER_SPEC.md`](MASTER_SPEC.md) (sections `CONSTRAINT ARCHITECTURE`,
`FLOOR-PLAN GENERATION`, `PLAN EVALUATION`, `REVISION SYSTEM`, and `MILESTONE D — PLAN`):

1. **Formal Constraint Compilation (`src/house_ai/constraints/`):**
   - Compile an approved `SpaceProgram`, `DesignBrief`, `Site`, and optional
     `CodePack` into explicit `HARD` (invalidating) and `SOFT` (multi-objective
     scored) constraints.
   - Maintain the `CodePack` boundary (`src/house_ai/domain/codepack.py`): never
     claim `"code compliant"` unless a verified jurisdiction and edition are
     loaded; otherwise report `"not checked"` or
     `"conceptual best-practice check only"`.
2. **Solver-Backed Multi-Concept Floor-Plan Generator (`src/house_ai/generation/`):**
   - Implement `PlanGenerator` (`src/house_ai/generation/base.py`) using a
     hybrid architecture: topology/strategy setup → formal discrete/geometric
     solver (e.g. Google OR-Tools CP-SAT or justified optimization engine +
     Shapely computational geometry) → valid canonical `HouseModel` /
     `PlanVersion` geometry → deterministic `check_model` validation.
   - Do **not** let an LLM invent room coordinates.
   - Given the same approved brief and program, generate **at least THREE (3+)
     meaningfully different architectural concepts** (e.g. compact two-story,
     split-level / stepped hillside, courtyard / two-wing / linear), not
     cosmetic variations.
   - Each generated candidate must produce:
     - `plan.json` (canonical `PlanVersion` stored in `ProjectStore`)
     - `plan.svg` (rendered 2D floor plan per level + site context)
     - `metrics.json` / `EvaluationReport`
     - `violations.json`
     - `assumptions.json`
     - `explanation.md`
3. **2D Floor-Plan SVG Renderer (`src/house_ai/render2d/`):**
   - Render canonical `PlanVersion` geometry to deterministic SVG showing levels,
     walls, doors, windows, stairs, room labels, dimensions, room areas, north
     arrow, circulation paths, and site boundary/envelope context.
4. **Modular Quantitative & Qualitative Evaluators (`src/house_ai/evaluation/`):**
   - Implement at minimum:
     - `GeometryEvaluator` (wrapping `check_model` + dimensional checks)
     - `ProgramEvaluator` (room counts, min/target areas, widths, level prefs)
     - `AdjacencyEvaluator` (hard and soft adjacency satisfaction, graph distances)
     - `CirculationEvaluator` (reachability, corridor ratio, guest/private crossings)
     - `PrivacyEvaluator` (zone separation, entry sightlines, bedroom privacy)
     - `SiteEvaluator` (envelope containment, road entry alignment, slope/level
       fit)
   - Every metric must carry its `MeasurementMethod` / `Epistemic` status
     (`measured`, `inferred`, `simulated`, `ai_judgment`, `not_checked`) and
     provenance. Expose individual metrics and trade-offs rather than a single
     opaque score.
5. **Conversational Plan Revisions & Versioning:**
   - Every plan iteration writes a new immutable `PlanVersion` in `ProjectStore`
     and produces a `RevisionReport` (requested change verbatim, geometry/rooms
     changed, area deltas, metric deltas, new/resolved violations, assumptions).
   - Never overwrite an approved or reviewed plan.
   - Integrate with workflow transitions (`PROGRAM_APPROVED → CONCEPT_GENERATION ⇄ CONCEPT_REVIEW → [plan gate] PLAN_APPROVED`)
     while keeping `workflow approve <dir> plan` strictly human-only.

---

## 6. How Milestone D Should Account for a Steep Hillside Parcel

Because the primary project (`projects/my-house/`) sits on a steep parcel
(see the audited values in section 2: ~600 m², ~12.5 m relief inside the parcel,
~41 % mean slope over the parcel's TIN, 21 m frontage on the drawing-west side;
geographic north unknown), Milestone D's level/section model, solver, and `SiteEvaluator` must
support hillside realities (without hardcoding `my-house` numbers into general
algorithms):

- **Section / level strategy against terrain:** support stepped / split-level
  and walk-out lower-level configurations (`Level.elevation_m` relative to the
  local datum and terrain elevation range), not only flat single-pad houses.
- **Road-frontage access:** allow parking/garage and primary entrance placement
  aligned with the road frontage edge and road elevation.
- **Excavation, retaining walls, and drainage proxies:** surface cut/fill depth,
  footprint-on-slope, and retaining-wall exposure as explicit metrics or
  assumptions in `SiteEvaluator` rather than silently flattening the terrain.

---

## 7. What Milestone D Must NOT Assume

1. **Do NOT assume `projects/my-house` is site-approved or program-approved.**
   Until the homeowner confirms the site and approves the `site` and `program`
   gates in their terminal, run Milestone D solver tests and demonstrations on
   synthetic fixtures (such as `examples/projects/synthetic-bungalow/`,
   `examples/surveys/synthetic/`, and a synthetic sloped-site fixture).
2. **Do NOT assume the entire 600 m² parcel of `my-house` is buildable.**
   Setbacks, maximum site coverage, height limits, and FAR for the jurisdiction
   are not yet loaded (`CodePack` is unverified).
3. **Do NOT require an Anthropic, OpenAI, or Gemini API key** to generate,
   solve, evaluate, render, or revise floor plans. Coding agents (Claude Code,
   Gemini CLI, Codex) must be able to run all Milestone D commands deterministically
   via the `house-ai` CLI.
4. **Do NOT claim any generated concept is permit-ready, code-compliant, or
   structurally/geotechnically engineered.**

---

## 8. Which Tests and Schemas Must Remain Intact

All existing verification checks must continue to pass before and after every
Milestone D change:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests examples
.venv/bin/house-ai schemas check
.venv/bin/house-ai project verify my-house
```

- **22 JSON Schemas** in `schemas/` must stay synchronized with `src/house_ai/domain/`
  (`tests/test_schemas.py`). If you add new optional fields to existing models,
  ensure backwards compatibility with stored artifacts or regenerate synthetic
  fixtures without breaking `projects/my-house/` (`house-ai project verify my-house`
  must always pass with 0 problems).
- **`docs/AGENT_CONTRACT.md`** must remain `< 12,000` characters
  (`tests/test_agent_instructions.py`).
- **Vendor SDK isolation** (`tests/test_providers_agents.py::test_only_vendor_adapters_import_a_vendor_sdk`):
  no vendor SDK may be imported outside `src/house_ai/providers/`.
- **All 419 tests** across Milestones A, B, and C (`test_schemas.py`,
  `test_units_crs_geometry.py`, `test_integrity.py`, `test_storage_workflow_cli.py`,
  `test_providers_agents.py`, `test_agent_instructions.py`, `test_site_ingestion.py`,
  `test_site_review_fixes.py`, `test_projects.py`, `test_interview.py`,
  `test_ai_interview.py`) must remain green on both Python 3.11 and Python 3.13.
