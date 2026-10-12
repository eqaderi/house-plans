# Status

- **Phase:** 1, site (measured; awaiting the owner's confirmation)
- **Revision:** none yet
- **Last session (2026-10-13, Claude Code, laptop 1):**
  - Survey DWGs converted to `derived/survey/`, and measured with
    `scripts/measure_site.py`; results in `docs/site.md`.
  - Plot D7: a 32.570 × 21.000 m parallelogram, 600.004 m², corners
    61°/119°. Road 9.000 m on the west. The plot falls 37–38 % to the east.
  - `hp survey` now finds outlines closed by repeating their end points.
  - Owner's brief entered.
- **Next:** the owner records the checksums, then answers
  `docs/open-questions.md` #14–29. Then phase 2 (envelope over the survey).
- **Owner action:** agent writes under `sources/` are blocked, so the
  manifest is empty. Run:
  `shasum -a 256 sources/height-points.dwg sources/seperated.dwg >> sources/MANIFEST.sha256 && shasum -a 256 -c sources/MANIFEST.sha256`
- **Blocking:** see docs/open-questions.md
