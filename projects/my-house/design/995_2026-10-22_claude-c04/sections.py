"""EXPLORATORY C04 site sections and earthwork (agent:claude-code, 2026-10-22).

Cuts the stored survey TIN along the north edge, the south edge of the lower
floor and across the house, and draws the C04 floor plates, terraces and lawn.
Quantities use the canonical geospatial.earthworks.integrate (inferred on the
TIN; 0.35 m formation below floors; not contractor quantities).

Run: .venv/bin/python projects/my-house/design/995_2026-10-22_claude-c04/sections.py
"""

import json
import subprocess
from pathlib import Path

from shapely.geometry import Polygon

from house_ai.geospatial.earthworks import integrate

from section_study import ENVELOPE, FORMATION, PARCEL, rect, site, surface, xy

HERE = Path(__file__).resolve().parent
ROAD_Z, UP_Z, LOW_Z, LAWN_Z = 1677.7, 1674.3, 1670.7, 1668.3
STOREY = {ROAD_Z: 3.0, UP_Z: 3.4, LOW_Z: 3.6}
# Plates in metres (u0, u1, v0, v1) in the frame of section_study.py.
# Matches generate.py PLATE/TERRACES (dm / 10). Road level spans u 1.0-10.0 (v < 8.6: to 10.0).
PLATES = [("Road: garage / lobby / office", ROAD_Z, 1.0, 10.0, 0.0, 12.4),
          ("Upper: living / kitchen / grand master", UP_Z, 1.0, 13.2, 0.0, 12.4),
          ("Lower: 3 bedrooms / family room", LOW_Z, 5.2, 15.0, 0.0, 15.6)]
TERRACES = [("West court (covered by road forecourt)", UP_Z, -2.0, 1.0, 4.0, 9.6),
            ("West court (open)", UP_Z, -5.2, 1.0, 9.6, 12.4),
            ("Road forecourt slab", ROAD_Z, -2.0, 1.0, 0.0, 9.6),
            ("Road-level roof deck", ROAD_Z, 10.0, 13.2, 0.0, 12.4),
            ("Upper south terrace", UP_Z, 1.0, 13.2, 12.4, 15.6),
            ("Upper east balcony (roof of lower)", UP_Z, 13.2, 15.0, 0.0, 15.6),
            ("Lower garden terrace", LOW_Z, 15.0, 18.0, 0.0, 15.6)]
LAWN_U0 = 18.0


def ground(u, v):
    from house_ai.domain.terrain import elevation_at
    try:
        return elevation_at(surface, xy(u, v))
    except Exception:
        return None


def quantities():
    regions = [("lower floor", rect(5.2, 15.0, 0, 15.6), LOW_Z - FORMATION),
               ("upper floor (part on ground)", rect(1.0, 5.2, 0, 12.4), UP_Z - FORMATION),
               ("west entrance court", rect(-2.0, 1.0, 4.0, 9.6).union(rect(-5.2, 1.0, 9.6, 12.4)),
                UP_Z - FORMATION)]
    out = {"building": []}
    cut = 0.0
    for name, poly, z in regions:
        r = integrate(surface, poly.intersection(PARCEL), z)
        cut += r.cut_m3 or 0
        out["building"].append({"region": name, "cut_m3": round(r.cut_m3 or 0, 1),
                                "max_cut_m": round(r.max_cut_m or 0, 2),
                                "max_gap_below_formation_m": round(r.max_below_m or 0, 2)})
    out["building_cut_m3"] = round(cut, 1)
    fills = [("upper south terrace platform (part on ground)", rect(1.0, 5.2, 12.4, 15.6), UP_Z),
             ("lower garden terrace", rect(15.0, 18.0, 0, 15.6), LOW_Z)]
    out["terraces"] = []
    for name, poly, z in fills:
        r = integrate(surface, poly.intersection(ENVELOPE), z)
        out["terraces"].append({"region": name, "fill_m3": round(r.below_plane_m3 or 0, 1),
                                "cut_m3": round(r.cut_m3 or 0, 1), "max_fill_m": round(r.max_below_m or 0, 2)})
    lawn = rect(LAWN_U0, 40, -1, 25).intersection(ENVELOPE)
    r = integrate(surface, lawn, LAWN_Z)
    out["lawn"] = {"level": LAWN_Z, "area_m2": round(lawn.area, 1), "cut_m3": round(r.cut_m3 or 0, 1),
                   "fill_m3": round(r.below_plane_m3 or 0, 1), "max_cut_m": round(r.max_cut_m or 0, 2),
                   "max_fill_m": round(r.max_below_m or 0, 2)}
    out["method"] = ("geospatial.earthworks.integrate on stored survey TIN; INFERRED; formation 0.35 m "
                     "below finished floors; excludes footings, working space, batters, bulking, drainage")
    return out


SCALE = 22  # px per metre, equal horizontal and vertical scale
Z0, Z1 = 1663.0, 1682.0


def section_svg(title, along, fixed, lo, hi, y0):
    """One section strip. along='u' cuts W->E at v=fixed; along='v' cuts N->S at u=fixed."""
    def X(s):
        return 60 + (s - lo) * SCALE

    def Y(z):
        return y0 + (Z1 - z) * SCALE

    parts = [f'<text x="60" y="{y0 - 8}" class="h">{title}</text>']
    pts = []
    s = lo
    while s <= hi + 1e-9:
        g = ground(s, fixed) if along == "u" else ground(fixed, s)
        if g is not None:
            pts.append((s, g))
        s += 0.25
    if pts:
        poly = [(X(pts[0][0]), Y(Z0))] + [(X(a), Y(b)) for a, b in pts] + [(X(pts[-1][0]), Y(Z0))]
        parts.append('<polygon class="earth" points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in poly) + '"/>')
        parts.append('<polyline class="ground" points="' + " ".join(f"{X(a):.1f},{Y(b):.1f}" for a, b in pts) + '"/>')

    def span(item):
        _, z, u0, u1, v0, v1 = item
        if along == "u":
            return (u0, u1) if v0 <= fixed <= v1 else None
        return (v0, v1) if u0 <= fixed <= u1 else None

    for item in PLATES:
        sp = span(item)
        if not sp:
            continue
        z = item[1]
        a, b = sp
        h = STOREY[z]
        parts.append(f'<rect class="room" x="{X(a):.1f}" y="{Y(z + h):.1f}" width="{(b - a) * SCALE:.1f}" '
                     f'height="{h * SCALE:.1f}"/>')
        parts.append(f'<rect class="slab" x="{X(a):.1f}" y="{Y(z):.1f}" width="{(b - a) * SCALE:.1f}" height="6"/>')
        parts.append(f'<text x="{X(a) + 6:.1f}" y="{Y(z + h / 2) + 4:.1f}" class="t">{item[0]}</text>')
        parts.append(f'<text x="{X(b) + 4:.1f}" y="{Y(z) + 4:.1f}" class="lv">{z:.1f}</text>')
        # Cut depth at the uphill end of each plate.
        for e in (a, b):
            g = ground(e, fixed) if along == "u" else ground(fixed, e)
            if g is not None and g > z - FORMATION + 0.3:
                parts.append(f'<line class="cut" x1="{X(e):.1f}" y1="{Y(g):.1f}" x2="{X(e):.1f}" y2="{Y(z - FORMATION):.1f}"/>')
                parts.append(f'<text x="{X(e) + 3:.1f}" y="{Y((g + z) / 2):.1f}" class="cutt">cut {g - z + FORMATION:.1f} m</text>')
    for item in TERRACES:
        sp = span(item)
        if not sp:
            continue
        a, b = sp
        parts.append(f'<rect class="terr" x="{X(a):.1f}" y="{Y(item[1]):.1f}" width="{(b - a) * SCALE:.1f}" height="5"/>')
    lawn_hi = hi
    if along == "u":
        parts.append(f'<line class="lawn" x1="{X(LAWN_U0):.1f}" y1="{Y(LAWN_Z):.1f}" x2="{X(lawn_hi):.1f}" y2="{Y(LAWN_Z):.1f}"/>')
        parts.append(f'<text x="{X(LAWN_U0) + 6:.1f}" y="{Y(LAWN_Z) - 6:.1f}" class="t">flat lawn {LAWN_Z:.1f} '
                     f'(stair 2.4 m down from lower terrace)</text>')
        for e in (LAWN_U0, lawn_hi):
            g = ground(e, fixed)
            if g is not None:
                parts.append(f'<line class="wall" x1="{X(e):.1f}" y1="{Y(max(g, LAWN_Z)):.1f}" x2="{X(e):.1f}" '
                             f'y2="{Y(min(g, LAWN_Z)):.1f}"/>')
                parts.append(f'<text x="{X(e) - 70:.1f}" y="{Y(min(g, LAWN_Z)) + 14:.1f}" class="cutt">'
                             f'wall {abs(g - LAWN_Z):.1f} m</text>')
    for m in range(int(lo), int(hi) + 1, 5):
        parts.append(f'<text x="{X(m):.1f}" y="{Y(Z0) + 14:.1f}" class="ax">{m} m</text>')
    return "\n".join(parts)


def main():
    q = quantities()
    (HERE / "earthwork.json").write_text(json.dumps(q, indent=1))
    w, h = 60 + 36 * SCALE + 380, 3 * (Z1 - Z0) * SCALE + 260
    css = ("text{font-family:Helvetica,Arial,sans-serif;fill:#1f2a2e}.h{font-size:17px;font-weight:600}"
           ".t{font-size:11px}.lv{font-size:11px;fill:#555}.ax{font-size:10px;fill:#777}.cutt{font-size:10px;fill:#b44}"
           ".earth{fill:#e6d8bd}.ground{fill:none;stroke:#5d6b3a;stroke-width:2}.room{fill:#dfe9e4;stroke:#2f4a48;"
           "stroke-width:1.5}.slab{fill:#2f4a48}.terr{fill:#b08a2e}.lawn{stroke:#4f8a3a;stroke-width:5}"
           ".cut{stroke:#c44;stroke-width:3}.wall{stroke:#7a3b2e;stroke-width:4}")
    body = [section_svg("A-A  north edge (v = 0.5 m), west/road -> east/downhill", "u", 0.5, -1, 33, 60),
            section_svg("B-B  south side (v = 15.2 m), west -> east", "u", 15.2, -9, 26, 60 + (Z1 - Z0) * SCALE + 70),
            section_svg("C-C  across the house at u = 9 m, north -> south", "v", 9.0, -0.5, 18.4,
                        60 + 2 * ((Z1 - Z0) * SCALE + 70))]
    b = q["building"]
    notes = [f"Building cut (TIN, inferred): {q['building_cut_m3']} m3",
             f"  lower floor: {b[0]['cut_m3']} m3, deepest {b[0]['max_cut_m']} m",
             f"  upper floor on ground: {b[1]['cut_m3']} m3, deepest {b[1]['max_cut_m']} m",
             f"  west court: {b[2]['cut_m3']} m3, deepest {b[2]['max_cut_m']} m",
             f"Lawn {q['lawn']['level']}: {q['lawn']['area_m2']} m2 flat",
             f"  fill {q['lawn']['fill_m3']} m3 (max {q['lawn']['max_fill_m']} m)",
             f"  cut {q['lawn']['cut_m3']} m3 (max {q['lawn']['max_cut_m']} m)",
             *[f"{t['region']}: fill {t['fill_m3']} m3" for t in q["terraces"]],
             "", "Dug soil is reused for lawn fill.", "EXPLORATORY: no structural, geotechnical,",
             "drainage or code approval. Equal H/V scale."]
    tx = 60 + 36 * SCALE + 20
    body.append("\n".join(f'<text x="{tx}" y="{90 + i * 18}" class="t">{n}</text>' for i, n in enumerate(notes)))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'<style>{css}</style><rect width="100%" height="100%" fill="#f7f4ee"/>'
           f'<text x="60" y="30" class="h">Claude C04-A | ground, digging and stepped floors | 22 Oct 2026</text>'
           + "\n".join(body) + "</svg>")
    (HERE / "terrain-sections.svg").write_text(svg)
    subprocess.run(["rsvg-convert", "-o", str(HERE / "terrain-sections.png"), str(HERE / "terrain-sections.svg")],
                   check=True)
    print(json.dumps(q, indent=1))


if __name__ == "__main__":
    main()
