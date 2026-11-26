"""C11 structure model: what every slab stands on (rule 4.9, stmt-027), drawn the same way everywhere.

One list of elements (design.structure()) plus each storey's own outer and core walls, plus the site walls
derived once from the ground model. Plans, sections, the support sheet and the 3D model all draw from these
lists, and each returns the ids it drew so checks.py can prove they agree (C11-DRW-01, §7 check 3).

Concept-stage only: spans and supports are a geometric consistency check, not an engineering design.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

import engine as E
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
from shapely.ops import linemerge, unary_union
from shapely.prepared import prep

SPAN_MAX = 7.0  # one-way slab span between two bearing lines, m (concept limit)
CANT_MAX = 1.4  # cantilever beyond a bearing line (C11 §7 check 1)
ON_LINE = 0.30  # a slab point within this of a bearing line stands on it
FILL_MAX = 1.0  # ground-bearing slab: at most 1.0 m of engineered fill under the formation (§7 check 4)
STEP = 0.25  # sampling grid, m


@dataclass
class Element:
    id: str
    kind: str  # wall | beam | column | retaining
    geom: object  # LineString or Point
    z_bot: float
    z_top: float
    t: float = 0.25
    storey: str = ""  # lower | main | road | site | all
    note: str = ""


@dataclass
class Flight:
    id: str
    risers: int
    rise: float
    going: float
    width: float
    z_top: float
    z_bot: float


@dataclass
class OutdoorStair:
    name: str
    route: str
    flights: list[Flight]
    landings: list[str]
    landing_min: float
    handrails: str
    width_clear: float


@dataclass
class Slab:
    id: str
    name: str
    geom: Polygon
    z: float
    level: str  # level key the slab belongs to, or "roof"
    kind: str  # plate | terrace | deck | roof
    suspended: object = None  # polygon of the plate declared suspended
    ground_ok: bool = False  # may bear on the ground


@dataclass
class Report:
    slabs: list = field(default_factory=list)
    cells: dict = field(default_factory=dict)  # slab id -> [(cell polygon, kind)]


STOREY_BELOW = {"road": "main", "main": "lower", "roof": "road"}


def storey_height(key: str) -> float:
    return {"lower": 3.6, "main": 3.9, "road": 3.3}[key]


def slabs(opt) -> list[Slab]:
    L = opt.levels
    out = []
    for key in ("lower", "main", "road"):
        lv = L[key]
        susp = unary_union(lv.suspended) if lv.suspended else Polygon()
        out.append(Slab(f"{key}-plate", f"{lv.title.title().replace(' + Garden', '')} floor", lv.footprint, lv.z, key, "plate", susp, True))
        for t in lv.terraces:
            if t.kind in ("terrace", "deck", "green"):
                out.append(Slab(t.id, t.name.title() or t.note, t.geom, t.z, key, "terrace" if t.kind == "terrace" else "deck"))
    road = L["road"]
    out.append(Slab("roof", "Road-level roof", road.footprint, road.z + storey_height("road"), "roof", "roof"))
    return out


def _lines(geom) -> list[LineString]:
    if geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [geom]
    if geom.geom_type in ("MultiLineString", "GeometryCollection"):
        return [g for g in geom.geoms if g.geom_type == "LineString"]
    if geom.geom_type == "Polygon":
        return [LineString(geom.exterior.coords)] + [LineString(h.coords) for h in geom.interiors]
    if geom.geom_type == "MultiPolygon":
        return [x for g in geom.geoms for x in _lines(g)]
    return []


OPENING_MIN = 1.0  # openings at least this wide are not wall: something else must carry over them


def storey_walls(lv, solid: bool = True) -> list[LineString]:
    """A storey's own bearing walls: the plate's outer wall and the stair and lift walls.

    With solid=True (default), outside doors and windows 1.0 m wide or more are cut out: glass is not a wall.
    """
    out = _lines(lv.footprint)
    for r in lv.rooms:
        if r.kind in ("stair", "lift") or r.id == "store-u":
            out += _lines(r.geom)
    if not solid:
        return out
    cuts = [E.door_cut(d) for d in lv.doors if "ext" in (d.a, d.b) and d.w >= OPENING_MIN]
    cuts += [E.win_cut(w) for w in lv.windows if max(abs(w.u1 - w.u0), abs(w.v1 - w.v0)) >= OPENING_MIN]
    if cuts:
        cu = unary_union(cuts)
        res = []
        for ln in out:
            res += _lines(ln.difference(cu))
        out = [x for x in res if x.length > 0.05]
    return out


def bearing_lines(opt, elements, slab: Slab) -> list[LineString]:
    """Lines that carry this slab: walls of the storey below, plus beams and walls whose top is at the slab."""
    out = []
    L = opt.levels
    below = STOREY_BELOW.get(slab.level)
    if below:
        out += storey_walls(L[below])
        out += [e.geom for e in elements if e.kind in ("wall", "retaining") and e.storey == below and e.geom.geom_type == "LineString"]
    if slab.level == "lower":
        out += storey_walls(L["lower"])  # perimeter strip footings
        out += [e.geom for e in elements if e.kind in ("wall", "retaining") and e.storey == "lower"]
    for e in elements:
        if e.geom.geom_type != "LineString":
            continue
        if e.kind == "beam" and abs(e.z_top - slab.z) <= 0.35:
            out.append(e.geom)
        elif e.kind in ("wall", "retaining") and abs(e.z_top - slab.z) <= 0.35 and e.z_bot < slab.z - 0.3:
            out.append(e.geom)
    flat = []
    for g in out:
        flat += _lines(g)
    return flat


def _ray_hits(p: Point, lines_u, lines_v, along: str, sign: int, reach: float = 7.6):
    """Distance from p to the nearest bearing line crossed by a ray along u or v."""
    u, v = p.x, p.y
    end = (u + sign * reach, v) if along == "u" else (u, v + sign * reach)
    ray = LineString([(u, v), end])
    best = None
    for ln in lines_u if along == "u" else lines_v:
        if not ray.intersects(ln):
            continue
        x = ray.intersection(ln)
        for g in getattr(x, "geoms", [x]):
            if g.geom_type == "Point":
                d = math.hypot(g.x - u, g.y - v)
                if d > 1e-6 and (best is None or d < best):
                    best = d
    return best


def classify(opt, gm, elements, slab: Slab):
    """Per sample point of a slab: ground | wall | span | cantilever | unsupported."""
    lines = bearing_lines(opt, elements, slab)
    allg = unary_union(lines) if lines else LineString()
    pl = prep(allg.buffer(ON_LINE)) if lines else None
    susp = slab.suspended if slab.suspended is not None else Polygon()
    lower_fp = None
    if slab.level in ("main", "road", "roof") and slab.kind == "plate":
        lower_fp = unary_union([lv.footprint for lv in opt.levels.values() if lv.z < slab.z - 0.5])
    u0, v0, u1, v1 = slab.geom.bounds
    ps = prep(slab.geom)
    out = []
    i = 0
    while u0 + (i + 0.5) * STEP < u1:
        j = 0
        while v0 + (j + 0.5) * STEP < v1:
            cu, cv = u0 + (i + 0.5) * STEP, v0 + (j + 0.5) * STEP
            p = Point(cu, cv)
            j += 1
            if not ps.contains(p):
                continue
            kind = None
            if slab.ground_ok and not susp.contains(p) and (lower_fp is None or not lower_fp.contains(p)):
                zn = E.zg_safe(cu, cv)
                if zn >= slab.z - E.FORMATION - FILL_MAX:
                    kind = "ground"
            if kind is None and pl is not None and pl.contains(p):
                kind = "wall"
            if kind is None:
                du = [_ray_hits(p, lines, lines, "u", s) for s in (-1, 1)]
                dv = [_ray_hits(p, lines, lines, "v", s) for s in (-1, 1)]
                if (du[0] and du[1] and du[0] + du[1] <= SPAN_MAX) or (dv[0] and dv[1] and dv[0] + dv[1] <= SPAN_MAX):
                    kind = "span"
                else:
                    cand = [d for d in du + dv if d is not None]
                    edge = any(a is None for a in du + dv)
                    kind = "cantilever" if cand and min(cand) <= CANT_MAX and edge else "unsupported"
            out.append((box(cu - STEP / 2, cv - STEP / 2, cu + STEP / 2, cv + STEP / 2), kind))
        i += 1
    return out


def support_report(opt, gm, elements) -> Report:
    rep = Report()
    for s in slabs(opt):
        cells = classify(opt, gm, elements, s)
        rep.cells[s.id] = cells
        area = {k: 0.0 for k in ("ground", "wall", "span", "cantilever", "unsupported")}
        for c, k in cells:
            area[k] += c.intersection(s.geom).area
        bad = unary_union([c for c, k in cells if k == "unsupported"])
        rep.slabs.append({"id": s.id, "name": s.name, "level": s.level, "z": round(s.z, 2),
                          "area": round(s.geom.area, 1), **{k: round(v, 1) for k, v in area.items()},
                          "unsupported_where": [tuple(round(x, 1) for x in g.bounds) for g in E.polys(bad.buffer(0.01))]})
    return rep


# ---------------------------------------------------------------- wall over wall
def wall_over_wall(opt, elements) -> dict:
    """Every bearing wall of the main and road storeys lands on a wall or beam below, or on a footing."""
    L = opt.levels
    rows = []
    for key in ("main", "road"):
        lv = L[key]
        below = STOREY_BELOW[key]
        lower = L[below]
        own = [(f"{key} outer/core", g) for g in storey_walls(lv)]
        own += [(e.id, e.geom) for e in elements if e.storey == key and e.kind in ("wall", "retaining")]
        carriers = storey_walls(lower) + [e.geom for e in elements if e.geom.geom_type == "LineString"
                                          and (e.storey == below or (e.kind == "beam" and abs(e.z_top - lv.z) <= 0.35)
                                               or (e.kind in ("wall", "retaining") and abs(e.z_top - lv.z) <= 0.35))]
        cols = [e.geom for e in elements if e.kind == "column" and e.z_bot < lv.z - 0.3 and e.z_top >= lv.z - 0.1]
        carr = unary_union(carriers + [c.buffer(0.25) for c in cols])
        fp_below = prep(lower.footprint.buffer(-0.05))
        susp = unary_union(lv.suspended) if lv.suspended else Polygon()
        segs = []
        for name, g in own:
            for ring in _lines(g):
                cs = list(ring.coords)
                segs += [(name, LineString([a, b])) for a, b in zip(cs, cs[1:]) if math.dist(a, b) > 0.05]
        for name, ln in segs:
            if True:
                n = max(1, int(ln.length / STEP))
                worst, bad_len, off_len = 0.0, 0.0, 0.0
                for k in range(n):
                    p = ln.interpolate((k + 0.5) / n, normalized=True)
                    if key == "main" and not fp_below.contains(p):
                        continue  # founded on its own footing in the dug ground
                    d = carr.distance(p)
                    if key == "road" and not fp_below.contains(p) and not susp.buffer(0.3).contains(p):
                        d = d if d > 0.1 else 0.0
                    worst = max(worst, d)
                    if d > 0.5:
                        bad_len += ln.length / n
                    elif d > 0.1:
                        off_len += ln.length / n
                if bad_len > 0.05 or off_len > 0.05:
                    rows.append({"storey": key, "wall": name, "from": tuple(round(x, 2) for x in ln.coords[0]),
                                 "to": tuple(round(x, 2) for x in ln.coords[-1]), "worst_offset_m": round(worst, 2),
                                 "mid_span_m": round(bad_len, 2), "offset_0.1_0.5_m": round(off_len, 2)})
    return {"rows": rows, "mid_span_total_m": round(sum(r["mid_span_m"] for r in rows), 2),
            "offset_total_m": round(sum(r["offset_0.1_0.5_m"] for r in rows), 2)}


def columns_and_beams(opt, gm, elements) -> dict:
    """Columns reach below the ground; beam ends rest on a column, a wall or another beam."""
    bad_cols, bad_beams = [], []
    for e in elements:
        if e.kind == "column":
            zg = min(E.zg_safe(e.geom.x, e.geom.y), gm.finished(e.geom.x, e.geom.y))
            # a column may also start on a bearing wall whose top is at its base
            on_wall = any(abs(w.z_top - e.z_bot) < 0.15 and w.geom.geom_type == "LineString" and w.geom.distance(e.geom) < 0.2
                          for w in elements if w.kind in ("wall", "retaining"))
            if e.z_bot > zg - 0.5 and not on_wall:
                bad_cols.append(f"{e.id}: footing {e.z_bot:.2f} vs ground {zg:.2f}")
    for e in elements:
        if e.kind != "beam":
            continue
        cols = [c.geom for c in elements if c.kind == "column" and c.z_top >= e.z_top - 0.1 and c.z_bot < e.z_bot]
        walls_ = [c.geom for c in elements if c.kind in ("wall", "retaining", "beam") and c is not e and c.geom.geom_type == "LineString"]
        st = STOREY_BELOW.get({1677.5: "road", 1673.6: "main"}.get(round(e.z_top, 1), ""), "")
        if st:
            walls_ += storey_walls(opt.levels[st])
        if e.storey in ("lower", "main") and round(e.z_top, 1) == 1673.6:
            walls_ += storey_walls(opt.levels["lower"])
        if round(e.z_top, 1) == 1677.5:
            walls_ += storey_walls(opt.levels["main"])
        for lv in opt.levels.values():
            if lv.z <= e.z_bot and lv.z + storey_height(lv.key) >= e.z_top - 0.4:
                walls_ += storey_walls(lv)
        sup = unary_union(walls_ + [c.buffer(0.3) for c in cols])
        for end in (Point(e.geom.coords[0]), Point(e.geom.coords[-1])):
            if sup.distance(end) > 0.3:
                bad_beams.append(f"{e.id} end ({end.x:.2f}, {end.y:.2f})")
    return {"columns_not_founded": bad_cols, "beam_ends_unsupported": bad_beams}


def lower_foundations(opt, elements) -> list[str]:
    """Every lower outer wall reaches sound ground: where the ground under it is below the formation,
    a foundation wall must take it down (the house never stands on air at its edge)."""
    lv = opt.levels["lower"]
    form = lv.z - E.FORMATION
    fws = [e for e in elements if e.kind in ("wall", "retaining") and e.geom.geom_type == "LineString" and e.z_top <= lv.z + 3.7]
    bad = []
    for ln in _lines(lv.footprint):
        n = max(1, int(ln.length / STEP))
        for k in range(n):
            p = ln.interpolate((k + 0.5) / n, normalized=True)
            zg = E.zg_safe(p.x, p.y)
            if zg >= form - 0.3:
                continue
            if not any(e.geom.distance(p) < 0.25 and e.z_bot <= zg - 0.3 for e in fws):
                bad.append((round(p.x, 1), round(p.y, 1), round(form - zg, 2)))
    return bad


# ---------------------------------------------------------------- site walls, derived once from the ground model
@dataclass
class SiteWall:
    id: str
    geom: LineString
    z_top: float
    z_bot: float  # finished level on the low side
    note: str = ""

    @property
    def height(self) -> float:
        return self.z_top - self.z_bot


def site_walls(gm, elements) -> list[SiteWall]:
    """Wherever the finished ground steps by 0.3 m or more at the edge of a platform, a wall holds it."""
    pieces = []
    for r in gm.regions:
        if r.kind in ("pit", "void"):
            continue
        for ring in [r.geom.exterior, *r.geom.interiors]:
            cs = list(ring.coords)
            for (ua, va), (ub, vb) in zip(cs, cs[1:]):
                d = math.hypot(ub - ua, vb - va)
                if d < 1e-6:
                    continue
                n = ((vb - va) / d, -(ub - ua) / d)
                if r.geom.contains(Point((ua + ub) / 2 + n[0] * 0.02, (va + vb) / 2 + n[1] * 0.02)):
                    n = (-n[0], -n[1])
                m = max(1, int(d / 0.5))
                for k in range(m):
                    p0 = (ua + (ub - ua) * k / m, va + (vb - va) * k / m)
                    p1 = (ua + (ub - ua) * (k + 1) / m, va + (vb - va) * (k + 1) / m)
                    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
                    out = (mid[0] + n[0] * 0.05, mid[1] + n[1] * 0.05)
                    if not E.PARCEL.buffer(0.3).contains(Point(out)):
                        continue
                    other = gm.region_at(*out)
                    if other is not None and other.kind in ("pit", "void"):
                        continue  # the house's own buried wall
                    zi = r.level(mid[0] - n[0] * 0.05, mid[1] - n[1] * 0.05)
                    zo = other.level(*out) if other else E.zg_safe(*out)
                    if abs(zi - zo) < 0.25:
                        continue
                    key = (id(r), id(other) if other else None, round(math.atan2(vb - va, ub - ua), 2))
                    pieces.append((key, LineString([p0, p1]), max(zi, zo), min(zi, zo)))
    # one run per edge between the same two platforms; keep the highest top and lowest bottom of the run
    groups: dict = {}
    for key, g, t, b in pieces:
        groups.setdefault(frozenset([key[0], key[1]]) | {key[2]}, []).append((g, t, b))
    runs = []
    seen = []
    for items in groups.values():
        u_ = unary_union([g for g, _, _ in items])
        merged = u_ if u_.geom_type == "LineString" else linemerge(u_)
        for ln in _lines(merged):
            if ln.length < 0.4 or any(ln.buffer(0.05).contains(x) or x.buffer(0.05).contains(ln) for x in seen):
                continue
            seen.append(ln)
            own = [(t, b) for g, t, b in items if g.within(ln.buffer(0.05))]
            name = ""
            for e in elements:
                if e.kind in ("retaining", "wall") and e.geom.geom_type == "LineString" and ln.within(e.geom.buffer(0.35)):
                    name = e.id
                    break
            runs.append(SiteWall(name or f"SW-{len(runs) + 1}", ln, round(max(t for t, _ in own), 2), round(min(b for _, b in own), 2),
                                 "explicit element" if name else "derived from the ground model"))
    return runs


def ground_steps_unwalled(gm, walls_: list[SiteWall], opt=None, elements=()) -> list[tuple]:
    """Independent re-sampling of the ground steps: any step >= 0.3 m without a wall within 0.15 m.

    Steps against the house itself (within its 0.25 m outer wall) and along explicit walls count as walled.
    """
    cover = unary_union([w.geom for w in walls_]).buffer(0.15) if walls_ else Polygon()
    if opt is not None:
        cover = cover.union(unary_union([lv.footprint for lv in opt.levels.values()]).buffer(E.EXT_OUT + 0.1, join_style=2))
    lines = [e.geom for e in elements if e.kind in ("wall", "retaining") and e.geom.geom_type == "LineString"]
    if lines:
        cover = cover.union(unary_union(lines).buffer(0.3))
    bad = []
    for r in gm.regions:
        if r.kind in ("pit", "void"):
            continue
        ring = r.geom.exterior
        n = max(1, int(ring.length / 0.25))
        for k in range(n):
            d = (k + 0.5) / n * ring.length
            p = ring.interpolate(d)
            pa, pb = ring.interpolate(max(0.0, d - 0.02)), ring.interpolate(min(ring.length, d + 0.02))
            L = math.hypot(pb.x - pa.x, pb.y - pa.y) or 1.0
            nu, nv = (pb.y - pa.y) / L, -(pb.x - pa.x) / L
            for s in (1, -1):
                for qq in (Point(p.x + s * nu * 0.06, p.y + s * nv * 0.06),):
                    if r.geom.contains(qq) or not E.PARCEL.contains(qq):
                        continue
                    o = gm.region_at(qq.x, qq.y)
                    if o is not None and o.kind in ("pit", "void"):
                        continue
                    zo = o.level(qq.x, qq.y) if o else E.zg_safe(qq.x, qq.y)
                    zi = r.level(p.x, p.y)
                    if abs(zi - zo) >= 0.3 and not cover.contains(p):
                        bad.append((round(p.x, 1), round(p.y, 1), round(abs(zi - zo), 2)))
    return sorted(set(bad))[:20]


# ---------------------------------------------------------------- plan overlay (same elements on every plan)
PLAN_Z = (1670.0, 1673.6, 1677.5)


def plan_for(z_top: float) -> float:
    """The one plan an outdoor wall belongs to: the highest floor at or below its top + 0.7 m."""
    cand = [z for z in PLAN_Z if z <= z_top + 0.7]
    return max(cand) if cand else PLAN_Z[0]


def elements_on_level(lv, elements, walls_: list[SiteWall]):
    els = []
    for e in elements:
        if e.kind in ("column", "beam"):
            if e.z_bot < lv.z + 1.0 <= e.z_top + 0.6 or (e.kind == "beam" and lv.z < e.z_top <= lv.z + 4.0):
                els.append(e)
        elif e.kind == "retaining" or e.storey == "site" or e.id.startswith(("FW-", "RC-", "LIFT")):
            if e.id == "LIFT-OVR":
                continue  # on the roof: sections and 3D only
            if abs(plan_for(e.z_top) - lv.z) < 0.01 or (e.id.startswith("LIFT") and lv.key == "lower"):
                els.append(e)
    sws = [w for w in walls_ if abs(plan_for(w.z_top) - lv.z) < 0.01 and not w.id.startswith(("RW-", "FW-", "RC-"))]
    return els, sws


def draw_on_plan(sheet, lv, elements, walls_) -> set[str]:
    els, sws = elements_on_level(lv, elements, walls_)
    drawn = set()
    for e in els:
        if e.kind == "column":
            sheet.path(box(e.geom.x - e.t / 2, e.geom.y - e.t / 2, e.geom.x + e.t / 2, e.geom.y + e.t / 2), "col")
        elif e.kind == "beam":
            if e.z_top <= lv.z + 0.4:
                continue  # a beam under this floor belongs to the plan below
            sheet.path(e.geom, "beam")
        elif e.z_top <= lv.z + 0.05 and e.z_bot < lv.z - 0.3:
            # under this floor (ground beams, foundation walls, the lift pit): hidden, dashed
            sheet.path(e.geom.buffer(e.t / 2, cap_style=2), "below")
        else:
            sheet.path(e.geom.buffer(e.t / 2, cap_style=2), "rwall")
        drawn.add(e.id)
    for w in sws:
        sheet.path(w.geom.buffer(0.12, cap_style=2), "rwall")
        drawn.add(w.id)
    return drawn


# ---------------------------------------------------------------- the "what stands on what" sheet
COLOURS = {"ground": "#c9a675", "wall": "#3d6fb0", "span": "#8fb3dc", "cantilever": "#55b0a3", "unsupported": "#d0312d"}
WORDS = {"ground": "on dug ground (≤1.0 m fill)", "wall": "directly on a wall or beam below",
         "span": "spans between walls/beams below (≤7.0 m)", "cantilever": "cantilever ≤1.4 m", "unsupported": "STANDS ON NOTHING"}


def draw_support_sheet(opt, gm, elements, rep: Report, path_svg: Path, design_grid) -> set[str]:
    """Three panels: the road slab over the main floor, the main slab over the lower floor, the lower slab on the ground."""
    W, H = 2400, 900
    parts = [f'<rect class="bg" x="0" y="0" width="{W}" height="{H}"/>',
             '<text class="h1" x="40" y="48">C11 · What stands on what</text>',
             '<text class="h2" x="40" y="72">Each floor (and its terraces) coloured by what carries it, drawn over the walls, beams and columns of the storey below. '
             'Dark lines = bearing walls below. Squares = columns. Grid = the structural grid. Drawn in the design frame: east (downhill) to the right, south down.</text>']
    panels = [
        ("road", ["road-plate", "deck-r", "green-r", "fore-deck"], "ROAD LEVEL 1677.50 over the main floor",
         "Garage, hall, office and the roof terrace stand on the main floor's walls."),
        ("main", ["main-plate", "t-south", "balc-e", "balc-m"], "MAIN FLOOR 1673.60 over the lower floor",
         "Day rooms and terraces stand on the lower floor's walls and the v 13.0 beam; the west part on dug ground."),
        ("lower", ["lower-plate", "loggia", "t-low"], "LOWER FLOOR 1670.00 on the ground",
         "Dug ground in the west; the east is a suspended slab on foundation walls over a crawl void."),
    ]
    drawn = set()
    s = 24.5
    for i, (key, ids, title, sub) in enumerate(panels):
        ox, oy = 60 + i * 790, 150

        sc = 24.5

        def X(u, v):
            return ox + (u + 7.0) * sc + 0 * v, oy + (v + 0.5) * sc

        def path(g, cls="", style=""):
            if g.is_empty:
                return
            if g.geom_type in ("MultiPolygon", "GeometryCollection", "MultiLineString"):
                for x in g.geoms:
                    path(x, cls, style)
                return
            if g.geom_type == "Polygon":
                d = "M" + " L".join(f"{X(*c)[0]:.1f},{X(*c)[1]:.1f}" for c in g.exterior.coords) + " Z"
                parts.append(f'<path class="{cls}" style="{style}" d="{d}"/>')
            elif g.geom_type == "LineString":
                pts = " ".join(f"{X(*c)[0]:.1f},{X(*c)[1]:.1f}" for c in g.coords)
                parts.append(f'<polyline class="{cls}" style="{style}" points="{pts}"/>')

        parts.append(f'<text class="lbl" style="font-size:15px" x="{ox}" y="{oy - 30}">{escape(title)}</text>')
        parts.append(f'<text class="note" x="{ox}" y="{oy - 12}">{escape(sub)}</text>')
        path(E.PARCEL.intersection(box(-7.0, -1.0, 22.5, 19.0)), "parcel")
        for gu in design_grid[0]:
            path(LineString([(gu, 0.2), (gu, 17.6)]), "grid", "stroke-dasharray:4 4")
            x, y = X(gu, 0.0)
            parts.append(f'<text class="tiny" x="{x:.1f}" y="{y - 4:.1f}" text-anchor="middle">{gu:g}</text>')
        for gv in design_grid[1]:
            path(LineString([(-6.5, gv), (22.0, gv)]), "grid", "stroke-dasharray:4 4")
            x, y = X(-6.6, gv)
            parts.append(f'<text class="tiny" x="{x:.1f}" y="{y + 3:.1f}" text-anchor="end">{gv:g}</text>')
        for sid in ids:
            for c, k in rep.cells.get(sid, []):
                path(c, "", f"fill:{COLOURS[k]};fill-opacity:.78;stroke:none")
        for sl in slabs(opt):
            if sl.id in ids:
                path(sl.geom, "", "fill:none;stroke:#1d2f3a;stroke-width:1.6")
                if sl.suspended is not None and not sl.suspended.is_empty:
                    path(sl.suspended, "", "fill:url(#hatch);fill-opacity:.55;stroke:#5d4a2c;stroke-dasharray:5 3")
        # bearing lines below (same list the check uses)
        for sl in slabs(opt):
            if sl.id == ids[0]:
                for ln in bearing_lines(opt, elements, sl):
                    path(ln, "", "fill:none;stroke:#1d2f3a;stroke-width:3.2;stroke-linecap:square")
        zc = opt.levels[key].z
        for e in elements:
            if e.kind == "column" and e.z_bot < zc - 0.2 and e.z_top >= zc - 0.1:
                path(box(e.geom.x - 0.25, e.geom.y - 0.25, e.geom.x + 0.25, e.geom.y + 0.25), "", "fill:#111;stroke:none")
                drawn.add(e.id)
            elif e.kind != "column" and abs(e.z_top - zc) <= 0.35 and e.geom.geom_type == "LineString":
                drawn.add(e.id)
        # numbers
        rows = [r for r in rep.slabs if r["id"] in ids]
        ty = oy + 18.5 * sc + 40
        parts.append(f'<text class="noteb" x="{ox}" y="{ty}">m² by support</text>')
        ty += 20
        for r in rows:
            bits = ", ".join(f"{k} {r[k]:.0f}" for k in ("ground", "wall", "span", "cantilever", "unsupported") if r[k] >= 0.5)
            parts.append(f'<text class="note" x="{ox}" y="{ty}">{escape(r["name"])} {r["area"]:.0f} m²: {escape(bits)}</text>')
            ty += 17
    # legend
    ly = H - 95
    lx = 70
    for k in ("ground", "wall", "span", "cantilever", "unsupported"):
        parts.append(f'<rect x="{lx}" y="{ly}" width="26" height="16" fill="{COLOURS[k]}" fill-opacity=".8"/>')
        parts.append(f'<text class="key" x="{lx + 34}" y="{ly + 13}">{escape(WORDS[k])}</text>')
        lx += 330
    parts.append(f'<rect x="70" y="{ly + 30}" width="26" height="16" fill="url(#hatch)" stroke="#5d4a2c"/>'
                 f'<text class="key" x="104" y="{ly + 43}">suspended slab over a ventilated crawl void (never filled)</text>')
    parts.append(f'<line x1="520" y1="{ly + 38}" x2="560" y2="{ly + 38}" stroke="#1d2f3a" stroke-width="3.2"/>'
                 f'<text class="key" x="570" y="{ly + 43}">bearing wall or beam of the storey below (the lines the check uses)</text>')
    parts.append(f'<rect x="1180" y="{ly + 31}" width="14" height="14" fill="#111"/>'
                 f'<text class="key" x="1202" y="{ly + 43}">column, continuous to its footing</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<style>{E.CSS}.key{{font:400 13px Helvetica,Arial,sans-serif;fill:#22343f}}</style>{E.DEFS}' + "".join(parts) + "</svg>")
    path_svg.write_text(svg)
    return drawn
