# Synthetic hillside usability report

Exploratory software demonstration; no homeowner or professional approvals.

All planning thresholds are assumptions; every finding cites canonical IDs.

| Strategy | Generated | Integrity clean | Usability findings | Not checked |
|---|---|---|---:|---:|
| compact | generated | True | 14 | 7 |
| split_level | generated | True | 8 | 12 |
| linear | generated | True | 9 | 6 |

Furniture uses a bounded 0.1 m, four-rotation search in each room's own frame.
A failure means no sampled fit, not continuous infeasibility; an undecided search
is not checked. Routes are point paths through net-floor polygons; they do not
certify wheelchair width. Routes across a stair without a walking line are inferred
estimates. Vehicle dimensions and terrain coverage remain not checked when absent.
Solar/daylight and airflow are not simulated.

## Findings

### compact

- `living_through_traffic` (sp-living, d-living-corridor-b0, o-kitchen-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-dining-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, d-living-terrace): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, o-dining-living, d-living-terrace): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `daily_route_long` (sp-garage, sp-kitchen, sp-garage, d-garage-corridor-b0, d-living-corridor-b0, o-kitchen-living, sp-kitchen): garage_to_kitchen: 17.049 m point route. [measured]
- `excess_circulation` (lv-down-300, sp-corridor-b1, sp-stair-0b): Circulation share exceeds the conceptual assumption. [inferred]
- `bedroom_noise_stacking` (sp-bed-main, sp-laundry): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-child-1, sp-kitchen): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_adjacency` (sp-bed-child-1, sp-mechanical): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-child-2, sp-kitchen): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-child-2, sp-living): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `low_daylight_opportunity` (sp-bed-main): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `low_daylight_opportunity` (sp-bed-child-2): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `outdoor_door_grade_mismatch` (d-garage-garage-ext, w-entry-001, sp-garage): Door threshold is 0.391 m relative to grade; check landing/ramp. [inferred]

### split_level

- `kitchen_no_sampled_fit` (sp-kitchen): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-kitchen-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, d-living-terrace): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, o-dining-living, d-living-terrace): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `excess_circulation` (lv-down-450, sp-corridor-b1, sp-stair-0b, sp-stairwell-0): Circulation share exceeds the conceptual assumption. [inferred]
- `low_daylight_opportunity` (sp-living): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `low_daylight_opportunity` (sp-bed-main): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `outdoor_door_grade_mismatch` (d-garage-garage-ext, w-entry-001, sp-garage): Door threshold is 0.401 m relative to grade; check landing/ramp. [inferred]

### linear

- `bed_double_no_sampled_fit` (sp-bed-main): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-kitchen-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-dining-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, d-living-terrace): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, o-dining-living, d-living-terrace): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `daily_route_long` (sp-garage, sp-kitchen, sp-garage, d-garage-corridor-b0, d-living-corridor-b0, o-kitchen-living, sp-kitchen): garage_to_kitchen: 21.979 m point route. [measured]
- `low_daylight_opportunity` (sp-dining): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `low_daylight_opportunity` (sp-bed-child-2): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `outdoor_door_grade_mismatch` (d-garage-garage-ext, w-entry-001, sp-garage): Door threshold is 0.491 m relative to grade; check landing/ramp. [inferred]

## Seeded defects

| Defect | Detected | Clean twin passes |
|---|---|---|
| headroom | True | True |
| short-run | True | True |
| arrival | True | True |
| height | True | True |
| door-bed | True | True |
| wc-front | True | True |
| bed-width | True | True |
| dead-end | True | True |
