# C10 review 03: geotechnics and earthworks

Concept stage, nothing geotechnically verified. Heights: 27-point survey TIN (inferred). Volumes `measured` with `zg` on a 0.05–0.1 m grid unless marked.

## Summary

1. The digging is reasonable: the building cut is 215 m³ and the deepest cut is 3.97 m. But C10 does not say what about 160 m³ of slab "void" stands on, under the garage, the master strip and the SE living corner.
2. The 4 m cut at the stair corner is 1.1 m from the north boundary. It cannot be battered and needs shoring first.
3. The forecourt is a 3 m fill wedge on the road embankment, which falls at about 50%. It sits below the road, so road water drains into it.
4. Owner proposal (b) costs about 5 m³ of cut if the stair starts inside the court. Proposal (a) costs 87–98 m³ and two walls of about 3.9 m. A reduced (a) costs 31 m³ and needs walls of 2.4 m at most.
5. No foundation can be fixed before boreholes give rock depth, bedding dip and groundwater.

## Findings

| ID | Sev. | Where | Issue |
|---|---|---|---|
| GEO-01 | BLOCKER | garage, main N strip, living SE, lower SE | slabs 1.4–5.1 m above undug ground; support not defined |
| GEO-02 | BLOCKER | `gs-court` u 4.6–6.6 | the stair falls 2.30 m in a 2.0 m run |
| GEO-03 | MAJOR | lower NW, u 6.8–13, v 1.1 | 3–4.5 m dig 1.1 m from the north boundary |
| GEO-04 | MAJOR | v 1.1 / v 2.8, u 9.4–18 | two walls with soil trapped between them; upper footing in the lower dig's influence zone |
| GEO-05 | MAJOR | forecourt | 3.0 m fill on a 50% embankment; 3.8 m drop at v 11.6; sits below the road |
| GEO-06 | MAJOR | lower slab | cut up to 3.95 m (NW) and fill up to 1.39 m (SE) under one slab |
| GEO-07 | MAJOR | garden terrace, lawn | 2.64 m fill on a 35% slope; 2.4 m wall partly founded on fill |
| GEO-08 | MAJOR | owner (b) | feasible and cheap: adopt with the stair starting at u 0.4 |
| GEO-09 | MAJOR | owner (a) | full version too costly against the road; adopt the reduced version |
| GEO-10 | MAJOR | site | drainage and outfall not designed |
| GEO-11 | MINOR | site | spoil balance |

## Finding details

**GEO-01 (BLOCKER). "What does the garage stand on?"**

Slab formation (FFL − 0.35 m) against natural ground, `measured`:

| Zone | Air or fill below the slab | Max depth |
|---|---|---|
| Garage, u 0–2 | 29 m³ | 3.0 m |
| Garage NW notches, u 2–6.8, v 1.1–2.8/4.6 | 30 m³ | 3.75 m |
| Main floor (ensuite, dressing, master), u 9.4–17.8, v 1.1–2.8/5.0 | 37 m³ | 3.78 m |
| Living room over the loggia, u 15.4–17.8, v 11.6–13 | 16 m³ | 5.1 m |
| Lower slab, SE | 16 m³ | 1.39 m |
| Loggia | 17 m³ | 2.1 m |

The engine's pit model (`min(ground, formation)`) hides all of this, and `checks.json` counts none of it.

Fix: no fill deeper than 1.0 m under any slab; suspended RC slabs on walls stepped to undisturbed ground:
- at u 0 (garage west);
- at v 1.1 from u 0 to 6.8;
- at v 1.1 from u 9.4 to 18 (see GEO-04);
- at u 18 and v 16.4 under the loggia.

The garage undercroft (about 30 m², 1.5–3.75 m high) can become a ventilated, drained store.

**GEO-02 (BLOCKER). Court stair as drawn**

1673.60 to 1671.30 is 14 risers, which need at least 3.9 m of goings; C10 gives them 2.0 m. The owner is right.

**GEO-03 (MAJOR). Dig at the north boundary**

Cut to formation along v 1.1 (`measured`): 3.97 m at u 6.8, 3.04 m at u 9.4, 2.46 m at u 11 and 1.73 m at u 13. Footings add about 0.5 m. A 1:1 batter would cut about 3.4 m into the neighbour.

Fix:
- Before digging, install an embedded wall along v 0.9 from u 5 to 13: soldier piles with lagging, or contiguous piles about Ø450 at 0.7 m centres (`assumption`, to be sized).
- Or build the permanent wall in alternate bays no more than 1.5 m wide.
- No anchors or nails under the neighbour without written consent.

**GEO-04 (MAJOR). Soil trapped between walls**

The lower floor's north wall is at v 2.8 and v 5.0. The main floor's north wall at v 1.1 is founded on undug soil 1.7 m away. At u 12 the upper footing would sit at about 1671.0 and the lower wall's base at about 1669.15. The level difference (1.85 m) is more than the distance between them (1.7 m), so the upper footing can be undermined.

Fix:
- Extend the lower dig to v 1.1 for u 9.4–18. This adds 30 m³ (max 3.03 m) and gives one basement wall founded at about 1669.15. The strip can be used for ducts or storage.
- The lower floor's west walls at u 6.8 and u 5.0 retain 3.6–3.95 m under main-floor footings. Design them as basement walls propped by both slabs, and never backfill before the main slab is cast.

**GEO-05 (MAJOR). Forecourt**

Ground falls from 1677.5 at the road to 1674.8 within 4–5 m. This is probably embankment (`inferred`). The forecourt adds 39 m³ of fill, up to 3.0 m deep, held by the garage wall at u 0 (0.25–3.0 m). Along v 11.6 it drops 3.8 m to the court and carries cars.

The forecourt (1677.40) is also 0.05–0.14 m below the road (1677.49–1677.54), so runoff and snowmelt run to the garage doors (1677.50) and into the fill.

Fix:
- Preferred: build the forecourt as a deck on the garage wall plus a pier line 0.5 m inside the boundary, with no fill.
- Otherwise: bench the slope (benches at least 1.5 m wide, no more than 0.5 m high), use granular fill in 200 mm layers at 95% of maximum dry density with geogrid (`assumption`), and design the walls for traffic surcharge plus seismic load.
- Put a channel drain at the boundary and another at the garage doors, with the forecourt falling 1.5–2% towards them. Pipe the water east, never into fill.

**GEO-06 (MAJOR). Lower slab on both cut and fill**

The NW sits in a cut of up to 3.95 m, probably dense soil or rock (`inferred`). Around (18, 11.6) the ground is at 1668.24, below the 1669.65 formation.

Fix:
- Found every footing on undisturbed ground. Step the east and south footings from about 1669.2 down to about 1667.4, which allows a frost depth of at least 0.8 m (`assumption`).
- Keep steps no more than 0.5 m high.
- Use ground-bearing fill no deeper than 1.0 m; suspend the slab elsewhere.
- If the NW is on rock and the SE on soil, use piers to rock or a movement joint at about u 13.

**GEO-07 (MAJOR). Garden terrace and lawn**

`measured`:
- Garden terrace: fill up to 2.64 m at (20.6, 11.6). The wall at u 20.6 is 2.38 m high, and south of v 9 it stands on lawn fill.
- Lawn: fill up to 1.35 m. Its contour wall is 1.1–1.2 m high on the crest of the 35% bank.
- Lawn south edge: a 1.2 m wall 1 m from the boundary.
- Lawn north edge at v 0.6: a 1.19 m cut 0.6 m from the boundary.
- At v 12.5 the stacked walls are only 2.3 m apart.

Fix:
- Suspend the terrace between the lower floor's east wall and a beam on a wall at u 20.6 founded at about 1666.5. This removes 39 m³ of wet fill against the guest room and lounge.
- Build the lawn walls as gabion or reinforced-soil walls, with the base at least 1.0 m below the lawn, the toe at least 1.5 m back from the bank face, benched fill and a heel drain.
- Keep stacked walls at least 2.4 m apart.

**GEO-08 (MAJOR). Owner (b): dig along the south for a gentle stair. Reasonable.**

- Drop: 6.00 m. Stair: 38 risers of 0.158 m with 0.33 m goings, in 4 flights (10, 10, 9, 9) with three 1.2 m landings. Run: 14.8 m.
- Placed in the band v 16.4–17.42 from u 0.4 (inside the court), it reaches 1667.60 at u 15.2 and continues as a level path to the lawn at u 18.
- Earthworks (`measured`): cut 4.7 m³ (max 0.81 m), fill 0.8 m³; about 10 m³ with the sub-base. South edging walls no more than 0.8 m.
- Starting at the court's SE corner (u 4.6) instead puts the stair 1.0–1.8 m above ground on 16.6 m³ of fill. There, excavation does not help.
- Knock-on: the lower floor's south footings must sit at least 0.6 m below the adjacent treads, which means about 1668.3 at u 12 and about 1667.0 at u 15.2.
- Width is capped at 1.0 m by rule 4.7.

**GEO-09 (MAJOR). Owner (a): dig west of the court to 1673.60. Feasible; use the reduced version.**

Full version, u −1.2 to the road, v 11.6–17.42:
- Area gained 39.2 m². Cut 86.5 m³ to the finished level, or 98.3 m³ to formation. That is +40–46% on the building cut.
- Maximum cut 3.97 m, about 4.8 m to the footing base, which is at the limit of rule 4.4.
- New walls:
  - along the road: 6.6 m long × 3.85–3.9 m, with traffic load;
  - at v 17.42: 8.3 m long × 0–3.98 m, 1 m from what the survey labels a shared footpath;
  - forecourt wall at v 11.6: grows to 5.2 m × 3.8 m.
- It needs road-side piles before any digging, a wall founded on its toe (no heel under the road) and road-authority consent.

Reduced version: stop where natural ground is 1676.0. That line runs from (−3.4, 11.6) to (−6.4, 17.42), about 3 m inside the boundary.
- Area gained 21.7 m², cut 31 m³, walls no more than 2.4 m, no wall against the road.
- Stair: 9 risers down the road-side shelf from the forecourt's SW corner to a landing at about 1675.9, then 15 risers east into the court.

**GEO-10 (MAJOR). Drainage**

The buried NW (stair, WC, wudu, pantry, laundry) has no drainage design, and the area is rich in springs (`inferred`).

Fix:
- Perimeter drains at footing level behind every buried wall, plus a drainage layer and tanking.
- A lift pit no deeper than 0.3 m, or a sealed pit with a sump.
- A gravity outfall from about 1669.0 to a dispersion trench in the tree bank at about 1666.0. Never discharge onto the footpath or the east neighbour.

**GEO-11 (MINOR). Spoil**

- In-situ cut: about 300 m³ (building 215, plus GEO-04 30, plus footings about 40 (`assumption`), plus courts 12), about 400 m³ loose.
- Reusable: about 145 m³ in situ for the 124 m³ of compacted fill, if it is granular. Less is needed if GEO-07 is adopted.
- Strip 0.3 m of topsoil first and keep about 22 m³ of it for the lawn.
- Haul about 20 trucks of 12 m³. Proposal (a) adds 10–11 trucks in full form, or 3–4 reduced.

Sequence:
1. Condition surveys and utility locates, then strip topsoil.
2. Install the north and road-side shoring.
3. Dig top-down from west to east in lifts of no more than 1.5 m. Batter only on the east and south.
4. Build bottom-up, and backfill only after the slabs are cast.
5. Do garden walls last.
6. Dig in the dry season (about Jun–Oct, `inferred`).

**Investigation needed:**
- Boreholes at (7, 1.5) to 10 m or 3 m into rock, at (−2, 9), (16, 14) and (23, 8), and a trial pit at (−6, 16) if (a) goes ahead.
- Rock depth and RQD, and the bedding and joint dip against the east-facing slope (marl or shale dipping east would be critical).
- SPT, plasticity and swell, sulfate and gypsum, and a Proctor test on the spoil.
- Groundwater and springs monitored through a wet season.
- Vs30 and site class (Standard 2800 values are an `assumption` until sourced).
- How the road embankment was built and what utilities run under it; the neighbours' structures; frost depth; soakage.

## What C10 gets right

- The buried NW under the wet cluster is left undug, so the cut stays at 3.97 m, inside rule 4.4.
- The floors step east with the slope. A cut of 215 m³ for 459 m² gross on 35% is modest.
- The lawn follows the contour: fill is no more than 1.35 m (C09 had 2.6 m), and the tree bank stays natural.
- Windows only where ground is no more than +0.6 m above the floor.

## Out-of-scope notes

- Structure: the master balcony (u 17.8–19.4, v 1.1–2.8) and the living corner over the loggia need defined supports.
- Privacy: the stair in (b) passes the children's south windows 0–0.8 m below the sill.
