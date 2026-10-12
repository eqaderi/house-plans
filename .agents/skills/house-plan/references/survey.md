# Survey, DWG and site

## Rules

- Originals live in `sources/` and are never modified, renamed or re-saved.
  Record each one's SHA-256 in `sources/MANIFEST.sha256` when it arrives:
  `shasum -a 256 sources/<file> >> sources/MANIFEST.sha256`.
- Every derived file is reproducible from a command written in
  `derived/README.md`.
- Never estimate a coordinate or level from an image. Measure it from the
  DXF with ezdxf, or from survey points.
- Real measured XYZ beats any interpolation. Interpolated terrain is labelled
  as such, with the method and its source points.

## DWG to DXF

```sh
bin/hp dwg2dxf sources/<file>.dwg derived/survey/
```

It copies the DWG to a scratch folder, runs the ODA File Converter on the
copy (DXF 2018), and refuses to finish if the original's checksum changed. On
macOS the ODA window may flash; that is normal.

## Reading the survey DXF

In `~/.venvs/architecture-ai/bin/python`:

```python
import ezdxf
doc = ezdxf.readfile("derived/survey/<file>.dxf")
print(doc.header.get("$INSUNITS"), doc.header.get("$EXTMIN"), doc.header.get("$EXTMAX"))
msp = doc.modelspace()
for layer in sorted({e.dxf.layer for e in msp}):
    print(layer, len(msp.query(f'*[layer=="{layer}"]')))
```

1. **Units first.** `$INSUNITS` (4 = mm, 6 = m) and sanity-check one known
   distance (a plot side from the deed, a building edge). Iranian surveys are
   usually in metres.
2. **Inventory the layers** and write what each holds in `derived/README.md`:
   boundary, buildings, spot heights (POINT or TEXT/INSERT with Z), contours,
   breaklines, trees, utilities.
3. **Coordinates.** Iranian surveys use UTM on WGS84 (zones 38N–41N; Tehran
   is zone 39N, EPSG:32639) or a local grid. Confirm the zone from the
   coordinates' magnitude and the drawing notes, never assume. Use pyproj for
   conversions and QGIS for maps.
4. **Local origin.** Pick a point near the building (a plot corner), and
   record its survey easting, northing and Z in `docs/decisions.md`. Spec
   coordinates are millimetres from that origin; `project.datum.survey_z_mm`
   holds the Z of ±0.00.
5. **Boundary and setbacks** from the boundary layer and the municipal
   conditions, as shapely polygons. Check the footprint against them.

## Terrain and sections

- QGIS processing (`qgis_process`) for TIN/DEM from spot heights, contours,
  slope and aspect. Write the exact algorithm and parameters into
  `derived/README.md`.
- For building cross-sections on a slope, sample the terrain along the
  section line at the survey's resolution; do not smooth. The sibling project
  `house-profile-slope` shows the expected rigor: frozen survey payload,
  round-trip tests, and every figure computed from full-precision data.

## When the plan comes from an existing drawing

Measure walls from the DXF entities, convert to the spec's local
millimetres, and keep a table in `docs/trace.md` of every wall: source entity
handle, source coordinates, spec coordinates. List every conflict (walls that
don't meet, dimensions that disagree with geometry, inconsistent thicknesses)
for the user to resolve. Never "fix" a source silently.
