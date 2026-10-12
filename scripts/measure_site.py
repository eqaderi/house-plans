"""Phase 1 site measurements from the two survey DXFs (derived/survey/).

Read-only. Prints every number the site report quotes, so none is computed by
hand. Entities are identified by handle because everything is on layer 0:
  seperated.dxf     BC = road west edge, C5 = road east edge, D7 = plot outline
  height-points.dxf POINT entities with MTEXT labels, incl. the benchmark

Run:  ~/.venvs/architecture-ai/bin/python scripts/measure_site.py
"""

from __future__ import annotations

import math
from pathlib import Path

import ezdxf
from pyproj import CRS, Geod, Proj, Transformer
from shapely.geometry import LineString, Point, Polygon

ROOT = Path(__file__).resolve().parent.parent
SEP = ROOT / "derived/survey/seperated.dxf"
HP = ROOT / "derived/survey/height-points.dxf"
EPSG = 32638  # UTM 38N, to be confirmed by the surveyor
KAABA = (39.826206, 21.422487)  # lon, lat
GEOD = Geod(ellps="WGS84")


def points(doc):
    msp = doc.modelspace()
    labels = {tuple(round(c, 3) for c in t.dxf.insert): t.plain_text() for t in msp.query("MTEXT")}
    out = []
    for p in msp.query("POINT"):
        loc = p.dxf.location
        label = labels.get(tuple(round(c, 3) for c in loc), "?")
        out.append((label.split("\n")[0], loc.x, loc.y, loc.z, label))
    return out


def poly(doc, handle):
    return [(x, y) for x, y, *_ in doc.entitydb[handle].get_points()]


def grid_az(a, b):
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360


def main():
    sep, hp = ezdxf.readfile(SEP), ezdxf.readfile(HP)
    road_w, road_e = LineString(poly(sep, "BC")), LineString(poly(sep, "C5"))
    ring = poly(sep, "D7")[:-1]
    plot = Polygon(ring)

    to_geo = Transformer.from_crs(EPSG, 4326, always_xy=True)
    c = plot.centroid
    lon, lat = to_geo.transform(c.x, c.y)
    conv = Proj(CRS.from_epsg(EPSG)).get_factors(lon, lat).meridian_convergence
    lon_n, lat_n = to_geo.transform(c.x, c.y + 100)
    true_az_of_grid_north = GEOD.inv(lon, lat, lon_n, lat_n)[0] % 360
    qibla_true = GEOD.inv(lon, lat, *KAABA)[0] % 360
    print(f"CRS assumed           EPSG:{EPSG} (UTM 38N, WGS84)")
    print(f"plot centroid         E {c.x:.3f}  N {c.y:.3f}  ->  lat {lat:.6f}  lon {lon:.6f}")
    print(f"grid north            true azimuth {true_az_of_grid_north:.3f} deg (pyproj convergence {conv:.3f} deg)")
    print(f"qibla                 true azimuth {qibla_true:.2f} deg, grid azimuth {(qibla_true - true_az_of_grid_north) % 360:.2f} deg")

    print("\nroad (BC west edge, C5 east edge): perpendicular width at each vertex")
    for name, line, other in (("BC", road_w, road_e), ("C5", road_e, road_w)):
        for x, y in line.coords:
            print(f"  {name} vertex ({x:.3f}, {y:.3f})  distance to other edge {other.distance(Point(x, y)):.3f} m")

    print("\nplot D7: vertices, distance to road east edge C5")
    for i, (x, y) in enumerate(ring):
        print(f"  V{i} ({x:.3f}, {y:.3f})  to C5 {road_e.distance(Point(x, y)):.3f} m")
    print(f"  area {plot.area:.3f} m2   perimeter {plot.length:.3f} m")

    print("\nplot D7 sides (grid azimuth from grid north, clockwise)")
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        az = grid_az(a, b)
        # outward normal: left of travel on a clockwise ring, right on a ccw one
        out_az = (az + (90 if plot.exterior.is_ccw else -90)) % 360
        print(f"  V{i}->V{(i + 1) % n}  length {math.dist(a, b):.3f} m  azimuth {az:.2f}  faces (outward) grid {out_az:.2f} / true {(out_az + true_az_of_grid_north) % 360:.2f}  mid ({mid[0]:.2f}, {mid[1]:.2f})")
    print("\nplot D7 perpendicular distance between opposite sides")
    for i in range(2):
        (ax, ay), (bx, by), (px, py) = ring[i], ring[i + 1], ring[i + 2]
        d = abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) / math.dist(ring[i], ring[i + 1])  # point to infinite line
        print(f"  V{i}->V{i + 1} to V{i + 2}->V{(i + 3) % n}  {d:.3f} m")
    print("\nplot D7 interior angles")
    for i in range(n):
        p, q, r = ring[i - 1], ring[i], ring[(i + 1) % n]
        a1 = math.atan2(p[1] - q[1], p[0] - q[0])
        a2 = math.atan2(r[1] - q[1], r[0] - q[0])
        print(f"  V{i}  {math.degrees(abs(a1 - a2)) % 360 if abs(a1 - a2) <= math.pi else 360 - math.degrees(abs(a1 - a2)):.2f} deg")

    print("\nheight points (label check, distance to plot boundary; inside = +)")
    for fname, doc in (("height-points", hp), ("seperated", sep)):
        for name, x, y, z, label in points(doc):
            d = plot.exterior.distance(Point(x, y)) * (1 if plot.contains(Point(x, y)) else -1)
            text_z = label.split("\n")[1] if "\n" in label else "-"
            ok = "" if text_z == "-" or abs(float(text_z) - z) < 0.0005 else "  LABEL != Z"
            print(f"  {fname:13} {name:10} ({x:.3f}, {y:.3f})  Z {z:.3f}  label {text_z:>9}  to boundary {d:+.3f} m{ok}")

    print("\nnearest point pairs across the two files (< 2 m)")
    a, b = points(hp), points(sep)
    for pa in a:
        for pb in b:
            dist = math.dist(pa[1:3], pb[1:3])
            if dist < 2:
                print(f"  hp {pa[0]} / sep {pb[0]}  plan distance {dist:.3f} m  dZ (sep - hp) {pb[3] - pa[3]:+.3f} m")

    print("\nslope along plot sides, using the height point nearest each corner (height-points.dxf)")
    hpp = points(hp)
    corner_z = []
    for i, v in enumerate(ring):
        best = min(hpp, key=lambda p: math.dist(p[1:3], v))
        corner_z.append(best[3])
        print(f"  V{i} nearest {best[0]} at {math.dist(best[1:3], v):.3f} m  Z {best[3]:.3f}")
    for i in range(n):
        j = (i + 1) % n
        drop = corner_z[i] - corner_z[j]
        print(f"  V{i}->V{j}  drop (Z start - Z end) {drop:+.3f} m over {math.dist(ring[i], ring[j]):.3f} m  = {100 * drop / math.dist(ring[i], ring[j]):.1f} %")

    print("\n1 m strip along the plot side facing south (owner: alley), if it lies inside D7")
    south = min(range(n), key=lambda i: (ring[i][1] + ring[(i + 1) % n][1]))
    a, b = ring[south], ring[(south + 1) % n]
    # band within 1 m (perpendicular) of the side's full line, so the skewed ends are not cut off
    ux, uy = (b[0] - a[0]) / math.dist(a, b), (b[1] - a[1]) / math.dist(a, b)
    line = LineString([(a[0] - 100 * ux, a[1] - 100 * uy), (b[0] + 100 * ux, b[1] + 100 * uy)])
    strip = plot.intersection(line.buffer(1.0, cap_style=2))
    print(f"  side V{south}->V{(south + 1) % n}  strip area {strip.area:.3f} m2  remaining {plot.area - strip.area:.3f} m2")


if __name__ == "__main__":
    main()
