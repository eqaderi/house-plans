"""Every default plan option on synthetic-hillside is integrity-clean and gate-approvable.

Uses the shared exploratory plans of conftest `hillside` (seed 0, default budget), so no
strategy is solved again here when another test on this worker already asked for it.
"""

from __future__ import annotations

import pytest

from house_ai.constants.evaluations import PLAN_GATE_BLOCKING_CODES
from house_ai.constants.strategies import STRATEGY_COURTYARD, STRATEGY_ORDER
from house_ai.domain.integrity import check_model, errors
from house_ai.orchestration.plans import PlanWorkflowError

#: The default strategies that lay out a house on synthetic-hillside.
FEASIBLE = ["compact", "split_level", "linear", "two_wing", "split_walkout"]


def test_feasible_strategies_are_exactly_the_default_order_less_courtyard(hillside):
    assert [s for s in STRATEGY_ORDER if s != STRATEGY_COURTYARD] == FEASIBLE
    # The envelope has no strip deep enough for a second pavilion behind a garden court.
    with pytest.raises(PlanWorkflowError, match="courtyard: .*no room for a second pavilion"):
        hillside.option(STRATEGY_COURTYARD)


@pytest.mark.parametrize("strategy", FEASIBLE)
def test_plan_option_has_no_integrity_error_hard_violation_or_gate_blocker(hillside, strategy):
    option = hillside.option(strategy)
    plan, report = option.candidate.plan, option.report
    assert plan is not None and option.candidate.status == "generated"
    inp = hillside.inputs()
    assert [f.code for f in errors(check_model(plan.model, inp.site, inp.program))] == []
    assert [f.code for f in errors(option.candidate.findings)] == []
    assert [v.code for v in report.hard_violations] == []
    # The soft findings that still close the plan gate (ADR 0024) are absent.
    assert {v.code for v in report.violations} & PLAN_GATE_BLOCKING_CODES == set()
