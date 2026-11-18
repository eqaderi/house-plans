# ADR 0028: SiteService, and each stage's module moves its own workflow state

Status: accepted (2026-11-17).

## Context

An architecture review after [ADR 0027](0027-deep-modules-at-the-human-and-private-data-seams.md)
found that the site's part of the workflow had no home. Getting from survey
files to an approvable site took nine steps spread over the CLI, the
`site_ingestion` functions and `Workflow`: start ingestion by hand, ingest,
assess, confirm, transition back by hand, assess again, approve. The CLI
printed some of these steps and not others, and test preludes re-typed the
sequence. The defect the Owner would meet: after `site confirm` cleared every
Blocker the project stayed in `SITE_NEEDS_CONFIRMATION`, the site gate only
approves from `SITE_INGESTION`, and nothing told anyone to run the
`workflow transition` in between. `my-house` waits at exactly that point.

The same pattern existed one stage later: `program review` worked only from
`INTERVIEWING`, so after the site gate someone had to run `workflow transition
INTERVIEWING` by hand. `PlanService` already made its own moves
(`PROGRAM_APPROVED → PLAN_GENERATION → PLAN_REVIEW`).

## Decision

- `house_ai.orchestration.site.SiteService` is the site's module, a peer of
  `InterviewService` and `PlanService`. It is not called a "stage": the
  glossary reserves that word for tracker work. It owns four things:
  - **ingest**: extract the stored survey sources (one `cad_import` per file
    and a `site`), start site ingestion on a new project, and assess the Site;
  - **assess**: from `NEW_PROJECT` start site ingestion; in `SITE_INGESTION`
    move an ambiguous Site to `SITE_NEEDS_CONFIRMATION` (the event keeps its
    saved shape: `site` and `blockers` in the payload); anywhere else report
    the Blockers and move nothing. `workflow assess-site` stays as this
    re-assessment. `Workflow.assess_site` is deleted;
  - **confirm**: apply a human confirmation, re-assess, and if no Blocker
    remains while the project waits in `SITE_NEEDS_CONFIRMATION`, move it back
    to `SITE_INGESTION` with the confirmer as the event's actor. The site gate
    is then approvable with no step in between. If a Blocker remains, the
    workflow state does not change;
  - **write the site review package** (validation report, drawings, import
    records, Owner statements) for a Site version, callable without the CLI;
  - and it answers what blocks the site gate now.
- Confirmation stays human-only (agent contract §8, ADR 0006 §2):
  `confirm_site` refuses a non-human actor before anything is written, and the
  CLI keeps its terminal and typed-phrase check. The separate records of
  ADR 0006 §1 stay separate; only the sequencing moved into the module.
- **Each stage's module moves its own workflow state.** `SiteService` makes
  the site moves, `InterviewService.review_program` makes the move from
  `SITE_APPROVED` to `INTERVIEWING` before entering `PROGRAM_REVIEW`, and
  `PlanService` keeps its moves. No stage needs a hand-run `workflow
  transition`; the command remains for recovery. Gate approval, reopening and
  program rejection stay human-only and are unchanged.

## Consequences

- One call takes a new project from survey sources to the right workflow
  state with its Blockers reported, and the Owner's `site confirm` is the last
  step before the site gate. Agent contract §7, the site skill and the agent
  workflows document describe these steps.
- Tests of the site sequence go through `SiteService` with a temp-folder store
  and the synthetic survey; only one `main([...])` test per command stays for
  argument wiring and exit codes.
- The workflow state table is unchanged: `SITE_NEEDS_CONFIRMATION →
  SITE_INGESTION` is still an ordinary transition, so an unusual state can be
  repaired by hand. The usual route out is the human confirmation.
- Typed Blockers and a gate status with the next human command are separate
  work (part 3 of the same review); `SiteService` reports Blockers as the
  strings `site_verification_blockers` returns today.
