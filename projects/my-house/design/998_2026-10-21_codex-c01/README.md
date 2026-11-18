# Codex C01 — compact, boundary-aligned house

Author: **agent:codex**. Date: **21 October 2026**. Status: **exploratory siting, massing and floor-use proposals**. This is a new study, not a revival of the deleted/rejected plans. No room plan or approval is implied.

[View the comparison board](codex-c01-board.png).

## Your direction carried forward

Your original words and subsequent answers are recorded in the shared interview through the project CLI, with Codex authorship. The first message is also exported verbatim as `owner-direction.txt`. Your answers were **“Yes, three levels total”** and **“Compare both before deciding”**. Your later instruction excludes every road-aligned main-house option. Your latest priority is minimum building land take and a large downhill garden.

- Place the house near the northwest, with its orthogonal axes following the long northern/southern boundaries. Their measured view-axis bearing is approximately 67.97° true under the owner-supplied CRS, or 22.03° north of east. Formal site verification remains pending.
- Reserve the western wedge as an **arrival court / entrance courtyard (hayat)**. It is outside the building but inside the property. Its eventual paved portion need not occupy the whole reserve.
- Vehicle approach reaches the closed two-car garage at road level; a separate pedestrian gate leads into the court and down an exterior stair to the main entrance on the upper residential floor.
- A shared internal stair and lift serve the garage tier and both residential floors. A step-free pedestrian connection from the court to the top lift lobby should be tested, so using the lift need not require walking through parking bays.
- Upper and lower residential floors need exterior access: upper via arrival stairs; lower via the garden route. Exact stairs, landings, thresholds and door locations are unresolved.
- No long corridors with rows of doors. Test a compact core, a small entrance lobby, and two small bedroom clusters with short private vestibules. Bedrooms must not become circulation routes, and open circulation does not erase the earlier kitchen enclosure/smell-control brief.
- Excavation and retaining walls are acceptable to you. That records willingness to consider them, not an assumption of unlimited physical feasibility.

## Two proposals using the same siting

| Tier | C01-A — living upstairs | C01-B — living downstairs |
|---|---|---|
| Top, at road | Garage, shared core, tentative quiet office and separate plant room | Same |
| Upper residential | Main entrance, living, kitchen with daily dining, separate dining, pantry, shared bathroom and storage | Main entrance landing screened from four bedrooms; shared bathroom, parents’ en-suite, laundry |
| Lower residential | Four bedrooms; shared bathroom, parents’ en-suite, laundry | Living, kitchen with daily dining, separate dining, pantry, shared bathroom and storage, garden connection |

The bedrooms remain parents, boys sharing, girls sharing and grandparents sharing. The earlier accepted lift means grandparents need not be on the arrival floor. Both options preserve the kitchen's full-height enclosure, two circulation openings, separate pantry and nearby dining area; the drawings do not change that to an entirely open kitchen.

**Architectural judgment:** B deserves the first detailed room-layout test because the garden is central to your brief. A is the comparison for a more direct arrival into the day spaces. B requires a screened upper entrance landing and easy descent to living areas. No choice has been recorded for you.

Office and plant positions remain proposals. Allocate a separate service room rather than assuming a boiler, purification equipment and electrical equipment can share the parking space or office. Actual equipment, access, ventilation, sound and service routes are not designed here.

## Land take and size tests

The CP-SAT study selects rectangles on a 0.1 m grid, aligned strictly to the long boundaries, inside the current provisional envelope. It minimizes the **union of all three floor projections**, including the small lower-floor step. This is a minimum within the tested candidate set and assumptions, not proof of the smallest workable house.

| Assumed gross residential plate | Combined projected building footprint | What it means |
|---|---:|---|
| 115 m² per residential floor | 122.36 m² | Smaller sensitivity case; room/furniture fit not established |
| 125 m² per residential floor | **132.30 m²** | Working case on the board; 125.1 m² each residential floor |
| 135 m² per residential floor | 142.20 m² | More room, with greater land take |

The working main floor plate is 13.9 m along the long boundaries by 9.0 m perpendicular to them. The top tier is 10.0 × 9.0 m and occupies the western part. The lower floor steps 0.8 m farther downhill; its western edge also moves 0.8 m. All these dimensions are **Codex assumptions selected for an exploratory budget**, not owner-fixed dimensions. Exact room packing may require a wider/shorter rectangle or a different offset.

- Parcel: **600.00 m²**, calculated from source boundary.
- Combined projected building footprint: **132.30 m² (22.05%)**, calculated from the union of solver-selected plates.
- Enclosed plate total: **340.20 m²**, including the 90 m² garage/office/service tier. This is a gross massing allowance, not net usable area or a cost estimate.
- Unbuilt parcel area: **467.70 m²**. This includes arrival, passages, setbacks and slopes; it is not all garden.
- Connected south/east garden reserve: **318.21 m²**. This excludes the western arrival reserve, building and narrow northern strip. It includes future garden paths, terraces and retaining/drainage works; it is not 318 m² of flat lawn.
- Of that garden reserve, **112.60 m²** lies wholly beyond the downhill building end. The remainder connects around its southern side. The garden reserve is an L-shaped connected region, not a single rectangular pad.
- Western arrival/approach reserve: **76.59 m²**, including the wedge and possible outside stairs. Paving, landscaping, gates and manoeuvring must be designed within it; the whole reserve need not be paved.

No vehicle swept-path study has been done. The 5.5 m western approach allowance is measured along the house axis, not a claim of 5.5 m perpendicular road clearance at every point. The assumed 1 m northern clearance is not an asserted legal setback. Existing owner-reported 1 m south/east strips remain intact.

## Area budget to test in room layouts

These are proposed usable-area allowances plus explicit common-space/wall budgets; not fitted rooms. Shared children's bedrooms are larger than the compiler's old 11 m² defaults. Garage sizing still needs actual vehicle envelopes.

| Floor-use group | Working allowances | Total |
|---|---|---:|
| Day floor | Living 32.5; kitchen/daily dining 23; dining 14; pantry 4; bathroom 6; storage 5; entrance/landing 6; stair/lift 14; walls + short circulation 20.5 | 125 m² |
| Night floor | Parents 18; grandparents 16; boys 15; girls 15; en-suite 5; shared bathroom 7; laundry 6; stair/lift 14; landing/vestibules + walls 29 | 125 m² |
| Top tier | Garage 45; office 12; plant 6; stair/lift 14; lobby 4; walls 9 | 90 m² |

Only one main entrance is intended; “entrance/landing” is the allowance on the relevant floor. Stair/lift area is counted on **every tier**, unlike simply dividing the generic program total by three. Terrace area is outside these enclosed budgets and must be deducted from the garden allocation when laid out. No bathroom on the garage tier is assumed yet.

## Terrain is the next physical constraint

The three heights in `massing-model.json` use a TIN-interpolated western-boundary midpoint and hypothetical 3.2 m floor intervals. They are **not adopted finished-floor levels**. The field's actual road threshold at the intended garage location still needs to be coordinated.

At the illustrative lower-floor plane, the far-east 112.60 m² garden region sits entirely below that plane: the integrated geometric space below it is about **463 m³**, with a maximum vertical gap of **5.81 m**. This is a terrain calculation, **not** a retaining-wall design, actual fill requirement or cost. It shows why extending one flat platform across the entire downhill garden cannot be assumed. Test a connected terrace near the living floor plus a broad lower garden, or reconsider floor levels and garden grading together. Your acceptance of excavation/retaining expands the options; it does not determine the solution.

## Provenance, verification and next work

- `study.json` pins site v3 and program v6, solver assumptions, measured areas and terrain screening.
- `massing-model.json` uses the shared `HouseModel` schema. It contains **three massing floor slabs only**, no invented room layout. `check_model` returned no findings on that limited model; this establishes neither room fit nor architectural completeness.
- `codex-c01-a-proposal.json` and `codex-c01-b-proposal.json` are schema-valid `ConceptProposal` exports. The generic level names mean `upper` = road tier, `entry` = upper residential tier, `lower` = lower residential tier. The lift/core assignment is an anchor, not a single-floor lift.
- **Do not feed these proposals into the current default road-aligned generation path.** This study never invoked it. Boundary alignment must remain explicit in every later room solver and rendering.
- `build_study.py` reproduces the massing search using the project venv. `render_study.py` derives the board from those exports. `rsvg-convert` renders the PNG. No survey originals or application code were changed by C01.
- Authorship is visible on every proposal/board and in project events. Claude, Gemini and Codex should read the same owner brief, then produce distinct named/versioned proposals rather than overwriting each other's alternatives.

Next: fit and furnish both floor-use arrangements inside boundary-aligned envelopes; test two beds in each children's room, two real vehicles, core alignment, kitchen passages, outside stairs and compact private circulation; then coordinate road threshold and garden levels. Reject any candidate that fits only by losing an agreed room, inventing a road-facing layout or turning circulation into a long hallway.

Site and program approval gates remain open. C01 does not request or grant approval, and it is not a construction drawing.
