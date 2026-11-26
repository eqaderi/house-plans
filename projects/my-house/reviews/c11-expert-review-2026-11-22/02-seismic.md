# 02 · Seismic and lateral stability: review of C11

This is a concept-stage review only: nothing is engineered, code-checked or geotechnically verified. These are `assumption`: hazard (Standard 2800, high, kh 0.2), K₀ 0.5, γ 19 kN/m³, φ 30° and μ 0.5. Soil, rock and frost depth are **unknown**. Torsion and thrust figures are my own `inferred` estimates (±30 %).

## Summary

1. For gravity, C11 answers stmt-027: every slab is supported, the master stilts are gone, and the garage stands on walls.
2. Laterally the house is still buried NW and open SE. The main storey's eccentricity is about 4.5 m both ways, against a target of 1.2–1.8 m, and nothing checks it.
3. More walls are now integral, so the uphill earth thrust has tripled since C10 (about 3.6 MN in an earthquake). Sliding FS ≈ 0.75.
4. New weak points: short or captive 0.30 m balcony columns, the road SE corner on a 0.30 m pier, the pile wall overlapping the house wall, and a 0.25 m core wall retaining 3.6 m.
5. Separating the uphill retaining walls from the frame fixes torsion and thrust together.

## Scorecard

SCORECARD: fixed=3 partly=6 not_fixed=2 worse=0 new_blocker=0 new_major=6 new_minor=2

## Part A · C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| SEI-01 | **fixed** | `measured`: lower north wall on v 1.1, u 9.4–18 (0.45 m) under the main north wall; main plate 0 m² unsupported | — |
| SEI-02 | **fixed** | `measured`: service room dug to 1673.60; MW-0F, MW-2.0, 2.8, 3.8, 4.6, 7.3 and MB-9.5 carry the garage; 0 m² unsupported | Minor: the shutter piers are 0.475, 0.75 and 0.475 m, and RB-5.3 sits on the 0.75 m pier. Draw RC portals with lintels ≥ 0.6 m deep |
| SEI-03 (BLOCKER) | **not fixed** | `inferred`, main storey: mass centre (7.95, 7.10), stiffness centre (3.0–3.7, 2.5–2.7), so e_u 4.3–4.9 m (24–27 %) and e_v 4.4–4.6 m (37–39 %). Lower storey: e_v 2.6–5.9 m (18–40 %). No check in `checks.py` | The buried v 1.1 wall is about 12× stiffer than any south panel, so adding walls cannot balance it. Use route A (N01). Add a stiffness/mass-centre check that fails when e > 0.1 L |
| SEI-04 | **partly fixed** | `measured`: RC-18L and MW-SE built. Main east about 70 % solid (was 29 %), lower east 43 % plus RC-18L. Main south 39 %, piers 0.30–0.65 m. Only MW-SE and RC-18L are declared RC | Make these RC 0.30 elements: u 18 v 1.1–3.2/3.3 (both floors), u 18 v 5.0–6.7 (main), v 13 u 3.9–5.35 (main) |
| SEI-05 | **partly fixed** | `measured`: lift RC. The spine u 8.0 exists only at lower level; at main and road it is a 0.2 × 3.4 m "bench", absent from `core_walls()`. Stair mouth open 2.6 m at main and road. No collectors or sliding bearings | RC spine at main and road; 0.6 m stubs at u 6.8 and 9.4 on v 7.3 with a 0.6 m coupling beam; one sliding bearing per flight |
| SEI-06 | **partly fixed** | `measured`: grid adopted, east walls on u 18, road south on v 13. Remaining notches: lower NW 2.2 × 6.2 m (16/42 %), loggia 2.6 × 4.8 m (19/33 %), road storey L 3.2 × 6.2 m (25/52 %) | Drag beams: lower v 7.3 (u 4.6–6.8); lower v 10.95 and u 15.4; road roof v 7.3 (u 9.4–12.6) |
| SEI-07 | **partly fixed** | `measured`: v 13 columns equal and continuous; plate centroids u 5.88 / 9.27 / 11.35 (shift 5.5 m, unchanged). New unequal column line on u 19.6 | N03 |
| SEI-08 | **partly fixed** | `measured`: integral walls now drawn. Joints are only a note; W1 touches the house at (0, 11.6); PW-N overlaps the house wall. `inferred` thrust: 2.2 + 1.4 MN (C10: 0.59 + 0.47) | N01, N02, N07 |
| SEI-09 | **fixed** | `measured`: tanks on the ground slab; extensive green roof; pavers on pedestals | Compute snow and drift (`assumption` 1.5–2.6 kPa) |
| SEI-10 | **partly fixed** | `measured`: worst fill 0.90 m; lounge east, loggia and `t-low` suspended | Draw the lower east wall's footing (u 18, ground 1669.6→1668.3) at ≤ 1667.8, plus grade beams both ways |
| SEI-11 | **not fixed** | `measured`: no collectors. The on-grade west slab joins the suspended east only through the band v 7.3–13, beside the 4.6 × 6.2 m void | Collectors 300 × 500 on v 1.1 and v 7.3, u 0–12.6; dowel or joint the on-grade slab |

## Part B · New problems

| ID | Sev. | Where | Finding | Correction |
|---|---|---|---|---|
| SEI-N01 | MAJOR | West and north walls | Integral thrust ≈ 3.6 MN; sliding FS ≈ 0.75 | Route A: separate retaining walls |
| SEI-N02 | MAJOR | PW-N, v 0.85 | Piles overlap the house wall by 0.225 m; toe only 0.8 m below formation | Declare it integral, or move it to v 0.50 and deepen the toe |
| SEI-N03 | MAJOR | C-B/*, u 19.6 | 0.30 m columns, 3.6 m vs 6.6 m clear; captive | Sleeve, 0.40 m, tie beam at 1670 |
| SEI-N04 | MAJOR | (12.6, 13.0); v 13 road floor | Corner on a 0.30 m pier; no beam; checker counts openings as walls | MB-13.0; fix `storey_walls()` |
| SEI-N05 | MAJOR | Lower u 6.8, v 1.1–7.3 | 0.25 m wall retains 3.6 m, unpropped | 0.45 m RC |
| SEI-N06 | MAJOR | W2 + W3 | Stepped 4.45 m road walls; W2 footing sits in W3's wedge | One U-trough |
| SEI-N07 | MINOR | Forecourt deck, W1 | Tied to the house | Bearings, drawn joints |
| SEI-N08 | MINOR | All "wall" elements | RC or masonry not stated | Lateral-system sheet |

## Part B details

**SEI-N01 · Global sliding (`inferred`).** Integral walls and the height they retain:
- u 0, v 1.1–9.5: 4.47 m plus traffic, over 8.4 m;
- u 4.6: 3.6–4.2 m, over 8.45 m;
- core u 6.8: 3.6 m, over 6.2 m.

The earth pushes the house east with about 2.2 MN statically (surcharges included) and about 1.4 MN more in an earthquake (Wood). Weight is about 7.3 MN, so base shear is about 1.1–1.5 MN. Demand is about 4.9 MN against friction of about 3.6 MN, so FS ≈ 0.75. The downhill side gives no passive resistance.

- **Route A:** free-standing cantilever walls on u 0 (base about 2.8 m, under the service room), u 4.6 and u 6.8, each with a ≥ 100 mm joint. This also removes the NW stiffness behind SEI-03.
- **Route B:** keep the walls integral and add shear keys 0.6 m deep under the grade beams on u 15.4 and u 18, sized from a geotechnical μ.

**SEI-N02 · North pile wall (`measured`).** The house wall's outer face is at v 0.85, and the Ø450 piles centred on v 0.85 fill v 0.625–1.075, so they overlap the wall. Their toe (1668.6) is only 0.8 m below lower formation (1669.4) where 3.3–4.2 m is retained. They cannot cantilever, so the house must prop them, taking about 1.0 MN southward, eccentric (u 0–13.2).

Either declare an integral lining and design the v 1.1 collectors for that thrust, or move the piles to v 0.50 (100 mm gap) with the toe at about 1664.5.

**SEI-N03 · Balcony columns (`measured`).** Clear height to 1673.60:
- C-B/2.75, 6.2, 9.4 and 12.8 pass through `t-low` at 1669.98: 3.62 m clear.
- C-B/16.2 stands on ground at 1666.98: 6.62 m clear, about 6× more flexible on the same beam BB-19.6, with λ = 22.

FW-19.3 is 50 mm from the column faces, and C-B/12.8 sits on FW-12.8T.

Correction:
- Sleeve the columns through `t-low` with a 50 mm joint.
- Move FW-19.3 to u 19.0.
- Make the columns 0.40 × 0.40.
- Tie C-B/16.2 to RC-18L at 1670.0.

**SEI-N04 · Hidden discontinuities (`measured`).** The road SE corner (roof, RW-12.6 and the south wall end) stands on a 0.30 m pier between the dining window (to u 12.4) and the living slider (from u 12.7). The pier lands on LB-13.0, 1.5 m from C-11.1.
- MB-9.4 and MB-12.6 also end on the glazed v 13 line.
- RW-6.8, RW-9.4, RW-9.5 and RW-12.6 stand on beams.

§7.1 and §7.2 pass only because `storey_walls()` counts the whole perimeter, openings included.

Correction:
- Add MB-13.0, 300 × 600, along u 2.0–18.0 at 1677.5, on the five v 13 columns.
- Make the road walls on beams lightweight (≤ 1 kPa) with sliding heads.
- Subtract `Door`/`Win` spans in `storey_walls()`.

**SEI-N05 · Core wall used as a retaining wall (`inferred`).** The on-grade main slab (u 4.6–6.8, v 1.1–7.3) rests on a block of soil. That block is held only by the 0.25 m core wall on u 6.8 and by v 7.3, with the stair void on the east side. The wall spans 6.2 m under about 50 kPa at its base and needs 0.40–0.45 m.

Correction: 0.45 m RC, as C11-THM-01 requires.

**SEI-N06 · Stepped road walls (`inferred`).** W2 (base 1675.0) stands 1.725 m from W3 (base 1673.0, H ≈ 3.0–3.4 m). W3's active wedge is about 1.7–2.0 m wide statically and about 2.5–3 m in an earthquake, so W2's footing, the road behind it and its traffic surcharge W3.

Correction: one RC U-trough under flight 1 with a shear key, designed as a single 4.45 m wall for traffic plus seismic load, with a geotechnical global-stability check.

**SEI-N07.** The deck bears on MW-0F, and W1 meets RC-0. Correction: a corbel with a sliding bearing, and drawn 100 mm joints at (0, 11.6).

**SEI-N08.** Only the core, the lift, RC-18L, MW-SE and the retaining walls are clearly RC; MW-6.2 is masonry. Correction: a sheet with the RC hatched, infill isolated (20 mm gaps, ties), and a table of mass and stiffness centres per storey.

## What C11 gets right

- One structure model in every view; the support sheet answers stmt-027.
- The master stilts and the garage voids are gone, and walls stand over walls on v 1.1 and on u 18.
- The columns on v 13 run continuously, are equal in height and are hidden in partitions; no column stands on a slab.
- RC-18L and MW-SE stiffen the SE corner.
- Tanks on the ground; light green roof; one diaphragm at 1677.5.
- No ground-bearing slab sits on more than 0.90 m of fill.

## Out-of-scope notes

- C-6.8/9.5 overlaps the hall–kitchen opening by 75 mm.
- Geotechnical investigation F1 decides between route A and route B.
