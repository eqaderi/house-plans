"""Site ingestion: survey files in the project store -> cad_import(s) + site.

A survey may arrive as several files (e.g. the boundary in one DWG and the
heights in another). All of them form one site: each file gets its own
``cad_import`` record, ids are namespaced per file, and what the files
declare must agree.

Pipeline (each step separate, each result traceable):

1. the original file is already preserved in ``source/`` (``source add``);
2. a CAD adapter extracts raw entities in SOURCE coordinates;
3. :func:`declared_frame` records only what the file itself declares
   (``$INSUNITS``, a GEODATA EPSG code); nothing is inferred;
4. :func:`interpret` converts SOURCE -> GRID -> LOCAL with
   :class:`~house_ai.domain.coordinates.SurveyTransform` and applies the
   human layer mapping;
5. terrain (TIN), frontage and issues are derived;
6. a ``site`` artifact is written. Unconfirmed facts block the site gate,
   so ``workflow assess-site`` moves the project to SITE_NEEDS_CONFIRMATION.

:func:`confirm_site` is the only way to mark units, CRS, datum or boundary
as confirmed. It requires a human actor; the CLI additionally requires an
interactive terminal and a typed phrase, like gate approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from house_ai.cad.base import CadExtraction, CadInspection
from house_ai.cad.dwg_oda import adapter_for
from house_ai.cad.layers import LayerMapping
from house_ai.cad.site_extract import MappedLayerSiteExtractor, SiteExtraction
from house_ai.domain.coordinates import (
    HorizontalCRS,
    LocalCoordinateSystem,
    SiteCoordinates,
    SurveyTransform,
    VerticalDatum,
)
from house_ai.domain.epistemics import ConfirmationStatus, Epistemic
from house_ai.domain.geometry import Point3
from house_ai.domain.provenance import (
    Actor,
    ActorKind,
    ArtifactKind,
    ArtifactRef,
    DataClassification,
    Provenance,
    SourceDocument,
)
from house_ai.domain.records import Assumption, Issue, IssueStatus, Severity
from house_ai.domain.site import CadImportProvenance, Site, site_verification_blockers
from house_ai.domain.units import METRES_PER_UNIT, LengthUnit, UnitDeclaration, unit_from_insunits
from house_ai.geospatial.base import set_coordinate_reference_system
from house_ai.geospatial.crs import (
    CrsValidationError,
    describe_epsg,
    grid_to_lonlat,
    grid_to_true_north_deg,
    inside_area_of_use,
    require_projected_metric,
    require_vertical,
)
from house_ai.geospatial.parcel import derive_frontage
from house_ai.geospatial.terrain import crossing_contours, terrain_from_survey
from house_ai.storage import ProjectStore, StoreError

from .workflow import ApprovalRequiresHuman

TOOL = "house-ai site ingestion"
LOCAL_FRAME_ID = "lcs-site"


@dataclass(frozen=True)
class FrameDeclaration:
    """Units, CRS and datum as currently known, and the local frame placement."""

    source_units: UnitDeclaration
    elevation_units: UnitDeclaration
    horizontal_crs: HorizontalCRS
    vertical_datum: VerticalDatum
    #: GRID origin of the local frame; None places it automatically.
    origin: Point3 | None = None
    rotation_deg: float = 0.0


@dataclass(frozen=True)
class SurveySource:
    """One stored survey file and its raw extraction."""

    doc_ref: ArtifactRef
    doc: SourceDocument
    extraction: CadExtraction


@dataclass
class Interpretation:
    frame: FrameDeclaration
    local: LocalCoordinateSystem | None
    #: All sources merged.
    extraction: SiteExtraction
    issues: list[Issue] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    #: Per source id, for each file's cad_import record.
    per_source: dict[str, SiteExtraction] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestResult:
    #: The first file's cad_import (all of them are in ``cad_refs``).
    cad_ref: ArtifactRef
    site_ref: ArtifactRef
    blockers: list[str]
    cad_refs: list[ArtifactRef] = field(default_factory=list)


@dataclass
class SiteConfirmation:
    """What a human confirms. Fields left None keep their current status."""

    units: LengthUnit | None = None
    elevation_units: LengthUnit | None = None
    epsg: int | None = None
    #: The survey is in a local frame with no georeference.
    local_only: bool = False
    vertical_datum: str | None = None
    vertical_epsg: int | None = None
    #: Elevations are relative to a local benchmark named by ``vertical_datum``.
    vertical_local: bool = False
    boundary_verified: bool = False
    origin: Point3 | None = None
    rotation_deg: float | None = None
    accept_issues: list[str] = field(default_factory=list)

    def summary(self) -> list[str]:
        out = []
        if self.units:
            out.append(f"drawing units {self.units.value}")
        if self.elevation_units:
            out.append(f"elevation units {self.elevation_units.value}")
        if self.epsg:
            out.append(f"horizontal CRS EPSG:{self.epsg}")
        if self.local_only:
            out.append("survey is local-only (no georeference)")
        if self.vertical_datum:
            kind = "local benchmark" if self.vertical_local else "vertical datum"
            epsg = f" EPSG:{self.vertical_epsg}" if self.vertical_epsg else ""
            out.append(f"{kind} {self.vertical_datum}{epsg}")
        if self.boundary_verified:
            out.append("parcel boundary verified")
        if self.origin:
            out.append(f"local origin {self.origin}")
        if self.rotation_deg is not None:
            out.append(f"local rotation {self.rotation_deg}°")
        out += [f"accept issue {i}" for i in self.accept_issues]
        return out


# --------------------------------------------------------------------- frame


def _tag(source_id: str) -> str:
    return source_id.removeprefix("src-")


def declared_frame(
    inspection: CadInspection, source_id: str = "src"
) -> tuple[FrameDeclaration, list[Issue]]:
    """Only what one file states. DXF stores z in drawing units, so the
    declared drawing unit is also the declared elevation unit."""
    issues: list[Issue] = []
    tag = _tag(source_id)
    unit = unit_from_insunits(inspection.declared_insunits)
    units = (
        UnitDeclaration(unit=unit, status=ConfirmationStatus.DECLARED_IN_SOURCE)
        if unit
        else UnitDeclaration()
    )
    epsg = inspection.declared_epsg
    crs = HorizontalCRS()
    if epsg:
        try:
            require_projected_metric(epsg)
            crs = set_coordinate_reference_system(
                actor=Actor(kind=ActorKind.SYSTEM, id="house-ai"),
                status=ConfirmationStatus.DECLARED_IN_SOURCE,
                declared_epsg=epsg,
            )
        except (CrsValidationError, ValueError) as exc:
            issues.append(
                Issue(
                    id=f"iss-geodata-crs-invalid-{tag}"[:64].rstrip("-_"),
                    title=f"{source_id}: the declared CRS (EPSG:{epsg}) is not usable",
                    description=str(exc),
                    severity=Severity.BLOCKING,
                )
            )
    geo = inspection.geodata
    if geo is not None:
        h_scale = geo.get("horizontal_unit_scale")
        v_scale = geo.get("vertical_unit_scale")
        h_disagrees = (
            unit and isinstance(h_scale, float) and abs(h_scale - METRES_PER_UNIT[unit]) > 1e-9
        )
        v_disagrees = (
            unit and isinstance(v_scale, float) and abs(v_scale - METRES_PER_UNIT[unit]) > 1e-9
        )
        if h_disagrees or v_disagrees:
            scale_desc = (
                f"{h_scale} m"
                if h_scale == v_scale or v_scale is None
                else f"horizontal {h_scale} m, vertical {v_scale} m"
            )
            issues.append(
                Issue(
                    id=f"iss-geodata-unit-conflict-{tag}"[:64].rstrip("-_"),
                    title=f"{source_id}: GEODATA and $INSUNITS disagree on the unit",
                    description=f"$INSUNITS says {unit.value}; GEODATA scales by {scale_desc}.",
                    severity=Severity.BLOCKING,
                )
            )
        design, reference = geo.get("design_point"), geo.get("reference_point")
        north = geo.get("north_direction")
        shifted = (
            (design is not None and reference is not None and design != reference)
            or (north is not None and north not in ([0.0, 1.0], [0.0, 1.0, 0.0]))
            or geo.get("coordinate_type") == "geographic"
        )
        if shifted:
            issues.append(
                Issue(
                    id=f"iss-geodata-transform-{tag}"[:64].rstrip("-_"),
                    title=f"{source_id}: the drawing declares a georeference transform that "
                    "is not applied",
                    description=f"GEODATA design point {design}, reference point {reference}, "
                    f"north {north}. Coordinates are used as drawn.",
                    severity=Severity.BLOCKING,
                )
            )
    return (
        FrameDeclaration(
            source_units=units,
            elevation_units=units,
            horizontal_crs=crs,
            vertical_datum=VerticalDatum(),
        ),
        issues,
    )


def combined_frame(sources: list[SurveySource]) -> tuple[FrameDeclaration, list[Issue]]:
    """What all files declare together. A declaration counts only if every file
    makes the same one; disagreement is a blocking issue that confirmation
    cannot clear, because one site has one unit and one CRS."""
    issues: list[Issue] = []
    frames = []
    for src in sources:
        assert src.extraction.inspection is not None
        frame, file_issues = declared_frame(src.extraction.inspection, src.doc.id)
        frames.append((src.doc.id, frame))
        issues += file_issues
    units = {sid: f.source_units.unit for sid, f in frames}
    declared_units = {u for u in units.values() if u is not None}
    if len(declared_units) > 1:
        detail = ", ".join(f"{sid}: {u.value if u else 'none'}" for sid, u in units.items())
        issues.append(
            Issue(
                id="iss-sources-disagree-units",
                title="The survey files declare different units; one site needs one unit",
                description=f"{detail}. Convert the files to one unit first.",
                severity=Severity.BLOCKING,
            )
        )
    if len(declared_units) == 1 and None not in units.values():
        unit_decl = frames[0][1].source_units
    else:
        unit_decl = UnitDeclaration()
    epsgs = {
        f.horizontal_crs.declared_epsg or s.extraction.inspection.declared_epsg
        for s, (_, f) in zip(sources, frames, strict=True)
    } - {None}
    if len(epsgs) > 1:
        issues.append(
            Issue(
                id="iss-sources-disagree-crs",
                title="The survey files declare different coordinate systems",
                description="Declared EPSG codes: " + ", ".join(str(e) for e in sorted(epsgs)),
                severity=Severity.BLOCKING,
            )
        )
    valid_epsgs = {f.horizontal_crs.declared_epsg for _, f in frames} - {None}
    crs = (
        next(f.horizontal_crs for _, f in frames if f.horizontal_crs.declared_epsg)
        if len(epsgs) == 1 and len(valid_epsgs) == 1
        else HorizontalCRS()
    )
    return (
        FrameDeclaration(
            source_units=unit_decl,
            elevation_units=unit_decl,
            horizontal_crs=crs,
            vertical_datum=VerticalDatum(),
        ),
        issues,
    )


# ---------------------------------------------------------------- interpret


def _merge(parts: list[tuple[str, SiteExtraction]]) -> SiteExtraction:
    out = SiteExtraction()
    with_boundary = [(sid, x) for sid, x in parts if x.boundary is not None]
    if len(with_boundary) == 1:
        out.boundary = with_boundary[0][1].boundary
        out.boundary_source_ref = with_boundary[0][1].boundary_source_ref
    for sid, x in parts:
        out.boundary_candidates += [f"{sid}#{h}" for h in x.boundary_candidates]
        out.contours += x.contours
        out.breaklines += x.breaklines
        out.spot_elevations += x.spot_elevations
        out.features += x.features
        out.ambiguous += x.ambiguous
        out.label_checks += x.label_checks
        out.ignored_count += x.ignored_count
        out.conflicts += x.conflicts
        out.warnings += x.warnings
        for kind, n in x.unrecognized_entities.items():
            out.unrecognized_entities[kind] = out.unrecognized_entities.get(kind, 0) + n
    out.unrecognized_layers = sorted({la for _, x in parts for la in x.unrecognized_layers})
    return out


def _extraction_issues(
    site_ext: SiteExtraction,
    mapping: LayerMapping,
    *,
    has_multiple_boundaries: bool,
    unit_known: bool,
) -> list[Issue]:
    issues: list[Issue] = []
    for i, conflict in enumerate(site_ext.conflicts, start=1):
        issues.append(Issue(id=f"iss-conflict-{i}", title=conflict, severity=Severity.BLOCKING))
    if (
        site_ext.boundary is None
        and not has_multiple_boundaries
        and len(site_ext.boundary_candidates) > 1
    ):
        issues.append(
            Issue(
                id="iss-boundary-ambiguous",
                title=f"{len(site_ext.boundary_candidates)} closed polylines could be the parcel",
                description="Candidates (source#handle): "
                + ", ".join(site_ext.boundary_candidates)
                + ". Name the parcel with boundary_handle in the layer mapping.",
                severity=Severity.BLOCKING,
            )
        )
    elif (
        unit_known
        and site_ext.boundary is None
        and not has_multiple_boundaries
        and mapping.has_boundary_role()
    ):
        issues.append(
            Issue(
                id="iss-boundary-missing",
                title="No usable parcel boundary on the boundary layers",
                severity=Severity.BLOCKING,
            )
        )
    for a, b in crossing_contours(site_ext.contours):
        issues.append(
            Issue(
                id=f"iss-contours-cross-{a}-{b}"[:64].rstrip("-_"),
                title=f"Contours {a} and {b} cross although their elevations differ",
                severity=Severity.BLOCKING,
                subject_ids=[a, b],
            )
        )
    if site_ext.ambiguous:
        issues.append(
            Issue(
                id="iss-ambiguous-entities",
                title=f"{len(site_ext.ambiguous)} ambiguous CAD entities were left out",
                description="Listed with handle and reason in the cad_import artifacts.",
                severity=Severity.WARNING,
            )
        )
    for i, warning in enumerate(site_ext.warnings, start=1):
        issues.append(Issue(id=f"iss-warning-{i}", title=warning, severity=Severity.WARNING))
    if site_ext.unrecognized_layers:
        issues.append(
            Issue(
                id="iss-unmapped-layers",
                title=f"{len(site_ext.unrecognized_layers)} layers have no role and were not read",
                description=", ".join(site_ext.unrecognized_layers),
                severity=Severity.INFO,
            )
        )
    return issues


def interpret(
    sources: list[tuple[str, CadExtraction]], mapping: LayerMapping, frame: FrameDeclaration
) -> Interpretation:
    """Interpret every file in one shared frame. ``sources`` is (source id, extraction)."""
    issues: list[Issue] = []
    h_unit, v_unit = frame.source_units.unit, frame.elevation_units.unit
    extractors = [(sid, ext, MappedLayerSiteExtractor(mapping, sid)) for sid, ext in sources]
    if h_unit is None:
        per_source_unscaled: dict[str, SiteExtraction] = {}
        for sid, ext, x in extractors:
            e = ext.inspection.extents if ext.inspection else None
            src_origin = (e[0], e[1], 0.0) if e else (0.0, 0.0, 0.0)
            src_tf = SurveyTransform(
                1.0, 1.0, LocalCoordinateSystem(id="source", origin=src_origin)
            )
            part = x.extract(ext, src_tf)
            part.boundary = None
            part.boundary_source_ref = None
            part.contours = []
            part.breaklines = []
            part.spot_elevations = []
            part.features = []
            per_source_unscaled[sid] = part
        site_ext = _merge(list(per_source_unscaled.items()))
        issues += _extraction_issues(
            site_ext, mapping, has_multiple_boundaries=False, unit_known=False
        )
        return Interpretation(
            frame=frame,
            local=None,
            extraction=site_ext,
            issues=issues,
            assumptions=[],
            per_source=per_source_unscaled,
        )
    h_m = METRES_PER_UNIT[h_unit]
    # Without an elevation unit the z values are not converted at all (see below);
    # the vertical scale used here only keeps the transform well defined.
    v_m = METRES_PER_UNIT[v_unit] if v_unit else 1.0

    origin, basis = frame.origin, "given by a human"
    grid_frame = LocalCoordinateSystem(id="grid", origin=(0.0, 0.0, 0.0))
    first = [
        (sid, x.extract(ext, SurveyTransform(h_m, v_m, grid_frame))) for sid, ext, x in extractors
    ]
    boundaries = [(sid, r.boundary) for sid, r in first if r.boundary is not None]
    if len(boundaries) > 1:
        issues.append(
            Issue(
                id="iss-boundary-in-several-files",
                title="More than one survey file holds a parcel boundary",
                description="Files: "
                + ", ".join(sid for sid, _ in boundaries)
                + ". Map the boundary layer in one file only.",
                severity=Severity.BLOCKING,
            )
        )
    if origin is None:
        if len(boundaries) == 1:
            e, n = min(boundaries[0][1].outer, key=lambda p: (p[1], p[0]))
            origin = (e, n, 0.0)
            basis = "south-west-most boundary vertex (lowest northing, then easting); z 0"
        else:
            corners = [
                ext.inspection.extents
                for _, ext in sources
                if ext.inspection and ext.inspection.extents
            ]
            origin = (
                (min(c[0] for c in corners) * h_m, min(c[1] for c in corners) * h_m, 0.0)
                if corners
                else (0.0, 0.0, 0.0)
            )
            basis = "minimum corner of the drawing extents; z 0"
    crs = frame.horizontal_crs
    g2t = None
    if crs.status is ConfirmationStatus.USER_CONFIRMED and crs.epsg:
        g2t = grid_to_true_north_deg(crs.epsg, origin[0], origin[1])
        info = describe_epsg(crs.epsg)
        lon, lat = grid_to_lonlat(crs.epsg, origin[0], origin[1])
        if inside_area_of_use(info, lon, lat) is False:
            issues.append(
                Issue(
                    id="iss-crs-area-of-use",
                    title=f"The site lies outside the area of use of EPSG:{crs.epsg}",
                    description=f"Local origin maps to lon {lon:.5f}, lat {lat:.5f}. The CRS "
                    "or the drawing units are probably wrong.",
                    severity=Severity.BLOCKING,
                )
            )
    local = LocalCoordinateSystem(
        id=LOCAL_FRAME_ID,
        name=f"Survey frame; origin: {basis}",
        origin=origin,
        rotation_deg=frame.rotation_deg,
        grid_to_true_north_deg=g2t,
    )
    transform = SurveyTransform(h_m, v_m, local)
    per_source = {sid: x.extract(ext, transform) for sid, ext, x in extractors}
    if v_unit is None:
        for part in per_source.values():
            dropped = len(part.spot_elevations) + len(part.contours) + len(part.breaklines)
            if dropped:
                part.warnings.append(
                    f"{dropped} elevation entities not converted: the elevation unit is unknown"
                )
            part.spot_elevations, part.contours = [], []
            part.breaklines = []
    site_ext = _merge(list(per_source.items()))
    if v_unit is None and any("elevation unit is unknown" in w for w in site_ext.warnings):
        issues.append(
            Issue(
                id="iss-elevation-units-unknown",
                title="Elevations are left out until a human states the elevation unit",
                severity=Severity.BLOCKING,
            )
        )
    issues += _extraction_issues(
        site_ext,
        mapping,
        has_multiple_boundaries=len(boundaries) > 1,
        unit_known=True,
    )
    assumptions = [
        Assumption(
            id="asm-local-origin",
            statement=f"The local project origin is at grid {origin} ({basis}); local x is "
            f"rotated {frame.rotation_deg}° from grid east.",
            basis="A frame choice that keeps coordinates small; not a survey fact.",
            confirm_with="owner",
        )
    ]
    return Interpretation(frame, local, site_ext, issues, assumptions, per_source)


def assemble_site(
    interp: Interpretation,
    *,
    site_id: str,
    project_id: str,
    name: str,
    classification: DataClassification,
    inputs: list[ArtifactRef],
    actor: Actor,
    created_at: datetime,
    method: str,
    boundary_verified: bool,
    extra_issues: list[Issue],
    accept: set[str],
    carry_accepted: set[str] = frozenset(),
    carry_accepted_signatures: set[tuple[str, str, str | None]] = frozenset(),
    notes: str | None = None,
) -> Site:
    """Build the canonical site. ``accept`` holds issue ids a human accepts now
    (each must exist); ``carry_accepted`` / ``carry_accepted_signatures`` keep
    earlier acceptances that still apply."""
    ext = interp.extraction
    terrain, tin = terrain_from_survey(ext.spot_elevations, ext.contours, ext.breaklines)
    issues = [*extra_issues, *interp.issues]
    for i, conflict in enumerate(tin.conflicts, start=1):
        issues.append(
            Issue(id=f"iss-terrain-conflict-{i}", title=conflict, severity=Severity.BLOCKING)
        )
    features = [*ext.features, *derive_frontage(ext.boundary, ext.features)]
    unknown = accept - {i.id for i in issues}
    if unknown:
        raise ValueError(f"cannot accept unknown issue(s): {', '.join(sorted(unknown))}")
    accepted = accept | carry_accepted
    issues = [
        i.model_copy(update={"status": IssueStatus.ACCEPTED})
        if (
            i.id in accepted
            or (i.id, i.title, i.description) in carry_accepted_signatures
        )
        else i
        for i in issues
    ]
    if ext.boundary is None:
        boundary_status = Epistemic.UNKNOWN
    elif boundary_verified:
        boundary_status = Epistemic.VERIFIED_FACT
    else:
        boundary_status = Epistemic.INFERENCE
    f = interp.frame
    return Site(
        id=site_id,
        project_id=project_id,
        name=name,
        classification=classification,
        coordinates=SiteCoordinates(
            source_units=f.source_units,
            elevation_units=f.elevation_units,
            horizontal_crs=f.horizontal_crs,
            vertical_datum=f.vertical_datum,
            local=interp.local,
        ),
        boundary=ext.boundary,
        boundary_status=boundary_status,
        boundary_source_ref=ext.boundary_source_ref,
        terrain=terrain,
        features=features,
        assumptions=interp.assumptions,
        issues=issues,
        provenance=Provenance(
            created_at=created_at,
            created_by=actor,
            method=method,
            tool=TOOL,
            inputs=inputs,
            notes=notes,
        ),
    )


def _classification(sources: list[SurveySource]) -> DataClassification:
    """The most restrictive classification of the inputs."""
    order = [DataClassification.PRIVATE, DataClassification.PUBLIC, DataClassification.SYNTHETIC]
    return next(c for c in order if any(s.doc.classification is c for s in sources))


# ------------------------------------------------------------------- ingest


def _load(store: ProjectStore, source_id: str, mapping: LayerMapping) -> SurveySource:
    ref = store.latest(ArtifactKind.SOURCE_DOCUMENT, source_id)
    if ref is None:
        raise StoreError(f"no source document {source_id!r}; run `house-ai source add` first")
    doc = store.get(ref, SourceDocument)
    path = store.root / doc.stored_path
    return SurveySource(ref, doc, adapter_for(path).extract_cad(path, mapping.as_dict()))


def _cad_record(
    src: SurveySource, part: SiteExtraction, interp: Interpretation, mapping: LayerMapping
) -> CadImportProvenance:
    insp = src.extraction.inspection
    assert insp is not None
    frame = interp.frame
    return CadImportProvenance(
        source_document_id=src.doc.id,
        original_filename=src.doc.original_filename,
        sha256=src.doc.sha256,
        source_format=insp.source_format,
        drawing_units=_file_units(insp, src.doc.id, frame.source_units),
        parser=insp.parser,
        parser_version=insp.parser_version,
        converter=insp.converter,
        converter_version=insp.converter_version,
        converted_sha256=insp.converted_sha256,
        horizontal_crs_status=frame.horizontal_crs.status,
        epsg=frame.horizontal_crs.epsg,
        declared_epsg=insp.declared_epsg,
        vertical_datum_status=frame.vertical_datum.status,
        local_origin=interp.local.origin if interp.local else None,
        warnings=[*insp.warnings, *part.warnings],
        unrecognized_layers=part.unrecognized_layers,
        unrecognized_entities=part.unrecognized_entities,
        layer_roles=mapping.as_dict(),
        handle_roles=mapping.handle_roles_as_dict(),
        zero_elevation_is_valid=mapping.zero_elevation_is_valid,
        boundary_handle=mapping.boundary_handle,
        ambiguous_entities=part.ambiguous,
        height_label_checks=part.label_checks,
    )


def _file_units(
    inspection: CadInspection, source_id: str, site_units: UnitDeclaration
) -> UnitDeclaration:
    """The unit of one file: what it declares, or the site's confirmed unit if the
    file declares none or the same one. A human confirming metres for the site
    never makes a file that declares millimetres say metres."""
    own = declared_frame(inspection, source_id)[0].source_units
    if site_units.confirmed and own.unit in (None, site_units.unit):
        return site_units
    return own


def _check_mapping_targets(mapping: LayerMapping, source_ids: list[str]) -> None:
    """Handle overrides must name one ingested file: DXF handles restart in every
    file, so a bare handle would match an unrelated entity in another file."""
    keys = list(mapping.handle_roles)
    if mapping.boundary_handle is not None:
        keys.append(mapping.boundary_handle)
    known = {s.lower() for s in source_ids} | {s.lower().removeprefix("src-") for s in source_ids}
    for key in keys:
        prefix, sep, _ = key.strip().partition("#")
        if not sep:
            if len(source_ids) > 1:
                raise ValueError(
                    f"handle {key!r} in the layer mapping does not say which file it is in; "
                    "with several survey files write it as source_id#handle "
                    f"(files: {', '.join(source_ids)})"
                )
        elif prefix.strip().lower() not in known:
            raise ValueError(
                f"handle {key!r} in the layer mapping names {prefix!r}, which is not one of "
                f"the ingested files ({', '.join(source_ids)})"
            )


def ingest_site(
    store: ProjectStore,
    source_ids: str | list[str],
    mapping: LayerMapping,
    actor: Actor,
    *,
    site_id: str = "site",
) -> IngestResult:
    """Extract stored survey file(s) and write one cad_import per file and a site.

    Units and CRS keep the status the files give them (declared or unknown);
    the boundary is an inference. Confirmation is a separate human step.
    """
    ids = [source_ids] if isinstance(source_ids, str) else list(source_ids)
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("give one or more distinct source ids")
    _check_mapping_targets(mapping, ids)
    sources = [_load(store, sid, mapping) for sid in ids]
    frame, frame_issues = combined_frame(sources)
    interp = interpret([(s.doc.id, s.extraction) for s in sources], mapping, frame)
    cad_refs = [
        store.put(
            ArtifactKind.CAD_IMPORT,
            f"cad-{s.doc.id}"[:64].rstrip("-_"),
            _cad_record(s, interp.per_source.get(s.doc.id, SiteExtraction()), interp, mapping),
            actor,
        )
        for s in sources
    ]
    names = ", ".join(s.doc.original_filename for s in sources)
    site = assemble_site(
        interp,
        site_id=site_id,
        project_id=store.project_id,
        name=store.manifest().name,
        classification=_classification(sources),
        inputs=[*(s.doc_ref for s in sources), *cad_refs],
        actor=actor,
        created_at=store.clock(),
        method="cad_import",
        boundary_verified=False,
        extra_issues=frame_issues,
        accept=set(),
        notes=f"Imported from {names}; nothing confirmed by a human yet.",
    )
    site_ref = store.put(ArtifactKind.SITE, site_id, site, actor, reason="site ingestion")
    return IngestResult(cad_refs[0], site_ref, site_verification_blockers(site), cad_refs)


# ------------------------------------------------------------------ confirm


def confirm_site(
    store: ProjectStore, site_id: str, actor: Actor, conf: SiteConfirmation
) -> ArtifactRef:
    """Write a new site version with human-confirmed units, CRS, datum or boundary.

    The site is re-derived from the immutable source files with the confirmed
    values, so a corrected unit changes every coordinate consistently.
    """
    if actor.kind is not ActorKind.HUMAN:
        raise ApprovalRequiresHuman(
            f"{actor.kind.value} {actor.id!r} cannot confirm site facts; only a human can"
        )
    if conf.epsg is not None and conf.local_only:
        raise ValueError("choose either an EPSG code or local-only, not both")
    if conf.vertical_epsg is not None and conf.vertical_local:
        raise ValueError("a local benchmark has no EPSG code")
    if (conf.vertical_epsg is not None or conf.vertical_local) and not conf.vertical_datum:
        raise ValueError("name the vertical datum or benchmark")
    if not conf.summary():
        raise ValueError("nothing to confirm")
    site_ref = store.latest(ArtifactKind.SITE, site_id)
    if site_ref is None:
        raise StoreError(f"no site {site_id!r}")
    site = store.get(site_ref, Site)
    cad_refs = [r for r in site.provenance.inputs if r.kind is ArtifactKind.CAD_IMPORT]
    if not cad_refs:
        raise StoreError(f"site {site_id} was not produced by a CAD import")
    cads = [store.get(r, CadImportProvenance) for r in cad_refs]
    mapping = LayerMapping.model_validate(
        {
            "layers": cads[0].layer_roles,
            "handle_roles": cads[0].handle_roles,
            "zero_elevation_is_valid": cads[0].zero_elevation_is_valid,
            "boundary_handle": cads[0].boundary_handle,
        }
    )
    sources = [_load(store, cad.source_document_id, mapping) for cad in cads]
    _, frame_issues = combined_frame(sources)

    c = site.coordinates
    confirmed = ConfirmationStatus.USER_CONFIRMED
    units = UnitDeclaration(unit=conf.units, status=confirmed) if conf.units else c.source_units
    elevation = (
        UnitDeclaration(unit=conf.elevation_units, status=confirmed)
        if conf.elevation_units
        else c.elevation_units
    )
    if conf.epsg is not None:
        crs = set_coordinate_reference_system(
            actor=actor,
            status=confirmed,
            epsg=conf.epsg,
            declared_epsg=c.horizontal_crs.declared_epsg,
        )
    elif conf.local_only:
        crs = set_coordinate_reference_system(
            actor=actor,
            status=ConfirmationStatus.LOCAL_ONLY_CONFIRMED,
            declared_epsg=c.horizontal_crs.declared_epsg,
            name="local survey frame, no georeference",
        )
    else:
        crs = c.horizontal_crs
    if conf.vertical_datum and conf.vertical_local:
        datum = VerticalDatum(
            status=ConfirmationStatus.LOCAL_ONLY_CONFIRMED, name=conf.vertical_datum
        )
    elif conf.vertical_datum:
        if conf.vertical_epsg is not None:
            require_vertical(conf.vertical_epsg)
        datum = VerticalDatum(status=confirmed, name=conf.vertical_datum, epsg=conf.vertical_epsg)
    else:
        datum = c.vertical_datum
    if conf.origin is not None:
        origin: Point3 | None = conf.origin
    elif c.local is not None and "given by a human" in (c.local.name or ""):
        origin = c.local.origin
    else:
        origin = None
    if conf.rotation_deg is not None:
        rotation = conf.rotation_deg
    else:
        rotation = c.local.rotation_deg if c.local else 0.0
    frame = FrameDeclaration(units, elevation, crs, datum, origin, rotation)
    interp = interpret([(s.doc.id, s.extraction) for s in sources], mapping, frame)
    unchanged = interp.extraction.boundary == site.boundary
    still_verified = site.boundary_status is Epistemic.VERIFIED_FACT and unchanged
    previously_accepted_sigs = {
        (i.id, i.title, i.description)
        for i in site.issues
        if i.status is IssueStatus.ACCEPTED
    }
    created_at = store.clock()

    def build(inputs: list[ArtifactRef]) -> Site:
        return assemble_site(
            interp,
            site_id=site_id,
            project_id=store.project_id,
            name=site.name,
            classification=_classification(sources),
            inputs=inputs,
            actor=actor,
            created_at=created_at,
            method="human_site_confirmation",
            boundary_verified=conf.boundary_verified or still_verified,
            extra_issues=frame_issues,
            accept=set(conf.accept_issues),
            carry_accepted_signatures=previously_accepted_sigs,
            notes=f"{actor.id} confirmed: " + "; ".join(conf.summary()),
        )

    # Build the site once before writing anything, so a confirmation that fails
    # (e.g. an unknown --accept-issue) leaves no cad_import claiming it happened.
    build([s.doc_ref for s in sources])
    new_cad_refs = [
        store.put(
            ArtifactKind.CAD_IMPORT,
            f"cad-{s.doc.id}"[:64].rstrip("-_"),
            _cad_record(s, interp.per_source.get(s.doc.id, SiteExtraction()), interp, mapping),
            actor,
            reason="human site confirmation: " + "; ".join(conf.summary()),
        )
        for s in sources
    ]
    new = build([*(s.doc_ref for s in sources), *new_cad_refs])
    return store.put(
        ArtifactKind.SITE,
        site_id,
        new,
        actor,
        reason="human site confirmation: " + "; ".join(conf.summary()),
    )
