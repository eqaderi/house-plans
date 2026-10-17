# concept-linear: Linear bar along the contours

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

> Design exploration produced by a constraint solver from the program. Nobody qualified has reviewed it; it has no permit, code or engineering status. Compliance: not checked.

## Strategy

One long bar along the contours on a single level. A road-level floor over falling terrain may require substantial underfloor support; inner clustered rooms may lack exterior windows. Compare the measured cut, void and circulation quantities.

## Levels

- **Entry level** (FFL +11.70 m local): Entrance hall, Dining, Kitchen, Living room, En-suite bathroom, Main bedroom, Child's bedroom 1, Child's bedroom 2, Bathroom 1, Study 1, Garage, Laundry, Plant / technical room

## Rooms

| Room | Level | Area m² | Program target m² | Program min m² |
|---|---|---:|---:|---:|
| Corridor | lv-entry | 21.0 | — | — |
| Entrance hall | lv-entry | 8.1 | 6.0 | 4.0 |
| Dining | lv-entry | 14.1 | 14.0 | 10.0 |
| Kitchen | lv-entry | 11.3 | 12.0 | 8.0 |
| Living room | lv-entry | 24.8 | 25.0 | 16.0 |
| En-suite bathroom | lv-entry | 8.6 | 5.0 | 3.5 |
| Main bedroom | lv-entry | 16.2 | 15.0 | 12.0 |
| Child's bedroom 1 | lv-entry | 14.6 | 11.0 | 9.0 |
| Child's bedroom 2 | lv-entry | 14.6 | 11.0 | 9.0 |
| Bathroom 1 | lv-entry | 9.7 | 6.0 | 4.0 |
| Study 1 | lv-entry | 13.0 | 9.0 | 6.0 |
| Garage | lv-entry | 36.2 | 36.0 | 30.0 |
| Laundry | lv-entry | 9.7 | 6.0 | 4.0 |
| Plant / technical room | lv-entry | 8.1 | 4.0 | 3.0 |

## Measured results and trade-offs

Status in brackets when a value is not measured exactly.

- Gross floor area (centreline): 210.00 m²
- Footprint: 210.00 m²
- Floor levels: 1
- Programmed room area: 189.00 m²
- Flexible area not in the program: 0 m²
- Circulation share: 0.14
- Hard adjacencies met: 5
- Soft adjacency score (0-1): 0.83
- Level preferences met: 9
- Longest walk from the front door: 24.79 m (inferred)
- Routes to shared rooms through private rooms: 0
- Walls between private and public rooms: 2
- Footprint compactness (1 = circle): 0.22
- Excavation below floors: 0.04 m³ (inferred)
- Underfloor void (fill/support unspecified): 484.68 m³ (inferred)
- Maximum floor height over terrain: 4.99 m (inferred)
- Deepest cut: 0.07 m (inferred)
- Retaining wall length: 0 m
- Retained earth face: 0.00 m² (inferred)
- Closest approach to the envelope edge: 0.10 m

## Violations (0 hard, 9 soft)

- **soft** `elongated_room`: sp-bath-ensuite has a 3.4:1 aspect ratio; check furniture and clear usable dimensions (3:1 is a conceptual review trigger, not a code limit)
- **soft** `elongated_room`: sp-bath-1 has a 3.0:1 aspect ratio; check furniture and clear usable dimensions (3:1 is a conceptual review trigger, not a code limit)
- **soft** `program_item_missing`: Stair (pi-stair): 0 of 1 placed; not needed in a one-level concept
- **soft** `level_count_differs`: the program asks for 2 storey(s); this concept has 1 floor level(s)
- **soft** `soft_adjacency_unmet`: adj-12-laundry-kitchen: pi-laundry near pi-kitchen is not met
- **soft** `soft_adjacency_unmet`: adj-14-stair-entry: pi-stair near pi-entry is not met
- **soft** `elevated_floor_support_unresolved`: About 484.7 m³ lies between terrain and the lowest floors, up to 4.99 m high. This is underfloor void, not specified engineered fill; supports, lateral stability, foundations and drainage are unresolved. Compare embedded, walk-out and stepped alternatives without assuming that less excavation is preferable
- **soft** `exterior_access_level_unresolved`: d-front-entry-ext floor differs from existing ground by +0.53 m; an approach, ramp, steps or excavated terrace has not been designed (0.3 m is a conceptual review trigger, not an accessibility rule)
- **soft** `exterior_access_level_unresolved`: d-garage-garage-ext floor differs from existing ground by +0.37 m; an approach, ramp, steps or excavated terrace has not been designed (0.3 m is a conceptual review trigger, not an accessibility rule)

Not evaluated (no evaluator yet): DaylightEvaluator, SolarEvaluator, AccessibilityEvaluator, LifeSafetyEvaluator, StructuralConceptEvaluator, MEPConceptEvaluator, CostEvaluator, EnergyEvaluator, CulturalFitEvaluator.

## Assumptions

- [assumption] Room areas are measured to wall centerlines; net floor areas are smaller.
- [assumption] Floor-to-floor height 3 m; split levels step in half storeys of 1.5 m; walls 2.8 m high.
- [assumption] Exterior and retaining walls 0.3 m, partitions 0.15 m thick; no structural design has been done.
- [assumption] Plan grid: u axis along the parcel edge nearest road road-uphill.
- [assumption] Entry level set at the mean surveyed ground along the road-side face (11.70 m local), interpolated from the survey TIN (inferred).
- [assumption] A garage needs at least 5.4 m depth for a car.
- [assumption] The plan is kept inside the buildable envelope (synthetic setbacks (3 m road side, 2 m sides, 3 m rear) invented for the example; not a zoning rule).
- [inference] Level elevations, earth contact and retaining walls are inferred by linear interpolation of the surveyed points; ground between survey points is not verified.

## How it was produced

- Generator `house-ai-cpsat-bars` 0.2.0, solver ortools-cp-sat 9.15.6755: OPTIMAL, objective 14580, seed 0, deterministic-time budget 4.
- Parameters: b0_length_m=17.5, b0_start_m=0.1, back_row_depth_m=4.2, corridor_width_m=1.2, front_row_depth_m=4.2, level_elevations_m=11.70, levels=1, strategy=linear.
- Inputs: site/site v1 (c2d20667c325), space_program/program v1 (9bed3e94e948)
