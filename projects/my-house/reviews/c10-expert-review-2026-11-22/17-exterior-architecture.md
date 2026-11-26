# 17 · Exterior architecture review of C10

Concept stage; nothing is permit-ready or code-checked. Heights: `zg()` on the 27-point TIN (inferred). `U_BEARING` 67.2°: "east" faces ENE, "south" faces SSE (157°).

## Summary

1. C10 steps properly to the south (lower floor to v 16.4, main floor to v 13.0). To the east it barely steps: main u 17.8 vs lower u 18.0. The SE corner is sheer for 11.1 m, and the lawn to the road roof is 13.2 m.
2. The street sees two shutters and a door on an open triangle. There is no pedestrian gate and no walled *hayat*, which contradicts the owner's own description.
3. A 2.4–4.2 m void under the master's north strip reads as "box on stilts".
4. Openings are uncomposed: five widths, 0.3–0.4 m piers, no alignment, low heads.
5. Concrete walls, glass guards, a bare jagged roof. Stone terracing and solid parapets (the Hawraman idiom) fix most of this.

## Findings

| ID | Sev. | Where | Issue |
|---|---|---|---|
| EXT-01 | MAJOR | Road `fore`, west façade u 0 | No gated *hayat*, no pedestrian gate, stair head open to the road |
| EXT-02 | MAJOR | East elevation u 17.8–20.6 | Main and lower floors flush; 11.1 m sheer SE corner |
| EXT-03 | MAJOR | Main `master`/`balc-m`, u 14.2–19.4, v 1.1–2.8 | Open undercroft 2.4–4.2 m high |
| EXT-04 | MAJOR | East and south walls | Window widths, piers and heads not composed |
| EXT-05 | MAJOR | `t-low`, `lawn`, SE plinth, `court-w`, `fore` | Retaining walls and exposed foundations are blank concrete |
| EXT-06 | MAJOR | All terrace edges (~55 m, inferred) | Frameless glass on every edge |
| EXT-07 | MAJOR | Road-block roof 1680.80 | Fifth façade undesigned; no parapet, overrun or plant zone |
| EXT-08 | MAJOR | Main south v 13.0; lower south v 16.4 | No sun overhangs on the SSE façade |
| EXT-09 | MINOR | Road block, south and east faces | Jogged walls not sitting on the walls below |
| EXT-10 | MINOR | `hall-r` street door | Door 0.25 m from corner; no canopy or address zone |
| EXT-11 | MINOR | Whole house | No material concept; no regional character |

## Finding details

**EXT-01 (MAJOR).** The owner said (brief, round 23): *"There's a door for the garage … And there's a door beside it. You open it. You're in a perimeter where you can then, with some stairs, go down."* The interview summary also records "separate vehicle and pedestrian gates" (still an inference awaiting confirmation).

Measured in C10:
- The forecourt is a 36 m² open triangle. The west boundary runs along u = −0.547 v, so the apron is 1.8 m deep in front of shutter 1 and 4.0 m in front of shutter 2.
- `gstair` leaves the forecourt at v 11.6 with no gate.
- The road façade is 10.5 × 3.3 m, 64% of it shutter, with no windows.

Correction:
- The apron is too shallow for a separate vehicle gate, so the two 3.35 m shutters are the vehicle gates.
- Build a stone street wall on the west boundary from v 11.6 to 17.42: 1.0 m solid plus a 0.8 m brick or steel lattice (top ≈ 1679.2).
- Put a 1.2 m pedestrian gate beside the garage at the stair head, under a 1.2 m canopy, with a 1.5 × 1.5 m landing at 1677.40 before the first riser.
- The enlarged court at 1673.60 (rule 4.10) becomes the walled *hayat*.

**EXT-02 (MAJOR).** Measured heights (m):

| Level | Height |
|---|---|
| Tree bank at the lawn edge | 1666.3 |
| Lawn | 1667.60 |
| Garden terrace | 1669.98 |
| Deck guard top | ≈ 1678.6 |
| Road roof | 1680.80 (no parapet modelled) |

- Lawn to road roof: **13.2 m** (13.7 m with a 0.5 m parapet).
- At the SE corner, ground is 1667.48. Above it stand a 2.5 m plinth, then 3.6 m, then 3.9 m, then a 1.1 m guard: **11.1 m sheer**.
- The only east step is road → main floor, 5.6 m. Pulling the main floor back would break rule 3.3, because the living room is 5.2 m wide.

So make the tiers read through construction instead:
- (a) Lower floor, plinth and terrace wall become one stone base up to 1673.3.
- (b) The main floor is lime-rendered behind a 1.2 m slab or pergola at about 1677.2 over `balc-e` (v 6.2–16.4), so the balcony becomes a shaded *ayvan*-like porch.
- (c) The road block stays set back.


**EXT-03 (MAJOR).** The lower floor starts at v 2.8, but `master` and `balc-m` run to v 1.1. Under the main soffit (1673.3), measured clearance is 2.36 m at u 14.2, 3.7 m at u 18.0 and 4.2 m at u 19.4. Visible to the north neighbour.

Correction: build a stone-faced wall on v 1.1 from u 11.4 to 18.0, top 1673.3. Enclose u 14.2–18.0 × v 1.1–2.8 (≈ 6.5 m²) as a store or part of the guest room. Return the wall at u 18.0 to carry `balc-m`.

**EXT-04 (MAJOR).** Measured:
- **Main east openings:** 2.4, 0.8, 1.9, 2.8 and 0.6 m wide, with piers of 0.4, 0.9, 0.4 and 0.3 m.
- **Living vs lounge sliders:** centres at v 10.4 and 9.45.
- **Master slider vs guest openings:** centre v 3.4 vs 3.7 and 5.6.
- **Heads (`model3d`):** 2.2–2.3 m, leaving blank bands of 1.6 m (main) and 1.3 m (lower).

Correction:
- Use only two opening types: 2.4–3.0 m sliders and 1.0 m vertical windows.
- Piers at least 0.9 m (Standard 2800 practice; assumption).
- Heads at 2.7 m (main) and 2.5 m (lower).
- **Shared east centreline at v 3.9:** master slider v 2.7–5.1 over guest slider v 2.9–4.9, replacing both guest openings.
- **Shared east centreline at v 10.0:** living slider v 8.6–11.4 over lounge slider v 8.5–11.5.
- Delete the 0.6 m sliver at v 12.1–12.7.
- **South:** merge u 12.8–14.8 and 15.2–17.3 into one 3.0 m slider plus a 1.0 m window. Keep piers of at least 0.9 m at the partitions (u 4.6, 9.2, 12.6).

**EXT-05 (MAJOR).** Visible concrete, measured:

| Wall | Size |
|---|---|
| `t-low` wall at u 20.6 | 8.8 m long, 2.38 m above the lawn |
| Lawn edge (u + 0.448v = 28.5) | ≈ 17 m long, 1.2–1.3 m high |
| Plinth along v 16.4, u 13–18 | 0.85–2.5 m |
| Forecourt | on up to 3.0 m of fill |
| Court north face, v 11.6 | 3.8 m |

Correction:
- Face every retaining wall in one coursed local stone, battered about 1:10, with a stone coping.
- `t-low`: either 1.6 m wall plus a 0.8 m planted step (costs ≈ 5 m² of lawn), or a single 2.4 m wall with planting pockets.
- Build `gs-lawn` as a solid stone stair inside the wall line.
- Run the court stair down along the road wall, so a 3.8 m face becomes a stepped bank. This is the Palangan device (ai_judgment).
- Hold the stone base to one datum (1670.0 east and south) so it reads as a level line.

**EXT-06 (MAJOR).** There is 1.05 m glass on every free edge: south terrace 13.2 m, balconies ≈ 17 m, deck ≈ 13 m, garden terrace ≈ 10 m. From the shared south footpath (ground 1667–1671) people look up into the kitchen terrace (1673.58). Glass also streaks in snow and dust.

Correction (heights are assumptions):
- **South terrace edge:** 1.1 m solid parapet with a 0.45 m planter.
- **East balconies:** 0.3 m upstand plus a 0.8 m steel flat-bar rail, which keeps the view.
- **Deck south and east edges:** 1.1 m solid.
- **Garden terrace:** 0.5 m stone plus a rail.
- **New guards:** at the forecourt's 3.8 m drop into the court (u −1.2–0, v 11.6), and on the court's south edge (up to 1.8 m above the falling ground).

**EXT-07 (MAJOR).** The road-block roof covers ≈ 126 m² at 1680.80, with a 0.12 m eave, no parapet and about 12 corners. No lift overrun is modelled; with a 3.3 m storey, a machine-room-less lift likely needs 0.3–0.8 m above the roof (assumption; confirm with the supplier). The roof is seen from upslope and from the deck. The main roof (≈ 81 m²) is seen from the road's south half and the court.

Correction:
- Rectangular outline, u 0–12.2 × v 1.1–13.0.
- 0.5 m parapet (top ≈ 1681.3) with external scuppers and downpipes, which do not freeze.
- Gravel or green finish.
- One plant zone over the core (u 6.8–11.4, v 1.1–7.3) behind a 1.2 m louvre, for the overrun, solar heaters and antennas.

**EXT-08 (MAJOR).** The REPORT gives noon sun at 78.5° (June) and 31.6° (December). On a 157° façade the profile angles are about 79° and 34°. About 8 m of main south glazing has no overhang.

Correction:
- A 1.0 m slab or pergola at about 1677.2 over v 13.0–14.0, u 4.6–17.8. It shades a 2.7 m opening at summer noon (needs ≥ 0.66 m); in December the shadow edge falls only 0.67 m, so the glass is fully sunlit.
- Extend the south terrace slab lip 0.6 m to v 17.0 (inside the setback at 17.42) over the children's windows (needs ≥ 0.44 m).
- On the ENE façade, low morning sun defeats overhangs: use external sliding timber shutters on the master and living sliders.

**EXT-09 (MINOR).** Road-block south faces sit at v 11.6, 12.6 and 13.3. `plant` and `wc-r` project 0.3 m past the main south wall (v 13.0) over u 3.4–9.0. East faces sit at u 11.4 and 12.2.

Correction: one south plane at v 13.0 (u 3.4–12.2) and one east plane at u 12.2 (v 5.0–13.0, lobby +1.8 m²), each landing on a wall below.

**EXT-10 (MINOR).** The door at v 10.15–11.35 leaves a 0.25 m return to the corner.

Correction:
- A 1.0 m leaf at v 10.1–11.1.
- A 1.2 m canopy over the door and the gate.
- One lit address/intercom panel.
- Shutters in vertical timber slats, so the shutter-heavy wall reads as wall.

**EXT-11 (MINOR, ai_judgment).** Hawraman villages (Palangan, Uraman Takht) build in stone wherever earth is held, use flat roofs that serve as the yard of the house above, deep-set vertical openings, and timber balconies and lattices. The owner wants "a mixture more towards modern" (round 15), so this is a palette, not pastiche. Use four materials only:
- Local limestone for the base, walls and street wall.
- Off-white lime render for the main floor.
- Timber for shutters, pergolas and the road-block east face.
- Dark steel for rails.


## What C10 gets right

- It genuinely steps to the south, with the south terrace on the lower roof.
- The main roof becomes the road deck plus a closed green roof over the master: the Palangan roof-as-yard move.
- The road block is low (3.3 m) and modest toward the street.
- The 1.6 m east balcony already shades the lower east glazing.
- The road hall bridging the court (u 0–2, v 9.6–11.6, 3.6 m clear) gives a covered entry porch; keep it.
- Day rooms and bedrooms take the open south and east; the buried NW needs no façade.

## Out-of-scope notes

- Structure: check the EXT-08 overhang, the `balc-e` pergola and the EXT-03 wall. The 0.3 m road-block projection (EXT-09) sits on no wall.
- Drainage: the stone walls need drainage behind them, and the court needs falls and an outlet.
- Court stair geometry belongs to the stair reviewer (rules 4.10, 4.11).
