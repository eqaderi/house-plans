"""Explicit HARD and SOFT constraints.

HARD: a candidate plan is invalid if violated.
SOFT: contributes, with a weight, to a multi-objective score.

Rules are a discriminated union so solvers and evaluators can dispatch on
``rule.kind`` and unknown rule kinds fail validation.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, StrictModel
from .program import Strength
from .provenance import Provenance


class SoftObjective(StrEnum):
    ADJACENCY_QUALITY = "adjacency_quality"
    CIRCULATION_EFFICIENCY = "circulation_efficiency"
    PRIVACY = "privacy"
    ACOUSTIC_ZONING = "acoustic_zoning"
    DAYLIGHT_OPPORTUNITY = "daylight_opportunity"
    ORIENTATION = "orientation"
    VIEWS = "views"
    CROSS_VENTILATION = "cross_ventilation"
    INDOOR_OUTDOOR = "indoor_outdoor"
    KITCHEN_FUNCTIONALITY = "kitchen_functionality"
    FURNITURE_USABILITY = "furniture_usability"
    STORAGE = "storage"
    CONSOLIDATED_WET_ZONES = "consolidated_wet_zones"
    STRUCTURAL_REGULARITY = "structural_regularity"
    ENVELOPE_SIMPLICITY = "envelope_simplicity"
    ADAPTABILITY = "adaptability"
    CONSTRUCTION_COMPLEXITY = "construction_complexity"
    COST_PROXY = "cost_proxy"
    SITE_RESPONSE = "site_response"
    LANDSCAPE_QUALITY = "landscape_quality"
    CULTURAL_FIT = "cultural_fit"


class NoOverlapRule(StrictModel):
    kind: Literal["no_overlap"] = "no_overlap"


class WithinEnvelopeRule(StrictModel):
    kind: Literal["within_envelope"] = "within_envelope"


class ValidGeometryRule(StrictModel):
    kind: Literal["valid_geometry"] = "valid_geometry"


class OpeningsOnWallsRule(StrictModel):
    kind: Literal["openings_on_walls"] = "openings_on_walls"


class DoorsConnectValidSpacesRule(StrictModel):
    kind: Literal["doors_connect_valid_spaces"] = "doors_connect_valid_spaces"


class TraversableRule(StrictModel):
    """Every listed target is reachable from ``origin`` through passable openings."""

    kind: Literal["traversable"] = "traversable"
    origin: Id = "exterior"
    #: Program item ids; empty means every space.
    targets: list[Id] = Field(default_factory=list)


class MinAreaRule(StrictModel):
    kind: Literal["min_area"] = "min_area"
    program_item_id: Id
    min_area_m2: float = Field(gt=0)


class MinDimensionRule(StrictModel):
    kind: Literal["min_dimension"] = "min_dimension"
    program_item_id: Id
    min_width_m: float = Field(gt=0)


class AdjacencyRule(StrictModel):
    kind: Literal["adjacency"] = "adjacency"
    #: AdjacencyRequirement id in the space program.
    requirement_id: Id


class ObjectiveRule(StrictModel):
    kind: Literal["objective"] = "objective"
    objective: SoftObjective


Rule = Annotated[
    NoOverlapRule
    | WithinEnvelopeRule
    | ValidGeometryRule
    | OpeningsOnWallsRule
    | DoorsConnectValidSpacesRule
    | TraversableRule
    | MinAreaRule
    | MinDimensionRule
    | AdjacencyRule
    | ObjectiveRule,
    Field(discriminator="kind"),
]


class ConstraintSourceKind(StrEnum):
    PROGRAM = "program"
    BRIEF = "brief"
    SITE = "site"
    CODEPACK = "codepack"
    USER = "user"
    #: Built-in geometric validity requirement (not a regulation).
    SYSTEM = "system"


class ConstraintSource(StrictModel):
    kind: ConstraintSourceKind
    ref: str | None = None


class CodeRuleRef(StrictModel):
    codepack_id: Id
    rule_id: Id


class Constraint(StrictModel):
    id: Id
    strength: Strength
    rule: Rule
    weight: float | None = Field(default=None, gt=0)
    source: ConstraintSource
    code_rule: CodeRuleRef | None = None
    rationale: str | None = None

    @model_validator(mode="after")
    def _consistent(self) -> Constraint:
        if self.strength is Strength.SOFT and self.weight is None:
            raise ValueError(f"{self.id}: soft constraints need a weight")
        if self.strength is Strength.HARD and self.weight is not None:
            raise ValueError(f"{self.id}: hard constraints must not carry a weight")
        if isinstance(self.rule, ObjectiveRule) and self.strength is Strength.HARD:
            raise ValueError(f"{self.id}: objectives are soft by definition")
        if (self.source.kind is ConstraintSourceKind.CODEPACK) != (self.code_rule is not None):
            raise ValueError(f"{self.id}: codepack constraints, and only they, cite a code rule")
        return self


class ConstraintSet(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    project_id: Id
    constraints: list[Constraint] = Field(default_factory=list)
    provenance: Provenance

    @model_validator(mode="after")
    def _unique_ids(self) -> ConstraintSet:
        ids = [c.id for c in self.constraints]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate constraint ids: {sorted(dupes)}")
        return self

    def hard(self) -> list[Constraint]:
        return [c for c in self.constraints if c.strength is Strength.HARD]

    def soft(self) -> list[Constraint]:
        return [c for c in self.constraints if c.strength is Strength.SOFT]
