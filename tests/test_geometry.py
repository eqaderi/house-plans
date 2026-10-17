"""Polygon validity and area calculations."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from house_ai.domain.geometry import Polygon2D, Polyline2D


def test_rectangle_area():
    assert Polygon2D.rectangle(10, 12, 16, 17).area_m2 == pytest.approx(30.0)


def test_l_shape_area():
    poly = Polygon2D(outer=[(0, 0), (6, 0), (6, 3), (3, 3), (3, 5), (0, 5)])
    assert poly.area_m2 == pytest.approx(6 * 3 + 3 * 2)


def test_courtyard_hole_is_subtracted():
    poly = Polygon2D(
        outer=[(0, 0), (20, 0), (20, 20), (0, 20)],
        holes=[[(5, 5), (15, 5), (15, 15), (5, 15)]],
    )
    assert poly.area_m2 == pytest.approx(400 - 100)


def test_closing_point_is_normalised_away():
    poly = Polygon2D(outer=[(0, 0), (4, 0), (4, 3), (0, 3), (0, 0)])
    assert len(poly.outer) == 4
    assert poly == Polygon2D.rectangle(0, 0, 4, 3)


def test_orientation_does_not_change_area():
    cw = Polygon2D(outer=[(0, 0), (0, 3), (4, 3), (4, 0)])
    assert cw.area_m2 == pytest.approx(12.0)


@pytest.mark.parametrize(
    "outer",
    [
        [(0, 0), (4, 4), (4, 0), (0, 4)],  # bow-tie, self-intersecting
        [(0, 0), (1, 0), (2, 0)],  # collinear, zero area
        [(0, 0), (1, 0)],  # too few points
    ],
)
def test_invalid_polygons_are_rejected(outer):
    with pytest.raises(ValidationError):
        Polygon2D(outer=outer)


def test_hole_outside_outer_is_rejected():
    with pytest.raises(ValidationError, match="invalid polygon"):
        Polygon2D(outer=[(0, 0), (4, 0), (4, 4), (0, 4)], holes=[[(5, 5), (6, 5), (6, 6)]])


def test_polyline_length():
    assert Polyline2D(points=[(0, 0), (3, 4)]).length_m == pytest.approx(5.0)
    assert Polyline2D(points=[(0, 0), (3, 0), (3, 4)], closed=True).length_m == pytest.approx(12.0)


def test_oriented_polygon_normalises_winding():
    cw_outer = Polygon2D(
        outer=[(0, 0), (0, 10), (10, 10), (10, 0)],
        holes=[[(2, 2), (8, 2), (8, 8), (2, 8)]],  # CCW hole
    )
    ccw_outer = Polygon2D(
        outer=[(0, 0), (10, 0), (10, 10), (0, 10)],
        holes=[[(2, 2), (2, 8), (8, 8), (8, 2)]],  # CW hole
    )
    assert cw_outer.oriented().area_m2 == pytest.approx(ccw_outer.area_m2)
    assert cw_outer.oriented().to_shapely().exterior.is_ccw
    assert not cw_outer.oriented().to_shapely().interiors[0].is_ccw


def test_rotated_rectangle():
    r0 = Polygon2D.rotated_rectangle((5.0, 5.0), 2.0, 4.0, rotation_deg=0.0)
    r90 = Polygon2D.rotated_rectangle((5.0, 5.0), 2.0, 4.0, rotation_deg=90.0)
    assert r0.area_m2 == pytest.approx(8.0)
    assert r90.area_m2 == pytest.approx(8.0)
    assert r0.bounds == pytest.approx((4.0, 3.0, 6.0, 7.0))
    assert r90.bounds == pytest.approx((3.0, 4.0, 7.0, 6.0))

