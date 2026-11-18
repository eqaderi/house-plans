"""Enclosure: the walls, openings, slabs and ceilings derived around the Spaces of a plan.

Both assemblers (bars and 2D placement) reduce a solved layout to named rectangles per
Level, each with a function and a Zone, on the design grid (decimetres). Enclosure derives
everything that encloses them from those rectangles and the terrain (ADR 0031):

- Walls: every wall segment has exactly one Space (or the outside) on each side, so an
  opening placed inside a wall lies between the two Spaces it claims to connect. Exterior
  faces are classified with the terrain: a face with ground well above its floor is a
  retaining wall; a face against a neighbour on another Level is a party wall; a
  terrace's open edge is a parapet.
- Openings: doors and windows are fitted into those walls without overlap, at least
  their minimum width, with the width-shrink fit and corner doors for kitchens and
  garages, and never across a face with another Space just beyond it.
- Slabs, ceilings, Zones and relationships: a floor slab per Level with a void over each
  flight arriving on it, a roof wherever no higher Level covers it, terrace slabs,
  ceilings except over stairs and terraces, the Zones the Spaces use and the plan's
  Space relationships.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import box
from shapely.ops import unary_union

from house_ai.constants.placement2d import (
    PARAPET_HEIGHT_M,
    PARAPET_THICKNESS_M,
    TERRACE_SLAB_THICKNESS_M,
)
from house_ai.constants.reviewer import DOOR_APPROACH_CLEAR_DM
from house_ai.domain.base import EXTERIOR
from house_ai.domain.geometry import Polygon2D
from house_ai.domain.integrity import OPENING_END_INSET_M, PROBE_BEYOND_FACE_M
from house_ai.domain.model import (
    STOREY_HEIGHT_M,
    Ceiling,
    Level,
    MaterialCategory,
    MaterialRef,
    Opening,
    OpeningKind,
    OpeningRole,
    Operation,
    PlanRelationship,
    RelationshipKind,
    Slab,
    SlabKind,
    Stair,
    Wall,
    WallKind,
    Zone,
)
from house_ai.domain.program import (
    ProgramZone,
    SpaceFunction,
    SpaceRelationship,
    SpaceRelationshipKind,
)

from .frame import DesignFrame, from_dm
from .stairs import SLAB_M

S = SpaceFunction
EXTERIOR_WALL_M = 0.30
INTERIOR_WALL_M = 0.15
WALL_HEIGHT_M = 2.8
DOOR_H_M = 2.1
CEILING_M = 2.7
#: Slab parts smaller than this (dm², 0.5 m²) are slivers, not slabs.
MIN_SLAB_PART_DM2 = 50
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


class Terrain(Protocol):
    """Ground elevation sampled in the design frame (metres); None where unknown."""

    def mean_along(self, pts: list[tuple[float, float]]) -> float | None: ...


@dataclass
class Rect:
    """An axis-aligned rectangle on the design grid, decimetres."""

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


@dataclass(frozen=True)
class EnclosedSpace:
    """One named rectangle on one Level: what Enclosure needs to know of a Space."""

    id: str
    level_id: str
    rect: Rect
    function: SpaceFunction
    zone_id: str | None = None
    program_item_id: str | None = None
    #: Whether the Space gets a ceiling; by default all but stairs and terraces do.
    ceiling: bool | None = None

    @property
    def has_ceiling(self) -> bool:
        if self.ceiling is not None:
            return self.ceiling
        return self.function not in (S.STAIR, S.TERRACE)


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
    #: Overrides for walls that do not span a plain storey, such as stairwells (ADR 0023).
    height_m: float = WALL_HEIGHT_M
    base_offset_m: float = 0.0

    @property
    def length(self) -> int:
        return self.b - self.a

    @property
    def length_m(self) -> float:
        return from_dm(self.length)

    def sides(self) -> set[str | None]:
        return {self.neg, self.pos}

    def outward(self) -> tuple[int, int]:
        """Direction from the space to the outside, for an exterior segment."""
        sign = -1 if self.neg is None else 1
        return (0, sign) if self.orient == "h" else (sign, 0)

    def points(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """Start and end on the design grid (dm)."""
        if self.orient == "h":
            return (self.a, self.c), (self.b, self.c)
        return (self.c, self.a), (self.c, self.b)


class Enclosure:
    """Everything that encloses the given rectangles, derived once on construction."""

    def __init__(
        self,
        levels: Sequence[Level],
        spaces: Sequence[EnclosedSpace],
        frame: DesignFrame,
        terrain: Terrain,
    ) -> None:
        self.levels = list(levels)
        self.spaces = list(spaces)
        self.frame = frame
        self.terrain = terrain
        self._elevation = {lv.id: lv.elevation_m for lv in self.levels}
        self._storey = {lv.id: lv.floor_to_floor_m or STOREY_HEIGHT_M for lv in self.levels}
        self.walls: list[WallSeg] = []
        self.openings: list[Opening] = []
        self._ids: set[str] = set()
        self._derive_walls()

    def space(self, sid: str) -> EnclosedSpace:
        return next(s for s in self.spaces if s.id == sid)

    # ----------------------------------------------------------------- walls

    def _derive_walls(self) -> None:
        by_level: dict[str, list[EnclosedSpace]] = {}
        for s in self.spaces:
            by_level.setdefault(s.level_id, []).append(s)
        terraces = {s.id for s in self.spaces if s.function is S.TERRACE}
        for lv in sorted(by_level):
            segs = _sweep(lv, by_level[lv])
            suffix = lv.removeprefix("lv-")
            for n, seg in enumerate(segs, start=1):
                seg.id = f"w-{suffix}-{n:03d}"
                self._classify(seg)
                if seg.sides() & terraces:
                    _terrace_edge(seg)
            self.walls.extend(segs)

    def _classify(self, seg: WallSeg) -> None:
        if seg.neg is not None and seg.pos is not None:
            seg.kind, seg.thickness = WallKind.INTERIOR, INTERIOR_WALL_M
            return
        seg.thickness = EXTERIOR_WALL_M
        du, dv = seg.outward()
        (u0, v0), (u1, v1) = seg.points()
        n = max(2, seg.length // 10 + 1)
        samples = [
            (
                from_dm(u0 + (u1 - u0) * (i + 0.5) / n) + du * 0.6,
                from_dm(v0 + (v1 - v0) * (i + 0.5) / n) + dv * 0.6,
            )
            for i in range(n)
        ]
        z = self._elevation[seg.level_id]
        mid = samples[len(samples) // 2]
        probe = (mid[0] - du * 0.35, mid[1] - dv * 0.35)  # 0.25 m outside the face
        for o in self.spaces:
            if o.level_id == seg.level_id or not (
                from_dm(o.rect.u0) < probe[0] < from_dm(o.rect.u1)
                and from_dm(o.rect.v0) < probe[1] < from_dm(o.rect.v1)
            ):
                continue
            if self._elevation[o.level_id] + self._storey[o.level_id] > z + 0.05:
                # The neighbour's rooms or substructure stand against this face.
                seg.kind, seg.party = WallKind.INTERIOR, True
                return
        self.retain(seg, z, self.terrain.mean_along(samples))

    @staticmethod
    def retain(seg: WallSeg, base_z: float, ground: float | None) -> None:
        """Classify an exterior face as retaining or not against the ground outside it."""
        seg.retained_m = 0.0 if ground is None else max(0.0, ground - base_z)
        seg.kind = WallKind.RETAINING if seg.retained_m > RETAINING_M else WallKind.EXTERIOR

    def walls_between(self, level: str, a: str, b: str | None) -> list[WallSeg]:
        """Walls between two Spaces, or a Space's exterior walls that can take an opening.

        Party and retaining walls never take an exterior opening.
        """
        return [
            w
            for w in self.walls
            if w.level_id == level
            and w.sides() == {a, b}
            and (b is not None or not w.party and w.kind is not WallKind.RETAINING)
        ]

    # -------------------------------------------------------------- openings

    def new_id(self, base: str) -> str:
        """A unique opening id from ``base``, numbered from 2 on a clash."""
        base = base[:60].rstrip("-_")
        ident, n = base, 2
        while ident in self._ids:
            ident = f"{base[:57]}-{n}"
            n += 1
        self._ids.add(ident)
        return ident

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
        require_direction: bool = False,
        material: str | None = None,
        prefix: str = "d",
        walls: Sequence[WallSeg] | None = None,
        role: OpeningRole | None = None,
    ) -> Opening | None:
        """Fit an opening between ``a`` and ``b`` (None: the outside), or return None.

        The candidate walls are ``walls`` or every wall between the two; the longest comes
        first, or those facing ``prefer`` (an outward direction) when given. An opening keeps
        ``clear_m`` from the wall ends and shrinks to ``min_width_m`` before a wall is given
        up. Person doors of a kitchen or garage keep to a wall's end (S10-09, S10-19) and
        widen to leave exactly a door approach beside them.
        """
        candidates = list(walls) if walls is not None else self.walls_between(level, a, b)
        ends = (
            kind is not OpeningKind.WINDOW
            and not (b is None and self.space(a).function is S.GARAGE)
            and any(
                sid is not None and self.space(sid).function in (S.KITCHEN, S.GARAGE)
                for sid in (a, b)
            )
        )
        if prefer is not None:
            if require_direction:
                candidates = [w for w in candidates if w.outward() == prefer]
            candidates.sort(key=lambda w: (w.outward() != prefer, -w.length, w.id))
        else:
            candidates.sort(key=lambda w: (-w.length, w.id))
        outside = a if b is None else None
        for seg in candidates:
            width = round(width_m * 10)
            clear = round(clear_m * 10)
            if ends and seg.length - clear - width < DOOR_APPROACH_CLEAR_DM:
                target_w = seg.length - clear - DOOR_APPROACH_CLEAR_DM
                if target_w >= round(min_width_m * 10):
                    width = target_w
            off = self._fit(seg, width, clear, ends, outside)
            while off is None and width > round(min_width_m * 10):
                width -= 1
                off = self._fit(seg, width, clear, ends, outside)
            if off is None and clear > 1:
                clear = 1
                width = round(min_width_m * 10)
                off = self._fit(seg, width, clear, ends, outside)
            if off is None:
                continue
            other = b if b is not None else EXTERIOR
            return self.cut(
                seg,
                off,
                width,
                kind=kind,
                connects=(a, other),
                ident=self.new_id(f"{prefix}-{_short(a)}-{_short(other)}"),
                height_m=height_m,
                sill_m=sill_m,
                operation=operation,
                opens_into=opens_into,
                material=material,
                role=role,
            )
        return None

    def cut(
        self,
        seg: WallSeg,
        offset_dm: int,
        width_dm: int,
        *,
        kind: OpeningKind,
        connects: tuple[str, str],
        ident: str,
        height_m: float,
        sill_m: float = 0.0,
        operation: Operation = Operation.NONE,
        opens_into: str | None = None,
        material: str | None = None,
        role: OpeningRole | None = None,
    ) -> Opening:
        """Record an opening at a chosen place in ``seg``: the span is then taken."""
        seg.used.append((offset_dm, offset_dm + width_dm))
        op = Opening(
            id=ident,
            kind=kind,
            host_wall_id=seg.id,
            offset_m=from_dm(offset_dm),
            width_m=from_dm(width_dm),
            height_m=height_m,
            sill_m=sill_m,
            connects=connects,
            operation=operation,
            opens_into=opens_into,
            material_id=material,
            role=role,
        )
        self.openings.append(op)
        return op

    def _fit(
        self, seg: WallSeg, width: int, clear: int, ends: bool, outside: str | None
    ) -> int | None:
        """Offset (dm, from seg.a) for an opening of ``width`` avoiding used spans.

        Openings are centred, or with ``ends`` placed nearest a wall end, so the rest of
        the wall stays one run (S10-09: a kitchen's counter needs 3 m of plain wall). An
        opening to the outside of ``outside`` must have only that Space and the outside
        on its two faces.
        """
        lo, hi = clear, seg.length - clear - width
        if hi < lo:
            return None
        centre = (seg.length - width) // 2
        key = (lambda o: (min(o - lo, hi - o), o)) if ends else (lambda o: (abs(o - centre), o))
        for off in sorted(range(lo, hi + 1), key=key):
            if all(off + width + 1 <= a or off >= b + 1 for a, b in seg.used) and (
                outside is None or self._clear_outside(seg, off, width, outside)
            ):
                return off
        return None

    def _clear_outside(self, seg: WallSeg, offset: int, width: int, inside: str) -> bool:
        """Whether the faces of an exterior opening see ``inside`` and nothing else.

        A narrow crevice between two Spaces can leave a room just beyond a nominal exterior
        face; the probes are those of the integrity check.
        """
        rooms = [s for s in self.spaces if s.level_id == seg.level_id]
        reach = (seg.thickness / 2 + PROBE_BEYOND_FACE_M) * 10
        inset = min(OPENING_END_INSET_M * 10, width * 0.1)
        for t in (offset + inset, offset + width / 2, offset + width - inset):
            sides = []
            for sign in (1, -1):
                u, v = (
                    (seg.a + t, seg.c + sign * reach)
                    if seg.orient == "h"
                    else (seg.c + sign * reach, seg.a + t)
                )
                hits = [
                    r.id for r in rooms if r.rect.u0 < u < r.rect.u1 and r.rect.v0 < v < r.rect.v1
                ]
                sides.append(hits[0] if len(hits) == 1 else EXTERIOR if not hits else None)
            if set(sides) != {inside, EXTERIOR}:
                return False
        return True

    # --------------------------------------------- slabs, ceilings, Zones, relationships

    def slabs(
        self, stairs: Sequence[Stair], landings: Mapping[str, Rect] | None = None
    ) -> list[Slab]:
        """Terrace slabs, then per Level (lowest first) its floor and roof slabs.

        A floor is open over each flight arriving on its Level, except a ``landings``
        rectangle kept for that stair; a roof sits at storey height wherever no higher
        Level covers this one (ADR 0023).
        """
        landings = landings or {}
        out: list[Slab] = []
        levels = sorted(self.levels, key=lambda lv: lv.elevation_m)
        polys = {
            lv.id: unary_union(
                [
                    box(s.rect.u0, s.rect.v0, s.rect.u1, s.rect.v1)
                    for s in self.spaces
                    if s.level_id == lv.id and s.function is not S.TERRACE
                ]
            )
            for lv in levels
        }
        for t in (s for s in self.spaces if s.function is S.TERRACE):
            r = t.rect
            out.append(
                Slab(
                    id=f"slab-terrace-{_short(t.id)}"[:64],
                    level_id=t.level_id,
                    kind=SlabKind.TERRACE,
                    boundary=self.frame.rect(r.u0, r.v0, r.u1, r.v1),
                    thickness_m=TERRACE_SLAB_THICKNESS_M,
                    material_id="m-slab",
                )
            )
        for lv in levels:
            above = [polys[o.id] for o in levels if o.elevation_m > lv.elevation_m]
            roof = polys[lv.id].difference(unary_union(above)) if above else polys[lv.id]
            floor = polys[lv.id]
            for stair in stairs:
                if stair.to_level_id != lv.id:
                    continue
                # Snap back to the decimetre grid the flight was built on: frame round-trip
                # noise would leave slivers against stairwell edges (ADR 0023).
                flight = ShapelyPolygon(
                    [
                        tuple(round(v * 10) for v in self.frame.to_design(xy))
                        for xy in stair.footprint.outer
                    ]
                )
                if stair.id in landings:
                    r = landings[stair.id]
                    flight = flight.difference(box(r.u0, r.v0, r.u1, r.v1))
                floor = floor.difference(flight)
            for kind, geom, offset in (
                (SlabKind.FLOOR, floor, 0.0),
                (SlabKind.ROOF, roof, lv.floor_to_floor_m or STOREY_HEIGHT_M),
            ):
                parts = [g for g in getattr(geom, "geoms", [geom]) if g.area >= MIN_SLAB_PART_DM2]
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

    def ceilings(self) -> list[Ceiling]:
        return [
            Ceiling(
                id=f"ceil-{_short(s.id)}"[:64],
                space_id=s.id,
                height_m=CEILING_M,
                material_id="m-int-wall",
            )
            for s in self.spaces
            if s.has_ceiling
        ]

    def zones(self, definitions: Sequence[ProgramZone]) -> list[Zone]:
        """The Zones the Spaces use, in id order; the first definition of an id counts.

        A Zone id nobody defines is left out; the adapter clears it from its Space.
        """
        known: dict[str, ProgramZone] = {}
        for z in definitions:
            known.setdefault(z.id, z)
        used: dict[str, list[str]] = {}
        for s in self.spaces:
            if s.zone_id:
                used.setdefault(s.zone_id, []).append(s.id)
        return [
            Zone(id=zid, name=known[zid].name, privacy=known[zid].privacy, space_ids=used[zid])
            for zid in sorted(used)
            if zid in known
        ]

    def relationships(self, required: Sequence[SpaceRelationship]) -> list[PlanRelationship]:
        """The program's Space relationships, each between the first Space of its two items."""
        first: dict[str, str] = {}
        for s in self.spaces:
            if s.program_item_id and s.program_item_id not in first:
                first[s.program_item_id] = s.id
        out = []
        for adj in required:
            a, b = first.get(adj.a), first.get(adj.b)
            if a is None or b is None or adj.kind not in _RELATIONSHIP_KINDS:
                continue
            out.append(
                PlanRelationship(
                    id=f"rel-{adj.id.removeprefix('adj-')}"[:64].rstrip("-"),
                    a=a,
                    b=b,
                    kind=_RELATIONSHIP_KINDS[adj.kind],
                    requirement_id=adj.id,
                )
            )
        return out

    # ----------------------------------------------------------------- model

    def wall_model(self, seg: WallSeg) -> Wall:
        (u0, v0), (u1, v1) = seg.points()
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

    def wall_models(self) -> list[Wall]:
        return [self.wall_model(w) for w in self.walls]

    @staticmethod
    def materials() -> list[MaterialRef]:
        return list(MATERIALS)


_RELATIONSHIP_KINDS = {
    SpaceRelationshipKind.CONNECTED: RelationshipKind.CONNECTED,
    SpaceRelationshipKind.ADJACENT: RelationshipKind.ADJACENT,
    SpaceRelationshipKind.VISUAL: RelationshipKind.VISUAL,
    SpaceRelationshipKind.SEPARATED: RelationshipKind.SEPARATED,
    SpaceRelationshipKind.ACOUSTIC_SEPARATION: RelationshipKind.SEPARATED,
}


def _short(sid: str) -> str:
    return sid.removeprefix("sp-") if sid != EXTERIOR else "ext"


def _sweep(level_id: str, spaces: list[EnclosedSpace]) -> list[WallSeg]:
    """Wall segments along every rectangle edge, split wherever a side changes."""
    segs: list[WallSeg] = []
    for orient in ("h", "v"):
        lines: dict[int, list[tuple[int, int, str, str]]] = {}
        for s in spaces:
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
                neg = next((e[3] for e in edges if e[2] == "neg" and e[0] <= p and q <= e[1]), None)
                pos = next((e[3] for e in edges if e[2] == "pos" and e[0] <= p and q <= e[1]), None)
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
                    run = WallSeg(level_id, orient, c, p, q, neg, pos)
            if run:
                segs.append(run)
    return segs


def _terrace_edge(seg: WallSeg) -> None:
    """A terrace's edge: an exterior wall where it meets a room, else a parapet (S10-11)."""
    if seg.neg is not None and seg.pos is not None:
        seg.kind, seg.thickness, seg.party = WallKind.EXTERIOR, EXTERIOR_WALL_M, False
    else:
        seg.kind, seg.thickness, seg.retained_m = WallKind.PARAPET, PARAPET_THICKNESS_M, 0.0
        seg.height_m = PARAPET_HEIGHT_M
