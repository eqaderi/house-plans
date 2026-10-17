"""Records of derived builds (Blender scene, Unreal transfer).

Milestones F and G produce these. Defined now so the model approval gate has
a concrete artifact to approve and so a build is always traceable to the
approved plan version it was generated from.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, Sha256, StrictModel
from .provenance import ArtifactKind, ArtifactRef, Provenance


class BuildTarget(StrEnum):
    BLENDER = "blender"
    UNREAL = "unreal"
    IFC = "ifc"


class BuildOutput(StrictModel):
    #: Path relative to the project root.
    path: str
    sha256: Sha256
    role: str


class BuildRecord(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    target: BuildTarget
    input_plan: ArtifactRef
    tool: str
    tool_version: str | None = None
    script: str | None = None
    outputs: list[BuildOutput] = Field(default_factory=list)
    provenance: Provenance

    @model_validator(mode="after")
    def _from_a_plan(self) -> BuildRecord:
        if self.input_plan.kind is not ArtifactKind.PLAN:
            raise ValueError("builds are generated from a plan version")
        return self
