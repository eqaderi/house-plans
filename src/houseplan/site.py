"""The survey-to-spec transform.

Survey coordinates (eastings and northings in metres, on a projected grid)
never go into the spec. The spec frame is a rigid rotation and shift of the
survey grid: origin at a chosen survey point, +x along a chosen direction, +y
90 degrees counter-clockwise from it, lengths in millimetres. This module is
the only place that converts between the two.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MM_PER_M = 1000.0


@dataclass(frozen=True)
class SurveyFrame:
    """origin: survey (E, N) in metres of spec (0, 0).
    x_azimuth_deg: grid azimuth (clockwise from grid north) of spec +x."""

    origin_e: float
    origin_n: float
    x_azimuth_deg: float

    @classmethod
    def along(cls, origin: tuple[float, float], toward: tuple[float, float]) -> SurveyFrame:
        """Origin at `origin`, +x pointing at `toward`."""
        az = math.degrees(math.atan2(toward[0] - origin[0], toward[1] - origin[1])) % 360
        return cls(origin[0], origin[1], az)

    @property
    def _u(self) -> tuple[float, float]:
        a = math.radians(self.x_azimuth_deg)
        return math.sin(a), math.cos(a)  # (east, north) components of +x

    def to_spec(self, e: float, n: float) -> tuple[float, float]:
        """Survey (E, N) metres to spec (x, y) millimetres."""
        ue, un = self._u
        de, dn = e - self.origin_e, n - self.origin_n
        return (de * ue + dn * un) * MM_PER_M, (-de * un + dn * ue) * MM_PER_M

    def to_survey(self, x: float, y: float) -> tuple[float, float]:
        """Spec (x, y) millimetres to survey (E, N) metres."""
        ue, un = self._u
        x, y = x / MM_PER_M, y / MM_PER_M
        return self.origin_e + x * ue - y * un, self.origin_n + x * un + y * ue

    def north_angle_deg(self, grid_north_true_az: float) -> float:
        """True bearing of spec +y: the value of project.north_angle_deg.
        grid_north_true_az is the true azimuth of grid north at the site."""
        return (self.x_azimuth_deg - 90 + grid_north_true_az) % 360


def grid_north_true_azimuth(e: float, n: float, epsg: int = 32638) -> float:
    """True azimuth of grid north at a survey point (the negative of the
    meridian convergence's sense), measured geodesically with pyproj."""
    from pyproj import Geod, Transformer

    to_geo = Transformer.from_crs(epsg, 4326, always_xy=True)
    lon, lat = to_geo.transform(e, n)
    lon_n, lat_n = to_geo.transform(e, n + 100)
    return Geod(ellps="WGS84").inv(lon, lat, lon_n, lat_n)[0] % 360
