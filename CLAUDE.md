# CLAUDE.md

@docs/AGENT_CONTRACT.md

## Claude Code specifics

- Use the project venv: `.venv/bin/python`, `.venv/bin/house-ai`.
- Your Bash tool is not a TTY, so `house-ai workflow approve` refuses to
  run there (exit code 2). When a gate is ready, ask the user to run
  `.venv/bin/house-ai workflow approve <dir> <gate> --id <id> --approver <name>`
  in their own terminal window and type the confirmation phrase it shows.
- Pass `--actor agent:claude-code` on state-changing commands.
