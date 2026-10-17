"""One self-contained HTML page for reviewing a site: drawings, numbers and gaps.

Every value carries one of four labels so the owner can see how it is known:

* MEASURED: as drawn or recorded in the survey file (coordinates, z values,
  declared units), traced to ``source#handle``;
* CALCULATED: computed deterministically from measured values (area,
  lengths, slope, frontage);
* INTERPRETATION: a reading of the drawing by the layer mapping or an agent
  (which polyline is the parcel, which lines are a road), not yet confirmed;
* UNKNOWN: not established; nothing is invented to fill it.

The page approves nothing. It is static (no scripts, no external resources)
and deterministic for a given site version.
"""

from __future__ import annotations

from collections.abc import Sequence
from xml.sax.saxutils import escape

from house_ai.domain.epistemics import ConfirmationStatus, Epistemic
from house_ai.domain.records import OwnerStatement
from house_ai.domain.site import CadImportProvenance, Site, SiteFeatureKind
from house_ai.geospatial.validation import SiteValidationReport

MEASURED, CALCULATED, INTERPRETATION, UNKNOWN, CONFIRMED = (
    "measured",
    "calculated",
    "interpretation",
    "unknown",
    "confirmed",
)

_STYLE = """
body{font-family:Helvetica,Arial,sans-serif;margin:0;color:#111;background:#fff}
main{max-width:1320px;margin:0 auto;padding:16px}
h1{font-size:22px;margin:8px 0}h2{font-size:17px;margin:28px 0 8px;border-bottom:1px solid #ccc}
table{border-collapse:collapse;font-size:13px;margin:6px 0}
td,th{border:1px solid #ddd;padding:3px 7px;text-align:left;vertical-align:top}
th{background:#f4f4f4}.num{text-align:right;font-variant-numeric:tabular-nums}
.tag{display:inline-block;font-size:11px;padding:1px 6px;border-radius:8px;color:#fff}
.measured{background:#1f4e9c}.calculated{background:#2d7d46}.interpretation{background:#a15c00}
.unknown{background:#b00020}.confirmed{background:#444}
.banner{background:#fff4e5;border:1px solid #e0a040;padding:10px;margin:8px 0}
.svg{overflow-x:auto;border:1px solid #ddd}.svg svg{max-width:100%;height:auto}
ul{margin:4px 0 4px 20px;padding:0}li{margin:2px 0}
"""


def _tag(kind: str) -> str:
    return f'<span class="tag {kind}">{kind}</span>'


def _row(cells: list[str], num: set[int] = frozenset()) -> str:
    return "<tr>" + "".join(
        f'<td class="num">{c}</td>' if i in num else f"<td>{c}</td>" for i, c in enumerate(cells)
    ) + "</tr>"


def _table(head: list[str], rows: list[str]) -> str:
    return (
        "<table><tr>" + "".join(f"<th>{escape(h)}</th>" for h in head) + "</tr>"
        + "".join(rows) + "</table>"
    )


def _status_tag(status: ConfirmationStatus) -> str:
    return {
        ConfirmationStatus.UNKNOWN: _tag(UNKNOWN),
        ConfirmationStatus.DECLARED_IN_SOURCE: _tag(MEASURED) + " declared by the file, "
        "not confirmed",
        ConfirmationStatus.USER_CONFIRMED: _tag(CONFIRMED) + " confirmed by a human",
        ConfirmationStatus.LOCAL_ONLY_CONFIRMED: _tag(CONFIRMED) + " confirmed local-only",
    }[status]


def render_review_html(
    site: Site,
    report: SiteValidationReport,
    site_svg: str,
    terrain_svg: str,
    cad_imports: list[CadImportProvenance],
    statements: Sequence[OwnerStatement] = (),
) -> str:
    ref = report.site_ref
    version = f" v{ref.version} (sha256 {ref.sha256[:12]})" if ref else ""
    c, b, t, fr = report.coordinates, report.boundary, report.terrain, report.frontage
    e = escape
    parts: list[str] = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Site review {e(site.id)}</title><style>{_STYLE}</style></head><body><main>",
        f"<h1>Site review: {e(site.name)} ({e(site.id)}{e(version)})</h1>",
    ]
    if report.blockers:
        parts.append(
            '<div class="banner"><b>Not approved.</b> This site has '
            f"{len(report.blockers)} open blocker(s) (section 9). Nothing on this page has "
            "been confirmed by you yet. This page approves nothing.</div>"
        )
    else:
        parts.append(
            '<div class="banner">No blockers remain. The site still needs your explicit '
            "approval at the site gate; this page approves nothing.</div>"
        )
    parts.append(
        "<p>Labels: "
        + " ".join(
            f"{_tag(k)} {e(d)}"
            for k, d in (
                (MEASURED, "as drawn or recorded in the survey file"),
                (CALCULATED, "computed from measured values"),
                (INTERPRETATION, "a reading of the drawing, not yet confirmed"),
                (UNKNOWN, "not established"),
                (CONFIRMED, "confirmed by a human"),
            )
        )
        + "</p>"
    )

    # 1. drawing
    parts += ["<h2>1. Parcel boundary drawing</h2>", f'<div class="svg">{site_svg}</div>']

    # 2. dimensions
    bstatus = (
        _tag(CONFIRMED) + " verified by a human"
        if site.boundary_status is Epistemic.VERIFIED_FACT
        else _tag(INTERPRETATION) + " chosen by the layer mapping, not verified"
        if site.boundary is not None
        else _tag(UNKNOWN)
    )
    parts += ["<h2>2. Boundary dimensions and area</h2>", f"<p>Boundary: {bstatus}; source "
              f"<code>{e(b.source_ref or '-')}</code>. Vertices {_tag(MEASURED)} as drawn; "
              f"lengths, area and bearings {_tag(CALCULATED)}.</p>"]
    if b.present and b.area_m2 is not None and b.perimeter_m is not None:
        parts.append(
            f"<p>Area <b>{b.area_m2:.2f} m²</b>, perimeter <b>{b.perimeter_m:.3f} m</b>, "
            f"{b.vertex_count} vertices"
            + (
                f", oriented extent {b.oriented_extent_m[0]:.3f} × {b.oriented_extent_m[1]:.3f} m"
                if b.oriented_extent_m
                else ""
            )
            + f" {_tag(CALCULATED)}.</p>"
        )
        rows = [
            _row(
                [
                    str(x.index),
                    f"{x.length_m:.3f}",
                    f"{x.bearing_local_deg:.2f}°",
                    "unknown" if x.bearing_grid_deg is None else f"{x.bearing_grid_deg:.2f}°",
                    "unknown" if x.bearing_true_deg is None else f"{x.bearing_true_deg:.2f}°",
                ],
                {1, 2, 3, 4},
            )
            for x in b.edges
        ]
        parts.append(
            _table(["Edge", "Length (m)", "Bearing, local", "Bearing, grid", "Bearing, true"], rows)
        )
        parts.append(
            "<p>Local bearings are clockwise from the drawing's +Y axis. Grid and true "
            "bearings stay unknown until the coordinate system is confirmed.</p>"
        )

    # 3. road and frontage
    roads = [f for f in site.features if f.kind is SiteFeatureKind.ROAD]
    parts.append("<h2>3. Road location and frontage</h2>")
    if roads:
        rows = [
            _row(
                [
                    e(f.id),
                    f"<code>{e(f.source_ref or '-')}</code>",
                    _tag(INTERPRETATION if f.status is not Epistemic.VERIFIED_FACT else CONFIRMED),
                    f"{f.geometry.line.length_m:.3f}" if f.geometry.type == "polyline" else "-",
                ],
                {3},
            )
            for f in roads
        ]
        parts.append(_table(["Road feature", "Source", "Status", "Length (m)"], rows))
    else:
        parts.append(f"<p>No road features. Access is {_tag(UNKNOWN)}.</p>")
    parts.append(
        f"<p>Frontage: <b>{fr.length_m:.3f} m</b> in {len(fr.segments)} segment(s) "
        f"{_tag(CALCULATED)} (boundary edges within 0.5 m of a road line; geometric, not "
        "legal access).</p>"
    )
    for w in fr.road_widths:
        parts.append(
            f"<p>Road lines <code>{e(w.a)}</code> and <code>{e(w.b)}</code> run parallel, "
            f"{w.min_m:.3f}–{w.max_m:.3f} m apart {_tag(CALCULATED)}: the corridor width if "
            f"they are the two road edges {_tag(INTERPRETATION)}.</p>"
        )

    # 4. spot elevations
    parts.append("<h2>4. Surveyed elevation points</h2>")
    parts.append(
        f"<p>{t.spot_count} spot elevations {_tag(MEASURED)} (z as recorded; elevation unit "
        f"{e(c.elevation_units)}; vertical datum {e(c.vertical_datum)}). Local x/y are metres "
        "from the local origin.</p>"
    )
    checks = {(ci.source_document_id, h.spot_handle): h for ci in cad_imports
              for h in ci.height_label_checks}
    rows = []
    for s in site.terrain.spot_elevations:
        src, _, rest = (s.source_ref or "").partition("#")
        handle = rest.split(" ")[0]
        chk = checks.get((src, handle))
        label = (
            "-" if chk is None
            else f"{chk.label_value:g} {'agrees' if chk.agrees else 'DISAGREES'}"
        )
        rows.append(
            _row(
                [e(s.id), f"<code>{e(s.source_ref or '-')}</code>", f"{s.xy[0]:.3f}",
                 f"{s.xy[1]:.3f}", f"{s.z_m:.3f}", e(label)],
                {2, 3, 4},
            )
        )
    parts.append(_table(["Id", "Source", "x (m)", "y (m)", "z (m)", "Height label"], rows))
    n_checked = sum(len(ci.height_label_checks) for ci in cad_imports)
    n_agree = sum(h.agrees for ci in cad_imports for h in ci.height_label_checks)
    parts.append(
        f"<p>Height labels drawn at a point: {n_checked}, of which {n_agree} agree with the "
        "point's z. Labels are a cross-check only; they are never used as elevations.</p>"
    )

    # 5./6. terrain
    parts.append("<h2>5. Preliminary terrain model</h2>")
    if t.tin_triangles:
        parts.append(
            "<ul>"
            f"<li>Triangulated surface (TIN) from surveyed points only: {t.tin_vertices} "
            f"vertices, {t.tin_triangles} triangles {_tag(CALCULATED)}</li>"
            f"<li>Elevation range {t.z_min_m:.3f} to {t.z_max_m:.3f} m {_tag(MEASURED)}</li>"
            + (
                f"<li>Parcel covered by the surveyed area: {t.parcel_coverage * 100:.1f} % "
                f"{_tag(CALCULATED)}; elsewhere elevation is {_tag(UNKNOWN)} (never "
                "extrapolated)</li>"
                if t.parcel_coverage is not None
                else ""
            )
            + (
                f"<li>Slope: area-weighted mean {t.mean_slope_pct:.1f} %, steepest triangle "
                f"{t.max_slope_pct:.1f} % {_tag(CALCULATED)}</li>"
                if t.mean_slope_pct is not None and t.max_slope_pct is not None
                else ""
            )
            + f"<li>Spot elevations outside the parcel: {len(t.spots_outside_boundary)}</li>"
            "</ul><p>Preliminary: linear between survey points, so it misses anything between "
            "them (walls, banks, ditches).</p>"
        )
        if t.steep_triangles:
            rows = [
                _row([
                    e(", ".join(s.vertices)), f"{s.slope_pct:.0f} %", f"{s.area_m2:.2f} m²",
                    f"{s.min_angle_deg:.1f}°", e(f"{s.pair[0]} – {s.pair[1]}"),
                    f"{s.pair_distance_m:.2f} m", f"{s.pair_dz_m:.2f} m",
                    f"{s.edge_rise_pct:.0f} %",
                    e(", ".join(s.sources) or "unknown"),
                    "unknown" if s.inside_parcel is None else ("yes" if s.inside_parcel else "no"),
                    e(", ".join(s.traits) or "-"),
                ])
                for s in t.steep_triangles
            ]  # fmt: skip
            parts.append(
                f"<h3>Triangles steeper than 100 % ({len(rows)}) {_tag(CALCULATED)}</h3>"
                "<p>Each is kept as surveyed. The traits are measurements to check with the "
                "surveyor (a wall, kerb, step or a mistyped height), not causes.</p>"
            )
            parts.append(_table(
                ["Vertices", "Slope", "Area", "Min angle", "Steepest edge", "Distance", "Δz",
                 "Edge rise", "Sources", "In parcel", "Traits"],
                rows,
            ))  # fmt: skip
    else:
        parts.append(f"<p>No terrain surface: terrain is {_tag(UNKNOWN)}.</p>")
    parts += ["<h2>6. Terrain slope</h2>", f'<div class="svg">{terrain_svg}</div>']

    # 7. north
    parts += [
        "<h2>7. North and orientation</h2>",
        "<ul>",
        f"<li>Grid north: {e(c.grid_north)}</li>",
        "<li>True north: "
        + (
            f"{c.grid_to_true_north_deg:+.4f}° from grid north {_tag(CALCULATED)}"
            if c.grid_to_true_north_deg is not None
            else _tag(UNKNOWN)
        )
        + "</li>",
        f"<li>Local frame: {e(c.local_frame or 'none')}</li>",
        "</ul>",
    ]

    # 8. validation
    parts.append("<h2>8. Validation report</h2>")
    parts.append(
        "<ul>"
        + (
            "".join(f"<li><b>{e(x.severity.value)}</b> {e(x.code)}: {e(x.message)}</li>"
                    for x in report.findings)
            or "<li>no findings</li>"
        )
        + "</ul><h3>Open issues</h3><ul>"
        + ("".join(f"<li>{e(i)}</li>" for i in report.open_issues) or "<li>none</li>")
        + "</ul>"
    )
    amb = [(ci.source_document_id, a) for ci in cad_imports for a in ci.ambiguous_entities]
    if amb:
        rows = [
            _row([f"<code>{e(sid)}#{e(a.handle)}</code>", e(a.entity_type), e(a.layer),
                  e(a.reason)])
            for sid, a in amb
        ]
        parts.append(f"<h3>Entities not used ({len(amb)})</h3>")
        parts.append(_table(["Entity", "Type", "Layer", "Why"], rows))

    # 9. coordinate system
    s_units = site.coordinates.source_units.status
    e_units = site.coordinates.elevation_units.status
    h_crs = site.coordinates.horizontal_crs.status
    v_dat = site.coordinates.vertical_datum.status
    parts += [
        "<h2>9. Coordinate system and what remains to confirm</h2>",
        _table(
            ["Item", "Value", "Status"],
            [
                _row(["Drawing units", e(c.drawing_units), _status_tag(s_units)]),
                _row(["Elevation units", e(c.elevation_units), _status_tag(e_units)]),
                _row(["Horizontal CRS", e(c.horizontal_crs), _status_tag(h_crs)]),
                _row(["Vertical datum", e(c.vertical_datum), _status_tag(v_dat)]),
                _row(["Parcel boundary", e(site.boundary_status.value), bstatus]),
            ],
        ),
        "<h3>Blockers for the site gate</h3><ul>"
        + ("".join(f"<li>{e(x)}</li>" for x in report.blockers) or "<li>none</li>")
        + "</ul>",
    ]
    if statements:
        parts.append(
            "<h3>What you told us (recorded, not yet confirmed in the tool)</h3>"
            "<p>Your words, as recorded. They change no status above; the formal step is "
            "listed with each.</p><ul>"
            + "".join(
                f"<li><b>{e(st.subject)}</b>: “{e(st.words)}” ({e(st.stated_by)}, "
                f"{e(st.channel)}; recorded by {e(st.recorded_by.kind.value)}:"
                f"{e(st.recorded_by.id)})"
                + (f"<br>Formal step: <code>{e(st.pending_confirmation)}</code>"
                   if st.pending_confirmation else "")
                + "</li>"
                for st in statements
            )
            + "</ul>"
        )  # fmt: skip
    if site.assumptions:
        parts.append(
            "<h3>Assumptions</h3><ul>"
            + "".join(f"<li>{_tag(INTERPRETATION)} {e(a.statement)}</li>"
                      for a in site.assumptions)
            + "</ul>"
        )
    sources = "".join(
        f"<li><code>{e(ci.original_filename)}</code> sha256 <code>{e(ci.sha256)}</code>, "
        f"{e(ci.source_format or '')}, parsed by {e(ci.parser)} {e(ci.parser_version or '')}"
        + (f" after {e(ci.converter)} {e(ci.converter_version or '')}" if ci.converter else "")
        + "</li>"
        for ci in cad_imports
    )
    parts += ["<h2>Sources</h2>", f"<ul>{sources}</ul>", "</main></body></html>"]
    return "\n".join(parts) + "\n"
