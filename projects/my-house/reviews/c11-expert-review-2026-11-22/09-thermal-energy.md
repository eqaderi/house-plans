# 09 · Thermal comfort, energy and envelope review of C11

## Summary

1. C11 draws real walls, sets the slab down 0.25 m under the roof terraces and puts the balconies on their own columns. But none of my 13 C10 findings is fully fixed.
2. The ledger says the envelope, snow, insulation, return-loop and PV items were added as "notes". No C11 file contains any of them.
3. Measured ray-casts: the lounge gets 0.73 sun-hour-equivalents on 21 Dec (claimed: 2.8 h). The children's glass is 80–100 % sunlit on mid-August mornings.
4. New conflicts:
   - The north piles overlap the buried wall by 0.225 m.
   - 0.45 m columns fill the 0.40 m south wall.
   - The plant room is 3.0 m² clear and has no flue.
5. The garage is now the cold ceiling over 56.7 m² of rooms (C10: 28.9). STR-01 makes that necessary, but C11 gives no insulation for it.

## Scorecard

SCORECARD: fixed=0 partly=11 not_fixed=1 worse=1 new_blocker=0 new_major=3 new_minor=3

## Part A · C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| THM-01 glass balance | partly fixed | measured: windows 1.5 m, glazed doors 2.4 m.<br>- ENE glass is 28.3 m² (C10: 37.1); SSE 34.7; ENE/SSE 0.82 (target ≤0.5).<br>- Done: living ENE window replaced by a clerestory; master north window cut; grandparents' north window gone.<br>- Not done: no blinds, no Uw. | - Delete the lounge ENE window (u 18, v 6.6–8.4).<br>- Office slider 1.8 → 1.2 m. ENE then falls to about 24 m².<br>- External blinds on the 6 remaining ENE openings.<br>- Uw ≤1.3, and ≤1.0 on ENE and NNW. |
| THM-02 SSE shading | partly fixed | inferred, ray-cast.<br>- The 1.0 m canopy is only a dashed rectangle on the plan: no height, not in `structure()` or 3D.<br>- If built at 1677.2, the kitchen slider is sunlit 0 / 40 / 100 % at noon in Jun / Aug / Dec.<br>- Children's windows, 15 Aug: 100 / 80 / 53 % sunlit at 08 / 10 / 12 h. | - Canopy in `structure()` at 1677.2 on thermally broken brackets.<br>- 0.6 m louvre at 1672.45, v 16.0–16.6, over both children's windows. August sun becomes 45 / 20 / 0 %; December loses ≤27 %. |
| THM-03 lounge sun | partly fixed | inferred, ray-cast for 21 Dec.<br>- The pergola is drawn.<br>- The slider gets 0.73 sun-hour-equivalents (C10: about 0).<br>- The solid covered walk (v 15.2–16.4) and RC-18L block the rest. | - Glazed walk roof: about 1.35 h.<br>- Also open RC-18L at v 13.4–15.2, if the engineer allows: about 1.8 h. |
| THM-04 build-up depth | partly fixed | measured: set-down 0.25 m on t-south, deck-r and green-r; §7.8 passes; formation 0.60 m.<br>Inferred, with XPS 180 mm and falls 1:60: 0.38 m is available. t-south needs 0.33 and deck-r 0.37, so both fit. green-r needs about 0.46, so it does not (N04). | Write the build-up layers on the page. |
| THM-05 snow | partly fixed | measured: the south canopy shelters the main sliders. The lobby door (12.6, 8.4) and the office slider (12.6, 11.9) sit 20 mm above a deck 3.3 m below the road roof. That is the drift zone, and nothing is drawn there. There are no parapets or snow guards. | - 1.2 m canopy at 1680.2 over u 12.6–13.8, v 7.6–12.9.<br>- 0.5 m parapets with snow guards on the south and east edges.<br>- Design deck-r for drift (assumption). |
| THM-06 balcony bridge | partly fixed | measured from `checks.json` support: the balconies bear on the house wall for 10.5 + 3.5 m. 13.8 m of slab still crosses the insulation at u 18.25, with ψ of about 0.35 (inferred). | Shear-only thermal-break connectors (ψ ≤0.2) along u 18.25, v 2.6–16.4, or a separate slab with a 30 mm insulated joint. |
| THM-07 buried NW | partly fixed | measured from `zg`.<br>- Buried wall is about 101 m² (C10: 77), up to 3.6 m deep.<br>- Main wet cluster is now interior, which is good.<br>- The lower bathroom and laundry are still on the u 4.6 wall.<br>- Tanking and XPS appear only in the ledger; on the north side they are impossible (N01).<br>- No extract rates. | - XPS 100 / 60 mm with tanking, once N01 is fixed.<br>- Humidistat extract: laundry 10/30 L/s, each wet room 15 L/s. |
| THM-08 garage | **made worse** | measured: the garage covers 56.7 m² of rooms (C10: 28.9). The fire door and stair screen are drawn. No insulation is specified. | - 120 mm under the garage slab.<br>- 80 mm on RW-9.5, RW-6.8 and the core wall.<br>- 100 mm under the garage roof.<br>- Sealed, insulated shutters.<br>- Tanks room kept ≥5 °C. |
| THM-09 plant and fuel | partly fixed | measured.<br>- Done: tanks moved off the kitchen.<br>- Plant room is 3.0 m² clear and 1.19 m deep, with 0.34 m in front of the equipment (asked: ≥9 m²).<br>- No flue. SH-K is the grease-duct riser, so it cannot take one.<br>- Fuel is unknown.<br>- Heated area about 454 m². Load about 18–19 kW with a good envelope, 52 kW built the usual local way (inferred). | - A separate vertical flue at about (6.8, 12.3), ≥1.0 m above the roof.<br>- Merge store-r into the plant room: R(4.4, 11.6, 9.4, 13.0), about 5.8 m².<br>- If there is no gas, a heat-pump pad on the road roof. |
| THM-10 distribution | partly fixed | measured: SH-K, SH-W and SH-E are drawn where asked.<br>Inferred runs: 19 m to the master ensuite, 25 m to the seated ensuite, 26 m to the tea bar. No return loop is written anywhere. | - Insulated return loop with a timer pump.<br>- 10 L heater at the tea bar.<br>- Underfloor heating at 35–40 °C in the 0.15 m build-up. |
| THM-11 stair stack | partly fixed | measured: the glazed screen at the road stair mouth is drawn. The only rooflight is over the road hall, R(7.6, 9.6, 9.0, 11.5), not the stair. No n50 target. | - Motorised rooflight 2.2 × 1.2 m at u 7.0–9.2, v 1.5–2.7.<br>- n50 ≤3/h.<br>- One heating zone per floor. |
| THM-12 roof solar | not fixed | measured: no PV or solar-thermal zone is drawn or written. | - Reserve R(0.4, 1.5, 9.2, 9.3), about 68 m²: 6–7 kWp plus 4–5 m² of collectors.<br>- Put terminals and rooflights in the v 9.5–13 band. |
| THM-13 exposed floors | partly fixed | measured: 21.9 m² of heated floor over outside air or a void (C10: 37.4). Lounge east 12.35 m² over a void, living SE 5.3 m² over the loggia, road hall 4.2 m² over the porch (new). None is insulated. | 150 mm soffit insulation under all three. Loggia soffit about 1672.85; porch soffit about 1677.0. |

## Part B · New problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| THM-N01 | MAJOR | north buried wall v 1.1, u 0–13.2, main and lower | The PW-N piles (Ø450 at v 0.85, so v 0.625–1.075) overlap the wall body (outer face v 0.85) by 0.225 m. About 25 m² of buried wall has no room for membrane, drainage or XPS. | Pile centre line to v 0.40, leaving 0.175 m for a blind-side membrane, 100 mm XPS and drainage. Otherwise, 60 mm inside lining plus a vapour control layer. |
| THM-N02 | MAJOR | south façade v 13.0; the slab lip at v 16.0–16.4; the SE corner | Five 0.45 m RC columns fill the 0.40 m wall. The t-south slab runs 0.4 m past the lower wall for 7.6 m. RC-18L ties into the living corner. Inner faces run about 13 °C at −10 °C outside (inferred). | Columns 0.30 × 0.65 m, long side along the wall, with ≥0.10 m of external insulation. Wrap the lip in 100 mm. Insulation return at the top of RC-18L. |
| THM-N03 | MAJOR | `CORRECTIONS.md` against the deliverable | The THM-02, THM-04, VEH-04, MEP-04/05/06 and WAT-04/10 items are marked done as "notes". `grep` finds no U-value, n50, insulation, snow or PV text in any C11 file. | Add an envelope schedule to the page: walls ≤0.30, roof ≤0.20, Uw ≤1.3/1.0, n50 ≤3, insulation layers, thermal breaks, snow load. Mark each one an assumption. |
| THM-N04 | MINOR | `green-r` | The build-up needs about 0.46 m, but 0.38 m is available. | No door opens onto it, so raise its top to about 1677.60 behind a 150 mm upstand, or set the slab down 0.35 m there. |
| THM-N05 | MINOR | lounge-east void, R(15.4, 6.2, 18, 10.95) | It is called "ventilated", but it is enclosed on every side and only 0.2–1.3 m deep. | Make it a closed void: 100 mm XPS on the perimeter, a radon/vapour membrane, a 0.6 m hatch. |
| THM-N06 | MINOR | kitchen hood | A hood of ≥600 m³/h in an airtight house with MVHR has no make-up air. | Interlocked 0.02 m² low-level inlet in the kitchen south wall at u 4.6–5.3. |

## Part B details

- **N01**, measured from `structure()` and `engine.walls()`. The exterior band puts the outer face of the wall at v 0.85, and the piles reach v 1.075. This is the coldest, wettest wall, with 3.5 m of earth at (6.8, 1.1). As drawn, it can only be insulated from the inside.
- **N02**, inferred. Each column bridge has ψ of about 0.3–0.5 W/K per storey. Together they add about 8–10 W/K to H. They make cold patches behind the kitchen sink and the dining sideboard.
- **Ray-cast** (inferred): +u at 67.97° true; obstacles are boxes at the `design.py` levels; the pergola is taken as 50 % open.

## What C11 gets right

- Real walls are deducted from room sizes. The 0.60 m formation leaves room for slab insulation and a gas layer.
- Terraces are set down 0.25 m and checked. The balconies and the loggia are uninsulated and stand on their own columns.
- The ENE living window is now a clerestory; the north windows are cut or deleted.
- The tanks and the WC are off the kitchen ceiling, and SH-K runs exactly through plant, kitchen and store.
- A glazed stair screen and a self-closing garage fire door cut stack leakage and fumes.
- The main wet cluster is buffered from the earth.

## Out-of-scope notes

- The PW-N overlap with the house wall is first a structural clash.
- SH-K cannot hold both the grease duct and a flue.
- The balcony slab and an RC-18L opening need a seismic check.
- The closed crawl void needs a radon sump.
