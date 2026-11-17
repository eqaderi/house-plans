"""Run the evaluators on one plan version and assemble an :class:`EvaluationReport`."""

from __future__ import annotations

from datetime import datetime

from house_ai.domain.codepack import CodePack, compliance_statement
from house_ai.domain.constraints import ConstraintSet
from house_ai.domain.evaluation import EvaluationReport, EvaluatorRun, EvaluatorRunStatus
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import Actor, ActorKind, ArtifactRef, Provenance
from house_ai.domain.site import Site

from .base import FUTURE_EVALUATORS, EvaluationContext
from .evaluators import REQUIRED, VERSION, codepack_rules_checked
from .usability import USABILITY_EVALUATORS

EVALUATION_ACTOR = Actor(kind=ActorKind.SYSTEM, id="house-ai-evaluation")


def report_id(option_id: str) -> str:
    return f"eval-{option_id}"[:64]


def evaluate_plan(
    plan: PlanVersion,
    plan_ref: ArtifactRef,
    *,
    site: Site | None,
    program: SpaceProgram | None,
    constraints: ConstraintSet | None,
    codepack: CodePack | None,
    created_at: datetime,
    site_approved: bool | None = None,
    inputs: list[ArtifactRef] | None = None,
) -> EvaluationReport:
    ctx = EvaluationContext(plan.model, site, program, constraints, site_approved)
    runs, metrics, violations = [], [], []
    for ev in [*REQUIRED, *USABILITY_EVALUATORS]:
        res = ev.evaluate(ctx)
        runs.append(res.run)
        metrics.extend(res.metrics)
        violations.extend(res.violations)
    for name in FUTURE_EVALUATORS:
        runs.append(
            EvaluatorRun(
                name=name,
                version=VERSION,
                status=EvaluatorRunStatus.NOT_RUN,
                reason="designed for a later milestone; nothing was measured",
            )
        )
    violations = [
        v.model_copy(update={"id": f"v-{i:03d}-{v.code.replace('_', '-')}"[:64].rstrip("-")})
        for i, v in enumerate(violations, start=1)
    ]
    checked = codepack_rules_checked(ctx) if codepack is not None else []
    return EvaluationReport(
        id=report_id(plan.option_id),
        plan_ref=plan_ref,
        evaluators=runs,
        metrics=metrics,
        violations=violations,
        compliance=compliance_statement(codepack, checked),
        provenance=Provenance(
            created_at=created_at,
            created_by=EVALUATION_ACTOR,
            method="deterministic_evaluation",
            tool="house-ai evaluation",
            tool_version=VERSION,
            inputs=[plan_ref, *(inputs or [])],
            notes="Measured from the canonical model; terrain values are interpolated (inferred).",
        ),
    )
