"""Render C04 floor plans in the house frame (u = field east to the right, field north up).

Reads <option>/plan.json (canonical model) and draws every level at one scale with
rooms, areas, walls, doors, windows, the family stair, terraces and the parcel.
Writes <option>/floor-plans.svg and .png.

Run: .venv/bin/python projects/my-house/design/995_2026-10-22_claude-c04/render.py claude-c04-a
"""

import html
import math
import subprocess
import sys
from pathlib import Path

from shapely.geometry import Polygon

from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceFunction as F

from generate import EAST, NW, SOUTH, site

HERE = Path(__file__).resolve().parent
OY = 110
S = 34  # px per metre
PAD = 40
U0, U1, V0, V1 = -4.0, 33.5, -1.0, 19.0  # drawing window in metres (frame)
PANEL_W, PANEL_H = (U1 - U0) * S, (V1 - V0) * S
FILL = {F.LIVING: "#e3efd9", F.DINING: "#e8f0dc", F.KITCHEN: "#f3e3c3", F.PANTRY: "#efe3cc",
        F.BEDROOM: "#efdcc9", F.FAMILY: "#e3efd9", F.STUDY: "#e0e4f0", F.BATHROOM: "#d5e6ee",
        F.WC: "#d5e6ee", F.ENTRY: "#ecebe4", F.HALL: "#f1f0ea", F.STAIR: "#d9dcdc", F.LIFT: "#b9c4c6",
        F.GARAGE: "#dddedd", F.STORAGE: "#ecebe4", F.LAUNDRY: "#d5e6ee", F.MECHANICAL: "#dddedd",
        F.TERRACE: "#cfe3c0"}
TITLES = {"lv-upper": "Road level  +1677.7", "lv-entry": "Upper residential  +1674.3",
          "lv-lower": "Lower residential  +1670.7"}


def design(xy):
    dx, dy = xy[0] - NW[0], xy[1] - NW[1]
    return dx * EAST[0] + dy * EAST[1], dx * SOUTH[0] + dy * SOUTH[1]


def px(u, v, ox, oy=None):
    return ox + (u - U0) * S, (OY if oy is None else oy) + (v - V0) * S


def poly(points, ox, **attrs):
    pts = " ".join(f"{px(u, v, ox)[0]:.1f},{px(u, v, ox)[1]:.1f}" for u, v in points)
    a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{pts}" {a}/>'


def text(x, y, s, size=11, weight="normal", anchor="middle", fill="#1f2a2e"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{fill}">{html.escape(s)}</text>')


def panel(model, level_id, ox):
    out = [text(ox + 10, OY - 12, TITLES[level_id], 18, "bold", "start")]
    parcel = [design(p) for p in site.boundary.outer]
    out.append(poly(parcel, ox, fill="none", stroke="#9aa", stroke_width=1.2, stroke_dasharray="6 4"))
    spaces = [s for s in model.spaces if s.level_id == level_id]
    for s in sorted(spaces, key=lambda s: s.function is not F.TERRACE):
        pts = [design(p) for p in s.boundary.outer]
        out.append(poly(pts, ox, fill=FILL.get(s.function, "#eee"), stroke="none"))
    for w in model.walls:
        if w.level_id != level_id:
            continue
        (a, b), (c, d) = design(w.start), design(w.end)
        x0, y0 = px(a, b, ox)
        x1, y1 = px(c, d, ox)
        width = max(1.5, w.thickness_m * S) if w.kind.value != "parapet" else 1.5
        color = "#2f4a48" if w.kind.value != "parapet" else "#7a9a6a"
        out.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{color}" '
                   f'stroke-width="{width:.1f}" stroke-linecap="square"/>')
    walls = {w.id: w for w in model.walls}
    for o in model.openings:
        w = walls[o.host_wall_id]
        if w.level_id != level_id:
            continue
        (a, b), (c, d) = design(w.start), design(w.end)
        length = math.hypot(c - a, d - b)
        t0, t1 = o.offset_m / length, (o.offset_m + o.width_m) / length
        p0 = px(a + (c - a) * t0, b + (d - b) * t0, ox)
        p1 = px(a + (c - a) * t1, b + (d - b) * t1, ox)
        kind = o.kind.value
        if kind == "window":
            out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                       f'stroke="#ffffff" stroke-width="6"/>')
            out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                       f'stroke="#3b7ea1" stroke-width="2.5"/>')
        else:
            out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                       f'stroke="#ffffff" stroke-width="8"/>')
            if kind == "door":
                out.append(f'<line x1="{p0[0]:.1f}" y1="{p0[1]:.1f}" x2="{p1[0]:.1f}" y2="{p1[1]:.1f}" '
                           f'stroke="#b5651d" stroke-width="2"/>')
    for st in model.stairs:
        if level_id not in (st.from_level_id, st.to_level_id):
            continue
        out.append(poly([design(p) for p in st.footprint.outer], ox, fill="#c8cccc", stroke="#555",
                        stroke_width=1))
        line = [px(*design(p), ox) for p in st.walking_line]
        out.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in line) +
                   '" fill="none" stroke="#333" stroke-width="1.5" marker-end="url(#ar)"/>')
    for s in spaces:
        g = Polygon([design(p) for p in s.boundary.outer])
        c = g.representative_point()
        x, y = px(c.x, c.y, ox)
        minx, miny, maxx, maxy = g.bounds
        dims = f"{maxx - minx:.1f} × {maxy - miny:.1f}" if abs(g.area - (maxx - minx) * (maxy - miny)) < .05 \
            else "L-shaped"
        size = 10 if g.area > 6 else 8
        out.append(text(x, y - 4, s.name, size, "bold"))
        if s.function is F.LIFT:
            out.append(poly([(minx, miny), (maxx, maxy), (maxx, miny), (minx, maxy)], ox, fill="none",
                            stroke="#666", stroke_width=1))
        out.append(text(x, y + 9, f"{g.area:.1f} m²" + (f"  {dims}" if g.area > 4 else ""), 9))
    # compass and scale
    nx, ny = -SOUTH[0], SOUTH[1]  # true north (local +y) in the drawing (u right, v down)
    north = (0 * EAST[0] + 1 * EAST[1], -(0 * SOUTH[0] + 1 * SOUTH[1]))
    cx, cy = ox + PANEL_W - 50, OY + 30
    out.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + 22 * north[0]:.1f}" y2="{cy - 22 * north[1]:.1f}" '
               f'stroke="#b33" stroke-width="2.5" marker-end="url(#ar)"/>')
    out.append(text(cx + 30 * north[0], cy - 30 * north[1] - 2, "N", 12, "bold", fill="#b33"))
    sx, sy = ox + 20, OY + PANEL_H - 10
    out.append(f'<line x1="{sx}" y1="{sy}" x2="{sx + 5 * S}" y2="{sy}" stroke="#333" stroke-width="3"/>')
    out.append(text(sx + 2.5 * S, sy + 16, "5 m", 11))
    del nx, ny
    return "\n".join(out)


def main():
    option = sys.argv[1] if len(sys.argv) > 1 else "claude-c04-a"
    folder = HERE / option
    plan = PlanVersion.model_validate_json((folder / "plan.json").read_text())
    model = plan.model
    order = ["lv-upper", "lv-entry", "lv-lower"]
    global OY
    width = PAD * 2 + PANEL_W
    height = 90 + (PANEL_H + 50) * len(order) + 40
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
             f'font-family="Helvetica, Arial, sans-serif">',
             '<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">'
             '<path d="M0,0 L8,4 L0,8 z" fill="#333"/></marker></defs>',
             f'<rect width="100%" height="100%" fill="#f7f4ee"/>',
             text(PAD, 28, f"{plan.label} | floor plans | EXPLORATORY | 22 Oct 2026", 20, "bold", "start"),
             text(PAD, 48, "Field east (downhill, view) to the right; field north (boundary) at the top.", 13,
                  anchor="start"),
             text(PAD, 66, "Dashed: parcel. Blue: windows. Brown: doors. White gaps: open passages.", 13,
                  anchor="start")]
    for i, lv in enumerate(order):
        OY = 110 + i * (PANEL_H + 50)
        parts.append(panel(model, lv, PAD))
    parts.append(text(PAD, height - 26, "Room geometry: CP-SAT exact tiling per floor (no unassigned area); "
                      "lift + family stair placed by design.", 12, anchor="start"))
    parts.append(text(PAD, height - 10, "Not reviewed by an architect or engineer; structure, retaining walls, "
                      "drainage and codes unresolved.", 12, anchor="start"))
    parts.append("</svg>")
    svg = folder / "floor-plans.svg"
    svg.write_text("\n".join(parts))
    subprocess.run(["rsvg-convert", "-o", str(folder / "floor-plans.png"), str(svg)], check=True)
    print("wrote", svg)


if __name__ == "__main__":
    main()
