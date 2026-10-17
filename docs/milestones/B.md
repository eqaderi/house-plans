# Milestone B: site ingestion

Date: 2026-10-17. Branch: `milestone-b` (from `main` at the Milestone A
merge). Not merged and not pushed; both need the owner's approval.

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
  water, access point, other feature, annotation, ignore.
- **Interpretation with explicit ambiguity** (`cad/site_extract.py`): each
  entity on a mapped layer is used (and keeps `source#handle (layer)`) or is
  listed with a reason. Several boundary candidates mean no boundary until
  `boundary_handle` names one. Elevation 0, varying-z "contours", height
  labels with no point, and conflicting spots are never used silently.
- **Units and CRS verification**: ingestion records only what the file
  declares (`$INSUNITS`, a GEODATA EPSG code) as `declared_in_source`.
  `house-ai site confirm` (human, interactive terminal, typed phrase)
  confirms drawing units, elevation units, EPSG or local-only, vertical
  datum or local benchmark, and the boundary. It re-derives the whole site
  from the immutable source. EPSG codes are validated with PROJ (projected,
  metre axes; vertical datums must be vertical CRSs), and a CRS whose area
  of use does not contain the site raises a blocking issue. The confirm
  command prints the site's lon/lat so a wrong UTM zone is visible.
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
  `site.svg` (parcel, dimensions, scale bar, north or "north not
  established", contours, spot heights, roads, buildings, trees, access,
  frontage, coordinate status, blockers and open issues),
  `cad-import.json` (provenance record).

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

`332 passed` (Python 3.13.3, macOS arm64), 0 failed, 0 skipped. The DWG
test ran against ODA File Converter 27.9. The CI install (version ranges,
fresh Homebrew Python 3.11 venv, pyproj 3.7.2) also passed in full, ruff
clean, 20 schemas up to date; the DWG test skips where ODA is absent.

| File | Tests |
|---|---|
| `test_cad.py` (new) | 20 |
| `test_geospatial.py` (new) | 31 |
| `test_site_pipeline.py` (new) | 41 |
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
`boundary_source_ref`, `terrain.surface`).

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
- A DXF GEODATA "local grid" transform (design point ≠ reference point, or
  rotated north) is not applied; it raises a blocking issue instead.
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

## Readiness for the real survey

`house-ai site inspect` is ready to run on the owner's files; see
`project-data/README.md`. The real files were not opened by the coding
agent: reading them would send their content to its model provider, which
needs the owner's explicit consent. The inspection is read-only and reports
what needs confirmation. Nothing about the real site is approved or
assumed.

## Next: Milestone C (program)

Not started. Interview engine, design brief, space program, adjacency
graph and the program gate, once the owner has approved Milestone B and
the real site.
