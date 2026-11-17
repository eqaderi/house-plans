# Records written before ADR 0025

`store/` is a synthetic project store written by the code of commit `386be0d`,
before the glossary renames (ADR 0025, Stage S11). Never regenerate or edit it:
the tests check that the current code reads these records unchanged and that
every content hash and the event hash chain still hold.

It holds every saved name the stage renamed:

- events with the states `SITE_NEEDS_VERIFICATION`, `CONCEPT_GENERATION` and
  `CONCEPT_REVIEW` (the last two appended directly, as state names only, then
  back to `INTERVIEWING`);
- an interview session that answered `q-floors` and confirmed the slot
  `floors`, and design briefs with the fact `f-floors`;
- a space program of schema 0.1.0 with `items`, `adjacencies`, `levels`,
  `site_verified` and `usability.double_bed_program_item_ids` /
  `single_bed_program_item_ids`.

How it was made: on a worktree of `386be0d`, a script created the store with a
fixed clock (2026-11-17 09:00 UTC, one second per call), moved it to
`SITE_INGESTION`, appended a `SITE_NEEDS_VERIFICATION` transition and back,
moved to `INTERVIEWING`, answered the first five answers of
`examples/interviews/synthetic-family/answers.yaml`, confirmed them, built the
program, and appended transitions to `CONCEPT_GENERATION`, `CONCEPT_REVIEW` and
back to `INTERVIEWING`.
All data is synthetic.
