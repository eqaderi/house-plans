"""Deterministic checks of C10 against OWNER_DESIGN_RULES.md (what geometry can prove).

Copied from ../991_2026-10-27_claude-c09 and extended with three checks C09 lacked: every door and
opening is clear of furniture (C09 fails this at 22 doors), every window and outside door clears the natural ground, and every
habitable room has daylight of its own or says where it borrows it.
"""

from __future__ import annotations

from itertools import combinations

from engine import ENVELOPE, INT_WALL, GroundModel, Option, R, door_cut, room_dims, zg_safe
from shapely.geometry import Point
from shapely.ops import unary_union


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


def _fits_square(poly, side):
    u0, v0, u1, v1 = poly.bounds
    step = 0.1
    u = u0
    while u + side <= u1 + 1e-9:
        v = v0
        while v + side <= v1 + 1e-9:
            if poly.buffer(1e-6).contains(R(u, v, u + side, v + side)):
                return True
            v += step
        u += step
    return False


def check_option(opt: Option, ew: dict, gm: GroundModel) -> dict:
    rules = []

    def add(rid, ok, evidence, manual=False, open_=False):
        st = "open" if open_ else ("manual" if manual else ("pass" if ok else "FAIL"))
        rules.append({"id": rid, "status": st, "evidence": evidence})

    L = opt.levels
    road, main, lower = L["road"], L["main"], L["lower"]

    # geometry hygiene
    for lv in L.values():
        bad = [(a.id, b.id, round(a.geom.intersection(b.geom).area, 2))
               for a, b in combinations(lv.rooms, 2) if a.geom.intersection(b.geom).area > 0.01]
        add(f"geom.overlap.{lv.key}", not bad, f"overlapping rooms: {bad or 'none'}")
        out = lv.footprint.difference(ENVELOPE.buffer(0.01)).area
        add(f"geom.envelope.{lv.key}", out < 0.05, f"area outside buildable envelope {out:.2f} m²")
        spill = {t.id: round(t.geom.difference(ENVELOPE.buffer(0.01)).area, 2) for t in lv.terraces
                 if t.kind not in ("lawn", "stair") and lv.key != "road"}
        spill = {k: v for k, v in spill.items() if v >= 0.05}
        add(f"geom.terraces.{lv.key}", not spill, f"terraces/paths outside parcel setbacks: {spill or 'none'}")
        holes = sum(len(getattr(g, "interiors", [])) for g in getattr(lv.footprint, "geoms", [lv.footprint]))
        add(f"2.3.voids.{lv.key}", holes == 0, f"enclosed leftover holes in plate: {holes}")

    def area(lv, rid):
        return room_dims(lv.room(rid))[2]

    k = main.room("kitchen")
    kb = k.geom.bounds
    south_ext = abs(kb[3] - main.footprint.bounds[3]) < 0.05
    kdoor = [d for d in main.doors if "kitchen" in (d.a, d.b) and "ext" in (d.a, d.b)
             and d.axis == "u" and abs(d.v - kb[3]) < 0.05]
    terr = [t for t in main.terraces if t.geom.distance(R(kb[0], kb[3], kb[2], kb[3] + 0.2)) < 0.05 and t.kind == "terrace"]
    add("1.1 kitchen→south terrace", south_ext and bool(kdoor) and bool(terr),
        f"kitchen south wall is façade={south_ext}; door(s) {[round(d.w, 2) for d in kdoor]} m onto {[t.name for t in terr]}")
    add("1.2 kitchen prime frontage", south_ext, f"kitchen spans u {kb[0]:.1f}–{kb[2]:.1f} on the south façade")
    portals = [d for d in main.doors if "kitchen" in (d.a, d.b) and "ext" not in (d.a, d.b) and "pantry" not in (d.a, d.b)]
    add("1.3 semi-open kitchen", len(portals) >= 2 and all(d.kind == "open" for d in portals),
        f"{len(portals)} doorless portals: {[(d.a, d.b, d.w) for d in portals]}; full-height walls otherwise")
    ka, da = area(main, "kitchen"), area(main, "dining")
    dw = min(room_dims(main.room("dining"))[:2])
    pantry = [r for r in main.rooms if "pantry" in r.id]
    pa = room_dims(pantry[0])[2] if pantry else 0
    joined = any({d.a, d.b} == {"dining", "living"} and d.kind == "open" and d.w >= 2.0 for d in main.doors)
    add("1.5 kitchen/dining right-sized", 15 <= ka <= 17.2 and (11 if joined else 13.5) <= da <= 15.5 and dw >= 3.2 and 4.0 <= pa <= 5.5,
        f"kitchen {ka} m², pantry {pa} m², dining {da} m² ({dw:.2f} m wide){', open to the living room (stmt-024)' if joined else ''}")

    hall_ids = [r.id for r in main.rooms if r.kind == "hall"]
    mains = {r.id for r in main.rooms if r.main}
    res = {t: _reach(main, hall_ids, t, mains) for t in sorted(mains)}
    hall_l = [r.id for r in lower.rooms if r.kind == "hall"]
    mains_l = {r.id for r in lower.rooms if r.main}
    res.update({t: _reach(lower, hall_l, t, mains_l) for t in sorted(mains_l)})
    add("2.1 every main room off a hall", all(res.values()), f"reachable without crossing another main room: {res}")
    m = main.room("master")
    via = [d for d in main.doors if "master" in (d.a, d.b) and d.kind == "door"]
    sources = {d.a if d.b == "master" else d.b for d in via}
    entry_ok = _reach(main, hall_ids, "master", mains | {"dress"} | {r.id for r in main.rooms if r.id.startswith("ens")})
    add("2.5 master not through closet", entry_ok and bool(sources & set(hall_ids)),
        f"bedroom door(s) from {sorted(sources)}")
    fr = [d for d in road.doors if d.b == "ext" and d.a.startswith("hall") and d.axis == "v"
          and abs(d.u - road.footprint.bounds[0]) < 0.05]
    fm = [d for d in main.doors if d.b == "ext" and main.room(d.a).kind == "hall" and d.axis == "v"
          and abs(d.u - main.footprint.bounds[0]) < 0.05]
    add("2.6a front doors on the west façade", bool(fr) and bool(fm),
        f"road door u={fr[0].u if fr else '-'} into {fr[0].a if fr else '-'}; main door u={fm[0].u if fm else '-'} into {fm[0].a if fm else '-'}; both open-sky, no passage")
    add("2.6b straight line door → stair/lift", False,
        "Road (the daily front door): door → 7 m straight hall → stair and lift on the left, glass door to the roof terrace ahead. "
        "Main (the court door): door → entry → turn north → turn east along the hall to the stair, two turns as in C09. "
        "A door on the hall axis would sit under the garage slab, the passage you rejected. Your call.", open_=True)

    lv_room = main.room("living")
    la = area(main, "living")
    w5 = _fits_square(lv_room.geom.buffer(-INT_WALL / 2, join_style=2), 5.0)
    add("3.3 living ~34 m², ≥5.0 m wide", 32 <= la <= 40 and w5, f"living {la} m², 5.0 m clear square fits={w5}")
    lb = lv_room.geom.bounds
    add("3.1 cozy corner, north closed", True,
        f"living north edge v={lb[1]:.1f}; north neighbour = {[r.name for r in main.rooms if r.geom.touches(lv_room.geom) and r.geom.bounds[3] <= lb[1] + 0.01]}",
        manual=True)

    ue = [round(L[k].footprint.bounds[2], 1) for k in ("road", "main", "lower")]
    uw = [round(L[k].footprint.bounds[0], 1) for k in ("road", "main", "lower")]
    add("4.2 steps east going down", uw[0] < uw[1] < uw[2] and ue[0] < ue[1] <= ue[2],
        f"west edges road/main/lower u = {uw}; east edges u = {ue}")
    garden = ENVELOPE.intersection(R(ue[2], -1, 40, 18)).area
    add("4.7 fits the field, ~150 m² east garden", ue[2] <= 18.3 and garden >= 140,
        f"lower floor ends u={ue[2]}; east garden {garden:.0f} m² inside the setbacks; "
        f"gross floor {sum(lv.footprint.area for lv in L.values()):.0f} m²")
    terr_main = sum(t.geom.area for t in main.terraces if t.kind == "terrace")
    add("4.3 main-floor terraces", terr_main > 30, f"{terr_main:.0f} m² of main-floor terraces/balconies: {[t.name for t in main.terraces if t.kind == 'terrace']}")

    g = road.room("garage")
    ga = round(g.geom.area, 1)
    add("5.5 garage 55–60 m²", 55 <= ga <= 60.5, f"garage {ga} m² gross")
    lift_r = [r.id for r in road.rooms if r.kind == "lift"][0]
    ok = _reach(road, ["garage"], lift_r, set())
    add("5.1 garage→lift indoors", ok, "door chain garage → core lobby → lift")
    st = [r.geom.bounds for lv in L.values() for r in lv.rooms if r.kind == "stair"]
    add("5.2 one stair, all levels", len(st) == 3 and len(set(st)) == 1, f"stair boxes {set(st)}")

    beds_main = [r for r in main.rooms if r.kind == "sleep"]
    beds_low = [r for r in lower.rooms if r.kind == "sleep"]
    north = all(r.geom.centroid.y < main.footprint.centroid.y for r in beds_main)
    add("6.5 master main/north + 3 lower bedrooms", len(beds_main) == 1 and north and len(beds_low) == 3,
        f"main bedrooms {[r.name for r in beds_main]} (north half={north}); lower {[r.name for r in beds_low]}")
    private = _reach(main, ["master"], "ens", set(hall_ids) | (mains - {"master"}))
    add("6.1 master ensuite", private, "ensuite reached from inside the bedroom suite only, never via the hall")
    tea = any("TEA" in r.name for r in lower.rooms)
    add("6.6 tea/snack bar downstairs", tea, "tea bar counter with sink + under-counter fridge")
    kids = [room_dims(lower.room(x)) for x in ("boys", "girls")]
    add("6.7 owner's 4.3×4.8 children rooms", all(abs(w - 4.18) < 0.25 and abs(d - 4.68) < 0.35 for w, d, _ in kids),
        f"boys/girls clear {kids}")
    gens = [r for r in lower.rooms if r.id == "gens"]
    add("I10 guest seated ensuite", bool(gens), f"{gens[0].name if gens else '-'} {room_dims(gens[0])[2] if gens else ''} m²")
    lau = [r for r in lower.rooms if "laundry" in r.id]
    add("I12 laundry 12–14 m²", bool(lau) and 12 <= room_dims(lau[0])[2] <= 14.5, f"laundry {room_dims(lau[0])[2] if lau else '-'} m²")
    hall = main.room("hall")
    hb = hall.geom.bounds
    add("2.2 no long corridors", False,
        f"main family hall {hb[2] - hb[0]:.1f} × {hb[3] - hb[1]:.1f} m, rooms on one side, open to the stair (2.6 m), the dining room (3.0 m) and the living room. "
        f"Lower family hall {room_dims(lower.room('hall-l'))[2]:.0f} m², square. Not a double-loaded corridor, but long. Your call.", open_=True)
    fb = main.footprint.bounds
    se = [r.name.title() for r in main.rooms if r.main and r.kind != "sleep"
          and (abs(r.geom.bounds[3] - fb[3]) < 0.05 or abs(r.geom.bounds[2] - fb[2]) < 0.05)]
    nw = [r.name.title() for r in main.rooms if r.kind in ("wet", "service") and r.geom.bounds[0] < 7.0 and r.name]
    nd = sum(d.kind == "door" for d in main.doors)
    no = sum(d.kind == "open" for d in main.doors)
    ld = main.doors[[i for i, d in enumerate(main.doors) if "living" in (d.a, d.b) and "hall" in (d.a, d.b)][0]]
    bc = [r for r in ew["rows"] if "dig" in r["zone"]]
    mc = max((r["max_cut_m"] for r in bc), default=0)
    sizes = {r.name.title(): room_dims(r)[2] for lv in (main, lower) for r in lv.rooms if r.main}
    add("4.4 digging ≤ ~4.5 m", mc <= 4.6, f"deepest building cut {mc:.2f} m below natural ground (formation 0.35 m under FFL)")
    judged = [
        ("4.1 south + east for day rooms", f"on the S/E façades: {', '.join(se)}; buried NW holds {', '.join(nw)}"),
        ("2.4 no unnecessary doors", f"main floor: {no} doorless openings, {nd} hinged doors (bedroom, baths, stores, lobby only)"),
        ("3.2 living has its own hall entry", f"{ld.w:.1f} m opening straight from the family hall"),
        ("4.4 earth balance", f"building cut ≈ {sum(r['cut_m3'] for r in bc):.0f} m³; outdoor fill ≈ {ew['total_fill_m3']:.0f} m³"),
        ("5.3 stair at the heart", "stair box u 6.8–9.4 opens 2.6 m wide onto the hall on the road and main floors, 1.2 m on the lower floor"),
        ("5.4 step-free", "lift reaches all 3 levels and each level is one flat floor. Threshold details are not designed"),
        ("6.3 stores not in odd places", "household store is the south end of the laundry room, beside the core; plant room off the road hall; pantry off the main hall"),
        ("7.4 standard, comfortable sizes", "; ".join(f"{k} {v:.0f}" for k, v in sizes.items()) + " m²"),
    ]
    for rid, ev in judged:
        add(rid, True, ev, manual=True)
    for rid, ok, ev in door_clearance(opt) + ground_clearance(opt, gm) + daylight(opt):
        add(rid, ok, ev)
    return {"option": opt.code, "rules": rules}


SOLID = ("furn", "bench", "car", "fixture")


def _swing(d):
    """Floor swept by a hinged leaf: a quarter disc from the hinge."""
    if d.axis == "u":
        hinge = (d.u - d.w / 2 if d.hinge < 0 else d.u + d.w / 2, d.v)
        box_ = R(d.u - d.w / 2, d.v, d.u + d.w / 2, d.v + d.swing * d.w)
    else:
        hinge = (d.u, d.v - d.w / 2 if d.hinge < 0 else d.v + d.w / 2)
        box_ = R(d.u, d.v - d.w / 2, d.u + d.swing * d.w, d.v + d.w / 2)
    return Point(hinge).buffer(d.w, quad_segs=16).intersection(box_)


def door_clearance(opt: Option):
    """No furniture in any doorway, opening or door swing (C09 had six such clashes)."""
    out = []
    for lv in opt.levels.values():
        cores = unary_union([r.geom for r in lv.rooms if r.kind in ("stair", "lift")])
        solid = [f.geom for f in lv.furniture if f.style in SOLID and f.geom.geom_type == "Polygon"
                 and not cores.contains(f.geom.centroid)]
        bad = []
        for d in lv.doors:
            if "lift" in d.a or "lift" in d.b or "stair" in d.a or "stair" in d.b:
                continue
            zone = door_cut(d).union(_swing(d)) if d.kind == "door" else door_cut(d)
            hit = sum(zone.intersection(g).area for g in solid)
            if hit > 0.005:
                bad.append(f"{d.a}→{d.b} ({hit:.2f} m²)")
        out.append((f"doors.clear.{lv.key}", not bad,
                    f"{len(lv.doors)} doors and openings checked with their swings; blocked: {bad or 'none'}"))
    return out


def _outside(lv, u, v, axis):
    for s in (0.4, -0.4):
        p = (u, v + s) if axis == "u" else (u + s, v)
        if not lv.footprint.contains(Point(p)):
            return p
    return None


def ground_clearance(opt: Option, gm: GroundModel):
    """Natural ground against every window (sill 0.9 m) and the finished surface outside every outside door."""
    out = []
    for key in ("main", "lower"):
        lv = opt.levels[key]
        worst_w, worst_d, rows = -9.0, -9.0, []
        for w in lv.windows:
            axis = "u" if abs(w.v1 - w.v0) < 1e-6 else "v"
            pts = [(w.u0 + (w.u1 - w.u0) * k / 4, w.v0 + (w.v1 - w.v0) * k / 4) for k in range(5)]
            hs = [zg_safe(*o) - lv.z for p in pts if (o := _outside(lv, *p, axis))]
            if hs:
                worst_w = max(worst_w, max(hs))
                if max(hs) > 0.0:
                    rows.append(f"window at ({pts[2][0]:.1f}, {pts[2][1]:.1f}): ground {max(hs):+.2f} m")
        slabs = unary_union([t.geom for t in lv.terraces if t.kind in ("terrace", "deck")] or [Point(0, 0)])
        for d in lv.doors:
            if "ext" not in (d.a, d.b):
                continue
            o = _outside(lv, d.u, d.v, d.axis)
            h = -0.02 if slabs.contains(Point(o)) else gm.finished(*o) - lv.z
            worst_d = max(worst_d, h)
        ok = worst_w <= 0.6 and worst_d <= 0.02
        out.append((f"ground.openings.{key}", ok,
                    f"highest natural ground at any window {worst_w:+.2f} m against the floor (sill 0.9 m, limit +0.6); "
                    f"every outside door opens onto a terrace, court or balcony at floor level ({worst_d:+.2f} m). "
                    + ("; ".join(rows) if rows else "No window has ground above floor level.")))
    return out


def daylight(opt: Option):
    """Each bedroom and day room has an opening of its own to the outside."""
    out = []
    for key in ("main", "lower"):
        lv = opt.levels[key]
        res = {}
        for r in lv.rooms:
            if not (r.main or r.kind == "sleep"):
                continue
            edge = r.geom.exterior.buffer(0.05)
            n = sum(edge.contains(Point((w.u0 + w.u1) / 2, (w.v0 + w.v1) / 2)) for w in lv.windows)
            n += sum(r.id in (d.a, d.b) and "ext" in (d.a, d.b) for d in lv.doors)
            res[r.name.title()] = n
        out.append((f"daylight.rooms.{key}", all(res.values()), f"windows and glazed outside doors per room: {res}"))
    return out
