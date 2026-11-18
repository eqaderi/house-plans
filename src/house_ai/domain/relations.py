"""Authoritative relation and adjacency semantics shared by solver and evaluators.

Defines spatial relation satisfaction conditions per ADR 0020.
"""

from __future__ import annotations

from collections import deque

import shapely.ops

from house_ai.constants.relations import (
    EXTERIOR_SHARED_WALL_MIN_M,
    NEAR_MAX_HOPS,
    SEPARATION_TOUCH_TOLERANCE_M,
    SHARED_WALL_MIN_M,
)
from house_ai.domain.base import EXTERIOR
from house_ai.domain.model import HouseModel
from house_ai.domain.program import SpaceRelationshipKind


def shared_wall_length(model: HouseModel, a: str, b: str) -> float:
    """Calculate the shared wall contact length (in metres) between two spaces."""
    if a == EXTERIOR and b == EXTERIOR:
        return 0.0
    if a == EXTERIOR:
        return exterior_wall_length(model, b)
    if b == EXTERIOR:
        return exterior_wall_length(model, a)

    sa, sb = model.space(a), model.space(b)
    if sa.level_id != sb.level_id:
        return 0.0

    poly_a = sa.boundary.to_shapely()
    poly_b = sb.boundary.to_shapely()
    inter = poly_a.boundary.intersection(poly_b.boundary)
    return float(inter.length)


def exterior_wall_length(model: HouseModel, space_id: str) -> float:
    """Calculate the length (in metres) of the space perimeter bordering the exterior."""
    if space_id == EXTERIOR:
        return 0.0
    space = model.space(space_id)
    level_spaces = [
        s for s in model.spaces if s.level_id == space.level_id and s.id != space_id
    ]
    poly = space.boundary.to_shapely()
    if not level_spaces:
        return float(poly.boundary.length)

    others_poly = shapely.ops.unary_union([s.boundary.to_shapely() for s in level_spaces])
    ext_boundary = poly.boundary.difference(others_poly.buffer(1e-5))
    return float(ext_boundary.length)


def hops_between(graph: dict[str, set[str]], origin: str) -> dict[str, int]:
    """Breadth-first shortest path hop counts from origin across the circulation graph."""
    dist: dict[str, int] = {origin: 0}
    queue = deque([origin])
    while queue:
        n = queue.popleft()
        for m in sorted(graph.get(n, ())):
            if m not in dist:
                dist[m] = dist[n] + 1
                queue.append(m)
    return dist


def is_relation_satisfied(  # noqa: C901
    kind: SpaceRelationshipKind,
    model: HouseModel,
    graph: dict[str, set[str]],
    a_spaces: list[str],
    b_spaces: list[str],
) -> tuple[bool | None, str]:
    """Evaluate whether an adjacency relation is satisfied.

    Returns:
        (satisfied, method) where satisfied is True, False, or None (not evaluated/checked).
    """
    if not a_spaces or not b_spaces:
        return False, "missing_spaces"

    K = SpaceRelationshipKind
    if kind is K.CONNECTED:
        method = "graph_analysis"
        connected = any(b in graph.get(a, set()) for a in a_spaces for b in b_spaces)
        return connected, method

    if kind is K.ADJACENT:
        method = "shared_boundary"
        for a in a_spaces:
            for b in b_spaces:
                if a == EXTERIOR:
                    if exterior_wall_length(model, b) >= EXTERIOR_SHARED_WALL_MIN_M:
                        return True, method
                elif b == EXTERIOR:
                    if exterior_wall_length(model, a) >= EXTERIOR_SHARED_WALL_MIN_M:
                        return True, method
                else:
                    if shared_wall_length(model, a, b) >= SHARED_WALL_MIN_M:
                        return True, method
        return False, method

    if kind is K.NEAR:
        method = "graph_analysis"
        for a in a_spaces:
            hops = hops_between(graph, a)
            for b in b_spaces:
                if hops.get(b, 999) <= NEAR_MAX_HOPS:
                    return True, method
        return False, method

    if kind is K.SEPARATED:
        method = "shared_boundary_and_connectivity"
        for a in a_spaces:
            for b in b_spaces:
                if a == EXTERIOR:
                    if (
                        b in graph.get(a, set())
                        or exterior_wall_length(model, b) > SEPARATION_TOUCH_TOLERANCE_M
                    ):
                        return False, method
                elif b == EXTERIOR:
                    if (
                        a in graph.get(b, set())
                        or exterior_wall_length(model, a) > SEPARATION_TOUCH_TOLERANCE_M
                    ):
                        return False, method
                else:
                    if (
                        b in graph.get(a, set())
                        or shared_wall_length(model, a, b) > SEPARATION_TOUCH_TOLERANCE_M
                    ):
                        return False, method
        return True, method

    if kind is K.ACOUSTIC_SEPARATION:
        method = "shared_boundary"
        for a in a_spaces:
            for b in b_spaces:
                if a == EXTERIOR:
                    if exterior_wall_length(model, b) > SEPARATION_TOUCH_TOLERANCE_M:
                        return False, method
                elif b == EXTERIOR:
                    if exterior_wall_length(model, a) > SEPARATION_TOUCH_TOLERANCE_M:
                        return False, method
                else:
                    if (
                        b in graph.get(a, set())
                        or shared_wall_length(model, a, b) > SEPARATION_TOUCH_TOLERANCE_M
                    ):
                        return False, method
        return True, method

    if kind is K.VISUAL:
        # Visual sightlines require open-plan zoning or cased interior openings
        return None, "line_of_sight_analysis"

    return None, "not_evaluated"
