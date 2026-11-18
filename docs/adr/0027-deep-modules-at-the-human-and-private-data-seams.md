# ADR 0027: One module per rule at the human-only and private-data seams

Status: accepted (2026-11-17).

## Context

An architecture review of `src/house_ai` looked for shallow modules: an
interface nearly as large as the behaviour behind it, or one rule smeared
across many callers. Four places carried the security-relevant rules of the
[agent contract](../AGENT_CONTRACT.md) §5 and §8:

- **Human-only commands.** `workflow approve`, `workflow reopen`, `site
  confirm`, `interview consent`, `program reject` and `interview run` each
  re-implemented "interactive terminal, human identity, exact typed phrase",
  with small differences (one helper checked the terminal but not the
  identity; three repeated an agent-name check the `Actor` validator already
  makes). The library had five copies of "refuse a non-human actor", one of
  them in `geospatial`, which cannot import orchestration. The tests could
  only reach the rule by patching `sys.stdin` per command.
- **Provider consent.** `LlmAssist(provider, policy)` took a `DataFlowPolicy`
  that `InterviewService` silently replaced before every request. The
  parameter misled any other caller: it would send with the policy it was
  given, not with the consent the owner recorded.
- **Grounding.** `evaluation/grounding.py` (written critiques, `plan ground`)
  and `validation/grounding.py` (visual critiques, Stage S5) both defined
  `validate_critique_grounding`, with different signatures and different sets
  of valid IDs. Visual revision-op targets passed on a `z-` prefix alone.
- **Store paths.** `ProjectStore` built artifact paths from an id it did not
  check; `put` was safe only because an `ArtifactRef` (whose `Id` pattern
  refuses `../`) happened to be built before the file was written.
  `SourceDocument.stored_path` was any string and `verify()` joined it onto the
  project folder.

## Decision

- `house_ai.cli.human` is the one human-only check in the CLI:
  `require_human(action, who, terminal)` returns the human `Actor` or raises
  `HumanCheckFailed` (exit 2); `require_phrase(action, phrase, terminal)`
  raises `NotConfirmed` (exit 1). Each command names a `HumanOnly` action;
  `main()` turns the exceptions into exit codes, which `cli/exit_codes.py`
  defines once for every command module. The `Terminal` seam has two adapters:
  the process's stdin and a scripted terminal in tests. The consent asked
  inside `interview run` uses the same `require_phrase`.
- `house_ai.domain.provenance.refuse_non_human(actor, what)` is the one
  library check and raises `ApprovalRequiresHuman`; workflow, interview, site
  confirmation and CRS confirmation (`geospatial`) call it, and
  `cli.human.require_human` uses it for actors. It lives in `domain` so every
  layer can reach it; its name differs from the CLI's `require_human` because
  it checks only the identity, not the terminal.
- `LlmAssist.policy` is a callable read on every request.
  `InterviewService.use_ai(provider)` attaches an assist bound to
  `InterviewService.policy`, so consent recorded later applies at once and a
  policy object can no longer be cached by mistake.
- `house_ai.validation.grounding` is the one grounding module. Written and
  visual critiques use the same `collect_canonical_ids`; the written check is
  renamed `validate_cited_ids`. A revision-op target must exist; the `z-`
  wildcard is gone. `evaluation/grounding.py` is deleted.
- `ProjectStore` validates every artifact id as an `Id` before it reads or
  writes under it; `put` checks it before reading the event log. `SourceDocument.stored_path` must match
  `source/<sha12>-<name>`.
- Deleted as pass-throughs: the `generation.base.PlanGenerator` protocol and
  `CpSatPlanGenerator.generate` (one adapter; production code calls
  `candidates`), and the CLI's `_dir` wrapper around `resolve_project_dir`.
  A generator protocol returns when a second generator exists. (This means
  the whole generator; the bar and 2D engines are a seam inside it,
  [ADR 0032](0032-engine-seam-inside-the-generator.md).)

`plan ground` still reads a `plan.json` file rather than a stored plan
version: exploratory plans, which it exists to check, are never stored
([ADR 0013](0013-solver-backed-plan-generation.md)).

## Consequences

- A new human-only command gets the full check by declaring a `HumanOnly`
  action; `tests/test_human_only.py` tests the rule once through its
  interface, and `tests/test_human_gates.py` keeps one test per command.
- `ApprovalRequiresHuman` moves from `orchestration.workflow` to
  `domain.provenance` and is now a `ValueError`, not a `WorkflowError`;
  the CLI catches it before either. The CRS refusal message reads
  "... cannot confirm the coordinate reference system; only a human can".
- The terminal check is still not a security boundary against a determined
  local process (see `cli/main.py`); the library check and the hash-chained
  log remain the enforcement.
- Visual critiques may now cite space requirements, zones and other model entities
  that written critiques could already cite; they may no longer target a zone
  the plan lacks.
- `schemas/source_document.schema.json` gains the `stored_path` pattern;
  existing stores (all written by `add_source`) already match it.
