"""The survey-to-spec frame, the site block and the terrain model, tested
against the real survey files in derived/survey/ and numbers quoted in
docs/site.md."""

from __future__ import annotations

import math
from pathlib import Path

import ezdxf
import pytest

from houseplan.site import SurveyFrame, grid_north_true_azimuth

ROOT = Path(__file__).resolve().parents[1]
SEP = ROOT / "derived" / "survey" / "seperated.dxf"


@pytest.fixture(scope="module")
def d7():
    doc = ezdxf.readfile(SEP)
    return [(x, y) for x, y, *_ in doc.entitydb["D7"].get_points()][:-1]  # V0..V3


@pytest.fixture(scope="module")
def frame(d7):
    return SurveyFrame.along(d7[3], d7[2])  # origin V3, x towards V2


def test_frame_puts_v3_at_origin_and_v2_on_x(frame, d7):
    assert frame.to_spec(*d7[3]) == pytest.approx((0, 0), abs=1e-6)
    x, y = frame.to_spec(*d7[2])
    assert x == pytest.approx(32570, abs=1) and y == pytest.approx(0, abs=1e-6)


def test_frame_y_runs_into_the_plot(frame, d7):
    # docs/site.md: north to south side 18.422 m
    for v in (d7[0], d7[1]):
        assert frame.to_spec(*v)[1] == pytest.approx(18422, abs=1)


def test_frame_round_trip(frame, d7):
    for v in d7:
        assert frame.to_survey(*frame.to_spec(*v)) == pytest.approx(v, abs=1e-9)


def test_frame_axis_azimuth(frame):
    # docs/site.md: V2->V3 azimuth 247.19, so V3->V2 is 67.19
    assert frame.x_azimuth_deg == pytest.approx(67.19, abs=0.005)


def test_north_angle_is_true_bearing_of_spec_y(frame, d7):
    # docs/site.md: grid north is 0.778 deg east of true north, and the north
    # side V0->V1 faces true 337.97. The north side is parallel to spec x, so
    # its outward normal is spec +y.
    # (measured at the plot centroid, as scripts/measure_site.py does)
    centroid = (sum(v[0] for v in d7) / 4, sum(v[1] for v in d7) / 4)
    c = grid_north_true_azimuth(*centroid)
    assert c == pytest.approx(0.778, abs=0.0005)
    assert frame.north_angle_deg(c) == pytest.approx(337.97, abs=0.005)


def test_north_angle_convention_in_family_and_drawing():
    """north_angle_deg is the true bearing of spec +y: a window facing +y
    faces exactly that bearing, and the north arrow points to true north."""
    import yaml

    from houseplan import geometry
    from houseplan.drawing import _north
    from houseplan.family import _window_bearings
    from houseplan.model import Design

    spec = yaml.safe_load((ROOT / "design" / "examples" / "bungalow.yaml").read_text(encoding="utf-8"))
    design = Design.model_validate(spec)
    lg = geometry.build(design)["GF"]
    # F1 sits in the south wall WS, so it faces spec -y: true 337.97 - 180
    assert 157.97 in [round(b, 2) for b in _window_bearings(lg, "R1", 337.97)]

    doc = ezdxf.new()
    _north(doc.modelspace(), (0, 0), 1, 337.97)
    tip = doc.modelspace().query("LWPOLYLINE")[0].get_points()[0]
    # true north is 22.03 deg clockwise of spec +y on the sheet
    assert math.degrees(math.atan2(tip[0], tip[1])) == pytest.approx(22.03, abs=0.01)
