# 18 · Interior space and heights (INT) · C11

Build-ups are `assumption`: floor 0.15 m, slab 0.22 m, terrace 0.40 m, garage 0.45 m. Geometry is `measured` from `design.py`; ground is `measured` on the inferred TIN.

## Summary

1. Heights work: every room is ≥2.90 m clear under its beams after the 0.60 m formation and the 0.25 m set-downs. But no ceilings are declared, and the living room (3.26 m) is lower than the hall, kitchen and dining (3.45–3.53 m).
2. Rule 3.1 is still broken: the hall → living opening sits on the hall axis. The new 1.1 m shelf stands between the TV and the sofa.
3. The "walk-on rooflight" lies inside the roofed road lobby. Both family halls stay without sky light.
4. The garden walk and the loggia touch only at a point, so the owner's outdoor way into the lower floor does not connect.
5. There are furniture clashes the checks miss: the lounge sofa sits on its coffee table, the v 13.0 columns hit 9 pieces of furniture, and the lower WC pan is wedged into 0.60 m.

## Scorecard

SCORECARD: fixed=3 partly=8 not_fixed=2 worse=0 new_blocker=1 new_major=4 new_minor=5

## Part A · C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| INT-01 terraces | partly | Set-down 0.25 m on `t-south`, `deck-r`, `green-r` ✓. Slot channels are a note. The south canopy is a dashed rectangle, not in `structure()`. Uncovered doors: lobby → deck (12.6, 8.4), office (12.6, 11.9), master (18, 4.1), living east (18, 10.0). | 1.0 m canopies at +2.5 m over those 4 doors, as elements. Draw the channels. |
| INT-02 formation | fixed | 0.60 m; 1669.40 / 1673.00; deepest cut 4.22 m (checks.json) | — |
| INT-03 hall axis | not fixed | Opening v 7.45–8.65 (centre 8.05); the hall's east part v 7.3–8.75 (centre 8.03). A sightline from (2.2, 8.0) reaches the sofa's west-facing arm 14.6 m away, unobstructed. | See N01 |
| INT-04 lower hall | partly | Opening 2.7 m ✓; table removed ✓. Hall's west end 9.8 m from glass. The "rooflight" is fake (N04). | N04; lounge east glass head +2.90 |
| INT-05 ventilation | partly | SH-W, SH-K, SH-E on all floors ✓; hob 0.5 m from SH-K, no bulkhead ✓. No duct-zone ceilings declared; MVHR rates are notes. | Ceilings 2.70 m (main hall west, wet cluster) and 2.60 m (lower wet rooms, laundry); MVHR mains above the hall |
| INT-06 grandparents | partly | Wall on v 1.1 ✓; north window deleted ✓. The east window at v 1.3–2.7 is not drawn. The only glass is a 2.0 m slider under the 1.85 m balcony, in a room 6.6 m deep. | Window at u 18.0, v 1.4–2.9, sill +0.45 (ground 1669.2–1669.6) |
| INT-07 loggia sun | partly | Pergola ✓. The living's SE corner still roofs the loggia's north 2.05 m. At winter noon, sun reaches only 1.06–1.72 m up the lounge slider, through slats (inferred). | Do not count the lounge as a winter-sun room; glaze the slider to the soffit |
| INT-08 road axis | fixed | Office door at the lobby (10.45, 9.5); end wall lit by a rooflight 0.4 m away | — |
| INT-09 court door | fixed | Door under the dug porch, u 2.0, v 10.1–11.1; soffit ≈3.3 m | — |
| INT-10 dining | partly | Openings 51% of the perimeter (was 66%). The sideboard R(11.25, 8.85, 12.45, 9.3) is 0.45 m from the table end. The north end chair, pulled out, sits in the hall opening; the south one blocks the slider (u 9.5–10.9). | The 3.08 × 4.04 m room has no wall outside the chair zone. Move the sideboard to the kitchen and seat 4 + 4 on the long sides. |
| INT-11 ceilings | not fixed | None declared. Soffits: hall 3.45, kitchen and dining 3.53, living 3.26. The sequence runs backwards. | Hall 2.70; kitchen 2.90; dining 3.15 (flush with the beams); living 3.26 exposed; sofa band 2.70; children's rooms flat at 2.85 (hides LB-13.0) |
| INT-12 stair | partly | 309 mm goings on every flight ✓. Rooflight and window are notes. A window on v 1.1 (sill 1676.45) would face the PW-N piles (top 1677.0), 0.25 m away. | Draw a 2.2 × 1.2 m rooflight over the north landing; drop the window |
| INT-13 garage / lift | partly | Pit 1668.80 and overrun drawn ✓ (3.9 m from the top landing to the lid). The note's "1% (1677.50 → 1677.47)" is 0.44%; a true 1% puts the shutters 40 mm below the forecourt. | State 0.5% with a trench drain inside the shutters |

## Part B · new problems

| ID | Sev. | Where | Finding | Correction |
|---|---|---|---|---|
| INT-N01 | MAJOR | main `living` | The 1.1 m shelf (u 13.3–14.0, v 8.2–9.6) stands 0.25 m in front of the TV (u 12.7–13.05, v 8.75–9.95) and hides it below ~1.09 m from the sofa. | Screen plus TV (below) |
| INT-N02 | MAJOR | lower `lounge` | The sofa overlaps the coffee table by 0.60 m². Its east-facing arm ends 0.65 m from the TV and does not face it. | Re-plan the seating (below) |
| INT-N03 | BLOCKER | lower, walk / loggia | `walk-s` (u ≤15.4) and `loggia` (v ≤16.0) meet at the point (15.4, 16.0). The walk ends at a 1.73 m drop (ground 1668.27). Rule 4.11 and the README route fail. | Landing R(15.4, 16.0, 17.0, 17.12) at 1669.98 |
| INT-N04 | MAJOR | road `lobby-r`, main `hall`, `hall-l` | The "walk-on rooflight" R(11.4, 7.5, 12.2, 9.3) lies inside the roofed lobby R(6.8, 7.3, 12.6, 9.5). The 10.6 m main hall is windowless; its midpoint is ≥4.5 m from glass. | Real rooflight (below) |
| INT-N05 | MAJOR | lower `wc-l` | The pan (5.05, 9.75) is 0.31 m from SH-W and 0.29 m from the laundry wall: 0.60 m between obstructions (≥0.80, assumption). | Pan at (6.10, 9.70) facing north: 0.60 m each side; door at v 8.8–9.5; re-run §7.17 |
| INT-N06 | MINOR | v 13.0 columns | The 0.45 m columns stand in 0.20–0.25 m walls, so they jut 0.075–0.125 m into the rooms. They hit 9 pieces of furniture: beds and wardrobes in both children's rooms, the store shelves, the loggia bench, the kitchen counter, the office desk, the plant unit. | Move the furniture 0.10 m, or 0.25 × 0.60 m blade columns (engineer) |
| INT-N07 | MINOR | main `ens` | The window u 10.0–10.6 on v 1.1 faces the PW-N pile wall (top 1677.0) at 0 m; sill ≈1675.2. §7.12 missed it. | Delete it; extract via SH-E |
| INT-N08 | MINOR | `structure()`, sections | Beam tops are at FFL (LB-13.0 1673.05–1673.60), and the terrace build-up is drawn 0.25 m thick. Sections overstate the soffits by 0.12–0.15 m: children's rooms 3.08 drawn vs ~2.96 real; 2.90 under LB-13.0. | Beam tops at FFL − 0.15; draw the 0.40 m build-up |
| INT-N09 | MINOR | suspended slabs | Soffit ≈1669.55 over a void dug to 1669.40: 0.15 m at the lounge's west edge (ground 1669.85 at (15.4, 6.2)), ~0.1 m under `t-low` at (18, 1.1). It cannot be ventilated or inspected. | Void ≥0.30 m (dig to ~1669.25) |
| INT-N10 | MINOR | lower stair, `store-u` | Opens to `hall-l` 1.2 m only (C10: 2.6 m). The store has ≥2.0 m headroom only at v ≈3.3–7.3: ~3.8 of its 5.5 m² (inferred). | Open the stair fully over u 8.2–9.4; report the usable store area |

## Part B details

**Clear heights (m).**

| Space | Clear | Under beam |
|---|---|---|
| Main hall west, wet cluster | 3.45 | — |
| Hall east, kitchen, dining | 3.53 | 3.15 (MB-9.4 / 9.5 / 12.6) |
| Living, master | 3.26 (3.17 at the east edge with the slab cast to falls) | 3.15 |
| Lower hall, lounge, grandparents | 3.23 | 3.00 (LB-9.5) |
| Children: north 2.05 m / under `t-south` | 3.23 / 2.96–2.91 | 2.90 (LB-13.0) |
| Loggia / road rooms / garage | 3.10 / 3.08 / 3.08 | garage 2.70 (RB-5.3) |

There is plenty of height. The fault is proportion: the kitchen is 5.0 × 3.5 m on plan and 3.5 m high, a shaft.

**N01, living room.**
- From the eye on the sofa's west-facing arm, (17.2, 7.6) at 1.15 m, to the TV centre (12.9, 9.35), the line crosses the shelf at 1.08–1.10 m (inferred).
- Fix:
  - A 2.1 m-high, 0.35 m-deep bookcase screen at u 13.4–13.75, v 7.3–8.7, opposite the opening, with the TV on its east face 3.4 m from that sofa arm.
  - Delete the west-wall TV. People entering turn south at v 8.7–9.7, outside the viewing line.
  - The screen is furniture, so rule 3.3's clear square holds.

**N02, lounge.**
- Sofa arms R(13.4, 7.4, 14.3, 9.6) and R(13.4, 8.7, 15.5, 9.6); coffee table R(13.55, 7.7, 14.45, 8.5); TV R(13.0, 6.3, 14.5, 6.75).
- Fix:
  - Sofa R(13.4, 8.9, 15.8, 9.8) facing north, 2.4 m from the TV centred at u 14.6.
  - Coffee table R(14.0, 7.6, 15.2, 8.3).
  - Two armchairs R(16.3, 7.9, 17.1, 9.6) facing west, 1.0 m clear of the tea bar.
  - The garden route at v 9.8–10.85 stays 1.05 m.

**N03, outdoor entry.**
- Ground is 1668.08 at (16.5, 15.8): both the loggia's front and the walk's end are unguarded drops.
- Fix:
  - A suspended landing R(15.4, 16.0, 17.0, 17.12) at 1669.98 on a wall at v 17.12, inside the setback.
  - Open the loggia front at u 15.5–17.0 below LB-16.0.
  - 1.1 m guards on u 17.0–18.0 and on the landing's edges.

**N04, halls.**
- Put a 0.8 × 1.8 m rooflight in the road roof at u 11.4–12.2, v 7.5–9.3, over the lobby's glass floor, so the main hall's east end gets sky light.
- Owner's option: a second glass panel in the main hall at u 11.4–12.2, v 7.4–8.6, down to `hall-l`.
- Draw the stair rooflight (INT-12). It reaches all three halls through the stair openings.

## What C11 gets right

- The 0.60 m formation and the 0.25 m set-downs are in the model, and every room keeps ≥2.90 m under its beams.
- The hob sits 0.5 m from riser SH-K: a straight hood duct, with no bulkhead.
- The lift door, the dining opening and the dining slider still line up: you step out of the lift and face the valley.
- At the road, the arrival ends on a lit wall. On the main floor, the front door sits under a real covered porch.
- The lower hall is a clear 4.4 × 3.65 m landing with a 2.7 m opening to the lounge.
- The grandparents' north slot is closed, and their twin beds have a 1.75 m transfer zone.

## Out-of-scope notes

- MB-12.6 ends at (12.6, 13.0) with no column under it, and no main-storey beam runs on v 13.0 between C-11.1 and C-15.4 (structure).
- The dining slider overlaps the face of column C-11.1 by 25 mm (windows).
- The cylinder in the plant room above the kitchen needs a tray and a drain (MEP).
- The court stair passes 0.3–1.3 m from the boys' window, at eye level above its sill (privacy).
- The garden store under `t-low` is a 1.3 × 6.3 m corridor (landscape).
