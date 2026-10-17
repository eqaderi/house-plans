"""Coordinate reference systems through pyproj/PROJ.

Only codes a human typed or a file declared are looked up here; nothing in
this module chooses a CRS. :func:`utm_candidates` lists every EPSG CRS for a
UTM zone so a human can pick the datum: a zone number alone does not fix
the datum (WGS 84, ETRS89, NAD83, ... share zone numbers).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pyproj import CRS, Transformer
from pyproj.database import query_crs_info
from pyproj.enums import PJType
from pyproj.exceptions import CRSError


class CrsValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CrsInfo:
    epsg: int
    name: str
    kind: str
    #: Linear unit of the first axis, e.g. "metre".
    unit: str | None
    datum: str | None
    #: e.g. "32N" for a UTM CRS, else None.
    utm_zone: str | None
    #: Area of use in degrees: west, south, east, north.
    area_of_use: tuple[float, float, float, float] | None


def describe_epsg(epsg: int) -> CrsInfo:
    try:
        crs = CRS.from_epsg(epsg)
    except CRSError as exc:
        raise CrsValidationError(f"EPSG:{epsg} is not in the PROJ database: {exc}") from exc
    aou = crs.area_of_use
    return CrsInfo(
        epsg=epsg,
        name=crs.name,
        kind=crs.type_name,
        unit=crs.axis_info[0].unit_name if crs.axis_info else None,
        datum=crs.datum.name if crs.datum else None,
        utm_zone=crs.utm_zone,
        area_of_use=(aou.west, aou.south, aou.east, aou.north) if aou else None,
    )


def require_projected_metric(epsg: int) -> CrsInfo:
    """A horizontal CRS the site model can use: projected, axes in metres."""
    info = describe_epsg(epsg)
    crs = CRS.from_epsg(epsg)
    if not crs.is_projected:
        raise CrsValidationError(
            f"EPSG:{epsg} ({info.name}) is {info.kind}, not a projected CRS; the site model "
            "needs easting/northing"
        )
    if info.unit not in ("metre", "meter"):
        raise CrsValidationError(
            f"EPSG:{epsg} ({info.name}) has axes in {info.unit}; only metre-based CRSs are "
            "supported so that GRID coordinates equal CRS coordinates"
        )
    return info


def require_vertical(epsg: int) -> CrsInfo:
    info = describe_epsg(epsg)
    if not CRS.from_epsg(epsg).is_vertical:
        raise CrsValidationError(f"EPSG:{epsg} ({info.name}) is {info.kind}, not a vertical CRS")
    return info


def utm_candidates(zone: int, hemisphere: str) -> list[CrsInfo]:
    """Every EPSG projected CRS named "... UTM zone <zone><N|S>"."""
    if not 1 <= zone <= 60:
        raise CrsValidationError(f"UTM zone must be 1-60, got {zone}")
    hemi = hemisphere.upper()
    if hemi not in ("N", "S"):
        raise CrsValidationError(f"hemisphere must be N or S, got {hemisphere!r}")
    suffix = f"UTM zone {zone}{hemi}"
    codes = {
        int(info.code)
        for info in query_crs_info(auth_name="EPSG", pj_types=PJType.PROJECTED_CRS)
        if info.name.endswith(suffix) and not info.deprecated
    }
    return [describe_epsg(code) for code in sorted(codes)]


def grid_to_lonlat(epsg: int, easting: float, northing: float) -> tuple[float, float]:
    crs = CRS.from_epsg(epsg)
    to_geo = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
    lon, lat = to_geo.transform(easting, northing)
    return float(lon), float(lat)


def grid_to_true_north_deg(epsg: int, easting: float, northing: float) -> float:
    """Clockwise angle from grid north to true north at a grid point, in degrees.

    Computed numerically, not from a sign convention: project a short step
    north along the meridian through the point and measure its direction in
    the grid. East of a UTM central meridian (northern hemisphere) true north
    lies counter-clockwise of grid north, so the result is negative there.
    """
    crs = CRS.from_epsg(epsg)
    to_geo = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
    to_grid = Transformer.from_crs(crs.geodetic_crs, crs, always_xy=True)
    lon, lat = to_geo.transform(easting, northing)
    e1, n1 = to_grid.transform(lon, lat)
    e2, n2 = to_grid.transform(lon, lat + 1e-4)
    return math.degrees(math.atan2(e2 - e1, n2 - n1))


def inside_area_of_use(info: CrsInfo, lon: float, lat: float) -> bool | None:
    """Whether a point lies in the CRS's published area of use (None if unknown)."""
    if info.area_of_use is None:
        return None
    west, south, east, north = info.area_of_use
    in_lon = west <= lon <= east if west <= east else (lon >= west or lon <= east)
    return in_lon and south <= lat <= north
