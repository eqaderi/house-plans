"""S10-07 (ISS-29, ADR 0024): unbuildable findings keep the plan gate closed."""

from __future__ import annotations

import pytest

from house_ai.cli.main import main
from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.evaluation import EvaluationReport, Violation
from house_ai.domain.program import Strength
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.workflow import Gate
from house_ai.orchestration.plans import PlanService
from house_ai.orchestration.workflow import GateBlocked, Workflow

from .conftest import AGENT
from .test_plan_workflow import OWNER, _approve_site_and_program, _load


def _finding(code: str, message: str) -> Violation:
    return Violation(
        id=f"v-test-{code}".replace("_", "-"),
        code=code,
        strength=Strength.SOFT,
        message=message,
        subject_ids=["st-0"],
        status=ClaimStatus.MEASURED,
        evaluator="StairUsabilityEvaluator",
    )


def _with(store, ref, extra: list[Violation]) -> None:
    """Store a new version of the plan's evaluation report carrying ``extra`` findings."""
    report_ref = next(
        r
        for r in reversed(store.refs(ArtifactKind.EVALUATION_REPORT))
        if store.get(r, EvaluationReport).plan_ref == ref
    )
    report = store.get(report_ref, EvaluationReport)
    kept = [v for v in report.violations if not v.id.startswith("v-test-")]
    store.put(
        ArtifactKind.EVALUATION_REPORT,
        report.id,
        report.model_copy(update={"violations": [*kept, *extra]}),
        AGENT,
        reason="test findings",
    )


def test_soft_unbuildable_stair_finding_blocks_plan_approval(tmp_path, capsys):
    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    svc.generate(AGENT, strategies=["compact"])
    ref = store.latest(ArtifactKind.PLAN, "concept-compact")
    wf = Workflow(store)
    assert wf.gate_status(Gate.PLAN, ref).blockers == []

    _with(
        store,
        ref,
        [
            _finding("stair_low_headroom", "Pitch-line headroom 0.500 m under slab."),
            _finding("height_limit_exceeded", "Height 12.04 m exceeds envelope 10 m."),
        ],
    )
    status = wf.gate_status(Gate.PLAN, ref)
    assert [(b.kind.value, b.code) for b in status.blockers] == [
        ("unbuildable", "stair_low_headroom")
    ]
    assert "0.500 m" in status.blockers[0].message
    # Soft envelope height (not a verified fact) is shown, not blocking.
    assert status.attention == [
        "height_limit_exceeded (eval-concept-compact): Height 12.04 m exceeds envelope 10 m."
    ]
    assert main(["plan", "review", str(store.root), "concept-compact", "--actor",
                 "agent:claude-code"]) == 0  # fmt: skip
    out = capsys.readouterr().out
    assert "OPEN unbuildable stair_low_headroom" in out
    assert "ATTENTION height_limit_exceeded" in out
    with pytest.raises(GateBlocked):
        wf.approve(Gate.PLAN, ref, OWNER, "approve despite the stair")

    # Fixed (here: the finding gone), the human can approve.
    _with(store, ref, [_finding("height_limit_exceeded", "Height 12.04 m exceeds envelope 10 m.")])
    assert wf.gate_status(Gate.PLAN, ref).blockers == []
    wf.approve(Gate.PLAN, ref, OWNER, "synthetic owner approves")
    assert store.verify() == []


def test_colliding_labels_never_close_the_plan_gate(tmp_path):
    """A drawing defect is shown in the Evaluation and never blocks (ADR 0024, ADR 0033)."""
    store = _load(tmp_path)
    _approve_site_and_program(store)
    PlanService(store).generate(AGENT, strategies=["compact"])
    ref = store.latest(ArtifactKind.PLAN, "concept-compact")
    _with(store, ref, [_finding("label_collision", "The labels of a and b overlap.")])
    status = Workflow(store).gate_status(Gate.PLAN, ref)
    assert status.blockers == [] and status.attention == []
    assert status.approvable
