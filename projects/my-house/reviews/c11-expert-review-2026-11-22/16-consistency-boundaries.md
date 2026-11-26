# C11 review 16: consistency, geometry and boundaries (QA)

All figures are `measured` unless marked. `checks.json` reproduces exactly from the code (0 differences in 68 rules). The terrain is a 27-point TIN (inferred).

## Summary

1. All 13 C10 findings are handled: 8 fixed, 5 partly. Garage, master strip, court, stairs and bedroom windows now agree across design.py, plans, sections and 3D.
2. Column C-6.8/9.5 fills the lower WC doorway completely. No check tests columns against doors or furniture.
3. The guard check cannot fail. It leaves 12.3 m of roof-terrace edge (3.9 m drop) and three more edges (1.7–3.6 m drops) unguarded.
4. Pile wall PW-N has a flat top at 1677.0 on ground that falls to 1671.3. It overlaps the house wall by 0.225 m and blocks the ensuite window.
5. The support and wall-over-wall checks ignore openings. The road south wall stands on 7.0 m of glazing with no beam.

## Scorecard

SCORECARD: fixed=8 partly=5 not_fixed=0 worse=0 new_blocker=2 new_major=3 new_minor=4

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| QA-01 `gs-court` | fixed | 3 × 8R of 150 mm. Each flight runs 2.38 m, which is what it needs. 1.5 m landings to `walk-s` 1670.00 | Clear width: N07d |
| QA-02 window into a void | fixed | Window deleted. Porch dug to 1673.60, RC-0, door under the porch | — |
| QA-03 forecourt edge | fixed | W1 (3.87 m) guarded from u −4.57 to −0.33, open at the stair head | Small gaps: N09 |
| QA-04 garage on nothing | fixed | Road plate 132.9 m²: 43.8 on walls, 88.3 spanning, 0.0 on nothing | Beam: N04 |
| QA-05 master void | fixed | Lower north wall on v 1.1 for u 9.4–18. Guest north window deleted | Text: N07a |
| QA-06 wall over no wall | partly | Office and road south wall now on the grid, columns and LB-13.0 added. But 7.0 m of the road south wall sits over main-floor openings, with no beam | N04 |
| QA-07 retaining walls not drawn | partly | 44 derived walls plus elements appear on plans, sections and 3D. Plans give no top or bottom levels. In the sections, the storeys' buried walls are thin lines: lower u 4.6 (about 3.4 m), core u 6.8 and v 7.3 (about 3.6 m) | Write top/bottom levels on the plans. Draw the buried walls at their thickness |
| QA-08 road stair | fixed | 12R × 164 + 12R × 158 mm, 320 mm goings, landing at 1675.50, 1.40 m between W2 and W3 | — |
| QA-09 soil at the boys' room | fixed | Highest surface in front of the windows: boys +0.42, girls +0.00 (sill +0.90) | — |
| QA-10 checks.py | partly | Now samples 0.3–2.0 m out, on all levels and kinds. New pass-by-construction paths | N02–N05, N09 |
| QA-11 v 17.42 margin | partly | Platforms stop at 17.12, stairs at 17.27. RW-W4 (0.30 m on v 17.27) has its outer face exactly on 17.42 (0 mm margin), so its toe crosses the setback | Move W4 and the stair band 0.15 m north |
| QA-12 sections | partly | Invented posts are gone. New cuts at u −1.8 / 5.6 and v 16.6. The dug hatch is still drawn over rooms. F–F omits the lift pit | N06 |
| QA-13 raised slab, "65 m²" | fixed | Lounge east suspended. Worst fill 0.90 m. Terraces 64.5 m², so "65" is correct | — |

## Part B: new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| QA-N01 | BLOCKER | Lower `lav`→`wc-l` door (u 6.8, v 9.05–9.75) | C-6.8/9.5 (0.35 m) sits wholly in the 0.7 m opening: 0.1225 m² overlap, the whole column. It also takes 75 mm off the main kitchen opening | Stop the column at 1673.60 on a new beam LB-6.8 (u 6.8, v 7.3–10.95, 300 × 500) |
| QA-N02 | BLOCKER | Roof terrace, south terrace, loggia | Unguarded drops of 1.7–3.9 m. §7.7 cannot fail | Add 1.1 m guards; rewrite `guards()` |
| QA-N03 | MAJOR | PW-N, v 0.85, u 0–13.2 | Top fixed at 1677.0 while the ground falls 1677.22 → 1671.34. Its body overlaps the house wall by 0.225 m (2.17 / 2.97 / 1.49 m² on the three plans). The main ensuite window (u 10.0–10.6, sill 1675.2) opens into it | Re-line the piles and step their top |
| QA-N04 | MAJOR | Road south wall, v 13.0 | Stands on 7.0 m of main-floor openings with no beam at 1677.5. Between C-6.8 and C-11.1 only 0.9 m of the 4.3 m is solid | Add MB-13.0, and make the checks subtract openings |
| QA-N05 | MAJOR | Columns 0.45 m in 0.20–0.40 m walls | Clash with 10 pieces of furniture and 3 openings | Move the openings and furniture; add the columns to `_solids()` |
| QA-N06 | MINOR | sections.png | F–F leaves out LIFT-PIT and LIFT-OVR, although CORRECTIONS cites F–F for them. Rooms are hatched. cs-f1 is missing from the court (main) plan | Handle MultiPoint crossings. Require every element a cut crosses to be drawn |
| QA-N07 | MINOR | index.html, notes, checks.json | Five texts disagree with the geometry | See details |
| QA-N08 | MINOR | Bins R(0,0.05,2.4,1.05) | Overlap the garage wall (0.48 m²) and PW-N (1.02 m²). They stand on ground at 1676.05–1676.62, 0.85–1.42 m below the forecourt, with no access drawn | Move them to the forecourt, R(−2.6,1.4,−0.4,2.4) |
| QA-N09 | MINOR | checks.py | More lenient code paths and small guard gaps | See details |

## Part B details

**QA-N01.** The column spans v 9.325–9.675 inside the WC door at v 9.05–9.75. That leaves 0.275 m and 0.075 m beside it, so nobody can pass. `doors.clear.lower` says "blocked: none" because `_solids()` counts furniture only. The alternative fix is a 0.6 m door at v 8.72–9.32 with the column shifted to v 9.5–9.85.

**QA-N02.** In `checks.guards()`, `missing = []` is never appended to. Edge points within 0.30 m of any footprint are skipped, and a slab one floor up (`t-south` over the loggia) counts as "the surface outside". My own edge sampling finds:

| Edge | Where | Length | Drop |
|---|---|---|---|
| `deck-r` east | u 18.0, v 6.2–13.0 | 6.8 m | 3.9 m |
| `deck-r` south | v 13.0, u 12.6–18 | 5.4 m | 3.9 m |
| `t-south` over the court stair | v 16.0, u 4.6–7.8, plus the return on u 7.8 | 3.6 m | up to 2.38 m |
| `t-south` at the pergola void | u 15.4, v 13.25–15.2 | 2.0 m | 3.6 m into the loggia |
| Loggia front | v 16.0, u 15.4–18 | 2.6 m | 1.72–2.48 m |

The road plan draws no guard on the roof terrace, yet ARR-04 and SAF-02 are marked done. *Fix:* put guards on these edges. Rewrite the check so it takes the lowest surface 0.3–0.6 m outside each walkable edge, ignores slabs above, and compares against the **drawn** guards.

**QA-N03.** Sections D–D and F–F draw PW-N 2.9 m and 4.5 m above the ground. §7.12 tests only the derived `swalls`; it builds `walls_near` and never uses it. *Fix:*
- Centre the piles on v 0.575, so their face is at 0.80 and a 50 mm drainage board fits against the house's 0.85 face.
- Step the capping beam: 1677.2 at u 0, 1674.9 at u 4, 1672.5 at u 10, 1671.3 at u 13.2.
- Test retaining elements in §7.12.

**QA-N04.** The main south wall has sliders at u 7.1–9.1 and 9.5–10.9. Check §7.2 reports 0 m because `storey_walls()` treats the whole outline, glass included, as wall. The same blindness counts three walls as continuous: LW-12.6 (58 % open), LW-8.2 (54 %) and RW-12.6 (51 %). MB-12.6 (span 6.8 m) ends on a 0.3 m pier at (12.6, 13.0), which loads LB-13.0 mid-span. *Fix:*
- MB-13.0, 300 × 600, u 4.6–12.6 at 1676.9–1677.5, on C-4.6, C-6.8 and C-11.1.
- A pier or column at (12.6, 13.0).
- Subtract openings longer than 1.2 m in `bearing_lines()` and `wall_over_wall()` unless a beam is listed over them.

**QA-N05.** Overlaps in m²:

| Item | Overlap (m²) |
|---|---|
| Kitchen sink run | 0.034 |
| Each children's wardrobe (C-11.1) | 0.034 |
| Boys' bed / girls' bed | 0.024 each |
| Store shelves | 0.034 / 0.013 |
| Loggia bench | 0.034 |
| Office desk / boiler | 0.011 each |

Openings: the dining slider ends at 10.9 against the column face at 10.875 (25 mm), the office window 25 mm, the kitchen opening 75 mm. *Fix:*
- Dining slider to u 9.5–10.8, office window to u 9.7–10.8.
- Sink run u 5.45–6.5.
- Wardrobes and beds 0.15–0.25 m clear of the column faces.

**QA-N07.**
- (a) Decision 19 says the grandparents' north part is "a sitting area with a window to the garden". No lower window exists at v 1.1–3.3, and the beds stand at v 1.25–3.25. STR-02's east window (u 18, v 1.3–2.7) is not drawn.
- (b) The rule 5.1 evidence says 3.6 m; the note and the claim say 4.4 m.
- (c) The RC-0 note says it holds 0.8–1.0 m of ground; the derived wall is 1.15 m.
- (d) The court stair is called "1.27 m clear". SW-6/7/8 are centred on v 16.0, which leaves 1.12–1.15 m before handrails.
- (e) The "147 m² east garden" includes the garden-terrace slab (27.5 m²) and the lawn stair (8.2 m²). Lawn plus tree bank is 92.8 m².

**QA-N09.**
- `wall_over_wall` treats every main-wall point outside the lower footprint (shrunk by 0.05 m) as founded. My re-test found nothing hidden, but the check should test ground or a carrier.
- §7.6 computes the internal stair from constants, not from the drawing.
- The landing test skips `rs-head`, and the court stair's top landing (`court`) is not a terrace id.
- The guard has gaps on W1 at u −3.08…−2.87 and −0.33…0, and at u 4.32–4.6 on v 16.0, where the drop is about 1.6 m.

## What C11 gets right

- One element list plus one derived site-wall list drive the plans, sections, support sheet and 3D. All 52 required ids are drawn, and none is invented.
- All 11 text claims recompute within tolerance, and `checks.json` matches the code exactly.
- No slab region stands on nothing (0.0 m² unsupported), and fill under ground-bearing slabs is at most 0.90 m.
- Every outdoor flight's run equals its need (3.52 / 2.38 / 2.24 m), and every stair ends exactly at its owner level.
- Everything, walls included, is inside the parcel and the envelope (I re-tested the derived walls at 0.30 m, which check 13 does not).

## Out of scope

- Structure: MB-12.6 → pier → LB-13.0 mid-span. The 0.20 m LW-7.3 and 0.25 m core retain about 3.6 m.
- Privacy: the court stair passes 0–0.4 m from the boys' window.
