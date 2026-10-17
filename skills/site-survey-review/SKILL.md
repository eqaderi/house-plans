---
name: site-survey-review
description: Inspect and ingest survey CAD files (DWG/DXF), validate boundary and terrain, identify blockers, and prepare the site confirmation sheet for homeowner approval.
---

# Site Survey Review

Follow [docs/AGENT_CONTRACT.md](../../docs/AGENT_CONTRACT.md) (§5 private data,
§6 unknowns, §7 CAD and coordinates, §8 gates). In every command,
`agent:<tool>` is your own tool name: `claude-code`, `codex` or `gemini`.

## Purpose
Guide the agent through inspecting raw CAD survey files, ingesting survey entities into the project store with a human layer mapping, computing boundary and terrain metrics, evaluating site blockers, drafting the owner's questions and confirmation sheet, and requesting the human site gate.

## When to invoke
- When a new project is created and survey files (DWG or DXF) need ingestion.
- When existing survey files need inspection or re-ingestion.
- When checking site status, boundary area, slope, relief, frontage, or terrain triangles.
- When preparing the site facts for the homeowner before the site approval gate.

## Inputs
- Project folder or name under `projects/` (`<project>`).
- Raw CAD survey files (DWG or DXF).
- A layer mapping YAML naming which CAD layers hold the boundary, elevation points and contours.

## Outputs
- Survey inspection report (`inspection.json`, `inspection.md`).
- Stored source documents, `cad_import` and `site` artifacts.
- Site review package from `site report` (`site-report.md`, `site.svg`).
- Owner confirmation sheet `projects/<project>/reviews/CONFIRM-SITE.md`.
- An `approval_requested` event for the site gate.

## Exact commands

1. **Inspect survey files (read-only, no project required):**
   ```bash
   .venv/bin/house-ai site inspect <survey-file-1> [<survey-file-2> ...] --out <scratch-dir>/inspection
   ```

2. **Add each survey file as an immutable source, then ingest by source id:**
   ```bash
   .venv/bin/house-ai source add <project> <survey-cad-file> --classification <private|synthetic> \
     --actor agent:<tool>
   # prints: source <source-id>: <stored path> sha256 <hash>

   .venv/bin/house-ai site ingest <project> --source <source-id> [--source <source-id-2>] \
     --layers <layers.yaml> --actor agent:<tool>
   ```
   `--source` takes the id printed by `source add`, never a file path.

3. **Assess the site against the gate's blockers:**
   ```bash
   # From NEW_PROJECT only:
   .venv/bin/house-ai workflow transition <project> SITE_INGESTION --reason "ingesting survey" \
     --actor agent:<tool>

   .venv/bin/house-ai workflow assess-site <project> --id site --actor agent:<tool>
   ```

4. **Generate the site review package:**
   ```bash
   .venv/bin/house-ai site report <project> --out projects/<project>/reviews/site-v<N>
   ```

5. **Draft the owner's questions and `reviews/CONFIRM-SITE.md`.** Write it in
   plain language (and in the owner's language) with these sections:
   - what the owner already told us (verbatim, marked "not yet confirmed in the tool");
   - what the survey answers (area, relief, frontage, point counts), each with how it was obtained;
   - every open blocker from `assess-site` and `site report` (units, horizontal CRS, vertical datum, boundary), phrased as a question only the owner or surveyor can answer;
   - suspicious terrain findings (steep or sliver triangles, close point pairs), stated as measurements, never smoothed;
   - the exact commands the owner runs in their own terminal (see Human-approval boundaries).
   Never guess a CRS, UTM zone, hemisphere, datum or unit from coordinate magnitudes; list them as unknown.

6. **Request the human site gate review:**
   ```bash
   .venv/bin/house-ai workflow request-approval <project> site --id site --actor agent:<tool>
   ```

7. **Verify integrity and status:**
   ```bash
   .venv/bin/house-ai project verify <project>
   .venv/bin/house-ai project status <project> --json
   ```

## Required validations
- Survey file format and byte integrity (`site inspect`).
- Parcel area, boundary closure, and orientation.
- Terrain TIN: steep triangles, slivers, duplicated XY with different Z.
- Coordinates stay in the SOURCE frame until the owner confirms the CRS.
- CRS, datum, and unit are never inferred from coordinate magnitudes.
- `project verify <project>` reports the store intact.
- Real project values never go into `examples/`, `tests/` or public docs.

## Human-approval boundaries
- **NEVER** run `house-ai site confirm`: units, horizontal CRS, vertical datum, and parcel boundary are confirmed by a human in an interactive terminal.
- **NEVER** run `house-ai workflow approve <project> site`: the site gate is human-only.
- Stop after step 6 and ask the human to run, in their own terminal:
  ```bash
  .venv/bin/house-ai site confirm <project> --units <unit> --epsg <EPSG> --vertical-datum <datum> \
    --boundary-verified --confirmer <name>
  .venv/bin/house-ai workflow approve <project> site --id site --version <v> --approver <name>
  ```

## Failure handling
- **ODA File Converter missing**: if DWG conversion is unavailable, ask the user to convert DWG to DXF or install ODA File Converter.
- **Ambiguous boundary or missing elevation**: record it as unknown in the confirmation sheet and keep the project in `SITE_NEEDS_VERIFICATION`.
- **`site ingest` cannot find the source**: rerun `source add` and pass the printed id.
- **Integrity failure**: if `project verify` reports tampering or a hash mismatch, stop and report it.
