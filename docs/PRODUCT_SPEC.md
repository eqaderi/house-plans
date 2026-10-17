# Product spec (summary)

The authoritative specification is [MASTER_SPEC.md](MASTER_SPEC.md). This
page is a short summary for orientation.

## What it is

HOUSE DESIGN AI helps a homeowner who is not an architect explore the
design of a real house on a real, surveyed site. It is a design-exploration
and decision-support tool. It produces structured, checkable geometry and
hands it to qualified professionals; it does not produce permit or
construction documents.

## Workflow

survey → verified site → owner interview → approved program → adjacency
concepts → alternative floor plans → evaluation → human iteration →
approved plan → semantic/BIM model → Blender → Blender validation → Unreal →
walkthrough.

A human explicitly approves four things: site truth, the program, the final
floor plan, and the Blender model before Unreal production.

## Product rules

- One canonical semantic model; every view is derived from it.
- Hard constraints make a plan invalid; soft objectives are scored
  individually, never folded into one opaque score.
- Every claim carries provenance and says whether it was measured, inferred,
  simulated, judged by AI or not checked.
- Unknown facts stay unknown. The CRS is never guessed from coordinates.
- No "code compliant" claim without a loaded, verified code pack for the
  jurisdiction and edition.
- Private survey and owner data stay local unless the owner explicitly
  allows a specific provider.
- Works with any AI provider; the domain has no vendor dependency.

## Milestones

| | Scope | Status |
|---|---|---|
| A | Repository, canonical schemas, project storage, provenance, workflow state machine, tests | done, see [milestones/A.md](milestones/A.md) |
| B | Synthetic DXF, CAD inspection, layers, units, CRS confirmation, boundary, terrain, site SVG | next |
| C | Interview engine, brief, program, adjacency graph, program approval | |
| D | Constraint model, 3+ alternative plans, SVG, evaluators, plan versioning | |
| E | Web reviewer: options, metrics, version comparison, change requests | |
| F | Deterministic Blender generator, renders, geometry validation | |
| G | FBX, scene manifest, Unreal importer, first-person walkthrough | |
