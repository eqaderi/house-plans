# 06 · Internal circulation, stair and lift: review of C10

Concept-stage review only; not engineered or code-checked. Product and code figures are `assumption`.

## Summary

1. The stacked dog-leg works: 46 risers in one box connect all three floors. Landings are 1.40 m and
   headroom is at least 3.2 m. Rule 5.2 is met in plan.
2. The lift is the weak part. Its lower landing is blocked by furniture, the shaft takes no stretcher
   car, and the pit and overrun are undesigned (the overrun pierces the road roof).
3. Garage → lift is blocked by the bikes, and the garage door swings toward the top of the down flight.
4. Daily walks are fine (child bed → WC 11 m; car → fridge 17 m), except three: wudu → prayer 14 m,
   laundry → outdoor drying 13 m, and the lawn, which is not step-free.
5. About 9 m² under the lower flights is dug, built and unused.

## Findings

| ID | Sev | Where | Finding |
|---|---|---|---|
| CIR-01 | BLOCKER | lower `hall-l` (10.4, 7.3–8.4) | 0.9 m clear in front of the lift door (rule 5.4) |
| CIR-02 | MAJOR | `LIFT` (9.4,5.0,11.4,7.3) | 1.80 × 2.10 m clear shaft: no stretcher car |
| CIR-03 | MAJOR | lift pit and head | Pit in the wet uphill corner; overrun above the road roof |
| CIR-04 | MAJOR | `garage` → `lobby-r` | Bikes leave a 0.25 m gap; door swings into the stair zone |
| CIR-05 | MAJOR | road `lobby-r` | Stair open to the garage lobby on all floors: cold and fume chimney |
| CIR-06 | MAJOR | main `wudu` → mats | 14.0 m; mats about 48° off qibla |
| CIR-07 | MAJOR | `guest` → `lawn` | Lawn 2.38 m down steep 1.2 m steps |
| CIR-08 | MAJOR | lower, under stair | About 9 m² of void (rule 2.3) |
| CIR-09 | MAJOR | lower `laundry` | Windowless buried drying strip |
| CIR-10 | MINOR | stair main→lower | Going 0.340 vs 0.309; drawing shows 24R |
| CIR-11 | MINOR | stair | No window on any flight |
| CIR-12 | MINOR | stair well 0.20 m | Open 7.5 m drop |
| CIR-13 | MINOR | main `hall` | 10.6 × 2.2 m with openings on both sides (rule 2.2) |
| CIR-14 | MINOR | main `mlob` | Master lobby opening 0.6 m from the lift door |

## Finding details

**Stair facts** (`measured` from `STAIR`, `stair_dogleg` and the levels).
- *Road → main.* 3.90 m in 24 risers of 0.1625. Each flight has 12 risers and 11 treads of 0.309 in a
  3.40 m run. 2R+G = 0.634.
- *Main → lower.* 3.60 m in 22 risers of 0.1636. Each flight has 11 risers and 10 treads of 0.340.
  2R+G = 0.667, a long stride.
- *Landings.* Rest landings at 1675.55 and 1671.80, each 2.6 × 1.40 m. Flights are 1.14 m to the wall
  face.
- *Arrival points.*
  - Road: you leave from u 6.8–8.0.
  - Main: you arrive at u 8.2–9.4, 0.5 m west of the lift door, and leave again from u 6.8–8.0.
  - Lower: you arrive at u 8.2–9.4, matching the 1.2 m opening.
- *Headroom.* 3.5 m or more under the west flights and 3.2 m or more under the east flights (0.25 m
  waist).

**CIR-01.**
- *Problem.* The homework chair at (10.4, 8.4) leaves 0.9 m of clear depth in front of the lift door
  (u 9.9–10.9). A wheelchair needs a 1.5 m circle; a stretcher needs about 2.2 m straight out. The
  boys' night route to the WC also passes 0.46 m from the chair at (9.45, 9.35).
- *Fix.*
  - Keep u 8.2–12.6 × v 7.3–8.9 clear as a "landing street".
  - Move the table to (10.0, 10.1), at most 1.0 m across, with chairs east and west only. Or move it
    into the lounge.

**CIR-02.**
- *Problem.* The box is 2.0 × 2.3 m gross. With realistic 0.20 m RC walls (C10 draws 0.12 m), the
  clear shaft is 1.80 × 2.10 m. A 1.10 × 2.10 m stretcher car (EN 81-70 type 3) needs about
  1.70–1.80 × 2.50–2.60 m (`assumption`). Today only a 1.10 × 1.40 m wheelchair car fits.
- *Fix.*
  - Set `LIFT = (9.4, 4.5, 11.4, 7.3)` with a 0.90 m clear door on the south face (keep).
  - Knock-on: the main `ens` becomes (9.4, 1.1, 11.4, 4.5), 6.8 m² with one basin. About 2.5 m³ more cut.
  - The long car also carries wardrobes up and down.

**CIR-03.**
- *Pit.* A pit of about 1.2 m puts the formation at about 1668.4. Natural ground there is
  1671.4–1671.8 (`measured`), so the pit is 3.0–3.4 m deep, at the uphill back wall. Groundwater is
  `unknown`.
  - *Fix:* tanked RC pit, perimeter drain at an invert of about 1668.2, falling about 10% east to an
    outfall on the tree bank (about 1666.5). Gravity drainage, no sump.
- *Overrun.* 3.5–3.7 m of top headroom puts the shaft soffit at about 1681.1. The road roof is about
  1680.8 (`inferred` from `sections.png`).
  - *Fix:* draw a roof upstand of 2.4 × 3.2 m, about 0.7 m high, or specify a low-headroom unit (about
    3.1 m). Add a battery rescue device for power cuts.

**CIR-04.**
- *Problem.*
  - Car 2's nose is at u 5.15 and the bikes are at u 5.4–6.75, so there is no route from the LC300 to
    the house door.
  - The door's leaf sweeps u 6.8–7.8 × v 7.9–8.9, 2.0 m from the top nosing.
  - The real route is 6.0 + 4.5 m to the lift, then 6.9 m to the fridge: not the README's "4 m".
- *Fix.*
  - Bikes on a rack above the workbench. Keep u 5.2–6.8 × v 6.2–9.5 clear.
  - Move the door to v 8.35–9.35, swinging into the garage and hinged at v 9.35 so it parks against the
    south wall. Self-closing, with seals.

**CIR-05.**
- *Problem.* The stair opens 2.6 / 2.6 / 1.2 m on the three floors. The road lobby carries the garage
  door, the terrace door and the front hall. In winter at 1670 m, cold air and garage fumes fall and
  rise through 7.5 m (`ai_judgment`).
- *Fix.* A glazed full-height screen with a 1.0 m self-closing glass door across u 6.8–9.4 at road
  level. It is a needed door (rule 2.4), and the view stays.

**CIR-06.**
- *Problem.* Wudu → hall → living opening → mats (15.9, 11.6) is 14.0 m, through the TV zone
  (`measured`). That is better than the 18.55 m of I11, but not the "direct short doorway" of rule 6.7.
  The mats face a bearing of about 157°; qibla is about 205° (`inferred` from the unconfirmed
  coordinates).
- *Fix.* Wudu within 5 m of the prayer bay: either a 0.6 × 1.2 m wudu niche with a floor drain at the
  hall's east end, or the wet cluster moved east of the core. Rotate the mats.

**CIR-07.**
- *Problem.* Only the terrace (24 m²) and loggia (12 m²) are step-free; bed → loggia is 11.5 m. The
  lawn is 2.38 m below, down 14 risers of 0.170 with goings of 0.277 and no handrail. A 1:12 ramp would
  be 28.6 m.
- *Fix.*
  - Easy stair: 16 risers × 0.149, going 0.35, 1.5 m wide, rails both sides, a landing after 8 risers
    (6.45 m run).
  - Step-free sitting space of 30 m² or more.
  - Tell the owner the lawn is stepped.

**CIR-08.**
- *Problem.* On the lower floor, the space under the west flight and rest landing is unused: about
  9.1 m², with soffits from 3.35 m down to 1.55 m (`measured`).
- *Fix.* Household store (rule 6.3) with a 0.8 m door at u 6.9–7.7 off the stair landing. This frees
  the laundry strip v 13.5–16.4.

**CIR-09.**
- *Problem.* The strip (u 5.0–6.8, v 11.6–16.4) is buried 1.85–2.28 m, with 0.8 m between benches.
- *Distances.*
  - to the loggia: 12.8 m, through the lounge;
  - to the boys' and girls' wardrobes: 6.7 / 8.1 m;
  - to the grandparents': 10.0 m;
  - to the master: 6.3 m + lift + 8.7 m.
- *Fix.* A heat-pump dryer, a ceiling airer and continuous extract (MEP to size it). A fold-down rack
  on the loggia's west wall (u 15.4, v 12–16).

**CIR-10.**
- *Fix (two choices).*
  - Main→lower as 24 risers × 0.150, with the same 11 treads × 0.309. One going everywhere, and the
    drawing becomes true.
  - Or keep 22 risers with a 0.309 going (3.09 m flights, 1.71 m rest landing).

**CIR-11.**
- *Problem.* Only the road→main rest landing (1675.55) stands above the north ground (1672.7–1673.6).
- *Fix.*
  - North window u 7.0–9.2 with its sill at 1676.45, obscured glass (1.1 m from the boundary).
  - A 2.6 × 1.4 m rooflight.
  - Battery step lights and glow nosings, so the stair works without electricity.

**CIR-12.**
- *Fix.* Balusters at 0.10 m or less, or a 0.15 m spine wall (which also stiffens the core). Handrails
  on both sides with 1.0 m or more between them. Make 2.6 m the internal clear width.

**CIR-13.**
- *Problem.* The hall's depth reaches 3.6 m at the stair; the west 4.8 m is corridor.
- *Fix.* Widen the kitchen opening to 1.6 m (u 5.6–7.2). The hall's length is the owner's call.

**CIR-14.**
- *Fix.* A 0.9 m door on `mlob` at (12.0, 7.3), for privacy. It is needed, so rule 2.4 holds.

**Other scenarios** (`measured`, fine):
- Girls' bed → WC: 10.8 m.
- Main court door → sofa: 15.7 m, with no bedroom door in view.
- Road door → living: 12.0 m + 24 risers + 8.4 m.
- Lift → grandparents' bed: 7.1 m.

## What C10 gets right

- One stacked dog-leg in one box on every floor. Arrival and departure share the south landing, and
  the road→main flights are textbook.
- The 2.6 m stair openings make the stair the heart of the house, not a shaft.
- The lift door is on the same south face on every floor, next to the stair foot.
- The lower family hall is 4.4 × 4.3 m, a real room, with bath, laundry and bedrooms within 4 m.
- The grandparents' door is 1.6 m from the lift, and their slider leads step-free to the terrace.
- Garage → lift is indoors, through a single door (rule 5.1).

## Out-of-scope notes

- Garage fire separation: see the life-safety review.
- The external road→court stair (22 risers) and the court→lawn path: landscape and access review.
- What structure carries the garage and the road lobby: structural review.
