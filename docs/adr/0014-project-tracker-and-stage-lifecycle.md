# ADR 0014: One project tracker and a reviewed stage lifecycle

Status: accepted (stage T0.1 closed by the owner, 2026-10-17, merge `7a41629`)

## Context

Milestones A to D are merged (`a9b68fe`). What comes next was spread over
milestone reports, `MILESTONE_D_HANDOFF.md` (since removed), the README and chat history,
and several of those disagree (see the tracker's open issues). Three coding
agents (Claude Code, Codex, Gemini/Antigravity) work on the repository in
separate sessions with no shared memory. The owner should not have to
reconstruct the roadmap, and an agent's report that work passed is not
evidence that it did.

The owner also changed the implementation order on 2026-10-17: excellent
2D floor plans on the steep site come before Blender, IFC and Unreal. The
MASTER_SPEC mission (survey to walkthrough) is unchanged; only the order of
work after Milestone D changes.

## Decision

1. `docs/PROJECT_TRACKER.md` is the single roadmap, task register, stage
   lifecycle and progress record. No other TODO, roadmap or stage-status
   file is kept. MASTER_SPEC stays the product authority; the tracker turns
   it into stages and tasks and links to it instead of repeating it.
2. Work is done in stages. A stage has its own branch
   (`stage/<ID>-<slug>`), scope, acceptance criteria and required tests.
   Implementation status (`NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`,
   `DEFERRED`) is kept separate from review status (`NOT_REQUESTED`,
   `PENDING`, `CHANGES_REQUESTED`, `APPROVED`).
3. The owner drives the lifecycle with four phrases, defined in the tracker
   (§O) and pointed to from AGENT_CONTRACT §10: "Project status", "Next
   stage", "Review stage <ID>", "Close stage <ID>". An implementer stops
   after pushing its branch; an independent reviewer (preferably another
   agent or model) records a verdict on the branch; "Close stage" merges
   only an APPROVED, current commit and is the owner's merge authorisation.
4. A task is `DONE` only with evidence, and only once its stage is closed
   on `main` (work merged before this ADR counts as closed).
   `tools/check_tracker.py` (run by `tests/test_project_tracker.py`) checks
   the tracker's format, IDs, dependencies, checkbox/status agreement and
   that no `DONE` task lacks evidence.
5. Implementation order after Milestone D: governance and safety fixes,
   agent skills, the interactive reviewer (MASTER_SPEC Milestone E), agent
   visual inspection, usability critics, flexible generation, hillside
   geometry, benchmarks, then a floor-plan readiness gate before the real
   house is designed. Blender (F), IFC and Unreal (G) are deferred, not
   removed.
6. Software-stage closure never implies the owner's approval of a site,
   program, plan or model; those stay the four human gates of AGENT_CONTRACT
   §8.

## Consequences

- A fresh agent session can resume from the repository alone.
- Every stage costs one extra review pass; that is the point.
- The contract stays below the 12,000-character limit of ADR 0005 by
  keeping the full protocol in the tracker; the contract only points to it.
- Stale documents found while creating the tracker are recorded as open
  issues and fixed in stage T0.4 rather than silently rewritten.
