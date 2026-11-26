# 24 · Flexibility, adaptability and lifecycle (30+ years) · C11

This review covers a concept only. Nothing here is engineered or checked against any code. Figures marked `measured` come from `design.py` (`build()`, `structure()`, `engine.clear_geom` / `room_dims`) or from `engine.zg`.

## Summary

1. Storage is fixed (27.6 m² of stores, against about 13 m² in C10), and the lift now takes a stretcher.
2. New BLOCKER: riser SH-E R(11.0, 3.55, 11.4, 4.15) stands inside both ensuite doorways, so neither ensuite can be entered with a wheelchair.
3. `structure()` makes ten lower partitions load-bearing. Three of them (u 11.1, u 8.2, u 6.8 south) carry nothing above, yet they are the walls a family moves over time.
4. Lintels, the knock-out panel and the key switches exist only in words. The new guest/lounge wall is lined end to end with joinery.
5. The main floor still has no laundry. The plant room leaves 0.34 m of service space in front of its equipment.

## Scorecard

SCORECARD: fixed=1 partly=6 not_fixed=3 worse=0 new_blocker=1 new_major=2 new_minor=2

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| FLX-01 children's block cannot split | **not fixed** (deferred by the Q15 default "no") | measured: `boys` and `girls` are 4.14 × 4.59 and 4.05 × 4.59 m clear. The windows at u 8.9–10.7 and 11.45–14.75 still cross the 3-bay lines u 9.67 and 12.53. LW-11.1 is now declared load-bearing. | Under Q15 "no", keep at least the option to merge the two rooms when the children leave: make u 11.1 non-bearing (FLX-N02). The merged room would be about 38 m², with column C-11.1/13 left as a pilaster. |
| FLX-02 lower floor has no entrance of its own and cannot be separated | **partly fixed** | measured: court stair (3 × 8 risers of 150 mm) → `walk-s` at 1670.00 → loggia → lounge slider (u 16.7). The ledger marks C11-FLX-01 "Partly: notes". `design.py` and the plans contain no lintel, frame or key switch. | Add to `structure()` and draw: lintels and frames at the stair mouths, main (v 7.3, u 6.8–9.4) and lower (v 7.3, u 8.2–9.4), left open today (rule 5.3); key switches on the lift calls; a future 1.0 m solid door at u 16.7. |
| FLX-03 no separable suite for a married child while the grandparents live in | **not fixed** | measured: the guest/lounge wall is now v 6.2 (LW-6.2, bearing). It is lined by wardrobes at u 13.3–17.4 on one side and by the TV (u 13.0–14.5) and tea bar (u 15.5–17.75) on the other, so no metre is free for a door. The 32 A circuit and the duct are notes only. | Form a 1.0 m opening with a lintel now in LW-6.2 at u 13.1–14.1, filled with a non-bearing panel. Start the wardrobes at u 14.2; move the TV to u 14.3–15.4. Draw the cooker circuit and the duct route. |
| FLX-04 lift | **partly fixed** | measured: shaft R(9.4, 4.5, 11.4, 7.3) is 1.80 × 2.60 m clear, enough for a 1.1 × 2.1 m car (assumption: supplier to confirm). LIFT-PIT floor 1668.80 (1.2 m). LIFT-OVR top 1681.60, about 4.1 m above the top stop. The garage→lobby door stays 1.0 m. The lifting hook is a note only. | Widen the fire door to 1.2 m (u 6.8, v 8.15–9.35). Draw the 1.5 t hook in the overrun. |
| FLX-05 ageing on the main floor | **partly fixed** | measured: the ensuite opens straight off the bedroom, but SH-E blocks the door (FLX-N01). There is no washer reserve. The only laundry is downstairs and would be lost if the lower floor were separated. | Fix FLX-N01. Reserve a washer-dryer stack R(1.15, 6.30, 1.85, 7.00) in `tanks` (water, booster and 1.2 m hall door already there), with a feed, a gully and a 16 A circuit. |
| FLX-06 no partition or column strategy | **partly fixed** | measured: the columns on v 13.0 at u 4.6, 6.8, 11.1, 15.4 and 18.0 all sit in today's partition lines, so no column stands loose in a room. However, `structure()` makes almost every lower partition bearing: LW-6.2, -12.6, -11.4, -10.95, -11.1, -15.4, -6.8, -7.3, -7.3E and -8.2. | See FLX-N02. The columns are 0.45 m inside 0.20 m walls (FLX-N04). |
| FLX-07 storage | **partly fixed** | measured clear: `bulk` 9.6, `store-u` 5.5, `store-s` 6.0, `store-r` 2.2, `pantry` 4.3 = 27.6 m². The garden store is only a label (no extent, no floor level). Ground at (18.6, 9.5) is 1668.35, under a soffit of about 1669.68. | Draw `gstore` R(18.15, 9.0, 19.15, 12.65): floor 1667.60, about 2.05 m clear, 1.2 m door on v 12.8 where the ground is 1667.74. Dig ≤ 0.75 m. |
| FLX-08 office too small to serve as a bedsit | **partly fixed** | measured: `office` is 2.99 × 3.29 m = 9.8 m² clear. The fold bed drawn is 0.85 × 1.8 m, a single. The deck screen and the obscured glass are notes only. | Draw a 1.4 × 2.0 m fold-down double at R(11.05, 9.6, 12.45, 11.6), clear of the desk and the door leaf. Draw the 1.8 m screen at u 12.6, v 9.5–11.0. |
| FLX-09 vertical extension undecided | **fixed** | Q13 default "no upward growth". Roofs are labelled non-accessible except `deck-r`. The overrun and rooflights are consistent with that. | The owner still has to confirm Q13. |
| FLX-10 `hall-l` too short for a 3-bay block | **not fixed** (moot under Q15) | measured: the `hall-l` south edge runs u 8.2–12.6. A third bay at u 12.53–15.4 could only be entered through the lounge. | Only if Q15 becomes "yes": R(12.6, 10.6, 13.5, 10.95). |

## Part B: new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| FLX-N01 | BLOCKER | main `ens`, lower `gens`, riser SH-E | Riser stands in both ensuite doorways | Move SH-E; keep 0.9 m clear inside each door |
| FLX-N02 | MAJOR | lower LW-11.1, LW-8.2, LW-6.8 (v 7.3–15.75) | Bearing though nothing above needs them; freezes the plan | Make them non-bearing infill |
| FLX-N03 | MAJOR | road `plant` R(4.4, 11.6, 7.4, 13.0) | 3.0 m² clear, 0.34 m service zone, no room for a heat pump | Enlarge to R(4.4, 11.3, 9.4, 13.0) |
| FLX-N04 | MINOR | columns on v 13.0 | 0.45 m columns in 0.20 m walls clash with furniture | Blade columns, or move furniture |
| FLX-N05 | MINOR | road stair | The only step-free route depends on one lift | Platform-lift-ready road stair |

## Part B details

**FLX-N01 · BLOCKER.** The ensuite doors cannot be used, which breaks rule 2.5 in practice and rule 5.4 for the grandparents.

- Evidence (measured):
  - Main: the slider spans v 3.50–4.40 at u 11.4, and the riser fills v 3.55–4.15. The free gap is 0.25 m, and the basin (u 10.45–10.95, v 3.99–4.41) sits right behind it.
  - Lower: the slider spans v 3.20–4.20, leaving a 0.35 m gap. The `gens` turning circle overlaps the riser and the WC.
  - No check in `checks.py` tests doors against risers or fixtures.
- Correction:
  - Move SH-E to R(11.0, 2.5, 11.4, 3.1) on both floors, still stacked.
  - Shorten the main shower to v 1.25–2.45 (1.7 × 1.2 m).
  - Keep u 10.44–11.34 × the door width clear of fixtures. Move the main basin to the v 4.4 wall, u 9.6–10.1.
  - Add a check: each door opening, extended 0.9 m into each room, touches no riser and no fixture.

**FLX-N02 · MAJOR.** These are the walls a family moves over 30 years: merging the children's rooms, enlarging the bathroom for a wheelchair, widening the laundry.

- Evidence:
  - `measured`: above LW-11.1, LW-8.2 and LW-6.8 the main floor is kitchen, dining and terrace, with no wall on those lines.
  - `ai_judgment`: the slab spans one way in v (2.05 m from LW-10.95 to LB-13.0, then 2.75 m), so it needs no support at u 11.1.
- Correction:
  - Mark these walls in `structure()` as non-bearing 200 mm dense infill with a soft head joint, Rw ≥ 45 dB (assumption).
  - Keep the columns C-6.8/13 and C-11.1/13 and the beam LB-13.0.
  - The engineer confirms the spans and the seismic infill detailing (Standard 2800, assumption).
  - Show bearing and non-bearing walls in two colours on `supports.png`.

**FLX-N03 · MAJOR.** Rule 6.7 asks for "a replaceable plant room".

- Evidence (measured): the clear room is 2.88 × 1.19 m. The equipment occupies v 12.0–12.8, which leaves 0.34 m in front of it. There is no space for a 200–300 L buffer or heat-pump cylinder, and no outdoor-unit position. Over 30 years expect about two boiler replacements and one MVHR replacement (ai_judgment).
- Correction:
  - Move the hall wall to v 11.3 for u 4.4–9.4 (`hall-r` keeps 1.7 m) and absorb `store-r`. The plant room becomes R(4.4, 11.3, 9.4, 13.0), about 7.3 m² clear, with 0.7 m of service space.
  - Put an outdoor-unit pad at R(16.6, 6.35, 17.8, 7.2) behind the drying-yard screen.

**FLX-N04 · MINOR.** Measured: each 0.45 m column stands 0.125 m proud of its 0.20 m wall. It clashes with:

- the boys' west bed (u 6.95–7.025, v 12.775–13.10);
- the girls' east bed (u 15.175–15.25);
- both wardrobes at u 11.1;
- the kitchen sink run (u 6.575–7.025).

Correction: use 0.25 × 0.80 m blade columns along the wall line (engineer to confirm), or pull the furniture 0.15 m clear.

**FLX-N05 · MINOR.** Lift modernisation (about every 20–25 years, assumption) takes the lift out for weeks, and the grandparents then have 24 risers to the car. The road stair is straight, 12 + 12 risers, 1.40 m clear (measured), which fits an inclined platform lift. Correction: keep the 1.40 m width, reserve the fixing zone on W3, and put a 16 A spur at the stair head and at L1.

## What C11 gets right

- Storage about doubled (27.6 m² clear), placed beside the core and the laundry (rule 6.3).
- A stretcher-size lift shaft with a pit and an overrun, its door on the same south face on every floor.
- The v 13.0 columns follow today's partitions, so no column stands loose in a bedroom.
- The lower floor has a real outdoor route of its own (24 risers of 150 mm, then a level walk).
- The ensuite and dressing open from inside the master bedroom, and the two ensuites stack on one riser.

## Out-of-scope notes

- Privacy: `walk-s` (1670.00) passes 0.25–1.4 m in front of both children's windows at eye height. `index.html` claims lintels and a knock-out panel that are not drawn.
