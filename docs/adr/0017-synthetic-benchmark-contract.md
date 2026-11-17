# ADR 0017: Synthetic benchmark contracts and observed expectations

Status: accepted (Stage S3, closed 2026-10-17)

## Context

S3 needs reusable inputs and known answers for S4–S9. Existing golden
examples test particular pipelines; they do not declare acceptance categories,
household scenarios or unimplemented checks. Passing a regression must not be
mistaken for evidence that a floor plan is good architecture.

## Decision

`domain.benchmark.BenchmarkFixture` composes canonical `Site`, `SpaceProgram`
and optional `HouseModel` cases. It is exported as JSON Schema but is not a
ProjectStore artifact kind. Benchmarks never create approvals, alter a real
project, or introduce a second architectural representation.

Each expected finding selects a named metric or finding code, its source,
target and optional subjects, expected value/count, evidence status, absolute
tolerance and analytical basis. Ten acceptance categories are explicit. Fixture
and expectation IDs are unique; private sites and unresolved targets are
rejected. Cases pin the exact site and program content hashes at version 1.

The development harness (`house_ai.benchmarks`) composes the existing site
builder, site validation, integrity and evaluation boundaries read-only. It
also observes declared program requirements, labelled `program_requirement`;
those checks establish scenario inputs, not evidence of a usable design.
It rebuilds site TINs from the observations and compares results to independently
declared formulas. It never uses expected values as observations.

Outcomes have distinct meanings:

- `PASS`: the observation matched, including intentional negative cases.
- `FAIL`: wrong value or status, absent or ambiguous observation.
- `NOT_CHECKED`: an explicitly declared future probe, with its responsible
  stage and reason. This is never a passing check. `--require-complete` fails
  if any remain; the default regression command fails on mismatches only.

An implemented metric whose correct value is unknown can separately be tested
for `status=not_checked`, `value=null`. For example, local Cartesian axes
establish no geographic north. The site's existing grid/true orientation
outputs must stay unknown; solar/daylight studies remain future work.

`examples/benchmarks/make_fixtures.py` deterministically writes fictional
Cartesian metre sites and programs. The steep reference is 19.2 × 31.25 m
with `z=12.5-0.4y`: area 600 m², relief 12.5 m, area-weighted slope 40%.
It has no geographic CRS or survey origin. Existing human-authored synthetic
bungalow geometry supplies checked reference cases and explicitly seeded
defects. No generated plan is presented as an approved design.

Preference comparisons evaluate the same two fixed reference layouts on the
same site under opposite cooking relationships. They show space
relationship satisfaction and kitchen area separately. They do not demonstrate solver
diversity or compute a single architectural quality score.

## Consequences

Later stages can consume typed fixtures and add actual probes without silently
turning missing capability into success. Generated JSON is larger because
each fixture is self-contained, but regeneration and drift checks are simple.
Adding the benchmark schema does not change project artifact schemas or
introduce runtime dependencies. Versioned solver revisions, visual review,
full usability and hillside support remain their scheduled stages.
