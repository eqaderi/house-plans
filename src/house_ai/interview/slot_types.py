"""The type of every interview slot, and a strict check of proposed values.

Used for values proposed by an LLM (anything that does not fit is discarded)
and, in tests, to prove the deterministic parsers only produce valid values.
"""

from __future__ import annotations

import re
from typing import Any

from house_ai.domain.brief import FactValue

from .parsing import ROOMS
from .questions import SLOTS

INT = {"adults", "children", "elders", "household_size", "bedrooms", "bathrooms", "storeys",
       "workspaces", "cars"}  # fmt: skip
BOOL = {
    "children_own_rooms", "elder_step_free", "ensuite", "entry_at_road", "open_plan",
    "kitchen_smell_separate", "pantry", "office_quiet", "ev_charging", "laundry_room",
    "storage_room", "lift", "accessible_ground_suite", "bedrooms_separate", "cross_ventilation",
    "future_expansion", "prayer_room", "gathering_space",
}  # fmt: skip
CHOICE: dict[str, set[str]] = {
    "slope_strategy": {"step_down", "platform", "no_preference"},
    "cooking": {"frequent", "light"},
    "dining": {"kitchen", "separate_room"},
    "guest_accommodation": {"none", "room", "suite"},
    "guest_frequency": {"often", "sometimes", "rarely"},
    "parking_type": {"garage", "carport", "open"},
    "accessibility": {"none", "step_free", "wheelchair", "future_ready"},
    "privacy": {"high", "normal", "low"},
    "kitchen_layout": {"open", "semi_open", "closed"},
}
OUTDOOR = {"terrace", "roof_terrace", "garden", "balcony", "pool", "play_area",
           "vegetable_garden"}  # fmt: skip
TEXT = {"light_wishes", "style", "priorities"}
_ROOM_KEYS = "|".join(ROOMS)
_REL = re.compile(rf"^({_ROOM_KEYS})\|(near|apart)\|({_ROOM_KEYS})$")
_SIZE = re.compile(rf"^({_ROOM_KEYS})(=\d+(\.\d+)?|\*\d+(\.\d+)?)$")
_BUDGET = re.compile(r"^\d+ [A-Z]{3}$")
assert INT | BOOL | set(CHOICE) | TEXT | {"outdoor", "relationships", "room_sizes", "budget",
                                          "target_area"} == set(SLOTS)  # fmt: skip


class InvalidValue(ValueError):
    pass


def check(slot: str, value: Any) -> FactValue:
    """Return ``value`` if it is a valid value for ``slot``; raise otherwise."""
    if slot not in SLOTS:
        raise InvalidValue(f"unknown slot {slot!r}")
    if value is None:
        return None
    ok: bool
    if slot in INT:
        ok = isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 30
    elif slot in BOOL:
        ok = isinstance(value, bool)
    elif slot in CHOICE:
        ok = isinstance(value, str) and value in CHOICE[slot]
    elif slot == "outdoor":
        ok = isinstance(value, list) and all(v in OUTDOOR for v in value)
    elif slot == "relationships":
        ok = isinstance(value, list) and all(isinstance(v, str) and _REL.match(v) for v in value)
    elif slot == "room_sizes":
        ok = isinstance(value, list) and all(isinstance(v, str) and _SIZE.match(v) for v in value)
    elif slot == "priorities":
        ok = isinstance(value, list) and all(isinstance(v, str) and v for v in value)
    elif slot == "budget":
        ok = isinstance(value, str) and bool(_BUDGET.match(value))
    elif slot == "target_area":
        ok = isinstance(value, int | float) and not isinstance(value, bool) and 10 <= value <= 5000
    else:
        ok = isinstance(value, str) and 0 < len(value) <= 2000
    if not ok:
        raise InvalidValue(f"{value!r} is not a valid value for {slot}")
    return value
