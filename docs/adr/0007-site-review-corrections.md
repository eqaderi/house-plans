# ADR 0007: Handle overrides name their file; height labels cross-check points

Status: accepted (Milestone B corrections, 2026-10-17)

## Context

Checking the Milestone B review commit (ec25922) and running the pipeline on
a real survey delivered as two DWG files showed:

- DXF handles restart in every file. A bare handle in `boundary_handle` or
  `handle_roles` matched entities in every ingested file, so it silently
  reclassified unrelated entities in the other file.
- Surveyors draw a height label exactly at each surveyed point (a name line
  and a height line). ADR 0006 ignores every label, so the label could
  neither confirm nor dispute the point's z.
- Per-file `cad_import` records took the site's combined unit, so a file that
  declares millimetres could be recorded as metres after confirmation.

## Decision

1. With several survey files, every handle override must be written as
   `source_id#handle` (or `<id without src->#handle`). A bare handle is
   refused for multi-file ingestion; a prefix that names no ingested file is
   refused always. Single-file ingestion still accepts bare handles.
2. A label on a spot-elevation layer is linked to a point only when it sits at
   the same position (1 mm, no nearest-point search). If one of its lines is a
   number equal to the point's z to the label's precision, the pair is
   recorded as a `HeightLabelCheck` that agrees. If no line agrees, the point
   and label are left out and a blocking conflict is raised. A label at a
   point with no number is listed as a point name. Labels never become
   elevations.
3. A `cad_import` record states its own file's declared unit; the site's
   confirmed unit replaces it only if the file declares none or the same.
4. Entity ids from long source ids use a 15-character head plus an 8-digit
   SHA-256 of the full id, and `Site` rejects duplicate ids. Ids are saved in
   site records, so this scheme cannot change without renaming every entity.

## Consequences

- Layer mappings for multi-file surveys are a little more verbose but cannot
  act on the wrong file.
- `cad_import` gained `height_label_checks` (schema regenerated).
- Nothing about units, CRS, datum or boundary status changed: these still
  need a human through `site confirm`.
