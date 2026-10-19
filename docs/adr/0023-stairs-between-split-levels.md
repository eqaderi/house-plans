# ADR 0023 — Stairs between split levels

Date: 2026-10-19. Status: accepted for Stage S10 (ISS-29), awaiting stage review.

## Context

The S9 readiness assessment (FPR-05, FPR-08) found three faults in stairs that
join bars standing side by side at different floor levels:

1. `floor_connection_height_mismatch` fired on every split-level stair. ADR 0019
   compared a level's declared floor-to-floor height with the rise of any stair
   to the next level up. Between bars side by side that comparison is wrong: a
   3.0 m storey beside a bar 1.5 m or 4.5 m higher is consistent, because the
   higher floor does not rest on the lower storey.
2. Straight flights centred on the bar boundary rise under the lower bar's roof
   slab: on a 4.5 m rise the measured pitch-line headroom was 0.500 m. That
   finding was correct.
3. The flight crosses the boundary walls, and nothing checked it. Headroom
   looked only at slabs. On the S9 demonstration plans, the lower bar's
   boundary wall stands across the flight inside the clear band on all three
   split flights, and on a 1.5 m rise so does the higher bar's boundary wall.

## Decision

**Floor-to-floor only for stacked storeys.** A stair tests its bottom level's
declared floor-to-floor height only when it goes to the next level up *and*
arrives over a space of the bottom level. With a walking line, "arrives over"
means the arrival landing beyond the top end (`landing_m` long, flight-wide)
overlaps a bottom-level space in plan; without one (a U-shaped flight), the
whole top space is tested. The rise itself is still compared with the level
elevations (`stair_height_mismatch`) for every stair. This is a geometric test
on the canonical model, not generator metadata, so hand-written fixtures and
benchmarks are judged the same way.

**Flights may not walk through walls.** Where a wall's plan line crosses a
walking line, the wall's vertical extent (level elevation + `base_offset_m`, up
to `height_m`) must stay out of the clear band from the pitch line at that
point to `min_headroom_m` above it, unless an opening in that wall spans the
flight's width and the band. Otherwise `stair_wall_clash` is reported with the
band, and `stair_wall_clashes` counts them (measured).

**The generator models the junction as one stair volume on both levels.** The
straight flight stays centred on the bar boundary (`generation/assemble.py`).
The part of the flight on the higher bar's side runs below that bar's floor, in
a *stairwell* space on the lower level, walled from the lower floor up to the
higher floor slab's underside (`rise − 0.25 m`). The part over the lower bar
rises in a *stair hall* space on the higher level, walled from the lower roof
slab's underside (`3.0 − 0.25 − rise` relative to the higher floor) to the
higher storey's wall head (2.8 m). Each opens onto its stair space across the
boundary through a full-height opening as wide as the hall (flight width plus
0.1 m on each side). Where a level is already built over that region (a bar
stacked over another, as in the S8 `elevated` mode), the flight continues in that
existing room through the same opening instead. A flight occupies floor in every
space of its two levels it passes through, and a stair space with no floor beside
its flight is walked through, not walked to. Existing rules then do the rest:

- the lower roof is open under the stair hall (a roof is what no level above
  covers), and the stair hall carries the higher storey's roof;
- the higher floor is open over the flight, as before;
- stairwell walls are classified by the ground outside them: buried ones are
  retaining walls, with the professional findings that implies;
- earthworks measure the stairwell at the lower floor's slab underside, so its
  excavation is counted instead of hidden under the higher floor.

Rejected: limiting each link's rise by the depth of the higher bar and moving
the run onto the higher side. Leaving 2.0 m headroom and a 0.9 m landing needs
about 6.8 m of stair-space depth for a 4.5 m rise; the synthetic hillside's
rows are at most 6.6 m deep, so split-level and two-wing became infeasible,
and the S8 terrain band ruled out a smaller rise. Rejected also: relabelling the
lower storey's floor-to-floor height, which would hide the clash, not fix it.

The headroom (2.0 m) and landing (0.9 m) assumptions are shared constants used
by both the generator and the critic (`constants/evaluations.py`); their values
are those of ADR 0019.

## Consequences

- False floor-to-floor findings on split-level stairs disappear. A stacked
  storey whose declared height disagrees with its stair is still reported.
- A split-level flight that passes through a boundary wall is now reported. On
  the S9 demonstration concepts, generated straight flights now measure 2.75 m
  headroom with no wall clash.
- Stairwells add floor area (they are spaces) and, on a slope, excavation and
  retaining walls; both are reported, not assumed away. On the S9 split-level
  concept excavation rises from 0.54 to 3.23 m³ and 8.2 m of retaining wall
  appears.
- The stair hall is a narrow tower over the lower bar's roof. Its form, light
  and structure are a design matter left to the owner and professionals.
- U-shaped flights have walking lines too (S10-06). `Stair.landing_segments`
  marks level landing segments; the rise is shared among the other segments by
  length, so headroom, wall clashes, run fit (`(risers − flights) × going`),
  routes and section risers follow flights and stay level on the landing. The
  generator lays a U flight out as two lanes kept 0.2 m from the walls, both
  flights meeting the corridor-side line where the upper landing stays in the
  floor, turning on a half landing at least a flight's width deep; otherwise
  the model carries a blocking issue. Only a stair without a walking line stays
  `not_checked`.
