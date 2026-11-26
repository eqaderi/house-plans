# 10 · MEP services review of C10 (plumbing, drainage, water, ventilation, gas, electrical)

Concept stage; nothing engineered or code-checked. Iranian National Building Regulations Parts
13/14/16/17 would apply; practice figures are `assumption`.

## Summary

1. Wastewater from the main floor (1673.60) and lower floor (1670.00) **cannot reach a road sewer by
   gravity**; C10 shows no pump, no downhill outfall and no septic. Where sewage goes is unknown.
2. No wet room stacks on another and **no service riser is drawn**; three risers fit with small moves.
3. The kitchen hob sits under the road entrance hall, so the hood has **no exhaust route**.
4. ~3 t of water tanks in a 5.5 m² road-level plant room above the kitchen: undersized, heavy, leak-prone.
5. Nine windowless wet/service rooms, including a windowless drying room, have no duct routes.

## Findings table

| ID | Sev | Where | Issue |
|---|---|---|---|
| MEP-01 | BLOCKER | main + lower drains | No gravity outfall to road; downstream unknown |
| MEP-02 | MAJOR | all floors | No risers; wet rooms do not stack |
| MEP-03 | MAJOR | main `kitchen` | Hood exhaust has no route |
| MEP-04 | MAJOR | road `plant` | Tanks at the top, over the kitchen; room too small |
| MEP-05 | MAJOR | main NW, lower NW | Windowless rooms, no ventilation routes |
| MEP-06 | MAJOR | lower `laundry` | Windowless buried drying room |
| MEP-07 | MAJOR | road `plant`, forecourt | Boiler, flue, gas meter, CO safety undefined |
| MEP-08 | MAJOR | forecourt, core | Power supply, panels, lift, outage resilience |
| MEP-09 | MINOR | `wc-r`, `ens` | Wet floors on suspended slabs over kitchen / void |
| MEP-10 | MINOR | `green-r`, `lawn` | Irrigation and green-roof load |
| MEP-11 | MINOR | all floors | Hot-water dead legs |
| MEP-12 | MINOR | garage, forecourt | Riser through garage; frost on shallow pipes |
| MEP-13 | MINOR | all floors | Cooling strategy not chosen; it decides duct sizes |

## Finding details

**MEP-01 · BLOCKER · wastewater outfall.** Road surface along the frontage is 1677.41–1677.50
(`measured`, zg at u −0.55 v 1.1 to u −5.9 v 10.8). Whether a public sewer exists in the road, its
invert depth, and whether there is any sewer or lower street east (downhill) of the parcel are
**unknown**. Gravity needs (`inferred`, 2% falls):
- `wc-r` (invert ≈1677.2): sewer ≥0.6 m deep. Plausible.
- main wudu WC (≈1673.3): sewer ≥4.4 m deep. Unlikely.
- lower WC (≈1669.5): sewer ≥8.1 m deep. Impossible.
- Downhill east works by gravity (to NE envelope corner, ground 1665.29: 4 m drop over ~20 m), but
  only if something is there to receive it.

Correction: owner confirms with the provincial water and wastewater company (a) road sewer and its
invert at the frontage; (b) any downhill sewer/road and an easement across the east neighbour. C11
reserves space for all three outcomes:
- **A, road sewer (expected):** road level drains west by gravity. Main + lower drain by gravity
  to a duplex sealed lifting station in a pit **R(5.0, 9.6, 6.2, 10.8)**, 1.5 m deep, at the north
  end of `laundry`, ≥1.2 m³ emergency volume (one day, 8 people × 150 L), vented up SH-W; DN50
  rising main up SH-W, 8.6 m static (≈12 m head), to a break chamber under the forecourt at
  (−2.0, 10.5), then gravity to the road.
- **B, downhill sewer or easement:** one gravity drain from the lower slab east under `t-low` and
  `lawn` to an inspection chamber at about (29.5, 1.5). No pumps.
- **C, no sewer:** a soak-away on a 35% slope above retaining walls and a neighbour needs
  geotechnical approval and may be unacceptable. A road tanker cannot lift 12 m (suction ≈6–8 m), so
  any septic/holding tank goes under the forecourt, fed by the pump in A.

**MEP-02 · MAJOR · stacking and risers** (`measured` from design.py):
- `wc-r` (u 7–9, v 11.6–13.3) sits over the kitchen island zone and, one floor further down, over
  `boys`.
- Main `wc-m/sh-m/wudu/wlob` (u 3.8–6.8, v 2.8–7.3) have unexcavated earth under them. The lower
  wet rooms are 0–2.3 m further south.
- `ens` (u 9.4–11.4, v 1.1–5.0) has earth under it (ground 1672.07) and the green roof above it.
- Lower `gens` (u 11.4–14.2, v 2.8–5.2) is directly east of `ens`.
- The lower WC/shower/basins sit under the main family hall.
- Only the kitchen sink (6.0, 12.65) stacks well, over the lower store.

Correction: three risers.
- **SH-K, R(5.0, 12.35, 5.6, 12.95), all floors**: plant room / kitchen SW counter corner / store.
  Road WC drain (B/C), sink waste, hood duct, gas, mains down to tanks, booster, hot-water and
  heating risers. Shorten the kitchen south window to u 5.7–6.9; the sink stays under it.
- **SH-W, R(5.0, 7.3, 5.6, 8.1), all floors**: boxed pier in the garage / pier on the family
  hall's north side, clear of the wudu-lobby opening (u 5.85–6.65) / lower wet block. Main
  wet-cluster stack, rising main, Ø125 extracts. Lower re-plan: WC R(5.6, 7.3, 6.9, 8.6), pan on
  the north wall; shower R(5.0, 8.6, 6.9, 9.6); basins u 6.9–8.2 as now.
- **SH-E, R(11.4, 2.8, 12.0, 3.5), main → lower**: `dress` wardrobe corner / `gens` NW corner,
  0.45 m from the ensuite WC (10.95, 2.95). Move the `gens` shower to u 12.0–13.2. Terminals through
  `green-r`, >3 m from `deck-r`.

**MEP-03 · MAJOR · kitchen hood.** The hob at (4.95, 11.3) has the road `hall-r` above it. A wall
outlet onto `t-south` would put cooking smell on the dining terrace and back through the 1.6 m
slider, against rule 1.3. Correction: move the hob to v 11.55–12.15 on the west counter. Run a Ø150
duct 0.5 m to SH-K, then straight up through the plant room in a fire-rated enclosure to ≥1.0 m
above the road roof (≈1682), about 6 m and two bends. Allow make-up air (a trickle inlet or a
damper interlocked with the hood).

**MEP-04 · MAJOR · water storage.** 8 people × 150 L/p/d × 2 days ≈ 2.4 m³, plus summer
irrigation of ≈0.5 m³/d. Specify **3–4 m³** (two 1.5–2 m³ tanks) plus a booster set (`assumption`).
3–4 t on the top storey over the kitchen adds roof-level seismic mass and leak risk; 5.5 m² cannot
also hold boiler, cylinder and booster (needs ≈10 m²). Low tanks, 7.4 m below the road, also fill
better from a weak intermittent main.
Correction: a ground-bearing water room on the lower floor, **R(5.0, 13.4, 6.8, 16.4)** (5.4 m²),
with tanks, booster, filter/softener and a floor gully. Recover laundry/store area (rule 6.7,
12–14 m²) by extending the lower west strip to **u 3.8 for v 11.6–16.4** (+5.8 m², ≈16 m³ more
digging; ground 1672.2–1673.1). The road plant room keeps 5.5 m² for heating only.

**MEP-05 · MAJOR · ventilation.** Windowless rooms, all `measured`:
- main `pantry`, `wc-m`, `sh-m`, `wudu`, `wlob`: buried 0.6–0.7 m, with the garage slab above;
- lower `wc-l`, `sh-l`, `lav` (ground 1673.0–1673.4, 3+ m above the floor), `gens`;
- `hall-l` gets only borrowed air.

Correction: whole-house heat recovery (MVHR, ≈0.6 × 0.6 × 1.2 m, road plant) or individual fans;
extract WC 15, shower/wudu 25, pantry 10, laundry 30 L/s (`assumption`); supply to `hall-l` and
lounge. Main ducts run under the garage slab to SH-W (≤4.5 m); lower to SH-W, `gens` to SH-E.
Terminals on the road roof or green roof, never the east façade (winter wind mostly E, REPORT.md).

**MEP-06 · MAJOR · drying room.** `laundry` (15.0 m²) has no window: its west wall is buried
2.2–2.6 m and its south wall at v 16.4 has 1.2–1.9 m of earth against it. Indoor drying there for 8
people will grow mould. Correction: a heat-pump (condensing) dryer, a 30 L/s boost extract to SH-W,
and a dehumidifier gully. Outdoor drying goes on `loggia` or `t-low`.

**MEP-07 · MAJOR · heating and gas.** Heated net area is ≈402 m² (`measured`, rooms excluding the
garage). The peak load is 16–40 kW depending on insulation (`inferred`); a heat-loss calculation
is required. Correction:
- room-sealed condensing boiler + 300 L indirect cylinder in road `plant`, vertical flue through
  the road roof; no open-flued appliance the hood can depressurise;
- gas meter at the forecourt boundary near (−1.0, 1.8), seismic shut-off valve, kitchen gas
  detector; hob gas down SH-K in its own ventilated sleeve;
- underfloor heating on the lower slab-on-grade.

**MEP-08 · MAJOR · electrical.**
- Load: lift (MRL, ≈5.5 kW 3-phase), two sewage pumps, booster, MVHR, kitchen, and possibly EV
  charging in the garage, so ask for a **3-phase supply** (`assumption`).
- Electricity and water meters at the forecourt boundary near (−5.5, 10.0); the water-meter pit is
  insulated and ≥0.8 m deep.
- Main board in `lobby-r` (0.6 × 0.25 m recess), sub-boards by the core per floor; lift
  controller at the road landing, with automatic rescue device.
- Grid outages occur in Iran (`inferred`): sewage pump, booster, boiler controls and lighting on
  a 3–5 kVA battery inverter, or nobody can flush.
- Lay the foundation earth electrode in the footings before concrete is poured.

**MEP-09 · MINOR.** `wc-r` sits on a suspended slab over the kitchen; `ens` sits over a void. Recess
the structural slab 0.2–0.25 m at R(7.0, 11.6, 9.0, 13.3) and R(9.4, 1.1, 11.4, 5.0) for level
showers and tanking. No pipe joints in the kitchen ceiling.

**MEP-10 · MINOR.** `green-r` 41.3 m² (`measured`): extensive sedum (≈150 kg/m² saturated,
`assumption`), drip-fed from the booster. Lawn 74.4 m² ≈0.4 m³/d in summer. Backflow preventer,
separate branch.

**MEP-11 · MINOR.** Pipe runs from the road cylinder to the lower fixtures are ≈15–20 m. Add a
hot-water recirculation loop via SH-K and SH-W, and a 10 L point-of-use heater at the tea bar
(13.4, 7.7).

**MEP-12 · MINOR.** SH-W through the garage: fire-rated, gas-tight, no openings (car CO). Road WC
drain under the forecourt ≈0.4 m deep: insulate or lay ≥0.8 m (frost depth `unknown`).

**MEP-13 · MINOR.** Evaporative coolers (common in Iran) need ≈0.5 × 0.5 m ducts to each floor,
which no shaft allows. Decide now; split heat pumps need only refrigerant pipes in SH-K/SH-W, outdoor
units on the road roof.

## What C10 gets right

- Wet and service rooms grouped in the buried NW; the risers need only small moves.
- Kitchen sink over the lower store: a natural stack.
- Main ensuite and lower seated ensuite adjacent across u 11.4.
- Road plant room with a 1.2 m door to the hall: replaceable plant, good boiler spot.
- Honest note that pantry and wudu cluster need mechanical ventilation.
- Lower slab on grade: level showers and floor gullies are easy.

## Out-of-scope notes

- Stormwater must stay out of the sewage pump (drainage). Lift pit ≈1668.7 needs tanking and a sump.
- Road level overhangs the main floor 0.3 m at v 13.0–13.3 (structure). Buried walls need tanking.
