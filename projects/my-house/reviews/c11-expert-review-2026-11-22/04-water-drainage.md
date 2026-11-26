# 04 · Water: stormwater, drainage, waterproofing (C11 review)

Concept review; nothing is engineered or code-checked. Levels from `design.py`, `checks.json` and `zg` (27-point TIN, inferred). "Road edge" = `zg` on the west boundary; road unsurveyed (F6).

## Summary

1. C11 draws water: the `WATER` table gives 13 surfaces a fall and outlets. The 0.25 m set-downs are modelled and checked, and the tanks stand on the ground.
2. The road is now the threat. The W2 wall top (1677.40–1677.45) and the stair head (1677.47) sit 40–150 mm below the road edge (1677.51–1677.57), so road water runs down the entrance stair.
3. At v 8–11.6 the forecourt channel lies below the road and takes its water, and no outfall is shown.
4. Lower floor: the garden walk is at 1670.00, the children's floor level. `t-low` and the loggia have no set-down. The north piles fill the space the wall drainage needs.
5. Tanking, footing drains, frost and spreader exist only in the ledger.

## Scorecard

SCORECARD: fixed=2 partly=10 not_fixed=2 worse=0 new_blocker=1 new_major=4 new_minor=3

## Part A · C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| WAT-01 garage vs road | partly fixed | *measured:* forecourt 1677.47 at the shutters, falling west. Road edge 1677.39 / 1677.34 / 1677.37 at v 3 / 5 / 7. The garage fall is a note only: the floor is modelled flat at 1677.50. §7.9b is open. | See N02. Model the garage floor at 1677.54 → 1677.48 (0.9 %), with a trench drain inside each shutter. |
| WAT-02 court sump | partly fixed | *measured:* gullies at (4.3, 15.8) and (−2.8, 16.9); the door is under the covered porch. The court is modelled flat at 1673.60 and meets `t-south` (1673.58) along u 4.6, v 13.0–16.0, with **no kerb**. The snow pit and the DN150 outfall are text only. | 150 mm kerb plus channel on u 4.5, v 13–16, membrane up to 1673.73. Model the falls (1673.57 → 1673.48). Snow-pit drain DN110 at invert ≤1671.9, run east under the court stair. |
| WAT-03 t-south | partly fixed | *measured:* set-down 0.25 m, 2.95 m clear below. Outlet (6.8, 16.2) lies **0.2 m outside** the terrace, over landing `cs-l2`. The overflow (11.25, 16.3) spouts 3.6 m onto the walk. The 0.4 m oversail drips onto `cs-f3` and `walk-s`, and no gutter is declared. | Edge gutter on v 16.35 (u 7.8–15.4) to outlets at (7.9, 16.2) and (15.3, 16.2); downpipes in sealed pipe under the stair; overflow into a walk gully. |
| WAT-04 deck-r, green-r | fixed | *measured:* set-down 0.25; falls east to 2 outlets plus an overflow; doors at u 12.6 face away from the fall. | Minor: the outlets at u 17.5–17.6 sit inside the wall's inner face (17.85). Move them to u 17.8 in a chase. |
| WAT-05 buried walls | partly fixed | *measured:* 0.45 m walls drawn. The new service room retains **3.87 m** on u 0 (C10: 3.62 m max). The lower west wall and the stair's north wall retain 3.6 m. Tanking and drains: ledger only, 0 hits in the drawings or report. | Draw the footing drain (invert 1669.35 → pit at (18.6, 13.0)) and a main-floor drain at 1672.9 on u 0 / v 1.1. Dry inner skin for the bulk store. See N05. |
| WAT-06 lift pit | partly fixed | *measured:* pit 1.2 m deep, floor 1668.80, tanked. The drain is not drawn, and a straight run east at v 4.5–6.5 hits the cistern (FW-6.2T, v 6.5). | Drain at invert 1668.20 along v 7.0 at 10 %: 1667.26 at u 20.6 through a sleeve, 0.48 m under the lawn, daylight at u ≈25.6. |
| WAT-07 north strip | partly fixed | *measured:* the master's earth pocket is gone (wall on v 1.1). The channel is a note. NW ground (1677.58) is 80 mm above the garage floor. | See N05. |
| WAT-08 final discharge | partly fixed | *measured:* cistern bay drawn, floor 1666.8. *Inferred* size ≈15–18 m³; balcony columns at u 19.6 stand in it. No spreader. The bank is only **2.05–3.57 m** wide at 28–32 %. Hard area ≈450 m², plus road water (N02). | A spreader 3 m from the boundary fits only at v < 8. Use a 12 m infiltration trench (0.6 × 0.8 m) on the lawn's east edge, ≥3.5 m from the boundary. Add 5 m³ of attenuation with an orifice. Percolation test first. |
| WAT-09 balconies | fixed | *measured:* fall east to edge outlets at u 19.7, with downpipes on the columns at u 19.6. | — |
| WAT-10 t-low, lawn | partly fixed | *measured:* `t-low` is suspended, but its set-down is 0 (N03). The lawn falls east, yet its outlet (21, 12) is on the west edge. The overflow (26, 10) lies 1.81 m outside the lawn. | Fall the lawn 1:60 west to a slot drain on u 21.0 (1667.60 → 1667.53), with the overflow inside the lawn. |
| WAT-11 south strip | partly fixed | *measured:* walk cross-fall 1:40, but its outlets fall over SW-29 (1.69 m) towards the shared footpath with no route. See N03 and N04. | Solid DN110 east under the strip to the lawn trench. |
| WAT-12 tanks over kitchen | partly fixed | *measured:* the tanks are on the ground and the WC is over the entry. But the boiler and cylinder (R(5.55, 12.0, 7.25, 12.8)) sit over the kitchen's sink and hob. §7.15 passes wrongly, and the bund is a note. | Plant floor bunded: 150 mm upstand, membrane, gully to SH-K; cylinder in a piped drip tray. |
| WAT-13 top roof | not fixed | *measured:* the ≈140 m² roof at 1680.80 has no `WATER` entry. | Fall 1:60 east to outlets at (12.3, 2.0) and (12.3, 12.6) plus an overflow; downpipes in the risers. |
| WAT-14 frost and ice | not fixed | *measured:* "frost", "heat-trace" and "downpipe": 0 hits outside the ledger. | Heat-trace the north outlets and the forecourt channel. Pipes ≥0.8 m deep (frost depth unknown) or insulated, and none in the garage. |

## Part B · New problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| WAT-N01 | BLOCKER | W2, W4, `rs-head`, v 11.6–17.27 | Road water runs over W2 and the stair head onto 24 steps | Solid upstand ≥ road edge + 0.15; hump and slot drain at the head |
| WAT-N02 | MAJOR | `fore` v 7.5–11.6; garage | Channel below the road; no outfall | Crest at the boundary; DN150 outfall to the court |
| WAT-N03 | MAJOR | `walk-s`, `t-low`, `loggia` | Outdoor floors flush with the inside floor | Walk at 1669.85; 0.20 m set-down |
| WAT-N04 | MAJOR | court stair v 16.0–17.27 | Steps up to 0.27 m below the strip beside them | Kerb plus cut-off channel |
| WAT-N05 | MAJOR | PW-N, u 0–13.2 | Piles overlap the house wall; no drained cavity | Move the piles to v 0.40; cavity drain |
| WAT-N06 | MINOR | `checks.py` §7.9 | Passes with surfaces and outlets missing | Extend the check |
| WAT-N07 | MINOR | drawings, report | Water design invisible to the owner | Water plan plus three details |
| WAT-N08 | MINOR | `fore`, `court-w`, `walk-s` | Falls laid on 1.55–1.77 m of fill | Engineered fill or slabs |

## Part B details

**N01 (BLOCKER: ice on the main pedestrian entry).** *Measured, TIN:* the road edge is 1677.51 at v 11.6 and 1677.57 at v 17.12. The W2 top is 1677.40–1677.42, `rs-head` 1677.47, and the west part of W4 1677.25 against 1677.45 of ground. The ledger's "stone + lattice" W2 would let water through. *Correction:*
- W2 solid, top ≥1677.66 at v 11.6 and ≥1677.72 at v 17.12.
- W4 top ≥1677.60 at u −9.0 to −8.0.
- A 30 mm hump at the gate (crest ≥1677.54), then a 150 mm slot drain across `rs-head` into the forecourt channel.
- Confirm with F6.

**N02.** *Measured:* at v 9–11.6 a 1.5–2 % fall puts the boundary channel at 1677.34–1677.40, below the road edge (1677.45–1677.51). Its outlets, the garage trench drain and the interceptor have no pipe or level. *Correction:*
- A rounded crest from v 7.5 to 11.6 at road edge + 0.03, no more than 50 mm proud.
- The channel 0.8 m inside it at 1677.40–1677.44.
- A DN150 outfall inside W1/W3 to the SW court gully. Size the court outfall for ≈96 m².
- Interceptor to foul (outfall unknown).

**N03.** *Measured:*
- `walk-s` is at 1670.00 against the children's south wall (FFL 1670.00, structural slab 1669.85) for 5.66 m.
- `t-low` and `loggia` are at 1669.98, and `SETDOWN` leaves them out. Check 8 tests only the main and road levels.
- `t-low` is the roof of the garden store and the cistern.

*Correction:*
- Walk at 1669.85 at the wall, falling 1:40, with a 150 mm slot channel and tanking to 1670.15.
- Court stair 24 risers × 0.156 m. A 1:20 ramp at u 12.8–15.4 keeps the loggia step-free.
- `t-low` and `loggia` slabs at ≤1669.78 with a membrane, and slot channels at the doors (18.0, 4.3) and (18.0, 9.9).

**N04.** *Measured:* ground at v 17.42 sits 0.18–0.27 m above the stair at u 1.5–2.0, 0.17 m at u 5.86 and 0.08 m at u 9.74. The ARR-02 kerb is not modelled. *Correction:* a kerb on v 17.27 with its top at ground + 0.15 (≈1672.85 at u 2, 1671.55 at u 5.9, 1670.25 at u 9.7), plus a cut-off channel falling east to the walk channel.

**N05.** *Measured:* PW-N is Ø450 piles at 0.7 m centres (0.25 m gaps) on v 0.85, south face at 1.075. The house wall's outer face is at ≈0.80, an overlap of ≈0.27 m, so there is no room for a membrane or drain. The pile top (1677.0) is 0.22 m below the ground at u 0. *Correction:*
- Piles on v 0.40, with a 75 mm facing.
- A 0.15 m drained cavity with a DN110 drain at the toe.
- The north channel cast in the capping beam (1677.35 at u 0; drop pits at u 2, 6.8 and 11.4).

**N06.** §7.9 misses:
- surfaces: the top roof, the south canopy, and all three outdoor stairs;
- outlets outside their surface: `t-south` (6.8, 16.2) and `fore-deck`;
- inflow from higher neighbouring surfaces;
- doors properly: it tests them from the centroid only.

**N07.** Drains, downpipes, heat trace, the spreader, tanking and bunds have 0 hits in `index.html` and the report. Add `drawings/water.png` with inverts, and details of the north cavity, the `t-south` edge and the walk's wall foot.

**N08.** *Measured:* fill is up to 1.64 m under the forecourt, 1.55 m under the court and 1.77 m under the walk. *Inferred:* settling of 16–35 mm would reverse 1.5 % falls. Use compacted granular fill in 150 mm layers or slabs on walls, with channels fixed to the structure.

## What C11 gets right

- Set-downs are modelled per surface and tested.
- The tanks are on the ground, and no WC sits over the kitchen.
- `t-low` is suspended, so about 39 m³ of wet fill becomes a cistern void.
- The lift pit is 1.2 m deep and tanked.
- The balconies are uninsulated, fall to their edge on columns, and keep water off the sliders. The front door is under a porch.
- The master suite's north earth pocket is gone.

## Out-of-scope notes

- MEP: foul outfall unknown (lower WCs 7.5 m below the road).
- Structure: pile/wall overlap; W2 upstand load.
- Geotech: fill depths; infiltration on a 30 % bank.
- Safety: ice on the outdoor stairs.
