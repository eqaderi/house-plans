"""Who produced what, from which inputs, and how."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from house_ai.constants.actors import DISALLOWED_HUMAN_PREFIXES, KNOWN_AGENT_TOOL_NAMES

from .base import Id, Sha256, StrictModel, UtcDatetime


def is_disallowed_human_id(ident: str) -> bool:
    """True if the identifier resembles an agent or system actor."""
    normalized = ident.strip().lower()
    if any(normalized.startswith(prefix) for prefix in DISALLOWED_HUMAN_PREFIXES):
        return True
    if normalized in KNOWN_AGENT_TOOL_NAMES:
        return True
    return False


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
    def _validate_actor(self) -> Actor:
        if self.kind is not ActorKind.AGENT and (self.provider or self.model):
            raise ValueError("provider/model may only be set on agent actors")
        if self.kind is ActorKind.HUMAN and is_disallowed_human_id(self.id):
            raise ValueError(
                f"disallowed human actor id {self.id!r}: resembles an agent or system tool"
            )
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
    INTERVIEW_SESSION = "interview_session"
    OWNER_STATEMENTS = "owner_statements"
    CONCEPT_PROPOSAL = "concept_proposal"


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
    #: Relative to the project folder, always ``source/<sha12>-<name>``: never outside it.
    stored_path: str = Field(pattern=r"^source/[0-9a-f]{12}-[^/\\]+$")
    classification: DataClassification
    imported_at: UtcDatetime
    imported_by: Actor
