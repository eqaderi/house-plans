"""Synthetic benchmark contracts, separate from the owner's project artifacts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, StrictModel
from .epistemics import ClaimStatus
from .model import HouseModel
from .program import SpaceProgram
from .provenance import DataClassification
from .site import Site


class AcceptanceCategory(StrEnum):
    GEOMETRY = "geometric_feasibility"
    USABILITY = "practical_usability"
    CIRCULATION = "circulation"
    PRIVACY = "privacy"
    TERRAIN = "terrain_compatibility"
    DIVERSITY = "spatial_topological_diversity"
    ACCURACY = "metric_accuracy"
    UNKNOWNS = "unknowns"
    VISUAL = "visual_consistency"
    REVISIONS = "versioned_revisions"


class ExpectedFinding(StrictModel):
    """A metric comparison or count of findings, with explicit evidence status.

    An unavailable future probe is NOT_CHECKED, never a successful regression.
    A metric intentionally reporting NOT_CHECKED (e.g. unknown orientation) can
    be asserted by setting status=not_checked and value=null instead.
    """

    id: Id
    category: AcceptanceCategory
    target: Id = "site"  # site, program, or a BenchmarkCase id
    source: Literal["site", "program", "integrity", "evaluation", "future"]
    metric: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")
    code: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")
    subject_ids: list[Id] = Field(default_factory=list)
    value: float | int | bool | str | None = None
    status: ClaimStatus = ClaimStatus.MEASURED
    tolerance: float = Field(default=1e-6, ge=0)
    pending_stage: str | None = Field(default=None, pattern=r"^S[0-9]+$")
    basis: str = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> ExpectedFinding:
        if (self.metric is None) == (self.code is None):
            raise ValueError("specify exactly one metric or finding code")
        if self.source == "future":
            if not self.pending_stage:
                raise ValueError("a future probe needs a pending_stage")
        elif self.pending_stage:
            raise ValueError("pending_stage is only allowed on future probes")
        if self.status is ClaimStatus.NOT_CHECKED:
            if self.value is not None or self.code is not None:
                raise ValueError("not_checked requires a metric and null value")
        elif self.value is None:
            raise ValueError("checked expectations require a value")
        if self.code and (
            type(self.value) is not int
            or self.value < 0
            or self.source not in ("integrity", "evaluation", "future")
        ):
            raise ValueError("finding expectations require a nonnegative integer count")
        return self


class BenchmarkCase(StrictModel):
    id: Id
    description: str
    model: HouseModel
    #: Defects are intentional regression inputs, never proposed house designs.
    seeded_defect: bool = False


class BenchmarkFixture(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    description: str
    generator: str
    ground_truth: str = Field(min_length=1)
    site: Site
    program: SpaceProgram
    cases: list[BenchmarkCase] = Field(default_factory=list)
    expectations: list[ExpectedFinding] = Field(min_length=1)

    @model_validator(mode="after")
    def _synthetic_and_linked(self) -> BenchmarkFixture:
        if self.site.classification is not DataClassification.SYNTHETIC:
            raise ValueError("benchmarks may contain only synthetic sites")
        if self.site.project_id != self.program.project_id:
            raise ValueError("site and program must name the same synthetic project")
        ids = [c.id for c in self.cases]
        if len(ids) != len(set(ids)) or set(ids) & {"site", "program"}:
            raise ValueError("case ids must be unique and not site/program")
        expected_ids = [e.id for e in self.expectations]
        if len(expected_ids) != len(set(expected_ids)):
            raise ValueError("expectation ids must be unique")
        for e in self.expectations:
            if e.target not in {"site", "program", *ids}:
                raise ValueError(f"unknown expectation target {e.target}")
            if e.source == "site" and e.target != "site":
                raise ValueError("site probes require target site")
            if e.source == "program" and e.target != "program":
                raise ValueError("program probes require target program")
            if e.source in ("integrity", "evaluation") and e.target not in ids:
                raise ValueError("model probes require a case target")
        return self
