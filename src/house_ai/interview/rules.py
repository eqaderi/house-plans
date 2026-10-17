"""Contradictions between answers, with the trade-off and the ways out.

A rule looks at the current slot values. When requirements cannot all hold,
it names the slots involved, explains the trade-off in plain language and
offers options; each option says which slots it would change. Nothing is
changed until the owner picks one (a RESOLUTION turn). An option that keeps
the values as they are ("accept") resolves the contradiction for exactly
those values; if they change later, it is raised again.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .questions import Values, needed_bedrooms


@dataclass(frozen=True)
class Option:
    label: str
    #: Slot -> new value. Empty means "keep as is and accept the trade-off".
    updates: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    id: str
    statement: str
    slots: tuple[str, ...]
    tradeoff: str
    options: tuple[Option, ...]


Rule = Callable[[Values], Finding | None]


def _step_free(v: Values) -> bool:
    return v.get("accessibility") in ("step_free", "wheelchair") or v.get("elder_step_free") is True


def lift_on_one_level(v: Values) -> Finding | None:
    if v.get("floors") == 1 and v.get("lift") is True:
        return Finding(
            "c-lift-one-level",
            "You asked for a lift, but also for a house on one floor.",
            ("floors", "lift"),
            "A lift only helps between floors. On one floor it costs space and money and does "
            "nothing.",
            (
                Option("Keep one floor and drop the lift", {"lift": False}),
                Option("Build two floors with a lift", {"floors": 2}),
            ),
        )
    return None


def stairs_without_step_free_route(v: Values) -> Finding | None:
    floors = v.get("floors")
    if (
        _step_free(v)
        and isinstance(floors, int)
        and floors > 1
        and v.get("lift") is not True
        and v.get("accessible_ground_suite") is not True
    ):
        slots = tuple(
            s for s in ("accessibility", "elder_step_free", "floors", "lift") if s in v
        )
        return Finding(
            "c-stairs-step-free",
            f"Someone needs step-free living, but the house has {floors} floors and no lift.",
            slots,
            "Stairs would cut that person off from part of the house. A lift costs roughly a "
            "small room of floor area per level and adds cost and maintenance; keeping their "
            "rooms on the entrance level costs nothing but fixes where those rooms go.",
            (
                Option("Add a lift", {"lift": True}),
                Option(
                    "Put a bedroom, a bathroom and the kitchen on the entrance level for them",
                    {"accessible_ground_suite": True},
                ),
                Option("Build everything on one floor", {"floors": 1}),
            ),
        )
    return None


def too_few_bedrooms(v: Values) -> Finding | None:
    need, have = needed_bedrooms(v), v.get("bedrooms")
    if need is None or not isinstance(have, int) or have >= need:
        return None
    sharing = v.get("children_own_rooms")
    slots = tuple(
        s for s in ("bedrooms", "adults", "children", "elders", "children_own_rooms",
                    "guest_accommodation") if s in v
    )  # fmt: skip
    options = [Option(f"Plan {need} bedrooms", {"bedrooms": need})]
    if sharing is not False and (v.get("children") or 0) >= 2:
        options.append(Option("Let the children share bedrooms", {"children_own_rooms": False}))
    if v.get("guest_accommodation") == "room":
        options.append(Option("No separate guest room", {"guest_accommodation": "none"}))
    options.append(Option(f"Keep {have} bedrooms; we will manage", {}))
    return Finding(
        "c-too-few-bedrooms",
        f"You asked for {have} bedroom(s), but the household as you described it needs {need}.",
        slots,
        "Each extra bedroom adds about 10–14 m² and cost; fewer bedrooms means people share.",
        tuple(options),
    )


def open_kitchen_keeps_smells(v: Values) -> Finding | None:
    if (
        v.get("open_plan") is True
        and v.get("kitchen_smell_separate") is True
        and v.get("kitchen_layout") not in ("semi_open", "closed")
    ):
        return Finding(
            "c-open-kitchen-smells",
            "You want an open kitchen, and also that cooking smells stay out of the living room.",
            ("open_plan", "kitchen_smell_separate"),
            "An open kitchen shares its air with the living room; a strong extractor reduces "
            "smells but does not stop them. A door or glass wall stops them but makes the "
            "space less open.",
            (
                Option("Semi-open kitchen with glass sliding doors",
                       {"kitchen_layout": "semi_open"}),
                Option("Closed kitchen", {"kitchen_layout": "closed", "open_plan": False}),
                Option("Keep it open; some smell is acceptable",
                       {"kitchen_smell_separate": False}),
            ),
        )  # fmt: skip
    return None


def ensuite_is_the_only_bathroom(v: Values) -> Finding | None:
    if v.get("ensuite") is True and v.get("bathrooms") == 1 and (v.get("household_size") or 0) > 2:
        return Finding(
            "c-only-bathroom-ensuite",
            "You want an en-suite for the main bedroom, but only one bathroom in total.",
            ("ensuite", "bathrooms", "household_size"),
            "The only bathroom would be inside the main bedroom, so everyone else would walk "
            "through it. A second bathroom adds about 4–6 m².",
            (
                Option("Two bathrooms: the en-suite and a shared one", {"bathrooms": 2}),
                Option("No en-suite; one shared bathroom", {"ensuite": False}),
            ),
        )
    return None


def parking_without_cars(v: Values) -> Finding | None:
    if v.get("cars") == 0 and v.get("parking_type") in ("garage", "carport"):
        return Finding(
            "c-parking-no-cars",
            f"You asked for a {v['parking_type']}, but for no cars.",
            ("cars", "parking_type"),
            "A garage for one car needs about 15–18 m² that could go to other rooms.",
            (
                Option("Plan parking for one car", {"cars": 1}),
                Option("No garage or carport", {"parking_type": "open"}),
            ),
        )
    return None


def near_and_apart(v: Values) -> Finding | None:
    rels = v.get("relationships") or []
    pairs: dict[frozenset[str], set[str]] = {}
    for rel in rels:
        a, kind, b = rel.split("|")
        pairs.setdefault(frozenset((a, b)), set()).add(kind)
    clash = sorted(tuple(sorted(pair)) for pair, kinds in pairs.items() if len(kinds) > 1)
    if not clash:
        return None
    a, b = clash[0]
    keep_near = [r for r in rels if not (set(r.split("|")[::2]) == {a, b} and "|apart|" in r)]
    keep_apart = [r for r in rels if not (set(r.split("|")[::2]) == {a, b} and "|near|" in r)]
    return Finding(
        "c-near-and-apart",
        f"You asked for {a.replace('_', ' ')} to be both next to and away from "
        f"{b.replace('_', ' ')}.",
        ("relationships",),
        "Two rooms cannot be next to each other and apart at the same time.",
        (
            Option(f"Keep {a.replace('_', ' ')} next to {b.replace('_', ' ')}",
                   {"relationships": keep_near}),
            Option(f"Keep {a.replace('_', ' ')} away from {b.replace('_', ' ')}",
                   {"relationships": keep_apart}),
        ),
    )  # fmt: skip


RULES: list[Rule] = [
    lift_on_one_level,
    stairs_without_step_free_route,
    too_few_bedrooms,
    open_kitchen_keeps_smells,
    ensuite_is_the_only_bathroom,
    parking_without_cars,
    near_and_apart,
]


def contradictions(values: Values) -> list[Finding]:
    return [f for rule in RULES if (f := rule(values)) is not None]
