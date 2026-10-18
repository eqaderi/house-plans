"""Constants for the 2D concept reviewer application and bundle exchange."""

from __future__ import annotations

# Bundle format
REVIEWER_BUNDLE_SCHEMA_VERSION: str = "1.0.0"
REVIEWER_BUNDLE_FILENAME: str = "bundle.json"
REVISION_OPS_FILENAME: str = "revision_ops.json"

# DOM / SVG element identification
ATTR_DATA_ID: str = "data-id"
ATTR_DATA_KIND: str = "data-kind"

# Supported structured revision operation types
OP_AREA: str = "area"
OP_SEPARATE: str = "separate"
OP_CONNECT: str = "connect"
OP_ADJACENT: str = "adjacent"
OP_NEAR: str = "near"
OP_LEVEL: str = "level"
OP_RETHINK: str = "rethink"
OP_STRATEGY: str = "strategy"
OP_ORIENTATION: str = "orientation"
OP_DAYLIGHT: str = "daylight"
OP_STAIR: str = "stair"
OP_OUTDOOR: str = "outdoor"
OP_PROPOSAL: str = "proposal"

SUPPORTED_REVISION_OPS: tuple[str, ...] = (
    OP_AREA,
    OP_SEPARATE,
    OP_CONNECT,
    OP_ADJACENT,
    OP_NEAR,
    OP_LEVEL,
    OP_RETHINK,
    OP_STRATEGY,
    OP_ORIENTATION,
    OP_DAYLIGHT,
    OP_STAIR,
    OP_OUTDOOR,
    OP_PROPOSAL,
)

# Epistemic status values
STATUS_MEASURED: str = "measured"
STATUS_INFERRED: str = "inferred"
STATUS_SIMULATED: str = "simulated"
STATUS_AI_JUDGMENT: str = "ai_judgment"
STATUS_NOT_CHECKED: str = "not_checked"

EPISTEMIC_STATUSES: tuple[str, ...] = (
    STATUS_MEASURED,
    STATUS_INFERRED,
    STATUS_SIMULATED,
    STATUS_AI_JUDGMENT,
    STATUS_NOT_CHECKED,
)

# Human approval gates
GATE_SITE: str = "site"
GATE_PROGRAM: str = "program"
GATE_PLAN: str = "plan"
GATE_MODEL: str = "model"

APPROVAL_GATES: tuple[str, ...] = (
    GATE_SITE,
    GATE_PROGRAM,
    GATE_PLAN,
    GATE_MODEL,
)

# Default server port
REVIEWER_DEFAULT_PORT: int = 5173

# Element kinds for semantic DOM/SVG tagging and regression checking
KIND_SPACE: str = "space"
KIND_WALL: str = "wall"
KIND_DOOR: str = "door"
KIND_WINDOW: str = "window"
KIND_STAIR: str = "stair"
KIND_PARCEL: str = "parcel"
KIND_ENVELOPE: str = "envelope"
KIND_LABEL: str = "label"
KIND_ELEVATION_MARKER: str = "elevation-marker"

ELEMENT_KINDS: tuple[str, ...] = (
    KIND_SPACE,
    KIND_WALL,
    KIND_DOOR,
    KIND_WINDOW,
    KIND_STAIR,
    KIND_PARCEL,
    KIND_ENVELOPE,
    KIND_LABEL,
    KIND_ELEVATION_MARKER,
)

# Defect types for visual and geometric defect detectors
DEFECT_WINDOW_ON_RETAINING_WALL: str = "window_on_retaining_wall"
DEFECT_OVERLAPPING_LABELS: str = "overlapping_labels"
DEFECT_MISSING_STAIR_LEVEL: str = "missing_stair_level"
DEFECT_MISSING_STAIR_ARRIVAL: str = "missing_stair_arrival"
DEFECT_MISSING_HOST_WALL: str = "missing_host_wall"
DEFECT_DOOR_EXCEEDS_WALL: str = "door_exceeds_wall"

DEFECT_TYPES: tuple[str, ...] = (
    DEFECT_WINDOW_ON_RETAINING_WALL,
    DEFECT_OVERLAPPING_LABELS,
    DEFECT_MISSING_STAIR_LEVEL,
    DEFECT_MISSING_STAIR_ARRIVAL,
    DEFECT_MISSING_HOST_WALL,
    DEFECT_DOOR_EXCEEDS_WALL,
)

# Visual critique severities
SEVERITY_BLOCKING: str = "blocking"
SEVERITY_WARNING: str = "warning"
SEVERITY_INFO: str = "info"

CRITIQUE_SEVERITIES: tuple[str, ...] = (
    SEVERITY_BLOCKING,
    SEVERITY_WARNING,
    SEVERITY_INFO,
)

# SVG rasterization CLI tools
TOOL_RSVG_CONVERT: str = "rsvg-convert"
TOOL_INKSCAPE: str = "inkscape"

# Visual critique filenames and schema version
VISUAL_CRITIQUE_FILENAME: str = "visual_critique.json"
VISUAL_CRITIQUE_SCHEMA_VERSION: str = "1.0.0"
