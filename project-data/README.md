# project-data/

Private, owner-specific material lives here: real survey files and project
stores. Everything in this folder except this README is git-ignored.

Never copy anything from here into `examples/`, `tests/` or `docs/`, and
never send it to an AI provider without explicit consent
(see `docs/AGENT_CONTRACT.md`, section 5). An AI coding agent that reads
these files or the reports below sends their content to its provider.

## Your real survey

Keep the originals where they are and work on copies here:

```bash
mkdir -p project-data/surveys
cp ~/Downloads/<survey>.dwg project-data/surveys/        # cp leaves the original untouched

# 1. read-only inspection: formats, units, layers, CRS metadata, candidate
#    boundary, elevations, ambiguities, and the questions only you can answer
.venv/bin/house-ai site inspect project-data/surveys/* --out project-data/survey-inspection
```

Then write a layer mapping (copy `examples/surveys/synthetic/layers.yaml` to
`project-data/my-house-layers.yaml` and use your layer names), and:

```bash
.venv/bin/house-ai project init project-data/my-house --id my-house --name "My house" --actor human:<you>
.venv/bin/house-ai source add project-data/my-house project-data/surveys/<survey>.dwg --actor human:<you>
.venv/bin/house-ai workflow transition project-data/my-house SITE_INGESTION --reason "survey received" --actor human:<you>
# one --source per file, e.g. a boundary DWG and a separate heights DWG
.venv/bin/house-ai site ingest project-data/my-house --source <src-id> [--source <src-id-2>] --layers project-data/my-house-layers.yaml --actor human:<you>
.venv/bin/house-ai workflow assess-site project-data/my-house --id site --actor human:<you>
.venv/bin/house-ai crs utm-candidates <zone> <N|S>        # if you know the UTM zone but not the EPSG code
.venv/bin/house-ai site confirm project-data/my-house --confirmer <you> \
    --units m --elevation-units m --epsg <code> --vertical-datum "<name>" --boundary-verified
.venv/bin/house-ai site report project-data/my-house --id site --out project-data/my-house-report
```

`site confirm` and `workflow approve` only run in your own terminal and ask
you to type a confirmation phrase. DWG files need the ODA File Converter
(found at `/Applications/ODAFileConverter.app` or via `HOUSE_AI_ODA_CONVERTER`).
