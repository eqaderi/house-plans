# Status

- **Phase:** 2, envelope: done (plot, alley strip, terrain, kit). Next: phase 3, sketch options.
- **Revision:** none yet
- **Last session (2026-10-13, Claude Code, laptop 1, second session):**
  kit for phase 2–3: spec frame turned to the plot, `site:` block and site
  sheet, boundary and alley-strip checks, `bin/hp ground` (linear TIN),
  balconies, lifts, cars in the garage, cited lift and parking rules.
  92 tests pass; gate exits 0. No option drawn yet.
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
