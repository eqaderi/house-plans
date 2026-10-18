# Domain model

The canonical schemas live in `src/house_ai/domain/` and are exported as
JSON Schema to `schemas/`. This document explains what they mean. Field-level
detail is in the code and the generated schemas.

## Conventions

| Topic | Rule |
|---|---|
| Units | Everything in the canonical model is metres, square metres and degrees. Source drawing units are recorded separately and converted on import. |
| Frames | SOURCE (raw drawing units) → GRID (metres; easting/northing in the confirmed CRS) → LOCAL (project frame). All canonical geometry is LOCAL. |
| Identifiers | Lowercase slugs matching `^[a-z][a-z0-9]*([-_][a-z0-9]+)*$`, max 64 characters, unique across the whole model. Suggested prefixes: `sp-` space, `w-` wall, `d-` door, `win-` window, `o-` opening, `l` level, `z-` zone, `m-` material. `exterior` is reserved. |
| Time | Timezone-aware, stored in UTC. Naive timestamps are rejected. |
| Strictness | Unknown fields, NaN and infinity are rejected everywhere. |
| Unknown values | `null`, or an explicit status of `unknown`. Never a plausible default. |
| Areas | Space polygons and SVG labels use wall centreline areas. S6 derives net floor by subtracting modelled wall solids, allowing floor-level doorway recesses; missing wall edges are reported. Explicit floor slabs exclude unsupported floor and voids. Net dimension metrics are enclosing extents. |

## Epistemic status

Every claim says how it is known.

- `Epistemic` (brief facts, assumptions, site boundary, envelope):
  `verified_fact`, `inference`, `assumption`, `preference`,
  `simulation_result`, `professional_approval`, `unknown`.
- `ClaimStatus` (evaluator output): `measured`, `inferred`, `simulated`,
  `ai_judgment`, `not_checked`.
- `ConfirmationStatus` (units, CRS, vertical datum): `unknown`,
  `declared_in_source`, `user_confirmed`, `local_only_confirmed`. Only a
  human moves a value to the last two.

## Provenance

- `Actor`: `human`, `agent` (with optional provider and model) or `system`.
- `Provenance`: when, by whom, by what method and tool, from which input
  artifact versions.
- `ArtifactRef`: `(kind, id, version, sha256)`, a pointer to one immutable
  version. Plans pin the site and program versions they were drawn on;
  approvals pin the version they approve; builds pin the plan they came
  from.
- `SourceDocument`: an original input preserved byte-for-byte, with its
  SHA-256 and a data classification (`private` by default, `synthetic`,
  `public`).
- `CadImportProvenance` (artifact kind `cad_import`, id `cad-<source id>`):
  file name, SHA-256, detected format, drawing units and their status,
  parser and version, converter and version plus the converted file's
  SHA-256 (DWG), CRS status, EPSG (only if confirmed) and declared EPSG,
  vertical datum status, local origin, warnings, unrecognised layers and
  entity counts, the layer mapping used, every `AmbiguousEntity`
  (handle, layer, entity type, reason) that was left out, and every
  `HeightLabelCheck` (a height label drawn exactly at a surveyed point,
  its value, the point's z and whether they agree; labels are never used
  as elevations). Drawing units are the file's own declaration, or the
  site's confirmed unit when the file declares none or the same one.
  A `Site` refuses duplicate ids among spot elevations, contours, features
  and issues.

## Site and coordinates (`site`)

- `SiteCoordinates`: `source_units` and `elevation_units`
  (`UnitDeclaration`), `horizontal_crs` (`HorizontalCRS`: `epsg` only when
  confirmed, otherwise `declared_epsg`), `vertical_datum`, and `local`
  (`LocalCoordinateSystem`: GRID origin, rotation of local x from grid east,
  grid-to-true-north angle, computed with PROJ only from a confirmed CRS).
- `SurveyTransform`: the reversible SOURCE → GRID → LOCAL chain
  (horizontal and vertical unit scale, then the rigid local transform).
- `boundary`, `boundary_status` (`inference` when taken from a CAD layer,
  `verified_fact` only after a human confirms it) and
  `boundary_source_ref` (source id, entity handle and layer);
  `buildable_envelope` with a mandatory `basis` saying where it came from.
- `Terrain`: status, spot elevations and contours in the local frame, each
  with a `source_ref`, and an optional `TinSurface` (Delaunay triangles over
  surveyed vertices only; nothing is extrapolated outside their hull).
- `SiteFeature`: roads, driveways, easements, structures, utilities, trees, water,
  access points and `frontage` (boundary pieces within 0.5 m of a road,
  always an `inference`), each with point, polyline or polygon geometry.
- `site_verification_blockers(site)` lists every reason the site cannot be
  approved yet. Units, elevation units (when there are elevations), CRS
  and vertical datum must be confirmed by a human (or confirmed
  local-only); declared-in-source is not enough.

## Owner statements (`owner_statements`)

`OwnerStatementsFile` (id `owner-statements`, one new version per statement):
`OwnerStatement` items with a `subject` (e.g. `horizontal_crs`, `relief`), the
owner's `words` verbatim, `stated_by`, the `channel` it arrived through,
`recorded_by` (an agent may record), `recorded_at` and an optional
`pending_confirmation` (the step that would make it formal). A statement is
evidence only: it changes no confirmation status and clears no blocker
(ADR 0009).

## Brief (`design_brief`)

- `household`: members with role and age (`null` when not given).
- `facts`: `BriefFact` items with a topic (45 topics from the spec's
  interview list plus `levels`, `room_sizes`, `room_relationships` and
  `site_response`), a machine key, a statement, an optional value, an
  epistemic status, a MoSCoW priority and a source (owner answer, document,
  agent inference or default). An agent inference cannot be stored as a
  fact or a preference; an owner answer cannot be stored as an inference.
- `budget`, `target_gross_area_m2`, `contradictions` (each citing at least
  two facts, with a plain-language `tradeoff`, the `options` offered and,
  once resolved, the owner's `resolution` in their words),
  `interview_rounds_completed`.
- An interview-derived brief (`provenance.method: owner_interview`) has two
  kinds of fact (ADR 0008): `ans-<question>-<turn>` holds the owner's words
  verbatim (`owner_answer`); `f-<slot>` holds what was understood
  (`agent_inference` / `inference` until the owner confirms it, then
  `owner_answer` with ref `confirmed:<answer id>` or `resolution:<id>`;
  `unknown` when the owner does not know).

## Interview session (`interview_session`)

- `InterviewSession`: every `InterviewTurn` (answer, revision,
  confirmation, rejection, resolution, consent, program rejection) with the
  question as shown, the owner's words verbatim, what was `understood`
  (slot, value, method `parser`, `llm:<provider>` or `resolution`), the
  pending question, and a `SiteContext` (site version, `verified` only when
  the site gate approved that version, parcel area, relief, slope,
  frontage). Every turn needs a human actor. The brief is derived from the
  session; the session is the record of the conversation.

Companion files: `assumptions` (`AssumptionsFile`) and `open_questions`
(`OpenQuestionsFile`; a `blocking` open question blocks the program gate).

## Space program (`space_program`)

- `ProgramItem`: function, quantity, min/target/max area (ordered), minimum
  width, privacy, zone, level preference, priority, daylight need, whether
  it must be step-free (`accessible`), and the brief facts it derives from.
- `SpaceProgram` also records `levels` (floors wanted, or unknown), `budget`,
  and the `site_ref` it was checked against with `site_verified`.
- `AdjacencyRequirement`: `connected`, `adjacent`, `near`, `visual`,
  `separated`, `acoustic_separation`; `hard` (no weight) or `soft` (weight
  required). Endpoints are program items or `exterior`.
- `ProgramZone`, `target_gross_area_m2`, `circulation_factor`.

## Constraints and code packs

- `Constraint`: `hard` or `soft` (soft needs a weight), a typed `rule`
  (`no_overlap`, `within_envelope`, `valid_geometry`, `openings_on_walls`,
  `doors_connect_valid_spaces`, `traversable`, `min_area`, `min_dimension`,
  `adjacency`, `objective`), and a source. Objectives are always soft.
  Only code-pack constraints cite a code rule, and they must.
- `CodePack`: jurisdiction, authority, edition, effective date, source,
  rule ids, rules and verification status. Only a human can verify one.
- `ComplianceStatement`: `not_checked`, `conceptual_best_practice_only` or
  `checked_against_codepack`. `compliance_statement()` returns the strongest
  label the evidence supports; an unverified pack never yields a code check.

## The house model (`house_model`)

`HouseModel` is the canonical building. It names the local coordinate
system it is drawn in and pins `site_ref` and `program_ref`.

| Entity | Meaning |
|---|---|
| `Level` | Finished floor elevation (local z) and floor-to-floor height |
| `Space` | A room or area: function, level, boundary polygon (holes allowed), program item, zone, floor material |
| `Wall` | Straight centerline segment on a level, thickness, height, base offset, kind |
| `Opening` | Door, window or cased opening hosted by one wall: offset along the wall, width, height, sill, operation, and the two sides it connects (spaces or `exterior`) |
| `Slab` | Floor, roof, terrace or foundation polygon with thickness and top offset |
| `Ceiling` | Height above floor for a space |
| `Stair` | Footprint, kind, the two levels and the bottom/top spaces it joins, riser/tread data when known |
| `Zone` | Named group of spaces with a privacy class |
| `Fixture` | Typed fixture with position, rotation and footprint in a space |
| `SpaceRelationship` | Declared intent between two spaces (geometry decides whether it holds) |
| `CompositeSpace` | One physical open room partitioned into non-overlapping functional Space zones (e.g. open-plan living/dining/kitchen) |
| `MaterialRef` | Reference to a material by id, category and optional library URI |
| `assumptions`, `issues` | Assumptions and unresolved issues attached to this model |

Circulation is not stored. It is derived from passable openings and stairs
(`integrity.circulation_graph`), so it cannot disagree with the geometry.

## Concept proposals, plans, revisions and evaluations

Site reports retain `mean_slope_pct` as the horizontal-area-weighted mean over
the complete survey TIN. `parcel_mean_slope_pct` uses each triangle's exact
intersection area with the parcel, over `parcel_tin_area_m2` only, without
extrapolation. `SiteContext.mean_slope_pct` (interview/program context) uses this
parcel value; it is unknown without a covered parcel. See [ADR 0012](adr/0012-site-metric-scope.md).

- `ConceptProposal` (artifact kind `concept_proposal`): human or agent proposal
  structuring floor organization (`level_assignments`, `stair_cores`), zoning,
  outdoor links (`terrace`, `balcony`, `courtyard`), topology additions
  (`adjacency_graph`), and optional `target_strategy`. Validated deterministically
  before solving and recorded in provenance.
- `PlanVersion` (artifact kind `plan`, artifact id = `option_id`): label,
  strategy, parent version, the `ChangeRequest` that produced it, provenance,
  the `HouseModel` and, for generated plans, a `GenerationRecord`. The store
  assigns version numbers.
- `GenerationRecord` (Milestone D, optional; `null` for hand-authored plans):
  generator and solver names and versions, solver status and objective,
  seed, deterministic-time budget, the strategy parameters used (row depths,
  corridor width, level elevations, bar positions), one `RoomPlacement`
  (space, bar, row, start) per placed space, and the structured revision
  operations an agent applied (e.g. `area:pi-kitchen=16`). It lets a revision
  stay close to its parent and lets anyone reproduce the run.
- `ChangeRequest`: the owner's words verbatim, a kind (`modify`,
  `alternatives`, `restart_from_program`, `combine`, `other`) and the base
  plan versions. `combine` needs at least two.
- `RevisionReport`: requested change, geometry changed, rooms added,
  removed and changed, area changes, metric changes, new and resolved
  violations, assumptions.
- `EvaluationReport`: evaluator runs (ran, not run with a reason, failed),
  `MetricClaim`s (a not-checked metric has no value; a checked one must have
  one), `Violation`s with strength and status, and a compliance statement.

Generated plans use these conventions (see [ADR 0013](adr/0013-solver-backed-plan-generation.md)):
level ids `lv-entry`, `lv-down-<cm>`, `lv-up-<cm>` relative to the entry
level; space ids `sp-<item>` from program item ids (`-<n>` for quantities),
`sp-corridor-<bar>`, `sp-stair-<link><a|b>`, `sp-link-…`, `sp-gallery-…` and
`sp-flex-<row>` (flexible space not in the program); wall kinds `exterior`,
`interior` (also between split levels) and `retaining`. Terrain queries
(`domain.terrain`: `elevation_at`, `site_surface`) never extrapolate outside
the surveyed hull.

## Workflow records

- `WorkflowState`: the 15 states from the spec.
- `Gate`: `site`, `program`, `plan`, `model`, approving respectively a
  `site`, `space_program`, `plan` and `build_record` artifact.
- `Approval`: gate, pinned artifact, human approver (enforced by the
  schema), timestamp, statement and conditions.
- `WorkflowEvent`: one line of `events.jsonl` with sequence number, actor,
  type, states, reason, payload and the hash chain fields.
- `ProjectManifest`: identity only; the state comes from the events.
- `BuildRecord`: target (`blender`, `unreal`, `ifc`), the plan version it
  was generated from, tool, script and output file hashes.
- `AgentRoster`: role definitions; `may_approve` is fixed to `false`.

## Reviewer and visual critique records

- `RevisionOpsFile` (`revision_ops.schema.json`): Structured operations (`--area`, `--separate`, `--adjacent`, `--near`, `--level`, `--rethink`, `--strategy`, `--connect`, `--orientation`, `--daylight`) and entity-linked comments exported from the 2D reviewer UI or authored by agents, replayed via `house-ai plan revise-from-file`.
- `VisualCritiqueFile` (`visual_critique.schema.json`): Agent visual review records. Contains `VisualClaim` observations with element IDs grounded in a specific plan version, screenshot hash, claim text, epistemic status `ai_judgment`, severity, and suggested revision operations.


## Usability placements and derived checks (S6)

[ADR 0019](adr/0019-usability-geometry-and-assumptions.md) defines the geometry,
assumption sources and limits.

- `HouseModel.furniture`: explicit `Furniture` placements with stable ID, space,
  template ID, position, rotation and actual width/depth in metres. Fixed fixtures
  remain `Fixture`. Both participate in reference, footprint and overlap integrity
  checks. Proposed template fits are derived studies and never inserted in a plan.
- `HouseModel.clearance_zones`: explicit polygons referencing an element and space,
  with a purpose, basis and assumption status. They remain distinct from solids.
- `Stair.walking_line`: optional bottom-to-top 2D path; the generator emits it for
  straight flights. Its absence leaves run, landings and headroom unmeasured, and
  routes across the stair become inferred estimates (centroid-to-centroid run).
  With a walking line the flight footprint is not walkable floor on either level.
  Slab openings remain polygon holes. Headroom uses a linearly rising pitch line,
  not detailed geometry for intermediate landings of complex stairs.
- `SpaceProgram.usability`: optional household seats, vehicle envelopes, arrival
  path and bed variants by program item. Vehicle dimensions, side-door access and
  source are explicit; turning radius may be unknown. The program builder only
  derives household seats when adult and child counts are both supplied; stated
  older relatives are added (absent elders mean the program plans no elder room).
- `FurnitureTemplate`: individually cited `DimensionAssumption` records for body
  width/depth and four access margins. Front means local negative Y, for templates
  and for placed `Fixture`/`Furniture` rotation alike (the user side). Templates
  are exported as `furniture_template.schema.json`; library version 1.0.0.
- `MetricClaim.assumption_basis`, `Violation.method` and `Violation.assumption_basis`
  expose how a usability result was obtained. Usability findings are soft. Checked
  geometry and assumption-based feasibility retain separate claim statuses.

The eight added evaluators are `NetAreaEvaluator`, `DoorClearanceEvaluator`,
`StairUsabilityEvaluator`, `FurnitureUsabilityEvaluator`, `RouteUsabilityEvaluator`,
`PrivacyUsabilityEvaluator`, `DaylightOpportunityEvaluator` and
`VehicleArrivalEvaluator`. They run in normal evaluation reports and the benchmark
runner alongside the existing six evaluators. Full solar/daylight simulation and
life-safety/accessibility certification remain not run. Unknown inputs produce
null, not-checked metrics. The old straight-line walking estimate is replaced in
reports by a visibility-graph point route through actual room polygons and portals.

Empty/absent new fields are omitted during canonical serialization to retain
pre-S6 immutable hashes. Populated fields affect hashes normally; old project
artifacts and approvals are never rewritten.
