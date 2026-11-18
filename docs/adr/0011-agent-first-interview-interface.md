# ADR 0011: Agent-first interview interface (Claude Code, Gemini CLI, Codex)

Status: accepted (Milestone C finalization, 2026-10-17).
Supersedes ADR 0008 §6 (human-only TTY restriction on recording interview turns)
and clarifies ADR 0010 (`ClaudeProvider` is strictly optional).

## Context

The owner intends to design their house by conversing directly with interactive
coding agents — **Claude Code**, **Gemini CLI**, and **OpenAI Codex** — without
purchasing or configuring a separately billed Anthropic, OpenAI, or Gemini API
key.

In the initial Milestone C implementation:

- `house-ai interview answer`, `revise`, `confirm`, and `reject` refused non-human
  actors (`ApprovalRequiresHuman`) and required an interactive terminal
  (`sys.stdin.isatty() == True`), which prevented coding agents running shell
  commands from recording the owner's answers or confirmations.
- Answers could only be interpreted by the built-in English regex parser or by
  the optional `ClaudeProvider` (which requires `ANTHROPIC_API_KEY`), and only
  against the single currently pending question in the 30-question queue.

## Decision

1. **Coding agents are the primary AI interface; no API key is required.**
   The core workflow is:
   `Owner → Claude Code / Gemini CLI / Codex → house-ai CLI & ProjectStore → DesignBrief & SpaceProgram → Validation → Human Approval Gates`.
   The optional `ClaudeProvider` (`providers/claude.py`, ADR 0010) remains
   available when an API key is configured, but nothing in the core workflow
   depends on it.
2. **Coding agents may record the owner's interview turns (`--actor agent:<tool>`).**
   `InterviewTurn` and `InterviewService` allow `ActorKind.AGENT` (as well as
   `ActorKind.HUMAN`) on `answer`, `revision`, `confirmation`, `rejection`, and
   `resolution` turns, and those CLI commands run in non-interactive shells.
   `ActorKind.SYSTEM` remains forbidden on all interview turns.
3. **Human approval gates and provider consent remain strictly human-only.**
   `workflow approve`, `workflow reopen`, `site confirm`, `interview consent`,
   and `program reject` still require `ActorKind.HUMAN` and an interactive
   terminal (`sys.stdin.isatty()`). Coding agents can never approve a site,
   program, plan, or model gate on the owner's behalf.
4. **The owner's words verbatim, agent interpretations structured (`--set`).**
   Every `interview answer` and `interview revise` turn records the owner's
   exact original words verbatim (in English, Persian, or mixed language) as an
   `owner_answer` fact, and accepts interpretations via `--set SLOT=VALUE`,
   `--unknown SLOT`, or `--interpret-json`. Every interpretation proposed by an
   agent is validated through `slot_types.check()` and recorded with
   `method="agent:<id>"` and epistemic status `inference` until the owner
   explicitly confirms it (`interview confirm`).
5. **30-question completeness checklist + adaptive follow-up questions.**
   `house-ai interview checklist <dir> [--json]` (alias `interview status`)
   exposes the 30 predefined questions as a completeness checklist alongside
   site context, unconfirmed site blockers, steep-hillside considerations,
   unconfirmed interpretations, and open contradictions. Agents may answer any
   checklist question or slot out of order (`--question <qid|slot>`) and may
   record adaptive architectural follow-up questions outside the 30 predefined
   questions (`--question <custom-id> --question-text "<question>" --topic <topic>`).

   Note (spec #9, part 4): what these commands print is defined once, in
   orchestration (`orchestration/interview_views.py`, `project_status.py`, the
   site summary in `site_context.py`), and pinned by key-set tests there. Each
   glossary term has one shape, the richest of the earlier ones: an
   Interpretation is `{slot, label, value, display, method, status}` in turn
   results, `unconfirmed` and `custom_turns`; a Contradiction is
   `{id, statement, tradeoff, slots, options}` with each option
   `{option, label, updates}` (turn results used to list the option labels
   only). Keys keep their names; outputs may gain keys and lose none.

   Note (spec #9, part 9): which slots the Space program needs, and which of
   those block the program gate, is one table (`program/needed_slots.py`):
   `adults`, `bedrooms` and `bathrooms` block; `storeys`, `budget` and
   `target_area` are needed and do not block; `slope_strategy` is needed on a
   sloped Site and does not block. The program build (its Open questions), the
   program checks (`missing_information`) and the checklist's
   `missing_required_slots` all read it, so the checklist now also lists
   `storeys`, `budget` and `target_area` while they are unknown. A slot's value
   and status in a Design brief are read by `domain/interview.py::slot_facts`,
   which applies the old-name translation of ADR 0025. "Sloped" (relief of 2 m
   or more) and "steep" (relief of 8 m or more, or a mean slope of 20 % or more)
   are `SiteContext.sloped` / `.steep`, with the thresholds in
   `constants/slopes.py`. The slot types stay in `interview/slot_types.py`;
   there is no slot catalogue.

## Consequences

- Claude Code, Gemini CLI, and OpenAI Codex can conduct natural, adaptive
  architectural interviews in Persian, English, or mixed language and operate
  all of Milestone C without any paid API key.
- Every answer is preserved verbatim in `InterviewSession` and `DesignBrief`;
  every agent interpretation starts as `inference` and blocks the program gate
  until the owner confirms it.
- Human approval gates (`site`, `program`, `plan`, `model`) remain hard,
  terminal-enforced human boundaries.
