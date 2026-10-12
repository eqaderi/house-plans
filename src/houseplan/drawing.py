"""Plan drawings as DXF, in millimetres, one modelspace per level.

The sheet frame and title block are drawn in modelspace at drawing scale, so
a sheet rendered at 1:SCALE comes out at true paper size.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import ezdxf
from ezdxf import bbox
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from .geometry import LevelGeom, faces_of, frame_of
from .model import Design, OpeningKind, Site, WallKind

# name: (ACI colour, lineweight in 1/100 mm per ISO 128 series)
LAYERS = {
    "A-WALL": (7, 50),
    "A-WALL-PATN": (8, 0),
    "A-WALL-HEAD": (7, 13),
    "A-DOOR": (7, 25),
    "A-DOOR-SWNG": (7, 13),
    "A-GLAZ": (5, 25),
    "A-STAIR": (7, 25),
    "A-AREA-IDEN": (7, 18),
    "A-ANNO-DIMS": (7, 18),
    "A-ANNO-SYMB": (7, 25),
    "A-ANNO-TTLB": (7, 35),
    "V-PROP-LINE": (1, 50),
    "C-ROAD": (8, 25),
    "A-SITE-NOBLD": (8, 13),
    "V-SPOT": (7, 18),
}

PAPERS = {"A3": (420, 297), "A2": (594, 420), "A1": (841, 594), "A0": (1189, 841)}


@dataclass(frozen=True)
class Sheet:
    scale: int
    paper: str
    frame: tuple[float, float, float, float]  # modelspace min_x, min_y, max_x, max_y


def _poly(msp, coords, layer, closed=True):
    msp.add_lwpolyline([(x, y) for x, y in coords], close=closed, dxfattribs={"layer": layer})


def _rings(geom):
    for p in getattr(geom, "geoms", [geom]):
        if isinstance(p, Polygon) and not p.is_empty:
            yield p


def _setup(doc, scale: int, dim_unit: str):
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LWDISPLAY"] = 1
    doc.header["$LTSCALE"] = scale / 2
    for name, (color, lw) in LAYERS.items():
        doc.layers.add(name, color=color, lineweight=lw)
    k = scale
    ds = doc.dimstyles.new("PLAN")
    ds.dxf.dimtxt = 2.0 * k
    ds.dxf.dimblk = "ARCHTICK"
    ds.dxf.dimasz = 1.2 * k
    ds.dxf.dimexe = 1.0 * k
    ds.dxf.dimfxlon = 1
    ds.dxf.dimfxl = 1.5 * k
    ds.dxf.dimexo = 1.0 * k
    ds.dxf.dimgap = 0.6 * k
    ds.dxf.dimtad = 1
    ds.dxf.dimdec = 1
    ds.dxf.dimzin = 8
    ds.dxf.dimdsep = ord(".")
    ds.dxf.dimlfac = {"mm": 1.0, "cm": 0.1, "m": 0.001}[dim_unit]
    if dim_unit == "m":
        ds.dxf.dimdec = 2


def _text(msp, s, at, height, layer, align=TextEntityAlignment.MIDDLE_CENTER):
    return msp.add_text(s, height=height, dxfattribs={"layer": layer, "style": "Standard"}).set_placement(at, align=align)


def _walls(msp, lg: LevelGeom):
    cuts = unary_union([og.cut for og in lg.openings.values()])
    solid = lg.walls_union.difference(cuts) if not cuts.is_empty else lg.walls_union
    for p in _rings(solid):
        _poly(msp, p.exterior.coords, "A-WALL")
        for r in p.interiors:
            _poly(msp, r.coords, "A-WALL")
        hatch = msp.add_hatch(color=8, dxfattribs={"layer": "A-WALL-PATN"})
        hatch.paths.add_polyline_path(list(p.exterior.coords), is_closed=True, flags=1)
        for r in p.interiors:
            hatch.paths.add_polyline_path(list(r.coords), is_closed=True, flags=16)


def _openings(msp, lg: LevelGeom):
    for og in lg.openings.values():
        o, f = og.opening, frame_of(og.wall)
        a, b = faces_of(og.wall)
        s0, s1 = o.offset, o.offset + o.width
        if o.kind is OpeningKind.window:
            for t in (a, b):
                msp.add_line(f.at(s0, t), f.at(s1, t), dxfattribs={"layer": "A-GLAZ"})
            mid = (a + b) / 2
            for t in (mid - 15, mid + 15):
                msp.add_line(f.at(s0, t), f.at(s1, t), dxfattribs={"layer": "A-GLAZ"})
        elif o.kind is OpeningKind.opening:
            for t in (a, b):
                msp.add_line(f.at(s0, t), f.at(s1, t), dxfattribs={"layer": "A-WALL-HEAD", "linetype": "DASHED"})
        elif o.kind is OpeningKind.door:
            leaf = o.leaf or o.width
            face, side = (b, 1.0) if o.swing == "left" else (a, -1.0)
            hs, toward = (s0, 1.0) if o.hinge == "start" else (s1, -1.0)
            hinge = f.at(hs, face)
            open_tip = f.at(hs, face + side * leaf)
            msp.add_lwpolyline([hinge, open_tip], dxfattribs={"layer": "A-DOOR", "const_width": 0})
            pts = [f.at(hs + toward * leaf * math.cos(math.radians(i)), face + side * leaf * math.sin(math.radians(i))) for i in range(0, 91, 3)]
            msp.add_lwpolyline(pts, dxfattribs={"layer": "A-DOOR-SWNG"})


def _stairs(msp, design: Design, lg: LevelGeom, k: int):
    for s in (s for s in design.stairs if s.level == lg.level_id):
        fp = lg.stairs[s.id]
        _poly(msp, fp.exterior.coords, "A-STAIR")
        x, y = s.origin
        ux, uy = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[s.direction]
        nx, ny = -uy, ux
        half = s.width / 2
        for i in range(1, s.risers - 1):
            d = i * s.going
            msp.add_line((x + ux * d + nx * half, y + uy * d + ny * half), (x + ux * d - nx * half, y + uy * d - ny * half), dxfattribs={"layer": "A-STAIR"})
        run = (s.risers - 1) * s.going
        msp.add_line((x, y), (x + ux * run, y + uy * run), dxfattribs={"layer": "A-STAIR"})
        tip = (x + ux * run, y + uy * run)
        ah = 1.5 * k
        msp.add_lwpolyline([(tip[0] - ux * ah + nx * ah / 2, tip[1] - uy * ah + ny * ah / 2), tip, (tip[0] - ux * ah - nx * ah / 2, tip[1] - uy * ah - ny * ah / 2)], dxfattribs={"layer": "A-STAIR"})
        climb = design.level(s.to_level).ffl - design.level(s.level).ffl
        _text(msp, f"{s.risers} x {climb / s.risers:.1f} / {s.going}", (x + nx * (half + 2.5 * k), y + ny * (half + 2.5 * k)), 1.8 * k, "A-STAIR", TextEntityAlignment.MIDDLE_CENTER)


def _rooms(msp, design: Design, lg: LevelGeom, k: int):
    clear = design.level(lg.level_id).clear_height
    for rg in lg.rooms.values():
        if rg.outline is None:
            continue
        c = rg.outline.representative_point()
        minx, miny, maxx, maxy = rg.outline.bounds
        rect = abs(rg.outline.area - (maxx - minx) * (maxy - miny)) < 1.0
        _text(msp, rg.room.name.upper(), (c.x, c.y + 4.0 * k), 2.5 * k, "A-AREA-IDEN")
        _text(msp, f"{rg.area_mm2 / 1e6:.2f} m²", (c.x, c.y), 2.0 * k, "A-AREA-IDEN")
        sub = f"{(maxx - minx) / 1000:.2f} x {(maxy - miny) / 1000:.2f}  h={clear / 1000:.2f}" if rect else f"h={clear / 1000:.2f}"
        _text(msp, sub, (c.x, c.y - 3.6 * k), 1.6 * k, "A-AREA-IDEN")


def _chains(msp, design: Design, lg: LevelGeom, k: int):
    """Three exterior dimension chains per side, from the wall outward:
    openings and corners, wall faces, overall."""
    if lg.footprint.is_empty:
        return
    raw = lg.footprint
    fp = raw.simplify(0)
    minx, miny, maxx, maxy = fp.bounds
    sides = {"S": (0, -1, miny), "N": (0, 1, maxy), "W": (-1, 0, minx), "E": (1, 0, maxx)}
    for dx, dy, edge in sides.values():
        horizontal = dy != 0

        def coord(x, y):
            return round(x if horizontal else y, 2)

        corners = {coord(x, y) for p in _rings(fp) for x, y in p.exterior.coords}
        faces = set(corners) | {
            coord(x, y)
            for p in _rings(raw)
            for x, y in p.exterior.coords
            if abs((y if horizontal else x) - edge) < 0.5
        }
        openings = set(corners)
        for og in lg.openings.values():
            if og.wall.kind is not WallKind.exterior:
                continue
            f = frame_of(og.wall)
            if abs(f.ux * dx + f.uy * dy) > 1e-9:
                continue
            a, b = faces_of(og.wall)
            mid = og.opening.offset + og.opening.width / 2
            for face, sign in ((a, -1.0), (b, 1.0)):
                facing = (f.nx * dx + f.ny * dy) * sign > 0
                if facing and not fp.contains(Point(f.at(mid, face + sign * 50))):
                    for s in (og.opening.offset, og.opening.offset + og.opening.width):
                        openings.add(coord(*f.at(s, face)))
        rows = [sorted(openings), sorted(faces), [min(corners), max(corners)]]
        rows = [r for i, r in enumerate(rows) if len(r) >= 2 and r not in rows[:i]]
        for ring, values in enumerate(rows, start=1):
            off = edge + (dx + dy) * (ring * 7.0 * k + 3.0 * k)
            if horizontal:
                points, base, angle = [(v, edge) for v in values], (values[0], off), 0
            else:
                points, base, angle = [(edge, v) for v in values], (off, values[0]), 90
            msp.add_multi_point_linear_dim(base=base, points=points, angle=angle, dimstyle="PLAN", dxfattribs={"layer": "A-ANNO-DIMS"})


def _north(msp, at, k, angle_deg):
    x, y = at
    r = 6 * k
    msp.add_circle((x, y), r, dxfattribs={"layer": "A-ANNO-SYMB"})
    a = math.radians(-angle_deg)
    tip = (x + r * math.sin(a), y + r * math.cos(a))
    tail = (x - r * math.sin(a), y - r * math.cos(a))
    left = (x - r * 0.4 * math.cos(a), y + r * 0.4 * math.sin(a))
    right = (x + r * 0.4 * math.cos(a), y - r * 0.4 * math.sin(a))
    msp.add_lwpolyline([tip, left, tail, right, tip], dxfattribs={"layer": "A-ANNO-SYMB"})
    _text(msp, "N", (tip[0], tip[1] + 3 * k), 3 * k, "A-ANNO-SYMB")


def _scale_bar(msp, at, k):
    x, y = at
    for i in range(5):
        _poly(msp, [(x + i * 1000, y), (x + (i + 1) * 1000, y), (x + (i + 1) * 1000, y + 1.5 * k), (x + i * 1000, y + 1.5 * k)], "A-ANNO-SYMB")
        if i % 2 == 0:
            h = msp.add_hatch(color=7, dxfattribs={"layer": "A-ANNO-SYMB"})
            h.paths.add_polyline_path([(x + i * 1000, y), (x + (i + 1) * 1000, y), (x + (i + 1) * 1000, y + 1.5 * k), (x + i * 1000, y + 1.5 * k)], is_closed=True)
        _text(msp, f"{i}", (x + i * 1000, y - 2.5 * k), 1.8 * k, "A-ANNO-SYMB")
    _text(msp, "5 m", (x + 5000, y - 2.5 * k), 1.8 * k, "A-ANNO-SYMB")


def _sheet(bounds: tuple[float, float, float, float], scale: int) -> Sheet:
    minx, miny, maxx, maxy = bounds
    need_w = (maxx - minx) / scale + 2 * 30 + 20
    need_h = (maxy - miny) / scale + 2 * 30 + 45
    paper = next((p for p, (w, h) in PAPERS.items() if w >= need_w and h >= need_h), "A0")
    w, h = PAPERS[paper]
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2 + 15 * scale
    return Sheet(scale, paper, (cx - w * scale / 2, cy - h * scale / 2, cx + w * scale / 2, cy + h * scale / 2))


def _title_block(msp, design: Design, title: str, sheet: Sheet, status: str):
    k = sheet.scale
    x0, y0, x1, y1 = sheet.frame
    m = 10 * k
    _poly(msp, [(x0 + 20 * k, y0 + m), (x1 - m, y0 + m), (x1 - m, y1 - m), (x0 + 20 * k, y1 - m)], "A-ANNO-TTLB")
    tb_w, tb_h = 180 * k, 32 * k
    tx, ty = x1 - m - tb_w, y0 + m
    _poly(msp, [(tx, ty), (tx + tb_w, ty), (tx + tb_w, ty + tb_h), (tx, ty + tb_h)], "A-ANNO-TTLB")
    lines = [
        (design.project.name, 4.0),
        (title, 2.8),
        (f"Scale 1:{k} on {sheet.paper}   dimensions in {design_dim_unit(design)}   {dt.date.today().isoformat()}", 2.2),
        (f"Ruleset: {design.project.ruleset or 'none'}   Check: {status}", 2.2),
        ("DESIGN CHECK DRAWING - NOT FOR CONSTRUCTION OR PERMIT UNTIL REVIEWED AND SIGNED", 2.0),
    ]
    y = ty + tb_h - 6 * k
    for s, h in lines:
        _text(msp, s, (tx + 4 * k, y), h * k, "A-ANNO-TTLB", TextEntityAlignment.MIDDLE_LEFT)
        y -= (h + 3.2) * k
    _north(msp, (x0 + 40 * k, y1 - 30 * k), k, design.project.north_angle_deg)
    _scale_bar(msp, (x0 + 30 * k, y0 + 22 * k), k)


def _site_context(msp, site: Site, k: int):
    """Plot boundary and no-build zones, without text: the frame a plan sits in."""
    _poly(msp, site.boundary, "V-PROP-LINE")
    for zone in site.no_build:
        _poly(msp, zone.outline, "A-SITE-NOBLD")
        hatch = msp.add_hatch(dxfattribs={"layer": "A-SITE-NOBLD"})
        hatch.set_pattern_fill("ANSI31", scale=k / 2)
        hatch.paths.add_polyline_path(zone.outline, is_closed=True)


def _along(line: LineString, at: float, offset: float, away_from: Point) -> tuple[tuple[float, float], float]:
    """A point `at` (0..1) along a line, `offset` to the side away from a
    point, and the line's readable text angle there."""
    p = line.interpolate(at, normalized=True)
    q = line.interpolate(min(at + 0.01, 1.0), normalized=True)
    ux, uy = q.x - p.x, q.y - p.y
    n = math.hypot(ux, uy) or 1.0
    nx, ny = -uy / n, ux / n
    if (away_from.x - p.x) * nx + (away_from.y - p.y) * ny > 0:
        nx, ny = -nx, -ny
    angle = math.degrees(math.atan2(uy, ux))
    angle = angle - 180 if angle > 90 else angle + 180 if angle <= -90 else angle
    return (p.x + nx * offset, p.y + ny * offset), angle


def _free_text(msp, s, options, height, layer, placed: list, pad: float):
    """Write `s` at the first of `options` (at, align, rotation) whose extents
    keep `pad` clear of every text already placed; else at the last one."""
    for i, (at, align, rotation) in enumerate(options):
        e = _text(msp, s, at, height, layer, align)
        e.dxf.rotation = rotation
        b = bbox.extents([e], fast=False)
        ext = box(b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)
        if i == len(options) - 1 or not any(ext.distance(p) < pad for p in placed):
            placed.append(ext)
            return e
        msp.delete_entity(e)


def site_dxf(design: Design, geo: dict[str, LevelGeom], scale: int = 200, status: str = "unchecked") -> tuple[ezdxf.document.Drawing, Sheet]:
    """The site sheet: plot boundary with its side lengths, roads, no-build
    zones, surveyed spot heights and the building's outline on each level."""
    site = design.site
    doc = ezdxf.new("R2018", setup=True)
    _setup(doc, scale, design_dim_unit(design))
    msp = doc.modelspace()
    k = scale
    _site_context(msp, site, k)
    plot = Polygon(site.boundary)
    centre = plot.centroid
    placed: list = []
    pad = 1.0 * k  # 1 mm on paper, as the text audit asks
    mid = TextEntityAlignment.MIDDLE_CENTER
    c = 0.8 * k
    corners = [(1, 1, TextEntityAlignment.BOTTOM_LEFT), (-1, 1, TextEntityAlignment.BOTTOM_RIGHT),
               (1, -1, TextEntityAlignment.TOP_LEFT), (-1, -1, TextEntityAlignment.TOP_RIGHT)]
    for h in site.spot_heights:
        # cross at the point; label in the first free corner, towards the plot's middle first
        x, y = h.at
        msp.add_line((x - c, y - c), (x + c, y + c), dxfattribs={"layer": "V-SPOT"})
        msp.add_line((x - c, y + c), (x + c, y - c), dxfattribs={"layer": "V-SPOT"})
        order = sorted(corners, key=lambda q: -(q[0] * (centre.x - x) + q[1] * (centre.y - y)))
        options = [((x + sx * 1.2 * c, y + sy * 1.2 * c), align, 0) for sx, sy, align in order]
        _free_text(msp, f"{h.name} {h.survey_z_mm / 1000:.3f}", options, 1.6 * k, "V-SPOT", placed, pad)
    ring = list(site.boundary) + [site.boundary[0]]
    for a, b in zip(ring, ring[1:]):
        side = LineString([a, b])
        options = [_along(side, t, 3.0 * k, centre) for t in (0.5, 0.35, 0.65)]
        _free_text(msp, f"{side.length / 1000:.3f} m", [(at, mid, angle) for at, angle in options], 2.2 * k, "V-PROP-LINE", placed, pad)
    for road in site.roads:
        line = LineString(road.points)
        _poly(msp, road.points, "C-ROAD", closed=False)
        options = [_along(line, t, 2.5 * k, centre) for t in (0.15, 0.85, 0.05, 0.95, 0.3, 0.7, 0.5)]
        _free_text(msp, road.name.upper(), [(at, mid, angle) for at, angle in options], 1.8 * k, "C-ROAD", placed, pad)
    for zone in site.no_build:
        # labelled outside the plot, beside its longest edge on the boundary
        zr = list(zone.outline) + [zone.outline[0]]
        edges = [e for e in (LineString([a, b]) for a, b in zip(zr, zr[1:])) if e.interpolate(0.5, normalized=True).distance(plot.exterior) < 1.0]
        edge = max(edges or [LineString(zr[:2])], key=lambda e: e.length)
        options = [_along(edge, t, 3.0 * k, centre) for t in (0.25, 0.75, 0.5)]
        _free_text(msp, f"{zone.name.upper()} - NO BUILDING", [(at, mid, angle) for at, angle in options], 1.8 * k, "A-SITE-NOBLD", placed, pad)
    levels = sorted(design.levels, key=lambda l: l.ffl)
    for i, lv in enumerate(levels):
        fp = geo[lv.id].footprint
        for p in _rings(fp):
            msp.add_lwpolyline(list(p.exterior.coords), close=True, dxfattribs={"layer": "A-WALL" if i == 0 else "A-WALL-HEAD", "linetype": "CONTINUOUS" if i == 0 else "DASHED"})
    pts = [*site.points(), *(xy for lv in levels for p in _rings(geo[lv.id].footprint) for xy in p.exterior.coords)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    sheet = _sheet((min(xs), min(ys), max(xs), max(ys)), scale)
    title = f"Site plan  spot heights: survey Z in m  building: {levels[0].id} solid, upper levels dashed"
    _title_block(msp, design, title, sheet, status)
    return doc, sheet


def design_dim_unit(design: Design) -> str:
    return "cm" if design.project.jurisdiction.upper() == "IR" else "mm"


def plan_dxf(design: Design, lg: LevelGeom, scale: int = 100, status: str = "unchecked") -> tuple[ezdxf.document.Drawing, Sheet]:
    doc = ezdxf.new("R2018", setup=True)
    _setup(doc, scale, design_dim_unit(design))
    msp = doc.modelspace()
    _walls(msp, lg)
    _openings(msp, lg)
    _stairs(msp, design, lg, scale)
    _rooms(msp, design, lg, scale)
    _chains(msp, design, lg, scale)
    bounds = lg.footprint.bounds if not lg.footprint.is_empty else (0, 0, 1, 1)
    if design.site is not None:
        _site_context(msp, design.site, scale)
        bounds = unary_union([Polygon(design.site.boundary), lg.footprint]).bounds
    sheet = _sheet(bounds, scale)
    lv = design.level(lg.level_id)
    _title_block(msp, design, f"Floor plan {lv.name}  FFL {lv.ffl / 1000:+.2f}  ({design.project.datum.label})", sheet, status)
    return doc, sheet
