# How we work: from DWG to an agreed plan

The repo is the memory. Sessions are short and disposable. Any session,
Claude Code on this laptop or Codex on the other, starts by reading the
repo's state files and ends by updating them, so nothing depends on what one
chat remembers.

## State files (read at the start of every session, update at the end)

| File | Holds |
|---|---|
| `docs/STATUS.md` | Current phase, current revision, what changed last, what is next. One screen. |
| `docs/brief.md` | What the house must be: household, rooms, priorities. Changes only when the owner says so. |
| `docs/open-questions.md` | Facts still missing. Never guessed. |
| `docs/decisions.md` | Every decision with date, reason and who made it. |
| `docs/feedback/rev-<X>.md` | The owner's review of revision X, one numbered item per comment, and what was done with each. |
| `git log` | Every revision is a commit tagged `rev-<X>`. |

## Phases

0. **Intake.** The owner answers the intake questions in `docs/brief.md` and
   drops the DWG files into `sources/`. The agent records checksums and lists
   what is still missing in `docs/open-questions.md`.
1. **Site.** DWG → DXF into `derived/`. The agent reports units, coordinate
   system, plot boundary, plot area, levels and the street edges, with the
   commands it ran, and asks the owner to confirm them. Output: a site sheet
   and the datum, recorded in `docs/decisions.md`.
2. **Envelope.** From the municipal conditions (دستور نقشه): the buildable
   area, coverage, height and setbacks, drawn over the survey. Nothing is
   designed outside it.
3. **Sketch stage: options until one fits.** This is most of the work, so it
   stays light. Each option is a spec (`design/option-a.yaml`, ...) with
   `stage: sketch`. The agent runs `bin/hp sketch` and shows the owner one
   true-scale sheet per floor, with dimensions and room areas. Every sketch
   passes the full geometry and rule checks, so it is exact, just not
   documented. The owner answers in the chat ("no", "closer, but swap the
   kitchen and the guest room", "option B with A's stair"). No feedback files,
   no reports, no IFC, no review copies: the agent only commits the option
   and adds one line to `docs/STATUS.md` (which option, what the owner said),
   so the next session knows which ideas were already rejected.
4. **Final stage: the agreed plan, fully documented.** When the owner says
   "this one", set `stage: final` in that spec and run `bin/hp build`. Now the
   full set is produced and audited: DXF with true dimensions, IFC model,
   read-back of both, the drawing-text audit, the room schedule and the
   report. Changes from here go round by round:
   1. The agent builds revision X, commits, tags `rev-<X>`, and copies the
      sheets to `reviews/rev-<X>/`.
   2. The owner writes numbered notes in `docs/feedback/rev-<X>.md`.
   3. The next session answers every item (done / partly / question) and its
      side effects, applies them, and builds again.
   4. Repeat until the owner writes "Approved: yes".
5. **Hand-off.** The approved revision goes to the licensed engineers
   (architect and structural engineer of the engineering organisation) for
   review, structural design and the permit set.

## Sessions

- **Sketch stage:** stay in one session for as many options as the
  conversation stays clear; start a new one when it gets long. `docs/STATUS.md`
  carries what was tried and rejected.
- **Final stage:** one session per revision round: start it, read the state
  files, do the round, update `docs/STATUS.md`, commit, end. A fresh session
  per round keeps the context clean and the work reproducible.
- **Stay in the same session** for small follow-ups within the round ("move
  that door 20 cm"). Start a new one when the conversation gets long, when you
  switch laptops, or when a round is done.
- **Switching laptops:** push from one, pull on the other. The repo needs a
  private remote (GitHub, GitLab, or a shared drive). `sources/` can be large
  or private; if it stays out of git, copy it by hand and check
  `shasum -a 256 -c sources/MANIFEST.sha256` on arrival.
- **Resuming a chat** works too (`claude --continue`, `codex resume`), but the
  state files are what make a new session as good as an old one.

## Unattended rounds (Claude Code)

For a round the agent can finish alone, give it a measurable end state with
`/goal`, for example:

> /goal design/house.yaml applies every item in docs/feedback/rev-C.md;
> `bin/hp check design/house.yaml` prints 0 errors; `hooks/gate.sh` exits 0;
> docs/brief.md and the program block are unchanged; show the outputs. Stop
> after 20 turns.

The goal is re-checked after every turn and survives `--resume`. In Codex,
put the same end state at the top of the prompt.

## Opening prompt for a new session

> Continue the house plan. Read AGENTS.md, the house-plan skill,
> docs/STATUS.md, docs/brief.md, docs/open-questions.md and the newest file in
> docs/feedback/. Tell me in a few lines where we are and what you will do,
> then do it.

## What the agent delivers

**Sketch stage, per option:** the sheet PNGs (`out/<option>/sketch-*.png`),
the net area of each room, any rule that fails, and one line on what makes
this option different. Nothing else.

**Final stage, per revision:**

- The PDF sheets and the room schedule (`out/house/report.md`).
- Each feedback item: done, partly done (why), or a question.
- What changed that the owner did not ask for, and why it had to.
- Any rule now failing, any unverified rule involved, new open questions.
- `hooks/gate.sh` passed.
