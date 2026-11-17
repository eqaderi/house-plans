# ADR 0030: One home for Revision operations

Status: accepted (2026-11-17).

## Context

A **Revision operation** (GLOSSARY.md) is one structured change asked of a
Plan option, such as a new area or a Level for a Space. Before this decision
an operation was a `verb:argument` string parsed in six places: the CLI flag
builder, `PlanService._apply_ops` (merge with the parent's operations, then
solver input), `PlanService._unmet_request`, the combine feature mapping, the
visual-review loop and the grounding check. Five lists of verbs disagreed:
the reviewer app and `constants.reviewer.SUPPORTED_REVISION_OPS` offered
`orientation` and `daylight`, which `plan revise` refused as unknown; the
solver accepted three outdoor link kinds while the revise check allowed five.
An unknown verb was refused only after the store was opened and the parent
Plan version loaded. "Was this request met" read "separate" as "no door
between them" while the evaluators (ADR 0020) also require "no shared wall",
and it understood three of the six level words the command accepts.

## Decision

- `house_ai.domain.revision_ops` holds the one table of verbs and legal
  targets, `REVISION_VERBS`, with the one parser (`RevisionOp.parse`) and the
  one serialiser (`str(op)`). `RevisionOp.op_type` is the `RevisionVerb`
  enum, and a model validator checks every operation against the table, so
  the reviewer's operations file (`RevisionOpsFile`) and visual critiques
  parse through it too. Command-line flags are parsed before the project is
  opened. An unknown verb is refused once, with one message.
- Each verb's rule records whether the next Plan version inherits it
  (`lasting`): area, level, relations, stair, outdoor are continuing design
  intent; rethink, strategy and proposal apply to one solve.
- `house_ai.generation.revision` turns operations and a Space program into
  the solver request (`compile_revision`: area targets, level preferences,
  Space relationships, stair position, outdoor links, strategy, rethink and
  the parent's position hints), merges inherited operations with the same
  override rules as before (`merge_operations`), and answers "was this
  request met" (`unmet_requests`) with the shared definitions: "separate"
  through `domain.relations.is_relation_satisfied` (ADR 0020), levels through
  `domain.program.level_preference_met`, which the program evaluator also
  uses. `PlanService.revise` keeps storing, solving and provenance.
- Stored Plan versions keep their recorded operations as strings
  (`GenerationRecord.revision_ops`); `RevisionOp` is the in-memory form.
  Every string an earlier version could have stored still parses and
  serialises to the same text.
- The outdoor link kinds an operation may ask for are the ones the 2D solver
  places (`constants.proposals.VALID_OUTDOOR_LINKS`: terrace, balcony,
  courtyard); the solver reads the same constant.
- `orientation` and `daylight` are removed from the reviewer and from the
  constants until the solver supports them (tracker ISS-39). The unused
  `SUPPORTED_REVISION_OPS` and the `OP_*` constants are deleted; the table is
  the list.
- A Finding that suggests an operation builds a `RevisionOp`. Suggestions no
  operation can carry out are dropped: `void:` (stair through a slab) and
  "separate" of an opening from its host wall.
- The pass-through `PlanService.combine` is deleted; `plan combine` calls
  `revise` with `kind=combine`.

## Consequences

- The command line, the reviewer and the solver agree on which operations
  exist; `tests/test_revision_operations.py` checks the reviewer's list
  against the table.
- Revisions may now report unmet requests that passed silently before: two
  Spaces asked to be separate that still share a wall, or a Space asked to be
  off the entry Level (`not_entry`) or on it (`ground`) that is not. This is
  accepted.
- `revision_ops.schema.json` and `visual_critique.schema.json` list the verbs
  as an enum; the reviewer's TypeScript types gain `RevisionVerb`.
