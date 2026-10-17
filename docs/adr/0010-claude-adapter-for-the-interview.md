# ADR 0010: An optional Claude adapter for the AI-assisted interview

Status: accepted (Milestone C, 2026-10-17); see also
[ADR 0011](0011-agent-first-interview-interface.md) (the primary workflow is
agent-first via Claude Code, Gemini CLI and OpenAI Codex without requiring an
API key; this SDK adapter is strictly optional).

## Context

Milestone C shipped a deterministic interview and an LLM hook (`LlmAssist`:
word a question, read an answer the parser cannot) tested only with the
scripted provider. The owner wants a real AI-assisted architectural interview
that uses the selected project's site, labels unverified facts, keeps the
conversation, never approves anything, and never puts keys in git. Their
consumer subscriptions (ChatGPT Plus, Claude Code Team, Google AI Pro) are not
API credentials.

## Decision

1. **One vendor adapter: `providers/claude.py` (`ClaudeProvider`)**, using the
   official `anthropic` Python SDK (1.15). It is an optional extra
   (`pip install -e '.[ai]'`), imported only by the adapter, and the adapter is
   imported only by the CLI. `domain`, `storage` and `orchestration` stay
   vendor-free (test: `test_only_vendor_adapters_import_a_vendor_sdk`).
2. **Model and request.** Default `claude-opus-5-5` (`--model` overrides),
   effort `low` (short wording and extraction tasks). Structured output through
   `output_config.format` with the request's JSON Schema reduced to the
   supported subset; the reply is still validated against the slot types and
   anything invalid is dropped. Server-side fallback on a safety decline
   (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`).
3. **Credentials** come only from the SDK's own resolution: `ANTHROPIC_API_KEY`
   in the owner's environment, or an `ant auth login` profile. Nothing is
   stored by house-ai; `.env` and key files are git-ignored.
4. **Errors.** Every SDK failure becomes a `ProviderError` with a kind
   (not_configured, auth, rate_limit, unavailable, network, bad_request,
   refused, incomplete) and a message that never contains the key. The
   interview falls back to the planned question or the built-in parser and
   says so; a fatal kind (no credentials, refused key, bad request) turns the
   AI off for the rest of the session.
5. **Consent and context.** `interview run --ai anthropic` asks the owner, in
   their terminal, to type `allow anthropic` (a consent turn in the session)
   before anything is sent; `send()` still enforces it on every call. The AI
   receives the site values with their status ("from the survey; NOT yet
   confirmed by the owner"), the owner's statements and what was understood so
   far. While the site gate is not approved, the code (not the AI) adds to every
   reworded question: "Anything said here about your site comes from the
   survey; you have not confirmed the site yet."
6. **Persistence.** The answer turn stores the question exactly as shown (the
   AI's wording) and the `provider` and `model` that worded it or read the
   answer. Resuming re-asks the pending question. Contradiction choices are
   never reworded.
7. **What the AI may not do** is unchanged from ADR 0008: it proposes; every
   value it reads is an inference until the owner confirms it; it answers,
   confirms and approves nothing.

## Consequences

- The interview runs with a real model as soon as the owner has an Anthropic
  API key; without one it runs exactly as before.
- Tests use a fake client and the scripted provider: no network, no key, no
  cost. A live call has not been made from this repository.
- `InterviewTurn` gained `model`; stored sessions written by older code must be
  regenerated (the example outputs were).
- Questions stay planner-chosen. AI-generated follow-up questions are not
  implemented.
