# project-data/

Private, owner-specific project stores live here. Everything in this folder
except this README is git-ignored.

```bash
.venv/bin/house-ai project init project-data/my-house --id my-house --name "My house" --actor human:<you>
.venv/bin/house-ai source add project-data/my-house ~/Downloads/survey.dwg --actor human:<you>
```

Never copy anything from here into `examples/`, `tests/` or `docs/`, and
never send it to an AI provider without explicit consent
(see `docs/AGENT_CONTRACT.md`, section 5).
