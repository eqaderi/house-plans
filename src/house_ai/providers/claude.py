"""Anthropic Claude adapter (ADR 0010).

Optional: install with ``pip install -e '.[ai]'`` and set ``ANTHROPIC_API_KEY``
(an Anthropic API key from console.anthropic.com; a Claude.ai or Claude Code
subscription is not an API key). The key is read by the SDK from the
environment and never stored, logged or put in an error message.

Calls go through :func:`house_ai.providers.base.send` like every provider, so
private content reaches Claude only with the owner's consent. Structured output
uses ``output_config.format``; the caller still validates the reply.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import ProviderError, ProviderRequest, ProviderResponse

DEFAULT_MODEL = "claude-opus-5-5"
#: Server-side fallback on a safety decline, routed by Anthropic per refusal category.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
#: JSON Schema keywords structured output does not accept; the caller validates them.
_UNSUPPORTED = {
    "title", "default", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "multipleOf", "minLength", "maxLength", "minItems", "maxItems", "pattern",
}  # fmt: skip


def output_schema(schema: Any) -> Any:
    """``schema`` in the subset structured output accepts: every object closed."""
    if isinstance(schema, list):
        return [output_schema(s) for s in schema]
    if not isinstance(schema, dict):
        return schema
    out = {k: output_schema(v) for k, v in schema.items() if k not in _UNSUPPORTED}
    if out.get("type") == "object":
        out["additionalProperties"] = False
    return out


def _sdk():
    try:
        import anthropic
    except ImportError as exc:
        raise ProviderError(
            "not_configured",
            "the Anthropic SDK is not installed; run: .venv/bin/pip install -e '.[ai]'",
        ) from exc
    return anthropic


@dataclass
class ClaudeProvider:
    """:class:`~house_ai.providers.base.ModelProvider` for the Claude API."""

    model: str = DEFAULT_MODEL
    #: An ``anthropic.Anthropic`` client; tests pass a fake one.
    client: Any = None
    name: str = "anthropic"
    effort: str = "low"
    max_tokens: int = 4000
    timeout_s: float = 60.0

    @classmethod
    def from_environment(cls, model: str | None = None) -> ClaudeProvider:
        anthropic = _sdk()
        try:
            client = anthropic.Anthropic(timeout=cls.timeout_s, max_retries=2)
        except anthropic.AnthropicError as exc:
            raise ProviderError(
                "not_configured", "no Anthropic API key: set ANTHROPIC_API_KEY in your terminal"
            ) from exc
        return cls(model=model or DEFAULT_MODEL, client=client)

    def _params(self, request: ProviderRequest) -> dict[str, Any]:
        content = request.prompt
        for a in request.attachments:
            content += f"\n\n--- {a.label} ---\n{a.content}"
        output_config: dict[str, Any] = {"effort": self.effort}
        if request.response_schema is not None:
            output_config["format"] = {
                "type": "json_schema",
                "schema": output_schema(request.response_schema),
            }
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": content}],
            "output_config": output_config,
            "betas": [FALLBACK_BETA],
            "fallbacks": "default",
        }

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        if self.client is None:
            raise ProviderError("not_configured", "no Claude client; use from_environment()")
        response = self._call(self._params(request))
        if response.stop_reason == "refusal":
            raise ProviderError("refused", "Claude declined this request")
        if response.stop_reason == "max_tokens":
            raise ProviderError("incomplete", "Claude's reply was cut off")
        text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        return ProviderResponse(text=text, provider=self.name, model=response.model)

    def _call(self, params: dict[str, Any]) -> Any:
        try:
            return self.client.beta.messages.create(**params)
        except Exception as exc:
            raise _translate(exc) from exc


def _translate(exc: Exception) -> Exception:
    """An SDK exception as a ProviderError with a message safe to show."""
    try:
        import anthropic
    except ImportError:
        return exc
    if isinstance(exc, anthropic.AuthenticationError | anthropic.PermissionDeniedError):
        return ProviderError("auth", "the Anthropic API key was refused (check ANTHROPIC_API_KEY)")
    if isinstance(exc, anthropic.RateLimitError):
        return ProviderError("rate_limit", "Anthropic rate limit or spending limit reached")
    if isinstance(exc, anthropic.NotFoundError | anthropic.BadRequestError):
        return ProviderError("bad_request", f"Anthropic rejected the request ({exc.status_code})")
    if isinstance(exc, anthropic.APIStatusError):
        return ProviderError("unavailable", f"Anthropic is unavailable ({exc.status_code})")
    if isinstance(exc, anthropic.APIConnectionError):  # includes timeouts
        return ProviderError("network", "could not reach the Anthropic API")
    # The SDK raises a TypeError when it finds no key, token or login profile.
    if isinstance(exc, anthropic.AnthropicError) or (
        isinstance(exc, TypeError) and "authentication" in str(exc)
    ):
        return ProviderError(
            "not_configured", "no Anthropic credentials: set ANTHROPIC_API_KEY in your terminal"
        )
    return exc
