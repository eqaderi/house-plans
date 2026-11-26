# C11 review 03: geotechnics and earthworks

Concept stage; nothing here is geotechnically verified. Heights come from the 27-point TIN (`inferred`). `measured` means I computed it myself with `zg` / `GroundModel` on a 0.1 m grid from `design.py`. Soil parameters are `assumption`.

## Summary

1. Every slab now has a support. Under-slab fill is ≤0.91 m on the lower floor and ≤0.38 m on the main floor (`measured`), and the deepest cut to formation is 4.22 m.
2. As drawn, the north pile wall PW-N would not stand. At u 6.8–13.2 its toe is 0.8 m below a dig that retains 1.9–4.3 m. It also stops short at u 13.2 and clashes with the house wall.
3. Two soil ribs are still trapped between walls: the road stair (W2 and W3, 1.7 m apart) and the lawn stair (on 2.0 m of fill, with 2.4 m walls on the bank crest).
4. The house is a three-sided retaining box (4.47 m on the west with traffic, 4.22 m on the north) with integral walls. Sliding and global stability are not shown.
5. The earthworks figures leave out stairs, footings, piles and sub-bases. The dig sequence never reaches the owner's pages.

## Scorecard

`SCORECARD: fixed=3 partly=8 not_fixed=0 worse=0 new_blocker=1 new_major=4 new_minor=2`

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| GEO-01 slabs over air | **fixed** | `measured`:<br>- Main pit dug to 1673.00 under the whole garage; fill ≤0.38 m.<br>- Lower north wall on v 1.1.<br>- Lower-slab fill ≤0.91 m; lounge east suspended.<br>- Loggia on FW-16.0, FW-13.4 and RC-18L.<br>- 0 m² unsupported. | Footing depths: see N04. |
| GEO-02 court stair | **fixed** | `measured`: 24 × 150/340 mm. Cut ≤0.51 m and fill ≤0.29 m along the whole flight. | — |
| GEO-03 north dig | **partly** | PW-N is drawn: Ø450 at 0.7 m, toe 1668.6. | See N01. |
| GEO-04 trapped soil, west walls | **partly** | The double north wall is gone. The core wall on u 6.8 and the lower west wall on u 4.6 still retain 3.6 m (1673.0 → 1669.4), with main-floor footings 0–3 m away. They are drawn only as "integral, engineer designs". | Note on the drawings: basement walls propped by both slabs; no backfill or load before the main slab is cast; built in bays ≤3 m. |
| GEO-05 forecourt | **partly** | The deck is only 9.9 m². `measured`:<br>- The rest is a 20 m³ fill wedge, max 1.63 m, with 8.4 m² deeper than 1.0 m at u −4.2…−0.1, v 3.7–11.5.<br>- It sits on a 52% bank: 1677.27 → 1674.99 in 4.4 m at v 8.6.<br>- Car loads bear behind W1 (3.87 m) and MW-0F (4.47 m).<br>- P-F/11.6 sits on W1's line, 1.5 m above W1's base. | Extend the deck over v 8.6–11.6 (about +10 m²) from W1 to PB-F to u 0, and delete P-F/11.6. Draw the benching (≥1.5 m wide, ≤0.5 m high), 200 mm layers at 95% MDD, and geogrid. |
| GEO-06 lower cut and fill | **partly** | Fill ≤0.91 m (fixed). The lower perimeter footings have no levels. The rock-in-the-NW / soil-in-the-SE question (piers or a joint near u 13) is not addressed. | N04, plus a note on that question. |
| GEO-07 terrace and lawn fills | **partly** | `t-low` is suspended on FW-20.6 at 1666.5 (cover ≥0.66 m). Lawn fill ≤1.31 m and SW-33 ≤1.33 m (`measured`). The wall type (gabion or reinforced soil), the base ≥1.0 m down and the toe ≥1.5 m back from the bank face are not shown. The lawn stair adds a new fill (N03). | Draw the lawn walls as gabion or reinforced soil, base ≤1666.6, toe ≥1.5 m back from the bank face, heel drain. |
| GEO-08 owner (b) | **fixed** | The court stair starts at u −0.4 on natural ground at 1673.61; treads stay within ±0.5 m of natural ground. | — |
| GEO-09 owner (a) | **partly** | `measured`: cut 32.4 m³ (max 2.76 m), fill 7.5 m³. Walls: W1 3.87 m, W3 ≤2.79 m, W2 ≤1.92 m, W4 ≤2.23 m. No road-side shoring is drawn. The road stair forms a soil rib (N02). | Draw soldier piles along the road edge, installed before any digging west of u −3. |
| GEO-10 drainage | **partly** | The `WATER` table and the lift-pit gravity drain exist. The WAT-04 footing drain, stone blanket and outfall spreader exist only as text, not in `design.py` or the sections. | Model a footing drain (invert ≤1668.9) behind the north wall and the u 6.8 / u 4.6 walls, the catch pit at (18.6, 13.0), and the outfall to the spreader ≥3 m from the east boundary. |
| GEO-11 spoil and sequence | **partly** | 397 m³ cut and 66 m³ fill are reported. Missing:<br>- stairs (+7 m³ cut, +5.4 m³ fill);<br>- footings (~45 m³, `assumption`);<br>- pile arisings (~27 m³);<br>- the lift pit (~7 m³);<br>- sub-bases (~14 m³).<br>The sequence is in `CORRECTIONS.md` only, not in `index.html`. | Report about 500 m³ in situ (about 650 m³ loose, about 55 loads of 12 m³) and about 110 m³ of fill. Put the 7-step sequence on the owner page. |

## Part B: new problems

| ID | Sev. | Where | Finding | Correction |
|---|---|---|---|---|
| GEO-N01 | BLOCKER | PW-N, v 0.85 | Toe too shallow; ends at u 13.2; overlaps the house wall; top drawn in the air | Deepen, extend, offset, step the cap |
| GEO-N02 | MAJOR | road stair W2/W3/W4 | 1.4 m soil rib between walls 1.7 m apart; W4 modelled 1.8 m too low | One RC U-trough; raise W4 |
| GEO-N03 | MAJOR | lawn stair R(20.6, 3.4, 21.8, 10.28) | On ≤1.99 m of fill (9.4 m³, unreported); 2.2–2.4 m walls 1.2 m from FW-20.6 | Suspended RC flight |
| GEO-N04 | MAJOR | lower perimeter, loggia | No footing levels for the storey walls; FW-16.0 and FW-13.4 have 0.15 / 0.36 m of cover at u 18 | Set the levels below |
| GEO-N05 | MAJOR | whole house | Integral walls retain on two sides with the downhill side open; sliding not shown | Separate the retaining walls, or add keys; analysis |
| GEO-N06 | MINOR | court SE, R(2.0, 13.0, 4.6, 16.0) | Fill ≤1.53 m surcharges the 4.2 m wall on u 4.6 | Engineered fill, or a suspended slab |
| GEO-N07 | MINOR | garden walk, SW-29 | Fill 1.75 m (agreed ≤1.7 m); wall 0.30 m from the setback | L-wall with its heel under the walk |

## Part B details

**GEO-N01: north pile wall.** `measured`, retained height to formation and toe depth below it:

| u | 0 | 3.3 | 6.8 | 9.9 | 13.2 | 15 |
|---|---|---|---|---|---|---|
| Retained (m) | 4.22 | 2.31 | 4.26 | 3.15 | 1.94 | 1.28, no piles |
| Toe below formation (m) | 4.4 | 4.4 | 0.8 | 0.8 | 0.8 | — |

Why it fails:
- With no anchors allowed, the piles stand as a cantilever during the dig. A toe 0.8 m below a 4.26 m face, which is level with the footing base, rotates into the pit.
- The piles occupy v 0.625–1.075 and the house wall's outer face is at v 0.85: they overlap by 0.225 m, with no room for drainage or membrane.
- The element's top is 1677.0 along the whole length. Sections D–D and F–F show the wall 4–5.7 m above the ground east of u 7.

Fix:
- Toe ≤1664.5 at u 6.8–11, embedment ≥1.2 × retained height (`assumption`, to be sized after boreholes); ≤1666.5 at u 13.
- Extend the wall to u 16.
- Pile centres on v 0.55.
- Cap 0.2 m below the ground: 1677.0 at u 0, 1673.5 at u 6.8, 1671.1 at u 13.2, 1670.2 at u 16.
- Or leave a 1:1 berm against the piles and remove it in bays ≤1.5 m wide while the propped wall is cast.

**GEO-N02: road stair rib.**
- W2 is founded at 1675.0 and W3 at 1673.0, 1.725 m apart. W2's footing sits in W3's active wedge, and the spacing is under the agreed 2.4 m.
- RW-W4's top is 1675.6, but the ground behind L1 at (−9.1, 17.3) is 1677.40 (`measured`).
- Fix: cast W2, W3 and the stair slab as one RC U-trough founded at 1673.0. W4 becomes an L-wall with its toe north, its top at 1677.45 west of u −6.5, and no footing south of v 17.42.

**GEO-N03: lawn stair.**
- Natural ground is 1668.11 at (21.8, 3.4) and 1667.19 at (21.8, 10.28) (`measured`).
- The fill is 9.4 m³, up to 1.99 m deep. `earthworks()` skips every stair region, so it is unreported.
- It breaks C11-STR-07 and the 2.4 m wall spacing: FW-20.6 (3.48 m) is 1.2 m from SW-20/21/23 on the 35% crest.
- Fix: an RC flight spanning from FW-20.6 to a new wall on u 21.8, founded at 1667.3 → 1666.4, with a void and no fill.

**GEO-N04: footing levels** (frost ≥0.8 m `assumption`; steps ≤0.5 m).
- `measured` natural ground: 1669.59 → 1668.33 along u 18, and 1669.91 → 1668.46 along v 15.75. Formation is 1669.40.
- Buried north and west walls: 1668.9.
- East wall: 1668.8 → 1667.5.
- South wall: 1668.6 at u 6.8, stepping to 1667.6 at u 15.4, below the walk fill.
- LW-15.4: 1667.6.
- FW-16.0 and FW-13.4: 1666.7 at u 18.

**GEO-N05: the house as a retaining structure.**
- What it holds: MW-0F 4.47 m (forecourt and traffic); the north wall 4.22 m at u 0, tapering to 0; the u 6.8 and u 4.6 walls 3.6 m each.
- Order of magnitude (`assumption`: γ 19 kN/m³, K0 0.5, 10 kPa traffic, ΔK_AE 0.3, base shear 0.15–0.2 W, W ≈ 5.6 MN, friction 0.5):
  - the west face alone gives about 1.0 MN static plus 0.5 MN seismic;
  - with the house's own inertia, the factor against sliding in an earthquake is about 1.1, before passive resistance.
- Fix:
  - Take STR-09 option A: PW-N and the extended forecourt deck carry the earth and traffic, with a 0.6 m drained gap to the house.
  - Otherwise, shear keys or rock sockets under the lower east footings.
  - Either way, a global stability check after boreholes.

**GEO-N06.** Court SE fill up to 1.53 m (2.6 m² deeper than 1 m). Use granular fill in 200 mm layers, and design the wall on u 4.6 for it plus 5 kPa. Or suspend the slab between u 4.6 and a wall on u 2.0.

**GEO-N07.** Garden walk fill up to 1.75 m at (15.4, 17.1). Make SW-29 an L-wall with its heel under the walk and a toe ≤0.25 m, or span the walk from the lower south footing to SW-29.

## What C11 gets right

- Every slab has a support, and fill under ground-bearing slabs is ≤1.0 m (`measured`). This answers stmt-027.
- The lower north wall on v 1.1 ends the trapped soil, and the cut stays at 4.22 m, inside the ~4.5 m limit.
- The court stair follows natural ground within ±0.5 m: easy, with no fill and no trench.
- `t-low` is suspended on FW-20.6, removing about 39 m³ of wet fill.
- The ground model derives every site wall with its real levels; the sections are at true scale.

## Out-of-scope notes

- Arrival court: 40.6 m² plus the 4.2 m² porch, against the 51.6 m² that ARR-01 promised (reviewer 05).
- Forecourt and road water depend on the road survey (reviewer 22).
