# 02 · Seismic / lateral stability review of C10

Concept-stage only: nothing here is engineered, code-checked or geotechnically verified. Hazard is `assumption` (Standard 2800, 4th ed., high hazard, A ≈ 0.30–0.35 g; check the zoning table). Soil/rock, friction angle and frost depth are **unknown**.

## Summary

1. C10 is a "step-back" building: soil holds its NW, and its SE is open glass on the tallest supports. That is the worst case for torsion, and it was common in the 2017 M7.3 failures.
2. To the owner's question "what is under it?": **49 % of the garage floor (28 m²) and 19 m² of the master/ensuite floor rest on nothing defined**, over gaps of up to 4.1 m.
3. The only stiff element, the stair + lift core, is an open C-shape about 3.3 m north of the mass centre. It adds to the NW bias instead of balancing it.
4. Integral uphill walls push the house downhill in an earthquake with a force about the size of the whole building's design base shear (inferred).
5. C11 should keep the stacking and the core, square off the plates, add solid walls at the NE and SE corners, have no stilts, stay one structure, and detach every site wall.

## Findings

| ID | Sev. | Where | Issue |
|---|---|---|---|
| SEI-01 | BLOCKER | Main, master/ensuite, u 9.4–17.8, v 1.1–2.8 (+u 9.4–11.4, v 1.1–5.0) | Slab on stilts of 0.9 → 4.1 m: short-column trap |
| SEI-02 | BLOCKER | Road, garage u 0–6.8, v 1.1–9.5 | Half the garage over voids/fill, 0.4–4.1 m deep |
| SEI-03 | BLOCKER | Lower + main storeys | Soil NW and glass SE: large torsional eccentricity |
| SEI-04 | MAJOR | East u 17.8/18, south v 13 / 16.4 | Soft, weak downhill façades; SE corner on 5.5–6 m columns |
| SEI-05 | MAJOR | Core u 6.8–11.4, v 1.1–7.3 | Open C-core; stair flights act as struts |
| SEI-06 | MAJOR | All plates | Re-entrant notches, 0.2 m façade offset, south wall without a wall below |
| SEI-07 | MAJOR | Vertical | Mass shifts 5.7 m west going up; column heights differ along frame lines |
| SEI-08 | MAJOR | All retaining walls | Seismic earth pressure; integral or separate not decided |
| SEI-09 | MAJOR | Roof 1677.45; road plant room | Green roof + deck over the softest wing; tanks over the kitchen |
| SEI-10 | MINOR | Lower slab east; east footings | Slab on up to 1.74 m of fill; footings beside fill walls |
| SEI-11 | MINOR | Main + road slabs | Stair void cuts the diaphragm from its north edge |

## Finding details

**SEI-01 · BLOCKER.** The main floor north of v 2.8, and the ensuite at u 9.4–11.4, have no lower floor below.

*Evidence (`measured`, zg):* slab-to-ground gaps are 0.93 m (u 9.4), 1.6 (11.4), 2.3 (13.2), 3.1 (15.4) and 3.95 m (17.8). The 0.9 m column is about 84× stiffer than the 3.95 m one (1/h³, `inferred`). It takes almost all the shear and fails brittle, the classic 2017 failure (`ai_judgment`).

*Fix:*
- Extend the lower plate north to v 1.1 for u 9.4–18.0. That gives about 19 m² of store/plant, and the main north wall stands on a full-height lower wall.
- Minimum alternative: a continuous RC stem wall along v 1.1 on stepped strip footings, vented behind.
- No isolated columns.

**SEI-02 · BLOCKER.** Of the garage's 57.1 m², 28.2 m² has nothing built under it: u 0–2 for the full depth, u 2–6.8 × v 1.1–2.8, and u 2–3.8 × v 2.8–4.6.

*Evidence (`measured`):*
- Gap to natural ground 0.4–4.1 m, mean 2.43 m, about 69 m³; deepest at (6.8, 2.8), ground 1673.38.
- Fill that deep slumps in an earthquake.
- The road hall at u 0–2, v 9.5–11.6 overhangs the court by 2 m.
- The west wall has only 2.6 m of solid wall in 10.5 m (two 3.35 m shutters, rule 6.7).

*Fix:*
- Build out the main plate to u 2.0–6.8 × v 1.1–4.6 as an on-grade plant + tank room at 1673.60.
- Make the garage slab suspended, on walls everywhere.
- Add an RC wall along u 0, v 1.1–9.5, founded at least 0.5 m into natural ground (1676.7 → 1674.3).
- Frame the shutters as RC portals with deep lintels.

**SEI-03 · BLOCKER.** The lower storey is buried 1.85–3.6 m on its west walls (u 5, u 6.8) and 0–3.6 m on its north walls. Its east and south sides are sliders and the loggia.

*Evidence:*
- Mass above the lower slab is about 540 t, centred at **u 8.9, v 7.5** (`inferred`; 1 t/m² floors, 0.5–0.8 t/m² terraces).
- The stiffness centre is near u 6–7, v 3.5–4.5, because buried walls are near-rigid (`ai_judgment`).
- Eccentricity is therefore 2–3 m east–west and 3–4 m north–south, about 20–35 % of the plan dimension. The SE corner twists most and is also the weakest (SEI-04).

*Fix target for C11:* in each storey and direction, the stiffness centre within 0.1 × the plan dimension (about 1.3–1.6 m) of the mass centre, reached through SEI-04, SEI-05 and SEI-08.

**SEI-04 · MAJOR.** Solid wall as a share of façade length (`measured`):

| Façade | Solid wall | Widest pier |
|---|---|---|
| Main east | 3.4 / 11.9 m (29 %) | 1.1 m |
| Main south | 5.2 / 15.8 m (33 %) | 1.0 m |
| Lower east | 3.2 / 8.8 m | 1.55 m |
| Loggia | 0 % | none |

The living corner over the loggia rests on columns at (18, 13), (18, 16.4) and (15.4, 16.4). They run from natural ground at 1668.0–1667.5 to 1673.60, 5.5–6.1 m clear: the softest supports in the house, at the corner farthest from the stiff NW.

*Fix:*
- RC wall at u 18.0, v 12.8–16.4 (beside the 14 steps), footing to 1673.60. The loggia stays open to the south.
- Main SE L-wall: u 18.0, v 11.6–13.0, plus v 13.0, u 16.4–18.0. The window moves to u 15.0–16.4.
- NE panel on both floors: u 18.0, v 1.1–3.1. The master slider moves to v 3.1–5.5, and the guest east window moves to the north face.
- Lower south pier: u 8.9–10.4. Boys' window u 7.0–8.9.

**SEI-05 · MAJOR.** At road and main level the stair mouth is open over its full 2.6 m width (v 7.3). The core is therefore a C-section, weak in torsion. The dog-leg flights brace the floors diagonally (`ai_judgment`).

*Fix:*
- RC stubs of at least 0.6 m at u 6.8 and u 9.4, leaving a 1.4 m opening, with a 0.6 m deep coupling beam.
- Lift shaft fully RC.
- One end of each flight on a sliding bearing.

**SEI-06 · MAJOR.** Plan irregularities (`measured`):
- The lower plate has four notches: NW (u 5–6.8, v 1.1–7.3), under the ensuite, the north strip (v 1.1–2.8), and the SE loggia (2.6 × 4.8 m, 20 % / 31 %).
- Main east wall u 17.8 against lower east wall u 18.0.
- Road south edge v 13.3 against main south wall v 13.0.
- The main south wall at v 13.0 lands mid-span on the boys'/girls' ceilings.

*Fix:*
- Structural grid. u: 2.0 · 6.8 · 9.4 · 11.4 · 12.6 · 15.4 · 18.0. v: 1.1 · 4.6 · 7.3 · 11.6 · 13.0 · 16.4.
- Both east façades at u 18.0, road south edge at v 13.0, office east wall at u 12.6.
- A v 13.0 beam line in the lower floor, on columns inside the existing partitions at u 6.8 / 11.1 / 15.4.

**SEI-07 · MAJOR.** Plate centroids (`measured`): road u 5.65, main u 10.28, lower u 11.31, so the mass moves 5.7 m west going up. Support heights along single frame lines:
- v 13.0: 0.1 m (u 2), 1.1 m (u 5), 3.6 m (u 6.8–15.4), 5.5 m (u 17.8).
- v 1.1: see SEI-01.

*Fix:* on every frame line, either equal-height columns, or RC walls wherever a column would be under half the height of its neighbours.

**SEI-08 · MAJOR. One structure or joints.**

*Estimate:* integral lower west/core walls, 9.1 m at h 2.6 and 6.2 m at h 3.2. With γ 19 kN/m³, K₀ 0.5 and a Wood increment at kh 0.2, they push east about 1.07 MN, of which 0.47 MN is seismic. Design base shear is only about 0.86 MN (C ≈ 0.15, `assumption`). The downhill side gives no passive resistance.

*Recommendation (`ai_judgment`):*
- **(a) One structure, no internal joint.**
- **(b) Detach every site wall with a gap of at least 100 mm** (`assumption`, ≈ 1 % of the 11 m height). That covers the forecourt (2.8 m), the court walls, the road stair, and the lawn walls (1.6 / 2.4 / 1.1 m). The owner's proposed west-court dig creates a wall of about 3.8–4.0 m holding up the public road. It must be an independent cantilever designed for traffic surcharge plus seismic increment.
- **(c) Uphill house walls retaining more than 1.5 m** (u 5, u 6.8, core north): preferably separate RC walls with a drained 0.6–0.8 m service gap. That is about 40 m³ of extra dig, and it keeps the NW wet rooms dry. Otherwise, design them integral for full seismic earth pressure and balance them with SEI-04. C11 must draw which one it chose.

The natural slope west of the house is 58 % (≈ 30°, `measured` TIN), close to a typical φ. A geotechnical report is needed before sizing.

**SEI-09 · MAJOR.** The green roof (41 m²) and deck (40 m²) sit at 1677.45, above the weakest walls. An intensive green roof adds about 16–25 t saturated (`assumption`), plus snow. The tanks (mass unknown, about 2–4 t) sit at road level, u 3.4–7.0, v 11.6–13.3, over the kitchen, on the plate edge farthest from the core.

*Fix:*
- Extensive green roof with at most 150 mm substrate (≤ 200 kg/m², `assumption`).
- Deck paving on pedestals.
- Tanks into the new NW on-grade room (SEI-02), with a booster pump.

**SEI-10 · MINOR.** East of the 1670 contour the lower slab is up to 1.74 m above natural ground (mean 0.42 m over 55 m², `measured`). The footings at u 18 sit right above the 1.6 m and 2.4 m fill walls.

*Fix:* a suspended slab on stepped strip footings in natural ground, below the influence line of the downhill walls, with grade beams both ways (`assumption`: 2800 practice). Frost depth: unknown.

**SEI-11 · MINOR.** The stair void (u 6.8–9.4, v 1.1–7.3) cuts 6.2 m of the 11.9 m slab depth from the north edge. The on-grade west strip (u 2–5) adjoins suspended slab.

*Fix:* collector beams along v 1.1 and v 7.3, tied to the core. The on-grade strip either jointed from the frame or suspended.

## What C10 gets right

- One continuous core on every floor, at u ≈ 9.1, almost on the east–west mass centre (8.9).
- Each plate is a single level. The roof deck (1677.45) and the garage floor (1677.50) form one diaphragm.
- The plates get smaller going up (156 / 177 / 126 m²), and 84 % of the road plate sits over the main plate.
- The deepest cut is 3.97 m and the NW is not dug, which limits retained heights.
- The 4.3 m bedroom bays (u 6.8 / 11.1 / 15.4) give natural column lines.

## Out-of-scope notes

- Tanks over the kitchen are a leak risk.
- The buried NW wet rooms need tanking and drainage.
- A geotechnical report is needed before C11 freezes wall positions.
- Stair comfort belongs to other reviewers.
