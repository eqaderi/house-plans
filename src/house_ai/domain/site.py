"""The site: parcel, coordinate systems, terrain and context.

All geometry here is in the LOCAL project frame (metres) once a local
coordinate system exists. A site that cannot be trusted reports blockers via
:func:`site_verification_blockers`; the workflow refuses the site approval
gate while any remain.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from .base import SCHEMA_VERSION, Id, Sha256, StrictModel
from .coordinates import SiteCoordinates
from .epistemics import ConfirmationStatus, Epistemic
from .geometry import Point2, Point3, Polygon2D, Polyline2D
from .provenance import DataClassification, Provenance
from .records import Assumption, Issue, IssueStatus, Severity
from .units import UnitDeclaration


class PointGeometry(StrictModel):
    type: Literal["point"] = "point"
    xy: Point2


class PolylineGeometry(StrictModel):
    type: Literal["polyline"] = "polyline"
    line: Polyline2D


class PolygonGeometry(StrictModel):
    type: Literal["polygon"] = "polygon"
    polygon: Polygon2D


FeatureGeometry = Annotated[
    PointGeometry | PolylineGeometry | PolygonGeometry, Field(discriminator="type")
]


class SiteFeatureKind(StrEnum):
    ROAD = "road"
    EASEMENT = "easement"
    EXISTING_STRUCTURE = "existing_structure"
    UTILITY = "utility"
    TREE = "tree"
    WATER = "water"
    ACCESS_POINT = "access_point"
    OTHER = "other"


class SiteFeature(StrictModel):
    id: Id
    kind: SiteFeatureKind
    name: str | None = None
    geometry: FeatureGeometry
    status: Epistemic = Epistemic.VERIFIED_FACT
    #: CAD layer or other source reference.
    source_ref: str | None = None
    notes: str | None = None


class SpotElevation(StrictModel):
    id: Id
    xy: Point2
    #: Elevation in the local frame (metres above the local origin elevation).
    z_m: float
    source_ref: str | None = None


class Contour(StrictModel):
    id: Id
    z_m: float
    line: Polyline2D
    source_ref: str | None = None


class TerrainStatus(StrEnum):
    UNKNOWN = "unknown"
    #: Elevations are surveyed but no surface has been built yet.
    SURVEYED_POINTS = "surveyed_points"
    #: A terrain surface (e.g. TIN) has been built from surveyed data.
    SURFACE_BUILT = "surface_built"
    #: A human states the site is effectively flat at a given level.
    ASSUMED_FLAT = "assumed_flat"


class Terrain(StrictModel):
    status: TerrainStatus = TerrainStatus.UNKNOWN
    spot_elevations: list[SpotElevation] = Field(default_factory=list)
    contours: list[Contour] = Field(default_factory=list)
    #: Reference to a derived surface artifact (Milestone B), if any.
    surface_ref: str | None = None


class BuildableEnvelope(StrictModel):
    """Where the building may stand. Its source must be stated."""

    polygon: Polygon2D
    status: Epistemic
    #: e.g. "3 m setback assumed on all sides", "zoning plan 2024 sheet 3".
    basis: str = Field(min_length=1)
    max_height_m: float | None = Field(default=None, gt=0)


class CadImportProvenance(StrictModel):
    """Record of one CAD import (filled in by Milestone B adapters)."""

    source_document_id: Id
    original_filename: str
    sha256: Sha256
    drawing_units: UnitDeclaration
    parser: str
    parser_version: str | None = None
    horizontal_crs_status: ConfirmationStatus
    epsg: int | None = None
    vertical_datum_status: ConfirmationStatus
    #: Local origin in GRID metres, if a local frame was created.
    local_origin: Point3 | None = None
    warnings: list[str] = Field(default_factory=list)
    unrecognized_layers: list[str] = Field(default_factory=list)
    #: Entity type -> count of entities we could not interpret.
    unrecognized_entities: dict[str, int] = Field(default_factory=dict)


class Site(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    project_id: Id
    name: str
    classification: DataClassification
    coordinates: SiteCoordinates = Field(default_factory=SiteCoordinates)
    boundary: Polygon2D | None = None
    boundary_status: Epistemic = Epistemic.UNKNOWN
    buildable_envelope: BuildableEnvelope | None = None
    terrain: Terrain = Field(default_factory=Terrain)
    features: list[SiteFeature] = Field(default_factory=list)
    cad_imports: list[CadImportProvenance] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    provenance: Provenance


def site_verification_blockers(site: Site) -> list[str]:
    """Reasons the site cannot yet be approved as site truth. Empty means ready."""
    blockers: list[str] = []
    coords = site.coordinates
    if not coords.source_units.confirmed:
        blockers.append(
            f"drawing units are {coords.source_units.status.value}"
            + (f" ({coords.source_units.unit.value})" if coords.source_units.unit else "")
            + "; a human must confirm them"
        )
    if not coords.horizontal_crs.resolved:
        crs = coords.horizontal_crs
        detail = f" (source declares EPSG:{crs.declared_epsg})" if crs.declared_epsg else ""
        blockers.append(
            f"horizontal CRS is {crs.status.value}{detail}; a human must confirm the EPSG code "
            "or confirm the survey is local-only"
        )
    if not coords.vertical_datum.resolved:
        blockers.append(
            f"vertical datum is {coords.vertical_datum.status.value}; a human must confirm it "
            "or confirm elevations are relative to a local benchmark"
        )
    if coords.local is None:
        blockers.append("no local project coordinate system has been created")
    if site.boundary is None:
        blockers.append("parcel boundary is missing")
    elif site.boundary_status is not Epistemic.VERIFIED_FACT:
        blockers.append(f"parcel boundary status is {site.boundary_status.value}, not verified")
    for issue in site.issues:
        if issue.severity is Severity.BLOCKING and issue.status is IssueStatus.OPEN:
            blockers.append(f"blocking issue {issue.id}: {issue.title}")
    return blockers
