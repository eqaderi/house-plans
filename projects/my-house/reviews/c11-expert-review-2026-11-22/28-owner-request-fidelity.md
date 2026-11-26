# 28 · Owner-request fidelity · C11 review (prefix OWN)

This reviewer is new, so Part A audits the 108-row `CORRECTIONS.md` ledger. Nothing in C11 is engineered or code-compliant. Heights come from the TIN (`inferred`).

## Summary

1. **"Garage stays on top of what?"** Answered. A service room is dug under the whole garage, and 0 m² stands on nothing (`measured`).
2. **"Main floor stays on top of what?"** Mostly answered. The 0 m mid-span result counts the glazed v 13.0 façade as a wall (OWN-N03).
3. **The court and the stairs.** The bigger court and the road-side L-stair are delivered (40.6 m² open + 4.2 m² porch). Every flight is easy.
4. **"Connections are all possible": no.** The garden walk touches the loggia only at the point (15.4, 16.0) and dead-ends (OWN-N01, BLOCKER).
5. **Rule 3.1 is breached.** The cozy sofa looks straight down the hall (OWN-N02, BLOCKER). Of the 62 "Done" rows, 6 are overstated or false.

## Scorecard

`SCORECARD: fixed=56 partly=45 not_fixed=1 worse=6 new_blocker=2 new_major=3 new_minor=5`

(How the ledger statuses map: verified → fixed. Honest "Partly" → partly. Honest "Not done" (DRW-04) → not_fixed. Overstated or false → worse.)

## Part A: ledger audit, all 108 rows

### Verified (56 rows)

The claim is true in `design.py`, `checks.json` and the drawings.

- **Structure:** STR-01, STR-02, STR-04.
- **Ground:** GEO-01, GEO-02 (forecourt fill 1.64 m to finished level, so about 1.04 m under the 0.6 m build-up; borderline, accepted), GEO-03, GEO-04 (4.22 m), GEO-06.
- **Water:** WAT-02, WAT-03, WAT-05, WAT-08.
- **Arrival:** ARR-01. The deviation is disclosed: 40.6 m² instead of 51.6 m², with the walls inside the parcel. ARR-03 (16 × 149 mm), ARR-04, ARR-06.
- **Garage:** VEH-01, VEH-02, VEH-04.
- **Circulation:** CIR-01, CIR-02, CIR-04 (store only 0.92 m clear wide, but it is what was asked).
- **Rooms:** ROOM-02, ROOM-04, ROOM-05, ROOM-07, ROOM-08, ROOM-09, ROOM-10, ROOM-11, ROOM-12, ROOM-13 (laundry 4.8 m² clear, which meets stmt-028).
- **Kitchen and baths:** KB-01, KB-02, KB-03, KB-06.
- **Services:** MEP-02 (SH-W move disclosed), MEP-03.
- **Sun:** SUN-01, SUN-02, SUN-04.
- **Thermal:** THM-01, THM-03.
- **Safety and access:** SAF-01, SAF-02, ACS-02.
- **Privacy:** PRV-01, PRV-02.
- **Garden and operations:** LND-01, OPS-01, OPS-02, OPS-03, OPS-04.
- **Flexibility and checks:** FLX-02, DRW-01, DRW-02.

### Honest "Partly" (45 rows)

The ledger already says these are part done or notes only, and that is accurate: STR-06, STR-08, STR-09, STR-10, GEO-05, WAT-01, WAT-04, WAT-06, WAT-07, WAT-09, WAT-10, ARR-05, ARR-07, VEH-03, VEH-05, CIR-03, CIR-05, ROOM-01, ROOM-03, KB-04, KB-05, MEP-01, MEP-04, MEP-05, MEP-06, MEP-07, SUN-03, SUN-05, THM-02, THM-04, SAF-03, SAF-04, SAF-05, SAF-06, ACS-01, PRV-03, LND-02, LND-03, LND-04, EXT-01, EXT-02, EXT-03, EXT-04, EXT-05, FLX-01.
### Honest "Not done" (1 row)

DRW-04. The reason given is valid: correcting the brief needs an interview session the owner confirms.

### Overstated or false (6 rows)

| Ledger ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| **C11-ARR-02** | **false** | The claim is "garden walk at 1670.00 to the loggia". `measured`: `walk-s ∩ loggia` = POINT(15.4, 16.0), zero length. Section E–E ends the walk at u 15.4 with wall SW-38 and a 1.7 m drop. The girls' SE wall corner (outer faces at u 15.65 and v 16.0) blocks the corner. `lower.png` draws a closed brown wall and a guard there. No door on v 15.75 opens off the walk. | See OWN-N01. |
| **C11-ROOM-06** | **overstated** | The 1.1 m shelf R(13.3, 8.2, 14.0, 9.6) stands 0.25 m in front of the TV R(12.7, 8.75, 13.05, 9.95). It covers only v 8.2–8.65 of the hall opening (v 7.45–8.65), so 0.75 m stays unscreened. The sofa's west arm runs v 6.35–8.95, and the line v 7.45–8.2 from it runs unobstructed down the hall to the entry (`measured` geometry; the view itself is `ai_judgment`). | See OWN-N02. |
| **C11-STR-07** | **overstated** | The row asked to "suspend … every outdoor-stair base". Earthworks show fill of 2.01 m under the lawn-stair top landing (1669.98), 1.28 m under `ls-l1` and 1.77 m under `walk-s`, all ground-bearing between site walls (`measured`, `checks.json` earthworks). | Suspend `ls-top`, `ls-l1` and `walk-s` on walls/FW lines, or cap compacted fill at ≤1.0 m with stepped walls. |
| **C11-STR-03** | **overstated** (minor) | The claim is "openings clear". The dining slider spans u 9.5–10.9, but the face of column C-11.1/13 (0.45 m) is at 10.875, so they overlap by 25 mm. The kitchen window ends at 6.55 against the C-6.8 face at 6.575, leaving 25 mm with no frame zone (`measured`). | Dining slider to u 9.55–10.75; kitchen window to u 5.3–6.4. |
| **C11-STR-05** | **overstated** | The evidence is "§7.2: 0 m mid-span". But `structure.storey_walls()` returns the footprint outline, so glazed façades count as walls. The road-level south wall (u 2.0–12.6, v 13.0, 0.40 m, 3.3 m tall) stands over the 2.0 m kitchen slider and the 1.4 m dining slider with no beam at road-slab level. Beam MB-12.6 ends at (12.6, 13.0) on a 0.30 m pier between the dining window (to 12.4) and the living slider (from 12.7) (`measured` from code and geometry). | See OWN-N03. |
| **C11-DRW-03** | **overstated** | The claim is "notes recomputed". The `index.html` comparison table lists the C11 east garden as **151 m², "unchanged"**, while rule check 4.7 says **147 m²**. Check §7.20 passes only because it does not test the comparison table. | Use one computed figure everywhere, and add the comparison table to §7.20. |

## Part B: owner's words and rules

### The owner's questions, answered bluntly

| Owner asked (stmt-027/028/029) | Delivered? |
|---|---|
| "Garage stays on top of what?" | **Yes.** Main-floor rooms are dug under all 57 m² of it; support sheet 0 m² unsupported. |
| "Main floor stays on top of what?" | **Mostly.** 61 m² on dug ground, the rest on lower walls, the v 13.0 beam and RC-18L. The road storey's south strip rests on glass (N03). |
| Dig the area west of the court; stair at the far west against the road | **Yes.** F1 runs along the road boundary (0.30 m off it, behind W2). Court 40.6 m² open (+19%; +45% against C10's ~28 m² open). |
| Court → lawn/terrace stair "too steep … excavate" | **Yes for the stairs:** 3 × 8 × 150 mm and 2 × 8 × 149 mm. **No for the route:** it breaks at the walk (N01). |
| "Connections are all possible and nothing is hard" | **No.** N01. |
| Laundry not 12–14 m² (stmt-028) | **Yes:** 4.8 m² clear, with separate stores. |
| Fan out reviewers to check it (stmt-029) | In progress (this review). |

### Rule-by-rule result

**Pass, verified (`measured`):**

- 1.1–1.5 (kitchen 15.6 m², pantry 4.3 m², 4 stools, dining fits 2.8 × 4.0).
- 2.1, 2.3, 2.4, 2.5; 3.2, 3.3 (5.19 m clear).
- 4.2–4.10 except 4.11. For 4.8, my own `zg` test: ground in front of the bedroom windows is at most +0.56 m, below the +0.90 m sill.
- 5.1–5.4; 6.1–6.7.
- 7.2, 7.3, 7.5, 7.6, 8.1, 8.5. The C10/C11 comparison has orange outlines, but see DRW-03.
- Court-stair treads stay within −0.39 … +0.44 m of natural ground.

**Breached:**

- 4.11 (N01).
- 3.1 (N02).

**Open or at risk:**

- 2.2 (N04).
- 4.1, literal reading (N05).
- 2.6 detail (N07).
- 5.5 by clear area (N09).
- 7.1 annotations (N10).

| New ID | Severity | Where | Finding | Correction |
|---|---|---|---|---|
| OWN-N01 | **BLOCKER** | lower, `walk-s` R(9.74, 16.0, 15.4, 17.12) ↔ `loggia` R(15.4, 10.95, 18.0, 16.0) | The court → garden route is broken: the walk dead-ends and never reaches the loggia, `t-low` or the lawn (rule 4.11, stmt-027). | Extend the walk to R(9.74, 16.0, 17.0, 17.12) and open the loggia's south guard over u 15.7–17.0 (1.3 m). Carry the extension on FW-16.0 plus a wall on u 17.0 founded at about 1667.5; it stays inside v 17.42. Add a continuity check: outdoor surfaces from road to lawn linked by shared edges ≥1.0 m. |
| OWN-N02 | **BLOCKER** | main, living W wall u 12.6–14.0, v 7.3–10.0 | The cozy corner looks straight into the hall (rule 3.1, stmt-015), and the screening shelf blocks the TV. | Move the 1.1 m screen to R(13.3, 7.3, 14.0, 8.9) so it covers the opening, with entry around its south end. Keep TV R(12.7, 9.0, 13.05, 10.2) and leave 2.5 m in front of it free. Ray-test sofa → hall the way §7.17 tests WC pans. |
| OWN-N03 | MAJOR | road/main, v 13.0 u 2.0–12.6; (12.6, 13.0) | The answer to "what stands on what" relies on the glazed façade counted as a wall. | Add beam MB-13.0 (300 × 600, 1676.9–1677.5) on C-4.6/6.8/11.1. Add a column or a ≥0.9 m solid pier at (12.6, 13.0) for MB-12.6 (dining window to 11.5–12.0). Make `storey_walls()` subtract openings and rerun §7.1/§7.2. |
| OWN-N04 | MAJOR | main `hall` u 2.0–12.6 | Rule 2.2 is shown as "your decision" in the checklist. Rule 8.1 needs a pass; otherwise stop and ask *before* presenting. The hall is 10.6 m long, 1.45 m deep in front of the dining, with 7 openings off both sides. | Put it to the owner as an explicit question with a plan crop, or widen the hall into the dining (dining north wall line removed, sideboard on the east wall) so it reads as a room. |
| OWN-N05 | MAJOR | road, south façade v 13.0 u 2.0–9.4 | 7.4 m of the 10.6 m south façade holds a WC, a plant room and a store. Rule 4.1 names "stores … on the best façade" as a fail, and the entrance hall gets no south light. | Ask the owner (Q-new). If kept, state it on the page. Otherwise give the hall a 1.2 m south window by moving `store-r` under the stair landing. |
| OWN-N06 | MINOR | `index.html` "The idea" | The headline "45 m² arrival court" counts the covered porch, while CONSOLIDATED promised the owner 51.6 m². | Headline: "40.6 m² open court (+19%), plus a 4.2 m² porch; 51.6 was without wall thickness". |
| OWN-N07 | MINOR | main entry R(2.0, 9.5, 4.4, 13.0) | The door faces east into the kitchen's west wall. The route is two turns to the core; the checker says one. The door is visible only obliquely from the court. | Correct the 2.6 evidence text, and put a glazed side light at u 2.0, v 11.1–11.5. |
| OWN-N08 | MINOR | lower, boys/girls | The owner's 4.3 × 4.8 m is met on the grid; clear size is 4.14 / 4.05 × 4.59 m. | State both figures on the page (rule 7.6). |
| OWN-N09 | MINOR | road, garage | Rule 5.5 is ~55–60 m². The pass uses the grid (57.1); clear is 53.0 m². | Report the clear size, or move the riser out of the garage (+0.4 m²) and say so. |
| OWN-N10 | MINOR | `main.png` | "1.0 m CANOPY OVER THE SOUTH GLASS" runs over the column and the 3.00/3.20 dimensions, and "PRAYER ↙ QIBLA" is clipped by the mats. The label check tests room labels only. | Extend the collision test to all text and move these two notes. |

## Part B details

**N01.** The page promises *"24 easy steps … to the garden walk …, the loggia and the garden terrace."*

- `walk-s` meets `loggia` only at the point (15.4, 16.0) (`measured`).
- Ground east of u 15.4 is 1.6–2.0 m below the walk (`zg`).
- No door opens from the walk into the house.

So the 24 steps lead into a 6 m² dead end in front of the children's windows. That is the exact failure of stmt-027. The checker misses it because §7.5 tests each flight on its own, never whether the surfaces connect.

**N02.** C11 moved the hall opening north, because the dining took v 8.75 onwards, but left the shelf where the review had put it. The sofa's line at v 7.8 now runs about 15 m along the hall to the entry. Rule 3.1 is marked "designer's judgement", with no test.

**N03.** `structure.storey_walls()` returns the footprint outline, so glass counts as a bearing wall. `structure()` has no element at road-slab level on v 13.0.

## What C11 gets right

- The garage question is answered physically: a ground-bearing service room under the garage, and a support sheet showing 0 m² on nothing.
- It builds the owner's court idea: the dig, and the 12 + 12 L-stair against the road.
- Every outdoor flight is easy: risers 149–164 mm, goings 320–340 mm, landings and handrails on both sides.
- It follows stmt-028 and stmt-029: laundry 4.8 m², kitchen 15.6 m², dining for 8, safety doors only.
- The presentation meets rules 7.x and 8.x: the idea first, furnished levels plus the garden, 8 sections, 3D, the comparison view and the rule checklist.
- The ledger is mostly honest: 45 rows are marked "Partly".

## Out-of-scope notes

- **Privacy:** each child's only window faces the public court → garden stair and walk at 0–1.3 m.
- **Kitchen:** the island's east stool at (8.25, 10.8) sits in the kitchen → dining serving line.
- **Earthworks:** cut is up 74% (228 → 397 m³). Given stmt-012, show this on the idea page.
