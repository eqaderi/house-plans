# C10 review 27 · Materials, durability and envelope detailing

Concept stage only; nothing is engineered or code-checked. Code figures (Topic 19, Standard 2800, EN classes) are `assumption`. Frost depth, snow load, soil and local stone quality are **unknown**. Numbers come from `design.py`, `engine.py` and `zg` on the 27-point TIN (an inferred surface).

## Summary

1. `engine.walls()` draws external walls 0.30 m thick, centred on the room line. Real walls are 0.40 m above ground and 0.45 m against earth. The living room is 4.99 m clear as drawn and 4.89 m with real walls, which breaks rule 3.3.
2. Grow walls outward and set `EAST_MAIN = 18.0`. Every room then keeps its size, and the garden loses about 1.5 m².
3. Use an RC dual system with RC walls in the buried north-west and the core. Do not use steel.
4. 110 m² of terrace and roof, plus 29 m² of garage floor, sit over rooms. Each needs a protected two-layer membrane on a solid RC deck.
5. Use RC retaining walls up to 3.8 m, and gabion only on the lawn edge. Use frost-tested stone, mechanically fixed, and aluminium lift-and-slide doors for the sliders.

## Findings table

| ID | Sev | Where | Issue |
|---|---|---|---|
| MAT-01 | BLOCKER | external walls; `living` | Walls drawn 0.30 m, need 0.40–0.47 m; living < 5.0 m |
| MAT-02 | MAJOR | frame | Structural system and its plan sizes |
| MAT-03 | MAJOR | `t-south`, `deck-r`, `green-r` | Terraces over beds and the living room |
| MAT-04 | MAJOR | `garage` over pantry, wudu, hall | Salt, meltwater and oil over rooms |
| MAT-05 | MAJOR | site walls | Retaining-wall material per wall |
| MAT-06 | MAJOR | `t-low`, `gs-lawn` | Paving on 2.64 m of fill |
| MAT-07 | MAJOR | 10 sliders, 1.6–3.0 m | Window system |
| MAT-08 | MAJOR | stone façades | How the stone is fixed |
| MAT-09 | MAJOR | outdoor stairs, paving | Frost and slip resistance |
| MAT-10 | MAJOR | `boys` south wall | Bedroom wall buried up to 1.22 m |
| MAT-11 | MINOR | `green-r` | Weight, irrigation, access |
| MAT-12 | MINOR | `balc-e`, `balc-m` | Drip, gutters, railing fixings |
| MAT-13 | MINOR | exposed concrete | Freeze-thaw mix |

## Finding details

**MAT-01 · Wall thickness (BLOCKER).** `EXT_WALL = 0.30` is buffered ±0.15 m (`walls()`). `room_dims()` deducts only 0.06 m on exterior sides, so reported areas overstate the plan.

Measured clear sizes: reported / as drawn / with real walls grown inward:

- `living`: 5.08 × 6.68 = 33.9 m² / 4.99 × 6.59 = 32.9 / **4.89 × 6.49 = 31.7**
- `master`: 23.0 / 22.1 / 21.2 m²
- `girls`: 4.18 / 4.09 / 3.99 m wide
- `pantry`: 1.68 / 1.59 / 1.44 m wide (too narrow for shelves on both sides)

Needed build-ups (`ai_judgment`; U-values from review 09):

- **W-A, above ground: 0.40 m.** 20 mm plaster, 200 mm clay or LECA block, 100 mm mineral wool, 40 mm ventilated gap, 30–40 mm stone.
- **W-E, against earth: 0.45 m.** 20 mm plaster, 300 mm RC, two layers of 4 mm SBS, 80–100 mm XPS, drainage board.
  - Use 350 mm RC where more than 3 m is retained: lower u 5.0 (+3.38 m), the stair at v 1.1 (+3.62 m), main u 2.0.
  - Add a 50 mm service lining to wet rooms against earth.

**C11 correction:**

- **engine.py:**
  - Add `EXT_WALL_ABOVE = 0.40` and `EXT_WALL_EARTH = 0.45`. An edge counts as earth when `zg − FFL > 0.3`.
  - Keep the inner face at footprint − 0.15 and grow the wall outward.
  - Fix `room_dims()` to deduct the real thickness.
- **design.py:**
  - `EAST_MAIN = 18.0`: one wall line with the lower floor (grid J, review 01). Living becomes **5.19 × 6.59 = 34.2 m²**.
  - `BALC = 19.85`: the balcony keeps 1.6 m clear.
  - `TERR` stays 20.6, leaving 2.35 m of lower terrace.
- The lower outer face moves only 18.15 → 18.25, which costs about 1.5 m² of garden. There are no north or west setbacks.

**MAT-02 · Structure (MAJOR, `ai_judgment`).**

- **Recommended:** an RC dual system.
  - Buried walls are 300–350 mm RC that retain earth and act as shear walls: lower u 5.0 and v 1.1/2.8, main u 2.0 and v 2.8.
  - Stair walls (u 6.8, 9.4) and the lift shaft are 250 mm RC. Stair clear width becomes 2.35 m (2 × 1.075 m flights + 0.2 m). Lift shaft becomes 1.75 × 2.05 m; MEP should check the lift fits.
  - Columns about 450 × 450 mm (`assumption`), set at partitions and inside the insulation.
  - Solid RC slabs under all terraces and wet rooms; joist-and-block decks crack along the joints and leak.
- **Steel: rejected.** Larger drift cracks the stone, infill and glass. Exposed and buried steel rusts. The buried RC walls are needed anyway.

**MAT-03 · Terraces over rooms (MAJOR).** Measured:

- `t-south`: 29.2 m² over the children's beds, 6.1 m² over the laundry.
- `deck-r`: 39.8 m² over the living room.
- `green-r`: 41.3 m² over the master suite.

Depth for the build-up: see THM-04.

Specification:

- Inverted roof on an RC deck laid to 1.5–2% falls.
- Two-layer SBS membrane (root-resistant under the green roof), then XPS.
- Pavers on pedestals with open joints: 20 mm porcelain or 30–40 mm stone.
- At least 2 outlets plus an overflow per area.
- Upstands 150 mm; 50 mm at the sliders, with a slot channel.
- Flood-test for 48 h before the pavers go down.

The usual single exposed membrane under a mortar-bed tile lasts 5–10 years. A protected two-layer membrane lasts 25–35.

**MAT-04 · Garage over rooms (MAJOR).** Measured: 28.9 m² of garage floor lies over the pantry, wudu/WC and hall.

Correction:

- RC slab to 1.5% falls, toward two trapped gullies and an oil separator.
- Membrane turned up 150 mm.
- 80 mm reinforced screed with a PU traffic coat.
- Insulation in the ceiling of the rooms below.

**MAT-05 · Retaining walls (MAJOR).** Heights are measured from `GroundModel` steps.

| Wall | Height | Material |
|---|---|---|
| RW-1 forecourt → court, v 11.6, u −1.2…0 | 3.8 m | RC cantilever, 0.35 m stem, base about 2.6 m under the forecourt (road surcharge). Gabion rejected: its base and batter eat 1 m of the court (rule 4.10) |
| RW-2 road stair / court, u −1.2 | 0–3.8 m | RC, with the stair slab cast on it |
| RW-3 forecourt south and stair west | ≤ 1.95 m | RC 0.25 m with stone facing. Geogrid only if the road authority accepts grids under its verge |
| RW-4 court S/E, u 0.4–4.6 | ≤ 1.81 m | Mortared stone gravity wall: base about 1.2 m, 1:6 batter. RC if the owner's extra dig raises it above 2 m |
| RW-5 garden terrace, u 20.6 / v 2.8; 14-step edge | ≤ 2.38 m | RC, part of MAT-06 |
| RW-6 lawn edges, 34 m long | ≤ 1.38 m | Gabion (Galfan + PVC, local limestone) or dry stone, base about 1.0 m |

For every wall:

- 300 mm of drained gravel, filter fabric, a pipe to daylight, and weep holes every 2 m. Water frozen behind a wall pushes it over.
- Footings at ≥ 0.8 m (`assumption`).
- RC joints every 6–8 m.

**MAT-06 · Terrace on fill (MAJOR).** `t-low` and the 14 steps sit on up to 2.64 m of fill (38.9 m³). Settlement of 25–50 mm (`ai_judgment`) would crack the paving and pull it away from the 3.0 m lounge slider sill.

Correction: a suspended RC slab on RW-5 and the lower footings, over a drained void.

**MAT-07 · Windows (MAJOR).** Measured: 11.4 m of east sliders (2.4, 2.8, 3.0, 1.6, 1.6 m) face the most frequent winter wind (E, 26.4% of DJF hours; REPORT.md, one model year).

Correction:

- **Every slider ≥ 2.0 m:** thermally broken aluminium lift-and-slide, one fixed panel and one sliding.
  - uPVC sags above 2.4 m. Keep uPVC, white and reinforced, to windows ≤ 1.5 m.
- **Glazing:** double low-e, argon. Toughened outside, laminated 44.2 inside at every door and every low pane.
- **Ratings** (`assumption`): air class 4, water 7A, wind C3.
- **Fixing:** to the RC frame, never to block. Leave a 10–15 mm drift gap with expanding tape.
- **Heads:** span openings over 2.0 m with an RC beam.
- **Sills:** 40 mm projection with a drip.

**MAT-08 · Stone façade (MAJOR).** Stone set in mortar on wire ties falls in earthquakes (`inferred` from regional damage), and the ties rust.

Correction:

- **Fixing:** dry-fix 30–40 mm dense stone on stainless A4 anchors.
- **Plinth:** stone at least 600 mm above ground.
- **Copings:** fall inward, with a drip.
- **Render:** ETICS only above 2 m on the north and road sides; repaint every 10–15 years.
- **Timber:** avoid exposed timber; high-altitude UV greys it within 2–3 years.

**MAT-09 · Outdoor stairs and paving (MAJOR).** Covers the road stair, the 14 steps, `gs-court` and `path-s`.

- **Base:** RC slab on footings below frost depth, never on fill.
- **Treads:** one 40 mm stone piece per tread, flamed, with an integral nosing and 1–2% forward fall. Wet PTV ≥ 36 (`assumption`).
- **Stone tests:** absorption ≤ 0.5% (EN 13755) and a frost test (EN 12371) on each batch.
- **Ban:** travertine, soft sandstone, polished marble and glazed tile; they spall.
- **Handrails:** both sides, duplex-coated steel.
- **Road stair:** a canopy over the top flight.

**MAT-10 · Boys' south wall (MAJOR).** Measured finished ground at the wall, relative to lower FFL: +1.22 at u 6.8, +0.52 at the window's west jamb (u 8.9), −0.16 at u 10.9. The 0.9 m sill clears the ground by only 0.38 m.

Correction:

- Build u 6.8–11.1 as type W-E, tanked to +1.4 m, with a footing drain.
- Cut a drained gravel margin at v 16.55–17.4, down to ≤ 1669.70, for u 8.5–11.1.

**MAT-11 · Green roof (MINOR).**

- **Type:** extensive, 80–120 mm of substrate, 1.2–1.8 kN/m² saturated (`assumption`). That is 5–7 t; an intensive roof would be 15–18 t at the top of a seismic building.
- **Plants:** native drought-tolerant plants with drip irrigation; summers are dry.
- **Edges and drains:** a 500 mm gravel strip, two inspection chambers.
- **Access:** a maintenance gate from `deck-r` and fall-arrest anchors.

**MAT-12 · Balconies (MINOR).**

- **Gutters:** drip from `balc-e` falls in front of the lounge slider and ices. Fall the balcony 1.5% to an edge gutter with downpipes at v 1.1 and v 16.4.
- **Railings:** side-fixed through the slab edge, never through the membrane.

**MAT-13 · Concrete (MINOR, `assumption`).** Exposed elements: air-entrained C35/45, w/c ≤ 0.45, 45–50 mm cover. Use XF4 at the forecourt, garage and road stair, where salt reaches.

**Life (`ai_judgment`):** drained RC 75–100 yr. Dry-fixed stone 60+ yr (anchors checked every 10 yr); mortar-set stone 15–30 yr. Aluminium lift-and-slide 40–50 yr (gaskets 15–20 yr). Protected SBS 25–35 yr; exposed single membrane 5–10 yr. Sealants 10–15 yr. Coated gabions 50+ yr. Clean outlets twice a year.

## What C10 gets right

- Rooms sit where the ground falls away, and services fill the buried north-west: the right damp strategy.
- One stacked stair and lift core is a natural RC shear core.
- The green roof over the master is closed to people.
- `balc-e` shelters the 14 garden steps from snow and ice.
- Terraces are drawn within 20 mm of FFL; the step-free intent is right.
- The dig is cut to 200 m³ with a deepest cut of 3.97 m, so retaining heights are lower.

## Out-of-scope notes

- Main u 17.8 against lower u 18.0, and the invented `supports()` posts: review 01.
- `gs-court` drops 2.3 m in 2.0 m: circulation.
- U-values: review 09. Outfall: review 04. Lift fit: MEP.
