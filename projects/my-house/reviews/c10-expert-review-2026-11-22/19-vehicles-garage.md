# 19 · Vehicles, garage and road interface (C10 review)

## Summary

1. The garage floor (1677.50) is within 0.0–0.2 m of the road edge: no ramp on a 35% hill. Keep it.
2. The boundary meets the garage façade at 28.7°. The forecourt is 0.86–2.69 m deep in front of shutter 1 and 3.11–4.94 m in front of shutter 2. Both are less than one LC300 (4.98 m), so every car waits on the road.
3. Swept paths with 0.3 m clearance: driving nose-in to bay 1 from the north uses 9.0 m of road, all of it. Reversing in uses 3.1–3.3 m. Leaving bay 1, the driver sees 2.5–3.0 m to the north.
4. The bikes and car 2's nose leave 0.25 m on the only path to the lobby door, so rule 5.1 fails in use. The workbench leaves 0.6–0.7 m in front of the bumper.
5. There are no gates, no vehicle barrier at a 3.8 m drop, and the forecourt is graded flat, so road water runs in. The fire door to a lobby that is open to the stair is not specified.

## Findings

| ID | Sev. | Where | Issue |
|---|---|---|---|
| VEH-01 | BLOCKER | `garage` u 5.15–6.75, v 6.4–8.4 | Bikes and car 2 block the walk to the lobby door (rule 5.1 in use) |
| VEH-02 | BLOCKER | bay 1 exit | Blind: 2.5–3.0 m of sight to the north |
| VEH-03 | MAJOR | shutters v 3.25 / 7.35 | 28.7° skew: entering from the north uses 7–9 m of road |
| VEH-04 | MAJOR | `fore` | Shallower than one car; nowhere to stop off the road |
| VEH-05 | MAJOR | `garage` east wall | Bench 0.61–0.71 m from the bumper; car 0.20 m from the curtain |
| VEH-06 | MAJOR | `fore`, thresholds | Flat forecourt at or below the road edge; 0.10 m steps |
| VEH-07 | MAJOR | `fore` edge v 11.6 | 3.8 m drop beside the swept path; up to 3.0 m of fill |
| VEH-08 | MAJOR | road frontage | The brief's separate vehicle and pedestrian gates are missing |
| VEH-09 | MAJOR | door `garage`→`lobby-r` | One unspecified door between the cars and the only stair |
| VEH-10 | MINOR | shutter heads | Coil box, lintel and power-cut operation not defined |
| VEH-11 | MINOR | `garage` | No EV provision (`f-ev_charging` unknown) |

## Finding details

**VEH-01 · BLOCKER.**
Evidence (`measured`, design.py):
- Car 2 is drawn at u 0.35–5.15. The bikes take u 5.40–6.75, v 7.0–7.8, leaving a 0.25 m gap. With an LC300 in bay 2 the gap is 0.07 m.
- Behind the cars there is 0.20 m.
- Anyone coming from bay 1 has no walkable route to the door at v 7.9–8.9. `checks.py` passes 5.1 only because it reads the door chain and ignores the furniture.

Correction: keep an **unloading aisle u 5.54–6.74 across the full garage (v 1.25–9.44)**, clear below 1.9 m. Cars park between u 0.55 and 5.54. The bikes move as set out in VEH-05.

**VEH-02 · BLOCKER (unsafe).**
Evidence: sight lines measured from the geometry. The driver's eye is taken 2.4 m behind the front bumper or 2.6 m ahead of the rear (`inferred`), and the neighbour's land as opaque. Sight is measured to the north, along the near and far lane centres.

| Exit | Near lane | Far lane |
|---|---|---|
| Bay 1, nose-out (eye still inside, u +0.62) | 3.0 m | 6.5 m |
| Bay 1, reversing out | 2.5 m | 5.0 m |
| Bay 2, nose-out | 14.5 m | 30 m |
| Bay 2, reversing out | 14.0 m | 28 m |

- To the south every bay sees more than 60 m.
- Bay 1 stays blind even with no neighbour wall, because the garage's own north wall blocks the view.
- About 25 m is needed at 30 km/h (`assumption`).

Correction:
- Put the **LC300 in bay 2**, and make **reverse-in, drive-out** the rule.
- Fit a convex mirror opposite the doors (consent `unknown`) and a reversing camera.
- Confirm the road's traffic and speed (`unknown`).

**VEH-03 · MAJOR: swept paths.**
Method: simulated single manoeuvres (straight, arc, then along the road). The car is an LC300 of about 4.985 × 1.98 m, wheelbase 2.85 m, turning circle 11.8 m, so rear-axle radius 4.34 m (dimensions `inferred`). It keeps 0.3 m clear of jambs, walls and the parcel edge. Results are `measured` as the road depth used, from the boundary, out of 9.0 m.

| Manoeuvre | Bay 1 (C10) | Bay 2 (C10) | Bay 1 (fix) | Bay 2 (fix) |
|---|---|---|---|---|
| Nose-in from N (118°) = reverse out, leave S | **9.02** | 7.05 | 5.04 | 7.19 |
| Nose-in from S (61°) = reverse out, leave N | 4.86 | 2.89 | 5.26 | 2.43 |
| Reverse in (61°) = drive out S | 3.06 | 3.29 | 3.04 | 3.20 |
| Drive out N (118°) | 6.08 | 4.12 | 6.05 | 3.58 |

- Bay 1 nose-in from the north is impossible in one move. A car parked on the far kerb turns it into a 3-point turn on the road.

Correction:
- Replace the two shutters and their 0.75 m pier with **one 7.45 m opening at v 1.45–8.90**. The lintel carries only the roof.
- Set the bay centres at **v 3.14 and 6.89**.
- Use reverse-in parking.

Still to survey: whether "9 m" is the carriageway or the right-of-way, and whether a *jub* (open gutter) or footway runs along the boundary (`unknown`). A jub needs a culvert slab across the opening.

**VEH-04 · MAJOR: forecourt.**
Evidence (`measured`, depth along −u at the north jamb / centre / south jamb):
- Shutter 1: 0.86 / 1.78 / 2.69 m.
- Shutter 2: 3.11 / 4.02 / 4.94 m.

Correction:
- Fit a fast door operator (≥0.2 m/s) with a remote.
- Mark a **2.2 × 6.6 m stop bay parallel to the road**, corners (−2.22, 4.48), (−5.39, 10.27), (−3.46, 11.33), (−0.29, 5.54), for deliveries. It blocks bay 2 only while in use.
- Long-stay visitors park on the road (about 6.8 m stays clear).
- Do not take the strip south of v 11.6 for a lay-by: rule 4.10 gives it to the road stair.

**VEH-05 · MAJOR: layout inside the garage.**
Evidence (`measured`): the clear interior is u 0.15–6.74 by v 1.25–9.44.
- The tail of the drawn LC300 is 0.20 m from the face where the curtain hangs.
- With a 0.40 m clearance there, only 0.61 m is left in front of the bench (≥0.9 m needed, `ai_judgment`).

Correction (v bands, clear):

| Zone | v | Width |
|---|---|---|
| North door zone | 1.25–2.15 | 0.90 m |
| Car 1 | 2.15–4.13 | 1.98 m |
| Shared door zone | 4.13–5.90 | 1.77 m |
| LC300 | 5.90–7.88 | 1.98 m |
| Door and bench working zone | 7.88–8.84 | 0.96 m |
| Workbench (u 2.8–4.9) and flat-hung bikes (u 0.6–2.6) | 8.84–9.44 | 0.60 m |

- Every door zone is ≥0.65 m (rule 6.7).
- Fit wheel stops.
- With reverse-in parking the liftgate opens over the aisle, about 2 m from the lobby door.
- Bench: RCD circuit, steel cabinet for fuel and solvents.
- The garage stays at 57.1 m² gross.

**VEH-06 · MAJOR: apron and drainage.**
Evidence: road edges interpolated on the boundary (`inferred`; the road itself is not surveyed).

| v | 1.1 | 3.25 | 6.0 | 7.35 | 9.5 | 11.6 |
|---|---|---|---|---|---|---|
| Road edge | 1677.43 | 1677.38 | 1677.32 | 1677.37 | 1677.46 | 1677.51 |

- With the forecourt flat at 1677.40, the road sits 0.06–0.11 m above it at v 9.5–11.6, so runoff and snowmelt flow towards the front door and the shutters.
- There are 0.10 m steps at the shutters and at the front door.

Correction:
- Survey kerb and crown levels every 3 m.
- Forecourt: **1677.47 at the shutters and 1677.48 at the front door**, falling 2–5% to a **channel drain along the boundary**, with its grate 20 mm below the road edge.
- A slot drain across the opening at u −0.30, with flush thresholds.
- Garage floor falls 1% westward (1677.50 to 1677.47) to an internal trench drain, then to an oil/silt interceptor. It never falls towards the lobby.
- The garage slab roofs the main-floor wudu, pantry and hall, so it needs a tanked build-up of about 0.40 m within the 3.9 m floor-to-floor.

**VEH-07 · MAJOR: drop and fill.**
Evidence (`measured`):
- The forecourt edge at v 11.6 (u −6.35 to 0) drops 3.80 m to the arrival court and the head of the stair.
- Reversing out of bay 2 and leaving to the south sweeps this zone.
- checks.json shows up to 3.0 m of fill.

Correction:
- Build an **RC vehicle-restraint upstand (0.6 m) with a 1.1 m guard** along v 11.6, and add 2 bollards at the stair opening.
- Fill on a retaining wall over an engineered sub-base. Impact loads and the geotechnical design are for the engineer.

**VEH-08 · MAJOR: gates.**
Evidence: the brief says "separate vehicle and pedestrian gates". The owner says "a door for the garage … and there's a door beside it … you're in a perimeter". C10's forecourt and road stair are open.

Correction:
- The shutters are the vehicle gates. A forecourt gate cannot work with 0.86 m of depth.
- Add a **1.2 m lockable pedestrian gate on the boundary at the head of the relocated far-west road stair** (rule 4.10), with intercom and parcel box.

Owner to confirm.

**VEH-09 · MAJOR: fire door.**
Evidence (`measured`): `lobby-r` is open 2.6 m to the stair and 2.2 m to the hall.

Correction:
- A **fire-resisting, smoke-sealed door**, about 60 minutes (`assumption`; Iranian National Building Regulations Part 3 governs), 1.0 m clear.
- An automatic opener with fire-alarm release, which also keeps the route step-free for rule 5.4.
- Fire-separating walls and slab.
- A CO detector, and permanent high- and low-level ventilation.

**VEH-10 · MINOR: headroom.**
The road level is 3.0 m clear and the shutter 2.5 m high (`measured`, model3d.py). An LC300 is about 1.95 m tall, 2.4 m with a roof box (`inferred`).
- Use an **upstand lintel** so the soffit stays at 1680.50.
- The coil box is about 0.35 m (0.45 m for a 7.45 m roller), which keeps a 2.50 m opening head.
- Add a manual override or battery back-up, and wind locks.

**VEH-11 · MINOR: EV.**
Run a 3-phase, 32 A-capable cable from the plant room to a wall box at **u 6.74, v 5.0**, 1.2 m high and guarded by a bollard, with a 7.5 m tethered cable that reaches both bays.

## What C10 gets right

- The garage is level with the road (1677.50 against 1677.32–1677.51): no ramp and no icy apron.
- The garage-to-lift route is about 4 m through one door.
- There are two closable full bays, 57.1 m², within 55–60 m².
- The front door is separate from the vehicle doors, on the west façade.
- The 3.0 m clear storey takes a 2.5 m door plus its coil box.
- Bay 2 has 3.1–4.9 m of forecourt and 14–15 m of sight to the north.

## Out-of-scope notes

- Structure: the garage's west wall bears on ground down to 1674.78 at v 9.5, so it needs foundations about 2.7 m deep.
- Stairs: the 22R road stair rises 0.173 m per step; check it against rule 4.11.
