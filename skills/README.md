# Project Agent Skills

Canonical, provider-neutral architectural task instructions for coding agents
(Claude Code, Codex, Gemini CLI / Antigravity) per
[ADR 0015](../docs/adr/0015-agent-skills-canonical-location-and-discovery.md).

Every skill links [docs/AGENT_CONTRACT.md](../docs/AGENT_CONTRACT.md), uses only
real `house-ai` commands, and stops at every human gate. Commands write
`--actor agent:<tool>`; the agent substitutes its own name (`claude-code`,
`codex`, `gemini`).

## Discovery and Structure

- **Canonical location**: `skills/<skill-name>/SKILL.md` (the only copy)
- **Claude Code discovery**: `.claude/skills/<skill-name>` → `../../skills/<skill-name>`
- **Codex, Gemini CLI and Antigravity discovery**: `.agents/skills/<skill-name>` → `../../skills/<skill-name>`
- `python tools/sync_skills.py` creates missing links; `--check` only verifies;
  `--prune` also removes non-canonical entries (never done by default).
- `tests/test_skills.py` checks links, template, commands and flags against the CLI.

## Skills Catalog

1. **`site-survey-review`**: survey inspection, ingestion by source id, terrain/boundary validation, blockers, owner questions and `CONFIRM-SITE.md`, site gate request.
2. **`architectural-programming`**: adaptive interview in rounds (English, Persian, mixed) with hillside questions, verbatim recording, confirmation, contradictions, space program, program gate request.
3. **`generate-concepts`**: exploratory and stored CP-SAT concepts, feasibility reasons, revision ops, plan gate request.
4. **`critique-plan`**: grounded critique of exploratory or exported concepts, checked with `house-ai plan ground`, with explicit revision ops.
5. **`visual-review`**: visual inspection and grounded critique of rendered plan SVGs or reviewer bundles, defect detection (door clashes, window/wall misalignment, label overlaps), fix verification.

## Skill Template

Every `SKILL.md` must follow this structure:

```markdown
---
name: <skill-name>
description: <concise summary of when and how to invoke this skill>
---

# <Skill Title>

Follow [docs/AGENT_CONTRACT.md](../../docs/AGENT_CONTRACT.md) (<relevant sections>).
In every command, `agent:<tool>` is your own tool name: `claude-code`, `codex` or `gemini`.

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
<Gates and decisions that must NEVER be automated and must stop for human action>

## Failure handling
<How to diagnose errors, recover from infeasible states, and handle missing data>
```
