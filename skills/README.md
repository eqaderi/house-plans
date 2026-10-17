# Project Agent Skills

Canonical, provider-neutral architectural task instructions for coding agents
(Claude Code, Codex, Antigravity/Gemini) per [ADR 0015](../docs/adr/0015-agent-skills-canonical-location-and-discovery.md).

All skills reference [docs/AGENT_CONTRACT.md](../docs/AGENT_CONTRACT.md) and
operate deterministically via the `house-ai` CLI.

## Discovery and Structure

- **Canonical location**: `skills/<skill-name>/SKILL.md`
- **Claude Code discovery**: `.claude/skills/<skill-name>` (symlink to `../../skills/<skill-name>`)
- **Codex & Antigravity discovery**: `.agents/skills/<skill-name>` (symlink to `../../skills/<skill-name>`)

## Skills Catalog

1. **`site-survey-review`**: Survey file inspection, layer ingestion, terrain/boundary validation, identifying blockers and drafting the owner confirmation sheet.
2. **`architectural-programming`**: Adaptive homeowner interview (English, Persian, mixed), brief compilation, space program derivation and deterministic validation.
3. **`generate-concepts`**: Solver-backed floor-plan concept generation across massing strategies, feasibility reporting, revision ops, and review preparation.
4. **`critique-plan`**: Grounded architectural evaluation across geometry, program, circulation, privacy, and hillside metrics, proposing explicit revision operations.

## Skill Template

Every `SKILL.md` must follow this structure:

```markdown
---
name: <skill-name>
description: <concise summary of when and how to invoke this skill>
---

# <Skill Title>

## Purpose
<What this skill accomplishes and why>

## When to invoke
<Specific trigger conditions, workflow states, and user requests>

## Inputs
<Required files, project identifiers, survey data, or parameters>

## Outputs
<Artifacts, terminal reports, or store mutations produced>

## Exact commands
<Exact house-ai commands with arguments and flags>

## Required validations
<Validation steps, integrity checks, and assertions>

## Human-approval boundaries
<Explicit list of gates and decisions that must NEVER be automated and must stop for human action>

## Failure handling
<How to diagnose errors, recover from infeasible states, and handle missing data>
```
