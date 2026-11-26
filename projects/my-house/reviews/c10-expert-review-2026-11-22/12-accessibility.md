# 12 · Accessibility and ageing in place: review of C10

Scope: rule 5.4. Test users: a wheelchair user (1.5 m turning circle, 0.85 m clear doors) and a grandparent with a walker. Clearances use C10's walls (exterior 0.30, interior 0.12). Benchmarks marked (assumption) are common practice (ISO 21542 / M4(2)-type), not a checked code.

## Summary

1. The lift serves all three floors with its door on the same face, and road door → lift is level and short. The core of rule 5.4 works.
2. Rule 6.7 asks for a private accessible ensuite in the parents' suite. C10's master ensuite sits behind two 0.8 m doors and a dressing room and has no turning space. **BLOCKER.**
3. The main and road floors have no accessible WC. The only one is inside the grandparents' bedroom.
4. Furniture blocks the lift route on two floors: 0.84 m in front of the lower-floor lift, 0.25 m past the garage bikes.
5. In a power cut, the grandparents are 46 risers below the road, and no outdoor route anywhere is step-free.

## Findings

| ID | Sev. | Where | Issue |
|---|---|---|---|
| ACS-01 | BLOCKER | main · `ens`, `dress`, `mlob` | Master ensuite not accessible (rules 6.7, 5.4) |
| ACS-02 | MAJOR | main wet cluster; road `wc-r` | No accessible day WC |
| ACS-03 | MAJOR | lower · `hall-l` | Table blocks the lift landing |
| ACS-04 | MAJOR | road · `garage` | Bikes and workbench block garage → lift |
| ACS-05 | MAJOR | lower · `guest` | No bed-transfer space; door approaches blocked |
| ACS-06 | MAJOR | lift, stair | No power-cut or evacuation plan |
| ACS-07 | MAJOR | front door; terraces | 0.10 m step; −0.02 m roof-terrace thresholds unbuildable |
| ACS-08 | MAJOR | 1.6 m sliders | About 0.75 m clear |
| ACS-09 | MAJOR | `gs-lawn`, `gstair` | 14- and 22-riser single flights |
| ACS-10 | MINOR | lower · `gens` | Shower and door need upsizing |
| ACS-11 | MINOR | lift | Car and door not specified |
| ACS-12 | MINOR | main · `kitchen` | No turning circle |
| ACS-13 | MINOR | `court-w` | Not step-free from the road, and cannot be |

## Finding details

**ACS-01 BLOCKER: master ensuite.** *Measured.* The route runs:
1. Hall → `mlob` (1.08 m clear).
2. 0.9 m door into the bedroom.
3. 0.8 m door at (13.2, 4.1–4.9) into the dressing room, then a 1.04 m aisle (v 3.9–4.94).
4. 0.8 m door at (11.4, 3.9–4.7) into the ensuite, 1.88 × 3.69 m clear.

Inside, 0.70 m separates the basins (u ≤ 10.0) from the WC bowl (u ≥ 10.70). Rule 6.7 names a "Private Accessible Ensuite", and rule 5.4 names the broken leg, most likely to happen to the parents.
*Correction:* The two inner doors become 0.9 m pocket sliders, and `mlob` → master a 1.0 m leaf. Cut the dressing joinery back to v ≤ 3.7, for a 1.24 m aisle. Re-plan the ensuite:
- flush wet zone across the north, 1.88 × 1.5 m (v 1.25–2.75), with a fold-down seat; it doubles as the turning circle;
- WC on the west wall at v 3.3, one wall-hung basin at v 4.4;
- 1.18 m clear aisle along the east side.

**ACS-02 MAJOR: day WC.** *Measured:*
- `wc-m`: 1.29 × 1.89 m clear, 0.75 m door, reached through the wudu (0.99 m clear beside its bench).
- The lobby baffle at v 5.4 leaves 0.54 m.
- `wc-r` (road floor): 1.88 × 1.49 m, 0.8 m door.

`space_program.yaml` `pi-bath-1` (accessible, must, entry level, ≥ 2.2 m wide) is unmet.
*Correction:* Keep the 4-part cluster (rule 6.7) but swap the north cells:
- shower → R(3.8, 2.8, 5.0, 4.9);
- accessible WC → R(5.0, 2.8, 6.8, 4.9), 1.68 × 1.89 m clear: pan against the north wall, centred 0.45 m off the east wall, 0.9 m transfer space to its west;
- door: 0.9 m pocket slider at u 5.84–6.74, reached head-on through the 1.38 m lobby from the existing hall opening.

The free baffle cannot stay. The solid WC door is the screen (**owner decision**).

**ACS-03 MAJOR: lower hall.** *Measured.* The homework set needs 2.3 m. Its north chair ends at v 8.2, leaving **0.84 m** between it and the lift door (v 7.36).
*Correction:* Keep v 7.36–8.9, u 9.6–12.5 clear: a 1.5 m circle at the lift and a 1.2 m route to the `guest` door. Replace the set with a wall desk at u 8.3–10.0, v 11.0–11.54.

**ACS-04 MAJOR: garage.** *Measured.* The bikes R(5.4, 7.0, 6.75, 7.8) leave **0.25 m** beside car 2 (front at u 5.15). From car 1 or the gap between the cars, there is no other way to the 1.0 m lobby door. Car 1 front to workbench: 0.8 m.
*Correction:*
- Move the bikes to the north wall at u 0.2–1.0.
- Workbench to v 1.5–4.0, giving a 1.2 m aisle at u 5.2–6.74 from v 4.2 to 9.35.
- Keep the 2.2 m gap between the cars as the transfer bay.
- Give the fire door to the lobby power-assisted hold-open (assumption).

**ACS-05 MAJOR: grandparents' room.** *Measured:*
- Bed u 15.2–17.0 has 0.94 m clear west and 0.85 m east; a transfer side needs ≥ 1.2, ideally 1.5 (assumption).
- Latch-side space inside the hall door is 0.2 m (latch at u 12.5, wardrobe from 12.7); about 0.6 is needed (assumption).
- The 0.9 m ensuite door swings into a 1.39 m zone that a wheelchair cannot clear.

*Correction:*
- Twin beds 0.9 × 2.0, heads north, at u 14.3–15.2 and 16.95–17.85: a shared **1.75 m** transfer and turning zone between them, so one elder can be nursed separately.
- Wardrobes to u 13.3–15.8, v 6.65–7.25: a 1.84 × 1.98 m clear zone inside the door.
- Ensuite door as a pocket slider (ACS-10).
- Delete the armchair at (16.6, 6.3).

**ACS-06 MAJOR: power cut and evacuation.** *Inferred.* The stair works without power (rule 5.2). A standard lift rescue lowers the car, here away from the road. The level exit from the lower floor to the garden terrace is a good refuge, but every way on from it climbs ≥ 3.8 m in steps.
*Correction:*
- Lift with automatic battery rescue plus backup for ≥ 5 full trips, on an essential circuit (PV/battery or a generator inlet; assumption).
- Manual evacuation chair at the lower stair foot. The 1.14 m flights and 1.40 × 2.6 m landing allow its turn (measured).
- Rail and sockets prepared for a future battery stair-lift.
- Emergency lighting on the stair and in the halls.
- Drain the garden-terrace refuge (ACS-07).

**ACS-07 MAJOR: thresholds.** *Measured.* Forecourt 1677.40 vs road floor 1677.50 makes a **0.10 m step** at the accessible front door. The main-floor terraces at −0.02 m sit on roofs over occupied rooms, and a membrane cannot turn up in 20 mm (inferred).
*Correction:*
- Forecourt: rise to 1677.48 within 1.5 m of the door, falling 1:50 to a channel. The road is 1677.18–1677.49 at the boundary (TIN).
- Terrace slabs: set 0.15–0.20 m down, with pedestal paving at −0.015 and a 150 mm grated drain at each door; sill ≤ 15 mm, bevelled.

**ACS-08 MAJOR: sliders.** *Inferred.* A two-panel 1.6 m slider gives about 0.70–0.75 m clear. It is used at the grandparents' terrace door, at kitchen → south terrace (rule 1.1, daily) and at the office.
*Correction:* 2.0 m units with a 1.0 m moving leaf (≥ 0.9 m clear), or a 1.0 m hinged leaf plus a fixed light.

**ACS-09 MAJOR: garden and court stairs.** *Measured:*
- `gs-lawn`: 2.38 m in 14 risers over 3.6 m (0.170 rise / 0.277 going, about 32°), one flight.
- `gstair`: 3.80 m in 22 risers (0.173 / 0.276), one flight.

*Correction:* Garden stairs at ≤ 0.15 rise, ≥ 0.35 going, ≤ 10 risers per flight, 1.2 m landings and width, rails both sides (assumption):
- lawn: 8 + 8 risers, run 6.1 m;
- road → court: 3 flights, 26 risers, run 10.5 m (far west, as the owner proposed).

A step-free lawn needs about 33 m of 1:12 ramp. Alternatives are an outdoor platform lift (2.4 m travel) at the terrace's SE corner, or accepting the terrace and loggia as the level outdoor rooms (**owner decision**).

**ACS-10 MINOR: `gens`.** *Measured:* 2.59 × 2.19 m clear. The 1.5 m circle overlaps the tray by 0.4 m. The WC sits 0.45 m off the side wall, with 1.5 m of transfer space: good.
*Correction:*
- Tray-free wet zone 1.5 × 1.2 m with a fold-down seat.
- 1.0 m pocket door.
- Grab rails.
- Mechanical extract (no window).

**ACS-11 MINOR: lift.** *Measured:* shaft 2.0 × 2.3 m on centrelines, about 1.8 × 2.1 m clear with 0.2 m concrete walls.
*Specify:*
- car ≥ 1.1 × 1.4 m (1.25 × 1.6 preferred);
- one automatic door ≥ 0.9 m clear on the south face;
- seat and handrail;
- pit below 1670.00 and overrun above 1677.50 to be confirmed by a supplier.

**ACS-12 MINOR: kitchen.** *Measured:* aisles of 1.15 m and 1.0 m, and no 1.5 m circle.
*Correction:* Island 1.4 × 0.8 m at u 7.0–8.4, v 10.5–11.3, stools at its east end. This leaves a 1.5 m circle at the sink/hob corner (u 5.25–6.75, v 10.85–12.35).

**ACS-13 MINOR: arrival court.** A 3.8 m rise needs about 46 m of 1:12 ramp, which cannot fit. Accept the lift as the step-free route and mark the road door as the accessible entrance. The `entry` court door itself is level.

## What C10 gets right

- One lift with three same-face stops, 2–4 m from every front door; garage → lift indoors is 4 m.
- The grandparents' room is 2 m from the lift, with a 1.0 m door, its own seated ensuite and a level exit outdoors.
- The stair is comfortable: 0.163 rise, 0.31–0.34 going, 12-riser flights, a 1.40 m rest landing. It works without power.
- Each floor is one flat level, and the court door and terraces are within 20 mm of floor level.
- The lift landings on the road and main floors are 2.08 m deep, and the road hall is 1.45 m clear.
- The lower-floor tea bar means no stairs at night.

## Out-of-scope notes

- Structure: terrace slab set-downs; lift pit and overrun.
- MEP: lift backup power; extract for windowless wet rooms.
- Landscape: regraded garden stairs need a site check.
