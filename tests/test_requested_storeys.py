"""S10-12: report departures from the program's requested storeys."""

import pytest

from house_ai.evaluation.explain import comparison_markdown, explanation_markdown


@pytest.mark.parametrize("strategy, actual", [("linear", 1), ("compact", 2)])
def test_requested_storeys_explained_in_both_exports(hillside, strategy, actual):
    generated = hillside.option(strategy)
    plan, report = generated.candidate.plan, generated.report
    program = hillside.inputs().program
    assert program.storeys == 2
    assert len(plan.model.levels) == actual
    notes = [a for a in plan.model.assumptions if a.id == "asm-gen-requested-storeys"]
    explanation = explanation_markdown(plan, None, report, program)
    comparison = comparison_markdown([(plan, None, report)], [])
    if actual == 1:
        (note,) = notes
        statement = "Requested storeys: 2; this plan option has 1 storey(s) on 1 level(s)."
        assert statement in note.statement
        assert "one bar on a single level" in note.statement
        assert note.statement in explanation and note.statement in comparison
        assert note.confirm_with == "owner"
    else:
        assert not notes
        assert "Requested storeys:" not in explanation + comparison
