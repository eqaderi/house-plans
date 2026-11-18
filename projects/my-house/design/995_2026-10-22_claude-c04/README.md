# Claude C04 — exploratory concept (22 Oct 2026, agent:claude-code)

**EXPLORATORY.** The site and program gates are open, so nothing here is stored as a plan version. Nobody has approved it, and no structural, geotechnical, drainage or code check has been done.

## How it was made
1. `section_study.py`: floor plates stepped on the stored survey TIN. Earthwork uses the canonical `geospatial.earthworks.integrate`.
2. `generate.py`: two parts are fixed as design decisions, the lift (u 5.2–7.4, v 6.2–8.6 m) and the family stair (u 5.2–7.8, v 0–5.0 m). Rooms on each floor are then placed by CP-SAT using exact tiling, so room areas sum to the plate and no unassigned void can exist. Every habitable room needs a facade where the TIN is below the sill, or that faces a terrace or court. The canonical `Builder2D` assembles the model. `check_model` on `claude-c04-a/plan.json`: **0 findings**.
3. `sections.py`: three cuts through the TIN (`terrain-sections.png`).
4. `render.py`: draws the floor plans (`floor-plans.png`).

Rebuilding from the cached solve takes seconds: `generate.py --reuse`.

## Levels and areas (centreline, m²)
| Level | Floor | Indoor | Outdoor |
|---|---|---|---|
| Road | 1677.7 | 93.4 (garage 47.1, lobby, office 12.6, WC+shower, plant, store) | roof decks 57.9; forecourt slab (landscape) |
| Upper | 1674.3 | 151.3 (living 33.6, kitchen 21.8, dining 14.4, entrance hall 15.8, grand master 17.0 + shower 6.0 + dressing 4.0, pantry, guest WC, store) | south terrace 39.0, east balcony 28.1, sunken west court 34.2 |
| Lower | 1670.7 | 152.9 (family room 31.4, boys 21.1, girls 21.3, parents/grandparents 21.0 + shower 5.2, shared shower 6.8, shared WC 3.2, laundry 6.8, store 7.8) | garden terrace 46.8 |
| Lawn | 1668.3 | — | about 151 flat, reached by a 2.4 m stair |

## Earthwork (inferred, TIN; formation 0.35 m below floors)
- **Building cut:** about 253 m³ (canonical `hillside_report`, includes the sunken court). Deepest is about 3.9 m, at the lower floor's north-west back wall. `sections.py` gives about 275 m³: 190 m³ lower floor, 28 m³ upper floor, 57 m³ court.
- **Lawn:** about 168 m³ of fill and 12 m³ of cut. Retaining wall about 3.1 m at the east edge. The building's dug soil roughly balances the lawn fill.
- **Voids under floors:** lower floor south-east corner about 1.8 m. Lower garden terrace up to about 2.9 m (fill). West half of the upper south terrace about 2.4 m, which needs structure or fill. The canonical report shows 4.9 m and 5.5 m maxima here, but those come from near-zero-area sliver polygons in its region split (a possible `hillside_report` bug); the TIN at the terrace corners gives at most about 2.4 m.

## Entrance and doors
- From the road: garage and road lobby (lift) open onto a road-level forecourt slab. That slab bridges the north part of the sunken west court, so the upper entrance hall opens under it as a covered porch. The court is open to the sky south of v 9.6 m, with a stair down along the road border.
- Doorless passages (owner 2026-10-22, "no unnecessary doors or barriers"): entrance and stair hall, kitchen to entrance, kitchen to dining, dining to living, pantry, landing to family room, dressing to bedroom. Doors remain for bedrooms, bathrooms and WCs, the office, lift, laundry, plant/stores and the suite entrance. Floors are level inside each storey.

## Validation basis
`check_model` ran against the existing, unapproved program (`program` v-latest). `pi-entry` is mapped to the road lobby, and `pi-bath-2` to the bed-3 shower room. Room sizes come from the `ROOMS` table in `generate.py`, which is an agent proposal, not an approved program.

## Known weaknesses (agent judgement)
- The parents/grandparents room (lower, south-west) has one 1.4 m window, and the ground outside sits just under the sill.
- The garage door needs about 1.4 m of build-up at the apron, carried by the forecourt slab. The road edge itself is level with the garage floor.
- Storey heights (3.4/3.6 m) differ from the canonical roof offset of 3.0 m, so roof slab heights are nominal.
- The lift is not part of the integrity reachability graph. Step-free access is by assumption, not by check.
