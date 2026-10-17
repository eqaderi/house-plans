"""The canonical semantic house model.

This is the single source of truth. 2D plans, schedules, IFC, Blender and
Unreal geometry are all derived from it (ADR 0001). Everything is in the
LOCAL project frame, metres.

Milestone A convention: space boundaries are drawn to wall centerlines, so
adjacent spaces share edges and areas are centerline areas. Net (finish to
finish) areas are a derived quantity for later milestones.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, PositiveFloat, StrictModel
from .geometry import Point2, Polygon2D, segment_length
from .program import Privacy, SpaceFunction
from .provenance import ArtifactRef
from .records import Assumption, Issue


class Level(StrictModel):
    id: Id
    name: str
    #: Finished floor elevation in the local frame, metres.
    elevation_m: float
    floor_to_floor_m: PositiveFloat | None = None


class Space(StrictModel):
    id: Id
    name: str
    function: SpaceFunction
    level_id: Id
    boundary: Polygon2D
    program_item_id: Id | None = None
    zone_id: Id | None = None
    floor_material_id: Id | None = None

    @property
    def area_m2(self) -> float:
        return self.boundary.area_m2


class WallKind(StrEnum):
    EXTERIOR = "exterior"
    INTERIOR = "interior"
    RETAINING = "retaining"
    PARAPET = "parapet"


class Wall(StrictModel):
    """A straight wall defined by its centerline on a level."""

    id: Id
    level_id: Id
    start: Point2
    end: Point2
    thickness_m: PositiveFloat
    height_m: PositiveFloat
    #: Bottom of the wall relative to the level elevation.
    base_offset_m: float = 0.0
    kind: WallKind
    material_id: Id | None = None
    #: Optional per-face finish material overrides (left/right relative to start -> end).
    left_material_id: Id | None = None
    right_material_id: Id | None = None

    @model_validator(mode="after")
    def _non_degenerate(self) -> Wall:
        if segment_length(self.start, self.end) < 0.01:
            raise ValueError(f"{self.id}: wall is shorter than 1 cm")
        return self

    @property
    def length_m(self) -> float:
        return segment_length(self.start, self.end)


class OpeningKind(StrEnum):
    DOOR = "door"
    WINDOW = "window"
    #: Cased opening without a leaf.
    OPENING = "opening"


class Operation(StrEnum):
    NONE = "none"
    SWING_LEFT = "swing_left"
    SWING_RIGHT = "swing_right"
    DOUBLE_SWING = "double_swing"
    SLIDING = "sliding"
    FIXED = "fixed"
    CASEMENT = "casement"
    TILT_TURN = "tilt_turn"


class Opening(StrictModel):
    """A door, window or cased opening hosted by exactly one wall."""

    id: Id
    kind: OpeningKind
    host_wall_id: Id
    #: Distance along the host wall from its start point to the opening's near edge.
    offset_m: float = Field(ge=0)
    width_m: PositiveFloat
    height_m: PositiveFloat
    #: Height of the bottom of the opening above the level floor (0 for doors).
    sill_m: float = Field(default=0.0, ge=0)
    #: The two things on either side: space ids or "exterior". Order is not significant.
    connects: tuple[Id, Id]
    #: Which side of ``connects`` a swinging door/casement opens into, if applicable.
    opens_into: Id | None = None
    operation: Operation = Operation.NONE
    material_id: Id | None = None

    @model_validator(mode="after")
    def _connects_two_things(self) -> Opening:
        a, b = self.connects
        if a == b:
            raise ValueError(f"{self.id}: an opening must connect two different sides")
        if self.opens_into is not None and self.opens_into not in self.connects:
            raise ValueError(
                f"{self.id}: opens_into ({self.opens_into!r}) must be one of {list(self.connects)}"
            )
        return self

    @property
    def is_passable(self) -> bool:
        return self.kind in (OpeningKind.DOOR, OpeningKind.OPENING)


class SlabKind(StrEnum):
    FLOOR = "floor"
    ROOF = "roof"
    TERRACE = "terrace"
    FOUNDATION = "foundation"


class Slab(StrictModel):
    id: Id
    level_id: Id
    kind: SlabKind
    boundary: Polygon2D
    thickness_m: PositiveFloat
    #: Top of slab relative to the level elevation.
    top_offset_m: float = 0.0
    material_id: Id | None = None


class Ceiling(StrictModel):
    id: Id
    space_id: Id
    #: Height above the level's finished floor.
    height_m: PositiveFloat
    material_id: Id | None = None


class StairKind(StrEnum):
    STRAIGHT = "straight"
    L_SHAPED = "l_shaped"
    U_SHAPED = "u_shaped"
    SPIRAL = "spiral"
    OTHER = "other"


class Stair(StrictModel):
    id: Id
    kind: StairKind
    from_level_id: Id
    to_level_id: Id
    #: Plan footprint in the local frame.
    footprint: Polygon2D
    #: Space at the bottom and at the top that the stair connects.
    bottom_space_id: Id
    top_space_id: Id
    width_m: PositiveFloat
    riser_count: int | None = Field(default=None, ge=1)
    riser_height_m: PositiveFloat | None = None
    tread_depth_m: PositiveFloat | None = None

    @model_validator(mode="after")
    def _different_levels(self) -> Stair:
        if self.from_level_id == self.to_level_id:
            raise ValueError(f"{self.id}: a stair must connect two different levels")
        return self


class Zone(StrictModel):
    id: Id
    name: str
    privacy: Privacy
    space_ids: list[Id] = Field(default_factory=list)


class Fixture(StrictModel):
    id: Id
    space_id: Id
    #: e.g. "wc", "basin", "shower", "kitchen_sink", "bed_double".
    fixture_type: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    #: Centre of the fixture footprint.
    position: Point2
    rotation_deg: float = 0.0
    width_m: PositiveFloat
    depth_m: PositiveFloat
    material_id: Id | None = None

    def footprint_polygon(self) -> Polygon2D:
        """Oriented 2D rectangular footprint of the fixture in the local frame."""
        return Polygon2D.rotated_rectangle(
            self.position, self.width_m, self.depth_m, self.rotation_deg
        )


class RelationshipKind(StrEnum):
    CONNECTED = "connected"
    ADJACENT = "adjacent"
    VISUAL = "visual"
    SEPARATED = "separated"


class SpaceRelationship(StrictModel):
    """A declared design intent between two spaces (geometry decides if it holds)."""

    id: Id
    a: Id
    b: Id
    kind: RelationshipKind
    #: Program adjacency requirement this realises, if any.
    requirement_id: Id | None = None


class MaterialCategory(StrEnum):
    WALL = "wall"
    FLOOR = "floor"
    CEILING = "ceiling"
    ROOF = "roof"
    GLAZING = "glazing"
    DOOR = "door"
    FRAME = "frame"
    TERRAIN = "terrain"
    FIXTURE = "fixture"
    OTHER = "other"


class MaterialRef(StrictModel):
    """A reference to a material; render/BIM details live in libraries."""

    id: Id
    name: str
    category: MaterialCategory
    library: str | None = None
    uri: str | None = None
    base_color_hex: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    roughness: float | None = Field(default=None, ge=0.0, le=1.0)
    metallic: float | None = Field(default=None, ge=0.0, le=1.0)
    texture_scale_m: PositiveFloat | None = None


class HouseModel(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    name: str
    units: Literal["m"] = "m"
    #: Id of the site's local coordinate system this model is drawn in.
    coordinate_system_id: Id
    site_ref: ArtifactRef | None = None
    program_ref: ArtifactRef | None = None
    levels: list[Level] = Field(min_length=1)
    spaces: list[Space] = Field(default_factory=list)
    walls: list[Wall] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    slabs: list[Slab] = Field(default_factory=list)
    ceilings: list[Ceiling] = Field(default_factory=list)
    stairs: list[Stair] = Field(default_factory=list)
    zones: list[Zone] = Field(default_factory=list)
    fixtures: list[Fixture] = Field(default_factory=list)
    relationships: list[SpaceRelationship] = Field(default_factory=list)
    materials: list[MaterialRef] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)

    def space(self, space_id: str) -> Space:
        return next(s for s in self.spaces if s.id == space_id)

    def wall(self, wall_id: str) -> Wall:
        return next(w for w in self.walls if w.id == wall_id)

    def level(self, level_id: str) -> Level:
        return next(lv for lv in self.levels if lv.id == level_id)

    def all_ids(self) -> list[str]:
        """Every entity id in the model, in a stable order (duplicates kept)."""
        groups = (
            self.levels,
            self.spaces,
            self.walls,
            self.openings,
            self.slabs,
            self.ceilings,
            self.stairs,
            self.zones,
            self.fixtures,
            self.relationships,
            self.materials,
            self.assumptions,
            self.issues,
        )
        return [item.id for group in groups for item in group]
