# CLAUDE.md

@docs/AGENT_CONTRACT.md

## Claude Code specifics

- Use the project venv: `.venv/bin/python`, `.venv/bin/house-ai`.
- Your Bash tool is not a TTY, so `house-ai workflow approve` will refuse to
  run. When a gate is ready, tell the user to type
  `! .venv/bin/house-ai workflow approve <dir> <gate> --id <id> --approver <name>`
  so they approve it themselves.
- Pass `--actor agent:claude-code` on state-changing commands.
