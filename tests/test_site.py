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


# --- site block and containment (phase 2) -----------------------------------

import copy  # noqa: E402

import yaml  # noqa: E402

from houseplan import checks, geometry, model  # noqa: E402
from houseplan.model import Design  # noqa: E402

EXAMPLE = ROOT / "design" / "examples" / "bungalow.yaml"
SITE = ROOT / "derived" / "site" / "d7.yaml"


@pytest.fixture
def spec() -> dict:
    s = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    # the bungalow's outer wall faces run from -150 to 12150 and -150 to 9150
    s["site"] = {
        "source": "test",
        "boundary": [[-1000, -1000], [20000, -1000], [20000, 20000], [-1000, 20000]],
        "no_build": [{"name": "south strip", "outline": [[-1000, -1000], [20000, -1000], [20000, -500], [-1000, -500]]}],
    }
    return s


def site_findings(spec):
    design = Design.model_validate(spec)
    geo = geometry.build(design)
    return {(f.code, f.severity) for f in checks.check_site(design, geo)}


def test_site_clean_when_inside(spec):
    assert site_findings(spec) == set()


def test_no_site_is_reported_not_passed(spec):
    del spec["site"]
    assert site_findings(spec) == {("SITE_NOT_SET", "info")}


def test_footprint_outside_boundary(spec):
    spec["site"]["boundary"] = [[0, -1000], [20000, -1000], [20000, 20000], [0, 20000]]
    assert ("SITE_OUTSIDE_BOUNDARY", "error") in site_findings(spec)


def test_wall_face_on_boundary_is_allowed(spec):
    # the brief lets a wall stand directly on the road line
    spec["site"]["boundary"] = [[-150, -1000], [20000, -1000], [20000, 20000], [-150, 20000]]
    assert site_findings(spec) == set()


def test_footprint_in_no_build_strip(spec):
    spec["site"]["no_build"][0]["outline"] = [[-1000, -1000], [20000, -1000], [20000, 0], [-1000, 0]]
    assert ("SITE_IN_NO_BUILD", "error") in site_findings(spec)


def test_wall_face_on_strip_line_is_allowed(spec):
    spec["site"]["no_build"][0]["outline"] = [[-1000, -1000], [20000, -1000], [20000, -150], [-1000, -150]]
    assert site_findings(spec) == set()


def test_upper_level_counts_too(spec):
    spec["levels"].append({"id": "L1", "name": "First floor", "ffl": 3200, "floor_to_floor": 3000, "slab": 350})
    spec["walls"].append({"id": "UX", "level": "L1", "start": [0, -2000], "end": [0, 0], "thickness": 300, "kind": "exterior"})
    assert ("SITE_IN_NO_BUILD", "error") in site_findings(spec)


def test_site_survey_coordinates_rejected(spec):
    spec["site"]["boundary"][0] = [623809167, 3870456033]
    with pytest.raises(ValueError, match="survey coordinates"):
        Design.model_validate(spec)


def test_site_file_is_loaded_by_reference(spec, tmp_path):
    (tmp_path / "site.yaml").write_text(yaml.safe_dump(spec.pop("site")), encoding="utf-8")
    spec["site"] = "site.yaml"
    (tmp_path / "d.yaml").write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    design = model.load(str(tmp_path / "d.yaml"))
    assert design.site is not None and design.site.boundary[0] == (-1000, -1000)


def test_derived_site_matches_survey(d7):
    """derived/site/d7.yaml, written by scripts/site_frame.py, maps back onto
    the survey's D7 corners within 1 mm, through its own recorded frame."""
    site = model.Site.model_validate(yaml.safe_load(SITE.read_text(encoding="utf-8")))
    f = SurveyFrame(site.frame.origin_e, site.frame.origin_n, site.frame.x_azimuth_deg)
    assert len(site.boundary) == 4
    for p, v in zip(site.boundary, (d7[3], d7[2], d7[1], d7[0])):
        e, n = f.to_survey(*p)
        assert math.dist((e, n), v) < 0.001
    assert [s.name for s in site.no_build] == ["alley strip"]
    assert len(site.spot_heights) == 21


def test_site_sheet_draws_site_and_reads_clean(spec, tmp_path):
    from houseplan import verify
    from houseplan.drawing import site_dxf

    spec["site"] = yaml.safe_load(SITE.read_text(encoding="utf-8"))
    spec["project"]["north_angle_deg"] = 337.97
    # the bungalow does not fit this plot's strip; only drawing is tested here
    design = Design.model_validate(spec)
    geo = geometry.build(design)
    doc, sheet = site_dxf(design, geo)
    layers = {e.dxf.layer for e in doc.modelspace()}
    assert {"V-PROP-LINE", "C-ROAD", "A-SITE-NOBLD", "V-SPOT"} <= layers
    texts = [e.dxf.text for e in doc.modelspace().query("TEXT")]
    assert any("1677.613" in t for t in texts)  # Pt19
    x0, y0, x1, y1 = sheet.frame
    assert x0 < -10409 and x1 > 42651 and y0 < -4583 and y1 > 39194  # roads and benchmark on the sheet
    path = tmp_path / "site.dxf"
    doc.saveas(path)
    found = verify.verify_text(str(path), geo["GF"], sheet.scale)
    assert not [f for f in found if f.code == "DXF_TEXT_OVERLAP"]


def test_plan_sheet_shows_boundary(spec):
    from houseplan.drawing import plan_dxf

    design = Design.model_validate(spec)
    geo = geometry.build(design)
    doc, sheet = plan_dxf(design, geo["GF"])
    assert {"V-PROP-LINE", "A-SITE-NOBLD"} <= {e.dxf.layer for e in doc.modelspace()}
    x0, y0, x1, y1 = sheet.frame
    assert x1 > 20000 and y1 > 20000
