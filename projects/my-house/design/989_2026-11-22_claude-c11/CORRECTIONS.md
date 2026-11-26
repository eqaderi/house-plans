# C11 corrections ledger

One line per row of [`CONSOLIDATED.md`](../../reviews/c10-expert-review-2026-11-22/CONSOLIDATED.md) §3. **Done** = in `design.py` and on the drawings, with the evidence named. **Partly** = the part that geometry can carry is in; the rest is a specification note or needs an engineer or a survey. **Not done** = with the reason. Check ids refer to `checks.json` (`§7.n` = CONSOLIDATED §7 check n). All figures `measured` from `design.py` unless marked.

Exploratory concept: nothing here is engineered, permit-ready or code-compliant.

**After the C11 review (28 reviewers, `../../reviews/c11-expert-review-2026-11-22/`).** The rows below are the ledger as first written, with the overstated claims corrected in place. Items described as "specified" are written out in [`SPECIFICATION.md`](SPECIFICATION.md); before the review that file did not exist, and the ledger's "notes" pointed nowhere (THM-N03, MAT-N01, KB-08). The fix round that followed the review is at the end of this file.

## Structure & stacking

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-STR-01 | Done | Service room dug to 1673.60 under the whole garage: `tanks` R(0, 1.1, 2.0, 9.5) and `bulk` store; walls u 0, u 2.0 (to v 1.1), v 1.1, v 2.8, v 4.6, v 7.3, u 3.8, stair core u 6.8; beam MB-9.5 under the garage back wall. Fallback (void) not needed. | Support sheet: road floor 133 m², 0 m² unsupported (§7.1); main pit max cut 4.15 m to formation (§7.4) |
| C11-STR-02 | Done | Lower north wall at v 1.1 for u 9.4–18.0. The space became the seated ensuite (stacked under the master ensuite, u 9.4–11.4), a walk-in and the grandparents' sitting area; guest north window deleted. Store/riser at u 9.4–11.4 replaced by the ensuite: the riser SH-E sits in the shared wall. | Wall-over-wall: 0 m mid-span (§7.2); main plate 207 m², 0 unsupported |
| C11-STR-03 | Done after the fix round (first written as done, **overstated** by 25 mm at two openings; columns now 0.35 m) | Columns C-4.6/13, C-6.8/13, C-11.1/13, C-15.4/13, C-18/13 from footings (1668.6 / 1666.6) to the road roof or the deck; beam LB-13.0. Openings clear: kitchen window u 5.35–6.55, dining slider u 9.5–10.9, living window u 15.75–16.35. | §7.2b: columns founded, beam ends supported; sections A–H draw them |
| C11-STR-04 | Done | RC-18L on u 18.0, v 12.8–16.4, founded 1666.6; beam LB-16.0 at the loggia front (v 16.0, the lower wall face) and BB-16.4 to the balcony; no isolated tall posts. | Sections G–G, A–A; support sheet |
| C11-STR-05 | Done after the fix round (first written as done, **overstated**: the checks counted glass as wall; beam MB-13.0 added) | Grid u 0 · 2.0 · 4.6 · 6.8 · 9.4 · 11.4 · 12.6 · 15.4 · 18.0; v 1.1 · 4.5 · 6.2 · 7.3 · 9.5 · 10.95 · 13.0 · 15.75. Main east wall 18.0, lower west RC wall 4.6, kitchen/dining 9.4, office u 9.4/12.6/v 13.0, road south 13.0, beam MB-6.8. Kitchen west wall at u 4.4 (off grid, on dug ground) so the kitchen reaches 15.6 m². | §7.2: 0 m landing mid-span, 0 m offset 0.1–0.5 m |
| C11-STR-06 | Partly | RC core (0.25 m stair walls with a solid spine, 0.20 m RC lift shaft); solid panels u 18.0 v 1.1–3.1 on both floors (sliders start at v 3.2 / 3.3); main SE L-wall MW-SE; garage north wall solid. Collector beams, sliding bearings and the stiffness-centre check are for the engineer. | Plans; MW-SE in `checks.json` elements |
| C11-STR-07 | Done after the fix round (first written as done, **overstated**: lawn-stair landings and the walk sat on 1.3–2.0 m of fill) | Suspended: lounge east R(15.4, 6.2, 18, 10.95) on ground beam FW-15.4, loggia (FW-13.4, FW-16.0), garden terrace (FW-20.6, FW-19.3), living over the loggia, forecourt deck. Every ground-bearing slab ≤1.0 m of fill. Footings stepped to 1666.6–1668.9 (frost depth unknown). | §7.4: worst fill 0.90 m lower, 0.35 m main |
| C11-STR-08 | Partly | Tanks off the road level (on the ground slab); green roof extensive; deck on pedestals. Snow and drift loads specified in SPECIFICATION.md, not calculated. | Plans; §7.15 |
| C11-STR-09 | Partly | Site walls are separate elements (RW-W1…W4, PW-N, FW-20.6), never part of the house frame; W2 a cantilever with no heel under the road. Uphill house walls drawn as integral RC basement walls (engineer designs them for seismic earth pressure). The 100 mm joints are specified in SPECIFICATION.md; whether the uphill walls stay integral is an engineer's and owner's decision (fix round). | `checks.json` elements |
| C11-STR-10 | Partly | Garage roof beam RB-5.3 on the shutter pier; v 1.1 and v 9.5 are walls. Slab spans ≤7.0 m checked; load figures for the engineer. | §7.1 (spans), §7.2b |

## Ground, retaining & earthworks

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-GEO-01 | Done | PW-N: contiguous Ø450 piles at 0.7 m along v 0.85, u 0–13.2, built before the north dig; no anchors under the neighbour (SPECIFICATION.md). Neighbour condition survey listed under limits. | Plans (road), sections C–C, D–D, 3D |
| C11-GEO-02 | Done | Forecourt split: ground-bearing near the road (≤1.0 m fill under a 0.6 m build-up), suspended deck (10 m²) on pier line PB-F with piers P-F/5.6, 8.6, 11.6 where fill would exceed 1 m. | Support sheet; section B–B |
| C11-GEO-03 | Done | `t-low` a suspended slab between the lower east wall and FW-20.6 (founded 1666.5); cistern north of FW-6.2T, garden store south; lawn walls derived from the ground model (max 1.33 m). | Section H–H; §7.3 |
| C11-GEO-04 | Done | Formation 0.60 m below every ground-bearing floor. Deepest cut to formation 4.22 m (lower) and 4.15 m (main, with STR-01): under ~4.5 m. | Earthwork table; check 4.4 |
| C11-GEO-05 | Partly | Volumes reported: 397 m³ cut, 66 m³ fill (inferred, in situ). The sequence (condition surveys → topsoil → north piles → top-down dig → tanking → frame → backfill → garden walls) is specified in SPECIFICATION.md; laydown and pump positions not drawn. | `checks.json` earthworks |
| C11-GEO-06 | Done | Lawn north edge at v 1.0; its walls inside the parcel. | §7.13 |

## Water & waterproofing

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-WAT-01 | Partly | Road FFL 1677.50 kept; forecourt 1677.47 at the shutters and road door, falling to a boundary channel (drawn as outlets and fall arrow); garage falls 1 % to the shutters (SPECIFICATION.md). The road crest cannot be checked: road levels unsurveyed. | §7.9 pass; §7.9b open (Q6) |
| C11-WAT-02 | Done | Court falls 1:60 to a south channel, gullies at (4.3, 15.8) and (−2.8, 16.9), overflow, DN150 outfall down the stair band; snow pit at the NW corner (SPECIFICATION.md). Porch slot drain at the door. | Plans (main); §7.9 |
| C11-WAT-03 | Done | Structural slab set down 0.25 m under `t-south`, `deck-r`, `green-r`; balconies and loggia uninsulated; outlets on wall lines as listed in the review; slot channels at every slider (SPECIFICATION.md); children's rooms keep 2.95 m clear. | §7.8; sections show the sand build-up band |
| C11-WAT-04 | Partly | Buried walls 0.45 m (drawn); tanking, drainage board, footing drain and stone blanket are specified in SPECIFICATION.md. | Plans |
| C11-WAT-05 | Done | LIFT-PIT: tanked 1.2 m pit (floor 1668.80) with a gravity drain east (SPECIFICATION.md). | Section F–F; §7.19 |
| C11-WAT-06 | Partly | North-strip channel and catch pits: specified in SPECIFICATION.md (cast into the pile cap). | — |
| C11-WAT-07 | Partly | Rainwater cistern under the garden terrace (drawn as FW-6.2T bay); spreader, greywater and percolation test are specified in SPECIFICATION.md. | Section H–H |
| C11-WAT-08 | Done | Garden walk 1:40 cross-fall to a channel with two outlets; kerb; walls inside the setback (walk stops at v 17.12). | §7.9, §7.13 |
| C11-WAT-09 | Partly | Road WC over the entry, not the kitchen; plant room bunded (SPECIFICATION.md); shower recesses specified in SPECIFICATION.md. | §7.15: no wet room over the kitchen |
| C11-WAT-10 | Partly | Internal downpipes and frost depth: specified in SPECIFICATION.md. | — |

## Arrival, gates & outdoor stairs

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-ARR-01 | Done, with a measured deviation | Reviewer 05's L-stair against the road: 12 + 12 risers (164 / 158 mm), 320 mm goings, corner landing at 1675.50, 1.4 m clear. Moved 0.30 m off the boundary so W2 stands inside the parcel, and F2 moved 0.30 m north so W4 stands inside the setback. Court 40.6 m² open + 4.2 m² covered porch (C10 34.0; review 51.6 with zero-thickness walls). | §7.5, §7.13; decision 17 |
| C11-ARR-02 | Done after the fix round (first written as done, which was **false**: the walk touched the loggia at one point) | Lower south wall at v 15.75 (outer face 16.00), so the band v 16.00–17.27 gives 1.27 m clear plus a kerb inside the setback (the review's v 16.02 left 1.15 m once walls had thickness). Court stair 3 × 8 risers of 150 mm, 340 mm goings, 1.5 m landings, treads within −0.34…+0.15 m of natural ground; garden walk at 1670.00 to the loggia (fill ≤1.77 m behind a wall). Rooms keep 4.3 × 4.8 m. | §7.5; section E–E; §7.11: ground in front of the boys' window +0.42 m, girls' +0.00 m (sill +0.90) |
| C11-ARR-03 | Done | Lawn stair R(20.6, 3.4, 21.8, 10.28): top landing 1.2 m, 2 × 8 risers of 149 mm, 320 mm goings, 1.2 m landing, walls both sides. | §7.5; section H–H |
| C11-ARR-04 | Done | Forecourt edge on v 11.6: W1 with a 0.6 m upstand and 1.1 m guard, open only at the stair head; guards on every court, stair and wall edge. | §7.7: 89.5 m of guards, none missing |
| C11-ARR-05 | Partly | Gate 1.2 m, intercom and parcel niche at the stair head (labelled on the main plan; refuge with 2 bollards and a sliding gate after the fix round); street wall = W2 raised as stone + lattice (SPECIFICATION.md); shutters as vehicle gates. Owner question Q7. | Main plan |
| C11-ARR-06 | Done | Porch R(0, 9.5, 2.0, 11.6) dug to 1673.60 under the road hall, RC-0 on u 0; front door 1.0 m on u 2.0 at v 10.1–11.1 under it; entry west window deleted; road door 1.0 m at v 10.1–11.1 with canopy and address panel (SPECIFICATION.md). | Plans; §7.12 no window into a void |
| C11-ARR-07 | Partly | Flamed stone treads, nosings, step lights and the canopy over L1/F2: specified in SPECIFICATION.md. | — |

## Garage & vehicles

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-VEH-01 | Done | Aisle u 5.54–6.74 clear for the full depth; cars between u 0.55 and 5.54; fire door at v 8.35–9.35 swinging into the garage, hinged at v 9.35. | §7.10: aisle clear = True |
| C11-VEH-02 | Done | Bands as listed; workbench u 2.8–4.7 (0.2 m shorter: riser SH-W stands at u 4.75–5.5), bikes u 0.6–2.6, EV box at (6.72, 5.0), tyre rack on the north wall. Wheel stops, RCD and fuel cabinet are specified in SPECIFICATION.md. | Road plan |
| C11-VEH-03 | Partly | LC300 in bay 2, reverse in. Delivery bay, mirror and camera need road consent (SPECIFICATION.md). | Road plan |
| C11-VEH-04 | Done | Fire door (kind `fire`) and the full-height glazed screen with a self-closing door across the road-level stair mouth (kind `screen`); extract, CO alarms and insulation are specified in SPECIFICATION.md. | §7.16 |
| C11-VEH-05 | Partly | Shutter details: specified in SPECIFICATION.md. | — |

## Internal circulation, stair & lift

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-CIR-01 | Done | 1.5 m circle clear of walls and furniture at the lift door on all three floors; homework table removed; lower hall a landing street. | §7.10: (road 0, 0), (main 0, 0), (lower 0, 0) m² |
| C11-CIR-02 | Done | Shaft R(9.4, 4.5, 11.4, 7.3), 1.80 × 2.60 m clear in 0.20 m RC; 0.9 m doors south; LIFT-OVR 0.8 m upstand; master ensuite gave up the 0.5 m. | §7.19 |
| C11-CIR-03 | Partly | 24 × 150 mm main→lower and 24 × 162.5 mm road→main, every flight 12 risers / 11 goings of 309 mm. Guards, the obscured half-landing window, rooflight, hatch, lighting and evacuation chair are specified in SPECIFICATION.md. | §7.6 |
| C11-CIR-04 | Done | `store-u` under the flight (5.5 m² clear) with a 0.8 m door off the lower landing through the spine. | Lower plan |
| C11-CIR-05 | Partly | Hall 1.45 m deep in front of the dining; kitchen opening 1.1 m. Pantry door → kitchen opening 3.4 m (target ≤3 m). | Main plan |

## Rooms

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-ROOM-01 | Partly | Plant room at road level, 1.2 m door, flue and riser SH-K beside it. First only 3.0 × 1.4 m; after the fix round 5.0 × 1.7 m (8.5 m² on the grid, store merged in, 0.9 m clear in front of the plant), boiler on its own flue. Still under the 9–10 m² asked. | Road plan; claims |
| C11-ROOM-02 | Done | Road WC + shower R(2.0, 11.6, 4.4, 13.0), 1.0 × 0.9 m tray, over the entry, drains west; plant beside, store buffers the office. 2.4 m wide, not 2.6, because the kitchen wall below moved to u 4.4. | §7.15, §7.17 |
| C11-ROOM-03 | Partly | Office on u 9.4 / 12.6 / v 13.0, 9.8 m² clear; door from the lobby; fold-down bed drawn; rooflight drawn. Deck screen and obscured glass are specified in SPECIFICATION.md. | Road plan; decision 20 |
| C11-ROOM-04 | Done | Dining R(9.4, 8.75, 12.6, 13.0), clear 3.08 × 4.04 m: 2.8 × 4.0 m zone fits; 8 chairs; sideboard; open to the living. | Check 1.5 |
| C11-ROOM-05 | Done | Kitchen 15.6 m² clear, pantry 4.3 m², island 1.4 × 0.7 m with 4 stools. | Checks 1.4, 1.5 |
| C11-ROOM-06 | Done after the fix round (first written as done, **overstated**: the shelf did not screen the hall axis) | Living 5.19 × 6.55 m clear; hall opening v 7.45–8.65 behind a 1.1 m shelf (v 8.5–9.5 is the dining); TV on the west wall, not shared with the master; 200 mm wall at v 6.2; kitchen–dining opening v 10.2–11.3. | Check 3.3 |
| C11-ROOM-07 | Done | Ensuite R(9.4, 1.1, 11.4, 4.5) off the bedroom by a 0.9 m slider, stacked over the seated ensuite; dressing R(11.4, 1.1, 13.2, 3.4) off the bedroom; bedroom door 1.0 m; cot place; ensuite window obscured, tilt-only. | Check 2.5 |
| C11-ROOM-08 | Done | Balcony starts at v 2.6 (Q5); 2.0 m screen at v 6.2 drawn; north window u 15.6–16.8 obscured to 1.7 m. | Main plan |
| C11-ROOM-09 | Done | Beds off the window wall; desks on the west walls near the glass; boys' window u 8.9–10.7, girls' u 11.45–14.75; escape casements and lower obscured glass specified in SPECIFICATION.md. | §7.11 |
| C11-ROOM-10 | Done | Wardrobes to u 17.4 on the lounge wall; dense walls; TV and tea bar on that wall; L-sofa for 6; garden route south of the sofa; hall opening 2.7 m. | Lower plan; §7.10 |
| C11-ROOM-11 | Done | Twin beds with a 1.75 m transfer zone; wardrobes; seated ensuite with a 1.5 m circle and a 1.0 m pocket door; 2.0 m slider. | Claims |
| C11-ROOM-12 | Done | Lockable door hall → basins; shower 2.2 × 1.4 m (3.1 m² on the grid) with a dry zone; WC 0.7 m slider, pan side-on to the door. | §7.17 |
| C11-ROOM-13 | Done | Laundry 4.8 m² clear (washer, heat-pump dryer, sink, airer); separate stores `store-u` 5.5 m² and `store-s` 6.0 m²; drying yard on the north end of the roof terrace drawn. | Check 6.3 |

## Kitchen & bathrooms

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-KB-01 | Done | Hob on the west run at v 11.3–12.2 under the plant room; hood duct up SH-K to the roof; walls to the ceiling. Make-up air and fire damper are specified in SPECIFICATION.md. | §7.15 |
| C11-KB-02 | Done | West run fridge, drawers, hob; south run sink under the window, dishwasher; tall unit at the north of the west run; pantry 3.4 m away. | Main plan |
| C11-KB-03 | Done | Accessible WC 1.67 × 1.98 m clear, pan 0.45 m off the side wall, 0.9 m transfer zone, outward door; shower off the wudu; wudu seats, trough, standing basin. No baffle needed: the pan is out of sight of the hall. | §7.17: 0 hits |
| C11-KB-04 | Partly | Door widths ≥0.75 m drawn. Shattaf, floor drains and dados were first claimed as drawn; they were not (KB-08). They are specified in SPECIFICATION.md. | §7.10 |
| C11-KB-05 | Partly | Outdoor cooking station in the court's west part, with no gas stored below road level; the LPG cage moved to open air at road level in the north strip (fix round, SAF-N04). | Main plan |
| C11-KB-06 | Done | Orthogonal pans, 43–47° off the qibla; owner question Q11. | — |

## Services

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-MEP-01 | Partly | Outfall unknown (F3). Space for the duplex lifting station in `store-s`; options A/B/C listed. | Limits |
| C11-MEP-02 | Done | SH-K R(4.85, 12.25, 5.45, 12.85); SH-E in the shared ensuite wall. SH-W moved to R(4.75, 8.84, 5.5, 9.44): at the review's R(5.0, 7.3, 5.6, 8.1) it would stand in the LC300's bay and the aisle. | §7.15: every wet room ≤4.5 m from a riser |
| C11-MEP-03 | Done | Two tanks of about 1.5 m³ on the ground slab of the service room under the garage, with the booster. | Main plan |
| C11-MEP-04 | Partly | MVHR in the plant room; rates are specified in SPECIFICATION.md. | — |
| C11-MEP-05 | Partly | Boiler, cylinder and flue in the plant room; the rest is specified in SPECIFICATION.md. | — |
| C11-MEP-06 | Partly | Power, PV and battery: specified in SPECIFICATION.md. | — |
| C11-MEP-07 | Partly | Radon: gas layer within the 0.60 m formation; tests are specified in SPECIFICATION.md. | GEO-04 |

## Daylight, sun & qibla

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-SUN-01 | Done | Grid north, true north (grid + 0.78°, from the UTM 38N convergence) and the qibla 204.6° true on every plan; two mats on the qibla in the living room's SE corner (Q12). | §7.18: mats 0.0° off |
| C11-SUN-02 | Done | Living ENE window replaced by a 0.6 m clerestory; slot deleted. Blinds and glazing values are specified in SPECIFICATION.md. | Main plan |
| C11-SUN-03 | Partly | 1.0 m canopy over the SSE glass drawn on the main plan; the awning is specified in SPECIFICATION.md. Not raytraced again. | Main plan |
| C11-SUN-04 | Done | Pergola u 15.4–17.8, v 13.0–15.2 over the loggia; covered walk kept to v 16.4. | Main plan |
| C11-SUN-05 | Partly | Lounge opening 2.7 m; walk-on rooflight in the roof terrace drawn. Glass floor panel: owner option. | Plans |

## Thermal & envelope

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-THM-01 | Done | Walls drawn and deducted at 0.40 / 0.45 / 0.25 / 0.20 / 0.12 m; walls grow outward; `room_dims()` uses them. | §7.14 |
| C11-THM-02 | Partly | Envelope values: specified in SPECIFICATION.md. | — |
| C11-THM-03 | Done | Balconies self-supporting on columns at u 19.6 and an edge beam, so only a short connection crosses the insulation line. | Support sheet |
| C11-THM-04 | Partly | Parapets, snow guards and drift: specified in SPECIFICATION.md. | — |

## Safety

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-SAF-01 | Done | Green roof marked "maintenance only"; guard with a locked gate on v 6.2 drawn on the road plan. | Road plan |
| C11-SAF-02 | Done | A 1.1 m guard on every edge that drops 0.6 m or more, drawn on all plans; no furniture within 0.6 m of a guard. | §7.7 |
| C11-SAF-03 | Partly | Gate at the stair head; the rest are specified in SPECIFICATION.md. | — |
| C11-SAF-04 | Partly | Specified in SPECIFICATION.md. | — |
| C11-SAF-05 | Partly | Specified in SPECIFICATION.md. | — |
| C11-SAF-06 | Partly | Specified in SPECIFICATION.md. | — |

## Accessibility

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-ACS-01 | Partly | Kitchen and grandparents' sliders 2.0 m; office slider 1.8 m; thresholds ≤20 mm with slot channels (SPECIFICATION.md). | Plans |
| C11-ACS-02 | Done | Limits told on the page: the court cannot be step-free from the road; the lift and the road door are the accessible entrance; the lawn is stepped. | index.html limits |

## Privacy & acoustics

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-PRV-01 | Done | Outdoor table at the west end of the south terrace; resilient pedestals specified in SPECIFICATION.md. | Main plan |
| C11-PRV-02 | Done | 200 mm dense walls at lower u 11.1, v 6.2, lounge/girls, main v 6.2 (drawn and deducted). | Plans |
| C11-PRV-03 | Partly | Street wall (SPECIFICATION.md) and the Q7 default; no court/terrace screen. | — |

## Garden & landscape

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-LND-01 | Done | Lawn at 1667.60 (Q4), 57 m² on the grid, 1:60 fall east, slot drain and heel drain. | §7.9 |
| C11-LND-02 | Partly | Three deciduous trees on the bank; species list and root barriers are specified in SPECIFICATION.md. | Lower plan |
| C11-LND-03 | Partly | Garden store under the garden terrace (door on its south wall, FW-12.8T); barrow route via the court stair. | Section H–H |
| C11-LND-04 | Partly | Boot bench at the loggia drawn; the rest are specified in SPECIFICATION.md. | Lower plan |

## Household operations

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-OPS-01 | Done | Shoe zone and 6 lockers in the road hall; 2.6 m shoe and coat cabinet in the main entry; covered guest door. | Plans |
| C11-OPS-02 | Done | Stores: `store-u` 5.5, `store-s` 6.0, `bulk` 9.6, road `store-r` 2.2 m² clear (C10: about 8.6 m³ of storage). | Check 6.3 |
| C11-OPS-03 | Done | Bin enclosure R(0, 0.05, 2.4, 1.05) drawn; parcel niche at the gate. | Road plan |
| C11-OPS-04 | Done | 15 seated (Q2); 30–35 on a sofreh through the dining and living. | Decision Q2 |

## Exterior architecture

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-EXT-01 | Partly | Stone base / rendered main floor: specified in SPECIFICATION.md; 3D shows the tiers. | 3D |
| C11-EXT-02 | Partly | Sliders 1.8 / 2.0 / 2.4 m; living south 2.4 m slider + 1.0 m window (3.0 m does not fit between the column and the wall: measured 2.5 m); shared east centrelines near v 4.1 and v 10.0. | Plans |
| C11-EXT-03 | Partly | Guards drawn; finishes are specified in SPECIFICATION.md. | §7.7 |
| C11-EXT-04 | Partly | Lift overrun and rooflights on the road roof; parapet and plant zone are specified in SPECIFICATION.md. | Section F–F |
| C11-EXT-05 | Partly | Materials: specified in SPECIFICATION.md. | — |

## Flexibility

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-FLX-01 | Partly | Specified in SPECIFICATION.md (lintels, knock-out panel, key switches). | — |
| C11-FLX-02 | Done | Q13 default "no"; roofs labelled non-accessible except the roof terrace. | Road plan |

## Drawing / checks

| ID | Status | How | Evidence |
|---|---|---|---|
| C11-DRW-01 | Done | `structure.py`: one element list and one derived site-wall list, drawn by plans, sections, support sheet and 3D; `engine.supports()` deleted; 8 sections cut every outdoor stair. | §7.3 |
| C11-DRW-02 | Done | All 22 §7 checks in `checks.py`; no 0110-r2 defect marked fixed. | `checks.json` |
| C11-DRW-03 | Done after the fix round (first written as done, **overstated**: east garden 151 vs 147 m²) | Platforms stop inside v 17.42 with their walls; notes recomputed (11 claims); storeys per façade reported. | §7.13, §7.20, §7.22 |
| C11-DRW-04 | Not done | Correcting the brief's EV and prayer-area records changes the project record; it needs an interview session the owner can confirm, not a design study. | — |

## Fix round after the C11 review (22 Nov 2026)

One round, as the work order asked: every BLOCKER the 28 reviewers found, and the MAJORs that need no owner decision. Finding IDs are the reviewers' (`../../reviews/c11-expert-review-2026-11-22/NN-*.md`). The checks were strengthened first, and each new check was shown to **fail on the pre-fix design** (measured on a copy of the pre-fix `design.py`): guards 20 unguarded drop points; routes court → loggia, garden terrace and lawn broken; 52 lower-wall points with no foundation; 5.5 m² of road floor resting only on glass; riser SH-E 0.21 m² inside each ensuite doorway. All pass after the fix.

### Blockers

| Finding(s) | Fix | Evidence after the fix |
|---|---|---|
| ACS-N01, KB-N01, ROM-N01, FLX-N01 (riser in both ensuite doorways) | SH-E moved to R(11.0, 2.4, 11.4, 3.0) on both floors; ensuite showers shortened to v 2.35 | §7.10: no doorway narrowed by a riser, column or thick wall |
| ACC-N01, LND-N01, INT-N03, ACS-N02, OWN-N01 (garden walk did not connect) | Walk continues on a slab `walk-e` R(15.4, 16.0, 18.0, 17.12) along the loggia's open front, all at 1669.98 | New check §7.23: road → court → 24 steps → walk → loggia → garden terrace → 16 steps → lawn, each link ≥0.9 m at one level |
| SAF-N01, QA-N02, VEH-N03, ACC-N02, SAF-08/09/N02/N03 (guard check could not fail; unguarded drops) | `guards()` rewritten: probes every edge of every walkable surface (roof terrace, green roof, loggia, walk, stairs, courts), adds a guard on every site and retaining wall ≥0.6 m, and an independent finer re-sampling lists anything unguarded. W2 raised as a 0.7 m RC vehicle parapet + rail; W3 and W4 guarded | §7.7: 237 m of guards, 0 drops unguarded |
| QA-N01 (column in the lower WC doorway) | C-6.8/9.5 now starts on wall LW-6.8 at the main floor | §7.10; §7.2b (a column may start on a bearing wall) |
| STR-N01, SEI-N04, QA-N04, OWN-N03 (no beam over the south glazing at road-slab level; checks counted glass as wall) | Beam MB-13.0 (400 × 650, u 2.0–18.0); lintel beams MB-18, MB-1.1N, LB-18E, LB-15.75; `storey_walls()` now cuts every opening ≥1.0 m out of the walls | §7.1: 0 m² unsupported; §7.2: 0 m mid-span |
| GEO-N01, BLD-N01, MAT-N02, THM-N01, WAT-N05, REG-N01, SEI-N02, QA-N03 (pile wall clashed with the house, toe too shallow) | Piles moved to v 0.40 (0.2 m drained cavity to the house wall), toes 1669.0 / 1664.5 / 1665.5, caps stepping with the ground, extended to u 16 | Plans, sections, 3D; §7.12 no window faces a pile wall above its sill |
| CIR-N01 (no stair spine) | 0.15 m RC spine on u 8.1 drawn on every floor; guards and handrails specified | Plans |
| SAF-N04, MEP-N06 (LPG cage in the sunk court) | LPG moved to open air at road level in the north strip; no gas below road level | Road plan |
| KB-N02 (wudu bench blocked the shower door) | Wudu, lobby and WC re-planned: bench and trough v 5.95–7.2, standing basin in the lobby | Main plan; §7.10 |
| ROM-N06, OWN-N02 (living looked down the hall; rule 3.1) | 2.1 m bookcase screen with the TV opposite the hall opening | Main plan |
| STR-N02, 7.2c (lower walls over falling ground had no foundations) | FW-18L, FW-15.75, FW-10.95; LW-15.4 founded at 1668.0; SE corner column C-18/10.95 | New check §7.2c: 0 points |
| VEH-N01 (tyre rack in the shutter opening) | Tyres high on the north wall | Road plan |

### Majors fixed (no owner decision needed)

| Finding(s) | Fix |
|---|---|
| ACS-02, ACS-N03, PRV-N06, CIR-N04 | Accessible WC 1.67 × 2.23 m clear with a Ø1.5 m circle; master and grandparents' doors moved to v 6.2 off the lift wall (0.9 m leaves, pull-side space) |
| CIR-N02 | Bathroom south wall to v 9.8: laundry neck 1.0 m clear |
| KB-N03, ROM-N02, INT-N05 | Lower WC pan moved, door opens inward and its leaf screens the pan |
| MEP-N01, THM-09, FLX-N03, BLD-N06, BRF-10 | Plant room 5.0 × 1.7 m on the grid (store merged), 0.9 m in front of the plant, boiler on its own flue |
| BRF-05 | Workbench 4.1 m along the back wall, bikes hung above |
| VEH-N02 | Shutters re-centred on the car lanes (v 1.40–4.75, 5.35–8.70), roof beam RB-5.05 on the pier |
| VEH-N04 | Refuge with 2 bollards and a sliding gate at the stair head |
| GEO-05, VEH-07 | Forecourt deck extended over v 8.6–11.6 on beams PB-8.6 and PB-W and four piers |
| GEO-N03, MAT-09, STR-07 | Lawn-stair landings and the east part of the walk are RC slabs on walls FW-22.05, FW-3.4L, FW-17.1, FW-11.8 |
| ACC-N04 | Lawn stair widened to 1.45 m on the grid (1.30 m clear) |
| LND-N04 | The pocket under the east balcony is lawn, not a walled sump; garden store on the lawn |
| LND-N03, BLD-N04 | Store wall FW-19.3 removed: one garden store; cistern end wall on the column line v 6.2 |
| LND-04 | Three medium trees on the middle of the bank |
| SUN-N01 | Pergola opened over the whole strip above the loggia |
| SUN-N03 | Balcony screen as obscured glass with a gate (keeps the master's second way out, SAF-N05) |
| SUN-N04, INT-N04 | The "walk-on rooflight" inside the roofed lobby deleted |
| ROM-N04 | Master bed moved off the north wall |
| ROM-N05, KB-N05 | Island with 3 stools at 0.65 m; hob landing kept |
| PRV-N03 | Girls' wardrobes on the lounge wall as the acoustic buffer |
| PRV-N04 | Children's doors re-hinged so beds are not seen from the hall |
| INT-N02, ROM-N03 | Lounge L-sofa re-planned, coffee table clear, sofa facing the TV |
| QA-N05 | Columns 0.35 m; furniture moved off every column (new check in §7.10) |
| WAT-N03 | Lower slabs over the store, cistern and crawl void set down 0.20 m; walk at the loggia's level with a slot channel at the bedroom wall |
| WAT-02, MAT-N04 | South-terrace outlets moved inside the terrace |
| BLD-N03, WAT-13 | Road-level roof: two outlets and an overflow; ladder and anchor line specified |
| STR-N05, MAT-01 | Lower core west wall and the wall under the wet cluster drawn 0.40 m (retaining 3.6 m) |
| STR-N03 | SE corner column at (18.0, 10.95) |
| HLT-N01 | Grandparents' east window added |
| THM-N03, MAT-N01, KB-08, VEH-N08, ACS-06 | Every "note" now written out in `SPECIFICATION.md` |
| OWN-N05 / DRW-03 | East garden measured from the wall face everywhere (147 m²) |

### Not fixed in this round: owner decisions or engineering

Listed on the page under "Your decisions", each with a recommendation:

- whether the uphill walls stay integral or become free-standing (SEI-03, SEI-N01, GEO-N05);
- the front door's position (ROM-N06);
- the gross area measured to the wall faces (REG-N05);
- privacy along the garden walk (PRV-N01);
- the lawn size and the one-level garden (BRF-08, LND-03, Q4);
- the room sizes (BRF-N02);
- the hayat enclosure along the south footpath (BRF-N01, Q7/Q8);
- the main hall length (rule 2.2).

Not fixed and not an owner decision:

- **Engineering:** structure, seismic and soil design.
- **Specification only:** materials, envelope and services are written out in `SPECIFICATION.md` but not drawn.

### Added after the consolidated review (same round)

| Row | Fix |
|---|---|
| C11F-GEO-01 | Pile toes 1666.5 / 1664.5 / 1667.0 and caps 0.2 m under the ground, in five segments |
| C11F-GEO-03 | W2 0.35 m on a common base at 1673.0 with W3 (U-trough in SPECIFICATION.md) |
| C11F-WAT-01 | Hump and slot drain across the road-stair head (water table `rs-head`) |
| C11F-KB-01 | Seated ensuite: true Ø1.5 m circle over the level shower, WC moved to v 3.9 |
| C11F-KB-02 | Wudu bench from v 6.15: a 1.0 m landing at the shower door |
| C11F-SAF-02 | Guard along the green-roof joint u 12.6, v 6.2–7.3 |
| C11F-CIR-01 | Road-level void over the half-landing labelled, guards specified |
| C11F-OPS-01 | Two 0.7 m slim tanks and the booster on the west wall, 0.9 m passage to the bulk store |
