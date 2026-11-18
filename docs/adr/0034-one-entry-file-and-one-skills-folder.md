# ADR 0034: One entry file and one skills folder for every coding agent

Status: proposed (requested by the owner 2026-11-18).

Revises [ADR 0005](0005-shared-coding-agent-instructions.md) (entry files) and
[ADR 0015](0015-agent-skills-canonical-location-and-discovery.md) (skill layout).

## Context

ADR 0005 kept the rules in `docs/AGENT_CONTRACT.md` behind three hand-written
entry files. Each repeated the same three "tool specifics" (project venv,
`workflow approve` refusing in a non-TTY shell, `--actor agent:<tool>`), all
of which the contract already stated or should state.

ADR 0015 kept skills in `skills/<name>/` with one symlink per skill in
`.claude/skills/` and `.agents/skills/`, created by `tools/sync_skills.py`.
Skills lived in three visible places; a new skill appeared to an agent only
after someone ran the sync tool. Gemini CLI's handling of symlinked skill
folders was never checked.

Content was also repeated across layers: contract §9 and §9b restated the
`architectural-programming` and `generate-plan-options` skills step by step;
`docs/AGENT_WORKFLOWS.md` restated both again, with a hardcoded
`agent:claude-code`, a "combine is not supported yet" line that `plan combine`
had made stale, and a "`my-house` today" snapshot of `project status`. Every
skill opened by pointing at the contract, which every tool already loads.

## Decision

1. **One entry file.** `AGENTS.md` is the only hand-written entry file.
   `CLAUDE.md` and `GEMINI.md` are relative symlinks to it, so an edit
   reaches every tool. It imports the contract with `@./docs/AGENT_CONTRACT.md`
   (the form Gemini CLI documents; Claude Code resolves the same relative path)
   and tells Codex, which does not expand imports, to read the contract.
   It holds no tool-specific rules: the venv and the approval hand-off are
   in the contract (§8, §10), and §4 already names each tool's `--actor`.
2. **`docs/AGENT_CONTRACT.md` stays the only home of rules**, as
   `MASTER_SPEC.md` requires. Section numbers are unchanged, so earlier
   "AGENT_CONTRACT §N" citations stay valid. §9 and §9b point to the skills
   and keep only the guardrails that must hold even when no skill is loaded.
3. **One skills folder.** `.agents/skills/<name>/SKILL.md` holds the only copy
   of each skill as real folders; Codex, Gemini CLI and Antigravity read it
   natively. `.claude/skills` is one relative symlink to `../.agents/skills`,
   so a new skill reaches Claude Code with no extra step.
   `tools/sync_skills.py` and `skills/README.md` are removed; the template
   stays enforced by `tests/test_skills.py`.
4. `docs/AGENT_WORKFLOWS.md` is removed; its one live addition (owner phrases
   that map to `plan generate --seed` and `plan combine`) moved into the
   `generate-plan-options` skill.

## Consequences

- One edit to `AGENTS.md`, the contract, or a skill reaches every tool.
- The contract shrank from 11,988 to under 9,000 characters (ISS-17).
- Gemini CLI and Antigravity no longer depend on following symlinked skill
  folders. Claude Code now depends on following a symlinked skills
  directory instead of symlinked skill entries; confirm with `/skills` in a
  new session. If it does not, the fallback is per-skill links in
  `.claude/skills`, as ADR 0015 had.
- Antigravity reads both `AGENTS.md` and `GEMINI.md`; both are now the same
  file, so it may load the contract twice. Not observed yet.
- Symlinked entry files need `core.symlinks` on Windows checkouts, as the
  skill links already did.
