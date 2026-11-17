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

First draft, from a scan of `src/house_ai/domain/` on 2026-11-17. "Saved"
means the name appears in stored records, so it needs a validation alias.
New names in brackets are proposals; the rename stage settles them.

| Old name | Saved | Glossary term | Status |
|---|---|---|---|
| `ProgramItem` (class) | no | Space requirement | to rename |
| `SpaceProgram.items` | yes | Space requirement (`space_requirements`) | to rename |
| `AdjacencyRequirement`, `AdjacencyKind` | no | Space relationship | to rename |
| `SpaceProgram.adjacencies` | yes | Space relationship (`space_relationships`) | to rename |
| `ProgramZone` (class) | no | Zone | to rename |
| `SpaceProgram.levels` | yes | Storey count (`storeys`); the owner's "how many floors" is a storey count, levels come from the plan | to rename |
| `SpaceProgram.site_verified` | yes | Approved (`site_approved`) | to rename |
| `SITE_NEEDS_VERIFICATION` (state) | yes | Workflow state awaiting site confirmation and approval (`SITE_NEEDS_CONFIRMATION`) | to rename |
| `CONCEPT_GENERATION`, `CONCEPT_REVIEW` (states) | yes | Plan option generation and review (`PLAN_GENERATION`, `PLAN_REVIEW`) | to rename |
| `BriefFact` (class) | no | Interpretation or answer, by its source | to decide in the rename stage |
| "slot value", "slot inference" (CLI text, docs) | no | Interpretation | to rename |
| "homeowner" (CLI help, docs) | no | Owner | to rename |
| "concept" for a stored plan (CLI text, `design/concepts/`) | export folder | Plan option / plan version | to rename; old export folders stay |
| "floor" meaning a storey (comments, docs) | no | Storey | to rename |

`PlanVersion.option_id`, `ConceptProposal`, `OwnerStatement`, `Finding`,
`Violation` and `Issue` already match the glossary.

## Consequences

- Old and new records in one project can use different names for the same
  thing. This table is how a reader tells them apart.
- Readers must keep accepting every old name in the table for as long as
  records using it exist.
