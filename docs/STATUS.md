# Status

- **Phase:** 1, site: done; brief complete. Next: phase 2, envelope.
- **Revision:** none yet
- **Last session (2026-10-13, Claude Code, laptop 1):**
  - Survey converted and measured (`docs/site.md`, `scripts/measure_site.py`).
  - Plot D7: a 32.570 × 21.000 m parallelogram, 600.004 m², corners
    61°/119°. Road 9.000 m on the west. The plot falls 37–38 % to the east.
  - Owner's brief entered: road, alley strip, parking, lift.
  - Datum and origin decided (`docs/decisions.md`).
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
  4. **Brief items the kit could not model.** Kit done 2026-10-13:
     `balconies` (outline outside the walls), `lifts` (stacked shaft rooms of
     use `lift`, car size, rule evaluators `lift_car_min`, `lift_shaft_min`,
     `lift_entrance_min_width`), `program.vehicles` with the rule
     `garage_fits_vehicles`. **Pending:** cited car and lift sizes into
     `docs/research.md` and `rules/iran.yaml`.
  5. **Phase 3:** the first sketch options (`design/option-a.yaml`, ...).
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
