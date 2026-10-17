# ADR 0015: Canonical agent skills layout and tool-specific discovery

Status: accepted (approved by the owner 2026-10-17, Stage S2, S2-01)

## Context

Stage S2 introduces project skills (`site-survey-review`,
`architectural-programming`, `generate-concepts`, `critique-plan`) that teach
coding agents multi-step `house-ai` workflows while respecting the human
approval gates.

[ADR 0005](0005-shared-coding-agent-instructions.md) decided:
> "No `.claude/`, `.agents/` or `.gemini/` rules or skills directories are
> added. Skills will be added when a recurring task justifies one."

The agents discover project skills in different directories. Vendor
documentation, read 2026-10-17:

| Tool | Project skill location | Symlinked skill folders | Source |
|---|---|---|---|
| Claude Code | `.claude/skills/<name>/SKILL.md`, in the start directory and every parent up to the repository root | Documented as supported ("a `<skill-name>` entry in the ... project location can be a symlink to a directory elsewhere on disk") | https://code.claude.com/docs/en/skills |
| OpenAI Codex | `.agents/skills` in every directory from the working directory up to the repository root | Documented as supported ("Codex supports symlinked skill folders and follows the symlink target") | https://developers.openai.com/codex/skills (redirects to https://learn.chatgpt.com/docs/build-skills) |
| Gemini CLI | `.gemini/skills/` or its `.agents/skills/` alias (the alias takes precedence) | Not stated | https://geminicli.com/docs/cli/skills/ |
| Antigravity | `<workspace-root>/.agents/skills/<name>/` (`.agent/skills` still accepted) | Not stated | https://antigravity.google/docs/skills |

Copying skill files into `.claude/skills` and `.agents/skills` would let them
drift apart, against the single-source principle of ADR 0005.

## Decision

1. **Revision of ADR 0005**: its skills clause is revised to allow
   provider skill-discovery directories. `docs/AGENT_CONTRACT.md` stays the
   only location for engineering rules; skills link to it.
2. **Canonical location**: `skills/<skill-name>/SKILL.md` at the repository
   root is the only copy of each skill.
3. **Relative symlinks for discovery**, created by `tools/sync_skills.py`:
   - `.claude/skills/<skill-name>` → `../../skills/<skill-name>` (Claude Code)
   - `.agents/skills/<skill-name>` → `../../skills/<skill-name>` (Codex, Gemini CLI, Antigravity)
   No `.gemini/skills` link: Gemini CLI reads the `.agents/skills` alias.
4. **Drift prevention**: `tests/test_skills.py` fails when a provider link is
   missing, broken, points elsewhere or is a real copy, when a skill lacks
   the template's front matter or sections, names a `house-ai` command or
   flag the CLI does not have, or hardcodes an agent identity.
   `sync_skills.py` never deletes a non-canonical entry unless `--prune` is
   given, and never overwrites a real copy.
5. **Skill template**: YAML front matter with `name` and `description`;
   sections `## Purpose`, `## When to invoke`, `## Inputs`, `## Outputs`,
   `## Exact commands`, `## Required validations`,
   `## Human-approval boundaries`, `## Failure handling`. Commands use
   `--actor agent:<tool>`, never a fixed agent name.

## Consequences

- Claude Code and Codex discover the skills through documented, symlink-aware
  locations. Discovery in both was observed (S2 records in the tracker).
- **Unverified risk**: Gemini CLI and Antigravity document `.agents/skills`
  but not whether they follow symlinked skill folders. Until discovery is
  observed in one of them (S2-06), treat their support as unknown. If either
  ignores symlinks, the fallback is a generated copy guarded by the drift
  test, decided in a new ADR.
- Editing `skills/<name>/SKILL.md` updates every agent at once.
- Skills never run `workflow approve`, `workflow reopen`, `site confirm`,
  `interview consent` or `program reject`; they stop and hand the command to
  the human.
