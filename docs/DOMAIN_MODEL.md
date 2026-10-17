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
| Areas | Milestone A space polygons are drawn to wall centerlines, so areas are centerline areas. Net areas are a later derived quantity. |

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
- `SiteFeature`: roads, easements, structures, utilities, trees, water,
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
  interview list), a machine key, a statement, an optional value, an
  epistemic status, a MoSCoW priority and a source (owner answer, document,
  agent inference or default). An agent inference cannot be stored as a
  fact or a preference; an owner answer cannot be stored as an inference.
- `budget`, `target_gross_area_m2`, `contradictions` (each citing at least
  two facts), `interview_rounds_completed`.

Companion files: `assumptions` (`AssumptionsFile`) and `open_questions`
(`OpenQuestionsFile`; a `blocking` open question blocks the program gate).

## Space program (`space_program`)

- `ProgramItem`: function, quantity, min/target/max area (ordered), minimum
  width, privacy, zone, level preference, priority, daylight need, and the
  brief facts it derives from.
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
| `MaterialRef` | Reference to a material by id, category and optional library URI |
| `assumptions`, `issues` | Assumptions and unresolved issues attached to this model |

Circulation is not stored. It is derived from passable openings and stairs
(`integrity.circulation_graph`), so it cannot disagree with the geometry.

## Plans, revisions and evaluations

- `PlanVersion` (artifact kind `plan`, artifact id = `option_id`): label,
  strategy, parent version, the `ChangeRequest` that produced it, provenance
  and the `HouseModel`. The store assigns version numbers.
- `ChangeRequest`: the owner's words verbatim, a kind (`modify`,
  `alternatives`, `restart_from_program`, `combine`, `other`) and the base
  plan versions. `combine` needs at least two.
- `RevisionReport`: requested change, geometry changed, rooms added,
  removed and changed, area changes, metric changes, new and resolved
  violations, assumptions.
- `EvaluationReport`: evaluator runs (ran, not run with a reason, failed),
  `MetricClaim`s (a not-checked metric has no value; a checked one must have
  one), `Violation`s with strength and status, and a compliance statement.

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
