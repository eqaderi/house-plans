# 04 · Water: stormwater, drainage, waterproofing (C10 review)

Reviewer specialty: water. Concept-stage review only; nothing here is engineered or code-checked.
Levels are from `design.py` and `zg` on the 27-point survey TIN (an inferred surface).

## Summary

1. C10 draws no water: every level is a flat number, with no falls, outlets, channels, tanking or outfall.
2. Three things fail as drawn: the garage floor sits 0.01–0.07 m above the road; the sunken court has no outlet and drains onto the boys' room roof; three roofs over rooms have 20–50 mm of build-up where 250–350 mm is needed.
3. Walls are buried up to 3.6 m on a wet slope below an uphill neighbour (Paveh station: median ~770 a year, units unverified).
4. About 380 m² of new hard surface drains to the east boundary (1664.9–1665.8), the downhill neighbour. No discharge is designed.
5. Gravity works everywhere, so every fix below is a gravity fix; only the lift pit needs extra care.

## Findings

| ID | Sev | Where | Issue |
|---|---|---|---|
| WAT-01 | BLOCKER | garage, hall-r, forecourt | Floor 0.01–0.07 m above the road; forecourt level with it |
| WAT-02 | BLOCKER | court-w, gstair | No outlet; drains onto t-south; door flush and exposed |
| WAT-03 | BLOCKER | t-south over bedrooms | 20 mm below FFL, no build-up or falls |
| WAT-04 | BLOCKER | deck-r, green-r | 50 mm below FFL; no build-up, outlets or access |
| WAT-05 | MAJOR | buried walls | Up to 3.6 m retained; no tanking or drains |
| WAT-06 | MAJOR | lift-l pit | Lowest point, in the wettest corner |
| WAT-07 | MAJOR | north strip | Uphill neighbour's water reaches the walls |
| WAT-08 | MAJOR | east boundary | No outfall; flow onto the neighbour |
| WAT-09 | MAJOR | balc-e, balc-m | Drip onto sliders and the 14 steps |
| WAT-10 | MAJOR | t-low, lawn | Thresholds on settling fill; flat lawn |
| WAT-11 | MAJOR | path-s, shared footpath | Runoff along the bedroom wall, onto the shared path |
| WAT-12 | MAJOR | plant room, wc-r | Tanks and shower over the kitchen |
| WAT-13 | MINOR | road-level top roof | No falls or outlets |
| WAT-14 | MINOR | north side, stairs | Frozen pipes, icy steps |

## Finding details

**WAT-01 · Road water into the garage.** *Measured:* road edge 1677.43 at (-0.6, 1.1) and 1677.49 at (-6.3, 11.6); garage floor 1677.50; forecourt a flat 1677.40 on up to 3.0 m of fill; apron at shutter 1 only 1.8 m deep. *Correction:*
- Option A (preferred; changes an owner level, owner decides): road FFL 1677.65, so floor-to-floor 4.05 m and 24 risers of 168.8 mm. Crest 1677.60 at the doors, falling 1:50 to a DN150 slot drain along the boundary (v 1.1–11.6), grate at 1677.45.
- Option B (keeps 1677.50): crest 1677.55, 0.8 m in from the road, falling back to the road and forward to a slot drain at 1677.46 outside the shutters and the door.
- Use sealed paving over the fill. Survey the road's crown and gutter first; "≈1677.4" is unknown.

**WAT-02 · Arrival court is a sump.** *Measured:* ground along u -1.2 is 1674.83–1673.77, so the court sits 0.2–1.2 m below its west side. It collects the court (34 m²), the 22R stair (7 m²) and the SW wedge (~47 m²). It is flush with t-south (1673.58) along u 4.6, so it drains onto the boys' roof. The entry door (2.0, 12.15) is level with the court and unsheltered (road slab ends at v 11.6). *Correction:*
- Court 1673.55 at the door, falling 1:60 south to a channel along v 17.1 at 1673.45.
- Gully at (4.3, 17.1), DN110 at invert ~1672.9, run down the south strip (ground 1671.8 at (4.6, 17.4)).
- At u 4.6: a 100 mm kerb plus a channel. At the door: a 1.5 m slot drain and a canopy over u 0–3.4, v 11.6–13.3.
- A channel at the stair top (v 11.6) and a cut-off drain along u -2.6.
- If the owner's larger court is dug west to the road, gravity still works: add a 150 mm kerb on the 3.9 m road wall, two gullies and DN150 pipe.

**WAT-03 · South terrace over the children's rooms.** *Measured:* 44.9 m² at 1673.58 against a floor of 1673.60. Its sliders have no overhang. *Correction:*
- Set the slab down 240 mm (~1673.26 at the façade); membrane falls 1:80 to v 16.2.
- On top: ~140 mm inverted insulation, a drainage mat and level pedestal pavers at 1673.58. This keeps the threshold step-free (rule 5.4) with a 150 mm membrane upstand, plus slot channels at the sliders.
- Outlets at (6.8, 16.2) and (15.4, 16.2), on wall lines; overflow at u 11.25, between the windows; parapet with a drip.
- About 3.0 m clear height remains below.

**WAT-04 · Roof terrace and green roof.** *Measured:* deck-r (39.8 m², over the living room) and green-r (41.3 m², over the master suite) are both at 1677.45 against a floor of 1677.50. *Correction:*
- Use the WAT-03 detail at the doors at (11.4, 8.4) and (12.2, 11.2).
- Deck: fall 1:60 to outlets at (17.6, 7.5) and (17.6, 12.0).
- Green roof: fall east to outlets at (17.5, 1.6) and (17.5, 5.8), never north. Root barrier, 300 mm gravel at upstands and outlets, 150 mm upstands at the core walls.
- Internal downpipes. A 0.9 m maintenance gate from the deck at (13, 6.2).

**WAT-05 · Buried walls.** *Measured* (height retained above FFL): main west wall 1.39 m at (2, 4.6); laundry 3.38–1.85 m; stair 3.62 m; grandparents and ensuite north wall 1.74 to -0.6 m; boys' south wall 1.25 m at u 6.8. *Correction:*
- Next to habitable rooms: watertight concrete, an external membrane and a drainage geocomposite.
- A DN110 footing drain at invert ~1669.35, falling 1:100 to a catch pit at (18.6, 13.0) (ground ~1668.0). Main-floor drains at ~1673.0 drop into it.
- Under the lower slab: a 150 mm stone blanket with drains to the east, because groundwater moves NW→SE.
- Surface water stays in solid pipes.

**WAT-06 · Lift pit.** *Measured:* ground at the lift is 1672.15–1671.44, so an assumed 1.4 m pit puts its floor at ~1668.6, under about 3.5 m of soil. *Correction:* a fully watertight pit with waterstops and a membrane, not a sump pump.

**WAT-07 · North strip.** *Measured:* the boundary sits 0.1–0.15 m above v 1.1, and the strip falls ~44% over 17.8 m. There is a closed earth pocket under the master at u 11.4–17.8, v 1.1–2.8. *Correction:*
- A lined channel at v 0.5 over a solid DN110 pipe, with drop catch pits at u 2, 6.8, 11.4 and 17.8.
- Fill the pocket with drained stone, or lay blinding falling to an outlet at (17.6, 2.0).

**WAT-08 · Final discharge.** *Measured:* about 378 m² of hard surface on the 600 m² field. Roofs alone (279 m²) give about 170 m³ a year (*inferred*). *Correction:*
- A 15–20 m³ cistern inside the garden-terrace fill (replacing ~40 m³ of fill), feeding irrigation and WC flushing.
- Overflow to a 12 m level-spreader along the lawn edge (u + 0.448v = 28.5, ~1666.3), at least 3 m from the east boundary. No pipe crosses the boundary.
- To confirm: storm intensity, a percolation test, slope stability, and whether any public drain exists.

**WAT-09 · Balconies.** *Correction:* fall them 1:60 to a 100 mm gutter at u 19.4, with downpipes at v 1.1, 6.2 and 16.4 and a drip edge. This keeps water off the sliders and the 14 steps.

**WAT-10 · Garden terrace and lawn.** *Measured:* t-low sits on up to 2.64 m of fill, the lawn on up to 1.35 m. *Correction:*
- Make the terrace a suspended slab from the house to the 2.4 m wall, with a slot channel along u 18, falling 1:60 to 1669.94.
- Fall the lawn 1:60 east, to 1667.47.
- Heel drains behind both walls, and a swale at the lawn's north cut (1.19 m).

**WAT-11 · South strip.** *Measured:* ground along v 16.4 falls 1671.25→1667.48 (~35%) and is 0.3 m lower at the shared footpath (a drawing label, to confirm). *Correction:* a 1:40 cross-fall to a channel at v 17.3, a 100 mm kerb at v 17.42, catch pits every ~1.5 m of drop, and walls tanked to 150 mm above ground.

**WAT-12 · Tanks above the kitchen.** The plant room (u 3.4–7, v 11.6–13.3) and wc-r sit over the kitchen and entry. *Correction:* a tanked, bunded floor (100 mm upstand) with a gully; tank overflows piped to the court channel.

**WAT-13 · Top roof.** *Correction:* fall 1:60 east to two outlets plus one overflow, with downpipes in the core riser.

**WAT-14 · Snow and ice.** The noon sun is ~31.6° high in midwinter, so the north side stays shaded (*inferred*). *Correction:* downpipes inside the warm envelope, heat-traced north outlets, pipes below frost depth (unknown, to confirm), and a channel at the foot of the 22R stair.

## What C10 gets right

- The buried NW holds only service and wet rooms. Bedrooms and day rooms face open ground to the south and east, which limits the length of wall that must be tanked to habitable standard.
- The whole site falls east, so every drain, including the lower floor's footing drain at about 1669.35, can reach an outfall by gravity, with no pumps.
- The master and east balconies shelter the lower floor's east sliders from rain.
- The lawn is laid along the contour, which keeps fill (1.35 m at most) and its drainage modest compared with C09.
- The green roof over the master suite reduces and slows runoff.

## Out-of-scope notes

- Foul drainage: the lower-floor WCs at 1670 sit 7.4 m below the road, so a sewer connection needs pumping, or an on-site system with a geotechnical check.
- Structural: the 240 mm slab set-downs, and the loads from snow plus a saturated green roof.
- Geotechnical: retaining walls up to 3.9 m, and the infiltration limits on a 35% slope.
- Safety: guards, and the riser change in WAT-01 option A.
