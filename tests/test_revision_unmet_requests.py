"""Unmet requests are checked with the shared definitions (ADR 0020, ADR 0030).

Hand-built house models and the synthetic Space program; no store and no solver.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from house_ai.constants.evaluations import REGRESSION_VIOLATION_PREFIX, REQUEST_NOT_MET_PREFIX
from house_ai.domain.model import HouseModel
from house_ai.domain.program import SpaceProgram, level_preference_met
from house_ai.domain.revision_ops import RevisionOp
from house_ai.generation.revision import request_unmet, unmet_requests
from house_ai.storage.hashing import load_document

PROGRAM = SpaceProgram.model_validate(
    load_document(
        Path(__file__).resolve().parents[1]
        / "examples/projects/synthetic-hillside/space_program.yaml"
    )
)


def _rect(x0: float, y0: float, x1: float, y1: float) -> dict:
    return {"outer": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


def _model(*, bed_x: float = 6.0, door: bool = False, study: str = "lv-upper") -> HouseModel:
    """Living 5 x 4 m and a 4 x 4 m kitchen on the entry Level, main bedroom beside living.

    ``bed_x`` 5.0 makes the bedroom share a 4 m wall with living; 6.0 keeps them 1 m apart.
    The study is 3 x 3 m on ``study``.
    """
    spaces = [
        {"id": "sp-living", "name": "Living", "function": "living", "level_id": "lv-entry",
         "boundary": _rect(0, 0, 5, 4)},
        {"id": "sp-bed-main", "name": "Main bedroom", "function": "bedroom",
         "level_id": "lv-entry", "boundary": _rect(bed_x, 0, bed_x + 4, 4)},
        {"id": "sp-kitchen", "name": "Kitchen", "function": "kitchen", "level_id": "lv-entry",
         "boundary": _rect(20, 0, 24, 4)},
        {"id": "sp-study-1", "name": "Study", "function": "study", "level_id": study,
         "boundary": _rect(0, 10, 3, 13)},
    ]
    walls = [
        {"id": "w-living-bed", "level_id": "lv-entry", "start": [5, 0], "end": [5, 4],
         "thickness_m": 0.15, "height_m": 2.8, "kind": "interior"},
    ]
    openings = (
        [{"id": "d-living-bed", "host_wall_id": "w-living-bed", "kind": "door",
          "offset_m": 1.0, "width_m": 0.9, "height_m": 2.1,
          "connects": ["sp-living", "sp-bed-main"]}]
        if door
        else []
    )
    return HouseModel.model_validate(
        {
            "id": "hand-built",
            "name": "Hand-built revision check",
            "coordinate_system_id": "local",
            "levels": [
                {"id": "lv-lower", "name": "Lower", "elevation_m": -3.0},
                {"id": "lv-entry", "name": "Entry", "elevation_m": 0.0},
                {"id": "lv-upper", "name": "Upper", "elevation_m": 3.0},
            ],
            "spaces": spaces,
            "walls": walls,
            "openings": openings,
        }
    )


def _unmet(text: str, model: HouseModel) -> str | None:
    return request_unmet(RevisionOp.parse(text), model, PROGRAM)


def test_separate_with_a_shared_wall_is_unmet() -> None:
    detail = _unmet("separate:pi-living,pi-bed-main", _model(bed_x=5.0))
    assert detail == "sp-living and sp-bed-main share a 4.00 m wall"


def test_separate_with_a_door_is_unmet() -> None:
    detail = _unmet("separate:pi-living,pi-bed-main", _model(bed_x=5.0, door=True))
    assert detail == "door d-living-bed connects sp-living and sp-bed-main"


def test_separate_apart_is_met() -> None:
    assert _unmet("separate:pi-living,pi-bed-main", _model(bed_x=6.0)) is None


@pytest.mark.parametrize(
    ("study", "word", "met"),
    [
        ("lv-entry", "not_entry", False),
        ("lv-upper", "not_entry", True),
        ("lv-lower", "not_entry", True),
        ("lv-upper", "ground", False),
        ("lv-entry", "ground", True),
        ("lv-entry", "entry", True),
        ("lv-lower", "entry", False),
        ("lv-upper", "upper", True),
        ("lv-entry", "upper", False),
        ("lv-lower", "lower", True),
        ("lv-upper", "lower", False),
        ("lv-lower", "any", True),
    ],
)
def test_one_level_check_covers_every_level_word(study: str, word: str, met: bool) -> None:
    detail = _unmet(f"level:pi-study-1={word}", _model(study=study))
    if met:
        assert detail is None
    else:
        assert detail == f"sp-study-1 is on {study}; the request is level={word}"


def test_level_words_match_the_program_evaluator_definition() -> None:
    # Off the entry Level is trivially met in a one-level house; unknown words are not checked.
    assert level_preference_met("not_entry", 0.0, 0.0, 1) is True
    assert level_preference_met("not_entry", 0.0, 0.0, 2) is False
    assert level_preference_met("lv-1", 3.0, 0.0, 2) is None
    assert level_preference_met("upper", 3.0, None, 2) is None


def test_area_check_keeps_the_two_square_metre_tolerance() -> None:
    model = _model()
    assert _unmet("area:pi-kitchen=18", model) is None
    assert _unmet("area:pi-kitchen=19", model) == "sp-kitchen area 16.0 m² < requested 19 m²"


def test_unmet_requests_tell_a_lost_request_from_one_never_met() -> None:
    op = RevisionOp.parse("separate:pi-living,pi-bed-main")
    apart, touching = _model(bed_x=6.0), _model(bed_x=5.0)
    assert unmet_requests([op], apart, PROGRAM, parent_ops=[op], parent_model=apart) == []
    (lost,) = unmet_requests([op], touching, PROGRAM, parent_ops=[op], parent_model=apart)
    assert lost == (
        f"{REGRESSION_VIOLATION_PREFIX}'separate:pi-living,pi-bed-main' is no longer satisfied "
        "(sp-living and sp-bed-main share a 4.00 m wall)"
    )
    (never,) = unmet_requests([op], touching, PROGRAM, parent_ops=[op], parent_model=touching)
    assert never == (
        f"{REQUEST_NOT_MET_PREFIX}'separate:pi-living,pi-bed-main' "
        "(sp-living and sp-bed-main share a 4.00 m wall)"
    )
    (new,) = unmet_requests([op], touching, PROGRAM, parent_ops=[], parent_model=apart)
    assert new.startswith(REQUEST_NOT_MET_PREFIX)


def test_requests_this_check_does_not_cover_are_silent() -> None:
    model = _model()
    for text in ("rethink:all", "strategy:compact", "stair:rear", "near:pi-living,pi-kitchen"):
        assert _unmet(text, model) is None
