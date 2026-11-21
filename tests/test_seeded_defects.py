"""Seeded defects are reported by the Evaluation or the integrity check (S5-07, ADR 0033).

Each test seeds one defect into a hand-built model and asserts on the Evaluation (the
evaluators, as `plan generate` runs them) or on ``check_model``; no solver, no store.
"""

from __future__ import annotations

import pytest

from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.evaluation import EvaluationReport, Violation
from house_ai.domain.geometry import Polygon2D
from house_ai.domain.integrity import (
    CODE_DANGLING_REFERENCE,
    CODE_OPENING_OUTSIDE_WALL,
    check_model,
    errors,
)
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
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import Strength
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, ArtifactRef, Provenance
from house_ai.domain.site import Site
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.report import evaluate_plan
from house_ai.evaluation.templates import UsabilityPolicy
from house_ai.evaluation.usability import StairUsabilityEvaluator
from house_ai.storage.hashing import load_document

from .conftest import REPO

HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"
WHEN = "2026-11-17T00:00:00Z"
#: The codes the seeded defects below are reported with.
SEEDED_CODES = {
    "window_buried",
    "label_collision",
    "stair_low_headroom",
    CODE_OPENING_OUTSIDE_WALL,
    CODE_DANGLING_REFERENCE,
}


def _evaluation(model: HouseModel, site: Site | None = None) -> EvaluationReport:
    """The Evaluation of a hand-built model, as `plan generate` would store it."""
    plan = PlanVersion(
        option_id="seeded",
        label="Seeded defects",
        provenance=Provenance(
            created_at=WHEN, created_by=Actor(kind=ActorKind.SYSTEM, id="test"), method="test"
        ),
        model=model,
    )
    ref = ArtifactRef(kind=ArtifactKind.PLAN, id="seeded", version=1, sha256="0" * 64)
    return evaluate_plan(
        plan, ref, site=site, program=None, constraints=None, codepack=None, created_at=WHEN
    )


def _findings(report: EvaluationReport, code: str) -> list[Violation]:
    return [v for v in report.violations if v.code == code]


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
                walking_line=[[1, 3], [1, 5]],
            )
        ],
    )


def _roof_over_the_flight(holes: list) -> Slab:
    return Slab(
        id="slab-roof-low",
        level_id="lvl-0",
        kind=SlabKind.ROOF,
        boundary=Polygon2D(outer=[[-1, 2], [3, 2], [3, 6], [-1, 6]], holes=holes),
        thickness_m=0.25,
        top_offset_m=1.5,
    )


def test_overlapping_space_labels_are_a_finding_of_the_evaluation(clean_model):
    """Two closets whose labels overlap on the drawing (anchors 0.5 m = 15.25 px apart at
    30.5 px/m, each "1.00 × 0.50" line about 42 px wide)."""
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

    findings = _findings(_evaluation(clean_model), "label_collision")
    assert [set(v.subject_ids) for v in findings] == [{"sp-closet-a", "sp-closet-b"}]
    assert findings[0].status is ClaimStatus.MEASURED
    assert findings[0].evaluator == "LabelCollisionEvaluator"


def test_clean_model_has_no_seeded_defect_findings(clean_model):
    """A clean model: the Evaluation reports none of the seeded defects below."""
    report = _evaluation(clean_model)
    assert {v.code for v in report.violations} & SEEDED_CODES == set()
    assert {f.code for f in check_model(clean_model)} & SEEDED_CODES == set()
    headroom = next(m for m in report.metrics if m.metric == "stair_min_headroom_m")
    assert headroom.status is ClaimStatus.NOT_CHECKED  # no slab over the flight
    # Its integrity errors are only that the hand-built rooms have no doors.
    assert {f.code for f in errors(check_model(clean_model))} == {"space_unreachable"}


def test_window_on_retaining_wall_is_a_measured_finding_even_without_terrain(clean_model):
    """The wall's own kind says the window faces earth: no Site is needed to report it."""
    clean_model.walls.append(
        Wall(
            id="w-ret-hillside",
            level_id="lvl-0",
            kind=WallKind.RETAINING,
            start=[0, 5],
            end=[6, 5],
            thickness_m=0.4,
            height_m=2.8,
        )
    )
    clean_model.openings.append(
        Opening(
            id="win-buried-1",
            host_wall_id="w-ret-hillside",
            kind=OpeningKind.WINDOW,
            offset_m=1.5,
            width_m=1.2,
            height_m=1.0,
            connects=("sp-living", "exterior"),
        )
    )
    (finding,) = _findings(_evaluation(clean_model), "window_buried")
    assert finding.subject_ids == ["win-buried-1", "w-ret-hillside", "sp-living"]
    assert finding.status is ClaimStatus.MEASURED
    assert finding.method == "host_wall_is_retaining"


def test_window_on_a_retaining_wall_of_a_room_that_is_not_habitable_is_reported(clean_model):
    clean_model.spaces[0].function = "storage"
    clean_model.walls.append(
        Wall(
            id="w-ret-store",
            level_id="lvl-0",
            kind=WallKind.RETAINING,
            start=[6, 0],
            end=[6, 5],
            thickness_m=0.4,
            height_m=2.8,
        )
    )
    clean_model.openings.append(
        Opening(
            id="win-store",
            host_wall_id="w-ret-store",
            kind=OpeningKind.WINDOW,
            offset_m=1.0,
            width_m=1.0,
            height_m=1.0,
            connects=("sp-living", "exterior"),
        )
    )
    (finding,) = _findings(_evaluation(clean_model), "window_buried")
    assert finding.subject_ids == ["win-store", "w-ret-store", "sp-living"]
    assert (finding.status, finding.method) == (ClaimStatus.MEASURED, "host_wall_is_retaining")


def test_missing_stair_level_and_arrival_space_are_dangling_references(clean_model):
    clean_model.stairs.append(
        Stair(
            id="st-dead-end",
            from_level_id="lvl-0",
            to_level_id="lvl-nonexistent",
            bottom_space_id="sp-living",
            top_space_id="sp-phantom-attic",
            width_m=1.0,
            kind=StairKind.STRAIGHT,
            footprint=Polygon2D(outer=[[4, 0], [5, 0], [5, 3], [4, 3]]),
        )
    )
    found = [(f.code, f.message) for f in check_model(clean_model)]
    assert found == [
        (CODE_DANGLING_REFERENCE, "st-dead-end.to_level_id -> unknown 'lvl-nonexistent'"),
        (CODE_DANGLING_REFERENCE, "st-dead-end.top_space_id -> unknown 'sp-phantom-attic'"),
    ]


def test_door_with_a_missing_host_wall_is_a_dangling_reference(clean_model):
    clean_model.openings.append(
        Opening(
            id="d-floating",
            host_wall_id="w-gone",
            kind=OpeningKind.DOOR,
            offset_m=0.5,
            width_m=0.9,
            height_m=2.1,
            connects=("sp-living", "exterior"),
        )
    )
    (finding,) = check_model(clean_model)
    assert (finding.code, finding.subject_ids) == (CODE_DANGLING_REFERENCE, ["d-floating"])
    assert finding.message == "d-floating.host_wall_id -> unknown 'w-gone'"


def test_door_wider_than_what_is_left_of_its_wall_is_a_hard_finding(clean_model):
    clean_model.openings.append(
        Opening(
            id="d-overshoot",
            host_wall_id="w-ext-1",  # 6.0 m long
            kind=OpeningKind.DOOR,
            offset_m=5.5,  # 5.5 + 1.0 = 6.5 m > 6.0 m
            width_m=1.0,
            height_m=2.1,
            connects=("sp-living", "exterior"),
        )
    )
    (finding,) = _findings(_evaluation(clean_model), CODE_OPENING_OUTSIDE_WALL)
    assert finding.subject_ids == ["d-overshoot", "w-ext-1"]
    assert finding.strength is Strength.HARD
    assert finding.message == "d-overshoot runs to 6.500 m along w-ext-1, which is 6.000 m long"


def test_stair_through_a_slab_without_a_void_is_low_headroom_in_the_evaluation(clean_model):
    # The flight rises 3 m over its 2 m walking line (x = 1, y 3 -> 5); the roof slab's
    # underside is at 1.5 - 0.25 = 1.25 m over the whole flight: 1.25 - 3.0 = -1.75 m.
    clean_model.slabs = [_roof_over_the_flight(holes=[])]
    report = _evaluation(clean_model)
    (finding,) = _findings(report, "stair_low_headroom")
    assert finding.subject_ids == ["st-main", "slab-roof-low"]
    headroom = next(m for m in report.metrics if m.metric == "stair_min_headroom_m")
    assert headroom.value == pytest.approx(-1.75)

    # A void over the flight's footprint clears it.
    clean_model.slabs = [_roof_over_the_flight(holes=[[[0, 3], [2, 3], [2, 5], [0, 5]]])]
    assert _findings(_evaluation(clean_model), "stair_low_headroom") == []


def test_stair_headroom_honours_the_usability_policy(clean_model):
    # A slab over the first 0.1 m of the flight, underside 2.15 - 0.25 = 1.90 m; the pitch
    # line there is 0.1 / 2 * 3 = 0.15 m up: 1.75 m of headroom.
    clean_model.slabs = [
        Slab(
            id="slab-low-beam",
            level_id="lvl-0",
            kind=SlabKind.ROOF,
            boundary=Polygon2D(outer=[[-1, 2], [3, 2], [3, 3.1], [-1, 3.1]]),
            thickness_m=0.25,
            top_offset_m=2.15,
        )
    ]
    ctx = EvaluationContext(clean_model, None, None, None)

    def low(policy: UsabilityPolicy) -> list[list[str]]:
        result = StairUsabilityEvaluator(policy).evaluate(ctx)
        metric = next(m for m in result.metrics if m.metric == "stair_min_headroom_m")
        assert metric.value == pytest.approx(1.75)
        return [v.subject_ids for v in result.violations if v.code == "stair_low_headroom"]

    assert low(UsabilityPolicy()) == [["st-main", "slab-low-beam"]]  # 2.0 m assumption
    assert low(UsabilityPolicy(min_headroom_m=1.7)) == []


def _two_wing_v1() -> HouseModel:
    """Self-contained copy of the S9 concept-two-wing v1 geometry with its two defects:
    stair st-0 through slab-roof-down-450 without a void (vc-stair-through-slab), and
    overlapping labels on the tight lower rooms (vc-lower-labels-overlap)."""
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
    return model


def test_s9_concept_two_wing_stair_through_slab_is_low_headroom_in_the_evaluation():
    report = _evaluation(_two_wing_v1())
    assert [v.subject_ids for v in _findings(report, "stair_low_headroom")] == [
        ["st-0", "slab-roof-down-450"]
    ]


def test_s9_concept_two_wing_lower_labels_overlap_on_the_drawing_with_the_site():
    """The S9 drawing showed the synthetic-hillside parcel: at its scale (12.34 px/m) the
    corridor and the child's bedroom 1, and that bedroom and the plant room, collide. Without
    the parcel the same rooms are drawn at 24.25 px/m and no labels collide."""
    model = _two_wing_v1()
    site = Site.model_validate(load_document(HILLSIDE / "site.yaml"))
    pairs = [set(v.subject_ids) for v in _findings(_evaluation(model, site), "label_collision")]
    assert pairs == [
        {"sp-corridor-b1", "sp-bed-child-1"},
        {"sp-bed-child-1", "sp-mechanical"},
    ]
    assert _findings(_evaluation(model), "label_collision") == []
