"""CAD ingestion boundary (Milestone B).

The rest of the application depends only on this protocol, never on a CAD
library. Adapters planned: DXF via ezdxf, DWG via GDAL/OGR when available,
DWG->DXF via an external converter. Every import must produce a
:class:`~house_ai.domain.site.CadImportProvenance` and must stop at
SITE_NEEDS_VERIFICATION when units or CRS are ambiguous.

Raw CAD entities extracted by :meth:`CadAdapter.extract_cad` remain in SOURCE
coordinates and units until units and the local project coordinate system are
confirmed and converted to LOCAL metres.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from house_ai.domain.coordinates import LocalCoordinateSystem
from house_ai.domain.geometry import Point2, Polygon2D
from house_ai.domain.site import (
    CadImportProvenance,
    Contour,
    SiteFeature,
    SpotElevation,
)
from house_ai.domain.units import LengthUnit


@dataclass(frozen=True)
class RawPoint:
    """A point or text/insert entity in raw SOURCE coordinates and drawing units."""

    xy: Point2
    z: float | None = None
    layer: str = ""
    text: str | None = None


@dataclass(frozen=True)
class RawPolyline:
    """A line or polyline entity in raw SOURCE coordinates and drawing units."""

    points: list[Point2]
    closed: bool = False
    elevation: float | None = None
    layer: str = ""


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


@dataclass(frozen=True)
class CadExtraction:
    """Geometry pulled from a drawing, still in SOURCE coordinates and units."""

    provenance: CadImportProvenance
    points: list[RawPoint] = field(default_factory=list)
    polylines: list[RawPolyline] = field(default_factory=list)
    layer_roles: dict[str, str] = field(default_factory=dict)


class CadAdapter(Protocol):
    name: str

    def can_read(self, path: Path) -> bool: ...

    def inspect_cad(self, path: Path) -> CadInspection: ...

    def extract_cad(self, path: Path, layer_roles: dict[str, str]) -> CadExtraction: ...


class CadSiteExtractor(Protocol):
    """Transforms raw SOURCE-frame CAD entities into LOCAL metric Site geometry."""

    def classify_layers(self, inspection: CadInspection) -> dict[str, str]: ...

    def extract_boundary(
        self,
        extraction: CadExtraction,
        source_unit: LengthUnit,
        local_frame: LocalCoordinateSystem,
    ) -> Polygon2D | None: ...

    def extract_contours(
        self,
        extraction: CadExtraction,
        source_unit: LengthUnit,
        local_frame: LocalCoordinateSystem,
    ) -> list[Contour]: ...

    def extract_spot_elevations(
        self,
        extraction: CadExtraction,
        source_unit: LengthUnit,
        local_frame: LocalCoordinateSystem,
    ) -> list[SpotElevation]: ...

    def extract_features(
        self,
        extraction: CadExtraction,
        source_unit: LengthUnit,
        local_frame: LocalCoordinateSystem,
    ) -> list[SiteFeature]: ...

