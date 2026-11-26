# 11 · Life safety review of C11

Concept stage. Code-like numbers are `assumption`; a licensed professional must check them.

## Summary

1. The stairs are now safe to walk: SAF-03 and SAF-04 are fixed in the geometry.
2. The §7.7 guard check cannot fail. `missing` in `checks.guards()` is never filled, and the function skips whole classes of edges.
3. About 25 m of real 1.8–3.9 m drops have no guard: the roof terrace, the terrace lip over the court stair, the loggia, the pocket under the balcony, the road edge, and the green-roof joint.
4. An LPG cage sits in the sunk arrival court, beside the front door.
5. The lift shaft bypasses the stair screen, and the new master-balcony screen removes the master's second way out.

## Scorecard

SCORECARD: fixed=3 partly=12 not_fixed=1 worse=0 new_blocker=4 new_major=3 new_minor=1

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| SAF-01 forecourt | partly | Guard on v 11.6, u −4.57…−0.33 (measured). **0.21 m gap at u −3.08…−2.87** where `fore` meets `fore-deck`, over a 3.87 m drop. W1 top = 1677.47, so the 0.6 m upstand is only text. | One continuous guard from u −4.41 to −0.25. Model the upstand (top 1678.07). |
| SAF-02 green roof | partly (still BLOCKER) | Guard only on v 6.2, u 12.6–18. **The joint u 12.6, v 6.2–7.3 between deck and green roof is open** (polygons). "Locked gate" is a label. North edge drops 6.43 m (zg(14, 0.8) = 1671.05); east edge drops 3.9–8 m. No parapet or anchors. The drying-yard screen stands 0.15 m from the guard: a ladder. | Guard on u 12.6, v 6.2–7.3. Gate as an element. Parapet, or anchors ≤6 m apart, on v 1.1 and u 18. Drying yard to v ≥ 6.8. |
| SAF-03 `gs-court` | fixed | 3 × 8 × 150/340, 1.5 m landings; treads within 0.1–0.3 m of natural ground. | See N02. |
| SAF-04 road stair | fixed | 12 + 12 × 164/158, 320 goings, landing 1675.50, 1.4 m, handrails both sides. | Road side: see N03. |
| SAF-05 garage CO | partly | `fire` door at (6.8, 8.85); RW-9.5 and RW-6.8 fire walls; stair `screen`. Extract, CO alarms and slab rating are notes. | Model the extract and inlet; garage slab ≈60 min (assumption). Lift path: N06. |
| SAF-06 plant | partly | `hall-r→plant` is kind `door`, opening onto the road escape hall. Flue and CO alarm are text. | Kind `fire`, self-closing, ≈30 min; draw the vertical flue. |
| SAF-07 stair voids | partly | Flights are 12/12 with 1.40 m landings. Guards and spine are notes; the lower well is open 1.2 m. | Draw 1.1 m void guards on all 3 floors; spine 0.15 m or balusters ≤0.10 m apart. |
| SAF-08 terraces | partly (still BLOCKER) | South terrace and balconies guarded. **`deck-r` has none**: east u 18 (6.8 m) drops 3.90 m onto `balc-e`; south v 13 (5.4 m) drops 3.58–3.90 m. It has two doors (lobby, office). | 1.1 m guard on u 18 (v 6.2–13) and v 13 (u 12.6–18). Window restrictors as elements. |
| SAF-09 garden drops | partly (still BLOCKER) | Guarded: `t-low` N/E, the lawn edge, the lawn stair. **Unguarded** (measured): loggia S v 16.0, u 15.4–18, 1.81–2.31 m; loggia E u 18, v 12.8–16, 2.15–2.45 m; `t-low` S v 12.8, u 18–19.85, 2.3 m into the pocket under `balc-e` (ground 1667.45); `walk-s` E end, v 16.0–16.5, 1.74 m. ≈8.5 m beside the lounge slider. | Guards on all four, or fill the pocket R(18, 12.8, 19.85, 16.6) to 1669.98. |
| SAF-10 children's escape | partly | Sills +0.90; open ground +0.42 / 0.00 m. Casements are text. | Model one ≥0.45 × 0.75 m (≥0.33 m²) casement per room. |
| SAF-11 hidden court | partly | Gate is a label; lights, camera and glass are notes; the gate can be bypassed (N07). | Gate as an element; N07. |
| SAF-12 boundaries | not fixed | Q8 default: no fence; no gates on the north strip or garden. | N07. |
| SAF-13 power cut | partly | Lift drawn; rescue device, battery, GSM and shutter cranks are notes. | Put them in the specification. |
| SAF-14 detection | partly | Notes only. | Alarm positions on the plans. |
| SAF-15 ice | partly | Canopy over the south glass; walk cross-fall. Treads, lights and the v 16.4 gutter are notes. | Gutter on v 16.4 above `walk-s`. |
| SAF-16 north slot | fixed | North wall on v 1.1; guest north window deleted. | — |

## Part B: new problems

| ID | Sev. | Where | Finding | Correction |
|---|---|---|---|---|
| SAF-N01 | BLOCKER | `checks.py` `guards()` | Cannot fail; misses most drops beside the house | Rewrite, with a failing test |
| SAF-N02 | BLOCKER | `t-south` v 16.0, u 4.32–7.8 | 1.95–2.50 m drop onto the court stair, unguarded | 1.1 m guard |
| SAF-N03 | BLOCKER | Road edge over W2; W4 | Road falls 0.8–2.07 m into the road stair; setback 0.6–1.58 m | Street wall ≥1.1 m above road; guard on W4 |
| SAF-N04 | BLOCKER | Court R(−0.2, 12.3, 0.4, 12.9) | LPG cylinders in a 3.8 m pit beside the front door | Move to open air at road level |
| SAF-N05 | MAJOR | Screen v 6.2, u 18.25–19.85 | Master loses its second way out | 0.8 m gate in the screen |
| SAF-N06 | MAJOR | Lift door in `lobby-r` | Shaft carries garage fumes past the stair screen | Smoke-sealed lift door, or move the screen |
| SAF-N07 | MAJOR | South strip; lawn; north strip | Stair-head gate bypassed at grade from the footpath | Fence and gates |
| SAF-N08 | MINOR | W3 on v 15.37 | Bank ledge 0.87 m above L1 falls 2.6–2.8 m to the court | Guard or planted slope |

## Part B details

**SAF-N01.** `missing` is initialised and never appended to, so §7.7 passes by construction (`measured`, code read and re-run). The function also misses most drops beside the house:

- (a) Any edge within 0.30 m of any footprint is skipped. That removes all of `deck-r`, the loggia's S and E edges, and the `t-south` lip.
- (b) The "outside surface" lookup is plan-only, so `balc-e` (1673.58) masks the 2.3 m drop beneath it.
- (c) Kinds `green` and `pergola` are ignored.
- (d) Points beyond the parcel plus 0.5 m are skipped, so the road edge is never checked.
- (e) It never checks drops from surrounding ground into a dig (W2, W4, W3).
- (f) It never checks the internal voids.
- (g) Plans, sections (`engine.py` ~l.1084) and 3D (`model3d.py` l.185) each derive guards separately, against §7.3.

*Fix:*
- Sample every edge of every slab, terrace, stair and dig against the highest surface below z − 0.05.
- Exempt an edge only where a wall rises ≥1.1 m above it.
- Add the voids.
- Store guards as elements that all three views read.
- Fail on any unguarded drop ≥0.6 m. Add a test that fails on today's `deck-r`.

**SAF-N02.** `t-south` keeps its pulled-back lip at v 16.0 over u 4.6–7.8, directly above `cs-f2`/`cs-l2`. Drops: 1.95 m at u 5, 2.38 m at u 6–7, 2.50 m at u 7.6 (`measured`). The court guard ends at u 4.32 and the terrace guard starts at (7.8, 16.16). *Fix:* a guard on v 16.0 for u 4.32–7.8, and on u 7.8 for v 16.0–16.4.

**SAF-N03.** W2's top (1677.40–1677.42) is below the road edge (1677.52–1677.57). Drops (`measured`):

- road into F1: 0.8 m at v 13, 1.45 m at v 14;
- road into L1 (1675.50): 2.05–2.07 m for v 15–17;
- over W4 from the setback strip: 1.58 m at u −8.5, 0.6–0.71 m along F2, 0.64 m into the court at u −2.5.

Nothing stops a pedestrian or a reversing car. *Fix:*
- The ARR-05 street wall modelled, top ≥1678.70, with a 0.15 m kerb.
- A 1.1 m guard on W4, u −9.03…−1.43.
- The road authority's consent.

**SAF-N04.** The cage is 0.6 m from the porch, which is dug under the road hall, and ≈2.3 m from the entry door (2.0, 10.6). It sits in a pit with W1 (3.8 m) on the north and W3 on the west. LPG is heavier than air. A leak pools in the court, enters the WAT-02 gullies, and runs down the court stair past the children's windows. *Fix:* store the cylinders at road level in open air on the forecourt boundary (≈(−5.0, 3.0)), ≥1 m from openings and ≥2 m from drains and below-ground openings (assumption). Pipe the gas to the court cooker with a shut-off, or cook electric.

**SAF-N05.** ROOM-08's full-width 2.0 m opaque screen makes `balc-m` (1.85 × 3.6 m, 3.6 m above `t-low`) a dead end. In C10 it linked to the east balcony ring. The master's only exit is now the hall door at (11.95, 7.3), past the open kitchen. *Fix:* a 0.8 m lockable gate in the screen, with a keyless thumb-turn on the master side.

**SAF-N06.** The lift's road door opens into `lobby-r`, 2–3 m from the garage fire door. The screen covers only u 6.8–9.4. The shaft vents to the main hall and to the lower family hall beside the bedrooms. *Fix:*
- Smoke-sealed landing doors at road level (E30 Sa, assumption), or a screen line that puts the lift on the protected side.
- A CO detector in `lobby-r`.
- An alarm-released hold-open on the garage door.

**SAF-N07.** The court stair's foot treads (1672.9–1673.6) are within 0.1–0.3 m of the boundary ground (zg(0, 18.3) = 1673.32, zg(1, 18.3) = 1672.96). Anyone on the footpath can walk up into the court and onto the terrace ring with its 5 sliders, past no gate. The lawn is just as open at v 17.12 (u 18.25–20.83) and from the north strip. *Fix:*
- A 1.8 m fence with a lockable gate on v 17.42, u −1.43…10.
- Gates at u ≈18.5 on the north strip and on the lawn's south edge.
- Q8 to be decided knowing the stair-head gate is otherwise useless.

**SAF-N08.** The ledge left between F1/L1 and the court (f(−6.0, 15.2) = 1676.37) is a 0.87 m step up from L1. W3 drops 2.6–2.8 m from it into the court. *Fix:* a guard on W3 (v 15.37, u −6.08…−3.48), or a planted 1:1 slope with a hedge.

## What C11 gets right

- All outdoor stairs meet rule 4.11: flights of ≤12 at 149–164 mm, landings ≥1.2 m, handrails both sides.
- The garage fire door and the glazed stair screen are real door elements, with fire walls.
- The north slot and its window are gone.
- Every floor keeps a level exit to open air, and the lower floor has its own route out.
- The children's windows have ≥2.4 m of open ground at or below the sill.
- The forecourt, south terrace, balconies, `t-low` and the lawn edge carry drawn guards.

## Out-of-scope notes

- Structure/vehicles: W2 retains the public road with no impact barrier.
- MEP: the plant room is 4.2 m² against ROOM-01's 9–10 m².
