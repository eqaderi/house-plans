# ADR 0006: Site ingestion pipeline, coordinate chain and CAD backends

Status: accepted (Milestone B, 2026-10-17)

## Context

Milestone B turns a land survey into a verified site model. Real surveys
arrive as DWG or DXF (sometimes PDF or point lists), in drawing units that
may be undeclared, with coordinates that look like UTM but declare nothing.
The spec forbids guessing the CRS from coordinate magnitudes and requires
human confirmation before anything downstream relies on the site.

Gemini's Milestone A review introduced `CadExtraction` (raw SOURCE-frame
entities), a `CadSiteExtractor` protocol taking `(source_unit, local_frame)`,
and `geospatial.base` helpers. Those are used as they are, with one change
below.

## Decision

1. **Separate steps with separate records.** A file is preserved under
   `source/` (`source add`); a CAD adapter extracts raw entities without
   interpreting them; a layer mapping written by a human assigns roles;
   `site_ingestion.interpret` converts to the local frame; terrain, frontage
   and issues are derived; a `cad_import` artifact (provenance and every
   ambiguous entity) and a `site` artifact are written.
2. **Declared versus confirmed.** Ingestion records only what the file
   declares (`$INSUNITS`, an EPSG code in a DXF GEODATA object) as
   `declared_in_source`; everything else stays `unknown`. The boundary from
   a CAD layer is an `inference`. `site confirm` is the only way to move a
   value to `user_confirmed`. It needs a human actor, and the CLI also needs
   an interactive terminal and a typed phrase, as gate approval does. A
   confirmation re-derives the whole site from the immutable source, so a
   corrected unit rescales every coordinate consistently.
3. **Coordinate chain.** SOURCE (drawing units) → GRID (× metres per unit,
   no offset) → LOCAL (rigid transform about an origin near the site),
   implemented by `domain.coordinates.SurveyTransform` and exactly
   invertible. The default local origin is the south-west-most boundary
   vertex at z = 0, recorded as an assumption. Elevation units are declared
   and confirmed separately from horizontal units.
4. **Protocol change.** `CadSiteExtractor` methods take a `SurveyTransform`
   instead of `(source_unit, local_frame)`, because elevations may use a
   different unit from x/y. `CadExtraction.provenance` became optional, since
   a read-only inspection has no store document.
5. **CRS work through pyproj/PROJ.** EPSG codes are validated (a horizontal
   CRS must be projected with metre axes; a vertical datum code must be a
   vertical CRS). Grid-to-true-north is computed numerically by projecting a
   short meridian step, not from a sign convention. A confirmed CRS whose
   area of use does not contain the site becomes a blocking issue. UTM zone
   lookup lists every datum for a zone and picks none.
6. **CAD backends.** DXF via ezdxf (`recover` mode, model space only). DWG
   via the ODA File Converter, run on a private ASCII-named copy in a
   temporary directory, with converter version and converted-file hash in
   provenance. QGIS's bundled GDAL 3.13 on the development machine has no
   DWG driver, so no GDAL adapter was added; `cad.dwg_oda.adapter_for` is
   the single place where a future backend would plug in.
7. **Terrain without invention.** A Delaunay TIN (shapely/GEOS) over spot
   heights and contour vertices; queries outside its hull return None.
   Elevation 0 counts as "not set" unless the mapping says otherwise. Two
   different elevations at one position are a blocking conflict and both
   are left out. scipy was not needed.
8. **Outputs are derived.** The validation report and the site SVG are
   computed from a site version and never stored as truth. Grid and true
   bearings and north arrows appear only once a human has confirmed the
   CRS. Example outputs are committed as snapshots and checked by a test.

## Consequences

- New runtime dependencies: `ezdxf` and `pyproj` (pyproj bundles PROJ).
- DWG support needs the ODA File Converter installed. Without it, DWG files
  are reported as unreadable instead of being guessed at; the DWG test
  skips.
- A wrong UTM zone with the same datum cannot be detected from coordinates,
  because the same easting is valid in every zone. Only the human can catch
  it, so the inspection and confirmation outputs show the resulting lon/lat.
- Frontage is geometric (boundary within 0.5 m of a drawn road), not legal
  access.
- Arcs in polylines are reduced to their vertices; areas and lengths are
  then chord approximations, and a warning says so.
