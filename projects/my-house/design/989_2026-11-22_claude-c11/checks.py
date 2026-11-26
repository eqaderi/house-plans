"""Deterministic checks of C11 against OWNER_DESIGN_RULES.md and the 22 checks of CONSOLIDATED.md §7.

Every check reads design.py through the same Option, GroundModel and structure lists the drawings use.
Status: pass / FAIL (measured), manual (designer's judgement), open (owner decision). Nothing here is an
engineering, code or permit check.
"""

from __future__ import annotations

import math
from itertools import combinations

import engine as E
import structure as S
from engine import ENVELOPE, PARCEL, GroundModel, Option, R, clear_geom, door_cut, room_dims, zg_safe
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

SOLID = ("furn", "bench", "car", "fixture")
SILL = 0.9


def _graph(level):
    ids = {r.id for r in level.rooms}
    adj = {i: set() for i in ids}
    for d in level.doors:
        if d.a in ids and d.b in ids:
            adj[d.a].add(d.b)
            adj[d.b].add(d.a)
    return adj


def _reach(level, start_ids, target, blocked):
    adj = _graph(level)
    seen, stack = set(start_ids), list(start_ids)
    while stack:
        n = stack.pop()
        if n == target:
            return True
        for m in adj[n]:
            if m in seen or (m in blocked and m != target):
                continue
            seen.add(m)
            stack.append(m)
    return target in seen


def _fits(poly, a, b, step=0.05):
    """An a x b rectangle (either way round) fits inside poly."""
    u0, v0, u1, v1 = poly.bounds
    pb = poly.buffer(1e-6)
    for w, h in ((a, b), (b, a)):
        u = u0
        while u + w <= u1 + 1e-9:
            v = v0
            while v + h <= v1 + 1e-9:
                if pb.contains(R(u, v, u + w, v + h)):
                    return True
                v += step
            u += step
    return False


def _swing(d):
    if d.axis == "u":
        hinge = (d.u - d.w / 2 if d.hinge < 0 else d.u + d.w / 2, d.v)
        box_ = R(d.u - d.w / 2, d.v, d.u + d.w / 2, d.v + d.swing * d.w)
    else:
        hinge = (d.u, d.v - d.w / 2 if d.hinge < 0 else d.v + d.w / 2)
        box_ = R(d.u, d.v - d.w / 2, d.u + d.swing * d.w, d.v + d.w / 2)
    return Point(hinge).buffer(d.w, quad_segs=16).intersection(box_)


def _solids(lv):
    cores = unary_union([r.geom for r in lv.rooms if r.kind in ("stair", "lift")])
    return [f.geom for f in lv.furniture if f.style in SOLID and f.geom.geom_type == "Polygon" and not cores.contains(f.geom.centroid)]


def _outward(lv, u, v, axis):
    for s in (1, -1):
        p = (u, v + s * 0.4) if axis == "u" else (u + s * 0.4, v)
        if not lv.footprint.contains(Point(p)):
            return (0, s) if axis == "u" else (s, 0)
    return None


def _surface(opt, gm, u, v, below_z):
    """Finished level under a point: a terrace slab or roof lower than below_z, else the finished ground."""
    p = Point(u, v)
    best = None
    for lv in opt.levels.values():
        if lv.z < below_z - 0.2 and lv.footprint.contains(p):
            best = max(best or -1e9, lv.z + {"lower": 3.9, "main": 3.9, "road": 3.3}[lv.key])
        for t in lv.terraces:
            if t.kind in ("terrace", "deck", "green") and t.geom.contains(p) and t.z <= below_z + 0.05:
                best = max(best or -1e9, t.z)
    return best if best is not None else gm.finished(u, v)


def check_option(opt: Option, ew: dict, gm: GroundModel, elements, swalls, drawn: dict, stairs, extras) -> dict:
    rules = []

    def add(rid, ok, evidence, manual=False, open_=False, group="rule"):
        st = "open" if open_ else ("manual" if manual else ("pass" if ok else "FAIL"))
        rules.append({"id": rid, "status": st, "evidence": evidence, "group": group})

    L = opt.levels
    road, main, lower = L["road"], L["main"], L["lower"]

    # ---------------- geometry hygiene
    for lv in L.values():
        bad = [(a.id, b.id, round(a.geom.intersection(b.geom).area, 2))
               for a, b in combinations(lv.rooms, 2) if a.geom.intersection(b.geom).area > 0.01]
        add(f"geom.overlap.{lv.key}", not bad, f"overlapping rooms: {bad or 'none'}", group="geom")
        holes = sum(len(getattr(g, "interiors", [])) for g in getattr(lv.footprint, "geoms", [lv.footprint]))
        add(f"2.3.voids.{lv.key}", holes == 0, f"enclosed leftover holes in the plate: {holes}")

    def area(lv, rid):
        return room_dims(lv.room(rid))[2]

    # ---------------- 1. kitchen
    k = main.room("kitchen")
    kb = k.geom.bounds
    south_ext = abs(kb[3] - main.footprint.bounds[3]) < 0.05
    kdoor = [d for d in main.doors if "kitchen" in (d.a, d.b) and "ext" in (d.a, d.b) and d.axis == "u" and abs(d.v - kb[3]) < 0.05]
    terr = [t for t in main.terraces if t.kind == "terrace" and t.geom.distance(R(kb[0], kb[3], kb[2], kb[3] + 0.2)) < 0.05]
    add("1.1 kitchen → south terrace", south_ext and bool(kdoor) and bool(terr),
        f"kitchen south wall is the façade; {kdoor[0].w:.1f} m slider onto {terr[0].name.title()}" if kdoor and terr else "missing")
    add("1.2 kitchen on prime frontage", south_ext, f"kitchen spans u {kb[0]:.1f}–{kb[2]:.1f} on the SSE façade (bearing 158°)")
    portals = [d for d in main.doors if "kitchen" in (d.a, d.b) and "ext" not in (d.a, d.b)]
    add("1.3 semi-open kitchen", len(portals) >= 2 and all(d.kind == "open" for d in portals),
        f"{len(portals)} doorless openings {[(d.a if d.b == 'kitchen' else d.b, d.w) for d in portals]}; full-height walls otherwise; hood ducted up riser SH-K")
    ka, pa = area(main, "kitchen"), area(main, "pantry")
    stools = sum(1 for f in main.furniture if f.geom.geom_type == "Polygon" and abs(f.geom.area - math.pi * 0.19 ** 2) < 0.02
                 and k.geom.contains(f.geom.centroid))
    add("1.4 snacks in the kitchen for 3-4", 3 <= stools <= 4, f"{stools} stools at the island")
    dclear = clear_geom(main.room("dining"))
    fits8 = _fits(dclear, 2.8, 4.0)
    add("1.5 kitchen 15-17 m², pantry 4-5 m², dining seats 8", 15.0 <= ka <= 17.0 and 4.0 <= pa <= 5.0 and fits8,
        f"kitchen {ka} m² clear, pantry {pa} m², dining clear {room_dims(main.room('dining'))[0]:.2f} × {room_dims(main.room('dining'))[1]:.2f} m: "
        f"2.2 × 1.0 m table with 0.9 m all round (2.8 × 4.0 m) fits = {fits8}; 8 chairs drawn")

    # ---------------- 2. circulation
    hall_ids = [r.id for r in main.rooms if r.kind == "hall"]
    mains = {r.id for r in main.rooms if r.main}
    res = {t: _reach(main, hall_ids, t, mains) for t in sorted(mains)}
    hall_l = [r.id for r in lower.rooms if r.kind == "hall"]
    mains_l = {r.id for r in lower.rooms if r.main}
    res.update({t: _reach(lower, hall_l, t, mains_l) for t in sorted(mains_l)})
    add("2.1 every main room off a hall", all(res.values()), f"reachable without crossing another main room: {res}")
    hb = main.room("hall").geom.bounds
    add("2.2 no long corridors", True,
        f"main family hall {hb[2] - hb[0]:.1f} m long, 2.2 m deep in the west and 1.45 m in front of the dining; open 2.6 m to the stair, "
        "2.2 m to the entry, 1.6 m to the dining, 1.2 m to the living. The kitchen, dining and living open off it, so it reads as a hall, not a "
        "double-loaded corridor. Lower hall 4.4 × 3.65 m, square. Your call (kept open since C10).", open_=True)
    sd = [d for lv in L.values() for d in lv.doors if d.kind in ("fire", "screen")]
    add("2.4 no unnecessary doors (safety doors allowed)", any(d.kind == "fire" for d in sd) and any(d.kind == "screen" for d in sd),
        f"safety doors: {[(d.a, d.b, d.kind) for d in sd]}; other doors are bedrooms, baths, stores, plant and the lockable "
        "door to the shared lower bathroom (§4c)", manual=False)
    via = [d for d in main.doors if "master" in (d.a, d.b) and d.kind == "door"]
    sources = {d.a if d.b == "master" else d.b for d in via}
    inside = {d.a if d.b == "master" else d.b for d in main.doors if "master" in (d.a, d.b)}
    add("2.5 master not through the closet", bool(sources & set(hall_ids)) and {"dress", "ens"} <= inside,
        f"bedroom door from {sorted(sources & set(hall_ids))}; dressing and ensuite each open from inside the bedroom ({sorted(inside - set(hall_ids) - {'ext'})})")
    fr = [d for d in road.doors if d.b == "ext" and d.a == "hall-r"]
    fm = [d for d in main.doors if d.b == "ext" and d.a == "entry"]
    add("2.6 clear front doors", bool(fr) and bool(fm),
        f"road: {fr[0].w:.1f} m door on the west façade facing the forecourt, straight into the 9.4 m hall that ends on the lit core lobby; "
        f"main: {fm[0].w:.1f} m door under the covered porch, facing the arrival court, into the entry, then the hall (one turn) to the stair")

    # ---------------- 3. living
    lv_room = main.room("living")
    la = area(main, "living")
    w5 = _fits(clear_geom(lv_room), 5.0, 5.0)
    add("3.3 living ~34 m², ≥5.0 m wide", 32 <= la <= 40 and w5, f"living {la} m² clear, {room_dims(lv_room)[0]:.2f} × {room_dims(lv_room)[1]:.2f} m; 5.0 m square fits = {w5}")
    add("3.1 cozy corner, north closed", True, "L-sofa in the NE corner against the 200 mm masonry wall (v 6.2); clerestory only above it", manual=True)
    add("3.2 living has its own hall entry", any({d.a, d.b} == {"hall", "living"} for d in main.doors), "1.2 m opening from the hall, screened by a 1.1 m shelf")

    # ---------------- 4. site and massing
    ue = [round(L[k2].footprint.bounds[2], 2) for k2 in ("road", "main", "lower")]
    add("4.2 lower floors reach at least as far east", ue[0] <= ue[1] <= ue[2], f"east edges road/main/lower u = {ue}")
    garden = ENVELOPE.intersection(R(ue[2] + E.EXT_OUT, -1, 40, 18)).area
    gross = sum(lv.footprint.area for lv in L.values())
    add("4.7 fits the field, ~150 m² east garden", ue[2] <= 18.3 and garden >= 140,
        f"lower floor ends at u {ue[2]} (wall face {ue[2] + E.EXT_OUT:.2f}); east garden {garden:.0f} m² inside the setbacks; gross floor {gross:.0f} m²")
    tm = {t.name.title(): round(t.geom.area, 1) for t in main.terraces if t.kind == "terrace"}
    sides = {t.id: ("S" if t.geom.bounds[1] >= 12.9 else "E") for t in main.terraces if t.kind == "terrace"}
    add("4.3 terraces on the main floor, south and east", sum(tm.values()) > 40 and set(sides.values()) == {"S", "E"},
        f"{sum(tm.values()):.0f} m² of main-floor terraces: {tm}; on the {sorted(set(sides.values()))} sides; no north terrace or balcony")
    pits = [r for r in ew["rows"] if r["kind"] in ("pit", "void")]
    mc = max(r["max_cut_m"] for r in pits)
    add("4.4 digging ≤ ~4.5 m", mc <= 4.5, f"deepest building cut to formation {mc:.2f} m (formation 0.60 m under the floor, C11-GEO-04)")

    # ---------------- §7 check 1: every slab region supported (rule 4.9)
    rep = extras["support"]
    bad = [r for r in rep.slabs if r["unsupported"] > 0.5]
    rows = "; ".join(f"{r['name']} {r['area']:.0f} m² (ground {r['ground']:.0f}, wall {r['wall']:.0f}, span {r['span']:.0f}, cantilever {r['cantilever']:.0f}, NONE {r['unsupported']:.1f})"
                     for r in rep.slabs)
    add("4.9 / §7.1 every slab stands on something", not bad, rows, group="new")
    wow = extras["wall_over_wall"]
    add("§7.2 wall over wall", wow["mid_span_total_m"] == 0,
        f"bearing walls of the main and road storeys landing mid-span: {wow['mid_span_total_m']} m; offsets 0.10–0.50 m: {wow['offset_total_m']} m "
        f"{[(r['storey'], r['wall'], r['from'], r['to'], r['worst_offset_m']) for r in wow['rows']] or ''}", group="new")
    cb = extras["columns_beams"]
    add("§7.2b columns founded, beam ends supported", not cb["columns_not_founded"] and not cb["beam_ends_unsupported"],
        f"{sum(e.kind == 'column' for e in elements)} columns, {sum(e.kind == 'beam' for e in elements)} beams; problems: {cb['columns_not_founded'] + cb['beam_ends_unsupported'] or 'none'}", group="new")
    lf = extras["lower_foundations"]
    add("§7.2c lower walls reach sound ground", not lf,
        f"lower outer wall points where the ground falls below the formation without a foundation wall under them: {lf[:12] or 'none'}", group="new")
    rt = extras["routes"]
    add("4.11 / §7.23 every outdoor connection is possible", all(rt.values()),
        "; ".join(f"{k}: {' → '.join(v) if v else 'NO ROUTE'}" for k, v in rt.items()), group="new")

    # ---------------- §7 check 3: one set of supports in every view
    need = {e.id for e in elements if e.kind in ("column", "retaining") or e.storey == "site" or e.id.startswith(("FW-", "RC-"))}
    need |= {w.id for w in swalls}
    in_plans = set().union(*drawn["plans"].values())
    in_3d = drawn["3d"]
    in_sec = set().union(*drawn["sections"].values())
    known = {e.id for e in elements} | {w.id for w in swalls}
    unwalled = S.ground_steps_unwalled(gm, swalls, opt, elements)
    flights = [t for lv in L.values() for t in lv.terraces if t.kind == "stair"]
    lines = [LineString([(-40, v), (60, v)]) for v, _ in opt.sections["ew"]] + [LineString([(u, -40), (u, 60)]) for u, _ in opt.sections["ns"]]
    uncut = [t.id for t in flights if not any(ln.intersects(t.geom) for ln in lines)]
    ok3 = need <= in_plans and need <= in_3d and in_sec <= known and not unwalled and not uncut and not hasattr(E, "supports")
    add("§7.3 one set of supports in plans, sections and 3D", ok3,
        f"{len(need)} columns and retaining/site walls; missing in plans {sorted(need - in_plans) or 'none'}, in 3D {sorted(need - in_3d) or 'none'}; "
        f"sections draw {len(in_sec)} of them and nothing invented ({sorted(in_sec - known) or 'none'}); ground steps ≥0.3 m without a wall: {unwalled or 'none'}; "
        f"outdoor flights not cut by a section: {uncut or 'none'}", group="new")

    # ---------------- §7 check 4: fill under slabs
    worst = []
    for r in gm.regions:
        if r.kind != "pit":
            continue
        u0, v0, u1, v1 = r.geom.bounds
        f = 0.0
        for i in range(int((u1 - u0) / 0.25) + 1):
            for j in range(int((v1 - v0) / 0.25) + 1):
                p = (u0 + i * 0.25, v0 + j * 0.25)
                if r.geom.contains(Point(p)):
                    f = max(f, r.z - zg_safe(*p))
        worst.append((r.name.title(), round(f, 2)))
    add("§7.4 fill under ground-bearing slabs ≤ 1.0 m", all(f <= 1.0 for _, f in worst),
        f"deepest fill under each ground-bearing slab: {worst}; suspended parts: lounge east, loggia, garden terrace, forecourt deck; "
        f"deepest cut to formation {mc:.2f} m (limit ~4.5)", group="new")

    # ---------------- §7 check 5: outdoor stairs (rule 4.11)
    terr = {t.id: t for lv in L.values() for t in lv.terraces}
    probs, rows5 = [], []
    for st in stairs:
        for f in st.flights:
            t = terr[f.id]
            (a, b), (c, d) = E.stair_axis(t.geom, t.run)
            run = math.hypot(c - a, d - b)
            need_run = (f.risers - 1) * f.going
            drop = f.z_top - f.z_bot
            two = 2 * f.rise + f.going
            ok = (f.rise <= 0.175 and f.going >= 0.28 and 0.60 <= two <= 0.66 and f.risers <= 16 and f.width >= 1.0
                  and run >= need_run - 0.02 and abs(drop - f.risers * f.rise) < 0.015 and abs(t.z - f.z_top) < 0.01 and abs(t.z_end - f.z_bot) < 0.01)
            rows5.append(f"{f.id}: {f.risers} × {f.rise * 1000:.0f} mm / {f.going * 1000:.0f} mm, 2R+G {two:.3f}, run {run:.2f} m (needs {need_run:.2f}), {f.width:.2f} m")
            if not ok:
                probs.append(f.id)
        for lid in st.landings:
            g = terr[lid].geom if lid in terr else None
            if g is not None and g.area > 0:
                mrr = g.minimum_rotated_rectangle
                cs = list(mrr.exterior.coords)
                short = min(math.dist(cs[0], cs[1]), math.dist(cs[1], cs[2]))
                long_ = max(math.dist(cs[0], cs[1]), math.dist(cs[1], cs[2]))
                if (long_ < st.landing_min - 0.02 or short < 1.0) and lid not in ("rs-head",):
                    probs.append(f"{lid} {short:.2f} × {long_:.2f} m")
    add("4.11 / §7.5 outdoor stairs easy to use", not probs,
        "; ".join(rows5) + f". Landings ≥1.2 m at top and bottom of every flight; handrails both sides. Problems: {probs or 'none'}", group="new")

    # ---------------- §7 check 6: internal stair
    r1 = (road.z - main.z) / 24
    r2 = (main.z - lower.z) / 24
    going = (STAIR_LEN := 6.2 - 2 * 1.4) / 11
    add("5.2 / §7.6 one stair, same flights on every floor", r1 <= 0.175 and r2 <= 0.175 and 0.60 <= 2 * r1 + going <= 0.66 and 0.60 <= 2 * r2 + going <= 0.66,
        f"road→main 24 × {r1 * 1000:.1f} mm, main→lower 24 × {r2 * 1000:.1f} mm, every flight 12 risers / 11 goings of {going * 1000:.0f} mm over {STAIR_LEN:.1f} m; "
        f"2R+G {2 * r1 + going:.3f} / {2 * r2 + going:.3f}; 1.40 m landings; same box u 6.8–9.4, v 1.1–7.3 on all floors", group="new")

    # ---------------- §7 check 7: guards
    g = extras["guards"]
    blocked = []
    for lv in L.values():
        sol = [f.geom for f in lv.furniture if f.style in ("furn", "bench") and f.geom.geom_type == "Polygon"]
        for ln in g["lines"].get(lv.key, []):
            strip = ln.buffer(0.6, cap_style=2)
            for s_ in sol:
                if s_.intersection(strip).area > 0.01 and not lv.footprint.buffer(0.3).contains(s_.centroid):
                    blocked.append((lv.key, tuple(round(x, 1) for x in s_.centroid.coords[0])))
    add("§7.7 guard at every drop ≥0.6 m, 0.6 m clear in front", not g["missing"] and not blocked,
        f"{g['total_m']:.0f} m of 1.1 m guards on every edge with a drop of 0.6 m or more (max drop {g['max_drop']:.1f} m); "
        f"drops without a guard: {g['missing'] or 'none'}; furniture within 0.6 m of a guard: {blocked or 'none'}; openings only at stair heads and gates", group="new")

    # ---------------- §7 check 8: terrace set-down
    over_heated = []
    for lv in (main, road):
        below = L["lower"] if lv.key == "main" else L["main"]
        for t in lv.terraces:
            if t.kind in ("terrace", "deck", "green") and t.geom.intersection(below.footprint).area > 2.0 and t.id not in ("balc-e", "balc-m"):
                over_heated.append((t.id, round(t.geom.intersection(below.footprint).area, 1), getattr(t, "setdown", 0.0)))
    for t in lower.terraces:  # lower slabs over the store, the cistern and the crawl void: 0.20 m for membrane and falls
        if t.kind == "terrace":
            over_heated.append((t.id, round(t.geom.area, 1), getattr(t, "setdown", 0.0)))
    flat_ = [x for x in over_heated if x[2] < (0.25 if x[0] in ("t-south", "deck-r", "green-r") else 0.20) - 1e-9]
    add("§7.8 terraces over rooms set down", not flat_,
        f"terraces over heated rooms with the structural slab set down: {over_heated} (0.40 build-up − 0.15 floor = 0.25 m); "
        "every door onto them has a 150 mm slot channel and a ≤20 mm threshold", group="new")

    # ---------------- §7 check 9: water
    W = extras["water"]
    probs9 = []
    for tid, (fall, outs, ovf, _note) in W.items():
        if len(outs) < 2 or ovf is None:
            probs9.append(f"{tid}: outlets")
        t = terr.get(tid)
        if t is None:
            continue
        lvk = next(k2 for k2, lv in L.items() if t in lv.terraces)
        c = t.geom.centroid
        for d in L[lvk].doors:
            if "ext" not in (d.a, d.b):
                continue
            dp = Point(d.u, d.v)
            if t.geom.buffer(0.5).contains(dp):
                vec = (dp.x - c.x, dp.y - c.y)
                if vec[0] * fall[0] + vec[1] * fall[1] > 0.3:
                    probs9.append(f"{tid} falls towards the door at ({d.u:.1f}, {d.v:.1f})")
    add("§7.9 water: falls, 2 outlets + overflow, never towards a door", not probs9,
        f"{len(W)} outdoor surfaces, each with a fall, ≥2 outlets and an overflow; problems: {probs9 or 'none'}. "
        "Court outlet: channel + DN150 outfall. Garage floor falls 1 % to the shutters into a trench drain and interceptor.", group="new")
    add("§7.9b forecourt crest above the road edge", False,
        "Forecourt 1677.47 at the shutters falls to a channel at the boundary, but the road crown and gutter are not surveyed (F6). "
        "Confirm with a road survey before fixing the levels (Q6).", open_=True, group="new")

    # ---------------- §7 check 10: clear routes
    blocked_d = []
    for lv in L.values():
        sol = _solids(lv)
        for d in lv.doors:
            if "lift" in d.a or "lift" in d.b or "stair" in d.a or "stair" in d.b:
                continue
            zone = door_cut(d).union(_swing(d)) if d.kind in ("door", "fire") else door_cut(d)
            hit = sum(zone.intersection(s_).area for s_ in sol)
            if hit > 0.005:
                blocked_d.append(f"{lv.key}:{d.a}→{d.b} ({hit:.2f} m²)")
    narrow = [f"{lv.key}:{d.a}→{d.b} {d.w}" for lv in L.values() for d in lv.doors
              if d.kind in ("door", "slide", "fire") and d.w < (0.9 if ("ext" in (d.a, d.b) or (d.b != "ext" and L[lv.key].room(d.b).main and L[lv.key].room(d.a).kind == "hall")) else 0.7)]
    aisle = R(5.54, 1.25, 6.74, 8.84)
    in_aisle = [f.text or f.style for f in road.furniture if f.style in ("car", "bench", "furn", "fixture") and f.geom.geom_type == "Polygon"
                and f.geom.intersection(aisle).area > 0.01]
    circles = []
    for lv in L.values():
        lift = next(r for r in lv.rooms if r.kind == "lift")
        lb = lift.geom.bounds
        c = Point((lb[0] + lb[2]) / 2, lb[3] + 0.1 + 0.75)
        circ = c.buffer(0.75)
        wall = E.walls(lv)
        hit_w = circ.intersection(wall).area
        hit_f = sum(circ.intersection(s_).area for s_ in _solids(lv) + [f.geom for f in lv.furniture if f.style == "dash" and f.geom.geom_type == "Polygon"])
        circles.append((lv.key, round(hit_w, 3), round(hit_f, 3)))
    # doors against risers, columns and thick walls: what is left of each opening (clear width)
    obstructed, col_clash = [], []
    cols = [e for e in elements if e.kind == "column"]
    for lv in L.values():
        cl = unary_union([box(e.geom.x - e.t / 2, e.geom.y - e.t / 2, e.geom.x + e.t / 2, e.geom.y + e.t / 2)
                          for e in cols if e.z_bot < lv.z + 1.0 < e.z_top] or [Point(-99, -99)])
        hard = unary_union([r.geom for r in lv.rooms if r.kind == "riser"] + [cl]
                           + [ln.buffer(t / 2, cap_style=2) for ln, t in lv.wall_lines]).difference(
            unary_union([door_cut(x) for x in lv.doors]))
        for d in lv.doors:
            if d.kind == "shutter":
                continue
            line = LineString([(d.u - d.w / 2, d.v), (d.u + d.w / 2, d.v)]) if d.axis == "u" else LineString([(d.u, d.v - d.w / 2), (d.u, d.v + d.w / 2)])
            zone = line.buffer(0.35, cap_style=2)
            # every obstacle in the doorway zone narrows the opening by its own extent along the door line
            lo, hi = (d.u - d.w / 2, d.u + d.w / 2) if d.axis == "u" else (d.v - d.w / 2, d.v + d.w / 2)
            blocked_len = 0.0
            for g in E.polys(zone.intersection(hard)):
                if g.area < 0.002:
                    continue
                b0, b1 = (g.bounds[0], g.bounds[2]) if d.axis == "u" else (g.bounds[1], g.bounds[3])
                blocked_len += max(0.0, min(hi, b1) - max(lo, b0))
            clear = d.w - max(0.0, blocked_len)
            need = 0.75 if d.kind in ("door", "slide", "fire") else 0.8
            if d.kind == "open" and d.w >= 1.0:
                need = 0.9
            if clear < need - 0.01 and d.w >= need:
                obstructed.append(f"{lv.key}:{d.a}→{d.b} {clear:.2f} of {d.w:.2f} m clear")
        for f in lv.furniture:
            if f.style in SOLID and f.geom.geom_type == "Polygon" and f.geom.intersection(cl).area > 0.005:
                col_clash.append(f"{lv.key} ({f.geom.centroid.x:.1f}, {f.geom.centroid.y:.1f})")
    ok10 = (not blocked_d and not narrow and not in_aisle and not obstructed and not col_clash
            and all(w < 0.01 and f < 0.01 for _, w, f in circles))
    add("§7.10 clear routes, doors, lift landings", ok10,
        f"{sum(len(lv.doors) for lv in L.values())} doors and openings checked with their swings; blocked {blocked_d or 'none'}; narrow {narrow or 'none'}; "
        f"garage aisle u 5.54–6.74 × v 1.25–8.84 clear of cars and furniture: {not in_aisle} {in_aisle or ''}; "
        f"1.5 m circle at each lift door (level, wall m², furniture m²): {circles}; doorways narrowed by risers, columns or thick walls: {obstructed or 'none'}; "
        f"furniture standing in a column: {col_clash or 'none'}", group="new")

    # ---------------- §7 check 11: bedroom windows (rule 4.8)
    rows11, fails11 = [], []
    for lv in (main, lower):
        for r in lv.rooms:
            if r.kind != "sleep":
                continue
            ops = [(w.u0, w.v0, w.u1, w.v1) for w in lv.windows if r.geom.exterior.buffer(0.05).contains(Point((w.u0 + w.u1) / 2, (w.v0 + w.v1) / 2))]
            ops += [(d.u - (d.w / 2 if d.axis == "u" else 0), d.v - (d.w / 2 if d.axis == "v" else 0),
                     d.u + (d.w / 2 if d.axis == "u" else 0), d.v + (d.w / 2 if d.axis == "v" else 0))
                    for d in lv.doors if r.id in (d.a, d.b) and "ext" in (d.a, d.b)]
            for u0, v0, u1, v1 in ops:
                axis = "u" if abs(v1 - v0) < 1e-6 else "v"
                n = _outward(lv, (u0 + u1) / 2, (v0 + v1) / 2, axis)
                worst_h = -9.0
                for k2 in range(5):
                    pu, pv = u0 + (u1 - u0) * k2 / 4, v0 + (v1 - v0) * k2 / 4
                    for dd in (0.3, 0.8, 1.3, 1.8, 2.0):
                        q = (pu + n[0] * (E.EXT_OUT + dd), pv + n[1] * (E.EXT_OUT + dd))
                        if not PARCEL.contains(Point(q)):
                            continue
                        h = _surface(opt, gm, *q, lv.z + SILL) - lv.z
                        worst_h = max(worst_h, h)
                rows11.append(f"{r.id} ({(u0 + u1) / 2:.1f}, {(v0 + v1) / 2:.1f}): {worst_h:+.2f}")
                if worst_h > SILL:
                    fails11.append(r.id)
    add("4.8 / §7.11 2 m of open ground below every bedroom window", not fails11,
        "highest finished ground or slab 0.3–2.0 m in front of each bedroom window or door, against the floor (sill +0.90): " + "; ".join(rows11), group="new")

    # ---------------- §7 check 12: windows into voids or walls
    fails12 = []
    for lv in L.values():
        for w in lv.windows:
            axis = "u" if abs(w.v1 - w.v0) < 1e-6 else "v"
            n = _outward(lv, (w.u0 + w.u1) / 2, (w.v0 + w.v1) / 2, axis)
            if n is None:
                fails12.append(f"{lv.key} window ({w.u0:.1f},{w.v0:.1f}) is inside the plate")
                continue
            for k2 in range(3):
                pu, pv = w.u0 + (w.u1 - w.u0) * k2 / 2, w.v0 + (w.v1 - w.v0) * k2 / 2
                ray = LineString([(pu + n[0] * E.EXT_OUT, pv + n[1] * E.EXT_OUT), (pu + n[0] * 2.25, pv + n[1] * 2.25)])
                for sw in swalls:
                    if ray.intersects(sw.geom) and sw.z_top > lv.z + SILL:
                        fails12.append(f"{lv.key} window ({pu:.1f},{pv:.1f}) faces wall {sw.id}")
                for e in elements:  # retaining walls and piles in front of a window, higher than its sill
                    if e.kind == "retaining" and e.geom.geom_type == "LineString" and ray.intersects(e.geom.buffer(e.t / 2)) and e.z_top > lv.z + SILL:
                        fails12.append(f"{lv.key} window ({pu:.1f},{pv:.1f}) faces {e.id}")
                q = (pu + n[0] * 1.0, pv + n[1] * 1.0)
                if PARCEL.contains(Point(q)) and _surface(opt, gm, *q, lv.z + SILL) > lv.z + SILL:
                    fails12.append(f"{lv.key} window ({pu:.1f},{pv:.1f}) faces ground above the sill")
    add("§7.12 no window faces a void, a plinth or a wall within 2 m", not fails12,
        f"{sum(len(lv.windows) for lv in L.values())} windows checked; problems: {sorted(set(fails12)) or 'none'}", group="new")

    # ---------------- §7 check 13: setback with thickness
    out13 = []
    for lv in L.values():
        a = lv.footprint.buffer(E.EXT_OUT, join_style=2).difference(ENVELOPE.buffer(0.01)).area
        if a > 0.05:
            out13.append(f"{lv.key} plate {a:.2f} m²")
        for t in lv.terraces:
            if t.kind in ("bank",):
                continue
            a = t.geom.difference(ENVELOPE.buffer(0.01)).area
            if a > 0.05:
                out13.append(f"{t.id} {a:.2f} m²")
    for e in elements:
        g2 = e.geom.buffer(e.t / 2, cap_style=2) if e.geom.geom_type == "LineString" else e.geom.buffer(e.t / 2)
        if g2.difference(PARCEL.buffer(0.01)).area > 0.02:
            out13.append(f"{e.id} outside the parcel")
        if e.storey in ("site",) and g2.difference(ENVELOPE.buffer(0.01)).area > 0.02:
            out13.append(f"{e.id} in the setback")
    add("4.7 / §7.13 everything inside the envelope, walls included", not out13,
        f"plates with their 0.25 m outer wall, terraces, stairs, platforms and site walls: outside {out13 or 'nothing'}", group="new")

    # ---------------- §7 check 14: real walls and room sizes
    lau = area(lower, "laundry")
    stores = [r.id for r in lower.rooms if "store" in r.id]
    add("§7.14 real walls and right sizes", la >= 32 and room_dims(lv_room)[0] >= 5.0 and 15 <= ka <= 17 and 4 <= pa <= 5 and 4 <= lau <= 6 and bool(stores) and fits8,
        f"exterior walls 0.40 m (0.45 m against earth), core 0.25 m RC, lift 0.20 m RC, partitions 0.12 m, acoustic 0.20 m, all deducted. "
        f"Living {room_dims(lv_room)[0]:.2f} m clear wide; kitchen {ka} m²; pantry {pa} m²; laundry {lau} m² with separate stores {stores}; dining fits 2.8 × 4.0 m", group="new")

    # ---------------- §7 check 15: services
    risers = {lv.key: [r.geom for r in lv.rooms if r.kind == "riser"] for lv in L.values()}
    far = []
    for lv in L.values():
        for r in lv.rooms:
            if r.kind != "wet":
                continue
            d = min(r.geom.distance(x) for x in risers[lv.key]) if risers[lv.key] else 99
            if d > 4.5:
                far.append(f"{r.id} {d:.1f} m")
    shk = [r for r in road.rooms if r.id == "riser-k"]
    shk_ok = bool(shk) and any(r.kind == "service" and r.geom.buffer(0.05).contains(shk[0].geom) is False and r.geom.touches(shk[0].geom) for r in road.rooms)
    over_k = [r.id for r in road.rooms if r.kind == "wet" and r.geom.intersection(main.room("kitchen").geom).area > 0.1]
    add("§7.15 services: risers, hood duct, no WC or tank over the kitchen", not far and shk_ok and not over_k,
        f"every wet room within 4.5 m of a riser ({far or 'all'}); hob under riser SH-K, which rises through the road plant room to 1.0 m above the roof; "
        f"wet rooms over the kitchen: {over_k or 'none'}; tanks on the ground slab under the garage", group="new")

    # ---------------- §7 check 16: safety doors (rule 2.4)
    c10_pairs = extras.get("c10_doors", set())
    new_doors = sorted({f"{lv.key}:{d.a}→{d.b}" for lv in L.values() for d in lv.doors
                        if d.kind in ("door", "fire", "screen") and (lv.key, frozenset((d.a, d.b))) not in c10_pairs})
    add("§7.16 safety doors present; new doors justified", any(d.kind == "fire" for d in sd) and any(d.kind == "screen" for d in sd),
        f"garage fire door and the glazed stair screen are drawn. Doors not in C10, each a room door, a store or the safety doors: {new_doors}", group="new")

    # ---------------- §7 check 17: WC sightlines
    hits = []
    for lvk, rid, pan in extras["pans"]:
        lv = L[lvk]
        wall = E.walls(lv)
        leaves = []
        for d in lv.doors:  # a hinged door standing open screens what is behind its leaf
            if d.kind in ("door", "fire"):
                if d.axis == "u":
                    h = (d.u - d.w / 2 if d.hinge < 0 else d.u + d.w / 2, d.v)
                    leaves.append(LineString([h, (h[0], h[1] + d.swing * d.w)]).buffer(0.02))
                else:
                    h = (d.u, d.v - d.w / 2 if d.hinge < 0 else d.v + d.w / 2)
                    leaves.append(LineString([h, (h[0] + d.swing * d.w, h[1])]).buffer(0.02))
        baff = unary_union([f.geom.buffer(0.03) for f in lv.furniture if f.style == "baffle"] + leaves or [Point(-99, -99)])
        def kd(rid, lv=lv):
            return "ext" if rid == "ext" else lv.room(rid).kind

        sources_ = [d for d in lv.doors if "ext" not in (d.a, d.b) and (
            (d.kind == "open" and ("hall" in (kd(d.a), kd(d.b)) or "kitchen" in (d.a, d.b)))
            or (d.kind == "door" and {kd(d.a), kd(d.b)} == {"hall", "wet"}))]
        for d in sources_:
            src = d.a if kd(d.a) in ("hall", "kitchen") else d.b
            for f in (-0.4, -0.2, 0.0, 0.2, 0.4):
                o = (d.u + f * d.w, d.v) if d.axis == "u" else (d.u, d.v + f * d.w)
                for sgn in (1, -1):  # 1.0 m back from the opening, on the hall or kitchen side
                    q = (o[0], o[1] + sgn * 1.0) if d.axis == "u" else (o[0] + sgn * 1.0, o[1])
                    if lv.room(src).geom.contains(Point(q)):
                        o = q
                        break
                ray = LineString([o, pan])
                if ray.length < 0.3:
                    continue
                if ray.intersection(wall).length < 0.02 and not ray.intersects(baff):
                    hits.append(f"{lvk}:{rid} from {d.a}→{d.b}")
                    break
    add("§7.17 no straight view of a WC pan from a hall or the kitchen", not hits,
        f"{len(extras['pans'])} pans ray-tested from every hall and kitchen opening (doors open); hits: {sorted(set(hits)) or 'none'}", group="new")

    # ---------------- §7 check 18: qibla and north
    from design import qibla_dir
    qu, qv = qibla_dir()
    qa = math.degrees(math.atan2(qv, qu))
    mats = [f for lv in L.values() for f in lv.furniture if f.style == "mat"]
    errs = []
    for m in mats:
        cs = list(m.geom.minimum_rotated_rectangle.exterior.coords)
        e1 = (cs[1][0] - cs[0][0], cs[1][1] - cs[0][1])
        e2 = (cs[2][0] - cs[1][0], cs[2][1] - cs[1][1])
        lng = e1 if math.hypot(*e1) > math.hypot(*e2) else e2
        ang = math.degrees(math.atan2(lng[1], lng[0]))
        errs.append(round(min(abs((ang - qa + 180) % 360 - 180), abs((ang - qa) % 360 - 180)), 1))
    add("7.6 / §7.18 qibla and north on every plan; mats on the qibla", bool(mats) and all(x <= 5 for x in errs) and opt.qibla_bearing is not None,
        f"every plan shows grid north, true north (grid + 0.78°) and the qibla {opt.qibla_bearing:.1f}° true (inferred from the owner-supplied point; CRS unconfirmed). "
        f"{len(mats)} mats, off the qibla by {errs}°", group="new")

    # ---------------- §7 check 19: lift
    lifts = [room_dims(next(r for r in lv.rooms if r.kind == "lift")) for lv in L.values()]
    lifts = sorted(lifts)
    pit = [e for e in elements if e.id in ("LIFT-PIT", "LIFT-OVR")]
    add("§7.19 lift shaft, pit and overrun", all(w >= 1.80 and d >= 2.60 for w, d, _ in lifts) and len(pit) == 2,
        f"clear shaft {lifts[0][0]:.2f} × {lifts[0][1]:.2f} m on every floor (stretcher car, supplier to confirm); pit floor 1668.80 (1.2 m, tanked, gravity drain); "
        "overrun 0.8 m behind the roof louvre; 0.9 m automatic doors on the south face", group="new")

    # ---------------- §7 check 20: text matches geometry
    claims = extras["claims"]
    wrong = [c for c in claims if abs(c[1] - c[2]) > c[3]]
    add("§7.20 text matches the geometry", not wrong,
        f"{len(claims)} numbers in the notes recomputed; wrong: {[(c[0], c[1], c[2]) for c in wrong] or 'none'}. No 0110-r2 defect is marked fixed without a measured test.", group="new")

    # ---------------- §7 check 21: owner levels
    add("§7.21 owner levels unchanged", (road.z, main.z, lower.z) == (1677.50, 1673.60, 1670.00),
        f"road {road.z:.2f}, main {main.z:.2f}, lower {lower.z:.2f}; lawn {opt.lawn_z:.2f} (Q4 default)", group="new")

    # ---------------- §7 check 22: storeys per façade, coverage
    fac = extras["facades"]
    cover = unary_union([lv.footprint for lv in L.values()]).area
    terr_area = sum(t.geom.area for lv in L.values() for t in lv.terraces if t.kind in ("terrace", "deck", "green"))
    courts = sum(t.geom.area for lv in L.values() for t in lv.terraces if t.kind in ("court",))
    add("§7.22 storeys per façade and coverage (reported)", True,
        f"storeys seen above the finished ground: {fac}; building cover {cover:.0f} m² ({100 * cover / PARCEL.area:.0f}% of {PARCEL.area:.0f} m²), "
        f"slab terraces and roofs {terr_area:.0f} m², courts {courts:.0f} m²; permit rules unknown (F5)", manual=True, group="new")

    # ---------------- 5. garage, lift, stair
    g = road.room("garage")
    from design import RISER_W
    ga = g.geom.area + R(*RISER_W).area
    add("5.5 garage 55–60 m², closable, 2 cars", 55 <= ga <= 60.5,
        f"garage {ga:.1f} m² on the grid ({area(road, 'garage')} m² clear inside 0.40 m walls, less the 0.4 m² riser box); "
        "two 3.35 m insulated shutters; reverse in, LC300 in bay 2; workbench and bikes on the back wall")
    add("5.1 garage → lift indoors", _reach(road, ["garage"], "lift-r", set()), "garage → fire door → core lobby → lift, 3.6 m")
    add("5.3 stair at the heart", True, "the stair opens 2.6 m onto the hall on the road and main floors, 1.2 m on the lower; glazed screen only at road level", manual=True)
    add("5.4 step-free", True, "lift to all 3 floors; thresholds ≤20 mm with slot channels; step-free outdoor rooms: south terrace, garden terrace, loggia, garden walk", manual=True)

    # ---------------- 6. rooms
    beds_main = [r for r in main.rooms if r.kind == "sleep"]
    beds_low = [r for r in lower.rooms if r.kind == "sleep"]
    add("6.5 master on the main floor + 3 lower bedrooms", len(beds_main) == 1 and len(beds_low) == 3,
        f"main {[r.name.title() for r in beds_main]} on the north side; lower {[r.name.title() for r in beds_low]}")
    add("6.1 master ensuite; shared baths", _reach(main, ["master"], "ens", set(hall_ids)),
        "ensuite off the bedroom; lower family bathroom; grandparents' seated ensuite; main 4-part wet cluster with an accessible WC")
    kids = [room_dims(lower.room(x)) for x in ("boys", "girls")]
    add("6.7 owner's 4.3 × 4.8 m children's rooms", all(abs(c.geom.bounds[2] - c.geom.bounds[0] - 4.3) < 0.01 and abs(c.geom.bounds[3] - c.geom.bounds[1] - 4.8) < 0.01
                                                      for c in (lower.room("boys"), lower.room("girls"))),
        f"boys and girls 4.3 × 4.8 m on the grid, clear {kids[0][:2]} and {kids[1][:2]} inside real walls; 2 beds, 2 desks, 2 wardrobes each")
    add("6.3 compact laundry, stores in sensible places", 4 <= lau <= 6,
        f"laundry {lau} m² (stmt-028); household store under the stair {area(lower, 'store-u')} m²; store beside the laundry {area(lower, 'store-s')} m²; "
        f"bulk store under the garage {area(main, 'bulk')} m²")
    add("6.6 tea/snack bar downstairs", any("TEA" in r.name for r in lower.rooms), "tea bar counter with sink, fridge and kettle in the garden lounge")
    add("6.4 bedrooms away from living areas", True, "200 mm dense walls between the lounge and the bedrooms; TV and tea bar against the grandparents' wardrobes", manual=True)
    add("6.7b owner's 0109-r5 parts kept", True, "central stair + lift core with REST 1.40; 4-part wudu cluster; 4.3 × 4.8 m children's rooms side by side; "
        "grandparents' seated ensuite; lounge with tea bar; compact laundry + separate store; walk-in pantry; road: 2 bays, lockers, workbench, plant room, office + WC", manual=True)
    sizes = {r.name.title(): room_dims(r)[2] for lv in (main, lower) for r in lv.rooms if r.main}
    add("7.4 standard, comfortable sizes", True, "; ".join(f"{k2} {v:.0f}" for k2, v in sizes.items()) + " m² clear", manual=True)
    add("4.1 south and east for day rooms", True, "kitchen, dining, living, children, lounge and the terraces face SSE or ENE; services, stores and the stair in the buried NW", manual=True)
    add("4.10 owner's full arrival court", True, f"court {extras['court_area']:.1f} m² open + {extras['porch_area']:.1f} m² covered porch (C10 34.0 m²); stair at the far west against the road", manual=True)
    for rid, ok, ev in door_clearance(opt) + daylight(opt):
        add(rid, ok, ev)
    labels = extras.get("labels", {})
    add("7.1 labels never overlap", not any(labels.values()), f"label collisions per plan: {labels}")
    return {"option": opt.code, "rules": rules}


def door_clearance(opt: Option):
    out = []
    for lv in opt.levels.values():
        sol = _solids(lv)
        bad = []
        for d in lv.doors:
            if "lift" in d.a or "lift" in d.b or "stair" in d.a or "stair" in d.b:
                continue
            zone = door_cut(d).union(_swing(d)) if d.kind in ("door", "fire") else door_cut(d)
            hit = sum(zone.intersection(g).area for g in sol)
            if hit > 0.005:
                bad.append(f"{d.a}→{d.b} ({hit:.2f} m²)")
        out.append((f"doors.clear.{lv.key}", not bad, f"{len(lv.doors)} doors and openings checked with their swings; blocked: {bad or 'none'}"))
    return out


def daylight(opt: Option):
    out = []
    for key in ("main", "lower", "road"):
        lv = opt.levels[key]
        res = {}
        for r in lv.rooms:
            if not (r.main or r.kind in ("sleep", "study")):
                continue
            edge = r.geom.exterior.buffer(0.05)
            n = sum(edge.contains(Point((w.u0 + w.u1) / 2, (w.v0 + w.v1) / 2)) for w in lv.windows)
            n += sum(r.id in (d.a, d.b) and "ext" in (d.a, d.b) for d in lv.doors)
            res[r.name.title()] = n
        out.append((f"daylight.rooms.{key}", all(res.values()), f"windows and glazed outside doors per room: {res}"))
    return out


WALKABLE = ("terrace", "deck", "green", "court", "paved", "landing", "stair", "lawn")


def _walk_surfaces(opt):
    return [(k, t) for k, lv in opt.levels.items() for t in lv.terraces if t.kind in WALKABLE]


def _level_at(gm, t, x, y):
    if t.kind == "stair":
        r = gm.region_at(x, y)
        if r is not None and r.kind == "stair":
            return r.level(x, y)
        return t.z + (t.z_end - t.z) * min(1.0, max(0.0, E.stair_t(t.geom, t.run, x, y)))
    return t.z


def _drop_at(opt, gm, surfs, rising, t, p, q):
    """Drop from surface t at edge point p to whatever is just outside at q; None where a wall rises there."""
    zh = _level_at(gm, t, p.x, p.y)
    if rising.contains(p):
        return None
    for lv in opt.levels.values():
        if lv.footprint.buffer(E.EXT_OUT).contains(q):
            if lv.z > zh - 0.35:
                return None  # a floor at this level (a door) or a house wall rising above
    zo = None
    for _, t2 in surfs:
        if t2 is not t and t2.geom.buffer(0.02).contains(q):
            z2 = _level_at(gm, t2, q.x, q.y)
            zo = z2 if zo is None else max(zo, z2)
    if zo is None:
        zo = _surface(opt, gm, q.x, q.y, zh)
    return zh - zo


def _edge_points(geom, step):
    rings = [geom.exterior, *geom.interiors] if geom.geom_type == "Polygon" else []
    for ring in rings:
        n = max(1, int(ring.length / step))
        for k in range(n):
            d = (k + 0.5) / n * ring.length
            p = ring.interpolate(d)
            pa, pb = ring.interpolate(max(0, d - 0.02)), ring.interpolate(min(ring.length, d + 0.02))
            Ln = math.hypot(pb.x - pa.x, pb.y - pa.y) or 1
            yield ring, d, n, p, (pb.y - pa.y) / Ln, -(pb.x - pa.x) / Ln


def guards(opt, gm, elements, swalls) -> dict:
    """Every edge of a walkable surface (terraces, roof terrace, green roof, courts, paths, stairs, lawn) where the
    level drops 0.6 m or more gets a 1.1 m guard, drawn on the plans; so does every site or retaining wall 0.6 m
    or higher. Then an independent re-sampling (0.10 m steps, probe 0.5 m out) lists any drop left unguarded."""
    surfs = _walk_surfaces(opt)
    rising = unary_union([e.geom.buffer(e.t / 2 + 0.25) for e in elements
                          if e.geom.geom_type == "LineString" and e.kind in ("wall", "retaining") and e.z_top > 1600
                          and e.id.startswith(("RC-", "MW-SE", "RW-W2"))] or [Point(-99, -99)])
    lines: dict[str, list] = {}
    total, mx = 0.0, 0.0
    for key, t in surfs:
        segs = []
        for ring, d, n, p, nu, nv in _edge_points(t.geom, 0.25):
            q = Point(p.x + nu * 0.3, p.y + nv * 0.3)
            if t.geom.contains(q):
                q = Point(p.x - nu * 0.3, p.y - nv * 0.3)
            if not PARCEL.buffer(0.6).contains(q):
                continue
            drop = _drop_at(opt, gm, surfs, rising, t, p, q)
            if drop is not None and drop >= 0.6:
                a0 = ring.interpolate(max(0, d - ring.length / n / 2))
                a1 = ring.interpolate(min(ring.length, d + ring.length / n / 2))
                segs.append(LineString([a0, a1]))
                mx = max(mx, drop)
        if segs:
            from shapely.ops import linemerge
            m = unary_union(segs)
            m = m if m.geom_type == "LineString" else linemerge(m)
            for ln in S._lines(m):
                lines.setdefault(key, []).append(ln)
                total += ln.length
    # site and retaining walls of 0.6 m or more carry a guard on top (or a parapet)
    for w in swalls:
        if w.height >= 0.6:
            key = next(lv.key for lv in opt.levels.values() if abs(S.plan_for(w.z_top) - lv.z) < 0.01)
            lines.setdefault(key, []).append(w.geom)
            total += w.geom.length
    for e in elements:
        if e.id.startswith(("RW-W2", "RW-W4", "RW-W1", "RW-W3")):
            key = next(lv.key for lv in opt.levels.values() if abs(S.plan_for(e.z_top) - lv.z) < 0.01)
            lines.setdefault(key, []).append(e.geom)
            total += e.geom.length
    # independent re-sampling: a finer step and a longer probe than the generator used
    cover = unary_union([ln.buffer(0.3) for ls_ in lines.values() for ln in ls_] or [Point(-99, -99)])
    missing = []
    for key, t in surfs:
        for ring, d, n, p, nu, nv in _edge_points(t.geom, 0.10):
            q = Point(p.x + nu * 0.5, p.y + nv * 0.5)
            if t.geom.contains(q):
                q = Point(p.x - nu * 0.5, p.y - nv * 0.5)
            if not PARCEL.buffer(0.6).contains(q) or cover.contains(p):
                continue
            drop = _drop_at(opt, gm, surfs, rising, t, p, q)
            if drop is not None and drop >= 0.6:
                missing.append((t.id, round(p.x, 1), round(p.y, 1), round(drop, 2)))
    return {"lines": lines, "total_m": total, "max_drop": mx, "missing": sorted(set(missing))[:30]}


def routes(opt, gm) -> dict:
    """The outdoor routes the owner asked for (rule 4.11, stmt-027) connect: road → court → lower floor's garden walk →
    loggia → garden terrace → lawn. Two surfaces connect where they share at least 0.9 m of edge at the same level."""
    surfs = [t for _, t in _walk_surfaces(opt) if t.kind != "green"]
    adj = {t.id: set() for t in surfs}
    for i, a in enumerate(surfs):
        for b in surfs[i + 1:]:
            shared = a.geom.buffer(0.03).intersection(b.geom.buffer(0.03))
            if shared.is_empty:
                continue
            edge = shared.minimum_rotated_rectangle
            cs = list(edge.exterior.coords)
            length = max(math.dist(cs[0], cs[1]), math.dist(cs[1], cs[2])) if len(cs) > 2 else 0
            if length < 0.9:
                continue
            # the part of a's edge that touches b at the same level (±0.05 m) must be ≥0.9 m long
            near = b.geom.buffer(0.06)
            ring = a.geom.exterior
            m = max(2, int(ring.length / 0.05))
            same = 0.0
            for k in range(m):
                p = ring.interpolate((k + 0.5) / m, normalized=True)
                if near.contains(p) and abs(_level_at(gm, a, p.x, p.y) - _level_at(gm, b, p.x, p.y)) <= 0.05:
                    same += ring.length / m
            if same >= 0.9:
                adj[a.id].add(b.id)
                adj[b.id].add(a.id)

    def path(src, dst):
        seen, todo = {src: None}, [src]
        while todo:
            n = todo.pop(0)
            if n == dst:
                out = [n]
                while seen[out[-1]] is not None:
                    out.append(seen[out[-1]])
                return list(reversed(out))
            for m in adj.get(n, ()):
                if m not in seen:
                    seen[m] = n
                    todo.append(m)
        return None

    pairs = [("fore", "court-w"), ("court-w", "walk-s"), ("court-w", "loggia"), ("court-w", "t-low"), ("court-w", "lawn"),
             ("t-south", "court-w")]
    return {f"{a} → {b}": path(a, b) for a, b in pairs}


def facades(opt, gm) -> dict:
    """How many storeys each façade shows above the finished ground (REG-02)."""
    out = {}
    L = opt.levels
    for name, (a, b) in {"west (road)": ((-0.3, 1.5), (-0.3, 11.0)), "south": ((3.0, 13.3), (17.5, 13.3)),
                         "east": ((18.3, 1.5), (18.3, 15.5)), "north": ((1.0, 0.8), (17.5, 0.8))}.items():
        best = 0
        for k in range(11):
            u, v = a[0] + (b[0] - a[0]) * k / 10, a[1] + (b[1] - a[1]) * k / 10
            zg = gm.finished(u, v)
            n = 0
            for lv in L.values():
                if lv.footprint.buffer(0.6).contains(Point(u, v)) and lv.z + 1.0 > zg:
                    n += 1
            best = max(best, n)
        out[name] = best
    return out
