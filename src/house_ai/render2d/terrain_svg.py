"""Terrain slope SVG: the surveyed TIN shaded by slope, with spot heights.

Drawn only from the canonical site's terrain surface. Contour lines here are
calculated from the TIN (linear interpolation between surveyed points) and are
labelled as such; they are not surveyed contours. Outside the TIN, elevation
is unknown and nothing is drawn. North follows the same rule as the site plan.
"""

from __future__ import annotations

import math
from xml.sax.saxutils import escape

from house_ai.domain.geometry import Point2, Point3
from house_ai.domain.site import Site
from house_ai.geospatial.terrain import triangle_slope_pct
from house_ai.geospatial.validation import SiteValidationReport

from .site_svg import COLOURS, DRAW_W, MARGIN, _Canvas, _f, _nice_length, _north, _scale_bar

#: Slope classes (upper bound in percent, fill colour, label).
SLOPE_CLASSES: list[tuple[float, str, str]] = [
    (5.0, "#e8f3e0", "0–5 %"),
    (15.0, "#c7e3a8", "5–15 %"),
    (25.0, "#f3e08a", "15–25 %"),
    (35.0, "#f0b45c", "25–35 %"),
    (50.0, "#e07b39", "35–50 %"),
    (100.0, "#c0392b", "50–100 %"),
    (math.inf, "#6d1a36", "> 100 % (check)"),
]

LEGEND_W = 260.0


def slope_class(slope_pct: float) -> int:
    return next(i for i, (upper, _, _) in enumerate(SLOPE_CLASSES) if slope_pct <= upper)


def contour_interval_for(z_min: float, z_max: float) -> float:
    """A readable interval giving roughly 5–15 calculated contours."""
    span = z_max - z_min
    if span <= 0:
        return 1.0
    for step in (0.1, 0.2, 0.25, 0.5, 1.0, 2.0, 2.5, 5.0, 10.0, 20.0, 50.0):
        if span / step <= 15:
            return step
    return _nice_length(span / 10)


def _segment_at(z: float, a: Point3, b: Point3, c: Point3) -> tuple[Point2, Point2] | None:
    """Where the plane through a, b, c crosses elevation z, as a segment."""
    pts: list[Point2] = []
    for p, q in ((a, b), (b, c), (c, a)):
        if (p[2] - z) * (q[2] - z) < 0:
            t = (z - p[2]) / (q[2] - p[2])
            pts.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return (pts[0], pts[1]) if len(pts) == 2 else None


def render_terrain_svg(site: Site, report: SiteValidationReport) -> str:
    surface = site.terrain.surface
    pts: list[Point2] = []
    if site.boundary is not None:
        pts += list(site.boundary.outer)
    if surface is not None:
        pts += [(x, y) for x, y, _ in surface.vertices]
    pts += [s.xy for s in site.terrain.spot_elevations]
    if not pts:
        pts = [(0.0, 0.0), (10.0, 10.0)]
    cv = _Canvas([p[0] for p in pts], [p[1] for p in pts])
    out: list[str] = []
    add = out.append
    counts = [0.0] * len(SLOPE_CLASSES)
    interval = None
    if surface is not None:
        for ia, ib, ic in surface.triangles:
            a, b, c = surface.vertices[ia], surface.vertices[ib], surface.vertices[ic]
            slope = triangle_slope_pct(a, b, c)
            k = slope_class(slope)
            counts[k] += abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
            add(
                f'<path d="{cv.path([a[:2], b[:2], c[:2]], True)}" fill="{SLOPE_CLASSES[k][1]}" '
                f'stroke="#ffffff" stroke-width="0.6"><title>slope {slope:.1f} %</title></path>'
            )
        zs = [v[2] for v in surface.vertices]
        interval = contour_interval_for(min(zs), max(zs))
        level = math.ceil(min(zs) / interval) * interval
        while level < max(zs):
            segs = [
                s
                for ia, ib, ic in surface.triangles
                if (
                    s := _segment_at(
                        level, surface.vertices[ia], surface.vertices[ib], surface.vertices[ic]
                    )
                )
                is not None
            ]
            major = abs(level / (interval * 5) - round(level / (interval * 5))) < 1e-9
            d = " ".join(f"M{_f(cv.p(p)[0])},{_f(cv.p(p)[1])} L{_f(cv.p(q)[0])},{_f(cv.p(q)[1])}"
                         for p, q in segs)
            if d:
                add(
                    f'<path d="{d}" fill="none" stroke="{COLOURS["contour"]}" '
                    f'stroke-width="{1.4 if major else 0.7}" stroke-dasharray="5 3">'
                    f"<title>calculated contour {level:.2f} m</title></path>"
                )
            level = round(level + interval, 9)
    if site.boundary is not None:
        add(
            f'<path d="{cv.polygon_path(site.boundary)}" fill="none" '
            f'stroke="{COLOURS["boundary"]}" stroke-width="2.2"/>'
        )
    for s in site.terrain.spot_elevations:
        x, y = cv.p(s.xy)
        ref = escape(s.source_ref or s.id)
        add(
            f'<g><circle cx="{_f(x)}" cy="{_f(y)}" r="3" fill="{COLOURS["spot"]}">'
            f"<title>{escape(s.id)} ({ref}): {s.z_m:.3f} m</title></circle>"
            f'<text x="{_f(x + 5)}" y="{_f(y - 4)}" font-size="9" fill="{COLOURS["spot"]}">'
            f"{s.z_m:.2f}</text></g>"
        )
    add(_scale_bar(cv))
    add(_north(site, cv))
    legend = _legend(report, counts, interval, surface is not None)
    height = max(cv.height, 40.0 + 18.0 * len(legend))
    width = DRAW_W + LEGEND_W
    add(f'<g transform="translate({_f(DRAW_W)},0)">')
    for i, (text, colour, swatch) in enumerate(legend):
        y = MARGIN + 18.0 * i
        if swatch:
            add(f'<rect x="0" y="{_f(y - 10)}" width="14" height="12" fill="{swatch}"/>')
        add(
            f'<text x="{20 if swatch else 0}" y="{_f(y)}" font-size="11" fill="{colour}">'
            f"{escape(text)}</text>"
        )
    add("</g>")
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(width)}" height="{_f(height)}" '
        f'viewBox="0 0 {_f(width)} {_f(height)}" font-family="Helvetica, Arial, sans-serif">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
    )
    return head + "".join(out) + "</svg>\n"


def _fmt(value: float | None, digits: int) -> str:
    return "unknown" if value is None else f"{value:.{digits}f}"


def _legend(
    report: SiteValidationReport, area_by_class: list[float], interval: float | None, has_tin: bool
) -> list[tuple[str, str, str | None]]:
    t = report.terrain
    lines: list[tuple[str, str, str | None]] = [
        ("TERRAIN SLOPE (preliminary)", "#000", None),
        ("Calculated from surveyed points only.", COLOURS["muted"], None),
    ]
    if not has_tin:
        return [*lines, ("No terrain surface: elevation unknown.", COLOURS["blocker"], None)]
    total = sum(area_by_class) or 1.0
    for (_, colour, label), area in zip(SLOPE_CLASSES, area_by_class, strict=True):
        lines.append((f"{label}: {100 * area / total:.0f} % of TIN area", "#000", colour))
    lines += [
        (f"Dashed: contours every {interval:g} m,", COLOURS["contour"], None),
        ("interpolated from the TIN, not surveyed.", COLOURS["contour"], None),
        (f"Spot heights: {t.spot_count}; z {_fmt(t.z_min_m, 2)} to {_fmt(t.z_max_m, 2)} m",
         COLOURS["spot"], None),
        (f"Whole TIN mean {_fmt(t.mean_slope_pct, 1)} %, max {_fmt(t.max_slope_pct, 1)} %", "#000",
         None),
        (f"Parcel mean {_fmt(t.parcel_mean_slope_pct, 1)} % (horizontal area weighted)",
         "#000", None),
        ("Outside the triangles: elevation unknown.", COLOURS["muted"], None),
        (f"Vertical datum: {report.coordinates.vertical_datum}", COLOURS["muted"], None),
    ]
    return lines
