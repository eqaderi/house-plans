# concept-compact: Compact stacked house

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

> Design exploration produced by a constraint solver from the program. Nobody qualified has reviewed it; it has no permit, code or engineering status. Compliance: not checked.

## Strategy

Identical floor plates stacked on two or more levels and joined by one stair. The smallest footprint and envelope; on a site falling away from the road the extra levels sit below the entrance as a walk-out, with retaining walls on the uphill side.

## Levels

- **Entry level** (FFL +11.70 m local): Entrance hall, Dining, Kitchen, Living room, Garage, Stair
- **Level -3.00 m from entry** (FFL +8.70 m local): En-suite bathroom, Main bedroom, Child's bedroom 1, Child's bedroom 2, Bathroom 1, Study 1, Laundry, Plant / technical room, Stair

## Rooms

| Room | Level | Area m² | Program target m² | Program min m² |
|---|---|---:|---:|---:|
| Corridor | lv-entry | 12.0 | — | — |
| Corridor | lv-down-300 | 12.0 | — | — |
| Entrance hall | lv-entry | 8.1 | 6.0 | 4.0 |
| Dining | lv-entry | 15.0 | 14.0 | 10.0 |
| Kitchen | lv-entry | 12.0 | 12.0 | 8.0 |
| Living room | lv-entry | 27.0 | 25.0 | 16.0 |
| En-suite bathroom | lv-down-300 | 8.6 | 5.0 | 3.5 |
| Main bedroom | lv-down-300 | 16.2 | 15.0 | 12.0 |
| Child's bedroom 1 | lv-down-300 | 14.6 | 11.0 | 9.0 |
| Child's bedroom 2 | lv-down-300 | 14.6 | 11.0 | 9.0 |
| Bathroom 1 | lv-down-300 | 9.7 | 6.0 | 4.0 |
| Study 1 | lv-down-300 | 13.0 | 9.0 | 6.0 |
| Garage | lv-entry | 32.4 | 36.0 | 30.0 |
| Laundry | lv-down-300 | 9.7 | 6.0 | 4.0 |
| Plant / technical room | lv-down-300 | 8.1 | 4.0 | 3.0 |
| Stair | lv-entry | 13.5 | 10.0 | 8.0 |
| Stair | lv-down-300 | 13.5 | 10.0 | 8.0 |

## Measured results and trade-offs

Status in brackets when a value is not measured exactly.

- Gross floor area (centreline): 240.00 m²
- Footprint: 120.00 m²
- Floor levels: 2
- Programmed room area: 216.00 m²
- Flexible area not in the program: 0 m²
- Circulation share: 0.25
- Hard adjacencies met: 5
- Soft adjacency score (0-1): 0.83
- Level preferences met: 9
- Longest walk from the front door: 35.00 m (inferred)
- Routes to shared rooms through private rooms: 0
- Walls between private and public rooms: 1
- Footprint compactness (1 = circle): 0.37
- Excavation below floors: 104.13 m³ (inferred)
- Underfloor void (fill/support unspecified): 39.54 m³ (inferred)
- Maximum floor height over terrain: 1.99 m (inferred)
- Deepest cut: 2.73 m (inferred)
- Retaining wall length: 22.00 m
- Retained earth face: 44.38 m² (inferred)
- Closest approach to the envelope edge: 0.10 m

## Violations (0 hard, 14 soft)

- **soft** `elongated_room`: sp-bath-ensuite has a 3.4:1 aspect ratio; check furniture and clear usable dimensions (3:1 is a conceptual review trigger, not a code limit)
- **soft** `required_daylight_no_exterior_window`: sp-study-1 requests daylight but has no exterior window; borrowed light and actual illumination are not checked
- **soft** `soft_adjacency_unmet`: adj-10-study-1-entry: pi-study-1 near pi-entry is not met
- **soft** `soft_adjacency_unmet`: adj-12-laundry-kitchen: pi-laundry near pi-kitchen is not met
- **soft** `elevated_floor_support_unresolved`: About 39.5 m³ lies between terrain and the lowest floors, up to 1.99 m high. This is underfloor void, not specified engineered fill; supports, lateral stability, foundations and drainage are unresolved. Compare embedded, walk-out and stepped alternatives without assuming that less excavation is preferable
- **soft** `exterior_access_level_unresolved`: d-garage-garage-ext floor differs from existing ground by +0.34 m; an approach, ramp, steps or excavated terrace has not been designed (0.3 m is a conceptual review trigger, not an accessibility rule)
- **soft** `living_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `living_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `bedroom_noise_stacking`: Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown.
- **soft** `bedroom_noise_stacking`: Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown.
- **soft** `bedroom_noise_stacking`: Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown.
- **soft** `bedroom_noise_stacking`: Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown.
- **soft** `low_daylight_opportunity`: Unburied glazing ratio is below assumption; no daylight simulation.
- **soft** `outdoor_door_grade_mismatch`: Door threshold is 0.281 m relative to grade; check landing/ramp.

Not evaluated (no evaluator yet): DaylightEvaluator, SolarEvaluator, AccessibilityEvaluator, LifeSafetyEvaluator, StructuralConceptEvaluator, MEPConceptEvaluator, CostEvaluator, EnergyEvaluator, CulturalFitEvaluator.

## Assumptions

- [assumption] Room areas are measured to wall centerlines; net floor areas are smaller.
- [assumption] Floor-to-floor height 3 m; split levels step in half storeys of 1.5 m; walls 2.8 m high.
- [assumption] Exterior and retaining walls 0.3 m, partitions 0.15 m thick; no structural design has been done.
- [assumption] Plan grid: u axis along the parcel edge nearest road road-uphill.
- [assumption] Entry level set at the mean surveyed ground along the road-side face (11.70 m local), interpolated from the survey TIN (inferred).
- [assumption] The site falls away from the road, so the other levels sit below the entry level (walk-out).
- [assumption] Stair risers at most 0.18 m with 0.28 m goings; typical comfortable geometry, not checked against any code.
- [assumption] A garage needs at least 5.4 m depth for a car.
- [assumption] The plan is kept inside the buildable envelope (synthetic setbacks (3 m road side, 2 m sides, 3 m rear) invented for the example; not a zoning rule).
- [inference] Level elevations, earth contact and retaining walls are inferred by linear interpolation of the surveyed points; ground between survey points is not verified.

## Open issues

- [warning] Retaining walls, excavation, slope drainage and foundations need geotechnical and structural engineering; nothing here is engineered.

## How it was produced

- Generator `house-ai-cpsat-bars` 0.2.0, solver ortools-cp-sat 9.15.6755: OPTIMAL, objective 22168, seed 0, deterministic-time budget 4.
- Parameters: b0_length_m=10.0, b0_start_m=0.1, b1_length_m=10.0, b1_start_m=0.1, back_row_depth_m=4.8, corridor_width_m=1.2, front_row_depth_m=5.4, level_elevations_m=8.70, 11.70, levels=2, strategy=compact.
- Inputs: site/site v1 (c2d20667c325), space_program/program v1 (aaebe10f8491)
