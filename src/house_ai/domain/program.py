"""The space program (space_program.yaml): what spaces the house needs."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .base import EXTERIOR, SCHEMA_VERSION, Id, StrictModel
from .brief import Priority
from .provenance import ArtifactRef, Provenance


class SpaceFunction(StrEnum):
    ENTRY = "entry"
    HALL = "hall"
    CORRIDOR = "corridor"
    LIVING = "living"
    FAMILY = "family"
    RECEPTION = "reception"
    DINING = "dining"
    KITCHEN = "kitchen"
    PANTRY = "pantry"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    WC = "wc"
    ABLUTION = "ablution"
    PRAYER = "prayer"
    STUDY = "study"
    GYM = "gym"
    PLAY = "play"
    STORAGE = "storage"
    LAUNDRY = "laundry"
    MECHANICAL = "mechanical"
    GARAGE = "garage"
    STAIR = "stair"
    LIFT = "lift"
    GUEST_SUITE = "guest_suite"
    TERRACE = "terrace"
    BALCONY = "balcony"
    OTHER = "other"


class Privacy(StrEnum):
    PUBLIC = "public"
    SEMI_PRIVATE = "semi_private"
    PRIVATE = "private"
    SERVICE = "service"


class DaylightNeed(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    NOT_NEEDED = "not_needed"


class ProgramItem(StrictModel):
    id: Id
    name: str
    function: SpaceFunction
    quantity: int = Field(default=1, ge=1)
    min_area_m2: float | None = Field(default=None, gt=0)
    target_area_m2: float | None = Field(default=None, gt=0)
    max_area_m2: float | None = Field(default=None, gt=0)
    min_width_m: float | None = Field(default=None, gt=0)
    privacy: Privacy
    zone_id: Id | None = None
    #: e.g. "ground", "upper", "any". Free text until levels exist.
    level_preference: str | None = None
    priority: Priority = Priority.MUST
    daylight: DaylightNeed = DaylightNeed.PREFERRED
    #: Brief facts this item derives from.
    source_fact_ids: list[str] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _area_order(self) -> ProgramItem:
        bounds = (self.min_area_m2, self.target_area_m2, self.max_area_m2)
        values = [v for v in bounds if v is not None]
        if values != sorted(values):
            raise ValueError(f"{self.id}: need min_area <= target_area <= max_area")
        return self


class AdjacencyKind(StrEnum):
    #: Direct door or opening between the two.
    CONNECTED = "connected"
    #: Share a wall.
    ADJACENT = "adjacent"
    #: Short walk, not necessarily touching.
    NEAR = "near"
    VISUAL = "visual"
    #: Must not be adjacent or directly connected.
    SEPARATED = "separated"
    #: Must be acoustically separated (not sharing a wall).
    ACOUSTIC_SEPARATION = "acoustic_separation"


class Strength(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class AdjacencyRequirement(StrictModel):
    id: Id
    a: Id
    #: Another program item id, or "exterior".
    b: Id
    kind: AdjacencyKind
    strength: Strength
    #: Soft requirements only; relative importance > 0.
    weight: float | None = Field(default=None, gt=0)
    rationale: str | None = None
    source_fact_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _weight_matches_strength(self) -> AdjacencyRequirement:
        if self.a == self.b:
            raise ValueError(f"{self.id}: adjacency from an item to itself")
        if self.strength is Strength.SOFT and self.weight is None:
            raise ValueError(f"{self.id}: soft requirements need a weight")
        if self.strength is Strength.HARD and self.weight is not None:
            raise ValueError(f"{self.id}: hard requirements must not carry a weight")
        return self


class ProgramZone(StrictModel):
    id: Id
    name: str
    privacy: Privacy


class SpaceProgram(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    project_id: Id
    brief_ref: ArtifactRef | None = None
    items: list[ProgramItem] = Field(min_length=1)
    adjacencies: list[AdjacencyRequirement] = Field(default_factory=list)
    zones: list[ProgramZone] = Field(default_factory=list)
    target_gross_area_m2: float | None = Field(default=None, gt=0)
    #: Circulation and walls as a fraction of net program area, if assumed.
    circulation_factor: float | None = Field(default=None, ge=0, lt=1)
    provenance: Provenance

    @model_validator(mode="after")
    def _references_resolve(self) -> SpaceProgram:
        ids = (
            [i.id for i in self.items]
            + [z.id for z in self.zones]
            + [a.id for a in self.adjacencies]
        )
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate ids in program: {sorted(dupes)}")
        item_ids = {i.id for i in self.items}
        zone_ids = {z.id for z in self.zones}
        for item in self.items:
            if item.zone_id and item.zone_id not in zone_ids:
                raise ValueError(f"{item.id}: unknown zone {item.zone_id}")
        for adj in self.adjacencies:
            for end in (adj.a, adj.b):
                if end != EXTERIOR and end not in item_ids:
                    raise ValueError(f"{adj.id}: unknown program item {end}")
        return self

    @property
    def net_target_area_m2(self) -> float | None:
        """Sum of target areas, or None if any item's target is unknown."""
        total = 0.0
        for item in self.items:
            if item.target_area_m2 is None:
                return None
            total += item.target_area_m2 * item.quantity
        return total
