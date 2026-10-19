"""Versioned, cited conceptual furniture templates; no jurisdictional authority."""

import math
from dataclasses import asdict, dataclass

from house_ai.constants.evaluations import MIN_STAIR_HEADROOM_M, MIN_STAIR_LANDING_M
from house_ai.domain.usability_templates import (  # noqa: F401  (re-exported)
    ACCESS,
    DINING,
    KITCHEN,
    PROJECT,
    STAIRS,
    TEMPLATES,
    VERSION,
    dimension,
    template,
)


@dataclass(frozen=True)
class UsabilityPolicy:
    """Every non-numerical-tolerance threshold is an assumption, overridable by caller."""

    min_rise_m: float = 0.15
    max_rise_m: float = 0.22
    min_going_m: float = 0.22
    min_stair_width_m: float = 0.9
    min_headroom_m: float = MIN_STAIR_HEADROOM_M
    landing_m: float = MIN_STAIR_LANDING_M
    approach_m: float = 0.9
    max_corridor_ratio: float = 0.25
    max_dead_end_m: float = 6
    residual_width_m: float = 0.9
    max_daily_route_m: float = 15
    max_grade_step_m: float = 0.2
    min_glazing_ratio: float = 0.1
    min_facade_angle_deg: float = 45
    potential_sill_m: float = 0.9
    turning_diameter_m: float = 1.5
    work_zone_inset_m: float = 0.75
    min_traffic_intersection_m: float = 0.1
    max_residual_share: float = 0.5

    def __post_init__(self):
        if any(not math.isfinite(v) or v <= 0 for v in asdict(self).values()):
            raise ValueError("usability thresholds must be finite and positive")
        if self.min_rise_m > self.max_rise_m:
            raise ValueError("minimum rise must not exceed maximum rise")
        if self.max_corridor_ratio >= 1 or self.max_residual_share >= 1:
            raise ValueError("area-share assumptions must be less than one")

    def basis(self, field: str) -> str:
        source = (
            STAIRS
            if field in {"min_rise_m", "max_rise_m", "min_going_m", "min_headroom_m"}
            else PROJECT
        )
        return f"assumption {field}={getattr(self, field)}; precedent: {source}; not code checked"
