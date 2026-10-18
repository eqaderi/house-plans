"""CP-SAT layout of rooms in a massing (Google OR-Tools).

Decision variables, all integers on the 10 cm grid:

* each bar's start and length along its axis (inside the envelope);
* for each cluster of rooms, which room row it occupies, where it starts in
  the row, and the width of each of its slots;
* stair and link slots joining bars, aligned across the bars they join.

HARD (constraints): every room row is tiled exactly by its units and an
optional filler (no gaps, no overlaps), each room meets its program minimum
area and width, the entry sits on the road-side row of the entry bar,
step-free rooms stay on the entry level, stairs and links line up, and hard
near/separation requirements between clusters hold.

SOFT (objective, integer-weighted): deviation from target areas, wasted
filler area, level preferences, which bar each room group belongs to,
daylight for rooms that need it, soft adjacencies and separations, bar
length (compactness) and, for revisions, staying close to the parent plan.

The solver runs single-threaded with a fixed seed and a deterministic-time
budget, so the same inputs give the same plan on the same platform.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from house_ai.domain.program import AdjacencyKind, SpaceFunction, Strength

from .massing import GARAGE_DEPTH_DM, Bar, Massing, Row, room_group
from .rooms import Cluster, ProgramRooms, Relation, RoomSpec, Slot

MIN_SLOT_DM = 15
MAX_ASPECT = 3
U_STAIR_DM = (24, 32)
STRAIGHT_STAIR_DM = (13, 20)
LINK_DM = (15, 24)
FILLER_MIN_DM = 15

W_LEVEL = 6000
W_GROUP = 2500
W_DAYLIGHT_REQUIRED = 1200
W_DAYLIGHT_PREFERRED = 300
W_FILLER = 2  # per dm² of filler
#: Per dm² a room exceeds OVERSIZE x its target: oversized rooms cost more than flex space.
W_OVERSIZE = 6
OVERSIZE = 1.3
W_ADJ = 300
W_NEAR = 200
W_STABILITY = 1500
#: Per dm a room or bar moves away from its parent position during a revision.
W_STABILITY_SHIFT = 15
#: Target deviation weight multiplier for areas the owner asked to change.
W_REQUESTED_TARGET = 4
#: Habitable rooms prefer the garden side of the entry bar; garage/entry/service face the road.
W_ROAD_SIDE = 400
HABITABLE_GROUPS = {"day", "night", "guest"}


@dataclass
class SolverOptions:
    seed: int = 0
    #: CP-SAT deterministic time budget (solver work units, not wall-clock seconds).
    deterministic_time: float = 4.0
    #: space id -> target area override (m²) from a revision.
    targets: dict[str, float] = field(default_factory=dict)
    #: space id -> level preference override ("entry", "not_entry", "upper", "lower").
    level_prefs: dict[str, str] = field(default_factory=dict)
    #: Extra soft relations from a revision.
    relations: list[Relation] = field(default_factory=list)
    #: space id -> (row id, bar-relative start dm) in the parent plan.
    hints: dict[str, tuple[str, int]] = field(default_factory=dict)
    #: bar id -> start (dm) in the parent plan, to keep the house where it was.
    bar_hints: dict[str, int] = field(default_factory=dict)
    #: Objective scales from the constraint set (objective name -> weight).
    objective_weights: dict[str, float] = field(default_factory=dict)
    #: Stair position override ("entry", "perimeter", "central", "rear") (S7-16, S7-21).
    stair_position: str | None = None
    #: Outdoor links (space_id, kind) (S7-19, S7-21).
    outdoor_links: list[tuple[str, str]] = field(default_factory=list)
    #: Force 2D placement solver (S7-10).
    force_2d: bool = False
    min_areas: dict[str, float] = field(default_factory=dict)
    min_widths: dict[str, float] = field(default_factory=dict)


@dataclass
class Unit:
    id: str
    kind: str  # "cluster" | "stair" | "link"
    rows: list[str]
    cluster: Cluster | None = None
    link_index: int | None = None
    side: str | None = None  # "a" | "b" for link units
    width_range: tuple[int, int] | None = None

    @property
    def slots(self) -> list[Slot]:
        return self.cluster.slots if self.cluster else []


@dataclass
class PlacedUnit:
    unit: Unit
    row_id: str
    start_dm: int
    widths: list[int]

    @property
    def width_dm(self) -> int:
        return sum(self.widths)


@dataclass
class Solution:
    status: str
    objective: float
    bar_start: dict[str, int]
    bar_length: dict[str, int]
    units: list[PlacedUnit]
    fillers: dict[str, tuple[int, int]]
    #: Inner depth (dm) of each stacked slot, by (row id, inner space id).
    splits: dict[tuple[str, str], int]


class SolveFailed(Exception):
    pass


def stair_risers(rise_m: float) -> tuple[int, float, float]:
    """(riser count, riser height m, run length m) for a straight flight, typical values."""
    n = max(2, math.ceil(abs(rise_m) / 0.18 - 1e-9))
    return n, abs(rise_m) / n, (n - 1) * 0.28


def split_depth(row_depth: int, inner: RoomSpec, outer: RoomSpec) -> int | None:
    t_in = inner.item.target_area_m2 or inner.min_area_m2 or 4.0
    t_out = outer.item.target_area_m2 or outer.min_area_m2 or 4.0
    lo_in = max(MIN_SLOT_DM, math.ceil((inner.min_width_m or 0) * 10 - 1e-9))
    lo_out = max(MIN_SLOT_DM, math.ceil((outer.min_width_m or 0) * 10 - 1e-9))
    d = round(row_depth * t_in / (t_in + t_out))
    d = max(lo_in, min(row_depth - lo_out, d))
    if d < lo_in or row_depth - d < lo_out:
        return None
    return d


def _ceil(x: float) -> int:
    return math.ceil(x - 1e-9)


def _slot_bounds(
    slot: Slot, row: Row, targets: dict[str, float], split: int | None
) -> tuple[int, int, list[tuple[RoomSpec, int]]] | None:
    """(min width, max width, [(room, piece depth)]) for a slot in a row, or None."""
    if slot.stacked:
        if split is None:
            return None
        pieces = [(slot.rooms[0], split), (slot.rooms[1], row.depth_dm - split)]
    else:
        pieces = [(slot.rooms[0], row.depth_dm)]
    wmin, wmax = MIN_SLOT_DM, None
    for room, depth in pieces:
        it = room.item
        min_w = room.min_width_m
        min_a = room.min_area_m2
        if min_w is not None and depth < _ceil(min_w * 10):
            return None
        if room.function is SpaceFunction.GARAGE and depth < GARAGE_DEPTH_DM:
            return None
        wmin = max(wmin, _ceil((min_w or 0) * 10))
        if min_a is not None:
            wmin = max(wmin, _ceil(min_a * 100 / depth))
        cap = MAX_ASPECT * depth
        target = targets.get(room.space_id, it.target_area_m2)
        if target is not None:
            cap = max(cap, _ceil(target * 100 / depth * 1.25))
        if it.max_area_m2 is not None:
            cap = min(cap, int(it.max_area_m2 * 100 // depth))
        wmax = cap if wmax is None else min(wmax, cap)
    assert wmax is not None
    wmax = max(wmax, wmin) if not any(r.item.max_area_m2 for r, _ in pieces) else wmax
    if wmax < wmin:
        return None
    return wmin, wmax, pieces


def _stair_range(rooms: ProgramRooms, rng: tuple[int, int], depth: int) -> tuple[int, int]:
    item = rooms.stair_item
    lo = rng[0]
    if item is not None:
        lo = max(lo, _ceil((item.min_width_m or 0) * 10))
        if item.min_area_m2:
            lo = max(lo, _ceil(item.min_area_m2 * 100 / depth))
    return lo, max(lo, rng[1])


def build_units(m: Massing, rooms: ProgramRooms) -> tuple[list[Unit], list[str]]:
    """Units to place and reasons a cluster has nowhere to go (empty when feasible)."""
    entry_z = m.entry_elevation_m
    units: list[Unit] = []
    problems: list[str] = []
    for cl in rooms.clusters:
        eligible = []
        for bar in m.bars:
            same_level = abs(bar.elevation_m - entry_z) < 1e-6
            for row in bar.room_rows:
                if cl.is_entry and not (bar.entry and row.side == "front"):
                    continue
                needs_entry_level = any(
                    r.item.accessible or r.function is SpaceFunction.LIFT for r in cl.members
                )
                if needs_entry_level and not same_level:
                    continue
                # Cars arrive from the road: a garage sits in the entry bar's road-side row.
                if any(r.function is SpaceFunction.GARAGE for r in cl.members) and not (
                    bar.entry and row.side == "front"
                ):
                    continue
                # A room that must open off the hall stays beside the entry bar's corridor.
                if not bar.entry and any(r.space_id in rooms.hall_connected for r in cl.members):
                    continue
                ok = True
                for slot in cl.slots:
                    split = (
                        split_depth(row.depth_dm, slot.rooms[0], slot.rooms[1])
                        if slot.stacked
                        else None
                    )
                    if _slot_bounds(slot, row, {}, split) is None:
                        ok = False
                        break
                if ok:
                    eligible.append(row.id)
        if not eligible:
            names = ", ".join(r.name for r in cl.members)
            problems.append(f"no row in this massing can hold {names}")
        units.append(Unit(cl.id, "cluster", eligible, cluster=cl))
    depth = {r.id: r.depth_dm for b in m.bars for r in b.rows}

    def unit(kind: str, i: int, side: str, row: str, rng: tuple[int, int]) -> Unit:
        if kind == "stair":
            rng = _stair_range(rooms, rng, depth[row])
        return Unit(f"{kind}-{i}{side}", kind, [row], link_index=i, side=side, width_range=rng)

    for i, link in enumerate(m.links):
        a, b = m.bar(link.a), m.bar(link.b)
        same = abs(a.elevation_m - b.elevation_m) < 1e-6
        if link.kind == "stacked":
            units.append(unit("stair", i, "a", link.a_row, U_STAIR_DM))
            units.append(unit("stair", i, "b", link.b_row, U_STAIR_DM))
        elif link.kind == "row":
            kind_a = "link" if same or link.gap_dm > 0 else "stair"
            kind_b = "link" if same else "stair"
            units.append(
                unit(kind_a, i, "a", link.a_row, LINK_DM if kind_a == "link" else STRAIGHT_STAIR_DM)
            )
            units.append(
                unit(kind_b, i, "b", link.b_row, LINK_DM if kind_b == "link" else STRAIGHT_STAIR_DM)
            )
        else:  # end: the slot spans the other wing's corridor end
            kind = "link" if same else "stair"
            rng = (m.corridor_dm, max(m.corridor_dm, LINK_DM[1] if same else U_STAIR_DM[1]))
            units.append(unit(kind, i, "a", link.a_row, rng))
    return units, problems


def _level_penalty(pref: str | None, bar: Bar, m: Massing) -> int:
    z, entry = bar.elevation_m, m.entry_elevation_m
    if pref in ("entry", "ground", "lv-entry", "lv-0"):
        return W_LEVEL if abs(z - entry) > 1e-6 else 0
    if pref in ("not_entry",):
        return W_LEVEL if m.level_count > 1 and abs(z - entry) < 1e-6 else 0
    if pref in ("upper", "lv-upper", "lv-1", "1"):
        return W_LEVEL if z <= entry + 1e-6 else 0
    if pref in ("lower", "lv-lower", "lv-basement", "-1"):
        return W_LEVEL if z >= entry - 1e-6 else 0
    return 0


def solve(m: Massing, rooms: ProgramRooms, opts: SolverOptions) -> Solution:
    units, problems = build_units(m, rooms)
    if problems:
        raise SolveFailed("; ".join(problems))
    md = cp_model.CpModel()
    ow = opts.objective_weights

    def w(name: str) -> float:
        return ow.get(name, 1.0)

    rows: dict[str, Row] = {r.id: r for b in m.bars for r in b.rows}
    bar_of = {r.id: b for b in m.bars for r in b.rows}
    lmax = max(b.start_hi_dm - (b.start_fixed_dm or b.start_lo_dm) for b in m.bars)

    start, length = {}, {}
    for b in m.bars:
        lo = b.start_fixed_dm if b.start_fixed_dm is not None else b.start_lo_dm
        hi_len = b.start_hi_dm - lo
        if b.start_fixed_dm is not None:
            start[b.id] = md.NewConstant(b.start_fixed_dm)
        else:
            start[b.id] = md.NewIntVar(b.start_lo_dm, b.start_hi_dm, f"S_{b.id}")
        length[b.id] = md.NewIntVar(min(60, hi_len), hi_len, f"L_{b.id}")
        md.Add(start[b.id] + length[b.id] <= b.start_hi_dm)

    obj: list = []
    x: dict[tuple[str, str], cp_model.IntVar] = {}
    st: dict[tuple[str, str], cp_model.IntVar] = {}
    width: dict[tuple[str, str], cp_model.LinearExpr] = {}
    slot_w: dict[tuple[str, str, int], cp_model.IntVar] = {}
    splits: dict[tuple[str, str], int] = {}
    intervals: dict[str, list] = {r: [] for r in rows if rows[r].side != "corridor"}
    widths_in_row: dict[str, list] = {r: [] for r in intervals}
    area_terms: dict[str, list] = {}

    for u in units:
        lits = []
        for rid in u.rows:
            row, bar = rows[rid], bar_of[rid]
            xr = md.NewBoolVar(f"x_{u.id}_{rid}")
            lits.append(xr)
            x[u.id, rid] = xr
            s = md.NewIntVar(0, lmax, f"st_{u.id}_{rid}")
            st[u.id, rid] = s
            parts = []
            if u.kind == "cluster":
                for j, slot in enumerate(u.slots):
                    split = (
                        split_depth(row.depth_dm, slot.rooms[0], slot.rooms[1])
                        if slot.stacked
                        else None
                    )
                    if split is not None:
                        splits[rid, slot.rooms[0].space_id] = split
                    bounds = _slot_bounds(slot, row, opts.targets, split)
                    assert bounds is not None
                    lo, hi, pieces = bounds
                    v = md.NewIntVar(0, min(hi, lmax), f"w_{u.id}_{rid}_{j}")
                    md.Add(v >= lo).OnlyEnforceIf(xr)
                    md.Add(v == 0).OnlyEnforceIf(xr.Not())
                    slot_w[u.id, rid, j] = v
                    parts.append(v)
                    for room, depth in pieces:
                        area_terms.setdefault(room.space_id, []).append((depth, v))
                    # Soft: level preference, bar group, daylight, garage on the road.
                    pen = 0
                    for k, (room, _depth) in enumerate(pieces):
                        pref = opts.level_prefs.get(room.space_id, room.item.level_preference)
                        pen += _level_penalty(pref, bar, m)
                        if bar.groups and room_group(room) not in bar.groups:
                            pen += W_GROUP
                        inner = slot.stacked and k == 0
                        dark = inner or not row.daylight_face
                        if dark and room.daylight_required:
                            pen += int(W_DAYLIGHT_REQUIRED * w("daylight_opportunity"))
                        elif dark and room.wants_daylight:
                            pen += int(W_DAYLIGHT_PREFERRED * w("daylight_opportunity"))
                        if (
                            bar.entry
                            and row.side == "front"
                            and room_group(room) in HABITABLE_GROUPS
                        ):
                            pen += int(W_ROAD_SIDE * w("site_response"))
                        hint = opts.hints.get(room.space_id)
                        if hint is not None and hint[0] != rid:
                            pen += W_STABILITY
                    if pen:
                        obj.append(pen * xr)
            else:
                lo, hi = u.width_range or (MIN_SLOT_DM, MIN_SLOT_DM)
                v = md.NewIntVar(0, hi, f"w_{u.id}_{rid}")
                md.Add(v >= lo).OnlyEnforceIf(xr)
                md.Add(v == 0).OnlyEnforceIf(xr.Not())
                slot_w[u.id, rid, 0] = v
                parts.append(v)
            wexpr = sum(parts)
            width[u.id, rid] = wexpr
            end = md.NewIntVar(0, lmax, f"end_{u.id}_{rid}")
            md.Add(end == s + wexpr)
            md.Add(end <= length[bar.id]).OnlyEnforceIf(xr)
            size = md.NewIntVar(0, lmax, f"size_{u.id}_{rid}")
            md.Add(size == wexpr)
            iv = md.NewOptionalIntervalVar(s, size, end, xr, f"iv_{u.id}_{rid}")
            intervals[rid].append(iv)
            widths_in_row[rid].append(wexpr)
        md.AddExactlyOne(lits)

    # Fillers: optional flexible space closing each row.
    filler: dict[str, tuple] = {}
    for rid in intervals:
        bar = bar_of[rid]
        f_on = md.NewBoolVar(f"f_on_{rid}")
        f_st = md.NewIntVar(0, lmax, f"f_st_{rid}")
        f_w = md.NewIntVar(0, lmax, f"f_w_{rid}")
        f_end = md.NewIntVar(0, lmax, f"f_end_{rid}")
        md.Add(f_end == f_st + f_w)
        md.Add(f_w >= FILLER_MIN_DM).OnlyEnforceIf(f_on)
        md.Add(f_w == 0).OnlyEnforceIf(f_on.Not())
        md.Add(f_end <= length[bar.id]).OnlyEnforceIf(f_on)
        intervals[rid].append(md.NewOptionalIntervalVar(f_st, f_w, f_end, f_on, f"f_iv_{rid}"))
        md.AddNoOverlap(intervals[rid])
        md.Add(sum(widths_in_row[rid]) + f_w == length[bar.id])
        filler[rid] = (f_on, f_st, f_w)
        obj.append(int(W_FILLER * w("circulation_efficiency")) * rows[rid].depth_dm * f_w)

    # Rooms: hard minimum area is in the slot bounds; soft deviation from target.
    for room in rooms.rooms:
        terms = area_terms.get(room.space_id)
        if not terms:
            continue
        area = sum(d * v for d, v in terms)
        target = opts.targets.get(room.space_id, room.item.target_area_m2)
        if room.min_area_m2 is not None:
            md.Add(area >= _ceil(room.min_area_m2 * 100))
        if room.item.max_area_m2 is not None:
            md.Add(area <= int(room.item.max_area_m2 * 100))
        if target is not None:
            dev = md.NewIntVar(0, 10_000_000, f"dev_{room.space_id}")
            md.Add(dev >= area - round(target * 100))
            md.Add(dev >= round(target * 100) - area)
            excess = md.NewIntVar(0, 10_000_000, f"excess_{room.space_id}")
            md.Add(excess >= area - round(target * 100 * OVERSIZE))
            weight = room.priority_weight * (
                W_REQUESTED_TARGET if room.space_id in opts.targets else 1
            )
            obj.append(weight * dev + W_OVERSIZE * excess)

    # The corridor standing for the program's hall must meet the hall minimum.
    if rooms.hall_item is not None and rooms.hall_item.min_area_m2 is not None:
        entry_bar = next(b for b in m.bars if b.entry)
        md.Add(length[entry_bar.id] * m.corridor_dm >= _ceil(rooms.hall_item.min_area_m2 * 100))

    # Links: aligned slots across bars, and galleries inside the envelope.
    def abs_start(unit_id: str, rid: str):
        bar = bar_of[rid]
        return start[bar.id] + st[unit_id, rid]

    by_link: dict[int, dict[str, Unit]] = {}
    for u in units:
        if u.link_index is not None:
            by_link.setdefault(u.link_index, {})[u.side or ""] = u
    for i, link in enumerate(m.links):
        pair = by_link[i]
        ua = pair["a"]
        if link.kind == "stacked":
            ub = pair["b"]
            md.Add(start[link.a] == start[link.b])
            md.Add(length[link.a] == length[link.b])
            md.Add(abs_start(ua.id, link.a_row) == abs_start(ub.id, link.b_row))
            md.Add(width[ua.id, link.a_row] == width[ub.id, link.b_row])
        elif link.kind == "row":
            ub = pair["b"]
            md.Add(abs_start(ua.id, link.a_row) == abs_start(ub.id, link.b_row))
            md.Add(width[ua.id, link.a_row] == width[ub.id, link.b_row])
            if link.gap_dm:
                md.Add(abs_start(ua.id, link.a_row) >= link.gallery_lo_dm)
                md.Add(
                    abs_start(ua.id, link.a_row) + width[ua.id, link.a_row] <= link.gallery_hi_dm
                )
        else:  # end: the slot meets the other wing's corridor
            b = m.bar(link.b)
            corridor_start = b.cross0_dm + b.row("front").depth_dm
            md.Add(abs_start(ua.id, link.a_row) <= corridor_start)
            md.Add(
                abs_start(ua.id, link.a_row) + width[ua.id, link.a_row]
                >= corridor_start + m.corridor_dm
            )

    # Relations between clusters.
    unit_of: dict[str, Unit] = {}
    for u in units:
        for r in u.cluster.members if u.cluster else []:
            unit_of[r.space_id] = u
    for rel in [*rooms.relations, *opts.relations]:
        ua, ub = unit_of.get(rel.a), unit_of.get(rel.b)
        if ua is None or ub is None or ua is ub:
            continue
        _relation(md, rel, ua, ub, x, st, width, bar_of, obj, w)

    if opts.hints:
        for u in units:
            # One hint per unit: the parent row of its anchor (CP-SAT rejects duplicate hints).
            anchor = u.cluster.anchor.space_id if u.cluster else None
            hint = opts.hints.get(anchor) if anchor else None
            if hint and (u.id, hint[0]) in x:
                md.AddHint(x[u.id, hint[0]], 1)

    # Revisions: stay close to the parent's bar positions and room starts.
    for bid, s0 in opts.bar_hints.items():
        if bid in start and m.bar(bid).start_fixed_dm is None:
            shift = md.NewIntVar(0, 10_000, f"shift_{bid}")
            md.AddAbsEquality(shift, start[bid] - s0)
            obj.append(W_STABILITY_SHIFT * 4 * shift)
    for u in units:
        anchor = u.cluster.anchor.space_id if u.cluster else None
        hint = opts.hints.get(anchor) if anchor else None
        if hint and (u.id, hint[0]) in st:
            shift = md.NewIntVar(0, 10_000, f"shift_{u.id}")
            md.AddAbsEquality(shift, st[u.id, hint[0]] - hint[1])
            obj.append(W_STABILITY_SHIFT * shift)
    for b in m.bars:
        scale = (w("envelope_simplicity") + w("cost_proxy")) / 2
        obj.append(int(m.compactness * scale) * length[b.id])

    md.Minimize(sum(obj))
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = opts.seed
    solver.parameters.max_deterministic_time = opts.deterministic_time
    status = solver.Solve(md)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise SolveFailed(f"CP-SAT found no layout ({solver.StatusName(status)})")

    placed = []
    for u in units:
        for rid in u.rows:
            if solver.Value(x[u.id, rid]):
                n = len(u.slots) if u.kind == "cluster" else 1
                placed.append(
                    PlacedUnit(
                        u,
                        rid,
                        solver.Value(st[u.id, rid]),
                        [solver.Value(slot_w[u.id, rid, j]) for j in range(n)],
                    )
                )
    fillers = {
        rid: (solver.Value(f_st), solver.Value(f_w))
        for rid, (f_on, f_st, f_w) in filler.items()
        if solver.Value(f_on)
    }
    return Solution(
        status=solver.StatusName(status),
        objective=solver.ObjectiveValue(),
        bar_start={b.id: solver.Value(start[b.id]) for b in m.bars},
        bar_length={b.id: solver.Value(length[b.id]) for b in m.bars},
        units=placed,
        fillers=fillers,
        splits=splits,
    )


def _relation(md, rel: Relation, ua: Unit, ub: Unit, x, st, width, bar_of, obj, w) -> None:
    shared = [r for r in ua.rows if r in ub.rows]
    touch_lits = []
    for rid in shared:
        for first, second in ((ua, ub), (ub, ua)):
            c = md.NewBoolVar(f"touch_{first.id}_{second.id}_{rid}")
            xa, xb = x[first.id, rid], x[second.id, rid]
            end_first = st[first.id, rid] + width[first.id, rid]
            md.AddImplication(c, xa)
            md.AddImplication(c, xb)
            md.Add(end_first == st[second.id, rid]).OnlyEnforceIf(c)
            md.Add(end_first != st[second.id, rid]).OnlyEnforceIf([xa, xb, c.Not()])
            touch_lits.append(c)
    touch = md.NewBoolVar(f"touch_{ua.id}_{ub.id}")
    if touch_lits:
        md.AddMaxEquality(touch, touch_lits)
    else:
        md.Add(touch == 0)
    bars = sorted({bar_of[r].id for r in ua.rows} & {bar_of[r].id for r in ub.rows})
    same_bar_lits = []
    for bid in bars:
        sb = md.NewBoolVar(f"samebar_{ua.id}_{ub.id}_{bid}")
        ya = sum(x[ua.id, r] for r in ua.rows if bar_of[r].id == bid)
        yb = sum(x[ub.id, r] for r in ub.rows if bar_of[r].id == bid)
        md.Add(sb <= ya)
        md.Add(sb <= yb)
        same_bar_lits.append(sb)
    same_bar = md.NewBoolVar(f"samebar_{ua.id}_{ub.id}")
    if same_bar_lits:
        md.Add(same_bar == sum(same_bar_lits))
    else:
        md.Add(same_bar == 0)
    hard = rel.strength is Strength.HARD
    K = AdjacencyKind
    if rel.kind in (K.ADJACENT, K.CONNECTED):
        if hard:
            md.Add(touch == 1)
        else:
            obj.append(int(W_ADJ * rel.weight * w("adjacency_quality")) * (1 - touch))
    elif rel.kind is K.NEAR:
        if hard:
            md.Add(same_bar == 1)
        else:
            obj.append(int(W_NEAR * rel.weight * w("adjacency_quality")) * (1 - same_bar))
    elif rel.kind in (K.SEPARATED, K.ACOUSTIC_SEPARATION):
        if hard:
            md.Add(touch == 0)
        else:
            name = "privacy" if rel.kind is K.SEPARATED else "acoustic_zoning"
            obj.append(int(W_ADJ * rel.weight * w(name)) * touch)
