# ADR 0003: File-based project store with a hash-chained event log

Status: accepted (Milestone A, 2026-10-17)

## Context

The spec requires immutable original inputs, versioning of every plan
iteration, never overwriting an approved or reviewed design, provenance for
everything, and explicit human approvals. Projects are single-owner, small
(megabytes) and must work offline and be inspectable without special
tools.

## Decision

- A project is a plain directory. `project.json` holds identity only.
- `events.jsonl` is append-only. Each event records actor, type, state
  change, reason and payload, plus `prev_hash` and its own SHA-256 over the
  canonical JSON. It is the single source of truth: artifact versions are
  registered by events, and the workflow state is replayed from events and
  never stored separately, so the two cannot diverge.
- Artifacts are write-once: `artifacts/<kind>/<id>/vNNNN.json`, created by
  an atomic hard link that fails if the target exists, then made read-only.
  Every write is a new version. Writing identical content returns the
  existing version.
- Content hashes are computed from the canonical JSON of the validated
  model, so formatting, YAML vs JSON and omitted defaults do not change
  them.
- Sources are copied byte-for-byte into `source/`, named by hash prefix,
  made read-only and re-hashed after copying.
- `verify()` checks the chain, every artifact's hash and schema, stray
  files and every source hash.
- Appends are serialised with an advisory `flock`.

## Alternatives considered

- **SQLite**: transactional, but opaque to people and diff tools, and
  immutability would still have to be enforced in code.
- **Git as the store**: gives history, but approvals and workflow state need
  their own semantics anyway, and owner data must not end up in the code
  repository.
- **Mutable files plus a state field**: simpler, but it breaks "never
  overwrite" and lets the stored state disagree with the history.

## Consequences

- Tamper-evident, not tamper-proof. Anyone with file access can rewrite the
  whole chain consistently. Approvals guard against accidental or silent
  skipping, not against an attacker on the same machine.
- Reads replay the log (O(events)). That is fine for the expected size;
  an index can be added later without changing the format.
- `flock` is POSIX-only. Windows support would need another lock.
