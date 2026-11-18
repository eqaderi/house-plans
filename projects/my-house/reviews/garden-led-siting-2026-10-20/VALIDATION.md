# Validation record — 20 October 2026

This validates the software/data consistency of the advisory study, not planning permission, slope stability, structural adequacy, cost or the final building/garden fit.

- Full repository suite: **870 passed in 433.44 seconds** (`.venv/bin/python -m pytest -q`).
- Ruff: passed (`.venv/bin/ruff check src tests examples`).
- Schema check: **29 schemas up to date** (`.venv/bin/house-ai schemas check`).
- Tracker check: passed (`.venv/bin/python tools/check_tracker.py`).
- Project integrity after recording the priorities and advisory source: **76 events, 73 artifact versions intact**.
- Canonical site remains **v3**; workflow remains **SITE_NEEDS_VERIFICATION**.
- Terrain-screening windows are fully covered by the survey TIN and contained in the current setback envelope. At the area-weighted mean-ground plane, computed geometric cut and space-below-plane agree within 1e-7 m³.
- No room geometry or construction pads were written into the canonical house model. Storey count, budget and total area were not changed into owner preferences.

The owner's English source answer is preserved by the interview interface. Updated English priority interpretations are in **interview v23 / design brief v23**, marked inference. The English advisory note was registered as immutable source **src-recommendation**, SHA-256 `a97bb528018e5107ffaf5c30402e5b934660af42984a009636d878489120cc8b`.
