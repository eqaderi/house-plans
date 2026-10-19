# concept-split-level: Split-level, stepping with the slope

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

> Design exploration produced by a constraint solver from the program. Nobody qualified has reviewed it; it has no permit, code or engineering status. Compliance: not checked.

## Strategy

Parallel bars stepping with the slope in half-storey increments chosen from the surveyed ground, joined by stairs. Road-level bars can still stand above the slope; stepping alone does not establish a close terrain fit or usable outdoor access.

## Levels

- **Entry level** (FFL +11.74 m local): Entrance hall, Dining, Kitchen, Living room, Study 1, Garage, Laundry, Plant / technical room, Stair, Stair hall
- **Level -4.50 m from entry** (FFL +7.24 m local): En-suite bathroom, Main bedroom, Child's bedroom 1, Child's bedroom 2, Bathroom 1, Stair, Stairwell

## Rooms

| Room | Level | Area m² | Program target m² | Program min m² |
|---|---|---:|---:|---:|
| Corridor | lv-entry | 14.9 | — | — |
| Corridor | lv-down-450 | 8.6 | — | — |
| Entrance hall | lv-entry | 8.1 | 6.0 | 4.0 |
| Dining | lv-entry | 13.8 | 14.0 | 10.0 |
| Kitchen | lv-entry | 11.0 | 12.0 | 8.0 |
| Living room | lv-entry | 22.1 | 25.0 | 16.0 |
| En-suite bathroom | lv-down-450 | 7.7 | 5.0 | 3.5 |
| Main bedroom | lv-down-450 | 16.3 | 15.0 | 12.0 |
| Child's bedroom 1 | lv-down-450 | 11.3 | 11.0 | 9.0 |
| Child's bedroom 2 | lv-down-450 | 11.3 | 11.0 | 9.0 |
| Bathroom 1 | lv-down-450 | 7.6 | 6.0 | 4.0 |
| Study 1 | lv-entry | 13.0 | 9.0 | 6.0 |
| Garage | lv-entry | 36.2 | 36.0 | 30.0 |
| Laundry | lv-entry | 9.7 | 6.0 | 4.0 |
| Plant / technical room | lv-entry | 8.1 | 4.0 | 3.0 |
| Stair | lv-entry | 11.9 | 10.0 | 8.0 |
| Stair | lv-down-450 | 10.6 | 10.0 | 8.0 |
| Stairwell | lv-down-450 | 4.8 | — | — |
| Stair hall | lv-entry | 4.8 | — | — |

## Measured results and trade-offs

Status in brackets when a value is not measured exactly.

- Gross floor area (centreline): 231.76 m²
- Footprint: 222.24 m²
- Floor levels: 2
- Programmed room area: 198.72 m²
- Flexible area not in the program: 0 m²
- Circulation share: 0.27
- Hard adjacencies met: 5
- Soft adjacency score (0-1): 0.91
- Level preferences met: 9
- Longest walk from the front door: 25.17 m
- Routes to shared rooms through private rooms: 0
- Walls between private and public rooms: 0
- Footprint compactness (1 = circle): 0.13
- Excavation below floors: 3.72 m³ (inferred)
- Underfloor void (support unspecified): 443.52 m³ (inferred)
- Proposed engineered fill (explicit pads only): not checked
- Maximum underfloor gap (see slab basis): 4.75 m (inferred)
- Deepest cut: 1.40 m (inferred)
- Retaining wall length: 8.20 m (inferred)
- Retained earth face: 4.60 m² (inferred)
- Closest approach to the envelope edge: 0.10 m

## Violations (0 hard, 36 soft)

- **soft** `soft_adjacency_unmet`: adj-12-laundry-kitchen: pi-laundry near pi-kitchen is not met
- **soft** `elevated_floor_support_unresolved`: Underfloor void is 443.5 m³, maximum 4.75 m. This is not specified engineered fill; supports, lateral stability, foundations and drainage unresolved.
- **soft** `large_underfloor_void`: Void clear height 4.75 m exceeds configured 4 m concept-review trigger.
- **soft** `garage_ramp_grade_review`: Straight candidate grade -23.7% exceeds configured concept trigger; no designed ramp or regulatory compliance established.
- **soft** `needs_professional_structure`: Concept load paths, lateral stability and support systems unresolved — needs professional.
- **soft** `needs_professional_foundations`: Bearing capacity, settlement and footing depths unverified — needs professional.
- **soft** `needs_professional_slope_stability`: Survey TIN does not establish geotechnical or slope stability — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
- **soft** `needs_professional_structure`: Underfloor clear space exceeds configured 4 m concept trigger; large void needs review — needs professional.
- **soft** `needs_professional_drainage`: Terrain-contact door: threshold drainage and approach unresolved — needs professional.
- **soft** `needs_professional_drainage`: Terrain-contact door: threshold drainage and approach unresolved — needs professional.
- **soft** `needs_professional_vehicle_access`: Garage ramp approach needs design and professional review — needs professional.
- **soft** `needs_professional_waterproofing`: Building-ground moisture details unverified — needs professional.
- **soft** `terrain_triangle_review`: Triangle 2 at (12.153666666666664, 0.5386666666666667): sliver; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 6 at (16.392333333333333, 1.4393333333333334): sliver; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 18 at (-3.4733333333333336, 11.530000000000001): sliver, steep_review; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 28 at (23.761, 8.458333333333334): sliver, steep_review; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 29 at (23.206333333333333, 11.067): sliver, steep_review; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 46 at (20.711333333333336, 22.804333333333332): sliver, steep_review; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 50 at (1.2619999999999998, 30.93866666666667): sliver; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 53 at (5.500333333333333, 31.839333333333336): sliver; survey review needed, no smoothing.
- **soft** `height_limit_exceeded`: Height 12.06 m exceeds envelope 10 m.
- **soft** `kitchen_no_sampled_fit`: No arrangement in the declared discrete template search; continuous infeasibility has not been proved.
- **soft** `garage_no_sampled_fit`: No arrangement in the declared discrete template search; continuous infeasibility has not been proved.
- **soft** `kitchen_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `living_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `living_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `daily_route_long`: entry_to_kitchen: 17.789 m point route.
- **soft** `excess_circulation`: Circulation share exceeds the conceptual assumption.
- **soft** `low_daylight_opportunity`: Unburied glazing ratio is below assumption; no daylight simulation.
- **soft** `outdoor_door_grade_mismatch`: Door threshold is 0.311 m relative to grade; check landing/ramp.

Not evaluated (no evaluator yet): DaylightEvaluator, SolarEvaluator, AccessibilityEvaluator, LifeSafetyEvaluator, StructuralConceptEvaluator, MEPConceptEvaluator, CostEvaluator, EnergyEvaluator, CulturalFitEvaluator.

## Assumptions

- [assumption] Room areas are measured to wall centerlines; net floor areas are smaller.
- [assumption] Floor-to-floor height 3 m; split levels step in half storeys of 1.5 m; walls 2.8 m high.
- [assumption] Exterior and retaining walls 0.3 m, partitions 0.15 m thick; no structural design has been done.
- [assumption] Plan grid: u axis along the parcel edge nearest road road-uphill.
- [assumption] Initial entry reference from the mean surveyed ground along the road-side face (11.70 m local), interpolated from the survey TIN (inferred).
- [assumption] Levels step by multiples of a half storey (1.5 m) chosen from the surveyed ground under each bar.
- [assumption] Floor elevations and bar positions/lengths solved jointly with TIN lookup; sectional contact bands and circulation/daylight objectives, no excavation/void penalty. Earthworks evaluated exactly afterward.
- [assumption] Stair risers at most 0.18 m with 0.28 m goings; typical comfortable geometry, not checked against any code.
- [assumption] A garage needs at least 5.4 m depth for a car.
- [assumption] The plan is kept inside the buildable envelope (synthetic setbacks (3 m road side, 2 m sides, 3 m rear) invented for the example; not a zoning rule).
- [inference] Level elevations, earth contact and retaining walls are inferred by linear interpolation of the surveyed points; ground between survey points is not verified.

## Open issues

- [warning] Retaining walls, excavation, slope drainage and foundations need geotechnical and structural engineering; nothing here is engineered.
- [warning] No fixture layout found for sp-kitchen; the sampled study reports on it
- [warning] No fixture layout found for sp-bath-ensuite; the sampled study reports on it

## Compiled soft objectives

| Objective | Status | Weight | Detail |
|---|---|---:|---|
| `acoustic_zoning` | `optimised` | 2 | optimised in solver: acoustic separation between noisy and quiet zones |
| `adjacency_quality` | `optimised` | 1 | optimised in solver: weighted adjacency satisfaction |
| `circulation_efficiency` | `optimised` | 1 | optimised in solver: filler area and circulation penalty |
| `daylight_opportunity` | `optimised` | 1 | optimised in solver: daylight-facing room requirements and penalties |
| `envelope_simplicity` | `optimised` | 1 | optimised in solver: bar compactness and envelope perimeter |
| `indoor_outdoor` | `not_optimised` | 2 | not_optimised in solver: outdoor terrace relationships evaluated downstream |
| `privacy` | `optimised` | 1 | optimised in solver: weighted separation between private and public zones |
| `site_response` | `optimised` | 2 | optimised in solver: road-side versus garden-side habitable room placement |

## How it was produced

- Generator `house-ai-cpsat-bars` 0.2.0, solver ortools-cp-sat 9.15.6755: OPTIMAL, objective 15918, seed 0, deterministic-time budget 4.
- Parameters: b0_length_m=12.4, b0_start_m=5.1, b1_length_m=7.2, b1_start_m=0.1, back_row_depth_m=4.2, corridor_width_m=1.2, front_row_depth_m=4.8, level_elevations_m=7.24, 11.74, level_solver=joint_cpsat_terrain_lookup_5cm_xy_1cm_z, levels=2, strategy=split_level.
- Inputs: site/site v1 (c2d20667c325), space_program/program v1 (9dd9270f641b)
