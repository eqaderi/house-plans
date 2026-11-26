# 22 · Natural hazards and resilience: review of C11

Concept-stage review of hazards and outages. Nothing here is engineered, code-checked or geotechnically verified. Code figures are *assumptions*.

## Summary

1. The geometry of the hill hazards is much better: the tanks are on the ground, `t-low` is suspended, the north pile wall is drawn, and the lower floor has three ways out at ground level.
2. The public road is now held by two thin walls 1.7 m apart, W2 and W3. W2 is founded 0.5 m below the stair, and its top is below the road edge. As drawn, this is not a road-retaining structure.
3. Nearly all resilience items are "notes", and grep finds none of them in the C11 folder: shut-offs, PV, battery, generator, lightning, wildfire, assembly points. The plant room is 4.2 m², with no space for the battery.
4. New water hazards: the court's overflow sits at the front-door level and discharges onto the court stair, one terrace outlet lands on a stair landing, and the garage falls 0.44 %, not 1 %, towards a lobby at the same level.
5. An LPG cage stands in the sunken court, 2.4 m from the front door.

## Scorecard

SCORECARD: fixed=1 partly=13 not_fixed=4 worse=0 new_blocker=1 new_major=4 new_minor=1

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| RES-01 road walls | partly fixed | *measured*: W1 is 3.87 m (RC 0.40), W3 2.36–2.79 m, W2 1.76–1.92 m exposed. All are separate site elements. | See RES-N01. |
| RES-02 north cut | partly fixed | *measured*: PW-N (Ø450 at 0.7 m) runs v 0.85, u 0–13.2, toe 1668.6. Lower formation 1669.40; cut at v 1.1 is 4.22 m at u 6.8 (ground 1673.62) and 3.29 m at u 9.4. Toe embedment is only **0.8 m**. The piles (v 0.625–1.075) overlap the 0.45 m house wall (outer face ≈ v 0.80). East of u 13.2 the cut is still 1.9 m (u 13.2) to 1.25 m (u 15), 0.8 m from the boundary, with no support. | Toe ≤1665.4 (embedment ≥1.0× retained height, *assumption*) for u 5–13.2, or design it as propped by both slabs plus temporary rakers. Move the pile centreline to v 0.50 (faces 0.275–0.725). Add a 75 mm drainage composite and a footing drain at 1669.0 along v 0.9. Extend PW-N to u 15.5. |
| RES-03 downhill fills | fixed | *measured*: `t-low` is suspended on FW-20.6 (founded 1666.5). The 2.64 m fill is gone; lawn fill ≤1.33 m. | — |
| RES-04 run-off and mud | partly fixed | *measured*: the boundary ground at v 3–7 is 1677.34–1677.39, below the forecourt (1677.47), which is good. At v 11.6–17.4 it is 1677.51–1677.57, above the W2 top of 1677.45 (RES-N01). The north swale is a note; §7.9b is open. | Draw the north channel at v 0.5 and its catch pits (WAT-06). Raise the W2 upstand (N01). Survey the road (Q6). |
| RES-05 snow storage | partly fixed | *measured*: the snow pit is only a text in `WATER`. No pit and no gate are drawn. | Drained pit 2.0 × 3.0 × 1.5 m at the court NW corner (≈ u −3.5…−1.5, v 11.8…14.8), with a 1.2 m hinged gate in the W1 guard. Shovelled snow never goes onto `rs-*` or `cs-*`. |
| RES-06 thresholds | partly fixed | *measured*: `SETDOWN` covers only t-south, deck-r and green-r (0.25 m). The ENE balconies (windward, E 26 % of winter hours) are not set down. Slot channels are a note. | Set the balc-e and balc-m slabs down ≥0.10 m. Draw a 150 mm slot channel at the four sliders on u 18.0 and at all the others. |
| RES-07 cornices, icicles | partly fixed | *measured*: the front door is now under the porch. Road-door canopy, parapets and snow guards are notes. The SSE canopy edge (v 14.0) drips onto the t-south table zone. | 0.6 m parapets with snow guards; a 1.5 m canopy over the road door and the lobby east door (u 12.6, v 7.9–8.9); a heat-traced gutter on the canopy edge at v 14.0. |
| RES-08 icing stairs | partly fixed | *measured*: real stairs now: 12 + 12 risers of 164/158 mm, 3 × 8 of 150 mm and 2 × 8 of 149 mm, landings, handrails both sides. Canopies and flamed treads are notes. The lawn stair (u 20.6–21.8) is open to the east wind. A terrace outlet lands on `cs-l2` (RES-N04). | Draw a canopy over `rs-f1`, `rs-l1` and `rs-f2`; use flamed treads with a 1–2 % forward fall; draw an east screen of 1.2 m on the lawn stair's u 21.8 guard. |
| RES-09 water | partly fixed | *measured*: 2 × 1.5 m³ on the ground slab (good), 3.0 m³ against the ≥4 asked. *inferred*: 2.5–3.3 days at 150 L/p/d for 6–8 people (*assumption*). Gravity head to the lower floor 1.6–2.8 m (0.16–0.28 bar). | Replace the bench at (0.2–0.75, 6.4–8.0) with a third 1.0 m³ tank. Seismic straps and flexible connectors. Booster on the essential circuit. |
| RES-10 power cuts | partly fixed | *measured*: the lift pit is gravity-drained (good). The automatic rescue device (ARD) is not in the ledger's CIR-02 line. PV, battery and generator are notes. The plant room is 4.2 m² (ROOM-01 asked 9–10 m²) and is already full with the boiler, cylinder and MVHR. | Make `store-r` R(7.4, 11.6, 9.4, 13.0) the battery, inverter and main-board room, fire-separated and away from water. Draw a PV zone of about 43 m² on the garage roof (u 0.5–6.3, v 1.6–9.0). Draw the 32 A generator inlet on the west pier (v 9.03–10.10). Write the ARD and its ≥5-trip battery into the lift spec. |
| RES-11 gas cut | not fixed | *measured*: no flue chase is drawn. The C10 position (12.8, 7.5) now falls inside the main hall→living opening (u 12.6, v 7.45–8.65) and in front of the road-lobby glass door. | A 250 × 250 chase at u 12.6–12.85, v 6.2–6.45: the lounge NW corner, then the living NW corner, then up the deck-r NW corner against RW-12.6, ending ≥1681.8 (1.0 m above the lobby roof at 1680.8). |
| RES-12 after an earthquake | not fixed | *measured*: the words shut-off, niche and assembly appear nowhere in the C11 folder. The 1.07 m pier between the south shutter and the road door (v 9.03–10.10) still exists. | Draw a 0.6 × 0.9 m niche in that pier (seismic gas valve, stop-cock, isolator). Assembly points: the road, and the lawn east of u 23.5 (H/2 of the 11.0 m east face; about 23 m² over v 1–11, *measured approx.*). Never the court, which has walls of 2.1–3.9 m. One of the 6 lockers is the 72 h kit. |
| RES-13 rainwater, greywater | partly fixed | *measured*: the cistern is named under `t-low`, but its volume and position are not given. Its floor (1666.8) is 0.8 m below the lawn (1667.6), so the bottom cannot drain by gravity. Greywater is a note. | Put the cistern in the u 19.3–20.6, v 1.1–6.5 bay (about 17 m³ gross, *inferred*), with its own walls, so water never stands against the guest room's wall at u 18. Add a 2″ suction point at the garden-store door for a petrol fire pump. |
| RES-14 wildfire | partly fixed | *measured*: 3 deciduous trees on the bank about 10.7 m from the u 18 façade (crowns ≥5 m away). Gravel strip and ember mesh are absent. The pergola slat material is unspecified. | 1.5 m gravel strip along u 18–20.6 and v 13–16; 3 mm ember mesh on all vents; non-combustible pergola and screens. |
| RES-15 lightning, earthing | not fixed | *measured*: not in the C11 folder. | Foundation earth electrode in the strip footings; roof ring with 4 down-conductors; Type 1+2 surge protection (MEP-06). |
| RES-16 wind | partly fixed | *measured*: a 2.0 m screen on v 6.2 between the balconies. The north end of balc-m (v 2.6) is open to the NNW. | 1.8 m screen on v 2.6 (u 18–19.85); anchored PV and furniture. |
| RES-17 roof access, snow load | partly fixed | *measured*: the lift overrun is drawn (+0.8 m). The hatch and the snow and drift loads are notes. | 0.9 × 0.9 m hatch over the REST landing. Write 1.5–2.5 kPa ground snow (*assumption*) plus drift at the 3.3 m lobby/office step onto deck-r into the structural notes. |
| RES-18 rockfall | not fixed | Still unknown (CONSOLIDATED F10). | Photos of the slope west of the road. If it has rock faces over 3 m, the garage west wall becomes solid RC. |

## Part B: new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| RES-N01 | BLOCKER | W2 / W3 / road stair, u −9…−3.5, v 11.6–17.12 | A public road is held by two thin stacked walls 1.7 m apart. W2's footing sits 0.5 m below the stair, inside W3's wedge, and its top is below the road | One RC trough: W2 and W3 on a common base, with the stair slabs as struts |
| RES-N02 | MAJOR | court, (−0.2…0.4, 12.3…12.9) | LPG cage in a sunken court, 2.4 m from the front door | Mains-gas bayonet, or cylinders at road level |
| RES-N03 | MAJOR | court overflow (0.8, 15.9); walk-s | The overflow equals the door threshold and empties onto the court stair; the walk is level with the lower FFL against the bedroom wall | Scupper at 1673.45 into a channel beside the stair; drained strip at the wall |
| RES-N04 | MAJOR | t-south (6.8, 16.2); fore-deck; lawn | Outlets and overflows lie outside their surfaces; one empties over a stair landing | Move them; make §7.9 test their location |
| RES-N05 | MAJOR | garage → core lobby → lift, road level | The garage falls 0.44 % towards a lobby at the same level; water reaches the lift shaft | 1.2 % fall to an internal trench, shutter sill above the forecourt |
| RES-N06 | MINOR | tank room R(0, 1.1, 2, 9.5), main | 1.5 m³ tanks behind a level 1.2 m door into the hall | 80 mm upstand, gully, straps |

## Part B: details

**RES-N01 · The road walls (BLOCKER).**
- *Measured* (`structure()` and `site_walls`):
  - W2 is a 0.30 m cantilever, 1675.0 → 1677.45, "no heel under the road". W3 is 0.35 m, founded at 1673.0, retaining 2.36–2.79 m.
  - Their centrelines are 0.15 m and 1.875 m off the boundary, so they stand 1.725 m apart. The road (1677.51–1677.57) to the court (1673.60) is a 3.9–4.0 m drop within 1.7 m.
  - W2's footing is only 0.5 m below L1 (1675.50), above the ≥0.8 m frost depth assumed in WAT-10. Its toe can only sit on the soil that W3 retains.
  - W2's top (1677.40–1677.45) is 0.06–0.17 m below the boundary ground, so road water, grit and the plough berm spill onto `rs-f1`.
  - Q7's "1.0 m stone wall with a 0.8 m lattice" on top is a 1.8 m unreinforced mass over the only stair, in a high-seismic zone.
- *Correction:*
  - Build W2, W3 and the stair as one drained RC U-trough. Both walls are 0.35 m on a common base slab at ≤1672.9, with the stair flights cast as RC slabs spanning between them, and cross-walls or counterforts at ≤3.0 m. Design for traffic surcharge (≈10 kPa, *assumption*) plus seismic earth pressure. Weep holes discharge to the court channel.
  - Cast W2 monolithic up to ≥1677.75, then a 1.1 m RC or steel barrier rated for vehicle impact. No loose stone.
  - Get the road authority's view first.

**RES-N02 · LPG in the sunken court.**
- *Measured:* the cage at (0.1, 12.6) is 2.4 m from the front door (u 2.0, v 10.1–11.1) and 2.6 m from the entry window (u 2.7–3.9, v 13.0). It sits beside the porch recess, inside walls of 2.1–3.87 m on the north and west.
- LPG is heavier than air. A leak pools in the court and the porch and runs down `cs-f1…f3` to `walk-s` and the loggia, and the gullies are about 5 m away.
- *Correction:*
  - If mains gas comes (MEP-05 assumes a meter), use a natural-gas bayonet at the cooking station.
  - Otherwise keep the cylinders at forecourt level (≈1677.4), open to the road, ≥1 m from openings and ≥2 m from drains and the court edge (*assumption*; supplier to confirm).
  - Never put cylinders below the surrounding ground.

**RES-N03 · Court overflow and the garden walk.**
- *Measured:*
  - `court-w` and `cs-f1` both start at 1673.60, and the porch and the front door are at 1673.60. The overflow at (0.8, 15.9) therefore only works once water reaches the threshold, and it then pours down 24 treads.
  - The catchment is about 60 m²: the court, the porch, the road stair and the W1/W3 faces.
  - `walk-s` R(9.74, 16.0, 15.4, 17.12) is at 1670.00, which is the bedrooms' FFL, directly against their south wall. The loggia (1669.98) has a 20 mm step to the lounge slider.
- *Correction:*
  - Court channel at 1673.45. A 150 × 300 mm scupper through SW-6 at 1673.45 feeds a 150 mm channel beside `cs-f1…f3` (never on the treads) into the walk channel.
  - Along v 16.0–16.3, a 300 mm drained gravel strip with a grated channel at 1669.85, and the wall tanked to 1670.15.

**RES-N04 · Outlets outside their surfaces.**
- *Measured* (shapely, `WATER` against the terrace polygons):
  - The `t-south` outlet (6.8, 16.2) lies in the cut-back R(4.6, 16.0, 7.8, 16.4), so it discharges over `cs-l2` (1671.20), and ice forms on a landing.
  - The `fore-deck` outlet (−3.2, 11.3) and its overflow (−3.4, 10.5) are off the deck.
  - The `lawn` overflow (26.0, 10.0) is on the bank. `lawn_edge(10)` = 24.0.
  - §7.9 passes because `checks.py` counts outlets and never tests where they are.
- *Correction:*
  - Move the t-south outlet to (7.8, 16.2) on LW-6.8's line extended, or onto the column C-6.8/13 with an internal downpipe.
  - Fore-deck outlets at (−1.5, 9.0) and (−2.6, 11.0).
  - Lawn overflow at (23.0, 10.0) to the level spreader.
  - Add a containment test to §7.9.

**RES-N05 · Garage flood path to the lift.**
- *Measured:* "falls 1 %, 1677.50 → 1677.47" is (0.03 / 6.8) = **0.44 %**. A true 1 % puts the shutter sill at 1677.43, below the forecourt (1677.47).
- The lobby and the lift landing are at 1677.50, flush with the garage's high end. Any pond over 30 mm (snowmelt off two cars, or forecourt ponding) crosses the fire door into the lobby, then the lift door, then the shaft and the pit (1668.8).
- *Correction:*
  - Garage at 1677.50 by the fire door, falling 1.2 % to an internal trench drain at u 0.8 (grate 1677.43) with an interceptor, piped to the boundary channel.
  - Shutter sills as a 20 mm hump at 1677.49.
  - A water bar at the fire door.

**RES-N06 · Tank room.** *Measured:* the tank room and the bulk store are about 23 m² behind a level 1.2 m door into the main hall. *Correction:* an 80 mm upstand ramp at the door (it holds one 1.5 m³ tank), a floor gully to SH-W with a non-return valve, seismic straps and flexible connectors.

## What C11 gets right

- The water tanks are off the roof and on the ground slab, which takes about 3 t off the top of the building.
- `t-low` is suspended and the lawn fill is ≤1.33 m. The 39 m³ wet fill wedge on a 35 % slope is gone.
- The road door gives an indoor route from road to lift and stair. In snow nobody has to use the 24-riser road stair, and the front door is under a porch (no cornice).
- The lift pit drains by gravity. The design has no sump pumps except the possible foul station.
- The lower floor has three exits at ground level (guest slider, lounge slider, garden walk), and every outdoor stair has a real riser count with landings.
- The north pile wall exists and stays off the neighbour (no anchors).

## Out-of-scope notes

- Geotech: the SW-29/30 fill wall (1.69–1.74 m) at v 17.12 is 1.3 m from the south boundary. The fore-deck piers stand on a ~50 % embankment.
- Structure: PW-N clashes with the 0.45 m north wall of the house.
- MEP: under outfall option A, the foul lifting station must be on the battery circuit.
- Life safety: a wheelchair user on the lower floor has no step-free way out in a power cut. Provide an evacuation chair and an ARD.
