"""Interpret raw CAD entities as site geometry, using a human layer mapping.

Implements :class:`house_ai.cad.base.CadSiteExtractor`. Every entity on a
mapped layer is either used (and keeps its handle as provenance) or listed
as an :class:`~house_ai.domain.site.AmbiguousEntity` with the reason. Rules:

* boundary: exactly one closed polyline on the boundary layers, or the one
  named by ``boundary_handle``; several candidates and nothing is chosen.
  Open linework is assembled into a polygon only if it forms exactly one.
* contours: polylines with one constant, non-zero elevation. A polyline
  whose z varies is not a contour; elevation 0 counts as "unset" unless the
  mapping says zero is a real elevation.
* spot elevations: POINT, INSERT and CIRCLE entities with a non-zero z.
  Text that looks like a height is never linked to a nearby point by
  guesswork. Two spots at one position with different z are a conflict.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from pydantic import ValidationError
from shapely.geometry import LineString
from shapely.ops import polygonize

from house_ai.domain.coordinates import SurveyTransform
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.geometry import Point2, Polygon2D, Polyline2D
from house_ai.domain.site import (
    AmbiguousEntity,
    Contour,
    PointGeometry,
    PolygonGeometry,
    PolylineGeometry,
    SiteFeature,
    SiteFeatureKind,
    SpotElevation,
)

from .base import CadExtraction, CadInspection, RawPoint, RawPolyline
from .layers import FEATURE_KINDS, UNCLASSIFIED, LayerMapping, LayerRole

#: Coincidence tolerance in drawing units for "first vertex == last vertex".
CLOSE_TOL = 1e-6
#: Two spot elevations closer than this (metres) are at the same position.
SAME_POSITION_M = 1e-3

_ID_PREFIX: dict[SiteFeatureKind, str] = {
    SiteFeatureKind.ROAD: "road",
    SiteFeatureKind.EASEMENT: "esmt",
    SiteFeatureKind.EXISTING_STRUCTURE: "bldg",
    SiteFeatureKind.UTILITY: "util",
    SiteFeatureKind.TREE: "tree",
    SiteFeatureKind.WATER: "water",
    SiteFeatureKind.ACCESS_POINT: "access",
    SiteFeatureKind.OTHER: "feat",
}


@dataclass
class SiteExtraction:
    """Everything interpreted from one drawing, in the LOCAL frame."""

    boundary: Polygon2D | None = None
    boundary_source_ref: str | None = None
    #: Handles of all closed polylines that could be the boundary.
    boundary_candidates: list[str] = field(default_factory=list)
    contours: list[Contour] = field(default_factory=list)
    spot_elevations: list[SpotElevation] = field(default_factory=list)
    features: list[SiteFeature] = field(default_factory=list)
    ambiguous: list[AmbiguousEntity] = field(default_factory=list)
    #: Layers that hold entities but have no role in the mapping.
    unrecognized_layers: list[str] = field(default_factory=list)
    #: Entity type -> count, for entities not interpreted at all.
    unrecognized_entities: dict[str, int] = field(default_factory=dict)
    #: Entities skipped on purpose (annotation / ignore layers).
    ignored_count: int = 0
    #: Contradictions in the data that must block approval.
    conflicts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class MappedLayerSiteExtractor:
    def __init__(self, mapping: LayerMapping, source_id: str) -> None:
        self.mapping = mapping
        self.source_id = source_id

    # ------------------------------------------------------ CadSiteExtractor

    def classify_layers(self, inspection: CadInspection) -> dict[str, str]:
        out = {}
        for layer in inspection.layers:
            role = self.mapping.role_of(layer)
            out[layer] = role.value if role else UNCLASSIFIED
        return out

    def extract_boundary(
        self, extraction: CadExtraction, transform: SurveyTransform
    ) -> Polygon2D | None:
        return self.extract(extraction, transform).boundary

    def extract_contours(
        self, extraction: CadExtraction, transform: SurveyTransform
    ) -> list[Contour]:
        return self.extract(extraction, transform).contours

    def extract_spot_elevations(
        self, extraction: CadExtraction, transform: SurveyTransform
    ) -> list[SpotElevation]:
        return self.extract(extraction, transform).spot_elevations

    def extract_features(
        self, extraction: CadExtraction, transform: SurveyTransform
    ) -> list[SiteFeature]:
        return self.extract(extraction, transform).features

    # ---------------------------------------------------------------- driver

    def extract(self, extraction: CadExtraction, transform: SurveyTransform) -> SiteExtraction:
        out = SiteExtraction(unrecognized_entities=dict(extraction.unsupported_entities))
        by_role: dict[LayerRole, tuple[list[RawPoint], list[RawPolyline]]] = {}
        unrecognized: Counter[str] = Counter()
        unrecognized_layers: set[str] = set()
        for ent in [*extraction.points, *extraction.polylines]:
            role = self.mapping.role_of(ent.layer)
            if role is None:
                unrecognized_layers.add(ent.layer)
                unrecognized[f"{ent.entity_type} on unmapped layer"] += 1
            elif role in (LayerRole.ANNOTATION, LayerRole.IGNORE):
                out.ignored_count += 1
            else:
                pts, lines = by_role.setdefault(role, ([], []))
                (pts if isinstance(ent, RawPoint) else lines).append(ent)
        out.unrecognized_layers = sorted(unrecognized_layers)
        out.unrecognized_entities.update(sorted(unrecognized.items()))

        for role, (pts, lines) in sorted(by_role.items()):
            if role is LayerRole.BOUNDARY:
                self._boundary(pts, lines, transform, out)
            elif role is LayerRole.CONTOUR:
                self._contours(pts, lines, transform, out)
            elif role is LayerRole.SPOT_ELEVATION:
                self._spots(pts, lines, transform, out)
            else:
                self._features(FEATURE_KINDS[role], pts, lines, transform, out)
        for line in (pl for _, lines in by_role.values() for pl in lines):
            if line.has_arcs:
                out.warnings.append(
                    f"{self._ref(line)} has arc segments; only its vertices are used, so its "
                    "length and area are chord approximations"
                )
        return out

    # --------------------------------------------------------------- helpers

    def _ref(self, ent: RawPoint | RawPolyline) -> str:
        return f"{self.source_id}#{ent.handle} (layer {ent.layer})"

    def _ambiguous(self, ent: RawPoint | RawPolyline, reason: str, out: SiteExtraction) -> None:
        out.ambiguous.append(
            AmbiguousEntity(
                handle=ent.handle, layer=ent.layer, entity_type=ent.entity_type, reason=reason
            )
        )

    def _zero(self, z: float | None) -> bool:
        return z == 0.0 and not self.mapping.zero_elevation_is_valid

    @staticmethod
    def _ring(line: RawPolyline) -> list[Point2] | None:
        """The polyline's vertices as a ring, if it is closed (flag or coincident ends)."""
        pts = list(line.points)
        if len(pts) >= 4 and math.dist(pts[0], pts[-1]) <= CLOSE_TOL:
            return pts[:-1]
        if line.closed and len(pts) >= 3:
            return pts
        return None

    def _local_xy(self, pts: list[Point2], transform: SurveyTransform) -> list[Point2]:
        return [transform.source_to_local_2d(p) for p in pts]

    # -------------------------------------------------------------- boundary

    def _boundary(
        self,
        pts: list[RawPoint],
        lines: list[RawPolyline],
        transform: SurveyTransform,
        out: SiteExtraction,
    ) -> None:
        for p in pts:
            self._ambiguous(p, "point or text on a boundary layer; not part of the boundary", out)
        rings = [(line, ring) for line in lines if (ring := self._ring(line)) is not None]
        open_lines = [line for line in lines if self._ring(line) is None]
        out.boundary_candidates = [line.handle for line, _ in rings]
        wanted = self.mapping.boundary_handle
        chosen: tuple[RawPolyline, list[Point2]] | None = None
        if wanted is not None:
            chosen = next(((ln, r) for ln, r in rings if ln.handle == wanted), None)
            if chosen is None:
                out.conflicts.append(
                    f"boundary_handle {wanted!r} is not a closed polyline on a boundary layer"
                )
        elif len(rings) == 1:
            chosen = rings[0]
        elif len(rings) > 1:
            for line, _ in rings:
                self._ambiguous(
                    line,
                    f"one of {len(rings)} closed polylines on the boundary layers; name the "
                    "parcel with boundary_handle in the layer mapping",
                    out,
                )
        for line, _ in rings:
            if chosen is not None and line is not chosen[0]:
                self._ambiguous(line, "closed polyline on a boundary layer, not chosen", out)

        if chosen is not None:
            line, ring = chosen
            try:
                out.boundary = Polygon2D(outer=self._local_xy(ring, transform)).oriented()
                out.boundary_source_ref = self._ref(line)
            except ValidationError as exc:
                self._ambiguous(line, f"boundary is not a valid polygon: {_first_error(exc)}", out)
            for ln in open_lines:
                self._ambiguous(ln, "open linework on a boundary layer, not part of it", out)
            return

        if not rings and open_lines:
            segments = [LineString(self._local_xy(ln.points, transform)) for ln in open_lines]
            polygons = list(polygonize(segments))
            if len(polygons) == 1:
                poly = polygons[0]
                try:
                    out.boundary = Polygon2D(outer=list(poly.exterior.coords)).oriented()
                except ValidationError as exc:
                    out.warnings.append(f"assembled boundary is invalid: {_first_error(exc)}")
                else:
                    handles = ",".join(ln.handle for ln in open_lines)
                    out.boundary_source_ref = (
                        f"{self.source_id}#{handles} (assembled from {len(open_lines)} "
                        "open segments)"
                    )
                    out.warnings.append(
                        f"the boundary was assembled from {len(open_lines)} open segments; "
                        "check it against the survey"
                    )
                    return
            for ln in open_lines:
                self._ambiguous(
                    ln,
                    f"open linework on a boundary layer forms {len(polygons)} polygons, not one",
                    out,
                )

    # -------------------------------------------------------------- contours

    def _contours(
        self,
        pts: list[RawPoint],
        lines: list[RawPolyline],
        transform: SurveyTransform,
        out: SiteExtraction,
    ) -> None:
        for p in pts:
            self._ambiguous(p, "point or label on a contour layer; contours are lines", out)
        for line in lines:
            if line.elevation is None:
                self._ambiguous(line, "z varies along the line, so it is not a contour", out)
                continue
            if self._zero(line.elevation):
                self._ambiguous(line, "contour elevation is 0, which may mean 'not set'", out)
                continue
            ring = self._ring(line)
            verts = ring if ring is not None else line.points
            local = [transform.source_to_local((x, y, line.elevation)) for x, y in verts]
            out.contours.append(
                Contour(
                    id=f"ctr-{line.handle.lower()}",
                    z_m=local[0][2],
                    line=Polyline2D(points=[(x, y) for x, y, _ in local], closed=ring is not None),
                    source_ref=self._ref(line),
                )
            )

    # ----------------------------------------------------------------- spots

    def _spots(
        self,
        pts: list[RawPoint],
        lines: list[RawPolyline],
        transform: SurveyTransform,
        out: SiteExtraction,
    ) -> None:
        for line in lines:
            self._ambiguous(line, "linework on a spot-elevation layer", out)
        candidates: list[tuple[RawPoint, SpotElevation]] = []
        for p in pts:
            if p.entity_type in ("TEXT", "MTEXT"):
                reason = (
                    "height label text is not linked to a surveyed point; not used"
                    if _is_number(p.text)
                    else "text on a spot-elevation layer"
                )
                self._ambiguous(p, reason, out)
                continue
            if p.z is None or self._zero(p.z):
                self._ambiguous(p, "point elevation is 0, which may mean 'not set'", out)
                continue
            x, y, z = transform.source_to_local((p.xy[0], p.xy[1], p.z))
            candidates.append(
                (
                    p,
                    SpotElevation(
                        id=f"spot-{p.handle.lower()}", xy=(x, y), z_m=z, source_ref=self._ref(p)
                    ),
                )
            )
        for i, (p, spot) in enumerate(candidates):
            clash = [
                (q, other)
                for j, (q, other) in enumerate(candidates)
                if j != i
                and math.dist(spot.xy, other.xy) < SAME_POSITION_M
                and other.z_m != spot.z_m
            ]
            if clash:
                self._ambiguous(
                    p, f"same position as {clash[0][0].handle} with a different elevation", out
                )
                if i < candidates.index(clash[0]):
                    out.conflicts.append(
                        f"spot elevations {p.handle} and {clash[0][0].handle} share a position "
                        f"but differ ({spot.z_m:.3f} m vs {clash[0][1].z_m:.3f} m)"
                    )
            else:
                out.spot_elevations.append(spot)

    # -------------------------------------------------------------- features

    def _features(
        self,
        kind: SiteFeatureKind,
        pts: list[RawPoint],
        lines: list[RawPolyline],
        transform: SurveyTransform,
        out: SiteExtraction,
    ) -> None:
        prefix = _ID_PREFIX[kind]
        for p in pts:
            if p.entity_type in ("TEXT", "MTEXT"):
                self._ambiguous(p, f"text label on a {kind.value} layer; not interpreted", out)
                continue
            out.features.append(
                SiteFeature(
                    id=f"{prefix}-{p.handle.lower()}",
                    kind=kind,
                    name=p.block_name,
                    geometry=PointGeometry(xy=transform.source_to_local_2d(p.xy)),
                    status=Epistemic.INFERENCE,
                    source_ref=self._ref(p),
                )
            )
        for line in lines:
            ring = self._ring(line)
            geometry: PolygonGeometry | PolylineGeometry
            try:
                if ring is not None:
                    geometry = PolygonGeometry(
                        polygon=Polygon2D(outer=self._local_xy(ring, transform)).oriented()
                    )
                else:
                    geometry = PolylineGeometry(
                        line=Polyline2D(points=self._local_xy(line.points, transform))
                    )
            except ValidationError as exc:
                self._ambiguous(line, f"invalid geometry: {_first_error(exc)}", out)
                continue
            out.features.append(
                SiteFeature(
                    id=f"{prefix}-{line.handle.lower()}",
                    kind=kind,
                    geometry=geometry,
                    status=Epistemic.INFERENCE,
                    source_ref=self._ref(line),
                    notes="classified by the layer mapping",
                )
            )


def _is_number(text: str | None) -> bool:
    if not text:
        return False
    try:
        float(text.strip().replace(",", "."))
    except ValueError:
        return False
    return True


def _first_error(exc: ValidationError) -> str:
    return exc.errors()[0]["msg"]
