# ADR 0005: One shared instruction file for all coding agents

Status: accepted (Milestone A handoff, 2026-10-17)

Revised by [ADR 0015](0015-agent-skills-canonical-location-and-discovery.md)
(accepted): its skills clause, "No `.claude/`, `.agents/` or `.gemini/` rules or
skills directories are added", is replaced for skills only.

## Context

Three coding agents work on this repository: Claude Code (primary
developer), OpenAI Codex (independent reviewer and debugger) and Google
Gemini through Gemini CLI or Antigravity (reviewer and second developer).
Each tool looks for its own entry file. Copying the project rules into
three files would let them drift apart.

These coding agents are not the runtime architectural roles in
`agents/roles.yaml`. Those roles are part of the product; the rules here
govern the tools that build it.

## Decision

`docs/AGENT_CONTRACT.md` is the only place where engineering rules are
written. `docs/MASTER_SPEC.md` stays the product specification. The entry
files contain only a pointer to the contract and tool-specific details:

| Tool | Entry file it reads | How the contract is loaded |
|---|---|---|
| Claude Code | `CLAUDE.md` (project root) | `@docs/AGENT_CONTRACT.md` import, expanded into context at session start |
| Codex CLI | `AGENTS.md` (from the git root down to the working directory) | No import mechanism. `AGENTS.md` tells Codex to read the contract before doing anything |
| Gemini CLI | `GEMINI.md` (hierarchical) | `@./docs/AGENT_CONTRACT.md` import (memory import processor) |
| Antigravity | `GEMINI.md` and `AGENTS.md` at the workspace root | Same `@./` import in `GEMINI.md`; `AGENTS.md` repeats the pointer |

No `.claude/`, `.agents/` or `.gemini/` rules or skills directories are
added. Skills will be added when a recurring task justifies one.

## Checks (2026-10-17)

- **Claude Code 2.1.302:** observed in a live session. The contract text
  appeared in the model context under `CLAUDE.md`'s import.
- **Codex CLI 0.146.0:** checked locally, with no model call, using
  `codex debug prompt-input "hi"` from the repository root. The rendered
  prompt contains `AGENTS.md` verbatim but none of the contract's text, so
  links are not followed. Hence the explicit "read the contract" sentence.
- **Gemini CLI / Antigravity:** checked against the vendor documentation
  only (Gemini CLI `docs/reference/memport.md`, Antigravity "Rules" and
  "Migrating from Gemini CLI"). Gemini CLI is not installed on the
  development machine. The documented import form is `@./path`, so
  `GEMINI.md` uses `@./docs/AGENT_CONTRACT.md`. To confirm, run
  `/memory show` in Gemini CLI from the repository root. Antigravity limits
  a rules file to 12,000 characters, so the contract is kept below that.

`tests/test_agent_instructions.py` checks that each entry file points at
the contract, stays small, and that the contract stays under 12,000
characters with working relative links.

## Consequences

- A rule changes in one place. The entry files change only when a tool's
  loading mechanism or a tool-specific detail changes.
- Codex depends on obeying a sentence rather than an import. Reviews by
  Codex should start by confirming it read the contract.
- The contract links to ARCHITECTURE, DOMAIN_MODEL, ADRs and milestone
  reports instead of repeating them, which keeps it under the size limit.
