"""Constants for relation and adjacency semantics shared by solver and evaluators."""

from __future__ import annotations

#: Minimum shared wall length (in metres) to satisfy an ADJACENT relation.
SHARED_WALL_MIN_M: float = 0.9

#: Threshold tolerance (in metres) below which wall sharing is deemed negligible
#: (for SEPARATED and ACOUSTIC_SEPARATION).
SEPARATION_TOUCH_TOLERANCE_M: float = 0.1

#: Maximum circulation graph hops to satisfy a NEAR relation.
NEAR_MAX_HOPS: int = 2

#: Maximum walking route distance (in metres) to satisfy a NEAR relation.
NEAR_MAX_DISTANCE_M: float = 12.0

#: Minimum exterior wall length (in metres) to satisfy an ADJACENT relation with EXTERIOR.
EXTERIOR_SHARED_WALL_MIN_M: float = 1.0

#: Minimum wall length (in metres) required to place a connecting door.
MIN_DOOR_WALL_LENGTH_M: float = 0.8
