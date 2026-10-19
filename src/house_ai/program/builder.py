"""Design brief -> space program, assumptions and open questions (Milestone C).

Deterministic. Every program item and adjacency cites the brief facts it comes
from; a size the owner did not give comes from :data:`TYPICAL` and is listed
as an assumption (typical sizes for a first layout, not building-code minima:
no jurisdiction is loaded). The program never changes what the owner asked
for; if the request does not fit, validation says so and offers options.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from house_ai.domain.base import EXTERIOR
from house_ai.domain.brief import BriefFact, DesignBrief, Priority
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.interview import SiteContext
from house_ai.domain.program import (
    AdjacencyKind,
    AdjacencyRequirement,
    DaylightNeed,
    Privacy,
    ProgramItem,
    ProgramZone,
    SpaceFunction,
    SpaceProgram,
    Strength,
)
from house_ai.domain.provenance import Actor, ActorKind, ArtifactRef, Provenance
from house_ai.domain.records import (
    Assumption,
    AssumptionsFile,
    OpenQuestion,
    OpenQuestionsFile,
)
from house_ai.domain.usability import UsabilityRequirements, VehicleEnvelope

TOOL_ACTOR = Actor(kind=ActorKind.SYSTEM, id="house-ai-program")

#: Typical sizes (min m², target m², min width m) for a first layout. Not code minima.
TYPICAL: dict[str, tuple[float, float, float | None]] = {
    "entry": (4.0, 6.0, 1.5),
    "living": (16.0, 25.0, 3.6),
    "kitchen": (8.0, 12.0, 2.4),
    "kitchen_dining": (14.0, 20.0, 3.0),
    "dining": (10.0, 14.0, 3.0),
    "reception": (20.0, 30.0, 4.0),
    "main_bedroom": (12.0, 15.0, 3.0),
    "bedroom": (9.0, 11.0, 2.7),
    "ensuite": (3.5, 5.0, 1.6),
    "bathroom": (4.0, 6.0, 1.8),
    "accessible_bathroom": (5.5, 7.0, 2.2),
    "study": (6.0, 9.0, 2.4),
    "guest_suite": (16.0, 22.0, 3.0),
    "garage_per_car": (15.0, 18.0, 3.0),
    "storage": (3.0, 5.0, None),
    "laundry": (4.0, 6.0, 1.8),
    "mechanical": (3.0, 4.0, None),
    "pantry": (2.0, 4.0, None),
    "prayer": (6.0, 9.0, 2.4),
    "stair": (8.0, 10.0, 2.2),
    "lift": (3.0, 4.0, 1.5),
    "terrace": (10.0, 16.0, 2.5),
    "roof_terrace": (12.0, 20.0, 2.5),
    "balcony": (4.0, 6.0, 1.5),
}
#: Circulation, walls and structure as a share of the net room area (an assumption).
CIRCULATION = 0.20
#: Outdoor wishes that are not rooms; carried as outdoor items with no area.
OUTDOOR_WISHES = {
    "garden": "Garden",
    "pool": "Pool",
    "play_area": "Children's play area",
    "vegetable_garden": "Vegetable garden",
}
OUTDOOR_FUNCTIONS = {SpaceFunction.TERRACE, SpaceFunction.BALCONY}
OUTDOOR_LEVELS = {"outdoor", "roof"}

#: Owner room words (see interview.parsing.ROOMS) -> item-id prefixes.
ROOM_ITEMS: dict[str, tuple[str, ...]] = {
    "kitchen": ("pi-kitchen",),
    "living": ("pi-living",),
    "dining": ("pi-dining", "pi-kitchen"),
    "main_bedroom": ("pi-bed-main",),
    "children_bedrooms": ("pi-bed-child",),
    "bedrooms": ("pi-bed",),
    "bathroom": ("pi-bath",),
    "office": ("pi-study",),
    "guest": ("pi-guest", "pi-bed-guest"),
    "garage": ("pi-garage",),
    "laundry": ("pi-laundry",),
    "entry": ("pi-entry",),
    "terrace": ("pi-terrace",),
    "elder_room": ("pi-bed-elder",),
}


def is_indoor(item: ProgramItem) -> bool:
    return item.function not in OUTDOOR_FUNCTIONS and item.level_preference not in OUTDOOR_LEVELS


class Facts:
    """Slot values from the brief's ``f-<slot>`` facts, any status."""

    def __init__(self, brief: DesignBrief) -> None:
        self.by_key: dict[str, BriefFact] = {
            f.key: f for f in brief.facts if f.id == f"f-{f.key}"
        }

    def get(self, key: str, default: Any = None) -> Any:
        f = self.by_key.get(key)
        return default if f is None or f.value is None else f.value

    def ids(self, *keys: str) -> list[str]:
        return [self.by_key[k].id for k in keys if k in self.by_key]

    def priority(self, key: str, default: Priority) -> Priority:
        f = self.by_key.get(key)
        return f.priority if f is not None and f.priority is not None else default

    def status(self, key: str) -> Epistemic | None:
        f = self.by_key.get(key)
        return f.status if f else None


@dataclass
class ProgramResult:
    program: SpaceProgram
    assumptions: AssumptionsFile
    open_questions: OpenQuestionsFile
    #: Item ids whose size is a typical value, not the owner's.
    typical_sized: list[str] = field(default_factory=list)


class _Builder:
    def __init__(self, brief: DesignBrief, site: SiteContext | None) -> None:
        self.f = Facts(brief)
        self.site = site
        self.items: list[ProgramItem] = []
        self.adj: list[AdjacencyRequirement] = []
        self.typical: list[str] = []
        floors = self.f.get("floors")
        self.floors = floors if isinstance(floors, int) and floors > 0 else None
        self.step_free = self.f.get("accessibility") in ("step_free", "wheelchair") or (
            self.f.get("elder_step_free") is True
        )

    # ------------------------------------------------------------ helpers

    def level(self, kind: str) -> str:
        if self.floors == 1:
            return "ground"
        if self.floors is None:
            return "any"
        return kind

    def add(
        self,
        item_id: str,
        name: str,
        function: SpaceFunction,
        size: str | None,
        privacy: Privacy,
        zone: str,
        *,
        level: str = "any",
        priority: Priority = Priority.MUST,
        daylight: DaylightNeed = DaylightNeed.PREFERRED,
        facts: list[str] | None = None,
        accessible: bool = False,
        scale: float = 1.0,
        notes: str | None = None,
    ) -> ProgramItem:
        lo = target = width = None
        if size is not None:
            lo, target, width = TYPICAL[size]
            lo, target = lo * scale, target * scale
            self.typical.append(item_id)
        item = ProgramItem(
            id=item_id, name=name, function=function, min_area_m2=lo, target_area_m2=target,
            min_width_m=width, privacy=privacy, zone_id=zone, level_preference=level,
            priority=priority, daylight=daylight, source_fact_ids=facts or [],
            accessible=accessible, notes=notes,
        )  # fmt: skip
        self.items.append(item)
        return item

    def link(
        self,
        a: str,
        b: str,
        kind: AdjacencyKind,
        strength: Strength,
        rationale: str,
        facts: list[str] | None = None,
        weight: float = 2.0,
    ) -> None:
        ids = {i.id for i in self.items} | {EXTERIOR}
        if a not in ids or b not in ids or a == b:
            return
        self.adj.append(
            AdjacencyRequirement(
                id=f"adj-{len(self.adj) + 1:02d}-{a.removeprefix('pi-')}-{b.removeprefix('pi-')}"[
                    :64
                ].rstrip("-_"),
                a=a, b=b, kind=kind, strength=strength,
                weight=weight if strength is Strength.SOFT else None,
                rationale=rationale, source_fact_ids=facts or [],
            )
        )  # fmt: skip

    def ids_for(self, room: str) -> list[str]:
        prefixes = ROOM_ITEMS.get(room, ())
        return [
            i.id for i in self.items if any(i.id == p or i.id.startswith(p + "-") for p in prefixes)
        ]

    # ------------------------------------------------------------- rooms

    def build(self) -> None:
        f = self.f
        S, P, D = SpaceFunction, Privacy, DaylightNeed
        entry_level = "entry"
        self.add("pi-entry", "Entrance hall", S.ENTRY, "entry", P.SEMI_PRIVATE, "z-circulation",
                 level=self.level(entry_level), facts=f.ids("entry_at_road"),
                 accessible=self.step_free)  # fmt: skip
        gathering = f.get("gathering_space") is True
        self.add("pi-living", "Living room", S.LIVING, "living", P.PUBLIC, "z-day",
                 level=self.level(entry_level), daylight=D.REQUIRED,
                 facts=f.ids("open_plan", "gathering_space", "privacy"),
                 scale=1.3 if gathering else 1.0, accessible=self.step_free,
                 notes="larger for family gatherings" if gathering else None)  # fmt: skip
        open_plan = f.get("open_plan")
        layout = f.get("kitchen_layout") or ("open" if open_plan is True else None)
        dining = f.get("dining")
        kitchen_facts = f.ids("open_plan", "kitchen_layout", "kitchen_smell_separate",
                              "cooking", "dining")  # fmt: skip
        cook_scale = 1.15 if f.get("cooking") == "frequent" else 1.0
        if open_plan is False and dining == "kitchen":
            self.add("pi-kitchen", "Kitchen and dining", S.KITCHEN, "kitchen_dining", P.PUBLIC,
                     "z-day", level=self.level(entry_level), daylight=D.REQUIRED,
                     facts=kitchen_facts, scale=cook_scale, accessible=self.step_free)  # fmt: skip
        else:
            self.add("pi-kitchen", "Kitchen", S.KITCHEN, "kitchen", P.PUBLIC, "z-day",
                     level=self.level(entry_level), daylight=D.REQUIRED, facts=kitchen_facts,
                     scale=cook_scale, accessible=self.step_free,
                     notes=f"layout: {layout.replace('_', '-')}" if layout else None)  # fmt: skip
            self.add("pi-dining", "Dining", S.DINING, "dining", P.PUBLIC, "z-day",
                     level=self.level(entry_level), facts=f.ids("dining", "open_plan"),
                     accessible=self.step_free)  # fmt: skip
        if f.get("pantry") is True:
            self.add("pi-pantry", "Pantry", S.PANTRY, "pantry", P.SERVICE, "z-service",
                     level=self.level(entry_level), priority=f.priority("pantry", Priority.SHOULD),
                     daylight=D.NOT_NEEDED, facts=f.ids("pantry"))  # fmt: skip
        self._bedrooms()
        self._bathrooms()
        if f.get("guest_accommodation") == "suite":
            self.add("pi-guest-suite", "Guest suite (bedroom with own bathroom)", S.GUEST_SUITE,
                     "guest_suite", P.SEMI_PRIVATE, "z-guest", level=self.level("any"),
                     priority=f.priority("guest_accommodation", Priority.SHOULD),
                     daylight=D.REQUIRED, facts=f.ids("guest_accommodation", "guest_frequency"),
                     notes="in addition to the bedrooms you counted")  # fmt: skip
        for i in range(1, int(f.get("workspaces", 0) or 0) + 1):
            self.add(f"pi-study-{i}", f"Study {i}", S.STUDY, "study", P.SEMI_PRIVATE, "z-day",
                     level=self.level("any"), priority=f.priority("workspaces", Priority.MUST),
                     daylight=D.REQUIRED, facts=f.ids("workspaces", "office_quiet"))  # fmt: skip
        cars, kind = int(f.get("cars", 0) or 0), f.get("parking_type")
        if cars > 0 and kind in ("garage", "carport"):
            self.add("pi-garage", "Garage" if kind == "garage" else "Carport", S.GARAGE,
                            "garage_per_car", P.SERVICE, "z-service",
                            level=self.level("entry" if f.get("entry_at_road") else "any"),
                            priority=f.priority("parking_type", Priority.MUST),
                            daylight=D.NOT_NEEDED, scale=cars,
                            facts=f.ids("cars", "parking_type", "ev_charging"),
                            notes=f"{cars} car(s)" + ("; EV charger" if f.get("ev_charging")
                                                      else ""))  # fmt: skip
        if f.get("laundry_room") is True:
            self.add("pi-laundry", "Laundry", S.LAUNDRY, "laundry", P.SERVICE, "z-service",
                     priority=f.priority("laundry_room", Priority.SHOULD), level=self.level("any"),
                     daylight=D.NOT_NEEDED, facts=f.ids("laundry_room"))  # fmt: skip
        if f.get("storage_room") is True:
            self.add("pi-storage", "Store room", S.STORAGE, "storage", P.SERVICE, "z-service",
                     priority=f.priority("storage_room", Priority.SHOULD), level=self.level("any"),
                     daylight=D.NOT_NEEDED, facts=f.ids("storage_room"))  # fmt: skip
        self.add("pi-mechanical", "Plant / technical room", S.MECHANICAL, "mechanical",
                 P.SERVICE, "z-service", level=self.level("any"), daylight=D.NOT_NEEDED,
                 notes="heating, water and electrics")  # fmt: skip
        if f.get("prayer_room") is True:
            self.add("pi-prayer", "Prayer / quiet room", S.PRAYER, "prayer", P.PRIVATE, "z-night",
                     priority=f.priority("prayer_room", Priority.SHOULD), level=self.level("any"),
                     facts=f.ids("prayer_room"))  # fmt: skip
        if self.floors and self.floors > 1:
            self.add("pi-stair", "Stair", S.STAIR, "stair", P.SEMI_PRIVATE, "z-circulation",
                     facts=f.ids("floors"), notes=f"connects {self.floors} floors",
                     daylight=D.PREFERRED)  # fmt: skip
        if f.get("lift") is True:
            self.add("pi-lift", "Lift", S.LIFT, "lift", P.SEMI_PRIVATE, "z-circulation",
                     facts=f.ids("lift", "accessibility"), accessible=True,
                     daylight=D.NOT_NEEDED)  # fmt: skip
        outdoor = f.get("outdoor") or []
        for key, (name, function, level) in {
            "terrace": ("Terrace", S.TERRACE, "outdoor"),
            "roof_terrace": ("Roof terrace", S.TERRACE, "roof"),
            "balcony": ("Balcony", S.BALCONY, "any" if not self.floors or self.floors > 1
                        else "outdoor"),
        }.items():  # fmt: skip
            if key in outdoor:
                self.add(f"pi-{key.replace('_', '-')}", name, function, key, P.PUBLIC,
                         "z-outdoor", level=level, priority=f.priority("outdoor", Priority.SHOULD),
                         facts=f.ids("outdoor"))  # fmt: skip
        for key, name in OUTDOOR_WISHES.items():
            if key in outdoor:
                self.add(f"pi-{key.replace('_', '-')}", name, SpaceFunction.OTHER, None,
                         P.PUBLIC, "z-outdoor", level="outdoor",
                         priority=f.priority("outdoor", Priority.SHOULD), facts=f.ids("outdoor"),
                         notes="outdoor; not a room and not part of the floor area")  # fmt: skip
        self._sizes()
        self._relations()

    def _bedrooms(self) -> None:
        f, S, P, D = self.f, SpaceFunction, Privacy, DaylightNeed
        total = f.get("bedrooms")
        if not isinstance(total, int) or total <= 0:
            return
        facts = f.ids("bedrooms", "adults", "children", "children_own_rooms", "bedrooms_separate")
        private_level = self.level("not_entry" if f.get("bedrooms_separate") else "any")
        wanted: list[tuple[str, str, str, bool, list[str]]] = [
            ("pi-bed-main", "Main bedroom", "main_bedroom", False, f.ids("ensuite"))
        ]
        elders = int(f.get("elders", 0) or 0)
        for i in range(1, elders + 1):
            wanted.append((f"pi-bed-elder-{i}", f"Bedroom for older relative {i}", "bedroom",
                           self.step_free, f.ids("elders", "elder_step_free")))  # fmt: skip
        children = int(f.get("children", 0) or 0)
        kids = children if f.get("children_own_rooms") is not False else math.ceil(children / 2)
        for i in range(1, kids + 1):
            wanted.append((f"pi-bed-child-{i}", f"Child's bedroom {i}", "bedroom", False, []))
        if f.get("guest_accommodation") == "room":
            wanted.append(("pi-bed-guest", "Guest bedroom", "bedroom", False,
                           f.ids("guest_accommodation", "guest_frequency")))  # fmt: skip
        while len(wanted) < total:
            n = len(wanted) + 1
            wanted.append((f"pi-bed-{n}", f"Bedroom {n}", "bedroom", False, []))
        shared = len(wanted) > total
        for item_id, name, size, accessible, extra in wanted[:total]:
            level = "entry" if accessible and self.floors and self.floors > 1 else private_level
            note = None
            if shared and item_id.startswith("pi-bed-child"):
                note = "children share: you kept fewer bedrooms than one per child"
            self.add(item_id, name, S.BEDROOM, size, P.PRIVATE, "z-night", level=level,
                     daylight=D.REQUIRED, facts=[*facts, *extra], accessible=accessible,
                     notes=note)  # fmt: skip
        if f.get("accessible_ground_suite") is True and not any(
            i.accessible and i.function is S.BEDROOM for i in self.items
        ):
            first = next((i for i in self.items if i.function is S.BEDROOM), None)
            if first is not None:
                idx = self.items.index(first)
                self.items[idx] = first.model_copy(
                    update={"accessible": True, "level_preference": self.level("entry"),
                            "source_fact_ids": [*first.source_fact_ids,
                                                *f.ids("accessible_ground_suite")]}
                )  # fmt: skip

    def _bathrooms(self) -> None:
        f, S, P = self.f, SpaceFunction, Privacy
        total = f.get("bathrooms")
        if not isinstance(total, int) or total <= 0:
            return
        facts = f.ids("bathrooms")
        n = 0
        if f.get("ensuite") is True and any(i.id == "pi-bed-main" for i in self.items):
            main = next(i for i in self.items if i.id == "pi-bed-main")
            self.add("pi-bath-ensuite", "En-suite bathroom", S.BATHROOM, "ensuite", P.PRIVATE,
                     "z-night", level=main.level_preference or "any",
                     facts=[*facts, *f.ids("ensuite")])  # fmt: skip
            n = 1
        accessible_needed = self.step_free or f.get("accessible_ground_suite") is True
        for i in range(1, total - n + 1):
            accessible = accessible_needed and i == 1
            self.add(f"pi-bath-{i}", "Accessible bathroom" if accessible else f"Bathroom {i}",
                     S.BATHROOM, "accessible_bathroom" if accessible else "bathroom", P.PRIVATE,
                     "z-night", level=self.level("entry") if accessible else self.level("any"),
                     facts=[*facts, *(f.ids("accessibility", "accessible_ground_suite")
                                      if accessible else [])],
                     accessible=accessible)  # fmt: skip

    def _sizes(self) -> None:
        """Apply the owner's size wishes ("living=40", "bedrooms*0.8")."""
        wishes = self.f.get("room_sizes") or []
        facts = self.f.ids("room_sizes")
        for wish in wishes:
            if "=" in wish:
                room, value = wish.split("=", 1)
                targets = self.ids_for(room)
                for item_id in targets:
                    self._resize(item_id, float(value) / max(1, len(targets)), None, facts)
            elif "*" in wish:
                room, factor = wish.split("*", 1)
                for item_id in self.ids_for(room):
                    self._resize(item_id, None, float(factor), facts)

    def _resize(
        self, item_id: str, target: float | None, factor: float | None, facts: list[str]
    ) -> None:
        idx = next(i for i, it in enumerate(self.items) if it.id == item_id)
        it = self.items[idx]
        if it.target_area_m2 is None:
            return
        new_target = target if target is not None else it.target_area_m2 * (factor or 1.0)
        new_min = min(it.min_area_m2 or new_target, new_target * 0.85)
        self.items[idx] = it.model_copy(
            update={"target_area_m2": round(new_target, 2), "min_area_m2": round(new_min, 2),
                    "max_area_m2": None, "source_fact_ids": [*it.source_fact_ids, *facts]}
        )  # fmt: skip
        if item_id in self.typical:
            self.typical.remove(item_id)

    def _relations(self) -> None:
        f = self.f
        K, H, Sf = AdjacencyKind, Strength.HARD, Strength.SOFT
        self.link("pi-entry", EXTERIOR, K.CONNECTED, H, "The front door opens into the hall")
        layout = f.get("kitchen_layout") or ("open" if f.get("open_plan") is True else None)
        kf = f.ids("open_plan", "kitchen_layout", "kitchen_smell_separate")
        if layout == "open":
            self.link("pi-kitchen", "pi-living", K.CONNECTED, H,
                      "One open living, dining and kitchen space", kf)  # fmt: skip
            self.link("pi-dining", "pi-living", K.CONNECTED, H, "Part of the open space", kf)
        else:
            self.link("pi-kitchen", "pi-living", K.ADJACENT, Sf,
                      "Kitchen close to living, behind a door or glass wall", kf)  # fmt: skip
            self.link("pi-dining", "pi-living", K.NEAR, Sf, "Dining near living", kf)
        self.link("pi-kitchen", "pi-dining", K.CONNECTED, H, "Food goes from kitchen to table",
                  f.ids("dining"))  # fmt: skip
        self.link("pi-pantry", "pi-kitchen", K.CONNECTED, H, "Pantry opens off the kitchen",
                  f.ids("pantry"))  # fmt: skip
        self.link("pi-bed-main", "pi-bath-ensuite", K.CONNECTED, H,
                  "En-suite opens from the main bedroom", f.ids("ensuite"))  # fmt: skip
        if f.get("bedrooms_separate") is True:
            for item in self.items:
                if item.function is SpaceFunction.BEDROOM:
                    self.link(item.id, "pi-living", K.ACOUSTIC_SEPARATION, Sf,
                              "Bedrooms kept away from the living areas",
                              f.ids("bedrooms_separate"), weight=1.5)  # fmt: skip
        if f.get("privacy") == "high" or f.get("bedrooms_separate") is True:
            self.link("pi-guest-suite", "pi-bed-main", K.SEPARATED, Sf,
                      "Guests and family sleep apart", f.ids("privacy", "bedrooms_separate"))
        if f.get("office_quiet") is True:
            for item in self.items:
                if item.function is SpaceFunction.STUDY:
                    self.link(item.id, "pi-living", K.ACOUSTIC_SEPARATION, Sf,
                              "Quiet workplace", f.ids("office_quiet"), weight=2.0)
                    self.link(item.id, "pi-entry", K.NEAR, Sf, "Visitors reach the study "
                              "without crossing the house", f.ids("workspaces"), weight=1.0)
        self.link("pi-garage", "pi-entry", K.NEAR, Sf, "Short walk from the car to the door",
                  f.ids("parking_type", "entry_at_road"))  # fmt: skip
        self.link("pi-laundry", "pi-kitchen", K.NEAR, Sf, "Service rooms together",
                  f.ids("laundry_room"), weight=1.0)  # fmt: skip
        self.link("pi-terrace", "pi-living", K.CONNECTED, Sf, "Living opens to the terrace",
                  f.ids("outdoor"))  # fmt: skip
        self.link("pi-stair", "pi-entry", K.NEAR, Sf, "Stair reached from the hall",
                  f.ids("floors"), weight=1.0)  # fmt: skip
        self.link("pi-lift", "pi-entry", K.NEAR, H, "Lift reached step-free from the entrance",
                  f.ids("lift"))  # fmt: skip
        for item in self.items:
            if item.accessible and item.function is SpaceFunction.BEDROOM:
                bath = next((b.id for b in self.items if b.accessible and
                             b.function is SpaceFunction.BATHROOM), None)  # fmt: skip
                if bath:
                    self.link(item.id, bath, K.NEAR, H, "Step-free bedroom near an accessible "
                              "bathroom", f.ids("accessibility", "elder_step_free",
                                                 "accessible_ground_suite"))  # fmt: skip
        rels = f.get("relationships") or []
        hard = f.priority("relationships", Priority.SHOULD) is Priority.MUST
        for rel in rels:
            a_room, kind, b_room = rel.split("|")
            a_ids = self.ids_for(a_room) or ([EXTERIOR] if a_room in ("garden", "terrace") else [])
            b_ids = self.ids_for(b_room) or ([EXTERIOR] if b_room in ("garden", "terrace") else [])
            for a in a_ids:
                for b in b_ids:
                    if a == EXTERIOR:
                        a, b = b, a
                    self.link(a, b, K.NEAR if kind == "near" else K.SEPARATED,
                              H if hard else Sf, f"You asked: {a_room.replace('_', ' ')} "
                              f"{'next to' if kind == 'near' else 'away from'} "
                              f"{b_room.replace('_', ' ')}", f.ids("relationships"),
                              weight=3.0)  # fmt: skip


ZONES = [
    ProgramZone(id="z-day", name="Day (living, kitchen, dining)", privacy=Privacy.PUBLIC),
    ProgramZone(id="z-night", name="Night (bedrooms, bathrooms)", privacy=Privacy.PRIVATE),
    ProgramZone(id="z-guest", name="Guests", privacy=Privacy.SEMI_PRIVATE),
    ProgramZone(id="z-service", name="Service", privacy=Privacy.SERVICE),
    ProgramZone(id="z-circulation", name="Circulation", privacy=Privacy.SEMI_PRIVATE),
    ProgramZone(id="z-outdoor", name="Outdoor", privacy=Privacy.PUBLIC),
]


#: Typical car envelope when the owner has not given a size (S10-10): an assumption, with
#: an open question asking for the real vehicle.
TYPICAL_CAR = {"width_m": 1.8, "length_m": 4.5, "door_side_clearance_m": 0.6}
TYPICAL_CAR_SOURCE = "typical car envelope (assumption until the owner gives the car size)"


def _usability(b: _Builder) -> UsabilityRequirements:
    """Seats, beds and vehicles the usability studies test the plan against (S10-10)."""
    ids = {i.id for i in b.items}
    cars = int(b.f.get("cars", 0) or 0) if "pi-garage" in ids else 0
    return UsabilityRequirements(
        household_seats=_household_seats(b.f),
        vehicles=[
            VehicleEnvelope(id=f"car-{n}", source=TYPICAL_CAR_SOURCE, **TYPICAL_CAR)
            for n in range(1, cars + 1)
        ]
        or None,
        double_bed_program_item_ids=[i for i in ("pi-bed-main",) if i in ids],
        single_bed_program_item_ids=sorted(i for i in ids if i.startswith("pi-bed-child")),
    )


def _household_seats(f: Facts) -> int | None:
    """Dining seats for everyone the program plans bedrooms for.

    Adults and children must both be stated. Older relatives are added when stated;
    when absent the program plans no elder bedrooms, so none are seated either.
    """
    counts = [f.get("adults"), f.get("children"), f.get("elders", 0)]
    if not all(type(c) is int for c in counts) or sum(counts) <= 0:
        return None
    return sum(counts)


def build_program(
    brief: DesignBrief,
    *,
    site: SiteContext | None,
    brief_ref: ArtifactRef | None,
    created_at: datetime,
    program_id: str = "program",
    open_prompts: int = 0,
) -> ProgramResult:
    """Build the program from the brief. ``open_prompts`` is how many interview
    questions are still unanswered (reported, not blocking)."""
    b = _Builder(brief, site)
    b.build()
    used_zones = {i.zone_id for i in b.items}
    budget = brief.budget
    provenance = Provenance(
        created_at=created_at,
        created_by=TOOL_ACTOR,
        method="program_from_brief",
        tool="house-ai program",
        inputs=[brief_ref] if brief_ref else [],
        notes="Deterministic; sizes not given by the owner are typical values (assumptions).",
    )
    program = SpaceProgram(
        id=program_id,
        project_id=brief.project_id,
        brief_ref=brief_ref,
        items=b.items,
        adjacencies=b.adj,
        zones=[z for z in ZONES if z.id in used_zones],
        target_gross_area_m2=brief.target_gross_area_m2,
        circulation_factor=CIRCULATION,
        levels=b.floors,
        budget=budget,
        site_ref=site.site_ref if site else None,
        site_verified=bool(site and site.verified),
        usability=_usability(b),
        provenance=provenance,
    )
    assumptions = [
        Assumption(
            id="asm-typical-sizes",
            statement="Rooms without a size from you use typical sizes for a first layout: "
            + ", ".join(
                f"{i.name} {i.target_area_m2:g} m²" for i in b.items
                if i.id in b.typical and i.target_area_m2
            )
            + ". These are not building-code minimums; no local rules are loaded.",
            basis="house-ai typical-size table (program.builder.TYPICAL)",
            affects=list(b.typical),
            confirm_with="owner",
        ),
        Assumption(
            id="asm-circulation",
            statement=f"Halls, walls and structure add {CIRCULATION:.0%} to the room areas.",
            basis="Typical share for a compact house; checked again in Milestone D.",
            affects=[program_id],
            confirm_with="architect",
        ),
        Assumption(
            id="asm-entry-and-plant",
            statement="The house has an entrance hall and a small plant / technical room.",
            basis="Every house needs a way in and room for heating, water and electrics.",
            affects=["pi-entry", "pi-mechanical"],
            confirm_with="owner",
        ),
    ]  # fmt: skip
    if site is not None and site.site_ref is not None and not site.verified:
        assumptions.append(
            Assumption(
                id="asm-site-unverified",
                statement="Site values used here (parcel area, slope, frontage) come from the "
                "survey but you have not confirmed the site yet.",
                basis="Site gate not approved for this site version.",
                status=Epistemic.UNKNOWN,
                affects=[program_id],
                confirm_with="owner",
            )
        )
    if any(i.id == "pi-guest-suite" for i in b.items):
        assumptions.append(
            Assumption(
                id="asm-guest-suite-extra",
                statement="The guest suite is in addition to the bedrooms you counted.",
                basis="The bedroom question counted bedrooms; a suite was asked separately.",
                affects=["pi-guest-suite"],
                confirm_with="owner",
            )
        )
    if site is not None and ((site.relief_m or 0.0) >= 8.0 or (site.mean_slope_pct or 0.0) >= 20.0):
        assumptions.append(
            Assumption(
                id="asm-hillside-engineering",
                statement=(
                    "Steep hillside terrain requires split-level or stepped massing, road-level "
                    "access coordination, excavation, retaining walls, slope drainage, and "
                    "structural engineering review; the full parcel area cannot be assumed "
                    "buildable."
                ),
                basis="Surveyed site relief and slope indicate steep hillside construction.",
                affects=[program_id],
                confirm_with="engineer",
            )
        )
    if program.usability.vehicles:
        assumptions.append(
            Assumption(
                id="asm-car-size",
                statement=(
                    "Each car is taken as {width_m} m wide and {length_m} m long, with "
                    "{door_side_clearance_m} m to open its doors, to test the garage."
                ).format(**TYPICAL_CAR),
                basis=TYPICAL_CAR_SOURCE,
                affects=["pi-garage"],
                confirm_with="owner",
            )
        )
    if program.usability.double_bed_program_item_ids:
        assumptions.append(
            Assumption(
                id="asm-beds",
                statement="The main bedroom is tested for a double bed and children's "
                "bedrooms for single beds.",
                basis="Who sleeps where, from the household answers.",
                affects=[
                    *program.usability.double_bed_program_item_ids,
                    *program.usability.single_bed_program_item_ids,
                ],
                confirm_with="owner",
            )
        )
    questions = _open_questions(b.f, open_prompts, site)
    if program.usability.vehicles:
        questions.append(
            OpenQuestion(
                id="oq-car-size",
                question="Which car(s) will you park? Their size tests the garage.",
                topic="cars",
                why_it_matters="the garage is checked against a typical car until then",
                blocking=False,
            )
        )
    return ProgramResult(
        program=program,
        assumptions=AssumptionsFile(
            project_id=brief.project_id, assumptions=assumptions, provenance=provenance
        ),
        open_questions=OpenQuestionsFile(
            project_id=brief.project_id, questions=questions, provenance=provenance
        ),
        typical_sized=list(b.typical),
    )


#: Slot -> question to record when it is unknown, and whether it blocks the program.
_NEEDED: dict[str, tuple[str, bool]] = {
    "adults": ("How many adults will live in the house?", True),
    "bedrooms": ("How many bedrooms do you want?", True),
    "bathrooms": ("How many bathrooms do you want?", True),
    "floors": ("How many floors should the house have?", False),
    "budget": ("What is the building budget?", False),
    "target_area": ("Is there a total floor area in mind?", False),
    "slope_strategy": ("How should the house meet the slope?", False),
}


def _open_questions(
    f: Facts, open_prompts: int, site: SiteContext | None
) -> list[OpenQuestion]:
    out = []
    sloped = site is not None and (site.relief_m or 0.0) >= 2.0
    for slot, (question, blocking) in _NEEDED.items():
        if slot == "slope_strategy" and not sloped:
            continue
        fact = f.by_key.get(slot)
        if fact is None or fact.value is None:
            out.append(
                OpenQuestion(
                    id=f"oq-{slot.replace('_', '-')}",
                    question=question,
                    topic=slot,
                    why_it_matters="needed to size the program" if blocking
                    else "helps check the program against budget and site",
                    blocking=blocking,
                    answer=None,
                )
            )  # fmt: skip
    if open_prompts:
        out.append(
            OpenQuestion(
                id="oq-interview-unfinished",
                question=f"The interview has {open_prompts} question(s) left.",
                topic="interview",
                why_it_matters="unanswered topics use defaults or are left out",
                blocking=False,
            )
        )
    return out
