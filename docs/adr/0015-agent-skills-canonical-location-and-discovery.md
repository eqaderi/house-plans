# ADR 0015: Canonical agent skills layout and tool-specific discovery

Status: accepted (Stage S2, 2026-10-17)

## Context

Stage S2 introduces reusable project skills (`site-survey-review`,
`architectural-programming`, `generate-concepts`, and `critique-plan`) to teach
coding agents multi-step procedural workflows using `house-ai` commands while
strictly respecting human approval gates and domain integrity.

ADR 0005 initially decided:
> "No `.claude/`, `.agents/` or `.gemini/` rules or skills directories are
> added. Skills will be added when a recurring task justifies one."

With the arrival of Stage S2, recurring architectural workflows now justify
project skills. However, the three primary agent environments discover project
skills in different directories:
- **Claude Code** looks for skills in `.claude/skills/<skill-name>/SKILL.md`.
- **OpenAI Codex CLI** looks for skills in `.agents/skills/<skill-name>/SKILL.md`
  (and `.codex/skills/`, verified via `codex debug prompt-input`).
- **Antigravity / Gemini CLI** looks for skills in `.agents/skills/<skill-name>/SKILL.md`
  (documented in Antigravity Customization System, Workspace Customizations).

Duplicating skill files across `.claude/skills` and `.agents/skills` would cause
maintenance drift, violating the single-source-of-truth principle established in
ADR 0005.

## Decision

1. **Revision of ADR 0005**: The clause in ADR 0005 forbidding `.claude/` and
   `.agents/` directories is hereby revised to allow provider-specific skill
   discovery directories, while keeping `docs/AGENT_CONTRACT.md` as the sole
   location for engineering rules.
2. **Canonical location**: The authoritative canonical home for all project skills
   is `skills/<skill-name>/SKILL.md` at the repository root.
3. **Symlink-based provider discovery**: Relative symbolic links are maintained
   from provider discovery locations to the canonical skill directories:
   - `.claude/skills/<skill-name>` → `../../skills/<skill-name>`
   - `.agents/skills/<skill-name>` → `../../skills/<skill-name>`
4. **Zero duplication & automated drift prevention**:
   Because provider directories use relative symlinks directly pointing to
   the canonical `skills/` directories, physical file content is never duplicated.
   A test in `tests/test_skills.py` verifies that:
   - Every skill directory under `skills/` has valid symlinks in `.claude/skills/`
     and `.agents/skills/`.
   - Symlinks resolve to real directories without broken targets.
   - Skill files conform to the standardized authoring template.
5. **Standard skill authoring layout**:
   Every skill file `skills/<skill-name>/SKILL.md` must have:
   - YAML frontmatter with `name` and `description`.
   - Required sections: `## Purpose`, `## When to invoke`, `## Inputs`,
     `## Outputs`, `## Exact commands`, `## Required validations`,
     `## Human-approval boundaries`, and `## Failure handling`.

## Consequences

- All three coding agent environments (Claude Code, Codex, Antigravity) automatically
  discover the project's skills in fresh sessions.
- No duplicate markdown files exist; editing `skills/<name>/SKILL.md` immediately
  updates the view for all agents.
- Human approval gates (`workflow approve`, `site confirm`, `program reject`)
  are explicitly enforced in skill definitions, preventing automated bypass.
- The `tests/test_skills.py` suite runs in CI to guarantee that any new skill added
  maintains this contract.
