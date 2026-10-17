# ADR 0001: One canonical semantic house model

Status: accepted (Milestone A, 2026-10-17)

## Context

The product has to show the same house as a 2D plan, a BIM export, a Blender
scene and an Unreal walkthrough, and the owner revises it many times. If any
of those views can be edited on its own, they drift apart and nobody knows
which one is the design. LLM-generated images and freehand coordinates make
this worse because they cannot be checked.

## Decision

- `house_ai.domain.model.HouseModel` is the only source of truth for the
  building. It is structured semantic data: levels, spaces with polygons,
  walls as centerlines, openings hosted by walls and connecting named
  spaces, slabs, ceilings, stairs, zones, fixtures, relationships and
  material references, all in one local metric frame with stable ids.
- Every other representation (SVG, IFC, Blender, Unreal) is generated from a
  specific `PlanVersion` and records which version in a `BuildRecord`.
  Changes are made to the canonical model and re-derived, never made in a
  derived view.
- Derived facts that could disagree with the geometry are not stored.
  Circulation is computed from openings and stairs, and areas from
  polygons.
- A model is only accepted at the plan gate if the deterministic integrity
  checks pass on it at approval time.
- Polygons support holes, and walls are general segments, so courtyards and
  non-orthogonal plans fit later without changing the model.

## Consequences

- Generators (solver, LLM topology proposals) must output canonical
  objects. They cannot hand back pictures.
- IFC is a mapping target, not the internal model. This keeps us
  independent of proprietary formats, at the cost of writing and testing
  the mapping ourselves.
- Wall-to-space relationships are geometric (an opening probes both wall
  faces), which keeps the data small but makes the integrity checks
  responsible for consistency.
