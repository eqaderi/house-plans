"""Typed topology proposals for floor-plan concept generation (Stage S7).

The AI proposes spatial ideas (zones, adjacency graph, level assignments,
stair core positions, outdoor links, intent text); the formal solver places
and verifies them. Raw LLM coordinates never replace the canonical model.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from house_ai.constants.proposals import (
    OUTDOOR_LINK_TERRACE,
    STAIR_CORE_CENTRAL,
)

from .base import SCHEMA_VERSION, Id, StrictModel
from .program import Privacy, SpaceRelationshipKind, Strength
from .provenance import Provenance


class ProposalZone(StrictModel):
    """A thematic functional zone grouping spaces in a concept proposal."""

    id: Id
    name: str = Field(min_length=1)
    program_item_ids: list[Id] = Field(default_factory=list)
    privacy: Privacy | None = None


class ProposalLevelAssignment(StrictModel):
    """Assignment of a program item to a specific storey or elevation tier."""

    program_item_id: Id
    level_id: str = Field(min_length=1)


class ProposalAdjacency(StrictModel):
    """Adjacency or connection relationship proposed between two spaces."""

    id: Id
    a: Id
    b: Id
    kind: SpaceRelationshipKind = SpaceRelationshipKind.ADJACENT
    strength: Strength = Strength.SOFT
    weight: float | None = Field(default=None, gt=0)
    rationale: str | None = None

    @model_validator(mode="after")
    def _validate_adjacency(self) -> ProposalAdjacency:
        if self.a == self.b:
            raise ValueError(f"{self.id}: adjacency from an item to itself ({self.a})")
        if self.strength is Strength.SOFT and self.weight is None:
            # Default soft weight to 1.0 if unspecified
            self.weight = 1.0
        elif self.strength is Strength.HARD and self.weight is not None:
            raise ValueError(f"{self.id}: hard requirements must not carry a weight")
        return self


class StairCoreProposal(StrictModel):
    """Proposed vertical circulation core and its target location."""

    id: Id
    position: str = STAIR_CORE_CENTRAL
    connects_levels: list[str] = Field(min_length=2)
    near_program_item_ids: list[Id] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_stair_core(self) -> StairCoreProposal:
        if len(set(self.connects_levels)) != len(self.connects_levels):
            raise ValueError(f"{self.id}: duplicate level in connects_levels")
        return self


class OutdoorLinkProposal(StrictModel):
    """Proposed connection between an interior space and an outdoor feature."""

    id: Id
    program_item_id: Id
    kind: str = OUTDOOR_LINK_TERRACE
    notes: str | None = None


class ConceptProposal(StrictModel):
    """A typed topology proposal submitted by an agent or human.

    Specifies high-level architectural intentions without hard-coded coordinates,
    allowing the solver to explore and optimize physical placement.
    """

    schema_version: str = SCHEMA_VERSION
    id: Id
    project_id: Id
    name: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    zones: list[ProposalZone] = Field(default_factory=list)
    level_assignments: list[ProposalLevelAssignment] = Field(default_factory=list)
    adjacency_graph: list[ProposalAdjacency] = Field(default_factory=list)
    stair_cores: list[StairCoreProposal] = Field(default_factory=list)
    outdoor_links: list[OutdoorLinkProposal] = Field(default_factory=list)
    target_strategy: str | None = None
    provenance: Provenance | None = None

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> ConceptProposal:
        for attr, items in (
            ("zones", self.zones),
            ("adjacency_graph", self.adjacency_graph),
            ("stair_cores", self.stair_cores),
            ("outdoor_links", self.outdoor_links),
        ):
            ids = [i.id for i in items]
            if len(set(ids)) != len(ids):
                raise ValueError(f"duplicate id found in {attr}")

        assigned_items = [la.program_item_id for la in self.level_assignments]
        if len(set(assigned_items)) != len(assigned_items):
            raise ValueError("duplicate program_item_id assigned to multiple levels")
        return self
