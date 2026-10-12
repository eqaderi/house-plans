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
  2. **Phase 2 kit extension** (test first):
     - a `site` block in the spec: the boundary polygon in mm and no-build
       strips;
     - a check that the footprint stays inside the boundary minus the strips;
     - the boundary, road edge, strip and spot heights drawn on the sheet,
       which also gives the missing site sheet.
  3. **Terrain:**
     - a linear TIN from `height-points.dxf` only, no smoothing, labelled
       "interpolated" with its method and source points;
     - a tool that reports ground Z at any footprint point.

     This decides which floor meets the road and which meets the garden
     (12.5 m of fall).
  4. **Brief items the kit cannot model yet** (see `references/spec.md`, "Not
     modelled yet"):
     - balconies outside the enclosure;
     - a lift: car and shaft size from a cited source, or the rule marked
       `unverified`;
     - covered parking: Land Cruiser 300 and Peugeot 301 dimensions from the
       manufacturer pages, with links, into `docs/research.md`.
  5. **Phase 3:** the first sketch options (`design/option-a.yaml`, ...).
  6. **Later:** Persian labels.
- **Note:** `references/slope.md` §5 (sun angles) is written for 35.7° N;
  this site is at 34.97° N. It is guidance only and no check consumes it.
  Neither `rules/iran.yaml` nor any check uses a Tehran-specific value.
- **Brief:** complete enough to sketch. Only #25 (water tank, solar) is
  left, and it matters only at the final stage.
- **Blocking:** see docs/open-questions.md
