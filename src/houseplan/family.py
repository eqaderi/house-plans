"""Checks for how a family lives in the plan, from references/family.md.

These are judgement-heavy, so they warn rather than block; the owner decides.
"""

from __future__ import annotations

import math

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from .checks import Finding, access_graph
from .geometry import LevelGeom, faces_of, frame_of
from .model import NOISY, PRIVATE_VIEW, SOCIAL, Design, OpeningKind, RoomUse, WallKind

RAY_STEP_DEG = 2
RAY_LENGTH = 30_000  # mm
SHARED_WALL_MIN = 1000  # mm of common wall before two rooms count as neighbours


def _entrance_doors(lg: LevelGeom):
    for og in lg.openings.values():
        if og.opening.kind is OpeningKind.door and og.wall.kind is WallKind.exterior:
            yield og


def check_entry_view(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    """محرمیت: from the open front door, no direct view of a bedroom, bath or WC door."""
    out: list[Finding] = []
    for lg in geo.values():
        see_through = unary_union([og.cut for og in lg.openings.values() if og.opening.kind is OpeningKind.opening])
        solid = lg.walls_union.difference(see_through) if not see_through.is_empty else lg.walls_union
        private_doors = {
            og.opening.id: og.cut
            for og in lg.openings.values()
            if og.opening.kind is OpeningKind.door
            and any(rg.outline is not None and rg.room.use in PRIVATE_VIEW and rg.outline.distance(og.cut) < 1.0 for rg in lg.rooms.values())
        }
        for front in _entrance_doors(lg):
            f = frame_of(front.wall)
            a, b = faces_of(front.wall)
            mid_s = front.opening.offset + front.opening.width / 2
            inward = 1.0 if lg.footprint.contains(Point(f.at(mid_s, b + 100))) else -1.0
            eye = Point(f.at(mid_s, (b if inward > 0 else a) + inward * 10))
            base = math.atan2(f.ny * inward, f.nx * inward)
            seen = set()
            for k in range(-80, 81, RAY_STEP_DEG):
                ang = base + math.radians(k)
                ray = LineString([eye.coords[0], (eye.x + RAY_LENGTH * math.cos(ang), eye.y + RAY_LENGTH * math.sin(ang))])
                hit = ray.intersection(solid)
                stop = min((eye.distance(p) for p in getattr(hit, "geoms", [hit]) if not p.is_empty), default=RAY_LENGTH)
                reach = LineString([eye.coords[0], ray.interpolate(stop).coords[0]]).buffer(1)
                for did, cut in private_doors.items():
                    if did != front.opening.id and reach.intersects(cut):
                        seen.add(did)
            for did in sorted(seen):
                out.append(Finding("ENTRY_VIEW_PRIVATE", "warning", front.opening.id, f"from the open entrance the door {did} of a bedroom, bath or WC is in direct view (محرمیت)"))
    return out


def check_zoning(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        graph = access_graph(lg)
        for rid, rg in lg.rooms.items():
            if rg.outline is None:
                continue
            nbrs = graph.get(rid, {})
            if rg.room.use is RoomUse.bedroom:
                social = sorted(n for n in nbrs if n in lg.rooms and lg.rooms[n].room.use in SOCIAL)
                if social:
                    out.append(Finding("BEDROOM_OFF_SOCIAL", "warning", rid, f"bedroom opens straight onto {social}; give it a hall or vestibule"))
            if "outside" in nbrs and rg.room.use in (RoomUse.living, RoomUse.reception, RoomUse.dining, RoomUse.kitchen):
                out.append(Finding("ENTRY_INTO_LIVING", "warning", rid, "the house is entered straight into a living space; an entry zone (ورودی / کفش‌کن) is missing"))
    return out


def _neighbours(lg: LevelGeom, rid: str) -> dict[str, float]:
    me = lg.rooms[rid].outline
    reach = max((g.wall.thickness for g in lg.walls.values()), default=300) + 10
    out = {}
    for oid, og in lg.rooms.items():
        if oid == rid or og.outline is None:
            continue
        shared = me.buffer(reach).intersection(og.outline.exterior)
        if shared.length >= SHARED_WALL_MIN:
            out[oid] = shared.length
    return out


def check_quiet_bedrooms(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    for lg in geo.values():
        for rid, rg in lg.rooms.items():
            if rg.outline is None or rg.room.use is not RoomUse.bedroom:
                continue
            loud = sorted(o for o in _neighbours(lg, rid) if lg.rooms[o].room.use in NOISY)
            if loud:
                out.append(Finding("BEDROOM_NEXT_TO_NOISE", "info", rid, f"shares a wall with {loud}; consider wardrobes or a buffer between"))
    return out


def _window_bearings(lg: LevelGeom, rid: str, north_deg: float) -> list[float]:
    """Compass bearings (0 = north, 90 = east) that the room's windows face."""
    room = lg.rooms[rid].outline
    out = []
    for og in lg.openings.values():
        if og.opening.kind is not OpeningKind.window or room.distance(og.cut) >= 1.0:
            continue
        f = frame_of(og.wall)
        a, b = faces_of(og.wall)
        mid = og.opening.offset + og.opening.width / 2
        sign = 1.0 if not lg.footprint.contains(Point(f.at(mid, b + 100))) else -1.0
        dx, dy = f.nx * sign, f.ny * sign
        out.append((math.degrees(math.atan2(dx, dy)) + north_deg) % 360)
    return out


def check_daylight_quality(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    out: list[Finding] = []
    north = design.project.north_angle_deg
    for lg in geo.values():
        for rid, rg in lg.rooms.items():
            if rg.outline is None or rg.room.use not in (RoomUse.living, RoomUse.reception, RoomUse.bedroom, RoomUse.dining):
                continue
            bearings = _window_bearings(lg, rid, north)
            sides = {round(b / 90) % 4 for b in bearings}
            if len(sides) < 2 and rg.room.use is not RoomUse.bedroom:
                out.append(Finding("LIGHT_ONE_SIDE", "info", rid, "daylight from one side only; two sides read better (Pattern Language 159)"))
            if rg.room.use in (RoomUse.living, RoomUse.reception) and not any(abs(((b - 180) + 180) % 360 - 180) <= 45 for b in bearings):
                out.append(Finding("LIVING_NOT_SOUTH", "info", rid, "no window within 45° of south; winter sun matters in a cold mountain climate"))
    return out


ALL = (check_entry_view, check_zoning, check_quiet_bedrooms, check_daylight_quality)


def run_family(design: Design, geo: dict[str, LevelGeom]) -> list[Finding]:
    return [f for check in ALL for f in check(design, geo)]
