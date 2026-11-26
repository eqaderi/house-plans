# 18 · Interior space and vertical dimensions (INT) · C10

Concept stage. Build-up and structure depths are `assumption`; ground heights from `zg` are `measured` on an inferred TIN.

## Summary

1. The 3.90 / 3.60 m floor-to-floor heights leave every room at least 2.65 m clear after real build-ups.
2. The terraces drawn 0.02 m (road deck 0.05 m) below the floors can be built. They need a slab recessed 0.20 m, a drain at each door and a canopy. None of that is drawn.
3. The ground slabs are drawn 0.35 m deep; they need about 0.65 m, which makes the dig 0.30 m deeper.
4. The sofa looks down the 10.6 m hall (rule 3.1); the lower hall is dark; the grandparents' north window faces a slot.
5. The windowless rooms have no ventilation riser, and the garage sits over them.

## Clear heights (m)

| Room | Above it | Build-up + slab | Clear | Under beam |
|---|---|---|---|---|
| Kitchen, dining, hall east (main) | road floors | 0.12 + 0.20 | 3.55 | 3.20 |
| Hall west, pantry, wet cluster (main) | garage | 0.22 + 0.25 | 3.40 | 3.05 |
| Living (main) | `deck-r`, top 1677.45 | 0.30 + 0.22 | 3.30 | 2.95 |
| Master (main) | green roof, top 1677.45 | 0.40 + 0.22 | 3.20 | 2.85 |
| Lower hall, lounge, grandparents | main floor | 0.12 + 0.20 | 3.25 | 2.90 |
| Boys and girls, south 3.4 m (lower) | `t-south`, top 1673.58 | 0.30 + 0.22 | 3.03 | 2.65 (transfer beam at v 13.0) |
| Loggia (lower) | `t-south` | same | 3.08 | — |

## Findings

| ID | Sev. | Where | Issue |
|---|---|---|---|
| INT-01 | MAJOR | all terraces over rooms | The −0.02 / −0.05 m terrace levels need recessed slabs and drained, covered thresholds; none are drawn |
| INT-02 | MAJOR | ground slabs | Formation 0.35 m below the floor is too shallow |
| INT-03 | MAJOR | main `living` | The sofa looks down the hall, and people entering cross the TV zone (rule 3.1) |
| INT-04 | MAJOR | lower `hall-l` | Windowless; the homework table is 7.6 m from glass |
| INT-05 | MAJOR | windowless rooms | No ventilation riser |
| INT-06 | MAJOR | lower `guest` | The north window opens into a dark slot under the master bedroom |
| INT-07 | MINOR | lower `lounge` | The covered loggia blocks winter sun |
| INT-08 | MINOR | road `hall-r` | The front-door axis ends at the office door |
| INT-09 | MINOR | main `entry` | The court door is uncovered |
| INT-10 | MINOR | main `dining` | 66% of its perimeter is openings |
| INT-11 | MINOR | all | No ceiling-height strategy; the living room height |
| INT-12 | MINOR | stair | Treads differ between flights; no daylight |
| INT-13 | MINOR | garage, lift | Garage floor at the lobby level; lift overrun and pit |

## Finding details

**INT-01 (MAJOR): terrace levels over rooms.**
- A terrace build-up is pavers, protection layer, 0.14 m XPS, membrane and screed to falls: about 0.30 m (`inferred`).
- An internal floor needs 0.12 m, so the structural slab must step down about 0.20 m at each façade line. Slab top: 1673.28 under the terrace against 1673.48 inside; 1677.15 under the deck against 1677.38 inside.
- None of the 7 terrace doors has more than 0.3 m of cover: the kitchen and dining sliders at v 13.0, both living sliders, the master slider, the office door and the lobby door. A level threshold under snow needs a drain and a cover overhead.
- **Fix:**
  - Keep −0.02 m (step-free, rule 5.4).
  - Draw the recessed slabs.
  - Put a 150 mm grated channel at each of the 7 doors.
  - Add 1.0 m canopies at +2.50 m.
  - Use an uninsulated 0.12 m build-up with thermal breaks over the loggia and the balconies beyond u 18.0.
  - Make the green roof extensive (0.40 m total, ≤ 1.8 kN/m² saturated), not 0.3–0.4 m of soil (about 5 kN/m² of seismic mass).

**INT-02 (MAJOR): slabs on ground.**
- `checks.json` puts the formation 0.35 m below the floor.
- Gravel, blinding, tanking, XPS, a 0.20 m slab, the underfloor-heating screed and the finish add up to about 0.60–0.65 m.
- **Fix:**
  - Lower the formation to 1669.35 (lower floor) and 1672.95 (main floor).
  - That is about 47 + 11 m³ more cut (`measured`, area × 0.30).
  - The deepest cut becomes 3.97 → about 4.27 m. Rule 4.7 (≤ ~4.5 m) still passes, but only just.

**INT-03 (MAJOR): rule 3.1 in the living room.**
- The hall opening (u 12.6, v 7.6–9.2) lies on the hall's axis (`measured`).
- The sofa's east leg (u 16.7–17.6, v 6.45–8.75) faces west, through the opening and down 10.6 m of hall to the entry.
- People entering pass between the TV (v 6.4–7.5) and the sofa.
- **Fix:**
  - Move the opening to v 8.5–9.5 (1.0 m).
  - Run the TV wall from v 6.2 to 8.5.
  - Put a 1.1 m-high open shelf at u 13.6–14.0, v 8.5–9.6. As furniture it keeps the 5.0 m clear square of rule 3.3, and it turns people entering toward the dining room.

**INT-04 (MAJOR): lower family hall.**
- The hall is 4.4 × 4.3 m with no window (`measured`).
- Its only light comes through a 2.2 m opening from the lounge, whose glass is at u 18.0.
- The table at (10.4, 9.35) is 7.6 m from the glass, about 2.8 × the window head height (`inferred`: artificial light all day).
- **Fix:**
  - Widen the opening to 2.6 m (v 7.9–10.5).
  - Raise the lounge's east glazing head to +2.90.
  - Put a walk-on rooflight of 0.8 × 1.8 m in the open strip of `deck-r` (u 11.4–12.2, v 7.5–9.3). It lights the main hall's dark east end.
  - Optional (owner's cost decision): a glass floor panel below the rooflight into `hall-l`.
  - Move the table to u 11.5–12.5.

**INT-05 (MAJOR): ventilation for windowless rooms.**
- On the main floor, the pantry and the wet cluster are buried and sit under the garage.
- On the lower floor, the WC, shower, basins and the laundry with drying are buried.
- No riser is drawn.
- **Fix:**
  - Add one 0.5 × 0.6 m fire-rated riser at u 6.3–6.8, v 6.7–7.3, running through all three levels: inside `wlob`, against the garage's east wall, and in a pocket behind `wc-l`. It exhausts above the road roof.
  - Duct ceilings: 2.70 m (main wet cluster and west hall), 2.60 m (lower wet rooms and laundry).
  - Run the kitchen hood duct out the south wall in a 0.25 m bulkhead.

**INT-06 (MAJOR): grandparents' north window.**
- `guest` starts at v 2.8, but the master bedroom above starts at v 1.1 (`measured`).
- The window at u 16.0–17.6 therefore faces a 1.7 m-deep roofed slot. The ground there is at 1669.78–1669.99, the room's own floor level, so runoff drains toward the glass.
- **Fix:**
  - Extend the north wall to v 1.1 for u 15.0–18.0 (+5.1 m²) and delete the north window.
  - Make the new bay a window-seat nook with an east window at u 18.0, v 1.3–2.7. The ground there is 1669.4–1669.6, below the floor.
  - This also gives the master's north-east corner a wall to stand on (rule 4.9).
  - Close the slot at u 11.4–15.0 with a wall and fill.

**INT-07 (MINOR): loggia shades the lounge.**
- The loggia is fully covered (soffit about 1673.06).
- Winter-noon sun stands at 31.6°. Over the 4.8 m depth it drops 2.95 m, so it reaches the lounge slider only 0.11 m above the floor (`measured`).
- **Fix:** leave a pergola void in `t-south` at u 15.4–17.8, v 14.6–16.4 (−4.3 m²; about 65 m² of terrace remains, rule 4.3). Sun then reaches about 1.2 m up the slider.

**INT-08 (MINOR): road arrival.**
- From the front door (0, 10.75) the axis ends at the office door (9.0, 10.5).
- The line of sight to the deck glass door hits the garage wall at u 6.07 (`measured`). The README's "a glass door ahead" is wrong.
- **Fix:**
  - Move the office door to the lobby (10.2, 9.5).
  - Make the end wall a feature wall, lit by a 1.4 × 1.9 m rooflight at u 7.6–9.0, v 9.6–11.5.

**INT-09 (MINOR): main court door.**
- The door spans v 11.55–12.75, but the road hall above covers the court only to v 11.6 (`measured`).
- **Fix:**
  - Swap the door and the window: door at v 9.9–11.1, under a natural porch about 3.4 m high (u 0–2).
  - Fall the court 1.5% to a channel drain.

**INT-10 (MINOR): dining room.**
- 9.1 m of its 13.8 m perimeter is openings (`measured`).
- The 3.0 m hall opening lies 0.55 m behind the chairs, and no wall is long enough for a sideboard.
- **Fix:** narrow the hall opening to u 9.6–11.2. That keeps the lift → slider axis and frees a 1.4 m wall for a sideboard.

**INT-11 (MINOR): ceiling strategy.**
- A higher living room is possible, but at a cost:
  - sinking it 0.45 m gives 3.75 m clear but breaks step-free access (rule 5.4);
  - raising `deck-r` needs steps from the lobby.
- Instead, use a beam-free 0.25 m slab, with the perimeter beams as window heads at +2.90. That gives 3.27 m clear, the tallest room in the house.
- Proposed clear ceilings, low to high, so each room opens up after the space before it:

| Space | Clear ceiling (m) |
|---|---|
| Entry and hall | 2.70 |
| Kitchen | 2.90 |
| Dining | 3.20 |
| Living | 3.27 |
| Sofa corner | 2.70 band, 1.2 m wide (rule 3.1) |
| Lower hall | 2.80 |
| Lounge | 3.20 |
| Children's rooms, wardrobe zone (v 11.6–13.0) | 2.65 (hides the transfer beam) |
| Children's rooms, beds | 3.00 |

- In the children's rooms: south window heads at +2.65, plus a 0.45 m-high window seat.

**INT-12 (MINOR): stair.**
- Road → main: 24 risers of 162.5 mm and 309 mm treads. Main → lower: 22 risers of 163.6 mm and 340 mm treads (`measured`).
- Headroom is at least 3.3 m everywhere.
- **Fix:**
  - Use 310 mm treads on every flight: lower flights 3.10 m long, south landing 1.70 m.
  - Add a rooflight of 2.2 × 1.2 m over the north landing.
  - Add a window at the main → road half-landing: u 7.0–9.2, sill 1676.45, with the ground outside at about 1673.2. It brings daylight to the heart of the house (rule 5.3) and gives a place to pause.

**INT-13 (MINOR): garage and lift.**
- The garage and the lobby are both at 1677.50, so snowmelt runs into the lobby.
- **Fix:**
  - Set the garage floor at 1677.42, falling toward the shutters, with a channel drain at the lobby door.
  - Allow an overrun upstand of about 0.8 m above the road roof for the lift.
  - Allow a 1.2 m tanked pit (floor about 1668.8).

## What C10 gets right

- The day floor is 0.30 m taller; no room drops below 2.65 m.
- The lift door, the dining opening and the south slider line up (u 9.9–10.9): you step out of the lift and see the valley.
- From the garage door, a straight 4.6 m line leads through the lobby to the deck's glass door.
- The living room is 5.2 × 6.8 m, lit east and south.
- Kitchen and dining are 3.5 m deep, lit from the south; every bedroom window is above ground.
- The stair opens 2.6 m wide to the halls, at the heart of the house.

## Out-of-scope notes

- Dining is 11.1 m², below the 13.5–15.5 m² of rule 1.5.
- Tanks and a WC sit over the kitchen, and the transfer beam at v 13.0 needs structural review.
- The master's north windows sit 1.1 m from the boundary.
- The master–living bookshelf wall must be an acoustic wall.
