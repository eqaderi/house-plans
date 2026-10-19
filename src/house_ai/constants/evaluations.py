"""Evaluation metric and violation code constants."""

from __future__ import annotations

#: Evaluation violation codes
VIOLATION_TERRAIN_COVERAGE_INCOMPLETE = "terrain_coverage_incomplete"
VIOLATION_ELEVATED_FLOOR_SUPPORT = "elevated_floor_support_unresolved"
VIOLATION_EXTERIOR_ACCESS_LEVEL = "exterior_access_level_unresolved"
VIOLATION_REQUIRED_DAYLIGHT_NO_WINDOW = "required_daylight_no_exterior_window"
VIOLATION_ELONGATED_ROOM = "elongated_room"
VIOLATION_BLOCKING_PLAN_ISSUE = "blocking_plan_issue"
VIOLATION_TERRACE_NO_DOOR = "terrace_no_door_access"
VIOLATION_TERRACE_STEP_TOO_HIGH = "terrace_step_too_high"

#: Key terrain and site metrics
METRIC_EXCAVATION_VOLUME = "excavation_volume_m3"
METRIC_FILL_VOLUME = "underfloor_void_volume_m3"
METRIC_MAX_CUT = "max_cut_m"
METRIC_MAX_FILL = "max_underfloor_void_height_m"
METRIC_RETAINING_WALL_LENGTH = "retaining_wall_length_m"
METRIC_RETAINING_WALL_FACE_AREA = "retaining_wall_face_area_m2"
METRIC_EXTERIOR_DOOR_GROUND_DELTA = "exterior_door_ground_delta_m"

#: Room-to-terrace and outdoor relationship metrics (S7-20)
METRIC_ROOM_TERRACE_DOOR_COUNT = "room_terrace_door_count"
METRIC_ROOM_TERRACE_LEVEL_DELTA = "room_terrace_level_delta_m"
METRIC_TERRACE_GROUND_DELTA = "terrace_ground_delta_m"

#: Quantitative diversity metrics and thresholds (S7-24)
DIVERSITY_IOU_THRESHOLD = 0.85
DIVERSITY_TOPOLOGY_THRESHOLD = 0.15
FLAG_NEAR_DUPLICATE = "⚠️ Near-duplicate"

#: Preserved design intent regression prefix (S7-23): a request met before and lost now
REGRESSION_VIOLATION_PREFIX = "regression: earlier request "
#: A request this version carries that is not met and was not met before (S10-03)
REQUEST_NOT_MET_PREFIX = "request not met: "
#: Shortfall allowed before an owner's area request counts as unmet (S7-23 value, kept)
REQUESTED_AREA_TOLERANCE_M2 = 2.0

