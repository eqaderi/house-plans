# S9 readiness demonstration record (SYNTHETIC)

Python 3.13.3 on Darwin arm64; strategies: all.
The owner is the synthetic actor `human:example-owner`; its approvals exercise the
gates and endorse nothing. Solver output can differ between platforms.

## Refusals (gates and frozen plans)

- `plan_generate_before_gates`: plan generation needs the owner's approved site and program (PROGRAM_APPROVED or later); the project is in SITE_INGESTION.
- `agent_approves_site`: agent 'claude-code' cannot approve the site gate; only a human can
- `agent_approves_program`: agent 'claude-code' cannot approve the program gate; only a human can
- `agent_approves_plan`: agent 'claude-code' cannot approve the plan gate; only a human can
- `revise_after_plan_approval`: plans can be revised during concept generation or review; the project is in PLAN_APPROVED. An approved plan is frozen: a human must reopen the plan gate (`house-ai workflow reopen <dir> plan`).

## Site

- relief 10.38 m, parcel 737.503 m², blockers []
- unknown (null, not invented): none

## Interview

- 27 turns; 26 of 26 scripted answers stored verbatim
- recorded by agent:claude-code; slot methods {'parser': 37, 'agent:claude-code': 2}
- 39 inferences before confirmation, 0 after
- outdoor (Persian answer, agent interpretation): ['terrace', 'garden']
- budget history kept: ['About 500k EUR.', 'Sorry, the budget is closer to 550k EUR.'] -> 550000 EUR

## Program

- 18 items, target gross area 170.0 m²; findings ['budget_not_checked']; 6 assumptions, 1 open questions

## Concepts and critics

Plans pin the approved site and program: True.

| Option | Feasible | Hard | Soft | Levels | Stairs (walking line) | Furniture/fixtures |
|---|---|---:|---:|---|---|---|
| concept-compact v1 | yes | 0 | 55 | lv-down-300 8.61, lv-entry 11.61 | st-0 u_shaped (yes) | 0/9 |
| concept-split-level v1 | yes | 0 | 38 | lv-down-450 7.15, lv-entry 11.65 | st-0 straight (yes) | 0/9 |
| concept-linear v1 | yes | 0 | 41 | lv-entry 11.75 | none | 0/9 |
| concept-two-wing v1 | yes | 0 | 44 | lv-down-450 7.2, lv-entry 11.7 | st-0 straight (yes) | 0/9 |
| concept-courtyard | no: rows 4.8/4.2 m: no room for a second pavilion behind a garden court: no 6 m long strip of  | | | | | |
| concept-split-walkout v1 | yes | 0 | 53 | lv-down-450 7.1, lv-down-300 8.6, lv-entry 11.6 | st-0 u_shaped (yes), st-1 straight (yes) | 0/9 |
| concept-open-plan-prop-day-up-night-down v1 | yes | 0 | 105 | lv-lower 8.75, lv-entry 11.75 | stair-main u_shaped (yes) | 0/0 |

Defects found by the critics:

- concept-compact: `large_underfloor_void` []: Void clear height 6.26 m exceeds configured 4 m concept-review trigger.
- concept-compact: `buried_habitable_face` ['w-down-300-001', 'sp-bed-child-2']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-compact: `buried_habitable_face` ['w-down-300-028', 'sp-bed-main']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-split-level: `large_underfloor_void` []: Void clear height 6.37 m exceeds configured 4 m concept-review trigger.
- concept-split-level: `height_limit_exceeded` []: Height 11.88 m exceeds envelope 10 m.
- concept-linear: `program_item_missing` ['pi-stair']: Stair (pi-stair): 0 of 1 placed; not needed in a one-level concept
- concept-linear: `level_count_differs` []: the program asks for 2 storey(s); this concept has 1 floor level(s)
- concept-linear: `large_underfloor_void` []: Void clear height 5.72 m exceeds configured 4 m concept-review trigger.
- concept-two-wing: `large_underfloor_void` []: Void clear height 5.73 m exceeds configured 4 m concept-review trigger.
- concept-two-wing: `height_limit_exceeded` []: Height 10.62 m exceeds envelope 10 m.
- concept-two-wing: `bed_double_no_sampled_fit` ['sp-bed-main']: No arrangement in the declared discrete template search; continuous infeasibility has not been proved.
- concept-split-walkout: `level_count_differs` []: the program asks for 2 storey(s); this concept has 3 floor level(s)
- concept-split-walkout: `large_underfloor_void` []: Void clear height 6.36 m exceeds configured 4 m concept-review trigger.
- concept-split-walkout: `height_limit_exceeded` []: Height 11.83 m exceeds envelope 10 m.
- concept-open-plan-prop-day-up-night-down: `large_underfloor_void` []: Void clear height 6.08 m exceeds configured 4 m concept-review trigger.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-001', 'sp-bed-child-1']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-002', 'sp-bed-child-2']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-004', 'sp-bed-main']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-006', 'sp-bed-main']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-007', 'sp-bed-child-2']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-024', 'sp-bed-main']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-029', 'sp-bed-child-1']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-032', 'sp-bed-main']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-035', 'sp-bed-child-1']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `buried_habitable_face` ['w-lower-045', 'sp-bed-child-2']: Buried face reduces daylight capability; waterproofing needs professional.
- concept-open-plan-prop-day-up-night-down: `window_buried` ['win-lower-024-30', 'w-lower-024', 'sp-bed-main']: Terrain/retaining face obscures part or all of this window.
- concept-open-plan-prop-day-up-night-down: `window_buried` ['win-lower-001-31', 'w-lower-001', 'sp-bed-child-1']: Terrain/retaining face obscures part or all of this window.
- concept-open-plan-prop-day-up-night-down: `window_buried` ['win-lower-002-32', 'w-lower-002', 'sp-bed-child-2']: Terrain/retaining face obscures part or all of this window.

Diversity: 10 pairs, near-duplicates none; max footprint IoU 0.86, min topology distance 0.38.

## Visual review

Critique by agent:claude-code; ungrounded IDs: none; made on this rendering: True.

- vc-stair-through-slab [ai_judgment] ['st-0', 'slab-roof-down-450', 'lv-down-450', 'lv-entry']: Stair st-0 is drawn outside both wing outlines on both plans and climbs 4.5 m between lv-down-450 and lv-entry, while the night wing is drawn 3.0 m tall: the flight passes the night wing's roof slab slab-roof-down-450, so it cannot be walked as drawn.
- vc-night-wing-floats [ai_judgment] ['lv-down-450', 'slab-floor-down-450']: In the true section the night wing floor slab-floor-down-450 hangs several metres above the terrain line, and the day wing also stands clear of the ground: both wings sit on large unsupported voids rather than stepping down the slope.
- vc-living-too-small [ai_judgment] ['sp-living', 'pi-living']: The living room sp-living is drawn as the smallest day room, well below the program target for pi-living; the dining room next to it is about as large.
- vc-lower-labels-overlap [ai_judgment] ['sp-bed-child-1', 'sp-bed-child-2', 'sp-corridor-b1', 'sp-mechanical']: On the lower level the labels of the child bedrooms, the corridor sp-corridor-b1 and the plant room sp-mechanical overlap and cannot be read at the default zoom.

Findings of the same version's Evaluation: large_underfloor_void [], height_limit_exceeded [], bed_double_no_sampled_fit ['sp-bed-main']

## Owner-style revisions

- v2: "The living room is too small for us. Please make it about 25 m2." ops ['area:pi-living=25']; rooms changed ['sp-corridor-b0', 'sp-dining', 'sp-entry', 'sp-flex-b0-front', 'sp-living', 'sp-stair-0a', 'sp-storage', 'sp-study-1', 'sp-terrace']; living 21.6 m²; new violations ["request not met: 'area:pi-living=25' (sp-living area 21.6 m² < requested 25 m²)"]
  - request met (within 2 m²): False; unmet request reported by the revision: True
- v3: "Keep the study away from the garage, it gets noisy when the car comes in." ops ['separate:pi-study-1,pi-garage']; rooms changed none; living 21.6 m²; new violations ["request not met: 'area:pi-living=25' (sp-living area 21.6 m² < requested 25 m²)"]

## Unapproved program change

- program v2 written after approval of v1; new plans pin program version(s) [1]

## Plan gate, bundle and provenance

- plan review open reasons: 0; attention: ['height_limit_exceeded (eval-concept-two-wing): Height 10.62 m exceeds envelope 10 m.']
- approvals: {'site': 'human:example-owner', 'program': 'human:example-owner', 'plan': 'human:example-owner'}; final state PLAN_APPROVED
- reviewer bundle bundle/bundle.json (3322123 bytes)
- store verify problems: none; 102 events

Nothing here is permit-ready, construction-ready or professionally checked; see
docs/PROFESSIONAL_HANDOFF.md.
