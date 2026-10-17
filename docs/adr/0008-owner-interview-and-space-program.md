# ADR 0008: Owner interview, interpretations and the space program

Status: accepted (Milestone C, 2026-10-17); §6 superseded by
[ADR 0011](0011-agent-first-interview-interface.md) so coding agents (Claude
Code, Gemini CLI, Codex) can record homeowner answers, revisions, confirmations
and contradiction resolutions via the CLI while approval gates remain
human-only.

## Context

Milestone C turns an owner interview into a design brief and a space program
that Milestone D's solver can use. The interview must be conversational (one
focused question at a time, follow-ups, no repeats, revisions, unknown
answers), but structured data must stay deterministic and owner-controlled.
Three facts shape the design:

- The owner's real site is not approved, so the workflow cannot reach
  `INTERVIEWING` (it needs `SITE_APPROVED`), yet the owner wants the interview
  now.
- An LLM can phrase questions and read free text well, but cannot be trusted
  for schema correctness, and owner material is private (`providers.base.send`
  refuses private data without a human's consent).
- `BriefFact` already forbids recording an agent inference as a fact or a
  preference, and an owner answer as an inference.

## Decision

1. **Interview state is an artifact.** A new artifact kind
   `interview_session` holds every turn (question shown, the owner's words
   verbatim, what was understood), the pending question, consents and the
   site context. Each turn writes a new version, so an interrupted interview
   resumes from the store, and nothing is lost on a revision.
2. **Two facts per answer.** The owner's words become a `BriefFact` with
   source `owner_answer` (`preference`, or `verified_fact` for statements
   about the household), recorded as stated. What the system understood
   (e.g. `bedroom_count = 3`) becomes separate facts with source
   `agent_inference` and status `inference`, linked to the answer. Only a
   human can confirm an interpretation; confirming rewrites it as an
   `owner_answer` fact with ref `confirmed:<answer id>`. Rejecting it removes
   the interpretation and asks the question again.
3. **The program uses only confirmed or explicit values.** The program
   builder derives items, areas, adjacencies, zones and levels from the
   brief. Program items cite the facts they come from. The program gate is
   blocked while any cited fact is still an unconfirmed inference, while a
   contradiction is unresolved, or while program validation reports a
   blocking finding. Sizes the owner did not give come from a small table of
   typical sizes and are recorded in `assumptions.yaml` as assumptions (not
   code requirements; no jurisdiction is loaded).
4. **Deterministic core, optional LLM.** Question choice (a fixed question
   bank with conditions and follow-ups), answer parsing (numbers, yes/no,
   unknown/undecided, must/nice-to-have), contradiction rules, program
   building and validation are deterministic. An LLM may only (a) rephrase
   the chosen question and (b) propose slot values from a free-text answer.
   Its output is parsed against a Pydantic model; anything invalid is
   discarded and the deterministic parser's result (or "unparsed, ask
   again") is used. LLM proposals are still `inference` until the owner
   confirms them. The LLM path runs only with a provider the owner allowed
   through `interview consent` (a human actor; recorded in the session) and
   always through `providers.base.send`. Tests use a scripted provider.
   No vendor adapter ships yet.
5. **The interview may run before the site is approved; the gate may not.**
   Interview commands write brief, program, assumptions and open-question
   versions in any state up to `PROGRAM_REVIEW`. No transition is added.
   Site values used by the interview (parcel area, slope, frontage) are
   labelled `unverified` until the site gate is approved for that site
   version, and they only produce warnings and questions, never hard limits.
   Program review (`INTERVIEWING -> PROGRAM_REVIEW`) and the program gate
   still need the approved site.
6. **Owner answers come from a human.** `interview answer`, `revise`,
   `resolve`, `confirm`, `consent` and `program reject` refuse non-human
   actors, so an agent cannot answer for the owner. Gate approval is
   unchanged (`workflow approve` needs an interactive terminal and a typed
   phrase; `Workflow.approve` rejects non-human actors).
7. **Rejection keeps the owner's words.** `program reject` moves
   `PROGRAM_REVIEW -> INTERVIEWING` with the owner's words as the reason and
   records them as an `owner_answer` fact in a new brief version.

## Consequences

- The real project can be interviewed now; its program cannot be reviewed or
  approved until the owner approves the site.
- Interview sessions grow by one version per turn; that is acceptable for
  the expected size (tens of turns).
- Adding a vendor adapter later needs no change to the interview: it only
  has to implement `ModelProvider`.
