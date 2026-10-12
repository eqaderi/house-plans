# House plans

Exact, checkable house plans for a site in Iran, worked on with Claude Code
on one laptop and Codex on another.

An agent never draws here. It edits one design spec in integer millimetres
(`design/<name>.yaml`). Deterministic code turns that into room outlines, net
areas, DXF/PDF/PNG sheets at true scale and an IFC model. The same code then
reopens the written files and checks them against the spec. The approach
follows [anatomy](https://github.com/wheresryan22/anatomy): a skill that sets
the workflow, a small kit that does the geometry, an audit that fails loudly,
and renders you read.

## Quick start

```sh
bin/doctor                                     # tools on this machine
bin/hp check design/examples/bungalow.yaml     # 0 errors expected
bin/hp build design/examples/bungalow.yaml     # writes out/bungalow/
python -m pytest -q                            # with the architecture venv
hooks/gate.sh                                  # the done-gate
```

`bin/hp` uses `~/.venvs/architecture-ai/bin/python`; override with `HP_PYTHON`.

## Layout

| Path | What |
|---|---|
| `AGENTS.md` | Rules for every agent (Codex reads it; `CLAUDE.md` imports it) |
| `.agents/skills/house-plan/` | The skill: workflow, craft rules, references (`.claude/skills/house-plan` links here) |
| `.claude/` | Claude Code hooks, permissions and the `plan-verifier` subagent |
| `.codex/config.toml`, `.mcp.json` | The IFC MCP server for Codex and Claude Code |
| `src/houseplan/` | The kit: `model` (schema), `geometry`, `checks`, `rules`, `drawing` (DXF), `render` (PDF/PNG), `ifc`, `verify` (read-back), `tools` (doctor, DWG) |
| `rules/` | Jurisdiction rules with values, sources and verified/unverified status |
| `design/` | Design specs; `design/examples/` holds test fixtures |
| `sources/` | Original survey and legal documents. Never modified |
| `derived/` | Reproducible conversions of sources |
| `docs/` | Brief, open questions, decisions, research |
| `tests/` | Each test breaks the example one way and expects the matching finding |
| `evals/evals.json` | Test prompts and what a good agent answer contains |
| `hooks/` | `check-design.sh` (after spec edits) and `gate.sh` (before "done") |

## On any laptop

First time on a machine:

```sh
git clone git@github.com:eqaderi/house-plans.git && cd house-plans
bin/doctor          # lists what is missing and the command for each fix
bin/setup           # Python environment: installs what is missing, sets the pinned versions
bin/setup --apps    # optionally, missing GUI apps via Homebrew (Blender+Bonsai, FreeCAD, QGIS, Inkscape)
bin/doctor          # until it reports 0 required missing
```

If a tool lives somewhere else on that machine, put its path in the untracked
`config/tools.local.toml` (same keys as `config/tools.toml`). In Codex, trust
the project so `.codex/config.toml` loads. Claude Code runs `bin/doctor
--quiet` at every session start.

Every session, either tool, either laptop: `git pull` first; update
`docs/STATUS.md`, commit and push last. CI on GitHub runs the tests, checks
every spec and draws the sheets; the sheets are attached to each run as the
`sheets` artifact.

## Status

The kit covers straight walls, openings, rooms, straight stairs, multiple
levels, plan sheets and IFC. Not yet modelled: columns, sections, elevations,
site plan, roofs, terraces outside the enclosure, L/U stairs. The Iranian
rules in `rules/iran.yaml` carry a verified/unverified status per value.
Nothing here is permit-ready until a licensed engineer has reviewed and
signed it.
