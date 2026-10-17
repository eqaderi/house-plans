# ADR 0004: Repository layout additions to the spec's suggested tree

Status: accepted (Milestone A, 2026-10-17)

## Context

MASTER_SPEC suggests `src/house_ai/{cad, geospatial, interview, program,
constraints, generation, evaluation, render2d, bim, blender, unreal,
providers, orchestration, cli}`. It has no obvious home for the canonical
schemas shared by all of them, for project storage, or for the workflow
state machine.

## Decision

- Add `house_ai/domain/` for every canonical schema and the pure functions
  on them (units, geometry, coordinate frames, integrity checks, compliance
  language, schema registry). Schemas are not split across feature packages
  because "one model" is easier to keep coherent when it lives in one
  place, and so that the domain depends on nothing else.
- Add `house_ai/storage/` for the project store, hashing and importer.
- Put the workflow state machine in `house_ai/orchestration/workflow.py`,
  where agent composition will also live.
- Keep every suggested package. Packages for later milestones contain a
  docstring and, where a boundary matters now (`cad`, `generation`,
  `evaluation`, `providers`), a `Protocol` in `base.py`. No placeholder
  logic.
- Keep the old `house-plans` tool's history in git. Milestone A starts from
  an empty tree (commit `bf50e60` removed the previous toolchain).

## Consequences

- Feature packages import from `house_ai.domain`, never the other way.
- The JSON Schemas in `schemas/` are generated from `domain/` only.
