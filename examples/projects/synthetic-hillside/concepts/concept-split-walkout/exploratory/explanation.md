# concept-split-walkout: Hybrid walk-out below entry with a stepped downhill wing

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

> Design exploration produced by a constraint solver from the program. Nobody qualified has reviewed it; it has no permit, code or engineering status. Compliance: not checked.

## Strategy

A lower floor under the road-level entry combines an embedded massing with a stepped downhill wing. Compare its cut, void, retaining walls, floor area, daylight and circulation against the other options; additional floors can overfill the program. Walk-out doors and terraces remain unresolved.

## Levels

- **Entry level** (FFL +11.70 m local): Entrance hall, Dining, Kitchen, Living room, Garage, Stair
- **Level -3.00 m from entry** (FFL +8.70 m local): En-suite bathroom, Main bedroom, Child's bedroom 1, Child's bedroom 2, Stair, Stair, Flexible space (not in program), Flexible space (not in program)
- **Level -6.00 m from entry** (FFL +5.70 m local): Bathroom 1, Study 1, Laundry, Plant / technical room, Stair, Flexible space (not in program)

## Rooms

| Room | Level | Area m² | Program target m² | Program min m² |
|---|---|---:|---:|---:|
| Corridor | lv-entry | 11.4 | — | — |
| Corridor | lv-down-300 | 11.4 | — | — |
| Corridor | lv-down-600 | 7.2 | — | — |
| Entrance hall | lv-entry | 8.1 | 6.0 | 4.0 |
| Dining | lv-entry | 14.7 | 14.0 | 10.0 |
| Kitchen | lv-entry | 11.8 | 12.0 | 8.0 |
| Living room | lv-entry | 24.8 | 25.0 | 16.0 |
| En-suite bathroom | lv-down-300 | 8.6 | 5.0 | 3.5 |
| Main bedroom | lv-down-300 | 16.2 | 15.0 | 12.0 |
| Child's bedroom 1 | lv-down-300 | 14.6 | 11.0 | 9.0 |
| Child's bedroom 2 | lv-down-300 | 14.6 | 11.0 | 9.0 |
| Bathroom 1 | lv-down-600 | 7.6 | 6.0 | 4.0 |
| Study 1 | lv-down-600 | 11.3 | 9.0 | 6.0 |
| Garage | lv-entry | 30.2 | 36.0 | 30.0 |
| Laundry | lv-down-600 | 8.6 | 6.0 | 4.0 |
| Plant / technical room | lv-down-600 | 6.3 | 4.0 | 3.0 |
| Stair | lv-entry | 13.0 | 10.0 | 8.0 |
| Stair | lv-down-300 | 13.0 | 10.0 | 8.0 |
| Stair | lv-down-300 | 11.9 | 10.0 | 8.0 |
| Stair | lv-down-600 | 10.6 | 10.0 | 8.0 |
| Flexible space (not in program) | lv-down-300 | 14.6 | — | — |
| Flexible space (not in program) | lv-down-300 | 9.2 | — | — |
| Flexible space (not in program) | lv-down-600 | 9.6 | — | — |

## Measured results and trade-offs

Status in brackets when a value is not measured exactly.

- Gross floor area (centreline): 289.20 m²
- Footprint: 175.20 m²
- Floor levels: 3
- Programmed room area: 225.84 m²
- Flexible area not in the program: 33.36 m²
- Circulation share: 0.30
- Hard adjacencies met: 5
- Soft adjacency score (0-1): 0.83
- Level preferences met: 9
- Longest walk from the front door: 46.72 m (inferred)
- Routes to shared rooms through private rooms: 0
- Walls between private and public rooms: 0
- Footprint compactness (1 = circle): 0.28
- Excavation below floors: 109.91 m³ (inferred)
- Underfloor void (fill/support unspecified): 98.72 m³ (inferred)
- Maximum floor height over terrain: 2.82 m (inferred)
- Deepest cut: 2.73 m (inferred)
- Retaining wall length: 23.30 m
- Retained earth face: 44.95 m² (inferred)
- Closest approach to the envelope edge: 0.10 m

## Violations (0 hard, 10 soft)

- **soft** `required_daylight_no_exterior_window`: sp-bed-child-1 requests daylight but has no exterior window; borrowed light and actual illumination are not checked
- **soft** `required_daylight_no_exterior_window`: sp-bed-child-2 requests daylight but has no exterior window; borrowed light and actual illumination are not checked
- **soft** `elongated_room`: sp-bath-ensuite has a 3.4:1 aspect ratio; check furniture and clear usable dimensions (3:1 is a conceptual review trigger, not a code limit)
- **soft** `level_count_differs`: the program asks for 2 storey(s); this concept has 3 floor level(s)
- **soft** `soft_adjacency_unmet`: adj-10-study-1-entry: pi-study-1 near pi-entry is not met
- **soft** `soft_adjacency_unmet`: adj-12-laundry-kitchen: pi-laundry near pi-kitchen is not met
- **soft** `elevated_floor_support_unresolved`: About 98.7 m³ lies between terrain and the lowest floors, up to 2.82 m high. This is underfloor void, not specified engineered fill; supports, lateral stability, foundations and drainage are unresolved. Compare embedded, walk-out and stepped alternatives without assuming that less excavation is preferable
- **soft** `exterior_access_level_unresolved`: d-front-entry-ext floor differs from existing ground by +0.53 m; an approach, ramp, steps or excavated terrace has not been designed (0.3 m is a conceptual review trigger, not an accessibility rule)
- **soft** `exterior_access_level_unresolved`: d-garage-garage-ext floor differs from existing ground by +0.39 m; an approach, ramp, steps or excavated terrace has not been designed (0.3 m is a conceptual review trigger, not an accessibility rule)
- **soft** `height_limit_exceeded`: about 11.8 m above the lowest ground under the house; the envelope allows 10 m (assumption)

Not evaluated (no evaluator yet): DaylightEvaluator, SolarEvaluator, AccessibilityEvaluator, LifeSafetyEvaluator, StructuralConceptEvaluator, MEPConceptEvaluator, CostEvaluator, EnergyEvaluator, CulturalFitEvaluator.

## Assumptions

- [assumption] Room areas are measured to wall centerlines; net floor areas are smaller.
- [assumption] Floor-to-floor height 3 m; split levels step in half storeys of 1.5 m; walls 2.8 m high.
- [assumption] Exterior and retaining walls 0.3 m, partitions 0.15 m thick; no structural design has been done.
- [assumption] Plan grid: u axis along the parcel edge nearest road road-uphill.
- [assumption] Entry level set at the mean surveyed ground along the road-side face (11.70 m local), interpolated from the survey TIN (inferred).
- [assumption] A full floor below the road-level entry reuses its footprint; the downhill wing steps from that floor toward its own surveyed ground, rather than inheriting the entry bar's terrain offset. The walk-out is a massing intent: exterior doors, terraces, waterproofing, drainage and structural support still need design. There is no excavation-depth limit or preference for minimizing excavation.
- [assumption] Stair risers at most 0.18 m with 0.28 m goings; typical comfortable geometry, not checked against any code.
- [assumption] A garage needs at least 5.4 m depth for a car.
- [assumption] Rows are closed with flexible spaces that are not in the program (storage, or space to give back).
- [assumption] The plan is kept inside the buildable envelope (synthetic setbacks (3 m road side, 2 m sides, 3 m rear) invented for the example; not a zoning rule).
- [inference] Level elevations, earth contact and retaining walls are inferred by linear interpolation of the surveyed points; ground between survey points is not verified.

## Open issues

- [warning] Retaining walls, excavation, slope drainage and foundations need geotechnical and structural engineering; nothing here is engineered.

## How it was produced

- Generator `house-ai-cpsat-bars` 0.2.0, solver ortools-cp-sat 9.15.6755: OPTIMAL, objective 31182, seed 0, deterministic-time budget 4.
- Parameters: b-walkout_length_m=9.5, b-walkout_start_m=0.1, b0_length_m=9.5, b0_start_m=0.1, b1_length_m=6.0, b1_start_m=4.7, back_row_depth_m=4.2, corridor_width_m=1.2, front_row_depth_m=4.8, hybrid_walkout=True, level_elevations_m=5.70, 8.70, 11.70, levels=3, strategy=split_walkout.
- Inputs: site/site v1 (c2d20667c325), space_program/program v1 (9bed3e94e948)
