# Synthetic hillside usability report

Exploratory software demonstration; no homeowner or professional approvals.

All planning thresholds are assumptions; every finding cites canonical IDs.

| Strategy | Generated | Integrity clean | Usability findings | Not checked |
|---|---|---|---:|---:|
| compact | generated | True | 8 | 12 |
| split_level | generated | True | 9 | 9 |
| linear | generated | True | 5 | 8 |

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
- `bedroom_noise_stacking` (sp-bed-main, sp-living): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-child-1, sp-kitchen): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-child-2, sp-kitchen): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-child-2, sp-living): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `low_daylight_opportunity` (sp-study-1): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `outdoor_door_grade_mismatch` (d-garage-garage-ext, w-entry-002, sp-garage): Door threshold is 0.281 m relative to grade; check landing/ramp. [inferred]

### split_level

- `stair_low_headroom` (st-0, slab-roof-down-300): Pitch-line headroom 1.250 m under slab. [inferred]
- `kitchen_no_sampled_fit` (sp-kitchen): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-kitchen-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-dining-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `daily_route_long` (sp-entry, sp-kitchen, sp-entry, d-entry-corridor-b0, d-living-corridor-b0, o-dining-living, o-kitchen-dining, sp-kitchen): entry_to_kitchen: 17.117 m point route. [measured]
- `excess_circulation` (lv-down-300, sp-corridor-b1, sp-stair-0b): Circulation share exceeds the conceptual assumption. [inferred]
- `low_daylight_opportunity` (sp-dining): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `outdoor_door_grade_mismatch` (d-front-entry-ext, w-entry-001, sp-entry): Door threshold is 0.471 m relative to grade; check landing/ramp. [inferred]
- `outdoor_door_grade_mismatch` (d-garage-garage-ext, w-entry-002, sp-garage): Door threshold is 0.309 m relative to grade; check landing/ramp. [inferred]

### linear

- `kitchen_no_sampled_fit` (sp-kitchen): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-kitchen-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-dining-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `bedroom_noise_adjacency` (sp-bed-main, sp-laundry): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_adjacency` (sp-bed-child-1, sp-mechanical): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]

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
