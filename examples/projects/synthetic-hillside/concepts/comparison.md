# Plan options compared

> **EXPLORATORY: not stored in the project; the site and/or program are not approved by the owner. Not a validated plan.**

Each column is one plan option; values are individual metrics, not a combined score. Status in brackets when not measured exactly.

| Metric | concept-compact | concept-split-level | concept-linear | concept-two-wing | concept-split-walkout |
|---|---|---|---|---|---|
| Strategy | compact | split_level | linear | two_wing | split_walkout |
| Hard violations | 0 | 0 | 0 | 0 | 0 |
| Soft violations | 53 | 39 | 35 | 36 | 57 |
| Gross floor area (centreline) | 250.46 m² | 238.24 m² | 200.24 m² | 233.54 m² | 281.70 m² |
| Footprint | 151.28 m² | 214.32 m² | 200.24 m² | 226.62 m² | 184.14 m² |
| Levels | 2 | 2 | 1 | 2 | 3 |
| Storeys | 2 (inferred) | 2 (inferred) | 1 (inferred) | 2 (inferred) | 2 (inferred) |
| Programmed room area | 213.48 m² | 185.04 m² | 168.48 m² | 178.50 m² | 218.94 m² |
| Flexible area not in the program | 0 m² | 9.60 m² | 0 m² | 13.02 m² | 20.16 m² |
| Circulation share | 0.23 | 0.25 | 0.11 | 0.19 | 0.32 |
| Hard adjacencies met | 5 | 5 | 5 | 5 | 5 |
| Soft adjacency score (0-1) | 0.93 | 0.93 | 0.85 | 0.93 | 0.85 |
| Level preferences met | 9 | 9 | 9 | 9 | 9 |
| Longest walk from the front door | 27.15 m | 28.99 m | 16.88 m | 20.13 m | 36.21 m |
| Routes to shared rooms through private rooms | 0 | 0 | 0 | 0 | 0 |
| Walls between private and public rooms | 0 | 0 | 2 | 0 | 1 |
| Footprint compactness (1 = circle) | 0.44 | 0.16 | 0.23 | 0.21 | 0.22 |
| Excavation below floors | 123.53 m³ (inferred) | 7.91 m³ (inferred) | 0.69 m³ (inferred) | 2.28 m³ (inferred) | 102.35 m³ (inferred) |
| Underfloor void (support unspecified) | 133.16 m³ (inferred) | 348.35 m³ (inferred) | 379.17 m³ (inferred) | 425.53 m³ (inferred) | 166.26 m³ (inferred) |
| Proposed engineered fill (explicit pads only) | not checked | not checked | not checked | not checked | not checked |
| Maximum underfloor gap (see slab basis) | 5.70 m (inferred) | 4.54 m (inferred) | 5.52 m (inferred) | 5.39 m (inferred) | 4.20 m (inferred) |
| Deepest cut | 3.27 m (inferred) | 1.96 m (inferred) | 0.37 m (inferred) | 0.55 m (inferred) | 3.24 m (inferred) |
| Retaining wall length | 25.50 m (inferred) | 8.20 m (inferred) | 0 m (inferred) | 0 m (inferred) | 27.60 m (inferred) |
| Retained earth face | 38.77 m² (inferred) | 9.17 m² (inferred) | 0 m² (inferred) | 0 m² (inferred) | 36.08 m² (inferred) |
| Closest approach to the envelope edge | 0.10 m | 0.10 m | 0.10 m | 0.10 m | 0.10 m |

## Requested storeys

- **concept-linear**: Requested storeys: 2; this plan option has 1 storey(s) on 1 level(s). The linear strategy places all rooms in one bar on a single level. The requested storey count is not enforced by this strategy; owner review needed.

## How different the plan options are (measured)

| Pair | Footprint IoU | Topology dist | Diff level | Levels/stairs | Assessment |
|---|---:|---:|---:|---|---|
| concept-compact / concept-split-level | 0.71 | 0.42 | 47% | 2/1 vs 2/1 | Distinct |
| concept-compact / concept-linear | 0.59 | 0.64 | 43% | 2/1 vs 1/0 | Distinct |
| concept-compact / concept-two-wing | 0.48 | 0.44 | 13% | 2/1 vs 2/1 | Distinct |
| concept-compact / concept-split-walkout | 0.60 | 0.64 | 47% | 2/1 vs 3/2 | Distinct |
| concept-split-level / concept-linear | 0.48 | 0.68 | 36% | 2/1 vs 1/0 | Distinct |
| concept-split-level / concept-two-wing | 0.44 | 0.31 | 40% | 2/1 vs 2/1 | Distinct |
| concept-split-level / concept-split-walkout | 0.72 | 0.64 | 33% | 2/1 vs 3/2 | Distinct |
| concept-linear / concept-two-wing | 0.47 | 0.62 | 36% | 1/0 vs 2/1 | Distinct |
| concept-linear / concept-split-walkout | 0.41 | 0.78 | 57% | 1/0 vs 3/2 | Distinct |
| concept-two-wing / concept-split-walkout | 0.44 | 0.69 | 47% | 2/1 vs 3/2 | Distinct |

## Strategies that could not be laid out

- **courtyard**: rows 4.8/4.2 m: no room for a second pavilion behind a garden court: no 6 m long strip of the envelope is 10.2 m deep at 16.5 m from the road edge; rows 4.2/4.2 m: no room for a second pavilion behind a garden court: no 6 m long strip of the envelope is 9.6 m deep at 15.9 m from the road edge; rows 5.4/5.4 m: no room for a second pavilion behind a garden court: no 6 m long strip of the envelope is 12 m deep at 17.1 m from the road edge

These are design explorations. None is reviewed, engineered or checked against a building code; see docs/PROFESSIONAL_HANDOFF.md.
