---
name: site-survey-review
description: Inspect and ingest survey CAD files (DWG/DXF), validate boundary and terrain, identify blockers, and prepare the site confirmation sheet for homeowner approval.
---

# Site Survey Review

## Purpose
Guide the agent through inspecting raw CAD survey files, ingesting survey entities into the project store with human layer mapping, computing boundary and terrain metrics, evaluating site blockers, and preparing the confirmation sheet for the human homeowner.

## When to invoke
- When a new project is created and survey files (DWG or DXF) need ingestion.
- When existing survey files need inspection or re-ingestion.
- When checking site status, boundary area, slope, relief, frontage, or terrain triangles.
- When preparing the site facts for the homeowner before the site approval gate.

## Inputs
- Project identifier (e.g. `my-house` or `<project-id>`).
- Raw CAD survey files (DWG or DXF) in `projects/<project-id>/surveys/`.
- Optional layer mapping YAML if custom CAD layers are used.

## Outputs
- Survey inspection report (`inspection.json`, `inspection.md`).
- Stored site artifact (`artifacts/site/site/v0001.json`).
- Stored CAD import artifact (`artifacts/cad_import/cad-import/v0001.json`).
- Visual SVG site map (`site.svg`).
- Site validation report (`site-report.md`) detailing boundary, terrain, frontage, relief, and blockers.
- Drafted CONFIRM-SITE sheet for homeowner review.

## Exact commands

1. **Inspect survey files (read-only, no project required):**
   ```bash
   .venv/bin/house-ai site inspect <survey-file-1> <survey-file-2> --out /tmp/inspection
   ```

2. **Ingest survey files into the project:**
   ```bash
   # Add survey CAD source document:
   .venv/bin/house-ai source add <project-id> <survey-cad-file> --actor agent:gemini

   # Ingest survey entities into site model:
   .venv/bin/house-ai site ingest <project-id> --source <source-path> --layers <path-to-layers.yaml> \
     --actor agent:gemini
   ```

3. **Assess site against workflow blockers:**
   ```bash
   # Move project to SITE_INGESTION if in NEW_PROJECT:
   .venv/bin/house-ai workflow transition <project-id> SITE_INGESTION --reason "ingesting survey" --actor agent:gemini

   # Run site assessment:
   .venv/bin/house-ai workflow assess-site <project-id> --id site --actor agent:gemini
   ```



4. **Generate site validation report and SVG:**
   ```bash
   .venv/bin/house-ai site report <project-id> --out projects/<project-id>/reviews/site-v1
   ```

5. **Verify project store integrity:**
   ```bash
   .venv/bin/house-ai project verify <project-id>
   ```

6. **Check project workflow status:**
   ```bash
   .venv/bin/house-ai project status <project-id> --json
   ```

## Required validations
- Verify survey file format and byte integrity.
- Check parcel area, boundary closure, and orientation.
- Validate Delaunay TIN terrain triangles; check for suspicious steep triangles or duplicated XY coordinates with mismatched Z elevations.
- Verify that coordinates remain strictly in SOURCE frame until confirmed by the owner.
- Confirm that CRS, datum, and unit are never guessed or inferred from coordinate magnitudes.
- Verify `project verify <project-id>` reports the store as intact with valid hash chain.

## Human-approval boundaries
- **NEVER** run `house-ai site confirm`: units, horizontal CRS, vertical datum, and parcel boundary must be confirmed by a human in an interactive terminal.
- **NEVER** run `house-ai workflow approve <project-id> site`: approving the site gate requires human authorization.
- The agent must summarize findings, list open site blockers, format the CONFIRM-SITE sheet, and ask the human to run:
  ```bash
  .venv/bin/house-ai site confirm <project-id> --units <m|ft> --epsg <EPSG> --vertical-datum <datum> --confirmer <name>
  .venv/bin/house-ai workflow approve <project-id> site --id site --version <v> --approver <name>
  ```


## Failure handling
- **ODA File Converter missing**: If DWG conversion is unavailable, ask the user to convert DWG to DXF or install ODA File Converter.
- **Ambiguous boundary or missing elevation**: Mark boundary as `inference_only` and record missing elevation data in `open_questions.yaml`. Keep the project in `SITE_NEEDS_VERIFICATION`.
- **Integrity failure**: If `project verify` reports tampering or hash mismatch, halt immediately and report the discrepancy.
