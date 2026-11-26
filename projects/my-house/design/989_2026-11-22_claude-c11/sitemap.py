"""Site plan: the field coloured by height, with the three floors, the garden and the section lines on it."""

from __future__ import annotations

import math
from html import escape
from pathlib import Path

import engine as E
from shapely.geometry import LineString, Point, box

RAINBOW = [(.23, .38, .85), (.16, .71, .85), (.25, .82, .56), (.73, .88, .29), (.96, .78, .24), (.94, .42, .18), (.70, .09, .17)]
Z_LO, Z_HI = 1664.5, 1678.2
LEVEL_INK = {"road": "#22343f", "main": "#0f6f8a", "lower": "#8a3d1d"}

CSS = """
.cell{stroke:none}
.fp{fill:#fff;fill-opacity:.34;stroke-width:3}
.day{fill:none;stroke-width:2.6;stroke-dasharray:10 5}
.sec{stroke:#111;stroke-width:1.3;stroke-dasharray:14 4 2 4;fill:none}
.bub{fill:#111}.bubt{font:700 13px Helvetica,Arial,sans-serif;fill:#fff}
.spot{font:700 12px Helvetica,Arial,sans-serif;fill:#111}
.spotbg{fill:#fff;fill-opacity:.85}
.arrow2{stroke:#111;stroke-width:2.4;fill:none;marker-end:url(#ar2)}
.gline{fill:none;stroke:#3d6b2a;stroke-width:1.6}
.pav{fill:#fff;fill-opacity:.35;stroke:#6d5b3c;stroke-width:1.2}
.key{font:400 12.5px Helvetica,Arial,sans-serif;fill:#22343f}
.keyb{font:700 12.5px Helvetica,Arial,sans-serif;fill:#22343f}
"""


def colour(z: float) -> str:
    t = min(1.0, max(0.0, (z - Z_LO) / (Z_HI - Z_LO))) * (len(RAINBOW) - 1)
    i = min(len(RAINBOW) - 2, int(t))
    f = t - i
    r, g, b = (RAINBOW[i][k] + (RAINBOW[i + 1][k] - RAINBOW[i][k]) * f for k in range(3))
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def level_line(lev: float) -> list[list[tuple[float, float]]]:
    """Marching squares on the TIN at one height, inside the parcel."""
    us = [x * 0.25 for x in range(-48, 140)]
    vs = [y * 0.25 for y in range(-2, 78)]
    zs = [[E.zg(u, v) for u in us] for v in vs]
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
            if len(pts) == 2 and E.PARCEL.contains(Point(pts[0])):
                segs.append(pts)
    return segs


def meets_ground(lev: float, v: float) -> float | None:
    """u where the natural ground equals `lev` along the line v = const."""
    prev = None
    for k in range(-100, 330):
        u = k * 0.1
        z = E.zg(u, v)
        if z is None:
            continue
        if prev and (prev[1] - lev) * (z - lev) <= 0:
            return prev[0] + (u - prev[0]) * (prev[1] - lev) / (prev[1] - z)
        prev = (u, z)
    return None


def draw_site(opt: E.Option, gm: E.GroundModel, path_svg: Path, width: int = 2200, height: int = 1880) -> None:
    sheet = E.Sheet(1.0, (0, 0))
    zone = E.PARCEL.buffer(0.8)
    xs, ys = zip(*[sheet.xy(u, v) for u, v in zone.exterior.coords])
    sheet.s = min((width - 420) / (max(xs) - min(xs)), (height - 170) / (max(ys) - min(ys)), 52.0)
    sheet.ox = 150 + (width - 500 - (max(xs) - min(xs)) * sheet.s) / 2 - min(xs) * sheet.s
    sheet.oy = 100 + (height - 150 - (max(ys) - min(ys)) * sheet.s) / 2 - min(ys) * sheet.s
    sheet.raw(f'<rect class="bg" x="0" y="0" width="{width}" height="{height}"/>')
    sheet.path(E.ROAD, "road")
    rx, ry = sheet.xy(-6.6, 7.0)
    sheet.text(rx, ry, "ROAD ≈ 1677.4", "tlbl")
    # height colours, 0.5 m cells clipped to the parcel
    step = 0.5
    u0, v0, u1, v1 = E.PARCEL.bounds
    for i in range(math.floor(u0 / step), math.ceil(u1 / step)):
        for j in range(math.floor(v0 / step), math.ceil(v1 / step)):
            cell = box(i * step, j * step, (i + 1) * step, (j + 1) * step).intersection(E.PARCEL)
            if cell.is_empty or cell.area < 1e-4:
                continue
            c = cell.centroid
            sheet.path(cell, "cell", f'fill="{colour(E.zg_safe(c.x, c.y))}" fill-opacity=".8"')
    E.contours(sheet)
    sheet.path(E.PARCEL, "parcel")
    sheet.path(E.ENVELOPE, "env")
    # garden and outdoor platforms
    for lv in opt.levels.values():
        for t in lv.terraces:
            if t.kind in ("lawn", "bank"):
                sheet.path(t.geom, "gline", 'style="fill:#fff;fill-opacity:.28"' if t.kind == "lawn" else 'stroke-dasharray="5 4"')
                if t.kind == "bank":
                    for k, p in enumerate(E.tree_spots(t.geom)):
                        sheet.path(Point(p).buffer(1.05 if k % 2 else 1.25), "tree")
            elif t.kind in ("paved", "court", "terrace", "stair", "landing", "deck"):
                sheet.path(t.geom, "pav")
    # the three floors
    for key in ("lower", "main", "road"):
        lv = opt.levels[key]
        sheet.path(lv.footprint, "fp", f'stroke="{LEVEL_INK[key]}"')
    # where each floor level meets the natural ground
    for key in ("main", "lower"):
        lv = opt.levels[key]
        for seg in level_line(lv.z):
            sheet.path(LineString(seg), "day", f'stroke="{LEVEL_INK[key]}"')
    # section lines
    letters = iter("ABCDEFGH")
    for (v, _), (u, _) in zip(opt.sections["ew"], opt.sections["ns"]):
        for axis, c in (("u", v), ("v", u)):
            st = E.boundary_stations(axis, c)
            a, b = ((st[0] - 0.9, c), (st[-1] + 0.9, c)) if axis == "u" else ((c, st[0] - 0.9), (c, st[-1] + 0.9))
            sheet.path(LineString([a, b]), "sec")
            letter = next(letters)
            for p in (a, b):
                x, y = sheet.xy(*p)
                sheet.raw(f'<circle class="bub" cx="{x:.1f}" cy="{y:.1f}" r="11"/>')
                sheet.text(x, y + 4.5, letter, "bubt")

    def spot(u, v, text, dx=0, dy=0):
        x, y = sheet.xy(u, v)
        x, y = x + dx, y + dy
        w = len(text) * 7.2 + 10
        sheet.raw(f'<rect class="spotbg" x="{x - w / 2:.1f}" y="{y - 13:.1f}" width="{w:.1f}" height="18" rx="3"/>')
        sheet.text(x, y, text, "spot")

    ring = list(E.PARCEL.exterior.coords)
    for name, (u, v), (dx, dy) in zip(("NW", "SW", "SE", "NE"), ring[:4], ((-10, -18), (-30, 26), (40, 26), (0, -20))):
        spot(u, v, f"{name} {E.zg_safe(u, v):.1f}", dx, dy)
    # the two falls
    za, zb = E.zg_safe(-0.5, 2.0), E.zg_safe(29.5, 2.0)
    a, b = sheet.xy(2.0, -2.6), sheet.xy(28.0, -2.6)
    sheet.raw(f'<line class="arrow2" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
    m = sheet.xy(15.0, -3.4)
    ang = -math.degrees(E.ROT)
    sheet.raw(f'<text class="spot" x="{m[0]:.1f}" y="{m[1]:.1f}" text-anchor="middle" transform="rotate({ang:.1f} {m[0]:.1f} {m[1]:.1f})">'
              f'MAIN SLOPE · falls {za - zb:.1f} m to the east ({100 * (za - zb) / 30:.0f}%)</text>')
    za, zb = E.zg_safe(12.0, 0.4), E.zg_safe(12.0, 18.0)
    a, b = sheet.xy(33.4, 1.0), sheet.xy(25.4, 15.6)
    sheet.raw(f'<line class="arrow2" x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}"/>')
    m = sheet.xy(30.3, 8.6)
    ang2 = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    sheet.raw(f'<text class="spot" x="{m[0]:.1f}" y="{m[1]:.1f}" text-anchor="middle" transform="rotate({ang2:.1f} {m[0]:.1f} {m[1]:.1f})">'
              f'CROSS SLOPE · falls {za - zb:.1f} m to the south ({100 * (za - zb) / 17.6:.0f}%)</text>')
    # floor names
    for key, (u, v) in (("road", (3.4, 5.3)), ("main", (15.2, 9.6)), ("lower", (11.2, 14.9))):
        lv = opt.levels[key]
        x, y = sheet.xy(u, v)
        t = f"{lv.title.replace(' + GARDEN', '')} · {lv.z:.2f}"
        w = len(t) * 7.4 + 12
        sheet.raw(f'<rect x="{x - w / 2:.1f}" y="{y - 14:.1f}" width="{w:.1f}" height="20" rx="3" fill="{LEVEL_INK[key]}"/>')
        sheet.raw(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" style="font:700 12px Helvetica,Arial,sans-serif;fill:#fff">{escape(t)}</text>')
    for name, (u, v) in (("PLAY LAWN 1667.60", (24.0, 12.5)), ("TREE BANK", (27.9, 5.9)), ("TERRACE 1669.98", (19.3, 8.0)),
                         ("ARRIVAL COURT 1673.60", (-1.6, 14.0)), ("FORECOURT 1677.47", (-2.6, 5.0)), ("ROAD STAIR", (-8.2, 13.2))):
        x, y = sheet.xy(u, v)
        sheet.text(x, y, name, "tlbl")
    E.north_marks(sheet, opt.levels["lower"])
    # header, north arrow, scale bar, key
    sheet.text(40, 50, f"{opt.code} · The house on the field", "h1", "start")
    sheet.text(40, 74, "Colours = natural ground height from the survey. Outlines = the three floors, each further east than the one above.", "h2", "start")
    nx, ny = width - 300, 70
    sheet.raw(f'<line x1="{nx}" y1="{ny + 50}" x2="{nx}" y2="{ny}" stroke="#1d2f3a" stroke-width="2" marker-end="url(#ar)"/>')
    sheet.text(nx, ny + 68, "N", "lbl")
    x0, y0 = 60, height - 70
    sheet.raw(f'<line x1="{x0}" y1="{y0}" x2="{x0 + 5 * sheet.s}" y2="{y0}" stroke="#1d2f3a" stroke-width="3"/>')
    for k in range(6):
        sheet.raw(f'<line x1="{x0 + k * sheet.s}" y1="{y0 - 5}" x2="{x0 + k * sheet.s}" y2="{y0 + 5}" stroke="#1d2f3a" stroke-width="1"/>')
    sheet.text(x0, y0 + 18, "0", "dim")
    sheet.text(x0 + 5 * sheet.s, y0 + 18, "5 m", "dim")
    kx, ky = width - 640, 1290
    sheet.text(kx, ky, "HOW TO READ THIS", "noteb", "start")
    ky += 26
    top = ky
    for z in range(1678, 1664, -2):
        sheet.raw(f'<rect x="{kx}" y="{ky - 12}" width="26" height="16" fill="{colour(z)}" fill-opacity=".8"/>')
        sheet.text(kx + 36, ky + 1, f"{z} m" + (" · road" if z == 1678 else " · lowest corner" if z == 1666 else ""), "key", "start")
        ky += 20
    fy = top
    for key in ("road", "main", "lower"):
        lv = opt.levels[key]
        sheet.raw(f'<rect x="{kx + 230}" y="{fy - 12}" width="26" height="16" fill="#fff" stroke="{LEVEL_INK[key]}" stroke-width="3"/>')
        sheet.text(kx + 266, fy + 1, f"{lv.title.replace(' + GARDEN', '').title()}, floor at {lv.z:.2f}", "key", "start")
        fy += 22
    sheet.raw(f'<line class="sec" x1="{kx + 230}" y1="{fy + 6}" x2="{kx + 256}" y2="{fy + 6}"/>')
    sheet.text(kx + 266, fy + 10, "A–A to D–D: the four section cuts", "key", "start")
    ky += 14
    mn, ms = meets_ground(opt.levels["lower"].z, 2.8), meets_ground(opt.levels["lower"].z, 16.4)
    notes = [
        ("Dashed coloured lines", "show where the natural ground is exactly at the main-floor level (blue) and the lower-floor level (brown). "
         "West of a line that floor is under ground; east of it the floor is in the open air."),
        ("They run diagonally", f"because the field also falls to the south. The lower-floor line is {mn:.1f} m from the west on the north side "
         f"but only {ms:.1f} m on the south side. So the south and east sides of the lower floor are open, and its north-west is buried."),
        ("That decides the plan.", "Bedrooms, lounge and terraces sit east and south of the lines. Stair, bathrooms, laundry and stores sit west of them."),
    ]
    for head, body in notes:
        sheet.text(kx, ky, head, "keyb", "start")
        ky += 17
        for line in E.wrap(body, 84):
            sheet.text(kx, ky, line, "key", "start")
            ky += 16
        ky += 9
    defs = E.DEFS.replace("</defs>", '<marker id="ar2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">'
                                     '<path d="M0,0 L10,5 L0,10 z" fill="#111"/></marker></defs>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
           f'<style>{E.CSS}{CSS}</style>{defs}' + "".join(sheet.parts) + "</svg>")
    path_svg.write_text(svg)
