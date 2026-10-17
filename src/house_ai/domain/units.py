"""Length units. The canonical model is always in metres.

Source drawings may be in any unit; the unit must be either declared by the
source file or confirmed by a human. It is never guessed from coordinate
magnitudes.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import model_validator

from .base import StrictModel
from .epistemics import ConfirmationStatus


class LengthUnit(StrEnum):
    MILLIMETRE = "mm"
    CENTIMETRE = "cm"
    DECIMETRE = "dm"
    METRE = "m"
    KILOMETRE = "km"
    INCH = "in"
    FOOT = "ft"
    US_SURVEY_FOOT = "us_survey_ft"
    YARD = "yd"
    MILE = "mi"


METRES_PER_UNIT: dict[LengthUnit, float] = {
    LengthUnit.MILLIMETRE: 0.001,
    LengthUnit.CENTIMETRE: 0.01,
    LengthUnit.DECIMETRE: 0.1,
    LengthUnit.METRE: 1.0,
    LengthUnit.KILOMETRE: 1000.0,
    LengthUnit.INCH: 0.0254,
    LengthUnit.FOOT: 0.3048,
    LengthUnit.US_SURVEY_FOOT: 1200.0 / 3937.0,
    LengthUnit.YARD: 0.9144,
    LengthUnit.MILE: 1609.344,
}

# DXF $INSUNITS header codes (AutoCAD DXF reference). 0 means "unitless",
# which we treat as unknown rather than defaulting to anything.
_INSUNITS: dict[int, LengthUnit] = {
    1: LengthUnit.INCH,
    2: LengthUnit.FOOT,
    3: LengthUnit.MILE,
    4: LengthUnit.MILLIMETRE,
    5: LengthUnit.CENTIMETRE,
    6: LengthUnit.METRE,
    7: LengthUnit.KILOMETRE,
    10: LengthUnit.YARD,
    14: LengthUnit.DECIMETRE,
    21: LengthUnit.US_SURVEY_FOOT,
}


def unit_from_insunits(code: int | None) -> LengthUnit | None:
    """Map a DXF $INSUNITS code to a unit; None when unitless or unsupported."""
    if code is None:
        return None
    return _INSUNITS.get(code)


def to_metres(value: float, unit: LengthUnit) -> float:
    return value * METRES_PER_UNIT[unit]


def from_metres(value: float, unit: LengthUnit) -> float:
    return value / METRES_PER_UNIT[unit]


def convert(value: float, src: LengthUnit, dst: LengthUnit) -> float:
    return from_metres(to_metres(value, src), dst)


class UnitDeclaration(StrictModel):
    """The length unit of a source drawing and how we know it."""

    unit: LengthUnit | None = None
    status: ConfirmationStatus = ConfirmationStatus.UNKNOWN

    @model_validator(mode="after")
    def _unit_matches_status(self) -> UnitDeclaration:
        if self.status is ConfirmationStatus.UNKNOWN and self.unit is not None:
            raise ValueError("status 'unknown' must not carry a unit")
        if self.status is ConfirmationStatus.LOCAL_ONLY_CONFIRMED:
            raise ValueError("'local_only_confirmed' does not apply to units")
        if self.status is not ConfirmationStatus.UNKNOWN and self.unit is None:
            raise ValueError(f"status {self.status.value!r} requires a unit")
        return self

    @property
    def confirmed(self) -> bool:
        return self.status is ConfirmationStatus.USER_CONFIRMED
