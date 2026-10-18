"""Tests for seeded visual defects and detection on synthetic fixtures (Stage S5, Task S5-07)."""

from __future__ import annotations

import pytest

from house_ai.constants.reviewer import (
    DEFECT_DOOR_EXCEEDS_WALL,
    DEFECT_MISSING_STAIR_ARRIVAL,
    DEFECT_MISSING_STAIR_LEVEL,
    DEFECT_OVERLAPPING_LABELS,
    DEFECT_WINDOW_ON_RETAINING_WALL,
)
from house_ai.domain.geometry import Polygon2D
from house_ai.domain.model import (
    HouseModel,
    Level,
    Opening,
    OpeningKind,
    Space,
    Stair,
    StairKind,
    Wall,
    WallKind,
)
from house_ai.validation.defect_detectors import (
    detect_door_into_wall_clash,
    detect_overlapping_space_labels,
    detect_stair_arrival_defects,
    detect_windows_on_retaining_walls,
    scan_all_model_defects,
)


@pytest.fixture
def clean_model() -> HouseModel:
    return HouseModel(
        id="model-clean",
        name="Clean Model",
        coordinate_system_id="local",
        levels=[
            Level(id="lvl-0", name="Ground", elevation_m=0.0),
            Level(id="lvl-1", name="Upper", elevation_m=3.0),
        ],
        spaces=[
            Space(
                id="sp-living",
                name="Living Room",
                function="living",
                level_id="lvl-0",
                boundary=Polygon2D(outer=[[0, 0], [6, 0], [6, 5], [0, 5]]),
            ),
            Space(
                id="sp-bed-1",
                name="Bedroom 1",
                function="bedroom",
                level_id="lvl-1",
                boundary=Polygon2D(outer=[[0, 0], [5, 0], [5, 4], [0, 4]]),
            ),
        ],
        walls=[
            Wall(
                id="w-ext-1",
                level_id="lvl-0",
                kind=WallKind.EXTERIOR,
                start=[0, 0],
                end=[6, 0],
                thickness_m=0.3,
                height_m=2.8,
            )
        ],
        openings=[
            Opening(
                id="win-clean",
                host_wall_id="w-ext-1",
                kind=OpeningKind.WINDOW,
                offset_m=2.0,
                width_m=1.5,
                height_m=1.2,
                connects=("sp-living", "exterior"),
            )
        ],
        stairs=[
            Stair(
                id="st-main",
                from_level_id="lvl-0",
                to_level_id="lvl-1",
                bottom_space_id="sp-living",
                top_space_id="sp-bed-1",
                width_m=1.0,
                kind=StairKind.STRAIGHT,
                footprint=Polygon2D(outer=[[0, 3], [2, 3], [2, 5], [0, 5]]),
            )
        ],
    )


def test_clean_model_has_no_defects(clean_model):
    """A clean plan model produces zero defect findings."""
    defects = scan_all_model_defects(clean_model)
    assert len(defects) == 0


def test_detects_window_on_retaining_wall(clean_model):
    """Detects when a window is hosted on a retaining wall buried in earth."""
    # Add a retaining wall with a window
    ret_wall = Wall(
        id="w-ret-hillside",
        level_id="lvl-0",
        kind=WallKind.RETAINING,
        start=[0, 5],
        end=[6, 5],
        thickness_m=0.4,
        height_m=2.8,
    )
    buried_window = Opening(
        id="win-buried-1",
        host_wall_id="w-ret-hillside",
        kind=OpeningKind.WINDOW,
        offset_m=1.5,
        width_m=1.2,
        height_m=1.0,
        connects=("sp-living", "exterior"),
    )
    clean_model.walls.append(ret_wall)
    clean_model.openings.append(buried_window)

    findings = detect_windows_on_retaining_walls(clean_model)
    assert len(findings) == 1
    assert findings[0].defect_type == DEFECT_WINDOW_ON_RETAINING_WALL
    assert "win-buried-1" in findings[0].element_ids
    assert "w-ret-hillside" in findings[0].element_ids


def test_detects_overlapping_space_labels(clean_model):
    """Detects when two room label centers collide / overlap."""
    # Add two tiny adjacent spaces whose centers are 0.5m apart (< 1.5m)
    clean_model.spaces.append(
        Space(
            id="sp-closet-a",
            name="Closet A",
            function="storage",
            level_id="lvl-0",
            boundary=Polygon2D(outer=[[10, 0], [10.5, 0], [10.5, 1], [10, 1]]),
        )
    )
    clean_model.spaces.append(
        Space(
            id="sp-closet-b",
            name="Closet B",
            function="storage",
            level_id="lvl-0",
            boundary=Polygon2D(outer=[[10.5, 0], [11, 0], [11, 1], [10.5, 1]]),
        )
    )

    findings = detect_overlapping_space_labels(clean_model, min_label_distance_m=1.0)
    assert len(findings) == 1
    assert findings[0].defect_type == DEFECT_OVERLAPPING_LABELS
    assert set(findings[0].element_ids) == {"sp-closet-a", "sp-closet-b"}


def test_detects_missing_stair_arrival(clean_model):
    """Detects stairs whose top space or destination level does not exist."""
    ghost_stair = Stair(
        id="st-dead-end",
        from_level_id="lvl-0",
        to_level_id="lvl-nonexistent",
        bottom_space_id="sp-living",
        top_space_id="sp-phantom-attic",
        width_m=1.0,
        kind=StairKind.STRAIGHT,
        footprint=Polygon2D(outer=[[4, 0], [5, 0], [5, 3], [4, 3]]),
    )
    clean_model.stairs.append(ghost_stair)

    findings = detect_stair_arrival_defects(clean_model)
    assert len(findings) >= 2
    types = [f.defect_type for f in findings]
    assert DEFECT_MISSING_STAIR_LEVEL in types
    assert DEFECT_MISSING_STAIR_ARRIVAL in types
    arrival_finding = next(f for f in findings if f.defect_type == DEFECT_MISSING_STAIR_ARRIVAL)
    assert "sp-phantom-attic" in arrival_finding.element_ids


def test_detects_door_clash(clean_model):
    """Detects doors that extend beyond host wall length into corners/intersections."""
    bad_door = Opening(
        id="d-overshoot",
        host_wall_id="w-ext-1",  # length is 6.0m
        kind=OpeningKind.DOOR,
        offset_m=5.5,  # 5.5 + 1.0 = 6.5m > 6.0m
        width_m=1.0,
        height_m=2.1,
        connects=("sp-living", "exterior"),
    )
    clean_model.openings.append(bad_door)

    findings = detect_door_into_wall_clash(clean_model)
    assert len(findings) == 1
    assert findings[0].defect_type == DEFECT_DOOR_EXCEEDS_WALL
    assert "d-overshoot" in findings[0].element_ids
    assert "w-ext-1" in findings[0].element_ids
