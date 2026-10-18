# Plan concepts compared

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

Each column is one concept; values are individual metrics, not a combined score. Status in brackets when not measured exactly.

| Metric | concept-compact | concept-split-level | concept-linear | concept-two-wing | concept-split-walkout |
|---|---|---|---|---|---|
| Strategy | compact | split_level | linear | two_wing | split_walkout |
| Hard violations | 0 | 0 | 0 | 0 | 0 |
| Soft violations | 14 | 12 | 18 | 12 | 23 |
| Gross floor area (centreline) | 240.00 m² | 222.24 m² | 210.00 m² | 202.08 m² | 289.20 m² |
| Footprint | 120.00 m² | 222.24 m² | 210.00 m² | 202.08 m² | 175.20 m² |
| Floor levels | 2 | 2 | 1 | 2 | 3 |
| Programmed room area | 216.00 m² | 198.72 m² | 189.00 m² | 180.00 m² | 225.84 m² |
| Flexible area not in the program | 0 m² | 0 m² | 0 m² | 0 m² | 33.36 m² |
| Circulation share | 0.25 | 0.24 | 0.14 | 0.21 | 0.30 |
| Hard adjacencies met | 5 | 5 | 5 | 5 | 5 |
| Soft adjacency score (0-1) | 0.83 | 0.91 | 0.83 | 0.91 | 0.83 |
| Level preferences met | 9 | 9 | 9 | 9 | 9 |
| Longest walk from the front door | 35.00 m (inferred) | 31.00 m | 24.87 m | 27.79 m | 44.49 m (inferred) |
| Routes to shared rooms through private rooms | 0 | 0 | 0 | 0 | 0 |
| Walls between private and public rooms | 1 | 0 | 2 | 0 | 0 |
| Footprint compactness (1 = circle) | 0.37 | 0.25 | 0.22 | 0.16 | 0.28 |
| Excavation below floors | 104.13 m³ (inferred) | 0.00 m³ (inferred) | 0.04 m³ (inferred) | 0.00 m³ (inferred) | 109.91 m³ (inferred) |
| Underfloor void (fill/support unspecified) | 39.54 m³ (inferred) | 649.37 m³ (inferred) | 484.68 m³ (inferred) | 552.41 m³ (inferred) | 98.72 m³ (inferred) |
| Maximum floor height over terrain | 1.99 m (inferred) | 6.00 m (inferred) | 4.99 m (inferred) | 5.16 m (inferred) | 2.82 m (inferred) |
| Deepest cut | 2.73 m (inferred) | 0.00 m (inferred) | 0.07 m (inferred) | 0.00 m (inferred) | 2.73 m (inferred) |
| Retaining wall length | 22.00 m | 0 m | 0 m | 0 m | 23.30 m |
| Retained earth face | 44.38 m² (inferred) | 0.00 m² (inferred) | 0.00 m² (inferred) | 0.00 m² (inferred) | 44.95 m² (inferred) |
| Closest approach to the envelope edge | 0.10 m | 0.10 m | 0.10 m | 0.10 m | 0.10 m |

## How different the concepts are (measured)

| Pair | Footprint overlap (IoU) | Rooms on a different level | Levels/stairs |
|---|---:|---:|---|
| concept-compact / concept-split-level | 0.54 | 21% | 2/1 vs 2/1 |
| concept-compact / concept-linear | 0.57 | 62% | 2/1 vs 1/0 |
| concept-compact / concept-two-wing | 0.34 | 14% | 2/1 vs 2/1 |
| concept-compact / concept-split-walkout | 0.63 | 36% | 2/1 vs 3/2 |
| concept-split-level / concept-linear | 0.52 | 38% | 2/1 vs 1/0 |
| concept-split-level / concept-two-wing | 0.65 | 21% | 2/1 vs 2/1 |
| concept-split-level / concept-split-walkout | 0.55 | 36% | 2/1 vs 3/2 |
| concept-linear / concept-two-wing | 0.45 | 54% | 1/0 vs 2/1 |
| concept-linear / concept-split-walkout | 0.42 | 62% | 1/0 vs 3/2 |
| concept-two-wing / concept-split-walkout | 0.44 | 36% | 2/1 vs 3/2 |

## Strategies that could not be laid out

- **courtyard**: rows 4.8/4.2 m: no room for a second pavilion behind a garden court: no 6 m long strip of the envelope is 10.2 m deep at 17.1 m from the road edge; rows 4.2/4.2 m: no room for a second pavilion behind a garden court: no 6 m long strip of the envelope is 9.6 m deep at 17.1 m from the road edge; rows 5.4/5.4 m: no room for a second pavilion behind a garden court: no 6 m long strip of the envelope is 12 m deep at 17.1 m from the road edge

These are design explorations. None is reviewed, engineered or checked against a building code; see docs/PROFESSIONAL_HANDOFF.md.
