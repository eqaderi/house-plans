# Continue the homeowner project

Saved 2026-10-20 by agent:codex. Private project data; this is a handoff export,
not a replacement for canonical records or homeowner approval.

## Start here

Workspace: `/Users/ershadqaderi/_projects/house-plans`.
Current branch: `stage/H2-interview-program`. Work is saved locally but has not
been committed or pushed. Preserve the existing changes and survey originals.

Read `docs/AGENT_CONTRACT.md` in full, then the H1/H2 sections and current
handoff in `docs/PROJECT_TRACKER.md`. Use the architectural-programming skill.
Use the project venv and `--actor agent:<your-tool>` on state mutations.
Do not restart the interview or repeat answered location questions.

Inspect live state rather than assuming versions remain current:

```bash
.venv/bin/house-ai project verify my-house
.venv/bin/house-ai project status my-house --json
.venv/bin/house-ai interview status my-house --json
.venv/bin/house-ai interview checklist my-house --json
.venv/bin/house-ai statement list my-house
```

At this handoff: interview and design brief v19; owner statements v11;
57 events and 54 artifact versions intact. Interview has 18 turns, 27/28
applicable checklist questions covered, 19 confirmed slots, 15 unconfirmed
interpretations and 8 unknown slots. Some unknowns reflect software limitations,
not missing homeowner answers. Inspect the complete raw answers before asking.
State remains `SITE_NEEDS_VERIFICATION`; no site/program gates are approved.

## Immediate next deliverable

Prepare a proposed room-and-area schedule and a concise consolidated brief for
homeowner review, with comfortable furniture/circulation-based sizes, bathroom
recommendations and separate indoor/garage/outdoor totals. The owner has no
preferred dimensions or total area and expects recommendations. Budget is
undecided. Proposed sizes and bathroom counts are agent recommendations, not
owner-confirmed requirements. Do not invent a fixed storey count.

Keep useful work moving while site confirmation is outstanding. Before a
canonical program is presented as validated, address ISS-38/39/40 below, resolve
remaining interpretation confirmations, and run the relevant validation. Do not
build knowingly incorrect output and call it complete. Then prepare the review
package and exact human confirmation/approval steps when their prerequisites
are met. Approved floor-plan generation follows the site and program gates.

## Preserve these homeowner requirements

The canonical raw interview answers are the authority; this list is a retrieval aid.

- Design for parents, two sons (already about ten), two possible future daughters,
  and potentially two permanent grandparents: capacity eight.
- **Four bedrooms**: parents, boys sharing, girls sharing, grandparents sharing.
  Do not turn the software's false five-bedroom warning into an owner problem.
- Lift and step-free access for older relatives or an injured family member.
  Bedrooms may be on any floor with lift access. Number of floors remains flexible.
- One shared family/guest living area; spacious living, views, daylight and a
  garden are major priorities.
- Kitchen with full-height walls and two openings on different sides/ends;
  preferably doorless, but doors acceptable if needed. Frequent substantial
  cooking; smell containment matters. Separate pantry.
- Daily eating in the kitchen **and** a distinct dining area nearby.
- Parents' bedroom has its own bathroom; other bedrooms may use shared bathrooms.
  Prefer a bathroom on each occupied floor, with showers preferred. Total number
  is for the agent to recommend. Do not reinterpret this as only one bathroom total.
- Closable garage comfortably fitting one large SUV and one medium sedan.
  Extra open parking/carport is optional, not required. Future EV provision,
  not a confirmed requirement to install a charger now.
- Quiet office for software-engineer father; occasional overnight guests are
  uncommon and office/guest dual use is acceptable. Separate laundry and storage.
- Moderate privacy; bedroom separation from entertaining is the current
  interpretation to confirm. Optional prayer area and optional workshop; no
  dedicated prayer room was demanded. Workshop can share garage only if both cars
  still fit comfortably; activity/equipment undecided.
- Garden, children's play area and outdoor dining/evening terrace. Largest usual
  gathering about 15 people total. Strong preference for **usable flat outdoors
  using retaining walls/excavation where feasible**. Do not confuse this with a
  preference against stepped house forms or excavation.
- Modern-leaning mixture of styles; materials flexible. Daylight/views very
  important; natural ventilation desired. Complete home, no planned extension.
- Budget, exact room sizes and total floor area undecided; recommend sizes.

The 15 unconfirmed slots include office, laundry, storage, guest frequency,
privacy/bedroom separation, style, daylight, no future expansion, priorities,
gatherings, flexible hillside strategy, no fixed sizes and ventilation. Present
one understandable addendum for confirmation rather than re-interviewing the
owner. Do not treat the later map recognition as confirmation of these slots.

## Program compiler issues — necessary before program review

Tracked in `docs/PROJECT_TRACKER.md`; no code fixes have been made yet:

- **ISS-38**: everyday kitchen dining can cause the separate requested dining
  area to disappear. Preserve both requirements in canonical program output.
- **ISS-39**: bedroom calculation assumes one room per elder and builder can
  truncate a child room. Support the explicitly shared grandparent room and
  preserve all four agreed sleeping groups. Do not reduce occupants, demand a
  fifth room or accept a misleading shortage override as the solution.
- **ISS-40**: CLI normalisation treats valid enum string `none` as unknown.
  Preserve valid choices before generic unknown aliases. Keep occasional guest
  accommodation/office dual use without inventing a dedicated guest bedroom.

Use synthetic regression data for fixes; never copy private household/site
facts into tests, examples or public docs. Follow domain/schema rules if models
need extending. Interpret open-plan status from the full recorded kitchen/living
answers; avoid repeating questions only because a slot was not populated.

## Site and environmental research already completed

Read `reviews/location-research/epsg-32638-preview/REPORT.md` relative to this
project. All supporting response data, source register, plots, reproducible
analysis script and transformed point CSV/GeoJSON are beside it.

- Owner explicitly supplied **EPSG:32638 — WGS 84 / UTM zone 38N**.
- Calculated candidate-parcel centre is **34.9692467 N, 46.3564133 E**.
  Owner answered **“Yes, that is my field”** to that exact map point.
  Another pin or nearest town is unnecessary for preliminary research.
- All 27 POINTs were independently read with ODA/ezdxf and native GNU LibreDWG
  0.14. Source XYZ agrees numerically. Originals are unchanged. No usable global
  CRS declaration was found within the DWGs; the owner supplied the missing CRS.
- Research north: true north about 0.778 degrees counterclockwise from grid north.
  Canonical site was not altered or formally confirmed.
- Survey-wide point heights 1664.884–1680.071 m; in-parcel spot relief 12.554 m.
  Owner says metres above sea level; exact vertical datum unknown.
- NASA 2001–2025 regional climatology and complete 2025 hourly model wind were
  saved. Broad grid/model elevation limitations are explicit. PVGIS horizon and
  solstice paths show winter midday sun clearing modelled mountain horizon.
- Provincial Paveh rainfall form was retrieved via agent-browser. Its table has
  missing/malformed entries and inconsistent totals; no verified station rainfall
  normal or drainage design storm was claimed. Regional wind is not an on-site
  prevailing-wind or structural wind study. Solar energy is not sunshine hours.
- External research used rounded coordinates as owner-authorised; no DWG uploaded.
  No further research is needed merely to re-establish these same findings.

Formal outstanding site work: human unit/CRS confirmation in the tool; precise
vertical datum or explicitly adopted local benchmark; legal boundary; actual
road/access interpretation; restrictions/setbacks; terrain warnings/professional
ground evidence. See `reviews/CONFIRM-SITE.md`. Unknowns stay unknown.

Never run `site confirm`, gate approval, provider consent or human-only rejection
on the owner's behalf, nor fake an interactive human actor/TTY. Prepare concrete
review materials first, then explain the exact human step only when required.

## Checks and session end

Full pytest passed **867 tests in 443.64 s** during the preceding investigation;
Ruff clean, 29 schemas current, tracker checker passed. Figure layouts were
visually inspected. Project integrity and original DWG hashes were verified.
These checks establish software/store consistency, not professional site approval.
No implementation changed after that full test run; subsequent edits are saved
records, research exports and handoff documents. Run checks appropriate to any
new code fixes and the contract-required checks before claiming their completion.

Update this handoff and tracker as work advances. Do not mark H1/H2 complete,
merge, push or silently approve a gate based on this handoff.
