"""Plan versions, change requests and revision reports.

A plan option (e.g. "plan-a") is an artifact; each stored version of it is
immutable. Revisions create a new version that names its parent; nothing is
ever overwritten (ADR 0003).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, StrictModel, UtcDatetime
from .model import HouseModel
from .provenance import Actor, ArtifactKind, ArtifactRef, Provenance


class ChangeRequestKind(StrEnum):
    #: "make the kitchen larger"
    MODIFY = "modify"
    #: "generate three alternatives"
    ALTERNATIVES = "alternatives"
    #: "start again from the approved program"
    RESTART_FROM_PROGRAM = "restart_from_program"
    #: "combine the entrance of B with the courtyard of A"
    COMBINE = "combine"
    OTHER = "other"


class ChangeRequest(StrictModel):
    id: Id
    #: The user's words, verbatim.
    text: str = Field(min_length=1)
    kind: ChangeRequestKind
    requested_by: Actor
    requested_at: UtcDatetime
    base_versions: list[ArtifactRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def _bases_are_plans(self) -> ChangeRequest:
        if any(ref.kind is not ArtifactKind.PLAN for ref in self.base_versions):
            raise ValueError("change requests can only be based on plan versions")
        if self.kind is ChangeRequestKind.COMBINE and len(self.base_versions) < 2:
            raise ValueError("a combine request needs at least two base versions")
        return self


class PlanVersion(StrictModel):
    """One immutable version of a plan option. Stored under artifact id = option_id."""

    schema_version: str = SCHEMA_VERSION
    option_id: Id
    label: str
    #: Generation strategy, e.g. "courtyard", "linear", "two_wing", "hand_authored".
    strategy: str | None = None
    parent: ArtifactRef | None = None
    change_request: ChangeRequest | None = None
    provenance: Provenance
    model: HouseModel

    @model_validator(mode="after")
    def _parent_is_plan(self) -> PlanVersion:
        if self.parent is not None and self.parent.kind is not ArtifactKind.PLAN:
            raise ValueError("a plan's parent must be a plan version")
        return self


class AreaChange(StrictModel):
    space_id: Id
    before_m2: float | None
    after_m2: float | None


class MetricChange(StrictModel):
    metric: str
    before: float | int | bool | str | None
    after: float | int | bool | str | None


class RevisionReport(StrictModel):
    """What changed between two plan versions, reported after every revision."""

    schema_version: str = SCHEMA_VERSION
    id: Id
    requested_change: str
    from_version: ArtifactRef
    to_version: ArtifactRef
    geometry_changed: list[str] = Field(default_factory=list)
    rooms_added: list[str] = Field(default_factory=list)
    rooms_removed: list[str] = Field(default_factory=list)
    rooms_changed: list[str] = Field(default_factory=list)
    area_changes: list[AreaChange] = Field(default_factory=list)
    metric_changes: list[MetricChange] = Field(default_factory=list)
    new_violations: list[str] = Field(default_factory=list)
    resolved_violations: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    provenance: Provenance
