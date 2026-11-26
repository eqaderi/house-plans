# 14 · Landscape and outdoor living review of C10 (LND)

Concept-stage review; nothing is engineered or code-checked. Heights come from the survey TIN (inferred). Sun hours are my own ray-cast (`simulation_result`): house as solid blocks, PVGIS horizon, no trees or neighbours.

## Summary

1. Outdoor tiers 1677.4, 1673.6 and 1670.0 each match a floor level. The play lawn at 1667.60 does not: it is 2.38 m below the garden terrace, reached only by 14 steps, and cannot be seen from the lounge.
2. The "74 m² lawn" is a wedge 7.45 → 2.7 m wide. The largest rectangle to play in is 4.0 × 7.5 m (30 m²).
3. The "tree bank" is 1.2–2.8 m wide at 31–33%. Its four trees sit 0.76–1.25 m from a fill wall: they cannot be the big trees the owner asked for.
4. The court-to-garden stair drops 2.30 m in 2.0 m and cannot be built. The south path passes 0.5 m from the boys' window.
5. Fix: one garden floor at 1669.85 (86 m²), a 53 m² tree bank, an easy south stair of 23 risers, a wheelbarrow route, a store, a water tank and guards.

## Findings

| ID | Sev | Where | Issue |
|---|---|---|---|
| LND-01 | BLOCKER | `gs-court`, `path-s` | 2.30 m drop in 2.0 m; 1.0 m path at the boys' window |
| LND-02 | MAJOR | `lawn`, `gs-lawn` | extra 2.38 m tier; lawn not step-free (rule 5.4 spirit) |
| LND-03 | MAJOR | `lawn` | 30 m² usable rectangle; hidden from the lounge |
| LND-04 | MAJOR | `bank` | trees 0.76–1.25 m from the wall on a 1.2–2.8 m strip |
| LND-05 | MAJOR | all edges | drops of 1.1–3.8 m without guards |
| LND-06 | MAJOR | road → lawn | no route for barrow, mower or soil except through the house |
| LND-07 | MAJOR | `lawn` | lawn in cut under a 2.4 m wall acts as a sump; no outlet |
| LND-08 | MAJOR | `court-w` | hayat only about 28 m² open; owner's westward dig is right |
| LND-09 | MINOR | `lawn` | no afternoon sun; NW wedge gets 0 h in winter |
| LND-10 | MINOR | laundry | no outdoor drying |
| LND-11 | MINOR | — | no herbs or vegetables |
| LND-12 | MINOR | garden | no irrigation or water source |
| LND-13 | MINOR | `t-low`, `loggia` | wind screen, rain path |

## Finding details

**LND-01 · BLOCKER.** `gs-court` R(4.6,16.4,6.6,17.4) falls 1673.60 → 1671.30 in 2.0 m, a 115% gradient (measured). Thirteen risers need at least 3.6 m. `path-s` is 1.0 m wide and descends 3.8 m on natural ground (1671.22 at u 6.6 → 1667.40 at u 18, measured) with no step design. At the boys' window (sill 1670.90) the path is at 1670.12, so a passer-by's eye is level with the room at 0.5 m.
*Correction:* with the garden at 1669.85 (LND-02) the drop is 3.75 m.
- 23 risers of 0.163 m, goings 0.35 m (2R+G 0.68).
- Flights of 8/8/7 with two 1.2 m landings: 9.4 m of run, u 4.6 → 14.0, then level to the garden.
- Excavate as needed (the owner allows it).
- 1.2 m clear width, in v 17.2–18.4 if the setback allows paths at grade (*unknown, confirm*).
- A 0.8 m shrub buffer, 1.2 m tall, in front of the bedroom glass.
- A 0.25 m wheel channel beside the steps.

**LND-02 · MAJOR.** The garden terrace (1669.98, 24.3 m²) and the lawn (1667.60) are split by a 2.38 m wall. The only link is one 14-riser flight, 0.170/0.277, 1.2 m wide, with an open 2.4 m side drop (measured). The grandparents and the lounge reach the terrace step-free but never the lawn. This contradicts "continuous, nearly level, as few level changes as feasible".
*Correction:* one garden floor.
- Paving at 1669.98, u 18.0–20.6.
- Lawn at 1669.85 with a 1.5% fall east, joined to the paving by a flush 0.13 m kerb or a 1.6 m long 1:12 ramp.
- Downhill edge on the line u + 0.448 v = 27.5, for v 1.0–17.42.
- Result: **86 m² level**, fill about 184 m³ (C10: 70 m³), downhill wall 3.0–3.2 m (measured).
- The bank becomes **53 m²**, 2.3–3.8 m wide.
- The 14 steps go.

The alternative edge, 28.5, gives 103 m² but needs 238 m³ of fill and a 3.3–3.6 m wall, and leaves no room for trees.

**LND-03 · MAJOR.** Lawn width is 7.45 m at v 1, 4.32 m at v 8 and 2.7 m at v 17.4. The largest rectangle is 4.0 × 7.5 m (measured). The sightline from a standing eye in the lounge (u 16, 1671.6) over the terrace edge (20.6, 1669.98) hides the lawn up to u ≈ 27.4, which is nearly all of it. Nobody can watch the children from the tea bar.
*Correction:* LND-02 fixes both. The garden floor is flush with the lounge, with a 4.0 × 9.0 m lawn rectangle plus 2.6 m of paving.

**LND-04 · MAJOR.** Tree spots (28.97,2.0), (27.18,5.6), (25.39,9.2) and (23.6,12.8) are 1.25/1.08/0.92/0.76 m from the 1.1–1.33 m lawn wall and 1.7–2.0 m from the boundary (measured). The drawn crowns are 2.1–2.5 m wide: shrubs. Roots this close will lift a fill wall and its drain.
*Correction (ai_judgment; distances are assumptions pending soil and arborist advice):*
- Three trees on the 53 m² bank, on the line u + 0.448 v = 29.8, at v 2.5, 6.0 and 10.0 (u 28.7 / 27.1 / 25.3). This frames, not fills, the living view axis at v 7–9.5.
- About 2.0 m from the wall face, with 1.2 m deep root barriers. The wall is designed for root and slope loads.
- Species, deciduous, deep-rooted, drought-hardy, 8–12 m, leaves that move in wind: *Celtis australis*, *Fraxinus angustifolia*, Zagros maple; *Quercus brantii* for the long term. Avoid poplar and plane (roots) and walnut (juglone, fruit drop on the lawn).
- A tree on ground at about 1666.2 tops out near 1676, which puts it in the foreground of the main-floor view (eye 1675.2).
- Crowns will overhang the neighbour by 1.5–2.5 m; consent is *unknown*.

**LND-05 · MAJOR.** No guards are drawn. Measured drops:

| Edge | Drop |
|---|---|
| Terrace east edge | 2.38 m |
| Lawn downhill edge | 1.1–1.33 m, then 33% to the boundary |
| Loggia south edge | about 2.1 m |
| Arrival court south-east | 1.7–2.4 m |
| Forecourt south edge | 3.0 m; 3.8 m once the hayat is dug |

*Correction:* 1.1 m non-climbable guards (gaps under 0.10 m, no horizontal rails; the height is an assumption until checked against national regulations) on every drop over 0.6 m. On the garden downhill wall, add a 1.0 m hedge inside the guard and a 2.0 m ball-stop net between the trees.

**LND-06 · MAJOR.** Road to the C10 lawn is 9.8 m of vertical by exterior steps, or through the garage, lift and lounge. About 15 m³ of topsoil, plus mulch and prunings, cannot go through the bedroom floor.
*Correction:*
- Route road → hayat → south stair (LND-01) → garden, all 1.2 m wide with wheel channels.
- A 1.5 × 2.5 m garden store at the south tail (u 18.0–20.5, v 15.0–17.4) for mower, hoses and toys.
- A 1 m² compost bay beside it.
- Taps at the garden, the south terrace and the hayat.
- Bulk soil pumped or craned from the road.

**LND-07 · MAJOR.** The C10 lawn is in cut up to 1.15 m at its north-west (natural 1668.75 at (20.6,1.0), measured), below a 2.4 m wall, catching roof and terrace runoff. It sheds onto the neighbour.
*Correction:*
- 1.5% fall to the east.
- A slot drain at u 20.6.
- A drainage layer and pipe behind the downhill wall, discharging to a sized soakaway or the legal outlet. The outlet and storm intensity are *unknown*.

**LND-08 · MAJOR · hayat.** `court-w` is 34 m², but its leg at u 0–2, v 9.6–11.6 lies under the road hall slab, leaving about 28 m² open. The forecourt is a car apron on 3.0 m of fill. The owner is right.
*Correction:*
- Dig the triangle west of u −1.2, v 11.6–17.42, to 1673.60. Natural ground there is 1674.2–1676.9, so the cut is up to about 3.3 m.
- This adds about 39 m², for a **sunken hayat of about 60 m²** (a *godal-baghche*) net of the new road stair.
- Plant one small tree (pomegranate or lilac) and a small pool on the south side.
- About 90 m³ of extra cut, plus C10's 228 m³, roughly feeds the LND-02 fill (inferred; bulking and soil suitability unknown).

**LND-09 · MINOR.** Mean sun on the C10 lawn is 8.0 / 5.2 / 3.3 h (June / March / December). Sun ends at about 12:50 solar time at equinox. The NW wedge (u 21–23, v 1–5) gets 0 h at equinox and in December. The south terrace gets 8.9 / 9.3 / 6.7 h. The merged garden is similar: 7.0 / 4.8 / 2.9 h.
*Correction:* afternoon shade suits July (mean 28 °C). Put winter sitting on the south terrace, and plant no tall trees south-east of the garden.

**LND-10 · MINOR.**
*Correction:* a drying strip of about 6 m² with a 1.5 m screen at the north end of the road-level roof terrace (u 12.2–17.8, v 6.2–7.4). It gets 6.9 h at equinox and 4.9 h in December, and is reached by laundry → lift → glass door. Keep washing off the view terraces.

**LND-11 · MINOR.**
*Correction:* a 0.6 × 4.6 m herb planter at the south terrace edge by the kitchen (u 4.6–9.2, v 15.8–16.4; 9.3 h at equinox). Add two 1.2 × 3.0 m vegetable beds at the garden's south tail (4.7 h at equinox).

**LND-12 · MINOR.** The summer is dry (July RH 20%). An assumed 35 mm/week for 20 weeks gives about 50 m³ per season for 70 m² of lawn.
*Correction:* drought-tolerant turf on the play area only, and drip irrigation elsewhere. Bury a 10–15 m³ rainwater tank in the garden fill, fed from the roofs. Mains top-up is needed; supply is *unknown*.

**LND-13 · MINOR.** The regional model gives E winds 22% of the year (26% in winter) and W in summer (inferred). The garden faces the winter wind.
*Correction:* a 1.8 m glass screen at the terrace's north end (v 2.8). The trees act as a permeable windbreak and give the leaf sound. Add a rain chain at (18.0, 16.4) into a gravel rill along the lawn edge. Keep the covered loggia for watching rain.

## What C10 gets right

- The arrival court and the 45 m² south terrace are level and joined: one sunny outdoor room off the kitchen.
- Every tier except the lawn matches a floor level.
- The covered loggia and the balcony-shaded terrace give rain cover and summer shade.
- The garden stays inside the setbacks, with about 151 m² east of u 18 (rule 4.7).
- The lawn follows the contour; it is just at the wrong level.

## Out-of-scope notes

- The north garage shutter is about 1.8 m from the road edge. The vehicle reviewer should check the car swing.
- Walls of 3.0–3.8 m near boundaries, in high seismic hazard, need geotechnical investigation and structural design.
- The new 24-riser road stair into the hayat needs a dog-leg of about 2.6 × 4.5 m.
