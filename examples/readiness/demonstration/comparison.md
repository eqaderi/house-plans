# Plan concepts compared

Each column is one concept; values are individual metrics, not a combined score. Status in brackets when not measured exactly.

| Metric | concept-compact v1 | concept-split-level v1 | concept-linear v2 | concept-two-wing v3 | concept-split-walkout v1 | concept-open-plan v1 |
|---|---|---|---|---|---|---|
| Strategy | compact | split_level | linear | two_wing | split_walkout | open_plan |
| Hard violations | 0 | 0 | 0 | 0 | 0 | 2 |
| Soft violations | 54 | 35 | 42 | 34 | 51 | 181 |
| Gross floor area (centreline) | 264.00 m² | 231.84 m² | 225.72 m² | 227.28 m² | 314.58 m² | 184.47 m² |
| Footprint | 132.00 m² | 231.84 m² | 225.72 m² | 227.28 m² | 203.70 m² | 119.75 m² |
| Floor levels | 2 | 2 | 1 | 2 | 3 | 2 |
| Programmed room area | 240.00 m² | 208.80 m² | 205.20 m² | 196.26 m² | 232.32 m² | 156.26 m² |
| Flexible area not in the program | 0 m² | 0 m² | 0 m² | 8.10 m² | 51.18 m² | 0 m² |
| Circulation share | 0.25 | 0.24 | 0.13 | 0.20 | 0.31 | 0.09 |
| Hard adjacencies met | 6 | 6 | 6 | 6 | 6 | 6 |
| Soft adjacency score (0-1) | 0.91 | 1.00 | 0.91 | 1.00 | 0.83 | 0.82 |
| Level preferences met | 10 | 10 | 10 | 10 | 10 | 10 |
| Longest walk from the front door | 34.95 m (inferred) | 32.96 m | 26.63 m | 29.62 m | 43.69 m (inferred) | 27.14 m (inferred) |
| Routes to shared rooms through private rooms | 0 | 0 | 0 | 0 | 0 | 0 |
| Walls between private and public rooms | 0 | 0 | 3 | 0 | 1 | 0 |
| Footprint compactness (1 = circle) | 0.77 | 0.17 | 0.30 | 0.16 | 0.42 | 0.40 |
| Excavation below floors | 127.22 m³ (inferred) | 0.54 m³ (inferred) | 1.18 m³ (inferred) | 0.56 m³ (inferred) | 119.56 m³ (inferred) | 445.42 m³ (inferred) |
| Underfloor void (support unspecified) | 41.03 m³ (inferred) | 523.36 m³ (inferred) | 504.27 m³ (inferred) | 489.22 m³ (inferred) | 243.13 m³ (inferred) | 0.00 m³ (inferred) |
| Proposed engineered fill (explicit pads only) | not checked | not checked | not checked | not checked | not checked | not checked |
| Maximum underfloor gap (see slab basis) | 5.31 m (inferred) | 5.35 m (inferred) | 5.45 m (inferred) | 5.31 m (inferred) | 5.28 m (inferred) | 0.00 m (inferred) |
| Deepest cut | 3.30 m (inferred) | 0.34 m (inferred) | 0.44 m (inferred) | 0.34 m (inferred) | 3.27 m (inferred) | 6.10 m (inferred) |
| Retaining wall length | 29.80 m (inferred) | 0 m (inferred) | 0 m (inferred) | 0 m (inferred) | 28.20 m (inferred) | 115.10 m (inferred) |
| Retained earth face | 52.65 m² (inferred) | 0 m² (inferred) | 0 m² (inferred) | 0 m² (inferred) | 47.98 m² (inferred) | 397.73 m² (inferred) |
| Closest approach to the envelope edge | 0.10 m | 0.10 m | 0.10 m | 0.10 m | 0.10 m | 0.00 m |

## How different the concepts are (measured)

| Pair | Footprint IoU | Topology dist | Diff level | Levels/stairs | Assessment |
|---|---:|---:|---:|---|---|
| concept-compact / concept-split-level | 0.09 | 0.51 | 56% | 2/1 vs 2/1 | Distinct |
| concept-compact / concept-linear | 0.58 | 0.74 | 53% | 2/1 vs 1/0 | Distinct |
| concept-compact / concept-two-wing | 0.33 | 0.59 | 56% | 2/1 vs 2/1 | Distinct |
| concept-compact / concept-split-walkout | 0.49 | 0.58 | 50% | 2/1 vs 3/2 | Distinct |
| concept-compact / concept-open-plan | 0.41 | 0.83 | 6% | 2/1 vs 2/1 | Distinct |
| concept-split-level / concept-linear | 0.37 | 0.61 | 33% | 2/1 vs 1/0 | Distinct |
| concept-split-level / concept-two-wing | 0.28 | 0.51 | 12% | 2/1 vs 2/1 | Distinct |
| concept-split-level / concept-split-walkout | 0.02 | 0.59 | 25% | 2/1 vs 3/2 | Distinct |
| concept-split-level / concept-open-plan | 0.22 | 0.87 | 56% | 2/1 vs 2/1 | Distinct |
| concept-linear / concept-two-wing | 0.55 | 0.72 | 40% | 1/0 vs 2/1 | Distinct |
| concept-linear / concept-split-walkout | 0.35 | 0.77 | 60% | 1/0 vs 3/2 | Distinct |
| concept-linear / concept-open-plan | 0.53 | 0.83 | 53% | 1/0 vs 2/1 | Distinct |
| concept-two-wing / concept-split-walkout | 0.35 | 0.62 | 25% | 2/1 vs 3/2 | Distinct |
| concept-two-wing / concept-open-plan | 0.39 | 0.84 | 50% | 2/1 vs 2/1 | Distinct |
| concept-split-walkout / concept-open-plan | 0.23 | 0.88 | 50% | 3/2 vs 2/1 | Distinct |

These are design explorations. None is reviewed, engineered or checked against a building code; see docs/PROFESSIONAL_HANDOFF.md.
