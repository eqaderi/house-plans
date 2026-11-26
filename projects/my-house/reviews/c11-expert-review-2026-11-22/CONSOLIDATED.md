# C11 expert review: consolidated corrections for the C11 fix round (2026-11-22)

Merged from the 28 specialist reviews in this folder ([index](#9-index-of-the-28-reviews)). Concept stage only: nothing here is engineered, permit-ready, code-compliant, structurally certified or geotechnically verified. Heights come from the 27-point TIN (an inferred surface); code and product figures are `assumption`. Statuses as the reviewers used them: `measured` (from `design.py`, `zg`, `GroundModel`, `checks.json`), `inferred`, `ai_judgment`.

**Binding order when reviewers disagree:** `OWNER_DESIGN_RULES.md` (stmt-027/028/029) → safety and physics → cost.

**What was reviewed.** C11 as built at 06:09–06:12 today. Since then, `SPECIFICATION.md` was written (10:03, after 26 of the 28 reviews), and a fix round has started in `design.py`, `checks.py` and `CORRECTIONS.md` (10:16–10:20). This document does not verify that round.
- The "exists only as a note" findings were true when written. `SPECIFICATION.md` now answers the text part of them.
- Geometry items still have to be drawn as elements.

Consolidator's spot-checks agree with the reviewers (`measured`):
- `walk-s` R(9.74, 16.0, 15.4, 17.12) and `loggia` R(15.4, 10.95, 18.0, 16.0) share only a point.
- The road edge is at 1677.51 (v 11.6) and 1677.57 (v 17.12).
- On the pile line, ground is at 1673.66 (u 6.8) and 1671.34 (u 13.2), under a pile top drawn at 1677.0.

## 1. Scorecard

### 1a. Per reviewer (from each `SCORECARD:` line)

"C10" is the number of that reviewer's own C10 findings. For 28, the status columns are its audit of the 108 ledger rows.

| NN | Specialty | C10 | Fixed | Partly | Not | Worse | New B | New M | New m |
|---|---|---|---|---|---|---|---|---|---|
| 01 | Structure: vertical load path | 12 | 7 | 5 | 0 | 0 | 1 | 7 | 3 |
| 02 | Seismic, lateral | 11 | 3 | 6 | 2 | 0 | 0 | 6 | 2 |
| 03 | Geotechnics, earthworks | 11 | 3 | 8 | 0 | 0 | 1 | 4 | 2 |
| 04 | Water, waterproofing | 14 | 2 | 10 | 2 | 0 | 1 | 4 | 3 |
| 05 | Site access, outdoor stairs | 13 | 4 | 8 | 1 | 0 | 2 | 3 | 3 |
| 06 | Circulation, stair, lift | 14 | 8 | 4 | 2 | 0 | 1 | 1 | 6 |
| 07 | Rooms, owner rules | 14 | 8 | 6 | 0 | 0 | 1 | 5 | 6 |
| 08 | Sun, daylight, views | 12 | 2 | 7 | 1 | 2 | 0 | 4 | 3 |
| 09 | Thermal, envelope | 13 | 0 | 11 | 1 | 1 | 0 | 3 | 3 |
| 10 | MEP services | 13 | 2 | 8 | 3 | 0 | 0 | 6 | 4 |
| 11 | Life safety | 16 | 3 | 12 | 1 | 0 | 4 | 3 | 1 |
| 12 | Accessibility | 13 | 5 | 6 | 2 | 0 | 2 | 2 | 1 |
| 13 | Privacy, acoustics, culture | 15 | 6 | 8 | 1 | 0 | 0 | 6 | 2 |
| 14 | Landscape | 13 | 1 | 8 | 3 | 1 | 1 | 4 | 2 |
| 15 | Constructability, cost | 14 | 4 | 9 | 0 | 1 | 1 | 5 | 2 |
| 16 | Consistency, boundaries | 13 | 8 | 5 | 0 | 0 | 2 | 3 | 4 |
| 17 | Exterior architecture | 11 | 2 | 7 | 2 | 0 | 0 | 3 | 4 |
| 18 | Interior space, heights | 13 | 3 | 8 | 2 | 0 | 1 | 4 | 5 |
| 19 | Vehicles, garage, road | 11 | 0 | 9 | 2 | 0 | 2 | 3 | 4 |
| 20 | Kitchen, bathrooms | 16 | 5 | 9 | 2 | 0 | 2 | 3 | 5 |
| 21 | Planning, neighbours | 11 | 1 | 5 | 5 | 0 | 0 | 5 | 4 |
| 22 | Hazards, resilience | 18 | 1 | 13 | 4 | 0 | 1 | 4 | 1 |
| 23 | Indoor health | 12 | 0 | 11 | 0 | 1 | 0 | 5 | 4 |
| 24 | Flexibility, lifecycle | 10 | 1 | 6 | 3 | 0 | 1 | 2 | 2 |
| 25 | Household operations | 13 | 2 | 10 | 1 | 0 | 1 | 5 | 4 |
| 26 | Brief fidelity | 10 | 2 | 5 | 1 | 2 | 0 | 4 | 4 |
| 27 | Materials, durability | 13 | 1 | 9 | 3 | 0 | 1 | 4 | 3 |
| 28 | Owner-request fidelity (new) | 108 rows | 56 | 45 | 1 | 6 | 2 | 3 | 5 |

### 1b. Totals

**Reviewers 01–27, 349 C10 findings:**

| Fixed | Partly | Not fixed | Made worse |
|---|---|---|---|
| **84** (24 %) | **213** (61 %) | **44** (13 %) | **8** (2 %) |

The eight made worse:
- SUN-04, SUN-05: less winter sun for the grandparents and the lounge.
- THM-08: the garage is now the cold ceiling of 56.7 m² of rooms.
- LND-03, BRF-08: the lawn, 74.4 → 56.8 m².
- BRF-10: the plant room, 6.1 → 3.8 m².
- BLD-03: retaining walls, about 130 → 158 m.
- HLT-09: bedroom ventilation.

**Reviewer 28, the 108-row ledger:**

| Verified | Honest "Partly" | Honest "Not done" | Overstated or false |
|---|---|---|---|
| 56 | 45 | 1 (C11-DRW-04) | 6: C11-ARR-02 false; C11-ROOM-06, -STR-03, -STR-05, -STR-07 and -DRW-03 overstated |

The specialists' measurements contradict 8 more rows that 28 counted as verified:

| Row | Reviewers | What they measured |
|---|---|---|
| C11-STR-04 | 17 | a lone 6.6 m post |
| C11-ACS-02 | 12 | no access limits on the page |
| C11-KB-02 | 20 | fit-out not drawn |
| C11-KB-03 | 20 | shower unreachable |
| C11-SAF-02 | 11, 16 | guards missing |
| C11-ARR-04 | 19 | the upstand is text only |
| C11-VEH-02 | 19, 25 | tyre rack in shutter 1 |
| C11-SUN-04 | 08 | the pergola adds 1 % |

So at most **48** ledger rows are verified, and at least **14** are overstated or false.

### 1c. New findings by severity

| | BLOCKER | MAJOR | MINOR | Total |
|---|---|---|---|---|
| Raw, reviewers 01–27 | 26 | 108 | 87 | 221 |
| Raw, all 28 | 28 | 111 | 92 | 231 |
| **De-duplicated (distinct problems)** | **17** | **66** | **35** | **118** |

Every raw finding was assigned to exactly one problem. A problem takes the highest severity any reviewer gave it.

Largest duplicate groups (number of findings):

| Problem | Findings | Reviewers |
|---|---|---|
| North pile wall PW-N overlaps the house wall | 8 | 01, 02, 04, 09, 16, 18, 21, 27 |
| LPG cage in the sunk court | 6 | 10, 11, 17, 20, 22, 25 |
| v 13.0 columns clash with openings and furniture | 6 | 01, 09, 16, 17, 18, 24 |
| Garden walk does not reach the loggia | 5 | 05, 12, 14, 18, 28 |
| No beam over the south glazing at road-slab level | 5 | 01, 02, 16, 27, 28 |
| "Walk-on rooflight" under a roof | 5 | 06, 08, 13, 18, 23 |
| Outdoor paving and stairs on more than 1.0 m of fill | 5 | 03 ×3, 04, 27 |
| Riser SH-E blocks both ensuite doors | 4 | 07, 12, 20, 24 |
| Guard check cannot fail | 4 | 05, 11, 14, 16 |
| PW-N toe and cap | 4 | 01, 03, 15, 21 |
| Undersized plant room | 4 | 10, 15, 23, 24 |
| Lower WC pan in a 0.60 m slot | 4 | 07, 10, 18, 20 |
| Laundry neck | 4 | 06, 07, 20, 25 |
| Crawl voids | 4 | 09, 15, 18, 23 |
| Specification only in the ledger | 4 | 04, 09, 19, 27 |
| Unguarded road edge | 3 | 05, 11, 19 |
| W2/W3 road walls | 3 | 02, 03, 22 |
| Bulk store behind the tanks | 3 | 10, 25, 26 |
| Bedroom doors beside the lift | 3 | 06, 07, 12 |
| Rule 3.1 living view | 3 | 08, 18, 28 |

§4 has **18 BLOCKER rows**: the 17 distinct new BLOCKERs, plus the C10 BLOCKER SEI-03 (lateral system), which is still open.

## 2. Verdict in plain words

C11 answers the garage question and mostly the main-floor question, and it builds the owner's court and easy flights. It does **not** deliver "connections are all possible and nothing is hard". It must not be presented as validated until the 18 BLOCKER rows are closed and the checks that let them pass are repaired (§8).

**"Garage stays on top of what?" Answered.**
- A service room is dug to 1673.60 under all 57 m² of the garage. Its walls run on a grid of ≤3 m (u 0, 2.0, 3.8, 6.8; v 1.1, 2.8, 4.6, 7.3, 9.5). 0 m² stands on nothing (`measured`: 01, 02, 03, 15, 16, 28).
- But in that room the tanks block the bulk store, and they fit through no door. Two walls retaining 3.6 m under the garage are only 0.20 and 0.25 m thick.

**"Main floor stays on top of what?" Mostly.**
- 61 m² stands on dug ground; the rest stands on lower walls, beam LB-13.0 and RC-18L.
- What is wrong:
  - The road storey's south wall and two beam ends stand on the main floor's glazing. There is no beam on v 13.0 at 1677.50.
  - The u 18 and girls' south and east walls carry two storeys over 0.5–1.1 m of void or fill, without foundations.
  - The "0 m² unsupported" result counts glass, and walls that stop 3.6 m below the slab, as bearing (01, 02, 16, 28).

**The bigger court with the stair at the far west: built** (rule 4.10).
- 40.6 m² open plus a 4.2 m² porch, against C10's 34.0 m², of which about 28 m² was open. The 51.6 m² target ignored wall thickness.
- The 12 + 12 L-stair runs against the road.
- But the road edge drops 1.76–2.10 m into that stair with no guard, road water runs down all 24 steps, and the road is held by two thin walls 1.7 m apart (02, 03, 04, 05, 11, 19, 22).

**Easy stairs: yes, every flight.**
- Road stair: 12 × 164 + 12 × 158 mm, 320 mm going.
- Court stair: 3 × 8 × 150 / 340 mm.
- Lawn stair: 2 × 8 × 149 / 320 mm.
- All have landings and handrails on both sides.
- The lawn stair is only ≤1.05 m clear and stands on up to 2 m of fill.

**"Connections are all possible and nothing is hard": no.**
- **Outdoors.** The 24 easy steps end in a 6 m² dead end in front of the children's windows. The walk touches the loggia at one point, then drops 1.7 m, while the owner's page says it reaches the garden (05, 12, 14, 18, 28).
- **Indoors:**
  - a riser stands in both ensuite doorways;
  - the wudu bench blocks the main shower;
  - a column fills the lower WC door;
  - a tyre rack stands in a garage door;
  - the bulk store sits behind the tanks.
- **Hard to build:**
  - The north pile wall would rotate into the pit, overlaps the house wall, and has its cap in the air.
  - The house is a three-sided retaining box, with a sliding factor of about 0.75–1.1 (`inferred`).
  - Cut is up 74 % (228 → 397 m³ modelled, about 500 m³ in place), out of an 8 m hole on a 35 % slope.
- **Safety:**
  - The guard check passes by construction, and about 25 m of 1.7–3.9 m drops are unguarded, including the roof terrace.
  - LPG cylinders sit in a pit beside the front door.
  - The stair has no spine and no void guards.

## 3. What C11 gets right: keep it

- **Support.**
  - A ground-bearing service room under the garage.
  - The lower north wall on v 1.1 (u 9.4–18), bearing and retaining under all floors.
  - Five continuous RC columns on v 13.0, and no column on a slab.
  - Balconies on their own beam and columns.
  - Fill under ground slabs ≤0.90 m. Deepest cut 4.22 m (01, 02, 03, 15, 16).
- **One model.**
  - One element list feeds plans, sections, the support sheet, 3D and checks.
  - The invented posts are gone.
  - `checks.json` reproduces exactly (0 differences in 68 rules) (16).
- **The owner's court**, dug, with the stair against the road (+32 %).
  - The court stair starts on natural ground at 1673.61, its treads 0–0.40 m in cut.
  - The boys' window keeps ground at +0.42 m, against a +0.90 m sill (rule 4.8) (03, 05, 28).
- **Easy flights.** Risers 149–164 mm, 2R+G 0.617–0.648, ≤12 risers per flight, landings at the top and bottom, and each run equal to its drop (05, 11, 16).
- **Core.**
  - 12 risers and 11 goings of 309 mm on all six flights; 1.40 m landings; headroom ≥3.3 m.
  - A stretcher lift, 1.80 × 2.64 m clear, with its door on the same south face on every floor and a clear Ø1.5 m landing.
  - Garage → fire door → lift: 3.6–3.9 m indoors (06, 12, 19, 25).
- **Rooms as stmt-028/029 asked.**
  - Kitchen 15.6 m², with a 2.0 m slider and the sink under the south window; pantry 4.3 m².
  - Dining 3.08 × 4.04 m for 8. Living 5.19 × 6.55 m.
  - Laundry 4.8 m² plus separate stores.
  - WC off the dry lobby, with 0 pan sightlines; a lockable lower bathroom.
  - The ensuites stack (07, 10, 13, 20).
- **Weight off the top.**
  - About 3 t of tanks now on a buried slab; no WC over the kitchen.
  - The hob 0.5 m from SH-K.
  - `t-low` suspended (about 39 m³ of wet fill gone).
  - A tanked 1.2 m lift pit; 0.25 m set-downs checked (04, 10, 22).
- **Sun and qibla.**
  - Day rooms and children's rooms keep 6.6–6.8 h of sun on 21 Dec.
  - ENE main glass is down 44 %.
  - The terrace lip shades the children's glass in June at no winter cost.
  - Qibla 204.64°, with the mats exact (08).
- **Fit.** Everything stays inside the parcel and setbacks. One storey above the road, no head-house. No C01–C09 rejection reason recurs. 45 ledger rows are honestly "Partly" (16, 21, 26, 28).

## 4. De-duplicated corrections for the fix round

- **Sev:** the highest any C11 reviewer gave. A still-open C10 finding keeps its C10 severity where the open part caused it.
- **"· owner":** needs an owner decision (§6). The stated default applies until the owner decides.
- **Sources:** reviewer finding IDs.
- **Rule:** owner rule numbers.

BLOCKERs come first in each theme.

### Structure & stacking (STR)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-STR-01 | BLOCKER | **Beam over the south glazing at road-slab level.**<br>- MB-13.0, about 400 × 650, u 2.0–18.0 at 1676.85–1677.50, on MW-2.0 and C-4.6/6.8/11.1/15.4/18.0.<br>- Size bay 6.8–11.1 for MB-9.4's point load, and bay 11.1–15.4 for MB-12.6's, 1.5 m from C-11.1.<br>- A column, or a ≥0.9 m solid pier, at (12.6, 13.0).<br>- Lintels about 300 × 450 over openings >2 m (girls' window on v 15.75).<br>- Road partitions on the kitchen slab: either ≤1.0 kPa dry-lining, or a beam on v 11.6 (u 2.0–9.4). | STR-N01, SEI-N04, QA-N04, OWN-N03, MAT-N08, STR-06 | 4.9 |
| C11F-STR-02 | BLOCKER | **Lateral system** (C10 SEI-03, not fixed). Main-storey eccentricity is about 4.5 m both ways, against ≤0.1 L (1.2–1.8 m). Integral uphill walls give about 2.2 MN of static thrust plus 1.4 MN in an earthquake; the sliding factor is about 0.75–1.1 (`inferred`).<br><br>**Route A (default):** free-standing drained retaining walls on u 0, u 4.6 and u 6.8, and PW-N and the forecourt deck carry the earth and traffic. Each has a ≥100 mm joint or a 0.6 m gap.<br>**Route B** (only if F1 allows): integral walls plus 0.6 m shear keys on u 15.4 and u 18.<br><br>**Both routes:**<br>- RC panels at u 18, v 1.1–3.3 (both floors), u 18, v 5.0–6.7 and v 13, u 3.9–5.35.<br>- The spine (CIR-01).<br>- Collectors 300 × 500 on v 1.1 and v 7.3.<br>- Drag beams at the notches.<br>- A lateral-system sheet with mass and stiffness centres. | SEI-03/04/05/06/11, SEI-N01, SEI-N08, GEO-N05 | 4.9 |
| C11F-STR-03 | BLOCKER | **Column C-6.8/9.5 fills the lower `lav` → `wc-l` door** (door v 9.05–9.75, column v 9.325–9.675).<br>- Start the column at 1673.60, on LW-6.8 or a new beam LB-6.8 (u 6.8, v 7.3–10.95, 300 × 500).<br>- The kitchen opening above stays ≥0.1 m clear of its faces (u 6.625–6.975). | QA-N01, STR-N09 | 2.1 |
| C11F-STR-04 | MAJOR | **Foundations where ground is below formation** (1669.40). Footings ≥0.8 m below natural ground, steps ≤0.5 m:<br>- u 18: 1668.8 → 1667.5;<br>- v 15.8: 1668.6 → 1667.6;<br>- LW-15.4: 1667.6;<br>- buried walls: 1668.9;<br>- FW-16.0 and FW-13.4: 1666.7 at u 18.<br>Redraw section A–A. | STR-N02, GEO-N04, GEO-06, SEI-10 | 4.9 |
| C11F-STR-05 | MAJOR | **SE corner.**<br>- Column C-18/10.95 (400 × 400), from a footing at about 1667.5.<br>- Lounge slider v 9.0–10.5; loggia slider u 15.8–17.4.<br>- RC-18L extended to v 11.6, so that MW-SE never stands on LB-18. | STR-N03, STR-N04 | 4.9 |
| C11F-STR-06 | MAJOR | **Walls retaining ≥3 m** (LW-7.3 is 0.20 m and the core wall on u 6.8 is 0.25 m; the lower core on v 1.1, u 0, and lower u 4.6):<br>- 0.35–0.40 m RC, ≥0.50 m with waterproofing, base about 1668.9;<br>- propped by both slabs; no backfill before the main slab; cast in bays ≤3 m.<br>- The core's east wall (u 9.4, v 1.1–4.5) becomes RC.<br>- Alternative: dig u 4.6–6.8, v 1.1–7.3 as a store (about 13 m²). | STR-N05, SEI-N05, GEO-04, MAT-01 | 4.9 |
| C11F-STR-07 | MAJOR | **MB-12.6** (6.8 m span, about 520 kNm, `assumption`):<br>- 400 × 750;<br>- or a column C-12.6/9.3, with the lower lounge opening moved to v 6.4–9.0. | STR-N07, STR-11 | 4.9 |
| C11F-STR-08 | MAJOR | **v 13.0 columns.** 0.45 m columns in 0.20–0.40 m walls hit about 10 furniture items and 3 openings, and they bridge cold.<br>- Blade columns about 0.25–0.30 × 0.65–0.80 m along the wall (engineer), with ≥0.10 m of outside insulation;<br>- or keep every frame 0.15 m and all furniture 0.15–0.25 m clear.<br>- Add the columns to `_solids()`. | QA-N05, STR-N09, INT-N06, FLX-N04, THM-N02, EXT-N01 | 4.9, 7.4 |
| C11F-STR-09 | MAJOR | **Balcony columns on u 19.6.** They are 0.30 m wide and clear 3.62 m or 6.62 m on the same beam (captive).<br>- 0.40 × 0.40, sleeved through `t-low`.<br>- C-B/9.4 to v 8.75.<br>- C-B/16.2 tied to RC-18L at 1670.0 (§5).<br>- C-B/2.75 cast through the cistern base with waterstops. | SEI-N03, EXT-N03, MAT-N07, BLD-N04 | 4.9 |
| C11F-STR-10 | MAJOR | **Lower walls that carry nothing**: LW-11.1, LW-8.2 and LW-6.8.<br>- Make them non-bearing 200 mm dense infill (Rw ≥45 dB, `assumption`).<br>- Show bearing and non-bearing walls in two colours on `supports.png`. | FLX-N02, FLX-01 | 6.4 |
| C11F-STR-11 | MINOR | **Joints and founding levels.**<br>- Corbel with a sliding bearing for the forecourt deck; drawn 100 mm joints at (0, 11.6).<br>- Delete P-F/11.6.<br>- 5 founding levels instead of 15 (1666.5, 1667.5, 1668.6, 1669.4, 1673.0).<br>- A load table marked `assumption`. | SEI-N07, STR-N11, BLD-N07 | 4.9 |

### Ground, retaining & earthworks (GEO)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-GEO-01 | BLOCKER | **PW-N embedment and cap.** It retains 4.26 m at u 6.8 and 3.15 m at u 9.9, yet its toe (1668.6) is 0.8 m below formation; it stops at u 13.2, where the cut is still 1.94 m.<br>- Toe ≤1666.5 at u 0–4, ≤1664.5 at u 4–11.4 and ≤1667.0 at u 11.4–14.5 (`assumption`, sized after boreholes).<br>- Extend it to u 14.5–16.<br>- Step the cap 0.2–0.3 m below ground: about 1677.0, 1673.5, 1671.1 and 1670.2 at u 0, 6.8, 13.2 and 16.<br>- Or design it as propped, with a berm removed in bays ≤1.5 m.<br>- Record the neighbour's wall first (F8). | GEO-N01, STR-N06, BLD-N01, REG-N02, RES-02 | 4.9 |
| C11F-GEO-02 | BLOCKER | **PW-N overlaps the north wall by 0.225 m** over u 0–13.2. The piles occupy v 0.625–1.075 and the wall face is at v 0.85, so there is no room for membrane, drain or XPS.<br>- Default (§5): piles on v 0.40, secant or with a shotcrete facing, and a 0.225 m drained cavity with a membrane, XPS and a DN110 toe drain.<br>- Delete the ensuite window, which faces the piles. | MAT-N02, SEI-N02, WAT-N05, THM-N01, QA-N03, REG-N01, STR-N10, INT-N07 | 4.9 |
| C11F-GEO-03 | BLOCKER | **Road walls.** W2 (0.30 m, base 1675.0) stands 1.725 m from W3 (base 1673.0), inside W3's wedge, with a soil rib between.<br>- Build W2, W3 and the stair as one drained RC U-trough: walls 0.35 m on a common base ≤1673.0 with a shear key, flights strutting between them, counterforts ≤3.0 m apart. Design for traffic (≈10 kPa) plus seismic load.<br>- W2 monolithic to ≥1677.75.<br>- W4 as an L-wall, top at ground +0.15 (1677.70 at u −9.0, 1675.40 at −5.0), moved 0.15 m north: its face is on v 17.42 today.<br>- Soldier piles before any dig west of u −3.<br>- Road survey and consent first (F6). The fallback is C10 §4a's reduced court. | RES-N01, SEI-N06, GEO-N02, GEO-09, ACC-N03, QA-11, BLD-14 | 4.10 |
| C11F-GEO-04 | MAJOR | **No outdoor surface on more than 1.0 m of fill.** Today: lawn-stair top 2.01 m, walk 1.77 m, forecourt 1.64 m, court SE 1.55 m.<br>- Walk: suspended on SW-29/31.<br>- Lawn stair: RC flights from FW-20.6 to a wall on u 22.05.<br>- Forecourt deck extended over v 8.6–11.6.<br>- Court: layered granular fill with geogrid.<br>- Earthworks count the stairs. | GEO-N03, GEO-N06, GEO-N07, GEO-05, WAT-N08, MAT-N05, MAT-09 | 4.9 |
| C11F-GEO-05 | MAJOR | **Honest earthworks.**<br>- About 500 m³ in place (about 650 m³ loose, 43–55 loads) and about 110 m³ of fill; the +74 % shown on the idea page.<br>- A long-reach excavator from the forecourt; skips craned from the road for the lower pit.<br>- Laydown R(−3, 1.1, 0, 11.6).<br>- The dig sequence on the owner's page. | GEO-11, BLD-N02, BLD-06 | 4.4, 7.6 |
| C11F-GEO-06 | MAJOR | **Site walls typed.**<br>- RC where ≥1.5 m (SW-8, 20, 21, 23, 29–31).<br>- Gabion or stone where ≤1.4 m, including the lawn walls (base ≤1666.6, toe ≥1.5 m from the bank face).<br>- All: gravel, a DN100 drain, weeps every 2 m, footing ≥0.8 m. | MAT-05, GEO-07, BLD-03 | — |

### Water & waterproofing (WAT)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-WAT-01 | BLOCKER | **Road water runs down the road stair.** W2's top (1677.40–1677.45) and `rs-head` (1677.47) are below the road edge (1677.51–1677.57).<br>- W2 solid to ≥1677.75 (ARR-02); W4 ≥1677.60 at u −9…−8.<br>- A 30 mm hump at the gate.<br>- A 150 mm slot drain across `rs-head`, with the head at 1677.52.<br>- Treads with a 1–2 % forward fall.<br>- Confirm against F6. | WAT-N01, ACC-N05, RES-04 | 4.11 |
| C11F-WAT-02 | MAJOR | **Forecourt channel** below the road at v 8.5–11.6, with no outfall.<br>- A boundary crest at road edge +0.03–0.05 (about 1677.56).<br>- The channel 0.8 m inside, at 1677.40–1677.44.<br>- A DN150 outfall to the court gully; the court outfall sized for about 96 m².<br>- An interceptor at (−1.0, 7.0). | WAT-N02, VEH-06, WAT-01 | — |
| C11F-WAT-03 | MAJOR | **Garage flood path to the lift.** The "1 %" fall is really 0.44 %.<br>- 1677.50 at the fire door, falling 1.2 % to an internal trench drain at u 0.6–0.8.<br>- A 20 mm hump at the shutter sills (1677.49) and a water bar at the fire door.<br>- A liquid-tight slab with an interceptor; no penetrations over the tanks or the pantry. | RES-N05, MAT-04, INT-13, HLT-N05 | 5.5 |
| C11F-WAT-04 | MAJOR | **Outdoor floors flush with the rooms** (walk, `t-low`, loggia, court).<br>- 150 mm below FFL at walls (walk 1669.85, court edge 1673.45), falling 1:40; or a gravel margin with a channel and tanking.<br>- `t-low` and loggia slabs ≤1669.78, with slot channels at the doors; balconies set down ≥0.10 m.<br>- Door lips ≤20 mm. | WAT-N03, MAT-N03, RES-N03, RES-06, WAT-10 | 5.4 |
| C11F-WAT-05 | MAJOR | **Court water.** The overflow (0.8, 15.9) sits at the door threshold and pours down the court stair.<br>- A court channel at 1673.45, and a scupper through SW-6 into a channel beside `cs-f1…f3`.<br>- A 150 mm kerb on u 4.5, v 13–16.<br>- A slot drain across the `cs-f1` head.<br>- A snow pit 2.0 × 3.0 × 1.5 m at the court's NW corner, with a gate in the W1 guard. | RES-N03, WAT-02, ACC-N05, RES-05 | — |
| C11F-WAT-06 | MAJOR | **Court-stair band.** The strip beside it is 0.08–0.27 m above the treads. A kerb on v 17.27 at ground +0.15 (1672.85 at u 2, 1670.25 at u 9.7), with a cut-off channel. | WAT-N04 | — |
| C11F-WAT-07 | MAJOR | **Outlets inside their own surfaces.**<br>- The `t-south` outlet moves from above landing `cs-l2` to about (7.9, 15.95), with an edge gutter on v 16.4 (u 7.8–15.4).<br>- `fore-deck` outlets at (−1.5, 9.0) and (−2.6, 11.0).<br>- The lawn falls west to a drain on u 21.0, with its overflow at (23.0, 10.0). | RES-N04, MAT-N04, WAT-03, WAT-10, WAT-N06 | — |
| C11F-WAT-08 | MAJOR | **Top roof (about 135 m²) has no water design.**<br>- Fall 1:60 east to internal outlets at about (12.3, 2.0) and (12.3, 12.6), plus a scupper (§5).<br>- A hatch over the REST landing.<br>- An anchor line or a parapet. | WAT-13, BLD-N03, RES-17 | — |
| C11F-WAT-09 | MAJOR | **Buried walls in the model.**<br>- Footing drains (invert 1668.9–1669.35) to the pit at (18.6, 13.0).<br>- Tanking drawn.<br>- The boys' south wall tanked to +1.4 m.<br>- The grandparents' v 1.1 wall (2.07–2.65 m of earth): tanked, 100 mm XPS, a lined wall, beds 0.1 m off it. | GEO-10, WAT-05, HLT-05, HLT-N02, MAT-10 | — |
| C11F-WAT-10 | MAJOR | **Final discharge.** The bank (2.05–3.57 m wide) cannot take a spreader.<br>- A gravel trench 1 × 1 × 10–12 m under the lawn along u 22.5, plus 5 m³ of attenuation.<br>- Percolation test first (F14).<br>- Correct `SPECIFICATION.md`. | WAT-08, LND-N05 | — |
| C11F-WAT-11 | MAJOR | **Lift-pit drain.** Trapped and kept off foul.<br>- Invert 1668.20, running along v 7.0 through FW-20.6.<br>- ≥0.48 m under the lawn, out to daylight, with a flap valve.<br>- Shown in section F–F. | WAT-06, BLD-N08, HLT-03 | — |
| C11F-WAT-12 | MINOR | **North channel, frost, tank room.**<br>- A channel on the pile cap at v 0.3–0.6, falling east.<br>- Heat trace on the north outlets and the forecourt channel.<br>- An 80 mm upstand and a gully at the tank-room door. | REG-N09, WAT-14, RES-N06 | — |

### Arrival, outdoor route & outdoor stairs (ARR)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-ARR-01 | BLOCKER | **Connect the garden walk** (the ledger's C11-ARR-02 is false).<br>- Add `walk-e` R(15.4, 16.0, 18.0, 17.12), suspended at the loggia's level on FW-16.0 and a wall on v 17.12 founded at about 1667.0.<br>- Delete SW-30/38.<br>- Open the loggia front over u 15.65–17.75.<br>- Guards on v 17.12 and u 18.0 (2.4 m drop).<br>- Route: road → court → 24 R → walk → loggia → `t-low` → 16 R → lawn, each joint ≥1.2 m wide (§8.2). | ACC-N01, ACS-N02, LND-N01, INT-N03, OWN-N01, ACC-12 | 4.11, 5.4 |
| C11F-ARR-02 | BLOCKER | **Road edge above the road stair:** a 1.76–2.10 m drop from a public road with no guard.<br>- An RC vehicle parapet monolithic with W2, top about 1678.25 (0.70 m above the road), plus an open rail (≥70 % open) to 1.1 m above the nosings, from the stair head to v 17.12.<br>- No loose stone and lattice wall (§5).<br>- The facing is Q7; the barrier is not optional. | ACC-N02, SAF-N03, VEH-N03, EXT-01, BRF-01 | safety, 4.10 |
| C11F-ARR-03 | MAJOR | **Banks around the road stair.** Ground at v 17.42 stands up to 2.05 m above L1, and a ledge falls 2.6–2.8 m over W3.<br>- W4 as in GEO-03, with a 1.1 m guard over u −9.03…−1.43.<br>- A guard on W3, or a planted 1:1 slope with a hedge. | ACC-N03, SAF-N08, REG-N06 | safety |
| C11F-ARR-04 | MAJOR | **Stair head with no landing.**<br>- A flush refuge 0.30–1.90 m off the boundary, at v 10.0–11.6.<br>- Bollards at (−3.45, 10.3) and (−4.05, 11.3).<br>- A 1.2 m sliding gate on v 11.6, modelled as an element, with a canopy. | VEH-N04, ACC-10, EXT-10, SAF-11 | 2.6 |
| C11F-ARR-05 | MAJOR · owner | **The hayat is open at grade** from the footpath, the lawn and the north strip.<br>- A 1.2 m open railing inside the parcel on v 18.3, from u about −1.4 to u 10 (≥2.3 m from the children's glass).<br>- Gates on the north strip and on the lawn's south edge.<br>- A footpath gate only if the owner asks (Q8). | SAF-N07, BRF-N01, SAF-12 | 4.8 |
| C11F-ARR-06 | MAJOR | **Lawn stair.** Today it is ≤1.05 m clear, on fill, with its head 2.4 m in front of the grandparents' slider.<br>- A suspended RC flight, 1.2 m clear at u 20.75–21.95.<br>- Reversed in place: top landing R(20.6, 9.1, 21.8, 10.3) by the loggia, flights down north to v 3.4 (§5).<br>- A 1.8 m planter screen on `t-low` at v 5.6–5.9.<br>- An east wind screen.<br>- A 1:8 ramp over the 0.34 m step. | ACC-N04, GEO-N03, OPS-N04, PRV-N05, RES-08, BLD-08 | 4.11, 6.4 |
| C11F-ARR-07 | MAJOR | **Ice on outdoor stairs.**<br>- A canopy of about 4 × 1.6 m over L1 + F2.<br>- Flamed one-piece treads with a 1–2 % fall.<br>- Step lights and drained landings. | ACC-13, SAF-15, MAT-09 | 4.11 |
| C11F-ARR-08 | MINOR | **Widths and edges.**<br>- Court stair 1.12–1.17 m clear, not 1.27 as stated: walls outside v 17.27, or accept the width and correct the text.<br>- Forecourt at 1677.48–1677.49 in front of the road door (a 30 mm step today).<br>- A court bench-planter on u 4.6, v 13.25–15.0; a pomegranate and a basin. | ACC-N07, ACC-08, ACS-07, EXT-N04, LND-08 | 5.4 |

### Garage & vehicles (VEH)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-VEH-01 | BLOCKER | **Tyre rack in shutter 1's opening** (R(0.2, 1.2, 0.5, 4.4), 0.05 m from car 1).<br>- A high rack R(0.6, 1.25, 3.8, 1.55) on the north wall, base ≥2.05 m.<br>- Check that u 0.15–0.65 behind every opening is free. | VEH-N01, OPS-N07 | 5.5 |
| C11F-VEH-02 | MAJOR | **Bay 2.** The LC300 is 0.225 m from the pier.<br>- Shutter 1 at v 1.40–4.75, a 0.60 m pier, shutter 2 at v 5.35–8.70, with RB-5.3 moved to v 5.05.<br>- Bay 1 for the smaller car, with a mirror and an exit light.<br>- Building-line caveat (F5). | VEH-N02, VEH-02, VEH-03, REG-09 | 5.5 |
| C11F-VEH-03 | MAJOR | **Forecourt as a vehicle structure.**<br>- Deck and piers designed for ≤16 t (`assumption`), with a hinged transition slab on PB-F.<br>- No laydown on the deck for 28 days.<br>- RW-W1 to 1678.07 as an impact-rated 0.6 m upstand + 0.5 m rail, continuous from u −4.41 to −0.25. | VEH-N05, VEH-07, GEO-05, SAF-01, QA-N09, EXT-N05 | safety |
| C11F-VEH-04 | MAJOR | **Stop bay** (not drawn): (−2.22, 4.48), (−4.72, 9.05), (−2.79, 10.11), (−0.29, 5.54). Door operator ≥0.2 m/s. | VEH-04 | 5.5 |
| C11F-VEH-05 | MAJOR | **Workbench** (not fixed). 4.1 m at u 0.6–4.7, with the bikes hung on the north wall below the tyres. | BRF-05 | 6.3 |
| C11F-VEH-06 | MINOR | **Aisle, EV, risers, bins, spec.**<br>- Cars at u 0.47–5.45, for a ≥1.2 m aisle.<br>- EV point on the pier at about (0.15, 5.3).<br>- SH-W as an EI 60 shaft with a kerb.<br>- A bin shelf R(0, 0.05, 2.4, 0.85) at 1677.45 on the pile cap, with a guard.<br>- One spec block on the road plan: fire door, CO, extract, coil box, wheel stops. | CIR-N06, VEH-N06–N09, QA-N08, VEH-01/09/10/11, OPS-05 | 5.5 |

### Stair, lift & circulation (CIR)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-CIR-01 | BLOCKER | **Stair spine and voids.**<br>- A 0.15 m RC spine centred on u 8.10, v 2.5–5.9, on every storey, leaving the flights 1.10 m clear.<br>- The road void (u 6.8–9.4 × v 1.1–≥3.1) drawn as a void, not as treads.<br>- 1.1 m guards on every void edge (the road landing at v 5.9 edges a drop of up to 3.9 m), and handrails on both sides.<br>- A section at u 8.7. | CIR-N01, CIR-12, SAF-07, SEI-05, CIR-N08 | 5.2 |
| C11F-CIR-02 | MAJOR | **The lift as a closed tube.**<br>- A 0.20 m RC front on v 7.3.<br>- A smoke-sealed landing door at road level, or the screen line moved; CO alarm in `lobby-r`.<br>- Pit and overrun in F–F.<br>- Rescue device, battery and hook in the spec. | CIR-N05, SAF-N06, HLT-02, CIR-03, BLD-10 | 5.4 |
| C11F-CIR-03 | MAJOR | **Bedroom doors beside the lift** (0.0 m latch-side space). Doors on v 6.2 (u 11.5–12.5) with 0.9 m leaves hinged at u 11.5. That gives 0.76 / 0.81 m of pull-side space, and the master's door sits 1.25 m off the guests' line. | ACS-N03, CIR-N04, PRV-07, ROM-N07 | 2.5, 5.4 |
| C11F-CIR-04 | MAJOR | **Laundry neck** (0.69–0.73 m clear with a 0.8 m door).<br>- `lav`'s south wall to v 9.80: 0.99 m neck.<br>- Stacked machines at R(4.83, 10.2, 5.48, 10.85), a sink, and a 1.2 m folding counter at R(5.6, 11.5, 6.7, 12.1).<br>- A floor drain.<br>- Report the area without the neck: about 3.8 m² now, against 4–6 m². | CIR-N02, ROM-N09, OPS-N05, KB-N08 | 6.7 |
| C11F-CIR-05 | MAJOR | **Stair rooflight.**<br>- Operable, about 2.2 × 1.2 m, at u 6.95–9.25, v 1.25–2.7, with ≥1.0 m² free area for night purge.<br>- No north window (it would face PW-N 0.25 m away). | CIR-11, SUN-06/08, THM-11, INT-12, HLT-N08 | 5.3 |
| C11F-CIR-06 | MAJOR | **Hall daylight.** The "walk-on rooflight" lies under the road roof.<br>- Delete it, or make it a real 0.8 × 1.8 m rooflight over fritted, slip-resistant glass.<br>- Obscured fanlights over the children's doors to light `hall-l`. | SUN-N04, INT-N04, HLT-N06, CIR-N07, PRV-N07 | — |
| C11F-CIR-07 | MINOR | **Under-stair store.**<br>- 0.40 m shelves on one side only.<br>- The sealed bay under the landing joined to the store.<br>- Report the usable area (about 3.8 of 5.5 m²).<br>- The lower stair opened to `hall-l` over u 8.2–9.4 (1.2 m today). | CIR-N03, ROM-N08, OPS-N06, INT-N10 | 5.3, 6.3 |

### Rooms (ROOM)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-ROOM-01 | BLOCKER | **Living room, rule 3.1.** The sofa sees 15 m down the hall, and the shelf hides the TV.<br>- A 2.1 m bookcase screen at u 13.4–13.75, v 7.3–8.7, with the TV on its east face.<br>- Delete the west-wall TV and the armchair in front of it.<br>- Entrants turn south at v 8.7–9.7.<br>- Ray test sofa → hall: 0 hits. | OWN-N02, INT-N01, INT-03, ROM-08, SUN-N07 | 3.1 |
| C11F-ROOM-02 | MAJOR | **Lounge.** Today the sofa overlaps the coffee table and the TV is on the grandparents' wall.<br>- Sofa R(13.4, 8.9, 15.8, 9.8), facing north.<br>- TV centred on u 14.6, backed by the guest wardrobes.<br>- Table R(14.0, 7.6, 15.2, 8.3); two armchairs.<br>- A 1.05 m garden route. | INT-N02, ROM-N03, PRV-08 | 6.4 |
| C11F-ROOM-03 | MAJOR | **Master bedroom.** Bed at v 2.05–3.85 (0.35 m off the wall today); a 0.6 m wardrobe at u 12.54, v 1.9–3.3. | ROM-N04, ROM-N11 | 7.3 |
| C11F-ROOM-04 | MAJOR | **Children's rooms.** The bed heads are on the laundry and lounge walls, and the rooms are 4.14 / 4.05 × 4.59 m clear.<br>- LW-10.95 to v 10.75.<br>- Wardrobes as buffers on the noisy walls; boys' desks on the laundry wall.<br>- 1.2–1.4 m desks.<br>- Doors re-hinged at u 9.95 and u 12.3.<br>- Show both grid and clear sizes. | PRV-N03, PRV-N04, ROM-N10, BRF-N03, OWN-N08 | 6.4, 6.7 |
| C11F-ROOM-05 | MAJOR · owner | **Front door (rule 2.6).** It is recessed, faces RC-0 2.0 m away, and is two to three turns from the core.<br>- (a) Keep it, with a sidelight at u 2.0, v 11.1–11.5;<br>- or (b) a south door at u 2.6–3.6 under a canopy.<br>- Correct the "one turn" evidence. | ROM-N06, OWN-N07 | 2.6 |
| C11F-ROOM-06 | MAJOR · owner | **Main hall (rule 2.2).** It is 10.6 m long with 7 doors, and it was shown to the owner as "your decision".<br>- Ask with a plan crop (rule 8.1).<br>- Prepare the alternative: widen the hall into the dining. | OWN-N04, ROM-09, BRF-N05 | 2.2, 8.1 |
| C11F-ROOM-07 | MAJOR · owner | **Sizes against the owner's B.** The master suite is 37.0 m², bigger than the 34.0 m² living room; the grandparents' suite is 36.7 m² (B: 17.5).<br>- Default: master about 22 m², with the L-leg as a wardrobe wall.<br>- The grandparents' north strip (about 8.7 m²) becomes a linen store.<br>- No window on u 18, v 1.1–3.3, which is a shear panel.<br>- Correct decision 19's text. | BRF-N02, QA-N07, INT-06 | 7.4 |
| C11F-ROOM-08 | MAJOR · owner | **Rule 4.1 at road level.** 7.4 m of the south façade is WC, plant and store (Q5). | OWN-N05 | 4.1 |
| C11F-ROOM-09 | MINOR | **Island, dining, storage.**<br>- Island 1.8 × 0.8 m with 3 stools at 0.6 m, and nothing on the serving line.<br>- Dining sideboard moved to the kitchen.<br>- A hall cupboard, two cleaning cupboards (not fixed) and a 0.6 m coat section.<br>- `store-s` shelving with a 0.85 m aisle and air. | ROM-02, KB-10, BRF-N07, INT-10, ROM-10, OPS-09, OPS-N10, OPS-N06, OPS-12 | 1.4, 6.3 |

### Kitchen & bathrooms (KB)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-KB-01 | BLOCKER | **SH-E blocks both ensuite doors.** At R(11.0, 3.55, 11.4, 4.15) it leaves 0.25 m and 0.35 m. Relocate it, stacked, so that:<br>1. the door width plus 0.9 m on each side is free;<br>2. the stack sits beside the pans;<br>3. the seated ensuite keeps a true Ø1.5 m circle and a ≥1.7 × 1.2 m wet zone.<br><br>First choice (§5): a service wall at u 9.53–9.93, v 3.0–4.4, with the pans in front of it. | ROM-N01, ACS-N01, KB-N01, FLX-N01, MEP-N02 | 2.5, 5.4 |
| C11F-KB-02 | BLOCKER | **The wudu bench leaves 0.29 m in front of the shower door.**<br>- Shower door at u 4.14–4.89.<br>- Bench and trough at v 5.95–7.24, leaving a 0.99 m landing; the trough drawn with a drain.<br>- Basin on `wlob`'s west wall at v 5.0–5.5.<br>- `wlob` → `wudu` opening at v 5.0–5.9, out of the hall's view; check it against the basin. | KB-N02, KB-09, PRV-04 | 2.3, 6.7 |
| C11F-KB-03 | MAJOR | **Kitchen.**<br>- Keep SH-K stacked (§5); a 0.75 m hob at v 11.05–11.80; masonry behind it; induction preferred.<br>- Draw the larder, tea niche, dishwasher and bins.<br>- A separate Ø200 hood duct to ≥1.0 m above the roof (a Ø150 duct loses about 170 Pa, `inferred`).<br>- Interlocked make-up air.<br>- Kitchen opening ≥1.5 m and clear of C-6.8/9.5, once the SH-W box leaves the hall.<br>- Pantry ≤3 m away. | ROM-N05, KB-N05, KB-N10, KB-04/05, THM-N06, MEP-N09, CIR-13, ROM-N12, OPS-10 | 1.3–1.5 |
| C11F-KB-04 | MAJOR | **Lower WC** (pan in a 0.60 m slot).<br>- Pan at about (6.10, 9.70), facing north.<br>- Slider at v 8.80–9.50.<br>- Re-test the sightline.<br>- After STR-03. | ROM-N02, INT-N05, KB-N03, MEP-N08, KB-11 | 6.1 |
| C11F-KB-05 | MAJOR | **Wet-room fit-out.**<br>- Basins on the ensuites' east walls.<br>- Seated ensuite: a fold-down seat, rails, a pocket door to the north, the true Ø1.5 m circle drawn.<br>- `wc-m`: south wall to v 5.15 and a west-wall basin, for a true Ø1.5 m circle; or call it "assisted".<br>- Every WC: shattaf, floor drain, dado, drawn. | ACS-01/02/10, KB-N07, KB-13, KB-08 | 5.4 |
| C11F-KB-06 | MINOR | **Road WC.** North wall to v 11.3; the pan on the east wall; an outward 0.8 m door.<br>**`lav`:** two basins at 0.6–0.7 m centres. | KB-14, ACS-N05, BLD-12, KB-N06 | — |

### Services (MEP)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-MEP-01 | MAJOR · owner | **Plant room** (3.0 m² clear, 1.19 m deep, no flue).<br>- Default: merge `store-r` into R(4.4, 11.3, 9.4, 13.0), about 7 m² clear.<br>- A ≤0.6 m equipment zone, a 1.2 m self-closing fire door.<br>- Its own room-sealed flue, never in SH-K.<br>- An outdoor-unit pad.<br>- Q5 offers the alternative. | MEP-N01, BLD-N06, FLX-N03, HLT-N04, THM-09, BRF-10, MEP-07, SAF-06, RES-11 | 6.7, 4.1 |
| C11F-MEP-02 | MAJOR | **Cylinder and boiler above the hob and sink.**<br>- A 150 mm bunded, tanked floor with a gully to SH-K.<br>- A leak shut-off and a cylinder tray.<br>- No pipe joints over the kitchen.<br>- Slab recesses under the upper wet rooms. | KB-N04, WAT-12, MEP-N07, MEP-09 | 1.3 |
| C11F-MEP-03 | MAJOR | **Risers and ventilation.** No riser can take a heat-recovery trunk.<br>- Default (§5): extract fans into the risers, plus single-room heat-recovery units in the bedrooms, lounge and living room.<br>- Draw the extract runs for the 20 windowless rooms, with their rates.<br>- Duct-zone ceilings 2.70 / 2.60 m. | MEP-N02, MEP-05, HLT-01, HLT-04, INT-05, HLT-N09 | — |
| C11F-MEP-04 | MAJOR | **Service entries cross the void under the forecourt deck.**<br>- Mains through MW-0F at v about 4.9–5.7, with ≥0.8 m cover.<br>- A backfilled strip at v 10.4–11.6 for the drain.<br>- Break chamber at (−2.0, 11.0).<br>- A shut-off niche in the pier at v 9.03–10.10. | MEP-N04, MEP-07, RES-12 | — |
| C11F-MEP-05 | MAJOR | **Foul outfall** (F3). Under option A, a sealed acoustic lifting pit at R(4.85, 14.25, 6.05, 15.45), nothing fixed to the boys' wall, on the battery circuit. | MEP-N05, MEP-01, HLT-N09 | — |
| C11F-MEP-06 | MAJOR | **Power and resilience on the plans** (not fixed).<br>- The main board, a fire-separated battery cupboard, and a generator inlet.<br>- A 43–68 m² PV zone.<br>- Earthing and surge protection.<br>- A booster on the battery circuit (0.16–0.28 bar by gravity).<br>- A third tank, for ≥4 m³. | MEP-08, THM-12, RES-09/10/15, MEP-N10 | — |
| C11F-MEP-07 | MINOR | **Smaller services.**<br>- A hot-water return loop and a tea-bar heater.<br>- The tea-bar drain trace-heated.<br>- Split-unit positions.<br>- A cistern pump with a backflow preventer. | MEP-11, THM-10, MEP-13, MEP-10 | — |

### Sun, daylight & envelope (ENV)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-ENV-01 | MAJOR | **Lounge winter sun.** The pergola adds 1 %. Open the whole strip u 15.4–18.0, v 13.0–16.4 with a rail guard: 2.1 h and 1,231 Wh/m², +81 % (`measured`). RC-18L stays solid. | SUN-N01, SUN-05, THM-03, INT-07 | — |
| C11F-ENV-02 | MAJOR | **Grandparents' room.** One slider under the balcony: 0.9 h of sun, daylight factor about 1.3 %, CO₂ about 1,500 ppm (`inferred`).<br>- A grating on the outer 1.0 m of both balconies: 1.7 h (`measured`).<br>- Opening widened to v 3.3–5.5, as a hinged leaf plus a tilt-turn sash with a night vent.<br>- ≥15 l/s supply, and external blinds. | SUN-N02, SUN-04, HLT-N01, HLT-09 | — |
| C11F-ENV-03 | MAJOR | **The opaque balcony screen on v 6.2** halves the master's sun (2.3 → 1.2 h) and removes its second way out.<br>- Obscured glass with a 0.8 m gate (keyless on the master's side).<br>- A 1.8 m opaque return on v 2.6. | SUN-N03, SAF-N05, REG-03, RES-16 | 4.3 |
| C11F-ENV-04 | MAJOR | **Canopies as real elements** in the structure, sections and 3D:<br>- SSE canopy CAN-13 at 1677.15–1677.35, 1.0 m clear of the wall, with a heated gutter;<br>- 1.0 m canopies over the four uncovered doors;<br>- the drift-zone canopy;<br>- `balc-e`;<br>- the road door. | SUN-N05, SUN-03, THM-02/05, EXT-08/10, INT-01, RES-07 | — |
| C11F-ENV-05 | MAJOR | **Glass balance.** ENE is 28.3 m² against 34.7 m² SSE (a ratio of 0.82).<br>- Office slider 1.8 → 1.2 m.<br>- Blinds drawn on all ENE openings.<br>- Uw ≤1.3, and ≤1.0 on the ENE side.<br>- Keep the lounge ENE window (§5).<br>- Boys' window head 2.65 m. | THM-01, SUN-02, SUN-11, HLT-11 | — |
| C11F-ENV-06 | MAJOR | **The garage over rooms** (made worse).<br>- 120 mm under the garage slab, 80 mm on the shared walls, 100 mm under the garage roof.<br>- Insulated shutters.<br>- 150 mm under the other exposed floors. | THM-08, THM-13 | — |
| C11F-ENV-07 | MAJOR | **Thermal bridges.**<br>- Thermal-break connectors on u 18.25 (ψ ≤0.2).<br>- Wrap the `t-south` lip.<br>- Insulation returned at RC-18L. | THM-06, THM-N02 | — |
| C11F-ENV-08 | MAJOR | **Crawl voids** (0.15–2.35 m deep, closed).<br>- ≥0.30 m deep everywhere.<br>- Either cross-ventilated, or sealed inside the radon membrane with a sump.<br>- Hatches; floors falling east; precast planks.<br>- Radon membrane and sumps drawn. | BLD-N05, HLT-N03, INT-N09, THM-N05, HLT-03 | — |
| C11F-ENV-09 | MINOR | **Smaller envelope items.**<br>- The green roof needs 0.46 m of build-up and has 0.38 m: raise it to 1677.60 or set the slab down 0.35 m.<br>- Sheers on the prayer-facing glass.<br>- Façade bearings and sun arcs on the site sheet. | THM-N04, MAT-11, SUN-N06, SUN-12 | — |

### Safety & security (SAF)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-SAF-01 | BLOCKER | **The guard check cannot fail.** `missing` is never appended to, and the check skips edges near footprints, the kinds `green` and `pergola`, road edges, digs and internal voids. Rewrite it (§8.1), with a test that fails on today's `deck-r`; guards become elements. | SAF-N01, QA-N09, LND-N07, ACC-N06 | 8.1 |
| C11F-SAF-02 | BLOCKER | **Unguarded drops** (1.1 m guards, typed per EXT-02):<br>- `deck-r` east and south (3.6–3.9 m);<br>- the `t-south` lip over the court stair (1.95–2.50 m);<br>- the pergola void (3.6 m);<br>- the loggia east (2.15–2.45 m);<br>- `t-low` south (2.3 m);<br>- the green-roof joint u 12.6, v 6.2–7.3;<br>- the gap u 4.32–4.6 on v 16.0.<br><br>Green roof: an upstand, anchors and a locked gate. The drying yard moves to R(14.0, 6.8, 17.8, 8.4), away from the guard. | SAF-N02, QA-N02, SAF-02/08/09, OPS-N09, REG-N08 | safety |
| C11F-SAF-03 | BLOCKER · owner (fuel) | **LPG cage in the 3.9 m deep sunk court,** 2.0–2.4 m from the front door. Heavier-than-air gas would pool and run down past the children's windows.<br>- No LPG below the surrounding ground.<br>- Default: induction burners at R(−4.3, 12.4, −2.5, 14.0), with a tap, a gully and a 32 A socket.<br>- Natural gas if a main exists (F4).<br>- Cylinders only at forecourt level, clear of bay 1 (§5). | SAF-N04, MEP-N06, RES-N02, OPS-N03, KB-N09, EXT-N04 | safety |
| C11F-SAF-04 | MAJOR | **Windows as elements.**<br>- `Win` gets a sill, head and opening.<br>- An escape casement ≥0.45 × 0.75 m and ≥0.98 m² openable per bedroom, with a night vent.<br>- Shutters and locks. | SAF-10, HLT-09, HLT-10 | — |
| C11F-SAF-05 | MAJOR | **Detection, outage and security on the plans.**<br>- Alarms; CO alarms in `lobby-r`, the plant room and both halls.<br>- An evacuation chair; assembly points (road; lawn east of u 23.5).<br>- Ember mesh and a gravel strip.<br>- A thumb-turn on the road screen door; a key-switched lift call. | SAF-13/14, ACS-06, RES-12/14, PRV-N08, FLX-02 | — |

### Privacy & acoustics (PRV)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-PRV-01 | MAJOR | **The walk and court stair pass the children's windows.** Eyes are 0.70–1.12 m above the sill, 0–1.3 m from the glass.<br>- Translucent glazing from the sill to FFL +1.75, clear above.<br>- No screen or hedge within 2 m (§5). | PRV-N01, LND-N06, ROM-05, PRV-02, ACC-04, REG-05 | 4.8, 6.4 |
| C11F-PRV-02 | MAJOR | **Impact noise over all four children's beds.**<br>- Floating screed (ΔLw ≥20 dB, `assumption`) in the kitchen, dining and living.<br>- Resilient ceilings below.<br>- Terrace pavers on a resilient layer.<br>- Solid-core bedroom doors. | PRV-N02, PRV-03, PRV-06, HLT-10 | 6.4 |
| C11F-PRV-03 | MAJOR | **The terrace table is seen from the road.** Move it to u 9.6–11.4, v 13.8–14.7, behind the road block; no screen on W1 (§5). | PRV-N06, PRV-01, BRF-07 | — |
| C11F-PRV-04 | MAJOR · owner | **The cook is seen from the living room.** No offset clears every sightline (Q10). | PRV-15 | 1.3 |

### Garden & landscape (LND)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-LND-01 | MAJOR · owner | **Lawn 74.4 → 56.8 m².**<br>- Report the garden by part: the 147 m² is lawn 57, terrace 30, stair 8, bank 36, pockets about 9.<br>- Ask Q4 again (Q2 in §6).<br>- Ball-stop net and hedge on the downhill edge. | LND-N02, LND-03, BRF-08, BRF-N05, LND-05 | 4.6, 4.7 |
| C11F-LND-02 | MAJOR | **Garden store and cistern.**<br>- Stop FW-19.3 at v 6.2–6.5 (engineer).<br>- One store R(18.25, 6.6, 20.45, 12.65), floor 1667.60, with a 1.2 m door.<br>- The cistern R(18.2, 1.3, 20.4, 6.2) as its own tanked box, about 14.5 m³, with a hatch.<br>- Both digs in the earthworks. | LND-N03, OPS-N02, BLD-N04, LND-12, RES-13, MAT-N07 | 2.3, 6.3 |
| C11F-LND-03 | MAJOR | **Leftover pockets** (rule 2.3).<br>- Under `balc-e`: fill to 1667.60 with a drain, as a covered bench or sandpit (§5).<br>- South of the loggia: it becomes `walk-e`.<br>- The NW slot becomes a herb bed at 1668.6. | LND-N04, ACC-N08, SAF-09 | 2.3 |
| C11F-LND-04 | MAJOR | **Trees** (not fixed).<br>- Three trees on the bank midline at (29.3, 2.5), (27.55, 6.0) and (25.55, 10.0).<br>- 6–8 m high species, with a root barrier.<br>- Fix `tree_spots`. | LND-04 | 4.6 |
| C11F-LND-05 | MINOR | **Garden use.**<br>- Play area and bench at u 19.2–22, v 12–17.<br>- Herb planter west of the kitchen slider.<br>- Taps and a foot-wash gully at (18.2, 12.5).<br>- Loggia shoe cabinet and drying rack.<br>- A rain chain; wheel channels. | SUN-07, LND-09/11/13, LND-06, OPS-02/04, CIR-09 | — |

### Household operations (OPS)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-OPS-01 | BLOCKER | **Bulk store unreachable; tanks trapped** (0.32 m gap; the Ø1.24 m tanks fit through no door).<br>- Two 0.7 × 2.2 × 1.0 m tanks at R(0.25, 1.4, 0.95, 3.6) and R(0.25, 3.8, 0.95, 6.0), and the booster at v 6.2–7.0. That leaves a 0.99 m passage.<br>- Optional: a pantry door at u 2.15–2.95.<br>- Name it one service room, and tell the owner it holds the garage up. | OPS-N01, MEP-N03, BRF-N06, BLD-N06, RES-09 | 6.3 |

### Exterior & openings (EXT)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-EXT-01 | MAJOR | **South openings schedule.** Frames ≥0.15 m from column faces, and ≥0.3 m solid either side of u 12.6:<br>- entry window 1.2 m at u 2.7–3.9;<br>- kitchen window at 5.2–6.4;<br>- kitchen slider 2.0 m at 7.2–9.2, with a ≥1.0 m leaf;<br>- dining: a 1.0 m fixed window at 9.7–10.7;<br>- living slider at 12.9–15.0;<br>- the 0.6 m window deleted;<br>- office window at 9.5–10.7.<br><br>Children's windows matched (≥1.8 m, 2.65 m heads). Heads 2.7 / 2.5 m. | EXT-N01, EXT-N06, EXT-04, ACS-08, BLD-12 | 1.1, 7.4 |
| C11F-EXT-02 | MAJOR | **3D and finishes.**<br>- Shells on the 0.25 m outer face; the columns show proud today.<br>- Model the canopy, parapets, gate and road parapet.<br>- Typed 1.1 m guards (1.05 m in the stills).<br>- A `finish` per façade: limestone below 1673.3, lime render above. | EXT-N02, EXT-N03, EXT-06, EXT-11, MAT-08, MAT-N06 | 7.5, 7.6 |
| C11F-EXT-03 | MINOR | **Façade details.**<br>- A 0.5 m parapet round the road block.<br>- A louvre round the core plant, counted in the height.<br>- The road south canopy line.<br>- Stone-faced site walls with copings. | EXT-07, EXT-N07, EXT-05, THM-05 | — |

### Flexibility (FLX)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-FLX-01 | MAJOR | **Adaptability drawn, not claimed.**<br>- Lintels at the stair mouths, and a lintel opening in LW-6.2 at u 13.1–14.1.<br>- Lift key switches.<br>- A 1.1–1.2 m fire door.<br>- A main-floor washer reserve.<br>- A fold-down double bed in the office.<br>- The road stair ready for a platform lift. | FLX-02/03/04/05/08, FLX-N05 | 5.4 |

### Planning & neighbours (REG)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-REG-01 | MAJOR · owner | **Area, coverage and height.** 552 m² gross and 42.9 % cover at the wall faces, against 510 m² and 40 % on the grid.<br>- Report both, with the C08 context.<br>- A height table: overall 13.3 m, 14.1 m to the overrun.<br>- Ask which measure counts (F5). | REG-N05, REG-N07, BRF-N08 | 4.7 |
| C11F-REG-02 | MAJOR | **Building line before W2.** Any road widening takes W2 and L1.<br>- Get the line before building.<br>- Keep the C10 §4a fallback.<br>- The gate opens inward. | REG-N04, REG-09 | 4.10 |
| C11F-REG-03 | MAJOR | **North overlooking.**<br>- Plant `t-low`'s north 1.5 m (v 1.1–2.6), with a 1.8 m screen on v 2.6.<br>- A hedge on v 1.2, u 24.9–28.0.<br>- A 1.8 m screen on `deck-r` along v 6.2. | REG-N03, LND-13, REG-11 | 4.3 |
| C11F-REG-04 | MAJOR | **Footpath edge.**<br>- A guard on W4's path side; a solid parapet on SW-29/30.<br>- No drainage onto the path.<br>- The easement first (F7). | REG-N06, REG-06 | 4.7 |

### Checks, drawings & owner page (DOC)

| ID | Sev | Correction | Sources | Rule |
|---|---|---|---|---|
| C11F-DOC-01 | MAJOR | **What the owner is told.**<br>- The access limits:<br>  - road door + lift is the only step-free entrance;<br>  - a ramp to the court would be about 46 m long;<br>  - the lawn is 16 steps down;<br>  - the terraces are step-free from inside only;<br>  - the lift runs on its battery in a power cut.<br>- Each decision quotes the owner's words, gives the change from C10 in numbers, and lists the alternatives.<br>- Headline "40.6 m² open court + 4.2 m² porch".<br>- Correct the 14 ledger rows. | ACS-N04, BRF-N05, OPS-N08, OWN-N06 | 7.6, 8.1 |
| C11F-DOC-02 | MAJOR | **The specification in the deliverable.**<br>- Link `SPECIFICATION.md` from the owner's page, with every figure marked `assumption`.<br>- A typed `SPEC` in `design.py` (walls, roofs, site walls, concrete C35/45 air-entrained, windows), tagged on each element.<br>- `drawings/water.png` plus three details. | THM-N03, MAT-N01, WAT-N07, VEH-N08, MAT-13 | 7.6 |
| C11F-DOC-03 | MAJOR | **The 0110-r2 register.** I01–I30 with measured statuses. Known: I05, I11 and I15 partly fixed; I20 made worse; I26 not fixed. | BRF-N04, BRF-07 | 6.7 |
| C11F-DOC-04 | MINOR | **Drawings match the model.**<br>- F–F with the lift pit.<br>- Buried walls drawn at their thickness; levels on the plans.<br>- Beam tops at FFL −0.15.<br>- Rule 5.1 at 3.6 m, not 4.4.<br>- One garden figure (147, not 151).<br>- Garage 53.0 m² clear.<br>- Every label collision-tested. | QA-N06, QA-N07, QA-07, CIR-N08, INT-N08, OWN-N09/N10 | 7.1, 7.6 |

## 5. Conflicts between reviewers and how they are resolved

| Topic | Positions | Resolution and why |
|---|---|---|
| Does the walk connect? | Connected: 22, 24, 26. A single point: 05, 12, 14, 18, 28. | **It does not.** The rectangles share a point; measured geometry wins. |
| Walk extension | Full width to u 18.0 (05, 12, 14), or to u 17.0 (18, 28); on fill (12, 14) or suspended (05, 18, 28). | **u 18.0, suspended.** It opens the whole loggia front, and fill would reach 2.2 m. |
| PW-N line | Piles north with a drained cavity, on v 0.30–0.575 (02, 03, 04, 09, 16, 22, 27). Piles as the permanent outer leaf, lined inside (15, 21). | **v 0.40 with a 0.225 m cavity.** Physics: it separates the retaining wall from the frame (route A) and allows outside waterproofing. 15/21's version only if the piling rig cannot work 0.175 m off the boundary (F8); the house then takes about 1.0 MN of thrust. |
| PW-N toe | ≤1664.5 (03, 15); ≤1665.4 (22); ≤1667.0 or propped (01). | **Draw ≤1664.5 at u 4–11.4 as an `assumption`.** Boreholes size it. |
| Road-edge barrier | A stone + lattice wall to about 1679.2 (13, 17, 26). An RC parapet + open rail (19, 22). A guard on W2 (05, 11). | **An RC parapet about 0.7 m above the road, plus an open rail.** Safety: a loose 1.8 m mass in a seismic zone, sitting in the cars' sight splay. Privacy comes from PRV-03. |
| Road walls | Stepped W2/W3 (C10 §4a). One trough (02, 03, 22). | **The trough.** W2's footing lies in W3's wedge. |
| SH-E position | North of the door (07, 24), in the dressing room (12), beside the pans (10, 20). | **The KB-01 tests decide.** First choice is beside the pans: short soil runs, and no shower or wardrobe shrinks. A north position only if the true Ø1.5 m circle, which fits only at (10.40, 2.27), survives. |
| Lawn-stair direction | Reverse it in place (25). Move it south to v 6.6–13.48 (13). | **Reverse in place, plus 13's screen.** It keeps the footprint, takes nothing more from the lawn's 2.6 m wide tail, and lands at the loggia tap. |
| Fence and children's glass | A 1.8 m fence on v 17.42 (11); a railing on v 18.3 (26); a hedge at v 17.2–17.4 (21); a screen on v 16.0 (05). | **Rule 4.8 first:** nothing above the sill within 2 m. The railing goes on v 18.3; privacy comes from the glazing. |
| Pocket under `balc-e` | Fill to 1669.98 (11) or to 1667.60 (14). | **1667.60.** Filling to 1669.98 means 2.3–3.1 m of fill; at 1667.60 the pocket is usable space (rule 2.3). |
| Cistern | The full bay (15); off the house wall (22); off the columns (27). | **The full bay as its own tanked box,** with a gap to the house and collars on the columns. 14.5 m³ against about 7 m³. |
| Top-roof fall | East (04) or west (15). | **East.** The forecourt already takes the road water and ices at the stair head. |
| Plant room | Merge `store-r` into it (09, 10, 15, 23, 24, 26). Use `store-r` for the battery (22). Rule 4.1 forbids stores on the best façade (28). | **Merge.** Six reviewers agree it is a physical need. The battery goes elsewhere. Rule 4.1 goes to the owner (Q5). |
| Moving SH-K | West to u 3.8–4.4 (07), or keep it (20). | **Keep it.** The lower floor starts at u 4.6, so SH-K could not stack. |
| Ventilation | Central heat recovery (23, `SPECIFICATION.md`). Decentralised (10). | **Decentralised,** unless a 0.4 × 0.8 m riser is found on every floor. |
| Lounge ENE window | Delete it (09). Keep it (08, 23). | **Keep it, with blinds; cut the office slider instead.** It is the lounge's only winter sun, and the lounge already lost sun. |
| RC-18L | Open it for sun (09, 17). Keep it solid (01, 02). | **Solid.** It is the downhill shear panel (safety). |
| C-B/16.2 | Delete it, with a cantilever (17). Keep it at 0.40 m, tied to RC-18L (02). | **02's version,** unless the engineer approves the cantilever. |
| W1 face | A 1.8 m screen (13). A low upstand + rail (17). | **The low face.** A screen would make a 5.6–6.3 m wall over a court 4.4 m deep; the table moves instead. |
| Terrace table | u 4.7–6.5 (26). u 9.6–11.4 (13). | **u 9.6–11.4.** It is hidden from the road, and over desks, not beds. |
| Office slider | 2.4 m (12). 1.2 m (09). | **1.2–1.4 m with a 0.9 m leaf.** The lobby door is the step-free one. |
| Girls' window | Reduce it to 1.8 m (17). More glass (08, 23). | **Match both rooms at ≥1.8 m with 2.65 m heads.** |
| Bins | On the forecourt (16). On a pile-cap shelf (19, 25). | **The shelf.** The forecourt spot blocks bay 1. |
| Grandparents' east window | Add one (16, 18, 23). A solid panel (02). | **The panel** (safety). |
| Green-roof edge | A 1.1 m guard (11, 17). An upstand + anchors (21). | **Upstand + anchors** on the locked roof, so it casts less shade on the north lot. |
| LPG spots | (−5.0, 3.0) (11); (−1.0, 2.0) (10). | **Neither.** The first is outside the parcel; the second is in front of shutter 1. |
| Ledger statuses | 28 verified 56 rows; the specialists contradict 8. | **Measured evidence wins** (DOC-01). |

## 6. Owner decisions from this review

| # | Question | Recommended default | From |
|---|---|---|---|
| Q1 | Court cooking: induction, natural gas, or LPG at road level? | Induction; no LPG below road level | 10, 11, 22, 25 |
| Q2 | Lawn (Q4 again):<br>(a) 57 m², 3.2 × 6.8 m, 1.33 m wall;<br>(b) about 86 m² on one level, a 3.0–3.2 m wall, 184 m³ of fill;<br>(c) about 110 m² to the setback | (a), plus pockets (+6.1 m²) and the reversed stair. Quote "flat outdoors" and "level, not steps". | 14, 26 |
| Q3 | Main hall (rule 2.2): accept 10.6 m, or widen it into the dining? | Ask with a plan crop; rule 2.2 is not a pass until answered | 07, 26, 28 |
| Q4 | Front door (rule 2.6): (a) keep it with a sidelight; (b) a south door | (a) | 07, 28 |
| Q5 | Rule 4.1: plant room enlarged on the road's south façade, or moved into the buried service room (frees a hall window; loses about 9.6 m² of store; needs a flue through the garage)? | Enlarge it on the south façade | 10, 15, 24, 28 |
| Q6 | Master about 22 m² and the grandparents' strip as linen, as in the owner's B? | Yes (rule 6.7) | 26 |
| Q7 | Street-wall finish over the RC parapet; a canopy at the gate? | A stone-faced parapet + open rail | 05, 17, 19, 22 |
| Q8 | A gate onto the footpath? | No, until F7 | 11, 26 |
| Q9 | Prayer place (Q12)? | The NE living corner with sheers, plus private mats in the master (14.4, 4.75) and the grandparents' room (16.0, 4.5) | 06, 08, 13, 26 |
| Q10 | A screen between kitchen and living (Q10)? | No (rule 1.3); hood + make-up air | 13 |
| Q11 | Keep the option to merge the children's rooms later? | Yes (wall u 11.1 non-bearing; Q15 stays "no") | 24 |
| Q12 | Does `store-s`, reached through the laundry, count as "separate"? | Yes | 07 |
| Q13 | A platform lift from `t-low` to the lawn? | No; stated as a limit | 12 |
| Q14 | The cozy seat: TV or valley view? | TV on the screen | 08, 28 |
| Q15 | A direct stair from `balc-e` to `t-low` (round 30)? | No; the route of about 48 m stands | 26 |
| Q16 | Size: 552 m² (faces) or 510 m² (grid)? | Report both | 21 |
| Q17 | Garage 53.0 m² clear, against ~55–60 m²? | Report both figures | 28 |
| Q18 | Still pending: a second lower WC; upward extension | No / no; confirm | 20, 24 |

## 7. Facts to confirm before construction

These refine C10 §5.

| # | Fact | Decides |
|---|---|---|
| F1 | Geotechnical investigation: rock, μ, frost depth, groundwater, Vs30 | STR-02 route; PW-N toe; the trough; footings |
| F3 | Sewer and its invert, or a downhill easement | MEP-05, WAT-02 |
| F4 | Gas main | SAF-03, Q1, MEP-01 |
| F5 | Permit regime, building line, basement rule, which area counts | REG-01/02, VEH-02 |
| F6 | Road survey (the edge at 1677.51–1677.57 is TIN-inferred), restraint and sight-splay rules | WAT-01, ARR-02, GEO-03 |
| F7 | Footpath ownership and easement | ARR-05, REG-04 |
| F8 | North neighbour's wall and footing; piling-rig clearance | GEO-01/02 |
| F9 | Snow load and drift | ENV-04, roofs |
| F10 | Rock faces west of the road | garage west wall |
| F11 | Site confirmation; a denser survey | every height |
| F12 | Lift supplier | CIR-02 |
| F14 | Percolation test (new) | WAT-10 |

## 8. Checks to add or repair

Each failing check blocks presentation (rule 8.1), and each needs a test that fails on C11 as reviewed.

1. **Guards.** Every edge of every surface, stair, dig and void, against the highest surface below it. Exempt only walls ≥1.1 m high. Road edges included. Fill `missing`; fail at a drop ≥0.6 m. Guards become shared elements.
2. **Route continuity**, road → lawn: each leg shares ≥1.2 m of edge, levels within 20 mm. Stair widths measured between wall faces.
3. **Door clearances.** The door width plus 0.9 m on each side is free of risers, columns, fixtures and tanks; every door has an approach ≥0.8 m. Columns in `_solids()`. Garage openings kept free.
4. **Support.**
   - Openings >1.0–1.2 m are not bearing unless a beam spans them.
   - Bearing lines are filtered by level.
   - Every beam end has a column, a beam, or ≥0.6 m of solid wall.
   - Footings ≤ zg − 0.8.
5. **Wall thickness against retained height:** ≥0.45 m above 0.3 m retained; ≥0.50 m above 3 m.
6. **Eccentricity** per storey ≤0.1 L.
7. **Fill** ≤1.0 m under every slab, paving and stair; earthworks complete.
8. **Water.**
   - All surfaces, including the roof, canopies and stairs.
   - Each outlet inside its own surface.
   - Inflow from neighbouring surfaces.
   - Full door widths.
   - Outdoor floors ≥0.15 m below FFL at walls.
   - Crests above the road.
9. **Services.** Water-holding rooms bunded; a duct ≤6 m from every windowless room; risers big enough for their contents.
10. **Sightlines:** sofa → hall; wudu seats; WC bowl fronts.
11. **§7.12** covers retaining elements and the windows facing them.
12. **Frames** ≥0.15 m from columns.
13. **Ledger:** "Done" only with a measured test; the comparison table and sun claims recomputed.
14. **0110-r2 register.**
15. **§7.22:** both area measures and a height table.
16. **Label collisions:** every text item.

## 9. Index of the 28 reviews

| NN | Specialty | File | Prefix | Top finding |
|---|---|---|---|---|
| 01 | Structure: load path | [01](01-structure-load-path.md) | STR | No v 13.0 beam at 1677.50 |
| 02 | Seismic, lateral | [02](02-seismic.md) | SEI | Eccentricity about 4.5 m; sliding FS about 0.75 |
| 03 | Geotechnics | [03](03-geotech-earthworks.md) | GEO | PW-N toe 0.8 m below formation |
| 04 | Water | [04](04-water-drainage.md) | WAT | Road water down the stair |
| 05 | Access, outdoor stairs | [05](05-site-access-external-stairs.md) | ACC | Walk dead end; road edge unguarded |
| 06 | Circulation | [06](06-internal-circulation.md) | CIR | No spine or void guards |
| 07 | Rooms, owner rules | [07](07-rooms-and-owner-rules.md) | ROM | SH-E blocks the ensuites |
| 08 | Sun, daylight | [08](08-sun-daylight-views.md) | SUN | Lower floor darker; pergola +1 % |
| 09 | Thermal | [09](09-thermal-energy.md) | THM | None fully fixed; spec only notes |
| 10 | MEP | [10](10-mep-services.md) | MEP | Plant room 2.95 m²; risers too small |
| 11 | Life safety | [11](11-life-safety.md) | SAF | Guard check cannot fail; LPG |
| 12 | Accessibility | [12](12-accessibility.md) | ACS | Ensuite doors; walk dead end |
| 13 | Privacy, acoustics | [13](13-privacy-acoustics-family.md) | PRV | Walk at the children's glass |
| 14 | Landscape | [14](14-landscape-garden.md) | LND | Walk–loggia gap; lawn −24 % |
| 15 | Constructability | [15](15-constructability-cost-maintenance.md) | BLD | PW-N unbuildable; spoil tripled |
| 16 | Consistency | [16](16-consistency-boundaries.md) | QA | Column in the WC door; unguarded drops |
| 17 | Exterior | [17](17-exterior-architecture.md) | EXT | Character only in notes |
| 18 | Interior, heights | [18](18-interior-space-heights.md) | INT | Walk and loggia meet at a point |
| 19 | Vehicles | [19](19-vehicles-garage.md) | VEH | Tyre rack in the door; road-edge drop |
| 20 | Kitchen, bathrooms | [20](20-kitchen-bathrooms.md) | KB | SH-E; wudu bench blocks the shower |
| 21 | Planning | [21](21-regulations-neighbours.md) | REG | 552 m² at the faces; building line |
| 22 | Hazards | [22](22-hazards-resilience.md) | RES | The road held by two stacked walls |
| 23 | Indoor health | [23](23-indoor-health.md) | HLT | Ventilation still notes; CO₂ worse |
| 24 | Flexibility | [24](24-flexibility-lifecycle.md) | FLX | SH-E; partitions made bearing |
| 25 | Operations | [25](25-household-operations.md) | OPS | Bulk store behind the tanks |
| 26 | Brief fidelity | [26](26-brief-fidelity.md) | BRF | Lawn 74 → 57 m²; hayat open |
| 27 | Materials | [27](27-materials-durability.md) | MAT | PW-N overlaps the house wall |
| 28 | Owner-request fidelity | [28](28-owner-request-fidelity.md) | OWN | "Connections all possible": no; rule 3.1 |

## Addendum: status of the BLOCKER rows after the fix round (designer, 22 Nov 2026)

Written after this consolidation, by the designer, not by the reviewers; not yet re-reviewed. Details and evidence are in `../../design/989_2026-11-22_claude-c11/CORRECTIONS.md` (section "Fix round"); every check in `checks.json` passes after the round, and each strengthened check was shown to fail on the pre-fix design.

| Row | Status after the fix round |
|---|---|
| C11F-STR-01 | Done: MB-13.0 (400 × 650, u 2.0–18.0) on the v 13.0 columns; lintels MB-18, MB-1.1N, LB-18E, LB-15.75; glass no longer counted as wall in the checks. The column or pier at (12.6, 13.0) is left to the engineer. |
| C11F-STR-02 | **Open (engineer + owner).** North pile wall detached; west and core walls still integral. On the page as a decision with a recommendation. |
| C11F-STR-03 | Done: C-6.8/9.5 starts on LW-6.8 at 1673.60. |
| C11F-GEO-01 | Done: toes 1666.5 / 1664.5 / 1667.0, extended to u 16, caps 0.2 m below ground, stepping (5 segments). |
| C11F-GEO-02 | Done: piles on v 0.40, 0.2 m drained cavity (SPECIFICATION.md). The ensuite window is kept: the pile cap there (1671.8) is below its sill. |
| C11F-GEO-03 | Partly: W2 thickened to 0.35 m on a common base at 1673.0; the U-trough is specified, not detailed. |
| C11F-WAT-01 | Done: W2 to 1678.30; W4 top 1677.6 at the corner landing; hump and slot drain at the stair head (water table). |
| C11F-ARR-01 | Done: `walk-e`; route check road → … → lawn passes. |
| C11F-ARR-02 | Done: RC vehicle parapet + rail along W2. |
| C11F-VEH-01 | Done: tyres high on the north wall. |
| C11F-CIR-01 | Done in plan: 0.15 m spine on every floor; the road void labelled with guards. The extra section at u 8.7 is not drawn. |
| C11F-ROOM-01 | Done: 2.1 m bookcase screen with the TV opposite the hall opening. No sofa → hall ray test was added. |
| C11F-KB-01 | Done: SH-E at R(11.0, 2.4, 11.4, 3.0); both doors clear (checked); seated ensuite with a true Ø1.5 m circle over the level shower. |
| C11F-KB-02 | Done: bench and trough from v 6.15, a 1.0 m landing at the shower door. |
| C11F-SAF-01 | Done: `guards()` rewritten with an independent re-sampling. It found 20 unguarded points on the pre-fix design and 0 now. Guards are not yet modelled as separate elements. |
| C11F-SAF-02 | Done: guards on the roof terrace, terrace lip, pergola void, loggia, garden terrace, green-roof joint and every site wall ≥0.6 m (237 m). |
| C11F-SAF-03 | Done: no gas stored below road level; LPG cage in the open-air north strip at road level. |
| C11F-OPS-01 | Done: two 0.7 m slim tanks and the booster along the west wall, leaving a 0.9 m passage to the bulk store. |
