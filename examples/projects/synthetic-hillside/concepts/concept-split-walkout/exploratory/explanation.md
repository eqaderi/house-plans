# concept-split-walkout: Hybrid walk-out below entry with a stepped downhill wing

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

> Design exploration produced by a constraint solver from the program. Nobody qualified has reviewed it; it has no permit, code or engineering status. Compliance: not checked.

## Strategy

A lower storey under the road-level entry combines an embedded massing with a stepped downhill wing. Compare its cut, void, retaining walls, floor area, daylight and circulation against the other options; additional storeys can overfill the program. Walk-out doors and terraces remain unresolved.

## Levels

- **Entry level** (FFL +11.67 m local): Entrance hall, Dining, Kitchen, Living room, Stair, Flexible space (not in program), Garage, Terrace
- **Level -3.00 m from entry** (FFL +8.67 m local): En-suite bathroom, Main bedroom, Laundry, Stair, Stair, Flexible space (not in program), Stair hall
- **Level -4.50 m from entry** (FFL +7.17 m local): Child's bedroom 1, Child's bedroom 2, Bathroom 1, Study 1, Plant / technical room, Stair, Stairwell

## Rooms

| Room | Level | Area m² | Program target m² | Program min m² |
|---|---|---:|---:|---:|
| Corridor | lv-entry | 8.4 | — | — |
| Corridor | lv-down-300 | 8.4 | — | — |
| Corridor | lv-down-450 | 8.0 | — | — |
| Entrance hall | lv-entry | 7.7 | 6.0 | 4.0 |
| Dining | lv-entry | 10.2 | 14.0 | 10.0 |
| Kitchen | lv-entry | 8.2 | 12.0 | 8.0 |
| Living room | lv-entry | 19.4 | 25.0 | 16.0 |
| En-suite bathroom | lv-down-300 | 8.6 | 5.0 | 3.5 |
| Main bedroom | lv-down-300 | 17.3 | 15.0 | 12.0 |
| Child's bedroom 1 | lv-down-450 | 13.0 | 11.0 | 9.0 |
| Child's bedroom 2 | lv-down-450 | 11.8 | 11.0 | 9.0 |
| Bathroom 1 | lv-down-450 | 8.6 | 6.0 | 4.0 |
| Study 1 | lv-down-450 | 10.1 | 9.0 | 6.0 |
| Laundry | lv-down-300 | 8.6 | 6.0 | 4.0 |
| Plant / technical room | lv-down-450 | 6.3 | 4.0 | 3.0 |
| Stair | lv-entry | 15.4 | 10.0 | 8.0 |
| Stair | lv-down-300 | 15.4 | 10.0 | 8.0 |
| Stair | lv-down-300 | 11.9 | 10.0 | 8.0 |
| Stair | lv-down-450 | 10.6 | 10.0 | 8.0 |
| Flexible space (not in program) | lv-down-300 | 9.6 | — | — |
| Flexible space (not in program) | lv-entry | 10.6 | — | — |
| Stairwell | lv-down-450 | 1.7 | — | — |
| Stair hall | lv-down-300 | 1.7 | — | — |
| Garage | lv-entry | 36.0 | 36.0 | 30.0 |
| Terrace | lv-entry | 14.4 | 16.0 | 10.0 |

## Measured results and trade-offs

Status in brackets when a value is not measured exactly.

- Gross floor area (centreline): 281.70 m²
- Footprint: 184.14 m²
- Levels: 3
- Storeys: 2 (inferred)
- Programmed room area: 218.94 m²
- Flexible area not in the program: 20.16 m²
- Circulation share: 0.32
- Hard adjacencies met: 5
- Soft adjacency score (0-1): 0.85
- Level preferences met: 9
- Longest walk from the front door: 36.21 m
- Routes to shared rooms through private rooms: 0
- Walls between private and public rooms: 1
- Footprint compactness (1 = circle): 0.22
- Excavation below floors: 102.35 m³ (inferred)
- Underfloor void (support unspecified): 166.26 m³ (inferred)
- Proposed engineered fill (explicit pads only): not checked
- Maximum underfloor gap (see slab basis): 4.20 m (inferred)
- Deepest cut: 3.24 m (inferred)
- Retaining wall length: 27.60 m (inferred)
- Retained earth face: 36.08 m² (inferred)
- Closest approach to the envelope edge: 0.10 m

## Violations (0 hard, 57 soft)

- **soft** `required_daylight_no_exterior_window`: sp-bed-main requests daylight but has no exterior window; borrowed light and actual illumination are not checked
- **soft** `required_daylight_no_exterior_window`: sp-bed-child-1 requests daylight but has no exterior window; borrowed light and actual illumination are not checked
- **soft** `elongated_room`: sp-bath-ensuite has a 3.4:1 aspect ratio; check furniture and clear usable dimensions (3:1 is a conceptual review trigger, not a code limit)
- **soft** `soft_adjacency_unmet`: adj-10-study-1-entry: pi-study-1 near pi-entry is not met
- **soft** `soft_adjacency_unmet`: adj-12-laundry-kitchen: pi-laundry near pi-kitchen is not met
- **soft** `elevated_floor_support_unresolved`: Underfloor void is 166.3 m³, maximum 4.20 m. This is not specified engineered fill; supports, lateral stability, foundations and drainage unresolved.
- **soft** `large_underfloor_void`: Void clear height 4.20 m exceeds configured 4 m concept-review trigger.
- **soft** `garage_ramp_grade_review`: Straight candidate grade -17.2% exceeds configured concept trigger; no designed ramp or regulatory compliance established.
- **soft** `needs_professional_structure`: Concept load paths, lateral stability and support systems unresolved — needs professional.
- **soft** `needs_professional_foundations`: Bearing capacity, settlement and footing depths unverified — needs professional.
- **soft** `needs_professional_slope_stability`: Survey TIN does not establish geotechnical or slope stability — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
- **soft** `needs_professional_retaining`: Earth-contact wall needs engineered retaining design — needs professional.
- **soft** `needs_professional_drainage`: Uphill earth-contact face: intercept and discharge routes unresolved — needs professional.
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
- **soft** `needs_professional_foundations`: Terrace supports, edge protection and garden approach unresolved — needs professional.
- **soft** `needs_professional_waterproofing`: Building-ground moisture details unverified — needs professional.
- **soft** `terrain_triangle_review`: Triangle 2 at (12.153666666666664, 0.5386666666666667): sliver; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 6 at (16.392333333333333, 1.4393333333333334): sliver; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 18 at (-3.4733333333333336, 11.530000000000001): sliver, steep_review; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 28 at (23.761, 8.458333333333334): sliver, steep_review; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 29 at (23.206333333333333, 11.067): sliver, steep_review; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 46 at (20.711333333333336, 22.804333333333332): sliver, steep_review; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 50 at (1.2619999999999998, 30.93866666666667): sliver; survey review needed, no smoothing.
- **soft** `terrain_triangle_review`: Triangle 53 at (5.500333333333333, 31.839333333333336): sliver; survey review needed, no smoothing.
- **soft** `height_limit_exceeded`: Height 11.55 m exceeds envelope 10 m.
- **soft** `kitchen_no_sampled_fit`: No arrangement in the declared discrete template search; continuous infeasibility has not been proved.
- **soft** `living_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `living_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `living_through_traffic`: Portal desire line crosses a work/seating zone; alternate routes may exist.
- **soft** `excess_circulation`: Circulation share exceeds the conceptual assumption.
- **soft** `excess_circulation`: Circulation share exceeds the conceptual assumption.
- **soft** `bedroom_noise_stacking`: Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown.
- **soft** `bedroom_noise_stacking`: Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown.
- **soft** `low_daylight_opportunity`: Unburied glazing ratio is below assumption; no daylight simulation.
- **soft** `low_daylight_opportunity`: Unburied glazing ratio is below assumption; no daylight simulation.
- **soft** `outdoor_door_grade_mismatch`: Door threshold is 0.351 m relative to grade; check landing/ramp.

Not evaluated (no evaluator yet): DaylightEvaluator, SolarEvaluator, AccessibilityEvaluator, LifeSafetyEvaluator, StructuralConceptEvaluator, MEPConceptEvaluator, CostEvaluator, EnergyEvaluator, CulturalFitEvaluator.

## Assumptions

- [assumption] Room areas are measured to wall centerlines; net floor areas are smaller.
- [assumption] Floor-to-floor height 3 m; split levels step in half storeys of 1.5 m; walls 2.8 m high.
- [assumption] Exterior and retaining walls 0.3 m, partitions 0.15 m thick; no structural design has been done.
- [assumption] Plan grid: u axis along the parcel edge nearest road road-uphill.
- [assumption] Initial entry reference from the mean surveyed ground along the road-side face (11.70 m local), interpolated from the survey TIN (inferred).
- [assumption] A full floor below the road-level entry reuses its footprint; the downhill wing steps from that floor toward its own surveyed ground, rather than inheriting the entry bar's terrain offset. The walk-out is a massing intent: exterior doors, terraces, waterproofing, drainage and structural support still need design. There is no excavation-depth limit or preference for minimizing excavation.
- [assumption] Garage: separate road-level volume 6 × 6 m beside the entry bar (DEC-12).
- [assumption] Floor elevations and bar positions/lengths solved jointly with TIN lookup; sectional contact bands and circulation/daylight objectives, no excavation/void penalty. Earthworks evaluated exactly afterward.
- [assumption] Stair risers at most 0.18 m with 0.28 m goings; typical comfortable geometry, not checked against any code.
- [assumption] The garage is a separate road-level volume, 6 m wide and 6 m deep for its cars (DEC-12).
- [assumption] Rows are closed with flexible spaces that are not in the program (storage, or space to give back).
- [assumption] The plan is kept inside the buildable envelope (synthetic setbacks (3 m road side, 2 m sides, 3 m rear) invented for the example; not a zoning rule).
- [inference] Level elevations, earth contact and retaining walls are inferred by linear interpolation of the surveyed points; ground between survey points is not verified.

## Open issues

- [warning] Retaining walls, excavation, slope drainage and foundations need geotechnical and structural engineering; nothing here is engineered.
- [warning] No fixture layout found for sp-kitchen; the sampled study reports on it

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

- Generator `house-ai-cpsat-bars` 0.2.0, solver ortools-cp-sat 9.15.6755: OPTIMAL, objective 26411, seed 0, deterministic-time budget 4.
- Parameters: b-walkout_length_m=7.0, b-walkout_start_m=6.1, b0_length_m=7.0, b0_start_m=6.1, b1_length_m=6.7, b1_start_m=6.4, back_row_depth_m=4.2, corridor_width_m=1.2, front_row_depth_m=4.8, hybrid_walkout=True, level_elevations_m=7.17, 8.67, 11.67, level_solver=joint_cpsat_terrain_lookup_5cm_xy_1cm_z, levels=3, strategy=split_walkout.
- Inputs: site/site v1 (c2d20667c325), space_program/program v1 (daac5729ee86)
