"""EXPLORATORY C04 concept generator (agent:claude-code, 2026-10-22).

Massing from section_study.py and owner answers (2026-10-22): straight plates stepping
east, north side dug in, bigger upper floor, entrance hall on the west through an
excavated courtyard, lift opening into the day area, open family stair upper->lower,
lawn 2.4 m below the lower floor.

Design decisions (agent): the shared lift shaft and the family stair are fixed below
(CORE). Each floor is then solved separately by CP-SAT with EXACT tiling (room areas
sum to the plate, so no unnamed leftover space), minimum widths, facade access for
habitable rooms where the survey TIN is below sill height (or a terrace/court is
outside), and door adjacencies. Canonical Builder2D assembles the model and
check_model audits it. Nothing is stored in the project record.

Run: .venv/bin/python projects/my-house/design/claude-c04/generate.py [--time 60]
"""

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

import ortools
from ortools.sat.python import cp_model
from shapely.geometry import box
from shapely.ops import unary_union

from house_ai.domain.geometry import Polygon2D
from house_ai.domain.integrity import check_model
from house_ai.domain.base import EXTERIOR
from house_ai.domain.model import Opening, OpeningKind, Operation, SlabKind, Stair, StairKind, WallKind
from house_ai.domain.plan import GenerationRecord, PlanVersion
from house_ai.domain.program import SpaceFunction as F
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, Provenance
from house_ai.domain.records import Assumption
from house_ai.domain.site import Site
from house_ai.generation.assemble2d import Builder2D
from house_ai.generation.frame import DesignFrame, Ground
from house_ai.generation.solver2d import PlacedRoom2D, SharedWall, Solution2D
from house_ai.generation.stairs import LANDING_STRIP_DM, u_layout
from house_ai.storage import ProjectStore

HERE = Path(__file__).resolve().parent
store = ProjectStore(HERE.parents[1])
actor = Actor(kind=ActorKind.AGENT, id="claude-code")
site_ref = store.latest(ArtifactKind.SITE, "site")
program_ref = store.latest(ArtifactKind.SPACE_PROGRAM, "program")
site = store.get(site_ref, Site)
program = store.get(program_ref, SpaceProgram)

NW, SW, SE, NE = site.boundary.outer
_len = math.dist(NW, NE)
EAST = ((NE[0] - NW[0]) / _len, (NE[1] - NW[1]) / _len)
SOUTH = (EAST[1], -EAST[0])
frame = DesignFrame(NW, EAST, SOUTH, "Owner-required alignment with the long N/S boundaries; "
                    "origin NW corner; u downhill (field east), v toward field south", None, None)
ground = Ground(site, frame)

ROAD, UPPER, LOWER = "lv-upper", "lv-entry", "lv-lower"
Z = {ROAD: 1677.7, UPPER: 1674.3, LOWER: 1670.7}
STOREY = {ROAD: 3.0, UPPER: 3.4, LOWER: 3.6}
FAMILY_STAIR_RISERS = 20  # 3.6 m / 20 = 0.18 m
# Plates in dm (u0, v0, u1, v1); BLOCKS are parts of the rectangle left open.
PLATE = {ROAD: (10, 0, 100, 124), UPPER: (10, 0, 132, 124), LOWER: (52, 0, 150, 156)}
BLOCKS = {ROAD: [(52, 86, 100, 124)]}
CORE = {"lift": (52, 62, 74, 86), "stair": (52, 0, 78, 50)}
TERRACES = [
    ("sp-deck-east", "Road-level roof deck (east)", ROAD, (100, 0, 132, 124)),
    ("sp-deck-south", "Road-level roof deck (south)", ROAD, (52, 86, 100, 124)),
    # Sunken court at the upper level, widened to the parcel edge. Its north part (v < 9.6 m)
    # is covered by the road-level forecourt slab, so garage and lobby doors open onto level
    # ground; the upper entrance opens under it (covered porch). Open to the sky further south.
    ("sp-court-west", "West entrance court (sunken; covered at north)", UPPER, [(-20, 40, 10, 96), (-52, 96, 10, 124)]),
    ("sp-terrace-south", "South terrace", UPPER, (10, 124, 132, 156)),
    ("sp-terrace-east", "East balcony (lower roof)", UPPER, (132, 0, 150, 156)),
    ("sp-terrace-lower", "Lower garden terrace", LOWER, (150, 0, 180, 156)),
]
OUTDOOR = ("sp-terrace-", "sp-deck-", "sp-court-")
# Doorless passages (owner: no unnecessary doors or barriers). Doors remain for bedrooms,
# bathrooms/WCs, the office, lift, garage, plant, laundry and stores.
DOORLESS = {frozenset(p) for p in [
    (F.ENTRY, F.HALL), (F.ENTRY, F.LIVING), (F.ENTRY, F.DINING), (F.ENTRY, F.KITCHEN),
    (F.KITCHEN, F.PANTRY), (F.HALL, F.FAMILY), (F.HALL, F.LIVING), (F.HALL, F.DINING),
]}
CELL = 2  # 0.2 m grid
SILL_M = 0.8


@dataclass
class Room:
    key: str
    name: str
    fn: F
    level: str
    area: tuple[float, float]
    min_w: float
    target: float | None = None
    window: bool = False
    edges: tuple[str, ...] = ()
    access: tuple[str, ...] = ()  # door to at least one of these
    pid: str = ""
    shaped: bool = False  # may be L-shaped (second rectangle)
    aspect: float = 2.2


ROOMS = [
    # Road level
    Room("garage", "Garage (SUV + sedan)", F.GARAGE, ROAD, (40, 50), 6.0, 42, edges=("west", "north"),
         pid="pi-garage"),
    Room("lobby", "Entrance lobby (road)", F.ENTRY, ROAD, (8, 16), 1.8, 10, edges=("west",), pid="pi-entry",
         shaped=True),
    Room("office", "Quiet office / guest", F.STUDY, ROAD, (11, 16), 3.0, 13, window=True,
         access=("lobby",), pid="pi-study-1"),
    Room("wc-r", "WC + shower", F.BATHROOM, ROAD, (2.5, 5), 1.2, 3.5, access=("lobby",)),
    Room("plant", "Plant / utilities", F.MECHANICAL, ROAD, (4, 8), 1.6, 5, access=("garage", "lobby"),
         pid="pi-mechanical"),
    Room("store-r", "Garage store / workshop", F.STORAGE, ROAD, (2, 30), 1.4, 8,
         access=("garage", "lobby"), shaped=True),
    # Upper level
    Room("entry", "Entrance hall (shoes)", F.ENTRY, UPPER, (9, 18), 2.4, 12, edges=("west",),
         access=("hall-u", "dining", "living", "lift-u"), shaped=True),
    Room("wc-u", "Guest WC", F.WC, UPPER, (2.2, 4), 1.1, 2.8, access=("entry", "hall-u")),
    Room("pantry", "Pantry", F.PANTRY, UPPER, (3, 6), 1.4, 4, access=("kitchen",), pid="pi-pantry"),
    Room("store-u", "Store", F.STORAGE, UPPER, (2, 14), 1.2, 4, access=("pantry", "entry", "hall-u"),
         pid="pi-storage", shaped=True),
    Room("kitchen", "Kitchen + breakfast", F.KITCHEN, UPPER, (16, 22), 3.4, 18, window=True,
         edges=("south",), access=("entry", "hall-u"), pid="pi-kitchen"),
    Room("dining", "Dining (open to kitchen + living)", F.DINING, UPPER, (12, 18), 3.2, 15,
         pid="pi-dining"),
    Room("living", "Living", F.LIVING, UPPER, (28, 40), 4.0, 33, window=True, edges=("east",),
         pid="pi-living", shaped=True),
    Room("hall-u", "Stair hall", F.HALL, UPPER, (3, 10), 1.2, 5, shaped=True),
    Room("master", "Grand master bedroom", F.BEDROOM, UPPER, (15, 20), 3.4, 17, window=True,
         edges=("east",), access=("closet", "hall-u"), pid="pi-bed-main"),
    Room("closet", "Dressing (suite vestibule)", F.STORAGE, UPPER, (3, 6), 1.4, 4,
         access=("hall-u", "living", "entry")),
    Room("ensuite-u", "Master shower room", F.BATHROOM, UPPER, (4.5, 7), 1.6, 5,
         access=("master",), pid="pi-bath-ensuite"),
    # Lower level
    Room("hall-l", "Landing", F.HALL, LOWER, (4, 14), 1.2, 7, shaped=True),
    Room("family", "Family room", F.FAMILY, LOWER, (18, 32), 3.8, 24, window=True,
         access=("hall-l",)),
    Room("bed3", "Parents / grandparents", F.BEDROOM, LOWER, (14, 21), 3.4, 16, window=True,
         access=("hall-l", "family"), pid="pi-bed-elder-1"),
    Room("ensuite-l", "Shower room (bed 3)", F.BATHROOM, LOWER, (4, 7), 1.6, 5, access=("bed3",),
         pid="pi-bath-2"),
    Room("boys", "Boys (two beds)", F.BEDROOM, LOWER, (16, 22), 3.2, 18, window=True,
         access=("hall-l", "family"), pid="pi-bed-child-1"),
    Room("girls", "Girls (two beds)", F.BEDROOM, LOWER, (16, 22), 3.2, 18, window=True,
         access=("hall-l", "family"), pid="pi-bed-child-2"),
    Room("shower-l", "Shared shower + basins", F.BATHROOM, LOWER, (4, 7), 1.6, 5,
         access=("hall-l", "family"), pid="pi-bath-1"),
    Room("wc-l", "Shared WC", F.WC, LOWER, (1.8, 3.2), 1.0, 2.2, access=("hall-l", "family")),
    Room("laundry", "Laundry / linen", F.LAUNDRY, LOWER, (4, 7), 1.6, 5, access=("hall-l", "family"),
         pid="pi-laundry"),
    Room("store-l", "Store", F.STORAGE, LOWER, (1.5, 20), 1.2, 3, access=("hall-l", "family", "laundry"),
         shaped=True),
]
# Fixed shared elements per level: (key, name, function, rect)
FIXED = {
    ROAD: [("lift-r", "Lift", F.LIFT, CORE["lift"])],
    UPPER: [("lift-u", "Lift", F.LIFT, CORE["lift"]), ("stair-u", "Family stair", F.STAIR, CORE["stair"])],
    LOWER: [("lift-l", "Lift", F.LIFT, CORE["lift"]), ("stair-l", "Family stair", F.STAIR, CORE["stair"])],
}
# Required relations beyond `access`: (a, b, door) where door False means a wide opening.
LINKS = {
    ROAD: [("lobby", "lift-r", True)],
    UPPER: [("hall-u", "stair-u", False), ("hall-u", "lift-u", True),
            ("kitchen", "dining", False), ("dining", "living", False), ("hall-u", "living", False),
            ("closet", "master", True)],
    LOWER: [("hall-l", "stair-l", False), ("hall-l", "lift-l", True)],
}
# Open-air spaces that lead outside: hayat stair (court), lawn stair (lower terrace),
# outdoor stair from the south terrace down to the lower terrace.
OUTDOOR_EXITS = [("sp-court-west", "south"), ("sp-terrace-lower", "east"), ("sp-terrace-south", "south")]
TERRACE_DOORS = [("entry", "sp-court-west"), ("kitchen", "sp-terrace-south"), ("living", "sp-terrace-south"),
                 ("living", "sp-terrace-east"), ("office", "sp-deck-south"), ("family", "sp-terrace-lower")]


def window_runs(level):
    """Plate-edge intervals (cells) where outside is a terrace/court or ground below sill."""
    u0, v0, u1, v1 = PLATE[level]
    open_rects = [q for t in TERRACES if t[2] == level for q in (t[3] if isinstance(t[3], list) else [t[3]])]
    runs = {}
    for edge, (fixed, lo, hi, out) in {
        "north": (v0, u0, u1, (0, -5)), "south": (v1, u0, u1, (0, 5)),
        "west": (u0, v0, v1, (-5, 0)), "east": (u1, v0, v1, (5, 0)),
    }.items():
        ok = []
        for s in range(lo, hi, CELL):
            m = s + CELL / 2
            u, v = (m, fixed) if edge in ("north", "south") else (fixed, m)
            pu, pv = u + out[0], v + out[1]
            if any(a <= pu <= c and b <= pv <= d for a, b, c, d in open_rects):
                ok.append(True)
                continue
            g = ground.at(pu / 10, pv / 10)
            ok.append(g is not None and g < Z[level] + SILL_M - 0.35)
        intervals, start = [], None
        for i, flag in enumerate(ok + [False]):
            if flag and start is None:
                start = i
            elif not flag and start is not None:
                intervals.append(((lo + start * CELL) // CELL, (lo + i * CELL) // CELL))
                start = None
        runs[edge] = intervals
    return runs


def _touch(md, A, B, span, name):
    flags = []
    for eq, l1, h1, l2, h2 in [
        (A["xe"] == B["x"], A["y"], A["ye"], B["y"], B["ye"]),
        (B["xe"] == A["x"], A["y"], A["ye"], B["y"], B["ye"]),
        (A["ye"] == B["y"], A["x"], A["xe"], B["x"], B["xe"]),
        (B["ye"] == A["y"], A["x"], A["xe"], B["x"], B["xe"]),
    ]:
        f = md.NewBoolVar(f"{name}{len(flags)}")
        md.Add(eq).OnlyEnforceIf(f)
        md.Add(h1 - l2 >= span).OnlyEnforceIf(f)
        md.Add(h2 - l1 >= span).OnlyEnforceIf(f)
        flags.append(f)
    any_f = md.NewBoolVar(name)
    md.AddBoolOr(flags).OnlyEnforceIf(any_f)
    for f in flags:
        md.AddImplication(f, any_f)
    return any_f


def touch_any(md, V, a, b, span=5):
    """Room a (any of its parts) shares >= span cells of wall with room b (any part)."""
    fs = []
    for i, pa in enumerate(V[a]["parts"]):
        for j, pb in enumerate(V[b]["parts"]):
            f = _touch(md, pa, pb, span, f"t-{a}-{b}-{i}-{j}")
            for p in (pa, pb):
                if "on" in p:
                    md.AddImplication(f, p["on"])
            fs.append(f)
    out = md.NewBoolVar(f"t-{a}-{b}")
    md.AddBoolOr(fs).OnlyEnforceIf(out)
    for f in fs:
        md.AddImplication(f, out)
    return out


def _rect_vars(md, key, plate, wmin, hmin, on=None):
    pu0, pv0, pu1, pv1 = plate
    x = md.NewIntVar(pu0, pu1, key + "x")
    y = md.NewIntVar(pv0, pv1, key + "y")
    w = md.NewIntVar(0, pu1 - pu0, key + "w")
    h = md.NewIntVar(0, pv1 - pv0, key + "h")
    xe = md.NewIntVar(pu0, pu1, key + "xe")
    ye = md.NewIntVar(pv0, pv1, key + "ye")
    md.Add(xe == x + w)
    md.Add(ye == y + h)
    a = md.NewIntVar(0, (pu1 - pu0) * (pv1 - pv0), key + "a")
    md.AddMultiplicationEquality(a, [w, h])
    if on is None:
        md.Add(w >= wmin)
        md.Add(h >= hmin)
        ix = md.NewIntervalVar(x, w, xe, key + "ix")
        iy = md.NewIntervalVar(y, h, ye, key + "iy")
    else:
        md.Add(w >= wmin).OnlyEnforceIf(on)
        md.Add(h >= hmin).OnlyEnforceIf(on)
        md.Add(w == 0).OnlyEnforceIf(on.Not())
        md.Add(h == 0).OnlyEnforceIf(on.Not())
        ix = md.NewOptionalIntervalVar(x, w, xe, on, key + "ix")
        iy = md.NewOptionalIntervalVar(y, h, ye, on, key + "iy")
    return dict(x=x, y=y, w=w, h=h, xe=xe, ye=ye, a=a, ix=ix, iy=iy)


def solve_level(level, seconds, seed, hint=None):
    md = cp_model.CpModel()
    plate = tuple(c // CELL for c in PLATE[level])
    pu0, pv0, pu1, pv1 = plate
    V, dev, small = {}, [], []
    rooms = [r for r in ROOMS if r.level == level]
    for r in rooms:
        min_c = math.ceil(r.min_w * 10 / CELL)
        lo_a, hi_a = (round(a * 100 / CELL**2) for a in r.area)
        p1 = _rect_vars(md, r.key, plate, min_c, min_c)
        parts = [p1]
        total = p1["a"]
        if r.shaped:
            on = md.NewBoolVar(r.key + "on2")
            p2 = _rect_vars(md, r.key + "_2", plate, 6, 6, on)
            p2["on"] = on
            glue = _touch(md, p1, p2, 6, r.key + "glue")
            md.AddImplication(on, glue)
            parts.append(p2)
            total = p1["a"] + p2["a"]
        else:
            md.Add(100 * p1["w"] <= round(r.aspect * 100) * p1["h"])
            md.Add(100 * p1["h"] <= round(r.aspect * 100) * p1["w"])
        md.Add(total >= lo_a)
        md.Add(total <= hi_a)
        if not r.window and level in (UPPER, LOWER) and r.fn not in (F.ENTRY, F.HALL):
            for q in parts:
                md.Add(q["xe"] <= pu1 - 1)
        for e in r.edges:
            md.Add({"west": p1["x"] == pu0, "east": p1["xe"] == pu1,
                    "north": p1["y"] == pv0, "south": p1["ye"] == pv1}[e])
        if r.key == "entry":
            # The entrance hall's west wall shares >= 1.2 m with the excavated court.
            court = next(t[3] for t in TERRACES if t[0] == "sp-court-west")
            span = (min(q[1] for q in court), max(q[3] for q in court))
            md.Add(p1["ye"] >= span[0] // CELL + 6)
            md.Add(p1["y"] <= span[1] // CELL - 6)
        V[r.key] = dict(parts=parts, total=total, room=r)
        if r.target:
            d = md.NewIntVar(0, 10**6, r.key + "dev")
            md.AddAbsEquality(d, total - round(r.target * 100 / CELL**2))
            dev.append(d)
        if r.fn in (F.HALL, F.STORAGE, F.ENTRY):
            small.append(total)
    fixed_area = 0
    for key, _name, _fn, rect in FIXED[level]:
        x, y, xe, ye = (c // CELL for c in rect)
        part = dict(x=md.NewConstant(x), y=md.NewConstant(y), xe=md.NewConstant(xe), ye=md.NewConstant(ye),
                    ix=md.NewFixedSizeIntervalVar(x, xe - x, key + "ix"),
                    iy=md.NewFixedSizeIntervalVar(y, ye - y, key + "iy"))
        V[key] = dict(parts=[part])
        fixed_area += (xe - x) * (ye - y)
    blocks = [tuple(c // CELL for c in b) for b in BLOCKS.get(level, [])]
    ix = [p["ix"] for v in V.values() for p in v["parts"]]
    iy = [p["iy"] for v in V.values() for p in v["parts"]]
    ix += [md.NewFixedSizeIntervalVar(b[0], b[2] - b[0], f"blk{i}x") for i, b in enumerate(blocks)]
    iy += [md.NewFixedSizeIntervalVar(b[1], b[3] - b[1], f"blk{i}y") for i, b in enumerate(blocks)]
    md.AddNoOverlap2D(ix, iy)
    plate_area = (pu1 - pu0) * (pv1 - pv0) - sum((b[2] - b[0]) * (b[3] - b[1]) for b in blocks)
    md.Add(sum(V[r.key]["total"] for r in rooms) + fixed_area == plate_area)
    # Habitable rooms own >= 1.2 m of open facade.
    runs = window_runs(level)
    for r in [r for r in rooms if r.window]:
        p = V[r.key]["parts"][0]
        opts = []
        for edge, ivs in runs.items():
            for lo, hi in ivs:
                if hi - lo < 6:
                    continue
                f = md.NewBoolVar(f"win-{r.key}-{edge}-{lo}")
                md.Add({"west": p["x"] == pu0, "east": p["xe"] == pu1, "north": p["y"] == pv0,
                        "south": p["ye"] == pv1}[edge]).OnlyEnforceIf(f)
                a, b = (p["x"], p["xe"]) if edge in ("north", "south") else (p["y"], p["ye"])
                md.Add(b >= lo + 6).OnlyEnforceIf(f)
                md.Add(a <= hi - 6).OnlyEnforceIf(f)
                opts.append(f)
        md.AddBoolOr(opts)
    doors = {}
    for r in rooms:
        if r.access:
            fs = [touch_any(md, V, r.key, o) for o in r.access]
            md.AddBoolOr(fs)
            doors.update({(r.key, o): f for o, f in zip(r.access, fs)})
    for a, b, is_door in LINKS[level]:
        f = touch_any(md, V, a, b, 5 if is_door else 10)
        md.Add(f == 1)
        doors[(a, b)] = f
    for k, rects in (hint or {}).items():
        if k in V and "room" in V[k] and rects:
            p = V[k]["parts"][0]
            for c, val in zip(("x", "y", "xe", "ye"), rects[0]):
                md.AddHint(p[c], val // CELL)
    md.Minimize(sum(dev) + sum(small))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = seed
    t = time.monotonic()
    st = solver.Solve(md)
    info = dict(level=level, status=solver.StatusName(st), wall_s=round(time.monotonic() - t, 1))
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, info
    info["objective"] = solver.ObjectiveValue()
    out = {}
    for k, v in V.items():
        rects = []
        for p in v["parts"]:
            if "on" in p and not solver.Value(p["on"]):
                continue
            vals = [solver.Value(p[c]) * CELL for c in ("x", "y", "xe", "ye")]
            if vals[2] > vals[0] and vals[3] > vals[1]:
                rects.append(tuple(vals))
        out[k] = rects
    opening = {(a, b) for a, b, door in LINKS[level] if not door}
    used = [(a, b, (a, b) in opening) for (a, b), f in doors.items() if solver.Value(f)]
    return (out, used), info


def _geom(r):
    return unary_union([box(*q) for q in (r.sub_rects or [(r.u0, r.v0, r.u1, r.v1)])])


def shared_wall(ra, rb):
    if ra.level_id != rb.level_id:
        return None
    inter = _geom(ra).boundary.intersection(_geom(rb).boundary)
    lines = [g for g in getattr(inter, "geoms", [inter]) if g.geom_type == "LineString"]
    if not lines:
        return None
    seg = max(lines, key=lambda g: g.length)
    x0, y0, x1, y1 = seg.bounds
    if x0 == x1:
        return SharedWall(ra.space_id, rb.space_id, ra.level_id, "v", int(x0), int(y0), int(y1))
    return SharedWall(ra.space_id, rb.space_id, ra.level_id, "h", int(y0), int(x0), int(x1))


def build_solution(results):
    rooms, links = [], []
    meta = {r.key: r for r in ROOMS}
    for level, (rects_by_key, used) in results.items():
        for k, rects in rects_by_key.items():
            if k in meta:
                name, fn, pid = meta[k].name, meta[k].fn, meta[k].pid
            else:
                name, fn = next((n, f) for kk, n, f, _ in FIXED[level] if kk == k)
                pid = "pi-lift" if fn is F.LIFT else "pi-stair"
            zone = "z-service" if level == ROAD else ("z-night" if fn in (F.BEDROOM, F.BATHROOM, F.WC)
                                                     else "z-day")
            rooms.append(PlacedRoom2D(
                "sp-" + k, name, fn, level, min(q[0] for q in rects), min(q[1] for q in rects),
                max(q[2] for q in rects), max(q[3] for q in rects), pid, zone,
                sub_rects=rects if len(rects) > 1 else None))
        links += [("sp-" + a, "sp-" + b, opening) for a, b, opening in used]
    for sid, name, lv, geom in TERRACES:
        rects = geom if isinstance(geom, list) else [geom]
        rooms.append(PlacedRoom2D(sid, name, F.TERRACE, lv, min(q[0] for q in rects), min(q[1] for q in rects),
                                  max(q[2] for q in rects), max(q[3] for q in rects), "", "z-outdoor",
                                  sub_rects=rects if len(rects) > 1 else None))
    links += [("sp-" + a, t, False) for a, t in TERRACE_DOORS]
    links.append(("sp-deck-south", "sp-deck-east", True))
    by = {r.space_id: r for r in rooms}
    walls, doors = [], []
    for a, b, opening in links:
        sw = shared_wall(by[a], by[b])
        if sw:
            walls.append(sw)
            doors.append((a, b, opening))
    sol = Solution2D(
        status="FEASIBLE", objective=0.0, rooms=rooms, shared_walls=walls, circulation_rooms=[],
        levels=[LOWER, UPPER, ROAD], deterministic_time=0.0, wall_time_s=0.0, seed=0,
        platform_info="local", strategy="stepped_terraces_exact_tiling", circulation_share=0.0,
        has_stairs=False, exterior_connections=[], level_elevations_m=dict(Z))
    return sol, doors


class Builder(Builder2D):
    doors: list = []
    stair_fits = None

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for lv in self.levels:
            lv.floor_to_floor_m = STOREY[lv.id]

    def wall_model(self, seg):
        wall = super().wall_model(seg)
        if seg.neg and seg.pos and all(s.startswith(OUTDOOR) for s in (seg.neg, seg.pos)):
            wall.kind = WallKind.PARAPET
            wall.height_m = 1.0
        return wall

    def _exterior(self, sid, kind, width, test, **kw):
        keep = self.walls
        self.walls = [w for w in keep if sid not in (w.neg, w.pos) or (w.neg and w.pos) or test(w)]
        op = self.place_opening(sid, None, kind, width_m=width, **kw)
        self.walls = keep
        return op

    def _windowable(self, w):
        """Ground outside the middle 1.8 m of the wall (where place_opening centres it) is below sill."""
        (a, c), (b, d) = self._seg_points(w)
        half = 9 / max(w.length_dm, 1)
        for t in (0.5 - half, 0.5, 0.5 + half):
            u, v = a + (b - a) * t, c + (d - c) * t
            if w.orient == "h":
                v += 5 if w.neg else -5
            else:
                u += 5 if w.neg else -5
            g = self.ground.at(u / 10, v / 10)
            if g is not None and g >= Z[w.level_id] + SILL_M - 0.35:
                return False
        return True

    def build_openings(self):
        rid = {r.space_id: r for r in self.sol.rooms}
        # Garage and road lobby open west onto the road-level forecourt: a landscape slab
        # (not a modelled space) bridging the covered north part of the sunken court.
        west = lambda w: w.orient == "v" and w.c == PLATE[ROAD][0]  # noqa: E731
        self._exterior("sp-garage", OpeningKind.DOOR, 5.5, west, operation=Operation.SLIDING,
                       prefix="d-garage")
        self._exterior("sp-lobby", OpeningKind.DOOR, 1.0, west, operation=Operation.SWING_RIGHT,
                       prefix="d-hayat")
        for a, b, opening in self.doors:
            pair = frozenset((rid[a].function, rid[b].function)) if b in rid else None
            if pair in DOORLESS or {a, b} == {"sp-closet", "sp-master"}:
                opening = True  # owner 2026-10-22: no unnecessary doors or barriers
            if opening:
                seg = max(self._walls_between(a, b), key=lambda w: w.length_dm)
                both_out = a.startswith(OUTDOOR) and b.startswith(OUTDOOR)
                self.place_opening(a, b, OpeningKind.OPENING, width_m=min(seg.length_m - 0.4, 3.6),
                                   height_m=1.0 if both_out else 2.4, operation=Operation.NONE, prefix="op")
            elif b.startswith(OUTDOOR):
                entry = a == "sp-entry"
                self.place_opening(a, b, OpeningKind.DOOR, width_m=1.0 if entry else 1.8,
                                   operation=Operation.SWING_RIGHT if entry else Operation.SLIDING,
                                   prefix="d-out")
            else:
                wet = {rid[a].function, rid[b].function} & {F.BATHROOM, F.WC}
                self.place_opening(a, b, OpeningKind.DOOR, width_m=0.8 if wet else 0.9,
                                   operation=Operation.SLIDING if F.WC in wet else Operation.SWING_LEFT,
                                   prefix="d")
        for sid, side in OUTDOOR_EXITS:
            r = rid[sid]
            c = {"south": r.v1, "east": r.u1, "west": r.u0, "north": r.v0}[side]
            self._exterior(sid, OpeningKind.OPENING, 1.2,
                           lambda w, c=c, side=side: w.c == c and (w.orient == "h") == (side in ("south", "north")),
                           height_m=1.0, operation=Operation.NONE, prefix="d-exit")
        habitable = (F.BEDROOM, F.LIVING, F.DINING, F.KITCHEN, F.STUDY, F.FAMILY)
        outdoors = [t for t in rid if t.startswith(OUTDOOR)]
        for r in self.sol.rooms:
            if r.function not in habitable:
                continue
            placed = 0
            for t in outdoors:
                if placed < 2 and self._walls_between(r.space_id, t):
                    if self.place_opening(r.space_id, t, OpeningKind.WINDOW, width_m=2.4, height_m=1.6,
                                          sill_m=0.6, operation=Operation.SLIDING, prefix="win"):
                        placed += 1
            for _ in range(2 - placed):
                if not self._exterior(r.space_id, OpeningKind.WINDOW, 1.8, self._windowable, height_m=1.4,
                                      sill_m=0.8, operation=Operation.SLIDING, prefix="win"):
                    self._slide_window(r.space_id)

    def _clear_at(self, w, off_dm, width_dm):
        """Survey ground is below sill along [off, off + width] of the wall, 0.5 m outside."""
        (a, c), (b, d) = self._seg_points(w)
        for t in (off_dm / w.length_dm, (off_dm + width_dm) / w.length_dm):
            u, v = a + (b - a) * t, c + (d - c) * t
            if w.orient == "h":
                v += 5 if w.neg else -5
            else:
                u += 5 if w.neg else -5
            g = self.ground.at(u / 10, v / 10)
            if g is not None and g >= Z[w.level_id] + SILL_M - 0.35:
                return False
        return True

    def _slide_window(self, sid, width_dm=14):
        """Off-centre window where only part of an exterior wall clears the ground."""
        for w in sorted(self._walls_between(sid, None), key=lambda w: -w.length_dm):
            for off in range(2, w.length_dm - width_dm - 1, 2):
                if any(off + width_dm > u0 and off < u1 for u0, u1 in w.used):
                    continue
                if self._clear_at(w, off, width_dm) and self._exterior_span_is_clear(w, off, width_dm, sid):
                    w.used.append((off, off + width_dm))
                    self.openings.append(Opening(
                        id=f"win-slid-{len(self.openings) + 1:02d}", host_wall_id=w.id, kind=OpeningKind.WINDOW,
                        offset_m=off / 10, width_m=width_dm / 10, height_m=1.4, sill_m=0.8,
                        operation=Operation.SLIDING, material_id="m-window", connects=(sid, EXTERIOR)))
                    return True
        return False

    def build_model(self, *a, **kw):
        model = super().build_model(*a, **kw)
        bottom = next(r for r in self.sol.rooms if r.space_id == "sp-stair-l")
        top = next(r for r in self.sol.rooms if r.space_id == "sp-stair-u")
        along_u = (top.u1 - top.u0) >= (top.v1 - top.v0)
        short = (top.v1 - top.v0) if along_u else (top.u1 - top.u0)
        width = round(min(1.0, short / 20 - 0.2), 3)
        lo, hi = (top.u0 + 2, top.u1 - 2) if along_u else (top.v0 + 2, top.v1 - 2)
        c0, c1 = (top.v0 + 2, top.v1 - 2) if along_u else (top.u0 + 2, top.u1 - 2)
        # Both flights meet the open south end of the stair, towards the halls.
        near, far = hi + 2 - LANDING_STRIP_DM, lo
        pts, fits = u_layout(near, far, c0, c1, width * 10, FAMILY_STAIR_RISERS)
        r0, r1 = sorted((near, far))
        fp = self.frame.rect(r0, c0, r1, c1) if along_u else self.frame.rect(c0, r0, c1, r1)
        line = [self.frame.to_local(*((x, c) if along_u else (c, x))) for x, c in pts]
        rise = Z[UPPER] - Z[LOWER]
        model.stairs = [Stair(
            id="stair-family", kind=StairKind.U_SHAPED, from_level_id=LOWER, to_level_id=UPPER,
            footprint=fp, bottom_space_id=bottom.space_id, top_space_id=top.space_id, width_m=width,
            riser_count=FAMILY_STAIR_RISERS, riser_height_m=rise / FAMILY_STAIR_RISERS, tread_depth_m=0.28,
            walking_line=line, landing_segments=[1])]
        self.stair_fits = fits
        hole = fp.to_shapely()
        for s in model.slabs:
            if s.level_id == UPPER and s.kind is SlabKind.FLOOR and s.boundary.to_shapely().intersects(hole):
                g = s.boundary.to_shapely().difference(hole)
                g = max(getattr(g, "geoms", [g]), key=lambda q: q.area)
                s.boundary = Polygon2D(outer=list(g.exterior.coords)[:-1],
                                       holes=[list(r.coords)[:-1] for r in g.interiors])
        return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--option", default="a")
    ap.add_argument("--reuse", action="store_true", help="rebuild from solve-cache.json")
    ap.add_argument("--resolve", choices=[ROAD, UPPER, LOWER], help="with --reuse: re-solve this level only")
    args = ap.parse_args()
    out = HERE / f"claude-c04-{args.option}"
    out.mkdir(exist_ok=True)
    cache = out / "solve-cache.json"
    if args.reuse:
        saved = json.loads(cache.read_text())
        infos = saved["infos"]
        results = {lv: ({k: [tuple(q) for q in v] for k, v in r[0].items()}, [tuple(u) for u in r[1]])
                   for lv, r in saved["results"].items()}
        if args.resolve:
            res, info = solve_level(args.resolve, args.time, args.seed, hint=results[args.resolve][0])
            print(json.dumps(info), flush=True)
            if not res:
                raise SystemExit(f"no layout on {args.resolve}: {info['status']}")
            results[args.resolve] = res
            infos = [info if i["level"] == args.resolve else i for i in infos]
            cache.write_text(json.dumps({"infos": infos, "results": results}))
    else:
        results, infos = {}, []
        for level in (ROAD, UPPER, LOWER):
            res, info = solve_level(level, args.time, args.seed)
            infos.append(info)
            print(json.dumps(info), flush=True)
            if not res:
                (out / "solver.json").write_text(json.dumps(infos, indent=1))
                raise SystemExit(f"no layout on {level}: {info['status']}")
            results[level] = res
        cache.write_text(json.dumps({"infos": infos, "results": results}))
    (out / "solver.json").write_text(json.dumps(infos, indent=1))
    sol, doors = build_solution(results)
    Builder.doors = doors
    builder = Builder(sol, site, frame, ground, program, actor)
    model = builder.build_model(f"claude-c04-{args.option}", f"Claude C04-{args.option.upper()}",
                                site_ref, program_ref)
    names = {ROAD: "Road level 1677.7 - garage, lobby, office", UPPER: "Upper 1674.3 - day + grand master",
             LOWER: "Lower 1670.7 - bedrooms + family room"}
    for lv in model.levels:
        lv.name = names[lv.id]
    model.assumptions = [Assumption(
        id="c04-basis", made_by=actor,
        statement="EXPLORATORY. Topology of the shared lift and family stair and the floor plates are agent "
                  "design decisions from the section study and owner answers of 2026-10-22; room geometry "
                  "is CP-SAT exact tiling per floor. Levels: road 1677.7 (near road-edge spots "
                  "1677.44-1677.81), upper 1674.3, lower 1670.7, lawn 1668.3. North wall on the boundary "
                  "(owner: no north limit). West court excavated to the upper level (owner idea). Room sizes "
                  "are agent proposals, not an approved program. Structure, retaining walls, drainage, "
                  "waterproofing and codes are unresolved.")]
    plan = PlanVersion(
        option_id=model.id, label=model.name, strategy="stepped-terraces-exact-tiling", model=model,
        provenance=Provenance(created_at=store.clock(), created_by=actor, method="cpsat_exact_tiling",
                              inputs=[site_ref, program_ref]),
        generation=GenerationRecord(generator="claude-c04-project-solver", generator_version="2",
                                    solver="ortools-cp-sat", solver_version=ortools.__version__,
                                    solver_status="FEASIBLE", objective=sum(i["objective"] for i in infos),
                                    seed=args.seed, deterministic_time_limit=float(args.time)))
    (out / "plan.json").write_text(plan.model_dump_json(indent=2) + "\n")
    findings = check_model(model, site, program)
    (out / "violations.json").write_text(json.dumps([f.model_dump(mode="json") for f in findings],
                                                    indent=2) + "\n")
    (out / "placement.json").write_text(json.dumps(
        {"plates": PLATE, "blocks": BLOCKS, "core": CORE, "levels": Z, "terraces": TERRACES,
         "stair_fits": builder.stair_fits,
         "rooms": [{**r.__dict__, "function": r.function.value} for r in sol.rooms], "doors": doors},
        indent=1, default=str))
    print("EXPORTED", out, "findings", len(findings), "stair fits", builder.stair_fits)
    for f in findings:
        print(" -", str(f)[:220])


if __name__ == "__main__":
    main()
