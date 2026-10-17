"""The site: parcel, coordinate systems, terrain and context.

All geometry here is in the LOCAL project frame (metres) once a local
coordinate system exists. A site that cannot be trusted reports blockers via
:func:`site_verification_blockers`; the workflow refuses the site approval
gate while any remain.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

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
    #: Boundary edge that adjoins a road; derived geometrically, so an inference.
    FRONTAGE = "frontage"
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


class TinSurface(StrictModel):
    """Triangulated terrain built only from surveyed points (LOCAL metres).

    It covers the convex hull of the survey data and nothing more: elevations
    outside it are unknown, never extrapolated.
    """

    method: Literal["delaunay_tin"] = "delaunay_tin"
    vertices: list[Point3] = Field(min_length=3)
    #: Vertex index triples, counter-clockwise.
    triangles: list[tuple[int, int, int]] = Field(min_length=1)
    #: Ids of the spot elevations and contours the vertices came from.
    source_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _indices_valid(self) -> TinSurface:
        n = len(self.vertices)
        for tri in self.triangles:
            if len(set(tri)) != 3 or not all(0 <= i < n for i in tri):
                raise ValueError(f"invalid triangle {tri} for {n} vertices")
        return self


class Terrain(StrictModel):
    status: TerrainStatus = TerrainStatus.UNKNOWN
    spot_elevations: list[SpotElevation] = Field(default_factory=list)
    contours: list[Contour] = Field(default_factory=list)
    #: Reference to a derived surface artifact (Milestone B), if any.
    surface_ref: str | None = None
    surface: TinSurface | None = None

    @model_validator(mode="after")
    def _surface_matches_status(self) -> Terrain:
        has_surface = self.surface is not None or self.surface_ref is not None
        if self.status is TerrainStatus.SURFACE_BUILT and not has_surface:
            raise ValueError("terrain status 'surface_built' needs a surface")
        return self


class BuildableEnvelope(StrictModel):
    """Where the building may stand. Its source must be stated."""

    polygon: Polygon2D
    status: Epistemic
    #: e.g. "3 m setback assumed on all sides", "zoning plan 2024 sheet 3".
    basis: str = Field(min_length=1)
    max_height_m: float | None = Field(default=None, gt=0)


class AmbiguousEntity(StrictModel):
    """A CAD entity that could not be interpreted with confidence, and why.

    Ambiguous entities are reported and left out of the site model; they are
    never silently used or dropped.
    """

    handle: str
    layer: str
    entity_type: str
    reason: str = Field(min_length=1)


class CadImportProvenance(StrictModel):
    """Record of one CAD import (filled in by Milestone B adapters)."""

    source_document_id: Id
    original_filename: str
    sha256: Sha256
    #: Detected file format and version, e.g. "dxf AC1032", "dwg AC1032".
    source_format: str | None = None
    drawing_units: UnitDeclaration
    parser: str
    parser_version: str | None = None
    #: External converter used before parsing (e.g. DWG -> DXF), if any.
    converter: str | None = None
    converter_version: str | None = None
    #: SHA-256 of the converted file the parser actually read.
    converted_sha256: Sha256 | None = None
    horizontal_crs_status: ConfirmationStatus
    epsg: int | None = None
    #: EPSG code the file declares (e.g. in a DXF GEODATA object), unconfirmed.
    declared_epsg: int | None = None
    vertical_datum_status: ConfirmationStatus
    #: Layer -> role mapping used for the import, as supplied by the user.
    layer_roles: dict[str, str] = Field(default_factory=dict)
    #: Mapping options used for the import (see house_ai.cad.layers.LayerMapping).
    zero_elevation_is_valid: bool = False
    boundary_handle: str | None = None
    ambiguous_entities: list[AmbiguousEntity] = Field(default_factory=list)
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
    #: Where the boundary came from, e.g. "src-survey#1A3 (layer BOUNDARY)".
    boundary_source_ref: str | None = None
    buildable_envelope: BuildableEnvelope | None = None
    terrain: Terrain = Field(default_factory=Terrain)
    features: list[SiteFeature] = Field(default_factory=list)
    cad_imports: list[CadImportProvenance] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    provenance: Provenance

    @property
    def has_geometry(self) -> bool:
        """Whether any local-frame geometry is populated on this site."""
        return bool(
            self.boundary is not None
            or self.buildable_envelope is not None
            or self.terrain.spot_elevations
            or self.terrain.contours
            or self.features
        )

    @property
    def geometry_frame_verified(self) -> bool:
        """Whether populated geometry has a confirmed metric unit scale and local frame."""
        return (
            self.coordinates.source_units.confirmed
            and self.coordinates.local is not None
            and self.coordinates.horizontal_crs.resolved
        )


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
    has_elevations = bool(site.terrain.spot_elevations or site.terrain.contours)
    if has_elevations and not coords.elevation_units.confirmed:
        blockers.append(
            f"elevation units are {coords.elevation_units.status.value}"
            + (f" ({coords.elevation_units.unit.value})" if coords.elevation_units.unit else "")
            + "; a human must confirm them"
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
