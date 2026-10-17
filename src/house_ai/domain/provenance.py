"""Who produced what, from which inputs, and how."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .base import Id, Sha256, StrictModel, UtcDatetime


class ActorKind(StrEnum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class Actor(StrictModel):
    kind: ActorKind
    id: str = Field(min_length=1, max_length=128)
    display_name: str | None = None
    #: AI provider and model, for agent actors only (e.g. "anthropic", "claude-opus-5-5").
    provider: str | None = None
    model: str | None = None

    @model_validator(mode="after")
    def _provider_only_for_agents(self) -> Actor:
        if self.kind is not ActorKind.AGENT and (self.provider or self.model):
            raise ValueError("provider/model may only be set on agent actors")
        return self

    @classmethod
    def parse(cls, text: str) -> Actor:
        """Parse "kind:id", e.g. "agent:claude-code" or "human:owner"."""
        kind, sep, ident = text.partition(":")
        if not sep or not ident:
            raise ValueError(f"actor must look like 'kind:id', got {text!r}")
        return cls(kind=ActorKind(kind), id=ident)


class DataClassification(StrEnum):
    #: Owner-specific material. Never sent to a model provider implicitly.
    PRIVATE = "private"
    #: Fabricated for tests and examples; safe to share.
    SYNTHETIC = "synthetic"
    #: Redistributable public data.
    PUBLIC = "public"


class ArtifactKind(StrEnum):
    """Kinds of versioned artifacts kept in a project store."""

    SOURCE_DOCUMENT = "source_document"
    CAD_IMPORT = "cad_import"
    SITE = "site"
    DESIGN_BRIEF = "design_brief"
    SPACE_PROGRAM = "space_program"
    ASSUMPTIONS = "assumptions"
    OPEN_QUESTIONS = "open_questions"
    CONSTRAINT_SET = "constraint_set"
    CODEPACK = "codepack"
    PLAN = "plan"
    EVALUATION_REPORT = "evaluation_report"
    REVISION_REPORT = "revision_report"
    BUILD_RECORD = "build_record"
    OWNER_STATEMENTS = "owner_statements"


class ArtifactRef(StrictModel):
    """Pointer to one immutable version of an artifact, pinned by content hash."""

    kind: ArtifactKind
    id: Id
    version: int = Field(ge=1)
    sha256: Sha256


class Provenance(StrictModel):
    created_at: UtcDatetime
    created_by: Actor
    #: How it was produced, e.g. "hand_authored", "owner_interview", "dxf_import".
    method: str = Field(min_length=1)
    tool: str | None = None
    tool_version: str | None = None
    inputs: list[ArtifactRef] = Field(default_factory=list)
    notes: str | None = None


class SourceDocument(StrictModel):
    """An original input file, preserved byte-for-byte under source/."""

    id: Id
    original_filename: str = Field(min_length=1)
    sha256: Sha256
    size_bytes: int = Field(ge=0)
    media_type: str | None = None
    #: Path relative to the project root.
    stored_path: str
    classification: DataClassification
    imported_at: UtcDatetime
    imported_by: Actor
