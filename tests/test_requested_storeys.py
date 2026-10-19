"""S10-12: report departures from the program's requested storeys."""

import pytest

from house_ai.evaluation.explain import comparison_markdown, explanation_markdown
from house_ai.orchestration.plans import PlanService

from .conftest import AGENT
from .test_plan_workflow import _approve_site_and_program, _load


@pytest.mark.parametrize("strategy, actual", [("linear", 1), ("compact", 2)])
def test_requested_storeys_explained_in_both_exports(tmp_path, strategy, actual):
    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    outcome = svc.generate(AGENT, strategies=[strategy], exploratory=True)
    (generated,) = outcome.generated
    plan, report = generated.candidate.plan, generated.report
    program = svc.inputs(exploratory=True).program
    assert program.levels == 2
    assert len(plan.model.levels) == actual
    notes = [a for a in plan.model.assumptions if a.id == "asm-gen-requested-levels"]
    explanation = explanation_markdown(plan, None, report, program)
    comparison = comparison_markdown([(plan, None, report)], [])
    if actual == 1:
        (note,) = notes
        assert "Requested storeys: 2; generated floor levels: 1." in note.statement
        assert "one bar on a single level" in note.statement
        assert note.statement in explanation and note.statement in comparison
        assert note.confirm_with == "owner"
    else:
        assert not notes
        assert "Requested storeys:" not in explanation + comparison
