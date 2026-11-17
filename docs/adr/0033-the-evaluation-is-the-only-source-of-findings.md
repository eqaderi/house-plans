# ADR 0033: The Evaluation is the only source of Findings about a Plan version

Status: accepted (2026-11-17).

## Context

Findings about a Plan version came from two places. The Evaluation (ADR 0013,
ADR 0019) is what the plan gate, the comparison and the revision report read.
Beside it, `validation/defect_detectors.py` (Stage S5, S5-07) repeated
evaluator rules through private imports (`evaluation.usability._pitch`,
`render2d.plan_svg._rect_dims`), added a `DefectFinding` type, and was called
by nothing outside tests, the readiness demonstration and the visual-review
loop.

- Its label-overlap check rebuilt the drawing's label boxes with its own scale
  (spaces only, never the Site boundary the drawing shows), its own padding and
  a centre-distance rule the drawing does not have, so it disagreed with what
  the Owner sees.
- Its stair-through-slab check used the fixed 2.0 m headroom constant and
  ignored the usability policy the stair evaluator honours.
- Fix verification (`orchestration/visual_review.py`, S5-09, S5-10) compared
  detector output, and its loop function `apply_visual_critique_loop` was
  called by nothing. The reviewer demonstration's "verified fix" was a hand
  edit that the Evaluation shows to be broken (a 1.2 m window at 1.0 m along a
  2.0 m wall, opening onto a Space the plan does not have, moved onto an
  interior wall already filled by an opening).

## Decision

- **The Evaluation is the only source of Findings about a Plan version.**
  Every Finding comes from an evaluator (or from `check_model` through the
  geometry evaluator) and says how it was obtained.
- **One label layout** (`render2d/labels.py`): the room labels, their text
  lines and the drawing scale (every Space, and the Site boundary when there is
  one, plus 2.5 m) are computed once. The plan drawing draws them (its output
  is unchanged) and `evaluation/drawing.py`'s `LabelCollisionEvaluator`
  reports overlapping labels on one Level as `label_collision`, soft,
  `measured`, method `drawing_label_layout`. It never closes the plan gate.
  The evaluation package imports the 2D rendering package for this one pure
  layout function, as it already imports `geospatial`.
- **What a revision fixed is checked, not assumed** (`evaluation/findings.py`).
  `PlanService.revise` compares the Findings of the parent's Evaluation and of
  the new one for the ids the request targeted
  (`generation.revision.targeted_ids`: each name an operation gives, the Spaces
  a requirement or a Zone means, every Space for `rethink:all`). The outcome
  carries three lists: disappeared, remaining, new; `plan revise --json` prints
  them as `findings`, and `revision.md` lists them. Two Findings are the same
  when their code and cited ids are. A Finding of the parent that the new
  Evaluation lacks has disappeared only when something it cites changed
  (an element moved, reshaped or removed; a Space gained or lost an opening;
  a Space requirement's Spaces changed); otherwise it remains, because the
  parent's Evaluation may come from an earlier evaluator. The stored
  `RevisionReport` artifact is unchanged.
- **The detectors that repeated evaluator rules are deleted**, with
  `DefectFinding` and the `DEFECT_*` constants. Each seeded defect is a Finding
  of the Evaluation or of the integrity check: a window in a retaining wall is
  `window_buried` from `DaylightOpportunityEvaluator`, measured from the wall's
  kind (no terrain needed, any room; method `host_wall_is_retaining`); a stair
  through a slab is `stair_low_headroom` from `StairUsabilityEvaluator`, which
  honours `UsabilityPolicy.min_headroom_m`; a door wider than what is left of
  its wall is `opening_outside_wall` and a missing host wall, stair Level or
  arrival Space is `dangling_reference` (`check_model`). No private name is
  imported across packages for these rules. No Finding suggests a Revision
  operation now; a visual claim's suggestions are `RevisionOp`s (ADR 0030) and
  the `void:` suggestion is gone.
- The visual-review loop function and the claim-by-claim verifier are deleted.
  Fix verification is the revise report; the visual-review skill reads it.
  The reviewer demonstration keeps its critique and images as a record and no
  longer claims a verified fix.

## Consequences

- Every Evaluation gains one evaluator run (`LabelCollisionEvaluator`), the
  `label_collisions` metric and any `label_collision` Findings. Stored
  Evaluations are untouched; re-evaluating a stored Plan version reports them.
- A window in a retaining wall is reported once per window, whatever the
  room, from the wall's kind; with terrain it is no longer also sampled.
- A revision whose request names no Space (only `--strategy` or `--stair`)
  reports three empty lists.
- Findings about ids the request did not target are not in the three lists;
  the stored revision report's `new_violations` and `resolved_violations`
  still cover every Finding.
