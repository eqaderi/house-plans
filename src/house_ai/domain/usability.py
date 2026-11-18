"""Canonical placed furniture, clear zones and explicit usability requirements.

Dimensions are LOCAL metres. Templates and proposed arrangements are derived;
only explicitly placed elements are canonical (ADR 0019).
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import Id, PositiveFloat, StrictModel
from .geometry import Point2, Polygon2D


class Furniture(StrictModel):
    id: Id
    space_id: Id
    template_id: Id
    position: Point2
    rotation_deg: float = 0
    width_m: PositiveFloat
    depth_m: PositiveFloat

    def footprint_polygon(self) -> Polygon2D:
        return Polygon2D.rotated_rectangle(
            self.position, self.width_m, self.depth_m, self.rotation_deg
        )


class ClearanceZone(StrictModel):
    id: Id
    element_id: Id
    space_id: Id
    boundary: Polygon2D
    purpose: str = Field(min_length=1)
    basis: str = Field(min_length=1)
    status: Literal["assumption"] = "assumption"


class VehicleEnvelope(StrictModel):
    """Requested vehicle size; not a turning-radius or swept-path model."""

    id: Id
    width_m: PositiveFloat
    length_m: PositiveFloat
    door_side_clearance_m: PositiveFloat
    turning_radius_m: PositiveFloat | None = None
    source: str = Field(min_length=1)


class UsabilityRequirements(StrictModel):
    #: Saved as ``*_program_item_ids`` in space programs before schema 0.2.0 (ADR 0025).

    household_seats: int | None = Field(default=None, ge=1)
    vehicles: list[VehicleEnvelope] | None = None
    arrival_path: list[Point2] | None = Field(default=None, min_length=2)
    double_bed_space_requirement_ids: list[Id] = Field(default_factory=list)
    single_bed_space_requirement_ids: list[Id] = Field(default_factory=list)


class DimensionAssumption(StrictModel):
    id: Id
    value: float = Field(ge=0)
    unit: Literal["m"]
    source: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    status: Literal["assumption"] = "assumption"


class FurnitureTemplate(StrictModel):
    id: Id
    width: DimensionAssumption
    depth: DimensionAssumption
    left: DimensionAssumption
    right: DimensionAssumption
    front: DimensionAssumption
    back: DimensionAssumption
    #: Front is local negative Y; rotation is CCW.
    description: str

    @model_validator(mode="after")
    def _positive_body(self) -> FurnitureTemplate:
        if self.width.value <= 0 or self.depth.value <= 0:
            raise ValueError("furniture bodies need positive width and depth")
        return self
