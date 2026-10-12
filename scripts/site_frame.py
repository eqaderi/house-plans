"""The site in the spec frame: origin at plot corner V3, x along the south
boundary towards V2, y square to it into the plot (docs/decisions.md,
2026-10-13 "spec frame").

Read-only on the survey. Prints the plot, the road edges, the 1 m alley strip
and every height point in spec millimetres, and project.north_angle_deg.
The transform itself is houseplan.site.SurveyFrame.

Run:  PYTHONPATH=src ~/.venvs/architecture-ai/bin/python scripts/site_frame.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import ezdxf
from shapely.geometry import Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_site import EPSG, HP, SEP, points, poly  # noqa: E402

from houseplan.site import SurveyFrame, grid_north_true_azimuth  # noqa: E402

STRIP_MM = 1000  # owner: no building within 1 m of the south boundary, measured square to it


def site_in_spec():
    sep, hp = ezdxf.readfile(SEP), ezdxf.readfile(HP)
    ring = poly(sep, "D7")[:-1]  # V0 NW, V1 NE, V2 SE, V3 SW
    frame = SurveyFrame.along(ring[3], ring[2])
    centroid = Polygon(ring).centroid
    conv = grid_north_true_azimuth(centroid.x, centroid.y, EPSG)

    def mm(e, n):
        x, y = frame.to_spec(e, n)
        return round(x), round(y)

    boundary = [mm(*ring[i]) for i in (3, 2, 1, 0)]  # counter-clockwise from the origin
    plot = Polygon(boundary)
    minx, _, maxx, _ = plot.bounds
    strip = plot.intersection(box(minx, 0, maxx, STRIP_MM))
    strip_ring = [(round(x), round(y)) for x, y in strip.exterior.coords[:-1]]
    roads = {"road west edge (BC)": [mm(*p) for p in poly(sep, "BC")], "road east edge = plot west boundary (C5)": [mm(*p) for p in poly(sep, "C5")]}
    heights = [(name, mm(x, y), round(z * 1000)) for name, x, y, z, _ in points(hp)]
    return frame, conv, boundary, strip_ring, roads, heights


def main():
    frame, conv, boundary, strip, roads, heights = site_in_spec()
    print(f"frame          origin V3 E {frame.origin_e:.3f} N {frame.origin_n:.3f}; +x grid azimuth {frame.x_azimuth_deg:.4f} deg")
    print(f"grid north     true azimuth {conv:.4f} deg (EPSG:{EPSG}, at the plot centroid)")
    print(f"north_angle_deg  {frame.north_angle_deg(conv):.2f}   (true bearing of spec +y)")
    print("\nplot boundary (spec mm, counter-clockwise from V3)")
    for name, p in zip(("V3 SW", "V2 SE", "V1 NE", "V0 NW"), boundary):
        print(f"  {name}  {p}")
    print(f"  area {Polygon(boundary).area / 1e6:.3f} m2")
    print(f"\nalley strip, {STRIP_MM} mm square to the south boundary, inside the plot")
    print(f"  {strip}   area {Polygon(strip).area / 1e6:.3f} m2")
    for name, pts in roads.items():
        print(f"\n{name}")
        for p in pts:
            print(f"  {p}")
    print("\nheight points (height-points.dxf), spec mm, survey Z mm")
    for name, p, z in heights:
        print(f"  {name:10} {str(p):18} Z {z}")


if __name__ == "__main__":
    main()
