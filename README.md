# HOUSE DESIGN AI

A model-provider-neutral system for exploring the design of a real house on
a real surveyed site. Its first purpose is the owner's own house on their own
parcel ([`projects/my-house/`](projects/my-house/README.md)); other projects get
their own folder (ADR 0009). Its outputs are structured semantic geometry, not
pictures. The full specification is [docs/MASTER_SPEC.md](docs/MASTER_SPEC.md).

**Current state: Milestones A–D merged into `main`; active development proceeds under the stage lifecycle in [docs/PROJECT_TRACKER.md](docs/PROJECT_TRACKER.md).**
Milestone A ([report](docs/milestones/A.md)) delivered canonical schemas,
project storage with provenance and the workflow with human approval gates.
Milestone B ([report](docs/milestones/B.md)) turns a DXF or DWG survey into
a validated site model: read-only inspection, raw CAD extraction, unit and
CRS confirmation by a human, a reversible survey-to-local transform,
boundary and terrain, a validation report, site and terrain SVGs and a
review page. Milestone C ([report](docs/milestones/C.md)) adds an
**agent-first** conversational owner interview ([ADR 0011](docs/adr/0011-agent-first-interview-interface.md))
that becomes a design brief and a validated space program for the floor-plan
solver, with owner confirmation and the program approval gate. Milestone D
([report](docs/milestones/D.md), [ADR 0013](docs/adr/0013-solver-backed-plan-generation.md))
generates several structurally different plan options from the approved
program with a constraint solver (OR-Tools CP-SAT), with level heights taken
from a steep site's surveyed terrain: a walk-out option that digs in behind
retaining walls, and stepped, linear and two-wing options that sit over the
falling ground (their void beneath is reported, not used). It evaluates them with
six evaluators, renders dimensioned SVG plans and saves every revision as a new plan
version behind the human plan gate. Blender and Unreal come in later milestones.

## Setup

Requires Python 3.13 or newer (developed and tested on 3.13 only; see [ADR 0026](docs/adr/0026-python-3-13-only.md)).

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
# or, for the exact tested versions on Python 3.13:
# .venv/bin/pip install -r requirements-lock.txt -e . --no-deps
```

No paid AI API key, Blender or Unreal is needed for the core workflow. DXF
needs nothing extra; DWG needs the free ODA File Converter (optional; its test
is skipped without it).

### Primary workflow: Agent-operated interview (Claude Code, Gemini CLI, Codex — no API key required)

Talk directly with **Claude Code**, **Gemini CLI**, or **OpenAI Codex** in
English, Persian, or mixed language. The coding agent inspects the project and
site, conducts an adaptive architectural interview (using the 30-question bank
as a completeness checklist plus intelligent follow-up questions), records your
exact words verbatim, proposes interpretations (`--set`), asks
you to confirm or correct them, resolves contradictions, and builds/validates
the space program — while human approval gates remain strictly yours in your
own terminal:

```bash
.venv/bin/house-ai project status my-house --json
.venv/bin/house-ai interview status my-house --json
.venv/bin/house-ai interview start my-house --json --actor agent:claude-code
.venv/bin/house-ai interview answer my-house "<owner's exact words>" \
    --set slope_strategy=step_down --set entry_at_road=true --actor agent:claude-code
.venv/bin/house-ai interview confirm my-house --text "<owner's confirmation>" --actor agent:claude-code
.venv/bin/house-ai program build my-house --out projects/my-house/design --actor agent:claude-code
```

### Optional: direct Anthropic SDK adapter (`--ai anthropic`)

If you prefer running the standalone terminal loop with the Anthropic SDK
rewording questions ([ADR 0010](docs/adr/0010-claude-adapter-for-the-interview.md)),
that adapter remains available as an optional extra and requires an
`ANTHROPIC_API_KEY` in your environment:

```bash
.venv/bin/pip install -e '.[ai]'
export ANTHROPIC_API_KEY=...        # never put it in a file in this repository
.venv/bin/house-ai interview run my-house --owner <you> --ai anthropic
```

It asks you to type `allow anthropic` before your answers or site details are
sent. Without a key, the agent-operated CLI and the built-in interview run with
zero external API dependencies.

## Run the tests

```bash
.venv/bin/python -m pytest -q          # full suite
.venv/bin/ruff check src tests examples  # lint
.venv/bin/house-ai schemas check       # committed JSON Schemas match the code
```

## Try it

Load the synthetic example into a new project store (under the git-ignored
`project-data/`):

```bash
.venv/bin/house-ai example load project-data/demo --actor agent:cli
.venv/bin/house-ai project status project-data/demo
.venv/bin/house-ai artifact check project-data/demo plan-a
.venv/bin/house-ai project verify project-data/demo
```

The project stops in `SITE_INGESTION`. Approving the site is a human act and
needs a terminal:

```bash
.venv/bin/house-ai workflow approve project-data/demo site --id site --approver <your-name>
# type the confirmation phrase it shows, e.g.: approve site site v1
```

Then continue through the program and plan gates:

```bash
.venv/bin/house-ai workflow transition project-data/demo INTERVIEWING --reason "start" --actor human:<you>
.venv/bin/house-ai workflow transition project-data/demo PROGRAM_REVIEW --reason "program drafted" --actor human:<you>
.venv/bin/house-ai workflow approve project-data/demo program --id program --approver <your-name>
.venv/bin/house-ai workflow transition project-data/demo PLAN_GENERATION --reason "go" --actor human:<you>
.venv/bin/house-ai workflow transition project-data/demo PLAN_REVIEW --reason "plan-a ready" --actor human:<you>
.venv/bin/house-ai workflow approve project-data/demo plan --id plan-a --approver <your-name>
```

Generate plan options on the synthetic steep hillside (Milestone D). The
exploratory preview stores nothing and needs no approval; the gated run works
only after the human approved the site and program gates
([worked examples](docs/AGENT_WORKFLOWS.md)):

```bash
.venv/bin/house-ai example load project-data/hill --name synthetic-hillside --project-id synthetic-hillside --actor human:<you>
.venv/bin/house-ai plan generate project-data/hill --exploratory --out project-data/hill-preview --actor human:<you>
# after `workflow approve ... site` and `... program` by you, in your terminal:
.venv/bin/house-ai plan generate project-data/hill --actor human:<you>      # -> PLAN_REVIEW
.venv/bin/house-ai plan revise project-data/hill concept-split-level "Bigger kitchen" --area pi-kitchen=16 --actor human:<you>
.venv/bin/house-ai plan review project-data/hill concept-split-level --actor human:<you>
```

A committed preview of these plan options is in
[examples/projects/synthetic-hillside/concepts/](examples/projects/synthetic-hillside/concepts/comparison.md).

Run the site pipeline on the synthetic survey (Milestone B):

```bash
S=examples/surveys/synthetic
.venv/bin/house-ai site inspect $S/survey.dxf --layers $S/layers.yaml        # read-only
.venv/bin/house-ai project init project-data/site-demo --id site-demo --name "Synthetic survey" --classification synthetic --actor human:<you>
.venv/bin/house-ai source add project-data/site-demo $S/survey.dxf --classification synthetic --actor human:<you>
.venv/bin/house-ai site ingest project-data/site-demo --source src-survey --layers $S/layers.yaml --actor human:<you>   # -> SITE_NEEDS_CONFIRMATION
.venv/bin/house-ai site confirm project-data/site-demo --confirmer <you> --units m --elevation-units m \
    --epsg 25832 --vertical-datum DHHN2016 --vertical-epsg 7837 --boundary-verified   # interactive; -> SITE_INGESTION
.venv/bin/house-ai workflow approve project-data/site-demo site --id site --approver <you>   # interactive
.venv/bin/house-ai site report project-data/site-demo --id site --out project-data/site-demo-report
```

Your own project: `.venv/bin/house-ai project status my-house`, then
[projects/my-house/reviews/CONFIRM-SITE.md](projects/my-house/reviews/CONFIRM-SITE.md).
A new project: `.venv/bin/house-ai project new <name> --actor human:<you>`
([projects/README.md](projects/README.md)).

Validate any file against its schema:

```bash
.venv/bin/house-ai validate plan examples/projects/synthetic-bungalow/plans/plan-a.json \
    --site examples/projects/synthetic-bungalow/site.yaml
```

## Repository

| Path | Contents |
|---|---|
| `docs/` | Spec, [architecture](docs/ARCHITECTURE.md), [domain model](docs/DOMAIN_MODEL.md), [agent contract](docs/AGENT_CONTRACT.md), [professional handoff](docs/PROFESSIONAL_HANDOFF.md), [ADRs](docs/adr/), milestone reports |
| `schemas/` | Generated JSON Schemas (do not edit; run `house-ai schemas export`) |
| `src/house_ai/` | The Python package (`domain`, `storage`, `orchestration`, `cli`, site and interview pipelines, `constraints`, `generation`, `evaluation`, `render2d`, and boundaries for later milestones) |
| `agents/roles.yaml` | Agent role definitions |
| `examples/` | Synthetic example projects |
| `tests/` | Automated tests (synthetic data only) |
| `projects/` | One folder per house project; `my-house/` is the owner's own (committed, private repository) |
| `project-data/` | Private scratch space, git-ignored |
| `skills/` | Canonical agent skills, linked into `.claude/skills/` and `.agents/skills/` ([skills/README.md](skills/README.md)) |
| `apps/reviewer/` | Placeholder for later milestones |

AI agents: start with [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md) or
[GEMINI.md](GEMINI.md), which all point to the agent contract.
