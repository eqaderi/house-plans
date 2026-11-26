# 15 · Builder review of C10: constructability, cost, maintenance

Prefix BLD. Concept stage, not engineered. Heights are from the 27-point TIN (inferred). Code values are `assumption`.

## Summary

1. 51 m² of floor sits over undrawn voids: under the garage and under the master's north strip and ensuite. `earthworks()` leaves them out.
2. The floors do not stack. The main east wall is 0.2 m off the lower one, the office walls are 0.2–0.4 m off the walls below, and the main south façade lands mid-span on the bedroom ceilings.
3. The main cost driver is about 130 m of earth-retaining wall (about 210 m² of face), roughly as much concrete as the frame.
4. There are 9–10 slab and formwork levels where 4 plus the lift pit would do. Windows come in 12 widths and sliders in 7.
5. Maintenance gaps: the green roof cannot be reached, there is no mower route or garden store, there is no service riser, and the lift pit has no drain.

## Findings

| ID | Sev | Where | Finding |
|---|---|---|---|
| BLD-01 | BLOCKER | `garage`, `ens`, `master` | Floors over undrawn voids up to 3.78 m deep |
| BLD-02 | BLOCKER | all levels | Walls and columns do not stack |
| BLD-03 | MAJOR | site + building | About 130 m of retaining wall |
| BLD-04 | MAJOR | lower slab, `loggia`, `t-low` | Ground-bearing slabs on up to 2.3 m of fill |
| BLD-05 | MAJOR | lower NW | 4 m cut 1.1 m from the north neighbour |
| BLD-06 | MAJOR | site | No laydown area and no build sequence |
| BLD-07 | MAJOR | all slabs | 9–10 formwork levels, notches |
| BLD-08 | MAJOR | garden | No mower route; terrace sits on fill |
| BLD-09 | MAJOR | `plant` | Tanks over the kitchen; no riser |
| BLD-10 | MAJOR | lift | Pit drain, overhead height, machine replacement |
| BLD-11 | MAJOR | roofs | About 116 m² of decks over rooms; no outfall |
| BLD-12 | MINOR | openings | Too many sizes |
| BLD-13 | MINOR | façades | Painting and cleaning |
| BLD-14 | MINOR | `court-w` | Cost of the owner's court extension |

## Finding details

**BLD-01 · What is under the garage and the master suite (BLOCKER: the owner asked today).** Measured:
- Road level, u 0–6.8 and v 1.1–11.6: 32.4 m² has no main room below it. Natural ground is up to 3.75 m below the slab underside, a 71 m³ void.
- Main level, u 9.4–17.8 and v 1.1–5.0: 18.7 m² has no lower room below it. Ground is 0.9 m down at (10.4, 1.1) and 3.6 m down at (17.8, 1.1), a 37 m³ void.

Correction:
- Make both slabs suspended reinforced concrete. Carry them on perimeter walls along u 0.0 (v 1.1–11.6) and v 1.1 (u 0–6.8 and u 9.4–18.0), founded on natural ground.
- Seal and drain the voids and give each a hatch. **Never fill them.**
- Better: carry the lower north wall out to v 1.1 for u 11.4–18.0. The grandparents' suite gains 10.9 m² for about 11 m³ of cut. Ground at (16, 1.1) is about +0.3 m, so a window still works.

**BLD-02 · Stacking (BLOCKER: "each story is on top of the other one").** Measured offsets and fixes:
- Main east wall 17.8 sits over lower east wall 18.0. Set both to **18.0** and the balcony edge to 19.4.
- Office walls: move east 12.2 → **12.6**, south 12.6 → **13.0** and west 9.0 → **9.2**, onto the walls below.
- Plant/WC strip at v 13.3: stop it at **13.0**. The plant room becomes 3.6 × 1.4 m.
- The main south façade at v 13.0 lands 1.4 m into the 4.8 m bedroom span. Add columns at (6.8, 13.0), (11.1, 13.0), (15.4, 13.0) and (18.0, 13.0), inside the lower partitions. Then move the dining slider to u 9.3–11.0 and the kitchen window to u 5.0–6.6, clear of the columns.
- Every column runs unbroken to its footing, on wall lines that already exist on two floors.
- The stair and lift box (u 6.8–11.4) is already continuous. Make it the concrete shear core.

**BLD-03 · Retaining walls (MAJOR, measured; concrete volume is `ai_judgment`).**

| Group | Length | Retained face | Highest |
|---|---|---|---|
| Lower-floor basement walls | 38 m | 83 m² | 3.62 m, plus about 0.85 m of formation and footing |
| Main-floor buried walls | 14 m | 9 m², or about 45 m² if the garage area is filled | — |
| Site walls | 77 m | 116 m² | 3.8 m (forecourt) |

The site walls include the garden terrace (8.8 m long × 2.38 m) and the lawn (18.4 m × 1.36 m).

That is about 150–180 m³ of concrete. Cheapest cuts, with no owner rule broken:
- Build a store box under the terrace instead of fill (BLD-08).
- Use one road-side wall instead of two stair walls (BLD-14).
- Build lawn walls of 1.4 m or less in dry stone or gabions.
- Never fill under the garage.

**BLD-04 · Slabs on fill (MAJOR, measured).**

| Area | On fill | Deepest fill |
|---|---|---|
| Lower slab, east part | 34.4 m² | 1.39 m |
| Loggia | 12.5 m² | 2.14 m |
| Garden terrace | 22.9 m² | 2.29 m |

Meanwhile the main floor at u 2–5 bears on cut ground, so the floors will settle unevenly and crack. Correction:
- Put a tie-beam grid under the lower floor, top at 1669.65.
- Suspend the lower slab east of u 12.6 and the loggia.
- Step the footings down to natural ground: about 1667.0 on u 18.0. The 0.8–1.0 m frost depth is an `assumption`.

**BLD-05 · North neighbour (MAJOR, measured).** At (6.8, 1.1) the cut is 3.97 m deep, plus about 0.5 m for the footing, and only 1.1 m from the boundary. There is no room to batter it. Correction:
- Dig and cast the north wall at u 6.8–9.4 in alternate bays of no more than 2.5 m, or use soldier piles. Anchors would need the neighbour's consent.
- Record the neighbour's building condition first.
- Soil and neighbouring foundations are `unknown` until a geotechnical investigation.

**BLD-06 · Sequence (MAJOR, `ai_judgment`).** No tower crane. Concrete comes from a 36 m boom pump on the road: the house's east edge is about 27 m away and the lawn wall about 35 m. Each pour needs a road closure.
1. Road-front walls (u 0, v 11.6), then fill the forecourt as a 36 m² laydown and pump stand.
2. Dig in benches from the top down with an 8 t tracked excavator and a tracked dumper. That is about 285 m³ loose, or about 30 trucks. Dig in June–September only.
3. Lift pit, basement walls, tanking and back-drains, all closed before the wet season.
4. Frame lower → main → road → roof. Use each finished slab as laydown.
5. Garden walls and topsoil last.

**BLD-07 · Formwork (MAJOR, measured).**
- **Lower slab:** 12 corners, 4 of them re-entrant, plus the lift pit.
- **Main slab** (with terraces): 10 corners. It needs a 28.5 m drop line for the terraces and is part on grade, part suspended.
- **Road slab:** 10 corners, with steps of 0.3, 0.4 and 0.7 m. It has 4 surfaces (garage with falls, indoor, deck, green) and a 0.9 m² green-roof sliver at u 11.4–12.2, v 6.2–7.3.

Correction:
- Apply BLD-02 and delete the sliver.
- Lay the green-roof build-up on a flush slab behind a parapet, instead of dropping the slab.
- Use one 0.20 m terrace drop, on straight lines only.
- Spans are then no more than 4.6 m, which suits beam-and-block joists at 0.5 m centres or a 0.20 m two-way slab (`assumption`, common practice in Iran).
- The garage spans 6.8 m and needs beams about 0.6 m deep.

**BLD-08 · Garden access (MAJOR, measured).**
- From outside: the road stair (22 risers), then the `gs-court` steps (a 2.3 m drop in a 2.0 m run, 49°), then the path.
- From inside: through the lift and the living rooms.

A mower cannot use either. Correction:
- Build a **garden store under the garden terrace**: u 18.2–20.4, v 3.0–11.4 (about 18 m²), floor at lawn level (1667.6), about 2.1 m headroom, 1.2 m door to the lawn, plus an outdoor tap and socket.
- It replaces 39 m³ of fill and a 2.38 m cantilever wall with a propped box.
- It gives a firm base to prop the balcony while it is cast.

**BLD-09 · Plant room (MAJOR; rule 6.7 wants it replaceable).** The 1.2 m door into the hall, then the 1.2 m front door, works.

Problems:
- Two 1000 L tanks weigh about 2.2 t full and sit mid-span over the kitchen.
- There is no riser to the floors below.
- The flue would come out above the kitchen window.

Correction:
- Put the tank plinth on beams at v 11.6 and v 13.0.
- Waterproof the floor with a 150 mm upstand and a floor drain.
- Use 2 × 1000 L tanks (about 1.05 m in diameter). A single 2000 L tank will not pass the door.
- Run a **0.6 × 0.6 m riser at u 5.0–5.6, v 12.4–13.0**: plant room → behind the kitchen corner unit → laundry, with an access panel on each floor.
- Take the flue to the roof.

**BLD-10 · Lift (MAJOR, values are `assumption`).**
- Use a machine-room-less lift. The 2.0 × 2.3 m shaft fits a 1.1 × 1.4 m car.
- Headroom above the top stop (1677.5) is only about 3.6 m, which is marginal. Raise the shaft head 0.5 m.
- Cast a 1.5 t lifting hook into the shaft head so the machine can be replaced.
- Pit bottom about 1668.8. Waterproof the pit and drain it by gravity (1:50 or steeper) to the lawn-edge drain at about 1667.5, 11 m away, with a back-up sump.

**BLD-11 · Roofs (MAJOR).** Waterproofed decks over rooms:
- roof terrace: 40 m² over the living room;
- green roof: 41 m² over the master suite, with no access;
- south terrace: about 35 m² over the bedrooms.

Plus 126 m² of plain roof. Correction:
- Make them inverted roofs with paving on pedestals, so the membrane can be inspected.
- Give each roof at least 2 outlets plus an overflow.
- Put the downpipes outside, with cleanouts.
- Pipe all water to a sealed outfall. **Never discharge it onto the slope above the downhill neighbour.**
- Green roof: add a gate from the roof terrace and a gravel strip, or replace it with gravel ballast.
- Balcony doors: a 0.15 m drop to a drained grating, so the floor stays step-free inside under rule 5.4.

**BLD-12 · Sizes (MINOR, measured).**
- Windows come in 12 widths, 0.6–3.3 m. Use **0.6, 1.2, 1.8 and 2.4**.
- Sliders come in 7 widths. Use **1.8, 2.4 and 3.0**.
- WC and shower doors at 0.75 m: make them at least 0.8 m.
- The garage door needs at least 2.4 m clear height.

**BLD-13 · Façades (MINOR).** The east face is about 10.4 m tall, from the lawn at 1667.6 to the parapet at about 1678.0.
- Glazing can be cleaned from the balcony and the garden terrace, which is good.
- The master's north window (u 14.4–17.0) is 4–5 m above a 1.1 m strip by the neighbour. Make it tilt-and-turn, opening inward.
- Use no-paint finishes: stone on the lower storey and walls, through-coloured render or brick above.
- Cast scaffold ties into the east face.

**BLD-14 · Owner's court extension (MINOR, measured).** Digging west to the road gives 39 m² more court for 86.5 m³ more cut.
- It adds a road-side wall 6.6 m long × 3.9 m that must carry traffic load. Build it before digging, in alternate bays.
- It removes the stair walls at u −1.2 and −2.4.
- Net: about 25 m² more wall face. Worth it.

## What C10 gets right

- The stair and lift box (u 6.8–11.4) runs straight through all three floors, a ready-made shear core.
- The main floor is set back, so the south terrace is the lower roof and needs no cantilever.
- All main and lower glazing can be cleaned from a terrace or balcony.
- The plant room can be replaced through two 1.2 m doors to the road.
- Earthwork is moderate: 228 m³ cut and 124 m³ fill, deepest cut 3.97 m.

## Out-of-scope notes

- Structure: stepped footings and buried walls on the west risk torsion and short-column effects under Standard 2800. Engineer's call.
- Stairs: the `gs-court` steps and the 22-riser road stair with no landing need rework.
