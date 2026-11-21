# Claude C10: one design, fitted to both falls of the field

The owner asked for one best design, presented clearly, with a 3D view of the field and of the house on it, taking both falls into account: west → east and north → south (stmt-026). This is an exploratory concept; nothing is stored in `ProjectStore`. Open `index.html`; the 3D model alone is `3d.html`.

C10 keeps the structure of C08/C09 (the owner's 0109-r5 core, room sizes and levels; lower floor ends at u 18) and places rooms by where each floor meets the natural ground.

| | C09-1 | C10 |
|---|---|---|
| Boys' south wall | 0.3–1.8 m under ground, window onto a dug trench | rooms moved 1.8 m east; highest ground at a window +0.47 m (sill 0.9 m) |
| Lower-floor pit | 240 m³, deepest cut 4.38 m | 200 m³, deepest cut 3.97 m (NW bathroom and riser room not dug) |
| Master suite | bedroom 19 m², dressing 2.8 m², ensuite 4.1 m² | NE corner, 23 m² + 6.4 m² + 7.1 m², own balcony |
| Main-floor terraces | 64 m² | 69 m², east balcony wraps into the south terrace |
| Garden | two lawns (71 + 38 m²) on up to 2.6 m of fill | one level lawn of 74 m² along the contour, natural tree bank below |
| Doors blocked by furniture | 22 | 0 (new check) |

Open owner decisions are listed at the end of `index.html`.

## Files

| File | What it is |
|---|---|
| `design.py` | the geometry: rooms, doors, windows, furniture, terraces, garden |
| `engine.py` | plans, the finished-ground model (`GroundModel`), earthwork, four-panel sections; copied from `../991_2026-10-27_claude-c09` and extended |
| `checks.py` | rule checks; new here: door swings clear of furniture, openings clear of the ground, daylight per room |
| `sitemap.py` | site plan coloured by height, with the floors, the daylight lines and the section lines |
| `model3d.py`, `viewer_template.html` | the 3D model and its WebGL viewer (no dependencies, works offline) → `3d.html` |
| `shots.py` | still pictures of the 3D model in `views/`, taken with headless Chrome (skipped if Chrome is missing) |
| `report.py` | `index.html` |
| `drawings/`, `views/`, `checks.json` | generated output |

Rebuild from the repository root: `.venv/bin/python projects/my-house/design/990_2026-11-18_claude-c10/build.py` (`--plans-only` skips the 3D model and the page).

Heights come from the stored survey TIN (inferred surface, 27 surveyed points). The site is still `SITE_NEEDS_CONFIRMATION`. Nothing here is engineered, permit-ready or code-checked.
