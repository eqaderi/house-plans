# ArchLang diagnostic experiment (S3-04)

Synthetic analytical fixtures only. `export_fixture.py` builds actual canonical
`HouseModel` instances, checks them with `check_model`, and exports a restricted
ArchLang view. `run_experiment.py` asserts independent compiler geometry and
semantics and exact seeded diagnostics. Neither changes project state.

From the repository root, with Node >=18 and npm available:

```bash
mkdir -p /tmp/house-ai-s3-archlang
npm install --prefix /tmp/house-ai-s3-archlang --ignore-scripts --no-audit --no-fund --save-exact @chanmeng666/archlang@1.43.1
.venv/bin/python examples/tool-evaluations/archlang/run_experiment.py
```

The npm environment is disposable; no npm package is installed into `.venv` or the
repository. To use another isolated installation, pass `--archlang /absolute/path/to/archlang`.
The runner rejects any version other than 1.43.1. Installation needs network; the
experiment itself needs no credentials, server or network calls.

`fixtures/` and `results/` are generated from the scripts, including four SVGs,
canonical JSON, raw diagnostic responses, and `results/summary.json`. Re-running
overwrites these evaluation artifacts only. These are ordinary synthetic examples,
not ProjectStore records. The three defect seeds remove a door, remove a bedroom
window, or place a sofa in the entrance approach; all four compile, but only the
baseline passes strict validation.

See [the decision note](../../../docs/research/s3-archlang.md) for the result,
upstream package identity, license, semantic losses, and proposed scope.
