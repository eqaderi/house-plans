"""A solved massing -> a canonical :class:`HouseModel`.

Spaces are rectangles on the design grid. Walls are derived from the space
edges on each level: every wall segment has exactly one space (or the
outside) on each side, so an opening placed inside a wall lies between the
two spaces it claims to connect. Exterior faces are classified with the
surveyed terrain: a face with ground well above its floor is a retaining
wall and gets no windows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import box
from shapely.ops import unary_union

from house_ai.domain.base import EXTERIOR
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.geometry import Polygon2D
from house_ai.domain.model import (
    Ceiling,
    HouseModel,
    Level,
    MaterialCategory,
    MaterialRef,
    Opening,
    OpeningKind,
    Operation,
    RelationshipKind,
    Slab,
    SlabKind,
    Space,
    SpaceRelationship,
    Stair,
    StairKind,
    Wall,
    WallKind,
    Zone,
)
from house_ai.domain.program import AdjacencyKind, Privacy, SpaceFunction, SpaceProgram
from house_ai.domain.provenance import Actor, ArtifactRef
from house_ai.domain.records import Assumption, Issue, Severity
from house_ai.domain.site import Site

from .fixtures import with_fixtures
from .frame import DesignFrame, Ground, from_dm
from .massing import (
    FLOOR_TO_FLOOR_M,
    GARAGE_DEPTH_DM,
    HALF_STOREY_M,
    Bar,
    Massing,
)
from .rooms import (
    DEPENDENT_FUNCTIONS,
    OPEN_PLAN_FUNCTIONS,
    ProgramRooms,
    RoomSpec,
    is_dependent,
    touches_corridor,
)
from .solver import Solution
from .stairs import LANDING_STRIP_DM, SLAB_M, TREAD_M, stair_risers, u_layout

S = SpaceFunction
EXTERIOR_WALL_M = 0.30
INTERIOR_WALL_M = 0.15
WALL_HEIGHT_M = 2.8
CEILING_M = 2.7
DOOR_H_M = 2.1
#: Ground this far above the floor outside an exterior face makes it a retaining wall.
RETAINING_M = 0.6

MATERIALS = [
    MaterialRef(
        id="m-ext-wall",
        name="Exterior wall (placeholder)",
        category=MaterialCategory.WALL,
        base_color_hex="#E8E2D6",
    ),
    MaterialRef(
        id="m-int-wall",
        name="Interior partition (placeholder)",
        category=MaterialCategory.WALL,
        base_color_hex="#F4F4F2",
    ),
    MaterialRef(
        id="m-retaining",
        name="Retaining wall, concrete (placeholder)",
        category=MaterialCategory.WALL,
        base_color_hex="#9A9A96",
    ),
    MaterialRef(
        id="m-floor",
        name="Floor finish (placeholder)",
        category=MaterialCategory.FLOOR,
        base_color_hex="#C8A97E",
    ),
    MaterialRef(
        id="m-slab",
        name="Concrete slab (placeholder)",
        category=MaterialCategory.FLOOR,
        base_color_hex="#A0A09C",
    ),
    MaterialRef(id="m-glass", name="Glazing (placeholder)", category=MaterialCategory.GLAZING),
    MaterialRef(id="m-door", name="Door leaf (placeholder)", category=MaterialCategory.DOOR),
]


@dataclass
class Rect:
    u0: int
    v0: int
    u1: int
    v1: int

    @property
    def w(self) -> int:
        return self.u1 - self.u0

    @property
    def h(self) -> int:
        return self.v1 - self.v0


@dataclass
class SpaceInfo:
    id: str
    name: str
    function: SpaceFunction
    level_id: str
    rect: Rect
    kind: str  # room | corridor | link | stair | gallery | filler
    bar_id: str | None = None
    row_id: str | None = None
    start_dm: int = 0
    room: RoomSpec | None = None
    program_item_id: str | None = None
    zone_id: str | None = None


@dataclass
class WallSeg:
    level_id: str
    orient: str  # "h" (constant v) | "v" (constant u)
    c: int
    a: int
    b: int
    neg: str | None
    pos: str | None
    id: str = ""
    kind: WallKind = WallKind.INTERIOR
    thickness: float = INTERIOR_WALL_M
    party: bool = False
    retained_m: float = 0.0
    used: list[tuple[int, int]] = field(default_factory=list)
    #: Overrides for stairwell enclosures, which do not span a plain storey (ADR 0023).
    height_m: float = WALL_HEIGHT_M
    base_offset_m: float = 0.0

    @property
    def length(self) -> int:
        return self.b - self.a

    def sides(self) -> set[str | None]:
        return {self.neg, self.pos}

    def outward(self) -> tuple[int, int]:
        """Direction from the space to the outside, for an exterior segment."""
        sign = -1 if self.neg is None else 1
        return (0, sign) if self.orient == "h" else (sign, 0)


@dataclass
class Stairwell:
    """A straight flight crossing from one bar into another at a different level."""

    stair_index: int
    low_level: str
    high_level: str
    #: Axis of the flight's run: "v" when it runs along v (bars of axis "u"), else "u".
    run_axis: str
    boundary: int
    lo: int
    hi: int
    #: Cross range (dm) of the stairwell: the flight's width plus a wall clearance.
    c0: int
    c1: int
    rise_m: float
    #: True when the lower bar lies on the ``lo`` side of the boundary.
    lower_on_lo: bool
    #: The stair spaces the flight starts and ends in.
    low_space: str
    high_space: str
    #: Space the flight continues in across the boundary, on each level ("below" on the
    #: lower level, "over" on the higher one): a new stairwell or stair hall, or an
    #: existing room where that level is already built (stacked bars).
    joins: dict[str, str] = field(default_factory=dict)
    #: The stairwell and stair-hall spaces created for this flight.
    created: set[str] = field(default_factory=set)

    @property
    def below_id(self) -> str:
        return f"sp-stairwell-{self.stair_index}"

    @property
    def over_id(self) -> str:
        return f"sp-stair-hall-{self.stair_index}"

    def rect(self, p0: int, p1: int) -> Rect:
        if self.run_axis == "v":
            return Rect(self.c0, p0, self.c1, p1)
        return Rect(p0, self.c0, p1, self.c1)


@dataclass
class Assembly:
    model: HouseModel
    spaces: list[SpaceInfo]
    walls: list[WallSeg]
    notes: list[str]


def _level_id(z: float, entry: float) -> str:
    rel = round(z - entry, 3)
    if abs(rel) < 1e-6:
        return "lv-entry"
    return f"lv-{'up' if rel > 0 else 'down'}-{round(abs(rel) * 100)}"


def _level_name(z: float, entry: float) -> str:
    rel = round(z - entry, 3)
    if abs(rel) < 1e-6:
        return "Entry level"
    return f"Level {rel:+.2f} m from entry"


def _bar_rect(bar: Bar, start: int, s0: int, s1: int, c0: int, c1: int) -> Rect:
    if bar.axis == "u":
        return Rect(start + s0, bar.cross0_dm + c0, start + s1, bar.cross0_dm + c1)
    return Rect(bar.cross0_dm + c0, start + s0, bar.cross0_dm + c1, start + s1)


def _overlap_dm2(a: Rect, b: Rect) -> int:
    """Area (dm²) shared by two rectangles."""
    du = min(a.u1, b.u1) - max(a.u0, b.u0)
    dv = min(a.v1, b.v1) - max(a.v0, b.v0)
    return du * dv if du > 0 and dv > 0 else 0


def _short(sid: str) -> str:
    return sid.removeprefix("sp-") if sid != EXTERIOR else "ext"


class _Builder:
    def __init__(
        self,
        m: Massing,
        sol: Solution,
        rooms: ProgramRooms,
        frame: DesignFrame,
        ground: Ground,
        program: SpaceProgram,
        site: Site,
        actor: Actor,
    ) -> None:
        self.m, self.sol, self.rooms, self.frame, self.ground = m, sol, rooms, frame, ground
        self.program, self.site, self.actor = program, site, actor
        self.entry_z = m.entry_elevation_m
        self.spaces: list[SpaceInfo] = []
        self.walls: list[WallSeg] = []
        self.openings: list[Opening] = []
        self.stairs: list[Stair] = []
        self.stairwells: list[Stairwell] = []
        self.issues: list[Issue] = []
        self.notes: list[str] = list(m.notes)
        self._ids: set[str] = set()

    # ---------------------------------------------------------------- spaces

    def level_of(self, bar: Bar) -> str:
        return _level_id(bar.elevation_m, self.entry_z)

    def add_space(self, info: SpaceInfo) -> None:
        self.spaces.append(info)

    def space(self, sid: str) -> SpaceInfo:
        return next(s for s in self.spaces if s.id == sid)

    def build_spaces(self) -> None:
        m, sol = self.m, self.sol
        stair_item = self.rooms.stair_item
        for bar in m.bars:
            start, length = sol.bar_start[bar.id], sol.bar_length[bar.id]
            corr = bar.row("corridor")
            hall = self.rooms.hall_item if bar.entry else None
            self.add_space(
                SpaceInfo(
                    id=f"sp-corridor-{bar.id}"
                    if hall is None
                    else "sp-" + hall.id.removeprefix("pi-"),
                    name=hall.name if hall else "Corridor",
                    function=hall.function if hall else S.CORRIDOR,
                    level_id=self.level_of(bar),
                    rect=_bar_rect(
                        bar, start, 0, length, corr.offset_dm, corr.offset_dm + corr.depth_dm
                    ),
                    kind="corridor",
                    bar_id=bar.id,
                    row_id=corr.id,
                    program_item_id=hall.id if hall else None,
                    zone_id=(hall.zone_id if hall else None) or "z-circulation",
                )
            )
        for pu in sol.units:
            bar = m.bar_of_row(pu.row_id)
            row = next(r for r in bar.rows if r.id == pu.row_id)
            start = sol.bar_start[bar.id]
            lv = self.level_of(bar)
            c_lo, c_hi = row.offset_dm, row.offset_dm + row.depth_dm
            corridor_high = row.side == "front"  # corridor lies at higher cross offset
            u = pu.unit
            if u.kind == "cluster":
                s = pu.start_dm
                for slot, wdm in zip(u.slots, pu.widths, strict=True):
                    if slot.stacked:
                        inner, outer = slot.rooms
                        d_in = self.sol.splits[pu.row_id, inner.space_id]
                        if corridor_high:
                            pieces = [(inner, c_hi - d_in, c_hi), (outer, c_lo, c_hi - d_in)]
                        else:
                            pieces = [(inner, c_lo, c_lo + d_in), (outer, c_lo + d_in, c_hi)]
                    else:
                        pieces = [(slot.rooms[0], c_lo, c_hi)]
                    for room, a, b in pieces:
                        self.add_space(
                            SpaceInfo(
                                id=room.space_id,
                                name=room.name,
                                function=room.function,
                                level_id=lv,
                                rect=_bar_rect(bar, start, s, s + wdm, a, b),
                                kind="room",
                                bar_id=bar.id,
                                row_id=row.id,
                                start_dm=s,
                                room=room,
                                program_item_id=room.item.id,
                                zone_id=room.item.zone_id,
                            )
                        )
                    s += wdm
            else:
                is_stair = u.kind == "stair"
                sid = f"sp-{u.kind}-{u.link_index}{u.side}"
                self.add_space(
                    SpaceInfo(
                        id=sid,
                        name="Stair" if is_stair else "Link hall",
                        function=S.STAIR if is_stair else S.CORRIDOR,
                        level_id=lv,
                        rect=_bar_rect(
                            bar, start, pu.start_dm, pu.start_dm + pu.width_dm, c_lo, c_hi
                        ),
                        kind=u.kind,
                        bar_id=bar.id,
                        row_id=row.id,
                        start_dm=pu.start_dm,
                        program_item_id=stair_item.id if is_stair and stair_item else None,
                        zone_id=(stair_item.zone_id if is_stair and stair_item else None)
                        or "z-circulation",
                    )
                )
        for i, link in enumerate(m.links):
            if link.kind == "row" and link.gap_dm:
                a, b = m.bar(link.a), m.bar(link.b)
                la = next(s for s in self.spaces if s.id.endswith(f"-{i}a") and s.kind != "room")
                self.add_space(
                    SpaceInfo(
                        id=f"sp-gallery-{i}",
                        name="Glazed gallery",
                        function=S.CORRIDOR,
                        level_id=self.level_of(a),
                        rect=Rect(la.rect.u0, a.cross1_dm, la.rect.u1, b.cross0_dm),
                        kind="gallery",
                        zone_id="z-circulation",
                    )
                )
        for rid, (fs, fw) in sorted(self.sol.fillers.items()):
            bar = m.bar_of_row(rid)
            row = next(r for r in bar.rows if r.id == rid)
            self.add_space(
                SpaceInfo(
                    id=f"sp-flex-{rid}",
                    name="Flexible space (not in program)",
                    function=S.STORAGE,
                    level_id=self.level_of(bar),
                    rect=_bar_rect(
                        bar,
                        self.sol.bar_start[bar.id],
                        fs,
                        fs + fw,
                        row.offset_dm,
                        row.offset_dm + row.depth_dm,
                    ),
                    kind="filler",
                    bar_id=bar.id,
                    row_id=rid,
                    start_dm=fs,
                )
            )

    # ----------------------------------------------------------------- walls

    def build_walls(self) -> None:
        by_level: dict[str, list[SpaceInfo]] = {}
        for s in self.spaces:
            by_level.setdefault(s.level_id, []).append(s)
        for lv in sorted(by_level):
            segs: list[WallSeg] = []
            for orient in ("h", "v"):
                lines: dict[int, list[tuple[int, int, str, str]]] = {}
                for s in by_level[lv]:
                    r = s.rect
                    if orient == "h":
                        lines.setdefault(r.v0, []).append((r.u0, r.u1, "pos", s.id))
                        lines.setdefault(r.v1, []).append((r.u0, r.u1, "neg", s.id))
                    else:
                        lines.setdefault(r.u0, []).append((r.v0, r.v1, "pos", s.id))
                        lines.setdefault(r.u1, []).append((r.v0, r.v1, "neg", s.id))
                for c in sorted(lines):
                    edges = lines[c]
                    pts = sorted({p for e in edges for p in e[:2]})
                    run: WallSeg | None = None
                    for p, q in zip(pts, pts[1:], strict=False):
                        neg = next(
                            (e[3] for e in edges if e[2] == "neg" and e[0] <= p and q <= e[1]), None
                        )
                        pos = next(
                            (e[3] for e in edges if e[2] == "pos" and e[0] <= p and q <= e[1]), None
                        )
                        if neg is None and pos is None:
                            if run:
                                segs.append(run)
                                run = None
                            continue
                        if run and run.b == p and run.neg == neg and run.pos == pos:
                            run.b = q
                        else:
                            if run:
                                segs.append(run)
                            run = WallSeg(lv, orient, c, p, q, neg, pos)
                    if run:
                        segs.append(run)
            suffix = lv.removeprefix("lv-")
            for n, seg in enumerate(segs, start=1):
                seg.id = f"w-{suffix}-{n:03d}"
                self._classify(seg)
                self._stairwell_wall(seg)
            self.walls.extend(segs)

    def _seg_points(self, seg: WallSeg) -> tuple[tuple[int, int], tuple[int, int]]:
        if seg.orient == "h":
            return (seg.a, seg.c), (seg.b, seg.c)
        return (seg.c, seg.a), (seg.c, seg.b)

    def _classify(self, seg: WallSeg) -> None:
        if seg.neg is not None and seg.pos is not None:
            seg.kind, seg.thickness = WallKind.INTERIOR, INTERIOR_WALL_M
            return
        seg.thickness = EXTERIOR_WALL_M
        du, dv = seg.outward()
        (u0, v0), (u1, v1) = self._seg_points(seg)
        n = max(2, seg.length // 10 + 1)
        samples = [
            (
                from_dm(u0 + (u1 - u0) * (i + 0.5) / n) + du * 0.6,
                from_dm(v0 + (v1 - v0) * (i + 0.5) / n) + dv * 0.6,
            )
            for i in range(n)
        ]
        z = next(lv.elevation_m for lv in self.levels if lv.id == seg.level_id)
        mid = samples[len(samples) // 2]
        probe = (mid[0] - du * 0.35, mid[1] - dv * 0.35)  # 0.25 m outside the face
        for o in self.spaces:
            if o.level_id == seg.level_id or not (
                from_dm(o.rect.u0) < probe[0] < from_dm(o.rect.u1)
                and from_dm(o.rect.v0) < probe[1] < from_dm(o.rect.v1)
            ):
                continue
            z_other = next(lv.elevation_m for lv in self.levels if lv.id == o.level_id)
            if z_other + FLOOR_TO_FLOOR_M > z + 0.05:
                # The neighbour's rooms or substructure stand against this face.
                seg.kind, seg.party = WallKind.INTERIOR, True
                return
        g = self.ground.mean_along(samples)
        seg.retained_m = 0.0 if g is None else max(0.0, g - z)
        seg.kind = WallKind.RETAINING if seg.retained_m > RETAINING_M else WallKind.EXTERIOR

    def wall_model(self, seg: WallSeg) -> Wall:
        (u0, v0), (u1, v1) = self._seg_points(seg)
        material = {
            WallKind.RETAINING: "m-retaining",
            WallKind.EXTERIOR: "m-ext-wall",
        }.get(seg.kind, "m-ext-wall" if seg.party else "m-int-wall")
        return Wall(
            id=seg.id,
            level_id=seg.level_id,
            start=self.frame.to_local(u0, v0),
            end=self.frame.to_local(u1, v1),
            thickness_m=seg.thickness,
            height_m=seg.height_m,
            base_offset_m=seg.base_offset_m,
            kind=seg.kind,
            material_id=material,
        )

    # -------------------------------------------------------------- openings

    def _new_id(self, base: str) -> str:
        base = base[:60].rstrip("-_")
        ident, n = base, 2
        while ident in self._ids:
            ident = f"{base[:57]}-{n}"
            n += 1
        self._ids.add(ident)
        return ident

    def _walls_between(self, level: str, a: str, b: str | None) -> list[WallSeg]:
        return [
            w
            for w in self.walls
            if w.level_id == level
            and w.sides() == {a, b}
            and (b is not None or not w.party and w.kind is not WallKind.RETAINING)
        ]

    def _fit(self, seg: WallSeg, width: int, clear: int, ends: bool = False) -> int | None:
        """Offset (dm, from seg.a) for an opening of ``width`` avoiding used spans.

        Openings are centred, or with ``ends`` placed nearest a wall end, so the rest of
        the wall stays one run (S10-09: a kitchen's counter needs 3 m of plain wall).
        """
        lo, hi = clear, seg.length - clear - width
        if hi < lo:
            return None
        centre = (seg.length - width) // 2
        key = (lambda o: (min(o - lo, hi - o), o)) if ends else (lambda o: (abs(o - centre), o))
        candidates = sorted(range(lo, hi + 1), key=key)
        for off in candidates:
            if all(off + width + 1 <= a or off >= b + 1 for a, b in seg.used):
                return off
        return None

    def place(
        self,
        level: str,
        a: str,
        b: str | None,
        kind: OpeningKind,
        width_m: float,
        *,
        min_width_m: float = 0.7,
        clear_m: float = 0.3,
        height_m: float = DOOR_H_M,
        sill_m: float = 0.0,
        operation: Operation = Operation.NONE,
        opens_into: str | None = None,
        prefer: tuple[int, int] | None = None,
        material: str | None = None,
        prefix: str = "d",
        host: WallSeg | None = None,
        require_direction: bool = False,
    ) -> Opening | None:
        walls = [host] if host is not None else self._walls_between(level, a, b)
        # Passable openings keep to the corners of a kitchen's walls (S10-09).
        ends = kind is not OpeningKind.WINDOW and any(
            sid is not None and self.space(sid).function is S.KITCHEN for sid in (a, b)
        )
        if prefer is not None:
            if require_direction:
                walls = [w for w in walls if w.outward() == prefer]
            walls.sort(key=lambda w: (w.outward() != prefer, -w.length, w.id))
        else:
            walls.sort(key=lambda w: (-w.length, w.id))
        for seg in walls:
            width = round(width_m * 10)
            clear = round(clear_m * 10)
            off = self._fit(seg, width, clear, ends)
            while off is None and width > round(min_width_m * 10):
                width -= 1
                off = self._fit(seg, width, clear, ends)
            if off is None and clear > 1:
                clear = 1
                width = round(min_width_m * 10)
                off = self._fit(seg, width, clear, ends)
            if off is None:
                continue
            seg.used.append((off, off + width))
            other = b if b is not None else EXTERIOR
            op = Opening(
                id=self._new_id(f"{prefix}-{_short(a)}-{_short(other)}"),
                kind=kind,
                host_wall_id=seg.id,
                offset_m=from_dm(off),
                width_m=from_dm(width),
                height_m=height_m,
                sill_m=sill_m,
                connects=(a, other),
                operation=operation,
                opens_into=opens_into,
                material_id=material,
            )
            self.openings.append(op)
            return op
        return None

    def _issue(self, ident: str, title: str, severity: Severity, subjects: list[str]) -> None:
        if any(i.id == ident for i in self.issues):
            return
        self.issues.append(
            Issue(
                id=ident, title=title, severity=severity, subject_ids=subjects, raised_by=self.actor
            )
        )

    def door(self, level: str, room: str, other: str | None, width: float, **kw) -> None:
        kind = kw.pop("kind", OpeningKind.DOOR)
        op = kw.pop(
            "operation", Operation.SWING_LEFT if kind is OpeningKind.DOOR else Operation.NONE
        )
        made = self.place(
            level,
            room,
            other,
            kind,
            width,
            operation=op,
            material="m-door" if kind is OpeningKind.DOOR else None,
            **kw,
        )
        if made is None:
            other_name = other or EXTERIOR
            self._issue(
                f"iss-no-door-{_short(room)}-{_short(other_name)}"[:64].rstrip("-"),
                f"No wall long enough for an opening between {room} and {other_name}",
                Severity.BLOCKING,
                [room] + ([other] if other else []),
            )

    def build_openings(self) -> None:
        corridor_of = {s.bar_id: s.id for s in self.spaces if s.kind == "corridor"}
        entry_bar = next(b for b in self.m.bars if b.entry)
        entry_level = self.level_of(entry_bar)
        road = (0, -1)
        er = self.rooms.entry_room
        if er is not None and any(s.id == er.space_id for s in self.spaces):
            self.door(
                entry_level,
                er.space_id,
                None,
                1.0,
                opens_into=er.space_id,
                prefer=road,
                prefix="d-front",
            )
        else:
            self.door(
                entry_level,
                corridor_of[entry_bar.id],
                None,
                1.0,
                clear_m=0.1,
                opens_into=corridor_of[entry_bar.id],
                prefix="d-front",
            )
        for pu in self.sol.units:
            u = pu.unit
            bar = self.m.bar_of_row(pu.row_id)
            lv, corr = self.level_of(bar), corridor_of[bar.id]
            if u.kind == "cluster":
                cl = u.cluster
                assert cl is not None
                slot_of = {r.space_id: s for s in cl.slots for r in s.rooms}
                for room in cl.members:
                    sid = room.space_id
                    needs = room is cl.anchor or sid in self.rooms.hall_connected
                    if not needs and not touches_corridor(slot_of[sid], room):
                        continue
                    if not needs and is_dependent(room, cl.connections):
                        continue
                    if not needs and len(cl.members) > 1:
                        continue
                    if room.function is S.ENTRY:
                        self.door(lv, sid, corr, 1.2, kind=OpeningKind.OPENING, min_width_m=0.9)
                        continue
                    width = (
                        1.0
                        if room.item.accessible
                        else (0.8 if room.function in DEPENDENT_FUNCTIONS | {S.MECHANICAL} else 0.9)
                    )
                    self.door(lv, sid, corr, width, opens_into=sid)
                for a, b in cl.connections:
                    fa, fb = self.space(a).function, self.space(b).function
                    if fa in OPEN_PLAN_FUNCTIONS and fb in OPEN_PLAN_FUNCTIONS:
                        self.door(
                            lv, a, b, 2.4, kind=OpeningKind.OPENING, min_width_m=0.9, prefix="o"
                        )
                    else:
                        dep = b if fb in DEPENDENT_FUNCTIONS else a
                        self.door(lv, a, b, 0.8, opens_into=dep)
                for room in cl.members:
                    if room.function is S.GARAGE:
                        bays = max(1, round(pu.widths[0] / 30))
                        made = self.place(
                            lv,
                            room.space_id,
                            None,
                            OpeningKind.DOOR,
                            2.6 * bays,
                            min_width_m=2.4,
                            operation=Operation.SLIDING,
                            height_m=2.2,
                            prefer=road,
                            require_direction=True,
                            material="m-door",
                            prefix="d-garage",
                        )
                        if made is None:
                            self._issue(
                                f"iss-garage-access-{_short(room.space_id)}",
                                "No vehicle opening fits on the garage's road-facing wall",
                                Severity.BLOCKING,
                                [room.space_id],
                            )
            else:
                sid = f"sp-{u.kind}-{u.link_index}{u.side}"
                self.door(lv, sid, corr, 1.2, kind=OpeningKind.OPENING, min_width_m=0.8, prefix="o")
        for s in self.spaces:
            if s.kind == "filler":
                self.door(s.level_id, s.id, corridor_of[s.bar_id], 0.8, opens_into=s.id)
        for i, link in enumerate(self.m.links):
            a, b = self.m.bar(link.a), self.m.bar(link.b)
            lv_a, la, g = self.level_of(a), f"sp-link-{i}a", f"sp-gallery-{i}"
            hall = {"kind": OpeningKind.OPENING, "min_width_m": 0.8, "prefix": "o"}
            if link.kind == "row" and link.gap_dm:
                self.door(lv_a, la, g, 1.2, **hall)
            if abs(a.elevation_m - b.elevation_m) > 1e-6:
                continue  # joined by a stair instead
            if link.kind == "end":
                self.door(lv_a, la, corridor_of[b.id], 1.2, **hall)
            elif link.kind == "row":
                self.door(lv_a, g if link.gap_dm else la, f"sp-link-{i}b", 1.2, **hall)
        self.open_stairwells()
        self._build_relation_doors()

    def _build_relation_doors(self) -> None:
        """Place doors for connected relations between touching spaces not covered by clusters."""
        connected_pairs: set[frozenset[str]] = {
            frozenset(o.connects) for o in self.openings if len(o.connects) == 2
        }
        for adj in self.program.adjacencies:
            if adj.kind is not AdjacencyKind.CONNECTED:
                continue
            if adj.a == EXTERIOR or adj.b == EXTERIOR:
                target = adj.a if adj.b == EXTERIOR else adj.b
                target_spaces = [s.id for s in self.spaces if s.program_item_id == target]
                for sid in target_spaces:
                    if any(sid in o.connects and EXTERIOR in o.connects for o in self.openings):
                        continue
                    sp = self.space(sid)
                    self.place(
                        sp.level_id,
                        sid,
                        None,
                        OpeningKind.DOOR,
                        0.9,
                        min_width_m=0.8,
                        prefix="d-ext",
                    )
                continue

            a_spaces = [s.id for s in self.spaces if s.program_item_id == adj.a]
            b_spaces = [s.id for s in self.spaces if s.program_item_id == adj.b]
            for a in a_spaces:
                for b in b_spaces:
                    pair = frozenset((a, b))
                    if pair in connected_pairs:
                        continue
                    sa, sb = self.space(a), self.space(b)
                    if sa.level_id != sb.level_id:
                        continue
                    if not self._walls_between(sa.level_id, a, b):
                        continue
                    fa, fb = sa.function, sb.function
                    if fa in OPEN_PLAN_FUNCTIONS and fb in OPEN_PLAN_FUNCTIONS:
                        door = self.place(
                            sa.level_id,
                            a,
                            b,
                            OpeningKind.OPENING,
                            2.4,
                            min_width_m=0.9,
                            prefix="o",
                        )
                    else:
                        dep = b if fb in DEPENDENT_FUNCTIONS else a
                        door = self.place(
                            sa.level_id,
                            a,
                            b,
                            OpeningKind.DOOR,
                            0.8,
                            min_width_m=0.7,
                            opens_into=dep,
                        )
                    if door is not None:
                        connected_pairs.add(pair)

    def build_windows(self) -> None:
        big = {S.LIVING, S.FAMILY, S.RECEPTION, S.DINING, S.KITCHEN}
        mid = {S.BEDROOM, S.GUEST_SUITE, S.STUDY, S.PLAY, S.GYM, S.PRAYER}
        wet = {S.BATHROOM, S.WC, S.ABLUTION}
        for s in self.spaces:
            if s.kind in ("filler", "stairwell") or s.function in (
                S.GARAGE,
                S.MECHANICAL,
                S.STORAGE,
            ):
                continue
            if s.room is not None and not s.room.wants_daylight:
                continue
            walls = sorted(
                (w for w in self._walls_between(s.level_id, s.id, None)),
                key=lambda w: (-w.length, w.id),
            )
            count = 2 if s.function in big or s.kind == "gallery" else 1
            for seg in walls[:count]:
                length = from_dm(seg.length)
                if s.kind == "gallery":
                    width, h, sill = min(4.0, max(1.2, 0.6 * length)), 2.1, 0.0
                elif s.function in big:
                    width, h, sill = min(3.0, max(1.2, 0.45 * length)), 1.5, 0.9
                elif s.function in mid:
                    width, h, sill = min(1.8, max(1.0, 0.4 * length)), 1.4, 0.9
                elif s.function in wet:
                    width, h, sill = 0.6, 0.6, 1.5
                else:
                    width, h, sill = 1.0, 1.2, 0.9
                self.place(
                    s.level_id,
                    s.id,
                    None,
                    OpeningKind.WINDOW,
                    width,
                    min_width_m=0.6,
                    height_m=h,
                    sill_m=sill,
                    operation=Operation.TILT_TURN,
                    material="m-glass",
                    prefix="win",
                    host=seg,
                )

    # ---------------------------------------------------------------- stairs

    def build_stairs(self) -> None:
        for i, link in enumerate(self.m.links):
            a, b = self.m.bar(link.a), self.m.bar(link.b)
            rise = b.elevation_m - a.elevation_m
            if abs(rise) < 1e-6:
                continue
            n, riser, run = stair_risers(rise)
            if link.kind == "stacked":
                sa, sb = self.space(f"sp-stair-{i}a"), self.space(f"sp-stair-{i}b")
                r = sa.rect
                kind = StairKind.U_SHAPED
                # Lanes keep half an exterior wall plus tolerance (0.2 m) from the walls.
                width = min(1.1, (from_dm(r.w if a.axis == "u" else r.h) - 0.4) / 2)
                low, high = (sa, sb) if a.elevation_m < b.elevation_m else (sb, sa)
                # Two lanes run away from the corridor side, where the upper landing stays
                # in the floor slab, and turn on a half landing (ADR 0023).
                row = self.m.bar(high.bar_id).row(high.row_id.rsplit("-", 1)[-1])
                strip, front = LANDING_STRIP_DM, row.side == "front"
                if a.axis == "u":
                    lo, hi, c0, c1 = r.v0 + 2, r.v1 - 2, r.u0 + 2, r.u1 - 2
                    near = r.v1 - strip if front else r.v0 + strip
                else:
                    lo, hi, c0, c1 = r.u0 + 2, r.u1 - 2, r.v0 + 2, r.v1 - 2
                    near = r.u1 - strip if front else r.u0 + strip
                far = lo if front else hi
                pts, fits = u_layout(near, far, c0, c1, width * 10, n)
                if not fits:
                    self._issue(
                        f"iss-stair-landing-{i}",
                        f"Stair {i} has no room for a {width:.2f} m half landing",
                        Severity.BLOCKING,
                        [],
                    )
                lo, hi = sorted((near, far))
                if a.axis == "u":
                    fp = self.frame.rect(c0, lo, c1, hi)
                    walking_line = [self.frame.to_local(c, x) for x, c in pts]
                else:
                    fp = self.frame.rect(lo, c0, hi, c1)
                    walking_line = [self.frame.to_local(x, c) for x, c in pts]
                landing_segments = [1]
            else:
                if link.kind == "end":
                    top_space = self.space(f"sp-stair-{i}a")
                    other = next(
                        s for s in self.spaces if s.kind == "corridor" and s.bar_id == b.id
                    )
                    boundary = a.cross1_dm
                elif link.gap_dm:
                    top_space = self.space(f"sp-gallery-{i}")
                    other = self.space(f"sp-stair-{i}b")
                    boundary = b.cross0_dm
                else:
                    top_space = self.space(f"sp-stair-{i}a")
                    other = self.space(f"sp-stair-{i}b")
                    boundary = a.cross1_dm
                half = math.ceil(run * 10 / 2)
                ref = other.rect if link.kind == "end" else top_space.rect
                depth_a = boundary - (top_space.rect.v0 if a.axis == "u" else top_space.rect.u0)
                depth_b = (other.rect.v1 if a.axis == "u" else other.rect.u1) - boundary
                lo = boundary - min(half, depth_a - 2)
                hi = boundary + min(half, depth_b - 2)
                if hi - lo < 2 * half:
                    self._issue(
                        f"iss-stair-run-{i}",
                        f"Stair {i} run is shorter than {run:.2f} m for a {abs(rise):.2f} m rise",
                        Severity.BLOCKING,
                        [],
                    )
                s0, s1 = (ref.u0, ref.u1) if a.axis == "u" else (ref.v0, ref.v1)
                inset = max(1, ((s1 - s0) - 11) // 2)
                if a.axis == "u":
                    fp = self.frame.rect(s0 + inset, lo, s1 - inset, hi)
                else:
                    fp = self.frame.rect(lo, s0 + inset, hi, s1 - inset)
                kind = StairKind.STRAIGHT
                width = from_dm((s1 - s0) - 2 * inset)
                landing_segments = []
                low, high = (
                    (top_space, other) if a.elevation_m < b.elevation_m else (other, top_space)
                )
                self.stairwells.append(
                    Stairwell(
                        i,
                        low.level_id,
                        high.level_id,
                        "v" if a.axis == "u" else "u",
                        boundary,
                        lo,
                        hi,
                        s0 + inset - 1,
                        s1 - inset + 1,
                        abs(rise),
                        a.elevation_m < b.elevation_m,
                        low.id,
                        high.id,
                    )
                )
                # Centre line of the flight, ordered bottom to top: top_space lies below
                # the boundary (the `lo` end), the other space above it (the `hi` end).
                mid = (s0 + s1) / 2
                ends = [lo, hi] if low is top_space else [hi, lo]
                walking_line = [
                    self.frame.to_local(mid, e) if a.axis == "u" else self.frame.to_local(e, mid)
                    for e in ends
                ]
            self.stairs.append(
                Stair(
                    id=f"st-{i}",
                    kind=kind,
                    from_level_id=low.level_id,
                    to_level_id=high.level_id,
                    footprint=fp,
                    bottom_space_id=low.id,
                    top_space_id=high.id,
                    width_m=width,
                    riser_count=n,
                    riser_height_m=round(riser, 4),
                    tread_depth_m=TREAD_M,
                    walking_line=walking_line,
                    landing_segments=landing_segments,
                )
            )

    def add_stairwell_spaces(self) -> None:
        """The two parts of each split-level stair volume (ADR 0023).

        Below the higher bar's floor the flight runs in a stairwell on the lower level; over
        the lower bar it rises in a stair hall on the higher level, whose roof replaces the
        lower bar's roof there. Where that level is already built over the region (stacked
        bars), the flight runs in the existing room instead.
        """
        for w in self.stairwells:
            lo_part, hi_part = (w.lo, w.boundary), (w.boundary, w.hi)
            below, over = (hi_part, lo_part) if w.lower_on_lo else (lo_part, hi_part)
            for part, sid, name, level, (p0, p1), stair_space in (
                ("below", w.below_id, "Stairwell", w.low_level, below, w.low_space),
                ("over", w.over_id, "Stair hall", w.high_level, over, w.high_space),
            ):
                r = w.rect(p0, p1)
                taken = [
                    o for o in self.spaces if o.level_id == level and _overlap_dm2(o.rect, r) > 0
                ]
                if not taken:
                    self.add_space(
                        SpaceInfo(
                            id=sid,
                            name=name,
                            function=S.STAIR,
                            level_id=level,
                            rect=r,
                            kind="stairwell",
                            zone_id=self.space(stair_space).zone_id,
                        )
                    )
                    w.created.add(sid)
                    w.joins[part] = sid
                elif len(taken) == 1 and _overlap_dm2(taken[0].rect, r) == _overlap_dm2(r, r):
                    w.joins[part] = taken[0].id
                else:
                    self._issue(
                        f"iss-stair-volume-{w.stair_index}-{part}",
                        f"Stair {w.stair_index} crosses into several rooms on {level}",
                        Severity.BLOCKING,
                        [o.id for o in taken],
                    )

    def open_stairwells(self) -> None:
        """A full-height opening across the bar boundary, exactly over each flight."""
        across = {"v": "h", "u": "v"}
        for w in self.stairwells:
            for part, level, stair_space in (
                ("below", w.low_level, w.low_space),
                ("over", w.high_level, w.high_space),
            ):
                other = w.joins.get(part)
                if other is None:
                    continue
                seg = next(
                    (
                        g
                        for g in self._walls_between(level, stair_space, other)
                        if g.orient == across[w.run_axis]
                        and g.c == w.boundary
                        and g.a <= w.c0
                        and w.c1 <= g.b
                    ),
                    None,
                )
                if seg is None:
                    self._issue(
                        f"iss-stair-opening-{w.stair_index}-{part}",
                        f"No boundary wall to open for stair {w.stair_index} on {level}",
                        Severity.BLOCKING,
                        [stair_space, other],
                    )
                    continue
                seg.used.append((w.c0 - seg.a, w.c1 - seg.a))
                self.openings.append(
                    Opening(
                        id=self._new_id(f"o-{_short(stair_space)}-{_short(other)}"),
                        kind=OpeningKind.OPENING,
                        host_wall_id=seg.id,
                        offset_m=from_dm(w.c0 - seg.a),
                        width_m=from_dm(w.c1 - w.c0),
                        height_m=seg.height_m,
                        connects=(stair_space, other),
                    )
                )

    def _stairwell_wall(self, seg: WallSeg) -> None:
        """Height and kind of a stairwell's outer wall: it does not span a plain storey."""
        w = next((x for x in self.stairwells if {seg.neg, seg.pos} & x.created), None)
        if w is None or (seg.neg is not None and seg.pos is not None):
            return
        z = next(lv.elevation_m for lv in self.levels if lv.id == seg.level_id)
        if seg.level_id == w.low_level:
            # From the lower floor to the higher floor slab's underside.
            seg.base_offset_m, seg.height_m = 0.0, round(w.rise_m - SLAB_M, 4)
        else:
            # From the lower roof slab's underside to the higher storey's wall head.
            seg.base_offset_m = round(FLOOR_TO_FLOOR_M - SLAB_M - w.rise_m, 4)
            seg.height_m = round(WALL_HEIGHT_M - seg.base_offset_m, 4)
        (u0, v0), (u1, v1) = self._seg_points(seg)
        ground = self.ground.mean_line((from_dm(u0), from_dm(v0)), (from_dm(u1), from_dm(v1)))
        base_z = z + seg.base_offset_m
        seg.party = False
        seg.thickness = EXTERIOR_WALL_M
        seg.retained_m = 0.0 if ground is None else max(0.0, ground - base_z)
        seg.kind = WallKind.RETAINING if seg.retained_m > RETAINING_M else WallKind.EXTERIOR

    # ----------------------------------------------------------------- model

    def build(self, model_id: str, name: str, site_ref, program_ref) -> HouseModel:
        elevations = sorted({b.elevation_m for b in self.m.bars})
        self.levels = [
            Level(
                id=_level_id(z, self.entry_z),
                name=_level_name(z, self.entry_z),
                elevation_m=z,
                floor_to_floor_m=FLOOR_TO_FLOOR_M,
            )
            for z in elevations
        ]
        self.build_spaces()
        self.build_stairs()
        self.add_stairwell_spaces()
        self.build_walls()
        self.build_openings()
        self.build_windows()
        spaces = [
            Space(
                id=s.id,
                name=s.name,
                function=s.function,
                level_id=s.level_id,
                boundary=self.frame.rect(s.rect.u0, s.rect.v0, s.rect.u1, s.rect.v1),
                program_item_id=s.program_item_id,
                zone_id=s.zone_id,
                floor_material_id="m-floor",
            )
            for s in self.spaces
        ]
        zones = self._zones(spaces)
        for sp in spaces:
            if sp.zone_id is not None and sp.zone_id not in {z.id for z in zones}:
                sp.zone_id = None
        walls = [self.wall_model(w) for w in self.walls]
        model = HouseModel(
            id=model_id,
            name=name,
            coordinate_system_id=self.site.coordinates.local.id,  # type: ignore[union-attr]
            site_ref=site_ref,
            program_ref=program_ref,
            levels=self.levels,
            spaces=spaces,
            walls=walls,
            openings=self.openings,
            slabs=self._slabs(),
            ceilings=[
                Ceiling(
                    id=f"ceil-{_short(s.id)}"[:64],
                    space_id=s.id,
                    height_m=CEILING_M,
                    material_id="m-int-wall",
                )
                for s in self.spaces
                if s.kind != "stair"
            ],
            stairs=self.stairs,
            zones=zones,
            relationships=self._relationships(),
            materials=list(MATERIALS),
            assumptions=self._assumptions(),
            issues=self._issues(),
        )
        return with_fixtures(model, self.actor)

    def _zones(self, spaces: list[Space]) -> list[Zone]:
        program_zones = {z.id: z for z in self.program.zones}
        used: dict[str, list[str]] = {}
        for sp in spaces:
            if sp.zone_id:
                used.setdefault(sp.zone_id, []).append(sp.id)
        out = []
        for zid in sorted(used):
            if zid in program_zones:
                pz = program_zones[zid]
                out.append(Zone(id=zid, name=pz.name, privacy=pz.privacy, space_ids=used[zid]))
            elif zid == "z-circulation":
                out.append(
                    Zone(
                        id=zid,
                        name="Circulation",
                        privacy=Privacy.SEMI_PRIVATE,
                        space_ids=used[zid],
                    )
                )
        return out

    def _slabs(self) -> list[Slab]:
        out: list[Slab] = []
        polys = {}
        for lv in self.levels:
            rects = [s.rect for s in self.spaces if s.level_id == lv.id]
            polys[lv.id] = unary_union([box(r.u0, r.v0, r.u1, r.v1) for r in rects])
        for lv in self.levels:
            above = [polys[o.id] for o in self.levels if o.elevation_m > lv.elevation_m]
            roof = polys[lv.id].difference(unary_union(above)) if above else polys[lv.id]
            floor = polys[lv.id]
            for stair in self.stairs:
                if stair.to_level_id != lv.id:
                    continue
                # Canonical floor slabs must leave a real opening over the flight.
                # Retain a landing on the corridor side of a stacked U stair.
                # Snap back to the decimetre grid the flight was built on: frame round-trip
                # noise would leave slivers against stairwell edges (ADR 0023).
                flight = ShapelyPolygon(
                    [
                        tuple(round(v * 10) for v in self.frame.to_design(xy))
                        for xy in stair.footprint.outer
                    ]
                )
                if stair.kind is StairKind.U_SHAPED:
                    top = self.space(stair.top_space_id)
                    row = self.m.bar_of_row(top.row_id).row(top.row_id.rsplit("-", 1)[-1])
                    r = top.rect
                    landing = math.ceil(stair.width_m * 10)
                    bar = self.m.bar(top.bar_id)
                    if bar.axis == "u":
                        region = (
                            box(r.u0, r.v1 - landing, r.u1, r.v1)
                            if row.side == "front"
                            else box(r.u0, r.v0, r.u1, r.v0 + landing)
                        )
                    else:
                        region = (
                            box(r.u1 - landing, r.v0, r.u1, r.v1)
                            if row.side == "front"
                            else box(r.u0, r.v0, r.u0 + landing, r.v1)
                        )
                    flight = flight.difference(region)
                floor = floor.difference(flight)
            for kind, geom, offset in (
                (SlabKind.FLOOR, floor, 0.0),
                (SlabKind.ROOF, roof, FLOOR_TO_FLOOR_M),
            ):
                parts = [g for g in getattr(geom, "geoms", [geom]) if g.area >= 50]
                for k, part in enumerate(parts, start=1):
                    part = part.simplify(0)
                    ring = [
                        self.frame.to_local(round(x), round(y))
                        for x, y in part.exterior.coords[:-1]
                    ]
                    holes = [
                        [self.frame.to_local(round(x), round(y)) for x, y in h.coords[:-1]]
                        for h in part.interiors
                    ]
                    suffix = f"-{k}" if len(parts) > 1 else ""
                    out.append(
                        Slab(
                            id=f"slab-{kind.value}-{lv.id.removeprefix('lv-')}{suffix}",
                            level_id=lv.id,
                            kind=kind,
                            boundary=Polygon2D(outer=ring, holes=holes),
                            thickness_m=SLAB_M,
                            top_offset_m=offset,
                            material_id="m-slab",
                        )
                    )
        return out

    def _relationships(self) -> list[SpaceRelationship]:
        ids = {s.id for s in self.spaces}
        hall_space = next(
            (
                s.id
                for s in self.spaces
                if s.program_item_id
                and self.rooms.hall_item
                and s.program_item_id == self.rooms.hall_item.id
            ),
            None,
        )
        first: dict[str, str] = {}
        for s in self.spaces:
            if s.program_item_id and s.program_item_id not in first:
                first[s.program_item_id] = s.id
        if hall_space and self.rooms.hall_item:
            first[self.rooms.hall_item.id] = hall_space
        K = AdjacencyKind
        mapping = {
            K.CONNECTED: RelationshipKind.CONNECTED,
            K.ADJACENT: RelationshipKind.ADJACENT,
            K.VISUAL: RelationshipKind.VISUAL,
            K.SEPARATED: RelationshipKind.SEPARATED,
            K.ACOUSTIC_SEPARATION: RelationshipKind.SEPARATED,
        }
        out = []
        for adj in self.program.adjacencies:
            a, b = first.get(adj.a), first.get(adj.b)
            if a is None or b is None or adj.kind not in mapping or a not in ids or b not in ids:
                continue
            out.append(
                SpaceRelationship(
                    id=f"rel-{adj.id.removeprefix('adj-')}"[:64].rstrip("-"),
                    a=a,
                    b=b,
                    kind=mapping[adj.kind],
                    requirement_id=adj.id,
                )
            )
        return out

    def _assumptions(self) -> list[Assumption]:
        level_ids = [lv.id for lv in self.levels]
        stair_ids = [st.id for st in self.stairs]
        A = Assumption
        out = [
            A(
                id="asm-gen-centerlines",
                statement="Room areas are measured to wall centerlines; "
                "net floor areas are smaller.",
                basis="canonical model convention (DOMAIN_MODEL.md)",
                made_by=self.actor,
            ),
            A(
                id="asm-gen-levels",
                statement=f"Floor-to-floor height {FLOOR_TO_FLOOR_M:g} m; "
                f"split levels step in half storeys of {HALF_STOREY_M:g} m; walls "
                f"{WALL_HEIGHT_M:g} m high.",
                basis="typical values for a first layout, not a regulation",
                affects=level_ids,
                confirm_with="architect",
                made_by=self.actor,
            ),
            A(
                id="asm-gen-walls",
                statement=f"Exterior and retaining walls {EXTERIOR_WALL_M:g} m, "
                f"partitions {INTERIOR_WALL_M:g} m thick; no structural design has been done.",
                basis="typical thicknesses for a first layout",
                confirm_with="structural engineer",
                made_by=self.actor,
            ),
            A(
                id="asm-gen-frame",
                statement=f"Plan grid: {self.frame.basis}.",
                basis="generator design frame",
                made_by=self.actor,
            ),
        ]
        for k, note in enumerate(self.notes, start=1):
            out.append(
                A(
                    id=f"asm-gen-note-{k}",
                    statement=note,
                    basis="massing strategy",
                    affects=level_ids,
                    made_by=self.actor,
                )
            )
        if stair_ids:
            out.append(
                A(
                    id="asm-gen-stairs",
                    statement="Stair risers at most 0.18 m with 0.28 m goings; "
                    "typical comfortable geometry, not checked against any code.",
                    basis="typical stair proportions",
                    affects=stair_ids,
                    confirm_with="architect",
                    made_by=self.actor,
                )
            )
            if self.rooms.stair_item is None:
                out.append(
                    A(
                        id="asm-gen-stair-added",
                        statement="The program has no stair; this concept "
                        "adds stair spaces because it uses more than one level.",
                        basis="strategy needs vertical circulation",
                        affects=stair_ids,
                        confirm_with="owner",
                        made_by=self.actor,
                    )
                )
        if any(s.function is S.GARAGE for s in self.spaces):
            out.append(
                A(
                    id="asm-gen-garage-depth",
                    statement=f"A garage needs at least "
                    f"{from_dm(GARAGE_DEPTH_DM):g} m depth for a car.",
                    basis="typical car length plus clearance; not in the program",
                    confirm_with="owner",
                    made_by=self.actor,
                )
            )
        fillers = [s.id for s in self.spaces if s.kind == "filler"]
        if fillers:
            out.append(
                A(
                    id="asm-gen-flex",
                    statement="Rows are closed with flexible spaces that are not "
                    "in the program (storage, or space to give back).",
                    basis="solver closes every row of the massing",
                    affects=fillers,
                    confirm_with="owner",
                    made_by=self.actor,
                )
            )
        env = self.site.buildable_envelope
        if env is None:
            out.append(
                A(
                    id="asm-gen-envelope",
                    statement="No buildable envelope is recorded (setbacks, "
                    "coverage and height limits unknown); the plan is only kept inside the parcel "
                    "boundary, which is not the buildable area.",
                    basis="site has no envelope",
                    status=Epistemic.UNKNOWN,
                    confirm_with="local planning authority",
                    made_by=self.actor,
                )
            )
        else:
            out.append(
                A(
                    id="asm-gen-envelope",
                    statement=f"The plan is kept inside the buildable envelope ({env.basis}).",
                    basis=f"site envelope, status {env.status.value}",
                    status=env.status
                    if env.status is not Epistemic.VERIFIED_FACT
                    else Epistemic.ASSUMPTION,
                    confirm_with="local planning authority",
                    made_by=self.actor,
                )
            )
        if self.ground.known:
            out.append(
                A(
                    id="asm-gen-terrain",
                    statement="Level elevations, earth contact and retaining "
                    "walls are inferred by linear interpolation of the surveyed points; ground "
                    "between survey points is not verified.",
                    basis="survey TIN",
                    status=Epistemic.INFERENCE,
                    affects=level_ids,
                    confirm_with="surveyor",
                    made_by=self.actor,
                )
            )
        return out

    def _issues(self) -> list[Issue]:
        retaining = [w.id for w in self.walls if w.kind is WallKind.RETAINING]
        if retaining:
            self._issue(
                "iss-hillside-engineering",
                "Retaining walls, excavation, slope drainage and foundations need geotechnical "
                "and structural engineering; nothing here is engineered.",
                Severity.WARNING,
                retaining,
            )
        if self.site.buildable_envelope is None:
            self._issue(
                "iss-envelope-unknown",
                "Buildable envelope (setbacks, coverage, height limit) is unknown",
                Severity.WARNING,
                [],
            )
        return self.issues


def assemble(
    m: Massing,
    sol: Solution,
    rooms: ProgramRooms,
    frame: DesignFrame,
    ground: Ground,
    program: SpaceProgram,
    site: Site,
    *,
    model_id: str,
    name: str,
    site_ref: ArtifactRef | None,
    program_ref: ArtifactRef | None,
    actor: Actor,
) -> Assembly:
    b = _Builder(m, sol, rooms, frame, ground, program, site, actor)
    model = b.build(model_id, name, site_ref, program_ref)
    return Assembly(model=model, spaces=b.spaces, walls=b.walls, notes=b.notes)
