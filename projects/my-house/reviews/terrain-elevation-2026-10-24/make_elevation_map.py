"""Terrain elevation map with east-west and north-south sections for projects/my-house.

EXPLORATORY drawing, derived read-only from the latest canonical site artifact. Heights come
from the stored TIN built on the 27 surveyed spot heights; nothing in the project record is
changed. Drawn in the plot frame: origin at the NW parcel corner, u toward field-east (right),
v toward field-south (down), metres, same orientation as the floor-plan drawings.

Run from the repository root:
    .venv/bin/python projects/my-house/reviews/terrain-elevation-2026-10-24/make_elevation_map.py
"""

from __future__ import annotations

import math
import subprocess
from html import escape
from pathlib import Path

import numpy as np
from pyproj import Proj, Transformer
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.ops import linemerge, nearest_points, unary_union

from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.site import Site
from house_ai.generation.frame import DesignFrame, Ground
from house_ai.storage import ProjectStore

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[1]

# ---------------------------------------------------------------- data and frame
store = ProjectStore(PROJECT)
site = store.get(store.latest(ArtifactKind.SITE, "site"), Site)
surface = site.terrain.surface
assert surface is not None, "site has no stored TIN"
NW, SW, SE, NE = site.boundary.outer
_len = math.dist(NW, NE)
EAST = ((NE[0] - NW[0]) / _len, (NE[1] - NW[1]) / _len)
SOUTH = (EAST[1], -EAST[0])
frame = DesignFrame(NW, EAST, SOUTH, "plot frame", None, None)
ground = Ground(site, frame)

parcel = Polygon([frame.to_design(p) for p in site.boundary.outer])
tin = [(*frame.to_design((x, y)), z) for x, y, z in surface.vertices]
tin_tris = [[tin[i], tin[j], tin[k]] for i, j, k in surface.triangles]
tin_hull = unary_union([Polygon([(a[0], a[1]) for a in t]) for t in tin_tris])
outside_tin = parcel.difference(tin_hull)

# Owner-supplied CRS (EPSG:32638, status unconfirmed) only orients the north arrow.
_origin = site.coordinates.local.origin
_lon, _lat = Transformer.from_crs(32638, 4326, always_xy=True).transform(_origin[0], _origin[1])
CONVERGENCE = Proj("EPSG:32638").get_factors(_lon, _lat).meridian_convergence
U_GRID_BEARING = math.degrees(math.atan2(EAST[0], EAST[1]))
U_TRUE_BEARING = U_GRID_BEARING + CONVERGENCE


def true_bearing(frame_angle_deg: float) -> float:
    """Frame angle (from field-east toward field-south) to bearing from true north."""
    return (U_TRUE_BEARING + frame_angle_deg) % 360


def z_at(u: float, v: float) -> float | None:
    return ground.at(u, v)


# ---------------------------------------------------------------- analysis
STEP = 0.25
samples = []
for u in np.arange(-10.5 + STEP / 2, 33.0, STEP):
    for v in np.arange(STEP / 2, 18.5, STEP):
        if parcel.contains(Point(u, v)):
            z = z_at(u, v)
            if z is not None:
                samples.append((u, v, z))
S_ARR = np.array(samples)
_m = np.c_[S_ARR[:, 0], S_ARR[:, 1], np.ones(len(S_ARR))]
(GU, GV, Z0), *_ = np.linalg.lstsq(_m, S_ARR[:, 2], rcond=None)
PLANE_RMS = float(np.sqrt(np.mean((_m @ np.array([GU, GV, Z0]) - S_ARR[:, 2]) ** 2)))
FALL_GRADE = math.hypot(GU, GV)
FALL_ANGLE = math.degrees(math.atan2(-GV, -GU))
CONTOUR_ANGLE = FALL_ANGLE + 90

ROAD_EDGE_ANGLE = math.degrees(math.atan2(*reversed(frame.to_design(SW))))


def corner_height(name: str, xy: tuple[float, float]) -> tuple[float, float]:
    """Height at a corner; if it lies outside the TIN, use the nearest point of the TIN."""
    u, v = frame.to_design(xy)
    z = z_at(u, v)
    if z is not None:
        return z, 0.0
    q = nearest_points(tin_hull, Point(u, v))[0]
    d = math.hypot(q.x - u, q.y - v)
    for k in range(1, 50):  # nudge just inside the TIN edge
        z = z_at(q.x + (q.x - u) / d * k * 1e-4, q.y + (q.y - v) / d * k * 1e-4)
        if z is not None:
            return z, d
    raise RuntimeError(name)


CORNER_XY = {"NW": NW, "SW": SW, "SE": SE, "NE": NE}
CORNERS = {n: corner_height(n, xy) for n, xy in CORNER_XY.items()}

# Relief: on a linear TIN the extremes lie at TIN vertices, corners or the boundary, so add
# those to the cell-centre samples (they are not used for the plane fit).
_extremes = [tuple(r) for r in S_ARR]
_extremes += [(*frame.to_design(xy), CORNERS[n][0]) for n, xy in CORNER_XY.items()]
_extremes += [(a[0], a[1], a[2]) for a in tin if parcel.buffer(1e-6).contains(Point(a[0], a[1]))]
for _k in range(int(parcel.exterior.length / 0.1)):
    _q = parcel.exterior.interpolate(_k * 0.1)
    _z = z_at(_q.x, _q.y)
    if _z is not None:
        _extremes.append((_q.x, _q.y, _z))
RELIEF_MAX = max(_extremes, key=lambda r: r[2])
RELIEF_MIN = min(_extremes, key=lambda r: r[2])

EW_V = (3.0, 9.0, 15.0)
NS_U = (4.0, 12.0, 20.0)
EW_NAMES = ("A", "B", "C")
NS_NAMES = ("D", "E", "F")
EPS = 1e-3


def section(a: tuple[float, float], b: tuple[float, float]):
    seg = LineString([a, b]).intersection(parcel)
    (p0, p1) = list(seg.coords)[0], list(seg.coords)[-1]
    length = math.dist(p0, p1)
    n = int(length / 0.1)
    pts = []
    for i in range(n + 1):
        s = min(max(i * length / n, EPS), length - EPS)
        u = p0[0] + (p1[0] - p0[0]) * s / length
        v = p0[1] + (p1[1] - p0[1]) * s / length
        z = z_at(u, v)
        if z is not None:
            pts.append((u, v, z))
    return {"p0": p0, "p1": p1, "length": length, "pts": pts,
            "z0": pts[0][2], "z1": pts[-1][2]}


EW = [section((-12.0, v), (35.0, v)) for v in EW_V]
NS = [section((u, -1.0), (u, 20.0)) for u in NS_U]
for s in EW + NS:
    s["fall"] = s["z0"] - s["z1"]
    s["grade"] = 100 * s["fall"] / s["length"]

# ---------------------------------------------------------------- colours
ZLO, ZHI, BAND = 1664.5, 1678.0, 0.5


def turbo(t: float) -> str:
    t = 0.10 + 0.83 * min(max(t, 0.0), 1.0)
    r = 0.13572138 + t * (4.61539260 + t * (-42.66032258 + t * (
        132.13108234 + t * (-152.94239396 + t * 59.28637943))))
    g = 0.09140261 + t * (2.19418839 + t * (4.84296658 + t * (
        -14.18503333 + t * (4.27729857 + t * 2.82956604))))
    b = 0.10667330 + t * (12.64194608 + t * (-60.58204836 + t * (
        110.36276771 + t * (-89.90310912 + t * 27.34824973))))
    return "#" + "".join(f"{round(255 * min(max(c, 0.0), 1.0)):02x}" for c in (r, g, b))


def band_colour(lo: float) -> str:
    return turbo((lo + BAND / 2 - ZLO) / (ZHI - ZLO))


def clip_z(poly: list, z: float, above: bool) -> list:
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1], strict=True):
        ina = a[2] >= z if above else a[2] <= z
        inb = b[2] >= z if above else b[2] <= z
        if ina:
            out.append(a)
        if ina != inb:
            t = (z - a[2]) / (b[2] - a[2])
            out.append(tuple(a[i] + t * (b[i] - a[i]) for i in range(3)))
    return out


def band_pieces(lo: float, hi: float) -> list:
    """Per-triangle pieces of one height band, clipped to the parcel.

    Pieces are kept separate on purpose: a GEOS unary_union of these slivers silently
    dropped a 1.1 m2 piece near spot 1672.91, leaving a hole in the fill.
    """
    parts = []
    for tri in tin_tris:
        p = clip_z(clip_z(tri, lo, True), hi, False)
        if len(p) >= 3:
            poly = Polygon([(q[0], q[1]) for q in p])
            if poly.area > 1e-9:
                piece = poly.intersection(parcel)
                if not piece.is_empty:
                    parts.append(piece)
    return parts


def contour_geometry(level: float):
    segs = []
    for tri in tin_tris:
        pts = []
        for a, b in zip(tri, tri[1:] + tri[:1], strict=True):
            if (a[2] - level) * (b[2] - level) < 0:
                t = (level - a[2]) / (b[2] - a[2])
                pts.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        if len(pts) == 2:
            segs.append(pts)
    if not segs:
        return []
    merged = linemerge(MultiLineString(segs)).intersection(parcel)
    geoms = getattr(merged, "geoms", [merged])
    return [g for g in geoms if g.geom_type == "LineString" and g.length > 0.05]


# ---------------------------------------------------------------- canvas and labels
W, H = 1900, 2050
S = 30.0  # px per metre everywhere (map and both profiles)
U0, V0 = -14.0, -3.0
MX0, MY0 = 50.0, 120.0
MAP_W, MAP_H = 49.0 * S, 24.0 * S
FONT = "Helvetica, Arial, sans-serif"
INK = "#1d2730"
SEC_COLOURS = ("#111111", "#8e2c9e", "#b4520a")


def X(u: float) -> float:
    return MX0 + S * (u - U0)


def Y(v: float) -> float:
    return MY0 + S * (v - V0)


placed: list[tuple[float, float, float, float, str]] = []


def bbox(x, y, text, size, anchor="start", angle=0.0):
    w = 0.56 * size * len(text)
    h = size
    x0 = {"start": 0.0, "middle": -w / 2, "end": -w}[anchor]
    corners = [(x0, -0.8 * h), (x0 + w, -0.8 * h), (x0, 0.2 * h), (x0 + w, 0.2 * h)]
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    pts = [(x + px * c - py * s, y + px * s + py * c) for px, py in corners]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2)


def collides(b) -> bool:
    return any(b[0] < q[2] and q[0] < b[2] and b[1] < q[3] and q[1] < b[3] for q in placed)


def reserve(b, tag: str) -> None:
    placed.append((*b, tag))


def text(x, y, value, size=14, colour=INK, anchor="start", weight="normal", halo=True,
         angle=0.0, italic=False, track=True, tag="text"):
    if track:
        reserve(bbox(x, y, value, size, anchor, angle), tag + ":" + value)
    h = (' paint-order="stroke" stroke="#ffffff" stroke-width="3.5" stroke-linejoin="round"'
         if halo else "")
    rot = f' transform="rotate({angle:.1f} {x:.1f} {y:.1f})"' if angle else ""
    st = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{colour}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{st}{h}{rot}>{escape(value)}</text>')


def path_d(coords, close=False) -> str:
    d = "M" + " L".join(f"{X(u):.1f},{Y(v):.1f}" for u, v in coords)
    return d + (" Z" if close else "")


def poly_d(geom) -> str:
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type != "Polygon" or g.is_empty:
            continue
        out.append(path_d(list(g.exterior.coords)[:-1], True))
        out.extend(path_d(list(r.coords)[:-1], True) for r in g.interiors)
    return " ".join(out)


svg: list[str] = []
add = svg.append

# ---------------------------------------------------------------- header
add(text(MX0, 46, "Plot terrain: elevation map with east-west and north-south sections",
         26, weight="bold", halo=False))
add(text(MX0, 78, "projects/my-house  |  plot frame: origin NW corner, field-east to the right, "
         "field-north up, metres  |  colour = ground height (m), 0.5 m bands", 15,
         colour="#4a5560", halo=False))

# ---------------------------------------------------------------- map: road and background
add(f'<rect x="{MX0}" y="{MY0}" width="{MAP_W}" height="{MAP_H}" fill="#f4f2ec" '
    'stroke="#c9c4b8"/>')
add(f'<clipPath id="mapclip"><rect x="{MX0}" y="{MY0}" width="{MAP_W}" height="{MAP_H}"/>'
    '</clipPath>')
add('<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" '
    'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="#555" '
    'stroke-width="1.2"/></pattern>')
roads = [[frame.to_design(p) for p in f.geometry.line.points]
         for f in site.features if f.kind == "road"]
roads.sort(key=lambda r: r[0][0])
road_poly = Polygon(roads[0] + list(reversed(roads[1])))
add(f'<g clip-path="url(#mapclip)"><path d="{poly_d(road_poly)}" fill="#d9d6cf" '
    'stroke="none"/>')
for r in roads:
    add(f'<path d="{path_d(r)}" fill="none" stroke="#8b867c" stroke-width="1.5"/>')
add("</g>")

# ---------------------------------------------------------------- map: hypsometric bands
levels = np.arange(ZLO, ZHI, BAND)
filled = 0.0
for lo in levels:
    pieces = band_pieces(lo, lo + BAND)
    filled += sum(g.area for g in pieces)
    if pieces:
        c = band_colour(lo)
        d = " ".join(poly_d(g) for g in pieces)
        add(f'<path d="{d}" fill="{c}" stroke="{c}" stroke-width="0.6"/>')
assert abs(filled - (parcel.area - outside_tin.area)) < 1e-3, filled
if not outside_tin.is_empty:
    add(f'<path d="{poly_d(outside_tin)}" fill="url(#hatch)" stroke="#555" '
        'stroke-width="0.6"/>')

# ---------------------------------------------------------------- map: contours
contours = {}
for lvl in np.arange(1665.0, 1678.0, 0.5):
    lines = contour_geometry(float(lvl))
    contours[float(lvl)] = lines
    major = abs(lvl - round(lvl)) < 1e-6
    for ln in lines:
        add(f'<path d="{path_d(list(ln.coords))}" fill="none" stroke="#2a2a2a" '
            f'stroke-width="{1.8 if major else 0.7}" stroke-opacity="{0.9 if major else 0.6}"/>')

add(f'<path d="{poly_d(parcel)}" fill="none" stroke="#111" stroke-width="2.6"/>')

# ---------------------------------------------------------------- spot dots (label obstacles)
SPOTS = []
for sp in site.terrain.spot_elevations:
    u, v = frame.to_design(sp.xy)
    SPOTS.append({"id": sp.id, "u": u, "v": v, "z": sp.z_m,
                  "inside": parcel.buffer(0.05).contains(Point(u, v))})
in_extent = [s for s in SPOTS
             if U0 <= s["u"] <= U0 + MAP_W / S and V0 <= s["v"] <= V0 + MAP_H / S]
OFF_MAP = [s for s in SPOTS if s not in in_extent]
for sp in in_extent:
    x, y = X(sp["u"]), Y(sp["v"])
    reserve((x - 5, y - 5, x + 5, y + 5), "dot:" + sp["id"])

# parcel edges are label obstacles too, so spot values do not sit on the boundary line
for k in range(int(parcel.exterior.length / 0.2)):
    q = parcel.exterior.interpolate(k * 0.2)
    reserve((X(q.x) - 3, Y(q.y) - 3, X(q.x) + 3, Y(q.y) + 3), "edge")

# ---------------------------------------------------------------- map: section lines
sec_lines = []
for i, s in enumerate(EW + NS):
    (u0, v0), (u1, v1) = s["p0"], s["p1"]
    sec_lines.append(LineString([s["p0"], s["p1"]]))
    add(f'<line x1="{X(u0):.1f}" y1="{Y(v0):.1f}" x2="{X(u1):.1f}" y2="{Y(v1):.1f}" '
        'stroke="#ffffff" stroke-width="4.5"/>')
    add(f'<line x1="{X(u0):.1f}" y1="{Y(v0):.1f}" x2="{X(u1):.1f}" y2="{Y(v1):.1f}" '
        f'stroke="{SEC_COLOURS[i % 3]}" stroke-width="2.2" stroke-dasharray="10 5"/>')
    xa, ya, xb, yb = X(u0), Y(v0), X(u1), Y(v1)
    lo = min(xa, xb) - 2, min(ya, yb) - 2, max(xa, xb) + 2, max(ya, yb) + 2
    reserve(lo, "section-line")


def end_badge(x, y, label, colour) -> None:
    r = 12
    reserve((x - r - 1, y - r - 1, x + r + 1, y + r + 1), "badge:" + label)
    add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#ffffff" stroke="{colour}" '
        'stroke-width="2.2"/>')
    add(text(x, y + 5, label, 14, colour, "middle", "bold", halo=False, track=False))


for i, (s, nm) in enumerate(zip(EW, EW_NAMES, strict=True)):
    end_badge(X(s["p0"][0]) - 18, Y(s["p0"][1]), nm, SEC_COLOURS[i])
    end_badge(X(s["p1"][0]) + 18, Y(s["p1"][1]), nm + "′", SEC_COLOURS[i])
for i, (s, nm) in enumerate(zip(NS, NS_NAMES, strict=True)):
    end_badge(X(s["p0"][0]), Y(s["p0"][1]) - 18, nm, SEC_COLOURS[i])
    end_badge(X(s["p1"][0]), Y(s["p1"][1]) + 18, nm + "′", SEC_COLOURS[i])

# ---------------------------------------------------------------- map: context labels
road_ang = math.degrees(math.atan2(*reversed(frame.to_design(SW)))) - 180
road_mid_v = 6.0
road_u = frame.to_design(SW)[0] / frame.to_design(SW)[1] * road_mid_v  # west edge
add(text(X(road_u - 5.2), Y(road_mid_v), "ROAD (west, uphill side)", 16, "#3c3a35",
         "middle", "bold", angle=road_ang))
add(text(X(road_u - 3.9), Y(road_mid_v), "~9 m corridor (owner-reported)", 12,
         "#3c3a35", "middle", angle=road_ang, italic=True, track=False))
add(text(X(16.0), Y(-1.9), "North boundary (future neighbour)", 13, "#5a5a5a", "middle",
         italic=True))
add(text(X(9.0), Y(20.3), "South boundary (2 m shared pedestrian passage)", 13, "#5a5a5a",
         "middle", italic=True))
CORNER_CANDS = {
    "NW": [(-10, -8, "end"), (-6, -22, "end"), (10, -12, "start"), (-24, 6, "end")],
    "NE": [(10, -12, "start"), (0, -16, "middle"), (12, 14, "start")],
    "SW": [(-10, 18, "end"), (0, 24, "middle"), (-14, 0, "end")],
    "SE": [(10, 20, "start"), (0, 26, "middle"), (14, 6, "start")],
}
for name, xy in zip(("NW", "SW", "SE", "NE"), (NW, SW, SE, NE), strict=True):
    u, v = frame.to_design(xy)
    for dx, dy, anc in CORNER_CANDS[name]:
        if not collides(bbox(X(u) + dx, Y(v) + dy, name, 14, anc)):
            add(text(X(u) + dx, Y(v) + dy, name, 14, INK, anc, "bold"))
            break
    else:
        raise RuntimeError(f"no room for corner label {name}")

# ---------------------------------------------------------------- map: spot heights
# (spot dots were reserved as label obstacles before any map text was placed)

CANDS = [(9, 5, "start"), (-9, 5, "end"), (0, -10, "middle"), (0, 20, "middle"),
         (8, -8, "start"), (8, 17, "start"), (-8, -8, "end"), (-8, 17, "end")]
FAR = [(dx * 3.2, dy * 2.4, a) for dx, dy, a in CANDS]
spot_svg = []
for sp in sorted(in_extent, key=lambda s: (not s["inside"], s["u"])):
    x, y = X(sp["u"]), Y(sp["v"])
    label = f"{sp['z']:.2f}"
    size = 13
    chosen = None
    for dx, dy, anc in CANDS + FAR:
        b = bbox(x + dx, y + dy, label, size, anc)
        if not collides(b):
            chosen = (dx, dy, anc)
            break
    if chosen is None:
        raise RuntimeError(f"no label position for {sp['id']}")
    dx, dy, anc = chosen
    if (dx, dy, anc) in FAR:
        spot_svg.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + dx * 0.8:.1f}" '
                        f'y2="{y + dy * 0.8 - 4:.1f}" stroke="#222" stroke-width="0.9"/>')
    colour = INK if sp["inside"] else "#6b6b6b"
    spot_svg.append(text(x + dx, y + dy, label, size, colour, anc,
                         "bold" if sp["inside"] else "normal", italic=not sp["inside"],
                         tag="spot"))
    if sp["inside"]:
        spot_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#111" '
                        'stroke="#fff" stroke-width="1.6"/>')
    else:
        spot_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#fff" '
                        'stroke="#444" stroke-width="1.6"/>')

# ---------------------------------------------------------------- map: contour labels
for lvl, lines in contours.items():
    if abs(lvl - round(lvl)) > 1e-6 or not lines:
        continue
    ln = max(lines, key=lambda g: g.length)
    if ln.length < 4.0:
        continue
    label = f"{lvl:.0f}"
    for frac in (0.5, 0.35, 0.65, 0.2, 0.8, 0.1, 0.9):
        p = ln.interpolate(frac, normalized=True)
        if parcel.exterior.distance(p) < 1.2:
            continue
        q = ln.interpolate(min(frac + 0.02, 1.0), normalized=True)
        r = ln.interpolate(max(frac - 0.02, 0.0), normalized=True)
        ang = math.degrees(math.atan2(Y(q.y) - Y(r.y), X(q.x) - X(r.x)))
        if ang > 90:
            ang -= 180
        if ang < -90:
            ang += 180
        b = bbox(X(p.x), Y(p.y) + 4, label, 13, "middle", ang)
        if not collides(b):
            add(text(X(p.x), Y(p.y) + 4, label, 13, "#111", "middle", "bold", angle=ang,
                     tag="contour"))
            break
svg.extend(spot_svg)

# ---------------------------------------------------------------- right column
RX = MX0 + MAP_W + 40
add(text(RX, MY0 + 14, "Ground height (m)", 16, weight="bold", halo=False))
LEG_TOP, BH = MY0 + 34, 17
for i, lo in enumerate(reversed(levels)):
    y = LEG_TOP + i * BH
    add(f'<rect x="{RX}" y="{y:.1f}" width="34" height="{BH}" fill="{band_colour(lo)}"/>')
    if abs(lo - round(lo)) < 1e-6:
        add(f'<line x1="{RX + 34}" y1="{y + BH:.1f}" x2="{RX + 42}" y2="{y + BH:.1f}" '
            'stroke="#333"/>')
        add(text(RX + 46, y + BH + 5, f"{lo:.0f}", 13, halo=False))
leg_bottom = LEG_TOP + len(levels) * BH
add(f'<rect x="{RX}" y="{LEG_TOP}" width="34" height="{leg_bottom - LEG_TOP}" fill="none" '
    'stroke="#333"/>')
add(text(RX + 46, LEG_TOP + 5, f"{ZHI:.0f}", 13, halo=False))
add(text(RX + 100, LEG_TOP + 10, "high", 13, "#7a1a0a", halo=False, italic=True))
add(text(RX + 100, leg_bottom - 4, "low", 13, "#1a2f8a", halo=False, italic=True))

ky = leg_bottom + 34
add(f'<line x1="{RX}" y1="{ky}" x2="{RX + 34}" y2="{ky}" stroke="#2a2a2a" stroke-width="1.8"/>')
add(text(RX + 44, ky + 5, "1 m contour (labelled)", 13, halo=False))
add(f'<line x1="{RX}" y1="{ky + 22}" x2="{RX + 34}" y2="{ky + 22}" stroke="#2a2a2a" '
    'stroke-width="0.7"/>')
add(text(RX + 44, ky + 27, "0.5 m contour", 13, halo=False))
add(f'<circle cx="{RX + 17}" cy="{ky + 44}" r="4.2" fill="#111" stroke="#fff"/>')
add(text(RX + 44, ky + 49, "surveyed spot, in parcel", 13, halo=False))
add(f'<circle cx="{RX + 17}" cy="{ky + 66}" r="4.2" fill="#fff" stroke="#444" '
    'stroke-width="1.6"/>')
add(text(RX + 44, ky + 71, "surveyed spot, off parcel", 13, halo=False))
add(f'<rect x="{RX + 4}" y="{ky + 82}" width="26" height="14" fill="url(#hatch)" '
    'stroke="#555"/>')
add(text(RX + 44, ky + 93, "outside TIN (no data)", 13, halo=False))
add(f'<line x1="{RX}" y1="{ky + 110}" x2="{RX + 34}" y2="{ky + 110}" stroke="#111" '
    'stroke-width="2.2" stroke-dasharray="10 5"/>')
add(text(RX + 44, ky + 115, "section line", 13, halo=False))

# north arrow (true north, from owner-supplied CRS)
NAX, NAY = RX + 70, ky + 210
tn = math.radians(-U_TRUE_BEARING)  # true north as frame angle from +u toward +v
tn_dx, tn_dy = math.cos(tn), math.sin(tn)
# frame angle of north: north is -U_TRUE_BEARING from field-east
ln_ = 48
tipx, tipy = NAX + tn_dx * ln_, NAY + tn_dy * ln_
tailx, taily = NAX - tn_dx * ln_ * 0.6, NAY - tn_dy * ln_ * 0.6
px_, py_ = -tn_dy, tn_dx
add(f'<line x1="{tailx:.1f}" y1="{taily:.1f}" x2="{tipx:.1f}" y2="{tipy:.1f}" stroke="#111" '
    'stroke-width="2.4"/>')
add(f'<path d="M{tipx:.1f},{tipy:.1f} L{tipx - tn_dx * 18 + px_ * 8:.1f},'
    f'{tipy - tn_dy * 18 + py_ * 8:.1f} L{tipx - tn_dx * 18 - px_ * 8:.1f},'
    f'{tipy - tn_dy * 18 - py_ * 8:.1f} Z" fill="#111"/>')
add(text(tipx + tn_dx * 16, tipy + tn_dy * 16 + 6, "N", 20, "#111", "middle", "bold"))
add(text(RX, NAY + 62, "True north (owner-supplied", 12, "#333", halo=False))
add(text(RX, NAY + 78, "CRS EPSG:32638, unconfirmed)", 12, "#333", halo=False))
add(text(RX, NAY + 96, f"field-east = {U_TRUE_BEARING:.1f}° true", 12, "#333",
         halo=False))

# scale bar
SBY = NAY + 140
add(text(RX, SBY - 10, "Scale (map and sections)", 13, weight="bold", halo=False))
for i in range(5):
    add(f'<rect x="{RX + i * 2 * S:.1f}" y="{SBY}" width="{2 * S:.1f}" height="8" '
        f'fill="{"#111" if i % 2 == 0 else "#fff"}" stroke="#111"/>')
for m in (0, 5, 10):
    add(text(RX + m * S, SBY + 24, f"{m}", 12, anchor="middle", halo=False))
add(text(RX + 10 * S + 12, SBY + 24, "m", 12, halo=False))

# ---------------------------------------------------------------- profiles
ZT, ZB = 1678.5, 1664.5


def profile_panel(title, secs, names, xfun, x_lo, x_hi, top, axis_label, tick_vals):
    yz = lambda z: top + S * (ZT - z)  # noqa: E731
    left, right = xfun(x_lo), xfun(x_hi)
    add(text(left - 60, top - 22, title, 17, weight="bold", halo=False))
    add(f'<rect x="{left:.1f}" y="{top:.1f}" width="{right - left:.1f}" '
        f'height="{S * (ZT - ZB):.1f}" fill="#fbfaf7" stroke="#999"/>')
    for z in np.arange(ZB + 0.5, ZT, 1.0):
        add(f'<line x1="{left:.1f}" y1="{yz(z):.1f}" x2="{right:.1f}" y2="{yz(z):.1f}" '
            f'stroke="#e3e0d8" stroke-width="{1.0}"/>')
        if abs(z % 2) < 1e-6:
            add(text(left - 8, yz(z) + 4, f"{z:.0f}", 12, anchor="end", halo=False))
    for t in tick_vals:
        add(f'<line x1="{xfun(t):.1f}" y1="{top:.1f}" x2="{xfun(t):.1f}" '
            f'y2="{yz(ZB):.1f}" stroke="#ece9e2"/>')
        add(text(xfun(t), yz(ZB) + 18, f"{t:g}", 12, anchor="middle", halo=False))
    add(text((left + right) / 2, yz(ZB) + 38, axis_label, 13, "#333", "middle", halo=False))
    add(text(left - 52, top + S * (ZT - ZB) / 2, "height (m)", 13, "#333", "middle",
             halo=False, angle=-90, track=False))
    for i, (s, nm) in enumerate(zip(secs, names, strict=True)):
        pts = [(xfun(p[0] if axis_label.startswith("u") else p[1]), yz(p[2]))
               for p in s["pts"]]
        d = "M" + " L".join(f"{a:.1f},{b:.1f}" for a, b in pts)
        add(f'<path d="{d}" fill="none" stroke="{SEC_COLOURS[i]}" stroke-width="2.6"/>')
        (xa, ya), (xb, yb) = pts[0], pts[-1]
        add(f'<circle cx="{xa:.1f}" cy="{ya:.1f}" r="3.5" fill="{SEC_COLOURS[i]}"/>')
        add(f'<circle cx="{xb:.1f}" cy="{yb:.1f}" r="3.5" fill="{SEC_COLOURS[i]}"/>')
        add(text(xa + 7, ya - 9, nm, 15, SEC_COLOURS[i], "start", "bold"))
        add(text(xb + 8, yb + 18, nm + "′", 15, SEC_COLOURS[i], "start", "bold"))
    ty = yz(ZB) + 66
    for i, s in enumerate(secs):
        add(f'<line x1="{left:.1f}" y1="{ty + i * 22 - 5:.1f}" x2="{left + 28:.1f}" '
            f'y2="{ty + i * 22 - 5:.1f}" stroke="{SEC_COLOURS[i]}" stroke-width="2.6"/>')
        add(text(left + 36, ty + i * 22, s["desc"], 13, halo=False))
    return ty + 3 * 22


for s, nm, v in zip(EW, EW_NAMES, EW_V, strict=True):
    s["desc"] = (f"{nm}–{nm}′ (v = {v:g} m): {s['z0']:.2f} → {s['z1']:.2f} m, "
                 f"fall {s['fall']:.2f} m over {s['length']:.2f} m = {s['grade']:.1f} % "
                 "toward field-east")
for s, nm, u in zip(NS, NS_NAMES, NS_U, strict=True):
    s["desc"] = (f"{nm}–{nm}′ (u = {u:g} m): {s['z0']:.2f} → {s['z1']:.2f} m, "
                 f"fall {s['fall']:.2f} m over {s['length']:.2f} m = {s['grade']:.1f} %")

P1 = MY0 + MAP_H + 70
end1 = profile_panel(
    "East–west sections A, B, C (field-west/road left, field-east right) — "
    "1:1, no vertical exaggeration; horizontal position aligned with the map",
    EW, EW_NAMES, X, -11.0, 33.5, P1, "u = distance toward field-east from NW corner (m)",
    list(range(-10, 35, 5)),
)
NSX0 = 130.0
P2 = end1 + 70


def xns(v: float) -> float:
    return NSX0 + S * v


end2 = profile_panel(
    "North–south sections D, E, F — 1:1, no vertical exaggeration",
    NS, NS_NAMES, xns, 0.0, 18.42, P2,
    "v = distance toward field-south from north boundary (m)", [0, 5, 10, 15, 18.42],
)
add(text(NSX0, P2 - 4, "field-north", 12, "#555", italic=True, halo=False, track=False))
add(text(xns(18.42), P2 - 4, "field-south", 12, "#555", "end", italic=True, halo=False,
         track=False))

# ---------------------------------------------------------------- fall summary box
BX, BY, BW = 760.0, P2 - 10, 1110.0
ew_mean = sum(s["grade"] for s in EW) / 3
ns_mean = sum(s["grade"] for s in NS) / 3
zmax, zmin = RELIEF_MAX, RELIEF_MIN
lines_box = [
    ("Fall summary (least-squares plane over "
     f"{len(S_ARR)} in-parcel TIN samples, 0.25 m grid)", True),
    (f"Plane: z = {Z0:.2f} − {-GU:.4f}·u − {-GV:.4f}·v  (u, v in m; "
     f"RMS residual {PLANE_RMS:.2f} m)", False),
    (f"Average E–W grade: {-100 * GU:.1f} % falling toward field-east "
     f"(sections A–C mean {ew_mean:.1f} %)", False),
    (f"Average N–S grade: {-100 * GV:.1f} % falling toward field-south "
     f"(sections D–F mean {ns_mean:.1f} %)", False),
    (f"Steepest fall: {100 * FALL_GRADE:.1f} % toward {FALL_ANGLE:.1f}° from field-east "
     f"toward field-south = true bearing {true_bearing(FALL_ANGLE):.0f}°",
     False),
    ("(about due east, if the owner-supplied CRS is confirmed)", False),
    (f"Contours run at {CONTOUR_ANGLE:.1f}° in the frame; the west (road) edge runs at "
     f"{ROAD_EDGE_ANGLE:.1f}°, so the road follows the contour line", False),
    ("and NW and SW stand at nearly the same height. The N–S fall along a fixed-u line is "
     "mostly the main", False),
    ("downhill slope seen obliquely: field axes follow the north boundary, not the slope.",
     False),
    (f"N–S fall is stronger near the road (D {NS[0]['grade']:.1f} %) than downhill "
     f"(F {NS[2]['grade']:.1f} %): the ground is not a perfect plane.", False),
    (f"Total relief in parcel: {zmax[2] - zmin[2]:.2f} m ({zmax[2]:.2f} m near u = "
     f"{zmax[0]:.1f}, v = {zmax[1]:.1f}; {zmin[2]:.2f} m near u = {zmin[0]:.1f}, "
     f"v = {zmin[1]:.1f})", False),
    ("Corner heights (TIN): " + ",  ".join(
        f"{n} {z:.2f}" + ("*" if off > 0 else "") for n, (z, off) in CORNERS.items()), False),
]
se_off = CORNERS["SE"][1]
if se_off > 0:
    lines_box.append((f"* SE corner lies in a {outside_tin.area:.2f} m² sliver outside the "
                      f"TIN; value taken at the nearest TIN point, {se_off:.2f} m away.", False))
n_in = sum(1 for s in SPOTS if s["inside"])
lines_box.append((f"Spot heights: {n_in} of {len(SPOTS)} inside the parcel; "
                  f"{len(in_extent) - n_in} off-parcel shown hollow; {len(OFF_MAP)} beyond the "
                  "map edge not drawn.", False))
box_h = 30 + 24 * len(lines_box)
add(f'<rect x="{BX}" y="{BY}" width="{BW}" height="{box_h}" fill="#ffffff" stroke="#333" '
    'stroke-width="1.4" rx="6"/>')
for i, (ln, bold) in enumerate(lines_box):
    add(text(BX + 16, BY + 28 + i * 24, ln, 16 if bold else 14,
             weight="bold" if bold else "normal", halo=False))

# ---------------------------------------------------------------- footer
FY = max(end2, BY + box_h) + 44
add(text(MX0, FY, "Heights interpolated from 27 surveyed spot heights (TIN); vertical datum and "
         "CRS unconfirmed; EXPLORATORY, 24 Oct 2026.", 15, "#333", weight="bold", halo=False))
H = int(FY + 30)

doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
       f'viewBox="0 0 {W} {H}" font-family="{FONT}">'
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>' + "\n".join(svg) + "</svg>\n")
(OUT / "terrain-elevation.svg").write_text(doc, encoding="utf-8")
subprocess.run(["rsvg-convert", "-o", str(OUT / "terrain-elevation.png"),
                str(OUT / "terrain-elevation.svg")], check=True)

# ---------------------------------------------------------------- report
def is_text(tag: str) -> bool:
    return not (tag in ("edge", "section-line") or tag.startswith(("dot:", "badge:")))


overlaps = [
    (a[4], b[4]) for i, a in enumerate(placed) for b in placed[i + 1:]
    if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    and (is_text(a[4]) or is_text(b[4]))
]
print("label overlaps:", overlaps or "none")
print(f"u true bearing {U_TRUE_BEARING:.2f} (grid {U_GRID_BEARING:.2f}, conv {CONVERGENCE:.3f})")
print(f"plane z = {Z0:.3f} {GU:+.5f} u {GV:+.5f} v, rms {PLANE_RMS:.3f}, n {len(S_ARR)}")
print(f"steepest {100 * FALL_GRADE:.2f}% at {FALL_ANGLE:.2f} deg frame, "
      f"true {true_bearing(FALL_ANGLE):.1f}; contour {CONTOUR_ANGLE:.1f}; "
      f"road {ROAD_EDGE_ANGLE:.1f}")
print("relief", zmax, zmin)
print("corners", CORNERS)
for s in EW + NS:
    print(s["desc"])
print("spots inside", n_in, "off-map", [s["id"] for s in OFF_MAP])
