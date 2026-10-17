# HOUSE DESIGN AI

A model-provider-neutral system for exploring the design of a real house on
a real surveyed site. Its first purpose is the owner's own house on their own
land ([`projects/my-house/`](projects/my-house/README.md)); other projects get
their own folder (ADR 0009). Its outputs are structured semantic geometry, not
pictures. The full specification is [docs/MASTER_SPEC.md](docs/MASTER_SPEC.md).

**Current state: Milestone C (owner interview and space program), on branch
`milestone-c`, built on `milestone-b` (not yet merged into `main`).**
Milestone A ([report](docs/milestones/A.md)) delivered canonical schemas,
project storage with provenance and the workflow with human approval gates.
Milestone B ([report](docs/milestones/B.md)) turns a DXF or DWG survey into
a validated site model: read-only inspection, raw CAD extraction, unit and
CRS verification by a human, a reversible survey-to-local transform,
boundary and terrain, a validation report, site and terrain SVGs and a
review page. Milestone C ([report](docs/milestones/C.md)) adds a
conversational owner interview that becomes a design brief and a validated
space program for the floor-plan solver, with owner confirmation and the
program approval gate. Plan generation, Blender and Unreal come in later
milestones.

## Setup

Requires Python 3.11 or newer (developed and tested on 3.13).

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
# or, for the exact tested versions:
# .venv/bin/pip install -r requirements-lock.txt -e . --no-deps
```

No paid AI API, Blender or Unreal is needed. DXF needs nothing extra;
DWG needs the free ODA File Converter (optional; its test is skipped
without it).

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
.venv/bin/house-ai workflow transition project-data/demo CONCEPT_GENERATION --reason "go" --actor human:<you>
.venv/bin/house-ai workflow transition project-data/demo CONCEPT_REVIEW --reason "plan-a ready" --actor human:<you>
.venv/bin/house-ai workflow approve project-data/demo plan --id plan-a --approver <your-name>
```

Run the site pipeline on the synthetic survey (Milestone B):

```bash
S=examples/surveys/synthetic
.venv/bin/house-ai site inspect $S/survey.dxf --layers $S/layers.yaml        # read-only
.venv/bin/house-ai project init project-data/site-demo --id site-demo --name "Synthetic survey" --classification synthetic --actor human:<you>
.venv/bin/house-ai source add project-data/site-demo $S/survey.dxf --classification synthetic --actor human:<you>
.venv/bin/house-ai workflow transition project-data/site-demo SITE_INGESTION --reason "survey received" --actor human:<you>
.venv/bin/house-ai site ingest project-data/site-demo --source src-survey --layers $S/layers.yaml --actor human:<you>
.venv/bin/house-ai workflow assess-site project-data/site-demo --id site --actor human:<you>   # -> SITE_NEEDS_VERIFICATION
.venv/bin/house-ai site confirm project-data/site-demo --confirmer <you> --units m --elevation-units m \
    --epsg 25832 --vertical-datum DHHN2016 --vertical-epsg 7837 --boundary-verified   # interactive
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
| `src/house_ai/` | The Python package (`domain`, `storage`, `orchestration`, `cli`, and boundaries for later milestones) |
| `agents/roles.yaml` | Agent role definitions |
| `examples/` | Synthetic example projects |
| `tests/` | Automated tests (synthetic data only) |
| `projects/` | One folder per house project; `my-house/` is the owner's own (committed, private repository) |
| `project-data/` | Private scratch space, git-ignored |
| `apps/reviewer/`, `skills/` | Placeholders for later milestones |

AI agents: start with [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md) or
[GEMINI.md](GEMINI.md), which all point to the agent contract.
