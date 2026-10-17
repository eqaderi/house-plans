# AGENTS.md

Before doing anything in this repository, read
[docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md) in full and follow it. It
is the one set of project rules for every coding agent (Claude Code, Codex,
Gemini); this file does not repeat them. `docs/MASTER_SPEC.md` is the
product specification.

Codex does not expand links or imports in this file, so open the contract
yourself at the start of every session.

Tool specifics (Codex, and any agent without its own entry file):

- Use the project venv: `.venv/bin/python`, `.venv/bin/house-ai`.
- Shell commands are non-interactive, so `house-ai workflow approve`
  refuses to run (exit code 2). Ask the human to run it in their terminal.
- Pass `--actor agent:codex` (or `agent:<your-tool>`) on state-changing
  commands.
