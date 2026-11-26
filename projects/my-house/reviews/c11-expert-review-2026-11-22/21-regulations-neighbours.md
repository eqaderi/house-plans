# 21 · Planning, zoning and neighbour relations: review of C11

Reviewer: planning/zoning/neighbours (agent:claude-code). Concept stage; nothing here is permit-ready or code-compliant. Rule figures are `assumption` unless sourced.

## Summary

1. Permit regime, building line and footpath status are still unknown (F5–F7).
2. North: the balcony now starts at v 2.6 and the north glass is obscured. However, the garden terrace `t-low` still reaches v 1.1, and the **pile wall overlaps the house wall by 0.225 m**.
3. Road: the owner's stair and W2 fill the first 1.7 m behind the road boundary, and W2's face sits *on* it. Any building line breaks rule 4.10.
4. South: a 2.2 m cut and a 1.7 m fill wall stand at the edge of the shared footpath, which has no easement.
5. Measured to the real wall faces, the gross area is 552 m² (FAR 0.92) and the cover 42.9%. `checks.json` reports 510 m² and 40% on grid lines.

## Scorecard

SCORECARD: fixed=1 partly=5 not_fixed=5 worse=0 new_blocker=0 new_major=5 new_minor=4

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| REG-01 jurisdiction | not fixed | No *estelam*; README says "permit rules unknown (F5)" | The owner obtains it before C12 |
| REG-02 storeys/height | partly fixed | §7.22 gives storey counts only, sampled at the wrong lines (`measured`, `facades()`) | Height table, REG-N07 |
| REG-03 north overlooking | partly fixed | `balc-m` from v 2.6; screen on v 6.2; north glass obscured. The see-through guard at v 2.6 is 4.2 m above the neighbour's ground, so the lot is visible from ~2 m in (`inferred`) | 1.8 m opaque return on v 2.6, u 18.25–19.85, top 1675.40 |
| REG-04 winter shade north | not fixed | Roof 1680.80 unchanged; north face now v 0.85. Noon shade on 21 Dec reaches ≈9.5–10.5 m into the lot (`inferred`, sun 31.6°, ground rising 15%) | Ask about any north-sun rule; REG-N08 |
| REG-05 children's windows | partly fixed | Glass at v 15.75 (face 16.0), 1.67 m from the path (C10 1.0 m); lower 0.6 m obscured. At u 10 the path is at 1670.0, so a walker's eye (1671.6) is just above the obscured band (top 1671.5) (`measured`) | 1.6 m hedge **on our side** at v 17.2–17.4, u 8.5–11.0 (top ≈ 1671.7) |
| REG-06 footpath status | not fixed | F7 open; C11 now builds hard edges on the path (REG-N06) | Easement before any wall on its edge |
| REG-07 south neighbour | not fixed | The girls' fallback window on u 15.4 is not drawn. A 7 m neighbour wall at v 19.42 puts the noon shade line at ≈ 1674.2 on our v 16.0 wall, above the lower ceiling (`inferred`) | Ask what the south lot may build; draw the girls' window v 12.4–13.6 onto the loggia |
| REG-08 coverage/placement | partly fixed | Beyond the v 13.05 band (`assumption`), with walls: lower 33.3 m², main 3.3 m² (C10 34.8). The court is now a cut. Fills remain: walk 1.69 m, lawn 1.33 m, forecourt 1.6 m (`measured`) | REG-N05; ask whether fill >1.0 m counts as coverage |
| REG-09 road line / shutters | not fixed | Shutters unchanged. Measured square to the road, shutter 1 is 1.56 m from the boundary at its centre and **0.76 m at its north jamb** (v 1.575) (`measured`) | Building line first; at 1 m, move shutter 1 or turn the face |
| REG-10 north lawn edge | fixed | Edge at v 1.0; SW-36 (1.0 m cut) and SW-37 (1.24 m fill) inside the parcel (`measured`) | Overlooking: REG-N03 |
| REG-11 roofs | partly fixed | Road roof hatch-only, green roof behind a locked gate. On `deck-r`'s north edge, a 1.5 m screen covers only u 14–17.8; u 12.6–14.0 has a 1.1 m guard; the plant louvre is a note (`measured`) | 1.8 m planter/screen on v 6.2 for u 12.6–18.0; draw the louvre and count its height |

## Part B: new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| REG-N01 | MAJOR | North, u 0–13.2, v 0.6–1.35 | Piles on v 0.85 overlap the drawn buried wall by 0.225 m | Piles as the outer leaf, 0.225 m lining |
| REG-N02 | MINOR | `PW-N` (D–D, F–F, 3D) | Top 1677.0 throughout: drawn up to 5.7 m above ground, 0.6 m from the neighbour | Cap at natural ground −0.2 |
| REG-N03 | MAJOR | `t-low` v 1.1; lawn NE | Overlooks the north lot from 1.0–1.1 m | Screen, or start the terrace at v 2.6 |
| REG-N04 | MAJOR | Road edge v 11.6–17.4 | Stair and W2 lie in any road widening; W2's face is on the boundary | Building line and consent first |
| REG-N05 | MAJOR | Whole house | 552 m² gross and 42.9% cover at the real faces, reported as 510 m² and 40% | Report both; owner decision |
| REG-N06 | MAJOR | South band v 17.12–17.42 | Walls up to 3 m at the shared path | Guards, parapet, easement |
| REG-N07 | MINOR | §7.22 | Wrong sample lines, no heights | Height table |
| REG-N08 | MINOR | Green roof, north edge | 1.1 m guard against the ≤0.3 m upstand of THM-04 | Anchors and a 0.3 m upstand |
| REG-N09 | MINOR | Strip v 0–0.85 | No drainage for the neighbour's runoff | Channel on the pile cap |

## Part B details

**REG-N01: pile wall against the house wall.**
- The piles (Ø450 on v 0.85) occupy v 0.625–1.075.
- `engine.py` draws the 0.25 m outer band and the 0.45 m buried wall centred on v 1.1, so the house wall occupies v 0.85–1.325.
- The two solids overlap by **0.225 m** over 13.2 m (`measured`). As drawn, either the rooms shrink by 0.25 m or the piles move to v 0.60, only 0.375 m from the neighbour.
- Correction:
  - Keep the piles on v 0.85 as the permanent outer leaf.
  - Add a 25 mm drainage composite, then a 0.225 m RC lining at v 1.10–1.325, and drop the outer band along u 0–13.2. The rooms keep their size.
  - Record the neighbour's wall and footing first (F8); a rig needs ~0.6–0.8 m clearance (`assumption`).

**REG-N02: pile top.**
- Natural ground on v 0.85 is 1677.22 at u 0, 1673.66 at u 6.8 and 1671.34 at u 13.2, yet the element top is 1677.0 throughout.
- Correction: step the capping beam down with the ground (1677.0 → 1671.1) and end the wall where the dig ends.

**REG-N03: overlooking from the lower garden.**
- `t-low` (1669.98, off the grandparents' slider) reaches v 1.1. Natural ground there is 1669.59–1668.74, so a standing eye is 2.0–2.8 m above the neighbour's ground at 1.1 m: closer than the balcony moved to v 2.6, against rule 4.3's intent.
- On the NE lawn, SW-37 holds 1.24 m of fill: an eye is 2.8 m above the neighbour (1666.4) at 1.0 m.
- Correction:
  - Plant R(18.25, 1.1, 20.6, 2.6) as a bed, with a 1.8 m opaque screen on v 2.6 (top 1671.80) and a 1.1 m guard on v 1.1 east of u 19.2.
  - On the lawn: a 1.5 m hedge on v 1.2, u 24.9–28.0.

**REG-N04: road edge.**
- W2 (0.30 m, centred 0.15 m in) has its face on the boundary. F1 sits 0.30–1.70 m behind it; L1 (1675.50) is ~1.9 m below the road.
- If the approved width exceeds the ~9 m road (`assumption`: 10–12 m), a widening of 0.5–1.5 m takes W2, F1 and L1, and rule 4.10 fails.
- A wall holding a public road needs road-authority consent and settled ownership (F6).
- Correction:
  - Get the building line before C12.
  - Keep CONSOLIDATED §4a's reduced version as the fallback.
  - W2's base stays wholly under the stair; the gate opens inward.

**REG-N05: size measured to the real faces.**
- Plates with walls: road 145.4, main 222.4, lower 184.5 m². That is **552.2 m² gross**, FAR 0.92, and a cover of 257.7 m² (42.9%).
- On grid lines: 510 m² (C10 459); the growth is mainly the service room under the garage (≈28 m²) (`measured`).
- Rule 4.7 calls "about 525–555 m² gross … covering about half the field" too big. On the external measure, C11 sits inside that band; the 147 m² east garden still passes.
- Correction:
  - Report both measures in §7.22 and the README.
  - Ask which one the authority counts, and whether the buried service room counts as basement.
  - The owner decides.

**REG-N06: shared footpath edge** (our strip v 17.42–18.42).
- W4's face is on the path edge (u −6.5…−2.98), holding the path up to 2.23 m above the stair.
- SW-29/30 hold the walk (1670.00) 1.0–1.9 m above the path; with its guard, the path faces 2.8–3.0 m of wall.
- The walk overlooks the south lot from 2.3 m to the boundary. If the path has to be widened (`assumption`: 4–6 m), there is no slack before v 16.0.
- Correction:
  - A 1.1 m guard on W4's path side.
  - A solid 1.1 m parapet on SW-29/30 (the §4c balustrade resolution).
  - The walk channels discharge into our own drainage, never onto the path.
  - The easement is in writing before these walls are built.

**REG-N07: heights** (`measured`, to slab 1680.80 or the parapet).

| Façade | Storeys | Max height above natural ground |
|---|---|---|
| West | 1 at the forecourt; 2 from the arrival court | 3.8 m / 7.7 m |
| South | 3, stepped (v 16.0, then v 13.0) | 11.3–12.0 m |
| East | 3 tiers (u 18; road block at u 12.6) | 11.1 m; 13.8 m to the road parapet |
| North | 2, at 0.85 m from the boundary | 8.2–8.4 m |

- Overall 13.3 m (1680.80 − 1667.47 at the SE corner); 14.1 m to the lift overrun; 14.5 m to the louvre.

**REG-N08: green-roof north guard.** The 1.1 m guard adds about 1.3 m of shade on the rising north lot. Correction: a 0.3 m upstand with fall-arrest anchors; the locked gate stays.

**REG-N09: north strip drainage.** The north lot falls about 15% towards us, and `WATER` has nothing for the strip v 0–0.85. Correction: a channel on the pile cap at v 0.3–0.6, falling east to the lawn swale and wholly inside the parcel; tell the neighbour.

## What C11 gets right

- Still one storey above the road, no head-house, roofs labelled; Q13 (vertical extension) defaults to "no".
- Balcony at v 2.6, a 2.0 m screen between the balconies, obscured north glass.
- Real walls stay inside the envelope (re-run: 0.00 m² outside).
- The arrival court is dug, not filled.
- No anchors under the neighbour; north lawn edge at v 1.0.

## Out-of-scope notes

- Ø450 piles at 0.70 m leave 0.25 m gaps; that wall needs lagging (geotech).
- W2's base under traffic load is not drawn (structure).
- The court stair passes the boys' window at eye level (privacy).
