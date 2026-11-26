# C10 review 16: consistency, geometry and boundaries (QA audit)

All numbers were computed with shapely and `zg` from `990_2026-11-18_claude-c10/design.py` / `engine.py` (`measured`) unless marked otherwise. The terrain is a 27-point TIN (an inferred surface). This is a concept-stage review.

## Summary

1. Everything is inside the parcel and the stored envelope (0.00 m² outside). The envelope has setbacks only on the south and east (owner-confirmed); north and west are 0 m.
2. `gs-court` falls 2.30 m in 2.00 m (115 %). It cannot be built as a stair.
3. The three outputs disagree under the road hall: design.py has a court, the ground model has soil, the 3D has a sealed void. The entry window opens into it.
4. 49 % of the garage and an 18.7 m² strip under the master suite stand over nothing designed. Sections draw posts, the 3D draws walls, the plans draw nothing. About 70 % of the upper exterior walls sit on no wall below.
5. About 20 retaining edges 0.5–3.8 m high appear on no plan. The pit walls (up to 3.7 m) appear in no section.

## Findings

| ID | Sev | Where | One line |
|---|---|---|---|
| QA-01 | BLOCKER | `gs-court` R(4.6,16.4,6.6,17.4) | Drops 2.30 m in 2.00 m. It needs 14 risers and 3.64 m of goings |
| QA-02 | BLOCKER | main `entry` window (2.0, 9.9–11.2) | Opens into a sealed void with soil +0.54 to +1.11 m |
| QA-03 | BLOCKER | `fore` south edge v 11.6 | Unguarded drop of 1.9–3.8 m, 0.25 m from the front door |
| QA-04 | MAJOR | garage R(0,1.1,6.8,9.5) | 28.2 m² over nothing, void 0.05–3.71 m |
| QA-05 | MAJOR | master/dress/ensuite, v 1.1–2.8 | 18.7 m² over a 0.6–3.7 m void. The guest north window faces it |
| QA-06 | MAJOR | stacking of walls | Main south façade and road-level south/office walls sit on no wall below |
| QA-07 | MAJOR | site-wide | Retaining walls exist only in the sections and 3D. Pit walls are in no drawing |
| QA-08 | MAJOR | `gstair` | 22 risers, no landing. 1.8 m / 3.6 m drops on its two sides |
| QA-09 | MAJOR | `boys` south wall | +1.19 m of soil against it. The path is 0.41 m below the window sill |
| QA-10 | MAJOR | checks.py | Several checks skip levels and kinds. The daylight check counts a window into a void |
| QA-11 | MINOR | v 17.42 setback | Four elements end 0.00–0.02 m from the line, where walls up to 1.8 m must stand |
| QA-12 | MINOR | sections.png | Soil hatch drawn inside rooms. No section cuts the outdoor stairs |
| QA-13 | MINOR | lower SE, notes | Lower slab up to 1.35 m above the ground. Terrace area stated as 65 m² against 69.36 m² |

## Finding details

**QA-01 BLOCKER. `gs-court` is not a stair.** It falls from 1673.60 to 1671.30 over u 4.6→6.6: 2.30 m in 2.00 m. At a 0.164 m riser it needs 14 risers and 13 × 0.28 = 3.64 m of going. The 3D draws 14 treads on 2 m, which makes each going 0.14 m. `path-s` then falls another 3.70 m (to 1667.60) on a 32 % natural slope, and design.py gives it no steps. *Fix:*
- Flight 1: cut into the court's south strip, v 16.4–17.1, from u 1.0 (1673.60) to u 4.64 (1671.32), 14R × 0.163 / 13G × 0.28. That strip is fill (1.0–1.8 m) anyway.
- Landing at 1671.30 over u 4.64–6.6 (natural ground 1671.6–1671.3).
- `path-s`: 22R in 3 flights with landings, following the natural ground down to 1667.60.

**QA-02 BLOCKER. The entry window looks into a void.** `court-w` includes (0–2, 9.6–11.6), under `hall-r`.
- `GroundModel` subtracts building footprints from platforms, so 4.36 m² of court is lost. At (1, 10.4) the finished ground is 1674.28.
- Natural ground outside the window is +0.54 m at 0.3 m and +1.11 m at 2.0 m above the main FFL: above the 0.9 m sill.
- The 3D (`model3d.py` plinths) seals the area with concrete walls on u 0 and v 11.6. Section A–A shows soil and a "wall 2.8 m".
- If it were dug as design.py says, the window would face a 3.8 m wall (1677.40 → 1673.60) 2.0 m away, under a slab.

*Fix:* delete the window. The entry keeps its south window (3.0–4.0, 13.0) and the glazed door. Remove u 0–2, v 9.6–11.6 from `court-w`.

**QA-03 BLOCKER. Open edge of the forecourt.** `fore` is at 1677.40. At v 11.6 it drops to the court at 1673.60 (3.80 m), to the stair head, and to natural ground at 1675.46 (1.94 m at u −2.4). The front door spans v 10.15–11.35, 0.25 m from that edge. No drawing shows a guard. *Fix:* a 1.1 m guard along v 11.6, u −6.35…0, open only at u −2.4…−1.2. Or adopt QA-08.

**QA-04 MAJOR. What the garage stands on.** 28.20 of 57.12 m² is over no main-floor room: u 0–2; u 2–3.8 × v 1.1–4.6; u 3.8–6.8 × v 1.1–2.8. Slab underside to ground is 0.05–3.71 m. Section C–C draws two posts (u 0 and about 3.2). The 3D draws concrete skirts on u 0 and v 1.1. The road plan draws nothing. *Fix:* draw these walls:
- u 0, v 1.1–11.6: foundation wall that also retains the forecourt fill (up to 2.98 m at (0, 11.5));
- v 1.1, u 0–6.8: 0.35–3.8 m;
- line u 2.0 extended from v 4.6 to v 1.1;
- line v 2.8 extended from u 3.8 to u 2.0.

State whether each void is filled or ventilated.

**QA-05 MAJOR. Void under the master suite.** The main floor reaches v 1.1, the lower floor only v 2.8 (and nothing lies under `ens` from u 9.4–11.4 down to v 5.0). That leaves 18.68 m² of slab 0.58–3.74 m above the ground, and 8.2 m of north façade (u 9.6–17.8) with no wall below. The 3D closes the void on v 1.1 and u 17.8, so the guest north window (16.0–17.6, 2.8) faces a sealed space 1.7 m deep: soil +0.11 to +0.32 m, slab overhead, no daylight. *Fix:* carry the lower north wall at v 1.1 from u 11.4 to 18.0 as a basement wall (soil 0 to +1.6 m). That adds about 11 m² to the guest suite. Move the guest window to the east wall.

**QA-06 MAJOR. Walls over no wall** (±0.2 m).

Road level: 34.6 of 48.8 m of exterior wall.
- `plant` and `wc-r` south wall (v 13.3, u 3.4–9.0): 0.3 m beyond the main wall at v 13.0, 4.5–6.4 m above the ground.
- `office` east wall (u 12.2) and south wall (v 12.6): land mid-span on the dining roof (main walls at u 12.6 and v 13.0).
- `lobby-r` east wall (u 11.4): lands mid-span on the main hall roof.

Main floor: 39.9 of 55.4 m. 14.8 m is in the NW, on soil, which is acceptable. The rest is the whole south façade (v 13.0, u 4.8–17.8, three sliders), mid-span over the boys' and girls' rooms (lower walls at v 11.6 and v 16.4).

*Fix:*
- Road south wall to v 13.0: `plant` R(3.4,11.6,7.0,13.0) = 5.0 m², `wc-r` 2.8 m².
- `office` to u 12.6 / v 13.0: 3.6 × 3.5 m.
- A beam line or wall under v 13.0 (for the structure reviewer).

**QA-07 MAJOR. Retaining walls missing from the drawings.** Measured steps in the finished ground (m):

| Edge | Step (m) |
|---|---|
| forecourt south | 3.80 |
| court west / south / east | 3.61 / 1.71 / 1.63 |
| `gstair` west / east | 1.80 / 3.61 |
| garden terrace north | 1.37 |
| garden terrace east and south | 2.38 |
| 14-step stair, two sides | 1.82 / 2.26 |
| lawn south | 1.15 |
| lawn downhill edge | 1.32 |
| lawn north (0.6 m from the neighbour) | 1.22 |
| `gs-court` sides | 1.53 / 1.73 |

None appears on any plan. The README says the slope below the lawn "stays natural", but the lawn edge needs a 1.3 m wall, and the 3D draws it.

`section_panel` skips walls at pit edges, so the deepest walls are drawn only as room lines: lower stair north/west +3.67/+3.73 m, WC/shower west +3.49 m, laundry west +3.16 m.

*Fix:* draw every wall at 0.3 m or thicker, with its top and bottom levels, on plans and sections.

**QA-08 MAJOR. Stair from the road.** It falls 3.80 m over 5.80 m in one straight flight: 22R, 0.173 / 0.276, no landing. At its top it is 1.80 m above natural ground on the west and 3.61 m above the court on the east. *Fix (the owner's proposal):*
- Put the flight on the west boundary.
- Excavate the triangle (−6.35,11.6)–(−1.2,11.6)–(−1.2,17.4)–(−9.52,17.4) to 1673.60. That is 39 m² added to the court.
- Up to 3.8 m of cut at the road edge, so a boundary wall is needed. How the road is supported must be confirmed.
- Split the flight 11R + 1.2 m landing + 11R.

**QA-09 MAJOR. Soil against the bedrooms.** The boys' south wall has +1.19 m of soil at (6.8, 16.4), falling to −0.25 m at u 11.1. At the window (8.9–10.9) the ground is +0.49 m (0.3 m out), 0.41 m below the sill, and the path runs at that height. The guest north wall has +0.77 m, the seated ensuite up to +1.85 m. The girls' room and the lounge are clear. *Fix:* a drained strip 0.9 m wide at 1669.85 along v 16.4–17.3, u 6.8–11.1 (cut ≤1.3 m, wall at v 17.3). Run the path beyond it.

**QA-10 MAJOR. checks.json.** Claims verified independently, all true:

| Claim | Measured |
|---|---|
| garage | 57.12 m² |
| kitchen / dining / living | 15.1 / 11.1 / 33.9 m² |
| east garden | 150.9 m² |
| main-floor terraces | 69.36 m² |
| lower dig | 200.0 m³, max 3.95 m |
| main dig | 15.2 m³ |
| 14 exterior doors | Δ −0.10 to 0.00 m |

Gaps:
- `geom.terraces` skips the road level and the stair and lawn kinds.
- `ground.openings` skips the road level and samples only 0.4 m out, so the entry window passes at +0.57 m against the +0.60 m limit while the soil reaches +1.11 m within 2 m.
- `daylight` counts the guest north window (QA-05).

*Fix:* sample 0.3–2.0 m out, test against plinth voids, and include all levels and kinds.

**QA-11 MINOR. Zero margin at the south setback.** The court, `gs-court` and `path-s` end at v 17.40, the lawn at 17.42. Walls of 1.71, 1.73 and 1.15 m stand there, so their thickness crosses the line. Stop these platforms at v 17.1.

**QA-12 MINOR. Sections.**
- A–A, B–B and C–C fill the laundry, hall, stair, ensuite and main WC with a soil hatch, so they read as rooms full of soil.
- A–A shows soil where the court is (QA-02).
- C–C and D–D draw posts where the 3D has walls.
- No section cuts `gstair`, `gs-court` or `path-s`. Add N–S cuts at u −1.8 and u 5.6 and a W–E cut at v 16.9.
- Otherwise every room, slab and level in A–D matches design.py.

**QA-13 MINOR.** The lower slab stands 1.35 / 1.26 / 0.77 m above the ground under the lounge, girls and guest rooms. That is a raised floor, not a pit. The note in design.py says "65 m²" of main terraces; the geometry gives 69.36 m².

## What C10 gets right

- All 15 outdoor elements and all 3 plates are inside the parcel and the envelope.
- All 14 exterior doors open onto a surface at their own level. None opens onto air or soil.
- The 1670.00 contour line is exact: (16.8, 1.1) = 1669.99 and (10.5, 16.4) = 1670.01. Day rooms, the master, the girls' room and the lounge have no soil above floor level.
- One shared `GroundModel` drives the sections, the checks and the 3D, so each inconsistency can be fixed once.
- The earthwork figures reproduce exactly.

## Out of scope (one line each)

- Structure: transfer beams (QA-06). Columns under the loggia and balconies.
- Services: the sealed voids need ventilation and access.
- Safety: guards on the 14-step lawn stair.
- Car access: the forecourt is only 1.78 m deep at the north shutter (v 3.25).
