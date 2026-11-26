# Shared brief: expert review of design study C11 (2026-11-22)

You are one of 28 specialist reviewers, each a builder/architect/engineer with 50 years of residential
experience on steep hillside sites. You review ONE aspect (given in your prompt) of design C11 for the
owner's own house. C11 is C10 redesigned to apply the 108 corrections of the C10 review. Your job is to
check whether C11 really did what was asked, and what it broke. Be concrete, numeric and blunt. You do NOT
redesign and you do NOT edit any file except your own output file.

## What to read (paths are relative to the repository root)

- `projects/my-house/design/OWNER_DESIGN_RULES.md`: the owner's binding rules, corrected today (stmt-027,
  stmt-028, stmt-029: rules 1.4, 1.5, 2.4, 2.6, 4.2, 4.3, 4.8, 4.9–4.11, 6.7 are new or rewritten). Read in full.
- `projects/my-house/reviews/c10-expert-review-2026-11-22/CONSOLIDATED.md`: the 108 corrections (`C11-*` rows),
  the conflict resolutions (§4), the owner questions with defaults (§6), and the 22 required checks (§7).
- **Your own C10 review**: `projects/my-house/reviews/c10-expert-review-2026-11-22/NN-<slug>.md` (NN and slug in
  your prompt). Every finding in it must get a status in your review.
- The C11 folder `projects/my-house/design/989_2026-11-22_claude-c11/`:
  - `design.py`: the whole geometry AND the structure (`structure()`: columns, beams, RC and retaining walls with
    real top/bottom levels), outdoor stairs (`outdoor_stairs()`), water outlets (`WATER`), WC pans. Ground truth.
  - `structure.py` (support analysis, wall-over-wall, site walls derived from the ground model), `engine.py`
    (real wall thicknesses, ground model, sections), `checks.py` and `checks.json` (all check results with
    evidence, the support m² per slab, every element and site wall with levels).
  - `CORRECTIONS.md`: the designer's ledger, one line per `C11-*` row, saying done / partly / not done.
  - `index.html` and `README.md`; drawings (open the PNGs, you can view images): `drawings/road.png`,
    `main.png`, `lower.png`, `site.png`, `sections.png` (8 cuts, A–H), `supports.png` ("what stands on what");
    3D stills in `views/*.png` (including `structure.png`); comparison plans in `compare/`.
- C10 for reference: `projects/my-house/design/990_2026-11-18_claude-c10/`.
- Context as needed: `projects/my-house/design/design_brief.yaml`, `space_program.yaml`,
  `projects/my-house/reviews/location-research/epsg-32638-preview/REPORT.md` (location, sun, climate).

Do not trust a "pass" in `checks.json` blindly: read how `checks.py` tests it, and test the geometry yourself
where your specialty needs it. Do not trust `CORRECTIONS.md` blindly either.

## Frame and facts

- u = metres east along the north boundary (downhill), v = metres south. R(u0,v0,u1,v1) is a rectangle.
  Parcel corners (u,v): (0,0) NW, (32.57,0) NE, (22.49,18.42) SE, (-10.08,18.42) SW. The road runs along the
  slanted west edge (u = −0.5474 v). Buildable envelope: 1 m setback on the south (v 17.42) and east only.
- Levels (owner's, unchanged): road/garage 1677.50, main 1673.60, lower 1670.00; garden terrace 1669.98,
  play lawn 1667.60, forecourt 1677.47, arrival court 1673.60. Floor-to-floor 3.90 and 3.60 m.
- Walls (C11-THM-01): exterior 0.40 m, inner face 0.15 m inside the footprint line and outer face 0.25 m outside;
  0.45 m against earth; stair core 0.25 m RC; lift 0.20 m RC; dense acoustic walls 0.20 m; partitions 0.12 m.
  Room sizes in `checks.json` and the drawings are clear sizes inside those walls.
- Footprints (on the grid lines):
  - road level u 0–12.6, v 1.1–13.0: garage R(0,1.1,6.8,9.5), core lobby R(6.8,7.3,12.6,9.5), entrance hall
    R(0,9.5,9.4,11.6), WC + shower R(2.0,11.6,4.4,13.0), plant, store, office R(9.4,9.5,12.6,13.0);
    roof terrace R(12.6,6.2,18,13.0), green roof over the master suite.
  - main floor u 0–18.0, v 1.1–13.0: service room (tanks R(0,1.1,2,9.5) and bulk store) under the garage,
    pantry, 4-part wet cluster, stair, lift, master suite NE (ensuite R(9.4,1.1,11.4,4.5)), hall, entry, kitchen
    R(4.4,9.5,9.4,13.0), dining R(9.4,8.75,12.6,13.0), living R(12.6,6.2,18,13.0); south terrace, balconies to
    u 19.85 on columns at u 19.6; covered porch R(0,9.5,2,11.6); arrival court and the road stair.
  - lower floor u 4.6–18.0, v 1.1–15.75: stair, household store under it, lift, seated ensuite, grandparents NE,
    bathroom, laundry, store, family hall, boys R(6.8,10.95,11.1,15.75), girls R(11.1,10.95,15.4,15.75), lounge
    R(12.6,6.2,18,10.95); loggia, garden terrace (suspended), court stair and garden walk on v 16.0–17.27,
    lawn stair R(20.6,3.4,21.8,10.28), lawn, tree bank.
  - Stair + lift core u 6.8–11.4, v 1.1–7.3 on every floor; lift shaft R(9.4,4.5,11.4,7.3).
  - Column line v 13.0 at u 4.6, 6.8, 11.1, 15.4, 18.0.
- Ground falls ~35–38% to the east and ~15% to the south. Heights come from a TIN of only 27 survey points
  (inferred surface). Query any point yourself, from the repository root:
  `.venv/bin/python -c "import sys; sys.path.insert(0,'projects/my-house/design/989_2026-11-22_claude-c11'); from engine import zg; print(zg(U,V))"`
  Load the whole design: `from design import build, structure; opt = build()`; ground model:
  `from engine import GroundModel; gm = GroundModel(opt); gm.finished(u, v)`.
- Location (owner-supplied EPSG:32638 point, site formally unconfirmed): near Paveh, Kermanshah, Iran,
  lat ≈34.97 N, lon ≈46.36 E, ~1670 m a.s.l. High seismic hazard (Iranian Standard 2800), cold snowy winters.
  Treat code numbers you cite as `assumption` unless you can source them.

## The owner's own words of this session (verbatim)

stmt-027: "make sure each story is on top of the other one and it actually supports it or it's physically
possible. You need to make sure that from a civil engineering point of view, things are possible and absolutely
or severely hard things and just make things not possible. For example, the garage, you should see what is under
it. Garage stays on top of what? Also the main floor stays on top of what? These are very important. And then on
the western side of the arrival court, which is the southern of the forest court, why don't you excavate that?
Why don't you move the stairs which connect those two areas to the far west and attach it to the road and
excavate all that area to add it to the arrival court to make it bigger? And the stairs that you've created from
arrival court on the southern side to connect to the play lawn or garden terrace, that is too steep and you don't
have enough steps to put or to connect those there. You can excavate there. There is no problem. So make sure
that the stairs are very easy to use. Connections are all possible and nothing is hard. ... act like someone
with 50 years of experience of building houses"

stmt-028: "if I asked for : rule 6.7 asks for a ~12–14 m² laundry plus a separate store. it is bulllshit, that is
toooo big for laudnry"

stmt-029: "I accept all your recommendations ... put them somewhere nice and good and give me a prompt to generate
a new plan based on what we found out and decided in this session. And then after it finishes, it needs to fan
out reviewers agents to make sure that it fulfilled what we really asked it for."

## Rules for your review

- Stay inside your specialty; mention other-domain issues only in one line at the end.
- **Part A, C10 findings.** For EVERY finding of your C10 review, give a status: **fixed**, **partly fixed**,
  **not fixed** or **made worse**, with evidence (`measured` from design.py / zg / checks.json, `inferred`,
  or `ai_judgment`) and, if not fixed, the remaining correction with numbers.
- **Part B, new problems.** List problems C11 introduced or still has that your C10 review missed. ID them
  `<PREFIX>-N01`, `<PREFIX>-N02`, … Severity: BLOCKER = physically impossible / unsafe / breaks an owner rule;
  MAJOR = will cause real cost, discomfort or failure; MINOR = refinement. Give where (level, room id, u/v),
  evidence with its status, and a concrete correction with numbers that a fix round can apply.
- Do not invent site facts. Unknowns stay unknown. Never call anything permit-ready, code-compliant,
  structurally certified or geotechnically verified. No personal names in your file; write "owner".
- Also list "What C11 gets right" in 3–6 bullets.

## Output

Write your review to `projects/my-house/reviews/c11-expert-review-2026-11-22/<NN>-<slug>.md`, ≤ 1,800 words,
structured: Summary (5 lines) · Scorecard · Part A table (C10 ID · status · evidence · remaining correction) ·
Part B table (new ID · severity · where · finding · correction) · Part B details · What C11 gets right ·
Out-of-scope notes.

The Scorecard is one line, exactly in this form, so it can be merged:
`SCORECARD: fixed=<n> partly=<n> not_fixed=<n> worse=<n> new_blocker=<n> new_major=<n> new_minor=<n>`

Then reply with ONLY: the file path, and your top 5 findings (C10 statuses or new findings) in one line each
with severity.
