# ADR 0002: Pydantic models as schema source, JSON Schema exported

Status: accepted (Milestone A, 2026-10-17)

## Context

Agents from several vendors, the Python pipeline and a future web reviewer
must all agree on the data. We need runtime validation in Python and a
language-neutral schema for everything else.

## Decision

- Pydantic v2 models in `house_ai.domain` are the source of truth. They
  carry the cross-field rules that JSON Schema cannot express (CRS EPSG
  only when confirmed, soft constraints need weights, approvals need a
  human, contradictions cite existing facts, and so on).
- Every persisted model forbids unknown fields and rejects NaN and
  infinity. Datetimes must be timezone-aware and are normalised to UTC.
- `house-ai schemas export` writes JSON Schema (draft 2020-12) for every
  registered schema to `schemas/`. Those files are committed.
  `test_committed_schemas_match_the_code` and `house-ai schemas check` fail
  when they drift.
- Pydantic is pinned to an exact version because its schema output can
  change between releases.

## Consequences

- Non-Python consumers get structural validation only. The cross-field rules
  are enforced when data passes through the Python store, which is the only
  sanctioned write path.
- A schema change is a code change plus a regenerated, reviewed diff in
  `schemas/`.
