# C11 review 01 · Structure: vertical load path

Concept stage; nothing is engineered or verified. Evidence: `design.py`, `structure.py`, `engine.zg` (inferred) and `checks.json`, re-run by me. Loads are assumptions.

## Summary

1. C11 fixes the three C10 blockers. The garage stands on the walls of a dug service room, line v 1.1 bears under all three floors, and continuous columns on v 13.0 replace the posts on slabs.
2. New blocker: there is no beam on v 13.0 at 1677.50. That façade is 61% glass, and beams MB-9.4 and MB-12.6 end on 0.4 m and 0.3 m mullions.
3. The lower perimeter stops at 1670.00. The u 18 wall, the SE corner and the girls' south and east walls carry two storeys over 0.5–1.1 m of void or fill. They have no foundation, and section A–A draws u 18 standing on the suspended slab.
4. "0 m² on nothing" is overstated. `structure.py` counts glass outlines, and foundation walls that stop 3.6 m below the slab, as bearing.
5. Retaining: a 0.20 m wall holds 3.6 m of ground under the garage walls, and the north piles have only 0.8 m of toe.

## Scorecard

SCORECARD: fixed=7 partly=5 not_fixed=0 worse=0 new_blocker=1 new_major=7 new_minor=3

## Part A · C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| STR-01 garage | **fixed** | measured: the road plate bears on walls u 0, 2.0, 3.8, 6.8 / v 1.1, 2.8, 4.6, 7.3, 9.5 of the 1673.60 service room; spans ≤3.0 m | none (see N05) |
| STR-02 master strip | **fixed** | measured: lower wall (9.4–18, 1.1), 0.45 m; ground 1672.69 → 1669.59 | none |
| STR-03 south façade | **partly fixed** | measured: C-4.6/6.8/11.1/15.4/18 continuous; LB-13.0 at 1673.60. No v 13.0 beam at 1677.50 (N01). | N01 |
| STR-04 loggia corner | **fixed** | RC-18L u 18, v 12.8–16.4 from 1666.6; LB-16.0, BB-16.4; balcony columns on u 19.6 | the north end of LB-18 needs a column (N03) |
| STR-05 tanks | **fixed** | tanks on the ground slab at 1673.60; road south wall on v 13.0 | none |
| STR-06 road walls | **partly fixed** | office on the grid; MB-6.8 added. Hall-r v 11.6 (9.4 m), u 4.4 and u 7.4 walls and the WC stand mid-span on the 3.5 m kitchen slab, never declared light or tested. | declare them ≤1.0 kPa dry-lining, or add a beam at 1677.50 on v 11.6, u 2.0–9.4 |
| STR-07 mixed bearing | **partly fixed** | measured: deep-fill zones suspended; the girls' room runs from 1.32 m cut to 0.94 m fill | N02 |
| STR-08 lateral | **partly fixed** | RC core; solid panels at u 18, v 1.1–3.1; solid garage north wall. The garage west wall is still 73% open (piers 0.47 / 0.75 / 0.47 m). MW-SE stands on a beam (N04). | N04; engineer's torsion check |
| STR-09 offsets | **fixed** | east wall 18.0, west wall 4.6, kitchen/dining 9.4 | none |
| STR-10 court pocket | **fixed** | porch dug to 1673.60; RC-0 retains 0.9–1.3 m; MB-11.6 carries the hall | none |
| STR-11 loads | **partly fixed** | RB-5.3 added; deck on pedestals. No slab depths or load table; MB-12.6 undersized (N07). | record slab depths and loads as assumptions |
| STR-12 invented posts | **fixed** | `engine.supports` is deleted; sections draw only `structure()` | the missing foundations (N02) show in the sections |

## Part B · New problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| STR-N01 | BLOCKER | main v 13.0 at 1677.50, u 2–18 | no head beam; road slab edge, road walls and two beam ends sit on glass | MB-13.0, 400 × 650, on the columns |
| STR-N02 | MAJOR | lower u 18 (v 3–12.8), v 15.75 (u 11.1–15.4), LW-15.4 | walls with no foundation over 0.5–1.1 m of void or fill | stepped foundation walls |
| STR-N03 | MAJOR | corner (18.0, 10.95) | LB-18 end and three lintels on 0.15 / 0.40 m piers | column, footing ≈1667.5 |
| STR-N04 | MAJOR | MW-SE | shear wall on beam LB-18 for 1.2 of its 1.4 m | RC-18L to v 11.6 |
| STR-N05 | MAJOR | LW-7.3 (u 4.6–6.8); core u 6.8 (lower) | 0.20 / 0.25 m walls retain 3.6 m under the garage footings | 0.35–0.40 m RC retaining |
| STR-N06 | MAJOR | PW-N, u 6.8–13.2 | toe 0.8 m below the dig for 1.9–4.3 m retained | toe ≤1667.0, or top-down |
| STR-N07 | MAJOR | MB-12.6 | 6.8 m span at 300 × 600 under a 0.40 m wall and the deck | 400 × 750, or a column |
| STR-N08 | MAJOR | `structure.py` | the checks count non-bearing lines and skip three wall families | four code fixes |
| STR-N09 | MINOR | C-6.8/9.5, C-11.1/13 | clash with the kitchen opening and the wardrobes | shift by 0.1–0.3 m |
| STR-N10 | MINOR | PW-N | piles overlap the north wall by 0.225 m; 0.25 m gaps | centres v 0.60, 0.50 m apart |
| STR-N11 | MINOR | P-F/11.6 | pier on the W1 line, footing above W1's base | delete; seat PB-F on W1 |

## Part B details

**N01 (BLOCKER).** Measured: main v 13.0 has 9.7 of 16.0 m open: 2.7–3.9, 5.35–6.55, 7.1–9.1, 9.5–10.9, 11.5–12.4, 12.7–15.1 and 15.75–16.35. No element at 1677.50 runs along v 13.0 for u 2.0–16.4. Yet that line carries the road slab and deck edges and the south walls of the plant room, WC, store and office.
- MB-9.4 ends at (9.4, 13.0), on a 0.4 m mullion.
- MB-12.6 ends at (12.6, 13.0), on a 0.3 m mullion, with ≈300 kN (assumption, see N07).
- Both ends are mid-bay over the children's rooms.

`columns_and_beams` passes them because any point of the plate outline counts as support. **Fix:** add MB-13.0: beam, u 2.0–18.0, z 1676.85–1677.50, ≈400 × 650. It sits on MW-2.0 and on C-4.6, C-6.8, C-11.1, C-15.4 and C-18. Size bay 6.8–11.1 for the MB-9.4 point load, and bay 11.1–15.4 for the MB-12.6 point load, which sits 1.5 m from C-11.1.

**N02 (MAJOR).** Measured natural ground against the 1669.40 formation:
- u 18: 1669.36 at v 3, 1668.96 at v 6.2, 1668.33 at v 10.95, 1668.05 at v 12.8;
- v 15.8: 1669.25 at u 13, 1668.45 at u 15.4;
- u 15.4: 1668.92–1668.46.

No element reaches below 1670 at (18, 8), (18, 10.5), (14, 15.8) or (15.4, 14). Section A–A puts the u 18 wall, which carries the main east wall and the deck edge, mid-span on the suspended slab between FW-15.4 and FW-19.3 (3.9 m). **Fix:** add these foundation walls, keeping every footing ≥0.8 m below natural ground (frost depth is unknown):
- FW-18E: u 18, v 1.1–12.8, 0.30 m, stepping ≤0.5 m at a time from 1668.8 down to 1667.5;
- FW-S: v 15.8, u 11.1–15.4, 1668.9 → 1667.6;
- FW-15.4S: u 15.4, v 10.95–15.75, 1668.4 → 1667.6.

**N03 (MAJOR).** The lounge slider (u 18, v 9.0–10.8) and the loggia slider (v 10.95, u 15.8–17.6) leave corner piers of 0.15 m and 0.40 m. These piers carry the north end of LB-18 (MW-SE and the deck), the main living-slider lintel and two lower lintels. The ground is 1.07 m below formation. **Fix:**
- Column C-18/10.95, 400 × 400, from a footing at ≈1667.5 up to 1677.50.
- Lounge slider to v 9.0–10.5.
- Loggia slider to u 15.8–17.4.

**N04 (MAJOR).** MW-SE is the downhill solid panel of C11-STR-06. For 1.2 of its 1.4 m on u 18 it stands on LB-18, a 1.85 m beam over the loggia opening. That is an in-plane discontinuity. **Fix:** extend RC-18L north to v 11.6, founded at 1666.6–1667.4. If the loggia must stay open, keep only the v 13.0 leg of MW-SE (u 16.4–18) over LB-13.0 and RC-18L. Never put a solid panel on a beam.

**N05 (MAJOR).** Measured: the finished level is 1672.85–1673.00 north of LW-7.3 and west of the lower core wall, against 1670.00 rooms with formation at 1669.40. A 0.20 m "wall" and a 0.25 m core wall each retain 3.6 m. The footings of MW-3.8, MW-2.8 and MW-7.3, which carry the garage, stand 0–2.2 m from that drop, and MW-2.0 stands 2.6 m from the u 4.6 wall. The brief's rule is 0.45 m against earth. **Fix:**
- LW-7.3 (u 4.6–6.8): `retaining`, 0.40 m RC, bottom 1668.9.
- Lower core west wall: 0.35 m RC.
- Both are propped by the two slabs and designed for the garage surcharge.
- Or dig u 4.6–6.8, v 1.1–7.3 to 1670.00 as a store (≈13 m², ≈45 m³).

**N06 (MAJOR).** Measured ground on v 0.85: 1673.66 at u 6.8, 1672.73 at u 9.4 and 1671.34 at u 13.2. The piles retain 4.3–1.9 m above the 1669.40 dig, with the toe at 1668.6 and no anchors. **Fix:** for u 6.8–13.2, put the toe at ≤1667.0. Or draw a capping beam at 1673.3 and state the sequence: piles, then the main slab as a prop, then the dig. u 0–6.8, with 4.4 m of toe below the 1673.0 pit, is fine.

**N07 (MAJOR).** MB-12.6 spans 6.8 m. It carries RW-12.6 (0.40 × 3.3 m), half the deck (2.7 m) and half the office roof (1.6 m). Assumption loads give ≈90 kN/m, so M ≈ 520 kNm and each end reaction is ≈300 kN; 300 × 600 is too small. **Fix:** 400 × 750. Or add C-12.6/9.3 in the main pier at v 8.65–10.0, move the lower lounge opening from v 8.0–10.7 to 6.4–9.0, and the spans drop to 3.1 m and 3.7 m.

**N08 (MAJOR).** Measured by re-running the module:
1. `bearing_lines` takes every `storey == "lower"` wall whatever its top. So nine walls that stop at 1669.98–1670.00 "carry" the 1673.60 slab and the balconies: FW-20.6, FW-19.3, FW-16.0, FW-13.4, FW-15.4, FW-1.1T, FW-12.8T, FW-6.2T and LIFT-PIT. Without them, balc-e drops from 10.5 to 7.8 m² "on a wall". The roof also counts LIFT-OVR, which stands on top of it.
2. Every plate outline counts as a wall, even where it is 57–61% glass.
3. A beam end anywhere on an outline counts as supported.
4. `wall_over_wall` skips road partitions, main walls outside the lower footprint, and every lower wall's foundation.

**Fix:**
- Filter lines by `z_bot < slab.z − 0.3 ≤ z_top + 0.35`.
- Subtract openings from outlines; a gap over 1.2 m with no beam does not bear.
- A beam end needs a column, a beam, or ≥0.6 m of solid wall within 0.3 m.
- Add a check that every lower wall's bottom is ≤ zg − 0.8 wherever the ground is below formation.

**N09 (MINOR).** C-6.8/9.5 occupies u 6.625–6.975, which cuts 0.075 m into the kitchen opening (5.6–6.7); move the opening to 5.5–6.5. C-11.1/13 (0.45 m in a 0.20 m wall) cuts 0.075 m into both wardrobes; start the wardrobes at v 13.3.

**N10, N11 (MINOR).** As in the table: piles centred on v 0.85 sit 0.225 m inside the north wall; P-F/11.6 (footing 1674.5) stands on the W1 stem (base 1673.0).

## What C11 gets right

- The garage is answered physically: a ground-bearing service room at 1673.60 with walls on a ≤3 m grid.
- Line v 1.1 bears and retains under all floors from u 0 to u 18.
- Five continuous RC columns on v 13.0; balconies on their own beam and columns; deep-fill zones suspended.
- One element list feeds the plans, sections, 3D and checks; the invented posts are gone.

## Out-of-scope notes

- Seismic: rerun torsion with N04. Water: tank the shower against LW-7.3. Thermal: balcony slabs need breaks. Architecture: RC-18L closes most of the loggia's east side.
