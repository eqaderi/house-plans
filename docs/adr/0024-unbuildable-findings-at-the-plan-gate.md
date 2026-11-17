# ADR 0024: Unbuildable findings at the plan gate

Status: accepted (Stage S10, ISS-29, closed 2026-10-19)

## Context

The plan gate refused approval only for integrity errors and hard violations.
Usability critics report their findings as soft, because most are matters of
judgement (a long route, a dark space). In the S9 readiness demonstration a plan
whose stair had 0.500 m of headroom under a slab, and a floor-to-floor height
that disagreed with the stair, went to plan review with 0 open reasons, and the
synthetic owner could approve it. A stair that cannot be walked is not a matter
of judgement.

## Decision

A named set of findings keeps the plan gate closed whatever their strength
(`PLAN_GATE_BLOCKING_CODES`): `stair_low_headroom`, `stair_wall_clash`,
`stair_run_does_not_fit`, `stair_height_mismatch`, `stair_nonascending_levels`,
`stair_walking_line_invalid`, `stair_landing_blocked` and
`floor_connection_height_mismatch` (stacked storeys, ADR 0023). Each appears in
`plan review` as `OPEN unbuildable <code> …`, and `workflow approve` refuses the
plan while any remains. The fix is a new plan version, not an override: an owner who
disagrees with a finding has the evaluator's assumption changed with a stated
basis, in its own decision.

Findings the owner should see but that do not block are listed as
`ATTENTION …` in the plan-review event (`attention`) and on the command line
(`PLAN_REVIEW_ATTENTION_CODES`). The first is `height_limit_exceeded` while the
envelope height is not a verified fact; once it is, the finding is hard and
blocks as before (ADR 0022).

## Consequences

- A plan with a stair that cannot be walked as drawn cannot be approved.
- The gate's rule is code-based: adding a critic that finds another unbuildable
  condition needs it added to the set, recorded here.
- Engineering findings (`needs_professional_*`) stay outside the gate: they are
  always present for hillside plan options and are resolved by professionals after
  plan approval (PROFESSIONAL_HANDOFF).
