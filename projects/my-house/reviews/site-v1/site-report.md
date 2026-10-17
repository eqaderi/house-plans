# Site validation report: site v1 (sha256 8e416cdc1c64)

Derived from the canonical site model. This report approves nothing.

## Coordinate system

- Drawing units: m (declared_in_source)
- Elevation units: m (declared_in_source)
- Horizontal CRS: unknown
- Vertical datum: unknown
- Local frame: lcs-site; origin (grid m) (623809.1666028872, 3870456.032537977, 0.0); rotation 0.0°
- Grid north: unconfirmed: the CRS is not confirmed, so grid north is not established
- Grid to true north: unknown (clockwise)

## Parcel boundary

- Status: inference; source: src-seperated#D7 (layer 0)
- Area: 600.00 m²; perimeter: 107.140 m; vertices: 4
- Oriented extent: 42.651 m × 18.422 m

| Edge | Length (m) | Bearing local | Bearing grid | Bearing true |
|---|---|---|---|---|
| 0 | 21.000 | 185.877° | unknown | unknown |
| 1 | 32.570 | 67.188° | unknown | unknown |
| 2 | 21.000 | 5.877° | unknown | unknown |
| 3 | 32.570 | 247.188° | unknown | unknown |

## Terrain

- Status: surface_built; spots: 27; contours: 0 (levels [], interval unknown)
- Elevation range: 1664.884 m to 1680.071 m (local)
- TIN: 27 vertices, 47 triangles; parcel coverage 100.0%
- Slope: max 150.21%, area-weighted mean 38.87%

### Steep triangles (over 100%)

Measured traits help the surveyor check each one; they are not causes. Nothing is smoothed or removed.

| Vertices | Slope | Area | Min angle | Steepest edge | Distance | Δz | Edge rise | Sources | In parcel | Traits |
|---|---|---|---|---|---|---|---|---|---|---|
| spot-elevation-85, spot-seperated-71, spot-elevation-87 | 150% | 1.05 m² | 3.7° | spot-seperated-71 – spot-elevation-87 | 0.72 m | 0.89 m | 124% | src-elevation, src-seperated | yes | sliver, close pair, mixes sources |
| spot-elevation-91, spot-seperated-6d, spot-seperated-6b | 147% | 3.68 m² | 0.3° | spot-seperated-6b – spot-elevation-91 | 33.61 m | 2.21 m | 7% | src-elevation, src-seperated | no | sliver, no steep edge, on survey edge, mixes sources, outside parcel |
| spot-elevation-89, spot-elevation-87, spot-seperated-71 | 124% | 2.31 m² | 6.4° | spot-seperated-71 – spot-elevation-87 | 0.72 m | 0.89 m | 124% | src-elevation, src-seperated | no | sliver, close pair, mixes sources, outside parcel |
| spot-elevation-91, spot-seperated-6b, spot-seperated-69 | 117% | 10.22 m² | 1.7° | spot-seperated-69 – spot-elevation-91 | 12.55 m | 1.54 m | 12% | src-elevation, src-seperated | no | sliver, no steep edge, mixes sources, outside parcel |
| spot-elevation-91, spot-elevation-69, spot-seperated-73 | 117% | 15.25 m² | 1.1° | spot-seperated-73 – spot-elevation-69 | 1.44 m | 0.49 m | 34% | src-elevation, src-seperated | no | sliver, no steep edge, on survey edge, close pair, mixes sources, outside parcel |

## Access and frontage

- Frontage length: 21.000 m in 1 segment(s)
- Access points on the frontage: none
- Road lines road-seperated-bc and road-seperated-c5 run parallel 9.000–9.000 m apart
- Features: {'frontage': 1, 'road': 2}

## Findings

- WARNING steep_terrain: 5 TIN triangle(s) are steeper than 100% (45°), up to 150% between spot-elevation-85, spot-seperated-71, spot-elevation-87: a wall, kerb or embankment, or an elevation error; check these points with the surveyor (each one is listed under steep triangles)
- INFO spots_outside_parcel: 11 spot elevation(s) lie outside the parcel boundary

## Open issues

- [warning] iss-ambiguous-entities: 6 ambiguous CAD entities were left out

## What the owner said (recorded, not confirmed in the tool)

- stmt-001 [horizontal_crs] owner: "The survey uses UTM coordinates." (chat with agent:claude-code, 2026-10-17; recorded by agent:claude-code)
  - formal step: `UTM zone, hemisphere (N/S) and horizontal datum/EPSG are still unknown: when known, house-ai site confirm my-house --confirmer <you> --epsg <code>. UTM is in metres, so the drawing unit can be confirmed now with --units m`
- stmt-002 [elevation_units] owner: "The elevation values are in METRES ABOVE SEA LEVEL." (chat with agent:claude-code, 2026-10-17; recorded by agent:claude-code)
  - formal step: `house-ai site confirm my-house --confirmer <you> --units m --elevation-units m (which sea-level datum is still unknown)`
- stmt-003 [relief] owner: "The approximately 12–12.5 metre elevation difference is CORRECT." (chat with agent:claude-code, 2026-10-17; recorded by agent:claude-code)
- stmt-004 [slope] owner: "My land is genuinely steep." (chat with agent:claude-code, 2026-10-17; recorded by agent:claude-code)
- stmt-005 [still_unknown] owner: "UTM zone is still unknown. Horizontal datum / EPSG is still unknown. The precise vertical datum is still unknown." (chat with agent:claude-code, 2026-10-17; recorded by agent:claude-code)

## Blockers for the site gate

- drawing units are declared_in_source (m); a human must confirm them
- horizontal CRS is unknown; a human must confirm the EPSG code or confirm the survey is local-only
- elevation units are declared_in_source (m); a human must confirm them
- vertical datum is unknown; a human must confirm it or confirm elevations are relative to a local benchmark
- parcel boundary status is inference, not verified
