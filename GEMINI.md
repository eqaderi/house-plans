# GEMINI.md

@./docs/AGENT_CONTRACT.md

## Gemini specifics (Gemini CLI and Antigravity)

- The import above loads the shared contract. If your tool shows it was not
  loaded (`/memory show` in Gemini CLI), read `docs/AGENT_CONTRACT.md`
  before working.
- Use the project venv: `.venv/bin/python`, `.venv/bin/house-ai`.
- Shell commands you run are non-interactive, so `house-ai workflow approve`
  will refuse. Ask the user to run it in their own terminal.
- Pass `--actor agent:gemini` on state-changing commands.
