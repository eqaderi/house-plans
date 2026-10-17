"""Site plan SVG, drawn from the canonical site model and its validation report.

Nothing is drawn that the model does not contain. North arrows show only
what is established: grid north when the CRS is confirmed, true north when
it has been computed, and otherwise an explicit "north not established".
Output is deterministic (fixed number formatting, no timestamps).
"""

from __future__ import annotations

import math
from xml.sax.saxutils import escape

from house_ai.domain.epistemics import ConfirmationStatus
from house_ai.domain.geometry import Point2, Polygon2D
from house_ai.domain.site import Site, SiteFeature, SiteFeatureKind
from house_ai.geospatial.validation import SiteValidationReport

DRAW_W = 900.0
PANEL_W = 400.0
MARGIN = 40.0
PAD_FRACTION = 0.12

COLOURS = {
    "boundary": "#111111",
    "envelope": "#2980b9",
    "frontage": "#e07b00",
    "contour": "#9a6b3f",
    "road": "#c9c9c9",
    "structure": "#b8c4d6",
    "easement": "#d4a017",
    "utility": "#8e44ad",
    "water": "#3498db",
    "tree": "#3c8d3c",
    "access": "#c0392b",
    "spot": "#1f4e9c",
    "blocker": "#b00020",
    "warning": "#a15c00",
    "muted": "#666666",
}

_FEATURE_COLOUR: dict[SiteFeatureKind, str] = {
    SiteFeatureKind.ROAD: COLOURS["road"],
    SiteFeatureKind.EXISTING_STRUCTURE: COLOURS["structure"],
    SiteFeatureKind.EASEMENT: COLOURS["easement"],
    SiteFeatureKind.UTILITY: COLOURS["utility"],
    SiteFeatureKind.WATER: COLOURS["water"],
    SiteFeatureKind.TREE: COLOURS["tree"],
    SiteFeatureKind.ACCESS_POINT: COLOURS["access"],
    SiteFeatureKind.OTHER: COLOURS["muted"],
}


def _f(v: float) -> str:
    return f"{v:.2f}"


def _nice_length(target: float) -> float:
    if target <= 0:
        return 1.0
    exp = 10 ** math.floor(math.log10(target))
    for m in (1, 2, 5, 10):
        if m * exp >= target:
            return m * exp
    return 10 * exp


def _wrap(text: str, width: int = 56) -> list[str]:
    words, lines, line = text.split(), [], ""
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    return [*lines, line] if line else lines


class _Canvas:
    def __init__(self, xs: list[float], ys: list[float]) -> None:
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        span = max(maxx - minx, maxy - miny, 1.0)
        pad = span * PAD_FRACTION
        self.minx, self.maxy = minx - pad, maxy + pad
        w, h = (maxx - minx) + 2 * pad, (maxy - miny) + 2 * pad
        self.k = (DRAW_W - 2 * MARGIN) / w
        self.height = h * self.k + 2 * MARGIN

    def p(self, xy: Point2) -> tuple[float, float]:
        return (MARGIN + (xy[0] - self.minx) * self.k, MARGIN + (self.maxy - xy[1]) * self.k)

    def path(self, pts: list[Point2], closed: bool) -> str:
        d = " ".join(
            ("M" if i == 0 else "L") + f"{_f(x)},{_f(y)}"
            for i, (x, y) in enumerate(self.p(q) for q in pts)
        )
        return d + (" Z" if closed else "")

    def polygon_path(self, poly: Polygon2D) -> str:
        return " ".join(self.path(list(r), True) for r in (poly.outer, *poly.holes))


def _feature_points(f: SiteFeature) -> list[Point2]:
    g = f.geometry
    if g.type == "polygon":
        return [p for r in (g.polygon.outer, *g.polygon.holes) for p in r]
    if g.type == "polyline":
        return list(g.line.points)
    return [g.xy]


def render_site_svg(site: Site, report: SiteValidationReport) -> str:
    pts: list[Point2] = []
    if site.boundary is not None:
        pts += [p for r in (site.boundary.outer, *site.boundary.holes) for p in r]
    if site.buildable_envelope is not None:
        env_poly = site.buildable_envelope.polygon
        pts += [p for r in (env_poly.outer, *env_poly.holes) for p in r]
    for f in site.features:
        pts += _feature_points(f)
    for c in site.terrain.contours:
        pts += c.line.points
    pts += [s.xy for s in site.terrain.spot_elevations]
    if not pts:
        pts = [(0.0, 0.0), (10.0, 10.0)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cv = _Canvas(xs, ys)
    out: list[str] = []
    add = out.append

    # Area and linear features first, then terrain, boundary, envelope, markers on top.
    for f in site.features:
        if f.kind is not SiteFeatureKind.FRONTAGE and f.geometry.type in ("polygon", "polyline"):
            colour = _FEATURE_COLOUR.get(f.kind, COLOURS["muted"])
            closed = f.geometry.type == "polygon"
            if closed:
                d = cv.polygon_path(f.geometry.polygon)
                rule = ' fill-rule="evenodd"' if f.geometry.polygon.holes else ""
            else:
                d = cv.path(list(f.geometry.line.points), f.geometry.line.closed)
                rule = ""
            fill = colour if closed else "none"
            stroke = "#888888" if closed else colour
            width = 1 if closed else (6 if f.kind is SiteFeatureKind.ROAD else 2)
            dash = (
                ' stroke-dasharray="6 4"'
                if f.kind in (SiteFeatureKind.EASEMENT, SiteFeatureKind.UTILITY)
                else ""
            )
            opacity = (
                ' fill-opacity="0.35"'
                if closed
                and f.kind not in (SiteFeatureKind.ROAD, SiteFeatureKind.EXISTING_STRUCTURE)
                else ""
            )
            add(
                f'<path d="{d}" fill="{fill}"{opacity}{rule} '
                f'stroke="{stroke}" stroke-width="{width}"{dash}><title>'
                f"{escape(f.id)} ({f.kind.value})</title></path>"
            )
    for c in sorted(site.terrain.contours, key=lambda c: (c.z_m, c.id)):
        add(
            f'<path d="{cv.path(c.line.points, c.line.closed)}" fill="none" '
            f'stroke="{COLOURS["contour"]}" stroke-width="1"><title>{escape(c.id)} '
            f"z={c.z_m:.2f} m</title></path>"
        )
        # A quarter along, so labels stay clear of edge dimensions at mid-edges.
        mid = c.line.to_shapely().interpolate(0.25, normalized=True)
        x, y = cv.p((mid.x, mid.y))
        add(
            f'<text x="{_f(x)}" y="{_f(y - 3)}" font-size="10" fill="{COLOURS["contour"]}" '
            f'text-anchor="middle">{c.z_m:.2f}</text>'
        )
    if site.boundary is not None:
        ring = site.boundary.outer
        add(
            f'<path d="{cv.polygon_path(site.boundary)}" fill="none" '
            f'stroke="{COLOURS["boundary"]}" stroke-width="2.5"><title>parcel boundary '
            f"({site.boundary_status.value})</title></path>"
        )
        for edge in report.boundary.edges:
            (x0, y0), (x1, y1) = cv.p(edge.start), cv.p(edge.end)
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
            if angle > 90 or angle < -90:
                angle += 180
            add(
                f'<text x="{_f(mx)}" y="{_f(my)}" font-size="11" text-anchor="middle" '
                f'transform="rotate({_f(angle)} {_f(mx)} {_f(my)}) translate(0 -5)">'
                f"{edge.length_m:.2f} m</text>"
            )
        for i, v in enumerate(ring):
            x, y = cv.p(v)
            add(f'<circle cx="{_f(x)}" cy="{_f(y)}" r="2.5" fill="{COLOURS["boundary"]}"/>')
            add(f'<text x="{_f(x + 4)}" y="{_f(y + 12)}" font-size="9">P{i}</text>')
    if site.buildable_envelope is not None:
        env = site.buildable_envelope
        add(
            f'<path d="{cv.polygon_path(env.polygon)}" fill="none" '
            f'stroke="{COLOURS["envelope"]}" stroke-width="1.5" stroke-dasharray="6 4">'
            f"<title>buildable envelope ({env.status.value}): {escape(env.basis)}"
            "</title></path>"
        )
    for f in site.features:
        if f.kind is SiteFeatureKind.FRONTAGE and f.geometry.type == "polyline":
            add(
                f'<path d="{cv.path(list(f.geometry.line.points), False)}" fill="none" '
                f'stroke="{COLOURS["frontage"]}" stroke-width="5" stroke-opacity="0.8">'
                f"<title>{escape(f.id)}: frontage (inference)</title></path>"
            )
        elif f.geometry.type == "point":
            x, y = cv.p(f.geometry.xy)
            if f.kind is SiteFeatureKind.TREE:
                add(
                    f'<circle cx="{_f(x)}" cy="{_f(y)}" r="7" fill="{COLOURS["tree"]}" '
                    f'fill-opacity="0.5"><title>{escape(f.id)}</title></circle>'
                )
            elif f.kind is SiteFeatureKind.ACCESS_POINT:
                add(
                    f'<path d="M{_f(x)},{_f(y - 8)} L{_f(x - 7)},{_f(y + 5)} '
                    f'L{_f(x + 7)},{_f(y + 5)} Z" fill="{COLOURS["access"]}">'
                    f"<title>{escape(f.id)}: access</title></path>"
                )
            else:
                colour = _FEATURE_COLOUR.get(f.kind, COLOURS["muted"])
                add(
                    f'<circle cx="{_f(x)}" cy="{_f(y)}" r="3" fill="{colour}">'
                    f"<title>{escape(f.id)} ({f.kind.value})</title></circle>"
                )
    for s in sorted(site.terrain.spot_elevations, key=lambda s: s.id):
        x, y = cv.p(s.xy)
        c = COLOURS["spot"]
        add(
            f'<path d="M{_f(x - 4)},{_f(y)} L{_f(x + 4)},{_f(y)} M{_f(x)},{_f(y - 4)} '
            f'L{_f(x)},{_f(y + 4)}" stroke="{c}" stroke-width="1.5"/>'
        )
        add(f'<text x="{_f(x + 5)}" y="{_f(y - 4)}" font-size="10" fill="{c}">{s.z_m:.2f}</text>')

    add(_scale_bar(cv))
    add(_north(site, cv))
    add(_panel(site, report))

    height = max(cv.height, _panel_height(site, report))
    width = DRAW_W + PANEL_W
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(width)}" height="{_f(height)}" '
        f'viewBox="0 0 {_f(width)} {_f(height)}" font-family="Helvetica, Arial, sans-serif">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
    )
    return head + "".join(out) + "</svg>\n"


def _scale_bar(cv: _Canvas) -> str:
    length = _nice_length((DRAW_W - 2 * MARGIN) * 0.2 / cv.k)
    px = length * cv.k
    x0, y0 = MARGIN, cv.height - 15
    return (
        f'<g><path d="M{_f(x0)},{_f(y0)} L{_f(x0 + px)},{_f(y0)}" stroke="#000" '
        f'stroke-width="3"/><path d="M{_f(x0)},{_f(y0 - 5)} L{_f(x0)},{_f(y0 + 5)} '
        f'M{_f(x0 + px)},{_f(y0 - 5)} L{_f(x0 + px)},{_f(y0 + 5)}" stroke="#000"/>'
        f'<text x="{_f(x0 + px / 2)}" y="{_f(y0 - 7)}" font-size="11" text-anchor="middle">'
        f"{length:g} m</text></g>"
    )


def _arrow(cx: float, cy: float, vec: Point2, label: str, colour: str, dashed: bool) -> str:
    """vec is a direction in LOCAL coordinates (+y up)."""
    n = math.hypot(*vec)
    dx, dy = vec[0] / n * 30, -vec[1] / n * 30
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    return (
        f'<path d="M{_f(cx - dx)},{_f(cy - dy)} L{_f(cx + dx)},{_f(cy + dy)}" '
        f'stroke="{colour}" stroke-width="2"{dash}/>'
        f'<circle cx="{_f(cx + dx)}" cy="{_f(cy + dy)}" r="3.5" fill="{colour}"/>'
        f'<text x="{_f(cx + dx * 1.35)}" y="{_f(cy + dy * 1.35 + 4)}" font-size="11" '
        f'text-anchor="middle" fill="{colour}">{escape(label)}</text>'
    )


def _north(site: Site, cv: _Canvas) -> str:
    cx, cy = DRAW_W - MARGIN - 40, MARGIN + 45
    local = site.coordinates.local
    crs = site.coordinates.horizontal_crs
    parts = ["<g>"]
    if local is not None and crs.status is ConfirmationStatus.USER_CONFIRMED:
        r = math.radians(local.rotation_deg)
        parts.append(_arrow(cx, cy, (math.sin(r), math.cos(r)), "GN", "#000000", False))
        if local.grid_to_true_north_deg is not None:
            t = math.radians(local.rotation_deg + local.grid_to_true_north_deg)
            parts.append(
                _arrow(cx - 50, cy, (math.sin(t), math.cos(t)), "TN", COLOURS["access"], False)
            )
            parts.append(
                f'<text x="{_f(cx - 25)}" y="{_f(cy + 52)}" font-size="9" text-anchor="middle">'
                f"TN {local.grid_to_true_north_deg:+.3f}° from GN</text>"
            )
    else:
        reason = (
            "local survey, no georeference"
            if crs.status is ConfirmationStatus.LOCAL_ONLY_CONFIRMED
            else "CRS not confirmed"
        )
        parts.append(_arrow(cx, cy, (0.0, 1.0), "+Y", COLOURS["muted"], True))
        parts.append(
            f'<text x="{_f(cx)}" y="{_f(cy + 48)}" font-size="9" text-anchor="middle" '
            f'fill="{COLOURS["blocker"]}">north not established</text>'
            f'<text x="{_f(cx)}" y="{_f(cy + 59)}" font-size="9" text-anchor="middle" '
            f'fill="{COLOURS["blocker"]}">({reason})</text>'
        )
    parts.append("</g>")
    return "".join(parts)


def _panel_lines(site: Site, report: SiteValidationReport) -> list[tuple[str, str, int]]:
    """(text, colour, font size) lines for the side panel."""
    c, b, t, f = report.coordinates, report.boundary, report.terrain, report.frontage
    ref = report.site_ref
    subtitle = f"site {site.id}" + (f" v{ref.version} (sha256 {ref.sha256[:12]})" if ref else "")
    lines: list[tuple[str, str, int]] = [(site.name, "#000", 16), (subtitle, COLOURS["muted"], 11)]

    def section(name: str) -> None:
        lines.append(("", "#000", 6))
        lines.append((name, "#000", 13))

    def text(value: str, colour: str = "#000") -> None:
        for i, chunk in enumerate(_wrap(value)):
            lines.append((("  " if i else "") + chunk, colour, 11))

    section("Coordinate system")
    text(f"Drawing units: {c.drawing_units}")
    text(f"Elevation units: {c.elevation_units}")
    text(f"Horizontal CRS: {c.horizontal_crs}")
    text(f"Vertical datum: {c.vertical_datum}")
    text(f"North: {c.grid_north}")
    if c.local_origin_grid:
        e, n, z = c.local_origin_grid
        text(f"Local origin (grid m): E {e:.3f} N {n:.3f} Z {z:.3f}")
    section("Parcel")
    text(f"Boundary status: {b.status}")
    if b.present:
        text(f"Area {b.area_m2:.2f} m²; perimeter {b.perimeter_m:.2f} m; {b.vertex_count} vertices")
    else:
        text("No parcel boundary", COLOURS["blocker"])
    text(f"Frontage: {f.length_m:.2f} m")
    section("Terrain")
    text(f"{t.status}: {t.spot_count} spots, {t.contour_count} contours")
    if t.z_min_m is not None:
        text(f"Elevation {t.z_min_m:.2f} to {t.z_max_m:.2f} m (local)")
    if t.contour_interval_m is not None:
        text(f"Contour interval {t.contour_interval_m:g} m")
    section("Blockers for the site gate")
    for item in report.blockers or ["none"]:
        text(f"• {item}", COLOURS["blocker"] if report.blockers else "#000")
    warnings = list(report.findings)
    section("Findings and open issues")
    for x in warnings:
        text(f"• {x.severity.value}: {x.message}", COLOURS["warning"])
    for issue in report.open_issues:
        text(f"• {issue}", COLOURS["warning"])
    if not warnings and not report.open_issues:
        text("none")
    lines.append(("", "#000", 6))
    text(
        "Design-exploration drawing generated from the canonical site model. It is not a "
        "survey and approves nothing.",
        COLOURS["muted"],
    )
    return lines


def _panel_height(site: Site, report: SiteValidationReport) -> float:
    return MARGIN + sum(size + 4 for _, _, size in _panel_lines(site, report)) + MARGIN


def _panel(site: Site, report: SiteValidationReport) -> str:
    x = DRAW_W + 10
    y = MARGIN
    parts = [
        f'<rect x="{_f(DRAW_W)}" y="0" width="{_f(PANEL_W)}" height="100%" fill="#f6f6f6"/>'
    ]
    for value, colour, size in _panel_lines(site, report):
        y += size + 4
        if value:
            weight = ' font-weight="bold"' if size >= 13 else ""
            parts.append(
                f'<text x="{_f(x)}" y="{_f(y)}" font-size="{size}" fill="{colour}"{weight}>'
                f"{escape(value)}</text>"
            )
    return "<g>" + "".join(parts) + "</g>"
