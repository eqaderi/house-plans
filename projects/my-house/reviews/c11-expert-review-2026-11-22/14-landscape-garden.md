# 14 · Landscape and outdoor living review of C11 (LND)

Concept stage, nothing engineered. Heights: TIN (inferred). `measured` = from `build()`, `zg` or `GroundModel`. Sun not simulated again.

## Summary

1. The court stair now works (3 × 8 × 150/340 mm). **But the garden walk does not reach the loggia:** they meet only at the corner point (15.4, 16.0), and guards close both edges.
2. **The play lawn shrank from 74.4 to 56.8 m².** Its largest rectangle is now 3.2 × 6.8 m (C10: 4.0 × 7.5 m). The lawn stair takes 8.3 m² of it, where ARR-03 estimated 2.5 m².
3. **The trees are C10's trees:** four, 0.76–1.25 m from the lawn wall. The ledger says "three". The species, root barriers, herbs, beds, wind screen and rain chain appear in no file.
4. **The garden store cannot be used:** FW-19.3 splits it into bays 0.95 and 1.05 m wide, it has no floor level, and its door opens into a walled pit with no drain.
5. Rule 4.7 passes (147 m²), but only 57 m² of that is level lawn.

## Scorecard

SCORECARD: fixed=1 partly=8 not_fixed=3 worse=1 new_blocker=1 new_major=4 new_minor=2

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| LND-01 | partly fixed | Measured: 24 risers of 150 mm, 1.27 m clear, 1.5 m landings, treads within −0.34…+0.15 m of natural ground. | The stair is done. The walk is broken (N01). Privacy at the window is N06. |
| LND-02 | partly fixed | Measured: the lawn stays at 1667.60 (the Q4 default). The stair is 2 × 8 × 149/320 mm with a 1.2 m landing. | Ask Q4 again with the C11 numbers (N02). |
| LND-03 | **made worse** | Measured: lawn 56.8 m² (C10 74.4). Largest rectangle 3.2 × 6.8 m (C10 4.0 × 7.5). Width 3.1 m at v 8, 2.6 m at v 10.3, 1.9 m at v 15. From the lounge (eye 1671.6 at u 17), the sightline over the slab edge (20.6, 1669.98) meets the lawn at u 25.9, past its edge (24.9). The lounge sees no lawn. Neither is drawn, as C11-LND-01 asked. | N02. Flat-bar guard (upstand ≤0.10 m, not 0.5 m of stone) and a bench on the t-low east edge, v 5–11. Tell the owner the children are watched from the terrace or the balcony. |
| LND-04 | **not fixed** | Measured: `engine.tree_spots` still gives (28.97, 2.0), (27.18, 5.6), (25.39, 9.2) and (23.60, 12.8), 1.25/1.08/0.92/0.76 m from the lawn. **Self-correction:** my C10 line u + 0.448v = 29.8 is 1.19 m from the wall, not 2.0 m. The bank is 3.57 m wide at v 0, 3.05 m at v 6, 2.70 m at v 10 and 2.09 m at v 17, measured perpendicular to the boundary: too narrow for 8–12 m trees. | Three trees on the bank midline at (29.3, 2.5), (27.55, 6.0) and (25.55, 10.0), 1.4–1.7 m from the wall and from the boundary. 6–8 m high, crown ≤6 m: *Acer monspessulanum*, *Cercis siliquastrum*, *Pistacia atlantica*, almond; no *Celtis* or *Fraxinus*. A 1.2 m root barrier on the wall side. Fix `tree_spots`. |
| LND-05 | partly fixed | Measured: 90 m of 1.1 m guards, including the lawn's downhill edge (1.33 m drop). | Ball-stop net 2.0 m high and a 1.0 m hedge on that edge. Neither is drawn or noted. |
| LND-06 | partly fixed | The store is unusable (N03) and the route is broken (N01). No wheel channel, compost bay or bulk-soil note in any file (grep). | Add 0.25 m wheel channels on both outdoor stairs and a 1 m² compost bay at (19.0, 16.0). |
| LND-07 | partly fixed | Measured: `WATER['lawn']` has a 1:60 fall, a slot drain and outlets at (21, 12) and (27, 2). No discharge is drawn. | N04, N05. |
| LND-08 | partly fixed | Measured: court 40.6 m² plus a 4.2 m² porch (CONSOLIDATED target 51.6 m²). No planting. | One small tree (pomegranate) in a 1.2 m pit, and a 1.0 × 2.0 m basin on the court's south edge. |
| LND-09 | partly fixed | Inferred: sun hours as in C10. Winter sitting on `t-south` exists. The winter bench and play corner (u 19.2–22, v 12–17) is not drawn; that band is now a pit. | N04 (a). |
| LND-10 | **fixed** | Measured: drying yard R(14.0, 6.35, 17.8, 8.0) on `deck-r`, 6.3 m², with a screen, reached by the lift. | — |
| LND-11 | not fixed | No planter or bed in any file. | A 0.6 × 4.6 m herb planter at R(4.6, 13.0, 9.2, 13.6) by the kitchen door. A raised bed in pocket N04 (c). |
| LND-12 | partly fixed | Measured: cistern bay 2.2 × 5.1 m under a soffit at about 1669.68. Holding 10–15 m³ needs a floor at 1668.3 or lower (0.4–1.1 m of cut), which is not modelled. Taps only at the court. | Cistern floor at 1668.2 (12 m³), dig added to the earthworks. Taps at the loggia, t-low and the store. |
| LND-13 | not fixed | No screen and no rain chain. | 1.8 m glass screen at the t-low north end (v 1.1). Rain chain at (18.0, 16.0) into a gravel rill. |

## Part B: new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| LND-N01 | BLOCKER | `walk-s` / `loggia` | They share 0.02 m of edge; the garden route does not connect. | Extend the walk to u 18.0; add a route check. |
| LND-N02 | MAJOR | `lawn` | 24% smaller; the stair walls stand in its narrow part. | Ask Q4 again; report the garden by part. |
| LND-N03 | MAJOR | under `t-low` | Bays 0.95/1.05 m wide, no floor, door into a pit. | One 12.5 m² room, floor 1667.60, 1.2 m door. |
| LND-N04 | MAJOR | under the balcony, south of the loggia, NW lawn slot | Three walled leftover pockets; the first is a sump. | Fill them and use them. |
| LND-N05 | MAJOR | bank | WAT-07's spreader does not fit the bank. | Trench under the lawn. |
| LND-N06 | MINOR | boys and girls, south glass | The walk passes 0–1.12 m from 5.1 m of glass, at eye level. | Draw ROOM-09's obscured glass up to 1.7 m and SAF-03's shutters. |
| LND-N07 | MINOR | `checks.py` | The route is never tested (§7.5 checks only risers and goings). `guards()` returns `missing = []` unconditionally. The 4.7 figure counts stairs and walls as garden. | Add N01's route test, fill `missing` from real drops without a guard, and report the garden by part. |

## Part B details

**N01 · BLOCKER.** `walk-s` is R(9.74, 16.0, 15.4, 17.12) and `loggia` is R(15.4, 10.95, 18.0, 16.0). They share 0.02 m of edge (measured), so `guards()` closes the walk's east end (SW-30, a 1.74 m drop) and the loggia's south edge (a 1.9 m drop to 1668.1). The lower floor's outdoor entrance, the barrow route and the route to the lawn all stop at u 15.4.

*Correction:*
- Extend `walk-s` to u 18.0 at 1670.00. That adds 2.9 m², with ≤2.2 m of fill behind the v 17.12 wall.
- Alternatively, extend the suspended loggia slab to v 17.12.
- Either way the shared edge becomes 2.6 m with no guard.
- Add a check: consecutive surfaces on every outdoor route share ≥1.2 m of edge at the same level.

**N02 · MAJOR.** The lawn lost 17.6 m² (measured) to the stair (8.3 m²), t-low reaching v 1.1, the west edge at u 20.8 and the balcony pocket. Rule 4.7's 147 m² is lawn 57, terrace 30, stair 8, bank 36 and pockets about 9.

*Correction:* put Q4 to the owner again: one level gives 86 m² with a 4.0 × 9.0 m rectangle, 184 m³ of fill and a 3.0–3.2 m wall; C11 gives 57 m², 3.2 × 6.8 m, 30 m³ and 1.33 m. If the default stands, apply N04, which adds 6.1 m² and widens the south tail to 4.5 m.

**N03 · MAJOR.** Measured: FW-19.3 runs the full length (v 1.1–12.8), and column C-B/9.4 narrows the east bay to 0.70 m. The ground falls from 1668.74 to 1667.29 under a soffit at about 1669.68. No floor, door or dig is modelled, and the FW-12.8T door faces pit N04 (a).

*Correction:*
- Stop FW-19.3 at v 6.5. The slab span is 2.2 m; the structure reviewer should confirm.
- Store R(18.25, 6.7, 20.45, 12.65), floor 1667.60: about 9 m³ of cut (≤1.15 m), 2.0 m clear.
- A 1.2 m door at u 18.4–19.6, with a tap and a socket.

**N04 · MAJOR.** Three pockets, measured:
- **(a) Under the balcony,** R(18.25, 12.8, 19.85, 16.6), 6.1 m², ground 1667.9 → 1666.85, walled on all four sides. It takes the `balc-e` outlet at (19.7, 15.5) and has no outlet.
- **(b) South of the loggia,** R(15.4, 16.0, 18.0, 17.12), 1.7–2.2 m down.
- **(c) The NW lawn slot,** R(20.8, 1.0, 21.8, 3.4), walled on three sides.

*Correction:*
- (a) Fill to 1667.60 with a slot drain to the lawn drain. It becomes a covered winter bench, sandpit and store apron.
- (b) Becomes the walk (N01).
- (c) A raised herb bed at 1668.6.

**N05 · MAJOR.** A 12 m spreader at least 3 m from the boundary fits only north of v 1.5. The lawn outlets and the drains of WAT-05 and WAT-06 all end "at the bank", about 1.5 m above the downhill neighbour.

*Correction:* a gravel trench 1.0 × 1.0 × 10 m under the lawn fill along u 22.5, v 2–11, at least 2 m from the heel of the downhill wall, subject to a percolation test. Nothing surfaces on the bank. If the test fails, the legal outlet is unknown (F3).

## What C11 gets right

- The court stair is easy and sits close to natural ground (±0.35 m).
- The lawn stair is easy: 16 × 149/320 mm, a mid landing, handrails on both sides.
- Guards are drawn on every drop of 0.6 m or more, including the lawn edge.
- A drying yard reached by the lift, off the view terraces.
- Everything, walls included, stays inside the setbacks.

## Out-of-scope notes

- Structure: confirm FW-19.3 can stop at v 6.5.
- Arrival: the court is 40.6 m² against the 51.6 m² target.
- Geotechnics: the 1.33 m lawn wall near trees needs root and seismic design.
