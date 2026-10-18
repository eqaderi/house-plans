"""Canonical proposed earthwork pads and derived hillside view requests.

All elevations use the model's LOCAL datum. Pads are design proposals, never
survey observations or statements of engineering suitability.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import Id, StrictModel
from .geometry import Point2, Polygon2D


class EarthworkPad(StrictModel):
    id: Id
    boundary: Polygon2D
    elevation_m: float
    basis: str = Field(min_length=1)


class SectionLine(StrictModel):
    id: Id
    start: Point2
    end: Point2

    @model_validator(mode="after")
    def _length(self) -> SectionLine:
        if self.start == self.end:
            raise ValueError("a section line needs distinct endpoints")
        return self


class HillsideSettings(StrictModel):
    """Concept review triggers, not jurisdictional or engineering limits."""

    large_void_height_m: float = Field(default=4.0, gt=0)
    access_step_trigger_m: float = Field(default=0.3, gt=0)
    vehicle_grade_trigger_pct: float = Field(default=15.0, gt=0)
    sliver_quality_trigger: float = Field(default=0.02, gt=0, lt=1)
