"""Tests for seeded visual defects and detection on synthetic fixtures (Stage S5, Task S5-07)."""

from __future__ import annotations

import pytest

from house_ai.constants.reviewer import (
    DEFECT_DOOR_EXCEEDS_WALL,
    DEFECT_MISSING_STAIR_ARRIVAL,
    DEFECT_MISSING_STAIR_LEVEL,
    DEFECT_OVERLAPPING_LABELS,
    DEFECT_STAIR_THROUGH_SLAB,
    DEFECT_WINDOW_ON_RETAINING_WALL,
)
from house_ai.domain.geometry import Polygon2D
from house_ai.domain.model import (
    HouseModel,
    Level,
    Opening,
    OpeningKind,
    Slab,
    SlabKind,
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
    detect_stair_through_slab,
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


def test_detects_stair_through_slab(clean_model):
    """Detects when a stair flight intersects a floor or roof slab without a void."""
    # Stair st-main climbs from lvl-0 (0m) to lvl-1 (3m), footprint [[0, 3], [2, 3], [2, 5], [0, 5]]
    # Add a roof slab over lvl-0 at elevation 1.5m that covers the stair flight without a void
    slab_unvoided = Slab(
        id="slab-roof-low",
        level_id="lvl-0",
        kind=SlabKind.ROOF,
        boundary=Polygon2D(outer=[[-1, 2], [3, 2], [3, 6], [-1, 6]]),
        thickness_m=0.25,
        top_offset_m=1.5,
    )
    clean_model.slabs = [slab_unvoided]

    findings = detect_stair_through_slab(clean_model)
    assert len(findings) == 1
    assert findings[0].defect_type == DEFECT_STAIR_THROUGH_SLAB
    assert "st-main" in findings[0].element_ids
    assert "slab-roof-low" in findings[0].element_ids
    assert "lvl-0" in findings[0].element_ids
    assert "lvl-1" in findings[0].element_ids

    # When a void is cut into the slab over the flight footprint, the clash is resolved
    slab_voided = Slab(
        id="slab-roof-low",
        level_id="lvl-0",
        kind=SlabKind.ROOF,
        boundary=Polygon2D(
            outer=[[-1, 2], [3, 2], [3, 6], [-1, 6]],
            holes=[[[0, 3], [2, 3], [2, 5], [0, 5]]],
        ),
        thickness_m=0.25,
        top_offset_m=1.5,
    )
    clean_model.slabs = [slab_voided]
    assert len(detect_stair_through_slab(clean_model)) == 0


def test_detects_s9_concept_two_wing_defects():
    """Detects the defects found during S9 visual review on concept-two-wing v1:

    1. Stair st-0 through slab-roof-down-450 without a void (vc-stair-through-slab).
    2. Overlapping labels on lower level tight rooms (vc-lower-labels-overlap).
    """
    # Self-contained representation of the S9 concept-two-wing v1 geometry with seeded defects
    model = HouseModel(
        id="concept-two-wing-v1",
        name="Two Wing v1",
        coordinate_system_id="local",
            levels=[
                Level(id="lv-down-450", name="Lower", elevation_m=7.13),
                Level(id="lv-entry", name="Entry", elevation_m=11.63),
            ],
            spaces=[
                Space(
                    id="sp-corridor-b1",
                    name="Corridor",
                    function="corridor",
                    level_id="lv-down-450",
                    boundary=Polygon2D(
                        outer=[
                            [2.773354, 17.253652],
                            [3.947131, 17.503147],
                            [2.512534, 24.252364],
                            [1.338757, 24.002869],
                        ]
                    ),
                ),
                Space(
                    id="sp-bed-child-1",
                    name="Child's bedroom 1",
                    function="bedroom",
                    level_id="lv-down-450",
                    boundary=Polygon2D(
                        outer=[
                            [3.385767, 20.144145],
                            [7.493986, 21.017378],
                            [6.932622, 23.658376],
                            [2.824403, 22.785143],
                        ]
                    ),
                ),
                Space(
                    id="sp-bed-child-2",
                    name="Child's bedroom 2",
                    function="bedroom",
                    level_id="lv-down-450",
                    boundary=Polygon2D(
                        outer=[
                            [3.947131, 17.503147],
                            [8.05535, 18.37638],
                            [7.493986, 21.017378],
                            [3.385767, 20.144145],
                        ]
                    ),
                ),
                Space(
                    id="sp-mechanical",
                    name="Plant / technical room",
                    function="mechanical",
                    level_id="lv-down-450",
                    boundary=Polygon2D(
                        outer=[
                            [2.824403, 22.785143],
                            [6.932622, 23.658376],
                            [6.620753, 25.125597],
                            [2.512534, 24.252364],
                        ]
                    ),
                ),
                Space(
                    id="sp-living",
                    name="Living Room",
                    function="living",
                    level_id="lv-entry",
                    boundary=Polygon2D(outer=[[10, 10], [16, 10], [16, 15], [10, 15]]),
                ),
            ],
            walls=[],
            openings=[],
            stairs=[
                Stair(
                    id="st-0",
                    from_level_id="lv-down-450",
                    to_level_id="lv-entry",
                    bottom_space_id="sp-corridor-b1",
                    top_space_id="sp-living",
                    width_m=1.0,
                    kind=StairKind.STRAIGHT,
                    footprint=Polygon2D(
                        outer=[
                            [3.578071, 13.948742],
                            [4.556219, 14.156655],
                            [3.121622, 20.905872],
                            [2.143474, 20.697959],
                        ]
                    ),
                    walking_line=[[2.653339, 20.704101], [4.067145, 14.052698]],
                )
            ],
            slabs=[
                Slab(
                    id="slab-floor-down-450",
                    level_id="lv-down-450",
                    kind=SlabKind.FLOOR,
                    boundary=Polygon2D(outer=[[0, 15], [10, 15], [10, 26], [0, 26]]),
                    thickness_m=0.25,
                    top_offset_m=0.0,
                ),
                Slab(
                    id="slab-roof-down-450",
                    level_id="lv-down-450",
                    kind=SlabKind.ROOF,
                    boundary=Polygon2D(outer=[[0, 15], [10, 15], [10, 26], [0, 26]]),
                    thickness_m=0.25,
                    top_offset_m=3.0,
                ),
            ],
        )

    # 1. Stair through slab defect detector flags st-0 penetrating slab-roof-down-450
    stair_findings = detect_stair_through_slab(model)
    assert len(stair_findings) >= 1
    stair_defect = next(f for f in stair_findings if f.defect_type == DEFECT_STAIR_THROUGH_SLAB)
    assert "st-0" in stair_defect.element_ids
    assert "slab-roof-down-450" in stair_defect.element_ids

    # 2. Overlapping label detector flags collisions between tight rooms on lv-down-450
    label_findings = detect_overlapping_space_labels(model)
    assert len(label_findings) >= 1
    implicated = {eid for f in label_findings for eid in f.element_ids}
    # At least two of the lower rooms whose labels collide are flagged
    lower_rooms = {"sp-bed-child-1", "sp-bed-child-2", "sp-corridor-b1", "sp-mechanical"}
    assert len(implicated & lower_rooms) >= 2

    # 3. scan_all_model_defects contains both defect types
    all_defects = scan_all_model_defects(model)
    types = {f.defect_type for f in all_defects}
    assert DEFECT_STAIR_THROUGH_SLAB in types
    assert DEFECT_OVERLAPPING_LABELS in types
