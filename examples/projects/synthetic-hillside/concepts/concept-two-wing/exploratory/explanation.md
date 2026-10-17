# concept-two-wing: Two wings (L): day wing on the road, night wing into the site

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

> Design exploration produced by a constraint solver from the program. Nobody qualified has reviewed it; it has no permit, code or engineering status. Compliance: not checked.

## Strategy

An L: a day wing along the road and a night wing running into the site, stepping down where the ground falls. Day and night zones are physically apart.

## Levels

- **Entry level** (FFL +11.70 m local): Entrance hall, Dining, Kitchen, Living room, Study 1, Garage, Stair
- **Level -3.00 m from entry** (FFL +8.70 m local): En-suite bathroom, Main bedroom, Child's bedroom 1, Child's bedroom 2, Bathroom 1, Laundry, Plant / technical room

## Rooms

| Room | Level | Area m² | Program target m² | Program min m² |
|---|---|---:|---:|---:|
| Corridor | lv-entry | 12.7 | — | — |
| Corridor | lv-down-300 | 9.4 | — | — |
| Entrance hall | lv-entry | 8.1 | 6.0 | 4.0 |
| Dining | lv-entry | 13.8 | 14.0 | 10.0 |
| Kitchen | lv-entry | 11.0 | 12.0 | 8.0 |
| Living room | lv-entry | 20.5 | 25.0 | 16.0 |
| En-suite bathroom | lv-down-300 | 6.7 | 5.0 | 3.5 |
| Main bedroom | lv-down-300 | 14.7 | 15.0 | 12.0 |
| Child's bedroom 1 | lv-down-300 | 11.3 | 11.0 | 9.0 |
| Child's bedroom 2 | lv-down-300 | 11.3 | 11.0 | 9.0 |
| Bathroom 1 | lv-down-300 | 7.6 | 6.0 | 4.0 |
| Study 1 | lv-entry | 13.0 | 9.0 | 6.0 |
| Garage | lv-entry | 36.2 | 36.0 | 30.0 |
| Laundry | lv-down-300 | 7.6 | 6.0 | 4.0 |
| Plant / technical room | lv-down-300 | 6.3 | 4.0 | 3.0 |
| Stair | lv-entry | 11.9 | 10.0 | 8.0 |

## Measured results and trade-offs

Status in brackets when a value is not measured exactly.

- Gross floor area (centreline): 202.08 m²
- Footprint: 202.08 m²
- Floor levels: 2
- Programmed room area: 180.00 m²
- Flexible area not in the program: 0 m²
- Circulation share: 0.21
- Hard adjacencies met: 5
- Soft adjacency score (0-1): 0.91
- Level preferences met: 9
- Longest walk from the front door: 27.75 m (inferred)
- Routes to shared rooms through private rooms: 0
- Walls between private and public rooms: 0
- Footprint compactness (1 = circle): 0.16
- Excavation below floors: 0.00 m³ (inferred)
- Fill / void under floors: 552.41 m³ (inferred)
- Deepest cut: 0.00 m (inferred)
- Retaining wall length: 0 m
- Retained earth face: 0.00 m² (inferred)
- Closest approach to the envelope edge: 0.10 m

## Violations (0 hard, 2 soft)

- **soft** `soft_adjacency_unmet`: adj-12-laundry-kitchen: pi-laundry near pi-kitchen is not met
- **soft** `height_limit_exceeded`: about 11.2 m above the lowest ground under the house; the envelope allows 10 m (assumption)

Not evaluated (no evaluator yet): DaylightEvaluator, SolarEvaluator, AccessibilityEvaluator, LifeSafetyEvaluator, StructuralConceptEvaluator, MEPConceptEvaluator, CostEvaluator, EnergyEvaluator, CulturalFitEvaluator.

## Assumptions

- [assumption] Room areas are measured to wall centerlines; net floor areas are smaller.
- [assumption] Floor-to-floor height 3 m; split levels step in half storeys of 1.5 m; walls 2.8 m high.
- [assumption] Exterior and retaining walls 0.3 m, partitions 0.15 m thick; no structural design has been done.
- [assumption] Plan grid: u axis along the parcel edge nearest road road-uphill.
- [assumption] Entry level set at the mean surveyed ground along the road-side face (11.70 m local), interpolated from the survey TIN (inferred).
- [assumption] Stair risers at most 0.18 m with 0.28 m goings; typical comfortable geometry, not checked against any code.
- [assumption] A garage needs at least 5.4 m depth for a car.
- [assumption] The plan is kept inside the buildable envelope (synthetic setbacks (3 m road side, 2 m sides, 3 m rear) invented for the example; not a zoning rule).
- [inference] Level elevations, earth contact and retaining walls are inferred by linear interpolation of the surveyed points; ground between survey points is not verified.

## How it was produced

- Generator `house-ai-cpsat-bars` 0.1.0, solver ortools-cp-sat 9.15.6755: OPTIMAL, objective 9232, seed 0, deterministic-time budget 4.
- Parameters: b0_length_m=10.6, b0_start_m=3.3, b1_length_m=7.8, b1_start_m=13.1, back_row_depth_m=4.2, corridor_width_m=1.2, front_row_depth_m=4.2, level_elevations_m=8.70, 11.70, levels=2, strategy=two_wing.
- Inputs: site/site v1 (c2d20667c325), space_program/program v1 (9bed3e94e948)
