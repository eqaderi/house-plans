# C10 review 08: sun, daylight, views, ventilation (prefix SUN)

Concept-stage review. Nothing here is engineered or code-checked.

## Summary

1. **Bearings.** The "east" façade (+u) faces **68° true (ENE)**. The "south" façade (+v) faces **158° (SSE)**. "West" is 248° and "north" is 338°. The ground falls towards about 91°.
2. **SSE rooms work in winter.** Kitchen, dining, living, boys and girls get the full 6.8 h of sun on Dec 21 (08:20–15:00 solar). The south terrace ends flush at v 16.4, so it does not shade the children's windows.
3. **ENE glass works against the climate.** It gets 349 Wh/m² on Dec 21 but 2,641 Wh/m² on Jun 21. There are 17 m² of it on the main floor, unshaded. The SSE glass has no summer shade either.
4. **Short of winter sun:**
   - grandparents' room: 1.1 h
   - lower lounge: 1.2–1.6 h
   - lower family hall: no window at all
   - play lawn: in shadow after 13:00
5. **Qibla.** The mats face 158°; the qibla is **204.6°**, so they are 46.7° off. The lower floor has no cross-ventilation and no stack.

**Method.** I raytraced design.py's geometry against:
- the engine.GroundModel ground
- the PVGIS horizon (`simulation_result`)
- clear-sky sun at 34.969 N, 46.356 E

True north is grid north +0.778°. That assumes EPSG:32638, which is unconfirmed.

Assumptions:
- window sill 0.9 m and head 2.4 m; sliders 0.1–2.4 m
- soffits 0.35 m below the floor above
- road roof at 1680.80
- railings see-through
- nothing beyond the parcel modelled

`measured` below means this computation.

## Findings table

| ID | Sev. | Where | Issue |
|---|---|---|---|
| SUN-01 | MAJOR | main, living | Mats face 158°; qibla is 204.6° |
| SUN-02 | MAJOR | ENE façades u 17.8 and u 18.0 | 16.9 m² of unshaded main-floor glass |
| SUN-03 | MAJOR | SSE façades v 13.0 and v 16.4 | No summer overhang |
| SUN-04 | MAJOR | lower, grandparents (11.4–18.0, 2.8–7.3) | Least winter sun in the house |
| SUN-05 | MAJOR | lower lounge (12.6–18.0, 7.3–11.6) and hall | Lounge in the shade of the loggia; hall windowless |
| SUN-06 | MAJOR | all floors | Rooms open on one side only; no stack |
| SUN-07 | MINOR | play lawn | Afternoon shade |
| SUN-08 | MINOR | stair (6.8–9.4, 1.1–7.3) | No daylight |
| SUN-09 | MINOR | master NNW window | No winter sun; summer evening sun |
| SUN-10 | MINOR | balcony and terrace edges | Parapet hides the view |
| SUN-11 | MINOR | boys, girls | Beds under the only window; boys' glass 15% of floor |
| SUN-12 | MINOR | drawings | No true north or qibla |

## Finding details

**Glazing per room** (`measured`, drawn net areas):

| Room | Glass | ÷ floor | Faces | Dec 21 sun |
|---|---|---|---|---|
| Kitchen | 6.5 m² | 43% | SSE | 6.8 h |
| Dining | 4.6 m² | 41% | SSE | 6.8 h |
| Living | 17.9 m² | 53% | ENE + SSE | 6.8 h (SSE) / 2.3 h (ENE) |
| Master | 10.6 m² | 46% | ENE + NNW | 2.3 h |
| Boys | 3.0 m² | 15% | SSE | 6.8 h |
| Girls | 5.0 m² | 25% | SSE | 6.8 h |
| Grandparents | 7.6 m² | 35% | ENE + NNW | 1.1 h |
| Lounge | 12.0 m² | 54% | ENE + SSE (covered) | 1.2 h / 1.6 h |
| Both halls, pantry, wudu, lower wet rooms, laundry | 0 | 0% | none | 0 |

The road-level roof terrace does **not** darken the living room. It ends exactly on the living room's walls (u 17.8, v 13.0), so it has no overhang. The living room's real problem is that its glass has no shade.

### SUN-01 Qibla (MAJOR)

- **Evidence** (`measured`):
  - `mats(15.35, 11.5, 2, "s")` faces 158°.
  - The Kaaba lies at 204.6°.
  - In the design frame that is the direction (−0.728, +0.686).
- **Correction:**
  - Rotate the mats 46.7° about (16.0, 11.4).
  - A sheer curtain on the slider at (12.8–14.8, 13.0).
  - A qibla arrow on the plans.

### SUN-02 ENE glass (MAJOR)

- **Evidence** (`measured`): per m² of glass:

  | Date | Direct sun | Hours |
  |---|---|---|
  | Dec 21 | 349 Wh/m² | 2.3 h |
  | Jun 21 | 2,641 Wh/m² | from sunrise to 11:30 |
  | Jul 25 | 2,463 Wh/m² | |

  For comparison, SSE glass gets 1,332 Wh/m² on Jun 21. On a clear June morning the living room receives about 27 kWh and the master about 18 kWh through this glass. The sun stands only 25–45° high when it faces this glass, so a canopy cannot stop it.
- **Correction:**
  - Exterior adjustable blinds or sliding timber shutters on all ENE glass.
  - On the master, these also black out the room; the sun reaches the bed from about 05:50.
  - Delete the slot window at (17.8, 12.1–12.7).
  - Plant deciduous trees on the bank (u 26–30) that mature at 10–12 m (`assumption`).

### SUN-03 SSE glass unshaded (MAJOR)

- **Evidence** (`measured`): 1,332 Wh/m² on Jun 21 and 1,724 Wh/m² on Jul 25. July's regional mean is 28.3 °C.
- **Correction** (raytraced):

  | Overhang | Where | June gain | Dec 21 |
  |---|---|---|---|
  | 0.9 m canopy, soffit 1677.15 | v 13.0–13.9, u 4.6–17.8 | falls to 408–643 Wh/m² (−52 to −69%) | unchanged: 3,622 Wh/m², 6.8 h |
  | Terrace slab extended 0.6 m | v 16.4–17.0, u 6.6–15.4 (envelope edge 17.42) | falls to 730–762 Wh/m² | unchanged |

  Shade the terrace table with an awning, not a fixed pergola. A fixed pergola would shade about half of the kitchen glass in winter.

### SUN-04 Grandparents (MAJOR)

- **Evidence** (`measured`):
  - Dec 21: 1.1–1.2 h (08:20–09:45), 215–231 Wh/m². The balcony overhead takes a third of it.
  - The NNW window gets no sun from October to March.
  - These occupants are home all day, and January's mean is 1 °C.
- **Correction:**
  - Follow Option B of rule 6.7: grandparents in the SE (about u 13.6–18.0, v 11.6–16.4) with a 2.4 m SSE window and a 1.6 m ENE slider. That gives 6.8 h on Dec 21.
  - Move the loggia to the NE.
  - **Conflict:** the boys' room would shift to u 5.0–9.3, where ground is +1.3 to +1.8 m above the floor. That breaks rule 4.8. C11 must either fit three rooms of about 3.7 m width between u 6.8 and 18.0, or ask the owner.

### SUN-05 Lounge and lower hall (MAJOR)

- **Evidence** (`measured`):
  - The SSE slider sits behind a 4.8 m deep covered loggia: 1.6 h and 914 Wh/m² on Dec 21.
  - The ENE slider gets 1.2 h.
  - The hall's homework table is 7.6 m from any glass, lit only through a 2.2 m opening.
- **Correction:**
  - Make u 15.4–17.8, v 13.0–15.2 an open pergola. Keep a 1.2 m walkway at v 15.2–16.4.
    - The lounge then gets 2.8 h and 1,655 Wh/m² (+81%).
    - The main floor loses 5.3 m² of terrace.
  - Open the whole wall between hall and lounge (u 12.6).
  - Move the table to (14.0, 10.6).
  - Raise lower-floor glass heads to 2.8 m.

### SUN-06 Ventilation (MAJOR)

- **Evidence** (`measured`):
  - Road level: an 11.4 m through-path from the WSW front door to the ENE lobby door.
  - Main floor: living and master have two sides. The kitchen has SSE only.
  - Lower floor: boys, girls and hall have one side or none. Laundry and wet rooms have no openings.
- **Evidence** (`inferred`):
  - The summer wind comes from the W (27.7% of hours), onto the buried side.
  - The summer air is dry (20% RH), so night purge is the reliable method.
- **Correction:**
  - An operable rooflight of about 1.2 × 1.0 m over the stair at about 1681, giving an 11 m stack.
  - Girls: a high window at u 15.4, v 14.4–15.2, sill 1.8 m.
  - Transfer grilles in the bedroom doors.
  - Laundry: a high window at u 6.0–6.8, v 16.4, sill 2.2 m (ground there is 1671.3–1672.0), plus mechanical extract.

### SUN-07 Lawn (MINOR)

- **Evidence** (`measured`): share of the lawn in sun on Dec 21:

  | Part of lawn | 13:00 | 14:00 | 15:00 |
  |---|---|---|---|
  | Whole lawn | 34% | 19% | 11% |
  | v < 11.6 | — | 0–6% | — |
  | v 11.6–17.4 | — | 71% | — |

  On Mar 21 at 14:00, the band at v 11.6–17.4 is 38% in sun.
- **Correction:**
  - Play equipment, sandpit and winter bench at u 19.2–22, v 12–17.
  - No evergreens in that band.

### SUN-08 Stair (MINOR)

- **Evidence** (`measured`): ground at (8.0, 1.1) is 1673.19. The mid-landing is at about 1675.5.
- **Correction:**
  - A window strip at u 7.6–8.6, v 1.1, from 1674.4 to 1680.0.
  - Obscure glass if the north neighbour is close (unknown).

### SUN-09 Master NNW window (MINOR)

- **Evidence** (`measured`):
  - Dec 21: 0 h.
  - Jun 21: 4.5 h, 13:50–18:10, 1,128 Wh/m².
  - The window is 1.1 m from the boundary.
- **Correction:** shrink it to u 15.6–16.8 with an external shutter. Keep it for cross-ventilation.

### SUN-10 Views (MINOR)

- **Evidence** (`measured`):
  - The ENE view reaches the living room, master, lounge, grandparents' room and office.
  - A seated eye in the living room is at 1674.8. Over a 1.1 m solid parapet 1.6 m out, the sight line drops 3.6°. It passes the tree bank (u 28) at 1674.2, so a tree must be more than 8 m tall to be seen.
  - The city's bearing is unknown.
- **Correction:**
  - Glass or thin-bar balustrades.
  - Trees that mature at 10–12 m.
  - Ask the owner for the city's bearing.

### SUN-11 Children (MINOR)

- **Evidence** (`measured`):
  - Both beds sit at v 15.25–16.25, under the only window. Cold air falls onto them, and the window is hard to reach.
  - The boys' glass is 15% of floor area.
  - Anything above about 1677 within 10 m to the south blocks the noon sun. **Unknown: what may be built there.**
- **Correction:**
  - Widen the boys' window to u 7.4–10.6.
  - Put the bed heads on the side walls.

### SUN-12 Drawings (MINOR)

The plans show grid north only. Add true north, the 158° and 68° façade bearings, the qibla, and the Dec and Jun sun arcs. "South" on the plans is 22° east of true south.

## What C10 gets right

- The day rooms face SSE with no overhang: 6.8 h of sun on Dec 21.
- The south terrace ends flush, so the children's rooms get full winter sun. Ground is at most +0.47 m, below the sill.
- The south terrace is 100% in sun from 09:00 to 15:00 on Dec 21.
- The master bedroom gets morning sun and the view, as promised.
- All service rooms sit in the buried NW; no bedroom faces a trench.
- The living room has openings on two sides.

## Out-of-scope notes

- Rule 6.7 conflicts with rule 4.8 over where the boys' room can go.
- The stair stack needs a fire and smoke check.
- The footpath is close to the children's rooms (privacy).
- About 54% glazing needs an energy check.
