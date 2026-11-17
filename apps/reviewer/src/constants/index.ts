/**
 * Constants for House AI Plan Reviewer UI.
 */

/**
 * Revision operations the reviewer offers. Every value must be a verb of the one table in
 * src/house_ai/domain/revision_ops.py (`REVISION_VERBS`); tests/test_revision_operations.py
 * checks this. Operations the solver cannot honour yet (orientation, daylight) are not offered.
 */
export const REVISION_OPS = [
  { value: "area", label: "--area", description: "Change target room area" },
  { value: "separate", label: "--separate", description: "Enforce separation between spaces" },
  { value: "adjacent", label: "--adjacent", description: "Enforce direct adjacency between spaces" },
  { value: "near", label: "--near", description: "Place spaces near each other" },
  { value: "level", label: "--level", description: "Assign room to specific level" },
  { value: "rethink", label: "--rethink", description: "Rethink/re-explore room layout" },
  { value: "strategy", label: "--strategy", description: "Switch massing strategy" },
  { value: "connect", label: "--connect", description: "Add direct door connection" },
  { value: "stair", label: "--stair", description: "Move the stair core (entry, perimeter, central, rear)" },
  { value: "outdoor", label: "--outdoor", description: "Link a room to a terrace, balcony or courtyard" },
] as const;

export type SupportedRevisionOpType = (typeof REVISION_OPS)[number]["value"];

export const DATA_ATTRS = {
  ID: "data-id",
  KIND: "data-kind",
  KINDS: {
    PARCEL: "parcel",
    ENVELOPE: "envelope",
    SPACE: "space",
    WALL: "wall",
    DOOR: "door",
    WINDOW: "window",
    STAIR: "stair",
  },
} as const;

export const PRIVACY_COLORS = {
  PRIVATE: "rgba(168, 85, 247, 0.25)",
  PUBLIC: "rgba(34, 197, 94, 0.25)",
  SERVICE: "rgba(234, 179, 8, 0.25)",
  SEMI_PRIVATE: "rgba(59, 130, 246, 0.25)",
  DEFAULT: "rgba(71, 85, 105, 0.25)",
} as const;
