"""One answer to "which slots are needed, and which of those block the program gate".

The program build, the program checks and the interview checklist read one table, so
they cannot disagree. "Sloped" and "steep" are defined once, on the site summary.
All data is synthetic.
"""

from __future__ import annotations

import pytest

from house_ai.cad.layers import load_layer_mapping
from house_ai.domain.brief import BriefFact, BriefTopic, FactSource, FactSourceKind
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.interview import SiteContext
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.provenance import DataClassification
from house_ai.orchestration.interview import InterviewService
from house_ai.orchestration.site import SiteService
from house_ai.program.builder import build_program
from house_ai.program.validation import blocking, validate_program

from .conftest import AGENT, HUMAN, SURVEY_DXF, SURVEY_LAYERS

#: Today's answers (spec #9, part 9): slot -> whether it blocks the program gate.
#: ``slope_strategy`` is needed only on a sloped Site.
TODAY = {
    "adults": True,
    "bedrooms": True,
    "bathrooms": True,
    "storeys": False,
    "budget": False,
    "target_area": False,
    "slope_strategy": False,
}
#: Relief of exactly 2 m is sloped; just under it is not.
SLOPED = SiteContext(relief_m=2.0, mean_slope_pct=4.0)
FLAT = SiteContext(relief_m=1.99, mean_slope_pct=4.0)


@pytest.fixture
def interview(new_store):
    """The synthetic survey (5.0 m relief, 11.18 % mean slope) and a started interview."""
    store = new_store("family")
    doc = store.add_source(SURVEY_DXF, HUMAN, classification=DataClassification.SYNTHETIC)
    SiteService(store).ingest(doc.id, load_layer_mapping(SURVEY_LAYERS), AGENT)
    svc = InterviewService(store)
    svc.start(AGENT)
    return svc


def _build(svc: InterviewService, site: SiteContext | None, brief=None):
    brief = brief or svc.brief()
    return build_program(
        brief, site=site, brief_ref=svc.store.latest(K.DESIGN_BRIEF, "brief"),
        created_at=svc.store.clock(),
    )  # fmt: skip


def _needed(result) -> dict[str, bool]:
    return {q.topic: q.blocking for q in result.open_questions.questions if q.topic in TODAY}


def test_program_build_and_checks_give_todays_seven_answers(interview):
    sloped = _build(interview, SLOPED)
    assert _needed(sloped) == TODAY
    assert [q.id for q in sloped.open_questions.questions if q.topic in TODAY] == [
        "oq-adults", "oq-bedrooms", "oq-bathrooms", "oq-storeys", "oq-budget",
        "oq-target-area", "oq-slope-strategy",
    ]  # fmt: skip
    assert _needed(_build(interview, FLAT)) == {k: v for k, v in TODAY.items()
                                                 if k != "slope_strategy"}  # fmt: skip

    findings = validate_program(sloped.program, interview.brief(), SLOPED)
    missing = [f for f in blocking(findings) if f.code == "missing_information"]
    assert [f.subject_ids for f in missing] == [["f-adults"], ["f-bedrooms"], ["f-bathrooms"]]
    assert missing[0].message == "We do not know yet how many adults live in the house."


def test_the_checklist_lists_the_needed_slots_the_program_build_asks_for(interview):
    checklist = interview.checklist()
    assert checklist.missing_required_slots == list(TODAY)
    asked = _needed(_build(interview, interview.site()))
    assert checklist.missing_required_slots == list(asked)

    interview.answer("Two adults and one child.", HUMAN)
    assert interview.checklist().missing_required_slots == [s for s in TODAY if s != "adults"]


def test_a_slot_saved_under_its_old_name_is_read_by_its_current_name(interview):
    brief = interview.brief()
    old = BriefFact(
        id="f-floors", topic=BriefTopic.LEVELS, key="floors", statement="Two storeys.",
        value=2, status=Epistemic.PREFERENCE, source=FactSource(kind=FactSourceKind.OWNER_ANSWER),
    )  # fmt: skip
    brief = brief.model_copy(update={"facts": [*brief.facts, old]})
    result = _build(interview, SLOPED, brief)
    assert "storeys" not in _needed(result)
    assert result.program.storeys == 2


def test_the_site_summary_answers_sloped_and_steep(interview):
    summary = interview.site_summary()
    assert (summary.context.relief_m, summary.context.mean_slope_pct) == (5.0, 11.18)
    assert (summary.sloped, summary.steep) == (True, False)

    def answers(relief_m, mean_slope_pct):
        site = SiteContext(relief_m=relief_m, mean_slope_pct=mean_slope_pct)
        return site.sloped, site.steep

    assert answers(1.99, 19.99) == (False, False)
    assert answers(2.0, 0.0) == (True, False)
    assert answers(7.99, 19.99) == (True, False)
    assert answers(8.0, 0.0) == (True, True)
    assert answers(1.0, 20.0) == (False, True)
    assert answers(None, None) == (False, False)
