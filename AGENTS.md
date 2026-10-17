# AGENTS.md

Read and follow [docs/AGENT_CONTRACT.md](docs/AGENT_CONTRACT.md). It is the
canonical instruction set for every agent in this repository.
`docs/MASTER_SPEC.md` is the product specification.

Setup and tests:

```bash
python3.13 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

Never approve a workflow gate. Ask the human to run
`house-ai workflow approve ...` in their own terminal.
