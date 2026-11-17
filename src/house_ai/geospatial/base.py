"""Geospatial and terrain boundary (Milestone B).

Implements the explicit human-confirmed CRS and local-frame operations required
by MASTER_SPEC.md, keeping coordinate reference system logic separate from raw
CAD parsing.
"""

from __future__ import annotations

from house_ai.domain.coordinates import HorizontalCRS
from house_ai.domain.epistemics import ConfirmationStatus
from house_ai.domain.provenance import Actor, refuse_non_human
from house_ai.domain.site import Contour, SpotElevation, Terrain, TerrainStatus, TinSurface

from .crs import describe_epsg, require_projected_metric


def set_coordinate_reference_system(
    *,
    actor: Actor,
    status: ConfirmationStatus,
    epsg: int | None = None,
    declared_epsg: int | None = None,
    name: str | None = None,
) -> HorizontalCRS:
    """Record or confirm the horizontal CRS of a site.

    Only a human actor may set ``USER_CONFIRMED`` or ``LOCAL_ONLY_CONFIRMED``.
    A confirmed code must exist in the PROJ database and be a projected,
    metre-based CRS; its official name is filled in when none is given.
    """
    if status in (ConfirmationStatus.USER_CONFIRMED, ConfirmationStatus.LOCAL_ONLY_CONFIRMED):
        refuse_non_human(actor, "confirm the coordinate reference system")
    if status is ConfirmationStatus.USER_CONFIRMED and epsg is not None:
        name = name or require_projected_metric(epsg).name
    elif declared_epsg is not None and name is None:
        name = describe_epsg(declared_epsg).name
    return HorizontalCRS(status=status, epsg=epsg, declared_epsg=declared_epsg, name=name)


def build_terrain(
    spot_elevations: list[SpotElevation],
    contours: list[Contour],
    *,
    surface_ref: str | None = None,
    surface: TinSurface | None = None,
) -> Terrain:
    """Assemble local-frame elevation data into a canonical Terrain record."""
    if surface_ref is not None or surface is not None:
        status = TerrainStatus.SURFACE_BUILT
    elif spot_elevations or contours:
        status = TerrainStatus.SURVEYED_POINTS
    else:
        status = TerrainStatus.UNKNOWN
    return Terrain(
        status=status,
        spot_elevations=spot_elevations,
        contours=contours,
        surface_ref=surface_ref,
        surface=surface,
    )
