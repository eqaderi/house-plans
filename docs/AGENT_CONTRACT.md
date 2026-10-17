# Agent contract

This is the single set of instructions for any AI agent working in this
repository, whatever the vendor. `AGENTS.md`, `CLAUDE.md` and `GEMINI.md`
point here and only add tool-specific details.

`docs/MASTER_SPEC.md` is the authoritative product specification. This
contract describes how to work inside the system that implements it. If the
two disagree, the spec wins; record the conflict in an ADR under `docs/adr/`.

## 1. One model, many views

- The canonical semantic house model (`house_ai.domain`) is the only source
  of truth. Plans, SVGs, IFC, Blender and Unreal output are derived from it.
- Never treat an image, a render or a prose description as the design. A
  design change is a new plan version of the canonical model.
- Never invent coordinates for rooms and trust them. Geometry comes from a
  solver or from a human, and it is always run through the deterministic
  checks (`house_ai.domain.integrity.check_model`).

## 2. Writing project state

- Every change to project state goes through the library or the `house-ai`
  CLI. Never edit files inside a project directory by hand or with shell
  tools: artifacts are read-only, and the event log is hash-chained, so
  edits are detected by `house-ai project verify`.
- Every artifact you write must validate against its schema. The store
  validates on write and refuses invalid content.
- Nothing is overwritten. A revision is a new version that names its
  parent. Approved and reviewed versions stay as they were.
- Identify yourself on every state-changing command with
  `--actor agent:<your-tool-name>`.

## 3. Unknowns, assumptions and evidence

- When an architectural fact is unknown, record it as unknown (`null`, or
  status `unknown`). Do not invent a value to unblock the pipeline.
- Label every statement with its epistemic status: `verified_fact`,
  `inference`, `assumption`, `preference`, `simulation_result`,
  `professional_approval` or `unknown`. An agent inference can never be
  recorded as a fact or as an owner preference; the schema refuses it.
- Evaluator output says how each value was obtained: `measured`,
  `inferred`, `simulated`, `ai_judgment` or `not_checked`. A metric you did
  not compute is `not_checked`, with no value.
- Put assumptions in `assumptions.yaml` and questions you could not answer
  in `open_questions.yaml`. Mark a question `blocking` if the program must
  not be approved before it is answered.
- Never infer a coordinate reference system from coordinate magnitudes. A
  six- or seven-digit easting proves nothing. Only the source file can
  *declare* a CRS or drawing unit, and only a human can *confirm* it. If
  units, CRS or vertical datum are not confirmed, the site goes to
  `SITE_NEEDS_VERIFICATION` and work stops until a human resolves it.

## 4. Workflow and approval gates

States: `NEW_PROJECT → SITE_INGESTION ⇄ SITE_NEEDS_VERIFICATION → [site
gate] SITE_APPROVED → INTERVIEWING ⇄ PROGRAM_REVIEW → [program gate]
PROGRAM_APPROVED → CONCEPT_GENERATION ⇄ CONCEPT_REVIEW → [plan gate]
PLAN_APPROVED → BLENDER_BUILD ⇄ BLENDER_REVIEW → [model gate] MODEL_APPROVED
→ UNREAL_BUILD ⇄ UNREAL_REVIEW`.

- Start every task with `house-ai project status <dir>` (add `--json` to
  parse it). Work only on what the current state allows.
- **You must never approve a gate.** The four gates (site truth, program,
  final floor plan, Blender model) are crossed only by a human with
  `house-ai workflow approve`. That command needs an interactive terminal
  and a typed confirmation, and it exits with code 2 in a non-interactive
  shell. Do not try to work around this. When a gate is ready, run
  `house-ai workflow request-approval ...` and ask the human to approve.
- Do not imply that something is approved when it is not. Say which gates
  are approved, for which artifact version, and by whom.
- Reopening a gate (`workflow reopen`) supersedes its approval and every
  later one. Only a human actor may reopen an approved gate.
- If the human's request needs a gate that is not yet approved (for example
  "build the Blender model" before the plan is approved), say so and stop.

## 5. Private data and providers

- `project-data/` holds owner-specific material and is git-ignored. Never
  commit it, and never copy it into `examples/`, `tests/` or docs.
- Source files are private by default. Never send private project data to
  a model provider unless a human has explicitly allowed that provider
  (`house_ai.providers.base.DataFlowPolicy`). Every provider call goes
  through `providers.base.send`, which enforces the policy.
- Tests and examples use synthetic data only.

## 6. Professional boundary

This is a design-exploration and decision-support system. Never describe
output as permit-ready, construction-ready, structurally certified,
code-compliant, MEP-engineered or geotechnically verified unless a qualified
professional or authority has supplied that status in the project record.

- Compliance language comes from `codepack.compliance_statement`. Without a
  loaded, human-verified code pack the only allowed labels are "not checked"
  and "conceptual best-practice check only".
- Run `codepack.find_prohibited_claims` over any explanation you generate
  for the owner. See `docs/PROFESSIONAL_HANDOFF.md`.

## 7. Roles

Roles are defined in `agents/roles.yaml` (schema `agent_roster`). Use the
smallest composition that answers the request; most requests need one role
or none. No role may approve a gate; the schema fixes `may_approve: false`.

## 8. Owner input

- Owner answers become `BriefFact` entries in the design brief with
  `source.kind: owner_answer`, recorded as stated, never paraphrased into
  something stronger.
- A request to change a plan becomes a `ChangeRequest` holding the owner's
  words verbatim, and the result is a new plan version plus a
  `RevisionReport`.

## 9. Commands

```bash
house-ai project status <dir> [--json]      # always first
house-ai project verify <dir>               # hash chain, artifacts, sources
house-ai validate <schema> <file> [--site site.yaml]
house-ai artifact put <dir> <kind> <file> --actor agent:<name>
house-ai artifact check <dir> <plan-id>     # integrity of a stored plan
house-ai source add <dir> <file> --actor human:<name>
house-ai workflow transition <dir> <STATE> --reason "..." --actor agent:<name>
house-ai workflow assess-site <dir> --id site --actor agent:<name>
house-ai workflow request-approval <dir> <gate> --id <id> --actor agent:<name>
house-ai schemas export | house-ai schemas check
```

## 10. Definition of done

Before you say a change is finished:

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests examples
.venv/bin/house-ai schemas check
```

If you changed a schema, run `house-ai schemas export` and commit the
regenerated files in `schemas/`. Report failures exactly as printed.
