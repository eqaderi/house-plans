# ADR 0029: Gate status

Status: accepted (2026-11-17).

## Context

An architecture review after [ADR 0027](0027-deep-modules-at-the-human-and-private-data-seams.md)
found that what blocks a gate left the workflow as sentences with ad-hoc
prefixes (`blocking open question …`, `program check …`, `unbuildable …`).
Agents and tests matched substrings of them. The plan gate's attention items
came from a second public method, and the Blockers of the site gate were the
strings `site_verification_blockers` returns, so `SiteService` (ADR 0028)
reported prose too.

## Decision

- **`Blocker` is a canonical domain type** (`house_ai.domain.workflow`,
  `schemas/blocker.schema.json`): `kind`, `code`, `subject_ids`, `message`.
  `code` is a stable machine code (`horizontal_crs`, `stair_low_headroom`,
  `wrong_state`) or, where the Blocker *is* one record, that record's id (an
  Open question, a Contradiction, a site Issue, an upstream gate). `message`
  is the sentence a person reads. The kinds are `workflow_state`, `artifact`,
  `upstream_gate`, `site_fact`, `site_issue`, `open_question`,
  `contradiction`, `program_check`, `pinned_input`, `integrity`,
  `hard_violation` and `unbuildable`.
- **`Workflow.gate_status(gate, ref)`** returns a `GateStatus` for one gate
  and one pinned artifact version: whether the project is in the gate's
  review state, its Blockers and its attention items (plan gate, ADR 0024).
  It covers the site, program, plan and model gates. `approve`,
  `request_approval`, `workflow approve`, `program review` and `plan review`
  all read it; `check_gate` and `plan_attention` are gone.
- `domain.site.site_blockers` gives the site gate's typed Blockers;
  `site_verification_blockers` is their messages, for the site validation
  report. `SiteService` reports typed Blockers.
- **The approval-requested event keeps its saved shape** (ADR 0003): `gate`,
  `artifact`, `open_reasons` and, for the plan gate, `attention`. Its
  `open_reasons` are the Blockers' messages, so the sentences are the ones
  saved before this change and a store written earlier still verifies. The
  SITE_NEEDS_CONFIRMATION transition keeps its `blockers` strings likewise.
  Blockers are computed from the store, never stored.
- **Program gate: one cause, one Blocker.** The program checks
  (`program.validation`) are the one source of program gate Blockers; their
  `contradiction` findings become Blockers of kind `contradiction` with the
  Contradiction's id as `code`. The gate adds only what they do not cover:
  the site gate's approval, blocking Open questions, and a cited brief the
  store lacks. A missing blocking answer is one Blocker, its Open question:
  the check's `missing_information` for the same slot (`f-<topic>`) is
  dropped. Before this, one missing answer produced two reasons, and an
  unknown fact id one per citing item plus the check's. With several stored
  briefs and none cited the checks cannot run; the gate then reports each
  brief's Contradictions and one `unknown_fact` itself. The gate still reads
  the latest Open questions, not those written with the program version
  being approved (tracker ISS-39).
- **Stale approval.** The gate status carries the gate's current approval
  and, when a newer version of what it approved has been written,
  `stale_against` (that version). The definition is unchanged from the CLI
  copy it replaces (ISS-05): the latest version of the approved artifact id
  has a higher version or another hash. `project status` reads it, and its
  `--json` keeps `stale`, `latest_version` and `stale_approvals` with the same
  values.
- `request_approval` returns the `GateStatus` it recorded; no caller reads
  the event payload by key. `--json` output that lists site blockers gains
  `blockers` (typed) beside `verification_blockers` (sentences).

## Consequences

- Agents act on `kind` and `code`; tests assert them instead of substrings.
- Unbuildable codes still keep the plan gate closed (ADR 0024): they are
  Blockers of kind `unbuildable`.
- A new reason a gate can be blocked needs a kind (or an existing one) and a
  code; the message stays free text.
