"""Records of derived builds (Blender scene, Unreal transfer) and scene manifest.

Milestones F and G produce these. Defined now so the model approval gate has
a concrete artifact to approve, a build is always traceable to the approved
plan version it was generated from, and the Blender -> FBX + scene_manifest.json
-> Unreal contract is fixed in the canonical domain.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, PositiveFloat, Sha256, StrictModel
from .geometry import Point3
from .provenance import ArtifactKind, ArtifactRef, Provenance
from .units import LengthUnit


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


class Transform3D(StrictModel):
    """3D transform in the manifest's declared units and coordinate system."""

    translation: Point3 = (0.0, 0.0, 0.0)
    rotation_euler_deg: Point3 = (0.0, 0.0, 0.0)
    scale: Point3 = (1.0, 1.0, 1.0)


class InteractionKind(StrEnum):
    NONE = "none"
    DOOR = "door"
    WINDOW = "window"
    DRAWER = "drawer"
    SWITCH = "switch"
    APPLIANCE = "appliance"


class InteractionMetadata(StrictModel):
    kind: InteractionKind = InteractionKind.NONE
    hinge_offset: Point3 | None = None
    max_angle_deg: float | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class SceneMaterial(StrictModel):
    id: Id
    name: str
    base_color_hex: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    roughness: float | None = Field(default=None, ge=0.0, le=1.0)
    metallic: float | None = Field(default=None, ge=0.0, le=1.0)
    texture_scale_m: PositiveFloat | None = None
    source_textures: dict[str, str] = Field(default_factory=dict)


class SceneObject(StrictModel):
    id: Id
    #: Semantic entity type, e.g. "wall", "slab", "door", "window", "space", "terrain".
    semantic_type: str = Field(min_length=1)
    #: Canonical domain entity id this 3D object derives from, if applicable.
    domain_id: Id | None = None
    parent_id: Id | None = None
    mesh_path: str | None = None
    instance_of: Id | None = None
    transform: Transform3D = Field(default_factory=Transform3D)
    material_ids: list[Id] = Field(default_factory=list)
    collision_enabled: bool = True
    interaction: InteractionMetadata = Field(default_factory=InteractionMetadata)


class SceneLight(StrictModel):
    id: Id
    kind: str = Field(min_length=1)
    transform: Transform3D = Field(default_factory=Transform3D)
    intensity: float = Field(ge=0.0)
    color_hex: str = Field(default="#FFFFFF", pattern=r"^#[0-9a-fA-F]{6}$")


class SceneCamera(StrictModel):
    id: Id
    label: str
    transform: Transform3D = Field(default_factory=Transform3D)
    fov_deg: PositiveFloat = 60.0
    orthographic: bool = False


class SceneManifest(StrictModel):
    """scene_manifest.json transferring an approved Blender build to Unreal Engine."""

    schema_version: str = SCHEMA_VERSION
    id: Id
    plan_ref: ArtifactRef
    blender_build_ref: ArtifactRef
    units: LengthUnit = LengthUnit.METRE
    coordinate_system_id: Id
    epsg: int | None = None
    origin_grid_m: Point3 | None = None
    player_start: Transform3D | None = None
    materials: list[SceneMaterial] = Field(default_factory=list)
    objects: list[SceneObject] = Field(default_factory=list)
    lights: list[SceneLight] = Field(default_factory=list)
    cameras: list[SceneCamera] = Field(default_factory=list)
    provenance: Provenance

    @model_validator(mode="after")
    def _references_resolve(self) -> SceneManifest:
        if self.plan_ref.kind is not ArtifactKind.PLAN:
            raise ValueError("plan_ref must point at a plan artifact")
        if self.blender_build_ref.kind is not ArtifactKind.BUILD_RECORD:
            raise ValueError("blender_build_ref must point at a build_record artifact")
        obj_ids = [o.id for o in self.objects]
        if len(set(obj_ids)) != len(obj_ids):
            raise ValueError("duplicate scene object ids")
        known_objs = set(obj_ids)
        known_mats = {m.id for m in self.materials}
        for obj in self.objects:
            if obj.parent_id is not None and obj.parent_id not in known_objs:
                raise ValueError(f"{obj.id}: unknown parent_id {obj.parent_id!r}")
            if obj.instance_of is not None and obj.instance_of not in known_objs:
                raise ValueError(f"{obj.id}: unknown instance_of {obj.instance_of!r}")
            for mat_id in obj.material_ids:
                if mat_id not in known_mats:
                    raise ValueError(f"{obj.id}: unknown material_id {mat_id!r}")
        return self

