# 15 · Builder review of C11: constructability, cost, maintenance

Prefix BLD. Concept only, not engineered. Heights from the TIN (`inferred`).

## Summary

1. Both C10 blockers are fixed. The garage stands on a dug service room, the lower north wall is on v 1.1, and 0 m² is unsupported.
2. The north pile wall PW-N cannot be built as modelled. Its toe is 0.8 m below formation where it retains 4.3 m, and it overlaps the north walls by 0.225 m.
3. Cost is up. Cut is 228 → 397 m³ and net spoil 104 → 331 m³. Retaining walls are about 130 → 158 m, plus piles, 14 columns and 13 beams.
4. The cistern, garden store, crawl voids and the 133 m² main roof are drawn but have no maintenance design.
5. The plant room is 1.19 m deep inside its walls, and the tanks cannot leave through the 1.0 m front door.

## Scorecard

SCORECARD: fixed=4 partly=9 not_fixed=0 worse=1 new_blocker=1 new_major=5 new_minor=2

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| BLD-01 voids | **fixed** | `measured`: service room under the garage; lower north wall on v 1.1; 0 m² unsupported | None; the dig buys about 43 m² of floor. |
| BLD-02 stacking | **fixed** | `measured`: `wall_over_wall` 0 m; 5 columns on v 13.0 | None. |
| BLD-03 retaining walls | **made worse** | `measured`: basement walls about 50 m, 108 m² retained face; site walls 105 m in 44 segments, 169 m² exposed face; plus PW-N. About 158 m and 275 m², against 130 m and 210 m² | Build the lawn walls (1.0–1.33 m) as gabions, not RC. See N07. |
| BLD-04 slabs on fill | **fixed** | `measured`: worst fill 0.90 m; four slabs suspended | None (voids: N05). |
| BLD-05 north neighbour | **partly fixed** | `measured`: PW-N, Ø450 piles at 0.7 m, u 0–13.2, no anchors | Fix as N01. Extend to u 14.5: the cut is still 1.94 m at u 13.2, 0.85 m from the boundary. |
| BLD-06 sequence and laydown | **partly fixed** | `measured`: sequence is a note; no laydown or haul route | See N02. |
| BLD-07 formwork | **partly fixed** | `measured`: 0.25 m set-downs on straight lines, but still about 9 slab levels; green-roof notch u 11.4–12.6, v 6.2–7.3 (1.3 m²) remains | Square the green roof to u 12.6. Give the balconies the same soffit as t-south. |
| BLD-08 garden route | **partly fixed** | `measured`: store under `t-low`; 24 + 16 risers road → lawn; no wheel channel; FW-12.8T leaves a 0.34 m step at u 19.85–20.8 | Ramp that step at 1:8. Draw a 0.25 m wheel channel on the court stair. Store levels: N04. |
| BLD-09 plant room | **partly fixed** | `measured`: tanks on the ground slab; SH-K, SH-W and SH-E risers; flue up SH-K | See N06. |
| BLD-10 lift | **partly fixed** | `measured`: pit floor 1668.80, tanked; overrun 0.8 m, about 3.85 m clear (enough, `assumption`) | No lifting hook modelled: cast a 1.5 t hook into the overrun slab. Drain: N08. |
| BLD-11 roofs | **partly fixed** | `measured`: 2 outlets + overflow per terrace, set-downs, pavers on pedestals, green-roof gate | Main roof: N03. Outfall still unknown. Anchors at 1.5 m centres on the green roof's north and east edges. |
| BLD-12 opening sizes | **partly fixed** | `measured`: windows 12 → 6 widths (0.6, 0.8, 0.9, 1.2, 1.8, 3.3); exterior sliders 7 → 4 (1.4, 1.8, 2.0, 2.4); one 0.7 m and two 0.75 m leaf doors | Windows 0.8 → 1.2 and 0.9 → 0.6. Dining slider 1.4 → 1.8, kitchen 2.0 → 1.8. WC and shower doors 0.8 m. |
| BLD-13 façades | **partly fixed** | `measured`: north window tilt-and-turn; materials are notes | Cast scaffold ties into the 10.4 m east face. |
| BLD-14 court extension | **fixed** | `measured`: court 40.6 m² + 4.2 m² porch; W1–W4 drawn with levels (31.7 m) | Cast W2 in alternate bays of 2.5 m or less before the stair dig. |

## Part B: new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| BLD-N01 | BLOCKER | PW-N, v 0.85, u 0–13.2 | It fails at u 6.8–9.4, clashes with the north walls, and its cap floats | Deeper toes; piles at v 0.60 as the permanent wall with a lining; stepped cap |
| BLD-N02 | MAJOR | site | Spoil tripled; no route out of an 8 m hole | Crane skip or long reach; draw the laydown |
| BLD-N03 | MAJOR | roof 1680.8, 133 m² | No outlets and no access | 2 outlets + scupper; fixed ladder; anchor line |
| BLD-N04 | MAJOR | under `t-low` | Cistern and store are labels; a column stands in the cistern | Levels, dig, hatch; realign FW-6.2T |
| BLD-N05 | MAJOR | lounge east and loggia voids | Closed voids, 0.23–2.0 m deep | Hatch, drain, vents, lost formwork |
| BLD-N06 | MAJOR | `plant`, `tanks` | Plant room unserviceable; tanks trapped | Shallower equipment; slimline tanks; 1.2 m door |
| BLD-N07 | MINOR | foundations, W3, P-F/11.6 | 15 founding levels; W3 skewed in 6 segments | 5 levels; 2 straight runs |
| BLD-N08 | MINOR | lift-pit drain | Runs through the cistern, shallow under the lawn | Reroute along v 7.0 |

## Part B details

**BLD-N01 (BLOCKER, `measured`; embedment rule is an `assumption`).**
- **Embedment.** The toe is 1668.6 everywhere. At u 6.8 the ground is 1673.66 and the formation 1669.40, so the wall retains 4.26 m (about 4.8 m with the footing). The toe is only 0.8 m below formation; a cantilever wall needs about 1.0–1.5 × the retained height.
- **Clash.** The piles occupy v 0.625–1.075. The north exterior walls of all three floors occupy v 0.85–1.25.
- **Cap.** Level at 1677.0 over ground of 1671.34 at u 13.2: 5.7 m in the air.

Correction:
- Pile centres at v 0.60 (the piles then occupy v 0.375–0.825).
- Make PW-N the permanent wall, with a 50 mm drain composite and a 0.35 m RC lining at v 0.875–1.225. This replaces the separate north wall for u 0–13.2.
- Toes about 1666.5 (u 0–4), 1664.5 (u 4–11.4) and 1667.0 (u 11.4–14.5).
- Cap stepped to ground − 0.3 m.
- About 21 piles, about 190 m of piling, by a specialist (`ai_judgment`).

**BLD-N02 (MAJOR).**
- `measured`: net export 331 m³ in situ is about 430 m³ loose, or about 43 loads of 10 m³.
- Footings, piles, the pit, the cistern and drains are excluded, so the real figure is about 450–480 m³ (`inferred`).
- The lower formation is 8.1 m below the forecourt. The 35% slope is steeper than a dumper can climb (about 25%, `assumption`).

Correction:
- Dig the main pit with a 15 m long-reach excavator from the forecourt.
- Dig the lower pit on 1.5 m benches, lifting the spoil in 2 m³ skips by a 40 t crane on the road (radius about 22 m).
- Laydown and pump stand: forecourt R(−3, 1.1, 0, 11.6).

**BLD-N03 (MAJOR, `measured`).** `WATER` lists 13 surfaces, but not `roof`. The §7.9 pass therefore ignores the biggest roof. It carries the flue, terminals, overrun, rooflights and PV, yet has no ladder or hatch. Correction:
- Falls 1:60 to the west.
- Outlets at (0.4, 1.4) and (0.4, 12.6), down to the forecourt channel. Scupper at (0.0, 7.0).
- A galvanised fixed ladder with a lockable guard on RW-12.6 at v 12.0, up from `deck-r`.
- An anchor line or a 1.1 m parapet.

**BLD-N04 (MAJOR, `measured`).**
- The soffit is about 1669.6 (`inferred`). Ground in the cistern bay is 1668.1–1669.6.
- Holding 10–15 m³ needs a floor at about 1667.7, which is 0.4–1.9 m of cut that the earthworks do not include.
- FW-19.3 splits the bay into two strips about 1.05 m clear.
- C-B/2.75 stands in the cistern. C-B/6.2 is 0.30 m off FW-6.2T (v 6.5).
- There is no hatch.

Correction:
- Cistern R(18.2, 1.3, 20.4, 6.2), floor 1667.7, about 14.5 m³.
- Delete FW-19.3 north of v 6.2, and move FW-6.2T to v 6.2.
- Cast C-B/2.75 monolithically through the tanked base.
- Hatch 0.6 × 0.6 m at (19.3, 3.6).
- Store floor 1667.6 (2.0 m headroom); add its cut to the earthworks.

**BLD-N05 (MAJOR, `measured`).**
- Lounge east void: 0.23–1.3 m (soffit about 1669.63).
- Loggia void: 0.7–2.0 m, closed on all sides.

Correction:
- A sealed hatch 0.6 × 0.8 m at (17.3, 10.4), and a door in FW-16.0.
- Void floors falling 1:50 east to the lawn heel drain.
- Vents with rodent mesh.
- Beam-and-block or precast-plank slabs: forms cannot be struck from a 0.23 m void.

**BLD-N06 (MAJOR, `measured`).**
- The plant room is 1.19 m between wall faces. The 0.8 m equipment block leaves 0.39 m to work in. ROOM-01 asked for a room at least 2.4 m deep.
- The tanks are 2 × about 1.5 m³, about 1.2 m in diameter (`assumption`). Their way out is a 1.0 m front door or the 0.9 m lift door.

Correction:
- Equipment zone no more than 0.6 m deep, with the MVHR on the ceiling.
- Absorb `store-r` into the plant room: R(4.4, 11.6, 9.4, 13.0).
- Tanks no more than 0.75 m wide.
- Front door 1.2 m.

**BLD-N07 (MINOR, `measured`).**
- There are 15 founding levels, 1666.0–1675.0. Rationalise them to 1666.5, 1667.5, 1668.6, 1669.4 and 1673.0.
- Build W3 as 2 straight runs.
- Found P-F/11.6 on W1.

**BLD-N08 (MINOR, `inferred`).** A drain due east crosses the cistern. Under the lawn it has 0.4–0.6 m of cover, against an assumed frost depth of 0.8–1.0 m. Correction:
- Route it along v 7.0 through the store, falling 1:12 to about 1667.0.
- Outfall at the toe of SW-33 (about 1666.4) with a flap valve.

## What C11 gets right

- Every slab has a drawn support (0 m² unsupported). The garage sits on a usable room.
- One structure list feeds the plans, sections and 3D, with founding levels a contractor can price.
- Fill under ground slabs is no more than 0.90 m, and total fill is down 47%.
- The tanks are on the ground, and every wet room is within 4.5 m of a riser.

## Out-of-scope notes

- Structure: W2 under traffic, with no heel; 12.2 m columns; 5 transfer beams. Engineer.
- Safety: no guard on the green roof's north and east edges.
