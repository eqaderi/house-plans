"""Coordinate reference systems and the local project frame.

Three frames are distinguished:

* SOURCE: raw drawing coordinates in drawing units.
* GRID: source coordinates scaled to metres. When the horizontal CRS is
  confirmed, GRID coordinates are easting/northing in that CRS.
* LOCAL: the project frame used by the canonical model. Metres, origin near
  the site, x axis rotated ``rotation_deg`` counter-clockwise from grid east,
  z measured from ``origin`` elevation.

The CRS is never inferred from coordinate magnitudes. A large 6-7 digit
coordinate looks like UTM but proves nothing; only the source file or a human
can state the CRS, and only a human can confirm it.
"""

from __future__ import annotations

import math

from pydantic import Field, model_validator

from .base import Id, StrictModel
from .epistemics import ConfirmationStatus
from .geometry import Point2, Point3
from .units import UnitDeclaration


class HorizontalCRS(StrictModel):
    status: ConfirmationStatus = ConfirmationStatus.UNKNOWN
    #: Set only once a human has confirmed the CRS.
    epsg: int | None = Field(default=None, ge=1024, le=999999)
    #: What the source file declares, pending confirmation.
    declared_epsg: int | None = Field(default=None, ge=1024, le=999999)
    name: str | None = None

    @model_validator(mode="after")
    def _epsg_only_when_confirmed(self) -> HorizontalCRS:
        if self.status is ConfirmationStatus.USER_CONFIRMED:
            if self.epsg is None:
                raise ValueError("a confirmed CRS needs an EPSG code")
        elif self.epsg is not None:
            raise ValueError(
                "epsg may only be set when status is 'user_confirmed'; "
                "use declared_epsg for an unconfirmed value"
            )
        if self.status is ConfirmationStatus.DECLARED_IN_SOURCE and self.declared_epsg is None:
            raise ValueError("status 'declared_in_source' needs declared_epsg")
        return self

    @property
    def resolved(self) -> bool:
        return self.status in (
            ConfirmationStatus.USER_CONFIRMED,
            ConfirmationStatus.LOCAL_ONLY_CONFIRMED,
        )


class VerticalDatum(StrictModel):
    status: ConfirmationStatus = ConfirmationStatus.UNKNOWN
    #: e.g. "EGM2008 height", "local benchmark BM1".
    name: str | None = None
    epsg: int | None = Field(default=None, ge=1024, le=999999)

    @model_validator(mode="after")
    def _name_when_known(self) -> VerticalDatum:
        if self.status is not ConfirmationStatus.UNKNOWN and not self.name:
            raise ValueError(f"vertical datum status {self.status.value!r} needs a name")
        return self

    @property
    def resolved(self) -> bool:
        return self.status in (
            ConfirmationStatus.USER_CONFIRMED,
            ConfirmationStatus.LOCAL_ONLY_CONFIRMED,
        )


class LocalCoordinateSystem(StrictModel):
    """Rigid transform between GRID metres and the LOCAL project frame."""

    id: Id
    name: str | None = None
    #: Origin of the local frame in GRID coordinates (metres): easting, northing, elevation.
    origin: Point3
    #: Counter-clockwise rotation of the local x axis from grid east, in degrees.
    rotation_deg: float = 0.0
    #: Angle from grid north to true north, degrees clockwise. UNKNOWN (None)
    #: until computed from a confirmed CRS (meridian convergence).
    grid_to_true_north_deg: float | None = None

    def grid_to_local(self, point: Point3) -> Point3:
        dx = point[0] - self.origin[0]
        dy = point[1] - self.origin[1]
        c, s = math.cos(math.radians(self.rotation_deg)), math.sin(math.radians(self.rotation_deg))
        return (c * dx + s * dy, -s * dx + c * dy, point[2] - self.origin[2])

    def local_to_grid(self, point: Point3) -> Point3:
        c, s = math.cos(math.radians(self.rotation_deg)), math.sin(math.radians(self.rotation_deg))
        x, y = point[0], point[1]
        return (
            self.origin[0] + c * x - s * y,
            self.origin[1] + s * x + c * y,
            point[2] + self.origin[2],
        )

    def grid_to_local_2d(self, point: Point2) -> Point2:
        x, y, _ = self.grid_to_local((point[0], point[1], self.origin[2]))
        return (x, y)

    @property
    def project_north_deg(self) -> float:
        """Angle of local +y from grid north, degrees clockwise."""
        return -self.rotation_deg


class SiteCoordinates(StrictModel):
    source_units: UnitDeclaration = Field(default_factory=UnitDeclaration)
    #: Unit of source elevations (z values). DXF uses the drawing unit for z,
    #: but surveys sometimes mix units, so it is declared and confirmed separately.
    elevation_units: UnitDeclaration = Field(default_factory=UnitDeclaration)
    horizontal_crs: HorizontalCRS = Field(default_factory=HorizontalCRS)
    vertical_datum: VerticalDatum = Field(default_factory=VerticalDatum)
    #: None until a local frame has been created for the site.
    local: LocalCoordinateSystem | None = None


class SurveyTransform:
    """The reversible chain SOURCE -> GRID -> LOCAL for one survey.

    SOURCE -> GRID multiplies horizontal coordinates by ``horizontal_m``
    (metres per drawing unit) and elevations by ``vertical_m``; there is no
    offset or rotation, so GRID easting/northing are the source numbers in
    metres. GRID -> LOCAL is the rigid transform of ``local``. Every step is
    exactly invertible, and LOCAL keeps coordinates small (origin near the
    site) so later Blender/Unreal stages do not lose float precision.
    """

    def __init__(self, horizontal_m: float, vertical_m: float, local: LocalCoordinateSystem):
        if horizontal_m <= 0 or vertical_m <= 0:
            raise ValueError("unit scale factors must be positive")
        self.horizontal_m = horizontal_m
        self.vertical_m = vertical_m
        self.local = local

    def source_to_grid(self, point: Point3) -> Point3:
        h, v = self.horizontal_m, self.vertical_m
        return (point[0] * h, point[1] * h, point[2] * v)

    def grid_to_source(self, point: Point3) -> Point3:
        h, v = self.horizontal_m, self.vertical_m
        return (point[0] / h, point[1] / h, point[2] / v)

    def source_to_local(self, point: Point3) -> Point3:
        return self.local.grid_to_local(self.source_to_grid(point))

    def local_to_source(self, point: Point3) -> Point3:
        return self.grid_to_source(self.local.local_to_grid(point))

    def source_to_local_2d(self, point: Point2) -> Point2:
        x, y = point[0] * self.horizontal_m, point[1] * self.horizontal_m
        return self.local.grid_to_local_2d((x, y))

    def local_to_source_2d(self, point: Point2) -> Point2:
        e, n, _ = self.local.local_to_grid((point[0], point[1], 0.0))
        return (e / self.horizontal_m, n / self.horizontal_m)
