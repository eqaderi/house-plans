"""Architectural strategies as massings of bars on the design grid.

A *bar* is an orthogonal block with a room row on each side of a corridor
(double-loaded). Its position across its axis and its rows' depths are fixed
here; its position and length along its axis, and which rooms go where, are
left to the CP-SAT solver. Strategies differ in topology, not in seed:

* ``linear``: one long bar along the contours, single level.
* ``compact``: identical bars stacked on two or more levels, joined by a stair;
  on a site falling away from the road the extra levels go below the entry.
* ``split_level``: parallel bars stepping down (or up) the slope in half-storey
  increments that follow the surveyed terrain, joined by short stairs.
* ``two_wing``: an L of a day wing along the road and a night wing running
  into the site, stepping with the terrain where it falls.
* ``courtyard``: a front and a back pavilion around a garden court, joined by
  a glazed gallery.

Level elevations come from the surveyed terrain (inferred by TIN
interpolation); where the terrain is unknown the levels are placed at the local
datum and the plan says so.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import Polygon as ShapelyPolygon

from house_ai.domain.program import Privacy, SpaceFunction, SpaceProgram

from .frame import ENVELOPE_MARGIN_M, DesignFrame, Ground, best_interval_dm, from_dm
from .rooms import ProgramRooms, RoomSpec

#: Typical values for a first layout; recorded as plan assumptions, not rules.
FLOOR_TO_FLOOR_M = 3.0
HALF_STOREY_M = 1.5
CORRIDOR_DM = 12
GARAGE_DEPTH_DM = 54
MIN_BAR_LENGTH_DM = 60
#: A bar face with ground more than this above its floor is against the earth.
BURIED_FACE_M = 1.0
COURTYARD_GAPS_DM = (50, 40)

STRATEGY_LABELS = {
    "linear": "Linear bar along the contours",
    "compact": "Compact stacked house",
    "split_level": "Split-level, stepping with the slope",
    "two_wing": "Two wings (L): day wing on the road, night wing into the site",
    "courtyard": "Two pavilions around a garden court",
}
STRATEGY_ORDER = ["compact", "split_level", "linear", "two_wing", "courtyard"]


class Infeasible(Exception):
    """The strategy cannot be laid out on this site/program; the message says why."""


@dataclass
class Row:
    id: str
    side: str  # "front" | "corridor" | "back"
    offset_dm: int
    depth_dm: int
    #: The row's exterior face can take windows (not buried, not against another bar).
    daylight_face: bool = True
    buried: bool = False


@dataclass
class Bar:
    id: str
    axis: str  # "u" or "v": direction of the bar's length
    cross0_dm: int
    rows: list[Row]
    start_lo_dm: int
    start_hi_dm: int
    start_fixed_dm: int | None = None
    elevation_m: float = 0.0
    entry: bool = False
    #: Room groups ("entry", "garage", "day", "night", "guest", "service") this bar is for.
    groups: frozenset[str] = frozenset()

    @property
    def depth_dm(self) -> int:
        return sum(r.depth_dm for r in self.rows)

    @property
    def cross1_dm(self) -> int:
        return self.cross0_dm + self.depth_dm

    def row(self, side: str) -> Row:
        return next(r for r in self.rows if r.side == side)

    @property
    def room_rows(self) -> list[Row]:
        return [r for r in self.rows if r.side != "corridor"]


@dataclass
class Link:
    kind: str  # "stacked" | "row" | "end"
    a: str
    b: str
    a_row: str
    b_row: str
    gap_dm: int = 0
    gallery_lo_dm: int = 0
    gallery_hi_dm: int = 0


@dataclass
class Massing:
    strategy: str
    bars: list[Bar]
    links: list[Link]
    corridor_dm: int
    entry_elevation_m: float
    #: Solver weight on bar length (dm): higher packs the plan tighter.
    compactness: int
    params: dict[str, float | int | str | bool] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def bar(self, bar_id: str) -> Bar:
        return next(b for b in self.bars if b.id == bar_id)

    def bar_of_row(self, row_id: str) -> Bar:
        return next(b for b in self.bars if any(r.id == row_id for r in b.rows))

    @property
    def level_count(self) -> int:
        return len({round(b.elevation_m, 3) for b in self.bars})


@dataclass
class MassingContext:
    frame: DesignFrame
    limit: ShapelyPolygon  # design-frame metres
    ground: Ground
    rooms: ProgramRooms
    program: SpaceProgram
    corridor_dm: int


def room_group(r: RoomSpec) -> str:
    f = r.function
    if f is SpaceFunction.ENTRY:
        return "entry"
    if f is SpaceFunction.GARAGE:
        return "garage"
    if f is SpaceFunction.GUEST_SUITE:
        return "guest"
    if r.item.privacy is Privacy.PRIVATE:
        return "night"
    if r.item.privacy is Privacy.SERVICE:
        return "service"
    return "day"


def _rows(bar_id: str, front: int, corridor: int, back: int) -> list[Row]:
    return [
        Row(f"{bar_id}-front", "front", 0, front),
        Row(f"{bar_id}-corridor", "corridor", front, corridor),
        Row(f"{bar_id}-back", "back", front + corridor, back),
    ]


def _u_bar(ctx: MassingContext, bar_id: str, cross0: int, depths: tuple[int, int]) -> Bar:
    rows = _rows(bar_id, depths[0], ctx.corridor_dm, depths[1])
    depth = sum(r.depth_dm for r in rows)
    ival = best_interval_dm(ctx.limit, cross0, cross0 + depth, "u")
    if ival is None or ival[1] - ival[0] < MIN_BAR_LENGTH_DM:
        raise Infeasible(
            f"no {from_dm(MIN_BAR_LENGTH_DM):g} m long strip of the envelope is "
            f"{from_dm(depth):g} m deep at {from_dm(cross0):g} m from the road edge"
        )
    return Bar(bar_id, "u", cross0, rows, ival[0], ival[1])


def _front_v(ctx: MassingContext) -> int:
    """First grid line inside the envelope on the road side (past the safety margin)."""
    return math.ceil((ctx.limit.bounds[1] + 2 * ENVELOPE_MARGIN_M) / 0.1 - 1e-9)


def _entry_depths(ctx: MassingContext, depths: tuple[int, int]) -> tuple[int, int]:
    """The entry bar's rows: deep enough for a garage on the road side and, on the
    garden side, for the day rooms' stacked slots (open living-kitchen-dining)."""
    front, back = depths
    if any(r.function is SpaceFunction.GARAGE for r in ctx.rooms.rooms):
        front = max(front, GARAGE_DEPTH_DM)
    for cl in ctx.rooms.clusters:
        if any(room_group(r) == "day" for r in cl.members):
            for slot in cl.slots:
                if slot.stacked:
                    need = sum(max(15, round((r.item.min_width_m or 0) * 10)) for r in slot.rooms)
                    back = max(back, need)
    return (front, back)


def _snap(z: float, step: float = 0.05) -> float:
    return round(round(z / step) * step, 3)


def _bar_ground(ctx: MassingContext, bar: Bar) -> float | None:
    """Mean surveyed ground over the bar's possible footprint."""
    s0, s1 = from_dm(bar.start_lo_dm), from_dm(bar.start_hi_dm)
    if bar.start_fixed_dm is not None:
        s0 = from_dm(bar.start_fixed_dm)
    c0, c1 = from_dm(bar.cross0_dm), from_dm(bar.cross1_dm)
    pts = []
    for i in range(5):
        for j in range(3):
            s = s0 + (s1 - s0) * (i + 0.5) / 5
            c = c0 + (c1 - c0) * (j + 0.5) / 3
            pts.append((s, c) if bar.axis == "u" else (c, s))
    return ctx.ground.mean_along(pts)


def _face_ground(ctx: MassingContext, bar: Bar, side: str) -> float | None:
    """Mean ground 0.5 m outside a bar's front (low cross) or back (high cross) face."""
    s0, s1 = from_dm(bar.start_lo_dm), from_dm(bar.start_hi_dm)
    if bar.start_fixed_dm is not None:
        s0 = from_dm(bar.start_fixed_dm)
    c = from_dm(bar.cross0_dm) - 0.5 if side == "front" else from_dm(bar.cross1_dm) + 0.5
    a, b = ((s0, c), (s1, c)) if bar.axis == "u" else ((c, s0), (c, s1))
    return ctx.ground.mean_line(a, b)


def _entry_elevation(ctx: MassingContext, bar0: Bar, notes: list[str]) -> float:
    z = _face_ground(ctx, bar0, "front")
    if z is None:
        z = _bar_ground(ctx, bar0)
    if z is None:
        notes.append(
            "Surveyed terrain does not cover the road side; the entry level is placed at the "
            "local datum (z = 0.00 m) as an assumption."
        )
        return 0.0
    notes.append(
        f"Entry level set at the mean surveyed ground along the road-side face "
        f"({_snap(z):.2f} m local), interpolated from the survey TIN (inferred)."
    )
    return _snap(z)


def _step(delta: float | None) -> float:
    if delta is None:
        return 0.0
    q = round(delta / HALF_STOREY_M) * HALF_STOREY_M
    return max(-FLOOR_TO_FLOOR_M, min(FLOOR_TO_FLOOR_M, q))


def _mark_faces(ctx: MassingContext, m: Massing) -> None:
    blocked: set[str] = set()
    for link in m.links:
        if link.kind == "row" and link.gap_dm == 0:
            a, b = m.bar(link.a), m.bar(link.b)
            rise = b.elevation_m - a.elevation_m
            # A bar a full storey above its neighbour looks out over the neighbour's roof.
            if rise < FLOOR_TO_FLOOR_M - 1e-6:
                blocked.add(link.a_row)
            if -rise < FLOOR_TO_FLOOR_M - 1e-6:
                blocked.add(link.b_row)
    for bar in m.bars:
        for row in bar.room_rows:
            ground = _face_ground(ctx, bar, row.side)
            row.buried = ground is not None and ground - bar.elevation_m > BURIED_FACE_M
            row.daylight_face = not row.buried and row.id not in blocked


def _levels_note(m: Massing) -> None:
    elevations = sorted({round(b.elevation_m, 3) for b in m.bars})
    m.params["levels"] = len(elevations)
    m.params["level_elevations_m"] = ", ".join(f"{z:.2f}" for z in elevations)


def build_massing(strategy: str, ctx: MassingContext, depths: tuple[int, int]) -> Massing:
    builder = {
        "linear": _linear,
        "compact": _compact,
        "split_level": _split_level,
        "two_wing": _two_wing,
        "courtyard": _courtyard,
    }.get(strategy)
    if builder is None:
        raise Infeasible(f"unknown strategy {strategy!r}; known: {', '.join(STRATEGY_ORDER)}")
    m = builder(ctx, depths)
    m.params.update(
        {
            "strategy": strategy,
            "front_row_depth_m": from_dm(depths[0]),
            "back_row_depth_m": from_dm(depths[1]),
            "corridor_width_m": from_dm(ctx.corridor_dm),
        }
    )
    _mark_faces(ctx, m)
    _levels_note(m)
    return m


ALL_GROUPS = frozenset({"entry", "garage", "day", "night", "guest", "service"})
DAY_GROUPS = frozenset({"entry", "garage", "day", "service"})
NIGHT_GROUPS = frozenset({"night", "guest"})


def _linear(ctx: MassingContext, depths: tuple[int, int]) -> Massing:
    bar = _u_bar(ctx, "b0", _front_v(ctx), _entry_depths(ctx, depths))
    bar.entry, bar.groups = True, ALL_GROUPS
    notes: list[str] = []
    bar.elevation_m = _entry_elevation(ctx, bar, notes)
    return Massing("linear", [bar], [], ctx.corridor_dm, bar.elevation_m, 4, notes=notes)


def _compact(ctx: MassingContext, depths: tuple[int, int]) -> Massing:
    n = max(2, ctx.program.levels or 2)
    d = _entry_depths(ctx, depths)
    b0 = _u_bar(ctx, "b0", _front_v(ctx), d)
    b0.entry, b0.groups = True, DAY_GROUPS
    notes: list[str] = []
    entry = _entry_elevation(ctx, b0, notes)
    b0.elevation_m = entry
    front, back = _face_ground(ctx, b0, "front"), _face_ground(ctx, b0, "back")
    below = front is not None and back is not None and back < front - BURIED_FACE_M
    sign = -1.0 if below else 1.0
    notes.append(
        "The site falls away from the road, so the other levels sit below the entry level "
        "(walk-out)."
        if below
        else "The other levels sit above the entry level."
    )
    bars, links = [b0], []
    for k in range(1, n):
        rows = _rows(f"b{k}", d[0], ctx.corridor_dm, d[1])
        bk = Bar(f"b{k}", "u", b0.cross0_dm, rows, b0.start_lo_dm, b0.start_hi_dm)
        bk.elevation_m = round(entry + sign * k * FLOOR_TO_FLOOR_M, 3)
        bk.groups = NIGHT_GROUPS | {"service"}
        side = "front" if below else "back"
        links.append(Link("stacked", f"b{k - 1}", f"b{k}", f"b{k - 1}-{side}", f"b{k}-{side}"))
        bars.append(bk)
    return Massing("compact", bars, links, ctx.corridor_dm, entry, 20, notes=notes)


def _split_level(ctx: MassingContext, depths: tuple[int, int]) -> Massing:
    if not ctx.ground.known:
        raise Infeasible("no surveyed terrain: a split level cannot follow an unknown slope")
    d0 = _entry_depths(ctx, depths)
    b0 = _u_bar(ctx, "b0", _front_v(ctx), d0)
    b0.entry = True
    notes: list[str] = []
    entry = _entry_elevation(ctx, b0, notes)
    b0.elevation_m = entry
    need = sum(r.item.target_area_m2 or r.item.min_area_m2 or 0.0 for r in ctx.rooms.rooms)
    per_bar = from_dm(min(b0.start_hi_dm - b0.start_lo_dm, 160)) * from_dm(sum(depths))
    n = 3 if need > 2 * per_bar * 0.85 else 2
    bars, links = [b0], []
    for k in range(1, n):
        prev = bars[-1]
        try:
            bk = _u_bar(ctx, f"b{k}", prev.cross1_dm, depths)
        except Infeasible as exc:
            if k == 1:
                raise Infeasible(
                    f"no room behind the entry bar for a lower split level: {exc}"
                ) from exc
            break
        g_prev, g_k = _bar_ground(ctx, prev), _bar_ground(ctx, bk)
        delta = None if g_prev is None or g_k is None else g_k - g_prev
        bk.elevation_m = round(prev.elevation_m + _step(delta), 3)
        bars.append(bk)
        links.append(Link("row", prev.id, bk.id, f"{prev.id}-back", f"{bk.id}-front"))
    if all(abs(b.elevation_m - entry) < 1e-6 for b in bars):
        raise Infeasible(
            "the surveyed ground under the bars differs by less than half a storey "
            f"({HALF_STOREY_M / 2:g} m rounding): a split level is not warranted"
        )
    if len(bars) == 2:
        b0.groups, bars[1].groups = DAY_GROUPS, NIGHT_GROUPS
    else:
        b0.groups = frozenset({"entry", "garage", "service"})
        bars[1].groups = frozenset({"day", "service"})
        bars[2].groups = NIGHT_GROUPS
    notes.append(
        f"Levels step by multiples of a half storey ({HALF_STOREY_M:g} m) chosen from the "
        "surveyed ground under each bar."
    )
    return Massing("split_level", bars, links, ctx.corridor_dm, entry, 15, notes=notes)


def _two_wing(ctx: MassingContext, depths: tuple[int, int]) -> Massing:
    d0 = _entry_depths(ctx, depths)
    a = _u_bar(ctx, "b0", _front_v(ctx), d0)
    a.entry, a.groups = True, DAY_GROUPS
    notes: list[str] = []
    entry = _entry_elevation(ctx, a, notes)
    a.elevation_m = entry
    rows_b = _rows("b1", depths[0], ctx.corridor_dm, depths[1])
    depth_b = sum(r.depth_dm for r in rows_b)
    best: Bar | None = None
    for u0 in (a.start_lo_dm, a.start_hi_dm - depth_b):
        ival = best_interval_dm(ctx.limit, u0, u0 + depth_b, "v")
        if ival is None or ival[0] > a.cross1_dm or ival[1] - a.cross1_dm < MIN_BAR_LENGTH_DM:
            continue
        bar = Bar(
            "b1",
            "v",
            u0,
            [Row(r.id, r.side, r.offset_dm, r.depth_dm) for r in rows_b],
            a.cross1_dm,
            ival[1],
            start_fixed_dm=a.cross1_dm,
        )
        if best is None or bar.start_hi_dm > best.start_hi_dm:
            best = bar
    if best is None:
        raise Infeasible("the envelope has no room for a wing running back from the day wing")
    b = best
    b.groups = NIGHT_GROUPS | {"service"}
    g_a, g_b = _bar_ground(ctx, a), _bar_ground(ctx, b)
    b.elevation_m = round(entry + _step(None if g_a is None or g_b is None else g_b - g_a), 3)
    link = Link("end", "b0", "b1", "b0-back", "b1-corridor")
    return Massing("two_wing", [a, b], [link], ctx.corridor_dm, entry, 15, notes=notes)


def _courtyard(ctx: MassingContext, depths: tuple[int, int]) -> Massing:
    d0 = _entry_depths(ctx, depths)
    a = _u_bar(ctx, "b0", _front_v(ctx), d0)
    a.entry, a.groups = True, DAY_GROUPS
    notes: list[str] = []
    entry = _entry_elevation(ctx, a, notes)
    a.elevation_m = entry
    last: Exception | None = None
    for gap in COURTYARD_GAPS_DM:
        try:
            b = _u_bar(ctx, "b1", a.cross1_dm + gap, depths)
        except Infeasible as exc:
            last = exc
            continue
        gallery = best_interval_dm(ctx.limit, a.cross1_dm, b.cross0_dm, "u")
        if gallery is None:
            continue
        b.groups = NIGHT_GROUPS | {"service"}
        g_a, g_b = _bar_ground(ctx, a), _bar_ground(ctx, b)
        b.elevation_m = round(entry + _step(None if g_a is None or g_b is None else g_b - g_a), 3)
        link = Link("row", "b0", "b1", "b0-back", "b1-front", gap, gallery[0], gallery[1])
        m = Massing("courtyard", [a, b], [link], ctx.corridor_dm, entry, 10, notes=notes)
        m.params["court_depth_m"] = from_dm(gap)
        return m
    raise Infeasible(f"no room for a second pavilion behind a garden court: {last}")
