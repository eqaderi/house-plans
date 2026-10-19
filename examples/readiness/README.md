# Readiness demonstration (Stage S9, task S9-02)

One synthetic project goes from site gate to a reviewed, revised and approved
plan on the steep synthetic hillside (`examples/projects/synthetic-hillside`),
with every refusal and every defect recorded. It is the evidence behind the
floor-plan readiness gate in `docs/PROJECT_TRACKER.md` §H.

Replay from the repository root (about one minute on a laptop):

```sh
.venv/bin/python examples/readiness/run_demo.py --out project-data/s9-demo
```

`--out` must be a new or empty folder; `project-data/` is git-ignored. The run
writes a project store (`project/`), concept exports (`concepts/`), renders
(`renders/`), a reviewer bundle (`bundle/`) and the record (`record.md`,
`record.json`). `tests/test_readiness_demo.py` runs a shorter version
(`two_wing` only) and checks properties, not geometry.

What it does, in order:

1. Stores the synthetic site; shows that plan generation and agent approvals are
   refused; the synthetic owner approves the site gate.
2. Runs the interview the way an agent does (ADR 0011): every answer in
   `answers.yaml` is recorded verbatim by `agent:claude-code`; one answer is in
   Persian and carries the agent's own interpretation; one answer is corrected
   later; the owner's confirmation is recorded with their words.
3. Builds the program; refuses an agent approval; the synthetic owner approves.
4. Generates every strategy (CP-SAT) with all critics, and measures diversity.
5. Generates a concept from the agent topology proposal in `proposal.yaml`.
6. Renders `concept-two-wing` v1 and checks the agent critique in
   `visual_critique.json` against canonical IDs; runs the S5 defect detectors.
7. Applies two owner-style revisions (verbatim words plus explicit ops) and
   checks the first request independently of the revision report.
8. Writes an unapproved program v2 and shows that new plans still pin the
   approved v1.
9. Requests plan review, refuses an agent approval, approves synthetically and
   shows that the approved plan is frozen.
10. Exports the reviewer bundle and verifies the store.

Read these outputs with care:

- **The owner is synthetic.** `human:example-owner` stands in for the homeowner,
  as in the tests and `examples/interviews/synthetic-family`. Its approvals
  exercise the gates and endorse nothing. In a real project only the homeowner
  approves, in their own terminal.
- **The visual critique is an agent's judgment** (`ai_judgment`), written in a
  session after looking at `renders/concept-two-wing-v1.png`. The script only
  checks its IDs and whether its `screenshot_hash` matches the new render. If the
  hash differs (another platform, rasteriser or solver tie, ISS-21, ISS-28), an
  agent must look at the new render and write the critique again.
- **`demonstration/` is illustrative output** from one run on macOS arm64
  (Python 3.13): `record.md`, `record.json`, `comparison.md` and the two
  renders. Solver output can differ between platforms, so nothing compares
  against it.
- Nothing here is permit-ready, construction-ready or professionally checked;
  see `docs/PROFESSIONAL_HANDOFF.md`.
