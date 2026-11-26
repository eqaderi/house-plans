# C11 review 27 · Materials and durability

Concept stage; nothing is engineered. Code figures are `assumption`; frost depth, soil and snow load are **unknown**. "Measured" = `design.py`, `engine.walls()`, `zg`, `GroundModel` (27-point TIN, inferred).

## Summary

1. The wall thicknesses are real, the living room is 5.19 m clear and `t-low` is suspended.
2. Materials are specified nowhere: the ledger's "notes" do not exist in the code, the drawings or `index.html`.
3. The lower core is 0.40 m thick but retains 3.84 m, and pile wall PW-N overlaps the north wall by 0.225 m.
4. The lawn stair and the walk sit on 1.3–2.0 m of fill, and the paving is flush with FFL against room walls.
5. A terrace outlet drains onto a stair landing, and the guards are drawn as glass.

## Scorecard

`SCORECARD: fixed=1 partly=9 not_fixed=3 worse=0 new_blocker=1 new_major=4 new_minor=3`

## Part A · C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| MAT-01 walls | partly | `measured`: real bands; living 5.19 × 6.55 m. The lower core u 6.8 and v 1.1 (u 6.8–9.4) retain +2.95–3.84 m and v 7.3 (u 4.6–6.8) retains +3.0 m, all drawn **0.40 m**. §7.14 never tests thickness per edge. | Every wall retaining > 3 m: 0.35 RC + SBS + 100 XPS + drain board + plaster = **0.50 m**. That means main u 0 (+3.87, cars above), main v 1.1 at u 0–3, lower u 4.6 and the lower core. Add a per-edge test: retained > 0.3 m needs ≥ 0.45 m; retained > 3 m needs ≥ 0.50 m. |
| MAT-02 system | partly | `measured`: RC dual system, RC core and shaft, no steel. | Solid RC slabs (no joist-and-block) under terraces and wet rooms. |
| MAT-03 terraces over rooms | partly | `measured`: 0.25 m set-down, 2 outlets plus an overflow, "inverted roof" and "pedestal pavers" in `WATER`; the SBS layers, XPS and flood test are in the ledger only. | Draw roof types R-1 to R-3 with their layers. Fix N04. |
| MAT-04 garage deck | partly | `measured`: the garage sits over the pantry, WC, shower and wudu. "1 % (1677.50 → 1677.47)" is 0.44 %; a true 1 % puts the shutters at 1677.43, 40 mm below the forecourt. | High point 1677.55 at the fire door, with a 50 mm upstand. Fall 1 % to a trench drain at u 0.6; threshold 1677.49. Membrane up 150 mm, screed and PU traffic coat, interceptor. |
| MAT-05 retaining walls | partly | `measured`: W1–W4 are RC (0.30–0.40 m). The derived SW-6…SW-34 walls (0.67–2.38 m high) have no material, footing or drainage, and no wall has weeps. | RC where ≥ 1.5 m (SW-8, 20, 21, 23, 29–31); stone or gabion where ≤ 1.4 m (the rest). All: 300 mm of gravel, DN100 drain to daylight, weeps every 2 m, footing ≥ 0.8 m. |
| MAT-06 terrace on fill | **fixed** | `measured`: `t-low` is suspended on FW-20.6 (founded 1666.5). | None |
| MAT-07 windows | partly | `measured`: sliders are now 1.4–2.4 m; no system or glazing is given. | Aluminium lift-and-slide ≥ 1.8 m; double low-e; 44.2 laminated inside; fixed to RC; sill drips. Heads: N08. |
| MAT-08 stone façade | **not fixed** | `measured`: no stone, anchors, plinth or coping outside the ledger; `views/house-se.png` shows render. | Dry-fixed 30–40 mm limestone on A4 anchors; plinth ≥ 600 mm; copings with drips. |
| MAT-09 outdoor stairs | **not fixed** | `measured`: tread spec only in the ledger. Fill: `ls-top` 2.01 m, `ls-l1` 1.28 m; section H–H draws the lawn stair as a filled box. `rs-f2` and `cs-f3` sit on ~1.0 m of fill. | RC stair slabs spanning between the flanking walls (FW-20.6 / SW-23; W3 / W4), never on fill. One-piece 40 mm flamed treads, absorption ≤ 0.5 %, frost-tested, 1–2 % forward fall. |
| MAT-10 boys' wall | partly | `measured`: window at u 8.9–10.7 (ground +0.42, sill +0.90). The wall is still 0.40 m; `cs-l2` (+1.20) and `cs-f3` bear on it; the store wall retains +1.84 m. | Lower south wall u 4.6–9.0 as W-E, tanked to +1.4 m; stair separated by a 20 mm joint with a drain board; footing drain. |
| MAT-11 green roof | partly | `measured`: extensive, guarded; no substrate, irrigation, gravel edge or anchors. | 80–120 mm substrate (≤ 1.8 kPa wet); drip line; 500 mm gravel strip; anchors on the north and east edges. |
| MAT-12 balconies | partly | `measured`: uninsulated, 1:60 to an edge gutter with drips, on columns. Rails untyped; the 3D shows glass. | Side-fixed duplex-coated steel rail on a 0.3 m upstand (EXT-03), never through the membrane. |
| MAT-13 concrete | **not fixed** | `measured`: no class, cover or mix. New exposed RC includes balcony columns 7.6 m tall, forecourt piers and W1–W4. | Air-entrained C35/45, w/c ≤ 0.45, cover 45–50 mm; XF4 at the forecourt, deck, garage, road stair and W1–W4. |

## Part B · new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| MAT-N01 | MAJOR | whole design | The specification exists only in CORRECTIONS.md | Typed schedule, tags, check |
| MAT-N02 | BLOCKER | PW-N v 0.85, u 0–13.2 | Pile wall and house wall overlap 0.225 m | Piles to v 0.30, waterproofing zone |
| MAT-N03 | MAJOR | `walk-s` u 9.74–15.4; `court-w` at u 2.0 and v 13.0 | Paving at FFL against room walls | −150 mm, or gravel strip + channel + tanking |
| MAT-N04 | MAJOR | `t-south` outlet (6.8, 16.2) | Discharges onto landing `cs-l2` | Move it onto the terrace; downpipe in the wall |
| MAT-N05 | MAJOR | `walk-s`, `fore`, `court-w` | Paving on 1.55–1.77 m of fill | Suspend; cap fill at 1.0 m |
| MAT-N06 | MINOR | 89.5 m of guards | Untyped; glass in the 3D | Type per EXT-03 |
| MAT-N07 | MINOR | balcony columns at u 19.6 | Pierce the `t-low` membrane, maybe the cistern | Collars; cistern in u 18–19.3 |
| MAT-N08 | MINOR | lower and main south openings | No lintels or beams over openings > 2 m | RC downstand beams |

## Part B details

**MAT-N01 (MAJOR).** A grep over the code, the SVGs and `index.html` finds no SBS, XPS, tanking, stone, tread, gabion, glazing or concrete class (`measured`). Six ledger rows say "Partly … notes", but the notes do not exist. Correction:
- Add a `SPEC` to `design.py`: walls W-A 0.40, W-E 0.45, W-E35 0.50; roofs R-1 to R-4; stair S-1; site walls SW-RC, SW-ST, SW-GB; concrete C-XF4; façade F-1; windows G-1.
- Tag every edge, terrace, stair and `Element`, and print the schedule.
- Check that every element has a type and a thickness that fits its retained height.

**MAT-N02 (BLOCKER, impossible as drawn).**
- PW-N (0.45 m on v 0.85) fills v 0.625–1.075. The house wall's outer face is at v 0.85.
- The overlap is 2.97 m² on the main plan and 2.17 m² on the road plan (`measured`); §7.3 passed it.
- Ø450 piles at 0.70 m centres leave 0.25 m gaps.
- The 3.7–3.9 m buried wall has no room for a membrane, drain board or XPS.

Correction: piles on v 0.30 at ≤ 0.55 m centres or secant, with 100 mm of shotcrete. That leaves 0.225 m for the drain composite, a pre-applied membrane and 100 mm XPS.

**MAT-N03 (MAJOR).** `walk-s` is +0.00 against FFL along the bedroom wall (5.7 m, no door) (`measured`). So is `court-w` along the entry west wall (v 9.5–13.0) and the main south wall at u 2.0–4.6. The paving bridges the damp course. Correction:
- Without a door, drop the walk to 1669.85 and the court edge to 1673.45, falling 1:40 away;
- or lay a 300 mm gravel margin with a slot channel, and tank the wall to +0.30 m.

**MAT-N04 (MAJOR).** The west outlet of `WATER["t-south"]` at (6.8, 16.2) lies in the cut-out R(4.6, 16.0, 7.8, 16.4), directly over `cs-l2` at 1671.20 (`measured`). The 0.40 m overhang over `cs-f3` and the walk has no drip. In winter that means ice on the main garden stair. Correction:
- outlet to (7.95, 15.90), with its downpipe in a wall chase to the footing drain;
- a gully under the overflow at (11.25, 16.3);
- a drip and gutter on v 16.4, u 7.8–15.4;
- a test that every outlet lies on its own surface.

**MAT-N05 (MAJOR).** §7.4 checks floors only. Fill under paving (`measured`):
- walk 1.77 m (boxed by SW-29/30/31);
- forecourt 1.64 m, under cars;
- court 1.55 m.

Expect 25–50 mm of settlement (`ai_judgment`). Correction:
- suspend the walk on SW-29/31 and the lower south footing;
- extend the forecourt deck wherever fill exceeds 1.0 m;
- compact the court in 150 mm lifts, with geogrid over 1.0 m of fill;
- extend §7.4 to every paved surface.

**MAT-N06 (MINOR).** `views/house-se.png` shows frameless glass on every edge, against EXT-03: a solid parapet with a planter on `t-south`, and an upstand with a rail on the balconies. Correction: type the guards. Where glass stays, use 2 × 10 mm heat-soaked laminated panes with a cap rail.

**MAT-N07 (MINOR).** The columns at (19.6, 2.75 / 6.2 / 9.4) pierce `t-low`'s membrane (`measured`). The first two stand in bay u 19.3–20.6, v 1.1–6.5, which is the cistern if it spans that bay (`inferred`). The cistern walls are 0.20 m. Correction:
- keep the cistern in u 18.0–19.3, with walls ≥ 0.25 m and waterstops;
- add 150 mm collars around the columns.

**MAT-N08 (MINOR).** `structure()` has no lintel over the girls' 3.3 m window or the main south sliders, which carry the road wall. Correction: 300 × 450 mm RC downstands at v 15.75 (u 11.3–14.9) and at main v 13.0 (u 7.0–15.2), sized by the engineer.

## What C11 gets right

- Real walls are drawn and deducted; the living room is 5.19 m wide.
- `t-low` and the lounge east bay are suspended; the C10 2.64 m fill is gone.
- An RC dual system with a solid core; no steel.
- A 0.25 m set-down, 2 outlets plus an overflow and slot channels on every terrace over a room.
- The east sliders are cut to 1.8–2.0 m, and the green roof is extensive with no tanks on the roof.

## Out-of-scope notes

- Structure: there is no beam on road v 13.0 over the sliders, and the balcony columns are 0.30 m wide and 7.6 m tall.
- Geotech: the PW-N top stands 4 m above ground at u 9–13.
- Water: the `fore-deck` outlet (−3.2, 11.3) and the lawn overflow (26.0, 10.0) lie off their surfaces.

