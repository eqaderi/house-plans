"""Units, CRS status rules and the local project frame."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from house_ai.domain.coordinates import HorizontalCRS, LocalCoordinateSystem, VerticalDatum
from house_ai.domain.epistemics import ConfirmationStatus
from house_ai.domain.site import Site, site_verification_blockers
from house_ai.domain.units import (
    LengthUnit,
    UnitDeclaration,
    convert,
    to_metres,
    unit_from_insunits,
)

C = ConfirmationStatus


@pytest.mark.parametrize(
    ("value", "unit", "metres"),
    [
        (1500, LengthUnit.MILLIMETRE, 1.5),
        (250, LengthUnit.CENTIMETRE, 2.5),
        (3, LengthUnit.METRE, 3.0),
        (10, LengthUnit.FOOT, 3.048),
        (12, LengthUnit.INCH, 0.3048),
        (3937, LengthUnit.US_SURVEY_FOOT, 1200.0),
        (1, LengthUnit.KILOMETRE, 1000.0),
    ],
)
def test_to_metres(value, unit, metres):
    assert to_metres(value, unit) == pytest.approx(metres, abs=1e-12)


def test_convert_round_trip():
    for unit in LengthUnit:
        assert convert(convert(12.345, LengthUnit.METRE, unit), unit, LengthUnit.METRE) == (
            pytest.approx(12.345, rel=1e-12)
        )


def test_us_survey_foot_differs_from_international_foot():
    # 2 ppm: ~2 m over a 1,000 km UTM easting. Never interchangeable.
    diff = to_metres(1_000_000, LengthUnit.US_SURVEY_FOOT) - to_metres(1_000_000, LengthUnit.FOOT)
    assert diff == pytest.approx(0.6096, abs=1e-4)


@pytest.mark.parametrize(
    ("code", "unit"),
    [
        (4, LengthUnit.MILLIMETRE),
        (6, LengthUnit.METRE),
        (2, LengthUnit.FOOT),
        (21, LengthUnit.US_SURVEY_FOOT),
    ],
)
def test_insunits_mapping(code, unit):
    assert unit_from_insunits(code) is unit


@pytest.mark.parametrize("code", [0, None, 99, 8])
def test_unitless_or_unsupported_insunits_is_unknown(code):
    assert unit_from_insunits(code) is None


def test_unit_declaration_rules():
    UnitDeclaration()  # unknown, no unit
    UnitDeclaration(unit=LengthUnit.METRE, status=C.DECLARED_IN_SOURCE)
    with pytest.raises(ValidationError):
        UnitDeclaration(unit=LengthUnit.METRE, status=C.UNKNOWN)
    with pytest.raises(ValidationError):
        UnitDeclaration(status=C.USER_CONFIRMED)
    with pytest.raises(ValidationError):
        UnitDeclaration(unit=LengthUnit.METRE, status=C.LOCAL_ONLY_CONFIRMED)


def test_crs_epsg_only_when_a_human_confirmed_it():
    HorizontalCRS(status=C.USER_CONFIRMED, epsg=32639)
    HorizontalCRS(status=C.DECLARED_IN_SOURCE, declared_epsg=32639)
    with pytest.raises(ValidationError, match="declared_epsg"):
        HorizontalCRS(status=C.DECLARED_IN_SOURCE, epsg=32639)
    with pytest.raises(ValidationError):
        HorizontalCRS(status=C.UNKNOWN, epsg=32639)
    with pytest.raises(ValidationError):
        HorizontalCRS(status=C.USER_CONFIRMED)
    assert not HorizontalCRS(status=C.DECLARED_IN_SOURCE, declared_epsg=32639).resolved
    assert HorizontalCRS(status=C.LOCAL_ONLY_CONFIRMED).resolved


def test_vertical_datum_needs_a_name_once_known():
    with pytest.raises(ValidationError):
        VerticalDatum(status=C.USER_CONFIRMED)
    assert VerticalDatum(status=C.LOCAL_ONLY_CONFIRMED, name="BM1").resolved


def test_utm_looking_coordinates_do_not_imply_a_crs(site_doc):
    """A 6/7-digit origin looks like UTM. That must not resolve the CRS."""
    site_doc["coordinates"]["horizontal_crs"] = {"status": "unknown"}
    site = Site.model_validate(site_doc)
    assert site.coordinates.local.origin[0] > 100_000
    blockers = site_verification_blockers(site)
    assert any("horizontal CRS is unknown" in b for b in blockers)


@pytest.mark.parametrize(
    ("patch", "expected"),
    [
        ({"source_units": {"status": "unknown"}}, "drawing units are unknown"),
        (
            {"source_units": {"unit": "mm", "status": "declared_in_source"}},
            "drawing units are declared_in_source (mm)",
        ),
        (
            {"horizontal_crs": {"status": "declared_in_source", "declared_epsg": 32632}},
            "EPSG:32632",
        ),
        ({"vertical_datum": {"status": "unknown"}}, "vertical datum is unknown"),
        ({"local": None}, "no local project coordinate system"),
    ],
)
def test_ambiguous_site_coordinates_block_approval(site_doc, patch, expected):
    site_doc["coordinates"].update(patch)
    blockers = site_verification_blockers(Site.model_validate(site_doc))
    assert any(expected in b for b in blockers), blockers


def test_golden_site_has_no_blockers(site):
    assert site_verification_blockers(site) == []


def test_unverified_boundary_and_blocking_issue_block(site_doc):
    site_doc["boundary_status"] = "assumption"
    site_doc["issues"] = [{"id": "iss-1", "title": "Boundary disputed", "severity": "blocking"}]
    blockers = site_verification_blockers(Site.model_validate(site_doc))
    assert any("boundary status is assumption" in b for b in blockers)
    assert any("Boundary disputed" in b for b in blockers)


@pytest.mark.parametrize("rotation", [0.0, 30.0, 90.0, -137.5])
def test_local_frame_round_trip(rotation):
    lcs = LocalCoordinateSystem(
        id="lcs", origin=(500123.4, 5401234.5, 812.3), rotation_deg=rotation
    )
    grid = (500150.0, 5401200.0, 815.0)
    back = lcs.local_to_grid(lcs.grid_to_local(grid))
    assert back == pytest.approx(grid, abs=1e-9)


def test_local_frame_rotation_direction():
    lcs = LocalCoordinateSystem(id="lcs", origin=(1000.0, 2000.0, 50.0), rotation_deg=90.0)
    # Local +x points to grid north when rotated 90 degrees counter-clockwise.
    x, y, z = lcs.grid_to_local((1000.0, 2010.0, 53.0))
    assert (x, y, z) == pytest.approx((10.0, 0.0, 3.0), abs=1e-9)
    assert lcs.project_north_deg == -90.0


def test_local_frame_preserves_distances():
    lcs = LocalCoordinateSystem(id="lcs", origin=(0.0, 0.0, 0.0), rotation_deg=23.0)
    a, b = (10.0, 5.0, 0.0), (40.0, -7.0, 0.0)
    la, lb = lcs.grid_to_local(a), lcs.grid_to_local(b)
    assert math.dist(la, lb) == pytest.approx(math.dist(a, b))


def test_true_north_is_unknown_until_computed(site):
    assert site.coordinates.local.grid_to_true_north_deg is None
