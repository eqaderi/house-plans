# ADR 0007: Handle overrides name their file; height labels cross-check points

Status: accepted (Milestone B corrections, 2026-10-17)

## Context

Verifying the Milestone B review commit (ec25922) and running the pipeline on
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
4. `site confirm` builds the new site before writing anything, so a failed
   confirmation writes no record.
5. Entity ids from long source ids use a 15-character head plus an 8-digit
   SHA-256 of the full id, and `Site` rejects duplicate ids.
6. Validation reports TIN triangles steeper than 100 % (45°) as a warning
   naming the points (a wall or kerb, or an elevation error), and the
   separation of road lines that run parallel. `site report` also writes
   `terrain.svg` (TIN by slope class, contours interpolated from the TIN and
   labelled as such) and a static `index.html` that tags each value as
   measured, calculated, interpretation, unknown or confirmed.

## Consequences

- Layer mappings for multi-file surveys are a little more verbose but cannot
  act on the wrong file.
- `cad_import` gained `height_label_checks` (schema regenerated).
- Nothing about units, CRS, datum or boundary status changed: these still
  need a human through `site confirm`.
