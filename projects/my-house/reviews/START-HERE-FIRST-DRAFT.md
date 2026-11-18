> **RESET — 20 October 2026:** The owner rejected every exploratory plan from this round and requested a fresh start. All plan outputs and their generating scripts have been deleted. Read [the restart record](RESTART-AFTER-REJECTED-DRAFTS.md) first. Do not regenerate the rejected layouts or adopt their numerical assumptions; await the owner's new direction. The material below is the earlier handoff and remains historical wherever it conflicts with this reset. Site evidence and owner requirements remain available.

# Start here: first exploratory house-plan draft

Updated 20 October 2026. English project record; homeowner-facing explanations should be in Persian unless requested otherwise.

## Purpose and current instruction

The homeowner wants the forthcoming first draft to use the agent's best architectural judgment, without another detailed discovery interview. They ask how to start here or in a new chat while retaining the analysis. This note prepares that continuation. **No new chat or floor-plan generation was started by creating this note.** Starting the first draft does not mean the homeowner has adopted the siting recommendation, chosen an exact floor count/area, confirmed every interview inference, or approved a workflow gate.

A future chat should run in this same `house-plans` checkout and read this file. The file is a navigation/handoff note; canonical project data and linked evidence own the facts. Inspect current versions rather than assuming the versions listed here remain latest.

## Read in this order

1. Repository instructions: [AGENT_CONTRACT.md](../../../docs/AGENT_CONTRACT.md), then the applicable floor-plan generation/review skills. Use `.venv/bin/python` / `.venv/bin/house-ai` and `--actor agent:codex` for state changes.
2. Current canonical project and interview status:
   ```bash
   .venv/bin/house-ai project verify my-house
   .venv/bin/house-ai project status my-house --json
   .venv/bin/house-ai interview status my-house --json
   ```
   At this handoff: site v3, interview/design brief v23, space program v2. Workflow `SITE_NEEDS_VERIFICATION`; no approvals. Formal coordinate/unit/datum/legal boundary confirmation remains pending. Owner-supplied EPSG:32638 and map recognition exist as evidence; do not ask for another map pin or guess a CRS.
3. [Architectural site brief](site-context-2026-10-20/SITE-BRIEF.md): parcel, road, orientation, neighbors, setbacks and confirmed shared pedestrian access.
4. [Elevation schematic](site-context-2026-10-20/site-context-elevations.png), [SVG](site-context-2026-10-20/site-context-elevations.svg), [elevation methods/evidence](site-context-2026-10-20/ELEVATION-NOTES.md). The owner explicitly recognized the schematic as accurate. This is owner feedback, not formal site approval.
5. [Garden-led siting recommendation](garden-led-siting-2026-10-20/RECOMMENDATION.md), [terrain screening](garden-led-siting-2026-10-20/terrain-screening.json), [assumptions](garden-led-siting-2026-10-20/assumptions.yaml), [open questions](garden-led-siting-2026-10-20/open_questions.yaml). This is architectural advice with calculations, not an adopted house layout. It is also preserved as registered source `src-recommendation`.
6. [Environmental assessment](location-research/epsg-32638-preview/REPORT.md): regional sun/climate/wind and mountain horizon, with substantial limits on parcel-level shadows and local winds. [Survey audit](survey-audit/REPORT.md) explains geometry, terrain metrics and anomalous points.
7. Latest canonical interview brief and program through ProjectStore. The editable `design/` exports may lag the canonical brief: program v2 references brief v22, while the latest tree/garden priorities are in brief v23. **Refresh the unapproved space program from the latest brief before generating**, then inspect changes. Do not rely solely on the old exported YAML or assume the generator reads advisory Markdown automatically.

## Preserve these requirements and distinctions

- Approximately 600 m² parallelogram: short sides 21 m, long sides 32.57 m. Long-axis view is ENE, approximately 67.97° true using the owner-supplied CRS. Keep original coordinates and survey geometry.
- Primary vehicular access is the upper western road, reported as 9 m total = 8 m asphalt + 1 m parcel-side sidewalk. Actual road thresholds/gates still require design checks.
- South/east have 1 m inward **perpendicular** no-build strips. Site v3 has the calculated 547.57 m² setback envelope as inference; it does not establish all applicable statutory controls. Do not return to an unbuffered 600 m² footprint area.
- Southern 2 m shared passage is continuously connected to the road and shared **pedestrian** use is agreed by the owner. It is not a second vehicle frontage or a documented legal easement verification.
- Future neighboring houses north and south; preserve privacy and test their shadows when heights are known.
- Surveyed interior spot relief is 12.554 m. The displayed centerline section drops 11.874 m over 32.57 m. Parcel-weighted mean TIN slope is 40.68%; these are different measurements. No slope smoothing, fabricated retaining breaklines, or extrapolated heights.
- Current household brief: parents, two sons, two daughters, potentially two grandparents; four bedrooms with children sharing, grandparents sharing; lift/step-free access requirement; closed two-car garage for a large SUV and medium sedan; quiet office, pantry, laundry/storage and relevant bathroom/day-space requirements. Read the full current brief for kitchen, dining and other details instead of treating this list as exhaustive.
- Main new priority: a generous continuous nearly level garden/play area, substantial trees in front of the city view, leaf movement/sound in wind, and enjoying the garden in rain. Preserve both play usability and garden/house connection. Persian explanation; English project records.

## Working architectural judgments, open to improvement

- Preferred initial search area: compact house in the upper western part, biased north, leaving meaningful continuous southern/eastern garden space. Do not blindly build on the northern boundary or force a full-width western barrier.
- Area bands proposed for comparison: combined projected house/garage footprint 160–180 m²; total enclosed gross area 280–320 m² including a 45–50 m² closed two-car garage; main continuous play/garden platform 100–150 m². These are agent working assumptions, not fixed owner constraints or a validated geometric fit.
- Compare two residential levels with a smaller road-level garage/entry tier against two levels total with the garage integrated into the upper floor. The first can mean **three access elevations in section**. Do not label it simply “two floors” and hide the garage level.
- Align the garden-facing living/day level with the main usable play platform where feasible. Examine a grandparents' room/bathroom on that level and lift connections. Let actual plan/terrain checks improve the arrangement.
- A 115.2 m² analytical window in the middle southern region has mean ground about 5.94 m below the interpolated west-boundary midpoint. Similar upper/lower windows are 4.59/7.29 m below. These are comparative sampling windows, **not proposed garden pads, actual road/garage levels, or proof that a house fits next to them**.
- Trees should frame the view at mature size, with actual rooting soil and drainage/retaining separation. Do not assume the 1 m eastern strip or deep fill is sufficient for large trees. Aim for one principal flat play area and limited broad landscape levels, rather than promising the whole 12.55 m fall can disappear into a few shallow steps.
- Regional climate/wind data do not prove garden sunshine hours, a sheltered side or structural design loads. Keep measured/inferred/simulated/judgment/not-checked statuses explicit.

## Starting the actual first draft

Use architectural judgment for reversible design choices and record the assumptions; do not invent survey facts or professional approvals. Broad discretion to draft is not permission to impersonate the homeowner at approval gates.

1. Re-read current inputs and refresh the space program from the latest brief:
   ```bash
   .venv/bin/house-ai program build my-house --out projects/my-house/design --actor agent:codex
   ```
   Keep proposed numerical areas/storeys distinct from owner decisions. Follow applicable generation/proposal interfaces for exploratory overrides rather than relabeling agent advice as a homeowner answer.
2. Before site/program gates are approved, use the supported **exploratory** generation path only:
   ```bash
   .venv/bin/house-ai plan generate my-house --exploratory --out projects/my-house/design/first-draft-exploratory --actor agent:codex
   ```
   This does not grant approval or record an approved plan. Read the actual current CLI help/skill for available strategy/sectional/proposal options. Use an exploratory proposal if the best garden/section arrangement needs one; do not assume the default generator incorporates this advisory note.
3. Generate several meaningfully different options, check them, explain trade-offs and recommend a strongest first draft. Use solver-generated geometry and canonical integrity checks; never hand-invent room coordinates or fix a pretty SVG independently of the model.
4. Deliver readable floor plans for every level, site placement, actual area schedules, a terrain section showing road/garage/house/garden relationships, and an explanation of which garden surfaces are truly usable/level and how they connect. Include vehicle access, accessible routes, retaining/drainage implications, sunlight/shadow limits and tree/view considerations. Report infeasible strategies rather than hiding them.
5. Use grounded architectural/visual review and fix material defects before presenting the draft. Exploratory output remains provisional even if software integrity checks pass. Geotechnical/slope stability, structural adequacy, legal/code permissions and actual costs remain unverified.

## Continuation prompt

> Read `projects/my-house/reviews/START-HERE-FIRST-DRAFT.md` and its linked evidence. Generate the first exploratory house-plan options using your best architectural judgment and clearly recorded assumptions. Prioritize the level garden/play area, trees and city view, road-level closed garage, and accessible family living. Compare the options and recommend your best draft with floor plans, site layout, areas and a terrain section. Keep records in English and explain in Persian. Do not repeat the discovery interview unless a missing fact truly prevents an exploratory draft, and do not bypass the approval gates.

## Validation and workspace caution

[Last full validation](garden-led-siting-2026-10-20/VALIDATION.md): 870 tests passed; Ruff/schema/tracker checks passed; 76 events/73 artifact versions intact at this handoff. The navigation note itself changes no canonical project state. Confirm current integrity before continuing.

The checkout already has substantial uncommitted work, including source/test changes unrelated to this note. Do not reset/clean, overwrite it, assume a new worktree copies it, or push/commit it as part of architectural drafting without the applicable workflow/authorization. Read current Git status before changing implementation.
