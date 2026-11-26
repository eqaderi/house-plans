# 25 · Household operations and storage: review of C11

## Summary

1. The compact laundry (4.8 m² clear) and its separate stores now meet stmt-028 and rule 6.3. The drying yard, covered guest door, bins, intercom and mats on the qibla are all drawn.
2. The 9.6 m² bulk store, the biggest store in the house and the only main-floor place for cleaning kit, cannot be reached. Its only door sits behind two Ø1.24 m tanks with 0.32 m to spare.
3. The tyre rack is drawn in the opening of shutter 1. The garden store is two 1 m slots with a door of 0.70 m at most. The laundry's only way in is a 0.69 m passage.
4. The LPG cage and the cooking station sit in the sunken court on the guests' line from the road stair, 2.0 m from the front door.
5. Garden traffic comes up the lawn stair to the grandparents' slider and is 10.9 m from the boot bench.

## Scorecard

SCORECARD: fixed=2 partly=10 not_fixed=1 worse=0 new_blocker=1 new_major=5 new_minor=4

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| OPS-01 laundry merged | **fixed** | `measured`: `laundry` is 4.8 m² clear (washer, heat-pump dryer, sink, airer). `store-s` (6.0 m²) and `store-u` (5.5 m²) are separate rooms (`clear_geom`). | Access and fit-out are covered in N05. |
| OPS-02 drying | **partly fixed** | `measured`: yard R(14.0,6.35,17.8,8.0) on `deck-r` gives about 19 m of line. The route laundry → lift → lobby glass door (12.6,8.4) is about 9 m plus the lift, all step-free. The fold-down rack in the loggia (ROOM-13) is not drawn. The winter airer is only 0.8 × 0.8 m. | Add a 1.2 m fold-down rack on the loggia wall at u 15.45, v 14.2–15.4. See N09 for the guard clearance. |
| OPS-03 shoes-off | **partly fixed** | `measured`: the guest door at u 2.0, v 10.1–11.1 is now under the porch. Road hall: 6 lockers plus a bench R(4.4,9.55,5.6,9.95), about 3 m from the fire door. Entry: cabinet 0.4 × 2.6 m. The tiled shoe zone is not shown. | See N10 (coat depth). Draw the tiled zone u 0.15–5.6 in `hall-r`. |
| OPS-04 garden door | **partly fixed** | `measured`: loggia bench R(15.55,12.3,15.95,14.0) is drawn. There is no shoe cabinet, no tap and no foot-wash gully (none in `WATER`, none in the furniture). The design.py comment says "tap", but nothing is drawn. | Tap and gully at (18.2,12.5) on the loggia/`t-low` threshold. Shoe cabinet 0.35 × 1.2 at R(15.55,14.1,15.9,15.3). Route: N04. |
| OPS-05 bins | **partly fixed** | `measured`: enclosure R(0,0.05,2.4,1.05). The garage's outer face is at v 0.85, so only 0.80 m is clear, and the drawn 1.0 m depth runs 0.2 m into the wall. The ground there is 1676.54–1677.15 (`zg`), 0.3–0.9 m below the forecourt (1677.47). No platform or ramp is drawn. Compost is not drawn. The 3-bin pull-out is not drawn (the sink run is 1.6 m only). | Slab the strip u −0.5–2.4, v 0.05–0.80 at 1677.45 on the PW-N cap, flush with the forecourt. Enclosure 0.75 × 2.4 m for 3 × 140 L bins (0.55 m deep), with lids hinged to the wall side. Draw the 0.6 m pull-out beside the sink and a compost bay at the lawn's NE corner. |
| OPS-06 one guest WC | **partly fixed** | `measured`: the main floor still has one WC. The road WC is 24 risers or one lift ride away. CONSOLIDATED OPS-04 accepts this at the Q2 default of 15 guests (1 WC per 15–20, `assumption`). | Only if the owner answers 30–35 to Q2: make `sh-m` (1.03 × 1.98 clear) a WC + shower. |
| OPS-07 bulk cooking, LPG | **partly fixed** | `measured`: only a text label and a 0.6 × 0.6 cage rectangle. No burners, tap, gully or socket are drawn, and the place is unsafe (N03). | See N03. |
| OPS-08 storage volume | **partly fixed** | `measured`/`inferred`, with 2.2 m usable height: `store-u` about 4.8 m³ (0.92 m wide, soffit 1.55 → 3.3 m); `store-s` about 7.0 m³; `store-r` 1.6 m³; bulk 6–8 m³. With the bulk store that is about 20 m³ against about 15 m³ needed for household goods and bedding, which would be enough. But the bulk store cannot be reached (N01), which leaves 13.4 m³, all of it on the lower and road floors. The garden store is not usable as designed (N02). | Fix N01, N02 and N06. Then the volume is met. |
| OPS-09 cleaning cupboards | **not fixed** | `measured`: the only "CLEANING" shelves are in the unreachable bulk store. No road-level cupboard. | Main floor: cupboard R(0.25,8.0,0.85,9.3) inside the tank-room door, clear of its 1.2 m leaf (u ≥ 1.0), with a charging socket. Road level: R(5.6,9.55,6.7,9.95) east of the hall bench. |
| OPS-10 pantry | **partly fixed** | `measured`: pantry door (3.25,7.3) to the kitchen opening (6.15,9.5) is 3.64 m. KB-02 asked for ≤3 m, and CORRECTIONS claims 3.4 m. The route still crosses the entry → stair line. No separate tall larder: the west run's tall unit is the fridge. | A 0.6 × 0.6 tall larder in place of the first 0.6 m of drawers on the west run (v 10.5–11.1). Keep the pantry for bulk goods. |
| OPS-11 prayer | **fixed** | `measured`: mats are 0.0° off the qibla (§7.18). Two seated wudu places. Outdoor tap labelled. | None. |
| OPS-12 bedding | **partly fixed** | `measured`: `store-s` has 0.58–0.65 m shelves, but the room is buried on its west and south sides and has no ventilation (`inferred`). | Supply/extract of 5 l/s to `store-s`. Bedding on slatted 0.7 m shelves ≥0.1 m off the wall. See N06. |
| OPS-13 deliveries, tyres, snow | **partly fixed** | `measured`: intercom and address at the road door, "PARCELS" text at the stair gate. The tyre rack is in the vehicle opening (N07). There is no place for snow tools. | Parcel niche 0.6 × 0.4 × 0.6 m in the road-door reveal at u −0.25, v 9.8. Snow-tool hooks on the garage north wall at u 5.6–6.6. |

## Part B: new problems

| ID | Sev. | Where | Finding | Correction |
|---|---|---|---|---|
| OPS-N01 | BLOCKER | main `tanks` → `bulk` | The bulk store's only door is behind two Ø1.24 m tanks. The gap is 0.32 m. | Pantry door, or slim rectangular tanks |
| OPS-N02 | MAJOR | `t-low` void | Garden store split into two 1 m slots. Door 0.70 m at most. Not drawn on any plan or section. | One 2.2 × 6.0 m store, 1.2 m door |
| OPS-N03 | MAJOR | `court-w` (−0.2…0.4, 12.3…12.9) | LPG cage and station in the sunken court, on the arrival line, 2.0 m from the front door | Move off the line. Electric burners, or cylinders at forecourt level |
| OPS-N04 | MAJOR | lawn stair, `t-low` | Garden traffic lands at the grandparents' slider, 10.9 m from the boot bench | Reverse the lawn stair |
| OPS-N05 | MAJOR | lower `laundry` | Only reached through a 0.69 × 1.4 m passage. No folding counter | Widen the passage to 0.9 m. Stack the machines and add a 1.2 m counter |
| OPS-N06 | MINOR | `store-s`, `store-u` | 0.60 m aisle. Shelf clashes with riser SH-K. `store-u` shelf block fills its width at the door | Re-plan the shelves |
| OPS-N07 | MAJOR | road `garage` | Tyre rack R(0.2,1.2,0.5,4.4) in shutter 1's opening (v 1.575–4.925), 0.05 m from car 1 | High rack on the north wall |
| OPS-N08 | MINOR | `CORRECTIONS.md` | The tyre-rack, garden-store "Section H–H", pantry "3.4 m" and OPS-09 claims do not match the geometry | Correct the ledger |
| OPS-N09 | MINOR | `deck-r` yard | Drying yard 0.15 m from the green-roof guard: the line posts are climbable | Shift to v 6.8–8.4 |
| OPS-N10 | MINOR | main `entry` | A 0.4 m deep cabinet cannot hang coats | Deepen 1.2 m of it to 0.6 m |

## Part B details

**OPS-N01 · BLOCKER · bulk store cannot be reached.**
- Evidence (`measured`):
  - The tank room is 1.715 m clear (u 0.225–1.94).
  - Tanks at (1.0,2.6) and (1.0,4.1), r 0.62, fill u 0.38–1.62. That leaves 0.32 m on the east side and 0.155 m on the west.
  - The only door to `bulk` is centred at u 2.0, v 2.6 (v 2.1–3.1), directly behind tank 1. To reach it you would have to squeeze past tank 2.
- `doors.clear` passes only because it tests the swing, not the approach.
- Result: 9.6 m² of store (gathering kit, cleaning, bulk goods) is unusable. A room reached through the plant room also breaks rule 6.3 ("no stores in odd places").
- Correction, either:
  - (a) A 0.8 m door from the pantry through MW-4.6 at u 2.15–2.95. Remove shelf R(2.55,4.75,3.25,5.15). The pantry aisle stays 0.88 m. Or:
  - (b) Two rectangular tanks of 0.7 × 2.2 × 1.0 m (1.54 m³ each) against the west wall, R(0.25,1.4,0.95,3.6) and R(0.25,3.8,0.95,6.0). Booster to R(0.25,6.2,0.95,7.0). That leaves a 0.99 m passage on u 0.95–1.94.

**OPS-N02 · MAJOR · garden store.**
- Evidence (`measured`):
  - FW-19.3 (0.20 m) runs the whole length v 1.1–12.8, so the store (v 6.6–12.65) becomes two slots: u 18.25–19.2 and u 19.4–20.45.
  - The door on FW-12.8T is limited by balcony column C-B/12.8 at u 19.45–19.75, so the east slot gets 0.70 m at most and the west slot 0.95 m.
  - Neither slot fits a 1.2 m door for a barrow or mower.
  - Headroom is 2.13 m (`inferred`).
  - No plan shows the store. Section H–H cuts u 21.2, east of it.
- Correction:
  - Stop FW-19.3 at v 6.5 (the cistern end). Span the 2.35 m between the lower east wall and FW-20.6, or put one beam there (structure to confirm).
  - One store R(18.25,6.6,20.45,12.65), 13.3 m², with a 1.2 m door at u 18.4–19.6 on v 12.8.
  - Level apron 1.5 m deep at 1667.60 (natural ground there is 1667.5–1667.7).
  - Tap and socket inside.

**OPS-N03 · MAJOR · LPG and cooking in the court.**
- Evidence:
  - The cage at (−0.2…0.4, 12.3…12.9) is 2.0 m from the front-door jamb (2.0,11.1) and 2.3 m from the entry window (`measured`).
  - The line from the road-stair foot (−2.98,16.4) to the front door runs through (0.1,12.8), right through the cage and the station (`measured`).
  - On gathering days, floor burners with 50–100 L pots would stand on the path the guests and children walk.
  - The court is a pit 0.6–3.9 m below the ground around it (`zg` (−3,13) = 1675.41 against 1673.60), walled on the north, west and east. Heavier-than-air gas would leave only down the court stair, ending at 1670.00 outside the boys' window (sill 1670.90) (`inferred`).
- Correction:
  - Station R(−4.3,12.4,−2.5,14.0) against W3, 1.6 m clear of the arrival line, with a tap/wudu point, gully and 32 A socket.
  - Default: two electric/induction floor burners of about 3.5 kW each, and no LPG at all.
  - If the owner wants gas: cylinder cage at forecourt level (open to the street, nothing below), with a fixed pipe to a bayonet point. MEP and gas safety to confirm (`assumption`).

**OPS-N04 · MAJOR · muddy route from the lawn.**
- `measured`:
  - The lawn stair climbs north. `ls-top` R(20.6,3.4,21.8,4.6) lands 2.4 m in front of the grandparents' 2.0 m slider (v 3.3–5.3).
  - From there to the loggia bench is about 10.9 m, passing the lounge slider (v 9.0–10.8) first. Children will use the lounge slider.
- This brings mud and noise to the grandparents' room and the lounge.
- Correction: reverse the lawn stair.
  - Top landing R(20.6,9.1,21.8,10.3) at 1669.98, with the flights going down north to the lawn at v 3.4. The lawn lies on both sides, so this fits.
  - The arrival point is then 3 m from the loggia: tap, gully and bench (OPS-04).

**OPS-N05 · MAJOR · laundry access and fit-out.**
- `measured`:
  - The tail at u 6.8–8.2 is 0.69 m clear (v 10.16–10.85), behind a 0.8 m door. That is the only way in, used every day with a 0.6 m basket.
  - The washer, the dryer and a 0.7 m sink counter fill the west wall. There is no folding surface. The washer drawing overlaps the 0.45 m wall by 0.075 m.
- Correction:
  - Move the lav/WC south wall to v 9.9 over u 6.8–8.2. The basins move 0.2 m north, and `lav` stays 1.4 × 2.6 m. The passage becomes 0.89 m.
  - Stack the washer and dryer at R(4.83,10.2,5.48,10.85).
  - Sink R(4.83,10.9,5.48,11.5).
  - 1.2 m folding counter R(5.6,11.5,6.7,12.1) under the airer.

**OPS-N06 · MINOR · store fit-out.**
- `store-s`:
  - The shelves at u 4.75–5.4 and 6.0–6.65 leave a 0.60 m aisle.
  - The west shelf overlaps riser SH-K (4.85–5.45 × 12.25–12.85).
  - The room is reached only through the laundry.
  - Correction: east shelf 0.40 m (u 6.30–6.70); west shelf 0.65 m from v 12.95; aisle 0.85 m.
- `store-u`:
  - The drawn shelf block R(6.9,5.2,7.9,7.2) fills the full 0.92 m width in front of the door (v 6.25–7.05), so the back 4 m cannot be reached.
  - Correction: 0.40 m shelves on the u 6.95 side only, starting at v ≤ 6.15, behind the door leaf.

**OPS-N07 · MAJOR · tyre rack.**
- `measured`: the "TYRES" rect R(0.2,1.2,0.5,4.4) stands inside shutter 1's opening, 0.05 m from car 1's bumper. CORRECTIONS says "north wall".
- Correction: high rack R(0.6,1.25,3.8,1.55), bottom at +2.05 m and top at +2.85 m, for 8 tyres on edge. It stays clear of RB-5.3 and of the door zone's headroom.

**OPS-N09 · MINOR.** Move the yard to R(14.0,6.8,17.8,8.4). That keeps it 0.6 m off the guard, as §7.7 requires for furniture, and still 1.4 m clear of the lobby door's swing.

**OPS-N10 · MINOR.** For 15 winter coats, deepen the cabinet over v 11.4–12.6 to 0.6 m (u 3.74–4.34). The entry stays 1.59 m clear.

## What C11 gets right

- The laundry is the right size (4.8 m²). It sits 2.3 m from the children's doors, and the master's door is 1.5 m from the lift on the main floor.
- Groceries go car → fire door → lift in 3.6 m indoors. Boot to pantry is about 15 m, step-free.
- The guest door is covered and faces the court. Shoe places are planned at both front doors.
- The drying yard has sun, is screened, is step-free by lift and keeps washing out of the south view.
- Gatherings: dining for 8, the sofreh line for 30–35, and mats on the qibla with a 2.2 m zone all work.
- The road door is level with the forecourt, and the intercom and address panel are drawn.

## Out-of-scope notes

- The road WC door is 0.7 m against KB-04's ≥0.8 m (KB).
- FW-19.3 removal and the bin slab on the PW-N cap need structural sizing (STR).
- LPG ventilation and the gas route need MEP and gas-safety review (MEP).
- No supply air to the stores (MEP-04).
