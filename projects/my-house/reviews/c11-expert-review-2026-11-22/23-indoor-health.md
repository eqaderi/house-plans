# 23 · Indoor environmental health review of C11

Concept stage, not engineered. Heights: `zg` / `GroundModel.finished` on the 27-point TIN (inferred). Rates are `assumption` unless sourced.

## Summary

1. The risers SH-W, SH-K and SH-E are real, and every wet room is within 3.94 m of one. Ducts, fans, rates, make-up air, the radon build-up and the garage extract are still notes, so 11 of my 12 C10 findings are only partly fixed.
2. Bedroom ventilation got worse: the grandparents have one slider under a balcony; the children's glass is 0.25 m from the garden walk.
3. The new north wall at v 1.1 puts the grandparents' bed heads, the seated ensuite and the walk-in against 0.8–2.65 m of earth.
4. New crawl voids under the lounge and the loggia have no cross-ventilation, no access and no membrane.
5. The 3.8 m² plant room cannot hold MVHR, cylinder and boiler.

## Scorecard

SCORECARD: fixed=0 partly=11 not_fixed=0 worse=1 new_blocker=0 new_major=5 new_minor=4

## Part A · C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| HLT-01 extract routes | partly fixed | *measured*: distance to the nearest riser is sh-m 3.94, wc-m 3.94, wudu 1.54, pantry 1.81, sh-l 0.14, lav 1.30, laundry 0.05 and gens 0 m. Windowless rooms are now 20 (C10: 10). No duct, fan, rate or ceiling zone is drawn. | Draw the runs (main cluster → hall ceiling 2.70 m → SH-W). WC 6–15 l/s; showers, wudu, ensuites 15–25 l/s with a 65 % RH boost; pantry 5–10; laundry 10/30. 5 l/s to each buried store. |
| HLT-02 garage air | partly fixed | *measured*: fire door (6.8, 8.35–9.35) and the stair screen are drawn; extract, inlet, seals and CO alarms are notes. The lift door (10.4, 7.3) opens into the same `lobby-r`, so the shaft bypasses the screen (*inferred*). | 20 l/s continuous garage extract, 150 l/s boost, holding ≥ −5 Pa. Draw the 0.05 m² low inlet. Smoke-sealed lift doors. CO alarms in `lobby-r`, both halls and every bedroom. |
| HLT-03 radon | partly fixed | *measured*: formation 0.60 m below FFL including the gas layer; SH-W is labelled "radon pipe". Membrane, sumps and tests are not drawn. The lift pit (1668.80) has an untrapped "gravity drain". | Draw the 0.4 mm membrane up the earth walls. Sumps at (10.4, 9.4) and (5.9, 13.0) on Ø110 pipe. Trapped pit drain. Winter tests; act at 100 Bq/m³ (WHO 2009). |
| HLT-04 laundry drying | partly fixed | *measured*: 4.8 m² with a heat-pump dryer, an airer inside, a drying yard on `deck-r` and +3.0 m of earth on wall u 4.6. Extract is a note. | 10/30 l/s humidistat extract to SH-K, in its own duct, never the hood duct. Self-closing door. Draw the loggia rack. |
| HLT-05 cold earth walls | partly fixed | *measured*: boys' beds now on the inner wall v 10.95, and the sill clearance is 0.48 m. The boys' south wall still has +1.20 → +0.42 m (stair landing L2) at the desks. The grandparents got worse (N02). Tanking is a note. | Draw tanking, 100 mm XPS and a footing drain on every heated earth wall. Boys' south wall tanked to +1.4 m. |
| HLT-06 lower hall daylight | partly fixed | *measured*: homework removed; opening 2.7 m. Lounge east glass is 3.6 m (C10: 3.0 m), south 1.8 m (C10: 2.2 m). Depth to the hall's west wall is still 9.8 m. The rooflight does not reach the hall (N06). | Keep `hall-l` as circulation and play. Wall reflectance ≥0.7. Lounge glass head 2.6–2.9 m (`Win` has no head). |
| HLT-07 cooking fumes | partly fixed | *measured*: hob at (4.76, 11.75) under `plant`, duct 0.5 m to SH-K, walls to the ceiling. Make-up air is a note. | Interlocked make-up inlet ≥100 cm² in the kitchen south wall. Induction preferred (ai_judgment). |
| HLT-08 boiler / flue | partly fixed | *measured*: plant 3.8 m² on the grid; flue, fuel and type unstated. ROOM-01's flue point (4.2, 12.9) falls inside `wc-r`. | See N04. Room-sealed only. CO alarm. |
| HLT-09 bedroom CO₂ | **made worse** | *measured*: `Win` still has no sill, head or opening. Boys' window 1.8 m (C10: 2.0). Garden walk and court stair 0.25 m outside the children's glass. Grandparents down from 3 openings to 1 (N01). *Inferred* at 0.3 ach with two sleepers: boys (19.0 m² × 2.95 m) ~2,100 ppm, grandparents ~1,500 ppm. | Add sill, head and opening to `Win`. Openable area ≥0.98 m² with a secure night-vent position. ≥15 l/s supply per two-person bedroom keeps CO₂ near 1,000 ppm. |
| HLT-10 sleep | partly fixed | *measured*: the terrace table at (6.3, 14.2) is off the beds; the TV is on the dense v 6.2 wall. Shutters, pavers and lift are notes. | Draw the roller shutters. ΔLw ≥20 dB under `t-south`. |
| HLT-11 desks | partly fixed | *measured*: users face west with the light on their left, behind them; boys' desks are 1.35 m off the glass. Windows 1.8 m against 3.3 m. | Boys' window head 2.65 m; desk task lights. |
| HLT-12 pantry / wudu | partly fixed | *measured*: the pantry is now interior and the wudu trough and drain are drawn. Extracts are notes, and the pantry ceiling is the garage slab (N05). | Pantry 5–10 l/s, wudu 15 l/s to SH-W (1.5–1.8 m). RH <65 %. |

## Part B · new problems

| ID | Severity | Where | Finding | Correction |
|---|---|---|---|---|
| HLT-N01 | MAJOR | lower `guest` slider (18.0, 3.3–5.3) | Only opening; under `balc-m`; faces the lawn-stair landing 2.35 m away | Hinged door + tilt-turn sash + supply air |
| HLT-N02 | MAJOR | wall v 1.1, `guest`, `gens`, `gwalk` | Bed heads and clothes against buried wall | Tanked, insulated, lined; walk-in extract |
| HLT-N03 | MAJOR | voids under `lounge` R(15.4,6.2,18,10.95) and `loggia` | Single-sided voids 0.3–2.35 m deep | Cross-vented or sealed radon void |
| HLT-N04 | MAJOR | road `plant` | MVHR does not fit; terminals crowded | Merge `store-r`; space terminals ≥3 m |
| HLT-N05 | MAJOR | main `tanks`, `pantry`, `bulk` | Drinking water and food under the car floor | Liquid-tight slab, sealed tanks |
| HLT-N06 | MINOR | road `lobby-r` R(11.4,7.5,12.2,9.3) | "Walk-on rooflight" lies under the road roof | Remove the claim or add a real rooflight |
| HLT-N07 | MINOR | `checks.py` §7.15 | Does not test extract routes | Extend the check |
| HLT-N08 | MINOR | stair u 6.8–9.4 | No rooflight or purge outlet drawn | Draw the CIR-03 rooflight |
| HLT-N09 | MINOR | lower `sh-l`, `store-u`, `store-s` | Buried wet and store rooms; lifting station by the boys' room | Inner insulation, extract, sealed pump chamber |

## Part B details

**N01 (MAJOR).**
- *Measured*: the north window was deleted, and the STR-02 east window (u 18.0, v 1.3–2.7) was never drawn; STR-06 made u 18.0, v 1.1–3.1 solid.
- The remaining 2.0 m slider sits wholly under `balc-m` (soffit about 3.3 m above the floor). The lawn route crosses in front of it.
- *Inferred*: average daylight factor about 1.3 % (about 54° of sky, 3.6 m² of glass, 28.2 m² room). The door stays shut at night, so CO₂ reaches about 1,500 ppm.
- *Correction*:
  - Replace the slider with a 1.0 m hinged leaf and a 1.0 m tilt-turn sash with a lockable night-vent position and a roller shutter.
  - Supply ≥15 l/s.
  - If the engineer allows, add a 0.9 × 1.2 m window at u 18.0, v 1.5–2.4 (the ground there is below the floor).

**N02 (MAJOR).**
- *Measured*: ground against v 1.1 is +1.23 m at u 13.5, +0.77 at 14.75, +0.31 at 16.0 and −0.19 at 17.4. `gens` has +2.07 to +2.65 m and `gwalk` +1.63 to +2.07 m. In C10 the bed head had +0.37 m.
- *Correction*:
  - Draw the tanking, 100 mm XPS and a drain for u 9.4–18.0, aiming for a surface temperature factor ≥0.75 (assumption).
  - Add an insulated batten lining behind the beds and keep them 0.1 m off the wall.
  - `gwalk`: a transfer grille plus 5 l/s to SH-E, 0.55 m away.

**N03 (MAJOR).**
- *Measured*: ground under the lounge's suspended part is 1668.44–1669.67, a void of about 0.3–1.6 m. Under the loggia it is 1667.65–1669.12, a void of 0.9–2.35 m.
- The only face to open air is FW-16.0. To the east lies the cistern and garden-store bay under `t-low`, to the north the dug `guest` slab, and to the west FW-15.4.
- *Correction*: choose (a) or (b).
  - (a) Vents of ≥1,500 mm² per metre (assumption) in FW-16.0, plus a ducted sleeve under `t-low` to FW-20.6. Openings of 0.1 m² through FW-13.4. A 0.3 mm membrane with 50 mm of blinding on the void floor. 120 mm of insulation under the slab. A 0.6 × 0.6 m hatch in the loggia.
  - (b) A sealed void inside the radon membrane, with a sump on the SH-W pipe.

**N04 (MAJOR).**
- *Measured*: about 2.6 × 1.0 m clear, holding one 1.7 × 0.8 m block for boiler, cylinder and MVHR.
- *Inferred*: MVHR with four Ø160–200 ducts, a 300 L cylinder and a boiler will not fit with service access, so MVHR gets dropped. The hood terminal at about (5.15, 12.55), the flue and the MVHR intake share 3 m of roof.
- *Correction*:
  - Merge `store-r` R(7.4,11.6,9.4,13.0) into `plant`, giving 7.0 m² on the grid.
  - MVHR intake at about (9.0, 12.5), 3.85 m from SH-K.
  - Room-sealed boiler with its flue at about (7.2, 12.4).
  - Enlarge SH-K to 0.6 × 0.9 m so the supply duct runs in its own compartment.

**N05 (MAJOR).**
- *Measured*: the garage R(0,1.1,6.8,9.5) is the ceiling of two 1.5 m³ tanks, `bulk` and `pantry`, and SH-W passes through it.
- *Correction*:
  - Liquid-tight RC slab with a membrane and a 1 % fall to a shutter channel with an oil interceptor.
  - No penetrations over `tanks` or `pantry`.
  - Sealed tanks with screened vents to the outside.
  - 5 l/s from `tanks` to SH-W.

**N06 (MINOR).** The rooflight is inside `lobby-r`, not on `deck-r` (u ≥12.6), so it cannot light `hall-l`.

**N07 (MINOR).** `checks.py` lines 441–455 test only that `wet` rooms are within 4.5 m of a riser. Test every windowless room, `service` rooms included, for a drawn duct path of 6 m or less, with a damper at each fire wall.

**N08 (MINOR).** The only road rooflight is over `hall-r` (u 7.6–9.0, v 9.6–11.5). Draw an operable 2.2 × 1.2 m rooflight at u 7.0–9.2, v 1.3–2.5, with ≥1.0 m² free area, for summer night purge.

**N09 (MINOR).**
- *Measured*: `sh-l` has +2.8 to +3.4 m of earth on two walls, `store-u` +2.9 to +3.6 m, and `store-s` +1.2 to +3.6 m. `store-s` also holds the MEP-01 lifting station, behind the boys' wall u 6.8.
- *Correction*:
  - Insulate the inner face of `sh-l` and give it a 25 l/s boost.
  - Put the pumps in a gas-tight chamber vented through SH-K.
  - 5 l/s to each store.

## What C11 gets right

- Hob under the plant room, 0.5 m from SH-K.
- Fire door and glazed screen between garage and stair.
- Main wet cluster and pantry off the earth walls.
- Compact laundry: heat-pump dryer, riser beside it, outdoor drying yard by lift.
- Children's beds off the cold wall; TV off bedroom walls.
- 0.60 m formation fits a radon gas layer.

## Out-of-scope notes

- Privacy: children's glass beside the garden walk.
- MEP: SH-K (0.6 × 0.6 m) is probably too small.
- Smoke: the road screen leaves the lift shaft open.
- Structure: STR-02's east window conflicts with STR-06.
