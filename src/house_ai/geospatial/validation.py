"""Site validation report: every number is computed from the canonical site.

The report is derived output. It is regenerated from a site version, never
edited, and it does not approve anything: ``blockers`` lists what still
stops the human site gate.
"""

from __future__ import annotations

import math

from pydantic import Field
from shapely.geometry import Point
from shapely.ops import unary_union

from house_ai.domain.base import StrictModel
from house_ai.domain.epistemics import ConfirmationStatus
from house_ai.domain.geometry import Point2, Point3
from house_ai.domain.provenance import ArtifactRef
from house_ai.domain.records import IssueStatus, Severity
from house_ai.domain.site import Site, SiteFeatureKind, site_verification_blockers
from house_ai.domain.units import UnitDeclaration

from .crs import CrsValidationError, describe_epsg, grid_to_lonlat, inside_area_of_use
from .parcel import parcel_metrics
from .terrain import boundary_coverage, contour_interval, crossing_contours, triangle_slope_pct


class Finding(StrictModel):
    code: str
    severity: Severity
    message: str


class CoordinateStatus(StrictModel):
    drawing_units: str
    elevation_units: str
    horizontal_crs: str
    vertical_datum: str
    local_frame: str | None
    local_origin_grid: Point3 | None = None
    local_rotation_deg: float | None = None
    grid_north: str
    grid_to_true_north_deg: float | None = None
    #: Longitude/latitude of the local origin; only with a confirmed CRS.
    origin_lon_lat: tuple[float, float] | None = None


class EdgeReport(StrictModel):
    index: int
    start: Point2
    end: Point2
    length_m: float
    bearing_local_deg: float
    bearing_grid_deg: float | None
    bearing_true_deg: float | None


class BoundaryReport(StrictModel):
    present: bool
    status: str
    source_ref: str | None = None
    area_m2: float | None = None
    perimeter_m: float | None = None
    vertex_count: int | None = None
    oriented_extent_m: tuple[float, float] | None = None
    edges: list[EdgeReport] = Field(default_factory=list)


class TerrainReport(StrictModel):
    status: str
    spot_count: int
    contour_count: int
    contour_levels_m: list[float]
    contour_interval_m: float | None
    z_min_m: float | None
    z_max_m: float | None
    tin_vertices: int
    tin_triangles: int
    #: Share of the parcel inside the surveyed hull (0..1).
    parcel_coverage: float | None
    max_slope_pct: float | None
    mean_slope_pct: float | None
    spots_outside_boundary: list[str]


class FrontageReport(StrictModel):
    length_m: float
    segments: list[tuple[str, float]]
    access_points_on_frontage: list[str]


class SiteValidationReport(StrictModel):
    site_id: str
    site_ref: ArtifactRef | None = None
    coordinates: CoordinateStatus
    boundary: BoundaryReport
    terrain: TerrainReport
    frontage: FrontageReport
    feature_counts: dict[str, int]
    findings: list[Finding]
    #: What still blocks the human site gate (site_verification_blockers).
    blockers: list[str]
    open_issues: list[str]


def _units(decl: UnitDeclaration) -> str:
    return f"{decl.unit.value} ({decl.status.value})" if decl.unit else decl.status.value


def coordinate_status(site: Site) -> CoordinateStatus:
    c = site.coordinates
    crs = c.horizontal_crs
    if crs.epsg is not None:
        crs_text = f"EPSG:{crs.epsg} {crs.name or ''} ({crs.status.value})".replace("  ", " ")
    elif crs.declared_epsg is not None:
        crs_text = f"declared EPSG:{crs.declared_epsg} {crs.name or ''} ({crs.status.value})"
    else:
        crs_text = crs.status.value
    vd = c.vertical_datum
    vd_text = f"{vd.name} ({vd.status.value})" if vd.name else vd.status.value
    local = c.local
    lonlat = None
    if crs.status is ConfirmationStatus.USER_CONFIRMED and crs.epsg and local:
        lonlat = grid_to_lonlat(crs.epsg, local.origin[0], local.origin[1])
    if crs.status is ConfirmationStatus.USER_CONFIRMED and local:
        north = (
            "local +y is grid north"
            if local.rotation_deg == 0
            else f"grid north is {local.project_north_deg:+.4f}° clockwise from local +y"
        )
    elif crs.status is ConfirmationStatus.LOCAL_ONLY_CONFIRMED:
        north = "unknown: the survey is in a local frame with no georeference"
    else:
        north = "unconfirmed: the CRS is not confirmed, so grid north is not established"
    return CoordinateStatus(
        drawing_units=_units(c.source_units),
        elevation_units=_units(c.elevation_units),
        horizontal_crs=crs_text.strip(),
        vertical_datum=vd_text,
        local_frame=local.id if local else None,
        local_origin_grid=local.origin if local else None,
        local_rotation_deg=local.rotation_deg if local else None,
        grid_north=north,
        grid_to_true_north_deg=local.grid_to_true_north_deg if local else None,
        origin_lon_lat=lonlat,
    )


def validate_site(site: Site, site_ref: ArtifactRef | None = None) -> SiteValidationReport:
    findings: list[Finding] = []
    local = site.coordinates.local
    crs = site.coordinates.horizontal_crs

    boundary = BoundaryReport(
        present=site.boundary is not None,
        status=site.boundary_status.value,
        source_ref=site.boundary_source_ref,
    )
    if site.boundary is not None:
        grid_known = crs.status is ConfirmationStatus.USER_CONFIRMED
        m = parcel_metrics(site.boundary, local, grid_north_known=grid_known)
        boundary = boundary.model_copy(
            update={
                "area_m2": m.area_m2,
                "perimeter_m": m.perimeter_m,
                "vertex_count": m.vertex_count,
                "oriented_extent_m": m.oriented_extent_m,
                "edges": [EdgeReport(**e.__dict__) for e in m.edges],
            }
        )

    terrain = site.terrain
    zs = [s.z_m for s in terrain.spot_elevations] + [c.z_m for c in terrain.contours]
    surface = terrain.surface
    slopes: list[tuple[float, float]] = []
    if surface is not None:
        for ia, ib, ic in surface.triangles:
            a, b, c = surface.vertices[ia], surface.vertices[ib], surface.vertices[ic]
            area = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2
            slopes.append((triangle_slope_pct(a, b, c), area))
    finite = [(s, w) for s, w in slopes if math.isfinite(s)]
    outside = []
    if site.boundary is not None:
        parcel = site.boundary.to_shapely().buffer(1e-6)
        outside = [s.id for s in terrain.spot_elevations if not parcel.covers(Point(s.xy))]
    coverage = (
        boundary_coverage(surface, site.boundary)
        if surface is not None and site.boundary is not None
        else None
    )
    terrain_report = TerrainReport(
        status=terrain.status.value,
        spot_count=len(terrain.spot_elevations),
        contour_count=len(terrain.contours),
        contour_levels_m=sorted({c.z_m for c in terrain.contours}),
        contour_interval_m=contour_interval(terrain.contours),
        z_min_m=min(zs) if zs else None,
        z_max_m=max(zs) if zs else None,
        tin_vertices=len(surface.vertices) if surface else 0,
        tin_triangles=len(surface.triangles) if surface else 0,
        parcel_coverage=coverage,
        max_slope_pct=max(s for s, _ in finite) if finite else None,
        mean_slope_pct=(
            sum(s * w for s, w in finite) / sum(w for _, w in finite) if finite else None
        ),
        spots_outside_boundary=outside,
    )
    for a, b in crossing_contours(terrain.contours):
        findings.append(
            Finding(
                code="contours_cross",
                severity=Severity.BLOCKING,
                message=f"contours {a} and {b} have different elevations but cross",
            )
        )
    if not zs:
        findings.append(
            Finding(
                code="no_elevations",
                severity=Severity.WARNING,
                message="no surveyed elevations: terrain is unknown",
            )
        )
    elif surface is None:
        findings.append(
            Finding(
                code="no_surface",
                severity=Severity.WARNING,
                message="elevations exist but no terrain surface could be built",
            )
        )
    if coverage is not None and coverage < 0.999:
        findings.append(
            Finding(
                code="partial_terrain",
                severity=Severity.WARNING,
                message=f"{(1 - coverage) * 100:.1f}% of the parcel lies outside the surveyed "
                "elevation hull; elevation there is unknown",
            )
        )
    if outside:
        findings.append(
            Finding(
                code="spots_outside_parcel",
                severity=Severity.INFO,
                message=f"{len(outside)} spot elevation(s) lie outside the parcel boundary",
            )
        )

    frontage = [f for f in site.features if f.kind is SiteFeatureKind.FRONTAGE]
    lengths = [(f.id, f.geometry.line.length_m) for f in frontage if f.geometry.type == "polyline"]
    access_on = []
    if frontage:
        zone = unary_union([f.geometry.line.to_shapely() for f in frontage]).buffer(0.5)
        access_on = [
            f.id
            for f in site.features
            if f.kind is SiteFeatureKind.ACCESS_POINT
            and f.geometry.type == "point"
            and zone.covers(Point(f.geometry.xy))
        ]
    if not any(f.kind is SiteFeatureKind.ROAD for f in site.features):
        findings.append(
            Finding(
                code="no_roads",
                severity=Severity.INFO,
                message="no road features; frontage and access are unknown",
            )
        )
    elif not frontage:
        findings.append(
            Finding(
                code="no_frontage",
                severity=Severity.WARNING,
                message="roads exist but no boundary edge lies within 0.5 m of one",
            )
        )

    if crs.status is ConfirmationStatus.USER_CONFIRMED and crs.epsg and local:
        try:
            info = describe_epsg(crs.epsg)
            lon, lat = grid_to_lonlat(crs.epsg, local.origin[0], local.origin[1])
            if inside_area_of_use(info, lon, lat) is False:
                findings.append(
                    Finding(
                        code="outside_crs_area",
                        severity=Severity.BLOCKING,
                        message=f"the local origin maps to lon {lon:.5f}, lat {lat:.5f}, outside "
                        f"the area of use of EPSG:{crs.epsg}; the CRS or the units are likely "
                        "wrong",
                    )
                )
        except CrsValidationError as exc:
            findings.append(
                Finding(code="crs_invalid", severity=Severity.BLOCKING, message=str(exc))
            )

    counts: dict[str, int] = {}
    for f in site.features:
        counts[f.kind.value] = counts.get(f.kind.value, 0) + 1
    return SiteValidationReport(
        site_id=site.id,
        site_ref=site_ref,
        coordinates=coordinate_status(site),
        boundary=boundary,
        terrain=terrain_report,
        frontage=FrontageReport(
            length_m=sum(length for _, length in lengths),
            segments=lengths,
            access_points_on_frontage=access_on,
        ),
        feature_counts=dict(sorted(counts.items())),
        findings=findings,
        blockers=site_verification_blockers(site),
        open_issues=[
            f"[{i.severity.value}] {i.id}: {i.title}"
            for i in site.issues
            if i.status is IssueStatus.OPEN
        ],
    )


def _fmt(value: float | None, unit: str = "", digits: int = 3) -> str:
    return "unknown" if value is None else f"{value:.{digits}f}{unit}"


def report_markdown(report: SiteValidationReport) -> str:
    c, b, t, f = report.coordinates, report.boundary, report.terrain, report.frontage
    ref = report.site_ref
    lines = [
        f"# Site validation report: {report.site_id}"
        + (f" v{ref.version} (sha256 {ref.sha256[:12]})" if ref else ""),
        "",
        "Derived from the canonical site model. This report approves nothing.",
        "",
        "## Coordinate system",
        "",
        f"- Drawing units: {c.drawing_units}",
        f"- Elevation units: {c.elevation_units}",
        f"- Horizontal CRS: {c.horizontal_crs}",
        f"- Vertical datum: {c.vertical_datum}",
        f"- Local frame: {c.local_frame or 'none'}; origin (grid m) {c.local_origin_grid}; "
        f"rotation {c.local_rotation_deg}°",
        f"- Grid north: {c.grid_north}",
        f"- Grid to true north: {_fmt(c.grid_to_true_north_deg, '°', 4)} (clockwise)",
    ]
    if c.origin_lon_lat:
        lon, lat = c.origin_lon_lat
        lines.append(f"- Local origin lon/lat: {lon:.6f}, {lat:.6f}")
    lines += ["", "## Parcel boundary", "", f"- Status: {b.status}; source: {b.source_ref}"]
    if b.present:
        lines += [
            f"- Area: {_fmt(b.area_m2, ' m²', 2)}; perimeter: {_fmt(b.perimeter_m, ' m', 3)}; "
            f"vertices: {b.vertex_count}",
            f"- Oriented extent: {b.oriented_extent_m[0]:.3f} m × {b.oriented_extent_m[1]:.3f} m"
            if b.oriented_extent_m
            else "",
            "",
            "| Edge | Length (m) | Bearing local | Bearing grid | Bearing true |",
            "|---|---|---|---|---|",
        ]
        lines += [
            f"| {e.index} | {e.length_m:.3f} | {e.bearing_local_deg:.3f}° | "
            f"{_fmt(e.bearing_grid_deg, '°')} | {_fmt(e.bearing_true_deg, '°')} |"
            for e in b.edges
        ]
    else:
        lines.append("- No boundary.")
    lines += [
        "",
        "## Terrain",
        "",
        f"- Status: {t.status}; spots: {t.spot_count}; contours: {t.contour_count} "
        f"(levels {t.contour_levels_m}, interval {_fmt(t.contour_interval_m, ' m')})",
        f"- Elevation range: {_fmt(t.z_min_m, ' m')} to {_fmt(t.z_max_m, ' m')} (local)",
        f"- TIN: {t.tin_vertices} vertices, {t.tin_triangles} triangles; parcel coverage "
        + ("unknown" if t.parcel_coverage is None else f"{t.parcel_coverage * 100:.1f}%"),
        f"- Slope: max {_fmt(t.max_slope_pct, '%', 2)}, area-weighted mean "
        f"{_fmt(t.mean_slope_pct, '%', 2)}",
        "",
        "## Access and frontage",
        "",
        f"- Frontage length: {f.length_m:.3f} m in {len(f.segments)} segment(s)",
        f"- Access points on the frontage: {', '.join(f.access_points_on_frontage) or 'none'}",
        f"- Features: {report.feature_counts}",
        "",
        "## Findings",
        "",
    ]
    lines += [f"- {x.severity.value.upper()} {x.code}: {x.message}" for x in report.findings] or [
        "- none"
    ]
    lines += ["", "## Open issues", ""]
    lines += [f"- {i}" for i in report.open_issues] or ["- none"]
    lines += ["", "## Blockers for the site gate", ""]
    lines += [f"- {x}" for x in report.blockers] or [
        "- none: the site can be reviewed and approved by a human"
    ]
    return "\n".join(line for line in lines if line is not None) + "\n"
