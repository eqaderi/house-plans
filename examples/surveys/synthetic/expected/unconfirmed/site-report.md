# Site validation report: site

Derived from the canonical site model. This report approves nothing.

## Coordinate system

- Drawing units: m (declared_in_source)
- Elevation units: m (declared_in_source)
- Horizontal CRS: declared EPSG:25832 ETRS89 / UTM zone 32N (declared_in_source)
- Vertical datum: unknown
- Local frame: lcs-site; origin (grid m) (500100.0, 5400200.0, 0.0); rotation 0.0°
- Grid north: unconfirmed: the CRS is not confirmed, so grid north is not established
- Grid to true north: unknown (clockwise)

## Parcel boundary

- Status: inference; source: src-survey#40 (layer PARCEL_BOUNDARY)
- Area: 1400.00 m²; perimeter: 145.765 m; vertices: 5
- Oriented extent: 40.000 m × 40.000 m

| Edge | Length (m) | Bearing local | Bearing grid | Bearing true |
|---|---|---|---|---|
| 0 | 40.000 | 90.000° | unknown | unknown |
| 1 | 30.000 | 0.000° | unknown | unknown |
| 2 | 31.623 | 288.435° | unknown | unknown |
| 3 | 14.142 | 225.000° | unknown | unknown |
| 4 | 30.000 | 180.000° | unknown | unknown |

## Terrain

- Status: surface_built; spots: 8; contours: 4 (levels [101.0, 102.0, 103.0, 104.0], interval 1.000 m)
- Elevation range: 100.000 m to 105.000 m (local)
- TIN: 20 vertices, 27 triangles; parcel coverage 100.0%
- Slope: max 11.18%, area-weighted mean 11.18%

## Access and frontage

- Frontage length: 40.000 m in 1 segment(s)
- Access points on the frontage: access-5c
- Features: {'access_point': 1, 'existing_structure': 1, 'frontage': 1, 'road': 1, 'tree': 1}

## Findings

- none

## Open issues

- [warning] iss-ambiguous-entities: 6 ambiguous CAD entities were left out
- [info] iss-unmapped-layers: 1 layers have no role and were not read

## Blockers for the site gate

- drawing units are declared_in_source (m); a human must confirm them
- horizontal CRS is declared_in_source (source declares EPSG:25832); a human must confirm the EPSG code or confirm the survey is local-only
- elevation units are declared_in_source (m); a human must confirm them
- vertical datum is unknown; a human must confirm it or confirm elevations are relative to a local benchmark
- parcel boundary status is inference, not verified
