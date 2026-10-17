# Milestone C: owner interview and space program

> [!NOTE] Post-Milestone C Update (2026-10-17)
> Milestone C was merged into `main` at `2ecb587`.
> The ~65.2% mean slope and ~12.4 m drop figures mentioned in § "Steep hillside site awareness" below were retracted by the subsequent survey audit (`projects/my-house/reviews/survey-audit/REPORT.md`, PR #1 / `b636164`), which established the horizontal-area-weighted mean slope as ~38.9% over the full survey TIN (~40.7% over the parcel intersection) and total relief as ~15.2 m across the 27 elevation points.
> Active development proceeds under [PROJECT_TRACKER.md](../PROJECT_TRACKER.md).

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
- **Steep hillside site awareness:** on steep parcels (`relief_m >= 8.0` or
  `mean_slope_pct >= 20.0`, such as `projects/my-house` with ~12.4 m drop and
  ~65.2% mean slope), `build_program` records the explicit assumption
  `asm-hillside-engineering` covering split-level massing, hillside construction,
  road-level access/parking, excavation, retaining walls, slope drainage,
  structural engineering, and not assuming the full parcel area is buildable.
  Selecting a single flat platform (`slope_strategy=platform`) on a steep site
  emits the `steep_site_flat_pad` warning.
- **Agent-first interview interface ([ADR 0011](../adr/0011-agent-first-interview-interface.md) — no API key required):**
  - Coding agents (**Claude Code**, **Gemini CLI**, **OpenAI Codex**) are the
    primary AI interfaces and operate the entire interview and program workflow
    via `house-ai` CLI commands with `--actor agent:<tool>` and `--json`.
  - `interview status <dir> [--json]` / `interview checklist <dir> [--json]`
    returns the 30-question completeness checklist, site measurements,
    verification blockers, steep-hillside considerations, owner statements,
    unconfirmed interpretations, and open contradictions.
  - `interview answer` and `interview revise` accept `--question <qid|slot|custom-id>`,
    `--question-text "<text>"`, `--topic <topic>`, `--set SLOT=VALUE`
    (repeatable), `--unknown SLOT`, `--interpret-json`, and `--option N`, so
    agents can record verbatim answers in **Persian, English, or mixed
    language**, propose validated slot interpretations (`inference`,
    `method: agent:<id>`), answer questions out of checklist order, and ask
    adaptive architectural follow-up questions outside the 30 predefined
    questions.
  - `interview confirm`, `interview reject`, and `interview resolve` allow
    coding agents to record the homeowner's confirmations, corrections, and
    contradiction choices.
- **Review and human-only approval gates:**
  - `program review` builds the program, moves `INTERVIEWING → PROGRAM_REVIEW`
    and requests approval.
  - `workflow approve`, `workflow reopen`, `site confirm`, `interview consent`,
    and `program reject` remain strictly **human-only** in an interactive
    terminal (exit code 2 otherwise). No agent can ever approve a site,
    program, plan, or model gate on the homeowner's behalf.
  - After approval, answers are locked until a human reopens the gate.
- **Unapproved site:** the interview runs before the site gate. Site values
  (parcel area, relief, frontage) are shown as "from the survey; you have not
  confirmed the site yet". The program records `site_verified: false` and the
  assumption `asm-site-unverified`. `program review` refuses with an
  explanation until the site is approved.
- **Optional Anthropic SDK adapter ([ADR 0010](../adr/0010-claude-adapter-for-the-interview.md)):**
  `interview run <project> --owner <name> --ai anthropic [--model <id>]` remains
  available as an optional extra (`pip install -e '.[ai]'`) when an
  `ANTHROPIC_API_KEY` is configured and the owner grants consent
  (`interview consent`). Without an API key or SDK, the primary agent-first CLI
  and built-in deterministic interview run with zero external API dependencies.
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
.venv/bin/python examples/interviews/synthetic-family/run_example.py --check

# primary agent-first interview workflow (Claude Code, Gemini CLI, Codex — no API key needed)
.venv/bin/house-ai project status my-house --json
.venv/bin/house-ai interview status my-house --json
.venv/bin/house-ai interview start <dir> --json --actor agent:claude-code
.venv/bin/house-ai interview answer <dir> "<verbatim homeowner words>" \
    --set slope_strategy=step_down --set entry_at_road=true --json --actor agent:claude-code
.venv/bin/house-ai interview confirm <dir> --text "<owner confirmation>" --json --actor agent:claude-code
.venv/bin/house-ai interview resolve <dir> <contradiction-id> "<owner choice>" --option 1 --json --actor agent:claude-code
.venv/bin/house-ai interview summary <dir>
.venv/bin/house-ai program build <dir> --actor agent:claude-code --out <dir>-program
.venv/bin/house-ai program review <dir> --actor agent:claude-code    # needs the approved site

# human-only interactive terminal commands
.venv/bin/house-ai workflow approve <dir> program --id program --approver <name>
.venv/bin/house-ai program reject <dir> --reason "<what is wrong>" --actor human:<name>
.venv/bin/house-ai interview run <dir> --owner <name> [--ai anthropic]
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

`419 passed` on Python 3.13.3 and `418 passed, 1 skipped` on Python 3.11.12
(without the optional `anthropic` SDK installed in the 3.11 venv).
`ruff check src tests examples`: all checks passed.
`house-ai schemas check`: 22 schemas up to date (`interview_session`,
`owner_statements`, plus the 20 Milestone A/B schemas).

`tests/test_interview.py` (33 tests) covers:

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
  only at the start of a reply;
- **agent-first end-to-end CLI workflow** (`test_agent_first_end_to_end_workflow_with_persian_english_and_mixed_answers`):
  project/site inspection, out-of-order multi-slot opening statement, adaptive
  custom follow-up question, Persian and mixed-language homeowner answers via
  `--set`, contradiction resolution via `interview resolve`, confirmation via
  `interview confirm`, revision preserving turn history, program build/review,
  and human-only gate enforcement;
- **steep hillside engineering assumptions & flat-pad warning**
  (`test_steep_hillside_site_records_engineering_assumptions_and_warns_on_flat_pad`);
- **read-only inspection of `projects/my-house`**
  (`test_agent_inspects_real_my_house_project_without_modifying_it`);
- committed example outputs.

## Known limitations

- The built-in regex parser reads common English phrasings only; when a coding
  agent (Claude Code, Gemini CLI, Codex) conducts the interview in Persian,
  English, or mixed language, the agent passes structured slot values via
  `--set` (`method: agent:<id>`), and every reading still requires the
  homeowner's confirmation before the program gate can be approved.
- The optional Claude SDK adapter (`providers/claude.py`) is tested with a fake
  client only: no live API call has been made (and no API key is required for
  the core workflow).
- Typical room sizes are a small fixed table, not a jurisdiction's rules;
  areas are not checked against any building code ("not checked").
- Cost is not estimated: the budget is recorded and reported as not checked.
- The program does not decide levels against the ground on a sloping site.
  It records the owner's slope preference and hillside engineering assumptions;
  the building section and floor plans come in Milestone D.
- A carport counts in the floor-area totals like a garage.
- One interview session per project (`interview`); several household members
  answering separately is not modelled.

## The owner's real project

`projects/my-house` (ADR 0009) remains in `SITE_NEEDS_VERIFICATION`; nothing in
it is approved (`house-ai project verify my-house` is intact: 12 events, 8
artifact versions). Confirmed by the homeowner: UTM coordinates, elevations in
metres above sea level, and a genuine ~12–12.5 m drop on steep land (~600 m²
parcel, ~21 m road frontage on a ~9 m road, 27 elevation points from
`seperated.dwg` and `elevation.dwg`). Still unverified: exact UTM zone,
hemisphere, horizontal datum/EPSG, vertical datum, and formal legal parcel
boundary. The homeowner interview can run now with Claude Code, Gemini CLI, or
Codex while `my-house` stays in `SITE_NEEDS_VERIFICATION`; `program review` and
the `program` gate wait for the `site` gate.

## Next: Milestone D (plan)

See [D.md](D.md) (the separate Milestone D handoff was retired on 2026-10-17;
see [PROJECT_TRACKER.md](../PROJECT_TRACKER.md)). Formal constraint
model and solver, 3+ alternative floor-plan concepts, plan SVG, evaluators and
plan versioning, starting from an approved program and an approved site.
