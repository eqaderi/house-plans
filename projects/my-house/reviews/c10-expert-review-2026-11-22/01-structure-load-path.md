# C10 review 01 · Structure: vertical load path and stacking of floors

Concept stage; nothing here is engineered, code-checked or geotechnically verified. Overlays: shapely on `design.py` plus `engine.zg` (inferred surface). FFL = finished floor level.

## Summary

1. **Garage:** 28.9 of 57.1 m² sits on main-floor rooms (pantry, WC/wudu cluster, hall). The other 28.2 m² sits on nothing drawn, with ground 0.4–4.1 m below. Its north (v 1.1) and west (u 0) walls have no wall under them.
2. **Main floor:** 119 of 177 m² sits on lower rooms and about 31 m² on cut ground (NW). The master suite's north strip (18.7 m²) is 0.9–3.9 m in the air, and the living room's SE corner is 5.1 m above ground over the open loggia.
3. Wall over wall: 37 of 86 m of road-level walls stand on main-floor walls; 41 of 132 m of main-floor walls stand on lower walls. The main south façade lands mid-span on the bedroom ceilings.
4. The sections hide this with posts `engine.supports()` invents. All of it is fixable: a service floor under the garage, one north wall line v 1.1 through all floors, columns on v 13.0 and at the loggia corner, and walls moved 0.2–0.4 m onto a grid.

## Findings table

| ID | Sev | Where | Issue |
|---|---|---|---|
| STR-01 | BLOCKER | road `garage` | half of it has no storey or wall below |
| STR-02 | BLOCKER | main `master`/`dress`/`ens` v 1.1–2.8 | north strip and its wall over a 0.9–3.9 m void |
| STR-03 | BLOCKER | main façade v 13.0 | stands on the bedroom ceilings; seismic discontinuity |
| STR-04 | MAJOR | `living` SE, `t-south`, `balc-e` | loggia corner unsupported |
| STR-05 | MAJOR | road `plant` | water tanks on the kitchen ceiling |
| STR-06 | MAJOR | road walls south of v 9.5 | 49 m of walls on slabs or offset |
| STR-07 | MAJOR | lower slab east edge, `loggia`, `t-low` | mixed bearing, cut and fill |
| STR-08 | MAJOR | whole house | torsion: stiff NW, glazed SE, garage west wall open |
| STR-09 | MAJOR | u 17.8/18.0, 4.6/5.0, 9.2/9.4 | wall offsets |
| STR-10 | MINOR | road `hall-r` u 0–2 | bridges a court pocket that is never dug |
| STR-11 | MINOR | `green-r`, `deck-r`, garage roof | loads and spans to specify |
| STR-12 | MINOR | `engine.py` sections | invented posts |

## Finding details

**STR-01 · What the garage stands on (BLOCKER).** Measured, below the garage FFL 1677.50:
- u 2–6.8, v 2.8/4.6–9.5 (28.9 m²): the main roof slab, on walls u 2.0, 3.8, 5.3, 6.8 and v 2.8, 4.6, 7.3.
- u 0–2, v 1.1–9.5 (16.8 m²): soil 0.40–3.37 m below (mean 2.09).
- u 2–3.8, v 1.1–4.6 (6.3 m²): soil 1.55–3.29 m below.
- u 3.8–6.8, v 1.1–2.8 (5.1 m²): soil 2.59–4.10 m below, a full storey of nothing.

Neither the 6.65 m north wall nor the 8.4 m west wall has anything under it. Deep fill beside cut will settle unevenly.

**Correction (preferred):** extend the main floor under the whole garage (u 0–6.8, v 1.1–9.5, at 1673.60) as a buried plant, tank and store room of about 24 m², entered from the pantry or hall. The maximum cut is 3.90 m at (0, 1.1), within the owner's ~4.5 m; about 51 m³ extra (inferred). **Fallback:** RC foundation walls on u 0 and v 1.1, stepped from about 1676.7 at the NW to 1673.3 at u 6.8, with a suspended slab over a void.

**STR-02 · Master north strip (BLOCKER).** Main u 9.4–17.8 × v 1.1–2.8 (14.3 m²) plus u 9.4–11.4 × 2.8–5.0 (4.4 m²) have no lower floor. Ground is 0.9 m below main FFL at (9.4, 1.1) and 3.95 m below at (17.8, 1.1). The north wall and the `green-r` edge stand on nothing. The master balcony corner (19.4, 1.1) cantilevers 1.4 m east and 1.7 m north of the nearest support, (18.0, 2.8).

**Correction:** move the lower north wall from v 2.8 to v 1.1 for u 9.4–18.0. Line v 1.1 then retains and bears under all three floors from u 0 to u 18. Extra cut is 0–3.0 m, about 30 m³, and it gains about 19 m² of store/plant space. Fallback: a foundation wall 0.9–3.95 m tall plus a column at (18.0, 1.1).

**STR-03 · South façade on the bedroom ceilings (BLOCKER).** The v 13.0 wall (main roof, `deck-r` parapet, road rooms) lands 1.4 m into the 4.8 m span of `boys`/`girls`. Only about 27% of it is solid, so it must be a frame. Columns standing on a slab are a vertical discontinuity, an irregularity under Iranian Standard 2800 (assumption: high hazard, to be confirmed).

**Correction:** continuous columns of about 350 × 350 from the footings to the road roof at (4.6, 13.0), (6.8, 13.0), (11.1, 13.0), (15.4, 13.0) and (18.0, 13.0). They hide in the bedroom side walls. Add a beam of about 300 × 500 between them, and move the openings off the columns: kitchen window 5.0–6.6, dining slider 9.4–11.0, living window 15.6–17.6.

**STR-04 · Loggia corner (MAJOR).** `living` u 15.4–17.8 × v 11.6–13.0, plus `t-south` and `balc-e` beyond it, stand over the open `loggia`. Ground at (18.0, 16.4) is 1667.48, 6.2 m below the balcony.

**Correction:** a column at (18.0, 16.4) founded at about 1666.6 and braced by the loggia slab. Edge beam on u 18.0 from v 11.6 to 16.4, and a beam on v 16.4 from u 15.4 to 18.0. The balcony then cantilevers 1.4 m along its whole length.

**STR-05 · Tanks over the kitchen (MAJOR).** `plant` (6.1 m², "PLANT + TANKS") sits on the 4.6 m kitchen/entry span with no wall below. Volume unstated (2–3 m³ ≈ 20–30 kN, assumption). Its south wall v 13.3, like that of `wc-r`, overhangs the façade by 0.3 m.

**Correction:** move the tanks into the STR-01 room on a ground-bearing slab at 1673.6. From there they feed the lower floor by gravity, with a booster pump for the upper floors. Pull the road level's south wall back to v 13.0.

**STR-06 · Road-level walls (MAJOR).** These stand on slabs: `hall-r` v 11.6 (6.85 m, across the middle of the kitchen); `plant`/`wc-r` u 3.4 and 7.0; `office` u 9.0, 12.2 and v 12.6, which miss the main walls by 0.2–0.4 m; and u 6.8 over the main hall.

**Correction:** set the office walls on u 9.4, 12.6 and v 13.0. Build the road partitions south of v 9.5 lightweight (≤ 1 kPa line load). Add a 2.2 m beam on u 6.8 from v 7.3 to 9.5.

**STR-07 · Mixed bearing (MAJOR).** The lower slab has 121.8 m² in cut (up to 3.95 m) but 34.4 m² along u 15.5–18 over ground up to 1.39 m below its formation. `loggia` sits on 1.0–2.1 m of fill and `t-low` on 1.0–2.3 m.

**Correction:** step every footing down to undisturbed ground below frost depth (unknown; assume ≥ 0.8 m). Suspend the slab east of u 15.5 and the loggia slab; no slab on fill deeper than 0.5 m. Soil facts are unknown: boreholes at (0, 1.1) and (18, 16.4).

**STR-08 · Lateral system (MAJOR).** Stiffness sits uphill (core, walls against earth); mass and glass sit downhill. The garage west wall is 80% open (piers 0.48, 0.75, 0.48 m). Short uphill against tall (≤ 7 m) downhill supports is the classic short-column case.

**Correction:** RC frame plus walls, with the core as the main shear wall and the retaining walls tied to the slabs. Make the garage north wall solid. Add at least two solid panels ≥ 1.8 m on the east façades (main u 18.0, v 4.6–6.7; lower u 18.0, v 2.8–4.6), plus frames on v 13.0 and v 16.4. An engineer must check torsion.

**STR-09 · Offsets (MAJOR).** Main east wall u 17.8 sits over lower u 18.0, main u 4.6 over lower u 5.0, and the kitchen/dining wall u 9.2 misses the core line u 9.4.

**Correction:** main east wall to u 18.0 (+2.4 m²; balcony 1.4 m deep, edge stays at 19.4). Lower west wall to u 4.6, designed as an RC retaining wall for 1.9–3.4 m of soil plus the main slab. Kitchen/dining wall to u 9.4 (dining 3.2 m wide, still within rule 1.5).

**STR-10 · Court pocket (MINOR).** `court-w` includes u 0–2 × v 9.6–11.6 at 1673.60 under `hall-r`, but `GroundModel` keeps natural ground there (1674.1–1674.8), and section A–A shows a void. Choose one: a covered porch dug to 1673.6, with the hall spanning 2 m from an RC retaining wall on u 0 (3.8 m) to u 2.0; or extend `entry` west to u 0.

**STR-11 · Loads (MINOR).**
- `green-r`: extensive roof ≤ 150 mm, about 2.0–2.5 kPa saturated, plus snow 1.5–2.5 kPa (assumption) and finishes about 1.5 kPa. Spans ≤ 4.6 × 5.1 m: fine.
- `deck-r` over the living room (5.2 × 6.8 m): about 250 mm two-way slab.
- Garage roof (6.8 × 8.4 m, no columns): beams of about 300 × 600 on v 1.1, 5.3 (on the shutter pier) and 9.5.
- Garage floor: spans ≤ 3 m; design for light vehicles (assumption 2.5 kPa plus a point load).

**STR-12 · Drawings (MINOR).** `supports()` invents posts: about 3.9 m under the garage (C–C), about 4 m under the master strip (D–D), and others under the loggia. In B–B, `wc-r` runs past the main slab (v 13.3 against 13.0). C11 should model columns, foundation walls and footing levels in `design.py` and draw only those.

### Proposed grid for C11

- **u:** A 0.0 · C 4.6 · D 6.8 · E 9.4 · F 11.4 (north of v 9.5) / F′ 11.1 (bedroom zone) · G 12.6 · H 15.4 · J 18.0; cantilever ≤ 1.4 m.
- **v:** 1 1.1 · 2 5.0 (partial) · 3 7.3 · 4 9.5 · 5 11.6 · 6 13.0 · 7 16.4.
- **Continuous from the footings to the roof:** line 1 (u 0–18), line 3, D, E–F (the core), J; line 6 at C, D, F′, H and J; line 7 at H and J.
- **Garage:** no columns inside; spans A–D (6.8 m). Largest panel G–J, 5.4 × 4.5 m.

## What C10 gets right

- The stair and lift core has the same footprint on every floor: a ready-made continuous RC shear core.
- Floor-to-floor heights are constant (3.90 and 3.60 m), and each roof is the terrace of the floor above, with no split slabs.
- 73% of the road level sits on the main floor and 67% of the main floor on lower rooms. The south terrace is the bedrooms' roof (rule 4.3).
- The deepest cut, 3.97 m, is within the owner's limit.

## Out-of-scope notes

- Thermal breaks at the balconies; robust waterproofing on the green roof.
- Drainage behind every retaining wall (v 1.1, u 0, u 4.6, u 20.6) is critical on this slope.
- The lift overrun probably rises 0.5–1 m above the road roof, and the pit is about 1.4 m deep.
