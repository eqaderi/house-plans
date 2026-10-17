"""Agent role definitions (agents/roles.yaml)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import Id, StrictModel
from .provenance import ArtifactKind


class AgentRole(StrictModel):
    id: Id
    name: str
    purpose: str
    #: When the orchestrator should invoke this role; keep compositions small.
    invoke_when: str
    #: Artifact kinds this role may write. Every write must be schema-valid.
    may_write: list[ArtifactKind] = Field(default_factory=list)
    #: Whether the role may request non-gate workflow transitions.
    may_transition: bool = False
    #: No agent can approve a gate. Fixed to False by schema.
    may_approve: Literal[False] = False
    #: Milestone in which the role becomes operational.
    milestone: str


class AgentRoster(StrictModel):
    roles: list[AgentRole]

    @model_validator(mode="after")
    def _unique(self) -> AgentRoster:
        ids = [r.id for r in self.roles]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate role ids")
        return self
