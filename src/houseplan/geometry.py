"""Deterministic plan geometry derived from the design spec.

Nothing here is typed in by hand: wall bodies, room outlines, opening cuts,
door swings and stair footprints are all computed from the spec, so a number
that appears on a drawing can always be traced back to the spec.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from shapely import set_precision
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .model import Design, Opening, OpeningKind, Room, Stair, Wall

GRID = 0.01  # mm; snapping grid that keeps float noise out of topology tests
TOUCH = 0.5  # mm; a wall end within this distance of another wall touches it


def snap(geom: BaseGeometry) -> BaseGeometry:
    return set_precision(geom, GRID)


@dataclass(frozen=True)
class Frame:
    """Local frame of a wall: origin at `start`, u along the wall, n to its left."""

    ox: float
    oy: float
    ux: float
    uy: float
    length: float

    @property
    def nx(self) -> float:
        return -self.uy

    @property
    def ny(self) -> float:
        return self.ux

    def at(self, s: float, t: float) -> tuple[float, float]:
        return (self.ox + self.ux * s + self.nx * t, self.oy + self.uy * s + self.ny * t)


def frame_of(wall: Wall) -> Frame:
    (x0, y0), (x1, y1) = wall.start, wall.end
    length = math.hypot(x1 - x0, y1 - y0)
    if length == 0:
        return Frame(x0, y0, 1.0, 0.0, 0.0)
    return Frame(x0, y0, (x1 - x0) / length, (y1 - y0) / length, length)


def faces_of(wall: Wall) -> tuple[float, float]:
    """Offsets of the right and left faces from the wall line, along n."""
    t = wall.thickness
    return {"center": (-t / 2, t / 2), "left": (-t, 0.0), "right": (0.0, t)}[wall.justify]


def raw_body(wall: Wall) -> Polygon:
    f = frame_of(wall)
    a, b = faces_of(wall)
    return Polygon([f.at(0, a), f.at(f.length, a), f.at(f.length, b), f.at(0, b)])


def _extension(wall: Wall, at_end: bool, others: list[Wall]) -> float:
    """How far a wall end must run on to fill the junction it sits in."""
    f = frame_of(wall)
    s, sign = (f.length, 1.0) if at_end else (0.0, -1.0)
    p = Point(f.at(s, 0))
    best = 0.0
    for other in others:
        body = raw_body(other)
        if body.distance(p) > TOUCH:
            continue
        far = f.at(s + sign * (other.thickness * 4 + 10_000), 0)
        ray = LineString([p.coords[0], far]).intersection(body.buffer(TOUCH))
        for part in getattr(ray, "geoms", [ray]):
            if part.is_empty or part.distance(p) > TOUCH:
                continue
            best = max(best, part.length - TOUCH)
    return max(best, 0.0)


@dataclass
class WallGeom:
    wall: Wall
    frame: Frame
    s0: float
    s1: float
    body: Polygon
    clear: BaseGeometry = field(default=None)


@dataclass
class OpeningGeom:
    opening: Opening
    wall: Wall
    cut: Polygon
    centre_line: LineString
    swing: Polygon | None


@dataclass
class RoomGeom:
    room: Room
    outline: Polygon | None
    problem: str | None = None

    @property
    def area_mm2(self) -> float:
        return self.outline.area if self.outline is not None else 0.0


@dataclass
class LevelGeom:
    level_id: str
    walls: dict[str, WallGeom]
    walls_union: BaseGeometry
    enclosed: list[Polygon]
    footprint: BaseGeometry
    openings: dict[str, OpeningGeom]
    rooms: dict[str, RoomGeom]
    stairs: dict[str, Polygon]
    balconies: dict[str, Polygon] = field(default_factory=dict)  # outside the footprint, never part of it


def build_walls(walls: list[Wall]) -> dict[str, WallGeom]:
    out: dict[str, WallGeom] = {}
    for w in walls:
        others = [o for o in walls if o.id != w.id]
        f = frame_of(w)
        s0 = -_extension(w, False, others)
        s1 = f.length + _extension(w, True, others)
        a, b = faces_of(w)
        body = snap(Polygon([f.at(s0, a), f.at(s1, a), f.at(s1, b), f.at(s0, b)]))
        out[w.id] = WallGeom(w, f, s0, s1, body)
    for gid, g in out.items():
        rest = unary_union([o.body for oid, o in out.items() if oid != gid])
        g.clear = snap(g.body.difference(rest)) if not rest.is_empty else g.body
    return out


def opening_geom(o: Opening, wg: WallGeom) -> OpeningGeom:
    f, w = wg.frame, wg.wall
    a, b = faces_of(w)
    s0, s1 = o.offset, o.offset + o.width
    cut = snap(Polygon([f.at(s0, a), f.at(s1, a), f.at(s1, b), f.at(s0, b)]))
    centre = LineString([f.at(s0, (a + b) / 2), f.at(s1, (a + b) / 2)])
    swing = None
    if o.kind is OpeningKind.door:
        leaf = o.leaf or o.width
        face = b if o.swing == "left" else a
        side = 1.0 if o.swing == "left" else -1.0
        hinge_s, toward = (s0, 1.0) if o.hinge == "start" else (s1, -1.0)
        pts = [f.at(hinge_s, face)]
        for i in range(0, 91, 3):
            ang = math.radians(i)
            pts.append(f.at(hinge_s + toward * leaf * math.cos(ang), face + side * leaf * math.sin(ang)))
        swing = snap(Polygon(pts))
    return OpeningGeom(o, w, cut, centre, swing)


def stair_footprint(s: Stair) -> Polygon:
    run = (s.risers - 1) * s.going
    x, y = s.origin
    half = s.width / 2
    return {
        "+x": box(x, y - half, x + run, y + half),
        "-x": box(x - run, y - half, x, y + half),
        "+y": box(x - half, y, x + half, y + run),
        "-y": box(x - half, y - run, x + half, y),
    }[s.direction]


def build_level(design: Design, level_id: str) -> LevelGeom:
    walls = [w for w in design.walls if w.level == level_id]
    wgs = build_walls(walls)
    union = snap(unary_union([g.body for g in wgs.values()])) if wgs else Polygon()
    parts = list(getattr(union, "geoms", [union])) if not union.is_empty else []
    enclosed = [snap(Polygon(ring).difference(union)) for part in parts for ring in part.interiors]
    enclosed = [e for e in enclosed if not e.is_empty and e.area > 1.0]
    footprint = snap(unary_union([Polygon(p.exterior) for p in parts])) if parts else Polygon()

    openings = {
        o.id: opening_geom(o, wgs[o.wall]) for o in design.openings if o.wall in wgs
    }

    rooms: dict[str, RoomGeom] = {}
    for r in (r for r in design.rooms if r.level == level_id):
        seed = Point(r.seed)
        hit = [e for e in enclosed if e.contains(seed)]
        if hit:
            rooms[r.id] = RoomGeom(r, hit[0])
        elif union.contains(seed) or union.touches(seed):
            rooms[r.id] = RoomGeom(r, None, "seed lies inside a wall")
        else:
            rooms[r.id] = RoomGeom(r, None, "seed is not in any space enclosed by walls")

    stairs = {s.id: stair_footprint(s) for s in design.stairs if s.level == level_id}
    balconies = {b.id: snap(Polygon(b.outline)) for b in design.balconies if b.level == level_id}
    return LevelGeom(level_id, wgs, union, enclosed, footprint, openings, rooms, stairs, balconies)


def build(design: Design) -> dict[str, LevelGeom]:
    return {l.id: build_level(design, l.id) for l in design.levels}


def sides_of(poly: Polygon) -> tuple[float, float]:
    """Short and long side of the smallest rotated rectangle around a polygon."""
    with np.errstate(divide="ignore", invalid="ignore"):
        r = poly.minimum_rotated_rectangle
    xs = list(r.exterior.coords)
    a = math.dist(xs[0], xs[1])
    b = math.dist(xs[1], xs[2])
    return min(a, b), max(a, b)


def side_probe(og: OpeningGeom, side: float, depth: float = 100.0) -> Point:
    """A point just beyond the wall face, at the middle of the opening."""
    wg_frame = frame_of(og.wall)
    a, b = faces_of(og.wall)
    s = og.opening.offset + og.opening.width / 2
    t = (b + depth) if side > 0 else (a - depth)
    return Point(wg_frame.at(s, t))
