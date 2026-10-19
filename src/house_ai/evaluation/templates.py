"""Versioned, cited conceptual furniture templates; no jurisdictional authority."""

import math
from dataclasses import asdict, dataclass

from house_ai.constants.evaluations import MIN_STAIR_HEADROOM_M, MIN_STAIR_LANDING_M
from house_ai.domain.usability import DimensionAssumption, FurnitureTemplate

VERSION = "1.0.0"
PROJECT = "docs/adr/0019-usability-geometry-and-assumptions.md (synthetic planning assumption)"
STAIRS = (
    "https://assets.publishing.service.gov.uk/government/uploads/"
    "system/uploads/attachment_data/file/996860/Approved_Document_K.pdf"
)
KITCHEN = "https://media.nkba.org/uploads/2022/05/Kitchen-Planning-Guidelines.pdf"
ACCESS = "https://www.access-board.gov/ada/guides/chapter-6-toilet-rooms/"
DINING = "https://www.ikea.com/gb/en/cat/6-seater-dining-tables-21827/"


def dimension(ident, value, source=PROJECT, rationale="Conceptual planning envelope"):
    return DimensionAssumption(id=ident, value=value, unit="m", source=source, rationale=rationale)


def template(ident, width, depth, *, left=0, right=0, front=0, back=0, source=PROJECT):
    def d(key, value):
        return dimension(f"{ident}-{key}", value, source)

    return FurnitureTemplate(
        id=ident,
        width=d("width", width),
        depth=d("depth", depth),
        left=d("left", left),
        right=d("right", right),
        front=d("front", front),
        back=d("back", back),
        description="Front is local negative Y; source is precedent, not code authority.",
    )


TEMPLATES = {
    t.id: t
    for t in [
        template("bed-double", 1.6, 2, left=0.6, right=0.6, front=0.75),
        template("bed-single", 0.9, 2, right=0.6, front=0.6),
        template("wardrobe", 1.2, 0.6, front=0.9),
        template("desk", 1.2, 0.6, front=0.9),
        template("chair", 0.5, 0.5, front=0.6),
        template(
            "dining",
            1.8,
            0.9,
            left=0.9,
            right=0.9,
            front=0.9,
            back=0.9,
            source=DINING + "; clearances: " + PROJECT,
        ),
        template("sofa-group", 2.4, 2.4, right=0.9),
        template("kitchen-run", 3, 0.6, front=1.219, source=KITCHEN + "; run/depth: " + PROJECT),
        template("appliance", 0.6, 0.6, front=0.9),
        template(
            "wc",
            0.4,
            0.7,
            front=0.75,
            left=0.2,
            right=0.2,
            source=ACCESS + "; non-accessible illustrative sizes: " + PROJECT,
        ),
        template("basin", 0.6, 0.5, front=0.7),
        template("shower", 0.9, 0.9, front=0.6),
        template("bath", 1.7, 0.75, front=0.6),
        template("vehicle", 1.8, 4.5, left=0.6, right=0.6, front=0.9, back=0.3),
        template("shelf", 1.2, 0.45, front=0.9),
        template("laundry", 1.8, 0.65, front=0.9),
    ]
}


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
