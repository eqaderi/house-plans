# Milestone B: site ingestion

Date: 2026-10-17. Branch: `milestone-b` (from `main` at the Milestone A
merge). Pushed to `origin/milestone-b` with the owner's authorisation (latest push
2026-10-17, including `projects/my-house`); not merged into `main`, which needs the owner's approval.

## What works

Every output below comes from implemented logic running on the synthetic
survey, with numbers checked against known ground truth in the tests.

- **Format detection from bytes** (`cad/formats.py`): DWG with its release
  code, ASCII/binary DXF, PDF, LandXML/KML/XML, ZIP, SQLite/GeoPackage,
  shapefile, LAS, TIFF/PNG/JPEG, text. A `.dwg` name proves nothing.
- **Read-only inspection** (`house-ai site inspect`): for each file, the
  10 items the owner asked for: format, drawing units, layers (with
  name-based role *hints*), coordinate metadata (DXF GEODATA), CRS status,
  candidate parcel boundaries, elevation-bearing entities per layer,
  unknown and ambiguous items, provenance, and a checklist of what only the
  owner can confirm. The file is hashed before and after; DWG is read
  through a private temporary copy.
- **Raw CAD extraction** (`cad/dxf_ezdxf.py`, `cad/dwg_oda.py`): ezdxf for
  DXF; DWG through the ODA File Converter. POINT, TEXT, MTEXT, INSERT,
  CIRCLE, LINE, LWPOLYLINE and 2D/3D POLYLINE are kept in SOURCE
  coordinates with their handles; other entity types are counted as
  unsupported. Empty or truncated drawings are flagged.
- **Layer roles** (`cad/layers.py`): only from a human-written mapping
  (`examples/surveys/synthetic/layers.yaml`). Roles: boundary, contour,
  spot elevation, road, easement, existing structure, utility, tree,
  water, access point, other feature, annotation, ignore. Drawings that put
  several kinds of geometry on one layer (e.g. layer `"0"`) can override
  individual entities with `handle_roles` (`handle` or `source_id#handle`)
  and `boundary_handle`.
- **Interpretation with explicit ambiguity** (`cad/site_extract.py`): each
  entity on a mapped layer is used (and keeps `source#handle (layer)`) or is
  listed with a reason. Several boundary candidates mean no boundary until
  `boundary_handle` names one (with or without `source_id#`). Elevation 0,
  varying-z "contours", single- or multi-line height labels with no point,
  points/inserts on area or linear feature layers, and conflicting spots
  are never used silently.
- **Units and CRS verification**: ingestion records only what the file
  declares (`$INSUNITS`, a GEODATA EPSG code) as `declared_in_source`.
  `house-ai site confirm` (human, interactive terminal, typed phrase)
  confirms drawing units, elevation units, EPSG or local-only, vertical
  datum or local benchmark, and the boundary. It re-derives the whole site
  and updates the `cad_import` provenance records from the immutable source.
  EPSG codes are validated with PROJ (projected, metre axes; vertical
  datums must be vertical CRSs), and a CRS whose area of use does not
  contain the site raises a blocking issue. The confirm command prints the
  site's lon/lat so a wrong UTM zone is visible.
- **Coordinate chain** (`domain/coordinates.py: SurveyTransform`): SOURCE →
  GRID (unit scale) → LOCAL (origin at the south-west boundary vertex,
  optional rotation), exactly invertible; grid-to-true-north computed
  numerically with pyproj once the CRS is confirmed; `crs utm-candidates`
  lists every datum's EPSG code for a zone without choosing one.
- **Site model, boundary and terrain**: normalised CCW parcel polygon;
  area, perimeter, edge lengths, local, grid and true bearings (the last
  two only with a confirmed CRS), oriented extent; Delaunay TIN from spot
  heights and contour vertices with no extrapolation; slope, contour
  interval, coverage of the parcel; crossing contours and elevation
  conflicts block; frontage derived where the boundary runs along a road.
- **Several survey files per site**: `site ingest --source A --source B`
  (e.g. the boundary in one DWG and the heights in another). Each file gets
  its own `cad_import` record, ids are namespaced per file because DXF
  handles restart in every file, a boundary may come from one file only,
  and the files' declarations must agree. A test splits the synthetic
  survey into two files and gets the same site.
- **Workflow**: `workflow assess-site` puts an unconfirmed site in
  `SITE_NEEDS_VERIFICATION`; elevation units are now a site-gate blocker
  when the site has elevations; only a human can confirm site facts or
  approve the gate.
- **Outputs** (`house-ai site report`): `site.json` (the canonical site
  version), `site-report.json` and `.md` (validation report),
  `site.svg` (parcel, holes, buildable envelope, dimensions, scale bar,
  north or "north not established", contours, spot heights, roads,
  buildings, easements, utilities, water, trees, access, frontage,
  coordinate status, blockers and open issues), `cad-import.json` (plus
  per-file `cad-<source_id>.json` when multiple files were ingested).

## Commands to reproduce

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests examples
.venv/bin/house-ai schemas check

# synthetic survey, end to end
S=examples/surveys/synthetic
P=project-data/site-demo
.venv/bin/house-ai site inspect $S/survey.dxf --layers $S/layers.yaml
.venv/bin/house-ai project init $P --id site-demo --name "Synthetic survey" --classification synthetic --actor human:<you>
.venv/bin/house-ai source add $P $S/survey.dxf --classification synthetic --actor human:<you>
.venv/bin/house-ai workflow transition $P SITE_INGESTION --reason "survey received" --actor human:<you>
.venv/bin/house-ai site ingest $P --source src-survey --layers $S/layers.yaml --actor human:<you>
.venv/bin/house-ai workflow assess-site $P --id site --actor human:<you>      # -> SITE_NEEDS_VERIFICATION
.venv/bin/house-ai site report $P --id site --out $P-report-v1               # unconfirmed outputs
.venv/bin/house-ai site confirm $P --confirmer <you> --units m --elevation-units m \
    --epsg 25832 --vertical-datum DHHN2016 --vertical-epsg 7837 --boundary-verified   # type: confirm site site
.venv/bin/house-ai workflow transition $P SITE_INGESTION --reason "site facts confirmed" --actor human:<you>
.venv/bin/house-ai workflow assess-site $P --id site --actor human:<you>      # no blockers
.venv/bin/house-ai site report $P --id site --out $P-report-v2
.venv/bin/house-ai workflow request-approval $P site --id site --actor human:<you>
.venv/bin/house-ai workflow approve $P site --id site --approver <you>       # type: approve site site v2
.venv/bin/house-ai project verify $P

# regenerate the committed example outputs
.venv/bin/python examples/surveys/synthetic/make_expected.py
```

Committed example outputs: `examples/surveys/synthetic/expected/`
(`inspection.md`; `unconfirmed/` and `confirmed/` each with
`site-report.md` and `site.svg`). The confirmed set comes from a scripted
confirmation by the synthetic actor `human:example-owner`, as in the tests.

## Results on the synthetic survey (ground truth in `make_survey.py`)

| Quantity | Expected | Measured |
|---|---|---|
| Parcel area | 1400 m² | 1400.00 m² |
| Perimeter | 40 + 30 + √1000 + √200 + 30 = 145.765 m | 145.765 m |
| Edge lengths | 40, 30, 31.623, 14.142, 30 m | same |
| Local origin (grid) | E 500100, N 5400200 | same |
| Terrain | plane z = 100 + 0.05x + 0.1y | TIN equals the plane to 1e-9 m; slope 11.18 % |
| Contours | 101, 102, 103, 104 m | 4 contours, interval 1 m |
| Spot heights | 8 valid | 8 (2 ambiguous excluded) |
| Frontage | 40 m along AB | 40.000 m |
| Ambiguous entities | 6 planted | 6, each with its reason |
| Grid to true north (EPSG:25832) | −Δλ·sin φ ≈ −0.001° | −0.00103°, equal to −(PROJ meridian convergence) |
| Same survey in mm | identical site | identical to 1e-9 m |

## Test results

`367 passed` on Python 3.13.3 (the locked versions in `requirements-lock.txt`),
0 failed, 0 skipped, after the project-folder change (2026-10-17). Before it:
`359 passed` on Python 3.13.3 and on Python 3.11.12 (macOS arm64) after the
corrections below. The lock pins numpy 2.5.4 and pyproj 3.8.0, which have no
Python 3.11 builds, so the 3.11 run used numpy 2.4.6 and pyproj 3.7.2; the
lock does not install on 3.11 although `requires-python` says `>=3.11` (open
item for the owner: raise the floor or keep a 3.11 lock). The same applies
to the earlier 3.11 claim at ec25922. The DWG test ran against ODA File
Converter 27.9. `ruff check src tests examples`: all checks passed.
`house-ai schemas check`: 21 schemas up to date (new: `owner_statements`). Before the corrections
(at ec25922): 344 passed.

| File | Tests |
|---|---|
| `test_cad.py` (new) | 23 |
| `test_geospatial.py` (new) | 32 |
| `test_site_pipeline.py` (new) | 49 |
| `test_site_review_fixes.py` (new) | 17 |
| `test_projects.py` (new) | 5 |
| `test_units_coordinates.py` | 37 |
| `test_schemas.py` | 32 |
| `test_workflow.py` | 40 |
| `test_domain_rules.py` | 34 |
| `test_integrity.py` | 28 |
| `test_storage.py` | 24 |
| `test_cli.py` | 14 |
| `test_geometry.py` | 12 |
| `test_providers_agents.py` | 10 |
| `test_agent_instructions.py` | 8 |
| `test_golden.py` | 1 |

All Milestone A tests pass unchanged. The golden bungalow plan was
regenerated with its own generator because it pins the site's content
hash, and the site schema gained fields (`elevation_units`,
`boundary_source_ref`, `terrain.surface`, and `handle_roles` on
`cad_import`).

## Dependencies

Added: `ezdxf` 1.4.5 (DXF) and `pyproj` 3.8.0 (bundles PROJ 9.8.1), plus
their dependencies fonttools, pyparsing and certifi. Reused: the project
venv (Python 3.13.3, shapely 2.2.0, numpy), and the installed ODA File
Converter 27.9 for DWG. Not needed: scipy (shapely's Delaunay suffices) and
GDAL. QGIS 4.2.3 bundles GDAL 3.13.3, but it has no DWG driver.

## Known limitations

- A wrong UTM zone with the right datum cannot be detected: the same
  easting is valid in every zone. Only the human can catch it from the
  lon/lat that `site confirm` and the report print.
- A DXF GEODATA georeference transform (design point ≠ reference point,
  rotated north, or geographic coordinate type) is not applied; it raises a
  blocking issue instead.
- Several survey files form one site only if they share one unit and one
  CRS. Files that declare different units or EPSG codes raise a blocking
  issue; converting one of them is up to the owner or surveyor.
- Arcs (polyline bulges) are reduced to their vertices; areas and lengths
  are chord approximations, with a warning.
- Block attributes (e.g. an `ELEV` tag) are not read as elevations; only
  real z values are. A spot block at z = 0 is listed as ambiguous.
- Frontage is geometric (boundary within 0.5 m of a drawn road), not
  legal access. North for a local-only survey stays unknown.
- A TIN over contour vertices alone can contain flat triangles across a
  ridge or valley; spot heights reduce this.
- PDF, LandXML, point lists and GIS formats are detected but not read.
- The confirmation is protected like gate approval (interactive terminal
  and typed phrase). It stops accidental confirmation by an agent; it is
  not a security boundary.

## Independent verification of ec25922 (Claude Code)

Each finding below was reproduced, given a failing test in
`tests/test_site_review_fixes.py`, then fixed (ADR 0007).

| Severity | Defect (at ec25922) | Fix |
|---|---|---|
| major | `site confirm` wrote new `cad_import` versions before the site could fail (e.g. a mistyped `--accept-issue`), leaving a permanent false confirmation record | the site is built first; nothing is written on failure |
| major | a bare `boundary_handle` / `handle_roles` key matched entities in every file of a multi-file survey (handles restart per file) | bare handles refused for several files; unknown `source_id#` prefixes refused |
| major | per-file `cad_import` records took the combined unit, so a millimetre file could be recorded as metres | each record states its own file's declaration |
| major | ids from long, similar source ids collided (17 spots, 9 ids) and the store accepted it | readable head plus SHA-256 digest; `Site` rejects duplicate ids |
| minor | the `point` keyword hinted `TREE_POINTS` and `UTILITY_POINT` as spot layers | generic keyword checked last; `access` hint added |
| minor | `site inspect` ignored `source_id#handle` keys | inspection uses the id `source add` would give |
| minor | prefix typo in `boundary_handle` gave no diagnostic | refused with the list of ingested files |
| minor | DWG inspection showed the converted DXF's `$ACADVER` | shows the DWG release |
| privacy | `tests/test_cad.py` and a docstring contained a real benchmark label and real elevations from the owner's survey | replaced with synthetic values; the values remain in the pushed history of ec25922 |

| minor | `has_numeric_elevation_label` / `numeric_label_values` missed inline units/point names (`1664.0 m`, `Pt1 101.25`) and counted integer point IDs after a point-header line (`Pt\n12`) as heights | inline units and point prefixes accepted; bare integer lines after point-header lines ignored |
| minor | `_boundary_candidates` in survey inspection ignored `handle_roles` / `boundary_handle` and matched layer names case-sensitively | uses `matches_boundary_handle` and `role_of_entity` case-insensitively |
| minor | point features of kind `utility`, `water`, `other` in `site.svg` used muted grey with no `<title>` | uses `_FEATURE_COLOUR[f.kind]` and `<title>{id} ({kind})</title>` |
| minor | `combined_frame` excluded a file whose GEODATA EPSG was rejected from the "files disagree on CRS" check | includes `inspection.declared_epsg` in multi-file CRS comparison |

Found on the real survey and added: height labels drawn at a point are
cross-checked against its z (`HeightLabelCheck`); steep TIN triangles
(> 100 %) and parallel road-line separation are reported; `site report`
writes `terrain.svg` and `index.html`.

## Personal-first project folders (2026-10-17, ADR 0009)

The owner decided the software is personal-first and authorised committing
their real project to this private repository.

- **Layout.** `projects/<name>/` is the `ProjectStore` root plus `surveys/`,
  `site/`, `reviews/` and `design/`. `house-ai project new <name>` creates one
  (with a README saying what it needs); `project list` lists them; every
  command accepts the name (`house-ai project status my-house`). `site
  report` defaults to `<project>/reviews/<site>-v<N>/`.
- **Migration.** The store `project-data/my-house` was moved unchanged to
  `projects/my-house` (relative stored paths, so `project verify` was intact
  before and after: 8 events, 5 artifact versions). `seperated.dwg` and
  `elevation.dwg` were copied into `surveys/` (SHA-256 27624ba1… and
  9689880c…, identical to `source/`; git stores each once). The layer mapping
  is `site/layers.yaml`; the inspection and the review package were
  regenerated into `site/inspection/` and `reviews/site-v1/` from the same
  site v1. `final.dwg` is not restored.
- **Owner statements** (`owner_statements`, `house-ai statement add|list`):
  the owner's words, verbatim, with who said it, the channel and the recorder.
  They confirm nothing. Recorded for `my-house` by agent:claude-code from the
  owner's chat of 2026-10-17: UTM coordinates; elevations in metres above sea
  level; the 12–12.5 m drop is correct; the land is genuinely steep; UTM zone,
  horizontal datum/EPSG and vertical datum still unknown.
- **Steep triangles itemised.** The report and review page list every TIN
  triangle over 100 % with its slope, area, smallest angle, steepest edge
  (distance, Δz, rise), sources, whether it lies in the parcel, and measured
  traits (`sliver`, `no steep edge`, `on survey edge`, `close pair`,
  `mixes sources`, `outside parcel`). Nothing is smoothed or removed.

## The owner's real survey

`projects/my-house` is in `SITE_NEEDS_VERIFICATION`; nothing is approved.
Blockers: drawing units and elevation units (declared metres, not yet
confirmed by the owner in the tool), horizontal CRS (UTM zone, hemisphere and
datum unknown), vertical datum, and the parcel boundary. The owner's sheet is
`projects/my-house/reviews/CONFIRM-SITE.md`.

The five steep triangles: two share one pair of points 0.72 m apart with
0.89 m height difference (124 % rise; one point from each file, near the
parcel's north-west corner in the drawing frame), one of them inside the
parcel. The other three are slivers outside the parcel (smallest angle
0.3°–1.7°) whose edges rise only 7 %, 12 % and 34 %: their steepness comes from
their shape. Readings of either are inferences for the surveyor.

## Next: Milestone C (program)

Not started. Interview engine, design brief, space program, adjacency
graph and the program gate, once the owner has approved Milestone B and
the real site.
