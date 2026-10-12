"""Geometry and consistency checks that hold in every jurisdiction.

Each check returns Findings. An `error` blocks the build; a `warning` must be
read and either fixed or explained; `info` is reported for the record.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from typing import Literal

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from .geometry import TOUCH, LevelGeom, lift_shafts, raw_body, side_probe, sides_of
from .model import HABITABLE, WET, Design, OpeningKind, RoomUse

AREA_EPS = 1.0  # mm²; overlaps smaller than this are float noise
MIN_JAMB = 100  # mm; nearest an opening may come to a wall junction before warning
SLIVER = 300  # mm; a room with no part this wide is a drafting accident
MAX_ASPECT = 3.0  # room proportion beyond which furnishing suffers (GFLAN, arXiv 2512.16275)
CIRCULATION_DETOUR = 1.5  # walking route / straight line from the entrance (GFLAN)
SITE_TOL = 1.0  # mm; site points are rounded to whole mm when converted from the survey


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Literal["error", "warning", "info"]
    subject: str
    message: str

    def as_dict(self) -> dict:
        return asdict(self)


def _err(code, subject, message):
    return Finding(code, "error", subject, message)


def _warn(code, subject, message):
    return Finding(code, "warning", subject, message)


def check_walls(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    allowed = set(design.project.allowed_wall_thicknesses)
    for w in design.walls:
        if w.start == w.end:
            out.append(_err("WALL_ZERO_LENGTH", w.id, "start and end are the same point"))
        if w.thickness not in allowed:
            out.append(_err("WALL_THICKNESS", w.id, f"{w.thickness} mm is not in allowed_wall_thicknesses {sorted(allowed)}"))
    for lg in geo.values():
        for g in lg.walls.values():
            others = [o.wall for o in lg.walls.values() if o.wall.id != g.wall.id]
            for name, end in (("start", g.wall.start), ("end", g.wall.end)):
                if all(raw_body(o).distance(Point(end)) > TOUCH for o in others):
                    out.append(_warn("WALL_END_FREE", g.wall.id, f"{name} {end} touches no other wall; intended free-standing end?"))
        items = list(lg.walls.values())
        for i, a in enumerate(items):
            for b in items[i + 1 :]:
                if a.frame.length == 0 or b.frame.length == 0:
                    continue
                cross = abs(a.frame.ux * b.frame.uy - a.frame.uy * b.frame.ux)
                if cross > 1e-9:
                    continue
                overlap = a.body.intersection(b.body).area
                if overlap > AREA_EPS:
                    out.append(_err("WALL_OVERLAP", f"{a.wall.id}/{b.wall.id}", f"parallel walls overlap by {overlap / 1e6:.4f} m²"))
    return out


def check_openings(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        by_wall: dict[str, list] = {}
        for og in lg.openings.values():
            o, wg = og.opening, lg.walls[og.wall.id]
            by_wall.setdefault(o.wall, []).append(og)
            if o.offset + o.width > wg.frame.length:
                out.append(_err("OPENING_PAST_WALL_END", o.id, f"runs {o.offset + o.width - wg.frame.length:.0f} mm past the end of {o.wall}"))
            spill = og.cut.difference(wg.clear.buffer(0.01)).area
            if spill > AREA_EPS:
                out.append(_err("OPENING_IN_JUNCTION", o.id, f"cuts {spill / 1e6:.4f} m² into a crossing wall"))
            else:
                rest = unary_union([g.body for k, g in lg.walls.items() if k != o.wall])
                gap = og.cut.distance(rest) if not rest.is_empty else float("inf")
                if gap < MIN_JAMB:
                    out.append(_warn("OPENING_NEAR_JUNCTION", o.id, f"jamb is {gap:.0f} mm from a crossing wall (< {MIN_JAMB} mm)"))
            clear = design.level(design.wall(o.wall).level).clear_height
            if o.sill + o.height > clear:
                out.append(_err("OPENING_TOO_TALL", o.id, f"sill {o.sill} + height {o.height} exceeds clear height {clear}"))
            if o.kind is OpeningKind.door and o.sill != 0:
                out.append(_warn("DOOR_SILL", o.id, f"door has a {o.sill} mm sill"))
        for wid, ogs in by_wall.items():
            ogs.sort(key=lambda g: g.opening.offset)
            for a, b in zip(ogs, ogs[1:]):
                pier = b.opening.offset - (a.opening.offset + a.opening.width)
                if pier < 0:
                    out.append(_err("OPENING_OVERLAP", f"{a.opening.id}/{b.opening.id}", f"overlap by {-pier} mm in {wid}"))
                elif pier < MIN_JAMB:
                    out.append(_warn("NARROW_PIER", f"{a.opening.id}/{b.opening.id}", f"pier between openings is {pier} mm"))
    return out


def check_rooms(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        claimed: dict[int, str] = {}
        for rg in lg.rooms.values():
            if rg.outline is None:
                out.append(_err("ROOM_NOT_ENCLOSED", rg.room.id, rg.problem or "no outline"))
                continue
            if not rg.outline.is_valid:
                out.append(_err("ROOM_INVALID", rg.room.id, "outline is not a valid polygon"))
            key = id(rg.outline)
            if key in claimed:
                out.append(_err("ROOM_SHARED", f"{claimed[key]}/{rg.room.id}", "two rooms resolve to the same enclosed space; a separating wall is missing"))
            claimed[key] = rg.room.id
        named = {id(rg.outline) for rg in lg.rooms.values() if rg.outline is not None}
        for e in lg.enclosed:
            if id(e) not in named:
                c = e.representative_point()
                out.append(_warn("SPACE_UNNAMED", lg.level_id, f"enclosed space of {e.area / 1e6:.2f} m² near ({c.x:.0f}, {c.y:.0f}) has no room"))
    return out


def _room_at(lg: LevelGeom, p: Point) -> str | None:
    for rid, rg in lg.rooms.items():
        if rg.outline is not None and rg.outline.contains(p):
            return rid
    if lg.footprint.contains(p):
        return "?"
    for bid, b in lg.balconies.items():
        if b.contains(p):
            return bid
    return "outside"


def access_graph(lg: LevelGeom) -> dict[str, dict[str, list[Point]]]:
    """Rooms and balconies joined by doors and openings: room -> neighbour ->
    door centres. The neighbour is "outside" for an exterior door and "?" for
    unnamed space."""
    graph: dict[str, dict[str, list[Point]]] = {rid: {} for rid in (*lg.rooms, *lg.balconies)}
    for og in lg.openings.values():
        if og.opening.kind is OpeningKind.window:
            continue
        left, right = _room_at(lg, side_probe(og, 1)), _room_at(lg, side_probe(og, -1))
        mid = og.centre_line.interpolate(0.5, normalized=True)
        for a, b in ((left, right), (right, left)):
            if a in graph:
                graph[a].setdefault(b, []).append(mid)
    return graph


def _starts(lg: LevelGeom, graph) -> list[str]:
    return [
        rid for rid, rg in lg.rooms.items()
        if rg.room.entrance or "outside" in graph.get(rid, {}) or rg.room.use in (RoomUse.stair, RoomUse.lift)
    ]


def _reach(graph, starts, blocked=frozenset()) -> set[str]:
    seen = set(starts)
    queue = deque(starts)
    while queue:
        here = queue.popleft()
        if here in blocked and here not in starts:
            continue
        for nxt in graph.get(here, {}):
            if nxt in graph and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def check_doors_and_access(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        graph = access_graph(lg)
        others = unary_union([og.swing for og in lg.openings.values() if og.swing is not None])
        for og in lg.openings.values():
            o = og.opening
            if o.kind is OpeningKind.window:
                continue
            left, right = _room_at(lg, side_probe(og, 1)), _room_at(lg, side_probe(og, -1))
            if left == right:
                out.append(_warn("OPENING_SAME_ROOM", o.id, f"both sides are {left}"))
            uses = {lg.rooms[r].room.use for r in (left, right) if r in lg.rooms}
            if left != right and uses == {RoomUse.bedroom}:
                out.append(_warn("BEDROOM_TO_BEDROOM", o.id, f"connects two bedrooms ({left}, {right})"))
            if og.swing is None:
                continue
            walls = unary_union([g.body for k, g in lg.walls.items() if k != o.wall])
            hit = og.swing.intersection(walls).area
            if hit > AREA_EPS:
                out.append(_err("DOOR_SWING_HITS_WALL", o.id, f"leaf sweeps {hit / 1e6:.4f} m² of wall"))
            for sid, sp in lg.stairs.items():
                if og.swing.intersection(sp).area > AREA_EPS:
                    out.append(_err("DOOR_SWING_HITS_STAIR", o.id, f"leaf sweeps over stair {sid}"))
            mine = others.difference(og.swing.buffer(0.01)) if not others.is_empty else others
            clash = og.swing.intersection(mine).area if not mine.is_empty else 0
            if clash > AREA_EPS:
                out.append(_warn("DOOR_SWINGS_CLASH", o.id, f"leaf sweep overlaps another door's by {clash / 1e6:.4f} m²"))
        seen = _reach(graph, _starts(lg, graph))
        for rid, rg in lg.rooms.items():
            if rg.outline is not None and rid not in seen:
                out.append(_err("ROOM_UNREACHABLE", rid, "no route through doors or openings from an entrance or a stair"))
    return out


def check_pass_through(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    """No room may be reachable only by walking through a private room,
    unless it names that room in `via` (an en-suite bath, a walk-in closet)."""
    out: list[Finding] = []
    private = set(design.program.private_uses)
    for lg in geo.values():
        graph = access_graph(lg)
        starts = _starts(lg, graph)
        everyone = _reach(graph, starts)
        blocked = frozenset(rid for rid, rg in lg.rooms.items() if rg.room.use in private)
        for rid, rg in lg.rooms.items():
            if rid not in everyone or rid in starts:
                continue
            allowed = blocked - {rg.room.via} if rg.room.via else blocked
            if rid not in _reach(graph, starts, allowed - {rid}):
                via = sorted(n for n in graph.get(rid, {}) if n in blocked)
                out.append(_err("PASS_THROUGH_PRIVATE", rid, f"reached only through private room(s) {via}; add a route or set via"))
    return out


def _path_ratio(lg: LevelGeom, graph, start: str, target: str) -> float | None:
    """Walking distance from the entrance door to a room's centre, through
    door centres, divided by the straight-line distance."""
    entries = [p for rid in [start] for n, pts in graph.get(rid, {}).items() if n == "outside" for p in pts]
    if not entries:
        entries = [lg.rooms[start].outline.representative_point()]
    origin = entries[0]
    goal = lg.rooms[target].outline.representative_point()
    best = {start: (0.0, origin)}
    frontier = [(0.0, start, origin)]
    while frontier:
        frontier.sort(key=lambda x: x[0])
        d, here, at = frontier.pop(0)
        if here == target:
            break
        for nxt, pts in graph.get(here, {}).items():
            if nxt not in lg.rooms or lg.rooms[nxt].outline is None:
                continue
            for p in pts:
                nd = d + at.distance(p)
                if nxt not in best or nd < best[nxt][0]:
                    best[nxt] = (nd, p)
                    frontier.append((nd, nxt, p))
    if target not in best:
        return None
    walk = best[target][0] + best[target][1].distance(goal)
    straight = origin.distance(goal)
    return walk / straight if straight > 0 else None


def check_circulation(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        graph = access_graph(lg)
        entrances = [rid for rid, rg in lg.rooms.items() if rg.outline is not None and (rg.room.entrance or "outside" in graph.get(rid, {}))]
        if not entrances:
            continue
        start = entrances[0]
        for rid, rg in lg.rooms.items():
            if rid == start or rg.outline is None:
                continue
            ratio = _path_ratio(lg, graph, start, rid)
            if ratio is not None and ratio > CIRCULATION_DETOUR:
                out.append(_warn("CIRCULATION_DETOUR", rid, f"walking route from the entrance is {ratio:.2f}x the straight line (> {CIRCULATION_DETOUR})"))
        circ = sum(rg.area_mm2 for rg in lg.rooms.values() if rg.room.use in (RoomUse.corridor, RoomUse.hall))
        net = sum(rg.area_mm2 for rg in lg.rooms.values())
        if net:
            out.append(Finding("CIRCULATION_SHARE", "info", lg.level_id, f"corridors and halls are {circ / net:.0%} of net area"))
    return out


def check_room_shape(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        for rid, rg in lg.rooms.items():
            if rg.outline is None:
                continue
            if rg.outline.buffer(-SLIVER / 2).is_empty:
                out.append(_err("ROOM_SLIVER", rid, f"no part of the room is {SLIVER} mm wide"))
                continue
            if rg.room.use in (RoomUse.corridor, RoomUse.hall, RoomUse.stair):
                continue
            short, long = sides_of(rg.outline)
            if short and long / short > MAX_ASPECT:
                out.append(_warn("ROOM_ASPECT", rid, f"proportion {long / short:.1f}:1 (> {MAX_ASPECT}:1) is hard to furnish"))
    return out


def check_program(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    prog = design.program
    found = [rg for lg in geo.values() for rg in lg.rooms.values() if rg.outline is not None]
    for req in prog.required:
        have = sum(rg.room.use is req.use for rg in found)
        if have < req.count:
            out.append(_err("PROGRAM_MISSING", req.use.value, f"brief asks for {req.count}, plan has {have}"))
    for rg in found:
        t = rg.room.target_area
        if t is None:
            continue
        a = rg.area_mm2 / 1e6
        if abs(a - t) / t > prog.area_tolerance:
            out.append(_warn("AREA_OFF_TARGET", rg.room.id, f"{a:.2f} m² vs brief {t:.2f} m² ({(a - t) / t:+.0%}, tolerance ±{prog.area_tolerance:.0%})"))
    for a, b in prog.connect:
        ok = any(b in access_graph(lg).get(a, {}) for lg in geo.values())
        if not ok:
            out.append(_err("CONNECTION_MISSING", f"{a}/{b}", "brief asks for a door or opening between these rooms"))
    return out


def check_stairs(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for s in design.stairs:
        lo, hi = design.level(s.level), design.level(s.to_level)
        climb = hi.ffl - lo.ffl
        if climb <= 0:
            out.append(_err("STAIR_DIRECTION", s.id, f"{s.to_level} is not above {s.level}"))
            continue
        rise = climb / s.risers
        out.append(Finding("STAIR_RISE", "info", s.id, f"{s.risers} risers × {rise:.2f} mm = {climb} mm; going {s.going} mm; 2R+G = {2 * rise + s.going:.1f} mm"))
        lg = geo[s.level]
        fp = lg.stairs[s.id]
        if fp.intersection(lg.walls_union).area > AREA_EPS:
            out.append(_err("STAIR_IN_WALL", s.id, "stair footprint runs into a wall"))
        host = [rid for rid, rg in lg.rooms.items() if rg.outline is not None and rg.outline.buffer(0.01).contains(fp)]
        if not host:
            out.append(_err("STAIR_NOT_IN_ROOM", s.id, f"footprint is not inside one room on {s.level}"))
        up = geo[s.to_level]
        well = unary_union([rg.outline for rg in up.rooms.values() if rg.outline is not None and rg.room.use is RoomUse.stair])
        if well.is_empty or not well.buffer(0.01).contains(fp):
            out.append(_warn("STAIR_NO_WELL", s.id, f"no stair room on {s.to_level} covers the run; check the slab opening and headroom"))
    return out


def check_stacking(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    ordered = sorted(design.levels, key=lambda l: l.ffl)
    for below, above in zip(ordered, ordered[1:]):
        lower = geo[below.id]
        bearing = unary_union([g.body for g in lower.walls.values() if g.wall.loadbearing])
        for g in geo[above.id].walls.values():
            if not g.wall.loadbearing:
                continue
            carried = g.body.intersection(bearing).area / g.body.area if g.body.area else 0
            if carried < 0.95:
                out.append(_warn("BEARING_NOT_STACKED", g.wall.id, f"only {carried:.0%} sits on a load-bearing wall of {below.id}"))
        wet_below = unary_union([r.outline for r in lower.rooms.values() if r.outline is not None and r.room.use in WET])
        for r in geo[above.id].rooms.values():
            if r.outline is not None and r.room.use in WET and r.room.use is not RoomUse.kitchen:
                if wet_below.is_empty or r.outline.intersection(wet_below).area < 0.25 * r.outline.area:
                    out.append(Finding("WET_NOT_STACKED", "info", r.room.id, f"wet room is not above a wet room on {below.id}; plan the drainage route"))
    return out


def check_daylight_presence(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        for rid, rg in lg.rooms.items():
            if rg.outline is None or rg.room.use not in HABITABLE:
                continue
            windows = [og for og in lg.openings.values() if og.opening.kind is OpeningKind.window and rg.outline.distance(og.cut) < 1.0 and og.wall.kind.value == "exterior"]
            if not windows:
                out.append(_err("NO_WINDOW", rid, "habitable room has no window in an exterior wall"))
    return out


def check_lifts(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    """Each lift: one shaft room of use `lift` per served level, stacked, with
    a landing door or opening on every level, and a car that fits the shaft."""
    out: list[Finding] = []
    listed = {r for lift in design.lifts for r in lift.shafts}
    for lg in geo.values():
        for rid, rg in lg.rooms.items():
            if rg.room.use is RoomUse.lift and rid not in listed:
                out.append(_warn("LIFT_UNLISTED", rid, "lift room is not a shaft of any entry in lifts"))
    for lift in design.lifts:
        rooms = [rg for lg in geo.values() for rid, rg in lg.rooms.items() if rid in lift.shafts]
        wrong = [rg.room.id for rg in rooms if rg.room.use is not RoomUse.lift]
        if wrong:
            out.append(_err("LIFT_ROOM_USE", lift.id, f"shaft rooms {wrong} do not have use lift"))
        levels = [rg.room.level for rg in rooms]
        if len(set(levels)) != len(levels):
            out.append(_err("LIFT_LEVELS", lift.id, f"two shaft rooms on one level: {sorted(levels)}"))
        if any(rg.outline is None for rg in rooms):
            continue
        for rg in rooms:
            lg = geo[rg.room.level]
            if not [n for n in access_graph(lg).get(rg.room.id, {}) if n in lg.rooms and lg.rooms[n].room.use is not RoomUse.lift]:
                out.append(_err("LIFT_NO_DOOR", rg.room.id, f"no landing door or opening on {rg.room.level}"))
        common = lift_shafts(design, geo)[lift.id]
        for rg in rooms:
            share = common.area / rg.outline.area if rg.outline.area else 0
            if share < 0.95:
                out.append(_err("LIFT_NOT_STACKED", rg.room.id, f"only {share:.0%} of this shaft is clear on every served level"))
        short, long = sides_of(common) if not common.is_empty else (0, 0)
        cw, cd = sorted(lift.car)
        if cw > short or cd > long:
            out.append(_err("LIFT_CAR_IN_SHAFT", lift.id, f"car {lift.car[0]} x {lift.car[1]} mm does not fit the clear shaft {short:.0f} x {long:.0f} mm"))
    return out


def check_garage_entrance(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    """The cars must physically pass the garage's way in: some exterior door
    or opening at least as wide as the widest car body and as tall as the
    tallest. No clearance is added; that is a rule's business, with a source."""
    cars = design.program.vehicles
    if not cars:
        return []
    width = max(c.width for c in cars)
    height = max((c.height for c in cars if c.height), default=0)
    out: list[Finding] = []
    for lg in geo.values():
        for rid, rg in lg.rooms.items():
            if rg.outline is None or rg.room.use is not RoomUse.garage:
                continue
            ways = [og.opening for og in lg.openings.values()
                    if og.opening.kind is not OpeningKind.window and "outside" in {_room_at(lg, side_probe(og, 1)), _room_at(lg, side_probe(og, -1))}
                    and rid in {_room_at(lg, side_probe(og, 1)), _room_at(lg, side_probe(og, -1))}]
            if not any((o.leaf or o.width) >= width and o.height >= height for o in ways):
                have = ", ".join(f"{o.id} {o.leaf or o.width} x {o.height}" for o in ways) or "none"
                out.append(_err("GARAGE_ENTRANCE", rid, f"no way in for a car {width} mm wide and {height} mm tall (exterior openings: {have})"))
    return out


def built_area(design: Design, geo: dict[str, LevelGeom]):
    """Everything built, on any level, seen from above, balconies included."""
    return unary_union([g for lg in geo.values() for g in (lg.footprint, *lg.balconies.values()) if not g.is_empty])


def check_balconies(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        graph = access_graph(lg)
        for bid, b in lg.balconies.items():
            if not b.is_valid or b.area <= AREA_EPS:
                out.append(_err("BALCONY_INVALID", bid, "outline is not a valid polygon with area"))
                continue
            inside = b.intersection(lg.footprint).area
            if inside > AREA_EPS:
                out.append(_err("BALCONY_OVERLAPS_BUILDING", bid, f"{inside / 1e6:.3f} m² lies inside the walls; a balcony is outside them"))
            elif b.distance(lg.footprint) > TOUCH:
                out.append(_err("BALCONY_DETACHED", bid, f"{b.distance(lg.footprint):.0f} mm from the outer wall face of {lg.level_id}"))
            for other, ob in lg.balconies.items():
                if other > bid and b.intersection(ob).area > AREA_EPS:
                    out.append(_err("BALCONY_OVERLAP", f"{bid}/{other}", "balconies overlap; make them one outline"))
            if not [n for n in graph.get(bid, {}) if n in lg.rooms]:
                out.append(_warn("BALCONY_NO_DOOR", bid, "no door or opening leads onto it from a room"))
            out.append(Finding("BALCONY_GUARD_UNCHECKED", "info", bid, "guard (railing) height not checked: no cited value in rules/ yet"))
    return out


def check_site(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    """The building stays inside the plot and out of its no-build zones.
    A wall face on the boundary is allowed (the brief allows building on the
    road line), within SITE_TOL."""
    site = design.site
    if site is None:
        return [Finding("SITE_NOT_SET", "info", "site", "no site block: plot boundary and no-build zones not checked")]
    out: list[Finding] = []
    built = built_area(design, geo)
    if built.is_empty:
        return out
    outside = built.difference(Polygon(site.boundary).buffer(SITE_TOL)).area
    if outside > AREA_EPS:
        out.append(_err("SITE_OUTSIDE_BOUNDARY", "site", f"{outside / 1e6:.3f} m² of the building lies outside the plot boundary"))
    for zone in site.no_build:
        inside = built.intersection(Polygon(zone.outline).buffer(-SITE_TOL)).area
        if inside > AREA_EPS:
            out.append(_err("SITE_IN_NO_BUILD", zone.name, f"{inside / 1e6:.3f} m² of the building lies in the no-build zone"))
    return out


ALL = (
    check_walls,
    check_openings,
    check_rooms,
    check_room_shape,
    check_doors_and_access,
    check_pass_through,
    check_circulation,
    check_program,
    check_stairs,
    check_stacking,
    check_daylight_presence,
    check_balconies,
    check_lifts,
    check_garage_entrance,
    check_site,
)


def run_all(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    return [f for check in ALL for f in check(design, geo)]
