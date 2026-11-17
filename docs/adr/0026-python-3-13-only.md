# ADR 0026 — Support and test Python 3.13 only

Date: 2026-11-17. Status: accepted. Supersedes the Python 3.11 support stated
in Milestone A (task A-05) and the "wheels for Python 3.11 and 3.13" point in
[ADR 0013](0013-solver-backed-plan-generation.md).

## Context

The project is personal-first ([ADR 0009](0009-personal-first-project-folders.md)):
it exists to design the owner's own house, and the owner runs Python 3.13.
Until now `requires-python` was `>=3.11` and CI ran the full test suite on
both 3.11 and 3.13. On this private repository every CI minute is billed, and
each test job takes about 15 minutes per push, so the 3.11 job doubled the
cost for a version nobody uses. The exact lock (`requirements-lock.txt`)
already did not install on 3.11 (numpy 2.5.4 has no cp311 wheels), so 3.11
was tested against looser dependency ranges than the owner actually runs.

## Decision

- `requires-python = ">=3.13"`; ruff `target-version = "py313"`.
- The CI test matrix runs Python 3.13 only.
- The agent contract and README state Python 3.13 only.
- Historical records (milestone reports, closed tracker stages, S3 tool
  evaluation results) keep their 3.11 mentions; they record what was true then.

Rejected: keeping 3.11 in CI on a schedule only (still billed, still a version
nobody runs); moving the floor to 3.12 (also untested, same cost argument).

## Consequences

- Code may use Python 3.12 and 3.13 language and standard-library features,
  and ruff's pyupgrade rules now target 3.13.
- Anyone on Python 3.11 or 3.12 must upgrade to 3.13 to install the package.
- CI test minutes per push are roughly halved.
- Adding another supported version later needs a new ADR and a CI matrix entry.
