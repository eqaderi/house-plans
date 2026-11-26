"""3D model of the field and of C11 on it, for the viewer in 3d.html.

C11: columns, beams, foundation, retaining and site walls are drawn from the same structure lists as the
plans and the sections (structure.py); nothing is invented here.

Everything is derived from the same Option and GroundModel that draw the plans and sections:
the survey TIN (natural ground), the finished ground (pits, platforms, walls), the three floors as
closed volumes and as open "dollhouse" plans. Model axes: x = u (field east), y = height above
1664 m, z = v (field south). Lengths are sent as integer centimetres.
"""

from __future__ import annotations

import math

import engine as E
from shapely import constrained_delaunay_triangles
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

Z0 = 1664.0
CELL = 0.5
WALL_CUT = 1.3  # dollhouse walls are cut at this height above the floor
STOREY = {"road": 3.0, "main": 3.6, "lower": 3.3}  # clear height drawn; the slab above adds 0.3
SHELL = {"road": (0.78, 0.79, 0.78), "main": (0.96, 0.95, 0.92), "lower": (0.85, 0.78, 0.68)}
ROOM = {"day": (0.96, 0.92, 0.85), "kitchen": (0.96, 0.89, 0.77), "sleep": (0.89, 0.92, 0.95), "wet": (0.85, 0.93, 0.92),
        "hall": (0.96, 0.96, 0.94), "core": (0.95, 0.93, 0.91), "service": (0.91, 0.90, 0.87), "garage": (0.89, 0.90, 0.89),
        "lift": (0.83, 0.87, 0.89), "stair": (0.95, 0.93, 0.91), "study": (0.91, 0.89, 0.94)}
GROUND = {"paved": (0.87, 0.81, 0.70), "lawn": (0.55, 0.72, 0.40), "court": (0.80, 0.78, 0.73), "stair": (0.78, 0.75, 0.69),
          "pit": (0.66, 0.55, 0.42), "void": (0.66, 0.55, 0.42), "landing": (0.82, 0.78, 0.70)}
STRUCT = {"column": (0.25, 0.25, 0.27), "beam": (0.35, 0.33, 0.38), "wall": (0.62, 0.62, 0.60), "retaining": (0.52, 0.47, 0.41)}
SLAB = {"terrace": (0.88, 0.82, 0.70), "deck": (0.85, 0.79, 0.69), "green": (0.60, 0.74, 0.48)}
FURN = {"furn": ((0.99, 0.98, 0.95), 0.45), "bench": ((0.80, 0.74, 0.64), 0.9), "car": ((0.60, 0.71, 0.80), 1.45),
        "fixture": ((0.97, 0.97, 0.96), 0.4), "mat": ((0.80, 0.87, 0.76), 0.03)}
CONCRETE = (0.74, 0.74, 0.72)
CUT_FACE = (0.72, 0.52, 0.36)
GLASS = (0.33, 0.52, 0.64)


class Builder:
    def __init__(self) -> None:
        self.tris: dict[tuple, list[int]] = {}
        self.lines: dict[tuple, list[int]] = {}
        self.labels: list[dict] = []
        self._z: dict[tuple[int, int], float] = {}

    # -- primitives
    def zn(self, u: float, v: float) -> float:
        k = (round(u * 100), round(v * 100))
        if k not in self._z:
            self._z[k] = E.zg_safe(u, v)
        return self._z[k]

    @staticmethod
    def _p(u: float, v: float, z: float) -> list[int]:
        return [round(u * 100), round((z - Z0) * 100), round(v * 100)]

    def tri(self, key: tuple, a, b, c, n) -> None:
        """Triangle (u, v, z) x 3, wound so its normal agrees with the hint n = (nu, nv, nz)."""
        ax, ay, az = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        bx, by, bz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        # normal in model axes (x=u, y=z, z=v)
        mx, my, mz = ax, az, ay
        nx, ny, nz_ = bx, bz, by
        cx, cy, cz = my * nz_ - mz * ny, mz * nx - mx * nz_, mx * ny - my * nx
        if cx * n[0] + cy * n[2] + cz * n[1] < 0:
            b, c = c, b
        self.tris.setdefault(key, []).extend(self._p(*a) + self._p(*b) + self._p(*c))

    def line(self, key: tuple, pts) -> None:
        out = self.lines.setdefault(key, [])
        for a, b in zip(pts, pts[1:]):
            out.extend(self._p(*a) + self._p(*b))

    def label(self, group: str, text: str, u: float, v: float, z: float, sub: str = "", cls: str = "") -> None:
        self.labels.append({"g": group, "t": text, "s": sub, "k": cls, "p": [round(u, 2), round(z - Z0, 2), round(v, 2)]})

    # -- solids
    def flat(self, key: tuple, poly, zf, up: bool = True) -> None:
        for g in E.polys(poly):
            for t in constrained_delaunay_triangles(g).geoms:
                a, b, c = [(x, y, zf(x, y) if callable(zf) else zf) for x, y in t.exterior.coords[:3]]
                self.tri(key, a, b, c, (0, 0, 1 if up else -1))

    def sides(self, key: tuple, poly, z0, z1) -> None:
        """Vertical faces around a polygon between z0 and z1 (numbers or functions of u, v)."""
        for g in E.polys(poly):
            pg = prep(g)
            for ring in [g.exterior, *g.interiors]:
                cs = list(ring.coords)
                for (u0, v0), (u1, v1) in zip(cs, cs[1:]):
                    d = math.hypot(u1 - u0, v1 - v0)
                    if d < 1e-6:
                        continue
                    n = ((v1 - v0) / d, -(u1 - u0) / d)
                    m = ((u0 + u1) / 2, (v0 + v1) / 2)
                    if pg.contains(Point(m[0] + n[0] * 0.01, m[1] + n[1] * 0.01)):
                        n = (-n[0], -n[1])

                    def f(z, u, v):
                        return z(u, v) if callable(z) else z

                    a, b = (u0, v0, f(z0, u0, v0)), (u1, v1, f(z0, u1, v1))
                    c, e = (u1, v1, f(z1, u1, v1)), (u0, v0, f(z1, u0, v0))
                    self.tri(key, a, b, c, (n[0], n[1], 0))
                    self.tri(key, a, c, e, (n[0], n[1], 0))

    def wall(self, key: tuple, lines, inside, z0, z1) -> None:
        """Vertical faces along loose line segments; `inside` is the polygon they bound."""
        pg = prep(inside)
        for ln in lines:
            cs = list(ln.coords)
            for (u0, v0), (u1, v1) in zip(cs, cs[1:]):
                d = math.hypot(u1 - u0, v1 - v0)
                if d < 1e-6:
                    continue
                n = ((v1 - v0) / d, -(u1 - u0) / d)
                if pg.contains(Point((u0 + u1) / 2 + n[0] * 0.02, (v0 + v1) / 2 + n[1] * 0.02)):
                    n = (-n[0], -n[1])
                m = max(1, int(d / 0.5))
                for k in range(m):
                    p0 = (u0 + (u1 - u0) * k / m, v0 + (v1 - v0) * k / m)
                    p1 = (u0 + (u1 - u0) * (k + 1) / m, v0 + (v1 - v0) * (k + 1) / m)
                    a, c = (*p0, z0(*p0)), (*p1, z0(*p1))
                    e, f = (*p1, z1), (*p0, z1)
                    self.tri(key, a, c, e, (n[0], n[1], 0))
                    self.tri(key, a, e, f, (n[0], n[1], 0))

    def prism(self, key: tuple, poly, z0: float, z1: float, edges: tuple | None = None, bottom: bool = False,
              top_key: tuple | None = None) -> None:
        self.flat(top_key or key, poly, z1)
        if bottom:
            self.flat(key, poly, z0, up=False)
        self.sides(key, poly, z0, z1)
        if edges:
            for g in E.polys(poly):
                for ring in [g.exterior, *g.interiors]:
                    cs = list(ring.simplify(0.01).coords)
                    self.line(edges, [(u, v, z1) for u, v in cs])
                    self.line(edges, [(u, v, z0) for u, v in cs])
                    for u, v in cs[:-1]:
                        self.line(edges, [(u, v, z0), (u, v, z1)])

    def blob(self, key: tuple, u: float, v: float, z: float, r: float, squash: float = 0.85) -> None:
        """Low-poly ball: tree crowns and heads."""
        rings, seg = 5, 10
        pts = [[(u + r * math.sin(math.pi * i / rings) * math.cos(2 * math.pi * j / seg),
                 v + r * math.sin(math.pi * i / rings) * math.sin(2 * math.pi * j / seg),
                 z + r * squash * math.cos(math.pi * i / rings)) for j in range(seg)] for i in range(rings + 1)]
        for i in range(rings):
            for j in range(seg):
                a, b, c, d = pts[i][j], pts[i][(j + 1) % seg], pts[i + 1][(j + 1) % seg], pts[i + 1][j]
                m = ((a[0] + c[0]) / 2 - u, (a[1] + c[1]) / 2 - v, (a[2] + c[2]) / 2 - z)
                if i:
                    self.tri(key, a, b, c, m)
                if i < rings - 1:
                    self.tri(key, a, c, d, m)

    # -- draped surfaces
    def drape(self, key, domain, zf) -> None:
        """Triangulated surface over `domain`, on a regular grid, with height zf(u, v).

        `key` is a batch key, or a function of (u, v) giving one.
        """
        fixed = None if callable(key) else key
        for dom in E.polys(domain):
            pd = prep(dom)
            u0, v0, u1, v1 = dom.bounds
            i0, i1 = math.floor(u0 / CELL), math.ceil(u1 / CELL)
            j0, j1 = math.floor(v0 / CELL), math.ceil(v1 / CELL)
            for i in range(i0, i1):
                for j in range(j0, j1):
                    cell = box(i * CELL, j * CELL, (i + 1) * CELL, (j + 1) * CELL)
                    k = fixed or key((i + 0.5) * CELL, (j + 0.5) * CELL)
                    if pd.contains(cell):
                        a, b, c, d = [(x, y, zf(x, y)) for x, y in cell.exterior.coords[:4]]
                        self.tri(k, a, b, c, (0, 0, 1))
                        self.tri(k, a, c, d, (0, 0, 1))
                    elif pd.intersects(cell):
                        self.flat(k, cell.intersection(dom), zf)


def free_edges(poly, blockers) -> list[LineString]:
    """Edges of a terrace that have nothing built against them: where a balustrade stands."""
    ring = poly.exterior
    if blockers is not None and not blockers.is_empty:
        ring = ring.difference(blockers.buffer(0.08, join_style=2))
    out = []
    for g in getattr(ring, "geoms", [ring]):
        if g.geom_type == "LineString" and g.length > 0.4:
            out.append(g)
    return out


def contour_segments(step: float = 1.0):
    us = [x * 0.5 for x in range(-24, 70)]
    vs = [y * 0.5 for y in range(-2, 40)]
    zs = [[E.zg(u, v) for u in us] for v in vs]
    for k in range(1663, 1680):
        lev = k * step
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
                if len(pts) == 2 and E.PARCEL.buffer(0.05).contains(LineString(pts)):
                    yield lev, pts


def build_model(opt: E.Option, gm: E.GroundModel, elements=(), swalls=()):
    """Returns (model, ids of the structure elements and site walls drawn)."""
    b = Builder()
    drawn: set[str] = set()
    zn = b.zn
    levels = opt.levels
    built = gm.built

    # ------------------------------------------------ the field as surveyed
    b.drape(("nat", "terrain"), E.PARCEL, zn)
    # The road and the land above it are not surveyed. They are drawn level across, at the height of
    # the west boundary, and wide enough that the model has no cliff on the uphill side.
    k = (ring_w := list(E.PARCEL.exterior.coords))[1][0] / ring_w[1][1]  # west boundary: u = k v

    def strip(a: float, c: float):
        return Polygon([(k * -8 - a, -8), (k * 24 - a, 24), (k * 24 - c, 24), (k * -8 - c, -8)]).difference(E.PARCEL)

    def z_road(u: float, v: float) -> float:
        vc = min(18.2, max(0.2, v))
        return zn(round(k * vc + 0.3, 2), round(vc, 2))

    road = strip(0, 26)
    b.drape(("road", (0.60, 0.60, 0.59)), strip(0, 9), z_road)
    b.drape(("road", (0.80, 0.79, 0.74)), strip(9, 26), z_road)
    ring = list(E.PARCEL.exterior.coords)

    def densify(coords):
        out = []
        for (u0, v0), (u1, v1) in zip(coords, coords[1:]):
            n = max(2, int(math.hypot(u1 - u0, v1 - v0) / 0.5))
            out += [(u0 + (u1 - u0) * k / n, v0 + (v1 - v0) * k / n) for k in range(n)]
        return out + [out[0]]

    b.line(("parcel", (0.72, 0.22, 0.14, 1.0)), [(u, v, zn(u, v) + 0.12) for u, v in densify(ring)])
    # skirt around field and road so they read as one solid block of earth
    base = Z0 - 1.5
    block = unary_union([E.PARCEL, road]).buffer(0.01).buffer(-0.01)
    edge_pts = densify(list(block.exterior.coords))
    for (u0, v0), (u1, v1) in zip(edge_pts, edge_pts[1:]):
        a, c = (u0, v0, base), (u1, v1, base)
        on_road = [not E.PARCEL.buffer(0.05).contains(Point(p)) for p in ((u0, v0), (u1, v1))]
        d = (u1, v1, z_road(u1, v1) if on_road[1] else zn(u1, v1))
        e = (u0, v0, z_road(u0, v0) if on_road[0] else zn(u0, v0))
        m = block.centroid
        n = ((u0 + u1) / 2 - m.x, (v0 + v1) / 2 - m.y, 0)
        b.tri(("earth", (0.71, 0.63, 0.52)), a, c, d, n)
        b.tri(("earth", (0.71, 0.63, 0.52)), a, d, e, n)
    for name, (u, v) in zip(("NW", "SW", "SE", "NE"), ring[:4]):
        z = zn(u, v)
        b.line(("parcel", (0.72, 0.22, 0.14, 1.0)), [(u, v, z), (u, v, z + 1.6)])
        b.label("heights", f"{name} corner", u, v, z + 1.9, f"{z:.1f} m", "h")
    for lev, pts in contour_segments():
        strong = int(lev) % 5 == 0
        b.line(("contours", (0.25, 0.2, 0.12, 0.9 if strong else 0.6)), [(u, v, lev + 0.05) for u, v in pts])
    for lev in (1666, 1668, 1670, 1672, 1674, 1676):
        # label each even contour where it meets the north boundary
        us = [k * 0.1 for k in range(0, 320)]
        hit = next((u for u in us if zn(u, 0.4) <= lev), None)
        if hit:
            b.label("contours", f"{lev}", hit, 0.2, lev + 0.3, "", "c")
    # the two falls, as arrows lying on the ground
    def arrow(p0, p1, text, sub, at):
        n = 24
        pts = [(p0[0] + (p1[0] - p0[0]) * k / n, p0[1] + (p1[1] - p0[1]) * k / n) for k in range(n + 1)]
        pts3 = [(u, v, zn(u, v) + 0.35) for u, v in pts]
        key = ("slopes", (0.1, 0.1, 0.1, 1.0))
        b.line(key, pts3)
        (ua, va), (ub, vb) = pts[-3], pts[-1]
        d = math.hypot(ub - ua, vb - va)
        du, dv = (ub - ua) / d, (vb - va) / d
        for s in (1, -1):
            b.line(key, [pts3[-1], (ub - du * 1.2 + s * dv * 0.6, vb - dv * 1.2 - s * du * 0.6, pts3[-1][2] + 0.4)])
        mid = pts3[round(n * at)]
        b.label("slopes", text, mid[0], mid[1], mid[2] + 1.2, sub, "s")

    za, zb = zn(-4.4, 9.0), zn(27.2, 9.0)
    arrow((-4.4, 9.0), (27.2, 9.0), f"falls {za - zb:.1f} m from the road to the east boundary",
          f"west → east, {100 * (za - zb) / 31.6:.0f}%: the main slope", 0.72)
    za, zb = zn(12.0, 0.4), zn(12.0, 18.0)
    arrow((12.0, 0.4), (12.0, 18.0), f"falls {za - zb:.1f} m from north to south",
          f"{100 * (za - zb) / 17.6:.0f}%: the cross slope", 0.3)

    # ------------------------------------------------ the ground after the works
    # the natural ground over every piece of reshaped ground, drawn see-through in the dig view
    b.drape(("natlid", (0.98, 0.86, 0.45, 0.42)), gm.works, zn)
    b.drape(("fin", "terrain"), E.PARCEL.difference(gm.works.buffer(0.001)), zn)
    for r in gm.regions:
        key = ("fin", GROUND[r.kind])
        if r.kind in ("pit", "void"):  # brown where the floor is dug in, plain ground where it stands above the hill
            b.drape(lambda u, v, r=r: ("fin", GROUND["pit"]) if zn(u, v) > r.z + 0.02 else ("fin", "terrain"), r.geom, r.level)
        elif r.kind == "stair":
            b.flat(key, r.geom, r.level)
            (a0, b0), (a1, b1) = E.stair_axis(r.geom, r.run)
            L = math.hypot(a1 - a0, b1 - b0)
            du, dv = (a1 - a0) / L, (b1 - b0) / L
            n = max(2, round(abs(r.z - r.z_end) / 0.155))
            for k in range(n + 1):
                pu, pv = a0 + (a1 - a0) * k / n, b0 + (b1 - b0) * k / n
                ln = LineString([(pu - dv * 4, pv + du * 4), (pu + dv * 4, pv - du * 4)]).intersection(r.geom)
                if ln.geom_type == "LineString" and not ln.is_empty:
                    b.line(("fin", (0.3, 0.3, 0.3, 0.7)), [(x, y, r.level(x, y) + 0.03) for x, y in ln.coords])
        else:
            b.flat(key, r.geom, r.z)
        # walls and cut faces wherever the ground steps at the edge of this region
        pr = prep(r.geom)
        for ringc in [r.geom.exterior, *r.geom.interiors]:
            cs = list(ringc.coords)
            for (ua, va), (ub, vb) in zip(cs, cs[1:]):
                d = math.hypot(ub - ua, vb - va)
                if d < 1e-6:
                    continue
                n = ((vb - va) / d, -(ub - ua) / d)
                if pr.contains(Point((ua + ub) / 2 + n[0] * 0.02, (va + vb) / 2 + n[1] * 0.02)):
                    n = (-n[0], -n[1])
                m = max(1, int(d / 0.5))
                for k in range(m):
                    p0 = (ua + (ub - ua) * k / m, va + (vb - va) * k / m)
                    p1 = (ua + (ub - ua) * (k + 1) / m, va + (vb - va) * (k + 1) / m)
                    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
                    out = (mid[0] + n[0] * 0.03, mid[1] + n[1] * 0.03)
                    if not E.PARCEL.contains(Point(out)):
                        continue
                    other = gm.region_at(*out)

                    def lev_out(p, other=other):
                        return other.level(*p) if other else zn(*p)

                    zi, zo = r.level(mid[0] - n[0] * 0.03, mid[1] - n[1] * 0.03), lev_out(out)
                    if abs(zi - zo) < 0.03:
                        continue
                    retaining = zi > zo  # this side is higher: a wall holds it up
                    natural_cut = (not retaining) and other is None
                    if not natural_cut:
                        continue  # walls are drawn from the site-wall list below
                    key2 = ("fin", CUT_FACE if natural_cut else CONCRETE)
                    nn = (n[0], n[1], 0) if retaining else (-n[0], -n[1], 0)
                    a = (*p0, r.level(*p0))
                    c = (*p1, r.level(*p1))
                    e = (*p1, lev_out(p1))
                    f = (*p0, lev_out(p0))
                    b.tri(key2, a, c, e, nn)
                    b.tri(key2, a, e, f, nn)
    # plinths: floors and terraces that stand above the ground are closed down to it
    below: list = []
    for lv in sorted(levels.values(), key=lambda x: x.z):
        contact = lv.footprint.difference(unary_union(below)) if below else lv.footprint
        below.append(lv.footprint)
        others = unary_union([o.footprint for o in levels.values() if o is not lv])
        for g in E.polys(contact):
            b.wall((f"base-{lv.key}", CONCRETE), free_edges(g, others), g, lambda u, v, z=lv.z: min(zn(u, v), z) - 0.3, lv.z - 0.3)
    # the structure model: columns, beams, foundation, retaining and site walls with their real levels
    for e in elements:
        if e.geom.geom_type == "Point":
            g = box(e.geom.x - e.t / 2, e.geom.y - e.t / 2, e.geom.x + e.t / 2, e.geom.y + e.t / 2)
        else:
            g = e.geom.buffer(e.t / 2, cap_style=2, join_style=2)
        if e.kind in ("wall",) and e.storey in ("main", "road") and not e.id.startswith(("MW-0F", "LIFT")):
            continue  # inner bearing walls are already the walls of the floor plans
        grp = "struct" if e.kind != "beam" else "struct"
        b.prism((grp, STRUCT[e.kind]), g, e.z_bot, e.z_top, edges=(grp, (0.15, 0.15, 0.15, 0.5)))
        drawn.add(e.id)
    for w in swalls:
        b.prism(("struct", STRUCT["retaining"]), w.geom.buffer(0.12, cap_style=2), w.z_bot - 0.5, w.z_top, edges=("struct", (0.15, 0.15, 0.15, 0.5)))
        drawn.add(w.id)

    # earthwork labels
    for r in gm.regions:
        if r.kind == "stair":
            continue
        c = r.geom.representative_point()
        res = E.integrate(E.site.terrain.surface, E.to_local_poly(r.geom), r.z)
        cut, fill = res.cut_m3 or 0, 0 if r.kind == "pit" else (res.below_plane_m3 or 0)
        bits = ([f"dig {cut:.0f} m³, up to {res.max_cut_m:.1f} m deep"] if cut >= 1 else []) + \
               ([f"fill {fill:.0f} m³, up to {res.max_below_m:.1f} m"] if fill >= 1 else [])
        if bits:
            nm = (r.name.split(" + ")[0] + " pit") if r.kind == "pit" else r.name
            b.label("earthwork", nm.title(), c.x, c.y, max(r.level(c.x, c.y), zn(c.x, c.y)) + 1.0, " · ".join(bits),
                    "dig" if cut > fill else "fill")

    # ------------------------------------------------ the house, floor by floor
    ghost = ("ghost", (0.13, 0.2, 0.25, 0.75))
    edge = (0.16, 0.22, 0.27, 0.55)
    for key, lv in levels.items():
        h = STOREY[key]
        fp = lv.footprint
        sk, pk, tk = f"shell-{key}", f"plan-{key}", f"terr-{key}"
        # closed volume
        shell = fp.buffer(E.EXT_OUT, join_style=2)  # walls grow outward: the house is seen at its outer face
        b.prism((sk, SHELL[key]), shell, lv.z - 0.3, lv.z + h, edges=(sk, edge))
        roof = fp.buffer(E.EXT_OUT + 0.05, join_style=2)
        b.prism((sk, (0.36, 0.40, 0.43)), roof, lv.z + h, lv.z + h + 0.3, edges=(sk, edge), bottom=True)
        for g in E.polys(fp):
            cs = list(g.exterior.simplify(0.01).coords)
            for zz in (lv.z, lv.z + h + 0.3):
                b.line(ghost, [(u, v, zz) for u, v in cs])
            for u, v in cs[:-1]:
                b.line(ghost, [(u, v, lv.z), (u, v, lv.z + h + 0.3)])
        # name each floor on its south-east corner, the one every downhill view shows
        cu, cv = max(fp.exterior.coords, key=lambda c: (round(c[0] + c[1], 2), c[0]))
        b.label(sk, lv.title.replace(" + GARDEN", ""), cu, cv, lv.z + h * 0.55, f"floor at {lv.z:.2f} m", "lvl")
        # glazing and doors on the outside
        pfp = prep(fp)
        for kind, u0, v0, u1, v1 in ([("win", w.u0, w.v0, w.u1, w.v1) for w in lv.windows] +
                                     [(d.kind, d.u - (d.w / 2 if d.axis == "u" else 0), d.v - (d.w / 2 if d.axis == "v" else 0),
                                       d.u + (d.w / 2 if d.axis == "u" else 0), d.v + (d.w / 2 if d.axis == "v" else 0))
                                      for d in lv.doors if "ext" in (d.a, d.b)]):
            along_u = abs(v1 - v0) < 1e-6
            n = (0, 1) if along_u else (1, 0)
            m = ((u0 + u1) / 2, (v0 + v1) / 2)
            if pfp.contains(Point(m[0] + n[0] * 0.3, m[1] + n[1] * 0.3)):
                n = (-n[0], -n[1])
            zb, zt, col = {"win": (0.9, 2.2, GLASS), "slide": (0.05, 2.3, GLASS), "glass": (0.05, 2.3, GLASS),
                           "door": (0.0, 2.2, (0.45, 0.33, 0.24)), "shutter": (0.0, 2.5, (0.36, 0.38, 0.40))}[kind]
            o = E.EXT_OUT + 0.02
            p0, p1 = (u0 + n[0] * o, v0 + n[1] * o), (u1 + n[0] * o, v1 + n[1] * o)
            a, c = (*p0, lv.z + zb), (*p1, lv.z + zb)
            e, f = (*p1, lv.z + zt), (*p0, lv.z + zt)
            b.tri((sk, col), a, c, e, (n[0], n[1], 0))
            b.tri((sk, col), a, e, f, (n[0], n[1], 0))
            b.line((sk, edge), [a, c, e, f, a])
        # open plan: floors, cut walls, furniture, names
        for r in lv.rooms:
            if r.kind == "merge":
                continue
            b.flat((pk, ROOM.get(r.kind, ROOM["hall"])), r.geom, lv.z + 0.02)
            if r.name and r.kind not in ("stair",):
                p = r.label_at or (r.geom.representative_point().x, r.geom.representative_point().y)
                w, d, a = E.room_dims(r)
                b.label(pk, r.name.title(), p[0], p[1], lv.z + WALL_CUT + 0.25, f"{a:.0f} m²" if a > 2.5 and not r.small else "",
                        "room" if not r.small else "room small")
        b.prism((pk, (0.93, 0.92, 0.89)), fp.buffer(0.15, join_style=2), lv.z - 0.3, lv.z + 0.01, edges=(pk, edge))
        b.prism((pk, (0.90, 0.89, 0.86)), E.walls(lv), lv.z, lv.z + WALL_CUT, top_key=(pk, (0.16, 0.22, 0.27)))
        cores = unary_union([r.geom for r in lv.rooms if r.kind in ("stair", "lift")])
        outdoor = unary_union([t.geom for t in lv.terraces] or [Polygon()])
        for f in lv.furniture:
            if f.style == "stair" and f.geom.geom_type == "LineString":
                b.line((pk, (0.3, 0.33, 0.36, 0.8)), [(u, v, lv.z + 0.05) for u, v in f.geom.coords])
            if f.style not in FURN or f.geom.geom_type != "Polygon" or f.geom.area < 0.04 or cores.contains(f.geom.centroid):
                continue
            col, hh = FURN[f.style]
            grp = tk if (outdoor.contains(f.geom.centroid) and not fp.contains(f.geom.centroid)) else pk
            b.prism((grp, col), f.geom, lv.z + 0.02, lv.z + hh, edges=(grp, (0.3, 0.33, 0.36, 0.45)))
        # terraces, balconies, roof decks that belong to this floor
        for t in lv.terraces:
            if t.kind not in SLAB:
                continue
            thick = 0.22 if t.kind == "terrace" else 0.06
            top = t.z + 0.08  # just proud of the roof slab it lies on
            b.prism((tk, SLAB[t.kind]), t.geom, t.z - thick, top, edges=(tk, edge), bottom=True)
            c = t.label_at if (t.label_at and t.geom.contains(Point(t.label_at))) else \
                (t.geom.representative_point().x, t.geom.representative_point().y)
            b.label(tk, t.name.title(), c[0], c[1], t.z + 1.5, t.note or f"{t.geom.area:.0f} m²", "terr")
            if t.kind == "green":
                continue
            others = unary_union([fp] + [o.geom for o in lv.terraces if o is not t and (o.kind in SLAB or abs(o.z - t.z) < 0.3)])
            for seg in free_edges(t.geom, others):
                cs = list(seg.coords)
                for (ua, va), (ub, vb) in zip(cs, cs[1:]):
                    a, c2 = (ua, va, top), (ub, vb, top)
                    e, f2 = (ub, vb, top + 1.05), (ua, va, top + 1.05)
                    b.tri((tk, (0.62, 0.80, 0.86, 0.32)), a, c2, e, (0, 0, 1))
                    b.tri((tk, (0.62, 0.80, 0.86, 0.32)), a, e, f2, (0, 0, 1))
                    b.line((tk, (0.2, 0.3, 0.36, 0.9)), [f2, e])
    # garden things: names, rails at drops, trees, people
    for lv in levels.values():
        for t in lv.terraces:
            if t.kind in E.GROUND_KINDS and t.name:
                c = t.label_at if (t.label_at and t.geom.contains(Point(t.label_at))) else \
                    (t.geom.representative_point().x, t.geom.representative_point().y)
                b.label("garden", t.name.title(), c[0], c[1], t.z + 1.5, f"{t.geom.area:.0f} m² · {t.z:.2f} m", "terr")
            if t.kind == "paved":
                for seg in free_edges(t.geom, built):
                    cs = list(seg.coords)
                    for (ua, va), (ub, vb) in zip(cs, cs[1:]):
                        mid = ((ua + ub) / 2, (va + vb) / 2)
                        d = math.hypot(ub - ua, vb - va)
                        n = ((vb - va) / d, -(ub - ua) / d)
                        out = (mid[0] + n[0] * 0.2, mid[1] + n[1] * 0.2)
                        if t.geom.contains(Point(out)):
                            out = (mid[0] - n[0] * 0.2, mid[1] - n[1] * 0.2)
                        if gm.finished(*out) > t.z - 0.6:
                            continue
                        a, c2, e, f2 = (ua, va, t.z), (ub, vb, t.z), (ub, vb, t.z + 1.05), (ua, va, t.z + 1.05)
                        b.tri(("garden", (0.62, 0.80, 0.86, 0.32)), a, c2, e, (0, 0, 1))
                        b.tri(("garden", (0.62, 0.80, 0.86, 0.32)), a, e, f2, (0, 0, 1))
                        b.line(("garden", (0.2, 0.3, 0.36, 0.9)), [f2, e])
            if t.kind == "bank":
                for k, (u, v) in enumerate(E.tree_spots(t.geom)):
                    z = zn(u, v)
                    trunk = Point(u, v).buffer(0.14, quad_segs=2)
                    b.prism(("trees", (0.42, 0.32, 0.24)), trunk, z, z + 2.3)
                    b.blob(("trees", (0.33, 0.50, 0.29) if k % 2 else (0.38, 0.55, 0.31)), u, v, z + 3.2, 1.35 if k % 2 == 0 else 1.15)
                spots = E.tree_spots(t.geom)
                c = spots[0] if spots else t.geom.representative_point().coords[0]
                b.label("garden", t.name.title(), c[0], c[1], zn(*c) + 5.2, t.note, "terr")

    def person(u, v, height=1.72, group="people"):
        z = gm.finished(u, v) if not built.contains(Point(u, v)) else None
        if z is None:
            return
        b.prism((group, (0.20, 0.26, 0.32)), box(u - 0.2, v - 0.13, u + 0.2, v + 0.13), z, z + height * 0.84)
        b.blob((group, (0.86, 0.72, 0.60)), u, v, z + height * 0.92, height * 0.075, 1.0)

    for u, v, hgt in ((-2.6, 6.0, 1.72), (19.4, 6.4, 1.72), (23.6, 5.2, 1.25), (22.6, 9.4, 1.72), (1.2, 14.6, 1.72)):
        person(u, v, hgt)
    # people standing on slabs
    for lv in levels.values():
        for t in lv.terraces:
            if t.kind in ("terrace", "deck") and t.geom.area > 30:
                c = t.geom.representative_point()
                u, v = c.x + 0.8, c.y
                b.prism((f"terr-{lv.key}", (0.20, 0.26, 0.32)), box(u - 0.2, v - 0.13, u + 0.2, v + 0.13), t.z, t.z + 1.45)
                b.blob((f"terr-{lv.key}", (0.86, 0.72, 0.60)), u, v, t.z + 1.58, 0.13, 1.0)

    def pack(d):
        out = []
        for (g, col), arr in d.items():
            if not arr:
                continue
            out.append({"g": g, "c": col if isinstance(col, str) else [round(x, 3) for x in col], "p": arr})
        return out

    u_bearing = E.U_BEARING
    return {
        "tris": pack(b.tris), "lines": pack(b.lines), "labels": b.labels,
        # grid north in model axes (x = u, z = v)
        "north": [round(math.cos(math.radians(u_bearing)), 4), round(-math.sin(math.radians(u_bearing)), 4)],
        "zrange": [1664.5, 1678.2], "z0": Z0,
        "stats": {"triangles": sum(len(a) for a in b.tris.values()) // 9},
    }, drawn
