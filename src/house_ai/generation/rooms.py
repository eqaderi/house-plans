"""Program items -> placeable rooms, and clusters of rooms that must touch.

A cluster is a connected component of HARD ``connected`` requirements. It is
placed as one contiguous group in a row of the massing, using a small slot
layout found by exhaustive search: each slot holds one room spanning the row
depth, or two rooms stacked across it (the "inner" one on the corridor side,
the "outer" one on the exterior side). Every pair that must connect then
shares a wall, which a 1-D sequence alone cannot guarantee (an open
living-kitchen-dining triangle, for example).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations

from house_ai.domain.base import EXTERIOR
from house_ai.domain.brief import Priority
from house_ai.domain.program import (
    AdjacencyKind,
    DaylightNeed,
    ProgramItem,
    SpaceFunction,
    SpaceProgram,
    Strength,
)

S = SpaceFunction

OUTDOOR_FUNCTIONS = {S.TERRACE, S.BALCONY}
OUTDOOR_LEVELS = {"outdoor", "roof"}
CIRCULATION_FUNCTIONS = {S.HALL, S.CORRIDOR}
#: Rooms normally entered through the room they serve, not from a corridor.
DEPENDENT_FUNCTIONS = {S.BATHROOM, S.WC, S.PANTRY, S.STORAGE, S.ABLUTION}
#: Rooms joined by a cased opening rather than a door when they must connect.
OPEN_PLAN_FUNCTIONS = {S.LIVING, S.FAMILY, S.KITCHEN, S.DINING, S.RECEPTION, S.ENTRY}
#: Which room of a cluster gets the corridor door: lower rank first.
ANCHOR_RANK = [
    S.ENTRY,
    S.LIVING,
    S.FAMILY,
    S.RECEPTION,
    S.KITCHEN,
    S.DINING,
    S.GUEST_SUITE,
    S.BEDROOM,
    S.STUDY,
    S.PLAY,
    S.GYM,
    S.PRAYER,
    S.GARAGE,
    S.LAUNDRY,
    S.MECHANICAL,
]
#: Largest cluster laid out exhaustively.
MAX_CLUSTER = 6


@dataclass(frozen=True)
class RoomSpec:
    space_id: str
    item: ProgramItem
    index: int
    effective_min_area_m2: float | None = None
    effective_min_width_m: float | None = None

    @property
    def min_area_m2(self) -> float | None:
        if self.effective_min_area_m2 is not None:
            return max(self.item.min_area_m2 or 0.0, self.effective_min_area_m2)
        return self.item.min_area_m2

    @property
    def min_width_m(self) -> float | None:
        if self.effective_min_width_m is not None:
            return max(self.item.min_width_m or 0.0, self.effective_min_width_m)
        return self.item.min_width_m

    @property
    def function(self) -> SpaceFunction:
        return self.item.function

    @property
    def name(self) -> str:
        return self.item.name if self.item.quantity == 1 else f"{self.item.name} {self.index}"

    @property
    def daylight_required(self) -> bool:
        return self.item.daylight is DaylightNeed.REQUIRED

    @property
    def wants_daylight(self) -> bool:
        return self.item.daylight is not DaylightNeed.NOT_NEEDED

    @property
    def priority_weight(self) -> int:
        return 2 if self.item.priority is Priority.MUST else 1


@dataclass
class Slot:
    """One column of a cluster: a room spanning the row, or (inner, outer) stacked."""

    rooms: tuple[RoomSpec, ...]

    @property
    def stacked(self) -> bool:
        return len(self.rooms) == 2


@dataclass
class Cluster:
    id: str
    members: list[RoomSpec]
    slots: list[Slot]
    #: Room that gets the corridor door.
    anchor: RoomSpec
    #: Pairs (space ids) inside the cluster that must connect directly.
    connections: list[tuple[str, str]]
    #: Hard pairs the slot layout could not make touch.
    unsatisfied: list[tuple[str, str]] = field(default_factory=list)

    @property
    def is_entry(self) -> bool:
        return any(r.function is S.ENTRY for r in self.members)


@dataclass
class Relation:
    a: str
    b: str
    kind: AdjacencyKind
    strength: Strength
    weight: float
    requirement_id: str


@dataclass
class ProgramRooms:
    rooms: list[RoomSpec]
    clusters: list[Cluster]
    #: The item the entry bar's corridor stands for (a hall), if the program has one.
    hall_item: ProgramItem | None
    stair_item: ProgramItem | None
    #: Room the front door opens into; None means the corridor (hall) itself.
    entry_room: RoomSpec | None
    relations: list[Relation]
    #: Rooms with a HARD connection to the hall item: they need a corridor door.
    hall_connected: set[str]
    skipped: list[tuple[str, str]]

    def room(self, space_id: str) -> RoomSpec:
        return next(r for r in self.rooms if r.space_id == space_id)


def space_id_for(item: ProgramItem, index: int) -> str:
    base = "sp-" + item.id.removeprefix("pi-")
    return base if item.quantity == 1 else f"{base}-{index}"


def is_indoor(item: ProgramItem) -> bool:
    if item.function in OUTDOOR_FUNCTIONS or item.level_preference in OUTDOOR_LEVELS:
        return False
    # Garden, pool and similar wishes carry no area and are not rooms.
    return not (
        item.function is S.OTHER and item.target_area_m2 is None and item.min_area_m2 is None
    )


def expand_program(
    program: SpaceProgram,
    hard_min_areas: dict[str, float] | None = None,
    hard_min_widths: dict[str, float] | None = None,
) -> ProgramRooms:
    rooms: list[RoomSpec] = []
    skipped: list[tuple[str, str]] = []
    hall_item = stair_item = None
    first_space: dict[str, str] = {}
    entry_item = next((i for i in program.items if i.function is S.ENTRY), None)
    for item in program.items:
        if not is_indoor(item):
            skipped.append((item.id, "outdoor item; Milestone D places indoor rooms only"))
            continue
        if item.function is S.STAIR:
            stair_item = stair_item or item
            continue
        if item.function in CIRCULATION_FUNCTIONS and hall_item is None:
            hall_item = item
            continue
        min_a = (hard_min_areas or {}).get(item.id)
        min_w = (hard_min_widths or {}).get(item.id)
        for k in range(1, item.quantity + 1):
            spec = RoomSpec(
                space_id_for(item, k),
                item,
                k,
                effective_min_area_m2=min_a,
                effective_min_width_m=min_w,
            )
            rooms.append(spec)
            first_space.setdefault(item.id, spec.space_id)
    hall_key = hall_item.id if hall_item else None

    relations: list[Relation] = []
    hard_pairs: list[tuple[str, str]] = []
    hall_connected: set[str] = set()
    for adj in program.adjacencies:
        a_id, b_id = adj.a, adj.b
        if EXTERIOR in (a_id, b_id):
            continue
        if hall_key in (a_id, b_id):
            other = b_id if a_id == hall_key else a_id
            if adj.kind is AdjacencyKind.CONNECTED and other in first_space:
                hall_connected.add(first_space[other])
            continue
        if a_id not in first_space or b_id not in first_space:
            continue
        a, b = first_space[a_id], first_space[b_id]
        relations.append(Relation(a, b, adj.kind, adj.strength, adj.weight or 0.0, adj.id))
        if adj.kind is AdjacencyKind.CONNECTED and adj.strength is Strength.HARD:
            hard_pairs.append((a, b))
    entry_room = next((r for r in rooms if entry_item and r.item.id == entry_item.id), None)
    clusters = _clusters(rooms, hard_pairs)
    return ProgramRooms(
        rooms=rooms,
        clusters=clusters,
        hall_item=hall_item,
        stair_item=stair_item,
        entry_room=entry_room,
        relations=relations,
        hall_connected=hall_connected,
        skipped=skipped,
    )


def _clusters(rooms: list[RoomSpec], pairs: list[tuple[str, str]]) -> list[Cluster]:
    parent = {r.space_id: r.space_id for r in rooms}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        parent[find(a)] = find(b)
    groups: dict[str, list[RoomSpec]] = {}
    for r in rooms:
        groups.setdefault(find(r.space_id), []).append(r)
    out = []
    for members in groups.values():
        ids = {m.space_id for m in members}
        conns = [(a, b) for a, b in pairs if a in ids and b in ids]
        slots, unsatisfied = layout_cluster(members, conns)
        anchor = _anchor(members, slots, conns)
        out.append(
            Cluster(
                id="cl-" + members[0].space_id.removeprefix("sp-"),
                members=members,
                slots=slots,
                anchor=anchor,
                connections=conns,
                unsatisfied=unsatisfied,
            )
        )
    return out


def _rank(r: RoomSpec) -> tuple[int, float, str]:
    rank = ANCHOR_RANK.index(r.function) if r.function in ANCHOR_RANK else len(ANCHOR_RANK)
    return (rank, -(r.item.target_area_m2 or 0.0), r.space_id)


def _degree(r: RoomSpec, conns: list[tuple[str, str]]) -> int:
    return sum(r.space_id in c for c in conns)


def is_dependent(r: RoomSpec, conns: list[tuple[str, str]]) -> bool:
    return r.function in DEPENDENT_FUNCTIONS and _degree(r, conns) == 1


def touches_corridor(slot: Slot, r: RoomSpec) -> bool:
    return not slot.stacked or slot.rooms[0] is r


def _anchor(members: list[RoomSpec], slots: list[Slot], conns) -> RoomSpec:
    on_corridor = [r for s in slots for r in s.rooms if touches_corridor(s, r)]
    candidates = [r for r in on_corridor if not is_dependent(r, conns)] or on_corridor
    return min(candidates, key=_rank)


def slot_adjacency(slots: list[Slot]) -> set[frozenset[str]]:
    """Pairs of rooms that share a wall in this slot layout."""
    pairs: set[frozenset[str]] = set()
    for s in slots:
        if s.stacked:
            pairs.add(frozenset(r.space_id for r in s.rooms))
    for left, right in zip(slots, slots[1:], strict=False):
        if left.stacked and right.stacked:
            pairs.add(frozenset((left.rooms[0].space_id, right.rooms[0].space_id)))
            pairs.add(frozenset((left.rooms[1].space_id, right.rooms[1].space_id)))
        else:
            for a in left.rooms:
                for b in right.rooms:
                    pairs.add(frozenset((a.space_id, b.space_id)))
    return pairs


def _layouts(members: list[RoomSpec]):
    """Every sequence of slots (singles and inner/outer stacks) over the members."""

    def walk(perm: tuple[RoomSpec, ...], i: int, acc: list[Slot]):
        # Choose where consecutive members pair up into a stack.
        if i == len(perm):
            yield list(acc)
            return
        yield from walk(perm, i + 1, [*acc, Slot((perm[i],))])
        if i + 1 < len(perm):
            yield from walk(perm, i + 2, [*acc, Slot((perm[i], perm[i + 1]))])

    for perm in permutations(members):
        yield from walk(perm, 0, [])


def layout_cluster(
    members: list[RoomSpec], conns: list[tuple[str, str]]
) -> tuple[list[Slot], list[tuple[str, str]]]:
    members = sorted(members, key=_rank)
    if len(members) == 1:
        return [Slot((members[0],))], []
    if len(members) > MAX_CLUSTER:
        slots = [Slot((m,)) for m in members]
        adj = slot_adjacency(slots)
        return slots, [c for c in conns if frozenset(c) not in adj]
    best: tuple[tuple, list[Slot], list[tuple[str, str]]] | None = None
    for slots in _layouts(members):
        adj = slot_adjacency(slots)
        missing = [c for c in conns if frozenset(c) not in adj]
        inner_dark = sum(1 for s in slots if s.stacked and s.rooms[0].daylight_required)
        corridor_ok = any(
            touches_corridor(s, r) and not is_dependent(r, conns) for s in slots for r in s.rooms
        )
        stacks = sum(s.stacked for s in slots)
        key = (
            len(missing),
            0 if corridor_ok else 1,
            inner_dark,
            stacks,
            tuple(tuple(r.space_id for r in s.rooms) for s in slots),
        )
        if best is None or key < best[0]:
            best = (key, slots, missing)
    assert best is not None
    return best[1], best[2]
