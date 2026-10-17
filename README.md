# HOUSE DESIGN AI

A model-provider-neutral system for exploring the design of a real house on
a real surveyed site. Its outputs are structured semantic geometry, not
pictures. The full specification is [docs/MASTER_SPEC.md](docs/MASTER_SPEC.md).

**Current state: Milestone A (domain foundation).** Canonical schemas,
project storage with provenance, the workflow state machine with human
approval gates, and tests. CAD import, interview, plan generation, Blender
and Unreal come in later milestones. See
[docs/milestones/A.md](docs/milestones/A.md).

## Setup

Requires Python 3.11 or newer (developed and tested on 3.13).

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
# or, for the exact tested versions:
# .venv/bin/pip install -r requirements-lock.txt -e . --no-deps
```

No paid AI API, CAD software, Blender or Unreal is needed for Milestone A.

## Run the tests

```bash
.venv/bin/python -m pytest -q          # full suite
.venv/bin/ruff check src tests         # lint
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
| `project-data/` | Private project stores, git-ignored |
| `apps/reviewer/`, `skills/` | Placeholders for later milestones |

AI agents: start with [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md) or
[GEMINI.md](GEMINI.md), which all point to the agent contract.
