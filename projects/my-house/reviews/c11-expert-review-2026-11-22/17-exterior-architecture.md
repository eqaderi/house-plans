# 17 · Exterior architecture review of C11

Concept stage; nothing is permit-ready or code-checked. Heights: `zg()` (inferred). Stills (`model3d.py`): heads 2.2/2.3, 1.05 m glass guards, 0.12 m eave.

## Summary

1. The geometry moves are done: the undercroft is closed (wall on v 1.1), the road block has one south plane at v 13.0, the street door has a 0.5 m return, and the road stair runs against the road.
2. Everything that makes the house *look* designed exists only as notes or dashed outlines: stone, render, parapet, louvre, street wall, gate, canopies, solid guards.
3. The south façade is worse than C10: 8 openings in 6 widths, piers 0.30–0.65 m. The dining slider and road office window overlap column C-11.1/13 by 25 mm.
4. The SE corner is still 11.1 m sheer, now with a blank 7.0 m RC fin and a lone 0.30 m post 6.6 m tall.
5. The court is big (40.6 m²) but reads as a pit: a 5.6 m barrier on the north, no east edge, LPG cooking 1.6 m from the front door.

## Scorecard

SCORECARD: fixed=2 partly=7 not_fixed=2 worse=0 new_blocker=0 new_major=3 new_minor=4

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| EXT-01 hayat / gate | partly fixed | measured: court 40.6 + porch 4.2 m²; L-stair against the road. Gate = text at (−4.9, 11.15); street wall = note. `house-road.png` shows neither. | Model a 1.2 m gate at the stair head (u −6.05…−4.85, v 11.6) with a canopy. Raise W2 as 1.0 m stone + 0.8 m lattice (top ≈1679.2), v 11.6–17.27. |
| EXT-02 east tiers / SE sheer | not fixed | measured: main and lower east walls on u 18.0 (rule 4.2, accepted). (18, 16.4) ground 1667.48 → deck guard ≈1678.6: **11.1 m sheer, unchanged**. Lawn → overrun top 1681.6: 14.0 m. The material tiers (C11-EXT-01) are notes only; no canopy over `balc-e`. | Stone zone on every face below 1673.3 (datum 1670.0), render above. 1.0 m `balc-e` canopy at ≈1677.2, v 6.2–16.4. Corner: N03. |
| EXT-03 undercroft | fixed | measured: lower wall (9.4, 1.1)–(18, 1.1), 0.45 m; FW-1.1T closes the terrace end. | None. |
| EXT-04 openings | partly fixed | measured. East: sliver deleted, clerestory in. Centrelines are main 4.1 / 7.6 / 10.0 against lower 4.3 / 7.5 / 9.9, near-misses of 0.1–0.2 m. Widths 1.8/2.0 m (2.4–3.0 asked). South: worse (N01). Heads unchanged at 2.2/2.3 m, leaving a 1.6 m blank band. | Stack exactly: suites both 2.0 m at v 3.2–5.2; windows v 6.7–8.5; day sliders v 9.0–10.8. Heads 2.7 m (main) / 2.5 m (lower) in `design.py` and `model3d.py`. |
| EXT-05 blank site walls | partly fixed | measured: road stair along the road; solid lawn stair against FW-20.6. FW-20.6 still 2.82 m exposed at v 12.8; W1 3.87 m; RC-18L 7.0 m. All drawn as concrete. | Coursed limestone, batter ~1:10, coping on W1, W3, W4, FW-20.6, FW-12.8T, RC-18L to 1670.0. Planting pockets on FW-20.6, v 10.28–12.8. |
| EXT-06 glass guards | partly fixed | measured: guards now cover every drop ≥0.6 m (§7.7, 89.5 m). All still frameless glass, 1.05 m in the stills. | Solid 1.1 m parapet + 0.45 m planter (south terrace); 0.3 m upstand + 0.8 m flat bar (balconies); 1.1 m solid (deck); 0.5 m stone + rail (`t-low`). Draw them. |
| EXT-07 road roof | partly fixed | measured: LIFT-OVR 0.8 m modelled. Outline still notched (132.9 m² against 149.9 m² for the rectangle; NE notch u 9.4–12.6 × v 1.1–7.3, SW notch u 0–2 × v 11.6–13.0). 0.12 m eave, no parapet. Louvre = text. | 0.5 m parapet (top ≈1681.3) on the road block and the green roof, so the roof reads as one rectangle u 0–12.6. 1.2 m louvre round u 6.8–11.4 × v 1.1–7.3. Gravel finish. |
| EXT-08 sun overhangs | partly fixed | measured: loggia pergola in; `t-south` lip 0.40 m past the lower wall face (≈0.55 m at the glass, OK). The SSE canopy is a **dashed plan outline only**: not in `structure()`, the sections or the 3D. ENE shutters are notes. | Make the canopy an element (1677.2–1677.5, u 4.6–17.8, v 13.0–14.0) so section G–G and the stills show it. Draw shutters on the 4 ENE sliders. |
| EXT-09 road jogs | fixed | measured: road south rooms end at v 13.0; RW-12.6 runs v 7.3–13.0. | None. |
| EXT-10 street door | partly fixed | measured: leaf at v 10.1–11.1, 0.5 m return. Canopy, address panel and slatted shutters are text only. | Model a 1.2 m canopy over the door and gate; slat finish on the shutters. |
| EXT-11 materials | not fixed | measured: no material data exists; the stills are grey/beige, concrete and glass. | Add a `finish` per façade segment and site wall (limestone / lime render / timber / dark steel) and colour the stills with it. |

## Part B: new problems

| ID | Sev. | Where | Finding | Correction |
|---|---|---|---|---|
| EXT-N01 | MAJOR | Main and road south, v 13.0 | Openings clash with columns; 6 widths; reveals 25–125 mm | Re-space to ≥0.9 m column piers (schedule below) |
| EXT-N02 | MAJOR | All 3D stills | Columns drawn 0.225 m proud; canopy, parapet, gate, wall, solid guards missing | Shells to the 0.25 m outer face; model the noted elements |
| EXT-N03 | MAJOR | SE corner u 18–19.85, v 12.8–16.4; posts on u 19.6 | Blank 7.0 m fin, lone 6.6 m post, posts off the piers | Cantilever off RC-18L, delete C-B/16.2, stone-face, realign posts |
| EXT-N04 | MINOR | Court u 2–4.6, v 13–16; cooking (−0.2…0.4, 12.3…12.9) | No court edge; LPG at the front door | Bench-planter on u 4.6; move the cooking station SW |
| EXT-N05 | MINOR | W1, v 11.6, u −4.0…0 | 5.6 m barrier over a 4.4 m deep court | Upstand inside the guard: 0.6 RC + 0.5 rail |
| EXT-N06 | MINOR | Lower south, v 15.75 | Twin rooms get 1.8 m and 3.3 m windows | Girls' 1.8 m at u 11.5–13.3 |
| EXT-N07 | MINOR | Road south, u 2–12.6, 1677.5–1680.8 | A flush 7.2 m two-storey wall; the upper 3.3 m has only 0.8 m and 1.2 m windows | Canopy at 1677.2 as the dividing line; WC window on the kitchen window's axis |

## Part B details

**EXT-N01.** Column faces sit at 4.375/4.825, 6.575/7.025, 10.875/11.325 and 15.175/15.625. Main south openings (u), measured:
- entry 2.7–3.9;
- kitchen window 5.35–6.55 (**25 mm** to C-6.8);
- kitchen slider 7.1–9.1 (75 mm);
- dining slider 9.5–10.9 (**25 mm into C-11.1**);
- 0.9 m window 11.5–12.4;
- living slider 12.7–15.1 (75 mm);
- 0.6 m window 15.75–16.35.

The road office window, 9.7–10.9, also **cuts C-11.1 by 25 mm**. The ledger says "openings clear" (STR-03) and "1.0 m window" (EXT-02); neither is true.

Schedule, with every frame ≥0.15 m from a column:
- entry 1.2 m at 2.7–3.9;
- kitchen window 1.2 m at 5.2–6.4;
- kitchen slider 1.8 m at 7.2–9.0;
- dining: one 1.0 m vertical window at 9.7–10.7, replacing the 1.4 m slider and the 0.9 m window (the kitchen slider is 1.3 m away);
- living slider 2.3 m at 12.7–15.0;
- the 0.6 m window deleted, so the SE corner is solid 15.0–18.25;
- road office window 1.2 m at 9.5–10.7.

That leaves four sizes, with every column inside a ≥0.9 m pier.

**EXT-N02.** `model3d.py` extrudes shells on the grid line, but THM-01 puts the outer face 0.25 m beyond it. The 0.45 m columns therefore show as a dark two-storey order, 1673.6 → 1680.8 on u 4.6 / 6.8 / 11.1 (`house-south.png`), that the real wall (face 13.25 against column face 13.225) buries. The owner judges from these stills (rules 7.5, 7.6). Offset the shells. Colour the columns as wall unless they are deliberately expressed, and then design them with N01. Model every element listed in Part A.

**EXT-N03.** Measured:
- **RC-18L** is 5.6–6.1 m exposed and blank.
- **C-B/16.2** at (19.6, 16.2) is a 0.30 m post alone on the bank: ground 1666.98, footing 1666.0, top 1673.6, so **6.6 m exposed**. STR-04 claims "no isolated tall posts".
- **C-B/9.4** stands 1.35 m in front of the lounge slider (v 9.0–10.8).

Correction:
- Delete C-B/16.2. Cantilever BB-16.4 1.6 m off RC-18L (engineer to confirm).
- Stone-face RC-18L to 1670.0, render above, and consider a 1.8 m opening at v 13.6–15.4 so the loggia sees the lawn.
- Move C-B/9.4 to v 8.75, onto the pier.

**EXT-N04.** The court meets `t-south` at u 4.6 on the same level (1673.60 / 1673.58), with no edge. The family table R(5.4, 13.75, 7.2, 14.65) is 0.8 m away. Keep the Q7 default (no screen), but add a threshold: a stone bench-planter 0.45 m high and 0.6 m deep on u 4.6, v 13.25–15.0, leaving v 15.0–16.0 open. Move the cooking/LPG station from beside the porch to u −2.5…−1.0, v 14.6–15.3 (safety reviewer to confirm the distances).

**EXT-N05.** W1 3.87 m + 0.6 m upstand + 1.1 m guard = 5.6 m, over a court 4.4 m deep (v 11.6–16.0); H:D 1.27 reads as a lightwell. A 0.6 m RC upstand + 0.5 m rail makes the 1.1 m guard (assumption) and brings the face to 4.47 m. Stone-face it: it takes the winter sun and becomes the court's backdrop.

**EXT-N06.** Boys' 8.9–10.7, girls' 11.45–14.75: the base has wider glass than any main-floor opening. Mirror the boys' window about u 11.1. Daylight reviewer to confirm 1.8 m for 4.3 × 4.8 m.

## What C11 gets right

- No undercroft: the lower floor bears on v 1.1 under the whole north side.
- The road block has one plane each way, lands on walls below, and stays a modest single storey from the street.
- The road stair runs against the road into a 40.6 m² court with a covered porch and a front door facing it: the Palangan device.
- The road block is set back 5.4 m on the east; the 1.85 m balcony shades the lower glass.
- Clutter is cut: the ENE sliver and the living window are gone, and the loggia has a pergola.

## Out-of-scope notes

- Structure: the BB-16.4 cantilever; the post spans after the move to v 8.75.
- Safety: LPG clearances in the court; guard height 1.05 m in the stills against 1.1 m in checks.
- Ledger: STR-03, STR-04 and EXT-02 are contradicted by `design.py`.
