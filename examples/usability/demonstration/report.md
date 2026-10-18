# Synthetic hillside usability report

Exploratory software demonstration; no homeowner or professional approvals.

All planning thresholds are assumptions; every finding cites canonical IDs.

| Strategy | Generated | Integrity clean | Usability findings | Not checked |
|---|---|---|---:|---:|
| compact | generated | True | 16 | 26 |
| split_level | generated | True | 21 | 25 |
| linear | generated | True | 12 | 11 |

Furniture uses a 0.1 m, four-rotation search. A failure means no sampled fit,
not continuous infeasibility. Routes are point paths through net-floor polygons;
they do not certify wheelchair width. Unknown stair direction, vehicle dimensions,
and terrain coverage remain not checked. Solar/daylight and airflow are not simulated.

## Findings

### compact

- `net_wall_basis_incomplete` (sp-corridor-b0): Net area subtracts modelled walls only; wall thickness is missing on edges. [inferred]
- `net_wall_basis_incomplete` (sp-corridor-b1): Net area subtracts modelled walls only; wall thickness is missing on edges. [inferred]
- `net_wall_basis_incomplete` (sp-living): Net area subtracts modelled walls only; wall thickness is missing on edges. [inferred]
- `stair_height_mismatch` (st-0, lv-down-300, lv-entry): Riser total disagrees with connected floor elevations. [measured]
- `dining_no_sampled_fit` (sp-dining): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `kitchen_no_sampled_fit` (sp-kitchen): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_double_no_sampled_fit` (sp-bed-main): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_double_no_sampled_fit` (sp-bed-child-1): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_double_no_sampled_fit` (sp-bed-child-2): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `laundry_folding_no_sampled_fit` (sp-laundry): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bedroom_noise_stacking` (sp-bed-main, sp-living): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-child-1, sp-kitchen): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-child-2, sp-kitchen): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-child-2, sp-living): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `low_daylight_opportunity` (sp-study-1): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `outdoor_door_grade_mismatch` (d-garage-garage-ext, w-entry-002, sp-garage): Door threshold is 0.281 m relative to grade; check landing/ramp. [inferred]

### split_level

- `net_wall_basis_incomplete` (sp-corridor-b0): Net area subtracts modelled walls only; wall thickness is missing on edges. [inferred]
- `net_wall_basis_incomplete` (sp-corridor-b1): Net area subtracts modelled walls only; wall thickness is missing on edges. [inferred]
- `net_wall_basis_incomplete` (sp-living): Net area subtracts modelled walls only; wall thickness is missing on edges. [inferred]
- `net_wall_basis_incomplete` (sp-stair-0a): Net area subtracts modelled walls only; wall thickness is missing on edges. [inferred]
- `stair_height_mismatch` (st-0, lv-down-300, lv-entry): Riser total disagrees with connected floor elevations. [measured]
- `dining_no_sampled_fit` (sp-dining): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `kitchen_no_sampled_fit` (sp-kitchen): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_double_no_sampled_fit` (sp-bed-main): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_double_no_sampled_fit` (sp-bed-child-1): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_single_no_sampled_fit` (sp-bed-child-1): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_double_no_sampled_fit` (sp-bed-child-2): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_single_no_sampled_fit` (sp-bed-child-2): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `laundry_folding_no_sampled_fit` (sp-laundry): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-kitchen-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `living_through_traffic` (sp-living, d-living-corridor-b0, o-dining-living): Portal desire line crosses a work/seating zone; alternate routes may exist. [inferred]
- `excess_circulation` (lv-down-300, sp-corridor-b1, sp-stair-0b): Circulation share exceeds the conceptual assumption. [inferred]
- `bedroom_noise_stacking` (sp-bed-main, sp-kitchen): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `bedroom_noise_stacking` (sp-bed-main, sp-living): Noisy activity beside/above/below sleeping space; acoustic assembly performance is unknown. [inferred]
- `low_daylight_opportunity` (sp-dining): Unburied glazing ratio is below assumption; no daylight simulation. [inferred]
- `outdoor_door_grade_mismatch` (d-front-entry-ext, w-entry-001, sp-entry): Door threshold is 0.471 m relative to grade; check landing/ramp. [inferred]
- `outdoor_door_grade_mismatch` (d-garage-garage-ext, w-entry-002, sp-garage): Door threshold is 0.309 m relative to grade; check landing/ramp. [inferred]

### linear

- `net_wall_basis_incomplete` (sp-corridor-b0): Net area subtracts modelled walls only; wall thickness is missing on edges. [inferred]
- `net_wall_basis_incomplete` (sp-living): Net area subtracts modelled walls only; wall thickness is missing on edges. [inferred]
- `dining_no_sampled_fit` (sp-dining): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `kitchen_no_sampled_fit` (sp-kitchen): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_double_no_sampled_fit` (sp-bed-main): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_double_no_sampled_fit` (sp-bed-child-1): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `bed_double_no_sampled_fit` (sp-bed-child-2): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
- `laundry_folding_no_sampled_fit` (sp-laundry): No arrangement in the declared discrete template search; continuous infeasibility has not been proved. [inferred]
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
