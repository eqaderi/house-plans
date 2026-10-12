# Research: how to make agent-generated house plans trustworthy

Compiled 2026-10-12 from nine parallel research passes (practitioner reports,
open-source agent tooling, academic papers, professional model checking,
toolchains, Claude Code practice, drafting standards, Iranian regulations).
Sources marked as unverified in the passes are left out or flagged.

## The finding that shaped this repo

Agents fail at producing plans directly and succeed at editing structured
intent that deterministic code turns into geometry and checks.

- LLMs writing coordinates: "None consistently produced a valid floor plan
  JSON" (arXiv 2605.14117, GPT-4o/o3/QwQ). Even fine-tuned with RL, 13 % of
  8-room plans still overlapped. Overlap rises with room count.
- LLM writes constraints, a solver places rooms: valid by construction
  (Kodnongbua et al. arXiv 2402.00052; Co-Layout 2511.12474 with 0 % overlap).
- Agents loops alone don't help: Claude Code and Codex in Blueprint-Bench
  (arXiv 2509.25229) were no better than random and claimed rooms were
  enclosed when they were not. FloorplanQA (2507.07644): models sum areas
  instead of taking the union.
- Practitioners: whole-house prompts miss doors and circulation and get
  stairs wrong (SketchUp, Blender and Revit MCP tests: focusedsketchup.com,
  mindstudio.ai, bimsmith.com); reading and checking structured or IFC data
  works (techdrawai.com: IFC exact where native RVT was not).
- "Valid geometry is not correct geometry" (rhino-mcp); "a picture is not a
  measure" (pascalorg/editor). Vision checks of renders were right only about
  65–68 % of the time in CADCodeVerify (2410.05340).

## What this repo does about it

| Lesson | Where |
|---|---|
| Agent edits a millimetre spec; code derives everything | `src/houseplan/model.py`, `geometry.py` |
| Rooms come from walls, so they cannot overlap or float | `geometry.build_level` |
| Boolean hard gates with structured findings and exit codes | `checks.py`, `bin/hp check` |
| Adjacency is not connectivity: check doors, reachability, pass-through | `checks.access_graph`, `check_pass_through` |
| Topology checks paired with area and dimension checks (no gaming) | `check_program`, rules |
| Read back what was written: DXF chains, text, IFC areas and schema | `verify.py` |
| Rule values carry a source and a confidence; unknown never passes | `rules/iran.yaml`, `RULES_NOT_APPLICABLE` |
| Brief cannot be rewritten to pass | `AGENTS.md` non-negotiables |
| Hooks run checks after edits and gate "done" | `hooks/`, `.claude/settings.json` |
| Independent reviewer that recomputes, never edits | `.claude/agents/plan-verifier.md`, `references/verify.md` |
| Renders are read for what checks cannot see, never as proof | skill step 7 |
| Light sketch stage, full documentation only for the chosen plan | `bin/hp sketch` vs `bin/hp build` |

## Ideas collected, not built yet

- Constraint solver for concept options (MILP / grid IP, with the minimal
  conflicting set fed back to the agent) — 2402.00052, 2511.12474.
- Clear-path width by distance field between openings (planhaus CIRC-01:
  error < 600 mm, warn < 900 mm); doorway landing 300 mm each side.
- Bathroom only off circulation, en-suite only off its bedroom (planscript
  access rules); equator-facing living rooms (archlang).
- Furniture and fixture clearance polygons (planscript-rust E903).
- IDS data requirements per element and `ifctester` (buildingSMART IDS;
  property list in the professional-checking pass).
- Wall junction topology: angle ≥ 5°, ≤ 2 ends per node, T not on a corner
  (plomada-mcp).
- Daylight 1/7 and 1/6 variants, light wells, building height from mean
  street level, plot coverage (rules/iran.yaml header).

## Key sources

- Papers: arXiv 2605.14117, 2402.00052, 2511.12474, 2509.25229, 2507.07644,
  2605.28579, 2512.16275, 2411.12279, 2410.05340.
- Open-source agent tooling: github.com/pepuscz/planhaus,
  github.com/chanmeng666/archlang, github.com/Stv-devl/PlanPilotMCP,
  github.com/Mats2208/plomada-mcp, github.com/jfromaniello/planscript,
  github.com/pascalorg/editor, github.com/LTplus-AG/ifc-lite,
  github.com/ProfRino/bonsai-bim-skills.
- Practice: techdrawai.com/blog/connect-claude-to-revit,
  bimpure.com/blog/pyrevit-mcp-claude-code-tutorial,
  community.osarch.org/discussion/2819, archsmarter.com/blog/ai-sketch-to-revit-model.
- Tooling: docs.ifcopenshell.org, ezdxf.readthedocs.io, code.claude.com/docs
  (hooks, permissions, sub-agents, best practices), github.com/openai/codex
  (skills in `.agents/skills`, MCP in `.codex/config.toml`).
- Iran: see `.agents/skills/house-plan/references/iran.md`.
