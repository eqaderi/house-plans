"""Deterministic and visual defect detectors for plan models (Stage S5, Task S5-07).

Detects visual and geometric defects including:
- Windows hosted on retaining walls (buried in earth).
- Doors clashing into walls or openings with zero clearance.
- Overlapping room labels / overlapping spaces.
- Missing or invalid stair arrival connections.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from house_ai.constants.evaluations import MIN_STAIR_HEADROOM_M
from house_ai.constants.reviewer import (
    DEFAULT_LABEL_PADDING_PX,
    DEFAULT_MIN_LABEL_DISTANCE_M,
    DEFECT_DOOR_EXCEEDS_WALL,
    DEFECT_MISSING_HOST_WALL,
    DEFECT_MISSING_STAIR_ARRIVAL,
    DEFECT_MISSING_STAIR_LEVEL,
    DEFECT_OVERLAPPING_LABELS,
    DEFECT_STAIR_THROUGH_SLAB,
    DEFECT_WINDOW_ON_RETAINING_WALL,
    MARGIN,
    MIN_SLAB_INTERSECTION_AREA_M2,
    PANEL_W,
)
from house_ai.domain.model import HouseModel, OpeningKind, SlabKind, WallKind
from house_ai.evaluation.usability import _pitch
from house_ai.render2d.plan_svg import _rect_dims


@dataclass
class DefectFinding:
    defect_type: str
    element_ids: list[str]
    description: str
    suggested_op: str | None = None


def _polygon_centroid(points: Sequence[Sequence[float]]) -> tuple[float, float]:
    """Calculate the centroid of a polygon vertex ring."""
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return (cx, cy)


def detect_windows_on_retaining_walls(model: HouseModel) -> list[DefectFinding]:
    """Flag any window hosted on a retaining wall (which faces earth)."""
    wall_map = {w.id: w for w in model.walls or []}
    findings: list[DefectFinding] = []

    for op in model.openings or []:
        if op.kind == OpeningKind.WINDOW:
            host = wall_map.get(op.host_wall_id)
            if host and host.kind == WallKind.RETAINING:
                findings.append(
                    DefectFinding(
                        defect_type=DEFECT_WINDOW_ON_RETAINING_WALL,
                        element_ids=[op.id, host.id],
                        description=(
                            f"Window '{op.id}' is hosted on retaining wall '{host.id}' "
                            "which faces earth/soil."
                        ),
                        suggested_op=f"separate:{op.id},{host.id}",
                    )
                )

    return findings


def detect_overlapping_space_labels(
    model: HouseModel, min_label_distance_m: float = DEFAULT_MIN_LABEL_DISTANCE_M
) -> list[DefectFinding]:
    """Flag spaces whose label centers or rendered bounding boxes collide / overlap.

    Detects both 3D/local centroid proximity (closer than min_label_distance_m)
    and 2D canvas label bounding box collisions at default plan viewing scale.
    """
    spaces_by_level: dict[str, list] = {}
    valid_shapes = []
    for sp in model.spaces or []:
        spaces_by_level.setdefault(sp.level_id, []).append(sp)
        if sp.boundary and sp.boundary.outer:
            poly = sp.boundary.to_shapely()
            if poly.is_valid and not poly.is_empty:
                valid_shapes.append(poly)

    if not spaces_by_level:
        return []

    # Compute rendered view scale across the model
    scale = 30.0
    minx, maxy = 0.0, 0.0
    if valid_shapes:
        bounds = unary_union(valid_shapes).buffer(2.5).bounds
        minx, miny, maxx, maxy = bounds
        scale = (PANEL_W - 2 * MARGIN) / max(maxx - minx, maxy - miny, 1.0)

    findings: list[DefectFinding] = []

    for _lvl_id, sp_list in spaces_by_level.items():
        boxes: dict[str, tuple[box, tuple[float, float]]] = {}
        for sp in sp_list:
            if not sp.boundary or not sp.boundary.outer:
                continue
            poly = sp.boundary.to_shapely()
            if not poly.is_valid:
                poly = poly.buffer(0)
            rep_pt = poly.representative_point()
            cx, cy = rep_pt.x, rep_pt.y
            px = (cx - minx) * scale
            py = (maxy - cy) * scale

            L, W = _rect_dims(sp.boundary)
            small = L * scale < 70
            name = sp.name if not small else sp.name.split(" ")[0]
            w = max(
                len(name) * (9 if not small else 7),
                len(f"{sp.area_m2:.1f} m²") * 8,
                len(f"{L:.2f} × {W:.2f}") * 7,
            ) * 0.55
            b = box(
                px - w / 2 - DEFAULT_LABEL_PADDING_PX,
                py - 12 - DEFAULT_LABEL_PADDING_PX,
                px + w / 2 + DEFAULT_LABEL_PADDING_PX,
                py + 22 + DEFAULT_LABEL_PADDING_PX,
            )
            boxes[sp.id] = (b, (cx, cy))

        for i in range(len(sp_list)):
            sp_a = sp_list[i]
            if sp_a.id not in boxes:
                continue
            box_a, center_a = boxes[sp_a.id]

            for j in range(i + 1, len(sp_list)):
                sp_b = sp_list[j]
                if sp_b.id not in boxes:
                    continue
                box_b, center_b = boxes[sp_b.id]

                dist = math.dist(center_a, center_b)
                box_clash = box_a.intersects(box_b)

                if dist < min_label_distance_m or box_clash:
                    if box_clash:
                        reason = f"colliding label bounding boxes (distance {dist:.2f} m)"
                    else:
                        reason = (
                            f"colliding label centers "
                            f"(distance {dist:.2f} m < {min_label_distance_m:.2f} m)"
                        )
                    findings.append(
                        DefectFinding(
                            defect_type=DEFECT_OVERLAPPING_LABELS,
                            element_ids=[sp_a.id, sp_b.id],
                            description=f"Spaces '{sp_a.id}' and '{sp_b.id}' have {reason}.",
                            suggested_op=f"separate:{sp_a.id},{sp_b.id}",
                        )
                    )

    return findings


def detect_stair_arrival_defects(model: HouseModel) -> list[DefectFinding]:
    """Flag stairs where top_space_id or bottom_space_id does not exist on the connected levels."""
    space_level_map = {sp.id: sp.level_id for sp in model.spaces or []}
    level_ids = {lvl.id for lvl in model.levels or []}
    findings: list[DefectFinding] = []

    for st in model.stairs or []:
        # Check level existence
        if st.from_level_id not in level_ids:
            findings.append(
                DefectFinding(
                    defect_type=DEFECT_MISSING_STAIR_LEVEL,
                    element_ids=[st.id],
                    description=(
                        f"Stair '{st.id}' references nonexistent "
                        f"from_level '{st.from_level_id}'."
                    ),
                )
            )
        if st.to_level_id not in level_ids:
            findings.append(
                DefectFinding(
                    defect_type=DEFECT_MISSING_STAIR_LEVEL,
                    element_ids=[st.id],
                    description=(
                        f"Stair '{st.id}' references nonexistent "
                        f"to_level '{st.to_level_id}'."
                    ),
                )
            )

        # Check arrival spaces
        if st.top_space_id and st.top_space_id not in space_level_map:
            findings.append(
                DefectFinding(
                    defect_type=DEFECT_MISSING_STAIR_ARRIVAL,
                    element_ids=[st.id, st.top_space_id],
                    description=(
                        f"Stair '{st.id}' arrives at nonexistent "
                        f"top space '{st.top_space_id}'."
                    ),
                )
            )
        if st.bottom_space_id and st.bottom_space_id not in space_level_map:
            findings.append(
                DefectFinding(
                    defect_type=DEFECT_MISSING_STAIR_ARRIVAL,
                    element_ids=[st.id, st.bottom_space_id],
                    description=(
                        f"Stair '{st.id}' departs from nonexistent "
                        f"bottom space '{st.bottom_space_id}'."
                    ),
                )
            )

    return findings


def detect_door_into_wall_clash(model: HouseModel) -> list[DefectFinding]:
    """Flag doors whose position exceeds the host wall length or clashes into corners."""
    wall_map = {w.id: w for w in model.walls or []}
    findings: list[DefectFinding] = []

    for op in model.openings or []:
        if op.kind == OpeningKind.DOOR:
            host = wall_map.get(op.host_wall_id)
            if not host:
                findings.append(
                    DefectFinding(
                        defect_type=DEFECT_MISSING_HOST_WALL,
                        element_ids=[op.id],
                        description=f"Door '{op.id}' has missing host wall '{op.host_wall_id}'.",
                    )
                )
                continue

            wall_len = math.dist(host.start[:2], host.end[:2])

            if op.offset_m + op.width_m > wall_len + 1e-4:
                findings.append(
                    DefectFinding(
                        defect_type=DEFECT_DOOR_EXCEEDS_WALL,
                        element_ids=[op.id, host.id],
                        description=(
                            f"Door '{op.id}' (offset {op.offset_m}m + width {op.width_m}m) "
                            f"exceeds host wall '{host.id}' length ({wall_len:.2f}m) "
                            "and clashes into corner/wall intersection."
                        ),
                        suggested_op=f"separate:{op.id},{host.id}",
                    )
                )

    return findings


def detect_stair_through_slab(model: HouseModel) -> list[DefectFinding]:
    """Flag stair flights intersecting floor or roof slabs without a void."""
    level_map = {lvl.id: lvl for lvl in model.levels or []}
    findings: list[DefectFinding] = []

    for st in model.stairs or []:
        if st.from_level_id not in level_map or st.to_level_id not in level_map:
            continue
        from_lvl = level_map[st.from_level_id]
        to_lvl = level_map[st.to_level_id]
        z_bot = min(from_lvl.elevation_m, to_lvl.elevation_m)
        z_top = max(from_lvl.elevation_m, to_lvl.elevation_m)
        rise = abs(to_lvl.elevation_m - from_lvl.elevation_m)
        st_poly = st.footprint.to_shapely()
        if not st_poly.is_valid:
            st_poly = st_poly.buffer(0)
        st_line = LineString(st.walking_line) if st.walking_line else None

        for sl in model.slabs or []:
            if sl.level_id not in level_map:
                continue
            sl_lvl = level_map[sl.level_id]
            sl_top = sl_lvl.elevation_m + sl.top_offset_m
            sl_bot = sl_top - sl.thickness_m

            # Supporting floor at or below the departure level is fine
            if sl_top <= z_bot + 0.05 and sl.kind == SlabKind.FLOOR:
                continue
            # Slab safely above the arrival floor + headroom is fine
            if sl_bot >= z_top + MIN_STAIR_HEADROOM_M - 0.01:
                continue

            sl_poly = sl.boundary.to_shapely()
            if not sl_poly.is_valid:
                sl_poly = sl_poly.buffer(0)

            inter_poly = st_poly.intersection(sl_poly)
            inter_line = st_line.intersection(sl_poly) if st_line else None

            has_clash = False
            if inter_line is not None and not inter_line.is_empty and inter_line.length > 0.05:
                pieces = list(inter_line.geoms) if hasattr(inter_line, "geoms") else [inter_line]
                pieces = [p for p in pieces if p.geom_type == "LineString" and p.length > 1e-4]
                if pieces:
                    distances = [
                        st_line.project(Point(xy))
                        for piece in pieces
                        for xy in piece.coords
                    ]
                    if distances:
                        head = min(sl_bot - z_bot - _pitch(st, rise, d) for d in distances)
                        if head + 1e-4 < MIN_STAIR_HEADROOM_M:
                            has_clash = True
                else:
                    has_clash = True
            elif (
                inter_poly is not None
                and not inter_poly.is_empty
                and inter_poly.area > MIN_SLAB_INTERSECTION_AREA_M2
            ):
                if sl_bot < z_top and sl_top > z_bot + 0.05:
                    has_clash = True

            if has_clash:
                findings.append(
                    DefectFinding(
                        defect_type=DEFECT_STAIR_THROUGH_SLAB,
                        element_ids=[st.id, sl.id, from_lvl.id, to_lvl.id],
                        description=(
                            f"Stair '{st.id}' passes through slab '{sl.id}' ({sl.kind}) "
                            f"between levels '{from_lvl.id}' and '{to_lvl.id}' without a void."
                        ),
                        suggested_op=f"void:{st.id},{sl.id}",
                    )
                )

    return findings


def scan_all_model_defects(model: HouseModel) -> list[DefectFinding]:
    """Run all defect detectors on a HouseModel."""
    return [
        *detect_windows_on_retaining_walls(model),
        *detect_overlapping_space_labels(model),
        *detect_stair_arrival_defects(model),
        *detect_door_into_wall_clash(model),
        *detect_stair_through_slab(model),
    ]
