"""Evaluator boundary (Milestone D).

Each evaluator reports individual metrics and violations, every one tagged
measured / inferred / simulated / ai_judgment / not_checked. An evaluator
that cannot run reports NOT_RUN with a reason rather than a guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from house_ai.domain.constraints import ConstraintSet
from house_ai.domain.evaluation import EvaluatorRun, MetricClaim, Violation
from house_ai.domain.model import HouseModel
from house_ai.domain.program import SpaceProgram
from house_ai.domain.site import Site


@dataclass
class EvaluationContext:
    model: HouseModel
    site: Site | None
    program: SpaceProgram | None
    constraints: ConstraintSet | None
    #: Whether a human approved this site version (site gate); None means unknown.
    site_approved: bool | None = None


@dataclass
class EvaluatorResult:
    run: EvaluatorRun
    metrics: list[MetricClaim] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)


class Evaluator(Protocol):
    name: str
    version: str

    def evaluate(self, ctx: EvaluationContext) -> EvaluatorResult: ...


#: Evaluators the spec requires first, and those designed for later.
REQUIRED_EVALUATORS = [
    "GeometryEvaluator",
    "ProgramEvaluator",
    "AdjacencyEvaluator",
    "CirculationEvaluator",
    "PrivacyEvaluator",
    "SiteEvaluator",
]
FUTURE_EVALUATORS = [
    "DaylightEvaluator",
    "SolarEvaluator",
    "AccessibilityEvaluator",
    "LifeSafetyEvaluator",
    "StructuralConceptEvaluator",
    "MEPConceptEvaluator",
    "CostEvaluator",
    "EnergyEvaluator",
    "CulturalFitEvaluator",
]
