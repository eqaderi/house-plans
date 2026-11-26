# C11: generate the corrected design, then prove it with a reviewer fan-out

These are the instructions for the agent that makes design study **C11** for `projects/my-house`.
The owner starts it with the short prompt at the end of this file. Follow every phase in order.

## Phase 0: read before anything else

1. `AGENTS.md` → `docs/AGENT_CONTRACT.md` (all project rules), then the skills
   `generate-plan-options`, `critique-plan` and `visual-review` in `.agents/skills/`.
2. `projects/my-house/design/OWNER_DESIGN_RULES.md`, **in full**. It was corrected on 2026-11-22
   (stmt-027, stmt-028, stmt-029): rules 1.4, 1.5, 2.4, 2.6, 4.2, 4.3, 4.8, 4.9–4.11 and 6.7 are new
   or rewritten. Every rule is a hard check.
3. `projects/my-house/reviews/c10-expert-review-2026-11-22/CONSOLIDATED.md`: the merged result of 27
   specialist reviews of C10. Its correction list (`C11-<THEME>-NN`), its conflict resolutions and
   its default answers to open owner questions are your work order. Open the individual reviews
   (`01-…` to `27-…` in the same folder) whenever you need the detail behind a row.
4. The owner's words of this session: `.venv/bin/house-ai statement list projects/my-house`
   (stmt-027, stmt-028, stmt-029).
5. C10 itself: `projects/my-house/design/990_2026-11-18_claude-c10/` (README, `design.py`,
   `engine.py`, `checks.py`, `model3d.py`, `report.py`). Reuse its engine, 3D model and page;
   C10's own drawings hid the missing supports, so do not trust them, and trust its checks only
   where `CONSOLIDATED.md` says they hold.

## Phase 1: design C11

**Folder:** `projects/my-house/design/989_<YYYY-MM-DD>_<tool>-c11/` (today's date, your tool name).
Copy C10's code in, then change it. Add a row at the top of the table in
`projects/my-house/design/README.md`. Never rename an older folder.

**Status:** the site is still `SITE_NEEDS_CONFIRMATION`, so C11 is an exploratory concept: store
nothing in `ProjectStore`, and never call it validated, permit-ready, code-compliant or engineered.

**One design.** The owner asked for *"a new plan with all the corrections"*, which means one corrected
design, not options. Show it next to C10 with the comparison view of rule 8.5
(`design/991_2026-10-27_claude-c09/compare.py`): a table of only what changed, plus each floor of C10
and C11 side by side with the changed rooms outlined in orange.

**What C11 must do:**
- Apply **every BLOCKER and MAJOR** row of `CONSOLIDATED.md`. Apply a MINOR row when it costs little.
  Where you cannot apply a row, say why with numbers. Never skip a row silently.
- Answer the owner's own questions directly, floor by floor: what the garage stands on, what the
  main floor stands on, and what every terrace and balcony stands on. A floor stands on a wall,
  a column line or solid ground (rule 4.9). No part of any floor may stand over an undrawn void.
- Arrival court: carry out the owner's full proposal (rule 4.10). Dig out the ground west of the court and
  south of the forecourt, put the road stair at the far west against the road, and give the stair
  landings. Add the walled *hayat*, the separate pedestrian gate, and guards on every drop.
- Outdoor stairs: every one must be comfortable (rule 4.11). Use risers of 0.175 m or less, goings of 0.28 m or more,
  at most 16 risers per flight and landings of at least 1.2 m. Dig to make room.
- Use realistic wall thicknesses (`CONSOLIDATED.md`). Show terrace slabs stepped down where they
  sit over rooms. Draw the service risers, plant room and tanks, and the structural grid.
- Follow every corrected rule: compact laundry of 4–6 m², kitchen 15–17 m² with seats for 3–4,
  dining that seats 8, terraces on the south and east, and bedroom windows over open ground.
- For any open owner question, use the default `CONSOLIDATED.md` recommends and list it on the
  page as an open decision.

**Add the checks** listed in `CONSOLIDATED.md` §7 to C11's `checks.py`. At minimum:
- every slab region is supported;
- plans, sections and 3D draw the same supports and retaining walls;
- outdoor stair geometry;
- terrace slab drops;
- clear routes past furniture and cars;
- 1.5 m clear landing at the lift on every floor;
- prayer mats on the qibla;
- 2 m of open ground in front of every bedroom window;
- a guard at every drop of 0.6 m or more;
- a wall-over-wall alignment report.

All must pass, or be reported as failing, with numbers.

**Deliverables** in the C11 folder:
- `design.py`, `engine.py`, `checks.py` and `checks.json`.
- Plans of all three levels plus the garden, furnished.
- A new **"what stands on what" drawing**: each floor outlined over the one below, showing supports, voids and the column grid.
- Sections that show every retaining wall and support.
- A site plan and the 3D model with stills.
- `index.html`. It explains the idea first in plain words, then shows the drawings, the comparison with C10, the rule checklist (rule 8.1: rule → pass + evidence) and the open decisions.
- `CORRECTIONS.md`: a ledger with one line per `C11-*` row. Each line says done, partly or not done; how it was done; and the evidence (a number or a drawing).

Rebuild from the repository root with the folder's `build.py`.

## Phase 2: prove it with a reviewer fan-out

When Phase 1 is complete, check whether C11 fulfilled what the owner really asked for.

1. Create `projects/my-house/reviews/c11-expert-review-<YYYY-MM-DD>/BRIEF.md`. Adapt
   `../c10-expert-review-2026-11-22/BRIEF.md` to C11: its paths, levels and footprints, plus this
   session's owner words (stmt-027, stmt-028, stmt-029).
2. Launch one reviewer agent for each of the **same 27 specialties** used for C10. Use the same
   numbers, slugs and finding prefixes, listed in the index table of `CONSOLIDATED.md`. Add a 28th
   reviewer, **"owner-request fidelity" (NN 28, prefix OWN)**. It checks C11 against stmt-027,
   stmt-028, stmt-029 and every corrected rule. It also checks `CORRECTIONS.md` line by line: is each
   "done" really done in `design.py` and the drawings?
3. Every reviewer:
   - reads `BRIEF.md`, `OWNER_DESIGN_RULES.md`, the C11 folder, and the C10 review in its own
     specialty (`../c10-expert-review-2026-11-22/NN-*.md`);
   - marks every C10 finding in its specialty as **fixed / partly fixed / not fixed / made worse**,
     with evidence;
   - lists new problems C11 introduced;
   - writes `NN-<slug>.md` and replies with only the path and its top 5 findings.
4. At most 20 agents run at once. Launch 20, then start each remaining reviewer as soon as a slot
   frees. Never fabricate or predict a pending reviewer's result.
5. Merge the 28 reports into `c11-expert-review-<date>/CONSOLIDATED.md` with the same structure as
   the C10 one, plus a scorecard: C10 findings fixed / partly / not fixed / worse, and new findings
   by severity.

## Phase 3: close the loop and report

1. Fix every BLOCKER the C11 reviewers found, and every MAJOR that does not need an owner decision.
   Do one fix round, rebuild, and re-run `checks.py`. If a fix needs the owner, put it in the open
   decisions instead.
2. Record any new owner words verbatim (`house-ai statement add … --actor agent:<tool>`). Never
   approve a gate or confirm site facts.
3. Run and report the project's finishing checks:
   ```bash
   .venv/bin/python -m pytest -q
   .venv/bin/ruff check src tests examples tools
   .venv/bin/house-ai schemas check
   .venv/bin/python tools/leak_scan.py
   .venv/bin/python tools/check_tracker.py
   ```
4. Tell the owner, briefly and in plain words:
   - what C11 changed;
   - the floor-by-floor answer to "what stands on what";
   - the reviewers' scorecard;
   - what is still open, with your recommendation for each item;
   - where to open `index.html`.

Never write a personal name into any file.

---

## The prompt to paste

```
Read projects/my-house/reviews/c10-expert-review-2026-11-22/C11-PROMPT.md and carry out all of it:
Phase 0 (read), Phase 1 (design C11 with every correction from CONSOLIDATED.md and the corrected
OWNER_DESIGN_RULES.md), Phase 2 (fan out the 28 reviewer agents against C11), and Phase 3 (fix
what they find and report to me in plain words). Use --actor agent:claude-code.
```
