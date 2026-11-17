"""Interpret raw CAD entities as site geometry, using a human layer mapping.

Every entity on a mapped layer is either used (and keeps its handle as provenance) or listed
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

import hashlib
import math
import re
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
    HeightLabelCheck,
    PointGeometry,
    PolygonGeometry,
    PolylineGeometry,
    SiteFeature,
    SiteFeatureKind,
    SpotElevation,
    TerrainBreakline,
)

from .base import CadExtraction, RawPoint, RawPolyline
from .layers import FEATURE_KINDS, LayerMapping, LayerRole

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
    breaklines: list[TerrainBreakline] = field(default_factory=list)
    spot_elevations: list[SpotElevation] = field(default_factory=list)
    features: list[SiteFeature] = field(default_factory=list)
    ambiguous: list[AmbiguousEntity] = field(default_factory=list)
    #: Height labels at surveyed points, checked against the point's z.
    label_checks: list[HeightLabelCheck] = field(default_factory=list)
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

    # ---------------------------------------------------------------- driver

    def extract(self, extraction: CadExtraction, transform: SurveyTransform) -> SiteExtraction:
        out = SiteExtraction(unrecognized_entities=dict(extraction.unsupported_entities))
        by_role: dict[LayerRole, tuple[list[RawPoint], list[RawPolyline]]] = {}
        unrecognized: Counter[str] = Counter()
        unrecognized_layers: set[str] = set()
        for ent in [*extraction.points, *extraction.polylines]:
            role = self.mapping.role_of_entity(self.source_id, ent.handle, ent.layer)
            if role is None:
                unrecognized_layers.add(ent.layer)
                unrecognized[f"{ent.entity_type} on unmapped layer"] += 1
            elif role in (LayerRole.ANNOTATION, LayerRole.IGNORE):
                out.ignored_count += 1
            else:
                pts, lines = by_role.setdefault(role, ([], []))
                (pts if isinstance(ent, RawPoint) else lines).append(ent)
        if (
            self.mapping.boundary_handle is not None
            and not self.mapping.boundary_handle_targets_other_source(self.source_id)
            and LayerRole.BOUNDARY not in by_role
        ):
            by_role[LayerRole.BOUNDARY] = ([], [])
        out.unrecognized_layers = sorted(unrecognized_layers)
        out.unrecognized_entities.update(sorted(unrecognized.items()))

        for role, (pts, lines) in sorted(by_role.items()):
            if role is LayerRole.BOUNDARY:
                self._boundary(pts, lines, transform, out)
            elif role is LayerRole.CONTOUR:
                self._contours(pts, lines, transform, out)
            elif role is LayerRole.SPOT_ELEVATION:
                self._spots(pts, lines, transform, out)
            elif role is LayerRole.BREAKLINE:
                self._breaklines(pts, lines, transform, out)
            else:
                self._features(FEATURE_KINDS[role], pts, lines, transform, out)
        for line in (pl for _, lines in by_role.values() for pl in lines):
            if line.has_arcs:
                out.warnings.append(
                    f"{self._ref(line)} has arc segments; only its vertices are used, so its "
                    "length and area are chord approximations"
                )
        return out

    def _breaklines(self, pts, lines, transform, out):
        for p in pts:
            self._ambiguous(p, "breakline requires a surveyed 3D line", out)
        for line in lines:
            zs = line.zs or (
                [line.elevation] * len(line.points) if line.elevation is not None else []
            )
            if len(zs) != len(line.points) or line.has_arcs or any(self._zero(z) for z in zs):
                self._ambiguous(
                    line,
                    "breakline needs explicit valid vertex elevations and straight segments",
                    out,
                )
                continue
            points = [
                transform.source_to_local((x, y, z))
                for (x, y), z in zip(line.points, zs, strict=True)
            ]
            if line.closed and points[0] != points[-1]:
                points.append(points[0])
            try:
                out.breaklines.append(
                    TerrainBreakline(
                        id=self._id("brk", line), vertices=points, source_ref=self._ref(line)
                    )
                )
            except ValidationError as exc:
                self._ambiguous(line, f"invalid breakline: {_first_error(exc)}", out)

    # --------------------------------------------------------------- helpers

    def _id(self, prefix: str, ent: RawPoint | RawPolyline) -> str:
        """Ids carry the source, because DXF handles restart in every file."""
        raw = self.source_id.removeprefix("src-")
        if len(raw) > 24:
            # A readable head plus a digest of the whole id: distinct ids stay distinct.
            digest = hashlib.sha256(self.source_id.encode()).hexdigest()[:8]
            tag = f"{raw[:15].rstrip('-_')}-{digest}"
        else:
            tag = raw.rstrip("-_")
        return f"{prefix}-{tag}-{ent.handle.lower()}"

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
        other_source = self.mapping.boundary_handle_targets_other_source(self.source_id)
        chosen: tuple[RawPolyline, list[Point2]] | None = None
        if wanted is not None:
            if not other_source:
                chosen = next(
                    (
                        (ln, r)
                        for ln, r in rings
                        if self.mapping.matches_boundary_handle(self.source_id, ln.handle)
                    ),
                    None,
                )
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
            if (chosen is not None and line is not chosen[0]) or other_source:
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

        if wanted is not None:
            for ln in open_lines:
                self._ambiguous(ln, "open linework on a boundary layer, not part of it", out)
            return

        if not rings and open_lines:
            valid_open: list[tuple[RawPolyline, LineString]] = []
            for ln in open_lines:
                local_pts = self._local_xy(ln.points, transform)
                if len(local_pts) < 2 or LineString(local_pts).length <= CLOSE_TOL:
                    self._ambiguous(ln, "degenerate open linework on a boundary layer", out)
                else:
                    valid_open.append((ln, LineString(local_pts)))
            if not valid_open:
                return
            polygons = list(polygonize([seg for _, seg in valid_open]))
            if len(polygons) == 1:
                poly = polygons[0]
                try:
                    out.boundary = Polygon2D(outer=list(poly.exterior.coords)).oriented()
                except ValidationError as exc:
                    out.warnings.append(f"assembled boundary is invalid: {_first_error(exc)}")
                else:
                    ring_buf = poly.exterior.buffer(1e-5)
                    used = [ln for ln, seg in valid_open if ring_buf.covers(seg)]
                    unused = [ln for ln, seg in valid_open if not ring_buf.covers(seg)]
                    for ln in unused:
                        self._ambiguous(
                            ln, "open linework on a boundary layer, not part of it", out
                        )
                    handles = ",".join(ln.handle for ln in used)
                    out.boundary_source_ref = (
                        f"{self.source_id}#{handles} (assembled from {len(used)} open segments)"
                    )
                    out.warnings.append(
                        f"the boundary was assembled from {len(used)} open segments; "
                        "check it against the survey"
                    )
                    return
            for ln, _ in valid_open:
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
            if len(verts) < 2:
                self._ambiguous(line, "invalid contour geometry: fewer than 2 vertices", out)
                continue
            local = [transform.source_to_local((x, y, line.elevation)) for x, y in verts]
            try:
                contour_line = Polyline2D(
                    points=[(x, y) for x, y, _ in local], closed=ring is not None
                )
            except ValidationError as exc:
                self._ambiguous(line, f"invalid contour geometry: {_first_error(exc)}", out)
                continue
            out.contours.append(
                Contour(
                    id=self._id("ctr", line),
                    z_m=local[0][2],
                    line=contour_line,
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
        labels = [p for p in pts if p.entity_type in ("TEXT", "MTEXT")]
        for p in pts:
            if p.entity_type in ("TEXT", "MTEXT"):
                continue
            if p.z is None or self._zero(p.z):
                self._ambiguous(p, "point elevation is 0, which may mean 'not set'", out)
                continue
            x, y, z = transform.source_to_local((p.xy[0], p.xy[1], p.z))
            candidates.append(
                (
                    p,
                    SpotElevation(
                        id=self._id("spot", p), xy=(x, y), z_m=z, source_ref=self._ref(p)
                    ),
                )
            )
        disputed = self._check_labels(labels, candidates, transform, out)
        candidates = [(p, spot) for p, spot in candidates if p.handle not in disputed]
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

    def _check_labels(
        self,
        labels: list[RawPoint],
        candidates: list[tuple[RawPoint, SpotElevation]],
        transform: SurveyTransform,
        out: SiteExtraction,
    ) -> set[str]:
        """Compare each label drawn exactly at a surveyed point with that point's z.

        A label is linked to a point only when it sits at the same position (no
        nearest-point guessing). Returns the handles of points whose label disagrees.
        """
        disputed: set[str] = set()
        for label in labels:
            at = transform.source_to_local_2d(label.xy)
            point = next(
                (p for p, spot in candidates if math.dist(spot.xy, at) < SAME_POSITION_M), None
            )
            values = numeric_label_values(label.text)
            if point is None:
                reason = (
                    "height label text is not linked to a surveyed point; not used"
                    if values
                    else "text on a spot-elevation layer"
                )
                self._ambiguous(label, reason, out)
                continue
            if not values:
                self._ambiguous(
                    label,
                    f"label at surveyed point {point.handle} has no height; read as a point "
                    "name, not interpreted",
                    out,
                )
                continue
            assert point.z is not None
            match = next((v for v, tol in values if abs(v - point.z) <= tol), None)
            value = match if match is not None else values[-1][0]
            out.label_checks.append(
                HeightLabelCheck(
                    label_handle=label.handle,
                    spot_handle=point.handle,
                    label_value=value,
                    point_z=point.z,
                    agrees=match is not None,
                )
            )
            if match is None:
                disputed.add(point.handle)
                self._ambiguous(
                    point, f"its height label {label.handle} says {value} but z is {point.z}", out
                )
                self._ambiguous(label, f"disagrees with the z of point {point.handle}", out)
                out.conflicts.append(
                    f"height label {self._ref(label)} says {value} but point "
                    f"{self._ref(point)} has z {point.z}"
                )
        return disputed

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
        area_or_line_kinds = {
            SiteFeatureKind.ROAD,
            SiteFeatureKind.EASEMENT,
            SiteFeatureKind.EXISTING_STRUCTURE,
            SiteFeatureKind.WATER,
        }
        for p in pts:
            if p.entity_type in ("TEXT", "MTEXT"):
                self._ambiguous(p, f"text label on a {kind.value} layer; not interpreted", out)
                continue
            if kind in area_or_line_kinds:
                reason = (
                    f"{p.entity_type.lower()} on a {kind.value} layer; linework or polygon expected"
                )
                self._ambiguous(p, reason, out)
                continue
            out.features.append(
                SiteFeature(
                    id=self._id(prefix, p),
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
                    id=self._id(prefix, line),
                    kind=kind,
                    geometry=geometry,
                    status=Epistemic.INFERENCE,
                    source_ref=self._ref(line),
                    notes="classified by the layer mapping",
                )
            )


_POINT_HEADER_RE = re.compile(r"^(?:pt|p|pnt|point|no\.?|#|bm|tp)\s*[-#.:]?\s*$", re.IGNORECASE)
_LABEL_HEIGHT_RE = re.compile(
    r"^(?:"
    r"(?:(?:z|h|el|elev|elevation|height|kote|höhe)\s*[:=]?\s*([+-]?(?:\d+\.\d*|\.\d+|\d+)))"
    r"|(?:(?:pt|p|pnt|point|bm|tp|#)\s*[-#.]?\s*\d+\s*[:=]?\s+([+-]?(?:\d+\.\d+|\.\d+)))"
    r"|([+-]?(?:\d+\.\d*|\.\d+|\d+))"
    r")(?:\s*(?:m|mm|cm|ft|'))?$",
    re.IGNORECASE,
)


def numeric_label_values(text: str | None) -> list[tuple[float, float]]:
    """Each line of a label that is a height number, with half a unit of its last decimal.

    ``"Pt1\\n101.250"`` gives ``[(101.250, 0.0005)]``: the label agrees with any z
    that rounds to what is written. Inline units (``"1664.0 m"``) and inline point
    names before a decimal height (``"Pt1 101.25"``) are accepted; a bare integer
    immediately after a point-header line (``"Pt\\n12"``) is treated as a point ID,
    not an elevation.
    """
    out: list[tuple[float, float]] = []
    lines = [ln.strip() for ln in (text or "").replace("\\P", "\n").splitlines() if ln.strip()]
    prev_is_point_header = False
    for line in lines:
        normalized = line.replace(",", ".")
        m = _LABEL_HEIGHT_RE.match(normalized)
        if m is None:
            prev_is_point_header = bool(_POINT_HEADER_RE.match(line))
            continue
        token = m.group(1) or m.group(2) or m.group(3)
        assert token is not None
        has_unit = normalized[-1].lower() in ("m", "t", "'")
        if prev_is_point_header and "." not in token and not has_unit and m.group(1) is None:
            prev_is_point_header = False
            continue
        prev_is_point_header = False
        try:
            val = float(token)
        except ValueError:
            continue
        if math.isfinite(val):
            decimals = len(token.partition(".")[2]) if "." in token else 0
            out.append((val, 0.5 * 10.0**-decimals + 1e-9))
    return out


def has_numeric_elevation_label(text: str | None) -> bool:
    """Whether ``text`` (or a line in a multi-line label like ``Pt1\\n101.250``) is a number."""
    return bool(numeric_label_values(text))


_is_number = has_numeric_elevation_label


def _first_error(exc: ValidationError) -> str:
    return exc.errors()[0]["msg"]
