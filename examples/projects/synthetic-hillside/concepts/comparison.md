# Plan concepts compared

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

Each column is one concept; values are individual metrics, not a combined score. Status in brackets when not measured exactly.

| Metric | concept-compact | concept-split-level | concept-linear | concept-two-wing | concept-split-walkout |
|---|---|---|---|---|---|
| Strategy | compact | split_level | linear | two_wing | split_walkout |
| Hard violations | 0 | 0 | 0 | 0 | 0 |
| Soft violations | 58 | 36 | 35 | 34 | 60 |
| Gross floor area (centreline) | 240.00 m² | 231.76 m² | 210.00 m² | 210.24 m² | 293.58 m² |
| Footprint | 120.00 m² | 222.24 m² | 210.00 m² | 202.08 m² | 176.22 m² |
| Floor levels | 2 | 2 | 1 | 2 | 3 |
| Programmed room area | 216.00 m² | 198.72 m² | 189.00 m² | 180.00 m² | 224.28 m² |
| Flexible area not in the program | 0 m² | 0 m² | 0 m² | 0 m² | 35.82 m² |
| Circulation share | 0.25 | 0.27 | 0.14 | 0.24 | 0.31 |
| Hard adjacencies met | 5 | 5 | 5 | 5 | 5 |
| Soft adjacency score (0-1) | 0.83 | 0.91 | 0.83 | 0.91 | 0.83 |
| Level preferences met | 9 | 9 | 9 | 9 | 9 |
| Longest walk from the front door | 33.62 m | 25.17 m | 22.45 m | 23.03 m | 38.59 m |
| Routes to shared rooms through private rooms | 0 | 0 | 0 | 0 | 0 |
| Walls between private and public rooms | 1 | 0 | 2 | 0 | 0 |
| Footprint compactness (1 = circle) | 0.78 | 0.13 | 0.22 | 0.37 | 0.35 |
| Excavation below floors | 142.56 m³ (inferred) | 3.72 m³ (inferred) | 1.23 m³ (inferred) | 3.42 m³ (inferred) | 136.91 m³ (inferred) |
| Underfloor void (support unspecified) | 21.73 m³ (inferred) | 443.52 m³ (inferred) | 419.78 m³ (inferred) | 359.14 m³ (inferred) | 131.85 m³ (inferred) |
| Proposed engineered fill (explicit pads only) | not checked | not checked | not checked | not checked | not checked |
| Maximum underfloor gap (see slab basis) | 4.80 m (inferred) | 4.75 m (inferred) | 4.93 m (inferred) | 4.57 m (inferred) | 4.79 m (inferred) |
| Deepest cut | 3.30 m (inferred) | 1.40 m (inferred) | 0.45 m (inferred) | 1.45 m (inferred) | 3.29 m (inferred) |
| Retaining wall length | 28.60 m (inferred) | 8.20 m (inferred) | 0 m (inferred) | 8.00 m (inferred) | 28.10 m (inferred) |
| Retained earth face | 52.65 m² (inferred) | 4.60 m² (inferred) | 0 m² (inferred) | 4.76 m² (inferred) | 51.20 m² (inferred) |
| Closest approach to the envelope edge | 0.10 m | 0.10 m | 0.10 m | 0.10 m | 0.10 m |

## How different the concepts are (measured)

| Pair | Footprint IoU | Topology dist | Diff level | Levels/stairs | Assessment |
|---|---:|---:|---:|---|---|
| concept-compact / concept-split-level | 0.21 | 0.57 | 64% | 2/1 vs 2/1 | Distinct |
| concept-compact / concept-linear | 0.57 | 0.82 | 62% | 2/1 vs 1/0 | Distinct |
| concept-compact / concept-two-wing | 0.34 | 0.50 | 64% | 2/1 vs 2/1 | Distinct |
| concept-compact / concept-split-walkout | 0.63 | 0.66 | 36% | 2/1 vs 3/2 | Distinct |
| concept-split-level / concept-linear | 0.52 | 0.69 | 38% | 2/1 vs 1/0 | Distinct |
| concept-split-level / concept-two-wing | 0.62 | 0.44 | 21% | 2/1 vs 2/1 | Distinct |
| concept-split-level / concept-split-walkout | 0.24 | 0.73 | 43% | 2/1 vs 3/2 | Distinct |
| concept-linear / concept-two-wing | 0.45 | 0.75 | 54% | 1/0 vs 2/1 | Distinct |
| concept-linear / concept-split-walkout | 0.42 | 0.84 | 62% | 1/0 vs 3/2 | Distinct |
| concept-two-wing / concept-split-walkout | 0.42 | 0.72 | 43% | 2/1 vs 3/2 | Distinct |

## Strategies that could not be laid out

- **courtyard**: rows 4.8/4.2 m: no room for a second pavilion behind a garden court: no 6 m long strip of the envelope is 10.2 m deep at 17.1 m from the road edge; rows 4.2/4.2 m: no room for a second pavilion behind a garden court: no 6 m long strip of the envelope is 9.6 m deep at 17.1 m from the road edge; rows 5.4/5.4 m: no room for a second pavilion behind a garden court: no 6 m long strip of the envelope is 12 m deep at 17.1 m from the road edge

These are design explorations. None is reviewed, engineered or checked against a building code; see docs/PROFESSIONAL_HANDOFF.md.
