# 06 · Internal circulation, stair and lift: review of C11

Concept-stage review; not engineered or code-checked. Product and code figures are `assumption`.

## Summary

1. The stair is now one stair. Every flight has 12 risers and 11 goings of 309 mm. Headroom is at least 3.3 m (`measured`).
2. The lift is a true stretcher shaft, 1.80 × 2.64 m clear, with a clear 1.5 m circle at every door. The LC300's tailgate is about 6 m from the lift, all indoors.
3. The core's safety is still on paper. There is no spine wall and no guard on the road or main floors, although the ledger claims one. The road landing edges a 3.9 m drop that check §7.7 cannot see.
4. Two doors cannot be built as drawn. The laundry neck is 0.73 m clear but has a 0.8 m door. The master and grandparents' doors are 1.0 m leaves in passages only 1.00–1.04 m clear.
5. Wudu → prayer is still about 14 m. The stair still has no daylight, and no section cuts its flights.

## Scorecard

SCORECARD: fixed=8 partly=4 not_fixed=2 worse=0 new_blocker=1 new_major=1 new_minor=6

## Part A · C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| CIR-01 lift landing | **fixed** | `measured`: the table is gone. The §7.10 circles hit 0 m² of wall and 0 m² of furniture on all 3 floors; dashed items are included. | — |
| CIR-02 lift car | **fixed** | `measured`: `room_dims` gives 1.80 × 2.64 m clear. The 0.9 m doors are on the south face of every floor. | Front wall: see N05 |
| CIR-03 pit and overrun | **partly fixed** | `measured`: `LIFT-PIT` 1668.80–1670.00, 2.7–3.1 m below natural ground. `LIFT-OVR` 1680.80–1681.60, which leaves about 3.9 m of head. `inferred`: F–F does not show them. No file mentions a rescue device or battery. | Show the pit, the drain invert at 1668.2 and the upstand in F–F. Note the automatic rescue device, battery for ≥5 trips and the GSM alarm. |
| CIR-04 garage → lift | **fixed** | `measured`: the aisle is clear. The fire door sits at v 8.35–9.35, swings into the garage and is hinged at 9.35. The bikes are on the back wall. Door → lift door 3.9 m. | Aisle width: see N06 |
| CIR-05 stair–garage-lobby air | **fixed** | `measured`: a 2.6 m `screen` crosses the stair at v 7.3 on the road floor, and the garage door is a fire door. | Draw the 1.0 m self-closing leaf. |
| CIR-06 wudu → mats | **partly fixed** | `measured`: the mats are 0.0° off the qibla. `inferred`: the route wudu → hall → living → mats (16.55, 11.7) is about 14 m, between the TV and the shelf. | Owner's call (Q12): a prayer zone at about (12.0, 11.8) cuts it to about 9.5 m. |
| CIR-07 guest → lawn | **fixed** | `measured`: 2 × 8 risers of 149 mm with 320 mm goings and 1.2 m landings. Slider → lawn is about 11 m. | — |
| CIR-08 under-stair void | **fixed** | `measured`: `store-u` is 5.5 m² clear with a 0.8 m door. | Usability: see N03 |
| CIR-09 laundry and drying | **partly fixed** | `measured`: 4.8 m² with a heat-pump dryer and an airer. The yard on `deck-r` is about 10 m away plus two floors by lift. No window. No loggia rack is drawn. | Draw a fold-down rack on the loggia's west wall, u 15.4, v 12.3–14.0: about 9 m away on the same floor. |
| CIR-10 going and drawing | **fixed** | `measured`: 24R per storey, 309 mm everywhere, 2R+G 0.634 / 0.609. The labels match. | — |
| CIR-11 stair daylight, no-power use | **not fixed** | `measured`: no window and no rooflight over `STAIR` on any floor. The ledger lists these as "notes". The north ground is 1673.2 (`zg`). | Draw an operable rooflight, 2.2 × 1.2 m, at u 6.95–9.25, v 1.25–2.45. Add a high obscured north window, sill ≥1676.45, if PW-N allows. Add step lights and glow nosings. |
| CIR-12 open well, guards | **not fixed** | `measured`: road and main cuts at v 2.0 and 4.0 run clear from 6.925 to 9.25/9.275. `core_walls()` has no spine line. The flights are 1.075 m clear, not 1.2 m. | See N01. |
| CIR-13 main hall | **partly fixed** | `measured`: 10.48 × 2.08 m clear. The kitchen opening is 1.1 m (I asked for 1.6 m). Pantry → kitchen opening 3.4 m. | Kitchen opening u 5.45–7.05. Hall length is the owner's call (2.2 open). |
| CIR-14 master privacy | **fixed** | `measured`: a 1.0 m door at (11.95, 7.3) swings into the master. | It cannot be framed: see N04 |

## Part B · New problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| CIR-N01 | BLOCKER | Core, road and main, u 6.8–9.4 × v 1.1–5.9 | No spine and no guards. The road void is drawn as treads. §7.7 reports "none missing". | A 0.15 m spine on u 8.10, guards, and the check extended |
| CIR-N02 | MAJOR | Lower laundry neck, u 6.8–8.2 × v 10.1–10.95 | 0.73 m clear with a 0.8 m door. It is the only way to the laundry and to `store-s`. | Lav wall to v 9.80 |
| CIR-N03 | MINOR | Lower `store-u` | 0.92 m wide, with the shelves inside the door's swing. A void is sealed under the east landing. | 0.40 m shelves on one side; take in the under-landing bay |
| CIR-N04 | MINOR | `master` / `guest` doors, u 11.45–12.45, v 7.3 | 1.0 m leaves in passages 1.00 / 1.04 m clear | 0.9 m leaves, ≥0.85 m clear |
| CIR-N05 | MINOR | Lift front, v 7.3 | The door face is a 0.12 m partition. | A 0.20 m RC front |
| CIR-N06 | MINOR | Garage aisle | 1.135 m clear; the EV point is in it. | Cars to u ≤5.45 |
| CIR-N07 | MINOR | Road lobby, rooflight R(11.4,7.5,12.2,9.3) | It is a walk-on glass panel on the lift → terrace route. | Slip-resistant, or move it |
| CIR-N08 | MINOR | Sections, notes | No cut through the flights. The notes say "4.4 m", checks say "3.6 m". | Section at u 8.7; quote 3.9 m |

## Part B · Details

**CIR-N01** (`measured`)
- **The well.** The 0.25 m RC core leaves flights 1.075 m clear and an open 0.20 m well. That well drops 7.5 m, from the road floor to 1670.0.
- **The road void.** The road→main rest landing is at 1675.55, only 1.95 m below the road FFL. So the road floor must be void over u 6.8–9.4 × v 1.1–≥3.1 and over the west flight. The road landing at v 5.9 edges a drop of up to 3.9 m.
- **What the drawing and the check show.** `road.png` draws both flights as "DOWN 24R" treads, with no void line and no guard. `guards()` scans terraces only.
- **The claim.** STR-06 and the `core_walls()` docstring say "solid spine". No spine is drawn.
- **Correction:**
  - A 0.15 m RC spine centred on u 8.10, v 2.5–5.9, on every storey. Both flights are then 1.10 m clear; today the lower wall on u 8.0 makes them 0.95 / 1.15 m.
  - A 1.1 m guard on every road void edge. Handrails on both sides.
  - Draw the void.
  - Make `guards()` test internal floor edges with a drop of 0.6 m or more.

**CIR-N02** (`measured`)
- **The neck.** It runs between the lav wall (0.12 m, v 10.1) and LW-10.95 (0.20 m), leaving v 10.16–10.89 clear.
- **The door.** The 0.8 m door at (8.2, 10.52) is wider than that, so its frame cannot be built.
- **Laundry area.** The 4.8 m² laundry counts about 1.0 m² of this neck.
- **Correction.**
  - Move the lav's south wall to v 9.80 and its basins to v 9.5.
  - The neck becomes 0.99 m clear, with a 0.8 m leaf hinged at v 10.85.
  - Report the laundry as about 3.8 m² plus the neck.

**CIR-N03** (`measured`)
- **Width and shelves.** The store is clear from u 6.95 to 7.875. The shelves rect(6.9,5.2,7.9,7.2) fill its width.
- **The door swing.** The door's swing (u 7.2–8.0 × v 6.25–7.05) lands inside the shelves. `checks.py` (335, 593) never tests doors that touch a stair room.
- **Headroom.** It is 1.9 m or more only at v ≈3.3–7.3, and about 1.5 m under the 1671.80 landing.
- **Sealed void.** u 8.125–9.3 × v 1.1–2.5 under the landing is sealed.
- **Correction:**
  - Shelves 0.40 m deep on the west wall only, at v 1.25–6.1.
  - Keep the door zone clear.
  - Stop the u 8.0 wall at v 2.5 and put a beam under the landing, so the store gains the low bay.

**CIR-N04** (`measured`)
- **The passages.** Both run between the lift's RC wall (face u 11.5) and the wall on u 12.6.
- **The doors.** A 1.0 m leaf needs a structural opening of about 1.10–1.15 m. On the grandparents' wheelchair route, the built door would give about 0.8 m clear.
- **Correction.** 0.9 m leaves at u 11.55–12.45, ≥0.85 m clear, hinged east, on both floors.

**CIR-N05** (`measured`)
- **The front.** `core_walls()` makes the lift an RC U, with no wall at v 7.3.
- **Correction.**
  - A 0.20 m RC front with a 1.1 × 2.15 m opening. The clear depth stays at 2.60 m.
  - The shaft becomes a closed fire and seismic tube.

**CIR-N06** (`measured`)
- **The aisle.** The core face is at u 6.675, so the aisle is 1.135 m clear, not 1.2 m.
- **Correction.**
  - Park the cars at u 0.47–5.45.
  - Move the EV point to the shutter pier (VEH-04).
  - The aisle becomes 1.22 m clear.

**CIR-N07** (`inferred` from the label)
- **The route.** The glass lies on the lift → terrace-door line, walked with wet shoes and baskets.
- **Correction.** Slip-resistant glass, or move it to u 11.6–12.4 × v 9.0–9.4.

**CIR-N08**
- **No core section.** Section C–C draws the core as boxes. F–F lacks the pit and the upstand (`inferred` from `sections.png`).
- **Correction:**
  - Add a section at u 8.7 through all six flights, the spine and the guards.
  - Quote garage door → lift as 3.9 m and tailgate → lift as about 6 m.

## What C11 gets right

- **One stair rhythm.** 309 mm goings on all six flights, 1.40 m landings, and labels that match the model.
- **A real lift.** A stretcher-size shaft with its door on the same south face on every floor and a clear 1.5 m landing on each.
- **Groceries.** About 6 m, all indoors, along a clear aisle, through a fire door that parks out of the way.
- **The lower hall.** It is a true landing street, 4.28 × 3.53 m, with no furniture.
- **The stair screen.** It keeps garage fumes and cold out of the stair,, and the stair stays visible.

## Out-of-scope notes

- Structure: the core's east wall on the lower floor (u 9.4, v 1.1–4.5) is a 0.12 m partition (`measured`), so the RC core does not reach its foundation.
- Water: the pit drain runs about 10 m east under the guest room.
