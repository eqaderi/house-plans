# ADR 0011: Agent-first interview interface (Claude Code, Gemini CLI, Codex)

Status: accepted (Milestone C finalization, 2026-10-17).
Supersedes ADR 0008 §6 (human-only TTY restriction on recording interview turns)
and clarifies ADR 0010 (`ClaudeProvider` is strictly optional).

## Context

The homeowner intends to design their house by conversing directly with interactive
coding agents — **Claude Code**, **Gemini CLI**, and **OpenAI Codex** — without
purchasing or configuring a separately billed Anthropic, OpenAI, or Gemini API
key.

In the initial Milestone C implementation:

- `house-ai interview answer`, `revise`, `confirm`, and `reject` refused non-human
  actors (`ApprovalRequiresHuman`) and required an interactive terminal
  (`sys.stdin.isatty() == True`), which prevented coding agents running shell
  commands from recording the homeowner's answers or confirmations.
- Answers could only be interpreted by the built-in English regex parser or by
  the optional `ClaudeProvider` (which requires `ANTHROPIC_API_KEY`), and only
  against the single currently pending question in the 30-question queue.

## Decision

1. **Coding agents are the primary AI interface; no API key is required.**
   The core workflow is:
   `Homeowner → Claude Code / Gemini CLI / Codex → house-ai CLI & ProjectStore → DesignBrief & SpaceProgram → Validation → Human Approval Gates`.
   The optional `ClaudeProvider` (`providers/claude.py`, ADR 0010) remains
   available when an API key is configured, but nothing in the core workflow
   depends on it.
2. **Coding agents may record homeowner interview turns (`--actor agent:<tool>`).**
   `InterviewTurn` and `InterviewService` allow `ActorKind.AGENT` (as well as
   `ActorKind.HUMAN`) on `answer`, `revision`, `confirmation`, `rejection`, and
   `resolution` turns, and those CLI commands run in non-interactive shells.
   `ActorKind.SYSTEM` remains forbidden on all interview turns.
3. **Human approval gates and provider consent remain strictly human-only.**
   `workflow approve`, `workflow reopen`, `site confirm`, `interview consent`,
   and `program reject` still require `ActorKind.HUMAN` and an interactive
   terminal (`sys.stdin.isatty()`). Coding agents can never approve a site,
   program, plan, or model gate on the homeowner's behalf.
4. **Verbatim homeowner words + structured agent interpretations (`--set`).**
   Every `interview answer` and `interview revise` turn records the homeowner's
   exact original words verbatim (in English, Persian, or mixed language) as an
   `owner_answer` fact, and accepts structured slot interpretations via
   `--set SLOT=VALUE`, `--unknown SLOT`, or `--interpret-json`. Every value
   proposed by an agent is validated through `slot_types.check()` and recorded
   with `method="agent:<id>"` and epistemic status `inference` until the
   homeowner explicitly confirms it (`interview confirm`).
5. **30-question completeness checklist + adaptive follow-up questions.**
   `house-ai interview checklist <dir> [--json]` (alias `interview status`)
   exposes the 30 predefined questions as a completeness checklist alongside
   site context, unverified site blockers, steep-hillside considerations,
   unconfirmed interpretations, and open contradictions. Agents may answer any
   checklist question or slot out of order (`--question <qid|slot>`) and may
   record adaptive architectural follow-up questions outside the 30 predefined
   questions (`--question <custom-id> --question-text "<question>" --topic <topic>`).
6. **Steep-hillside engineering assumptions.**
   On steep hillside sites (`relief_m >= 8.0` or `mean_slope_pct >= 20.0`, such
   as `projects/my-house/`), `build_program` records the explicit assumption
   `asm-hillside-engineering` (split-level massing, hillside construction,
   road-level access, excavation, retaining walls, slope drainage, structural
   engineering, and not assuming the full parcel is buildable), and
   `validate_program` warns (`steep_site_flat_pad`) if a single flat platform is
   selected on a steep hillside.

## Consequences

- Claude Code, Gemini CLI, and OpenAI Codex can conduct natural, adaptive
  architectural interviews in Persian, English, or mixed language and operate
  all of Milestone C without any paid API key.
- Every homeowner statement is preserved verbatim in `InterviewSession` and
  `DesignBrief`; every agent interpretation starts as `inference` and blocks the
  program gate until confirmed after asking the homeowner.
- Human approval gates (`site`, `program`, `plan`, `model`) remain hard,
  terminal-enforced human boundaries.
