"""Site ingestion: a survey file in the project store -> cad_import + site.

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
   so ``workflow assess-site`` moves the project to SITE_NEEDS_VERIFICATION.

:func:`confirm_site` is the only way to mark units, CRS, datum or boundary
as confirmed. It requires a human actor; the CLI additionally requires an
interactive terminal and a typed phrase, like gate approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from house_ai.cad.base import CadExtraction, CadInspection
from house_ai.cad.dwg_oda import adapter_for
from house_ai.cad.layers import LayerMapping, LayerRole
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
    Provenance,
    SourceDocument,
)
from house_ai.domain.records import Assumption, Issue, IssueStatus, Severity
from house_ai.domain.site import CadImportProvenance, Site, site_verification_blockers
from house_ai.domain.units import METRES_PER_UNIT, LengthUnit, UnitDeclaration, unit_from_insunits
from house_ai.geospatial.base import set_coordinate_reference_system
from house_ai.geospatial.crs import (
    describe_epsg,
    grid_to_lonlat,
    grid_to_true_north_deg,
    inside_area_of_use,
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


@dataclass
class Interpretation:
    frame: FrameDeclaration
    local: LocalCoordinateSystem | None
    extraction: SiteExtraction
    issues: list[Issue] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)


@dataclass(frozen=True)
class IngestResult:
    cad_ref: ArtifactRef
    site_ref: ArtifactRef
    blockers: list[str]


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


def declared_frame(inspection: CadInspection) -> tuple[FrameDeclaration, list[Issue]]:
    """Only what the file states. DXF stores z in drawing units, so the
    declared drawing unit is also the declared elevation unit."""
    issues: list[Issue] = []
    unit = unit_from_insunits(inspection.declared_insunits)
    units = (
        UnitDeclaration(unit=unit, status=ConfirmationStatus.DECLARED_IN_SOURCE)
        if unit
        else UnitDeclaration()
    )
    if unit is None:
        code = inspection.declared_insunits
        issues.append(
            Issue(
                id="iss-units-unknown",
                title="Drawing units are not declared",
                description=f"$INSUNITS is {code!r} (unitless or unsupported). Coordinates "
                "cannot be converted to metres until a human states the unit.",
                severity=Severity.BLOCKING,
            )
        )
    epsg = inspection.declared_epsg
    crs = (
        set_coordinate_reference_system(
            actor=Actor(kind=ActorKind.SYSTEM, id="house-ai"),
            status=ConfirmationStatus.DECLARED_IN_SOURCE,
            declared_epsg=epsg,
        )
        if epsg
        else HorizontalCRS()
    )
    geo = inspection.geodata
    if geo is not None:
        scale = geo.get("horizontal_unit_scale")
        if unit and isinstance(scale, float) and abs(scale - METRES_PER_UNIT[unit]) > 1e-9:
            issues.append(
                Issue(
                    id="iss-geodata-unit-conflict",
                    title="GEODATA and $INSUNITS disagree on the unit",
                    description=f"$INSUNITS says {unit.value}; GEODATA scales by {scale} m.",
                    severity=Severity.BLOCKING,
                )
            )
        design, reference = geo.get("design_point"), geo.get("reference_point")
        north = geo.get("north_direction")
        shifted = geo.get("coordinate_type") == "local grid" and (
            design != reference or north not in ([0.0, 1.0], [0.0, 1.0, 0.0])
        )
        if shifted:
            issues.append(
                Issue(
                    id="iss-geodata-transform",
                    title="The drawing declares a georeference transform that is not applied",
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


# ---------------------------------------------------------------- interpret


def interpret(
    extraction: CadExtraction, mapping: LayerMapping, source_id: str, frame: FrameDeclaration
) -> Interpretation:
    issues: list[Issue] = []
    h_unit, v_unit = frame.source_units.unit, frame.elevation_units.unit
    if h_unit is None:
        return Interpretation(frame=frame, local=None, extraction=SiteExtraction())
    h_m = METRES_PER_UNIT[h_unit]
    v_m = METRES_PER_UNIT[v_unit] if v_unit else h_m
    extractor = MappedLayerSiteExtractor(mapping, source_id)

    origin, basis = frame.origin, "given by a human"
    if origin is None:
        grid = SurveyTransform(h_m, v_m, LocalCoordinateSystem(id="grid", origin=(0.0, 0.0, 0.0)))
        first = extractor.extract(extraction, grid)
        if first.boundary is not None:
            e, n = min(first.boundary.outer, key=lambda p: (p[1], p[0]))
            origin = (e, n, 0.0)
            basis = "south-west-most boundary vertex (lowest northing, then easting); z 0"
        else:
            ext = extraction.inspection.extents if extraction.inspection else None
            origin = (ext[0] * h_m, ext[1] * h_m, 0.0) if ext else (0.0, 0.0, 0.0)
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
    site_ext = extractor.extract(extraction, SurveyTransform(h_m, v_m, local))

    for i, conflict in enumerate(site_ext.conflicts, start=1):
        issues.append(
            Issue(id=f"iss-conflict-{i}", title=conflict, severity=Severity.BLOCKING)
        )
    if site_ext.boundary is None and len(site_ext.boundary_candidates) > 1:
        issues.append(
            Issue(
                id="iss-boundary-ambiguous",
                title=f"{len(site_ext.boundary_candidates)} closed polylines could be the parcel",
                description="Candidates (handles): " + ", ".join(site_ext.boundary_candidates)
                + ". Name the parcel with boundary_handle in the layer mapping.",
                severity=Severity.BLOCKING,
            )
        )
    elif site_ext.boundary is None and any(
        r is LayerRole.BOUNDARY for r in mapping.layers.values()
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
                description="Listed with handle and reason in the cad_import artifact.",
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
    assumptions = [
        Assumption(
            id="asm-local-origin",
            statement=f"The local project origin is at grid {origin} ({basis}); local x is "
            f"rotated {frame.rotation_deg}° from grid east.",
            basis="A frame choice that keeps coordinates small; not a survey fact.",
            confirm_with="owner",
        )
    ]
    return Interpretation(frame, local, site_ext, issues, assumptions)


def assemble_site(
    interp: Interpretation,
    *,
    site_id: str,
    project_id: str,
    name: str,
    source: SourceDocument,
    inputs: list[ArtifactRef],
    actor: Actor,
    created_at,
    method: str,
    boundary_verified: bool,
    extra_issues: list[Issue],
    accept: set[str],
    carry_accepted: set[str] = frozenset(),
    notes: str | None = None,
) -> Site:
    """Build the canonical site. ``accept`` holds issue ids a human accepts now
    (each must exist); ``carry_accepted`` keeps earlier acceptances that still apply."""
    ext = interp.extraction
    terrain, tin = terrain_from_survey(ext.spot_elevations, ext.contours)
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
        i.model_copy(update={"status": IssueStatus.ACCEPTED}) if i.id in accepted else i
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
        classification=source.classification,
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


# ------------------------------------------------------------------- ingest


def _source(store: ProjectStore, source_id: str) -> tuple[ArtifactRef, SourceDocument, Path]:
    ref = store.latest(ArtifactKind.SOURCE_DOCUMENT, source_id)
    if ref is None:
        raise StoreError(f"no source document {source_id!r}; run `house-ai source add` first")
    doc = store.get(ref, SourceDocument)
    return ref, doc, store.root / doc.stored_path


def ingest_site(
    store: ProjectStore,
    source_id: str,
    mapping: LayerMapping,
    actor: Actor,
    *,
    site_id: str = "site",
) -> IngestResult:
    """Extract a stored survey and write cad_import and site artifacts.

    Units and CRS keep the status the file gives them (declared or unknown);
    the boundary is an inference. Confirmation is a separate human step.
    """
    doc_ref, doc, path = _source(store, source_id)
    extraction = adapter_for(path).extract_cad(path, mapping.as_dict())
    insp = extraction.inspection
    assert insp is not None
    frame, frame_issues = declared_frame(insp)
    interp = interpret(extraction, mapping, doc.id, frame)
    cad = CadImportProvenance(
        source_document_id=doc.id,
        original_filename=doc.original_filename,
        sha256=doc.sha256,
        source_format=insp.source_format,
        drawing_units=frame.source_units,
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
        warnings=[*insp.warnings, *interp.extraction.warnings],
        unrecognized_layers=interp.extraction.unrecognized_layers,
        unrecognized_entities=interp.extraction.unrecognized_entities,
        layer_roles=mapping.as_dict(),
        zero_elevation_is_valid=mapping.zero_elevation_is_valid,
        boundary_handle=mapping.boundary_handle,
        ambiguous_entities=interp.extraction.ambiguous,
    )
    cad_ref = store.put(ArtifactKind.CAD_IMPORT, f"cad-{doc.id}", cad, actor)
    site = assemble_site(
        interp,
        site_id=site_id,
        project_id=store.project_id,
        name=store.manifest().name,
        source=doc,
        inputs=[doc_ref, cad_ref],
        actor=actor,
        created_at=store.clock(),
        method="cad_import",
        boundary_verified=False,
        extra_issues=frame_issues,
        accept=set(),
        notes=f"Imported from {doc.original_filename}; nothing confirmed by a human yet.",
    )
    site_ref = store.put(ArtifactKind.SITE, site_id, site, actor, reason="site ingestion")
    return IngestResult(cad_ref, site_ref, site_verification_blockers(site))


# ------------------------------------------------------------------ confirm


def confirm_site(
    store: ProjectStore, site_id: str, actor: Actor, conf: SiteConfirmation
) -> ArtifactRef:
    """Write a new site version with human-confirmed units, CRS, datum or boundary.

    The site is re-derived from the immutable source file with the confirmed
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
    cad_ref = next((r for r in site.provenance.inputs if r.kind is ArtifactKind.CAD_IMPORT), None)
    if cad_ref is None:
        raise StoreError(f"site {site_id} was not produced by a CAD import")
    cad = store.get(cad_ref, CadImportProvenance)
    doc_ref, doc, path = _source(store, cad.source_document_id)
    mapping = LayerMapping.model_validate(
        {
            "layers": cad.layer_roles,
            "zero_elevation_is_valid": cad.zero_elevation_is_valid,
            "boundary_handle": cad.boundary_handle,
        }
    )
    extraction = adapter_for(path).extract_cad(path, mapping.as_dict())
    assert extraction.inspection is not None
    _, frame_issues = declared_frame(extraction.inspection)

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
    rotation = conf.rotation_deg if conf.rotation_deg is not None else (
        c.local.rotation_deg if c.local else 0.0
    )
    frame = FrameDeclaration(units, elevation, crs, datum, conf.origin, rotation)
    interp = interpret(extraction, mapping, doc.id, frame)
    unchanged = interp.extraction.boundary == site.boundary
    still_verified = site.boundary_status is Epistemic.VERIFIED_FACT and unchanged
    previously_accepted = {i.id for i in site.issues if i.status is IssueStatus.ACCEPTED}
    new = assemble_site(
        interp,
        site_id=site_id,
        project_id=store.project_id,
        name=site.name,
        source=doc,
        inputs=[doc_ref, cad_ref],
        actor=actor,
        created_at=store.clock(),
        method="human_site_confirmation",
        boundary_verified=conf.boundary_verified or still_verified,
        extra_issues=frame_issues,
        accept=set(conf.accept_issues),
        carry_accepted=previously_accepted,
        notes=f"{actor.id} confirmed: " + "; ".join(conf.summary()),
    )
    return store.put(
        ArtifactKind.SITE,
        site_id,
        new,
        actor,
        reason="human site confirmation: " + "; ".join(conf.summary()),
    )
