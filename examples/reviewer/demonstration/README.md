# Synthetic Hillside Visual Plan Review Demonstration

Demonstration of Stage S5 agent visual review loop on `synthetic-hillside`.

## Overview
This demonstration shows the complete visual critique and fix verification loop:
1. **Defect Identification**: Detection of seeded visual defect `window_on_retaining_wall`
   hosted on retaining wall `w-down-300-001`.
2. **Grounded Critique**: Generation of `visual_critique.json` citing only canonical element
   IDs (`win-buried-001`, `w-down-300-001`).
3. **Structured Revision**: Proposed `revision_ops.json` relocating the window to
   exterior wall `w-down-300-013`.
4. **Fix Verification**: Execution of `verify_visual_critique_fixes()` proving that
   the revised plan resolves the defect without leaving open claims.

## Artifacts
- **Before**: [`before.svg`](before.svg), [`before.png`](before.png) (SHA-256: `808609c4cc636db8b9f1975da645f84bf26a978b0add6e77f150f2bf25010a88`)
- **Critique Record**: [`visual_critique.json`](visual_critique.json)
- **Revision Operations**: [`revision_ops.json`](revision_ops.json)
- **After**: [`after.svg`](after.svg), [`after.png`](after.png)
- **Verification Report**: [`revision_report.json`](revision_report.json)

## Replay Instructions

To regenerate all demonstration artifacts, run:
```bash
.venv/bin/python examples/reviewer/demonstration/make_demonstration.py
```

To run the automated verification test:
```bash
.venv/bin/python -m pytest tests/test_visual_demonstration.py
```
