"""Constants for concept topology proposals (Stage S7)."""

from __future__ import annotations

#: Stair-core placement positions within a topology concept.
STAIR_CORE_CENTRAL: str = "central"
STAIR_CORE_ENTRY: str = "entry"
STAIR_CORE_PERIMETER: str = "perimeter"
STAIR_CORE_REAR: str = "rear"

VALID_STAIR_POSITIONS: frozenset[str] = frozenset(
    {
        STAIR_CORE_CENTRAL,
        STAIR_CORE_ENTRY,
        STAIR_CORE_PERIMETER,
        STAIR_CORE_REAR,
    }
)

#: Outdoor link kinds connecting interior spaces to exterior areas.
OUTDOOR_LINK_TERRACE: str = "terrace"
OUTDOOR_LINK_COURTYARD: str = "courtyard"
OUTDOOR_LINK_BALCONY: str = "balcony"

#: The outdoor link kinds the 2D solver can place, and so the ones a revision may ask for.
VALID_OUTDOOR_LINKS: frozenset[str] = frozenset(
    {
        OUTDOOR_LINK_TERRACE,
        OUTDOOR_LINK_COURTYARD,
        OUTDOOR_LINK_BALCONY,
    }
)

#: Finding codes for topology proposal validation.
ERR_UNKNOWN_PROGRAM_ITEM: str = "unknown_program_item"
ERR_MISSING_LEVEL_ASSIGNMENT: str = "missing_level_assignment"
ERR_DISCONNECTED_TOPOLOGY: str = "disconnected_topology"
ERR_CROSS_LEVEL_HARD_ADJACENCY: str = "cross_level_hard_adjacency"
ERR_CONFLICTING_ADJACENCY: str = "conflicting_adjacency"
ERR_PROGRAM_HARD_ADJACENCY_VIOLATION: str = "program_hard_adjacency_violation"
ERR_EXCESSIVE_LEVELS: str = "excessive_levels"
ERR_MISSING_VERTICAL_CIRCULATION: str = "missing_vertical_circulation"
