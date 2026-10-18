"""Constants for the two-dimensional placement engine (CP-SAT NoOverlap2D)."""

from __future__ import annotations

#: Maximum aspect ratio (length / width) allowed for rectangular rooms in 2D placement.
MAX_ASPECT_RATIO = 2.5

#: Minimum dimension (width or depth) in metres for any habitable space in 2D placement.
MIN_ROOM_DIMENSION_M = 1.5

#: Minimum shared wall length in metres for an open-plan composite space (living/dining/kitchen).
OPEN_PLAN_SHARED_WALL_MIN_M = 1.8

#: Maximum target circulation share (fraction of gross floor area) in corridor-free layout.
CIRCULATION_TARGET_SHARE_MAX = 0.15

#: Default CP-SAT deterministic time budget in solver work units.
DEFAULT_DET_TIME_BUDGET = 5.0

#: Default solver random seed.
DEFAULT_SOLVER_SEED = 0

#: Wall thicknesses for canonical model assembly from 2D placement.
WALL_THICKNESS_INTERIOR_M = 0.15
WALL_THICKNESS_EXTERIOR_M = 0.30
WALL_HEIGHT_M = 2.8

#: Default opening dimensions.
DOOR_WIDTH_DEFAULT_M = 0.8
DOOR_HEIGHT_DEFAULT_M = 2.1
OPEN_PLAN_OPENING_WIDTH_M = 1.8
WINDOW_WIDTH_DEFAULT_M = 1.2
WINDOW_HEIGHT_DEFAULT_M = 1.4

#: L-shaped and multi-wing layout constants (S7-14).
L_SHAPE_MIN_RECESS_DM = 20  # 2.0 m minimum corner recess
WING_DAY = "wing_day"
WING_NIGHT = "wing_night"

#: Courtyard layout constants (S7-15).
COURTYARD_SPACE_ID = "sp-court-central"
COURTYARD_NAME = "Central Courtyard"
COURTYARD_MIN_DIM_DM = 30  # 3.0 m
COURTYARD_MAX_DIM_DM = 60  # 6.0 m
COURTYARD_MIN_AREA_DM2 = 900  # 9.0 m²

#: Level identifiers and stair core constants (S7-16).
LEVEL_ENTRY = "lv-entry"
LEVEL_UPPER = "lv-upper"
LEVEL_LOWER = "lv-lower"
STAIR_CORE_DEFAULT_WIDTH_DM = 20  # 2.0 m
STAIR_CORE_DEFAULT_DEPTH_DM = 30  # 3.0 m
STAIR_CORE_SPACE_ID_ENTRY = "sp-stair-lv-entry"
STAIR_CORE_SPACE_ID_UPPER = "sp-stair-lv-upper"

#: Privacy zone identifiers (S7-17).
ZONE_FAMILY = "zone-family"
ZONE_PUBLIC = "zone-public"
ZONE_GUEST = "zone-guest"
ZONE_SERVICE = "zone-service"
ZONE_OUTDOOR = "zone-outdoor"

#: Terrace and parapet constants (S7-19).
PARAPET_HEIGHT_M = 1.0
PARAPET_THICKNESS_M = 0.20
TERRACE_SLAB_THICKNESS_M = 0.15
TERRACE_DOOR_DEFAULT_WIDTH_M = 1.2
