"""Everyday use, tested cheaply on the plan (owner, docs/brief.md "Everyday
use"): walking routes between rooms across levels, what can be seen from the
living room and from the open front door, and living rooms over bedrooms.

Routes are straight lines between door centres inside each room, so a length
is a lower bound on the real walk. Sight lines treat doors as closed and only
`opening`s as see-through. The visibility shares and their 10 % warning
threshold are judgement defaults, not regulation values.
"""

from __future__ import annotations

import heapq
import math
from itertools import count

from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.prepared import prep

from .checks import Finding, _room_at
from .geometry import LevelGeom, faces_of, frame_of, side_probe, stair_ends
from .model import Design, OpeningKind, RoomUse, WallKind

SEEN_SHARE_WARN = 0.10  # judgement: a glimpse is fine, a tenth of the room is a view
SOCIAL = {RoomUse.living, RoomUse.reception, RoomUse.dining, RoomUse.kitchen}
SITTING = {RoomUse.living, RoomUse.reception}
TOILETS = {RoomUse.wc, RoomUse.bath}
OVERLAP_MIN = 1.0e6  # mm², ignore wall-thickness slivers


# --- routes -----------------------------------------------------------------

def _graph(design: Design, geo: dict[str, LevelGeom]):
    """Nodes are door centres, stair ends and lift shafts; each node lies in
    one or two rooms. Within a room every pair of its nodes is joined by a
    straight line."""
    where: dict[tuple, Point] = {}
    rooms_of: dict[tuple, list[tuple[str, str]]] = {}
    extra: list[tuple[tuple, tuple, float, str]] = []
    for lid, lg in geo.items():
        for oid, og in lg.openings.items():
            if og.opening.kind is OpeningKind.window:
                continue
            node = ("door", oid)
            where[node] = og.centre_line.interpolate(0.5, normalized=True)
            rooms_of[node] = [(lid, r) for r in {_room_at(lg, side_probe(og, 1)), _room_at(lg, side_probe(og, -1))} if r in lg.rooms]
    for s in design.stairs:
        b, t = stair_ends(s)
        bottom, top = Point(b), Point(t)
        run = sum((k - 1) * s.going for k in s.flight_risers) + (s.landing_depth if len(s.flight_risers) > 1 else 0)
        climb = design.level(s.to_level).ffl - design.level(s.level).ffl
        for node, lid, p in ((("stair", s.id, "bottom"), s.level, bottom), (("stair", s.id, "top"), s.to_level, top)):
            where[node] = p
            r = _room_at(geo[lid], p)
            rooms_of[node] = [(lid, r)] if r in geo[lid].rooms else []
        extra.append((("stair", s.id, "bottom"), ("stair", s.id, "top"), math.hypot(run, climb), "stair"))
    for lift in design.lifts:
        nodes = []
        for rid in lift.shafts:
            lid = next((l for l, lg in geo.items() if rid in lg.rooms), None)
            if lid is None or geo[lid].rooms[rid].outline is None:
                continue
            node = ("lift", lift.id, rid)
            where[node] = geo[lid].rooms[rid].outline.representative_point()
            rooms_of[node] = [(lid, rid)]
            nodes.append(node)
        extra += [(a, b, 0.0, "lift") for a in nodes for b in nodes if a != b]
    return where, rooms_of, extra


def _walk(design, geo, graph, a: str, b: str, use_lift: bool):
    where, rooms_of, extra = graph
    loc = {rid: lid for lid, lg in geo.items() for rid in lg.rooms}
    if a not in loc or b not in loc:
        return None
    start, end = ("start", a), ("end", b)
    pts = dict(where)
    pts[start] = geo[loc[a]].rooms[a].outline.representative_point()
    pts[end] = geo[loc[b]].rooms[b].outline.representative_point()
    members: dict[tuple[str, str], list] = {}
    for node, rs in rooms_of.items():
        for r in rs:
            members.setdefault(r, []).append(node)
    members.setdefault((loc[a], a), []).append(start)
    members.setdefault((loc[b], b), []).append(end)
    adj: dict = {}
    for room, nodes in members.items():
        for u in nodes:
            for v in nodes:
                if u != v:
                    adj.setdefault(u, []).append((v, pts[u].distance(pts[v]), room[1]))
    for u, v, cost, kind in extra:
        if (kind == "lift") == use_lift:
            adj.setdefault(u, []).append((v, cost, kind))
    tie = count()
    best = {start: 0.0}
    prev: dict = {}
    heap = [(0.0, next(tie), start)]
    while heap:
        d, _, u = heapq.heappop(heap)
        if u == end:
            break
        if d > best.get(u, math.inf):
            continue
        for v, w, via in adj.get(u, []):
            if d + w < best.get(v, math.inf):
                best[v] = d + w
                prev[v] = (u, via)
                heapq.heappush(heap, (d + w, next(tie), v))
    if end not in best:
        return None
    steps, node = [], end
    while node != start:
        node, via = prev[node]
        steps.append(via)
    steps.reverse()
    rooms = []
    for via in steps:
        if via not in ("stair", "lift") and (not rooms or rooms[-1] != via):
            rooms.append(via)
    return best[end], rooms, steps.count("stair"), steps.count("lift")


def check_routes(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    if not design.program.scenarios:
        return out
    graph = _graph(design, geo)
    use_of = {rid: rg.room.use for lg in geo.values() for rid, rg in lg.rooms.items()}
    private = set(design.program.private_uses)
    for sc in design.program.scenarios:
        total, flights, rides, path, failed = 0.0, 0, 0, [], None
        for a, b in zip(sc.route, sc.route[1:]):
            leg = _walk(design, geo, graph, a, b, sc.lift)
            if leg is None:
                failed = (a, b)
                break
            d, rooms, f, r = leg
            total, flights, rides = total + d, flights + f, rides + r
            path += rooms if not path else rooms[1:] if rooms and rooms[0] == path[-1] else rooms
        if failed:
            out.append(Finding("ROUTE_NONE", "warning", sc.name, f"no way from {failed[0]} to {failed[1]}" + (" by lift" if sc.lift else " on foot")))
            continue
        how = f"{rides} lift ride(s)" if sc.lift else f"{flights} flight(s) of stairs"
        out.append(Finding("ROUTE", "info", sc.name, f"{' → '.join(path)}: {total / 1000:.1f} m walked (straight lines between doors), {how}"))
        crossed = sorted({r for r in path if r not in sc.route and use_of.get(r) in private})
        if crossed:
            out.append(Finding("ROUTE_THROUGH_PRIVATE", "warning", sc.name, f"passes through {crossed}"))
    return out


# --- sight lines ------------------------------------------------------------

def _samples(poly, step: float) -> list[Point]:
    inner = poly.buffer(-300)
    if inner.is_empty:
        return [poly.representative_point()]
    x0, y0, x1, y1 = inner.bounds
    pts = [Point(x0 + step / 2 + i * step, y0 + step / 2 + j * step)
           for i in range(int((x1 - x0) // step) + 1) for j in range(int((y1 - y0) // step) + 1)]
    pts = [p for p in pts if inner.contains(p)]
    return pts or [inner.representative_point()]


def _solid(lg: LevelGeom):
    see = unary_union([og.cut for og in lg.openings.values() if og.opening.kind is OpeningKind.opening])
    return lg.walls_union.difference(see) if not see.is_empty else lg.walls_union


def _sees(eyes, target: Point, solid) -> bool:
    return any(not solid.intersects(LineString([e.coords[0], target.coords[0]])) for e in eyes)


def _rooms(lg: LevelGeom, uses):
    return [(rid, rg) for rid, rg in lg.rooms.items() if rg.outline is not None and rg.room.use in uses]


def check_views(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        solid = _solid(lg)
        seats = _rooms(lg, SITTING)
        for sid, srg in seats:
            eyes = _samples(srg.outline, 600)
            for og in lg.openings.values():
                if og.opening.kind is not OpeningKind.door:
                    continue
                wc = [rid for rid, rg in _rooms(lg, TOILETS) if rg.outline.distance(og.cut) < 1.0]
                if not wc:
                    continue
                mid = og.centre_line.interpolate(0.5, normalized=True)
                if _sees(eyes, mid, prep(solid.difference(og.cut.buffer(1)))):
                    out.append(Finding("LIVING_SEES_WC", "warning", og.opening.id, f"from the living room {sid}, the door of {wc[0]} is in view: whoever goes in is seen going in"))
            p_solid = prep(solid)
            for kid, krg in _rooms(lg, {RoomUse.kitchen}):
                pts = _samples(krg.outline, 500)
                seen = sum(_sees(eyes, p, p_solid) for p in pts) / len(pts)
                if seen > 0:
                    sev = "warning" if seen >= SEEN_SHARE_WARN else "info"
                    out.append(Finding("KITCHEN_SEEN", sev, kid, f"{seen:.0%} of the kitchen floor is in view from the living room {sid}"))
        for og in lg.openings.values():
            if og.opening.kind is not OpeningKind.door or og.wall.kind is not WallKind.exterior:
                continue
            f = frame_of(og.wall)
            a, b = faces_of(og.wall)
            s = og.opening.offset + og.opening.width / 2
            inward = 1.0 if lg.footprint.contains(Point(f.at(s, b + 100))) else -1.0
            if any(bal.contains(Point(f.at(s, (a if inward > 0 else b) - inward * 100))) for bal in lg.balconies.values()):
                continue  # a balcony door is not an entrance
            eye = [Point(f.at(s, (b if inward > 0 else a) + inward * 10))]
            p_solid = prep(solid)
            for sid, srg in seats:
                pts = _samples(srg.outline, 600)
                seen = sum(_sees(eye, p, p_solid) for p in pts) / len(pts)
                if seen >= SEEN_SHARE_WARN:
                    out.append(Finding("ENTRY_SEES_LIVING", "warning", og.opening.id, f"from the open door, {seen:.0%} of the living room {sid} is in view"))
    return out


# --- noise between floors ------------------------------------------------------

def check_living_over_bedrooms(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    levels = sorted(design.levels, key=lambda lv: lv.ffl)
    for lo, hi in zip(levels, levels[1:]):
        for upper, lower, word in ((geo[hi.id], geo[lo.id], "over"), (geo[lo.id], geo[hi.id], "under")):
            for sid, srg in _rooms(upper, SOCIAL):
                for bid, brg in _rooms(lower, {RoomUse.bedroom}):
                    area = srg.outline.intersection(brg.outline).area
                    if area >= OVERLAP_MIN:
                        sev = "warning" if srg.room.use in SITTING else "info"  # the TV at night is the owner's case
                        out.append(Finding("LIVING_OVER_BEDROOM", sev, sid, f"{srg.room.use.value} {word} bedroom {bid} on {lower.level_id} for {area / 1e6:.1f} m²: TV and footsteps at night"))
    return out


ALL = (check_routes, check_views, check_living_over_bedrooms)


def run_usability(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    return [f for check in ALL for f in check(design, geo)]
