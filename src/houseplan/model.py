"""The design spec: the single source of truth for a house.

Every length is an integer number of millimetres. Coordinates are plan
coordinates in mm, x to the east and y to the north, relative to the project
origin. Heights are relative to the project datum (±0.00 = finished floor of
the entrance level) unless a field says otherwise.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Mm = int
Point = tuple[Mm, Mm]
MAX_COORD = 1_000_000  # mm; nothing in a house plan is a kilometre from its origin


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Datum(Strict):
    """Ties ±0.00 to the survey. Leave survey_z_mm unset until it is measured."""

    label: str = "±0.00"
    survey_z_mm: int | None = None
    source: str | None = None


class Project(Strict):
    name: str
    jurisdiction: str = Field(description="ISO 3166 code, e.g. IR")
    municipality: str | None = None
    ruleset: str | None = Field(default=None, description="File stem in rules/, e.g. iran")
    datum: Datum = Datum()
    allowed_wall_thicknesses: list[Mm] = Field(
        description="Every wall must use one of these thicknesses (finished, mm)."
    )
    north_angle_deg: float = Field(0.0, description="Angle of true north from +y, clockwise.")
    stage: Literal["sketch", "final"] = Field(
        "sketch",
        description="sketch: options shown to the owner, sheets only. final: the agreed plan, full documentation.",
    )


class Level(Strict):
    id: str
    name: str
    ffl: Mm = Field(description="Finished floor level relative to the datum.")
    floor_to_floor: Mm = Field(gt=0, description="This FFL to the next FFL above.")
    slab: Mm = Field(gt=0, description="Structural slab plus floor build-up above this level's ceiling.")

    @property
    def clear_height(self) -> Mm:
        return self.floor_to_floor - self.slab


class WallKind(str, Enum):
    exterior = "exterior"
    interior = "interior"
    party = "party"


class Wall(Strict):
    id: str
    level: str
    start: Point
    end: Point
    thickness: Mm = Field(gt=0)
    kind: WallKind
    loadbearing: bool = False
    justify: Literal["center", "left", "right"] = Field(
        "center", description="Where the start→end line sits in the wall; left/right seen walking from start to end."
    )


class OpeningKind(str, Enum):
    door = "door"
    window = "window"
    opening = "opening"


class Opening(Strict):
    """An opening in a host wall. offset is measured along the wall line from
    `start` to the near jamb; the jambs are square to the wall."""

    id: str
    wall: str
    kind: OpeningKind
    offset: Mm = Field(ge=0)
    width: Mm = Field(gt=0, description="Structural (rough) opening width.")
    height: Mm = Field(gt=0, description="Structural opening height above the sill.")
    sill: Mm = Field(0, ge=0, description="Sill height above FFL; 0 for doors.")
    hinge: Literal["start", "end"] | None = Field(None, description="Doors: which jamb carries the hinges.")
    swing: Literal["left", "right"] | None = Field(None, description="Doors: side of the wall line the leaf opens into.")
    leaf: Mm | None = Field(None, description="Doors: clear leaf width if different from width.")


class RoomUse(str, Enum):
    living = "living"  # family living, نشیمن
    reception = "reception"  # guest reception, پذیرایی
    dining = "dining"
    entry = "entry"  # entrance, ورودی / کفش‌کن / هشتی
    bedroom = "bedroom"
    kitchen = "kitchen"
    bath = "bath"
    wc = "wc"
    corridor = "corridor"
    hall = "hall"
    stair = "stair"
    storage = "storage"
    pantry = "pantry"  # انباری
    laundry = "laundry"
    garage = "garage"
    plant = "plant"
    balcony = "balcony"
    terrace = "terrace"


HABITABLE = {RoomUse.living, RoomUse.reception, RoomUse.dining, RoomUse.bedroom, RoomUse.kitchen}
PRIVATE_VIEW = {RoomUse.bedroom, RoomUse.bath, RoomUse.wc}
SOCIAL = {RoomUse.living, RoomUse.reception, RoomUse.dining, RoomUse.kitchen}
NOISY = {RoomUse.kitchen, RoomUse.living, RoomUse.reception, RoomUse.laundry, RoomUse.plant, RoomUse.garage}
WET = {RoomUse.bath, RoomUse.wc, RoomUse.kitchen, RoomUse.laundry}


class Room(Strict):
    """A room is the free space enclosed by walls that contains `seed`.
    Its outline and area are computed from the walls, never typed in."""

    id: str
    level: str
    name: str
    name_fa: str | None = None
    use: RoomUse
    seed: Point
    entrance: bool = Field(False, description="True if the house is entered from outside into this room.")
    target_area: float | None = Field(None, gt=0, description="Net area the brief asks for, m².")
    via: str | None = Field(None, description="Room this one is reached through on purpose (en-suite bath, walk-in closet).")


class Requirement(Strict):
    use: RoomUse
    count: int = Field(ge=1)


class Program(Strict):
    """What the brief asks for, as checkable requirements."""

    required: list[Requirement] = []
    connect: list[tuple[str, str]] = Field([], description="Pairs of room ids that must share a door or opening.")
    private_uses: list[RoomUse] = Field(
        [RoomUse.bedroom, RoomUse.bath, RoomUse.wc],
        description="Rooms no route may pass through, unless a room names it in `via`.",
    )
    area_tolerance: float = Field(0.10, ge=0, description="Allowed relative deviation from target_area.")


class Stair(Strict):
    """A straight run. origin is the bottom of the first riser on the run's
    centre line; direction is the walking direction going up."""

    id: str
    level: str = Field(description="Level the stair starts from.")
    to_level: str
    origin: Point
    direction: Literal["+x", "-x", "+y", "-y"]
    width: Mm = Field(gt=0, description="Clear width between finished walls or handrails.")
    risers: int = Field(gt=1)
    going: Mm = Field(gt=0, description="Horizontal tread depth, nosing to nosing.")


class Design(Strict):
    schema_version: Literal[1] = 1
    project: Project
    levels: list[Level]
    walls: list[Wall]
    openings: list[Opening] = []
    rooms: list[Room] = []
    stairs: list[Stair] = []
    program: Program = Program()

    @model_validator(mode="after")
    def _references(self) -> Design:
        ids: list[str] = [x.id for group in (self.levels, self.walls, self.openings, self.rooms, self.stairs) for x in group]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        points = [p for w in self.walls for p in (w.start, w.end)] + [r.seed for r in self.rooms] + [s.origin for s in self.stairs]
        far = [p for p in points if max(abs(p[0]), abs(p[1])) > MAX_COORD]
        if far:
            raise ValueError(f"coordinates beyond {MAX_COORD // 1_000_000} km from the origin, e.g. {far[0]}: survey coordinates belong in project.datum, not in the plan")
        if dupes:
            raise ValueError(f"duplicate ids: {dupes}")
        levels = {l.id for l in self.levels}
        walls = {w.id for w in self.walls}
        for item in (*self.walls, *self.rooms, *self.stairs):
            if item.level not in levels:
                raise ValueError(f"{item.id}: unknown level {item.level!r}")
        for s in self.stairs:
            if s.to_level not in levels:
                raise ValueError(f"{s.id}: unknown to_level {s.to_level!r}")
        rooms = {r.id for r in self.rooms}
        for r in self.rooms:
            if r.via is not None and r.via not in rooms:
                raise ValueError(f"{r.id}: via names unknown room {r.via!r}")
        for a, b in self.program.connect:
            if a not in rooms or b not in rooms:
                raise ValueError(f"program.connect: unknown room in {a!r}-{b!r}")
        for o in self.openings:
            if o.wall not in walls:
                raise ValueError(f"{o.id}: unknown wall {o.wall!r}")
            if o.kind is OpeningKind.door and (o.hinge is None or o.swing is None):
                raise ValueError(f"{o.id}: a door needs hinge and swing")
        return self

    def level(self, level_id: str) -> Level:
        return next(l for l in self.levels if l.id == level_id)

    def wall(self, wall_id: str) -> Wall:
        return next(w for w in self.walls if w.id == wall_id)

    def level_above(self, level_id: str) -> Level | None:
        here = self.level(level_id)
        above = [l for l in self.levels if l.ffl > here.ffl]
        return min(above, key=lambda l: l.ffl) if above else None


def load(path: str) -> Design:
    with open(path, encoding="utf-8") as fh:
        return Design.model_validate(yaml.safe_load(fh))
