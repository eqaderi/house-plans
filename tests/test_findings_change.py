"""Which Findings about the targeted ids disappeared, remain or are new (#35, ADR 0033).

The comparison reads two Evaluations (here the evaluators run on hand-built models, as
``evaluate_plan`` would); the `plan revise` report is tested through ``PlanService.revise``.
"""

from __future__ import annotations

import copy

from examples.usability.scenarios import flat_site, model
from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.evaluation import Violation
from house_ai.domain.model import HouseModel
from house_ai.domain.program import Strength
from house_ai.evaluation.findings import compare_findings
from house_ai.evaluation.report import model_findings

WINDOW = dict(
    id="win",
    kind="window",
    host_wall_id="south",
    offset_m=1,
    width_m=2,
    height_m=1.5,
    sill_m=0.9,
    connects=("room", "exterior"),
    operation="casement",
)


def _living_room(window_wall: str, *, south_retaining: bool) -> HouseModel:
    """A 4 x 4 m living room on flat ground with one window."""
    doc = model(4, 4, "living")
    doc["openings"] = [{**WINDOW, "host_wall_id": window_wall}]
    if south_retaining:
        doc["walls"][0]["kind"] = "retaining"
    return HouseModel.model_validate(doc)


def _codes(findings) -> list[str]:
    return sorted(v.code for v in findings)


def test_a_fix_that_moves_the_window_off_the_retaining_wall_makes_its_findings_disappear():
    site = flat_site()
    before = _living_room("south", south_retaining=True)
    after = _living_room("north", south_retaining=True)
    change = compare_findings(
        model_findings(before, site),
        model_findings(after, site),
        targets={"room"},
        before_model=before,
        after_model=after,
    )
    # On the retaining wall the 2 x 1.5 m window has no glazing above ground, so the room's
    # glazing ratio is 0 (< 0.1). On the north wall it is 3 m² / 3.85² m² = 0.20.
    assert [(v.code, v.subject_ids) for v in change.disappeared] == [
        ("window_buried", ["win", "south", "room"]),
        ("low_daylight_opportunity", ["room"]),
    ]
    # The retained south face is still there; the hand-built room has no door and no site
    # envelope around it.
    assert _codes(change.remaining) == [
        "buried_habitable_face",
        "needs_professional_waterproofing",
        "outside_envelope",
        "space_unreachable",
    ]
    assert change.new == ()


def test_findings_about_untargeted_ids_are_left_out():
    site = flat_site()
    before = _living_room("south", south_retaining=True)
    after = _living_room("north", south_retaining=True)
    change = compare_findings(
        model_findings(before, site),
        model_findings(after, site),
        targets={"sp-nowhere"},
        before_model=before,
        after_model=after,
    )
    assert change.disappeared == change.remaining == change.new == ()


def test_a_finding_on_an_unchanged_model_remains_and_a_new_one_is_new():
    site = flat_site()
    before = _living_room("south", south_retaining=True)
    after = _living_room("south", south_retaining=True)
    findings = model_findings(before, site)
    change = compare_findings(
        findings,
        model_findings(after, site),
        targets={"win"},
        before_model=before,
        after_model=after,
    )
    assert _codes(change.remaining) == ["window_buried"]
    assert change.disappeared == () and change.new == ()

    # Moving the window onto the room's west wall, also retaining, leaves it buried there:
    # a new Finding (another wall), and the one on the south wall disappeared.
    west = copy.deepcopy(before.model_dump(mode="json"))
    west["walls"][3]["kind"] = "retaining"
    west["openings"][0]["host_wall_id"] = "west"
    moved = HouseModel.model_validate(west)
    change = compare_findings(
        findings,
        model_findings(moved, site),
        targets={"win"},
        before_model=before,
        after_model=moved,
    )
    assert [v.subject_ids for v in change.disappeared] == [["win", "south", "room"]]
    assert [v.subject_ids for v in change.new] == [["win", "west", "room"]]


def test_a_finding_whose_cited_geometry_did_not_change_is_never_reported_as_a_fix():
    """The parent's stored Evaluation may come from an earlier evaluator: a Finding it holds
    that the new Evaluation lacks, about elements that did not change, is not a fix."""
    site = flat_site()
    before = _living_room("north", south_retaining=False)
    after = copy.deepcopy(before)
    stale = Violation(
        id="v-001-stale",
        code="window_too_small",
        strength=Strength.SOFT,
        message="Reported by an earlier evaluator.",
        subject_ids=["win", "room"],
        status=ClaimStatus.INFERRED,
        evaluator="EarlierEvaluator",
    )
    change = compare_findings(
        [*model_findings(before, site), stale],
        model_findings(after, site),
        targets={"win"},
        before_model=before,
        after_model=after,
    )
    assert change.disappeared == ()
    assert [v.code for v in change.remaining] == ["window_too_small"]
