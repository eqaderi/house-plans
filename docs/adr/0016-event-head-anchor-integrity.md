# ADR 0016: Preserve event-tail evidence before further writes

Status: accepted (S1 follow-up, 2026-10-17)

## Context

The S1 head anchor detects tail truncation only until the next write replaces
it. A missing anchor also looks like a legacy store. Verification must remain
read-only, including for the existing homeowner project.

## Decision

- Check the current anchor under the store lock before appending an event,
  writing an artifact, or copying a source. Refuse missing required, malformed,
  or mismatched anchors before changing project files.
- Add `head_anchor_required: true` to new event payloads. This additive marker
  makes deletion of an anchor detectable without changing canonical schemas.
- Stores without an anchor and without this marker remain readable. Their
  next explicit write creates an anchor and records the marker; reads never
  migrate a store. Existing anchors are checked even without the marker.
- Keep `head.json` as a derived, atomically replaced tail anchor; workflow
  state and registered artifacts remain sourced exclusively from the log.

## Consequences

A crash between the log append and anchor replacement is reported and blocks
further writes. Recovery requires inspecting the log and anchor, rather than
silently treating a mismatched tail as valid. Pre-marker legacy stores cannot
prove an anchor was deleted until a marked write exists. As in ADR 0003, this
is tamper evidence, not protection against rewriting every local record.
