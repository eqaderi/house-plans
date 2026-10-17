"""Plan generation boundary (Milestone D).

Hybrid pipeline: an LLM may propose topology (adjacency graph, strategy),
a formal solver (OR-Tools CP-SAT planned) produces vector geometry, and
deterministic checks validate it. Generators return canonical
:class:`~house_ai.domain.plan.PlanVersion` objects, never images.
"""

from __future__ import annotations

from typing import Protocol

from house_ai.domain.constraints import ConstraintSet
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.site import Site


class PlanGenerator(Protocol):
    name: str

    def generate(
        self,
        site: Site,
        program: SpaceProgram,
        constraints: ConstraintSet,
        *,
        strategies: list[str],
        seed: int,
    ) -> list[PlanVersion]: ...
