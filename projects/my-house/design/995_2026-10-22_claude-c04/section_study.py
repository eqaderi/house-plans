"""EXPLORATORY C04 section study (agent:claude-code, 2026-10-22).

Places three straight floor plates (road / upper / lower) and a bottom-east lawn
on the stored survey TIN, in a frame aligned with the long N/S boundaries as the
owner asked. Quantities use the canonical `geospatial.earthworks.integrate`, so
they are inferred on the TIN, not contractor quantities. Owner direction: dig the
north side (~3 m accepted), straight floors, short outdoor stair to the lawn,
house may touch the north boundary.

Run: .venv/bin/python projects/my-house/design/995_2026-10-22_claude-c04/section_study.py
"""

import itertools
import json
import math
from pathlib import Path

from shapely.geometry import Polygon

from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.site import Site
from house_ai.geospatial.earthworks import integrate
from house_ai.storage import ProjectStore

HERE = Path(__file__).resolve().parent
store = ProjectStore(HERE.parents[1])
site = store.get(store.latest(ArtifactKind.SITE, "site"), Site)
surface = site.terrain.surface
NW, SW, SE, NE = site.boundary.outer
L_EDGE = math.dist(NW, NE)
EAST = ((NE[0] - NW[0]) / L_EDGE, (NE[1] - NW[1]) / L_EDGE)
SOUTH = (EAST[1], -EAST[0])
ROAD_Z = 1677.7  # near road edge spots 1677.44-1677.81 (road-seperated-c5)
FORMATION = 0.35  # slab + sub-base below finished floor (assumption)


def xy(u, v):
    return (NW[0] + u * EAST[0] + v * SOUTH[0], NW[1] + u * EAST[1] + v * SOUTH[1])


def rect(u0, u1, v0, v1):
    return Polygon([xy(u0, v0), xy(u1, v0), xy(u1, v1), xy(u0, v1)])


ENVELOPE = Polygon(site.buildable_envelope.polygon.outer)
PARCEL = Polygon(site.boundary.outer)


def evaluate(width, storey, a_road, a_up, a_low, b_low, terrace, lawn_drop, lawn_gap, low_storey=None):
    up_z = ROAD_Z - storey
    low_z = up_z - (low_storey or storey)
    b_up = b_low - terrace
    # Lowest finished floor owns each XY once.
    regions = [
        ("lower", rect(a_low, b_low, 0, width), low_z),
        ("upper", rect(a_up, a_low, 0, width), up_z),
        ("road", rect(a_road, a_up, 0, width), ROAD_Z),
    ]
    out = {"levels": {"road": ROAD_Z, "upper": up_z, "lower": low_z}}
    cut = 0.0
    worst_cut = worst_gap = 0.0
    for name, poly, z in regions:
        if poly.area < 1e-6:
            continue
        r = integrate(surface, poly.intersection(PARCEL), z - FORMATION)
        cut += r.cut_m3 or 0
        worst_cut = max(worst_cut, r.max_cut_m or 0)
        gap = max(0.0, z - FORMATION - (r.ground_min_m or z))
        worst_gap = max(worst_gap, gap)
        out[name] = {"u": [round(poly.bounds[0], 2)], "cut_m3": round(r.cut_m3 or 0, 1),
                     "max_cut_m": round(r.max_cut_m or 0, 2), "max_gap_m": round(gap, 2)}
    lawn_z = low_z - lawn_drop
    lawn = rect(b_low + lawn_gap, 40, -1, 25).intersection(ENVELOPE)
    lr = integrate(surface, lawn, lawn_z)
    out.update(
        plates={"road": [a_road, a_up + 0], "upper": [a_up, b_up], "lower": [a_low, b_low]},
        width_m=width, storey_m=storey, low_storey_m=low_storey or storey, terrace_m=terrace,
        upper_area_m2=round((b_up - a_up) * width, 1), lower_area_m2=round((b_low - a_low) * width, 1),
        core_overlap_u=[a_low, min(a_up + 9.0, b_up)],
        building_cut_m3=round(cut, 1), max_cut_m=round(worst_cut, 2), max_gap_m=round(worst_gap, 2),
        lawn={"z": round(lawn_z, 2), "area_m2": round(lawn.area, 1), "cut_m3": round(lr.cut_m3 or 0, 1),
              "fill_m3": round(lr.below_plane_m3 or 0, 1), "max_cut_m": round(lr.max_cut_m or 0, 2),
              "max_fill_m": round(lr.max_below_m or 0, 2), "stair_rise_m": lawn_drop},
    )
    return out


def sweep():
    found = []
    for width, storey, low_storey, a_up, a_low, b_low, terrace in itertools.product(
        [14.0, 15.0], [3.2, 3.4], [3.4, 3.6, 3.8], [x * 0.5 for x in range(0, 5)],
        [x * 0.5 for x in range(4, 16)], [x * 0.5 for x in range(20, 34)], [4.0, 4.5],
    ):
        b_up = b_low - terrace
        if (b_up - a_up) * width < 135 or (b_low - a_low) * width < 145:
            continue
        if a_low > a_up + 8.5 - 3.6:  # stair/lift shaft must sit under the road plate (a_up..a_up+8.5)
            continue
        found.append(evaluate(width, storey, a_up, a_up, a_low, b_low, terrace, 1.8, 3.0, low_storey))
    return found


if __name__ == "__main__":
    found = sweep()
    picks = {}
    for limit in (0.6, 1.0, 1.5):
        ok = [r for r in found if r["max_gap_m"] <= limit]
        ok.sort(key=lambda r: (r["max_cut_m"], r["building_cut_m3"]))
        picks[str(limit)] = ok[:3]
        print("gap <=", limit, "candidates", len(ok))
        for r in ok[:3]:
            print("  ", json.dumps({k: r[k] for k in ["width_m", "storey_m", "low_storey_m", "plates", "levels",
                  "upper_area_m2", "lower_area_m2", "building_cut_m3", "max_cut_m", "max_gap_m"]}))
            for drop in (1.8, 2.4, 3.0):
                pl = r["plates"]
                q = evaluate(r["width_m"], r["storey_m"], pl["upper"][0], pl["upper"][0], pl["lower"][0],
                             pl["lower"][1], r["terrace_m"], drop, 3.0, r["low_storey_m"])
                print("      lawn", q["lawn"])
    (HERE / "section-study.json").write_text(json.dumps(picks, indent=1))
