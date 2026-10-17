"""Provider-neutral AI interface and explicit data-flow policy.

The domain never imports a vendor SDK. Vendor adapters implement
:class:`ModelProvider` (``providers/claude.py`` is the first, ADR 0010) and
raise :class:`ProviderError` for anything that goes wrong on the vendor side.

Private project data (the owner's survey, brief, photos) never leaves the
machine implicitly: every request declares the classification of what it
carries, and :func:`check_data_flow` refuses private content unless a human
has explicitly allowed that provider to receive it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from house_ai.domain.provenance import Actor, ActorKind, DataClassification


@dataclass(frozen=True)
class Attachment:
    #: What the content is, e.g. "site artifact v3", "design_brief.yaml".
    label: str
    classification: DataClassification
    content: str


@dataclass(frozen=True)
class ProviderRequest:
    system: str
    prompt: str
    attachments: list[Attachment] = field(default_factory=list)
    #: Classification of the prompt itself. None is treated as PRIVATE, with or
    #: without attachments, so an unlabelled prompt cannot leak owner data.
    classification: DataClassification | None = None
    #: JSON Schema the response must satisfy, when structured output is needed.
    response_schema: dict | None = None


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    provider: str
    model: str


@dataclass(frozen=True)
class DataFlowPolicy:
    """Which providers may receive private data, and who said so."""

    allowed_private_providers: frozenset[str] = frozenset()
    granted_by: Actor | None = None

    def __post_init__(self) -> None:
        if self.allowed_private_providers and (
            self.granted_by is None or self.granted_by.kind is not ActorKind.HUMAN
        ):
            raise ValueError("only a human can allow private data to reach a provider")


class PrivateDataFlowError(PermissionError):
    pass


class ProviderError(RuntimeError):
    """A provider could not answer. The message is safe to show: it never holds a key.

    ``kind`` is one of: not_configured, auth, rate_limit, unavailable, network,
    bad_request, refused, incomplete.
    """

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind

    #: Kinds that will not go away by asking again in this session.
    FATAL = frozenset({"not_configured", "auth", "bad_request"})

    @property
    def fatal(self) -> bool:
        return self.kind in self.FATAL


def check_data_flow(provider: str, request: ProviderRequest, policy: DataFlowPolicy) -> None:
    private = [
        a.label for a in request.attachments if a.classification is DataClassification.PRIVATE
    ]
    prompt_classification = request.classification or DataClassification.PRIVATE
    if prompt_classification is DataClassification.PRIVATE:
        private.append("prompt")
    if private and provider not in policy.allowed_private_providers:
        raise PrivateDataFlowError(
            f"refusing to send private data to {provider!r} without explicit consent: "
            + ", ".join(private)
        )


class ModelProvider(Protocol):
    name: str

    def complete(self, request: ProviderRequest) -> ProviderResponse: ...


def send(
    provider: ModelProvider, request: ProviderRequest, policy: DataFlowPolicy
) -> ProviderResponse:
    """The only sanctioned path to a provider: policy first, then the call."""
    check_data_flow(provider.name, request, policy)
    return provider.complete(request)
