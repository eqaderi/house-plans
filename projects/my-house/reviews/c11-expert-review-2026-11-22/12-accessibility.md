# 12 · Accessibility and ageing in place: review of C11

Reviewer 12, prefix ACS. Test users are a wheelchair user (Ø1.5 m turning circle, about 0.85 m clear door) and a grandparent with a walker. Geometry is `measured` from `design.py`; (assumption) marks common practice, not a checked code.

## Summary

1. The lift is right: 1.80 × 2.64 m clear (stretcher car), a 0.9 m automatic door and a clear Ø1.5 m landing on all three floors. The garage aisle and the lower hall are clear.
2. **The SH-E riser stands in both ensuite doorways** (master and seated ensuite), leaving 0.05 + 0.25 m and 0.35 + 0.05 m. **BLOCKER.**
3. **The garden walk is a dead end.** A 1.74 m wall closes it at u 15.4, so the court stair reaches neither the loggia, `t-low` nor the lawn. The page tells the owner it does. **BLOCKER.**
4. The main-floor "accessible" WC has no turning circle (the largest is Ø1.24 m), and its basin stands 0.62 m inside the door.
5. The owner is still not told the limits. C11-ACS-02 is marked "Done", but it appears on no page, and the rescue and evacuation "notes" exist nowhere.

## Scorecard

SCORECARD: fixed=5 partly=6 not_fixed=2 worse=0 new_blocker=2 new_major=2 new_minor=1

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| ACS-01 master ensuite | partly fixed | `measured`: opens straight off the bedroom by a 0.9 m slider; 1.81 × 3.15 m clear; flush shower 1.70 × 1.50 m; Ø1.5 m fits over the shower floor. But the riser blocks the door (N01), the basin is 0.39 m inside the door, and the pan (v 3.7) is 0.70 m from any wall, so no fixed rail is possible. | After N01: pan centre to v 3.95 (0.45 m off the wall face at 4.40) with a rail; basin on the east wall at v 2.60–3.10. |
| ACS-02 day WC | partly fixed | `measured`: wc-m 1.665 × 1.98 m clear, pan 0.45 m off the side wall, 1.0 m transfer space, outward door. But the core wall clips the opening to 0.825 m (about 0.75 m clear, assumption). The basin (u 6.25–6.65, v 3.78–4.23) blocks 0.40 m of the opening, 0.62 m inside, and sits inside the drawn transfer zone. The largest clear circle is **Ø1.24 m**. The latch-side pull space is 0.49 m. | South wall to v 5.15 (lobby 1.32 × 2.03 m). 0.9 m surface slider parking west (≥0.85 m clear). 0.40 × 0.30 m basin on the west wall at v 3.95–4.35. Result: Ø1.5 m at (5.92, 4.32), clear of the bowl. Otherwise, call it an "assisted WC". |
| ACS-03 lower hall | fixed | `measured`: the table is gone; Ø1.5 m clear at every lift door. | — |
| ACS-04 garage | fixed | `measured`: aisle u 5.54–6.74 clear; fire door at v 8.35–9.35; car 1's driver door opens into the 1.77 m shared zone. | Power-assisted fire door: not drawn or noted. Label car 1 as the accessible bay. |
| ACS-05 grandparents' room | partly fixed | `measured`: twin beds with a 1.75 m transfer zone. The hall door latches against the lift wall: **0.0 m** latch-side space (C10: 0.2). | N03. Move the armchair at u 14.6–15.35 off the transfer-zone mouth. |
| ACS-06 power cut and evacuation | not fixed | `measured` by text search: "rescue", "battery", "evacuation", "stair-lift" and "emergency light" are in no page, note or `design.py`. Only the ledger claims "notes". | On the lower sheet and in the limits: automatic rescue device; battery for ≥5 trips on the essential circuit; evacuation chair at the lower stair foot (1.21 m clear); stair-lift fixings; emergency lighting. |
| ACS-07 thresholds | partly fixed | `measured`: terraces set down 0.25 m ✓; porch and court at FFL ✓. Road door: `Z_FORE` 1677.47 against 1677.50 is **30 mm**, though the comment says "≤20 mm". | Forecourt at 1677.49 for 1.5 m in front of the door and the shutters; flush sill with a slot drain. |
| ACS-08 sliders | partly fixed | `measured`: kitchen and grandparents' sliders 2.0 m, with no 1.0 m leaf specified. Still at 1.8 m (about 0.80 m clear, assumption): office, master, living east, **both lounge exits**. Dining 1.4 m (about 0.60 m). | Every slider gets a ≥1.0 m moving leaf. Lounge south and office: 2.4 m. Dining: 1.8 m, or a fixed light. |
| ACS-09 garden stairs | fixed (stairs) | `measured`: court 3 × 8 risers of 150/340 mm; lawn 2 × 8 of 149/320 mm; landings; rails both sides. | The route is broken: N02. |
| ACS-10 seated ensuite | partly fixed | `measured`: 1.88 × 3.08 m clear; tray-free wet zone 1.70 × 1.25 m; 1.0 m pocket door. But the riser blocks the door (N01). The **drawn** circle at (10.4, 3.25) overlaps the pan and basin by 0.13 m² and crosses the riser. A true Ø1.5 m circle fits only at (10.40, 2.27). The basin is 0.34 m inside the door. No rails or extract shown. | Redraw the circle. Basin on the east wall at v 2.60–3.10. Draw rails. Extract 15 l/s (assumption). Pocket the door north (v 2.2–3.2), not into the RC lift wall. |
| ACS-11 lift | fixed | `measured`: 1.80 × 2.64 m clear; 0.9 m automatic doors; 1.2 m pit; 0.8 m overrun. | Seat and rail: supplier spec. |
| ACS-12 kitchen | fixed | `measured`: Ø1.5 m at (5.83, 11.50) is clear of walls, counters and the island. | — |
| ACS-13 arrival court | not fixed | `measured`: no accessible entrance is named. The 5.4 row lists the garden walk as "step-free", but it is reached only by 24 steps. | N04. |

## Part B: new problems

| ID | Sev. | Where | Finding | Correction |
|---|---|---|---|---|
| ACS-N01 | BLOCKER | main `ens`, lower `gens`; SH-E R(11.0, 3.55, 11.4, 4.15) | The riser fills 0.60 m of both ensuite doorways | SH-E to R(11.46, 2.40, 11.86, 3.00) |
| ACS-N02 | BLOCKER | lower `walk-s`, wall SW-30 at u 15.4 | No outdoor route court → loggia, `t-low` or lawn | Extend the walk to u 18.0 |
| ACS-N03 | MAJOR | master and grandparents' hall doors (11.95, 7.3) | 0.0 m latch-side space; 0.95 m structural opening | Move each door to v 6.2, hinged west |
| ACS-N04 | MAJOR | `report_text.py` LIMITS, `CORRECTIONS.md` | The owner gets false or no accessibility facts | Add the limits; correct the ledger |
| ACS-N05 | MINOR | road `wc-r` | 2.19 × 1.19 m, 0.7 m door: the only arrival-floor WC | Say the accessible WC is one lift stop down |

## Part B details

**ACS-N01 BLOCKER: riser in the ensuite doorways.** *Measured, and visible on `main.png` and `lower.png`:* the grey riser box sits behind the slider line.
- Master: door v 3.50–4.40 against riser v 3.55–4.15. Left: 0.05 m and 0.25 m.
- Seated ensuite: door v 3.20–4.20. Left: 0.35 m and 0.05 m.

Nobody can enter either ensuite; §7.10 checks only furniture.

*Correction:* SH-E to R(11.46, 2.40, 11.86, 3.00) on both floors, in `dress` (shorten the wardrobe to v 1.25–2.35) and in `gwalk` (clear of its shelf and of the door at u 12.5–13.3). They stack, and the riser vents on the green roof. Add a check: no riser within 0.7 m of a door opening.

**ACS-N02 BLOCKER: garden walk dead end** (rules 4.11 and 5.4). *Measured:*
- `walk-s` (1670.00) ends against SW-30 (1.74 m high).
- The loggia (1669.98) touches it only at the point (15.4, 16.0).
- The ground in front of the loggia edge is 1667.97–1668.30, a 1.7–2.0 m drop.

The court stair leads to a 5.7 m strip with no exit. The outdoor refuge of the lower floor (`t-low` and loggia) reaches the road only through the house. Yet the page says the stair goes "to the garden walk …, the loggia and the garden terrace".

*Correction:*
- Extend the walk as R(15.4, 16.0, 18.0, 17.12) at 1669.98–1670.00, on fill behind a wall on v 17.12 (about 2.0–2.4 m), or as a slab on the C-B/16.2 line.
- Delete SW-30.
- Leave the loggia front open over u 15.65–17.75.
- Put a 1.1 m guard at the east end.
- Add a reachability check: court → walk → loggia → `t-low` → lawn stair.

**ACS-N03 MAJOR: bedroom doors beside the lift.** *Measured.* Both hall doors are 1.0 m leaves hinged at u 12.45. The latch (11.45) sits behind the lift-wall face (11.50), and the doors open into a 1.04 × 0.96 m passage. To leave the room, the occupant pulls the door with 0.0 m beside the latch (about 0.6 m needed, assumption).

*Correction:* door at v 6.2 (u 11.5–12.5), hinged at u 11.5, swinging in. The pull side then has 0.76 m (grandparents) and 0.81 m (master), and the alcove joins the lift landing. Alternative for the grandparents: a low-energy automatic operator.

**ACS-N04 MAJOR: what the owner is told.** *Measured:* `LIMITS` (6 bullets) has nothing on access. "Cannot", "wheelchair", "ramp" and "accessible entrance" appear nowhere in `index.html`, yet C11-ACS-02 is marked "Done".

*Correction:* add to the limits:
- The road door plus the lift is the only step-free entrance. The court would need about 46 m of 1:12 ramp.
- The lawn is 16 steps down; a ramp of 29–33 m does not fit. A platform lift (2.4 m travel) at `t-low` is an owner option.
- The step-free outdoor rooms (`t-south`, `t-low`, the loggia) are reached from inside only.
- In a power cut, the lift relies on its rescue battery, and the evacuation chair waits at the lower stair.

Mark ACS-02, CIR-03 and MEP-06 as not done in `CORRECTIONS.md`.

## What C11 gets right

- A real stretcher lift with same-face automatic doors and a clear Ø1.5 m landing on every floor.
- Garage → lift indoors along a clear 1.2 m aisle, with a 1.77 m transfer bay at car 1.
- The parents' ensuite now opens straight off the bedroom, and both ensuites have flush 1.7 m wet zones that double as turning space.
- Twin beds with a 1.75 m transfer zone, and a level 2.0 m slider from the grandparents' room to the garden terrace.
- Easy outdoor stairs: 150 mm risers, 8-riser flights, landings, rails both sides.

## Out-of-scope notes

- Structure: the N02 extension and the retaining at the girls' SE corner.
- MEP: SH-E relocation; extract for the windowless seated ensuite.
- QA: §7.10 ignores risers in doorways, and the 5.4 row lists an unreachable walk.
