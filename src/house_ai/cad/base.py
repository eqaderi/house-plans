"""CAD ingestion boundary (Milestone B).

The rest of the application depends only on these protocols, never on a CAD
library. Adapters: DXF via ezdxf (:mod:`house_ai.cad.dxf_ezdxf`) and DWG via
an external DWG->DXF converter (:mod:`house_ai.cad.dwg_oda`). Every import
produces a :class:`~house_ai.domain.site.CadImportProvenance` and stops at
SITE_NEEDS_VERIFICATION when units or CRS are ambiguous.

Raw CAD entities extracted by :meth:`CadAdapter.extract_cad` remain in SOURCE
coordinates and units until units and the local project coordinate system are
confirmed and converted to LOCAL metres.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from house_ai.domain.coordinates import SurveyTransform
from house_ai.domain.geometry import Point2, Polygon2D
from house_ai.domain.site import (
    CadImportProvenance,
    Contour,
    SiteFeature,
    SpotElevation,
)


@dataclass(frozen=True)
class RawPoint:
    """A point or text/insert entity in raw SOURCE coordinates and drawing units."""

    xy: Point2
    z: float | None = None
    layer: str = ""
    text: str | None = None
    #: DXF entity handle: stable within the file, used for provenance.
    handle: str = ""
    #: POINT, TEXT, MTEXT, INSERT or CIRCLE.
    entity_type: str = ""
    block_name: str | None = None


@dataclass(frozen=True)
class RawPolyline:
    """A line or polyline entity in raw SOURCE coordinates and drawing units."""

    points: list[Point2]
    closed: bool = False
    #: Constant elevation (LWPOLYLINE elevation, or a 3D polyline whose
    #: vertices all share one z). None when the z values differ.
    elevation: float | None = None
    layer: str = ""
    handle: str = ""
    #: LINE, LWPOLYLINE or POLYLINE.
    entity_type: str = ""
    #: Per-vertex z for 3D polylines and lines; empty for 2D entities.
    zs: list[float] = field(default_factory=list)
    #: True when some segments are arcs (bulges); points are then only the
    #: vertices, so lengths and areas from them are chord approximations.
    has_arcs: bool = False


@dataclass(frozen=True)
class CadInspection:
    """What is in a drawing, before anything is interpreted."""

    parser: str
    parser_version: str | None
    declared_insunits: int | None
    layers: dict[str, int] = field(default_factory=dict)
    entity_counts: dict[str, int] = field(default_factory=dict)
    extents: tuple[float, float, float, float] | None = None
    warnings: list[str] = field(default_factory=list)
    #: e.g. "dxf AC1032".
    source_format: str | None = None
    #: Layer -> entity type -> count.
    layer_entity_types: dict[str, dict[str, int]] = field(default_factory=dict)
    #: Selected header variables as found ($MEASUREMENT, $LUNITS, ...).
    header: dict[str, object] = field(default_factory=dict)
    #: Summary of a DXF GEODATA object, when present.
    geodata: dict[str, object] | None = None
    #: EPSG code declared by the file (GEODATA), never inferred.
    declared_epsg: int | None = None
    #: Converter used before parsing, its version, and the converted file's SHA-256.
    converter: str | None = None
    converter_version: str | None = None
    converted_sha256: str | None = None


@dataclass(frozen=True)
class CadExtraction:
    """Geometry pulled from a drawing, still in SOURCE coordinates and units."""

    #: Filled in once the file is registered in a project store; None for a
    #: read-only inspection.
    provenance: CadImportProvenance | None = None
    points: list[RawPoint] = field(default_factory=list)
    polylines: list[RawPolyline] = field(default_factory=list)
    layer_roles: dict[str, str] = field(default_factory=dict)
    inspection: CadInspection | None = None
    #: Entity type -> count of entities the adapter cannot represent.
    unsupported_entities: dict[str, int] = field(default_factory=dict)


class CadAdapter(Protocol):
    name: str

    def can_read(self, path: Path) -> bool: ...

    def inspect_cad(self, path: Path) -> CadInspection: ...

    def extract_cad(self, path: Path, layer_roles: dict[str, str]) -> CadExtraction: ...


class CadSiteExtractor(Protocol):
    """Transforms raw SOURCE-frame CAD entities into LOCAL metric Site geometry.

    ``transform`` carries the horizontal and elevation unit scales and the
    local frame, so elevations may use a different unit from x/y.
    """

    def classify_layers(self, inspection: CadInspection) -> dict[str, str]: ...

    def extract_boundary(
        self,
        extraction: CadExtraction,
        transform: SurveyTransform,
    ) -> Polygon2D | None: ...

    def extract_contours(
        self,
        extraction: CadExtraction,
        transform: SurveyTransform,
    ) -> list[Contour]: ...

    def extract_spot_elevations(
        self,
        extraction: CadExtraction,
        transform: SurveyTransform,
    ) -> list[SpotElevation]: ...

    def extract_features(
        self,
        extraction: CadExtraction,
        transform: SurveyTransform,
    ) -> list[SiteFeature]: ...
