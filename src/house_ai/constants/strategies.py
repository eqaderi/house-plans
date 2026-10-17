"""Strategy identifiers and display order for plan generation."""

from __future__ import annotations

STRATEGY_COMPACT = "compact"
STRATEGY_SPLIT_LEVEL = "split_level"
STRATEGY_LINEAR = "linear"
STRATEGY_TWO_WING = "two_wing"
STRATEGY_COURTYARD = "courtyard"
STRATEGY_SPLIT_WALKOUT = "split_walkout"

STRATEGY_ORDER: list[str] = [
    STRATEGY_COMPACT,
    STRATEGY_SPLIT_LEVEL,
    STRATEGY_LINEAR,
    STRATEGY_TWO_WING,
    STRATEGY_COURTYARD,
    STRATEGY_SPLIT_WALKOUT,
]

STRATEGY_LABELS: dict[str, str] = {
    STRATEGY_LINEAR: "Linear bar along the contours",
    STRATEGY_COMPACT: "Compact stacked house",
    STRATEGY_SPLIT_LEVEL: "Split-level, stepping with the slope",
    STRATEGY_SPLIT_WALKOUT: "Hybrid walk-out below entry with a stepped downhill wing",
    STRATEGY_TWO_WING: "Two wings (L): day wing on the road, night wing into the site",
    STRATEGY_COURTYARD: "Two pavilions around a garden court",
}
