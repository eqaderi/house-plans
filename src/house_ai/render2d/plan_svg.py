"""Dimensioned floor-plan SVG drawn from a canonical plan version.

One panel per level at a common scale, plus a schematic section against the
surveyed terrain. Everything drawn comes from the model: spaces, walls (by
kind, retaining walls dark), doors with swings, windows, stairs, room labels
with areas and dimensions, overall dimensions, the circulation tree from the
front door, the parcel boundary and buildable envelope, and the north arrow
only as far as the site establishes it. Output is deterministic.
"""

from __future__ import annotations

import math
from collections import deque
from xml.sax.saxutils import escape

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from house_ai.domain.base import EXTERIOR
from house_ai.domain.epistemics import ConfirmationStatus
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.geometry import Point2, Polygon2D
from house_ai.domain.model import HouseModel, Opening, OpeningKind, Operation, Wall, WallKind
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import Privacy
from house_ai.domain.site import (
    PointGeometry,
    PolygonGeometry,
    PolylineGeometry,
    Site,
    SiteFeatureKind,
)
from house_ai.domain.terrain import elevation_at, site_surface

PANEL_W = 560.0
MARGIN = 36.0
HEADER_H = 92.0
SECTION_H = 230.0

FILL = {
    Privacy.PUBLIC: "#f6e7c8",
    Privacy.SEMI_PRIVATE: "#e9eef3",
    Privacy.PRIVATE: "#dcebdc",
    Privacy.SERVICE: "#ece4f2",
}
WALL_FILL = {
    WallKind.EXTERIOR: "#3a3a3a",
    WallKind.INTERIOR: "#7a7a7a",
    WallKind.RETAINING: "#6b4a2b",
    WallKind.PARAPET: "#555555",
}


def _f(v: float) -> str:
    return f"{v:.2f}"


def _t(
    x: float,
    y: float,
    text: str,
    size: float = 10,
    anchor: str = "middle",
    colour: str = "#222",
    weight: str = "normal",
    rotate: float | None = None,
) -> str:
    rot = f' transform="rotate({_f(rotate)} {_f(x)} {_f(y)})"' if rotate is not None else ""
    return (
        f'<text x="{_f(x)}" y="{_f(y)}" font-size="{_f(size)}" text-anchor="{anchor}" '
        f'fill="{colour}" font-weight="{weight}"{rot}>{escape(text)}</text>'
    )


class _View:
    """Local metres -> panel pixels (y up becomes y down)."""

    def __init__(self, bounds: tuple[float, float, float, float], ox: float, oy: float) -> None:
        minx, miny, maxx, maxy = bounds
        w, h = maxx - minx, maxy - miny
        self.scale = (PANEL_W - 2 * MARGIN) / max(w, h, 1.0)
        self.minx, self.maxy = minx, maxy
        self.ox, self.oy = ox + MARGIN, oy + MARGIN
        self.height = h * self.scale + 2 * MARGIN

    def p(self, xy: Point2) -> tuple[float, float]:
        return (
            self.ox + (xy[0] - self.minx) * self.scale,
            self.oy + (self.maxy - xy[1]) * self.scale,
        )

    def path(self, pts: list[Point2], closed: bool = True) -> str:
        d = " ".join(
            ("M" if i == 0 else "L") + f"{_f(x)},{_f(y)}"
            for i, (x, y) in enumerate(self.p(q) for q in pts)
        )
        return d + (" Z" if closed else "")

    def poly(self, poly: Polygon2D) -> str:
        return " ".join(self.path(r) for r in [poly.outer, *poly.holes])


def _wall_quad(w: Wall) -> list[Point2]:
    (x0, y0), (x1, y1) = w.start, w.end
    d = math.dist(w.start, w.end)
    nx, ny = -(y1 - y0) / d * w.thickness_m / 2, (x1 - x0) / d * w.thickness_m / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def _along(w: Wall, t: float) -> Point2:
    d = math.dist(w.start, w.end)
    return (
        w.start[0] + (w.end[0] - w.start[0]) * t / d,
        w.start[1] + (w.end[1] - w.start[1]) * t / d,
    )


def _opening_svg(v: _View, model: HouseModel, o: Opening) -> str:
    w = model.wall(o.host_wall_id)
    a, b = _along(w, o.offset_m), _along(w, o.offset_m + o.width_m)
    d = math.dist(w.start, w.end)
    ux, uy = (w.end[0] - w.start[0]) / d, (w.end[1] - w.start[1]) / d
    nx, ny = -uy, ux
    half = w.thickness_m / 2 + 0.01
    gap = [
        (a[0] + nx * half, a[1] + ny * half),
        (b[0] + nx * half, b[1] + ny * half),
        (b[0] - nx * half, b[1] - ny * half),
        (a[0] - nx * half, a[1] - ny * half),
    ]
    out = [f'<path d="{v.path(gap)}" fill="#ffffff" stroke="none"/>']
    if o.kind is OpeningKind.WINDOW:
        for s in (-0.35, 0.0, 0.35):
            p0 = (a[0] + nx * half * s * 2, a[1] + ny * half * s * 2)
            p1 = (b[0] + nx * half * s * 2, b[1] + ny * half * s * 2)
            out.append(f'<path d="{v.path([p0, p1], False)}" stroke="#2a6fb0" stroke-width="0.8"/>')
        return "".join(out)
    if o.kind is OpeningKind.OPENING or o.operation in (Operation.NONE, Operation.SLIDING):
        dash = ' stroke-dasharray="3,2"' if o.operation is Operation.SLIDING else ""
        out.append(f'<path d="{v.path([a, b], False)}" stroke="#999" stroke-width="0.6"{dash}/>')
        return "".join(out)
    # Swing door: leaf drawn open 90 degrees into the space it opens into.
    side = 1.0
    if o.opens_into and o.opens_into != EXTERIOR:
        sp = model.space(o.opens_into).boundary.to_shapely()
        mid = ((a[0] + b[0]) / 2 + nx * (half + 0.1), (a[1] + b[1]) / 2 + ny * (half + 0.1))
        side = 1.0 if sp.contains(Point(mid)) else -1.0
    hinge = a
    tip = (hinge[0] + nx * side * o.width_m, hinge[1] + ny * side * o.width_m)
    out.append(f'<path d="{v.path([hinge, tip], False)}" stroke="#222" stroke-width="1"/>')
    (hx, hy), (tx, ty), (ex, ey) = v.p(hinge), v.p(tip), v.p(b)
    r = o.width_m * v.scale
    sweep = 1 if (tx - hx) * (ey - hy) - (ty - hy) * (ex - hx) < 0 else 0
    out.append(
        f'<path d="M{_f(tx)},{_f(ty)} A{_f(r)},{_f(r)} 0 0 {sweep} {_f(ex)},{_f(ey)}" '
        f'fill="none" stroke="#666" stroke-width="0.6" stroke-dasharray="2,2"/>'
    )
    return "".join(out)


def _rect_dims(poly: Polygon2D) -> tuple[float, float]:
    r = poly.to_shapely().minimum_rotated_rectangle
    pts = list(r.exterior.coords)
    a, b = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])
    return (max(a, b), min(a, b))


def _dimension(v: _View, p0: Point2, p1: Point2, normal: Point2, offset: float) -> str:
    a = (p0[0] + normal[0] * offset, p0[1] + normal[1] * offset)
    b = (p1[0] + normal[0] * offset, p1[1] + normal[1] * offset)
    out = [f'<path d="{v.path([a, b], False)}" stroke="#444" stroke-width="0.7"/>']
    for p, q in ((p0, a), (p1, b)):
        out.append(f'<path d="{v.path([p, q], False)}" stroke="#888" stroke-width="0.5"/>')
        (x, y) = v.p(q)
        out.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="1.6" fill="#444"/>')
    (ax, ay), (bx, by) = v.p(a), v.p(b)
    ang = math.degrees(math.atan2(by - ay, bx - ax))
    if ang > 90 or ang < -90:
        ang += 180
    mx, my = (ax + bx) / 2, (ay + by) / 2
    out.append(_t(mx, my - 3, f"{math.dist(p0, p1):.2f} m", 9, rotate=ang))
    return "".join(out)


def _overall_dims(v: _View, model: HouseModel, level_id: str) -> str:
    shapes = [s.boundary.to_shapely() for s in model.spaces if s.level_id == level_id]
    if not shapes:
        return ""
    union = unary_union(shapes)
    rect = union.minimum_rotated_rectangle
    pts = list(rect.exterior.coords)[:4]
    c = union.centroid
    out = []
    for i in (0, 1):
        p0, p1 = pts[i], pts[i + 1]
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        d = math.dist(p0, p1)
        n = (-(p1[1] - p0[1]) / d, (p1[0] - p0[0]) / d)
        if (mx - c.x) * n[0] + (my - c.y) * n[1] < 0:
            n = (-n[0], -n[1])
        out.append(_dimension(v, p0, p1, n, 1.4))
    return "".join(out)


def _circulation(model: HouseModel) -> list[tuple[Point2, Point2, str]]:
    """Edges of the shortest-path tree from the outside, as (from, to, level) segments."""
    doors = [o for o in model.openings if o.is_passable]
    centre = {s.id: s.boundary.to_shapely().representative_point() for s in model.spaces}
    level = {s.id: s.level_id for s in model.spaces}
    adj: dict[str, list[tuple[str, Point2 | None]]] = {}
    for o in doors:
        w = model.wall(o.host_wall_id)
        mid = _along(w, o.offset_m + o.width_m / 2)
        a, b = o.connects
        adj.setdefault(a, []).append((b, mid))
        adj.setdefault(b, []).append((a, mid))
    for st in model.stairs:
        c = st.footprint.to_shapely().centroid
        adj.setdefault(st.bottom_space_id, []).append((st.top_space_id, (c.x, c.y)))
        adj.setdefault(st.top_space_id, []).append((st.bottom_space_id, (c.x, c.y)))
    seen, queue, edges = {EXTERIOR}, deque([(EXTERIOR, None)]), []
    while queue:
        node, via = queue.popleft()
        for nxt, mid in sorted(adj.get(node, []), key=lambda t: t[0]):
            if nxt in seen:
                continue
            seen.add(nxt)
            if mid is not None and nxt in centre:
                c = centre[nxt]
                edges.append((mid, (c.x, c.y), level[nxt]))
                if via is not None and node in centre:
                    edges.append((via, mid, level[node]))
            queue.append((nxt, (centre[nxt].x, centre[nxt].y) if nxt in centre else None))
    return edges


def _north(site: Site | None, x: float, y: float) -> str:
    local = site.coordinates.local if site else None
    crs = site.coordinates.horizontal_crs if site else None
    if local is not None and crs is not None and crs.status is ConfirmationStatus.USER_CONFIRMED:
        r = math.radians(local.rotation_deg)
        dx, dy = math.sin(r), math.cos(r)
        return (
            f'<path d="M{_f(x)},{_f(y)} L{_f(x + dx * 24)},{_f(y - dy * 24)}" stroke="#000" '
            f'stroke-width="1.6" marker-end="url(#arrow)"/>'
            + _t(x + dx * 32, y - dy * 32, "GN", 10, weight="bold")
        )
    reason = (
        "CRS not confirmed"
        if crs is None or crs.status is not ConfirmationStatus.LOCAL_ONLY_CONFIRMED
        else "local survey, no georeference"
    )
    return (
        f'<path d="M{_f(x)},{_f(y)} L{_f(x)},{_f(y - 24)}" stroke="#888" stroke-width="1.2" '
        f'stroke-dasharray="3,2" marker-end="url(#arrow)"/>'
        + _t(x, y - 30, "+Y", 9, colour="#888")
        + _t(x, y + 12, "north not established", 8, colour="#b00020")
        + _t(x, y + 22, f"({reason})", 8, colour="#b00020")
    )


def _site_context(v: _View, site: Site | None) -> str:
    if site is None:
        return ""
    out = []
    for f in site.features:
        g = f.geometry
        if f.kind is SiteFeatureKind.ROAD and isinstance(g, PolygonGeometry):
            out.append(f'<path d="{v.poly(g.polygon)}" fill="#e3e3e3" stroke="none"/>')
        elif isinstance(g, PolylineGeometry):
            out.append(
                f'<path d="{v.path(g.line.points, g.line.closed)}" fill="none" '
                f'stroke="#c08a3a" stroke-width="1"/>'
            )
        elif isinstance(g, PointGeometry) and f.kind is SiteFeatureKind.ACCESS_POINT:
            x, y = v.p(g.xy)
            out.append(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="3" fill="#c0392b"/>')
    if site.boundary is not None:
        out.append(
            f'<path d="{v.poly(site.boundary)}" fill="none" stroke="#111" stroke-width="1.2"/>'
        )
    if site.buildable_envelope is not None:
        out.append(
            f'<path d="{v.poly(site.buildable_envelope.polygon)}" fill="none" '
            f'stroke="#2980b9" stroke-width="1" stroke-dasharray="6,4"/>'
        )
    return "".join(out)


def _level_panel(v: _View, model: HouseModel, site: Site | None, level_id: str, circ) -> str:
    lv = model.level(level_id)
    zone_privacy = {z.id: z.privacy for z in model.zones}
    out = [_site_context(v, site)]
    for other in model.levels:
        if other.id == level_id:
            continue
        for s in model.spaces:
            if s.level_id == other.id:
                out.append(
                    f'<path d="{v.poly(s.boundary)}" fill="none" stroke="#bbb" '
                    f'stroke-width="0.6" stroke-dasharray="2,3"/>'
                )
    spaces = [s for s in model.spaces if s.level_id == level_id]
    for s in spaces:
        fill = FILL.get(zone_privacy.get(s.zone_id or ""), "#f2f2f2")
        if s.program_item_id is None and s.function.value == "storage":
            fill = "#f7f7f7"
        out.append(f'<path d="{v.poly(s.boundary)}" fill="{fill}" stroke="none"/>')
    for st in model.stairs:
        if level_id not in (st.from_level_id, st.to_level_id):
            continue
        out.append(
            f'<path d="{v.poly(st.footprint)}" fill="#ffffff" stroke="#555" stroke-width="0.8"/>'
        )
        r = st.footprint.to_shapely()
        minx, miny, maxx, maxy = r.bounds
        pts = list(r.minimum_rotated_rectangle.exterior.coords)
        long_a = max(((pts[i], pts[i + 1]) for i in range(4)), key=lambda e: math.dist(*e))
        L = math.dist(*long_a)
        steps = max(2, min(st.riser_count or 10, 20))
        ux, uy = (long_a[1][0] - long_a[0][0]) / L, (long_a[1][1] - long_a[0][1]) / L
        poly = r
        for k in range(1, steps):
            cx, cy = long_a[0][0] + ux * L * k / steps, long_a[0][1] + uy * L * k / steps
            line = LineString([(cx - uy * 50, cy + ux * 50), (cx + uy * 50, cy - ux * 50)])
            seg = line.intersection(poly)
            if not seg.is_empty and seg.geom_type == "LineString":
                out.append(
                    f'<path d="{v.path(list(seg.coords), False)}" stroke="#999" '
                    f'stroke-width="0.5"/>'
                )
        c = r.centroid
        x, y = v.p((c.x, c.y))
        up = "UP" if level_id == st.from_level_id else "DN"
        rise = abs(
            model.level(st.to_level_id).elevation_m - model.level(st.from_level_id).elevation_m
        )
        out.append(_t(x, y + 3, f"{up} {rise:.2f} m", 8, colour="#444", weight="bold"))
    for w in model.walls:
        if w.level_id == level_id:
            out.append(f'<path d="{v.path(_wall_quad(w))}" fill="{WALL_FILL[w.kind]}"/>')
    for o in model.openings:
        if model.wall(o.host_wall_id).level_id == level_id:
            out.append(_opening_svg(v, model, o))
    for a, b, lev in circ:
        if lev == level_id:
            out.append(
                f'<path d="{v.path([a, b], False)}" stroke="#d0342c" stroke-width="0.9" '
                f'stroke-dasharray="4,3" fill="none" opacity="0.8"/>'
            )
    for s in spaces:
        c = s.boundary.to_shapely().representative_point()
        x, y = v.p((c.x, c.y))
        L, W = _rect_dims(s.boundary)
        small = L * v.scale < 70
        out.append(
            _t(
                x,
                y - 4,
                s.name if not small else s.name.split(" ")[0],
                9 if not small else 7,
                weight="bold",
            )
        )
        out.append(_t(x, y + 7, f"{s.area_m2:.1f} m²", 8))
        out.append(_t(x, y + 17, f"{L:.2f} × {W:.2f}", 7, colour="#555"))
    out.append(_overall_dims(v, model, level_id))
    title = f"{lv.name} — FFL {lv.elevation_m:+.2f} m (local)"
    out.append(_t(v.ox - MARGIN + 10, v.oy - MARGIN + 18, title, 12, anchor="start", weight="bold"))
    return "".join(out)


def _section(model: HouseModel, site: Site | None, x0: float, y0: float, width: float) -> str:
    """Schematic section along the axis from the road through the building centre."""
    union = unary_union([s.boundary.to_shapely() for s in model.spaces])
    c = union.centroid
    direction = (0.0, 1.0)
    if site is not None:
        roads = [
            f.geometry
            for f in site.features
            if f.kind
            in (SiteFeatureKind.ROAD, SiteFeatureKind.FRONTAGE, SiteFeatureKind.ACCESS_POINT)
        ]
        shapes = []
        for g in roads:
            if isinstance(g, PolygonGeometry):
                shapes.append(g.polygon.to_shapely())
            elif isinstance(g, PolylineGeometry):
                shapes.append(g.line.to_shapely())
            elif isinstance(g, PointGeometry):
                shapes.append(Point(g.xy))
        if shapes:
            near = unary_union(shapes)
            from shapely.ops import nearest_points

            p = nearest_points(near, c)[0]
            d = math.dist((p.x, p.y), (c.x, c.y))
            if d > 1e-6:
                direction = ((c.x - p.x) / d, (c.y - p.y) / d)
    proj = [
        ((x - c.x) * direction[0] + (y - c.y) * direction[1])
        for s in model.spaces
        for x, y in s.boundary.outer
    ]
    lo, hi = min(proj) - 6.0, max(proj) + 6.0
    surface = site_surface(site) if site is not None else None
    ground = []
    if surface is not None:
        n = 60
        for i in range(n + 1):
            t = lo + (hi - lo) * i / n
            z = elevation_at(surface, (c.x + direction[0] * t, c.y + direction[1] * t))
            if z is not None:
                ground.append((t, z))
    bands = []
    for lv in model.levels:
        ps = [
            ((x - c.x) * direction[0] + (y - c.y) * direction[1])
            for s in model.spaces
            if s.level_id == lv.id
            for x, y in s.boundary.outer
        ]
        bands.append((lv, min(ps), max(ps)))
    zs = (
        [z for _, z in ground]
        + [lv.elevation_m for lv in model.levels]
        + [lv.elevation_m + (lv.floor_to_floor_m or 3.0) for lv in model.levels]
    )
    zmin, zmax = min(zs) - 1.0, max(zs) + 1.0
    sx = (width - 80) / (hi - lo)
    sz = min(sx, (SECTION_H - 60) / (zmax - zmin))

    def P(t: float, z: float) -> tuple[float, float]:
        return (x0 + 50 + (t - lo) * sx, y0 + SECTION_H - 25 - (z - zmin) * sz)

    out = [
        _t(
            x0 + 10,
            y0 + 16,
            "Schematic section from the road through the house "
            "(terrain interpolated from survey points; vertical scale = horizontal)",
            11,
            anchor="start",
            weight="bold",
        )
    ]
    if len(ground) >= 2:
        pts = " ".join(f"{_f(a)},{_f(b)}" for a, b in (P(t, z) for t, z in ground))
        out.append(f'<polyline points="{pts}" fill="none" stroke="#6b4a2b" stroke-width="1.6"/>')
    else:
        out.append(_t(x0 + width / 2, y0 + SECTION_H / 2, "terrain unknown", 11, colour="#b00020"))
    for lv, a, b in bands:
        h = lv.floor_to_floor_m or 3.0
        (ax, ay), (bx, by) = P(a, lv.elevation_m), P(b, lv.elevation_m + h)
        out.append(
            f'<rect x="{_f(ax)}" y="{_f(by)}" width="{_f(bx - ax)}" height="{_f(ay - by)}" '
            f'fill="#f6e7c8" fill-opacity="0.55" stroke="#333" stroke-width="1"/>'
        )
        out.append(_t(ax + 4, ay - 5, f"{lv.name} {lv.elevation_m:+.2f}", 9, anchor="start"))
    x, y = P(lo, zmin)
    out.append(_t(x, y + 14, "road side", 9, anchor="start", colour="#666"))
    x, y = P(hi, zmin)
    out.append(_t(x, y + 14, "into the site", 9, anchor="end", colour="#666"))
    return "".join(out)


def render_plan_svg(
    plan: PlanVersion,
    site: Site | None = None,
    report: EvaluationReport | None = None,
    *,
    version: int | None = None,
    banner: str | None = None,
) -> str:
    model = plan.model
    shapes = [s.boundary.to_shapely() for s in model.spaces]
    if site is not None and site.boundary is not None:
        shapes.append(site.boundary.to_shapely())
    bounds = unary_union(shapes).buffer(2.5).bounds
    levels = sorted(model.levels, key=lambda lv: -lv.elevation_m)
    cols = min(2, len(levels))
    rows = math.ceil(len(levels) / cols)
    probe = _View(bounds, 0, 0)
    panel_h = probe.height
    width = PANEL_W * cols
    height = HEADER_H + panel_h * rows + SECTION_H + 40
    circ = _circulation(model)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(width)}" height="{_f(height)}" '
        f'viewBox="0 0 {_f(width)} {_f(height)}" font-family="Helvetica, Arial, sans-serif">',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" '
        'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#000"/></marker></defs>',
        f'<rect width="{_f(width)}" height="{_f(height)}" fill="#ffffff"/>',
    ]
    ver = f" v{version}" if version else ""
    parts.append(
        _t(16, 24, f"{plan.option_id}{ver} — {plan.label}", 15, anchor="start", weight="bold")
    )
    parts.append(
        _t(
            16,
            42,
            "Design exploration generated by a constraint solver. Not reviewed, "
            "not engineered; no permit or code status.",
            10,
            anchor="start",
            colour="#b00020",
        )
    )
    if banner:
        parts.append(_t(16, 58, banner, 10, anchor="start", colour="#b00020", weight="bold"))
    if report is not None:
        hard = len(report.hard_violations)
        soft = len(report.violations) - hard
        gross = next((m.value for m in report.metrics if m.metric == "gross_floor_area_m2"), None)
        line = (
            f"Gross floor area {gross} m² · hard violations {hard} · soft violations {soft} · "
            f"compliance: {report.compliance.label}"
        )
        parts.append(_t(16, 74, line, 10, anchor="start"))
    parts.append(_north(site, width - 40, 50))
    for i, lv in enumerate(levels):
        ox = PANEL_W * (i % cols)
        oy = HEADER_H + panel_h * (i // cols)
        v = _View(bounds, ox, oy)
        parts.append(f'<g id="level-{lv.id}">{_level_panel(v, model, site, lv.id, circ)}</g>')
        parts.append(
            f'<rect x="{_f(ox + 4)}" y="{_f(oy + 2)}" width="{_f(PANEL_W - 8)}" '
            f'height="{_f(panel_h - 4)}" fill="none" stroke="#ddd"/>'
        )
    sy = HEADER_H + panel_h * rows + 10
    parts.append(f'<g id="section">{_section(model, site, 0, sy, width)}</g>')
    legend = (
        "Walls: dark = exterior, brown = retaining (earth side), grey = partition · "
        "red dashed = circulation from the front door · blue dashed = buildable envelope"
    )
    parts.append(_t(16, height - 12, legend, 9, anchor="start", colour="#555"))
    parts.append("</svg>")
    return "".join(parts) + "\n"
