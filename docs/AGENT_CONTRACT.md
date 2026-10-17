# Agent contract

The single set of engineering rules for every coding agent that works on
this repository: Claude Code (primary developer), OpenAI Codex (independent
reviewer and debugger) and Google Gemini (reviewer and second developer).
`AGENTS.md`, `CLAUDE.md` and `GEMINI.md` only load this file and add
tool-specific details; how each tool loads it is recorded in
[ADR 0005](adr/0005-shared-coding-agent-instructions.md). Never copy these
rules into a tool-specific file.

**Coding agents are not product agents.** The roles in `agents/roles.yaml`
(Site Analyst, Design Architect, ...) are runtime parts of the product,
described by the spec. This contract governs the tools that write the code.

## 1. Objectives and sources of truth

HOUSE DESIGN AI turns a real survey and an owner interview into a verified
site, an approved program, alternative floor plans, and then Blender and
Unreal models, all derived from one semantic model with human approval in
between.

| Question | Authority |
|---|---|
| What the product must do | [MASTER_SPEC.md](MASTER_SPEC.md) (wins every conflict) |
| How the code is layered | [ARCHITECTURE.md](ARCHITECTURE.md) |
| What the schemas mean | [DOMAIN_MODEL.md](DOMAIN_MODEL.md) |
| Why a decision was made | [adr/](adr/) |
| What each milestone delivered | [milestones/](milestones/) |

If this contract and the spec disagree, follow the spec and record the
conflict in an ADR.

## 2. Repository architecture

`src/house_ai/` is layered: `domain` (canonical Pydantic schemas, units,
geometry, integrity checks) ← `storage` ← `orchestration` (workflow) ←
`cli`. Pipeline packages (`cad`, `geospatial`, `render2d`, later
`generation`, `evaluation`, `blender`, `unreal`) depend on `domain` only.
Dependencies point toward `domain`; `domain` imports nothing above it. No
AI vendor SDK, CAD backend or game engine may become a dependency of
`domain`; each sits behind an adapter.

## 3. One model, many views

- The canonical semantic house model (`house_ai.domain`) is the only source
  of truth. Plans, SVGs, IFC, Blender and Unreal output are derived from it.
- Never treat an image, a render or a prose description as the design. A
  design change is a new plan version of the canonical model.
- Never invent coordinates for rooms and trust them. Geometry comes from a
  solver or a human and is always run through
  `house_ai.domain.integrity.check_model`.
- Do not rebuild or fork the domain model; extend it, regenerate the
  schemas, and update `DOMAIN_MODEL.md`.

## 4. Writing project state

- Every change to project state goes through the library or the `house-ai`
  CLI. Never edit files in a project directory by hand: artifacts are
  read-only and the event log is hash-chained (`house-ai project verify`).
- Every artifact must validate against its schema; the store refuses
  invalid content. Nothing is overwritten: a revision is a new version
  that names its parent.
- Identify yourself on state-changing commands: `--actor agent:<tool>`.
- Owner answers become `BriefFact` entries (`source.kind: owner_answer`),
  recorded as stated. A plan change request keeps the owner's words
  verbatim and produces a new plan version plus a `RevisionReport`.

## 5. Private data and providers

- `project-data/` holds owner material and is git-ignored. Never commit
  it or copy it into `examples/`, `tests/` or docs. Real survey inputs live
  there; the originals are never modified.
- Reading private data into your own context sends it to your model
  provider. Do not open, print or summarise the owner's surveys, briefs or
  reports unless the owner has explicitly allowed it in this session.
  Prepare the command and let the owner run it.
- In product code every provider call goes through `providers.base.send`,
  which enforces `DataFlowPolicy`; unlabelled content counts as private.
- Tests and examples use synthetic data only.

## 6. Unknowns, assumptions and evidence

- Unknown architectural facts are recorded as unknown (`null` or status
  `unknown`). Never invent a value to unblock the pipeline.
- Label statements with their epistemic status: `verified_fact`,
  `inference`, `assumption`, `preference`, `simulation_result`,
  `professional_approval`, `unknown`. An agent inference is never recorded
  as a fact or an owner preference.
- Evaluator output states how each value was obtained (`measured`,
  `inferred`, `simulated`, `ai_judgment`, `not_checked`). A metric you did
  not compute is `not_checked`, with no value.
- Every derived value keeps its provenance: source document and SHA-256,
  CAD entity handle and layer, parser and version, actor, input artifact
  versions. Assumptions go in `assumptions.yaml`, unanswered questions in
  `open_questions.yaml` (`blocking` if the program must wait for them).

## 7. CAD, units and coordinate systems

- DWG and DXF are file formats; UTM is a coordinate system. Inspect a
  file's real format before choosing a reader.
- Never infer a CRS, UTM zone, datum or drawing unit from coordinate
  magnitudes. Only a source file can *declare* them and only a human can
  *confirm* them. Unconfirmed units, CRS, elevation units or vertical
  datum put the site in `SITE_NEEDS_VERIFICATION`; work stops there.
- Raw CAD extraction stays in SOURCE coordinates and units. Conversion to
  GRID metres and the LOCAL project frame is a separate, reversible,
  documented step (`domain/coordinates.py`).
- Ambiguous entities are reported as ambiguous, never silently used or
  dropped. Missing elevations are never interpolated beyond surveyed data.

## 8. Workflow and human approval gates

States: `NEW_PROJECT → SITE_INGESTION ⇄ SITE_NEEDS_VERIFICATION → [site
gate] SITE_APPROVED → INTERVIEWING ⇄ PROGRAM_REVIEW → [program gate]
PROGRAM_APPROVED → CONCEPT_GENERATION ⇄ CONCEPT_REVIEW → [plan gate]
PLAN_APPROVED → BLENDER_BUILD ⇄ BLENDER_REVIEW → [model gate] MODEL_APPROVED
→ UNREAL_BUILD ⇄ UNREAL_REVIEW`.

- Start every project task with `house-ai project status <dir>`.
- **You must never approve a gate or confirm site facts.** `workflow
  approve` and `site confirm` need an interactive terminal and a typed
  phrase and exit with code 2 otherwise. Do not work around this (no fake
  TTY, no `--actor human:...` on the owner's behalf). Run
  `workflow request-approval` and ask the human.
- Never imply something is approved when it is not. Say which gates are
  approved, for which artifact version, and by whom.
- Reopening a gate supersedes it and every later approval; only a human
  may reopen. If a request needs a gate that is not approved, say so and
  stop.

## 9. Professional boundary

This is design exploration and decision support. Never call output
permit-ready, construction-ready, structurally certified, code-compliant,
MEP-engineered or geotechnically verified unless a qualified professional
supplied that status in the project record. Compliance wording comes from
`codepack.compliance_statement`; run `codepack.find_prohibited_claims` over
owner-facing text. See [PROFESSIONAL_HANDOFF.md](PROFESSIONAL_HANDOFF.md).

## 10. Coding conventions

- Python ≥ 3.11, type hints, `ruff` as configured in `pyproject.toml`
  (line length 100). Match the style of the surrounding code.
- Persisted data is a Pydantic `StrictModel` (unknown fields, NaN and
  infinity rejected). Canonical units are metres and degrees.
- Deterministic code for anything measurable; AI only where reasoning
  helps, and its output is validated before it changes state.
- Smallest change that solves the task. No speculative features,
  frameworks or configuration. Add a dependency only when needed, in
  `pyproject.toml` and `requirements-lock.txt`, and say why.
- External programs (ODA File Converter, Blender, Unreal) sit behind
  adapters and are optional; the rest of the slice runs without them.

## 11. Tests and definition of done

- Every behaviour change has a test. Bugs get a failing test first.
- Assert numbers against known ground truth (areas, lengths, transforms,
  elevations), not only "it ran". No mock success output.
- Tests run offline, without private data or paid APIs. Tests that need
  an external program skip cleanly when it is absent.

Before saying a change is finished, run and report exactly as printed:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests examples
.venv/bin/house-ai schemas check
```

If you changed a schema, run `house-ai schemas export` and commit the
regenerated files.

## 12. Architectural decisions

Record a decision as `docs/adr/NNNN-short-title.md` (context, decision,
consequences) when you change layering, add a dependency or external tool,
change storage or schema semantics, or resolve a spec conflict. Do not
rewrite accepted ADRs; supersede them with a new one.

## 13. Git workflow

- One branch per milestone (`milestone-a`, `milestone-b`, ...). Never
  commit directly to `main`.
- Never rewrite pushed history: no force-push, no rebase or amend of
  pushed commits. Do not reopen history issues the owner has acknowledged.
- Merge into `main` and push only when the owner explicitly authorises it.
- Commit messages: imperative subject, a prefix such as `feat:`, `fix:`,
  `docs:`, `test:`; the body says why. Never commit `project-data/`, real
  survey files or credentials.

## 14. Milestones and acceptance

Milestones follow the spec (A domain, B site, C program, D plan, E reviewer,
F Blender, G Unreal). Work on one milestone at a time and do not start the
next without the owner's go-ahead. A milestone is accepted when:

1. the spec's items for it work from real, implemented logic;
2. the definition of done (§11) passes;
3. `docs/milestones/<X>.md` states what works, exact commands to reproduce
   it, test results as printed, known limitations and the next milestone;
4. the owner has approved the merge.

## 15. Handoffs between coding agents

- Start with `git status`, `git log` and the current milestone file. If the
  tree holds another agent's uncommitted work, stop and ask.
- Never trust a reported result. Re-run §11 yourself and read the actual
  diff before building on it.
- Reviewers report findings as `file:line`, severity, failure scenario.
  Fix only confirmed defects, each with a test, and leave design changes to
  the owner.
- End a session with everything committed on the milestone branch and the
  milestone file updated (done, open findings, what needs the owner).

## 16. Commands

```bash
house-ai project status <dir> [--json]      # always first
house-ai project verify <dir>               # hash chain, artifacts, sources
house-ai validate <schema> <file> [--site site.yaml]
house-ai artifact put <dir> <kind> <file> --actor agent:<tool>
house-ai source add <dir> <file> --actor human:<name>
house-ai site inspect <file>... [--layers map.yaml]   # read-only
house-ai site ingest <dir> --source <src-id> --layers map.yaml --actor agent:<tool>
house-ai site report <dir> --id site --out <dir>
house-ai workflow transition <dir> <STATE> --reason "..." --actor agent:<tool>
house-ai workflow assess-site <dir> --id site --actor agent:<tool>
house-ai workflow request-approval <dir> <gate> --id <id> --actor agent:<tool>
house-ai schemas export | house-ai schemas check
```
