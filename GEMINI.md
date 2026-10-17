# GEMINI.md

@docs/AGENT_CONTRACT.md

## Gemini CLI specifics

- Use the project venv: `.venv/bin/python`, `.venv/bin/house-ai`.
- Shell commands you run are non-interactive, so `house-ai workflow approve`
  will refuse. Ask the user to run it in their own terminal.
- Pass `--actor agent:gemini-cli` on state-changing commands.
