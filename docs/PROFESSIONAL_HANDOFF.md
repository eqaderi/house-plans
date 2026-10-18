# Professional handoff

HOUSE DESIGN AI produces design-exploration material with AI assistance.
This page tells architects, engineers and authorities what they are looking
at and what has not been done.

## What the output is

- A canonical, structured house model (levels, spaces, walls, openings,
  slabs, stairs, fixtures) in metres, in a local frame tied to the site's
  coordinate reference system, with stable ids and full version history.
- A record of who decided what: the owner's brief and program, every plan
  version and change request, the evaluations run, and the owner's
  approvals, all in an append-only, hash-chained event log.
- For every claim, how it is known: verified fact, inference, assumption,
  preference, simulation result or professional approval. For every
  metric, whether it was measured, inferred, simulated, judged by AI or not
  checked.

## What it is not

Unless a qualified professional or an authority has recorded otherwise in
the project, the output is not:

- permit-ready or construction-ready;
- structurally designed or certified;
- checked for code compliance (only "not checked" or "conceptual
  best-practice check only" can appear without a verified code pack);
- MEP-engineered;
- geotechnically verified.

The owner's approvals in this system mean the owner chose this direction.
They are not professional approvals.

## What to check first

1. **Site truth.** The survey's units, CRS and vertical datum were confirmed
   by the owner, not by a surveyor. Check them against the original file
   preserved under `source/` (its SHA-256 is recorded).
2. **Assumptions.** Read `assumptions` and each plan's `assumptions`. Items
   such as setbacks and wall thicknesses are placeholders until a
   professional confirms them.
3. **Open questions and issues.** Unresolved items are listed, not hidden.
4. **Areas.** Room polygons and SVG labels use wall centreline areas. S6 reports
   derived net areas from the actual wall thicknesses and floor-level openings;
   incomplete wall models are flagged. Net bounding dimensions do not prove
   furniture fits a concave room.

## Exporting for review

Milestone A provides the structured project record (`house-ai project
status --json`, the artifacts under `artifacts/`, and the JSON Schemas in
`schemas/`). Milestone D adds, per plan concept and version, `plan.json`
(the canonical model), a dimensioned `plan.svg` with a true terrain
section, `metrics.json`, `violations.json`, `assumptions.json` and
`explanation.md`, plus `comparison.md` across concepts (`house-ai plan
export`). They are solver-generated explorations: stair geometry, wall
thicknesses, floor-to-floor heights, garage depth and retaining walls are
typical placeholders, and cut, fill and retained-earth figures are
interpolated from survey points, not geotechnical findings. IFC, Blender and
Unreal exports arrive in later milestones and will each record the plan
version they were made from.

## Hillside review material (S8)

Every concept export adds true `sections.json/svg`, projected
`elevations.json/svg`, `hillside.json` and `engineering-risks.md`. These list
structure, foundations, retaining, drainage, waterproofing and slope
stability as **needs professional**, with element IDs and observed triggers.
Read the complete register before choosing a sectional approach.

Cut, proposed engineered fill and underfloor void are distinct quantities.
They integrate the piecewise planar TIN against slab undersides where
provided; missing slabs use labelled finished-floor upper bounds. Fill
requires explicit formation pads. Unknown footprint, pad and section support
stays unknown. Exact integration for a TIN does not make the terrain exact
between survey observations. These are conceptual geometric quantities,
not construction estimates: footings, temporary works, excavation batter,
working space, soil bulking, compaction and ground improvement are excluded.
Deep excavation is an acceptable comparison option, with no default depth
penalty; large voids use a configurable review trigger (default 4 m).

Door thresholds use terrain 0.5 m outside the door. Garage grades describe a
straight candidate frontage approach; turning, ramps, vertical curves,
headroom, discharge and legal access require design and verification. Terrace
profiles show contact opportunities without claiming traversable garden
access. Unknown stair flight orientation remains unknown in true cuts.
Facade views project canonical walls/openings in LOCAL axes and do not
resolve hidden geometry. No professional suitability is implied by a green
integrity result or homeowner approval.
