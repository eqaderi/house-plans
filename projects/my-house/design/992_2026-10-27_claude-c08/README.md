# Claude C08: three plan options reworked from the owner's 0109-r5 designs

Exploratory concept sketches (stmt-022). Nothing is stored in `ProjectStore`. The site is still
`SITE_NEEDS_VERIFICATION`. Open `index.html`.

| Option | From | Idea |
|---|---|---|
| C08-1 | owner's B | Family-hall house: kitchen, dining and living along the south, master suite in the NE |
| C08-2 | owner's A | Reading-bay house: L-shaped living with a closed NE prayer/reading bay, master suite in the middle of the north side |
| C08-3 | owner's C | Kitchen-at-the-heart house: dining by the entry, kitchen with walk-in pantry, master suite with a private NE terrace |

Rebuild: `../../../../.venv/bin/python build.py` (writes `c08-*/{road,main,lower,sections}.{svg,png}`, `checks.json`, `index.html`).
Files: `engine.py` (frame, drawing, sections, earthwork), `options.py` (geometry), `checks.py` (rule checks), `report.py` (index).
