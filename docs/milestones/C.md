# Milestone C: owner interview and space program

Date: 2026-10-17. Branch: `milestone-c`, created from `milestone-b` at
commit 011c8c8. `milestone-b` is **not merged into `main`** yet, so
`milestone-c` contains all of Milestone B and must be merged after it (or
together with it). Nothing is pushed or merged; both need the owner's
approval. Design: [ADR 0008](../adr/0008-owner-interview-and-space-program.md).

## What works

All of it runs from implemented, deterministic logic; tests check results
against known answers.

- **Conversational interview** (`house_ai.interview`): 30 questions over the
  owner's topics (household, children's rooms, older relatives, bedrooms,
  bathrooms and en-suite, floors, how the house meets a sloping site,
  entrance level, open or separate living, cooking and smells, pantry,
  dining, guests, home office, parking and EV, laundry and storage, outdoor
  spaces, accessibility and lift, privacy, room relationships, daylight and
  ventilation, room sizes, cultural/religious practices, style, budget,
  total area, priorities, future expansion). One question at a time, in
  order of information value.
  - Questions whose condition does not hold are skipped: no lift question
    when nobody needs step-free access, no dining question when living is
    open-plan, no garage-type question without a car, no slope questions on
    flat ground.
  - A question is not asked when an earlier answer already said it ("we
    need 3 bedrooms and two floors" in the household answer).
  - A slot left open by an answer gets a short follow-up ("And should the
    main bedroom have its own bathroom?").
  - An answer nothing can be read from is asked again with a hint, once;
    then it is recorded as unknown and the interview moves on.
  - "Not sure", "don't know" and "undecided" are recorded as unknown, never
    filled in.
  - Must-haves ("must", "need", "essential") and nice-to-haves ("would be
    nice", "ideally", "maybe") are recorded as priorities.
- **The owner's words and the system's reading are kept apart.** Each answer
  is a brief fact with the owner's words verbatim (`owner_answer`). What was
  understood (e.g. bedrooms = 3) is a separate `inference` until the owner
  confirms it. The owner can reject an interpretation; it is removed and
  asked again. Confirmed household counts become `verified_fact`, wishes
  become `preference`.
- **Contradictions** (`interview/rules.py`): lift on one floor; step-free
  living with stairs and no lift; fewer bedrooms than the household needs
  (by what the owner said about sharing and guests); an open kitchen that
  must keep smells out; an en-suite as the only bathroom; a garage for no
  car; two rooms both next to and away from each other. Each states the
  trade-off in plain words and offers options. It becomes the next question,
  and nothing changes until the owner picks an option. "Not sure" defers
  it; it stays open and blocks the program gate.
- **Revisions:** `interview revise <question> "<new answer>"` records a
  revision turn. The old answer stays in the session history and the new
  value needs confirming again.
- **State persistence:** every turn writes a new `interview_session` version
  and the derived `design_brief`. An interrupted interview resumes at the
  same question from the store in a new process.
- **Space program** (`house_ai.program.builder`): items with quantities,
  min and target areas, minimum widths, floor preference, privacy, zone,
  priority (must/should/could), daylight need, `accessible` (step-free)
  and the facts they come from.
  - Adjacencies are hard or soft: open plan, kitchen–dining, en-suite,
    quiet study, bedrooms away from living, guests apart, garage near the
    entrance, plus the owner's own "X next to / away from Y".
  - Zones are day, night, guests, service, circulation and outdoor. The
    program also records the number of floors, the budget, and the site
    version with whether it was verified.
  - The owner's sizes ("living room about 30 m²", "small bedrooms are
    fine") replace typical sizes. Sizes the owner did not give are typical
    values, listed in `assumptions.yaml` as assumptions. They are not code
    minima: no jurisdiction is loaded.
  - `open_questions.yaml` lists unknowns; adults, bedrooms and bathrooms
    are blocking.
- **Program validation** (`program/validation.py`), deterministic:
  - missing information;
  - unconfirmed interpretations the program relies on;
  - unresolved contradictions;
  - duplicate spaces or requirements;
  - conflicting adjacencies (blocking when both are hard);
  - suspicious room sizes;
  - unusual combinations;
  - floors without a stair;
  - step-free spaces off the entrance level with no lift;
  - room totals against the owner's total area (infeasible: blocking, with
    options);
  - footprint against the parcel. This blocks when the site is verified;
    otherwise it is a warning marked "unconfirmed survey value".

  Findings never change the program; infeasible requests come with options.
  Blocking findings also block the program gate (`Workflow._check_program_gate`).
- **Review and approval:**
  - `program review` builds the program, moves INTERVIEWING → PROGRAM_REVIEW
    and requests approval.
  - The owner approves with the existing `workflow approve <dir> program`
    (interactive terminal, typed phrase).
  - Or the owner rejects with `program reject --reason "<their words>"`. This
    moves back to INTERVIEWING with their words in the event log and in the
    brief.
  - After approval, answers are locked until a human reopens the gate.
- **Human-only actions:** answering, revising, confirming, rejecting,
  consenting and rejecting the program need a human actor in the library.
  The CLI also needs an interactive terminal, so an agent cannot answer for
  the owner. `Workflow.approve` still rejects non-human actors.
- **Unapproved site:** the interview runs before the site gate. Site values
  (parcel area, relief, frontage) are shown as "from the survey; you have not
  confirmed the site yet". The program records `site_verified: false` and the
  assumption `asm-site-unverified`. `program review` refuses with an
  explanation until the site is approved.
- **AI providers:** `orchestration/interview_llm.py` lets an LLM propose slot
  values for an answer the parser could not read, and rephrase questions.
  Every call goes through `providers.base.send`, which needs the owner's
  consent (`interview consent`, recorded in the session) for private data.
  Output is validated against strict slot types (`interview/slot_types.py`);
  invalid values or non-JSON replies are dropped. What is kept is still an
  inference until confirmed. `providers/scripted.py` is the deterministic
  test provider. No vendor adapter ships (no credentials); the deterministic
  parser is the default.
- **Files** (`program build --out <dir>`): `design_brief.yaml`,
  `space_program.yaml`, `assumptions.yaml`, `open_questions.yaml`,
  `interview-summary.md` and `program-review.md`, a review sheet in plain
  language with every space's basis (from your answers, needs your
  confirmation, assumed).

## Commands to reproduce

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests examples
.venv/bin/house-ai schemas check

# the synthetic family, end to end (writes examples/interviews/synthetic-family/expected/)
.venv/bin/python examples/interviews/synthetic-family/run_example.py

# an interview on any project (the owner runs this in their own terminal)
.venv/bin/house-ai interview run <dir> --owner <name>     # :summary, :revise <id>, :quit
.venv/bin/house-ai interview summary <dir>
.venv/bin/house-ai program build <dir> --actor agent:<tool> --out <dir>-program
.venv/bin/house-ai program review <dir> --actor agent:<tool>    # needs the approved site
.venv/bin/house-ai workflow approve <dir> program --id program --approver <name>
.venv/bin/house-ai program reject <dir> --reason "<what is wrong>" --actor human:<name>
```

## Results on the synthetic family (`examples/interviews/synthetic-family/`)

25 scripted answers produce a complete interview with 0 blocking findings.
The program has 3 bedrooms, 2 bathrooms (one en-suite), a study, a carport,
a laundry, a store room, a plant room, a stair, a terrace and a garden.
Rooms total 116–164 m² net and about 139–197 m² gross against the owner's
180 m² on 2 floors. The program review succeeds, and a human approval moves
the project to PROGRAM_APPROVED. Outputs are committed under `expected/` and
checked by a test.

## Test results

`387 passed` on Python 3.13.3 and on Python 3.11.12 (macOS arm64), 0 failed,
0 skipped. `ruff check src tests examples`: all checks passed.
`house-ai schemas check`: 21 schemas up to date (new: `interview_session`).

`tests/test_interview.py` (27 tests) covers:

- a normal interview;
- one question at a time and no repeats;
- answers that already cover later questions;
- incomplete and unreadable answers;
- missing room sizes;
- contradictions resolved, too few bedrooms and deferred contradictions;
- changing an earlier answer and rejecting an interpretation;
- conflicting adjacencies in the interview and in a program;
- an unrealistic total area and a footprint larger than the parcel;
- an interrupted and resumed interview;
- a rejected program;
- an unauthorised AI approval (library and CLI);
- unconfirmed interpretations blocking the gate;
- answers locked after approval;
- the interview on an unapproved site;
- LLM consent, validation and garbage handling;
- parsers producing only valid slot values;
- the CLI, including the interactive loop and export;
- committed example outputs.

## Known limitations

- The deterministic parser reads common English phrasings only. Unusual
  answers are asked again and then recorded as unknown. An LLM can help once
  a vendor adapter exists and the owner consents. Every reading needs the
  owner's confirmation either way.
- No vendor LLM adapter (OpenAI, Anthropic, Gemini) is included yet; the
  interface and the consent path are in place and tested with the scripted
  provider.
- Typical room sizes are a small fixed table, not a jurisdiction's rules;
  areas are not checked against any building code ("not checked").
- Cost is not estimated: the budget is recorded and reported as not checked.
- The program does not decide levels against the ground on a sloping site.
  It records the owner's slope preference; the section comes first in
  Milestone D.
- A carport counts in the floor-area totals like a garage.
- One interview session per project (`interview`); several household members
  answering separately is not modelled.

## The owner's real project

`project-data/my-house` is in `SITE_NEEDS_VERIFICATION`; nothing in it is
approved. The interview can run on it now (`house-ai interview run
project-data/my-house --owner <name>`). Site values are shown as unconfirmed,
and program review waits for the site gate. No answers were recorded by an
agent.

## Next: Milestone D (plan)

Not started. Formal constraint model and solver, 3+ alternative plans,
plan SVG, evaluators and plan versioning, starting from the approved
program and the approved site.
