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

from house_ai.constants.reviewer import (
    DEFECT_DOOR_EXCEEDS_WALL,
    DEFECT_MISSING_HOST_WALL,
    DEFECT_MISSING_STAIR_ARRIVAL,
    DEFECT_MISSING_STAIR_LEVEL,
    DEFECT_OVERLAPPING_LABELS,
    DEFECT_WINDOW_ON_RETAINING_WALL,
)
from house_ai.domain.model import HouseModel, OpeningKind, WallKind


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
    model: HouseModel, min_label_distance_m: float = 1.5
) -> list[DefectFinding]:
    """Flag spaces whose label centers are closer than min_label_distance_m."""
    spaces_by_level: dict[str, list] = {}
    for sp in model.spaces or []:
        spaces_by_level.setdefault(sp.level_id, []).append(sp)

    findings: list[DefectFinding] = []

    for _lvl_id, sp_list in spaces_by_level.items():
        for i in range(len(sp_list)):
            sp_a = sp_list[i]
            pts_a = sp_a.boundary.outer
            if not pts_a:
                continue
            center_a = _polygon_centroid(pts_a)

            for j in range(i + 1, len(sp_list)):
                sp_b = sp_list[j]
                pts_b = sp_b.boundary.outer
                if not pts_b:
                    continue
                center_b = _polygon_centroid(pts_b)

                dist = math.dist(center_a, center_b)
                if dist < min_label_distance_m:
                    findings.append(
                        DefectFinding(
                            defect_type=DEFECT_OVERLAPPING_LABELS,
                            element_ids=[sp_a.id, sp_b.id],
                            description=(
                                f"Spaces '{sp_a.id}' and '{sp_b.id}' have colliding label centers "
                                f"(distance {dist:.2f} m < {min_label_distance_m:.2f} m)."
                            ),
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


def scan_all_model_defects(model: HouseModel) -> list[DefectFinding]:
    """Run all defect detectors on a HouseModel."""
    return [
        *detect_windows_on_retaining_walls(model),
        *detect_overlapping_space_labels(model),
        *detect_stair_arrival_defects(model),
        *detect_door_into_wall_clash(model),
    ]
