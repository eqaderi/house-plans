# 07 · Rooms and owner rules (residential architect) · C10 review

Prefix ROM. Geometry from `design.py`; ground from `engine.zg` (TIN, inferred). Concept stage only.

## Summary

1. Plan is sound: central core, every main room off a hall, 4.3 × 4.8 m children's rooms, step-free grandparents' suite.
2. Two owner numbers fail. Dining is 11.1 m², under rule 1.5's 13.5 m². The kitchen seats 3, yet 7 people eat daily there (rule 1.4).
3. The hob is on an inside wall, so its hood can only vent beside the front door or onto the terrace. The main-floor WC is reached across the wet wudu floor.
4. Lower floor: the lounge sits between two bedrooms (rule 6.4). The children's only windows face a path 0–2 m away. The laundry proper is 6.4 m² and windowless.
5. The 10.6 × 2.2 m main hall (20 % circulation) can shrink to 1.5 m, giving the dining (and kitchen) the space they need.

## Findings

| ID | Sev | Where | Finding |
|---|---|---|---|
| ROM-01 | BLOCKER | main `dining` | 11.1 m², 6 seats drawn; rule 1.5 asks 13.5–15.5 m² for 6–8 |
| ROM-02 | MAJOR | main `kitchen` | 3 stools for 7 daily eaters; rules 1.4 / 1.5 / 6.7 conflict |
| ROM-03 | MAJOR | `kitchen` hob (4.95,11.3) | Hood cannot reach outside cleanly; rule 1.3 doubtful |
| ROM-04 | MAJOR | `wudu` → `wc-m` | Guest WC reached across the wet wudu floor |
| ROM-05 | MAJOR | `boys`, `girls` v 16.4 | Single window on a path; beds against the glazing |
| ROM-06 | MAJOR | `lounge`, `hall-l` | Lounge between two bedrooms; games table blocks the lift landing |
| ROM-07 | MAJOR | `laundry` | 6.4 m² of laundry, buried, no drying yard |
| ROM-08 | MAJOR | `living` west side | Sofa looks 10.6 m down the hall (rule 3.1) |
| ROM-09 | MAJOR | main `hall` | Double-loaded 10.6 × 2.2 m hall, 35 m² circulation (rule 2.2) |
| ROM-10 | MAJOR | house-wide | No cleaning cupboard, short shoe storage, no garden store or mudroom |
| ROM-11 | MINOR | `dress`, `ens` | 0.75 m dressing aisle; ensuite only through the dressing |
| ROM-12 | MINOR | `master` | No cot place, though infants are expected |
| ROM-13 | MINOR | living prayer mats | Mats face ≈157°; qibla ≈205° (inferred) |
| ROM-14 | MINOR | `guest` | Bedhead under a north window 2.8 m from the neighbour |

## Finding details

**ROM-01 (measured).** Dining is R(9.2,9.5,12.6,13.0): 3.4 × 3.5 m gross, 11.1 m² net, with a 1.9 × 0.95 table and 6 chairs. Eight seats need a 2.2 × 1.0 table plus 0.9 m pull-back, about 3.4 × 4.2 m. stmt-024 allows the room to open into the living room. It does not waive 13.5 m². *Fix:* move the north wall to v 8.8, giving R(9.2,8.8,12.6,13.0) = 14.3 m² gross. Run the table along v with 8 chairs. Leave 1.5 m clear at the lift (ROM-09).

**ROM-02 (measured / ai_judgment).** The household is parents, 4 children aged 0–18 and the grandparents. The island is 2.0 × 0.85 m with 3 stools. Stool (6.8,10.2) stands 0.5 m inside the hall opening, and the serving route east of the island is 0.8 m. A table for 7 needs about 2.6 × 2.4 m plus a 1.0 m work aisle, which does not fit in 15–17 m². Rule 1.5 says 15–17 m², but rule 6.7 says 18–22. *Owner decides:*
- (a) Kitchen R(4.6,8.8,9.2,13.0) = 19.3 m², with a 1.8 × 0.9 table for 7 in place of the island.
- (b) Keep 15 m² and eat daily at the dining table.

**ROM-03 (measured).** The hob sits on wall u 4.6, shared with `entry`, and road-level rooms lie directly above it. The duct must run either 2.6 m over the entry to discharge beside the front door (2.0,12.15), or onto the dining terrace. Dining is open 3.0 m to the living room, so the hood decides rule 1.3. *Fix:*
- Put the hob on the south exterior wall at u 5.0–5.9, with a ≤0.5 m duct through the wall.
- Run an external stack to discharge above the road roof, ≥1 m from any opening window (assumption).
- Move the window to u 6.2–7.2 and the sink to the west run or the island.
- Add a make-up air inlet.
- Optional: a glazed pocket slider in the kitchen–dining portal.

**ROM-04 (measured).** The route is hall → lobby → wudu (open) → WC door (4.65,4.9). In a shoes-off home, guests walk through it in socks. *Fix:* swap the two rooms. The WC goes to R(5.3,2.8,6.8,4.9), off the dry lobby. The shower goes to R(3.8,2.8,5.3,4.9), off the wudu. Draw the wudu tap, foot basin and drain.

**ROM-05 (measured).** The windows run u 8.9–10.9 and 11.6–14.9. Ground is +0.51 m above the floor at (9.0,16.4) and −1.48 m at (14.9,16.4). `path-s` runs 0–1 m from the glass. The shared footpath on the boundary is level with the floor to 1.1 m below it. Passers-by look straight into the boys' room and down into the girls'. All four beds lie under the windows, on the cold wall where the heater would go. *Fix:*
- Windows: sill at 1.2 m with a frosted lower pane, and the path kept ≥1.5 m off the glass.
- Boys: beds along the side walls, R(6.9,13.0,7.9,15.05) and R(10.0,13.0,11.0,15.05), and a 2.5 m shared desk under the window at v 15.7–16.3.
- Girls: the mirror, beds at u 11.2–12.2 and 14.3–15.3.
- Door swings stay clear in both rooms (they reach v 12.5).

**ROM-06 (measured).** The lounge shares 5.4 m of wall with the grandparents and 2.8 m with the girls.
- The grandparents' wardrobes buffer u 12.7–15.8, but the TV at u 15.6–17.6 is unbuffered, 2.35 m from the grandparents' bed.
- The route from the hall to the garden passes between the TV and the sofa.
- The sofa seats only 4 for a household of 9.
- The games table sits in the 4.4 × 4.3 m hall, which has 8 openings. Its chairs leave 0.9 m in front of the lift, below the 1.5 m a wheelchair needs to turn.

*Fix:*
- Extend the grandparents' wardrobes to u 17.4 and move the armchair.
- Build both shared walls as acoustic walls (assumption: Rw ≥ 50).
- Fit an L-sofa for 6.
- Move the games table to the loggia, or replace it with a wall desk at u 8.3–9.9, v 11.0–11.6.

**ROM-07 (measured).** The 13.9 m² room is 6.4 m² of laundry plus a 1.8 × 4.8 m store strip. Rule 6.7 wants 12–14 m² of laundry, linen and drying *plus* a separate store. The walls are 1.25–2.64 m underground, so there is no window. Wet washing must travel about 12 m through the lounge to reach outdoors. *Fix:*
- Laundry: 6.4 m² plus R(5.0,11.6,6.8,14.1), 10.9 m² in total, with a ceiling airer, heat-pump dryer and extract.
- Store: R(5.0,14.1,6.8,16.4), 4.1 m².
- Drying yard: 8–10 m of screened line on the road roof terrace at R(14.0,6.2,17.8,8.0), step-free by lift.

**ROM-08 (measured).** From the short arm of the sofa at (17.1,7.6), you look west past the TV, through the 1.6 m opening and down the whole hall. The long arm's 3 seats face south, 90° away from the TV. Of the living room's 6.8 m west side, 4.6 m is open. *Fix:*
- With ROM-09, the opening narrows to v 7.6–8.8.
- Add a full-height 1.4 m bookcase screen at u 13.3, v 8.2–9.6.
- Put the long arm of the sofa along the east wall, facing the TV.

**ROM-09 (measured).** Circulation on the main floor is the hall (23.3 m²), the entry (9.1) and the master lobby (2.8): 35.2 m² of about 177 m². Pantry, wudu, stair, lift and lobby open on one side; entry, kitchen and dining on the other. *Fix:* narrow the hall to v 7.3–8.8, which is 1.5 m and still a 1.5 × 1.5 m lift landing. Give the 7.4 m² gained to ROM-01 and ROM-02a.

**ROM-10 (ai_judgment).** The main entry has a 1.5 m bench for 9 people plus guests, in a shoes-off home. The main floor has no broom or linen cupboard. The garden doors have no shoe drop, and there is nowhere for the mower or winter garden furniture. *Fix:*
- Shoe and coat cabinet, 0.4 × 2.6 m, at u 4.2–4.6, v 10.0–12.6 (needs ROM-03 first).
- Cleaning cupboard, 0.6 × 2.0 m, at u 2.0–2.6, v 7.4–9.4; pantry door moves to u 2.8–3.7.
- Covered shoe bench and outdoor tap on the loggia at u 15.45–15.85, v 12.0–13.8.
- Garden store, 2.2 m high, under the garden terrace (u 18.0–20.4, v 3.0–11.4, about 20 m²), opening onto the lawn at 1667.60. It replaces part of the 38.9 m³ of fill.

**ROM-11 (measured).** The dressing aisle is 0.75 m (12.05 to 12.8); use 0.55 m wardrobes and a 0.15 m bench to reach 0.9 m. The ensuite opens only from the dressing room. That meets rule 2.5's test but not its wording, so ask the owner.

**ROM-12 (ai_judgment).** The girls are "not born yet", so infants would sleep a floor below the parents. Mark a cot zone in the master bedroom at u 15.5–16.8, v 4.7–5.4.

**ROM-13 (inferred; CRS unconfirmed).** The +v axis bears about 157°; the qibla from 34.97 N, 46.36 E is about 205°. Rotate the mats 48° towards −u, at about 1.5 × 1.5 m each. Rule 6.7's "short doorway from wudu" to the prayer bay is now 6.6 m along the hall. Ask the owner.

**ROM-14 (measured).** The window (16.0–17.6, 2.8) sits over the bedhead. Use a high strip window, or keep the east windows only.

### Owner rules audit

| Rule | Verdict | Evidence |
|---|---|---|
| 1.1, 1.2 | pass | 1.6 m slider to south terrace; kitchen u 4.6–9.2 on south façade |
| 1.3 | doubtful | 2 portals; hood route (ROM-03) |
| 1.4 | fail | 3 seats for 7 (ROM-02) |
| 1.5 | fail | dining 11.1 < 13.5; kitchen 15.1 and pantry 4.3 pass |
| 2.1 | pass | 8 main rooms off halls |
| 2.2 | doubtful | ROM-09 |
| 2.3, 2.4 | pass | no voids; doors only where needed |
| 2.5 | pass / doubtful | bedroom off the lobby; ensuite via the dressing |
| 2.6 | road pass / main doubtful | main: door → entry → N → E, two turns |
| 3.1 | doubtful | NE corner closed; hall vista (ROM-08) |
| 3.2, 3.3 | pass | 1.6 m opening; 33.9 m², 5.0 m clear |
| 4.1, 4.2 | pass | day rooms S/E; west edges 0/2/5, east 12.2/17.8/18.0 |
| 4.3 | doubtful | 69 m² S+E; no north terrace, impossible with the north wall on the setback (v 1.1) |
| 4.4–4.7 | pass | 3.97 m cut; sections; 151 m² garden; 459 m² gross |
| 4.8 | pass / doubtful | windows clear the ground (+0.51 max) but face a path |
| 5.1–5.4 | pass | 4 m garage→lift; one central stair; lift on all floors (lawn by steps only) |
| 5.5 | pass / doubtful | 57.1 m²; 0.8 m standing at the bench with the LC300 parked |
| 6.1, 6.2, 6.5, 6.6 | pass | ensuite; 2 per room; master NE; tea bar |
| 6.3 | doubtful | store hidden inside the laundry |
| 6.4 | main doubtful / lower fail | master shares 5.2 m with living; ROM-06 |
| 6.7 | partial | 0109-r5 rooms kept; laundry size, prayer bay, kitchen 18–22 vs 1.5 |
| 7.1, 7.2, 7.5, 7.6 | pass | 0 label collisions; all levels; 3D; notes |
| 7.3 | partial | dining shows 6, not 8; wudu fittings missing |
| 7.4 | doubtful | dining small, hall oversized, dressing tight |

## What C10 gets right

- Central core, and every main room reached directly from a hall (2.1).
- Kitchen, dining and living face south and east, each with its own terrace door. Wet rooms and pantry fill the buried north-west.
- Grandparents' suite: 1.6 m from the lift, Ø1.5 m turning circle, outward-opening ensuite door, own garden door.
- Lower bathroom split into WC, shower and twin basins.
- Children's rooms with 2 beds, 2 desks and 2 wardrobes each. The wardrobes line the lounge wall and buffer its noise.
- Living room of 33.9 m² with a sheltered north-east corner behind the bookshelf wall.

## Out-of-scope notes

- Moving walls to v 8.8 (ROM-01/02/09) must be checked against the walls above (the garage's south wall is at v 9.5).
- The road-level plant room and WC overhang the kitchen wall by 0.3 m.
- `path-s` at 1669.0 contradicts the natural ground at the boys' wall (1670.0–1670.5).
