"""Coordinate transforms, CRS handling, terrain and parcel measurements (Milestone B)."""

from __future__ import annotations

import math

import pytest
from pyproj import CRS, Proj, Transformer

from house_ai.domain.coordinates import LocalCoordinateSystem, SurveyTransform
from house_ai.domain.epistemics import ConfirmationStatus as C
from house_ai.domain.geometry import Polygon2D, Polyline2D
from house_ai.domain.site import (
    Contour,
    PolygonGeometry,
    SiteFeature,
    SiteFeatureKind,
    SpotElevation,
    Terrain,
    TerrainStatus,
)
from house_ai.domain.units import METRES_PER_UNIT, LengthUnit
from house_ai.geospatial.base import set_coordinate_reference_system
from house_ai.geospatial.crs import (
    CrsValidationError,
    grid_to_lonlat,
    grid_to_true_north_deg,
    require_projected_metric,
    require_vertical,
    utm_candidates,
)
from house_ai.geospatial.parcel import derive_frontage, parcel_metrics
from house_ai.geospatial.terrain import (
    build_tin,
    contour_interval,
    crossing_contours,
    elevation_at,
    triangle_slope_pct,
)

from .conftest import AGENT, HUMAN

# ------------------------------------------------------------------ transforms


@pytest.mark.parametrize("rotation", [0.0, 17.5, -90.0, 133.0])
@pytest.mark.parametrize(
    "unit", [LengthUnit.METRE, LengthUnit.MILLIMETRE, LengthUnit.US_SURVEY_FOOT]
)
def test_survey_transform_round_trips_large_coordinates(rotation, unit):
    k = METRES_PER_UNIT[unit]
    local = LocalCoordinateSystem(
        id="lcs", origin=(612_345.678, 5_432_109.876, 250.0), rotation_deg=rotation
    )
    t = SurveyTransform(k, k, local)
    for source in [
        (612_345.678 / k, 5_432_109.876 / k, 250.0 / k),
        (612_400.1 / k, 5_432_050.2 / k, 263.4 / k),
    ]:
        back = t.local_to_source(t.source_to_local(source))
        assert math.dist(back, source) * k < 1e-6  # sub-micrometre after a full round trip
    origin_local = t.source_to_local((612_345.678 / k, 5_432_109.876 / k, 250.0 / k))
    assert math.dist(origin_local, (0.0, 0.0, 0.0)) < 1e-6


def test_local_frame_keeps_coordinates_small_and_rotates_correctly():
    local = LocalCoordinateSystem(id="lcs", origin=(500_000.0, 5_400_000.0, 0.0), rotation_deg=90.0)
    t = SurveyTransform(1.0, 1.0, local)
    # A point 10 m grid-north of the origin lies on local -x when local x points grid north.
    x, y, z = t.source_to_local((500_000.0, 5_400_010.0, 101.0))
    assert (x, y, z) == pytest.approx((10.0, 0.0, 101.0), abs=1e-9)
    assert t.source_to_local_2d((500_010.0, 5_400_000.0)) == pytest.approx((0.0, -10.0), abs=1e-9)


def test_separate_elevation_unit():
    t = SurveyTransform(0.001, 1.0, LocalCoordinateSystem(id="lcs", origin=(0.0, 0.0, 0.0)))
    assert t.source_to_local((1000.0, 2000.0, 101.5)) == pytest.approx((1.0, 2.0, 101.5))


def test_transform_rejects_non_positive_scale():
    with pytest.raises(ValueError):
        SurveyTransform(0.0, 1.0, LocalCoordinateSystem(id="lcs", origin=(0.0, 0.0, 0.0)))


# ------------------------------------------------------------------------- CRS


def test_true_north_is_computed_numerically_and_matches_proj():
    e, n = 600_000.0, 5_400_000.0  # 100 km east of the UTM 32N central meridian
    angle = grid_to_true_north_deg(25832, e, n)
    lon, lat = grid_to_lonlat(25832, e, n)
    convergence = Proj(CRS.from_epsg(25832)).get_factors(lon, lat).meridian_convergence
    # Same magnitude as PROJ's meridian convergence; east of the meridian true
    # north lies counter-clockwise of grid north, so the clockwise angle is negative.
    assert angle == pytest.approx(-convergence, abs=1e-6)
    assert angle < 0
    assert grid_to_true_north_deg(25832, 400_000.0, n) > 0
    assert abs(grid_to_true_north_deg(25832, 500_000.0, n)) < 1e-7


def test_grid_to_lonlat_matches_pyproj():
    to_geo = Transformer.from_crs(25832, 4258, always_xy=True)
    assert grid_to_lonlat(25832, 500_100.0, 5_400_200.0) == pytest.approx(
        to_geo.transform(500_100.0, 5_400_200.0), abs=1e-12
    )


def test_utm_zone_lists_every_datum_and_picks_none():
    codes = {c.epsg for c in utm_candidates(32, "N")}
    assert {25832, 32632, 23032} <= codes  # ETRS89, WGS 84, ED50
    assert 32633 not in codes and 32732 not in codes
    assert all(c.utm_zone == "32N" for c in utm_candidates(32, "N"))
    with pytest.raises(CrsValidationError):
        utm_candidates(61, "N")


def test_only_projected_metre_crs_are_accepted():
    assert require_projected_metric(25832).name == "ETRS89 / UTM zone 32N"
    with pytest.raises(CrsValidationError, match="not a projected"):
        require_projected_metric(4326)
    with pytest.raises(CrsValidationError, match="axes in"):
        require_projected_metric(2263)  # NAD83 / New York Long Island (ftUS)
    with pytest.raises(CrsValidationError, match="not in the PROJ database"):
        require_projected_metric(999_999)


def test_vertical_crs_validation():
    assert require_vertical(7837).name == "DHHN2016 height"
    with pytest.raises(CrsValidationError, match="not a vertical"):
        require_vertical(25832)


def test_only_a_human_confirms_and_codes_are_validated():
    with pytest.raises(ValueError, match="only a human"):
        set_coordinate_reference_system(actor=AGENT, status=C.USER_CONFIRMED, epsg=25832)
    crs = set_coordinate_reference_system(actor=HUMAN, status=C.USER_CONFIRMED, epsg=25832)
    assert crs.name == "ETRS89 / UTM zone 32N"
    with pytest.raises(CrsValidationError):
        set_coordinate_reference_system(actor=HUMAN, status=C.USER_CONFIRMED, epsg=4326)


# --------------------------------------------------------------------- terrain


def _plane(x: float, y: float) -> float:
    return 100.0 + 0.05 * x + 0.1 * y


def _plane_survey():
    spots = [
        SpotElevation(id=f"s{i}", xy=(x, y), z_m=_plane(x, y))
        for i, (x, y) in enumerate([(0, 0), (40, 0), (40, 30), (10, 40), (0, 30), (20, 15)])
    ]
    contours = [
        Contour(
            id=f"c{int(level)}",
            z_m=level,
            line=Polyline2D(points=[(x, 10 * (level - 100) - 0.5 * x) for x in (-5.0, 20.0, 45.0)]),
        )
        for level in (101.0, 102.0, 103.0)
    ]
    return spots, contours


def test_tin_reproduces_a_planar_survey_exactly():
    spots, contours = _plane_survey()
    tin = build_tin(spots, contours)
    assert tin.conflicts == [] and tin.surface is not None
    assert len(tin.surface.vertices) == 6 + 9
    for x in range(1, 40, 3):
        for y in range(1, 30, 3):
            assert elevation_at(tin.surface, (x, y)) == pytest.approx(_plane(x, y), abs=1e-9)
    for ia, ib, ic in tin.surface.triangles:
        a, b, c = (tin.surface.vertices[i] for i in (ia, ib, ic))
        assert triangle_slope_pct(a, b, c) == pytest.approx(100 * math.hypot(0.05, 0.1))


def test_no_elevation_is_invented_outside_the_survey():
    spots, contours = _plane_survey()
    surface = build_tin(spots, contours).surface
    assert elevation_at(surface, (100.0, 100.0)) is None
    assert elevation_at(surface, (-50.0, 0.0)) is None


def test_tin_refuses_conflicting_elevations():
    spots, contours = _plane_survey()
    spots.append(SpotElevation(id="dup", xy=(20.0, 15.0), z_m=90.0))
    tin = build_tin(spots, contours)
    assert tin.surface is None and "dup" in tin.conflicts[0]


def test_tin_needs_three_non_collinear_points():
    line = [SpotElevation(id=f"s{i}", xy=(float(i), 0.0), z_m=100.0) for i in range(4)]
    assert build_tin(line, []).surface is None
    assert build_tin(line[:2], []).surface is None


def test_contour_checks():
    _, contours = _plane_survey()
    assert contour_interval(contours) == 1.0
    assert crossing_contours(contours) == []
    rogue = Contour(id="rogue", z_m=150.0, line=Polyline2D(points=[(0.0, -20.0), (0.0, 40.0)]))
    assert {pair[1] for pair in crossing_contours([*contours, rogue])} == {"rogue"}
    assert contour_interval([*contours, rogue]) is None


def test_surface_built_status_requires_a_surface():
    with pytest.raises(ValueError, match="needs a surface"):
        Terrain(status=TerrainStatus.SURFACE_BUILT)


# ---------------------------------------------------------------------- parcel


PARCEL = Polygon2D(outer=[(0, 0), (40, 0), (40, 30), (10, 40), (0, 30)])


def test_parcel_dimensions_area_and_bearings():
    local = LocalCoordinateSystem(
        id="lcs", origin=(0.0, 0.0, 0.0), rotation_deg=0.0, grid_to_true_north_deg=-1.0
    )
    m = parcel_metrics(PARCEL, local, grid_north_known=True)
    assert m.area_m2 == pytest.approx(1400.0)
    assert m.perimeter_m == pytest.approx(40 + 30 + math.sqrt(1000) + math.sqrt(200) + 30)
    assert [round(e.length_m, 6) for e in m.edges] == [
        40.0,
        30.0,
        round(math.sqrt(1000), 6),
        round(math.sqrt(200), 6),
        30.0,
    ]
    assert m.edges[0].bearing_local_deg == pytest.approx(90.0)
    assert m.edges[1].bearing_local_deg == pytest.approx(0.0)
    # true bearing = grid bearing - (clockwise grid-to-true-north angle)
    assert m.edges[1].bearing_true_deg == pytest.approx(1.0)
    assert m.is_ccw and m.vertex_count == 5


def test_bearings_follow_the_local_rotation():
    local = LocalCoordinateSystem(id="lcs", origin=(0.0, 0.0, 0.0), rotation_deg=30.0)
    m = parcel_metrics(PARCEL, local, grid_north_known=True)
    # Local +y points 30° counter-clockwise of grid north.
    assert m.edges[1].bearing_grid_deg == pytest.approx(330.0)
    assert m.edges[1].bearing_true_deg is None  # true north not computed
    unconfirmed = parcel_metrics(PARCEL, local, grid_north_known=False)
    assert unconfirmed.edges[1].bearing_grid_deg is None


def _road(outer) -> SiteFeature:
    return SiteFeature(
        id="road-1",
        kind=SiteFeatureKind.ROAD,
        geometry=PolygonGeometry(polygon=Polygon2D(outer=outer)),
    )


def test_frontage_is_the_boundary_along_roads_only():
    frontage = derive_frontage(PARCEL, [_road([(-10, -8), (50, -8), (50, 0), (-10, 0)])])
    assert [f.id for f in frontage] == ["frontage-e0"]
    assert frontage[0].geometry.line.length_m == pytest.approx(40.0)
    assert frontage[0].status.value == "inference"


def test_no_road_means_no_frontage():
    assert derive_frontage(PARCEL, []) == []
    far = _road([(-10, -30), (50, -30), (50, -20), (-10, -20)])
    assert derive_frontage(PARCEL, [far]) == []
