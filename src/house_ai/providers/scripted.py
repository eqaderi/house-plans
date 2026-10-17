"""A provider that replays fixed responses: for tests and offline demos.

It records every request it receives, so tests can check what would have
been sent to a real provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import ProviderRequest, ProviderResponse


@dataclass
class ScriptedProvider:
    responses: list[str]
    name: str = "scripted"
    model: str = "scripted-1"
    requests: list[ProviderRequest] = field(default_factory=list)

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        if not self.responses:
            raise RuntimeError("scripted provider has no responses left")
        return ProviderResponse(text=self.responses.pop(0), provider=self.name, model=self.model)
