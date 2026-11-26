# Claude C11: C10 corrected, every floor stands on something

The owner asked for "a new plan with all the corrections" after the 27-reviewer review of C10 (stmt-027, stmt-028, stmt-029; [`CONSOLIDATED.md`](../../reviews/c10-expert-review-2026-11-22/CONSOLIDATED.md)). C11 is one corrected design, not options. It is an exploratory concept: nothing is stored in `ProjectStore`, the site is still `SITE_NEEDS_CONFIRMATION`, and nothing is engineered, permit-ready or code-checked.

Open `index.html`. The 3D model alone is `3d.html`. Every review row is accounted for in [`CORRECTIONS.md`](CORRECTIONS.md); what the drawings cannot show is written out in [`SPECIFICATION.md`](SPECIFICATION.md).

After it was drawn, C11 was checked by 28 reviewers ([`../../reviews/c11-expert-review-2026-11-22/`](../../reviews/c11-expert-review-2026-11-22/)) and corrected in one fix round (end of `CORRECTIONS.md`). The drawings and checks here are the state after that round.

| File | What it is |
|---|---|
| `design.py` | the geometry and the structure: rooms, doors, windows, furniture, terraces, outdoor stairs, columns, beams, RC and retaining walls, water outlets |
| `structure.py` | what every slab stands on (support and wall-over-wall analysis), site walls derived once from the ground model, the "what stands on what" sheet |
| `engine.py` | plans with real wall thicknesses, the ground model (0.60 m formation, suspended slabs), sections drawn only from the structure lists; copied from C10 and extended |
| `checks.py`, `checks.json` | the owner's rules and the 22 checks of CONSOLIDATED §7, with evidence |
| `compare.py`, `c10_dump.py` | the C10 ↔ C11 comparison (rule 8.5); C10 is read with its own code in a separate process |
| `model3d.py`, `viewer_template.html`, `shots.py` | the 3D model (same structure lists) and its still pictures |
| `sitemap.py`, `report.py`, `report_text.py` | site plan and `index.html` |
| `drawings/`, `views/`, `compare/` | generated output |

Rebuild from the repository root: `.venv/bin/python projects/my-house/design/989_2026-11-22_claude-c11/build.py` (`--plans-only` skips the site plan, the 3D stills and the page).
