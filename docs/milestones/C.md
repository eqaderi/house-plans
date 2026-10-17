# Milestone C: owner interview and space program

Date: 2026-10-17. Branch: `milestone-c`, created from `milestone-b` at
commit 011c8c8; the latest `milestone-b` (07cdfdd, with the project folders of
ADR 0009) is merged into it. Neither branch is merged into `main`; `milestone-c`
contains all of Milestone B and must be merged after it (or together with it),
with the owner's approval. Both are pushed to GitHub (private repository) with
the owner's authorisation. Design: [ADR 0008](../adr/0008-owner-interview-and-space-program.md),
the Claude adapter: [ADR 0010](../adr/0010-claude-adapter-for-the-interview.md).

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
  test provider.
- **Real AI interview** (ADR 0010): `interview run <project> --owner <name>
  --ai anthropic [--model <id>]` uses Claude (`providers/claude.py`, the
  official `anthropic` SDK, default `claude-opus-5-5`) to word each planned
  question as an architect would, using the project's site values, the owner's
  statements and the answers so far, and to read free answers the parser
  cannot. The owner types `allow anthropic` once (a consent turn). Structured
  output is schema-constrained and validated again; every value read is an
  inference until the owner confirms it. The code, not the AI, adds "Site
  figures here come from the survey; you have not confirmed the site yet"
  while the site gate is open. Each answer turn keeps the wording shown and
  the provider and model. Provider errors (no key, refused key, rate limit,
  outage, network, refusal, cut-off reply) fall back to the built-in question
  or parser with a note; the key never appears in output. Without the SDK or a
  key the interview runs exactly as before.
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
# with Claude (needs: pip install -e '.[ai]' and ANTHROPIC_API_KEY in that terminal)
.venv/bin/house-ai interview run my-house --owner <name> --ai anthropic
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

`410 passed` on Python 3.13.3 (locked versions, with the `[ai]` extra), 0
failed, 0 skipped, after merging the latest `milestone-b` and adding the
Claude adapter (2026-10-17). `ruff check src tests examples`: all checks
passed. `house-ai schemas check`: 22 schemas up to date (new:
`interview_session`, `owner_statements`). Before that: `390 passed` on Python
3.13.3 and on Python 3.11.12 (numpy 2.4.6 and pyproj 3.7.2 there, because the
lock's numpy 2.5.4 and pyproj 3.8.0 have no 3.11 builds).

`tests/test_ai_interview.py` (12 tests, fake Anthropic client and scripted
provider; no network, no key) covers the request (model, structured-output
schema, server-side fallback, attachments), refusals and cut-off replies,
SDK errors mapped without leaking the key, AI wording kept with provider and
model, the deterministic unconfirmed-site label, no request without consent,
fallback on transient and fatal errors, AI reading of an unreadable answer,
contradiction choices never reworded, and the CLI consent and no-credentials
paths.

`tests/test_interview.py` (30 tests) covers:

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
- confirming only what the owner was shown, and reading an option number
  only at the start of a reply (found in review, fixed with tests);
- committed example outputs.

## Known limitations

- The deterministic parser reads common English phrasings only. Unusual
  answers are asked again and then recorded as unknown unless the owner runs
  with `--ai anthropic`. Every reading needs the owner's confirmation.
- The Claude adapter is tested with a fake client only: no live API call has
  been made (no key in this environment). The first real run is the owner's.
- The AI words the planner's questions and reads answers; it does not invent
  new questions (AI follow-up questions are not implemented). Only Anthropic
  has an adapter; OpenAI and Gemini would be further adapters.
- AI wording is requested again when an interview resumes, so the resumed
  question may read differently; what was shown with each answer is kept.
- Typical room sizes are a small fixed table, not a jurisdiction's rules;
  areas are not checked against any building code ("not checked").
- Cost is not estimated: the budget is recorded and reported as not checked.
- The program does not decide levels against the ground on a sloping site.
  It records the owner's slope preference; the section comes first in
  Milestone D.
- A carport counts in the floor-area totals like a garage.
- One interview session per project (`interview`); several household members
  answering separately is not modelled.
- Models gained defaulted fields (`ProgramItem.accessible`,
  `SpaceProgram.levels` / `budget` / `site_ref` / `site_verified`,
  `Contradiction.tradeoff` / `options`). An artifact of those kinds stored
  with older code no longer matches its hash when read, and must be
  regenerated (the golden bungalow plan was regenerated). The owner's real
  project holds no such artifact (`project verify` is intact).
- The lock file does not install on Python 3.11 (see test results).

## The owner's real project

`projects/my-house` (ADR 0009) is in `SITE_NEEDS_VERIFICATION`; nothing in
it is approved. The interview can run on it now (`house-ai interview run
my-house --owner <name> [--ai anthropic]`); it has not been started. The AI
receives the site values marked "NOT yet confirmed by the owner" and the
owner's recorded statements (UTM, metres above sea level, the 12–12.5 m drop,
the steep land). Program review waits for the site gate. No answers were
recorded by an agent; a start on a scratch copy of the project confirmed the
first question and the context.

## Next: Milestone D (plan)

Not started. Formal constraint model and solver, 3+ alternative plans,
plan SVG, evaluators and plan versioning, starting from the approved
program and the approved site.
