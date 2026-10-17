"""CAD ingestion boundary (Milestone B).

The rest of the application depends only on this protocol, never on a CAD
library. Adapters planned: DXF via ezdxf, DWG via GDAL/OGR when available,
DWG->DXF via an external converter. Every import must produce a
:class:`~house_ai.domain.site.CadImportProvenance` and must stop at
SITE_NEEDS_VERIFICATION when units or CRS are ambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from house_ai.domain.geometry import Polygon2D
from house_ai.domain.site import CadImportProvenance, Contour, SpotElevation


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
    boundary: Polygon2D | None
    contours: list[Contour]
    spot_elevations: list[SpotElevation]


class CadAdapter(Protocol):
    name: str

    def can_read(self, path: Path) -> bool: ...

    def inspect_cad(self, path: Path) -> CadInspection: ...

    def extract_cad(self, path: Path, layer_roles: dict[str, str]) -> CadExtraction: ...
