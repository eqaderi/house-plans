"""Evaluation results: individual metrics and violations, each with provenance.

There is no single opaque score. Every value says how it was obtained
(measured, inferred, simulated, AI judgment, or not checked) and by which
evaluator and method.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_serializer, model_validator

from .base import SCHEMA_VERSION, Id, StrictModel
from .codepack import ComplianceStatement
from .epistemics import ClaimStatus
from .program import Strength
from .provenance import ArtifactKind, ArtifactRef, Provenance


class MetricClaim(StrictModel):
    metric: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    value: float | int | bool | str | None
    unit: str | None = None
    #: e.g. "graph_analysis", "polygon_area", "llm_critique".
    method: str
    status: ClaimStatus
    evaluator: str
    evaluator_version: str
    subject_ids: list[str] = Field(default_factory=list)
    assumption_basis: str | None = None

    @model_serializer(mode="wrap")
    def _legacy_hash_compatible(self, handler):
        data = handler(self)
        if self.assumption_basis is None:
            data.pop("assumption_basis", None)
        return data

    @model_validator(mode="after")
    def _not_checked_has_no_value(self) -> MetricClaim:
        if self.status is ClaimStatus.NOT_CHECKED and self.value is not None:
            raise ValueError(f"{self.metric}: a not-checked metric cannot carry a value")
        if self.status is not ClaimStatus.NOT_CHECKED and self.value is None:
            raise ValueError(f"{self.metric}: a checked metric needs a value")
        return self


class Violation(StrictModel):
    id: Id
    #: Constraint id from the constraint set, when the violation maps to one.
    constraint_id: Id | None = None
    #: Machine code, e.g. "space_overlap", "opening_outside_wall".
    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    strength: Strength
    message: str
    subject_ids: list[str] = Field(default_factory=list)
    status: ClaimStatus
    evaluator: str
    method: str | None = None
    assumption_basis: str | None = None

    @model_serializer(mode="wrap")
    def _legacy_hash_compatible(self, handler):
        data = handler(self)
        for field in ("method", "assumption_basis"):
            if getattr(self, field) is None:
                data.pop(field, None)
        return data


class EvaluatorRunStatus(StrEnum):
    RAN = "ran"
    NOT_RUN = "not_run"
    FAILED = "failed"


class EvaluatorRun(StrictModel):
    name: str
    version: str
    status: EvaluatorRunStatus
    reason: str | None = None


class EvaluationReport(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    plan_ref: ArtifactRef
    evaluators: list[EvaluatorRun] = Field(min_length=1)
    metrics: list[MetricClaim] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)
    compliance: ComplianceStatement
    provenance: Provenance

    @model_validator(mode="after")
    def _evaluates_a_plan(self) -> EvaluationReport:
        if self.plan_ref.kind is not ArtifactKind.PLAN:
            raise ValueError("plan_ref must point at a plan artifact")
        return self

    @property
    def hard_violations(self) -> list[Violation]:
        return [v for v in self.violations if v.strength is Strength.HARD]
