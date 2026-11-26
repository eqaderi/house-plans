# 23 · Indoor environmental health review of C10

Concept-stage review; nothing here is engineered or code-checked. Heights come from the 27-point survey TIN (an inferred surface).

## Summary

1. The right rooms are buried, but 10 windowless rooms have **no duct route** out, and the main wet cluster sits under the garage slab.
2. Garage air reaches every bedroom: one plain door → core lobby → open 3-storey stair → both bedroom halls.
3. The boys' room, the lower hall and `gens` sit on soil 0.9–1.2 m below natural ground. Radon is **unknown**, and a 0.35 m formation leaves no room for membrane, gas layer and insulation.
4. Clothes would dry in a windowless, buried 13.9 m² room beside the boys' room. The homework table is 7.6 m from glass.
5. All are fixable without moving a room: riser, garage depressurisation, radon-ready slab, heat-pump dryer, small opening and furniture changes.

## Findings

| ID | Sev. | Where | Issue |
|---|---|---|---|
| HLT-01 | MAJOR | main `wc-m sh-m wudu wlob pantry`; lower `wc-l sh-l lav laundry`; `gens` | 10 windowless rooms, no extract route |
| HLT-02 | MAJOR | road `garage` door (6.8, 8.4) → `lobby-r` → stair | Garage CO and fumes reach the bedroom levels |
| HLT-03 | MAJOR | lower slab, 156 m²; lift pit | Radon and soil gas unknown; no radon-ready build-up |
| HLT-04 | MAJOR | lower `laundry` u5.0–8.2, v9.6–16.4 | Indoor drying in a buried, windowless room |
| HLT-05 | MAJOR | lower `boys` S wall, `gens`, `guest` N wall | Beds and fittings against cold walls with earth behind them |
| HLT-06 | MAJOR | lower `hall-l` u8.2–12.6, v7.3–11.6 | Homework area gets daylight only through the lounge |
| HLT-07 | MAJOR | main `kitchen` hob (4.95, 11.3) | Cooking fumes reach the open stair; no duct route under `hall-r` |
| HLT-08 | MAJOR | road `plant` u3.4–7.0, v11.6–13.3 | Fuel, boiler type and flue are undefined |
| HLT-09 | MAJOR | `boys`, `girls`, `guest`, `master` | No night ventilation once windows are shut; CO₂ about 2,000 ppm |
| HLT-10 | MINOR | lower bedrooms | Sleep: terrace, TV and lift noise; no blackout |
| HLT-11 | MINOR | `boys`, `girls` desks | Two of four desks are lit from the writing-hand side; the boys' window is 2.0 m against the girls' 3.3 m |
| HLT-12 | MINOR | main `pantry`, `wudu` | Food stored against damp walls; wudu wets the floor 5× a day |

## Finding details

**HLT-01 · No extract route for windowless rooms (MAJOR).** *Evidence (measured):* the main wet cluster (u3.8–6.8, v2.8–7.3) and the pantry have earth 0.3–1.4 m above the floor; lower WC, shower, basins and laundry have 1.9–3.4 m on wall u5.0; `gens` has 0.7–1.7 m. None has a window. design.py has no riser, and the garage slab is the main cluster's ceiling, so no duct can rise straight up. *Correction:* a sealed, fire-rated riser 0.6 × 0.4 m at u6.2–6.8, v6.9–7.3 (NE corner of `wlob`; through the garage bike bay to a roof terminal). Lower rooms duct to its base, a run of 2 m or less. Prefer whole-house MVHR with the unit in `plant`. Extract rates (assumption): WC 6 l/s; showers and ensuites 15 l/s with a 65% RH boost; laundry 10/30 l/s. Undercut doors 10 mm. This riser can merge with THM-10's.

**HLT-02 · Garage air path to the bedrooms (MAJOR).** *Evidence (measured):* `lobby-r` is open 2.6 m to the stair, and the stair is open to `hall` (2.6 m) and `hall-l` (1.2 m), the two bedroom halls. The garage opens only to the west. Summer W wind (27.7% of hours, regional model, inferred) pushes its air east through the door, along with workbench solvents. *Correction:* make door (6.8, 8.4) solid, self-closing, with perimeter and drop seals. Seal all penetrations in the garage slab over `wc-m`, `wudu`, `pantry` and `hall`. A continuous 20 l/s extract high on the west wall keeps the garage under negative pressure, boosting to 150 l/s for 15 min after the shutter moves. Add a 0.05 m² low inlet in the north wall (u1–3; the ground there is below the garage floor). Interlinked CO alarms in `lobby-r`, `hall`, `hall-l` and every bedroom.

**HLT-03 · Radon and soil gas (MAJOR).** *Status:* **unknown**; fractured Zagros limestone or karst is an assumption. *Evidence (measured):* ground above the floor at room centres: boys +0.95 m, `hall-l` +1.18 m, `gens` +1.08 m, `wc-l` +3.0 m. The lift pit is about 3.5 m below the north ground. *Inferred:* the 10.5 m open stair at −5 °C outside gives about 5–6 Pa of suction at the slab, plus about 2 Pa from the hood without make-up air. *Correction:* 150 mm clean gravel gas layer; a 0.4 mm membrane lapped up the earth walls and taped at penetrations; lift pit tanked. Sumps at (10.4, 9.4) and (5.9, 13.0) on a Ø110 pipe up the HLT-01 riser, passive and fan-ready. Lower the formation from FFL −0.35 to **−0.55 (1669.45)**, about +31 m³ of dig. Run 3-month winter alpha-track tests in all four bedrooms and act at **100 Bq/m³** (WHO 2009).

**HLT-04 · Laundry drying (MAJOR).** *Evidence (measured):* 13.9 m², no window, earth 1.9–3.1 m above the floor on the west wall and 1.3–1.9 m on the south. It shares wall u6.8 with the boys' room. One load a day releases about 1.5–2.5 l of water (inferred). *Correction:* heat-pump condenser dryer (never vented), a drying cabinet on the HLT-01 extract, and a self-closing door at (8.2, 10.6). From April to October (RH 20–57%), dry on fold-down lines in the loggia, R(15.4, 11.6, 18.0, 16.4).

**HLT-05 · Cold walls with earth behind them (MAJOR).** *Evidence (measured):* the boys' south wall has ground +1.25 m at u6.8, +0.55 m at u8.9 and +0.21 m at u9.9, and both beds lie along it. The guest bed head is on wall v2.8 (ground +0.37 m). The 0.9 m sill sits only 0.35 m above ground at (8.9, 16.4), within reach of snow and splash. `path-s` at 1669.0 would cut a 1.5–2.2 m trench against this wall (rule 4.8). *Correction:* earth-contact walls of heated rooms get external tanking, 100 mm XPS and a footing drain, aiming at BS 8102 Grade 3 (assumption). Re-grade u8.9–10.9 to a 0.45 m sill clearance with a planted 1:2 batter, at most 0.4 m lower, no trench. Beds head-north (HLT-11); wardrobes 50 mm off earth walls.

**HLT-06 · Lower family hall daylight (MAJOR).** *Evidence:* the homework table at (10.4, 9.35) is 7.6 m from the lounge's east slider, through a 2.2 m opening; the hall's west wall is 9.8 m from the glass (measured). The limiting-depth test gives 9.8/4.3 + 9.8/2.4 = 6.4, against a limit of 4.0 (inferred). Average daylight factor below 0.5% (ai_judgment). *Correction:* move homework to the bedroom desks and keep the hall for play. Widen the hall→lounge opening to v8.0–10.7 (2.7 m; clear of the tea bar and the sofa). Lounge east glazing v7.5–11.4 with a 2.6 m head. Walls ≥ 0.7 reflectance. An openable 1.0 × 2.0 m rooflight over the stair rest (u7.0–9.2, v1.2–2.2) lights the stairwell and gives a summer night stack purge.

**HLT-07 · Cooking fumes (MAJOR).** *Evidence (measured):* the hob at (4.95, 11.3) is under `hall-r` (v ≤ 11.6), so no duct can rise straight up. The hall opening is 1.9 m from the hob and leads straight to the open stair. *Correction:* move the hob to (4.95, 12.0), under `plant`. A 900 mm canopy hood with its own Ø150–200 duct through `plant` to the roof, 400–600 m³/h boost. An interlocked make-up inlet ≥ 100 cm² on the south wall. Prefer induction (no NO₂; ai_judgment). Optional glazed pocket slider in the hall opening, closed only while frying; the owner decides (rule 1.3).

**HLT-08 · Boiler and water heater (MAJOR).** Fuel unknown. Room-sealed appliance only (no open flue beside a 600 m³/h hood). Vertical roof flue ≥ 1.0 m above roof, ≥ 2 m from `deck-r`, ≥ 3 m from MVHR intakes (assumption); never the south wall v13.3, 3.9 m above the kitchen window (measured). CO alarm in `plant`. Tanks: cold < 20 °C, stored hot 60 °C (Legionella, assumption).

**HLT-09 · Bedroom ventilation (MAJOR).**
- Purge ≥ 1/20 floor needs: boys/girls 0.98 m², guest 1.09, master 1.15. `Win` has no height or opening type, so it cannot be checked.
- The children's windows face `path-s` and the shared footpath ~2 m away, so they stay shut at night: two sleepers in ~59 m³ at 0.3 ach (4.9 l/s) reach ~2,050 ppm CO₂ (inferred).
- Correction: add `sill`/`head` to `Win`; two side-hung or tilt-turn sashes 0.7 × 1.3 m per children's window (1.82 m²); ≥ 15 l/s continuous supply per two-person bedroom (MVHR or ≥ 8,000 mm² trickle vents) keeps CO₂ near 1,000 ppm.

**HLT-10 · Sleep (MINOR).**
- Evidence (measured):
  - The terrace dining table (8.1, 14.9) is directly above the boys' beds.
  - The lounge TV (u15.6–17.6) hangs on wall v7.3, shared with the grandparents' room.
  - The lift shaft wall u11.4 adjoins `guest` and `gens`.
- Correction: resilient layer under the terrace screed; 200 mm dense lounge/guest wall with full-length wardrobes; quiet lift with isolated rails; external roller shutters on every bedroom window (blackout, security; June NE dawn hits master and guest glass).

**HLT-11 · Children's desks and light (MINOR).** *Measured:* the two east desks face east, so the south light falls on the writing-hand side and a right-hander writes in their own shadow. The boys' window is 2.0 m, the girls' 3.3 m. *Correction:* beds head-north on the hall wall (v11.6); both desks within 1.5 m of the south glass, users facing west; wardrobes on the side walls; boys' window u8.9–11.0 with a 2.4 m head.

**HLT-12 · Pantry and wudu (MINOR).** Pantry: tank and insulate W/N walls, 5 l/s extract, shelves 50 mm off walls, RH < 65% for rice and flour. Wudu: floor drain with fall, slip-resistant tile, on the 15 l/s extract.

## What C10 gets right

- Bedrooms and day rooms sit where ground is at or below the floor; services fill the buried NW (rule 4.8).
- Every bedroom has its own outside glazing.
- The master ensuite has a real north window (ground −0.9 m).
- The roof over the master is planted and closed: no footsteps over the bed.
- The lower tea bar avoids night trips up the stairs.

## Out-of-scope notes

- Structure: the master suite's north part (v1.1–2.8) has no lower floor beneath it.
- Smoke: the open stair is also a smoke shaft (SAF-05).
- Drainage: `path-s` at 1669.0 against the bedroom wall.
