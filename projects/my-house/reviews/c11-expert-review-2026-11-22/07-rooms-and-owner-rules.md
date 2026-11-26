# 07 · Rooms and owner rules (residential architect) · C11 review

Geometry from `design.py`, clear sizes from `engine.clear_geom`, ground from `GroundModel.finished` (inferred).

## Summary

1. The owner's numbers now hold: kitchen 15.6 m², pantry 4.3, dining for 8 with ≥0.90 m pull-back, living 5.19 × 6.55 (34.0 m²), laundry 4.8 m² with separate stores.
2. BLOCKER: riser SH-E stands right behind both ensuite sliders. The master ensuite keeps 0.25 m of its 0.9 m opening, the grandparents' seated ensuite 0.35 m of 1.0 m.
3. Furniture fails in three rooms: the master bed is 0.35 m off its wall, the lounge sofa sits on its coffee table and blocks the TV, and the lower WC pan is in a 0.6 m slot.
4. The kitchen is the right size, but SH-K in the corner breaks the L. That leaves ~2.1 m of free worktop and a 0.15 m hob landing.
5. The front door is hidden in a recess (rule 2.6 doubtful). The hall vista, the hall and the children's windows are partly fixed.

## Scorecard

SCORECARD: fixed=8 partly=6 not_fixed=0 worse=0 new_blocker=1 new_major=5 new_minor=6

## Part A: C10 findings

| C10 ID | Status | Evidence (measured unless noted) | Remaining correction |
|---|---|---|---|
| ROM-01 dining | fixed | Clear 3.08 × 4.04 m; pull-back W/E 1.04, N 0.94, S 0.90; 8 chairs | — |
| ROM-02 kitchen seats | partly | 1.4 m island, three stools at 0.45 m centres (0.6 is normal). The 4th stool (8.25, 10.8) is on the serving line | Island 1.8 × 0.8 at u 6.4–8.2. Three stools on the north side at 0.6 m. Nothing east of u 8.2 |
| ROM-03 hood | fixed | Hob on the west run, duct up SH-K, walls to the ceiling | Landing: N05 |
| ROM-04 WC via wudu | fixed | `wc-m` off the dry lobby; shower off the wudu; 0 pan sightlines | — |
| ROM-05 children's windows | partly | Beds now off the glass. Both windows face `walk-s` (+0.00 m, 0–1.12 m from the glass). West of u 9.74 the boys' window faces `cs-f3` treads at +0.37 m (eyes ≈ +2.0) over a band obscured only to +1.5 m | Obscure to 1.7 m and keep 1.7–2.5 m clear. Add the girls' east window onto the loggia, u 15.4, v 13.4–14.6 |
| ROM-06 lounge | partly | Wardrobes, dense walls, opening and hall done. The TV is on the grandparents' wall, against C11-ROOM-10. Sofa and coffee table collide (N03) | N03 |
| ROM-07 laundry | fixed (corrected 6.7) | 4.8 m², fully fitted; stores 6.0 + 5.5 m²; drying yard | Access: N09 |
| ROM-08 living vista | partly | The living opening is v 7.45–8.65, *on* the hall axis. From the sofa's short arm (17.3, 7.6) the eye runs 15 m down the hall through v 7.45–8.2, past the end of the shelf (v 8.2–9.6). The route to the east slider crosses the sofa–TV line. An armchair stands 0.25 m in front of the TV | Full-height bookcase screen at u 13.35–13.7, v 7.0–8.7, with the TV on its east face. Entry turns south at v 8.7–9.9. Delete the armchair |
| ROM-09 main hall | partly | 18.8 m² (C10 23.3); 10.48 m long, rooms on both sides; rule 2.2 left "open" | Owner decides on 2.2; remove the SH-W nib (N12) |
| ROM-10 storage, shoes | partly | Shoes, lockers, boot bench and garden store done. The cleaning shelves are in the bulk store, 2 doors and ~8 m from the hall | Hall cupboard R(2.0,7.35,2.45,8.95); pantry door to u 2.8–3.7 |
| ROM-11 dressing | fixed | Aisle 1.04 m; ensuite and dressing open from the bedroom | Hanging length: N11 |
| ROM-12 cot | fixed | R(15.5,4.7,16.8,5.4) | — |
| ROM-13 qibla | fixed | Mats 0.0° off the qibla (inferred; CRS unconfirmed) | — |
| ROM-14 north window | fixed | North wall buried, 0.45 m RC; no window | — |

## Part B: new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| ROM-N01 | BLOCKER | `ens` (main), `gens` (lower), u 11.0–11.4, v 3.55–4.15 | SH-E blocks both ensuite doors (rules 6.1, 5.4) | Move SH-E to R(11.0,2.75,11.4,3.35) on both floors |
| ROM-N02 | MAJOR | lower `wc-l` (5.05, 9.75) | Pan in a 0.60 m slot | Pan on the south wall at u 5.9, facing north |
| ROM-N03 | MAJOR | lower `lounge` | Coffee table inside the sofa; the sofa blocks the TV | Re-plan (details) |
| ROM-N04 | MAJOR | `master` bed | 0.35 m from the north wall | Bed at v 2.05–3.85 |
| ROM-N05 | MAJOR | `kitchen` | SH-K breaks the L; hob landing 0.15 m; ~2.1 m of free worktop | Move SH-K to the entry; continuous L |
| ROM-N06 | MAJOR | `entry`, `porch` | Door hidden in a 2.0 × 2.1 m recess; 3 turns to the core (rule 2.6) | Owner choice: south door at u 2.6–3.6 |
| ROM-N07 | MINOR | master door (11.95, 7.3) | Diners see up the master's neck to the ensuite | Hinge at u 11.45; 0.5 m return at v 6.2 |
| ROM-N08 | MINOR | `store-u` | 0.92 m wide; the door swings onto a full-width shelf | 0.40 m shelves on the west side only |
| ROM-N09 | MINOR | `laundry`, `store-s` | 0.73 m entry strip; store only through the laundry; shelf through SH-K | Strip 0.9 m; cut the shelf |
| ROM-N10 | MINOR | `boys` bed (6.95, 11.05) | Bedhead on the laundry wall | Swap the bed and the desks |
| ROM-N11 | MINOR | `dress` | ~2.45 m of usable hanging for two adults | Add a wardrobe on the east wall |
| ROM-N12 | MINOR | main hall, SH-W (4.75–5.5, 8.84–9.44) | Free-standing box 0.1 m from the kitchen opening | Into the kitchen wall line |

## Part B details

**N01 (measured).**
- Sliders: `ens` v 3.50–4.40 and `gens` v 3.20–4.20 on u 11.4.
- SH-E (clear 0.28 × 0.48 m) fills v 3.55–4.15 on the bathroom side, leaving 0.25 and 0.35 m. No one can walk in, and a wheelchair cannot reach the seated ensuite.
- `doors.clear` does not test risers.
- *Fix:* lower slider at v 3.4–4.4, lower basin at (10.6, 4.15), WC at (9.8, 3.5). Today the bowl cuts the 1.5 m circle by 0.13 m².

**N02 (measured).** SH-W takes the corner of `wc-l`. The pan centre is 0.31 m from the riser and 0.29 m from the wall; ≥0.40 m is needed (assumption). It is the children's only shared WC.

**N03 (measured).** Sofa arms R(13.4,8.7,15.5,9.6) and R(13.4,7.4,14.3,9.6). The coffee table R(13.55,7.7,14.45,8.5) is inside the second arm, which ends 0.65 m in front of the TV with its seats at 90° to it. *Fix:*
- TV at u 13.3–14.8, fully backed by the wardrobes.
- Long arm u 13.0–15.6, v 8.8–9.7; short arm u 15.6–16.5, v 7.6–9.7.
- Coffee table u 13.6–14.8, v 7.6–8.4.
- Garden path v 9.7–10.85.

**N04 (measured).** The bed spans v 1.6–3.4 and the wall face is at 1.25. At v 2.05–3.85 it gets 0.80 m on the north and 1.80 m on the south up to the bookshelf.

**N05 (measured).**
- Hob drawn 0.6 m, though 0.9 m was asked, at v 11.45–12.05. The run ends at 12.20, with SH-K in the corner.
- Sink landing 0.20 m. Free worktop about 1.1 + 1.0 m for nine people.
- *Fix:* SH-K to R(3.8,12.25,4.4,12.85), a 0.6 m duct offset, with the shoe cabinet ending at v 12.15. Then the west run is v 9.56–12.85 and the south run u 4.46–7.05. 0.9 m hob at v 11.0–11.9; fridge hinged on the wall side, since its door now sweeps the hall opening.

**N06 (measured / ai_judgment).**
- The porch is open to the south only.
- The door faces RC-0, 2.0 m away. Inside, its axis ends on the shoe cabinet; then you turn north, then east.
- Rule 2.6 forbids notches.
- *Owner choice:*
  - (a) Keep it, with a lit porch and a sidelight.
  - (b) A door at u 2.6–3.6 on v 13.0 (in place of the window), under a 1.2 m canopy, running 3.3 m straight to the hall.

**N07–N12 (measured).**
- **N07:** The master door is 0.15 m from the living opening and about 2 m from the dining head chair. Its east-hinged leaf opens the view to the ensuite slider.
- **N08:** `store-u` is 0.92 m clear. Its shelf R(6.9,5.2,7.9,7.2) fills the width at the door, and headroom is about 1.6 m under the rest landing (inferred). It holds about 3.5 m³ in use.
- **N09:**
  - The laundry is entered through a strip 0.73 × 1.4 m; it works as about 3.8 m².
  - `store-s` opens only from the laundry. Owner: does that count as "separate" (rule 6.7)?
  - Fix: laundry north wall to v 10.0; shelf cut at v 12.9.
- **N10:** The dryer runs at night (assumption). Fix: desks on the laundry wall, bed at v 13.6–15.6.
- **N11:** Wardrobes of 2.05 + 1.0 m in an L; two adults need about 3.6 m. Fix: a 0.6 m wardrobe at u 12.54, v 1.9–3.3 (0.85 m aisle).
- **N12:** Pantry → island is about 4.9 m with a detour (≤3 m asked). Fix: riser R(4.4,9.5,5.0,10.1) behind the fridge.

### Rules audit (rooms)

- **pass:** 1.1–1.3, 1.5, 2.1, 2.4, 2.5, 3.2, 3.3, 4.1, 6.2, 6.5–6.7.
- **doubtful:**
  - 1.4: about 3 real seats.
  - 2.2: long hall.
  - 2.6 on the main floor: N06.
  - 3.1: the vista.
  - 4.8: windows on the walk.
  - 6.3: store access.
  - 6.4: TV on a bedroom wall; N07.
- **fail:**
  - 5.4 / 6.1: N01.
  - 7.3 / 7.4: N03, N04.

## What C11 gets right

- Dining for 8 that works, open to the living as an L.
- The master suite obeys rule 2.5, with a 1.04 m dressing aisle and a cot place.
- The laundry is right-sized at 4.8 m², with three separate stores and a drying yard reached by lift.
- In the wet cluster the WC is off the dry lobby; 0 pan sightlines.
- The children's rooms keep 4.3 × 4.8 m with beds off the glass; the living is 5.19 m clear wide, with a sheltered NE sofa.

## Out-of-scope notes

- LB-13.0 crosses both children's rooms: about 3.05 m ceiling (structure).
- Main accessible WC: basin in its transfer zone (accessibility).
- `doors.clear` ignores risers and dashed furniture (QA).
- Escape casements are notes only (safety).
