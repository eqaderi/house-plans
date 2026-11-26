# 19 · Vehicles, garage, road interface (C11 review)

## Summary

1. The garage bands, aisle and fire door are now in `design.py`, but three things are wrong as drawn: the tyre rack stands **inside shutter 1's opening**, the LC300 is **0.225 m from the pier**, and the aisle is **1.135 m** clear at the RC core.
2. The road stair drops to 1675.50, 0.30 m from the road. That leaves a **2.0–2.07 m drop beside the road with no parapet**: W2's top is 1677.45, below the road edge.
3. The stair head has **no landing**: the first nosing is 0.16–0.93 m past the vehicle forecourt.
4. The forecourt deck removes the deep fill. But a diagonal deck/fill joint crosses the bay-2 wheel path, and no vehicle load class is set.
5. Most specifications (fire-door rating, operator, coil box, mirror, CO, stop bay) exist only as claims in CORRECTIONS.md, in no drawing or note (grep, `measured`).

## Scorecard

SCORECARD: fixed=0 partly=9 not_fixed=2 worse=0 new_blocker=2 new_major=3 new_minor=4

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| VEH-01 aisle | partly fixed | `measured`: cars at u ≤5.54 and bikes on the back wall, so the walk is clear. But the 0.25 m RC core face is at u 6.675 for v 1.25–7.3, so the aisle is 1.135 m. §7.10 tests a drawn rectangle and ignores walls and `dash` items. | N06 |
| VEH-02 bay 1 blind | partly fixed | Façade, north wall and parcel corner are unchanged, so north sight stays 3.0 / 6.5 m. LC300 in bay 2 and reverse-in are drawn. Mirror and camera are only claimed. | Bay 1 for the smaller car; convex mirror (consent `unknown`) and camera; amber exit-warning light on the north jamb, triggered by a loop in bay 1. |
| VEH-03 skew | partly fixed | §4 kept two shutters plus reverse-in (3.1–3.3 m of road). C11 then used my single-opening bay centres (3.14 / 6.89) against shutter centres 3.25 / 7.35. | N02 |
| VEH-04 shallow forecourt | not fixed | Stop bay not drawn. CORRECTIONS.md says it "needs road consent", but all four corners are inside the parcel. No operator spec. | Stop bay shortened to 5.2 m: (−2.22, 4.48) (−4.72, 9.05) (−2.79, 10.11) (−0.29, 5.54). Wholly on the ground part; clears N04. Operator ≥0.2 m/s with a remote. |
| VEH-05 bench / bumper | partly fixed | `measured`: tail to bench 0.96 m; nose 0.40 m from the curtain (C10: 0.20). Bench 1.9 m (asked 2.1). Tyre rack misplaced (N01). No wheel stops, RCD or fuel cabinet anywhere. | N01, N08 |
| VEH-06 apron, water | partly fixed | The forecourt is at 1677.47 and falls west. Road edge (TIN, `inferred`): 1677.33–1677.38 at v 3.25–7.35, but **1677.46–1677.51 at v 9.5–11.6**, level with or above the 1677.47 door threshold. The only overflow, (−3.4, 9.0), is inside the forecourt, so a channel blocked by snow overflows to the front door and shutter 2. §7.9b is open. | Until the road survey (Q6): a 50 mm crest at the boundary for v 8.5–11.6 (top 1677.56), the channel inside it, a DN150 overflow piped to the court outfall, and the oil interceptor located (~(−1.0, 7.0), under the deck). |
| VEH-07 drop and fill | partly fixed | Fill solved: ≤1.07 m below the 0.6 m build-up on the ground part; the deep wedge is now a 9.9 m² deck (`measured`). A 1.1 m guard is drawn. But **RW-W1's top is 1677.47: the 0.6 m upstand and the bollards are text only.** | RW-W1 top 1678.07, designed for car impact (assumption ~150 kN at 0.5 m; engineer); bollards per N04. |
| VEH-08 gates | partly fixed | The gate is a text label; the "W2 raised" street wall is a note (element top 1677.45). Q7 open. | N03, N04 |
| VEH-09 fire door | partly fixed | The `fire` door at u 6.8, v 8.35–9.35 swings into the garage, clear of SH-W (0.30 m) and the LC300 (0.47 m). The glazed stair screen is drawn. A 1.0 m leaf gives ~0.90 m clear (`inferred`). Rating, seals, closer, opener, CO and extract appear nowhere. | 1.1 m leaf; EI 60-S (assumption, INBR Part 3); self-closing; opener released by the fire alarm; step-free with a 10 mm spill lip; CO alarm; extract 20 / 150 l/s; on the road plan (N08). |
| VEH-10 shutter heads | not fixed | No spec. Geometry allows it (`inferred`): head 1680.00, coil box to ~1680.45, soffit ~1680.55. RB-5.3 lands between the boxes. | Upstand lintel, coil box ≤0.45 m, manual crank or battery, wind locks. |
| VEH-11 EV | partly fixed | Box at (6.72, 5.0) on the core face (6.675). A real box ~0.15 m deep leaves the aisle ~0.98 m. No cable or circuit. | Move to the pier's inside face (0.15, 5.3), 1.2 m high, with a bollard; a 7.5 m cable reaches both noses; 3-phase 32 A conduit. |

## Part B: new problems

| ID | Sev. | Where | Finding | Correction |
|---|---|---|---|---|
| VEH-N01 | BLOCKER | road `garage` u 0.2–0.5, v 1.2–4.4 | Tyre rack inside shutter 1's opening (v 1.575–4.925) | North wall, high level |
| VEH-N02 | MAJOR | shutter 2 / bay 2 | LC300 v 5.90–7.88 in an opening at v 5.675–9.025: 0.225 m to the pier | Openings and pier 0.2–0.3 m north |
| VEH-N03 | BLOCKER | road edge v 11.6–17.27, W2 | 2.0–2.07 m drop to the stair, 0.30 m from the road, no parapet | Vehicle parapet plus open railing; nothing solid in the splay |
| VEH-N04 | MAJOR | stair head u −6.0…−4.4, v 11.6 | No landing; gate cannot swing; top step on the vehicle forecourt | Pedestrian refuge, bollards, sliding gate |
| VEH-N05 | MAJOR | `fore` / `fore-deck`, PB-F | Deck/fill joint in the wheel path; no load class; laydown on the deck | Load class, hinged transition slab, sequence |
| VEH-N06 | MINOR | aisle, §7.10 | 1.135 m at the real wall; the check ignores walls and `dash` items | Cars 0.07 m west; fix the check |
| VEH-N07 | MINOR | u 0–2.4, v 0.05–1.05 | Bins on a 45% slope, 0.4–1.5 m below the road, over the PW-N piles | Level shelf at 1677.45 |
| VEH-N08 | MINOR | road plan | The claimed "notes" do not exist | One spec block on the plan |
| VEH-N09 | MINOR | SH-W R(4.75, 8.84, 5.5, 9.44) | Crosses the garage fire separation; no fire-stopping, no kerb | EI 60 shaft, collars and dampers, 150 mm kerb |

## Part B details

**VEH-N01.** Line 154 draws `rect(0.2, 1.2, 0.5, 4.4)` "TYRES" (`measured`), across 2.83 m of the 3.35 m opening.
- At floor level it blocks car 1. At head level it clashes with the coil box (u 0.15–0.60).
- CORRECTIONS.md says "north wall", which is false.
- Fix: rack at u 1.0–3.4, v 1.25–1.60, base ≥1.95 m above FFL, for 8 tyres.
- New check: u 0.15–0.65 behind every opening stays free.

**VEH-N02.** Bay 2 (`measured`):
- The LC300 is 0.225 m from the pier and 1.145 m from the south jamb; with mirrors (~2.2 m wide, `inferred`) about 0.12 m from the pier.
- A driver reversing in on a skew centres on the opening (7.35). That puts the car at v 6.36–8.34 and cuts the driver-door/bench zone to 0.50 m.

Fix:
- Shutter 1 at v 1.40–4.75, pier at v 4.75–5.35 (0.60 m), shutter 2 at v 5.35–8.70; RB-5.3 to v 5.05.
- Gaps become 0.55 / 0.82 m (LC300) and 0.75 / 0.62 m (car 1), with 0.15 m of guide room at the north jamb.
- The engineer confirms the pier.

**VEH-N03 (unsafe).** Levels: F1 runs 1677.47 → 1675.50 and L1 is at 1675.50, both 0.30 m from the boundary. The road edge is at 1677.51–1677.57 (`inferred`). W2's top is 1677.45.

Why the checker misses it:
- `checks.guards()` tests only walkable terraces. From the stair side the road is higher, so no guard is drawn.
- Its `missing` list is never filled, so §7.7 cannot fail.
- If the carriageway reaches the boundary (F6 `unknown`), a wheel or a pedestrian drops 2 m onto the stair.

Fix:
- An RC parapet 0.70 m above the road edge (~1678.25), designed for vehicle impact (assumption; road authority).
- Above it, an open railing (≥70% open) to 1.1 m above the nosings.
- Do **not** build ARR-05's solid 1.0 m stone plus 0.8 m lattice here. W2 lies in the south sight splay of every car leaving the forecourt: the eye-to-car line for 25 m crosses the boundary ~12–14 m south.

**VEH-N04.** `rs-head` gives 0.16 m (road side) to 0.93 m (court side) before the first riser (`measured`). The step is skewed 28.7°, at the edge where cars turn south out of bay 2. ARR-05's 1.5 × 1.5 m landing is missing.

Fix:
- A flush, distinctly paved refuge between boundary offsets 0.30 and 1.90 m, for v 10.0–11.6 (east edge (−3.31, 10.0)–(−4.19, 11.6)).
- Two Ø200 bollards, 1.0 m high, at (−3.45, 10.3) and (−4.05, 11.3).
- A 1.2 m sliding gate on v 11.6, between W2 and W3.
- Verify against the bay-2 swept path.

**VEH-N05.** PB-F runs from (−0.2, 5.6) to (−3.1, 11.6). East of it is the deck; west of it is slab on ≤1.07 m of fill (`measured`). The joint crosses the bay-2 entry and the door approach, and settling fill steps the wheel path (`ai_judgment`). The forecourt is open to vans, water tankers and LPG trucks, and GEO-05 plans laydown and a boom pump there.

Fix:
- Design the deck, PB-F and the piers for vehicles ≤16 t (assumption ~5 kPa plus a 90 kN axle; Iranian code governs).
- A 3.0 m × 200 mm RC transition slab hinged on PB-F over fill compacted to 95% MDD.
- No laydown or outriggers on the deck for 28 days.
- Or GEO-02's preferred form: a full deck on a pier line 0.5 m inside the boundary.

**VEH-N06.** Fix: LC300 at u 0.495–5.475. §7.10 subtracts walls and all furniture, `dash` items included.

**VEH-N07.** Ground under the bins is 1677.03–1675.99 (`gm.finished`). Fix:
- A shelf R(0, 0.05, 2.4, 0.85) at 1677.45 on the pile cap, falling 2% west, with a 1.1 m guard on its east end.
- On collection day the bins stand south of shutter 2, never at the NW corner (bay 1's only north view).

**VEH-N08.** A grep for upstand, bollard, mirror, camera, operator, CO, self-closing, wheel stop and stop bay finds only two plan labels. Fix: a numbered note block on the road plan with the Part A figures.

**VEH-N09.** Fix:
- EI 60 shaft (assumption) with intumescent collars and fire dampers at the garage slab, the fire separation to `hall` below.
- No garage-side openings.
- A 150 mm kerb at v 8.70, u 4.65–5.60.

## What C11 gets right

- The garage stands wholly on the service room walls (0 m² unsupported) and stays level with the road.
- The 1.2 m (nominal) aisle ends at the fire door, ~4.3 m from the lift, and the door swings clear of the riser and the LC300.
- Reverse-in parking with the LC300 in bay 2. Door zones are 0.90 / 1.77 / 0.96 m, and the nose sits 0.40 m from the curtain.
- The glazed, self-closing stair screen keeps fumes out of the stair (rule 2.4).
- The 3 m fill wedge has become a pier-supported deck.

## Out-of-scope notes

- Structure: P-F/11.6 sits on W1's line, so confirm one footing.
- QA: rule 5.1 route is 3.6 m in `checks.json` but 4.4 m in the road notes.
