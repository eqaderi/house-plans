"""Closed-form geometric ground truth; no private survey or network."""

import pytest
from shapely.geometry import Polygon, box

from house_ai.domain.hillside import EarthworkPad
from house_ai.domain.model import HouseModel, Level, Space
from house_ai.domain.program import SpaceFunction
from house_ai.domain.site import TinSurface
from house_ai.geospatial.earthworks import earthworks, integrate, retained_face, terrain_profile
from house_ai.geospatial.mesh import closed_tin, terrain_intersection


def surface(heights=(2, 4, 4, 2)):
    return TinSurface(
        vertices=[(0, 0, heights[0]), (10, 0, heights[1]), (10, 6, heights[2]), (0, 6, heights[3])],
        triangles=[(0, 1, 2), (0, 2, 3)],
    )


def model(floor=3):
    return HouseModel(
        id="house",
        name="Synthetic analytical house",
        coordinate_system_id="local",
        levels=[Level(id="entry", name="Entry", elevation_m=floor)],
        spaces=[
            Space(
                id="room",
                name="Room",
                level_id="entry",
                function=SpaceFunction.LIVING,
                boundary={"outer": [(0, 0), (10, 0), (10, 6), (0, 6)]},
            )
        ],
    )


@pytest.mark.parametrize(
    "tin,cut,void",
    [
        (surface(), 15, 15),
        (surface((1, 5, 5, 1)), 30, 30),
        (
            TinSurface(
                vertices=[(0, 0, 1), (10, 0, 1), (10, 6, 1), (0, 6, 1), (5, 3, 5)],
                triangles=[(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)],
            ),
            10,
            50,
        ),
    ],
)
def test_closed_form_volumes_and_independent_mesh_boolean(tin, cut, void):
    r = integrate(tin, box(0, 0, 10, 6), 3)
    assert r.cut_m3 == pytest.approx(cut, abs=1e-7)
    assert r.below_plane_m3 == pytest.approx(void, abs=1e-7)
    mesh = terrain_intersection(tin, box(0, 0, 10, 6), 3)
    assert mesh["watertight"]
    assert mesh["cut_m3"] == pytest.approx(cut, abs=1e-7)
    assert mesh["below_plane_m3"] == pytest.approx(void, abs=1e-7)


def test_stepped_pad_against_flat_terrain():
    m = model(5)
    m.earthwork_pads = [
        EarthworkPad(
            id="low-pad",
            elevation_m=2,
            basis="synthetic design",
            boundary={"outer": [(0, 0), (5, 0), (5, 6), (0, 6)]},
        ),
        EarthworkPad(
            id="high-pad",
            elevation_m=4,
            basis="synthetic design",
            boundary={"outer": [(5, 0), (10, 0), (10, 6), (5, 6)]},
        ),
    ]
    r = earthworks(m, surface((3, 3, 3, 3)))
    assert r["excavation_volume_m3"] == 30
    assert r["engineered_fill_volume_m3"] == 30
    assert r["underfloor_void_volume_m3"] == 120  # 30*(5-2) + 30*(5-4)


def test_void_is_not_fill_and_overlapping_levels_count_once():
    m = model(5)
    m.levels.append(Level(id="upper", name="Upper", elevation_m=8))
    m.spaces.append(m.spaces[0].model_copy(update={"id": "upper-room", "level_id": "upper"}))
    r = earthworks(m, surface((3, 3, 3, 3)))
    assert r["underfloor_void_volume_m3"] == 120
    assert r["engineered_fill_volume_m3"] is None
    assert r["footprint_area_m2"] == 60


def test_holes_and_partial_support_are_not_extrapolated():
    footprint = Polygon(
        [(-5, 0), (10, 0), (10, 6), (-5, 6)], holes=[[(2, 2), (4, 2), (4, 4), (2, 4)]]
    )
    r = integrate(surface((2, 2, 2, 2)), footprint, 3)
    assert r.area_m2 == 86
    assert r.known_area_m2 == 56
    assert r.below_plane_m3 == 56
    assert integrate(None, footprint, 3).cut_m3 is None


def test_true_profile_retained_height_and_unknown_gap():
    from shapely.geometry import LineString

    profile = terrain_profile(surface(), LineString([(-2, 3), (12, 3)]))
    assert sum(p["end_m"] - p["start_m"] for p in profile if p["status"] == "unknown") == 4
    known = [p for p in profile if p["status"] == "inferred"]
    assert known[0]["start_z_m"] == 2
    assert known[-1]["end_z_m"] == 4
    r = retained_face(surface(), (0, 3), (10, 3), 3)
    assert r["face_area_m2"] == pytest.approx(2.5)
    assert r["mean_retained_height_m"] == pytest.approx(0.25)
    assert r["max_retained_height_m"] == 1


def test_mesh_rejects_base_above_terrain():
    with pytest.raises(ValueError, match="strictly below"):
        closed_tin(surface(), 3)


def test_void_to_slab_underside_and_fill_require_known_pad_coverage():
    from house_ai.domain.model import Slab

    m = model(3)
    m.slabs = [
        Slab(
            id="floor-slab",
            level_id="entry",
            kind="floor",
            thickness_m=0.2,
            boundary=m.spaces[0].boundary,
        )
    ]
    r = earthworks(m, surface((2, 2, 2, 2)))
    assert r["underfloor_void_volume_m3"] == pytest.approx(48)
    assert r["max_underfloor_void_height_m"] == pytest.approx(0.8)
    assert r["regions"][0]["floor_basis"] == "underside:floor-slab"
    m.earthwork_pads = [
        EarthworkPad(
            id="away",
            elevation_m=1,
            basis="synthetic",
            boundary={"outer": [(20, 0), (30, 0), (30, 6), (20, 6)]},
        )
    ]
    r = earthworks(m, surface((2, 2, 2, 2)))
    assert r["engineered_fill_volume_m3"] is None
    assert r["unknown_pad_area_m2"] == 60


def test_overlapping_tin_is_explicitly_rejected_instead_of_double_counted():
    tin = surface()
    tin.triangles.append(tin.triangles[0])
    with pytest.raises(ValueError, match="overlap in XY"):
        integrate(tin, box(0, 0, 10, 6), 3)


def test_slab_extensions_contribute_volume_and_unknown_coverage():
    from house_ai.domain.geometry import Polygon2D
    from house_ai.domain.model import Slab

    m = model(5)
    m.slabs = [
        Slab(
            id="extended",
            level_id="entry",
            kind="floor",
            thickness_m=0.2,
            boundary=Polygon2D.rectangle(0, 0, 12, 6),
        )
    ]
    tin = surface((2, 2, 2, 2))
    tin.vertices = [(x * 1.2, y, z) for x, y, z in tin.vertices]
    r = earthworks(m, tin)
    assert r["footprint_area_m2"] == 72
    assert r["underfloor_void_volume_m3"] == pytest.approx(201.6)
    r = earthworks(m, surface((2, 2, 2, 2)))
    assert r["known_area_m2"] == 60
    assert r["unknown_area_m2"] == 12


def test_overlapping_or_above_floor_pads_fail_clearly():
    m = model()
    pad = EarthworkPad(id="pad", boundary=m.spaces[0].boundary, elevation_m=4, basis="synthetic")
    m.earthwork_pads = [pad]
    with pytest.raises(ValueError, match="above floor"):
        earthworks(m, surface())
    m.earthwork_pads.append(pad.model_copy(update={"id": "pad-2"}))
    with pytest.raises(ValueError, match="overlap"):
        earthworks(m, surface())


def test_slab_touching_the_region_along_an_edge_adds_only_its_area():
    """S10-19: an overlay that also returns an edge line must not break the next slabs."""
    from house_ai.domain.model import Slab
    from house_ai.geospatial.earthworks import ground_planes

    m = model(3)
    lower = Polygon([(0, 0), (5, 0), (5, 6), (10, 6), (10, 8), (0, 8)])
    m.levels.append(Level(id="down", name="Down", elevation_m=0))
    m.spaces.append(
        Space(
            id="below",
            name="Below",
            level_id="down",
            function=SpaceFunction.STORAGE,
            boundary={"outer": list(lower.exterior.coords)[:-1]},
        )
    )
    # Overlaps the entry region (x 5..10, y 0..6) only in x 8..10 and touches it along x = 5.
    hooked = box(3, 0, 5, 2).union(box(3, 0, 4, 7.5)).union(box(3, 6.5, 10, 7.5))
    hooked = hooked.union(box(8, 0, 10, 7.5))
    m.slabs = [
        Slab(
            id="hooked",
            level_id="entry",
            kind="floor",
            thickness_m=0.5,
            boundary={"outer": list(hooked.exterior.coords)[:-1]},
        ),
        # Over the lower level only: its overlay with the entry region is empty.
        Slab(
            id="hidden",
            level_id="entry",
            kind="floor",
            thickness_m=0.3,
            boundary={"outer": [(0, 0), (2, 0), (2, 2), (0, 2)]},
        ),
        Slab(
            id="plain",
            level_id="entry",
            kind="floor",
            thickness_m=0.2,
            boundary=m.spaces[0].boundary,
        ),
    ]
    planes = [(lv, z, round(region.area, 9), basis) for lv, z, region, basis in ground_planes(m)]
    assert planes == [
        ("down", 0, 50.0, "finished_floor_bound_no_slab"),
        ("entry", 2.5, 12.0, "underside:hooked"),
        ("entry", 2.8, 18.0, "underside:plain"),
    ]
