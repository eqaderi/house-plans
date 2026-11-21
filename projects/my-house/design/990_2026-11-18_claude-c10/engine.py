"""Drawing + checking engine for Claude C10 (exploratory concept, nothing stored in ProjectStore).

Copied from ../991_2026-10-27_claude-c09 and extended: ground platforms that follow the contours,
a finished-ground model shared by the sections, the checks and the 3D model, and a four-panel
section sheet (two west-east, two north-south).

Frame: the owner's 0109-r5 frame. u = metres along the north boundary towards field east
(downhill), v = metres towards field south. Origin = NW parcel corner. Sheets are drawn with
grid north up, so the house appears rotated like the owner's own drawings.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.site import Site
from house_ai.generation.frame import DesignFrame, Ground
from house_ai.geospatial.earthworks import integrate
from house_ai.storage import ProjectStore

HERE = Path(__file__).resolve().parent
store = ProjectStore(HERE.parents[1])
site = store.get(store.latest(ArtifactKind.SITE, "site"), Site)
_NW, _SW, _SE, _NE = site.boundary.outer
_L = math.dist(_NW, _NE)
_E = ((_NE[0] - _NW[0]) / _L, (_NE[1] - _NW[1]) / _L)
frame = DesignFrame(_NW, _E, (_E[1], -_E[0]), "C10: u along north edge, v field south", None, None)
ground = Ground(site, frame)
PARCEL = Polygon([frame.to_design(p) for p in site.boundary.outer])
ENVELOPE = Polygon([frame.to_design(p) for p in site.buildable_envelope.polygon.outer])
# Bearing of +u from grid north; the sheet rotates the house so grid north is up.
U_BEARING = math.degrees(math.atan2(_E[0], _E[1]))
ROT = math.radians(90.0 - U_BEARING)

# Road band beside the west boundary, about 5 m of it drawn.
ROAD = Polygon([(0.6, -1.1), (-10.7, 19.5), (-15.7, 19.5), (-4.4, -1.1)])

EXT_WALL = 0.30
INT_WALL = 0.12


def R(u0: float, v0: float, u1: float, v1: float) -> Polygon:
    return box(min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1))


def zg(u: float, v: float) -> float | None:
    return ground.at(u, v)


def zg_safe(u: float, v: float) -> float:
    """Survey TIN height; just outside the TIN, the nearest TIN height towards the parcel centre."""
    z = zg(u, v)
    if z is not None:
        return z
    c = PARCEL.centroid
    for k in range(1, 200):
        t = k * 0.01
        z = zg(u + (c.x - u) * t, v + (c.y - v) * t)
        if z is not None:
            return z
    raise ValueError(f"no terrain near ({u}, {v})")


GROUND_KINDS = ("lawn", "court", "paved")  # outdoor platforms levelled on the ground
FORMATION = 0.35  # building formation below FFL, m


def tree_spots(bank: Polygon, spacing: float = 3.6) -> list[tuple[float, float]]:
    """Tree positions along the middle of the planted bank, north to south."""
    u0, v0, u1, v1 = bank.bounds
    out = []
    v = v0 + 2.0
    while v < v1 - 1.4:
        seg = bank.intersection(LineString([(u0 - 1, v), (u1 + 1, v)]))
        if not seg.is_empty and seg.length > 1.6:
            out.append((seg.centroid.x, v))
        v += spacing
    return out


# ---------------------------------------------------------------- model
@dataclass
class Room:
    id: str
    name: str
    kind: str  # day | sleep | wet | hall | core | service | garage | lift | stair
    geom: Polygon
    label_at: tuple[float, float] | None = None
    main: bool = False  # a "main room" for rule 2.1
    show_dims: bool = True
    small: bool = False


@dataclass
class Door:
    a: str
    b: str  # room id, or "ext"
    u: float
    v: float
    w: float = 0.9
    axis: str = "u"  # wall runs along u -> opening spans u
    kind: str = "door"  # door | open | slide | shutter | glass
    swing: int = 1  # leaf opens toward +perpendicular (+v for axis u, +u for axis v)
    hinge: int = -1  # -1 hinge at low end, +1 at high end


@dataclass
class Win:
    u0: float
    v0: float
    u1: float
    v1: float


@dataclass
class Shape:
    geom: object
    style: str = "furn"  # furn | fixture | car | dash | text | stair | lift | bench
    text: str = ""


@dataclass
class Terrace:
    id: str
    name: str
    geom: Polygon
    z: float
    # terrace/deck/green = on a slab or roof; paved/lawn/court = on the ground at level z;
    # stair = flight from z down to z_end along `run`; bank/path = natural ground, untouched.
    kind: str = "terrace"
    label_at: tuple[float, float] | None = None
    note: str = ""  # replaces the "area · level" line under the label
    z_end: float | None = None
    run: str = ""  # u+ | u- | v+ | v-: direction the stair descends


@dataclass
class Level:
    key: str
    title: str
    z: float
    rooms: list[Room]
    doors: list[Door] = field(default_factory=list)
    windows: list[Win] = field(default_factory=list)
    furniture: list[Shape] = field(default_factory=list)
    terraces: list[Terrace] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def room(self, rid: str) -> Room:
        return next(r for r in self.rooms if r.id == rid)

    @property
    def footprint(self) -> Polygon:
        return unary_union([r.geom for r in self.rooms]).buffer(0.001).buffer(-0.001)


@dataclass
class Option:
    code: str
    title: str
    source: str
    idea: str
    levels: dict[str, Level]
    lawn_z: float
    lawn_u0: float
    critique_fixed: list[tuple[str, str]]
    sections: dict[str, list[tuple[float, str]]]


# ---------------------------------------------------------------- furniture helpers
def rect(u0, v0, u1, v1, style="furn", text=""):
    return Shape(R(u0, v0, u1, v1), style, text)


def bed(u, v, w, length, head="n", pillows=2):
    """Bed with head against the named wall; (u, v) is the head-wall-side corner (min u, min v)."""
    out = []
    if head in "ns":
        g = R(u, v, u + w, v + length)
        pv = v + 0.05 if head == "n" else v + length - 0.4
        ph = 0.35
        pw = (w - 0.15) / pillows - 0.05
        out.append(Shape(g))
        for i in range(pillows):
            pu = u + 0.08 + i * (pw + 0.05)
            out.append(Shape(R(pu, pv, pu + pw, pv + ph), "fixture"))
        fold = v + length * 0.62 if head == "n" else v + length * 0.38
        out.append(Shape(LineString([(u, fold), (u + w, fold)]), "fixture"))
    else:
        g = R(u, v, u + length, v + w)
        pu = u + 0.05 if head == "w" else u + length - 0.4
        pw = (w - 0.15) / pillows - 0.05
        out.append(Shape(g))
        for i in range(pillows):
            pv = v + 0.08 + i * (pw + 0.05)
            out.append(Shape(R(pu, pv, pu + 0.35, pv + pw), "fixture"))
        fold = u + length * 0.62 if head == "w" else u + length * 0.38
        out.append(Shape(LineString([(fold, v), (fold, v + w)]), "fixture"))
    return out


def wardrobe(u0, v0, u1, v1):
    g = R(u0, v0, u1, v1)
    out = [Shape(g, "bench")]
    if (u1 - u0) > (v1 - v0):
        out.append(Shape(LineString([(u0, (v0 + v1) / 2), (u1, (v0 + v1) / 2)]), "fixture"))
    else:
        out.append(Shape(LineString([((u0 + u1) / 2, v0), ((u0 + u1) / 2, v1)]), "fixture"))
    return out


def desk(u0, v0, u1, v1, chair: tuple[float, float] | None = None):
    out = [Shape(R(u0, v0, u1, v1))]
    if chair:
        out.append(Shape(Point(chair).buffer(0.22), "furn"))
    return out


def counter(u0, v0, u1, v1, sink=None, hob=None, fridge=None):
    out = [Shape(R(u0, v0, u1, v1), "bench")]
    if sink:
        out.append(Shape(R(sink[0] - 0.3, sink[1] - 0.2, sink[0] + 0.3, sink[1] + 0.2), "fixture"))
    if hob:
        for du in (-0.15, 0.15):
            for dv in (-0.13, 0.13):
                out.append(Shape(Point(hob[0] + du, hob[1] + dv).buffer(0.08), "fixture"))
    if fridge:
        out.append(Shape(R(*fridge), "fixture", "F"))
    return out


def table_chairs(cu, cv, lu, lv, n_long=3, ends=True):
    """Dining table centred at (cu, cv), lu along u, lv along v, with chairs."""
    out = [Shape(R(cu - lu / 2, cv - lv / 2, cu + lu / 2, cv + lv / 2))]
    if lu >= lv:
        for i in range(n_long):
            x = cu - lu / 2 + lu * (i + 0.5) / n_long
            out.append(Shape(R(x - 0.22, cv - lv / 2 - 0.5, x + 0.22, cv - lv / 2 - 0.08)))
            out.append(Shape(R(x - 0.22, cv + lv / 2 + 0.08, x + 0.22, cv + lv / 2 + 0.5)))
        if ends:
            out.append(Shape(R(cu - lu / 2 - 0.5, cv - 0.22, cu - lu / 2 - 0.08, cv + 0.22)))
            out.append(Shape(R(cu + lu / 2 + 0.08, cv - 0.22, cu + lu / 2 + 0.5, cv + 0.22)))
    else:
        for i in range(n_long):
            y = cv - lv / 2 + lv * (i + 0.5) / n_long
            out.append(Shape(R(cu - lu / 2 - 0.5, y - 0.22, cu - lu / 2 - 0.08, y + 0.22)))
            out.append(Shape(R(cu + lu / 2 + 0.08, y - 0.22, cu + lu / 2 + 0.5, y + 0.22)))
        if ends:
            out.append(Shape(R(cu - 0.22, cv - lv / 2 - 0.5, cu + 0.22, cv - lv / 2 - 0.08)))
            out.append(Shape(R(cu - 0.22, cv + lv / 2 + 0.08, cu + 0.22, cv + lv / 2 + 0.5)))
    return out


def sofa_l(u0, v0, la, lb, corner="nw", depth=0.9):
    """L-sofa; arm A runs along u (length la), arm B along v (length lb), meeting at `corner`."""
    su = 1 if corner[1] == "w" else -1
    sv = 1 if corner[0] == "n" else -1
    a = R(u0, v0, u0 + su * la, v0 + sv * depth)
    b = R(u0, v0, u0 + su * depth, v0 + sv * lb)
    return [Shape(unary_union([a, b]))]


def sofa(u0, v0, u1, v1):
    return [Shape(R(u0, v0, u1, v1))]


def armchair(u, v, s=0.8):
    return [Shape(R(u, v, u + s, v + s))]


def coffee(u0, v0, u1, v1):
    return [Shape(R(u0, v0, u1, v1), "fixture")]


def wc(u, v, facing="s", squat=False):
    """WC pan centred at (u, v); `facing` is the direction the user faces when seated."""
    if squat:
        return [Shape(R(u - 0.25, v - 0.35, u + 0.25, v + 0.35), "fixture"),
                Shape(Point(u, v).buffer(0.12), "fixture")]
    d = {"s": (0, 1), "n": (0, -1), "e": (1, 0), "w": (-1, 0)}[facing]
    bowl = Point(u + d[0] * 0.05, v + d[1] * 0.05).buffer(0.2)
    t = R(u - d[0] * 0.33 - abs(d[1]) * 0.22, v - d[1] * 0.33 - abs(d[0]) * 0.22,
          u - d[0] * 0.15 + abs(d[1]) * 0.22, v - d[1] * 0.15 + abs(d[0]) * 0.22)
    return [Shape(t, "fixture"), Shape(bowl, "fixture")]


def basin(u, v, w=0.55, d=0.42):
    return [Shape(R(u - w / 2, v - d / 2, u + w / 2, v + d / 2), "fixture"),
            Shape(Point(u, v).buffer(min(w, d) * 0.32), "fixture")]


def shower(u0, v0, u1, v1):
    return [Shape(R(u0, v0, u1, v1), "fixture"),
            Shape(LineString([(u0, v0), (u1, v1)]), "fixture"),
            Shape(LineString([(u0, v1), (u1, v0)]), "fixture")]


def car(u0, v0, length=5.0, width=2.0, label=""):
    g = R(u0, v0, u0 + length, v0 + width)
    return [Shape(g, "car", label),
            Shape(R(u0 + length * 0.28, v0 + 0.15, u0 + length * 0.72, v0 + width - 0.15), "fixture")]


def mats(u, v, n=2, dirn="s"):
    out = []
    for i in range(n):
        if dirn in "ns":
            out.append(Shape(R(u + i * 0.95, v, u + i * 0.95 + 0.8, v + 1.25), "mat"))
        else:
            out.append(Shape(R(u, v + i * 0.95, u + 1.25, v + i * 0.95 + 0.8), "mat"))
    return out


def lockers(u0, v0, u1, v1, n=6):
    out = [Shape(R(u0, v0, u1, v1), "bench")]
    horiz = (u1 - u0) > (v1 - v0)
    for i in range(1, n):
        if horiz:
            x = u0 + (u1 - u0) * i / n
            out.append(Shape(LineString([(x, v0), (x, v1)]), "fixture"))
        else:
            y = v0 + (v1 - v0) * i / n
            out.append(Shape(LineString([(u0, y), (u1, y)]), "fixture"))
    return out


def stair_dogleg(u0, v0, u1, v1, rest_north=True, risers=24, label="", gap=0.2):
    """Dog-leg stair in (u0..u1, v0..v1): flights run along v, rest landing at north."""
    out = []
    w = (u1 - u0 - gap) / 2
    land = 1.4
    f0, f1 = (v0 + land, v1 - land) if rest_north else (v0 + land, v1 - land)
    n = risers // 2 - 1
    for k in range(n + 1):
        y = f0 + (f1 - f0) * k / n
        out.append(Shape(LineString([(u0, y), (u0 + w, y)]), "stair"))
        out.append(Shape(LineString([(u1 - w, y), (u1, y)]), "stair"))
    out.append(Shape(R(u0 + w, f0, u1 - w, f1), "bench"))
    out.append(Shape(LineString([(u0 + w / 2, f1 - 0.2), (u0 + w / 2, f0 + 0.3)]), "arrow"))
    out.append(Shape(LineString([(u1 - w / 2, f0 + 0.3), (u1 - w / 2, f1 - 0.2)]), "arrow"))
    out.append(Shape(Point((u0 + u1) / 2, v0 + land / 2), "text", "REST 1.40"))
    if label:
        out.append(Shape(Point((u0 + u1) / 2, v1 - land / 2), "text", label))
    return out


def lift_car(u0, v0, u1, v1):
    return [Shape(R(u0 + 0.15, v0 + 0.15, u1 - 0.15, v1 - 0.15), "lift"),
            Shape(LineString([(u0 + 0.15, v0 + 0.15), (u1 - 0.15, v1 - 0.15)]), "fixture"),
            Shape(LineString([(u0 + 0.15, v1 - 0.15), (u1 - 0.15, v0 + 0.15)]), "fixture")]


def flat(*groups):
    out = []
    for g in groups:
        if isinstance(g, Shape):
            out.append(g)
        else:
            out.extend(g)
    return out


# ---------------------------------------------------------------- geometry of walls/openings
def door_cut(d: Door) -> Polygon:
    t = 0.7
    if d.axis == "u":
        return R(d.u - d.w / 2, d.v - t / 2, d.u + d.w / 2, d.v + t / 2)
    return R(d.u - t / 2, d.v - d.w / 2, d.u + t / 2, d.v + d.w / 2)


def win_cut(w: Win) -> Polygon:
    t = 0.7
    if abs(w.v1 - w.v0) < 1e-6:
        return R(w.u0, w.v0 - t / 2, w.u1, w.v0 + t / 2)
    return R(w.u0 - t / 2, w.v0, w.u0 + t / 2, w.v1)


def walls(level: Level) -> object:
    fp = level.footprint
    ext = fp.exterior.buffer(EXT_WALL / 2, cap_style=2, join_style=2)
    for hole in fp.interiors:
        ext = ext.union(hole.buffer(EXT_WALL / 2, cap_style=2, join_style=2))
    inner = []
    for r in level.rooms:
        if r.kind == "stair-void":
            continue
        inner.append(r.geom.exterior.buffer(INT_WALL / 2, cap_style=2, join_style=2))
    wall = unary_union([ext] + inner)
    cuts = [door_cut(d) for d in level.doors] + [win_cut(w) for w in level.windows]
    open_cuts = [r.geom for r in level.rooms if r.kind == "merge"]
    return wall.difference(unary_union(cuts + open_cuts))


# ---------------------------------------------------------------- SVG output
class Sheet:
    def __init__(self, scale: float, origin: tuple[float, float]):
        self.s = scale
        self.ox, self.oy = origin
        self.parts: list[str] = []

    def xy(self, u: float, v: float) -> tuple[float, float]:
        c, s = math.cos(ROT), math.sin(ROT)
        x = u * c + v * s
        y = -u * s + v * c
        return self.ox + x * self.s, self.oy + y * self.s

    def path(self, geom, cls: str, extra: str = "") -> None:
        if geom.is_empty:
            return
        gt = geom.geom_type
        if gt in ("MultiPolygon", "GeometryCollection", "MultiLineString"):
            for g in geom.geoms:
                self.path(g, cls, extra)
            return
        if gt == "Polygon":
            d = self._ring(geom.exterior.coords)
            for h in geom.interiors:
                d += self._ring(h.coords)
            self.parts.append(f'<path class="{cls}" d="{d}" fill-rule="evenodd" {extra}/>')
        elif gt == "LineString":
            pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (self.xy(*c) for c in geom.coords))
            self.parts.append(f'<polyline class="{cls}" points="{pts}" {extra}/>')

    def _ring(self, coords) -> str:
        pts = [self.xy(*c) for c in coords]
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z "

    def text(self, x, y, t, cls="lbl", anchor="middle"):
        self.parts.append(f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">{escape(t)}</text>')

    def raw(self, s: str) -> None:
        self.parts.append(s)


CSS = """
.bg{fill:#fbfaf6}
.parcel{fill:none;stroke:#b4472f;stroke-width:1.6}
.env{fill:none;stroke:#b4472f;stroke-width:0.8;stroke-dasharray:6 4;opacity:.6}
.road{fill:#e6e6e3;stroke:#a9a9a4;stroke-width:.8}
.contour{fill:none;stroke:#c69a62;stroke-width:.6;opacity:.75}
.contour5{fill:none;stroke:#b07a3c;stroke-width:1.1;opacity:.85}
.below{fill:none;stroke:#8a96a3;stroke-width:1;stroke-dasharray:4 3}
.terrace{fill:#eee4d3;stroke:#b9a88c;stroke-width:.8}
.lawn{fill:#dfe9cf;stroke:#97ad76;stroke-width:.8}
.bank{fill:#cfdcbc;stroke:#8aa06c;stroke-width:.8;stroke-dasharray:5 3}
.green{fill:#d5e3c8;stroke:#97ad76;stroke-width:.8;stroke-dasharray:2 2}
.path{fill:#efe9dc;stroke:#b5aa90;stroke-width:.7;stroke-dasharray:4 3}
.tree{fill:#9dbb7e;fill-opacity:.55;stroke:#6f8f52;stroke-width:.8}
.bdry{stroke:#b4472f;stroke-width:1;stroke-dasharray:6 4}
.person{stroke:#3a4a54;stroke-width:1.4;fill:none;stroke-linecap:round}
.fin{fill:none;stroke:#5f8a3c;stroke-width:2.2}
.court{fill:#ece9e1;stroke:#b5b0a3;stroke-width:.8}
.deck{fill:#e9e2d5;stroke:#b9a88c;stroke-width:.8}
.gstair{fill:#f3efe6;stroke:#a89c84;stroke-width:.8}
.r-day{fill:#f4ead8}.r-kitchen{fill:#f6e4c4}.r-sleep{fill:#e3ebf2}.r-wet{fill:#d9ecea}
.r-hall{fill:#f5f4f0}.r-core{fill:#f1eee7}.r-service{fill:#e8e6df}.r-garage{fill:#e4e5e2}
.r-lift{fill:#d3dde3}.r-stair{fill:#f1eee7}.r-prayer{fill:#efe8d0}.r-study{fill:#e8e4f0}
.wall{fill:#22343f}
.glass{stroke:#2b8aa6;stroke-width:1.3;fill:none}
.leaf{stroke:#2a7f73;stroke-width:1.1;fill:none}
.arc{stroke:#2a7f73;stroke-width:.6;fill:none;stroke-dasharray:3 2}
.slide{stroke:#2b8aa6;stroke-width:2.2;fill:none}
.shutter{stroke:#5d6b75;stroke-width:1.6;fill:none;stroke-dasharray:5 2}
.furn{fill:#fdfcf9;stroke:#7d8790;stroke-width:.7}
.fixture{fill:#fdfcf9;stroke:#8c959c;stroke-width:.55}
.bench{fill:#e6e0d4;stroke:#8c8678;stroke-width:.6}
.car{fill:#d7e3ea;stroke:#6f8796;stroke-width:.8}
.baffle{stroke:#b23a48;stroke-width:2;fill:none}
.mat{fill:#e8efe3;stroke:#7f9a73;stroke-width:.6}
.stair{stroke:#6b6f72;stroke-width:.6;fill:none}
.arrow{stroke:#3a4a54;stroke-width:.8;fill:none;marker-end:url(#ar)}
.lift{fill:#c9d6de;stroke:#55707f;stroke-width:.8}
.dash{fill:none;stroke:#8f99a1;stroke-width:.7;stroke-dasharray:3 3}
.lbl{font:600 10.5px Helvetica,Arial,sans-serif;fill:#22343f;letter-spacing:.2px}
.dim{font:400 9px Helvetica,Arial,sans-serif;fill:#4c5b66}
.tiny{font:500 8px Helvetica,Arial,sans-serif;fill:#55636d}
.tlbl{font:600 10px Helvetica,Arial,sans-serif;fill:#6d5b3c}
.tz{font:400 8.5px Helvetica,Arial,sans-serif;fill:#7c6b4e}
.h1{font:700 22px Helvetica,Arial,sans-serif;fill:#1d2f3a}
.h2{font:400 13px Helvetica,Arial,sans-serif;fill:#5c6a73}
.note{font:400 11px Helvetica,Arial,sans-serif;fill:#33434d}
.noteb{font:700 11.5px Helvetica,Arial,sans-serif;fill:#1f6f6a;letter-spacing:.6px}
.lblbg{fill:#fbfaf6;opacity:.86}
.cut{fill:#22343f}
.ground{fill:none;stroke:#7a5b34;stroke-width:1.6}
.earth{fill:#d9c9ab;opacity:.55}
.dig{fill:url(#hatch)}
.fill{fill:url(#hatchf)}
.slab{fill:#22343f}
.roomcut{fill:#f4efe6;stroke:#22343f;stroke-width:1}
.retain{fill:#5f6b72}
.grid{stroke:#d9d6cc;stroke-width:.5}
.hl{fill:#f08a3c;fill-opacity:.16;stroke:#e0662a;stroke-width:3.2;stroke-dasharray:9 4}
.dimline{stroke:#5b6a74;stroke-width:.6;fill:none}
.dimtick{stroke:#5b6a74;stroke-width:1;fill:none}
.dimt{font:500 8.5px Helvetica,Arial,sans-serif;fill:#3f4d57}
"""

DEFS = """<defs>
<marker id="ar" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#3a4a54"/></marker>
<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#efe3cc"/><line x1="0" y1="0" x2="0" y2="6" stroke="#b9774a" stroke-width="1.2"/></pattern>
<pattern id="hatchf" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><rect width="6" height="6" fill="#e3ead4"/><line x1="0" y1="0" x2="0" y2="6" stroke="#7f9a5c" stroke-width="1"/></pattern>
</defs>"""


def contours(sheet: Sheet, step=1.0) -> None:
    """Marching squares on the survey TIN, drawn faintly under the plan."""
    us = [x * 0.5 for x in range(-24, 70)]
    vs = [y * 0.5 for y in range(-2, 40)]
    zs = [[zg(u, v) for u in us] for v in vs]
    lo, hi = 1663, 1679
    for lev in [lo + k * step for k in range(int((hi - lo) / step) + 1)]:
        segs = []
        for j in range(len(vs) - 1):
            for i in range(len(us) - 1):
                c = [(us[i], vs[j], zs[j][i]), (us[i + 1], vs[j], zs[j][i + 1]),
                     (us[i + 1], vs[j + 1], zs[j + 1][i + 1]), (us[i], vs[j + 1], zs[j + 1][i])]
                if any(p[2] is None for p in c):
                    continue
                pts = []
                for a, b in zip(c, c[1:] + c[:1]):
                    if (a[2] - lev) * (b[2] - lev) < 0:
                        t = (lev - a[2]) / (b[2] - a[2])
                        pts.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
                if len(pts) == 2:
                    segs.append(pts)
        cls = "contour5" if int(lev) % 5 == 0 else "contour"
        for s in segs:
            sheet.path(LineString(s), cls)
        # label one point per level near the parcel's north edge
        lab = [s for s in segs if 0.0 <= s[0][1] <= 1.0]
        if lab:
            x, y = sheet.xy(*lab[0][0])
            sheet.text(x, y - 3, f"{lev:.0f}", "tz")


def door_graphics(sheet: Sheet, d: Door) -> None:
    if d.kind == "open":
        return
    if d.axis == "u":
        a, b = (d.u - d.w / 2, d.v), (d.u + d.w / 2, d.v)
        perp = (0, d.swing)
    else:
        a, b = (d.u, d.v - d.w / 2), (d.u, d.v + d.w / 2)
        perp = (d.swing, 0)
    if d.kind in ("slide", "glass"):
        sheet.path(LineString([a, b]), "slide")
        return
    if d.kind == "shutter":
        sheet.path(LineString([a, b]), "shutter")
        return
    hinge, far = (a, b) if d.hinge < 0 else (b, a)
    tip = (hinge[0] + perp[0] * d.w, hinge[1] + perp[1] * d.w)
    sheet.path(LineString([hinge, tip]), "leaf")
    pts = []
    v1 = (far[0] - hinge[0], far[1] - hinge[1])
    v2 = (tip[0] - hinge[0], tip[1] - hinge[1])
    for k in range(13):
        t = k / 12 * math.pi / 2
        pts.append((hinge[0] + v1[0] * math.cos(t) + v2[0] * math.sin(t),
                    hinge[1] + v1[1] * math.cos(t) + v2[1] * math.sin(t)))
    sheet.path(LineString(pts), "arc")


def win_graphics(sheet: Sheet, w: Win) -> None:
    if abs(w.v1 - w.v0) < 1e-6:
        for dv in (-0.07, 0.07):
            sheet.path(LineString([(w.u0, w.v0 + dv), (w.u1, w.v0 + dv)]), "glass")
    else:
        for du in (-0.07, 0.07):
            sheet.path(LineString([(w.u0 + du, w.v0), (w.u0 + du, w.v1)]), "glass")


def room_dims(r: Room) -> tuple[float, float, float]:
    """Clear width, depth (bounding) and clear area after half-wall deductions."""
    u0, v0, u1, v1 = r.geom.bounds
    clear = r.geom.buffer(-INT_WALL / 2, join_style=2)
    return round(u1 - u0 - INT_WALL, 2), round(v1 - v0 - INT_WALL, 2), round(clear.area, 1)


def label_boxes(sheet: Sheet, level: Level):
    boxes = []
    for r in level.rooms:
        if r.kind in ("merge", "stair-void"):
            continue
        p = r.label_at or (r.geom.representative_point().x, r.geom.representative_point().y)
        if r.label_at is None and r.geom.geom_type == "Polygon":
            c = r.geom.centroid
            if r.geom.buffer(-0.3).contains(c):
                p = (c.x, c.y)
        x, y = sheet.xy(*p)
        name = r.name
        w, d, a = room_dims(r)
        rect_like = r.geom.area > 0.97 * r.geom.envelope.area
        sub = (f"{w:.1f} × {d:.1f} · {a:.1f} m²" if rect_like else f"L-shaped · {a:.1f} m²") if r.show_dims and r.geom.area > 2.5 else ""
        if r.small:
            sub = f"{a:.1f} m²" if r.geom.area > 2.5 else ""
        fs = 10.5 if not r.small else 8.5
        tw = max(len(name) * fs * 0.6, len(sub) * 9 * 0.55) + 6
        th = (fs + 4) + (11 if sub else 0)
        boxes.append((r, x, y, tw, th, name, sub, fs))
    return boxes


def overlaps(b1, b2) -> bool:
    _, x1, y1, w1, h1, *_ = b1
    _, x2, y2, w2, h2, *_ = b2
    return abs(x1 - x2) * 2 < (w1 + w2) and abs(y1 - y2) * 2 < (h1 + h2)


def draw_level(level: Level, opt: Option, path_svg: Path, width=2200, height=1880,
               highlight: set[str] | None = None) -> dict:
    sheet = Sheet(1.0, (0, 0))
    zone = PARCEL.buffer(0.8)
    xs, ys = zip(*[sheet.xy(u, v) for u, v in zone.exterior.coords])
    sheet.s = min((width - 420) / (max(xs) - min(xs)), (height - 170) / (max(ys) - min(ys)), 52.0)
    sheet.ox = 150 + (width - 500 - (max(xs) - min(xs)) * sheet.s) / 2 - min(xs) * sheet.s
    sheet.oy = 100 + (height - 150 - (max(ys) - min(ys)) * sheet.s) / 2 - min(ys) * sheet.s
    sheet.raw(f'<rect class="bg" x="0" y="0" width="{width}" height="{height}"/>')
    # road band beside west boundary
    sheet.path(ROAD, "road")
    rx, ry = sheet.xy(-6.6, 7.0)
    sheet.text(rx, ry, "ROAD ≈ 1677.4", "tlbl")
    contours(sheet)
    sheet.path(PARCEL, "parcel")
    sheet.path(ENVELOPE, "env")
    # levels below shown dashed for orientation
    order = list(opt.levels)
    idx = order.index(level.key)
    if idx + 1 < len(order):
        below = opt.levels[order[idx + 1]].footprint
        sheet.path(below.exterior, "below")
    for t in level.terraces:
        sheet.path(t.geom, t.kind if t.kind in ("lawn", "court", "deck", "bank", "green", "path") else
                   ("gstair" if t.kind == "stair" else "terrace"))
        if t.kind == "bank":
            for k, p in enumerate(tree_spots(t.geom)):
                sheet.path(Point(p).buffer(1.05 if k % 2 else 1.25), "tree")
    for r in level.rooms:
        if r.kind == "merge":
            continue
        cls = {"day": "r-day", "kitchen": "r-kitchen", "sleep": "r-sleep", "wet": "r-wet",
               "hall": "r-hall", "core": "r-core", "service": "r-service", "garage": "r-garage",
               "lift": "r-lift", "stair": "r-stair", "prayer": "r-prayer", "study": "r-study"}.get(
            r.kind, "r-hall")
        sheet.path(r.geom, cls)
    for f in level.furniture:
        if f.style == "text":
            x, y = sheet.xy(f.geom.x, f.geom.y)
            sheet.text(x, y + 3, f.text, "tiny")
            continue
        sheet.path(f.geom, f.style)
        if f.text:
            c = f.geom.centroid
            x, y = sheet.xy(c.x, c.y)
            sheet.text(x, y + 3, f.text, "tiny")
    sheet.path(walls(level), "wall")
    for w in level.windows:
        win_graphics(sheet, w)
    for d in level.doors:
        door_graphics(sheet, d)
    for t in level.terraces:
        if not t.name:
            continue
        fb = level.footprint.bounds
        tb = t.geom.bounds
        c = t.label_at or (t.geom.representative_point().x, t.geom.representative_point().y)
        if t.label_at is None and tb[1] >= fb[3] - 0.1:
            c = ((tb[0] + tb[2]) / 2, tb[3] - 0.9)
        elif t.label_at is None and tb[0] >= fb[2] - 0.1:
            c = (tb[2] - 0.9, (tb[1] + tb[3]) / 2)
        x, y = sheet.xy(*c)
        sheet.text(x, y, t.name, "tlbl")
        sub = t.note or (f"{t.z:.2f} → {t.z_end:.2f}" if t.kind == "stair" else f"{t.geom.area:.0f} m² · {t.z:.2f}")
        sheet.text(x, y + 11, sub, "tz")
    dimension_strings(sheet, level)
    north_marks(sheet, level)
    for r in level.rooms + level.terraces:
        if highlight and r.id in highlight:
            sheet.path(r.geom.buffer(-0.08, join_style=2), "hl")
    boxes = label_boxes(sheet, level)
    collisions = []
    for i, b in enumerate(boxes):
        for b2 in boxes[i + 1:]:
            if overlaps(b, b2):
                collisions.append((b[0].id, b2[0].id))
    for r, x, y, tw, th, name, sub, fs in boxes:
        y0 = y - th / 2
        sheet.raw(f'<rect class="lblbg" x="{x - tw / 2:.1f}" y="{y0:.1f}" width="{tw:.1f}" height="{th:.1f}" rx="2"/>')
        sheet.raw(f'<text class="lbl" style="font-size:{fs}px" x="{x:.1f}" y="{y0 + fs + 1:.1f}" text-anchor="middle">{escape(name)}</text>')
        if sub:
            sheet.text(x, y0 + fs + 12, sub, "dim")
    # header + north arrow + scale bar
    sheet.text(40, 50, f"{opt.code} · {level.title}", "h1", "start")
    sheet.text(40, 74, f"FFL {level.z:.2f}  ·  {opt.title}", "h2", "start")
    if highlight is not None:
        sheet.text(40, 98, "Orange dashed = different from the other option(s)", "noteb", "start")
    nx, ny = width - 300, 70
    sheet.raw(f'<line x1="{nx}" y1="{ny + 50}" x2="{nx}" y2="{ny}" stroke="#1d2f3a" stroke-width="2" marker-end="url(#ar)"/>')
    sheet.text(nx, ny + 68, "N", "lbl")
    x0, y0 = 60, height - 70
    sheet.raw(f'<line x1="{x0}" y1="{y0}" x2="{x0 + 5 * sheet.s}" y2="{y0}" stroke="#1d2f3a" stroke-width="3"/>')
    for k in range(6):
        sheet.raw(f'<line x1="{x0 + k * sheet.s}" y1="{y0 - 5}" x2="{x0 + k * sheet.s}" y2="{y0 + 5}" stroke="#1d2f3a" stroke-width="1"/>')
    sheet.text(x0, y0 + 18, "0", "dim")
    sheet.text(x0 + 5 * sheet.s, y0 + 18, "5 m", "dim")
    sheet.text(x0, y0 + 36, "Grid north up · thin brown lines = natural ground contours every 1 m (survey TIN) · red = parcel boundary, dashed = 1 m setback", "tiny", "start")
    # side notes
    nxp = width - 330
    yy = 170
    sheet.text(nxp, yy, "HOW THIS FLOOR WORKS", "noteb", "start")
    yy += 22
    for n in level.notes:
        for line in wrap(n, 46):
            sheet.text(nxp, yy, line, "note", "start")
            yy += 16
        yy += 8
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}"><style>{CSS}</style>{DEFS}' + "".join(sheet.parts) + "</svg>")
    path_svg.write_text(svg)
    crop = unary_union([lv.footprint for lv in opt.levels.values()]
                       + [t.geom for t in level.terraces if t.kind == "terrace" and t.name]).buffer(0.9)
    cx, cy = zip(*[sheet.xy(u, v) for u, v in crop.envelope.exterior.coords])
    return {"label_collisions": collisions, "crop": (min(cx), min(cy) - 20, max(cx), max(cy))}


def dimension_strings(sheet: Sheet, level: Level) -> None:
    """Overall dimension chains: room breaks along the south side, plate depth on the east side."""
    u0, v0, u1, v1 = level.footprint.bounds
    off_v = v1 + 0.55
    south = sorted({round(r.geom.bounds[0], 2) for r in level.rooms if abs(r.geom.bounds[3] - v1) < 0.05}
                   | {round(r.geom.bounds[2], 2) for r in level.rooms if abs(r.geom.bounds[3] - v1) < 0.05})
    if len(south) < 2:
        south = [u0, u1]

    def chain(pts, fixed, along_u):
        ang = -math.degrees(ROT) if along_u else 90 - math.degrees(ROT)
        for a, b in zip(pts, pts[1:]):
            p0 = (a, fixed) if along_u else (fixed, a)
            p1 = (b, fixed) if along_u else (fixed, b)
            sheet.path(LineString([p0, p1]), "dimline")
            for p in (p0, p1):
                t0 = (p[0] - 0.12, p[1] + 0.12) if along_u else (p[0] - 0.12, p[1] - 0.12)
                t1 = (p[0] + 0.12, p[1] - 0.12) if along_u else (p[0] + 0.12, p[1] + 0.12)
                sheet.path(LineString([t0, t1]), "dimtick")
            if b - a > 0.9:
                mid = ((a + b) / 2, fixed - 0.18) if along_u else (fixed + 0.18, (a + b) / 2)
                x, y = sheet.xy(*mid)
                sheet.raw(f'<text class="dimt" x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
                          f'transform="rotate({ang:.1f} {x:.1f} {y:.1f})">{b - a:.2f}</text>')

    chain(south, off_v, True)
    chain([u0, u1], off_v + 0.6, True)
    east = [t.geom.bounds[2] for t in level.terraces if t.kind in ("terrace", "paved") and t.geom.bounds[2] > u1]
    chain([v0, v1], max([u1] + east) + 0.45, False)


def north_marks(sheet: Sheet, level: Level) -> None:
    """Compass words on the four sides of the parcel, so 'south terrace' can be found at a glance."""
    for (u, v), word in (((11.0, -1.0), "NORTH SIDE"), ((6.0, 19.3), "SOUTH SIDE · shared footpath"),
                         ((29.2, 9.2), "EAST · downhill")):
        x, y = sheet.xy(u, v)
        ang = -math.degrees(ROT) if "EAST" not in word else 90 - math.degrees(ROT) - 4.5
        sheet.raw(f'<text class="tiny" style="fill:#b4472f;letter-spacing:1px" x="{x:.1f}" y="{y:.1f}" text-anchor="middle" '
                  f'transform="rotate({ang:.1f} {x:.1f} {y:.1f})">{word}</text>')


def wrap(s: str, n: int) -> list[str]:
    out, cur = [], ""
    for w in s.split():
        if len(cur) + len(w) + 1 > n:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    return out



# ---------------------------------------------------------------- finished ground
def polys(g) -> list[Polygon]:
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [x for x in getattr(g, "geoms", []) if x.geom_type == "Polygon" and not x.is_empty]


@dataclass
class Region:
    """One piece of reshaped ground. Regions never overlap."""

    geom: Polygon
    kind: str  # pit | paved | lawn | court | stair
    name: str
    z: float  # pit: formation level; platform: finished level; stair: top level
    z_end: float | None = None
    run: str = ""

    def level(self, u: float, v: float) -> float:
        if self.kind == "pit":
            return min(zg_safe(u, v), self.z)
        if self.kind == "stair":
            u0, v0, u1, v1 = self.geom.bounds
            t = {"u+": (u - u0) / (u1 - u0), "u-": (u1 - u) / (u1 - u0),
                 "v+": (v - v0) / (v1 - v0), "v-": (v1 - v) / (v1 - v0)}[self.run]
            return self.z + (self.z_end - self.z) * min(1.0, max(0.0, t))
        return self.z


class GroundModel:
    """Finished ground: the survey TIN, dug to formation under the house, levelled at each outdoor platform."""

    def __init__(self, opt: Option):
        self.regions: list[Region] = []
        below: list[Polygon] = []
        for lv in sorted(opt.levels.values(), key=lambda x: x.z):
            contact = lv.footprint.difference(unary_union(below)) if below else lv.footprint
            below.append(lv.footprint)
            for g in polys(contact.intersection(PARCEL).buffer(-0.001).buffer(0.001)):
                if g.area > 0.5:
                    self.regions.append(Region(g, "pit", lv.title, lv.z - FORMATION))
        self.built = unary_union(below)
        claimed = self.built
        for lv in opt.levels.values():
            for t in lv.terraces:
                ground_stair = t.kind == "stair" and t.z_end is not None
                if t.kind not in GROUND_KINDS and not ground_stair:
                    continue
                for g in polys(t.geom.difference(claimed).intersection(PARCEL).buffer(-0.001).buffer(0.001)):
                    if g.area > 0.3:
                        if ground_stair:
                            self.regions.append(Region(g, "stair", t.name, t.z, t.z_end, t.run))
                        else:
                            self.regions.append(Region(g, t.kind, t.name, t.z))
                claimed = claimed.union(t.geom)
        self.works = unary_union([r.geom for r in self.regions])

    def region_at(self, u: float, v: float) -> Region | None:
        p = Point(u, v)
        for r in self.regions:
            if r.geom.contains(p):
                return r
        return None

    def finished(self, u: float, v: float) -> float:
        r = self.region_at(u, v)
        return r.level(u, v) if r else zg_safe(u, v)


def to_local_poly(p: Polygon) -> Polygon:
    return Polygon([frame.to_local_m(u, v) for u, v in p.exterior.coords])


def earthworks(gm: GroundModel) -> dict:
    """Cut and fill on the survey TIN for every reshaped piece of ground."""
    rows = []
    surf = site.terrain.surface
    for r in gm.regions:
        if r.kind == "stair":
            continue
        res = integrate(surf, to_local_poly(r.geom), r.z)
        cut = res.cut_m3 or 0.0
        fill = 0.0 if r.kind == "pit" else (res.below_plane_m3 or 0.0)
        if cut < 0.5 and fill < 0.5:
            continue
        label = f"{r.name.title()} dig (formation {r.z:.2f})" if r.kind == "pit" else f"{r.name.title()} (finished {r.z:.2f})"
        rows.append({"zone": label, "kind": r.kind, "area_m2": round(r.geom.area, 1), "cut_m3": round(cut, 1),
                     "fill_m3": round(fill, 1), "max_cut_m": round(res.max_cut_m or 0, 2),
                     "max_fill_m": 0.0 if r.kind == "pit" else round(res.max_below_m or 0, 2)})
    return {"rows": rows, "total_cut_m3": round(sum(r["cut_m3"] for r in rows), 0),
            "total_fill_m3": round(sum(r["fill_m3"] for r in rows), 0),
            "method": "house_ai.geospatial.earthworks.integrate on the stored survey TIN (inferred surface); "
                      "building formation 0.35 m below FFL; excludes footings, batters, bulking, drainage layers."}


# ---------------------------------------------------------------- sections
SEC_SCALE = 24.0  # px per metre on both axes: 1:1, no vertical exaggeration
ZMIN, ZMAX = 1663.0, 1682.0


def boundary_stations(axis: str, const: float) -> list[float]:
    """Where a section line crosses the parcel boundary."""
    line = LineString([(-40, const), (60, const)] if axis == "u" else [(const, -40), (const, 60)])
    hit = PARCEL.exterior.intersection(line)
    return sorted((g.x if axis == "u" else g.y) for g in getattr(hit, "geoms", [hit]) if g.geom_type == "Point")


def section_panel(parts: list[str], opt: Option, gm: GroundModel, title: str, x0: float, y_base: float,
                  axis: str, const: float, rng: tuple[float, float]) -> None:
    lo, hi = rng
    s = SEC_SCALE

    def X(t):
        return x0 + (t - lo) * s

    def Y(z):
        return y_base - (z - ZMIN) * s

    def at(t):
        return (t, const) if axis == "u" else (const, t)

    cut_line = LineString([at(lo), at(hi)])

    def spans(geom):
        out = []
        seg = geom.intersection(cut_line)
        for g in getattr(seg, "geoms", [seg]):
            if g.is_empty or g.geom_type != "LineString" or g.length < 0.05:
                continue
            cs = [c[0] if axis == "u" else c[1] for c in g.coords]
            out.append((min(cs), max(cs)))
        return out

    head, _, sub = title.partition("|")
    parts.append(f'<text class="lbl" style="font-size:14px" x="{x0}" y="{Y(ZMAX) - 26:.0f}">{escape(head)}</text>')
    parts.append(f'<text class="note" x="{x0}" y="{Y(ZMAX) - 10:.0f}">{escape(sub)}</text>')
    for z in range(int(ZMIN), int(ZMAX) + 1):
        if z % 2 == 0:
            parts.append(f'<line class="grid" x1="{X(lo)}" y1="{Y(z):.1f}" x2="{X(hi)}" y2="{Y(z):.1f}"/>')
            parts.append(f'<text class="tiny" x="{x0 - 8}" y="{Y(z) + 3:.1f}" text-anchor="end">{z}</text>')
    step = 0.1
    ts = [lo + k * step for k in range(int(round((hi - lo) / step)) + 1)]
    pts = [(t, zg(*at(t))) for t in ts]
    pts = [(t, z) for t, z in pts if z is not None]
    if pts:
        poly = [(X(t), Y(z)) for t, z in pts] + [(X(pts[-1][0]), Y(ZMIN)), (X(pts[0][0]), Y(ZMIN))]
        parts.append('<path class="earth" d="M' + " L".join(f"{a:.1f},{b:.1f}" for a, b in poly) + ' Z"/>')
    built = [(a, b, lv) for lv in opt.levels.values() for a, b in spans(lv.footprint)]
    slabs = [(a, b, tr) for lv in opt.levels.values() for tr in lv.terraces
             if tr.kind in ("terrace", "deck", "green") for a, b in spans(tr.geom)]
    # dig and fill hatching against the finished ground
    fin = []
    for t, z in pts:
        r = gm.region_at(*at(t))
        if r is None:
            fin.append((t, z, None))
            continue
        f = r.z if r.kind == "pit" else r.level(*at(t))
        fin.append((t, f if (r.kind != "pit" or z > f) else z, r))
        if z > f + 0.02:
            parts.append(f'<rect class="dig" x="{X(t):.1f}" y="{Y(z):.1f}" width="{step * s + .3:.1f}" height="{(z - f) * s:.1f}"/>')
        elif z < f - 0.05 and r.kind != "pit":
            parts.append(f'<rect class="fill" x="{X(t):.1f}" y="{Y(f):.1f}" width="{step * s + .3:.1f}" height="{(f - z) * s:.1f}"/>')
    # building: slabs + room cut boxes
    for a, b, lv in sorted(built, key=lambda x: -x[2].z):
        top = lv.z + (3.0 if lv.key == "road" else (3.6 if lv.key == "main" else 3.3))
        parts.append(f'<rect class="roomcut" x="{X(a):.1f}" y="{Y(top):.1f}" width="{(b - a) * s:.1f}" height="{(top - lv.z) * s:.1f}"/>')
        parts.append(f'<rect class="slab" x="{X(a) - 2:.1f}" y="{Y(lv.z):.1f}" width="{(b - a) * s + 4:.1f}" height="{0.3 * s:.1f}"/>')
        parts.append(f'<rect class="slab" x="{X(a) - 2:.1f}" y="{Y(top + 0.3):.1f}" width="{(b - a) * s + 4:.1f}" height="{0.3 * s:.1f}"/>')
        for r in lv.rooms:
            if r.kind == "merge":
                continue
            for ra, rb in spans(r.geom):
                if rb - ra < 1.5:
                    continue
                nm = r.name if len(r.name) * 5.0 < (rb - ra) * s - 6 else r.name.split(" ")[0]
                if nm and len(nm) * 5.0 < (rb - ra) * s:
                    parts.append(f'<text class="tiny" x="{X((ra + rb) / 2):.1f}" y="{Y(lv.z + 1.5):.1f}" text-anchor="middle">{escape(nm)}</text>')
                for e in (ra, rb):
                    if a + 0.05 < e < b - 0.05:
                        parts.append(f'<line x1="{X(e):.1f}" y1="{Y(top):.1f}" x2="{X(e):.1f}" y2="{Y(lv.z):.1f}" stroke="#22343f" stroke-width="1.2"/>')
        parts.append(f'<text class="dim" x="{X(b) + 6:.1f}" y="{Y(lv.z) - 4:.1f}">{lv.z:.2f}</text>')

    for t, z in pts:  # the part of the house that sits below natural ground
        r = gm.region_at(*at(t))
        if r is not None and r.kind == "pit" and z > r.z + 0.02:
            parts.append(f'<rect class="dig" style="opacity:.42" x="{X(t):.1f}" y="{Y(z):.1f}" width="{step * s + .3:.1f}" height="{(z - r.z) * s:.1f}"/>')

    def supports(a, b, z_top):
        """Posts or foundation walls down to the ground wherever nothing is built below this slab."""
        n = max(1, int((b - a) / 2.8))
        for k in range(n + 1):
            t = a + 0.15 + (b - a - 0.3) * k / n
            zgr = gm.finished(*at(t)) if zg(*at(t)) is not None else None
            below = any(a2 - 0.01 <= t <= b2 + 0.01 and lv2.z < z_top - 0.5 for a2, b2, lv2 in built)
            if zgr is None or below or zgr > z_top - 0.6:
                continue
            parts.append(f'<rect class="retain" x="{X(t) - 0.12 * s:.1f}" y="{Y(z_top - 0.3):.1f}" '
                         f'width="{0.25 * s:.1f}" height="{(z_top - 0.3 - zgr + 0.6) * s:.1f}"/>')

    for a, b, lv in built:
        supports(a, b, lv.z)
    for a, b, tr in slabs:
        parts.append(f'<rect class="slab" style="opacity:.75" x="{X(a):.1f}" y="{Y(tr.z):.1f}" '
                     f'width="{(b - a) * s:.1f}" height="{0.22 * s:.1f}"/>')
        over_building = any(a2 - 0.01 <= (a + b) / 2 <= b2 + 0.01 and lv2.z < tr.z - 0.5 for a2, b2, lv2 in built)
        if not over_building and tr.kind == "terrace" and "BALCONY" not in tr.name:
            supports(a, b, tr.z)
        for e, sgn in ((a, -1), (b, 1)):  # balustrade on open edges
            if not any(a2 - 0.05 <= e + sgn * 0.1 <= b2 + 0.05 and abs(lv2.z - tr.z) < 0.6 for a2, b2, lv2 in built) \
                    and not any(a2 - 0.05 <= e + sgn * 0.1 <= b2 + 0.05 and abs(t2.z - tr.z) < 0.1 for a2, b2, t2 in slabs):
                parts.append(f'<line x1="{X(e):.1f}" y1="{Y(tr.z):.1f}" x2="{X(e):.1f}" y2="{Y(tr.z + 1.1):.1f}" stroke="#2b8aa6" stroke-width="1.6"/>')
    # natural ground, then the finished ground on top
    if pts:
        parts.append('<polyline class="ground" points="' + " ".join(f"{X(t):.1f},{Y(z):.1f}" for t, z in pts) + '"/>')
    run: list[tuple[float, float]] = []
    prev = None
    for t, f, r in fin + [(None, None, None)]:
        show = r is not None and r.kind != "pit"
        if show and (prev is None or prev is r):
            run.append((t, f))
        else:
            if len(run) > 1:
                parts.append('<polyline class="fin" points="' + " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in run) + '"/>')
            run = [(t, f)] if show else []
        prev = r if show else None
    # retaining walls where the finished ground steps
    for (t0, f0, r0), (t1, f1, r1) in zip(fin, fin[1:]):
        if r0 is r1 or abs(f0 - f1) < 0.5:
            continue
        if (r0 is not None and r0.kind == "pit") or (r1 is not None and r1.kind == "pit"):
            continue
        hi_z, lo_z = max(f0, f1), min(f0, f1)
        parts.append(f'<rect class="retain" x="{X(t1) - 0.12 * s:.1f}" y="{Y(hi_z):.1f}" width="{0.25 * s:.1f}" height="{(hi_z - lo_z + 0.5) * s:.1f}"/>')
        parts.append(f'<text class="tiny" x="{X(t1) + 6:.1f}" y="{Y(lo_z) + 11:.1f}">wall {hi_z - lo_z:.1f} m</text>')
    # platform names
    seen = set()
    for t, f, r in fin:
        if r is None or r.kind in ("pit", "stair") or r.name in seen:
            continue
        a, b = min(x[0] for x in fin if x[2] is r), max(x[0] for x in fin if x[2] is r)
        if b - a < 1.2:
            continue
        seen.add(r.name)
        nm = r.name.title() if (b - a) * s > len(r.name) * 5.2 else r.name.split(" ")[-1].title()
        parts.append(f'<text class="tz" x="{X((a + b) / 2):.1f}" y="{Y(r.z) - 1.95 * s:.1f}" text-anchor="middle">{escape(nm)} {r.z:.2f}</text>')
        px = X((a + b) / 2)
        py = Y(r.z)
        parts.append(f'<path class="person" d="M{px:.1f},{py:.1f} v{-0.85 * s:.1f} m{-0.2 * s:.1f},{0.25 * s:.1f} h{0.4 * s:.1f} m{-0.2 * s:.1f},{-0.25 * s:.1f} v{-0.45 * s:.1f}"/>'
                     f'<circle cx="{px:.1f}" cy="{py - 1.55 * s:.1f}" r="{0.13 * s:.1f}" class="person"/>')
    # parcel boundary marks
    for b in boundary_stations(axis, const):
        if lo < b < hi:
            parts.append(f'<line class="bdry" x1="{X(b):.1f}" y1="{Y(ZMAX) + 6:.1f}" x2="{X(b):.1f}" y2="{Y(ZMIN):.1f}"/>')
            parts.append(f'<text class="tiny" style="fill:#b4472f" x="{X(b):.1f}" y="{Y(ZMAX) + 2:.1f}" text-anchor="middle">boundary</text>')
    for k in range(math.ceil(lo / 2) * 2, int(hi) + 1, 2):
        parts.append(f'<text class="tiny" x="{X(k):.1f}" y="{Y(ZMIN) + 14:.1f}" text-anchor="middle">{k}</text>')
    lab = "metres from the NW corner →" if axis == "u" else "metres from the north boundary →"
    parts.append(f'<text class="tiny" x="{X((lo + hi) / 2):.1f}" y="{Y(ZMIN) + 30:.1f}" text-anchor="middle">{lab}</text>')
    side = ("WEST · road", "EAST · downhill") if axis == "u" else ("NORTH", "SOUTH")
    parts.append(f'<text class="noteb" x="{X(lo):.1f}" y="{Y(ZMIN) + 30:.1f}">{side[0]}</text>')
    parts.append(f'<text class="noteb" x="{X(hi):.1f}" y="{Y(ZMIN) + 30:.1f}" text-anchor="end">{side[1]}</text>')


def draw_sections(opt: Option, gm: GroundModel, path_svg: Path) -> None:
    """Four cuts: two west-east and two north-south, so both falls of the field can be read."""
    W, H = 1800, 1260
    parts = [f'<rect class="bg" x="0" y="0" width="{W}" height="{H}"/>']
    cuts = opt.sections
    ew, ns = (-8.0, 31.0), (-1.0, 19.5)
    letters = iter("ABCD")
    rows = [(600, cuts["ew"][0], cuts["ns"][0]), (1170, cuts["ew"][1], cuts["ns"][1])]
    for y_base, (v, what_v), (u, what_u) in rows:
        a = next(letters)
        section_panel(parts, opt, gm, f"SECTION {a}–{a} · west → east|{v:.1f} m south of the north boundary, {what_v}", 70, y_base, "u", v, ew)
        b = next(letters)
        section_panel(parts, opt, gm, f"SECTION {b}–{b} · north → south|{u:.1f} m east of the NW corner, {what_u}", 1170, y_base, "v", u, ns)
    parts.append(f'<text class="h1" x="70" y="44">{opt.code} · Sections through the hill</text>')
    parts.append('<text class="h2" x="70" y="68">True scale, no vertical exaggeration. Brown line = natural ground (survey TIN). '
                 'Brown hatch = dug out. Green hatch = filled. Green line = finished garden and court levels. Grey = walls holding the ground.</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<style>{CSS}</style>{DEFS}' + "".join(parts) + "</svg>")
    path_svg.write_text(svg)
