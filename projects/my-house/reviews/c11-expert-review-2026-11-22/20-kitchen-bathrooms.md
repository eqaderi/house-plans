# 20 · Kitchen and bathrooms · C11 review

Concept stage; nothing here is code-checked. Product and code figures are `assumption`. Geometry is `measured` from `design.py` (`build()`, `clear_geom`) unless marked otherwise.

## Summary

1. The kitchen meets rules 1.3–1.5: 15.6 m² clear, a 4.3 m² pantry, 4 stools, a hob under riser SH-K and no WC over it. Its fit-out is thin, and the hob has almost no south landing.
2. **BLOCKER:** riser SH-E stands in both ensuite doorways. The master keeps 0.25 m of a 0.9 m slider; the grandparents keep 0.35 m of a 1.0 m slider.
3. **BLOCKER:** the wudu seat bench ends 0.29 m from the main shower's door, so the shower cannot be reached.
4. The lower WC pan sits in a 0.60 m slot. No WC has a shattaf or floor drain drawn, although CORRECTIONS.md says they are drawn.
5. The road plant room (300 L cylinder, boiler) sits over the hob and sink, and its bund is only a note.

## Scorecard

SCORECARD: fixed=5 partly=9 not_fixed=2 worse=0 new_blocker=2 new_major=3 new_minor=5

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| KB-01 meals for 8 | fixed | Rule 1.4 revised (stmt-029). 4 stools. Dining 3.08 × 4.04 m clear fits 2.2 × 1.0 + 0.9 m. | — (4th stool: KB-10) |
| KB-02 hood route | fixed | SH-K R(4.85,12.25,5.45,12.85) on all floors, through the plant room to the roof. Damper and make-up air are notes. | Draw the damper, the south-wall make-up inlet, and the terminal ≥1 m above the roof. |
| KB-03 pantry distance | partly | Pantry door → kitchen opening 3.7 m walked (target ≤3); pantry → hob 6.0 m (C10: 6.7). The route crosses the entry → stair flow. The SH-W box ends 0.10 m from the opening's jamb. | Keep the NW bulk store; add the in-kitchen larder (KB-04). |
| KB-04 fit-out | partly | 0.9 m fridge drawn. Free worktop ≈1.1 + 1.0 m. Oven, dishwasher, bins, larder and tea niche are claimed but **not drawn**. North wall u 6.7–9.34 unused. | Tall larder 0.6 m + tea/samovar niche 0.45 m at u 8.25–9.34, v 9.56–10.16. Draw the oven, the DW at u 6.35–6.95 and the bins. |
| KB-05 smell path | partly | Road-level stair screen drawn. Kitchen opening still 2.2 m from the open stair mouth; the lower stair is open. Hood rate and make-up air are notes. | Interlocked inlet 0.2 × 0.4 m in the south wall at u 5.0–5.3; hood ≥600 m³/h. Q10 stays the owner's. |
| KB-06 WC over kitchen | fixed | `wc-r` is over the entry; no wet room overlaps the kitchen. | Plant room: N04. |
| KB-07 main WC sightline | fixed | My ray test: 0.1 m grid over all hall and kitchen points → 3 bowl-front points. **0 hits**. | — |
| KB-08 shattaf, drains | not fixed | No shattaf, floor drain or dado in `design.py` or the SVGs, for any of the 5 WCs. | Each WC: shattaf with a hot/cold mixer beside the pan, a Ø50 drain 0.3 m in front of the bowl, a 1.2 m dado. Drawn as symbols. |
| KB-09 wudu | partly | Bench and basin drawn; the trough is text only. Dry path **0.49 m** (asked 0.9). Shower blocked: N02. | N02; draw the trough u 3.86–4.30 with a linear drain. |
| KB-10 island | partly | Island 1.4 × 0.7; aisles W 1.54, S 1.10. The east stool (8.25,10.8) sits **0.9 m** in front of the dining opening, on the serving line. | Island u 6.7–8.1; stools at u 6.95/7.4/7.85 north; delete the east stool (rule 1.4 allows 3). |
| KB-11 lower WC door | partly | 0.7 m slider now. The pan faces the door; with both doors open its front is visible from `hall-l` (8.5–8.8, 8.0–8.2), 13 rays. `checks.py` tests only the pan centre. | N03 |
| KB-12 morning rush | not fixed | 1 WC and 1 shower for 4 children (Q14 default: No). "Twin" basins have 0.47 m centres: in practice one. | N06; second WC is Q14. |
| KB-13 seated shower | partly | Tray-free 1.7 × 1.25 m wet zone. Seat and rails not drawn. Door blocked: N01. | 0.45 m fold-down seat at u 11.25, v 1.6–2.1; rails. |
| KB-14 road WC | partly | 1.0 × 0.9 tray drawn. Room 2.19 × 1.19 m clear. Pan centre **0.25 m** from the tray; inward leaf 0.05 m from the bowl. | North wall to v 11.3 (clear 1.49 m deep; the hall keeps 1.35 m past the lockers). Pan on the east wall facing west at (3.95,12.1). Tray 0.9 × 0.9 at u 2.15–3.05, v 11.95–12.85. Outward door at u 3.1–3.8. |
| KB-15 qibla | fixed | `wc-r` and `wc-m` face 158° (46.7° off); `ens`, `gens` and `wc-l` have their backs 43.3° off. This was the adopted resolution. | Q11 only. |
| KB-16 outdoor cooking | partly | Station and LPG cage are only dashed or text, 6.7 m from the slider. No tap at the kitchen side. | N09 |

## Part B: new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| KB-N01 | BLOCKER | `ens` (main), `gens` (lower), wall u 11.4 | SH-E R(11.0,3.55,11.4,4.15) fills 0.6 m of each ensuite doorway | Move SH-E to R(9.53,4.0,9.93,4.4) |
| KB-N02 | BLOCKER | main `wudu` / `sh-m` | Bench leaves 0.29 m in front of the shower door | Door east, bench shorter, basin to `wlob` |
| KB-N03 | MAJOR | lower `wc-l` | Pan in a 0.60 m slot, facing the door | Pan on the south wall, facing north |
| KB-N04 | MAJOR | road `plant` over the kitchen | Cylinder and boiler above the hob and sink; bund only a note | Tanked, bunded floor + shut-off |
| KB-N05 | MAJOR | kitchen SW corner | Hob jammed against SH-K; dead corner | 0.75 m hob at v 11.05–11.80 |
| KB-N06 | MINOR | lower `lav` | Basins 0.47 m apart | East wall, 0.7 m centres |
| KB-N07 | MINOR | `wc-m` | Basin inside the transfer zone | Move it behind the door |
| KB-N08 | MINOR | `laundry` | No floor drain; 0.73 m entry arm | Drain, washer tray |
| KB-N09 | MINOR | court LPG cage | 0.92 m from the porch drain outlet | Natural-gas point, or ≥2 m away |
| KB-N10 | MINOR | kitchen wall u 4.4 | Hob on a 0.12 m partition, backed by the coat store | 0.2 m masonry behind the hob |

## Part B details

**KB-N01 · BLOCKER (`measured`).** The master slider spans v 3.5–4.4 and the grandparents' slider v 3.2–4.2; SH-E spans v 3.55–4.15 behind both. Clear passage is 0.05 + 0.25 m (master) and 0.35 + 0.05 m (seated ensuite): no usable door to either. Check §7.15 never tests doorways. **Correction:**
- SH-E to R(9.53,4.0,9.93,4.4), in the corner of the stair-core and lift walls, beside both pans.
- Master pan to v 3.55 (0.45 m to the riser).
- The `gens` pan keeps 0.6 m, and its Ø1.5 circle stays clear.
- Add a door-versus-riser test.

**KB-N02 · BLOCKER (`measured`).** The shower door spans u 4.03–4.78 and the bench starts at v 5.25. That leaves 0.29 m, and only 0.03 m of the door width can be reached from the dry strip. **Correction:**
- Door 0.75 m at u 4.14–4.89.
- Bench and trough at v 5.95–7.24 (station centres v 6.25 and 6.9), giving a 0.99 m landing in front of the door.
- Standing basin to `wlob`'s west wall at u 5.36–5.81, v 5.0–5.5. It stays clear of the WC door's sweep and doubles as the WC hand basin.

**KB-N03 · MAJOR (`measured`).** SH-W fills the NW corner of `wc-l`. The pan (5.05,9.75) is 0.31 m from the riser and 0.29 m from the wall: 0.60 m of seat width (≥0.8 m, `assumption`). **Correction:**
- Pan centre (6.15, 9.71), facing north: 0.59 m to the east wall, 0.70 m clear in front.
- Slider moved to v 8.80–9.50.
- Drain at (5.9, 9.1).

**KB-N04 · MAJOR (`measured` position, `inferred` risk).** `plant` R(4.4,11.6,7.4,13.0) holds the 300 L cylinder, the boiler and the MVHR condensate over the hob and sink. §7.15 checks only rooms of kind `wet`. **Correction:**
- 150 mm bunded, tanked floor with a gully to SH-K.
- Leak sensor with a motorised mains shut-off.
- No pipe joint over u 4.46–7.34.
- Extend §7.15 to water-holding service rooms.

**KB-N05 · MAJOR (`measured`).** The drawn hob is 0.6 m wide, not the 0.9 m in the ledger. It has 0.15 m of landing before the full-height SH-K box (0 m with a 0.9 m hob). The corner u 4.46–4.85, v 12.2–12.85 is dead, and the two runs do not connect. **Correction:**
- 0.75 m hob at v 11.05–11.80, with landings of 0.59 m north and 0.40 m south.
- A spice pull-out in the corner.

**KB-N06 · MINOR (`measured`).** **Correction:** two 0.5 m basins on the hall wall of `lav`, centres v 8.95 and 9.65, from u 7.69 to 8.14. That leaves 0.83 m of aisle.

**KB-N07 · MINOR (`measured`).** In `wc-m`, the basin (u 6.25–6.65, v 3.78–4.23) intrudes into the transfer zone R(5.7,3.0,6.6,4.3). **Correction:**
- Basin at u 6.29–6.74, v 4.25–4.70.
- A drop-down rail on the transfer side.

**KB-N08 · MINOR (`measured`).** **Correction:**
- Ø50 floor drain at (5.6, 10.6).
- Washer tray with a leak sensor.
- Draw the folding counter.

The 0.73 m entry arm is tight but acceptable.

**KB-N09 · MINOR (`measured`).** The cage is at the foot of W1, where the court lies 3.9 m below the forecourt. LPG runs to gullies (`assumption`). **Correction:**
- Natural-gas bayonet point from the meter niche (MEP-05), with no cylinder store; or a cage ≥2 m from any gully or opening.
- Add the tap and gully beside the kitchen slider at u 5.0–6.2, v 13.3–13.9.

**KB-N10 · MINOR (`measured`).** **Correction:**
- u 4.4, v 10.9–12.2 becomes 0.2 m non-combustible masonry.
- Induction preferred.

## What C11 gets right

- The WC is off the kitchen ceiling; it sits over the entry and drains west.
- The main cluster has an accessible 1.67 × 1.98 m WC with an outward 0.9 m door and 0 sightlines (measured).
- The hood has a real vertical route through non-habitable rooms (SH-K on all floors).
- Kitchen: 15.6 m², a 2.0 m slider, the sink under the south window, a 0.9 m fridge and a 6.0 m work triangle.
- The laundry is 4.8 m² (stmt-028) with separate stores. The lower bathroom has a lockable door and a dry zone.
- The ensuites stack, and the seated ensuite's wet zone is 1.7 × 1.25 m.

## Out-of-scope notes

- MEP: the soil run from the `wc-m` pan to SH-W is ≈5.9 m. The plant room is 1.19 m deep clear, too small to service.
- Acoustics: the kitchen stands over the boys' room; the floating screed is only a note.
- QA: CORRECTIONS.md marks C11-KB-02, -03 and -04 as done or drawn, but the elements are missing from `design.py`.
