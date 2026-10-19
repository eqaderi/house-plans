# ADR 0019 — Canonical placements and derived usability studies

Date: 2026-10-18. Status: accepted for S6; revised after S6 review 1. The owner read
this ADR on 2026-10-18 ("I read 0019-usability-geometry-and-assumptions.md") and
requested no changes (task S6-02).

## Decision

Placed `Furniture` and explicitly declared `ClearanceZone` polygons belong to
`HouseModel`, with stable IDs and integrity-checked references. Furniture has a
template ID, space, position, rotation, width and depth. Existing fixed `Fixture`
elements keep their meaning. A clearance zone records its purpose and assumption
basis. Template dimensions and automatically searched arrangements are derived
studies, never canonical placements. No critic edits a plan or places furniture
on the homeowner's behalf. The generator learns to avoid findings in S7.

`SpaceProgram.usability` optionally records household seats, requested vehicle
envelopes, an arrival polyline and bed variants by program item ID. Null vehicle
data means unknown; an empty vehicle list explicitly requests none. The program
builder carries the sum of explicitly supplied adult and child counts, plus stated
older relatives, into seats; it does not assume a missing child count is zero or
infer vehicle dimensions. Without an elders count the program plans no elder bedroom,
so no elder is seated either.
The plan/program references preserve the input provenance of these studies.

Stairs optionally carry a walking line ordered bottom to top; the generator emits the
centre line of each straight flight (U-shaped flights have none). Slab voids use the
existing `Polygon2D.holes`; a second opening representation is unnecessary.

The front (user side) of every template, `Fixture` and `Furniture` is its local
negative Y before rotation. The synthetic bungalow's WC, basin, shower and sink were
re-authored to face their rooms under this rule; only `rotation_deg` changed, not
footprints.
`SiteFeatureKind.DRIVEWAY` distinguishes drive surfaces from roads. Metrics and
violations optionally carry `assumption_basis`; violations also carry `method`.
All new usability findings are soft and confer no CodePack/professional approval.

Absent/empty S6 additions are omitted by model serializers so that existing
canonical hashes, immutable records and pinned approvals remain readable. Nonempty
new data participates in hashes. This is an additive schema change; old artifact
files and approval records are not migrated or rewritten. Schemas and generated
reviewer types describe the optional additions.

## Geometry and measurement basis

- Net floor subtracts actual wall solids (half the thickness on each side of each
  centreline), with floor-level passable apertures removed from those solids. A wall
  end that meets another wall's end is extended by half its thickness, closing the
  notch a butt joint leaves at a reflex corner. Explicit floor/terrace slabs of the
  level, at any top offset, bound the supported floor and exclude their voids. The
  aperture recess contributes to the adjacent room up to the centreline. Missing wall
  edges produce an incomplete-basis finding and the net area becomes `inferred` (an
  upper bound). Net dimension metrics are enclosing rectangle extents, not a promise
  a concave room fits a rectangle; an empty net floor reports them not checked.
- Door handedness is viewed along wall start to end: left hinges at the near
  opening end, right at the far end. `opens_into` selects the swing side. Double
  swing means two half-width hinged leaves, not a double-action pivot. Sweep
  polygons use 0.5° angular sampling and conservative outward buffering. Both
  sides receive an approach rectangle measured from the wall's finish face; sliding
  doors have approach zones and no hinged sweep. Missing hinge-side information is
  not checked.
- Fixed/placed object access envelopes may overlap other clear envelopes, but
  cannot hit another object's body or leave the net floor. Door sweeps are kept
  out of access envelopes; door approaches are kept out of proposed solid bodies.
- Furniture studies work in the room's own frame (its longest boundary edge), so a
  verdict does not change when the plan is rotated. They search four orthogonal
  rotations over a 0.1 m translation grid plus placements aligned with every finish
  face (door recesses widen the bounds, so bounds alone misalign the grid). Templates
  with equal body and margin dimensions are interchangeable whatever their IDs (e.g.
  two cars), and a body-area bound rejects impossible sets. The
  search stops after 200,000 candidate placements: the study is then `not_checked`
  with method `search_budget_exhausted_before_decision`, never a failed fit. A failed
  study means no arrangement in that search, not continuous infeasibility. No
  ergonomic certificate follows from finding a placement. Results are cached by
  geometry and dimension content, never by project name. A bedroom the program does
  not designate must hold a single bed and wardrobe; its double-bed study is reported
  as information without a finding.
- Kitchen aisles are the clear distance between placed runs whose fronts face each
  other (each sees the other's body within 3 m ahead); narrower than the assumed
  aisle is a finding. Without a facing pair the aisle is not checked.
- Routes use a per-space visibility graph over net-floor polygons with fixture,
  furniture and (where a walking line is declared) stair-flight obstacles, including
  concave vertices and hole vertices. Only explicit passable portals join rooms;
  a door with a threshold joins at the nearest finish-face point on each side.
  Exterior exits are not interconnected. Stairs with a walking line join their
  ordered endpoints with pitch-line 3D length. A stair without one, but with riser
  data, joins the free-floor points nearest its footprint centroid with an
  estimated hypot((risers − 1) × going, rise); any route using it is `inferred`.
  Representative room points are the named destinations. Routes measure point paths;
  body width, escape and wheelchair certification are outside this check. The
  maximum entrance route is reported only when every space is reached: measured,
  or inferred if an estimated stair is used. Generated plans carry ~1e-7 m
  coordinate noise, so geometric tolerances are 1e-5 m (a numerical choice).
- Stored riser heights have four decimals, so the riser total may differ from the
  level rise by up to half a unit per riser before a height mismatch is reported.
  A level's floor-to-floor height is compared only for a stair to the next level up
  that arrives over the lower storey (ADR 0023 narrows this rule).
- A stair needs `(riser_count − 1) × going` in the declared walking line and a
  width strip contained in its footprint. Arrival/departure strips extend outward
  from the ordered endpoints. Headroom is the minimum separation between a
  linearly rising pitch line and each intersecting slab underside, respecting
  slab holes. Stair direction, missing riser metadata and absent intersecting
  slabs stay explicit unknowns. This is a straight-flight/pitch-line study;
  intermediate landing elevations of complex stairs are not resolved.
- Dead-end length is the farthest net-corner point path for a corridor with one
  portal. Multi-portal branching dead ends are not classified by this heuristic.
  Narrow residual floor is measured by morphological opening. Desire lines across
  central work/seating zones are warnings about possible traffic, not proof that
  people must take that route. Bathroom visibility assumes open doors and tests
  wall-occluded rays from representative shared-space points.
- Noisy activity touching/stacking with sleeping space is a geometric privacy
  warning. It does not predict sound transmission through unknown assemblies.
- Window-capable wall length uses exterior, non-retaining faces with terrain
  below an assumed sill at 0.25 m sample spacing. Glazing exposure uses three TIN
  samples per window. Interpolated quantities are inferred, never extrapolated;
  missing/mismatched terrain frames remain not checked. Different operable facade
  normals indicate ventilation opportunity only. There is no airflow, solar or
  daylight simulation and no invented orientation when north is unknown.
- Outdoor door threshold is compared with TIN grade just outside its host wall.
  A grade warning asks for a landing/ramp review, without inferring either exists.
- Vehicle arrival requires polygon road/drive surfaces, a requested arrival path,
  vehicle dimensions and turning radius. Each corner of the path is replaced by a
  circular arc of the turning radius (taken as the centreline radius); if an arc's
  tangent length does not fit its legs (interior legs shared by two corners) the
  turn fails. The bounding circle of the vehicle is swept along that filleted
  centreline and must stay on the surfaces. It is not a steering/tyre swept-path
  simulation. Missing data is not checked.

## Sources and configurable planning assumptions

These are deliberately selected conceptual study values, not universal minima.
Every template dimension records `status: assumption`, a rationale and source.
The source of independently chosen illustrative sizes is **this ADR**. A cited
precedent does not adopt that jurisdiction, edition or standard for a project.
No source fetch is needed at runtime or in tests.

| Assumption | Default | Basis |
|---|---|---|
| Rise range; going; headroom | 0.15–0.22 m; 0.22 m; 2 m | Selected study bounds using [England Approved Document K, 2013](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/996860/Approved_Document_K.pdf), Table 1.1 and §1.11 as precedent |
| Stair width, landing strip, door approach | 0.9 m each | Project planning assumption; these simplified rectangles do not implement ADA manoeuvring rules |
| Double bed / single bed bodies | 1.6×2 m / 0.9×2 m | Illustrative project furniture |
| Double-bed side access / foot access | 0.6 m each / 0.75 m | Project planning assumption; single bed uses one access side and 0.6 m foot space |
| Wardrobe / desk body and access | 1.2×0.6 m; 0.9 m front | Project planning assumption |
| Dining reference table / chair and passage envelope | 1.8×0.9 m; 0.9 m around | [IKEA six-seat table examples](https://www.ikea.com/gb/en/cat/6-seater-dining-tables-21827/) provide scale; clearances are project assumptions |
| Household table sizing | 0.6 m per place, two end places; width ≥1.2 m | Project packing assumption; household seats supplied in program |
| Kitchen run / depth / aisle | 3 m / 0.6 m / 1.219 m | Run and depth are project assumptions; the run's front access and the aisle between facing placed runs use the multiple-cook precedent in [NKBA guideline 6](https://media.nkba.org/uploads/2022/05/Kitchen-Planning-Guidelines.pdf) |
| WC, basin, shower, bath | 0.4×0.7, 0.6×0.5, 0.9×0.9, 1.7×0.75 m | Illustrative project fixture bodies, with 0.75/0.7/0.6/0.6 m front access; [Access Board guide](https://www.access-board.gov/ada/guides/chapter-6-toilet-rooms/) motivates separate fixture/door checks, not these dimensions |
| Vehicle reference / shelf / laundry and folding | 1.8×4.5 / 1.2×0.45 / 1.8×0.65 m | Project template assumptions; garage evaluation requires program-supplied vehicles, not the reference vehicle |
| Garage front/rear access; vehicle sides | 0.9 / 0.3 m; program-supplied sides | Project planning assumption |
| Turning circle | 1.5 m diameter | Project conceptual screen, not an accessibility certification |
| Excess circulation / long dead end / long daily route | 25% / 6 m / 15 m | Project heuristics |
| Narrow residual width / residual share | 0.9 m / 50% | Project morphology heuristic |
| Central work-zone inset / traffic intersection | 0.75 m / 0.1 m | Project desire-line heuristic; explicit canonical clear zones take precedence |
| Potential sill / glazing ratio / facade separation | 0.9 m / 10% / 45° | Project opportunity heuristics, not daylight or ventilation compliance |
| Outdoor threshold-to-grade warning | 0.2 m | Project conceptual warning |

The remaining template bodies (chair, sofa group and appliance) and access margins
are individually stated in `evaluation/templates.py` and exported in the demo's
`report.json`. They are illustrative assumptions from this ADR. `UsabilityPolicy`
overrides thresholds; invalid/nonfinite or inverted bounds are rejected. Geometry
tolerances and sampling resolutions are numerical choices, not architectural rules.

## Review and consequences

Hand-check: a 4×3 m centreline room bounded by 0.15 m partitions has
`(4−0.15)×(3−0.15) = 10.9725 m²` net floor before doorway recesses. An L route
from (5,1) to (1,5), around (2,2), is `2√10 = 6.324555… m`. A 2.6 m wide
centreline room has 2.45 m clear width: neither orientation of the assumed double
bed's 2.8×2.75 m envelope fits; its 3.4 m wide clean twin can hold bed and wardrobe.
Automated analytical and seeded/clean tests live in `tests/benchmarks/`.

These critics expose current generator shortcomings. They do not make existing
concepts good architecture, approve a design, or populate the missing physical
data. Furniture drawing/picking in the reviewer and avoidance in generation
remain later S7 work. Existing SVG gross labels keep their centreline basis;
the report exposes both net and gross metrics.
