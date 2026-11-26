# C11 review 08: sun, daylight, views, ventilation (prefix SUN)

Concept-stage review. Nothing here is engineered or code-checked.

## Summary

1. The SSE day rooms and the children's rooms still get the full 6.6–6.8 h of sun on 21 Dec. If the 1.0 m canopy is built, it cuts June gain on the main-floor SSE glass by 53–71%. The qibla (204.64°) and true north are correct and shown on every plan.
2. **The lower floor got darker.** The lounge's SSE glass now sits 2.05 m under the suspended living room. The pergola adds nothing: 1.2 h with it and 1.2 h without it (C10: 1.6 h). The grandparents' room drops to 0.9 h (C10: 1.1 h).
3. The cause on the ENE side is the continuous 1.85 m balcony slab. In December the sun runs along that façade from the SE (azimuth 132–154°), so the balcony south of each lower window shades it.
4. The new 2.0 m opaque balcony screen at v 6.2 halves the master's winter sun (2.3 → 1.2 h).
5. The "walk-on rooflight" lies inside the roofed road lobby, so it brings no daylight. The lower hall is still windowless. The stair rooflight, the stack and the stair window exist only as notes.

**Method** (`measured` below): my C10 raytrace re-run on `design.build()` with the GroundModel ground, the PVGIS horizon and clear-sky sun at 34.969 N, 46.356 E. +u faces 67.97° true (grid + 0.78°; the CRS is unconfirmed). Modelled: walls 0.25 m outside the line, glass at the outer face (no reveal), soffits at 1673.05 and 1673.15, the canopy at 1677.15–1677.35, the solid parapets, and the 2.0 m screen. Sills 0.9 m, heads 2.4 m. No neighbours.

## Scorecard

SCORECARD: fixed=2 partly=7 not_fixed=1 worse=2 new_blocker=0 new_major=4 new_minor=3

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| SUN-01 Qibla | **fixed** | `measured`: great-circle bearing 204.64°; the two mats are 0.0° off; the arrow and true north are on all three plans. | Glare: see N06. |
| SUN-02 ENE glass | **partly fixed** | `measured`: main-floor ENE glass 16.9 → 9.4 m². It still takes 2,641 Wh/m² on 21 Jun (13.8 kWh living, 10.9 kWh master). The deck ends flush at u 18.0, so nothing shades it. The blinds are notes only. | Draw external blinds on every ENE opening (main, lower, office). Uw ≤ 1.0. |
| SUN-03 SSE summer shade | **partly fixed** | `measured`, if built: 21 Jun 392–644 Wh/m² (1,332 without it); 21 Dec unchanged. It exists only on the plan (N05). | See N05. |
| SUN-04 Grandparents | **made worse** | `measured`: 21 Dec 0.9 h, 181 Wh/m² (C10: 1.1 h, 215). One 2.0 m slider for a 28 m² room 6.6 m deep (glass ≈16%). NE kept by consensus (accepted). | See N02: grate the balcony and widen the slider to v 3.3–5.5. |
| SUN-05 Lounge and lower hall | **made worse** | `measured`, 21 Dec: SSE 1.2 h (681 Wh/m²), ENE 0.7–1.0 h (C10: 1.6 and 1.2 h). `hall-l` has no glass; the nearest is 5.4 m beyond the opening. | See N01, N02 and N04. |
| SUN-06 Ventilation | **partly fixed** | `measured`: an MVHR is drawn in the plant room. The bedrooms are still single-sided. The stair rooflight (the stack) and the girls' second opening are not drawn. | Draw a 2.2 × 1.2 m operable rooflight over the stair (u 7.0–9.2, v 1.5–2.7, about 1680.8) and a girls' high window at u 15.4, v 12.4–13.6, sill 1.8 m. |
| SUN-07 Lawn | **partly fixed** | `measured`, 21 Dec: lawn sunlit 39% / 27% / 12% at 13/14/15 h. The band u 19.2–22, v 12–17 is 100% sunlit to 14:00. The play area is a note. | Draw the play area, sandpit and bench in that band. No evergreens there. |
| SUN-08 Stair | **not fixed** | `measured`: no stair window in `windows`; CIR-03 lists it as a note. | Add a window at u 7.0–9.2, v 1.1, sill 1676.45, obscured. Draw the rooflight (SUN-06). |
| SUN-09 Master NNW | **fixed** | `measured`: u 15.6–16.8, obscured to 1.7 m. | Draw the external shutter. |
| SUN-10 Views | **partly fixed** | `measured`: trees drawn; the balcony rail is a note; the clerestory removed the sofa's view (N07). The city's bearing is unknown. | Draw the open rail on `balc-e`; ask the owner for the bearing of the view. |
| SUN-11 Children | **partly fixed** | `measured`: beds off the window wall; 21 Dec 6.8 h; rule 4.8 holds (+0.37 m / 0.00). The boys' glass is still about 15% of floor, because ground west of u 8.9 is up on the court stair. | Boys' head to 2.65 m (about 17%). Unknown: a 6 m neighbour 3 m south of the boundary would take the noon sun (`inferred`). |
| SUN-12 Drawings | **partly fixed** | `measured`: north and qibla on the plans. Façade bearings (68°/158°), sun arcs and the site sheet are missing. | Add them to the north block and `site.png`. |

## Part B: new problems

| ID | Severity | Where | Finding | Correction |
|---|---|---|---|---|
| SUN-N01 | MAJOR | lower lounge SSE slider; pergola R(15.4, 13.0, 17.8, 15.2) | C11-SUN-04 is marked "Done" but gives +1% (681 against 672 Wh/m²). | Open the whole strip u 15.4–18.0, v 13.0–16.4 and use a rail guard there. Measured: 2.1 h, 1,231 Wh/m² (+81%). |
| SUN-N02 | MAJOR | lower ENE: grandparents' slider v 3.3–5.3, lounge v 6.6–10.8 | The continuous 1.85 m balcony slab shades the winter sun coming along the façade. | Use an open grating on the outer 1.0 m (u 18.85–19.85). Measured: 1.6–1.7 h. External blinds then become essential. |
| SUN-N03 | MAJOR | main, `balc-m`/`balc-e` screen at v 6.2, u 18.25–19.85 | The opaque 2.0 m screen halves the master's winter sun: 2.3 → 1.2 h, 349 → 166 Wh/m². | Make it obscured glass, or opaque to 1.1 m with obscured glass above. Measured: back to 2.3 h. |
| SUN-N04 | MAJOR | road lobby R(11.4, 7.5, 12.2, 9.3); `hall-l` | The "walk-on rooflight" lies inside the roofed lobby, not the deck (the deck starts at u 12.6). It gives no daylight, and in any case it would land in the main hall or dining. The lower hall stays dark. | Delete it or move it into `deck-r`. Light `hall-l` through 0.5 m obscured fanlights over the boys' and girls' doors on v 10.95. |
| SUN-N05 | MINOR | main SSE canopy, u 4.6–18.0, v 13.0–14.0 | The canopy is a plan outline only: it is not in `structure()`, the sections or the 3D. Its level and support are undefined. It projects only 0.75 m beyond the wall face. | Add element CAN-13 at 1677.15–1677.35, 1.25 m from the line, so 1.0 m clear. Draw it in sections A–A and E–E and in 3D. |
| SUN-N06 | MINOR | living prayer place (16.55, 11.7) | The worshipper faces 204.6° into the south glass. On 21 Dec at 14:00 the sun stands at azimuth 210°, altitude 25°: in the face during Dhuhr and Asr. | Sheer curtains or internal blinds on the slider at u 12.7–15.1 and the window at u 15.75–16.35. |
| SUN-N07 | MINOR | living ENE | The L-sofa backs onto the u 18 wall, the TV is on the west wall, and the clerestory sits behind people's heads. The valley view is only to the side, through the 1.8 m slider. | Two armchairs at u 16.6–17.4 facing the slider, keeping 0.9 m clear to the door. The owner decides between view and TV. |

## Part B details

**SUN-N01.** C10's raytrace had the lounge glass under 1.4 m of living-room slab; C11 has it under 2.05 m (`main.suspended` to v 13.0). At noon on 21 Dec the profile angle is 33.6°:
- Rays from the upper glass meet the underside of the living-room slab.
- Rays from mid-height pass through the pergola, then hit the 1.1 m solid parapet at v 16.25–16.4.
- Rays from the sill hit the remaining terrace strip at v 15.2–16.4.

Opening the whole strip at v 13.0–16.4 with a rail guard (`measured`): 2.1 h and 1,231 Wh/m², with June unchanged at 157 Wh/m². The loggia under the living room (2.05 m deep) stays a dry route. The cost is about 2.6 m² of terrace. CORRECTIONS.md says "Done" without re-raytracing.

**SUN-N02.** I traced which solid blocked each ray (`measured`). Between 08:30 and 10:20 on 21 Dec, every blocked ray from the grandparents' slider hits `balc-e` at u 18.4–19.7, v 6.3–11.1. Removing `balc-m` alone changes nothing (0.9 h). An open grating on the outer 1.0 m of both balconies gives:
- grandparents: 1.7 h, 304 Wh/m²
- lounge ENE: 1.6–1.7 h

The ENE façade cannot exceed 2.3 h in December. The grating raises June gain from 1,627 to 2,328 Wh/m², so the blinds (SUN-02) are required. Widen the grandparents' slider to v 3.3–5.5.

**SUN-N03.** The screen is needed for privacy, but it stands south of the master's only real window. Obscured glass keeps the privacy and restores 2.3 h, 349 Wh/m².

**SUN-N04.** In `road_level()` the label is drawn inside `lobby-r` R(6.8, 7.3, 12.6, 9.5), under the road roof. The lower hall (about 16 m²) has no window. Laminated, obscured fanlights over the two bedroom doors bring sunlit south light into it without breaking the acoustic walls.

## What C11 gets right

- Kitchen, dining, living, boys and girls keep 6.6–6.8 h of sun on 21 Dec. Rule 1.1 holds: the kitchen has a 2.0 m slider and a south window.
- Main-floor ENE glass cut by 44%, and the north glass reduced and obscured. The worst summer gains are halved.
- The 0.4 m terrace lip shades the children's windows in June (713 against about 1,332 Wh/m²) and costs no winter sun. Rule 4.8 holds with 0.37 m or less of ground above the floor.
- Qibla computed correctly, mats exact, arrow and true north on every plan.
- The play band of the lawn has full winter sun until 14:00.

## Out-of-scope notes

- The pergola is a 2.4 × 2.2 m hole in the walkable south terrace: no guard and no slat structure is drawn (safety, structure).
- The canopy over a south terrace with a 1.1 m parapet needs a snow-load and drip-line check (structure, water).
- People on the court stair look straight into the boys' window, 0–1.3 m away (privacy).
- The lawn is down to 56.8 m² (landscape).
