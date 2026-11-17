"""The Claude adapter and AI help in the interview (ADR 0010). No network, no key: the
Anthropic client is a fake, and all households and sites are synthetic."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from house_ai.domain.interview import TurnKind
from house_ai.orchestration.interview import UNCONFIRMED_SITE_LABEL, InterviewService
from house_ai.orchestration.statements import record_owner_statement
from house_ai.providers.base import (
    Attachment,
    ProviderError,
    ProviderRequest,
    ProviderResponse,
)
from house_ai.providers.claude import DEFAULT_MODEL, ClaudeProvider, output_schema
from house_ai.providers.scripted import ScriptedProvider

from .conftest import AGENT, HUMAN
from .test_interview import _project

FAKE_KEY = "sk-ant-test-not-a-real-key"


class FakeMessages:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _client(*replies):
    messages = FakeMessages(replies)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def _reply(text: str, stop: str = "end_turn", model: str = DEFAULT_MODEL):
    return SimpleNamespace(
        stop_reason=stop, model=model, content=[SimpleNamespace(type="text", text=text)]
    )


# ------------------------------------------------------------ the adapter


def test_claude_request_carries_model_schema_fallback_and_attachments():
    client, messages = _client(_reply('{"values": []}'))
    provider = ClaudeProvider(client=client)
    schema = {
        "title": "X", "type": "object", "required": ["n"],
        "properties": {"n": {"type": "integer", "minimum": 0, "title": "N"},
                       "inner": {"type": "object", "properties": {}}},
    }  # fmt: skip
    request = ProviderRequest(
        system="sys", prompt="the question",
        attachments=[Attachment(label="site", classification=None, content="600 m²")],
        response_schema=schema,
    )  # fmt: skip
    response = provider.complete(request)
    assert response == ProviderResponse(text='{"values": []}', provider="anthropic",
                                        model=DEFAULT_MODEL)  # fmt: skip
    (call,) = messages.calls
    assert call["model"] == "claude-opus-5-5" and call["system"] == "sys"
    assert call["fallbacks"] == "default" and call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["output_config"]["effort"] == "low"
    sent = call["output_config"]["format"]["schema"]
    assert sent == output_schema(schema)
    assert "title" not in sent and "minimum" not in sent["properties"]["n"]
    assert sent["additionalProperties"] is False
    assert sent["properties"]["inner"]["additionalProperties"] is False
    assert call["messages"] == [{"role": "user", "content": "the question\n\n--- site ---\n600 m²"}]


@pytest.mark.parametrize(("stop", "kind"), [("refusal", "refused"), ("max_tokens", "incomplete")])
def test_a_refusal_or_a_cut_off_reply_is_an_error_not_an_answer(stop, kind):
    client, _ = _client(_reply('{"values": [', stop=stop))
    with pytest.raises(ProviderError) as err:
        ClaudeProvider(client=client).complete(ProviderRequest(system="s", prompt="p"))
    assert err.value.kind == kind


def test_sdk_errors_become_provider_errors_without_the_key():
    anthropic = pytest.importorskip("anthropic")
    import httpx2

    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

    def status(cls, code):
        response = httpx2.Response(code, request=request)
        return cls(f"bad key {FAKE_KEY}", response=response, body={"key": FAKE_KEY})

    cases = [
        (status(anthropic.AuthenticationError, 401), "auth", True),
        (status(anthropic.RateLimitError, 429), "rate_limit", False),
        (status(anthropic.InternalServerError, 529), "unavailable", False),
        (status(anthropic.BadRequestError, 400), "bad_request", True),
        (anthropic.APIConnectionError(request=request), "network", False),
        (TypeError("Could not resolve authentication method."), "not_configured", True),
    ]
    for exc, kind, fatal in cases:
        client, _ = _client(exc)
        with pytest.raises(ProviderError) as err:
            ClaudeProvider(client=client).complete(ProviderRequest(system="s", prompt="p"))
        assert err.value.kind == kind and err.value.fatal is fatal
        assert FAKE_KEY not in str(err.value)


# ------------------------------------------------------------ the interview


@pytest.fixture
def unverified(new_store):
    """A project whose site is ingested but not confirmed, with one owner statement."""
    store = _project(new_store, approve_site=False)
    record_owner_statement(store, subject="slope", words="My land is genuinely steep.",
                           stated_by="owner", channel="chat", actor=AGENT)  # fmt: skip
    svc = InterviewService(store)
    svc.start(AGENT)
    return svc


def test_the_ai_words_the_question_and_the_shown_wording_is_kept(unverified):
    svc = unverified
    svc.consent(HUMAN, "scripted")
    provider = ScriptedProvider(["On your sloping 1400 m² plot: who will live in the house?"])
    svc.use_ai(provider)
    prompt = svc.pending()
    asked = svc.ask(prompt)
    assert asked.text.startswith("On your sloping") and asked.model == "scripted-1"
    # the site is unconfirmed: the label is added by code, whatever the AI wrote
    assert asked.notes == [UNCONFIRMED_SITE_LABEL]
    context = json.loads(json.loads(provider.requests[0].prompt)["context"])
    assert context["site"]["status"] == "from the survey; NOT yet confirmed by the owner"
    assert context["owner_said"] == [{"about": "slope", "words": "My land is genuinely steep."}]
    svc.answer("Two adults and one child.", HUMAN, shown=asked)
    turn = svc.session().turns[-1]
    assert turn.kind is TurnKind.ANSWER and turn.question_text == asked.text
    assert (turn.provider, turn.model) == ("scripted", "scripted-1")
    assert svc.state().values["adults"] == 2  # read by the parser; the AI only worded it


@pytest.mark.parametrize("verified", [False, True])
def test_every_ai_wording_is_labelled_while_the_site_is_unconfirmed(new_store, verified):
    svc = InterviewService(_project(new_store, approve_site=verified))
    svc.start(AGENT)
    svc.consent(HUMAN, "scripted")
    # no digit, no obvious site word
    svc.use_ai(ScriptedProvider(["Who will share the hillside home with you?"]))
    asked = svc.ask(svc.pending())
    assert asked.text == "Who will share the hillside home with you?"
    assert asked.notes == ([] if verified else [UNCONFIRMED_SITE_LABEL])


def test_without_consent_nothing_is_sent_and_the_planned_question_is_shown(unverified):
    provider = ScriptedProvider(["should never be used"])
    unverified.use_ai(provider)
    prompt = unverified.pending()
    asked = unverified.ask(prompt)
    assert asked.text == prompt.text and asked.provider is None
    assert provider.requests == [] and "not allowed" in asked.notes[0]


class FailingProvider:
    name = "scripted"

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        raise ProviderError(self.kind, f"{self.kind} happened")


@pytest.mark.parametrize(("kind", "stays_on"), [("rate_limit", True), ("auth", False)])
def test_a_provider_error_falls_back_to_the_built_in_interview(unverified, kind, stays_on):
    svc = unverified
    svc.consent(HUMAN, "scripted")
    svc.use_ai(FailingProvider(kind))
    prompt = svc.pending()
    asked = svc.ask(prompt)
    assert asked.text == prompt.text and f"{kind} happened" in asked.notes[0]
    assert (svc.assist is not None) is stays_on
    result = svc.answer("Two adults.", HUMAN, shown=asked)
    assert svc.state().values["adults"] == 2 and result.understood
    assert svc.session().turns[-1].provider is None  # the AI did nothing for this turn


def test_an_unreadable_answer_is_read_by_the_ai_and_recorded_with_its_model(svc_verified):
    svc = svc_verified
    svc.consent(HUMAN, "scripted")
    svc.use_ai(ScriptedProvider(['{"values": [{"slot": "adults", "value": 2}]}'],
                                model="scripted-2"))  # fmt: skip
    result = svc.answer("Just us, the happy pair.", HUMAN)  # the parser cannot read this
    assert [(u.slot, u.value, u.method) for u in result.understood if u.slot == "adults"] == [
        ("adults", 2, "llm:scripted")
    ]
    turn = svc.session().turns[-1]
    assert (turn.provider, turn.model) == ("scripted", "scripted-2")
    assert svc.state().slots["adults"].status == "inference"  # still needs the owner


def test_contradiction_choices_are_never_reworded(svc_verified):
    svc = svc_verified
    svc.consent(HUMAN, "scripted")
    provider = ScriptedProvider(["reworded"] * 10)
    for answer in ("Me and my wife.", "Two bedrooms.", "One bathroom, with an en-suite.",
                   "One level, a bungalow. We need a lift for later."):  # fmt: skip
        svc.answer(answer, HUMAN)
    svc.use_ai(provider)
    prompt = svc.pending()
    assert prompt.kind == "resolve"
    asked = svc.ask(prompt)
    assert asked.text == prompt.text and provider.requests == []


@pytest.fixture
def svc_verified(new_store):
    service = InterviewService(_project(new_store))
    service.start(AGENT)
    return service


def test_cli_run_with_ai_asks_consent_and_shows_the_ai_wording(new_store, monkeypatch, capsys):
    from house_ai.cli import main as cli

    store = _project(new_store)
    provider = ScriptedProvider(["Who will call this house home?", "And how many bedrooms?"])
    monkeypatch.setattr(cli, "_ai_provider", lambda name, model: provider)
    replies = iter(["allow scripted", "Two adults.", "y", ":quit"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *_: next(replies))
    assert cli.main(["interview", "run", str(store.root), "--owner", "example-owner",
                     "--ai", "anthropic"]) == 0  # fmt: skip
    out = capsys.readouterr().out
    assert "Who will call this house home?" in out and "AI assistant: scripted" in out
    svc = InterviewService(store)
    consent = [t for t in svc.session().turns if t.kind is TurnKind.CONSENT]
    assert consent and consent[0].actor.id == "example-owner"
    answer = next(t for t in svc.session().turns if t.kind is TurnKind.ANSWER)
    assert answer.question_text == "Who will call this house home?"


def test_cli_run_without_credentials_continues_without_ai(new_store, monkeypatch, capsys):
    from house_ai.cli import main as cli

    def missing(name, model):
        raise ProviderError("not_configured", "set ANTHROPIC_API_KEY")

    store = _project(new_store)
    monkeypatch.setattr(cli, "_ai_provider", missing)
    replies = iter([":quit"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *_: next(replies))
    assert cli.main(["interview", "run", str(store.root), "--owner", "example-owner",
                     "--ai", "anthropic"]) == 0  # fmt: skip
    assert "AI not available: set ANTHROPIC_API_KEY" in capsys.readouterr().out
