# 09 · Thermal comfort, energy and envelope review of C10

## Summary

1. The façades face **SSE 158°** and **ENE 68°**, not S and E. ENE glass (37 m²) equals SSE glass (37 m²); for this climate ENE should be about half.
2. No glass has summer shading. The garden lounge gets **no winter sun** (loggia cut-off 34.5°).
3. Terraces and roofs over heated rooms are drawn flush with the floors. As drawn, there is no depth for the 0.35–0.45 m insulated build-up they need.
4. Heat loss is about **16 kW with a good envelope** and about 46 kW built the usual local way. The 6.1 m² plant room has no flue, no riser and no confirmed fuel.
5. The buried NW must be insulated outside and mechanically extracted, or it will grow mould. Keep the road roof (126 m²) free for PV and solar hot water.

## Findings

| ID | Sev | Where | Issue |
|---|---|---|---|
| THM-01 | MAJOR | all façades | ENE glass equals SSE glass; ENE loses heat in winter and overheats summer mornings |
| THM-02 | MAJOR | main v13.0; `boys`/`girls` v16.4 | SSE glass has 0–0.3 m of shading |
| THM-03 | MAJOR | `lounge` slider v11.6 | Covered loggia blocks all winter sun |
| THM-04 | BLOCKER | `t-south`, `deck-r`, `green-r`, balconies, lower slab | No build-up depth for insulation |
| THM-05 | MAJOR | `deck-r` at u12.2; `t-south` at v13.0 | Snow drifts against step-free doors |
| THM-06 | MAJOR | `balc-m`, `balc-e` u17.8–19.4 | Cantilever slabs are thermal bridges |
| THM-07 | MAJOR | buried NW | Earth-contact walls next to the wettest rooms |
| THM-08 | MAJOR | `garage` over main | Unheated garage forms the ceiling and walls of heated rooms |
| THM-09 | MAJOR | `plant` u3.4–7.0, v11.6–13.3 | Too small, tanks over the kitchen, no flue, fuel unknown |
| THM-10 | MAJOR | distribution | No riser; hot water 19–25 m of pipe from the far fixtures |
| THM-11 | MAJOR | stair u6.8–9.4 | 10.8 m stack; no outlet at the top for summer night cooling |
| THM-12 | MAJOR | road roof | PV and solar-thermal space not reserved |
| THM-13 | MINOR | lower east edge; living over loggia | Exposed floors |

## Finding details

**THM-01 · Glass balance.**
- **Orientation** (measured): +u is at grid bearing 67.19°, plus 0.78° convergence, so 68.0° true.
- **Glass** (measured; windows 1.5 m, glazed doors 2.4 m assumed): SSE 37.4 m², ENE 37.1, NNW 9.0, WSW 2.0.
- **Sun on ENE** (measured): on 21 Dec, sun only 08:00–09:00 at 8.5–17.7°, against a 10.3° east horizon. On 21 Jun, 06:00–09:00 at cos i 0.97–0.58 and profile 13–52°, which no overhang stops.
- **Dec–Feb balance per m²** (inferred; g 0.5, Uw 1.3): ENE gains 0.40 kWh/day and loses 0.58. SSE gains 1.30 and loses 0.58.
- **Correction:**
  - Delete the living ENE window (v6.7–8.6) behind the L-sofa; use a 0.6 m clerestory at +2.4 m (helps rule 3.1).
  - Cut the master NNW window to u15.1–16.3 and the grandparents' NNW window to 1.0 m.
  - Glazing: Uw ≤ 1.3 everywhere; Uw ≤ 1.0 (triple) on ENE and NNW.
  - External roller or venetian blinds on all six ENE openings.

**THM-02 · Unshaded SSE glass.**
- **Sun angles** (measured): profile 58–70° in mid-August and 42–57° in late September (monthly means 27.9 and 23.3 °C); 34° at Dec noon.
- **Correction, main floor:** a 1.0 m canopy or light shelf at +2.6 m over u4.6–17.8, v13.0–14.0. At Dec noon it still leaves 80% of each opening sunlit.
- **Correction, boys and girls:** a 0.9 m brise-soleil at +2.7 m (v16.4–17.3, inside the 17.42 setback). It shades about 85% of the window at a 68° profile and none of it in December.

**THM-03 · Lounge has no winter sun.**
- **Why:** the loggia roof is 4.8 m deep at 3.3 m height, so it cuts off sun below atan(3.3/4.8) = 34.5°. The Dec-noon profile is 34°, so no sun reaches the slider.
- **Correction:** turn the 8.2 m² of south terrace over the loggia (u15.4–17.8, v13.0–16.4) into an open vine or louvre pergola.
  - The remaining 1.4 m overhang lets full winter sun onto the slider and fully shades it in summer.
  - Main-floor terraces drop from 69 to 61 m², which still meets rule 4.3 (ai_judgment).

**THM-04 · No build-up depth (BLOCKER as drawn).**
- **As drawn:** terrace finishes are 0.02–0.05 m below FFL and every slab is a uniform 0.30 m.
- **What is needed:** 116 m² of terrace and roof sits over heated rooms (measured). Each needs falls, membrane, XPS 160–200 mm and pavers: 0.35–0.45 m.
- **Correction:**
  - Drop the structural slab 0.45 m under the terraces, roofs and balconies; lower clear height stays about 2.9 m.
  - Falls ≥ 1.5% away from the house.
  - 150 mm slot drains at flush thresholds, keeping the floors step-free (rule 5.4).
  - Lower slab formation: 0.58 m below FFL, not 0.35, for about 35 m³ more cut (inferred).

**THM-05 · Snow drift.**
- **Snow load:** ground snow 1.5–2.5 kN/m² (assumption; confirm from the Iranian national building regulations, Part 6).
- **Drift** (inferred): off the 12.2 m road roof, about 0.7–0.8 m deep and 3 m wide, adding 1.9–2.6 kN/m². It lands against the lobby door (11.4, 8.4) and the office slider. The south terrace sits under a 7.2 m wall and drifts the same way.
- **Correction:**
  - A 1.0 m canopy over the east doors (u12.2–13.2, v6.2–13.0).
  - Design the deck and green roof for drift plus 1.5 kN/m² of saturated substrate.
  - Fit overflow outlets.

**THM-06 · Balcony bridge.**
- **Problem** (inferred): 15.3 m of continuous cantilever edge (ψ ≈ 0.7 W/mK). At −10 °C outside, the inner corner falls to about 8 °C, below the 12 °C dew point, so mould forms behind the sofa (17.6, 6.45).
- **Correction:** self-supporting balconies on 4 columns at u19.2 (v1.3, 6.2, 11.2, 16.2), or thermal-break connectors with ψ ≤ 0.2.

**THM-07 · Buried NW.**
- **Buried area** (measured): 77 m² of buried wall; ground is +3.4 m above lower FFL at (5, 7.3).
- **Risk:** the top 1.5 m of soil is near frost in January, beside the laundry, showers and the 5×-daily wudu.
- **Correction:**
  - Outside insulation: XPS 100 mm over the top 1.5 m and 60 mm below, with tanking, drainage board and a perforated drain at 1669.3.
  - Humidistat extract: laundry 10 L/s, boosting to 30; each wet room 15 L/s.
  - A fire-rated riser at u6.2–6.8, v1.1–1.6 in the garage corner, with the workbench starting at v1.7.

**THM-08 · Garage as cold buffer.**
- **Problem** (measured): 28.9 m² of garage floor is the ceiling of the wudu, WC, pantry and hall, and 50 m² of garage wall adjoins heated rooms.
- **Correction:**
  - 100 mm mineral wool under the garage slab.
  - 80 mm on the shared walls.
  - A gasketed, self-closing insulated door to the lobby.
  - Foam-filled shutters with brush seals.
  - 100 mm on the garage roof so the workshop stays above 0 °C.
  - No uninsulated pipes in the garage.

**THM-09 · Plant and fuel.**
- **Heat loss** (inferred): about 1,018 m² of envelope. With walls 0.30, roof 0.20, Uw 1.3 and n 0.5, H ≈ 545 W/K, or 449 W/K with heat-recovery ventilation. Built the usual local way (walls 1.2, Uw 2.8), about 1,530 W/K.
- **Design load:** at ΔT 30 K (assumption: −10 °C outside), 16.4 / 13.5 / 46 kW. Heating degree-days are about 2,300–2,500 K·day.
- **Correction:**
  - An 18–24 kW condensing system boiler.
  - A 300 L solar cylinder (8 occupants, assumption).
  - A vertical flue through the roof at (4.2, 12.9), ≥ 1.0 m above the finish. Not through the south wall.
  - Move the tanks (1–2 t over the kitchen span) to a buried 3 m³ cistern under the arrival court.
- **Fuel (confirm):** a gas main at the road is unconfirmed. If there is none, a heat pump or oil tank needs about 9 m² of plant room.

**THM-10 · Distribution.**
- **Riser:** add a 0.6 × 0.6 m shaft at u5.0–5.6, v12.4–13.0, through the plant room (road), the kitchen counter's dead corner (main) and the laundry (lower).
- **Hot-water pipe runs** (measured): guest ensuite about 25 m, tea bar 20 m, master ensuite 19 m. At 5 L of pipe, the wait is 35–45 s at a shower (inferred).
  - **Correction:** an insulated hot-water return loop with a timer pump.
- **Emitters:** underfloor heating at 35–40 °C with ≤ 50 mm screed on the lower and main floors; radiators at road level.
- **Load density:** living room about 60 W/m² at Uw 1.3 but about 85 at Uw 2.8, beyond what underfloor heating delivers; depends on THM-01.

**THM-11 · Stair stack.**
- **Problem:** the 10.8 m stack creates about 11 Pa at design conditions (inferred). Warm air leaks out of the road-level doors while the lower bedrooms run cold. The stair has no rooflight.
- **Correction:**
  - Airtightness n50 ≤ 3 /h.
  - Zone each floor separately.
  - Optional: a draught-lobby door at u1.5 (owner decision; rules 2.4 and 2.6).
  - A motorised rooflight 2.4 × 1.0 m (≥ 1.2 m² free area, rain sensor, security grille) over the stair.
- **Summer purge** (inferred): with 4 K ΔT over 9 m, about 1.1 m³/s, roughly 3.4 air changes per hour. Inlets: secure night vents in the lower rooms and 0.1 m² transfer grilles over the bedroom doors. Fans plus two small splits cover the rest; no ducted evaporative coolers.

**THM-12 · Roof for solar.**
- **Space:** about 85 m² of the road roof is usable.
- **Correction:**
  - PV in 3 rows facing true south, tilted 30–35°, at a 3.9 m pitch: 6.8–8.1 kWp, roughly 11–14 MWh/yr (inferred; confirm with PVGIS).
  - 4–5 m² of solar-thermal collectors above the plant room.
  - A 0.9 m roof hatch; no roof stair housing.

**THM-13 · Exposed floors.**
- **Problem** (measured): 34 m² of lower slab sits over a void averaging 0.48 m deep, and 3.4 m² of living-room floor sits over the open loggia.
- **Correction:** 120 mm insulation under both, a closed perimeter, and footings below frost depth (frost depth unknown).

## What C10 gets right

- Day rooms and the children's rooms face SSE, the ideal winter-gain orientation.
- Almost no WSW glass (2 m²), which avoids the hot summer afternoon sun.
- Service rooms sit in the buried NW, where the earth gives stable temperature.
- Compact stacked floors (about 396 m² heated) around a central core keep the envelope small.

## Out-of-scope notes

- The open 3-storey stair from the garage lobby is also a smoke shaft.
- Self-supporting balconies need a seismic check.
- The road WC drains through the kitchen ceiling.
- Roof and terrace rainwater needs outlets and overflows.
