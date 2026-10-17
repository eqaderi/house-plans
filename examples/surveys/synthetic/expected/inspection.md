# Survey inspection (read-only)

Read-only inspection. Values are what the files declare; nothing here is confirmed, and coordinate magnitudes are not evidence of a CRS or unit.

## survey.dxf

### 1. File format
- dxf AC1032 (DXF group code 0 SECTION)
- 22698 bytes, sha256 `ec124911da0ddeef41a74998f0eed669f427d8abac989389bf3e82bbbebaa676`; unchanged after inspection: yes

### 2. Drawing units
- $INSUNITS = 6 (metres); status: declared in source as m; needs your confirmation
- Header: {'$ACADVER': 'AC1032', '$INSUNITS': 6, '$MEASUREMENT': 1, '$LUNITS': 2, '$AUNITS': 0, '$ANGBASE': 0.0, '$ANGDIR': 0}

### 3. CAD layers

| Layer | Entities | Types | Mapped role | Suggested role (hint) |
|---|---|---|---|---|
| 0 | 0 | {} | unclassified | - |
| ACCESS | 1 | {'POINT': 1} | access_point | access_point (layer name contains 'access') |
| CONTOURS | 6 | {'LWPOLYLINE': 5, 'POLYLINE': 1} | contour | contour (layer name contains 'contour') |
| Defpoints | 0 | {} | unclassified | - |
| EXIST_BUILDING | 1 | {'LWPOLYLINE': 1} | existing_structure | existing_structure (layer name contains 'build') |
| MISC_XREF | 2 | {'LINE': 1, 'SPLINE': 1} | unclassified | - |
| PARCEL_BOUNDARY | 2 | {'LINE': 1, 'LWPOLYLINE': 1} | boundary | boundary (layer name contains 'boundary') |
| ROAD | 2 | {'LWPOLYLINE': 1, 'TEXT': 1} | road | road (layer name contains 'road') |
| SPOT_HEIGHTS | 10 | {'INSERT': 1, 'POINT': 8, 'TEXT': 1} | spot_elevation | spot_elevation (layer name contains 'spot') |
| TEXT_ANNO | 1 | {'TEXT': 1} | annotation | annotation (layer name contains 'text') |
| TREES | 1 | {'INSERT': 1} | tree | tree (layer name contains 'tree') |

### 4. Coordinate metadata
- GEODATA: {'coordinate_type': 'projected grid', 'design_point': [0.0, 0.0, 0.0], 'reference_point': [0.0, 0.0, 0.0], 'north_direction': [0.0, 1.0, 0.0], 'horizontal_unit_scale': 1.0, 'vertical_unit_scale': 1.0, 'horizontal_units': 6, 'vertical_units': 6, 'declared_epsg': 25832}
- Declared EPSG: 25832 (ETRS89 / UTM zone 32N)
- Extents (source units): (500090.0, 5400187.5, 500170.0, 5400270.0)

### 5. CRS verification status
- declared in source as EPSG:25832; needs your confirmation
- Coordinate magnitudes are not evidence of a CRS, zone or unit.

### 6. Candidate parcel boundary
- Basis: closed polylines on the layers your mapping marks as boundary
- 40 on 'PARCEL_BOUNDARY': 5 vertices, area 1400.000 unit², perimeter 145.765 (= 1400.00 m² if the declared unit is right)

### 7. Contours and spot elevations (by layer)

| Layer | Points with z | Points z=0 | Constant-z lines | z=0 lines | Varying-z lines | Numeric labels | z range |
|---|---|---|---|---|---|---|---|
| CONTOURS | 0 | 0 | 4 | 1 | 1 | 0 | 100.5 to 104.0 |
| SPOT_HEIGHTS | 8 | 1 | 0 | 0 | 0 | 1 | 100.0 to 105.0 |

### 8. Unknown or ambiguous information
- Unsupported entities: {'SPLINE': 1}
- Layers without a role: MISC_XREF
- 41 (LINE, PARCEL_BOUNDARY): open linework on a boundary layer, not part of it
- 46 (LWPOLYLINE, CONTOURS): contour elevation is 0, which may mean 'not set'
- 47 (POLYLINE, CONTOURS): z varies along the line, so it is not a contour
- 58 (TEXT, ROAD): text label on a road layer; not interpreted
- 56 (POINT, SPOT_HEIGHTS): point elevation is 0, which may mean 'not set'
- 55 (TEXT, SPOT_HEIGHTS): height label text is not linked to a surveyed point; not used

### 9. Provenance
- Path: examples/surveys/synthetic/survey.dxf
- Parser: ezdxf <version>

### 10. Needs your confirmation
- [ ] Confirm the drawing unit: the file declares m.
- [ ] Confirm the elevation unit (DXF z values use the drawing unit unless the surveyor says otherwise).
- [ ] Confirm the horizontal CRS: the file declares EPSG:25832 (ETRS89 / UTM zone 32N).
- [ ] State the vertical datum of the elevations (e.g. a national height system) or the local benchmark they are relative to.
- [ ] Confirm that polyline 40 on layer 'PARCEL_BOUNDARY' is the legal parcel boundary.
- [ ] Some elevation entities have z = 0: say whether 0 is a real elevation here.
- [ ] Review 6 ambiguous entities listed in this report.
