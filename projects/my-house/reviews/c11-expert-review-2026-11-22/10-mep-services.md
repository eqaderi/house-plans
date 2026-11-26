# 10 · MEP services review of C11

Concept stage; nothing engineered or code-checked. Geometry is `measured` (`design.py`, `clear_geom`, `zg`) unless marked.

## Summary

1. The big moves are right. The tanks now stand on a buried ground slab, the two ensuites stack exactly, the road WC is off the kitchen ceiling, and the hob sits under a riser that runs to the roof.
2. **The plant room shrank:** 2.95 m² clear and 1.19 m deep. C10 had 6.1 m² gross; the review asked for 9–10 m² and ≥2.4 m deep.
3. **The risers are drawn but too small:** SH-K 0.48 × 0.48 m, SH-W 0.63 × 0.48 m, SH-E 0.28 × 0.48 m clear. There is no route for MVHR trunks, and the hood duct needs Ø200.
4. **Services from the road cross an air void.** The road WC drain, the rising main, the break chamber and the mains all cross a 1.6–1.9 m void under the forecourt deck.
5. **Tanks and LPG.** The Ø1.24 m tanks cannot pass any door. The LPG cage sits in the sunken court, 2.0 m from the front door. The lifting station is not drawn.

## Scorecard

SCORECARD: fixed=2 partly=8 not_fixed=3 worse=0 new_blocker=0 new_major=6 new_minor=4

## Part A · C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| MEP-01 outfall | partly fixed | Options A/B/C are listed (LIMITS). No pit is drawn: `store-s` (1.92 × 3.34 m clear) is shelved on both sides with a 0.6 m aisle. The break chamber (−2.0, 10.5) is under the forecourt deck: ground 1675.54, deck 1677.47. | F3 answer from the owner or utility; N04, N05 |
| MEP-02 risers | partly fixed | SH-K, SH-W and SH-E run on all floors. `ens` and `gens` are both R(9.4, 1.1, 11.4, 4.5). Clear areas 0.23 / 0.30 / 0.13 m². | N02 |
| MEP-03 hood route | fixed | Hob (4.76, 11.75) under the plant room, 0.5 m from SH-K, duct to the roof. | Duct size N02; make-up air is still only a note |
| MEP-04 tanks / plant | partly fixed | 2 × ~1.5 m³ tanks on the 1673.60 slab, buried 3.0–3.9 m. The plant room got smaller. | N01, N03 |
| MEP-05 ventilation | partly fixed | MVHR named; no ducts drawn. 11 rooms are windowless (main pantry, `sh-m`, `wc-m`, `wudu`, `wlob`; lower `sh-l`, `wc-l`, `lav`, `laundry`, `gens`, `hall-l`). Main WC pan 5.6 m and shower 5.35 m from SH-W. | N02 |
| MEP-06 drying room | fixed | Laundry 4.8 m², heat-pump dryer, 0.05 m from SH-K. Drying yard on `deck-r`. | Draw the 10/30 l/s humidistat extract |
| MEP-07 heat / gas | partly fixed | Boiler and cylinder are in `plant`. No flue, gas meter, seismic valve or shut-off niche is drawn. | Concentric roof flue at ~(6.4, 12.4); meter niche in the u 0 pier at v 4.93–5.68 |
| MEP-08 power | not fixed | Notes only. Meters, board, the 1.5 m² battery cupboard and the generator inlet are not located. | Board recess in `lobby-r` at u 12.3–12.6, v 7.5–8.1; battery cupboard R(5.4, 1.1, 6.8, 2.8) in `bulk`, fire-separated |
| MEP-09 wet over rooms | partly fixed | Positions are fixed: `wc-r` over the entry, `ens` over `gens`. `SETDOWN` covers terraces only. | Recess the slab 0.20–0.25 m at R(2.0, 11.6, 4.4, 13.0) and R(9.4, 1.1, 11.4, 2.9) |
| MEP-10 irrigation | partly fixed | Extensive green roof; cistern under `t-low`. | Cistern pump, irrigation branch with backflow preventer, drip line to `green-r` |
| MEP-11 dead legs | not fixed | Cylinder → `gens` ≈22 m (`inferred`); notes only. | Return loop up SH-K/SH-W; 10 L heater at the tea bar |
| MEP-12 garage riser / frost | not fixed | SH-W in the garage is an unspecified box. The road WC drain now crosses an air void (N04). | 60 min gas-tight box, no access panel in the garage |
| MEP-13 cooling | partly fixed | Split heat pumps chosen; no positions. | Outdoor units in the core roof plant zone; refrigerant lines in SH-K/SH-W |

## Part B · New problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| MEP-N01 | MAJOR | road `plant` | 2.95 m² clear, 1.19 m deep; 0.34 m in front of the kit | Merge with `store-r`, wall at v 11.3: ≈6.9 m² |
| MEP-N02 | MAJOR | SH-K, SH-W, SH-E | Too small for their contents; no MVHR trunk route; Ø150 hood duct too small | Own Ø200 hood duct; WC stack behind the pans; decentralised ventilation |
| MEP-N03 | MAJOR | main `tanks` | Ø1.24 m tanks cannot pass the 1.2 m door (≈1.1 m clear) or the 1.0 m front door | Slimline tanks ≤0.8 m wide |
| MEP-N04 | MAJOR | forecourt deck, u −3.1…0, v 5.6–11.6 | Drains, rising main, break chamber and mains in a 1.6–1.9 m air void | Mains through MW-0F at v 4.9–5.7; filled strip for the foul lines |
| MEP-N05 | MAJOR | lower `store-s` | Lifting station not drawn and does not fit; beside the boys' bed | Pit at the south end, acoustically isolated |
| MEP-N06 | MAJOR | court (−0.2…0.4, 12.3…12.9) | LPG cage in a sunken court, 2.0 m from the front door | No LPG below forecourt level |
| MEP-N07 | MINOR | `checks.py` §7.15 | Measures room edges; ignores the cylinder over the kitchen | Test fixture → riser; bund the plant room |
| MEP-N08 | MINOR | lower `wc-l` | Pan centre 0.31 m from SH-W, 0.29 m from the wall | Pan to (5.95, 9.85), facing north |
| MEP-N09 | MINOR | road roof, lounge | Hood terminal 2.67 m from the hall rooflight; tea-bar drain in a cold crawl void | Fixed rooflight or terminal ≥3 m away; lag and trace-heat the drain |
| MEP-N10 | MINOR | main `tanks` | "Gravity feeds the lower floor" gives ≈2.2 m head | Every outlet on the booster |

## Part B · Details

**N01 · plant room.**
- The kit (boiler, cylinder, MVHR) is drawn at R(5.55, 12.0, 7.25, 12.8). The room's clear depth is v 11.66–12.85.
- That leaves no room for UFH manifolds, expansion vessels, the solar-thermal station or the inverter.
- An MVHR needs about 0.6 m in front of it for filter changes (`assumption`).
- **Fix:**
  - Plant becomes R(4.4, 11.3, 9.4, 13.0): ≈6.9 m² clear after SH-K.
  - `hall-r` keeps 1.68 m clear, leaving 1.23 m in front of the lockers.
  - The 1.2 m door moves to u 6.0–7.2.

**N02 · risers.**
- Hood (`inferred`): at 600 m³/h a Ø150 duct runs at 9.4 m/s and loses ≈170 Pa, so the hood delivers 350–400 m³/h. A Ø200 duct runs at 5.3 m/s and loses ≈50 Pa. Wrapped Ø200 (0.30 × 0.30 m) would leave a 0.18 m strip in SH-K. Fix: a separate fire-rated Ø200 duct from (4.76, 11.8) through the plant room's NW corner to 1.0 m above the roof.
- SH-E is 0.28 m clear (0.24 m if MW-11.4 is 0.20 m): one DN110 stack at most. Both pans are on the west wall, at (9.75, 3.7) and (9.80, 3.4). Fix: stack duct R(9.53, 3.0, 9.78, 4.2) on both floors; SH-E carries the extracts and water.
- MVHR trunks of Ø250–315 (≈230 l/s) fit no riser. Default: wet-room extract fans into the risers, plus Ø160 single-room heat-recovery units in the four bedrooms, the lounge and the living room. A central system needs a new 0.4 × 0.8 m riser on every floor.

**N03.** Fix: two slimline 1.5–2 m³ tanks (≈0.75 × 2.4 × 1.1 m) at u 0.25–1.0, v 1.4–6.4, with a 0.7 m aisle; booster at v 6.6–7.4; overflow to a gully draining to SH-W.

**N04 · service entries.**
- Under the deck, natural ground is 1674.89–1675.54 and the deck is at 1677.47, with open air between.
- The road WC drain leaves the house at ~1677.0. It hangs in that void, then lies under only ≈0.5 m of cover at the road edge. Frost depth is `unknown`.
- **Fix:**
  - Bring water, gas and power through MW-0F in the 0.75 m pier at v 4.93–5.68. The forecourt is on fill there (natural ground 1676.84). The lines enter the tanks room at ≈1676.6 with ≥0.8 m cover; the meter niche goes in that pier.
  - Backfill a 1.2 m strip under the deck at v 10.4–11.6, up to 0.25 m below the deck, for the WC drain and the rising main.
  - Put the break chamber at (−2.0, 11.0), with its cover flush in the deck.
  - No foul pipe runs over the tanks.

**N05 · lifting station.**
- A duplex pit of 1.2 × 1.2 × 1.5 m plus its service strip needs 1.8 × 1.2 m.
- Boys' bed 1 (v 11.05–13.1) lies against LW-6.8, the wall shared with `store-s`.
- **Fix:**
  - Pit at R(4.85, 14.25, 6.05, 15.45), with a sealed acoustic lid and resilient clips; nothing fixed to LW-6.8.
  - Vent up SH-K.
  - Shelves only at v 12.9–14.1.

**N06 · LPG.** LPG is heavier than air, and the court is 3.9 m deep and walled on two sides. A leak would pool there, reach the gullies and the court stair, and enter by the porch door (2.0, 10.1–11.1). Fix: natural gas with a seismic valve (if F4 confirms a main), or a forecourt cage at ~(−1.0, 2.0), ≥1 m from openings and ≥2 m from drains, piped to the burners.

**N07.** `checks.py` line 447 measures room edges and `over_k` sees only wet rooms. Add a 100 mm bund, a gully to SH-K, a leak shut-off valve, and a T&P tundish to SH-K.

**N10 · water pressure.** The tank's mid-level is ≈1674.2 and a lower shower head is at ≈1672.0. That gives 0.22 bar, unbalanced against the hot side (`inferred`). Put every outlet on a duty/standby booster on the battery circuit.

## What C11 gets right

- 3 t of water moved off the kitchen ceiling onto a buried, frost-free slab.
- The two ensuites share one footprint, R(9.4, 1.1, 11.4, 4.5): true wet-over-wet stacking.
- The road WC is off the kitchen ceiling and drains west by gravity.
- Hob and sink are ≤0.5 m from SH-K; the hood vents through the roof, not onto the terrace.
- Three continuous risers, none through a bedroom; compact laundry with a heat-pump dryer.

## Out-of-scope notes

- **Structure / daylight.** The main ensuite window (u 10.0–10.6, v 1.1) faces the PW-N piles at v 0.85.
- **Drainage.** The lift-pit drain must stay off the foul system.
