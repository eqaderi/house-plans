# concept-split-level: Split-level, stepping with the slope

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

> Design exploration produced by a constraint solver from the program. Nobody qualified has reviewed it; it has no permit, code or engineering status. Compliance: not checked.

## Strategy

Parallel bars stepping with the slope in half-storey increments chosen from the surveyed ground, joined by stairs. Road-level bars can still stand above the slope; stepping alone does not establish a close terrain fit or usable outdoor access.

## Levels

- **Entry level** (FFL +11.70 m local): Entrance hall, Dining, Kitchen, Living room, Study 1, Garage, Laundry, Plant / technical room, Stair
- **Level -3.00 m from entry** (FFL +8.70 m local): En-suite bathroom, Main bedroom, Child's bedroom 1, Child's bedroom 2, Bathroom 1, Stair

## Rooms

| Room | Level | Area m² | Program target m² | Program min m² |
|---|---|---:|---:|---:|
| Corridor | lv-entry | 14.9 | — | — |
| Corridor | lv-down-300 | 8.6 | — | — |
| Entrance hall | lv-entry | 8.1 | 6.0 | 4.0 |
| Dining | lv-entry | 12.3 | 14.0 | 10.0 |
| Kitchen | lv-entry | 9.8 | 12.0 | 8.0 |
| Living room | lv-entry | 24.8 | 25.0 | 16.0 |
| En-suite bathroom | lv-down-300 | 7.7 | 5.0 | 3.5 |
| Main bedroom | lv-down-300 | 16.3 | 15.0 | 12.0 |
| Child's bedroom 1 | lv-down-300 | 11.3 | 11.0 | 9.0 |
| Child's bedroom 2 | lv-down-300 | 11.3 | 11.0 | 9.0 |
| Bathroom 1 | lv-down-300 | 7.6 | 6.0 | 4.0 |
| Study 1 | lv-entry | 13.0 | 9.0 | 6.0 |
| Garage | lv-entry | 36.2 | 36.0 | 30.0 |
| Laundry | lv-entry | 9.7 | 6.0 | 4.0 |
| Plant / technical room | lv-entry | 8.1 | 4.0 | 3.0 |
| Stair | lv-entry | 11.9 | 10.0 | 8.0 |
| Stair | lv-down-300 | 10.6 | 10.0 | 8.0 |

## Measured results and trade-offs

Status in brackets when a value is not measured exactly.

- Gross floor area (centreline): 222.24 m²
- Footprint: 222.24 m²
- Floor levels: 2
- Programmed room area: 198.72 m²
- Flexible area not in the program: 0 m²
- Circulation share: 0.24
- Hard adjacencies met: 5
- Soft adjacency score (0-1): 0.91
- Level preferences met: 9
- Longest walk from the front door: 31.00 m
- Routes to shared rooms through private rooms: 0
- Walls between private and public rooms: 0
- Footprint compactness (1 = circle): 0.25
- Excavation below floors: 0.00 m³ (inferred)
- Underfloor void (fill/support unspecified): 649.37 m³ (inferred)
- Maximum floor height over terrain: 6.00 m (inferred)
- Deepest cut: 0.00 m (inferred)
- Retaining wall length: 0 m
- Retained earth face: 0.00 m² (inferred)
- Closest approach to the envelope edge: 0.10 m

## Violations (0 hard, 12 soft)

- **soft** `soft_adjacency_unmet`: adj-12-laundry-kitchen: pi-laundry near pi-kitchen is not met
- **soft** `elevated_floor_support_unresolved`: About 649.4 m³ lies between terrain and the lowest floors, up to 6.00 m high. This is underfloor void, not specified engineered fill; supports, lateral stability, foundations and drainage are unresolved. Compare embedded, walk-out and stepped alternatives without assuming that less excavation is preferable
- **soft** `exterior_access_level_unresolved`: d-garage-garage-ext floor differs from existing ground by +0.43 m; an approach, ramp, steps or excavated terrace has not been designed (0.3 m is a conceptual review trigger, not an accessibility rule)
- **soft** `height_limit_exceeded`: about 12.0 m above the lowest ground under the house; the envelope allows 10 m (assumption)
- **soft** `stair_low_headroom`: Pitch-line headroom 1.250 m under slab.
- **soft** `kitchen_no_sampled_fit`: No arrangement in the declared discrete template search; continuous infeasibility has not been proved.
- **soft** `living_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `living_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `excess_circulation`: Circulation share exceeds the conceptual assumption.
- **soft** `low_daylight_opportunity`: Unburied glazing ratio is below assumption; no daylight simulation.
- **soft** `outdoor_door_grade_mismatch`: Door threshold is 0.203 m relative to grade; check landing/ramp.
- **soft** `outdoor_door_grade_mismatch`: Door threshold is 0.369 m relative to grade; check landing/ramp.

Not evaluated (no evaluator yet): DaylightEvaluator, SolarEvaluator, AccessibilityEvaluator, LifeSafetyEvaluator, StructuralConceptEvaluator, MEPConceptEvaluator, CostEvaluator, EnergyEvaluator, CulturalFitEvaluator.

## Assumptions

- [assumption] Room areas are measured to wall centerlines; net floor areas are smaller.
- [assumption] Floor-to-floor height 3 m; split levels step in half storeys of 1.5 m; walls 2.8 m high.
- [assumption] Exterior and retaining walls 0.3 m, partitions 0.15 m thick; no structural design has been done.
- [assumption] Plan grid: u axis along the parcel edge nearest road road-uphill.
- [assumption] Entry level set at the mean surveyed ground along the road-side face (11.70 m local), interpolated from the survey TIN (inferred).
- [assumption] Levels step by multiples of a half storey (1.5 m) chosen from the surveyed ground under each bar.
- [assumption] Stair risers at most 0.18 m with 0.28 m goings; typical comfortable geometry, not checked against any code.
- [assumption] A garage needs at least 5.4 m depth for a car.
- [assumption] The plan is kept inside the buildable envelope (synthetic setbacks (3 m road side, 2 m sides, 3 m rear) invented for the example; not a zoning rule).
- [inference] Level elevations, earth contact and retaining walls are inferred by linear interpolation of the surveyed points; ground between survey points is not verified.

## How it was produced

- Generator `house-ai-cpsat-bars` 0.2.0, solver ortools-cp-sat 9.15.6755: OPTIMAL, objective 15068, seed 0, deterministic-time budget 4.
- Parameters: b0_length_m=12.4, b0_start_m=0.1, b1_length_m=7.2, b1_start_m=0.1, back_row_depth_m=4.2, corridor_width_m=1.2, front_row_depth_m=4.8, level_elevations_m=8.70, 11.70, levels=2, strategy=split_level.
- Inputs: site/site v1 (c2d20667c325), space_program/program v1 (aaebe10f8491)
