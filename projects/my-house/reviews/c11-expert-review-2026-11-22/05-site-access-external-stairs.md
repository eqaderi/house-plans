# 05 · Site access, arrival and external stairs (C11)

Concept-stage review on the inferred TIN; nothing is engineered or code-checked. Stair criteria are `assumption` (CONSOLIDATED §7.5): riser ≤175 mm, going ≥280 mm, 2R+G 0.60–0.66, ≤16 risers per flight, landings ≥1.2 m, width ≥1.0 m (target 1.2 m), guards 1.1 m at drops ≥0.6 m.

## Summary

1. The stair geometry is right this time. Road stair 12 + 12 (164 / 158 mm, 320 mm goings, 1.40 m between wall faces), court stair 3 × 8 (150 / 340 mm), lawn stair 2 × 8 (149 / 320 mm).
2. **The outdoor route does not connect.** `walk-s` touches the loggia only at the point (15.4, 16.0) and ends in a 1.74 m drop. Court → garden is impossible outdoors (rule 4.11).
3. **The road edge above the road stair has no guard.** W2's top (1677.45) is 90–150 mm below the road edge, and the drop into F1/L1 is 1.76–2.10 m.
4. The court is 40.6 m² open + 4.2 m² porch = 44.8 m², against 51.6 m² in my zero-thickness geometry. Rule 4.10 is met.
5. Also: an unguarded 2.05 m bank above L1, water into both stair heads, and a lawn stair ≤1.05 m clear.

## Scorecard

SCORECARD: fixed=4 partly=8 not_fixed=1 worse=0 new_blocker=2 new_major=3 new_minor=3

## Part A: C10 findings

| C10 ID | Status | Evidence | Remaining correction |
|---|---|---|---|
| ACC-01 court→garden | **partly fixed** | `measured`: cs-f1..f3 are 8 × 150 / 340 mm, run 2.38 m each (matches the drop), landings 1.5 m, treads 0 to −0.40 m against `zg`. But the walk dead-ends (N01) | N01 |
| ACC-02 22-riser flight | **fixed** | `measured`: 12 × 164 + 12 × 158 mm, 320 mm goings (2R+G 0.648 / 0.637), corner landing at 1675.50 (walking line 1.42 m); bottom landing = court | — |
| ACC-03 full court | **fixed** (measured deviation) | `measured`: `court-w` 40.57 + porch 4.20 = 44.8 m² (C10 34.0, +32%). The 6.8 m² gap to 51.6 is the stair 0.30 m off the boundary, W3 0.35 m thick, F2 0.30 m north, W4 0.30 m thick. Only the stair's wedge stays undug | — |
| ACC-04 strip width / privacy | **partly fixed** | `measured`: band v 16.00–17.27 = 1.27 m; rooms keep 4.3 × 4.8 m. Eyes on cs-f3 are at 1671.5–1672.6, 0.25–1.27 m from the boys' glass (sill 1670.90); no planter or screen drawn | 0.4 m planter or 1.2 m slatted screen on v 16.0, u 8.9–10.7, outside the clear width |
| ACC-05 retaining walls | **partly fixed** | `measured` (`site_walls`): W1 3.87 m, W3 ≤2.79 m, W2 ≤1.92 m, W4 ≤2.23 m. RW-W2 top is below the road and RW-W4 is modelled too low (N02, N03). No road survey | N02, N03 |
| ACC-06 drainage | **partly fixed** | The court has a 1:60 fall, 2 gullies and an outfall. Both stair heads take water (N05) | N05 |
| ACC-07 lawn steps | **partly fixed** | `measured`: 2 × 8 × 149 / 320 mm, 1.2 m landings, relocated to R(20.6,3.4,21.8,10.28). Clear width ≤1.05 m (N04) | N04 |
| ACC-08 road-door step | **partly fixed** | `measured`: 1677.50 − 1677.47 = 30 mm, against ≤20 mm asked | Forecourt 1677.48–1677.49 for 1.2 m in front of the road door |
| ACC-09 entry door | **fixed** | Door on u 2.0, v 10.1–11.1, inside the porch R(0,9.5,2,11.6), about 3.5 m clear | — |
| ACC-10 apron / swept path | **partly fixed** | LC300 in bay 2 (note); delivery bay and swept path not drawn | Draw both; keep 1.5 × 1.5 m bollarded at the stair head |
| ACC-11 bins | **fixed** | Enclosure R(0,0.05,2.4,1.05) drawn | — |
| ACC-12 continuous outdoor route | **not fixed** | Lower floor → outside → road needs walk → loggia, which is missing; the garden is still a dead end | N01 |
| ACC-13 winter ice | **partly fixed** | Treads, lights and canopy are notes only. The bank south of L1/F2 is 0.8–2.05 m high (`zg`), so L1/F2 get no midwinter sun | Draw the canopy over L1 + F2 (about 4 × 1.6 m); L1 falls 1–2% to a channel |

## Part B: new problems

| ID | Sev | Where | Finding | Correction |
|---|---|---|---|---|
| ACC-N01 | BLOCKER | lower, `walk-s`/`loggia`, u 15.4 | Garden walk dead-ends; there is no outdoor court → lower floor → garden route | Extend the walk to u 18.0 into the loggia |
| ACC-N02 | BLOCKER | W2, road edge, v 11.6–17.12 | Unguarded 1.76–2.10 m drop from the road into the stair | Kerb upstand + 1.1 m guard, whatever the answer to Q7 |
| ACC-N03 | MAJOR | W4, u −9.03…−2.98 | Bank up to 2.05 m above L1 with no guard; element top 1.95 m too low | Stepped W4 + guard |
| ACC-N04 | MAJOR | lawn stair | ≤1.05 m clear between walls | 1.2 m between faces |
| ACC-N05 | MAJOR | `rs-head`, `cs-f1` head | Road and court water run down both stairs | Slot drains + lips |
| ACC-N06 | MINOR | `checks.py` §7.5 / §7.7 | Width, links and guards are never really tested | Measure them |
| ACC-N07 | MINOR | court stair, walk | About 1.12–1.17 m and about 1.0 m clear; barrow route does not fit | Walls outside the band |
| ACC-N08 | MINOR | R(20.8,1.0,21.8,3.4) | A 1.0 m pit 0.7 m below ground behind `ls-top` | Fill or plant it |

## Part B details

**ACC-N01 BLOCKER: walk to loggia.** `measured`:
- `walk-s` R(9.74,16.0,15.4,17.12) at 1670.00 and the loggia R(15.4,10.95,18.0,16.0) at 1669.98 share only the point (15.4, 16.0).
- SW-30 at the walk's east end is a 1.74 m drop. The loggia's south edge drops about 1.96 m and is guarded. The lower floor has no door onto the walk.
- So the "own way out" (ARR-02, FLX-01) and the outdoor court → lawn route are false.

Correction:
- Add `walk-e` R(15.4,16.0,18.0,17.12) at 1669.99, suspended on FW-16.0 and a new wall or beam on v 17.12 founded at about 1667.0. Ground there is 1667.8–1668.4.
- Remove the loggia's south guard; guard v 17.12 and u 18.0 instead (2.4 m drop to the lawn).
- Route: court → 24 R → walk → loggia → `t-low` → 16 R → lawn.

**ACC-N02 BLOCKER: road edge.** `measured`:
- `zg` at the road edge: 1677.54 (v 11.6), 1677.57 (v 14.7), 1677.60 (v 17.12).
- RW-W2 runs from 1675.0 to **1677.45**, so the road is above the wall top. F1 ends at 1675.51 and L1 is at 1675.50: a 1.76–2.10 m fall from a public road, over 6.6 m.
- No guard is drawn. The street wall exists only in the Q7 text, and `guards()` never scans road edges.

Correction, unconditional: W2's top ≥1677.75 (150 mm above the road) plus a 1.1 m non-climbable guard to about 1678.85, from the stair head to v 17.12. If Q7 is yes, the stone + lattice street wall does this. An engineer decides on vehicle restraint; the road level is unsurveyed.

**ACC-N03 MAJOR: bank south of L1/F2.** `measured`:
- Ground at v 17.42 is 1677.55 (u −9.5), 1676.03 (−6.5), 1675.27 (−5.0) and 1674.40 (−3.0): 2.05 m above L1 and about 0.8 m above F2.
- RW-W4's top is a constant 1675.60, up to 1.95 m below the soil it holds. The derived walls (tops 1677.25 / 1675.97) contradict it, yet §7.3 passes.
- There is no guard against a 2 m fall from the setback onto L1.

Correction: W4's top at the ground +0.15 m (1677.70 at u −9.0, 1676.20 at −6.5, 1675.40 at −5.0, 1673.75 at −1.0), with a 1.1 m guard over u −9.03…−4.6.

**ACC-N04 MAJOR: lawn stair width.** `measured`:
- FW-20.6 (0.30 m thick, centred on u 20.6, face at 20.75) takes 0.15 m of the 1.20 m flight.
- With the east walls on u 21.8 the clear width is ≤1.05 m (about 0.95 m with a 0.2 m wall), about 0.8 m between handrails, on a flight 2.38 m above the lawn.
- §7.5 tests the declared `width=1.20`.

Correction: 1.2 m clear at u 20.75–21.95 (east wall centred on about 22.05). That costs about 0.9 m² of lawn.

**ACC-N05 MAJOR: stair heads.** `measured`:
- The road edge at `rs-head` is 1677.54, against the head at 1677.47. The boundary channel does not cross the head, so road water and snowmelt go down 24 risers.
- The court falls 1:60 to its south edge, where the `cs-f1` head sits between the gullies at (−2.8, 16.9) and (4.3, 15.8).

Correction: a 150 mm slot drain across `rs-head` 0.3 m before the top nosing, with the head at 1677.52; a slot drain and 20 mm lip across the `cs-f1` head at 1673.55; treads with a 1–2% forward fall.

**ACC-N06 MINOR: checks.**
- §7.5 skips `rs-head` and uses declared widths, not widths between wall faces.
- Nothing tests that stairs, walks and terraces connect.
- In `guards()`, `missing` is never appended to, so "none missing" is always true.

Correction: measure the widths; add a route test (each leg of road → court → walk → loggia → `t-low` → lawn shares ≥1.0 m of edge with the next, levels within 20 mm); include ground and road edges in the guard scan.

**ACC-N07 MINOR: widths in the south band.**
- SW-6/7/8 sit on v 16.0, so the court stair is about 1.12–1.17 m clear.
- `walk-s` is 1.12 m with a guard on SW-29 (1.69 m drop), about 1.0 m clear. LND-03's barrow route (1.2 m + 0.25 m channel) does not fit.

Correction: walls and guard outside v 17.27, or accept 1.15 m and drop the wheel channel.

**ACC-N08 MINOR: the lawn slot.** At 1667.60 against ground at 1668.3, it is a pit walled on three sides that traps snow and water. Fill it to ground as planting.

## What C11 gets right

- The owner's court is built as asked: the stair at the far west against the road, everything else dug, +32% over C10 (rule 4.10).
- Every flight has the run its drop needs: ≤12 risers at 149–164 mm, 2R+G 0.617–0.648, landings top and bottom (rule 4.11).
- The court stair starts where natural ground equals court level (1673.61). Its treads sit 0–0.40 m in cut, and the boys' window keeps ground at +0.42 m against a +0.90 m sill (rule 4.8).
- Headroom ≥2.35 m under the terrace lip over cs-f3; the front door is under a covered porch facing the court.

## Out-of-scope notes

- The lawn sits on up to 1.33 m of fill at SW-33 (geotech/landscape).
- W1 is 3.87 m high, and W2/W3 retain a road in a seismic zone with no road survey (structure).
- The VEH-03 delivery bay is not drawn (vehicles).
