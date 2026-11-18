# Synthetic Hillside Visual Plan Review Demonstration

Demonstration of Stage S5 agent visual review loop on `synthetic-hillside`.

## Overview
This demonstration shows a grounded visual critique and the revision it asks for:
1. **Seeded defect**: a window `win-buried-001` hosted on retaining wall
   `w-down-300-001`.
2. **Grounded Critique**: Generation of `visual_critique.json` citing only canonical element
   IDs (`win-buried-001`, `w-down-300-001`).
3. **Structured Revision**: Proposed `revision_ops.json` with a Revision operation
   `plan revise` can run (`rethink:sp-study-1`).
4. **After**: a hand-edited illustration that moves the window to `w-down-300-013`.
   It is not a Plan version and nothing verifies it.

Fix verification is what `plan revise` reports: for the ids the request targeted, the
Findings of the parent's Evaluation that disappeared, that remain and that are new
(`findings` in `plan revise --json`, ADR 0033). The hand-edited states here would not pass
it: the seeded window is 1.2 m wide at 1.0 m along a 2.0 m wall and opens onto `sp-study`,
which the plan does not have, and the interior wall it is moved to is already filled by an
opening.

## Artifacts
- **Before**: [`before.svg`](before.svg), [`before.png`](before.png) (SHA-256: `808609c4cc636db8b9f1975da645f84bf26a978b0add6e77f150f2bf25010a88`)
- **Critique Record**: [`visual_critique.json`](visual_critique.json)
- **Revision Operations**: [`revision_ops.json`](revision_ops.json)
- **After**: [`after.svg`](after.svg), [`after.png`](after.png)

## Replay Instructions

To regenerate all demonstration artifacts, run:
```bash
.venv/bin/python examples/reviewer/demonstration/make_demonstration.py
```

To run the tests on these artifacts:
```bash
.venv/bin/python -m pytest tests/test_visual_demonstration.py
```
