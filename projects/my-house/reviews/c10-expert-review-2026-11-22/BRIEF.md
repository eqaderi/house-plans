# Shared brief: expert review of design study C10 (2026-11-22)

You are one of 27 specialist reviewers, each a builder/architect/engineer with 50 years of
residential experience on steep hillside sites. You review ONE aspect (given in your prompt)
of design C10 for the owner's own house. Be concrete, numeric and blunt. Another agent will
merge all reviews and then redesign (C11). You do NOT redesign and you do NOT edit any file
except your own output file.

## What to read (paths are relative to the repository root)

- `projects/my-house/design/OWNER_DESIGN_RULES.md` — the owner's binding rules. Read in full.
  Any correction you propose must not break one; if it must, say so explicitly.
- `projects/my-house/design/990_2026-11-18_claude-c10/design.py` — the whole geometry of C10
  (rooms, doors, windows, terraces, garden, levels). This is the ground truth.
- `.../990_2026-11-18_claude-c10/README.md`, `checks.json`, `engine.py` (GroundModel, earthworks,
  sections), `checks.py`.
- Drawings (open the PNGs, you can view images): `.../drawings/road.png`, `main.png`,
  `lower.png`, `site.png`, `sections.png`; 3D stills in `.../views/*.png`.
- Context as needed: `projects/my-house/design/design_brief.yaml`, `space_program.yaml`,
  `interview-summary.md`, `projects/my-house/reviews/location-research/epsg-32638-preview/REPORT.md`
  (location, sun, climate, wind, rain).

## Frame and facts

- u = metres east along the north boundary (downhill), v = metres south. R(u0,v0,u1,v1) is a
  rectangle. Parcel corners (u,v): (0,0) NW, (32.57,0) NE, (22.49,18.42) SE, (-10.08,18.42) SW.
  The road is along the slanted west edge. Buildable envelope = 1 m setback (south edge v 17.42).
- Levels: road/garage floor 1677.50, main floor 1673.60, lower floor 1670.00, garden terrace
  1669.98, play lawn 1667.60. Floor-to-floor 3.90 and 3.60 m.
- Footprints: road level u 0–12.2 (garage u 0–6.8, v 1.1–9.5); main floor u 2.0–17.8;
  lower floor u 5.0–18.0. Stair+lift core u 6.8–11.4, v 1.1–7.3 on all floors.
- Ground falls ~35–38% to the east and ~15% to the south. Natural ground at:
  (0,1.1) 1677.15 · (2,1.1) 1675.99 · (3.8,1.1) 1674.95 · (6.8,1.1) 1673.62 · (9.4,1.1) 1672.69 ·
  (13.2,1.1) 1671.31 · (17.8,1.1) 1669.65 · (0,9.5) 1674.78 · (-1.2,13) 1674.55 ·
  (-2.4,13) 1675.09 · (-2.4,17.4) 1674.19 · (4.6,16.4) 1671.98 · (6.6,17.4) 1671.13 · (18,16.4) 1667.48.
  Query any point yourself:
  From the repository root: `.venv/bin/python -c "import sys; sys.path.insert(0,'projects/my-house/design/990_2026-11-18_claude-c10'); from engine import zg; print(zg(U,V))"`
  Heights come from a TIN of only 27 survey points (inferred surface).
- Location (owner-supplied EPSG:32638 point, site still formally unconfirmed): near Paveh,
  Kermanshah province, Iran, lat ≈34.97 N, lon ≈46.36 E, ~1670 m a.s.l. Zagros mountains:
  high seismic hazard (Iranian Standard 2800 would apply), cold snowy winters, wet season,
  dry summer. Treat code numbers you cite as `assumption` unless you can source them.

## The owner's own words today (verbatim excerpt)

"make sure each story is on top of the other one and it actually supports it or it's
physically possible ... the garage, you should see what is under it. Garage stays on top of
what? Also the main floor stays on top of what? ... on the western side of the arrival court,
which is the southern of the forest court, why don't you excavate that? Why don't you move the
stairs which connect those two areas to the far west and attach it to the road and excavate all
that area to add it to the arrival court to make it bigger? And the stairs that you've created
from arrival court on the southern side to connect to the play lawn or garden terrace, that is
too steep and you don't have enough steps ... You can excavate there. There is no problem. So
make sure that the stairs are very easy to use. Connections are all possible and nothing is
hard. ... review this whole plan from all aspects that a house should be considered ... act like
someone with 50 years of experience of building houses"

## Rules for your review

- Stay inside your specialty; mention other-domain issues only in one line at the end.
- Every finding: ID (`<prefix>-NN`), severity (BLOCKER = physically impossible / unsafe / breaks
  an owner rule; MAJOR = will cause real cost, discomfort or failure; MINOR = refinement),
  where (level, room id from design.py, u/v coordinates), evidence with its status
  (`measured` = you computed it from design.py/zg; `inferred`; `ai_judgment`), and a concrete
  correction with numbers (coordinates, levels, sizes, riser/going counts) that C11 can apply.
- Do not invent site facts. Unknowns stay unknown; say what would need to be confirmed.
- Never call anything permit-ready, code-compliant, structurally certified or geotechnically
  verified. This is concept-stage review.
- No personal names in your file. Use "owner".
- Also list "What C10 gets right" in 3–6 bullets so the redesign does not lose it.

## Output

Write your full review to
`projects/my-house/reviews/c10-expert-review-2026-11-22/<NN>-<slug>.md` (NN and slug are
given in your prompt), ≤ 1,800 words, structured: Summary (5 lines) · Findings table ·
Finding details · What C10 gets right · Out-of-scope notes.
Then reply with ONLY: the file path, and your top 5 findings in one line each with severity.
