# Plan concepts compared

Each column is one concept; values are individual metrics, not a combined score. Status in brackets when not measured exactly.

| Metric | concept-compact v1 | concept-split-level v1 | concept-linear v2 | concept-two-wing v3 | concept-split-walkout v1 | concept-open-plan-prop-day-up-night-down v1 |
|---|---|---|---|---|---|---|
| Strategy | compact | split_level | linear | two_wing | split_walkout | open_plan |
| Hard violations | 0 | 0 | 0 | 0 | 0 | 0 |
| Soft violations | 55 | 38 | 41 | 43 | 53 | 105 |
| Gross floor area (centreline) | 259.53 m² | 255.48 m² | 228.92 m² | 252.60 m² | 330.36 m² | 202.55 m² |
| Footprint | 148.65 m² | 242.11 m² | 228.92 m² | 235.53 m² | 217.56 m² | 131.81 m² |
| Floor levels | 2 | 2 | 1 | 2 | 3 | 2 |
| Programmed room area | 222.24 m² | 199.26 m² | 183.42 m² | 193.44 m² | 230.04 m² | 163.56 m² |
| Flexible area not in the program | 0 m² | 9.12 m² | 9.90 m² | 12.60 m² | 51.48 m² | 0 m² |
| Circulation share | 0.22 | 0.25 | 0.11 | 0.21 | 0.29 | 0.13 |
| Hard adjacencies met | 6 | 6 | 6 | 6 | 6 | 6 |
| Soft adjacency score (0-1) | 1.00 | 1.00 | 0.94 | 1.00 | 0.88 | 0.58 |
| Level preferences met | 10 | 10 | 10 | 10 | 10 | 10 |
| Longest walk from the front door | 26.48 m | 32.25 m | 22.04 m | 21.94 m | 38.21 m | 28.77 m |
| Routes to shared rooms through private rooms | 0 | 0 | 0 | 0 | 0 | 0 |
| Walls between private and public rooms | 0 | 0 | 0 | 0 | 1 | 0 |
| Footprint compactness (1 = circle) | 0.44 | 0.26 | 0.28 | 0.15 | 0.22 | 0.46 |
| Excavation below floors | 125.42 m³ (inferred) | 4.14 m³ (inferred) | 1.00 m³ (inferred) | 4.19 m³ (inferred) | 120.36 m³ (inferred) | 101.54 m³ (inferred) |
| Underfloor void (support unspecified) | 139.77 m³ (inferred) | 515.30 m³ (inferred) | 490.76 m³ (inferred) | 410.49 m³ (inferred) | 275.79 m³ (inferred) | 153.72 m³ (inferred) |
| Proposed engineered fill (explicit pads only) | not checked | not checked | not checked | not checked | not checked | not checked |
| Maximum underfloor gap (see slab basis) | 6.25 m (inferred) | 6.37 m (inferred) | 5.71 m (inferred) | 5.63 m (inferred) | 6.36 m (inferred) | 6.08 m (inferred) |
| Deepest cut | 3.27 m (inferred) | 1.53 m (inferred) | 0.42 m (inferred) | 1.38 m (inferred) | 3.27 m (inferred) | 3.04 m (inferred) |
| Retaining wall length | 28.00 m (inferred) | 8.20 m (inferred) | 0 m (inferred) | 8.00 m (inferred) | 27.60 m (inferred) | 45.20 m (inferred) |
| Retained earth face | 39.18 m² (inferred) | 5.46 m² (inferred) | 0 m² (inferred) | 4.30 m² (inferred) | 38.03 m² (inferred) | 74.23 m² (inferred) |
| Closest approach to the envelope edge | 0.10 m | 0.10 m | 0.10 m | 0.10 m | 0.10 m | 0.10 m |

## Requested storeys

- **concept-linear**: Requested storeys: 2; generated floor levels: 1. The linear strategy places all rooms in one bar on a single level. The requested storey count is not enforced by this strategy; owner review needed.
- **concept-split-walkout**: Requested storeys: 2; generated floor levels: 3. This strategy derives its floor levels from the massing and terrain; split floor levels need not represent full stacked storeys. The requested storey count is not enforced by this strategy; owner review needed.

## How different the concepts are (measured)

| Pair | Footprint IoU | Topology dist | Diff level | Levels/stairs | Assessment |
|---|---:|---:|---:|---|---|
| concept-compact / concept-split-level | 0.61 | 0.58 | 47% | 2/1 vs 2/1 | Distinct |
| concept-compact / concept-linear | 0.52 | 0.71 | 44% | 2/1 vs 1/0 | Distinct |
| concept-compact / concept-two-wing | 0.46 | 0.56 | 47% | 2/1 vs 2/1 | Distinct |
| concept-compact / concept-split-walkout | 0.65 | 0.67 | 47% | 2/1 vs 3/2 | Distinct |
| concept-compact / concept-open-plan-prop-day-up-night-down | 0.68 | 0.87 | 12% | 2/1 vs 2/1 | Distinct |
| concept-split-level / concept-linear | 0.53 | 0.64 | 31% | 2/1 vs 1/0 | Distinct |
| concept-split-level / concept-two-wing | 0.50 | 0.38 | 6% | 2/1 vs 2/1 | Distinct |
| concept-split-level / concept-split-walkout | 0.86 | 0.64 | 24% | 2/1 vs 3/2 | Distinct |
| concept-split-level / concept-open-plan-prop-day-up-night-down | 0.43 | 0.84 | 53% | 2/1 vs 2/1 | Distinct |
| concept-linear / concept-two-wing | 0.59 | 0.69 | 31% | 1/0 vs 2/1 | Distinct |
| concept-linear / concept-split-walkout | 0.43 | 0.78 | 50% | 1/0 vs 3/2 | Distinct |
| concept-linear / concept-open-plan-prop-day-up-night-down | 0.40 | 0.87 | 50% | 1/0 vs 2/1 | Distinct |
| concept-two-wing / concept-split-walkout | 0.41 | 0.66 | 29% | 2/1 vs 3/2 | Distinct |
| concept-two-wing / concept-open-plan-prop-day-up-night-down | 0.32 | 0.88 | 47% | 2/1 vs 2/1 | Distinct |
| concept-split-walkout / concept-open-plan-prop-day-up-night-down | 0.47 | 0.88 | 41% | 3/2 vs 2/1 | Distinct |

These are design explorations. None is reviewed, engineered or checked against a building code; see docs/PROFESSIONAL_HANDOFF.md.
