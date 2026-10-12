# Status

- **Phase:** 1, site: done. Next: phase 2, envelope.
- **Revision:** none yet
- **Last session (2026-10-13, Claude Code, laptop 1):**
  - Survey converted and measured (`docs/site.md`, `scripts/measure_site.py`).
  - Plot D7: a 32.570 × 21.000 m parallelogram, 600.004 m², corners
    61°/119°. Road 9.000 m on the west. The plot falls 37–38 % to the east.
  - Owner's brief entered: road, alley strip, parking, lift.
  - Datum and origin decided (`docs/decisions.md`).
- **Next:** phase 2. Draw the envelope over the survey: the plot minus the
  1 m south strip, with walls allowed on the road line. Then phase 3, the
  sketch options.
- **Brief:** complete enough to sketch. Only #25 (water tank, solar) is
  left, and it matters only at the final stage.
- **Kit gaps, before the first sketch:**
  1. Model toilet fixtures with an axis, and add a QIBLA check (test first)
     comparing each toilet axis with the qibla, grid 203.97°. The owner
     requires it.
  2. Persian labels (the owner prefers Persian; English until then).
- **Owner action:** the checksum manifest is still empty (agent writes
  under `sources/` are blocked). Run:
  `shasum -a 256 sources/height-points.dwg sources/seperated.dwg >> sources/MANIFEST.sha256 && shasum -a 256 -c sources/MANIFEST.sha256`
- **Blocking:** see docs/open-questions.md
