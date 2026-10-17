# Survey inspection (read-only)

Read-only inspection. Values are what the files declare; nothing here is confirmed, and coordinate magnitudes are not evidence of a CRS or unit.

## seperated.dwg

### 1. File format
- dwg AC1032 (file starts with 'AC1032')
- 17602 bytes, sha256 `27624ba14003e3d898143a9d86985d50d3d7098db0a45b94ae2dd999571519ed`; unchanged after inspection: yes

### 2. Drawing units
- $INSUNITS = 6 (metres); status: declared in source as m; needs your confirmation
- Header: {'$ACADVER': 'AC1032', '$INSUNITS': 6, '$MEASUREMENT': 0, '$LUNITS': 2, '$AUNITS': 0, '$ANGBASE': 0.0, '$ANGDIR': 0}

### 3. CAD layers

| Layer | Entities | Types | Mapped role | Suggested role (hint) |
|---|---|---|---|---|
| 0 | 15 | {'LWPOLYLINE': 3, 'MTEXT': 6, 'POINT': 6} | - | - |
| Defpoints | 0 | {} | - | - |

### 4. Coordinate metadata
- GEODATA: none
- Declared EPSG: none
- Extents (source units): (623799.692, 3870450.842897095, 623842.615, 3870490.101000001)

### 5. CRS verification status
- unknown: the file declares no coordinate reference system
- Coordinate magnitudes are not evidence of a CRS, zone or unit.

### 6. Candidate parcel boundary
- Basis: no boundary layer identified: the largest closed polylines in the drawing
- D7 on '0': 4 vertices, area 600.004 unit², perimeter 107.140 (= 600.00 m² if the declared unit is right)

### 7. Contours and spot elevations (by layer)

| Layer | Points with z | Points z=0 | Constant-z lines | z=0 lines | Varying-z lines | Numeric labels | z range |
|---|---|---|---|---|---|---|---|
| 0 | 6 | 0 | 3 | 0 | 0 | 0 | 1665.378 to 1680.071 |

### 8. Unknown or ambiguous information
- Unsupported entities: none

### 9. Provenance
- Path: projects/my-house/surveys/seperated.dwg
- Parser: ezdxf 1.4.5; converted with ODA File Converter 27.9.0.0 (DXF sha256 8bb53e323311fd12668aa1381a02fb440cb97fa58a3f56851cd11409e4f7f61d)

### 10. Needs your confirmation
- [ ] Confirm the drawing unit: the file declares m.
- [ ] Confirm the elevation unit (DXF z values use the drawing unit unless the surveyor says otherwise).
- [ ] State the horizontal CRS as an EPSG code (for UTM: zone, hemisphere and datum, e.g. ETRS89 / UTM 32N = EPSG:25832), or confirm the survey is local-only.
- [ ] State the vertical datum of the elevations (e.g. a national height system) or the local benchmark they are relative to.
- [ ] Write a layer mapping (layer -> role); suggested roles in this report are hints from layer names only.
- [ ] Confirm that polyline D7 on layer '0' is the legal parcel boundary.

## elevation.dwg

### 1. File format
- dwg AC1021 (file starts with 'AC1021')
- 30048 bytes, sha256 `9689880c47d9d0780089c5d4077f9396f5c29a2feeb298fafb86840bbae02f02`; unchanged after inspection: yes

### 2. Drawing units
- $INSUNITS = 6 (metres); status: declared in source as m; needs your confirmation
- Header: {'$ACADVER': 'AC1021', '$INSUNITS': 6, '$MEASUREMENT': 0, '$LUNITS': 2, '$AUNITS': 0, '$ANGBASE': 0.0, '$ANGDIR': 0}

### 3. CAD layers

| Layer | Entities | Types | Mapped role | Suggested role (hint) |
|---|---|---|---|---|
| 0 | 42 | {'MTEXT': 21, 'POINT': 21} | - | - |
| Defpoints | 0 | {} | - | - |

### 4. Coordinate metadata
- GEODATA: none
- Declared EPSG: none
- Extents (source units): (623803.322, 3870456.072, 623841.289, 3870496.094)

### 5. CRS verification status
- unknown: the file declares no coordinate reference system
- Coordinate magnitudes are not evidence of a CRS, zone or unit.

### 6. Candidate parcel boundary
- Basis: no boundary layer identified: the largest closed polylines in the drawing
- none found

### 7. Contours and spot elevations (by layer)

| Layer | Points with z | Points z=0 | Constant-z lines | z=0 lines | Varying-z lines | Numeric labels | z range |
|---|---|---|---|---|---|---|---|
| 0 | 21 | 0 | 0 | 0 | 0 | 21 | 1664.884 to 1677.805 |

### 8. Unknown or ambiguous information
- Unsupported entities: none

### 9. Provenance
- Path: projects/my-house/surveys/elevation.dwg
- Parser: ezdxf 1.4.5; converted with ODA File Converter 27.9.0.0 (DXF sha256 92f927e9c73289ae7c6d00b347200f033ceaa865faa8d0e60803fa17745ce5fb)

### 10. Needs your confirmation
- [ ] Confirm the drawing unit: the file declares m.
- [ ] Confirm the elevation unit (DXF z values use the drawing unit unless the surveyor says otherwise).
- [ ] State the horizontal CRS as an EPSG code (for UTM: zone, hemisphere and datum, e.g. ETRS89 / UTM 32N = EPSG:25832), or confirm the survey is local-only.
- [ ] State the vertical datum of the elevations (e.g. a national height system) or the local benchmark they are relative to.
- [ ] Write a layer mapping (layer -> role); suggested roles in this report are hints from layer names only.
- [ ] Identify the parcel boundary: 0 candidate closed polylines were found.
