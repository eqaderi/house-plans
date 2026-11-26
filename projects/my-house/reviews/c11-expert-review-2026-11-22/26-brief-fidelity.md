# 26 · Brief fidelity and design history (BRF), C11

## Summary

1. No C01–C09 rejection recurs. The lower floor gets its outdoor entrance (round 23), and the master balcony is private (I30).
2. The play lawn shrank from 74 to 57 m² (largest rectangle 4.0 × 7.5 → 3.2 × 6.8 m), and Q4 quotes neither *"flat outdoors"* nor *"level, not steps"*.
3. The *hayat* is no perimeter: the gate is a text label, and the south is open at grade to the footpath for ~10 m.
4. Owner-unsized rooms grew while owner-sized rooms shrank: master suite 37 m² clear (> living 34), grandparents 28 m² (B: 17.5), children 19.0 / 18.5 m² (owner's 20.6).
5. The workbench is a 1.9 m sliver, the plant room shrank to 3.8 m² (B: 7.44), and the 0110-r2 defect list is no longer tracked.

## Scorecard

`SCORECARD: fixed=2 partly=5 not_fixed=1 worse=2 new_blocker=0 new_major=4 new_minor=4`

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| BRF-01 hayat, gates | partly fixed | measured: the gate is only a text label (`design.py` l.302). There is no gate or street-wall element; W2's top is 1677.40 (road level). The south is open (N01). | Draw the gate as an element; raise W2 (1.0 m stone + 0.8 m lattice, top ≈1679.2); close the south (N01) |
| BRF-02 study/play | partly fixed | Asked as Q3, with the default "homework at the bedroom desks". Those desks are 0.8–1.0 m (B: 1.4 m). Owner's B: "QUIET OFFICE / GAMING" 9.61 m²; C11 office 9.8 m² clear. | Reword Q3: "the office doubles as study/gaming, as in your B". Desks 1.2–1.4 m (N03) |
| BRF-03 lower floor reachable from outside | **fixed** | measured: court → 3 × 8 risers of 150 mm → `walk-s` at 1670.00 → loggia → lounge slider (16.7, 10.95) | — |
| BRF-04 terrace → garden stair | partly fixed | inferred: terrace → court → 24 R → walk → loggia → `t-low` → 16 R → lawn is about 48 m, all easy risers (C10: ~30 m, steep). Q9 "No" omits round 30 (*"towards east or south, where the stairs outside can reach it"*). | Put round 30's words in Q9; give the direct-stair numbers (24 R from `balc-e` to `t-low`) |
| BRF-05 workshop sliver (C04-A) | **not fixed** | measured: bench R(2.8, 8.84, 4.7, 9.44) is 1.9 × 0.6 m (C10: 4.7 m long). The 0.96 m standing zone is also the LC300's door zone (v 7.88–8.84). | Bench u 0.6–4.7 (4.1 m). Bikes flat-hung on the north wall at v 1.25–1.55, with car 1 moved 0.2 m south (shared door zone 1.57 m) |
| BRF-06 master balcony reachable from road | **fixed** | measured: `balc-m` R(18, 2.6, 19.85, 6.2), with a 2.0 m screen across its full width at v 6.2 | — |
| BRF-07 0110-r2 defects | partly fixed | below | below |
| BRF-08 level lawn | **made worse** | measured: lawn 74.4 → 56.8 m²; largest rectangle 4.0 × 7.5 → 3.2 × 6.8 m (R(21.8, 1.0, 25.0, 7.8)). The lawn stair R(20.6, 3.4, 21.8, 10.28) now cuts into the lawn. | Restore ≥74 m² and a ≥4 × 7.5 m play rectangle. Offer Q4 with three options: (a) as now; (b) lawn to the setback, ~110 m², with a 1.6–2.3 m wall (C10 numbers); (c) 14's one level |
| BRF-09 EV and prayer mis-recorded | partly fixed | measured: EV box drawn at (6.72, 5.0). `design_brief.yaml` still says "EV charging: unknown" (l.716) and "Prayer … unknown" (l.910). DRW-04 not done. | Record both as `inference` (`method: agent:<tool>`) for the owner to confirm |
| BRF-10 guest bed; plant room | **made worse** | measured: fold bed drawn (fixed). Plant room 6.1 m² on the grid in C10, now 3.8 m² (3.0 m² clear, 1.4 m deep). Owner's B: 7.44 m² "REPLACEABLE PLANT" (rule 6.7). | Merge plant and `store-r` into R(4.4, 11.6, 9.4, 13.0): equipment in a row with 0.6 m in front; or put the cylinder and MVHR in the bulk store |

### BRF-07 details

- **I12/I22 (laundry): fixed.** 4.8 m² clear plus separate stores. My C10 "≥12 m²" was wrong (stmt-028); I withdraw it.
- **I14 (dining): fixed** (3.08 × 4.04 m clear, 8 chairs).
- **I26 (pantry): not fixed.**
  - Pantry door u 2.85–3.65 against the kitchen opening at u 5.6–6.7; pantry → fridge about 4.7 m (inferred; C10 ~5 m; CIR-05: ≤3 m).
  - Fix: kitchen opening at u 4.5–5.6, with the fridge moved to the south end of the west run.
- **I11 (prayer): partly fixed.**
  - Mats on the qibla (measured 0.0°), but wudu → mats is still about 13 m through the living room (inferred). The SE default respects rule 3.1.
- **I15 (noise): partly fixed.** The table at R(5.4, 13.75, 7.2, 14.65) still overhangs the boys' room east of u 6.8 by 0.4 m plus its chairs. Shift it to u 4.7–6.5.

## Part B: new problems

| ID | Sev. | Where | Finding | Correction |
|---|---|---|---|---|
| BRF-N01 | MAJOR | court stair band, u −0.4…9.7, v 16.0–18.42 | The *hayat* is open at grade to the shared footpath, so the road gate can be walked around | Railing or gate line inside the south boundary |
| BRF-N02 | MAJOR | main `master`, lower `guest` | Owner-unsized rooms bloated; master suite > living | Shrink to the owner's B sizes; give the area to storage or the office |
| BRF-N03 | MINOR | lower `boys`, `girls` | Below the owner's 4.3 × 4.8 m clear; desks and wardrobes below B | Regain depth; B furniture sizes |
| BRF-N04 | MAJOR | `checks.py` / `checks.json` | The 0110-r2 register (I01–I30) is dropped, so rule 6.7's "fix the defects" goes unchecked | 30-row table with a measured status |
| BRF-N05 | MAJOR | `index.html` decisions | Defaults misstate the drawing or omit the owner's words (Q4, Q7, Q9, hall) | Rewrite as below |
| BRF-N06 | MINOR | main `tanks` → `bulk` | Bulk store reached through the tank room on the north side, like C04-A's "strange" store | Door from the hall; name it the service room |
| BRF-N07 | MINOR | main `kitchen` island | "4 stools" on a 1.4 m island at 0.45 m centres | 3–4 seats at 0.6 m |
| BRF-N08 | MINOR | page summary | Gross 510 m² (C10 459) is not set against the C08 rejection (525–553 m²) | One line of context |

## Part B details

**BRF-N01**
- Source: round 23 *"You open it. You're in a perimeter"*; f-priorities (an `inference`).
- Evidence (measured, `zg`):
  - Ground at v 17.2 / 18.4: 1673.38 / 1673.34 (u 0), 1670.70 / 1670.56 (u 8). The treads lie within −0.34…+0.15 m of it, and guards come only at drops ≥0.6 m.
  - So anyone on the footpath can reach the court and every main-floor slider without passing the gate. The Q8 default ("no fence") cancels Q7.
- Correction:
  - A 1.2 m open railing inside the parcel on v 18.3, from W4 (u ≈ −1.4) to the garden-walk wall (u ≈ 10). It stands ≥2.5 m from the children's glass, so rule 4.8 holds.
  - A lockable gate at u ≈ 0 only if the owner wants footpath access (Q8). Inside the parcel, it does not depend on who owns the footpath.

**BRF-N02**
- Source: stmt-021 *"living room is too small"*; stmt-022 *"We don't want big unnecessarily"*; rule 7.4.
- Evidence (measured): master 28.1 + ensuite 5.4 + dressing 3.5 = 37.0 m² clear, against living 34.0 (C10 master 24.2 m² on the grid). Grandparents 28.2 + 5.5 + 3.0 = 36.7 m² (program 11, B 17.5). The master's L-leg R(11.4, 3.4, 12.6, 7.3), about 4.7 m², is a passage.
- Correction: master about 22 m² (B: 22.1), with the L-leg as a 0.6 m wardrobe wall plus a 1.0 m passage. Grandparents: default to a store or linen room in R(13.4, 1.1, 18.0, 3.0) (≈8.7 m²), not to "keep".

**BRF-N03**
- Evidence (measured): 4.14 × 4.59 and 4.05 × 4.59 m clear, against B's 4.3 × 4.8 m clear (CONSOLIDATED promised "rooms keep their size"). One 2.0 m wardrobe and 0.8–1.0 m desks per room, against B's two 1.5 m wardrobes and two 1.4 m desks.
- Correction: LW-10.95 to v 10.75 for u 6.8–15.4 (4.79 m clear depth; `hall-l` 3.45 m on the grid); two 1.2–1.4 m desks and 2 × 1.2 m wardrobes.

**BRF-N04**
- Source: rule 6.7 *"fix the defects in `independent-review-0110-r2`"*.
- Evidence: `checks.py` l.532 only asserts that no defect is "marked fixed"; none is listed. Known states: I05 (gates), I11 and I15 partly fixed; I20 (plant) made worse; I26 (pantry) not fixed.
- Correction: a check printing I01–I30 as fixed / partly / not, each with a measured test or `not_checked`.

**BRF-N05**
- Q4 hides the 74 → 57 m² change and omits *"flat outdoors"* / *"level, not steps"*. Q7 says "as drawn", but nothing is drawn. Q9 omits round 30.
- "Accept the 10.6 m hall" asks the owner to waive hard rule 2.2 without quoting round 31 (*"not building a hospital with long hallways"*).
- Correction: each decision gives the owner's words, the change from C10 in numbers, and the alternatives.

**BRF-N06–N08** (MINOR)
- N06: hall → `tanks` (a 2 × 8.4 m strip) → `bulk`, on the north side; C04-A was rejected for a "strange" north store (rule 6.3). Merge `tanks` and `bulk` into one named service room, so no store is reached through another room, and tell the owner it holds the garage up (stmt-027).
- N07: three stools at 0.45 m centres plus one at the island end give 2–3 comfortable seats (rule 1.4 asks for 3–4). Use a 1.8 × 0.8 m island with 3 stools at 0.6 m plus 1 at the end (reviewer 20 checks the fit).
- N08: gross 133 / 207 / 170 = 510 m². Say that 28 m² of it is the buried service room, and that C08 was rejected at 525–553 m² with ~50% cover where C11 covers 40%.

## What C11 gets right

- No C01–C09 rejection reason recurs (rules 1.1, 2.1, 2.5, 3.1–3.3, 4.2, 5.1, 6.5 hold).
- The lower floor's outdoor entrance (round 23): 24 risers of 150 mm to the loggia.
- Laundry and stores exactly per stmt-028; the master balcony is private (I30); dining seats 8 (I14).
- The owner's levels, the 24R core with REST 1.40, the wudu cluster and the tea bar are kept.

## Out-of-scope notes

- Stools against the kitchen hall opening: reviewer 20. Grandparents' slider onto a publicly reachable `t-low` until N01 is closed: reviewer 13.
