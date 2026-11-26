# 26 · Brief fidelity and design history (BRF)

## Summary

1. C10 avoids every C01–C09 rejection reason except one: the workshop is again a 0.6 m bench with 0.8 m to stand in (C04-A).
2. Five things the owner said once have been dropped:
   - an enclosed *hayat* with separate vehicle and pedestrian gates;
   - a study/play room (in C08, gone since C09);
   - an outside entrance to the lower floor;
   - an outdoor stair from the main-floor terraces to the garden;
   - a level garden instead of a natural bank.
3. `checks.json` marks 0110-r2 defects I12, I14, I26 and I30 as fixed; they are not.
4. The brief record holds two transcription errors (EV, prayer), and the priority list is still an unconfirmed `inference`.
5. Room areas match `space_program.yaml` and the owner's rules, except dining: 11.1 m² clear against 13.5–15.5 m².

## Findings

| ID | Sev. | Where | Finding |
|---|---|---|---|
| BRF-01 | MAJOR | `fore`, west boundary | No enclosed hayat; no vehicle or pedestrian gates |
| BRF-02 | MAJOR | lower `hall-l` | Study/play room lost |
| BRF-03 | MAJOR | lower floor, `path-s` | No real outside entrance to the lower floor |
| BRF-04 | MAJOR | `t-south`/`balc-e` | No outdoor stair from the terraces to the garden |
| BRF-05 | MAJOR | `garage` | Workshop is a sliver again (C04-A regression) |
| BRF-06 | MAJOR | `balc-m` | I30 repeated: the master balcony can be reached from the road |
| BRF-07 | MAJOR | several | 0110-r2 I11/I12/I14/I15/I22/I26 counted as fixed but not delivered |
| BRF-08 | MAJOR | `lawn`, `bank` | 74 m² level lawn against the owner's verbatim "flat outdoors" |
| BRF-09 | MINOR | `design_brief.yaml` | EV and prayer answers mis-recorded |
| BRF-10 | MINOR | road `office`, `plant` | Guest bed not shown; plant room 1.7 m deep |

## Finding details

**BRF-01**
- Source: round 23 verbatim: *"hayat … a door for the garage … And there's a door beside it. You open it. You're in a perimeter where you can then, with some stairs, go down"*. Also f-priorities: "separate vehicle and pedestrian gates".
- Evidence (measured):
  - No boundary wall or gate is drawn. Anyone on the road can walk down `gstair` to the court, the south terrace and every main-floor slider.
  - From the road edge (u = −0.547 v) to the garage face: 0.86–2.69 m at shutter 1, 3.1–4.9 m at shutter 2.
- Correction:
  - Build a ≈21 m road wall on the west boundary, v 0–18.42.
  - The garage shutters, flush with the wall line, serve as the vehicle gate; there is no room in front of shutter 1 for a separate gate.
  - Add a 1.2 m pedestrian gate at the head of the road stair, moved far west against the road (rule 4.10).
  - Ask the owner to confirm, because f-priorities is still an `inference`.

**BRF-02**
- Source: stmt-024: *"Not chosen: one downstairs lounge; study/play + office smaller."*
- Evidence:
  - C08 had a Study/Play room of up to 31 m². C09 and C10 have none.
  - C10's "HOMEWORK · GAMES" table sits in `hall-l` (18.9 m²), among 8 doors and openings.
- Reading (`inference`): the owner refused to shrink or merge the study/play room. Ask the owner to confirm this reading.
- Correction:
  - Add a room of ≥12 m² with a door and a window.
  - Candidate: road level, R(12.2, 9.5, 16.4, 13.0) = 14.7 m², beside the office, glazed east and south, taken from the 39.8 m² roof deck. Reviewer 01 checks the support over `living`.

**BRF-03**
- Source: round 23: *"this lower floor should be accessible from outside too. The entrance should be accessible from outside."*
- Evidence (measured): from the court, the only way to the lower floor is:
  - down `gs-court` (2.30 m drop in 2.0 m),
  - along `path-s` (1671.2 down to 1667.4),
  - onto the lawn, then up 14 steps to 1669.98.

  That is about 22 m, 6.0 m down and 2.4 m up. At u 15.4 the loggia is 1.7 m above the path.
- Correction: make the path end at 1670.0 at the loggia, and use the loggia as the lower floor's outdoor entrance (the lounge slider at u 16.7 opens onto it).
  - Steps: 21 risers of 0.171 m, goings 0.30 m, plus a 1.2 m landing, over u 4.6–11.8.
  - Then a level walk at 1670.0 over u 11.8–15.4, on 0.6–1.7 m of fill.
  - Screen the children's windows (PRV-02).

**BRF-04**
- Source: round 30: *"the upper floor … should have an entrance to outside, for example towards east or south, where the stairs outside can reach it"*. Also rule 4.11.
- Evidence (measured): from the 69 m² of main-floor terrace, the garden is reached only by going west to the court and then by BRF-03's route, about 30 m. Guests on the south terrace cannot step down to the children on the lawn.
- Correction: add a stair from the SE corner of `balc-e` down to `t-low`.
  - 3.58 m drop: 21 risers of 0.170 m and 20 goings of 0.30 m, plus a 1.2 m landing. That is ≥7.2 m of run, 1.2 m wide.
  - Candidate: u 19.4–20.6, running north from v 16.4 and landing at v ≈9.2. This needs `t-low` widened to u 21.8 for v 9.2–12.8.

**BRF-05**
- Source: C04-A was rejected for *"workshop … isn't it too narrow?"*. Also stmt-018 and rule 5.5.
- Evidence (measured):
  - The bench is R(6.15, 1.5, 6.75, 6.2), and the LC300's front is at u 5.35. That leaves 0.80 m to stand in.
  - The bikes leave 0.25 m in front of car 2.
- Correction:
  - Move the bench to R(6.2, 4.4, 6.8, 7.7), in front of the shorter car 2 (front u 5.15). That leaves 1.05 m to stand in, and the lobby door at v 7.9–8.9 stays clear.
  - Hang the bikes on the east wall at v 1.3–4.3. That leaves 1.0 m in front of the LC300.

**BRF-06**
- Source: 0110-r2 I30, and rule 6.5 ("quiet north side").
- Evidence (measured): `balc-m` shares its v 6.2 edge with `balc-e`. That balcony joins `t-south`, which joins `court-w`, which the open road stair reaches. A visitor can walk from the road to the master's 2.4 m slider. PRV-12 rates this MINOR; it is a defect the owner's review already found.
- Correction:
  - Put a 1.8 m opaque screen with a lockable gate at v 6.2, across u 17.8–19.4.
  - BRF-01's enclosure closes the court.

**BRF-07: 0110-r2 defects `checks.json` passes but C10 does not deliver**
- **I12, I22 (laundry and store)**
  - The laundry proper is R(5, 9.6, 8.2, 11.6) = 6.4 m², smaller than 0109-r5's 7.04 m². Its "13.9 m²" counts the 1.8 × 4.8 m store strip (0.8 m aisle).
  - Six bikes get 1.35 × 0.8 m, and no bins are shown.
  - Fix: a laundry of ≥12 m² on its own.
- **I14 (dining for 8)**
  - The table is 1.9 m in a room 3.4 m wide, so no chair fits at either end.
  - Fix: entry to u 2.0–4.2, kitchen to u 4.2–8.8 (still 16.1 m²), dining to u 8.8–12.6. That gives 13.3 m² and fits a 2.4 m table with end chairs.
- **I26, adj-05 hard (pantry)**
  - The pantry opens off the hall, about 5 m from the fridge.
  - Fix: move the kitchen's hall opening to u 4.6–5.7, opposite the pantry door; that makes it about 3 m.
- **I11 (prayer)**
  - The owner's NE prayer bay (0109-r5 B) is gone, and wudu to mats is about 14 m through the living room.
  - The mats face +v (157°); qibla ≈205° grid (computed; the CRS is unconfirmed).
  - Fix: a NE prayer bay in the living room, mats turned 48° clockwise.
- **I15 (noise over bedrooms)**
  - The kitchen, the dining room and the terrace table at (8.1, 14.9) sit over `boys`/`girls`. That clashes with *"terrace for … night time family or with guest time"*.
  - Fix: a floating deck build-up, or move the table zone to u 15.4–17.8, over the loggia.

**BRF-08**
- Source: round 18: *"I really perfer flat outdoors by retaining walls or excavation if possible"*. Round 22: *"level, not steps"*. stmt-024: about 150 m² of garden.
- Evidence (measured): the lawn is 74 m², and the 36 m² bank stays natural. Taking the lawn to the setback, where the ground is 1665.3–1666.0, needs a 1.6–2.3 m wall and gives about 110 m².
- Correction: give the owner both options with these numbers. If flat is chosen, plant the view trees in a 2 m bed on the lawn's east edge.

**BRF-09**
- Evidence:
  - Round 16 Q1: *"provision for future is nice"* was recorded as EV "unknown / not decided".
  - Round 20: *"a prayer area … nice to have"* was recorded as "unknown".
  - f-priorities and f-outdoor are still `inference`.
- Correction:
  - Record both corrections as an agent `inference` for the owner to confirm.
  - Show a future EV supply: conduit and an isolator at bay 1 (rating is an `assumption`).

**BRF-10**
- Source: round 14 Q3 (fold-out bed in the office: *"yes"*) and round 23 (boiler, purifier and electrical boxes at road level).
- Evidence:
  - The office (3.2 × 3.1 m, desk 0.65 m deep) leaves about 2.25 m, so a 2.0 m bed fits but is not drawn.
  - The plant room, labelled "+ TANKS", is 3.6 × 1.7 m. The owner's B had 7.44 m², and I20 already called that unproven.
- Correction:
  - Draw the opened bed.
  - Make the plant room ≥2.4 m deep (R(3.4, 11.6, 7.0, 14.0)), or move the tanks out.

## Brief → C10

| Requirement (source) | Status | Evidence |
|---|---|---|
| NW siting; road garage over two floors, stepping east (r23, r29) | met | east edges 12.2 / 17.8 / 18.0 |
| Hayat, separate gates (r23) | missing | BRF-01 |
| Lower floor reachable from outside (r23) | partly | BRF-03 |
| Outside entrance to the main floor by S/E stairs (r30) | partly | the west door is fixed by rule 2.6; BRF-04 |
| Terraces in every direction except west (stmt-012) | partly | S and E only |
| Level garden and play area (r18, r22, stmt-024) | partly | BRF-08 |
| Big trees in front of the city view (r22) | partly | 4 trees, 1.2–2.9 m bank (LND-04) |
| Study/play kept (stmt-024) | missing | BRF-02 |
| Office + WC at road level; plant (r11, r23) | partly | BRF-10 |
| Workshop bay (r20, stmt-018) | contradicted | BRF-05 |
| Prayer area (r20) | partly | BRF-07 |
| Everyday meals for 8 in the kitchen (r8) | contradicted | 3 stools (ROM-02) |
| Cross-ventilation (r17) | partly | kitchen and children's rooms single-aspect |
| EV provision (r16) | missing | BRF-09 |
| 0109-r5 basis (rule 6.7) | partly | NE prayer bay and plant placement dropped |
| Easy outdoor stairs; dig the west side (stmt-027) | contradicted | `gs-court` 2.3 m in 2.0 m |

Rules 1.5 (kitchen 15–17 m²) and 6.7 (18–22 m²) conflict; the owner must choose.

## History: rejection reasons

| Rejected | C10 |
|---|---|
| C01–03: kitchen without a terrace, voids, S/E wasted, digging | passes (the void under the stair is CIR-08) |
| C04-A: no garage→lift route, hidden stair, no cozy corner, **narrow workshop**, odd store | **workshop regressed**; the store is a corridor strip |
| C05: west kitchen, living reached through other rooms, narrow east | passes |
| C07: robotic, reused C06 plates | follows 0109-r5 |
| C08: 525–553 m², lawn 35–43 m², boundary crossed | 459 m², building cover 41%, lawn 74 m², inside the setbacks |

## Space program (target → C10 gross/clear, m²)

Rows not shown meet their targets: children 20.6 m² each, grandparents 23.0 m² + 6.7 m² bath, office 9.9 m², garage 57.1 m², terraces and balconies 69 m².

| Item | Target | C10 | Status |
|---|---|---|---|
| Living | 32.5 (rule ~34) | 35.4/33.9 | met |
| Kitchen | 23 incl. eating (rule 15–17) | 16.1/15.1 | meets the rule, not eating for 8 |
| Dining | 14 (rule 13.5–15.5) | 11.9/11.1 | **short** |
| Pantry | 4 | 4.9/4.3 | met; not off the kitchen |
| Master + ensuite | 15 + 5 | 24.2 + 7.8 + dressing 7.0 | suite 39 m² > living (ai_judgment) |
| Laundry / store | 6 / 5 | 6.4 / 8.6 | meets the program; I12 not met |

## What C10 gets right

- Every C05 failure is solved: the kitchen has a south slider, every main room opens off the hall, and the house is 15.8–16 m deep.
- The owner's 0109-r5 parts are kept: the 24R core with REST 1.40, the 4-part wudu cluster, the 4.3 × 4.8 m children's rooms on the south, the lounge with its tea bar, and the SE office.
- The grandparents get a seated ensuite (I10), and separate basins ease the morning queue (I13).
- The garage reaches the lift indoors, and the 4.2 m bays give 0 car-door clashes (I09).

## Out-of-scope notes

- Support under the master suite (the lower plate starts at v 2.8): reviewer 01.
- `gs-court` stair: 06/14.
- Lift landing: CIR-01.
