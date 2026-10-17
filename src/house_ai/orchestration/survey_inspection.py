"""Read-only inspection of survey files before anything is imported.

``house-ai site inspect`` runs this on the owner's real files. It never
writes next to them: it hashes each file before and after, reads DWG only
through a private temporary copy, and reports what the file *declares*.
Coordinate magnitudes are reported as numbers, never as evidence of a CRS.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from pathlib import Path

from pydantic import Field
from shapely.geometry import Polygon

from house_ai.cad.base import CadExtraction
from house_ai.cad.dwg_oda import DwgConversionError, adapter_for
from house_ai.cad.dxf_ezdxf import DxfReadError
from house_ai.cad.formats import detect_format
from house_ai.cad.layers import UNCLASSIFIED, LayerMapping, LayerRole, suggest_roles
from house_ai.cad.site_extract import MappedLayerSiteExtractor, has_numeric_elevation_label
from house_ai.domain.base import StrictModel
from house_ai.domain.coordinates import LocalCoordinateSystem, SurveyTransform
from house_ai.domain.site import AmbiguousEntity
from house_ai.domain.units import METRES_PER_UNIT, LengthUnit, unit_from_insunits
from house_ai.geospatial.crs import CrsValidationError, describe_epsg
from house_ai.storage.project_store import default_source_id

#: $INSUNITS codes and what AutoCAD calls them, for the report.
INSUNITS_NAMES = {
    0: "unitless",
    1: "inches",
    2: "feet",
    3: "miles",
    4: "millimetres",
    5: "centimetres",
    6: "metres",
    7: "kilometres",
    10: "yards",
    14: "decimetres",
    21: "US survey feet",
}
MAX_CANDIDATES = 10


class LayerReport(StrictModel):
    name: str
    entity_count: int
    entity_types: dict[str, int]
    mapped_role: str | None = None
    suggested_role: str | None = None
    suggestion_basis: str | None = None


class ElevationLayerReport(StrictModel):
    layer: str
    points_with_z: int
    points_at_zero: int
    constant_z_lines: int
    zero_z_lines: int
    varying_z_lines: int
    numeric_labels: int
    z_min: float | None
    z_max: float | None


class BoundaryCandidate(StrictModel):
    handle: str
    layer: str
    vertices: int
    area_source_units2: float
    perimeter_source_units: float
    #: Only when the file declares its unit; still unconfirmed.
    area_m2_if_declared_unit: float | None = None
    has_arcs: bool = False


class FileInspection(StrictModel):
    path: str
    file_name: str
    size_bytes: int
    sha256: str
    unchanged_after_inspection: bool
    detected_format: str
    format_evidence: str
    readable: bool
    read_error: str | None = None
    parser: str | None = None
    parser_version: str | None = None
    converter: str | None = None
    converter_version: str | None = None
    converted_sha256: str | None = None
    insunits_code: int | None = None
    insunits_meaning: str | None = None
    drawing_units_status: str = "unknown"
    header: dict[str, object] = Field(default_factory=dict)
    geodata: dict[str, object] | None = None
    declared_epsg: int | None = None
    declared_crs_name: str | None = None
    crs_status: str = "unknown"
    extents_source_units: tuple[float, float, float, float] | None = None
    entity_counts: dict[str, int] = Field(default_factory=dict)
    layers: list[LayerReport] = Field(default_factory=list)
    elevations: list[ElevationLayerReport] = Field(default_factory=list)
    boundary_candidates: list[BoundaryCandidate] = Field(default_factory=list)
    boundary_candidate_basis: str | None = None
    ambiguous: list[AmbiguousEntity] = Field(default_factory=list)
    unmapped_layers: list[str] = Field(default_factory=list)
    unsupported_entities: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    needs_confirmation: list[str] = Field(default_factory=list)


class SurveyInspection(StrictModel):
    note: str = (
        "Read-only inspection. Values are what the files declare; nothing here is "
        "confirmed, and coordinate magnitudes are not evidence of a CRS or unit."
    )
    files: list[FileInspection]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_files(paths: list[Path], mapping: LayerMapping | None = None) -> SurveyInspection:
    return SurveyInspection(files=[inspect_file(Path(p), mapping) for p in paths])


def inspect_file(path: Path, mapping: LayerMapping | None = None) -> FileInspection:
    before = _sha256(path)
    fmt = detect_format(path)
    report = FileInspection(
        path=str(path),
        file_name=path.name,
        size_bytes=path.stat().st_size,
        sha256=before,
        unchanged_after_inspection=True,
        detected_format=fmt.label,
        format_evidence=fmt.evidence,
        readable=False,
    )
    try:
        extraction = adapter_for(path).extract_cad(path, mapping.as_dict() if mapping else {})
    except (DxfReadError, DwgConversionError, ValueError) as exc:
        report.read_error = str(exc)
        report.needs_confirmation = [
            f"{path.name} could not be read as CAD ({fmt.label}). Provide it as DXF or DWG, or "
            "say what format it is and what it contains."
        ]
    else:
        _fill(report, extraction, mapping)
    report.unchanged_after_inspection = _sha256(path) == before
    if not report.unchanged_after_inspection:
        report.warnings.append("THE FILE CHANGED DURING INSPECTION; do not use this report")
    return report


def _fill(report: FileInspection, ext: CadExtraction, mapping: LayerMapping | None) -> None:
    insp = ext.inspection
    assert insp is not None
    report.readable = True
    report.parser, report.parser_version = insp.parser, insp.parser_version
    report.converter, report.converter_version = insp.converter, insp.converter_version
    report.converted_sha256 = insp.converted_sha256
    report.detected_format = insp.source_format or report.detected_format
    report.insunits_code = insp.declared_insunits
    report.insunits_meaning = INSUNITS_NAMES.get(insp.declared_insunits or 0, "unsupported code")
    unit = unit_from_insunits(insp.declared_insunits)
    report.drawing_units_status = (
        f"declared in source as {unit.value}; needs your confirmation" if unit else "unknown"
    )
    report.header = insp.header
    report.geodata = insp.geodata
    report.declared_epsg = insp.declared_epsg
    if insp.declared_epsg:
        try:
            report.declared_crs_name = describe_epsg(insp.declared_epsg).name
        except CrsValidationError as exc:
            report.warnings.append(str(exc))
        report.crs_status = (
            f"declared in source as EPSG:{insp.declared_epsg}; needs your confirmation"
        )
    else:
        report.crs_status = "unknown: the file declares no coordinate reference system"
    report.extents_source_units = insp.extents
    report.entity_counts = insp.entity_counts
    report.unsupported_entities = ext.unsupported_entities
    report.warnings += insp.warnings

    suggestions = suggest_roles(list(insp.layers))
    for name, count in insp.layers.items():
        role = mapping.role_of(name) if mapping else None
        sug = suggestions.get(name)
        report.layers.append(
            LayerReport(
                name=name,
                entity_count=count,
                entity_types=insp.layer_entity_types.get(name, {}),
                mapped_role=(role.value if role else UNCLASSIFIED) if mapping else None,
                suggested_role=sug[0].value if sug else None,
                suggestion_basis=f"layer name contains {sug[1]!r}" if sug else None,
            )
        )
    report.elevations = _elevations(ext)
    _boundary_candidates(report, ext, mapping, suggestions, unit)
    if mapping is not None:
        transform = _source_frame(ext)
        # The id `source add` would give this file, so `source_id#handle` keys match.
        source_id = default_source_id(Path(report.file_name))
        result = MappedLayerSiteExtractor(mapping, source_id).extract(ext, transform)
        report.ambiguous = result.ambiguous
        report.unmapped_layers = result.unrecognized_layers
        report.warnings += result.warnings + result.conflicts
    report.needs_confirmation = _questions(report, mapping, unit)


def _source_frame(ext: CadExtraction) -> SurveyTransform:
    """Identity scale, origin at the extents corner: source units, small numbers."""
    e = ext.inspection.extents if ext.inspection else None
    origin = (e[0], e[1], 0.0) if e else (0.0, 0.0, 0.0)
    return SurveyTransform(1.0, 1.0, LocalCoordinateSystem(id="source", origin=origin))


def _elevations(ext: CadExtraction) -> list[ElevationLayerReport]:
    stats: dict[str, Counter[str]] = {}
    zs: dict[str, list[float]] = {}
    for p in ext.points:
        c = stats.setdefault(p.layer, Counter())
        if p.entity_type in ("TEXT", "MTEXT"):
            if has_numeric_elevation_label(p.text):
                c["numeric_labels"] += 1
        elif p.z:
            c["points_with_z"] += 1
            zs.setdefault(p.layer, []).append(p.z)
        else:
            c["points_at_zero"] += 1
    for line in ext.polylines:
        c = stats.setdefault(line.layer, Counter())
        if line.elevation is None:
            c["varying_z_lines"] += 1
            zs.setdefault(line.layer, []).extend(line.zs)
        elif line.elevation == 0:
            c["zero_z_lines"] += 1
        else:
            c["constant_z_lines"] += 1
            zs.setdefault(line.layer, []).append(line.elevation)
    out = []
    for layer, c in sorted(stats.items()):
        if not any(c[k] for k in ("points_with_z", "constant_z_lines", "varying_z_lines",
                                  "numeric_labels")):
            continue
        values = zs.get(layer, [])
        out.append(
            ElevationLayerReport(
                layer=layer,
                points_with_z=c["points_with_z"],
                points_at_zero=c["points_at_zero"],
                constant_z_lines=c["constant_z_lines"],
                zero_z_lines=c["zero_z_lines"],
                varying_z_lines=c["varying_z_lines"],
                numeric_labels=c["numeric_labels"],
                z_min=min(values) if values else None,
                z_max=max(values) if values else None,
            )
        )
    return out


def _boundary_candidates(
    report: FileInspection,
    ext: CadExtraction,
    mapping: LayerMapping | None,
    suggestions: dict[str, tuple[LayerRole, str]],
    unit: LengthUnit | None,
) -> None:
    if mapping is not None and any(r is LayerRole.BOUNDARY for r in mapping.layers.values()):
        names = [layer.name for layer in report.layers]
        layers = {n for n in names if mapping.role_of(n) is LayerRole.BOUNDARY}
        basis = "closed polylines on the layers your mapping marks as boundary"
    else:
        layers = {n for n, (role, _) in suggestions.items() if role is LayerRole.BOUNDARY}
        basis = (
            "closed polylines on layers whose names suggest a boundary (a hint only)"
            if layers
            else "no boundary layer identified: the largest closed polylines in the drawing"
        )
    scale = METRES_PER_UNIT[unit] if unit else None
    found = []
    for line in ext.polylines:
        if layers and line.layer not in layers:
            continue
        pts = line.points
        closed = line.closed or (len(pts) >= 4 and math.dist(pts[0], pts[-1]) < 1e-6)
        if not closed or len(pts) < 3:
            continue
        ring = pts[:-1] if math.dist(pts[0], pts[-1]) < 1e-6 else pts
        if len(ring) < 3:
            continue
        x0, y0 = ring[0]
        try:
            shape = Polygon([(x - x0, y - y0) for x, y in ring])  # shifted: small numbers
        except Exception:
            continue
        area, perim = float(abs(shape.area)), float(shape.length)
        found.append(
            BoundaryCandidate(
                handle=line.handle,
                layer=line.layer,
                vertices=len(ring),
                area_source_units2=area,
                perimeter_source_units=perim,
                area_m2_if_declared_unit=area * scale**2 if scale else None,
                has_arcs=line.has_arcs,
            )
        )
    found.sort(key=lambda c: -c.area_source_units2)
    report.boundary_candidates = found[:MAX_CANDIDATES]
    report.boundary_candidate_basis = basis
    if len(found) > MAX_CANDIDATES:
        report.warnings.append(f"{len(found)} closed polylines; only the largest 10 are listed")


def _questions(
    report: FileInspection, mapping: LayerMapping | None, unit: LengthUnit | None
) -> list[str]:
    q = []
    if unit:
        q.append(f"Confirm the drawing unit: the file declares {unit.value}.")
    else:
        q.append(
            f"State the drawing unit: $INSUNITS is {report.insunits_code!r} "
            f"({report.insunits_meaning})."
        )
    q.append(
        "Confirm the elevation unit (DXF z values use the drawing unit unless the surveyor "
        "says otherwise)."
    )
    if report.declared_epsg:
        q.append(
            f"Confirm the horizontal CRS: the file declares EPSG:{report.declared_epsg} "
            f"({report.declared_crs_name})."
        )
    else:
        q.append(
            "State the horizontal CRS as an EPSG code (for UTM: zone, hemisphere and datum, "
            "e.g. ETRS89 / UTM 32N = EPSG:25832), or confirm the survey is local-only."
        )
    q.append(
        "State the vertical datum of the elevations (e.g. a national height system) or the "
        "local benchmark they are relative to."
    )
    if mapping is None:
        q.append(
            "Write a layer mapping (layer -> role); suggested roles in this report are hints "
            "from layer names only."
        )
    if len(report.boundary_candidates) != 1:
        q.append(
            f"Identify the parcel boundary: {len(report.boundary_candidates)} candidate closed "
            "polylines were found."
        )
    else:
        q.append(
            f"Confirm that polyline {report.boundary_candidates[0].handle} on layer "
            f"{report.boundary_candidates[0].layer!r} is the legal parcel boundary."
        )
    if any(e.points_at_zero or e.zero_z_lines for e in report.elevations):
        q.append("Some elevation entities have z = 0: say whether 0 is a real elevation here.")
    if report.ambiguous:
        q.append(f"Review {len(report.ambiguous)} ambiguous entities listed in this report.")
    return q


def inspection_markdown(insp: SurveyInspection) -> str:
    lines = ["# Survey inspection (read-only)", "", insp.note, ""]
    for f in insp.files:
        lines += [
            f"## {f.file_name}",
            "",
            "### 1. File format",
            f"- {f.detected_format} ({f.format_evidence})",
            f"- {f.size_bytes} bytes, sha256 `{f.sha256}`; unchanged after inspection: "
            f"{'yes' if f.unchanged_after_inspection else 'NO'}",
        ]
        if not f.readable:
            lines += [f"- Not readable as CAD: {f.read_error}", ""]
        else:
            lines += [
                "",
                "### 2. Drawing units",
                f"- $INSUNITS = {f.insunits_code} ({f.insunits_meaning}); status: "
                f"{f.drawing_units_status}",
                f"- Header: {f.header}",
                "",
                "### 3. CAD layers",
                "",
                "| Layer | Entities | Types | Mapped role | Suggested role (hint) |",
                "|---|---|---|---|---|",
            ]
            lines += [
                f"| {la.name} | {la.entity_count} | {la.entity_types} | {la.mapped_role or '-'} | "
                f"{la.suggested_role or '-'}"
                + (f" ({la.suggestion_basis})" if la.suggestion_basis else "")
                + " |"
                for la in f.layers
            ]
            lines += [
                "",
                "### 4. Coordinate metadata",
                f"- GEODATA: {f.geodata if f.geodata else 'none'}",
                f"- Declared EPSG: {f.declared_epsg or 'none'}"
                + (f" ({f.declared_crs_name})" if f.declared_crs_name else ""),
                f"- Extents (source units): {f.extents_source_units}",
                "",
                "### 5. CRS verification status",
                f"- {f.crs_status}",
                "- Coordinate magnitudes are not evidence of a CRS, zone or unit.",
                "",
                "### 6. Candidate parcel boundary",
                f"- Basis: {f.boundary_candidate_basis}",
            ]
            lines += [
                f"- {c.handle} on {c.layer!r}: {c.vertices} vertices, area "
                f"{c.area_source_units2:.3f} unit², perimeter {c.perimeter_source_units:.3f}"
                + (
                    f" (= {c.area_m2_if_declared_unit:.2f} m² if the declared unit is right)"
                    if c.area_m2_if_declared_unit is not None
                    else ""
                )
                + (" [has arcs: chord approximation]" if c.has_arcs else "")
                for c in f.boundary_candidates
            ] or ["- none found"]
            lines += [
                "",
                "### 7. Contours and spot elevations (by layer)",
                "",
                "| Layer | Points with z | Points z=0 | Constant-z lines | z=0 lines | "
                "Varying-z lines | Numeric labels | z range |",
                "|---|---|---|---|---|---|---|---|",
            ]
            lines += [
                f"| {e.layer} | {e.points_with_z} | {e.points_at_zero} | {e.constant_z_lines} | "
                f"{e.zero_z_lines} | {e.varying_z_lines} | {e.numeric_labels} | "
                f"{e.z_min} to {e.z_max} |"
                for e in f.elevations
            ] or ["| none | | | | | | | |"]
            lines += ["", "### 8. Unknown or ambiguous information"]
            lines += [f"- Unsupported entities: {f.unsupported_entities or 'none'}"]
            if f.unmapped_layers:
                lines.append(f"- Layers without a role: {', '.join(f.unmapped_layers)}")
            lines += [f"- {a.handle} ({a.entity_type}, {a.layer}): {a.reason}" for a in f.ambiguous]
            lines += [f"- Warning: {w}" for w in f.warnings]
            lines += [
                "",
                "### 9. Provenance",
                f"- Path: {f.path}",
                f"- Parser: {f.parser} {f.parser_version}"
                + (
                    f"; converted with {f.converter} {f.converter_version} "
                    f"(DXF sha256 {f.converted_sha256})"
                    if f.converter
                    else ""
                ),
            ]
        lines += ["", "### 10. Needs your confirmation"]
        lines += [f"- [ ] {q}" for q in f.needs_confirmation]
        lines.append("")
    return "\n".join(lines)
