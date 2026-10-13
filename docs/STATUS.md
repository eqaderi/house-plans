# Status

- **Phase:** 3, sketch options. Option A superseded by the owner's three-level section; option B drawn.
- **Revision:** none yet
- **Last session (2026-10-13, Claude Code, laptop 1, third session):**
  owner moved the garage to its own level at the road with the two house
  floors below, the house to the north-west of the plot, and asked for
  daylit safe stairs, open plans, no WC beside the prayer room and
  cheap everyday-use tests (all in `docs/brief.md`). Kit: `hp ground`
  against each level's floor; WINDOW/DOOR_BELOW_GROUND; routes, sight
  lines and living-over-bedroom checks (`usability.py`); two-flight
  stairs (L/U/straight with landing); cited stair rules; WALL_OVERLAP no
  longer counts junction squares. Research: `docs/research-usability.md`,
  `docs/research-stairs.md`. 116 tests pass.
- **Next (in order):**
  1. ~~**Spec frame.**~~ Done 2026-10-13: origin V3, x along the south
     boundary, `north_angle_deg: 337.97` (`scripts/site_frame.py`,
     `houseplan.site`, decisions entry "spec frame turned to the plot").
  2. ~~**Phase 2 kit extension.**~~ Done 2026-10-13: `site:` block
     (`derived/site/d7.yaml`, written by `scripts/site_frame.py --write`),
     checks SITE_OUTSIDE_BOUNDARY / SITE_IN_NO_BUILD, site sheet
     (`sketch-site.png`), boundary and strip on plan sheets. Options use
     `site: ../derived/site/d7.yaml`.
  3. ~~**Terrain.**~~ Done 2026-10-13: `bin/hp ground` (linear TIN,
     `houseplan.terrain`); benchmark kept out; weak spots in
     `docs/decisions.md`. Use it in phase 3 to choose which floor meets the
     road and which the garden.
  4. ~~**Brief items the kit could not model.**~~ Done 2026-10-13:
     balconies, lifts, `program.vehicles` with GARAGE_TOO_SMALL /
     GARAGE_ENTRANCE, and rules IR15-LIFT-CAR, IR15-LIFT-ENTRANCE,
     IR4-PARK-STALL, IR4-PARK-HEIGHT (transcribed), plus IR15-LIFT-SHAFT
     (unverified, suggested size). Sizes and sources are in
     `docs/research.md`; open questions 31 (which LC300) and 32 (which lift).
  5. **Phase 3: the first sketch options** (`design/option-a.yaml`, ...).
     - **Option B** (2026-10-13): three levels, G ±0.00 garage at the road,
       UF −3.20 living floor entered at grade from the SW, LF −6.40 bedrooms
       further east; stacked U stair (19 × 168.4 / 300, 10 + 9) with the
       lift; house against the north boundary. `bin/hp check`: 0 errors,
       12 warnings. Open: living over the parents' room (decisions.md), LF
       east floor 1.2–2.1 m above ground (terrace), the irregular G plan
       (IR2800 unverified), dining reached only through the kitchen (a
       main idea for option C: swap them), LF garden access only via the
       parents' room, landing windows need guards, garage walls over
       non-bearing UF partitions. North windows: the TIN says "unknown"
       at the wall; measured just inside it (`--at x,18300`), FL1 moved
       to clear the ground by 0.16 m on the weak 32.5 m triangle.
       Report page (private): https://claude.ai/artifact/KUYzje7XXC16TEyap3hhqC
       Next: the owner's reaction; then option C if he wants one.
     - **Option C** (2026-10-13, WIP, owner rejected the layout): reworked
       from the owner's reaction to B (`docs/brief.md`, "Reaction to option
       B"): house 3.0 m off the north boundary, stair and lift on the north,
       LF stepping out east and south, no hashti, wudhu room (new `wudhu`
       use, tested), no walk-in closet. `bin/hp check`: 0 errors,
       11 warnings; kitchen still 43 % in view
       from the living room; LF gross 133 m² is smaller than UF 148 m².
       Kept: the brief notes, the `wudhu` use, the ground table (ground
       falls about 0.35 m/m east, 0.16 m/m south). Layout itself to be redone
       with the owner.
     - **Option A** (2026-10-13, superseded by the owner): 13.0 × 12.0 m box by the road, garage NW,
       living/kitchen/dining on the road floor with a U balcony, bedrooms
       below. `bin/hp check`: 0 errors, 6 warnings. LF east half stands over
       an undercroft (ground −6.1 to −8.0 under a −3.2 floor).
     Inputs ready:
     - `site: ../derived/site/d7.yaml` and `project.north_angle_deg: 337.97`;
       the alley strip is y 0..1000, the west boundary is slanted (the
       wedge is accepted).
     - Run `bin/hp ground` first to decide which floor meets the road (west,
       about Z 1677.6) and which the garden (east, about Z 1665.3), then set
       `datum.survey_z_mm` and the level FFLs. Record the choice in
       `docs/decisions.md`.
     - `program.vehicles`: LC300 5145 × 1990 × 1945 (envelope, open question 31),
       Peugeot 301 4445 × 1748 × 1477 (`docs/research.md`).
     - Lift: car 1100 × 1400, shaft room at least 1600 × 1900 clear (open question 32).
     - Program per `docs/brief.md`: 3 bedrooms, kitchen with two open ends
       and a wall to living and a door to the balcony, a WC on the living
       floor, a prayer room with wudhu nearby, laundry, storage, boiler
       room, a roofed garage, a big balcony on as many sides as possible
       of the upper floor if living and kitchen are there, the lower floor
       on the garden, a door from the alley.
  6. **Later:** Persian labels.
- **Note:** `bin/hp ground` answers "unknown" at the four plot corners and
  in thin strips along the boundary: the survey's corner shots lie a few cm
  inside it, and the TIN never extrapolates. That is by design
  (`docs/decisions.md`, "terrain model").
- **Note:** `references/slope.md` §5 (sun angles) is written for 35.7° N;
  this site is at 34.97° N. It is guidance only and no check consumes it.
  Neither `rules/iran.yaml` nor any check uses a Tehran-specific value.
- **Brief:** complete enough to sketch. Only #25 (water tank, solar) is
  left, and it matters only at the final stage.
- **Blocking:** see docs/open-questions.md
