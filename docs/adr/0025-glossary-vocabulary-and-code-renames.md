# ADR 0025 — Glossary vocabulary and renaming saved names

Date: 2026-11-17. Status: accepted.

## Context

The owner had a glossary written ([GLOSSARY.md](../../GLOSSARY.md)) because
the code and docs used one word for several things (concept, floor, verified,
zone, stage) and several words for one thing (owner, homeowner). The owner
also wants the code to use the glossary's words. But artifact hashes are
taken from the canonical JSON of the validated model (`storage/hashing.py`),
the event log is hash-chained (ADR 0016), and approvals pin those hashes.
Renaming a saved name (a schema field, an enum value, a workflow state, an
artifact kind) changes the hash of every record that used it.

## Decision

GLOSSARY.md is the vocabulary for docs, CLI text, agent output and new code.
Saved records are never rewritten to match it:

- Records already written keep their old names forever. Nothing is migrated
  or re-hashed.
- When a name is renamed in code, new records use the new name and readers
  accept both (old names as validation aliases, keyed on `schema_version`
  where a meaning changed).
- The mapping below is the record of every old name and its glossary term.
  A rename stage updates its status; nothing else may rename saved names.

Rejected: renaming only Python identifiers and keeping old saved names forever
(new records would keep disagreeing with the glossary); migrating old records
to the new names (rewrites write-once artifacts and a hash-chained log, and
would invalidate every pinned approval).

## Mapping

First drafted from a scan of `src/house_ai/domain/` on 2026-11-17 and
settled by Stage S11. "Saved" means the name appears in stored records, so
readers still accept the old name.

| Old name | Saved | Glossary term | Status |
|---|---|---|---|
| `ProgramItem` (class) | no | Space requirement | renamed `SpaceRequirement` |
| `SpaceProgram.items` | yes | Space requirement | renamed `space_requirements` (schema 0.2.0) |
| `AdjacencyRequirement`, `AdjacencyKind` (classes) | no | Space relationship | renamed `SpaceRelationship`, `SpaceRelationshipKind` |
| `SpaceRelationship` (house model class) | no | none; it names the plan's side | renamed `PlanRelationship` to free the name |
| `SpaceProgram.adjacencies` | yes | Space relationship | renamed `space_relationships` (schema 0.2.0) |
| `ProgramZone` (class) | no | Zone | kept: `domain.model.Zone` is the zone in a house model; `ProgramZone` is the zone a program asks for and uses no avoided word |
| `SpaceProgram.levels` | yes | Storey | renamed `storeys` (schema 0.2.0); the plan derives its levels and `HouseModel.storey_count` |
| `SpaceProgram.site_verified` | yes | Approved | renamed `site_approved` (schema 0.2.0) |
| `UsabilityRequirements.double_bed_program_item_ids`, `single_bed_program_item_ids` | yes | Space requirement | renamed `*_space_requirement_ids` (inside space programs of schema 0.2.0) |
| `SITE_NEEDS_VERIFICATION` (state) | yes | Workflow state awaiting site confirmation and approval | renamed `SITE_NEEDS_CONFIRMATION` |
| `CONCEPT_GENERATION`, `CONCEPT_REVIEW` (states) | yes | Plan option generation and review | renamed `PLAN_GENERATION`, `PLAN_REVIEW` |
| Interview slot `floors`, question `q-floors` | yes | Storey | renamed `storeys`, `q-storeys` |
| Evaluation metric `site_verified`, violation `level_count_differs`, plan assumption `asm-gen-requested-levels` | yes | Approved, Storey | renamed `site_approved`, `storey_count_differs`, `asm-gen-requested-storeys` |
| `BriefFact` (class) | no | none | kept: a brief fact can be an answer, an interpretation, a confirmed value or an assumption, so neither term fits |
| `program_item_id` (`Space`, constraints, proposals), `program_item_ids`, `near_program_item_ids`, `adjacency_graph` (proposals) | yes | Space requirement, Space relationship | kept: these records have no rename schema version; follow-up candidate |
| `SiteContext.verified` (interview sessions), brief topic `levels` | yes | Approved; levels | kept: not in the S11 scope; follow-up candidate |
| Plan option ids `concept-<strategy>` | yes (artifact ids) | Plan option | kept: renaming the prefix would split one option into two when a project regenerates |
| Relationship ids `adj-*`, item ids `pi-*` | yes (ids) | none | kept: ids, not words |
| "slot value", "slot inference" (CLI text, docs) | no | Interpretation | renamed |
| "homeowner" (CLI help, docs, skills) | no | Owner | renamed; `MASTER_SPEC.md` and history keep it |
| "concept" for a stored plan (CLI text, skills, exports) | export folder | Plan option / plan version | renamed; new exports go to `design/plan-options/`, old `design/concepts/` folders stay and are still read; `--concepts-dir` stays as an alias of `--plan-options-dir`; the committed example `examples/projects/synthetic-hillside/concepts/` keeps its name (Milestone D history links it) |
| Skill `generate-concepts` | no | Plan option | renamed `generate-plan-options` |
| "floor" meaning a storey (comments, docs, interview and review text) | no | Storey | renamed |

`PlanVersion.option_id`, `ConceptProposal`, `OwnerStatement`, `Finding`,
`Violation` and `Issue` already match the glossary.

How old names are read:

- Space programs: schema 0.1.0 records are written back with their old
  field names, so their hashes hold; new programs are schema 0.2.0. Either
  name is accepted on input, never both.
- Events have no schema version: an event read with an old state name
  remembers it and is written back with it. `WorkflowState` maps old values
  to the current members, so code and the CLI accept old names.
- Interview sessions and briefs are read through `current_slot` and
  `current_question_id`; saved turns are never rewritten.
- JSON Schemas list only the new names; a document with old names is valid
  for the Python readers, not for the exported schema.

## Consequences

- Old and new records in one project can use different names for the same
  thing. This table is how a reader tells them apart.
- Readers must keep accepting every old name in the table for as long as
  records using it exist.
