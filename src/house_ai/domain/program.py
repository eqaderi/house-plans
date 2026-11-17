"""The space program (space_program.yaml): what spaces the house needs."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, model_serializer, model_validator

from .base import EXTERIOR, Id, StrictModel
from .brief import Money, Priority
from .provenance import ArtifactRef, Provenance
from .usability import UsabilityRequirements


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


#: Level words a Space may ask for, relative to the entry Level: on it ("entry", "ground"),
#: off it ("not_entry"), above ("upper"), below ("lower"), or anywhere ("any").
LEVEL_PREFERENCES: frozenset[str] = frozenset(
    {"entry", "ground", "not_entry", "upper", "lower", "any"}
)


class SpaceRequirement(StrictModel):
    """A kind of space the Owner needs, with a quantity and a size (GLOSSARY.md)."""

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
    #: Must be reachable and usable step-free (e.g. by a wheelchair user).
    accessible: bool = False
    #: Brief facts this requirement derives from.
    source_fact_ids: list[Id] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _area_order(self) -> SpaceRequirement:
        bounds = (self.min_area_m2, self.target_area_m2, self.max_area_m2)
        values = [v for v in bounds if v is not None]
        if values != sorted(values):
            raise ValueError(f"{self.id}: need min_area <= target_area <= max_area")
        return self


class SpaceRelationshipKind(StrEnum):
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


class SpaceRelationship(StrictModel):
    """How two spaces should relate (GLOSSARY.md)."""

    id: Id
    a: Id
    #: Another space requirement id, or "exterior".
    b: Id
    kind: SpaceRelationshipKind
    strength: Strength
    #: Soft requirements only; relative importance > 0.
    weight: float | None = Field(default=None, gt=0)
    rationale: str | None = None
    source_fact_ids: list[Id] = Field(default_factory=list)

    @model_validator(mode="after")
    def _weight_matches_strength(self) -> SpaceRelationship:
        if self.a == self.b:
            raise ValueError(f"{self.id}: relationship from a space requirement to itself")
        if self.strength is Strength.SOFT and self.weight is None:
            raise ValueError(f"{self.id}: soft requirements need a weight")
        if self.strength is Strength.HARD and self.weight is not None:
            raise ValueError(f"{self.id}: hard requirements must not carry a weight")
        return self


class ProgramZone(StrictModel):
    id: Id
    name: str
    privacy: Privacy


#: Schema 0.2.0 renamed saved fields to GLOSSARY.md terms (ADR 0025).
SPACE_PROGRAM_SCHEMA_VERSION = "0.2.0"
#: Schema versions whose records are written with the old field names.
OLD_NAMES_SCHEMA_VERSIONS = frozenset({"0.1.0"})
#: Old names whose meaning changed: read only from records of an old schema version.
#: ``levels`` held the floors wanted, which the Owner answers as storeys (S11-02).
VERSIONED_OLD_NAMES = frozenset({"levels"})
#: ADR 0025: (parent field or None, new name) -> name saved before schema 0.2.0.
RENAMED_FIELDS: dict[tuple[str | None, str], str] = {
    (None, "space_requirements"): "items",
    (None, "space_relationships"): "adjacencies",
    (None, "storeys"): "levels",
    (None, "site_approved"): "site_verified",
    ("usability", "double_bed_space_requirement_ids"): "double_bed_program_item_ids",
    ("usability", "single_bed_space_requirement_ids"): "single_bed_program_item_ids",
}


def _rename_keys(data: dict[str, Any], names: dict[str, str]) -> dict[str, Any]:
    """Copy of ``data`` with keys renamed by ``names``, in the same order."""
    clash = [(src, dst) for src, dst in names.items() if src in data and dst in data]
    if clash:
        raise ValueError(f"give {clash[0][0]!r} or {clash[0][1]!r}, not both")
    return {names.get(k, k): v for k, v in data.items()}


def _rename(data: dict[str, Any], to_old: bool) -> dict[str, Any]:
    """Copy of a space program document with renamed fields under their new or old names."""
    by_parent: dict[str | None, dict[str, str]] = {}
    for (parent, new), old in RENAMED_FIELDS.items():
        by_parent.setdefault(parent, {})[new if to_old else old] = old if to_old else new
    data = _rename_keys(data, by_parent.pop(None))
    for parent, names in by_parent.items():
        if isinstance(data.get(parent), dict):
            data[parent] = _rename_keys(data[parent], names)
    return data


class SpaceProgram(StrictModel):
    """The space requirements and relationships the program gate approves.

    Old field names (``items``, ``adjacencies``, ``levels``, ``site_verified``)
    are accepted on input; ``levels`` changed meaning, so only on schema 0.1.0.
    A record of schema 0.1.0 is written back with them, so programs saved before
    ADR 0025 keep their content hash.
    """

    schema_version: str = SPACE_PROGRAM_SCHEMA_VERSION
    id: Id
    project_id: Id
    brief_ref: ArtifactRef | None = None
    space_requirements: list[SpaceRequirement] = Field(min_length=1)
    space_relationships: list[SpaceRelationship] = Field(default_factory=list)
    zones: list[ProgramZone] = Field(default_factory=list)
    target_gross_area_m2: float | None = Field(default=None, gt=0)
    #: Circulation and walls as a fraction of net program area, if assumed.
    circulation_factor: float | None = Field(default=None, ge=0, lt=1)
    #: Number of storeys the Owner wants (how tall the house is); None means UNKNOWN.
    #: The number of levels is not stored here: the plan derives it from the slope.
    storeys: int | None = Field(default=None, ge=1, le=10)
    #: None means UNKNOWN.
    budget: Money | None = None
    #: Site version the program was checked against, and whether it was approved.
    site_ref: ArtifactRef | None = None
    site_approved: bool = False
    usability: UsabilityRequirements = Field(default_factory=UsabilityRequirements)
    provenance: Provenance

    @model_validator(mode="before")
    @classmethod
    def _accept_old_names(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        version = data.get("schema_version", SPACE_PROGRAM_SCHEMA_VERSION)
        if version not in OLD_NAMES_SCHEMA_VERSIONS:
            for name in sorted(VERSIONED_OLD_NAMES & data.keys()):
                new = next(n for (_, n), o in RENAMED_FIELDS.items() if o == name)
                raise ValueError(f"{name!r} is a schema 0.1.0 name; schema {version} uses {new!r}")
        return _rename(data, to_old=False)

    @model_serializer(mode="wrap")
    def _legacy_hash_compatible(self, handler):
        data = handler(self)
        if self.usability == UsabilityRequirements():
            data.pop("usability", None)
        if self.schema_version in OLD_NAMES_SCHEMA_VERSIONS:
            data = _rename(data, to_old=True)
        return data

    @model_validator(mode="after")
    def _references_resolve(self) -> SpaceProgram:
        ids = (
            [i.id for i in self.space_requirements]
            + [z.id for z in self.zones]
            + [a.id for a in self.space_relationships]
            + [v.id for v in self.usability.vehicles or []]
        )
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate ids in program: {sorted(dupes)}")
        item_ids = {i.id for i in self.space_requirements}
        double = set(self.usability.double_bed_space_requirement_ids)
        single = set(self.usability.single_bed_space_requirement_ids)
        if not (double | single) <= item_ids:
            raise ValueError("bed usability requirements reference unknown space requirements")
        if double & single:
            raise ValueError("bed variants must not conflict for the same space requirement")
        zone_ids = {z.id for z in self.zones}
        for item in self.space_requirements:
            if item.zone_id and item.zone_id not in zone_ids:
                raise ValueError(f"{item.id}: unknown zone {item.zone_id}")
        for adj in self.space_relationships:
            for end in (adj.a, adj.b):
                if end != EXTERIOR and end not in item_ids:
                    raise ValueError(f"{adj.id}: unknown space requirement {end}")
        return self

    @property
    def net_target_area_m2(self) -> float | None:
        """Sum of target areas, or None if any requirement's target is unknown."""
        total = 0.0
        for item in self.space_requirements:
            if item.target_area_m2 is None:
                return None
            total += item.target_area_m2 * item.quantity
        return total
