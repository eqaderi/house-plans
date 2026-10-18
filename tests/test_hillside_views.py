"""Analytical section, access, coverage, breakline and risk-register regressions."""

from pathlib import Path

import pytest
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from house_ai.cad.base import CadExtraction, RawPolyline
from house_ai.cad.layers import LayerMapping
from house_ai.cad.site_extract import MappedLayerSiteExtractor
from house_ai.domain.coordinates import LocalCoordinateSystem, SurveyTransform
from house_ai.domain.hillside import HillsideSettings, SectionLine
from house_ai.domain.model import Opening, Slab, Stair, Wall
from house_ai.domain.program import SpaceFunction
from house_ai.domain.site import Site, SiteFeature, SpotElevation, Terrain, TerrainBreakline
from house_ai.geospatial.hillside import hillside_report, triangle_quality
from house_ai.geospatial.sections import cut_section, facade_elevations, standard_sections
from house_ai.geospatial.terrain import build_tin
from house_ai.render2d.hillside_export import export_hillside_views
from house_ai.storage.hashing import canonical_json, load_document

from .test_hillside_earthworks import model, surface


def site_for(tin):
    p = Path(__file__).parents[1] / "examples/projects/synthetic-hillside/site.yaml"
    site = Site.model_validate(load_document(p))
    site.coordinates.local = LocalCoordinateSystem(id="local", origin=(0, 0, 0))
    site.terrain = Terrain(surface=tin)
    site.boundary = {"outer": [(-2, -2), (12, -2), (12, 8), (-2, 8)]}
    # Re-validate after replacing the polygon.
    return Site.model_validate(site.model_dump())


def house_with_elements():
    m = model()
    m.walls = [
        Wall(
            id="wall-south",
            level_id="entry",
            start=(0, 0),
            end=(10, 0),
            thickness_m=0.2,
            height_m=3,
            kind="exterior",
        )
    ]
    m.openings = [
        Opening(
            id="door",
            kind="door",
            host_wall_id="wall-south",
            offset_m=4,
            width_m=2,
            height_m=2.1,
            connects=("room", "exterior"),
        )
    ]
    m.slabs = [
        Slab(
            id="slab",
            kind="floor",
            level_id="entry",
            boundary=m.spaces[0].boundary,
            thickness_m=0.2,
        )
    ]
    return m


def test_section_cuts_only_intersected_geometry_and_preserves_apertures():
    m = house_with_elements()
    section = cut_section(m, site_for(surface()), SectionLine(id="cut", start=(5, -1), end=(5, 7)))
    cuts = section["cuts"]
    wall = next(c for c in cuts if c["subject_id"] == "wall-south")
    assert min(z for _, z in wall["polygon"]) == pytest.approx(5.1)  # door head
    assert max(z for _, z in wall["polygon"]) == 6
    slab = next(c for c in cuts if c["kind"] == "slab")
    assert min(z for _, z in slab["polygon"]) == 2.8
    assert max(z for _, z in slab["polygon"]) == 3
    assert max(x for x, _ in slab["polygon"]) - min(x for x, _ in slab["polygon"]) == 6
    away = cut_section(m, None, SectionLine(id="away", start=(11, -1), end=(11, 7)))
    assert away["cuts"] == []  # no projection of the full level into a true cut
    assert all(p["status"] == "unknown" for p in away["ground"])


def test_standard_cuts_intersect_named_elements_and_facades_include_openings(tmp_path):
    m = house_with_elements()
    m.spaces[0].function = SpaceFunction.GARAGE
    requests = standard_sections(m, site_for(surface()))
    assert {r.id for r in requests} == {
        "longitudinal",
        "transverse",
        "garage-room",
        "entrance-door",
    }
    entrance = next(r for r in requests if r.id == "entrance-door")
    assert LineString([entrance.start, entrance.end]).distance(Point(5, 0)) < 1e-8
    garage = next(r for r in requests if r.id == "garage-room")
    assert (
        LineString([garage.start, garage.end])
        .intersection(m.spaces[0].boundary.to_shapely())
        .length
        > 0
    )
    elevations = facade_elevations(m, site_for(surface()))
    assert any(c["subject_id"] == "door" for e in elevations for c in e["cuts"])
    before = canonical_json(m)
    export_hillside_views(m, site_for(surface()), tmp_path)
    assert canonical_json(m) == before
    assert {p.name for p in tmp_path.iterdir()} == {
        "sections.json",
        "elevations.json",
        "sections.svg",
        "elevations.svg",
        "hillside.json",
        "engineering-risks.md",
    }
    svg = (tmp_path / "sections.svg").read_text()
    assert 'data-subject-id="slab"' in svg
    assert "True section" in svg


def test_stair_cut_uses_canonical_walking_direction_and_unknown_stays_unknown():
    from house_ai.domain.model import Level

    m = house_with_elements()
    m.levels.append(Level(id="upper", name="Upper", elevation_m=6))
    m.stairs = [
        Stair(
            id="stairs",
            kind="straight",
            from_level_id="entry",
            to_level_id="upper",
            bottom_space_id="room",
            top_space_id="room",
            width_m=1,
            footprint={"outer": [(1, 2), (5, 2), (5, 3), (1, 3)]},
            walking_line=[(1, 2.5), (5, 2.5)],
            riser_count=15,
        )
    ]
    request = next(r for r in standard_sections(m, None) if r.id == "stair-stairs")
    section = cut_section(m, None, request)
    cuts = [c for c in section["cuts"] if c["subject_id"] == "stairs"]
    assert len(cuts) == 15
    assert max(z for c in cuts for _, z in c["polygon"]) == 6
    m.stairs[0].walking_line = None
    section = cut_section(m, None, request)
    assert section["unknowns"][0]["subject_id"] == "stairs"


def test_deep_excavation_has_no_depth_penalty_and_large_void_is_configurable():
    m = house_with_elements()
    result = hillside_report(m, site_for(surface((9, 9, 9, 9))))
    assert result["earthworks"]["excavation_volume_m3"] == 372  # slab underside at 2.8 m
    assert result["earthworks"]["max_cut_m"] == 6.2
    assert not any(
        "excavation penalty" in r["trigger"] or "large void" in r["trigger"]
        for r in result["risks"]
    )
    assert {
        "structure",
        "foundations",
        "retaining",
        "drainage",
        "waterproofing",
        "slope_stability",
    } <= {r["discipline"] for r in result["risks"]}
    assert all(r["status"] == "needs_professional" for r in result["risks"])
    high = model(8)
    result = hillside_report(high, site_for(surface((3, 3, 3, 3))))
    assert any("large void" in r["trigger"] for r in result["risks"])
    result = hillside_report(
        high, site_for(surface((3, 3, 3, 3))), HillsideSettings(large_void_height_m=6)
    )
    assert not any("large void" in r["trigger"] for r in result["risks"])


@pytest.mark.parametrize("height,expected", [(1, 2), (5, -2)])
def test_threshold_samples_outside_door_and_garage_frontage_grade(height, expected):
    m = house_with_elements()
    m.spaces[0].function = SpaceFunction.GARAGE
    tin = surface((height,) * 4)
    tin.vertices = [(x, y - 1, z) for x, y, z in tin.vertices]  # support the exterior approach
    site = site_for(tin)
    site.features = [
        SiteFeature(
            id="front",
            kind="frontage",
            geometry={"type": "polyline", "line": {"points": [(0, -1), (10, -1)]}},
        )
    ]
    result = hillside_report(m, site)
    assert result["doors"][0]["ground_z_m"] == height
    assert result["doors"][0]["delta_m"] == expected
    assert result["outdoor_level_changes_count"] == 1
    assert result["garages"][0]["candidate_run_m"] == 1
    assert result["garages"][0]["candidate_grade_pct"] == 100 * expected
    assert result["garages"][0]["inside_parcel"]


def test_missing_coverage_and_wrong_frame_never_become_flat_ground():
    m = house_with_elements()
    site = site_for(surface())
    site.coordinates.local.id = "different"
    r = hillside_report(m, site)
    assert r["earthworks"]["coverage_pct"] == 0
    assert r["earthworks"]["excavation_volume_m3"] is None
    assert r["doors"][0]["ground_z_m"] is None


def test_constrained_breakline_changes_ridge_and_keeps_edges():
    from house_ai.domain.terrain import elevation_at

    spots = [
        SpotElevation(id=f"p{i}", xy=(x, y), z_m=0)
        for i, (x, y) in enumerate([(0, 0), (10, 0), (10, 6), (0, 6)])
    ]
    line = TerrainBreakline(id="ridge", vertices=[(2, 3, 4), (8, 3, 4)], source_ref="synthetic#1")
    r = build_tin(spots, [], [line])
    assert not r.conflicts
    assert r.surface.method == "constrained_tin"
    assert elevation_at(r.surface, (5, 3)) == pytest.approx(4)
    edges = unary_union(
        [
            LineString([r.surface.vertices[a][:2], r.surface.vertices[b][:2]])
            for tri in r.surface.triangles
            for a, b in zip(tri, (*tri[1:], tri[0]), strict=True)
        ]
    )
    assert LineString([(2, 3), (8, 3)]).difference(edges.buffer(1e-7)).length == 0


def test_crossing_breaklines_with_conflicting_heights_block_surface():
    lines = [
        TerrainBreakline(id="one", vertices=[(0, 0, 0), (10, 6, 0)]),
        TerrainBreakline(id="two", vertices=[(0, 6, 2), (10, 0, 2)]),
    ]
    r = build_tin([], [], lines)
    assert r.surface is None
    assert any("inconsistent heights" in c for c in r.conflicts)


def test_explicit_cad_mapping_imports_only_surveyed_breakline_heights():
    line = RawPolyline(points=[(0, 0), (10, 6)], zs=[1, 5], layer="BANK", handle="AB")
    extraction = CadExtraction(polylines=[line])
    mapping = LayerMapping(layers={"BANK": "breakline"})
    out = MappedLayerSiteExtractor(mapping, "src-synthetic").extract(
        extraction, SurveyTransform(1, 1, LocalCoordinateSystem(id="local", origin=(0, 0, 0)))
    )
    assert out.breaklines[0].vertices == [(0, 0, 1), (10, 6, 5)]
    assert out.breaklines[0].source_ref == "src-synthetic#AB (layer BANK)"
    extraction = CadExtraction(
        polylines=[RawPolyline(points=[(0, 0), (10, 6)], layer="BANK", handle="AB")]
    )
    out = MappedLayerSiteExtractor(mapping, "src-synthetic").extract(
        extraction, SurveyTransform(1, 1, LocalCoordinateSystem(id="local", origin=(0, 0, 0)))
    )
    assert out.breaklines == []
    assert out.ambiguous


def test_sliver_triangle_is_located_and_not_smoothed():
    from house_ai.domain.site import TinSurface

    tin = TinSurface(vertices=[(0, 0, 0), (10, 0, 0), (5, 0.00001, 2)], triangles=[(0, 1, 2)])
    before = canonical_json(tin)
    r = triangle_quality(tin, HillsideSettings())
    assert "sliver" in r[0]["triggers"]
    assert r[0]["xy"][0] == 5
    assert canonical_json(tin) == before


def test_breakline_elevations_require_human_unit_confirmation():
    from house_ai.domain.site import site_verification_blockers
    from house_ai.domain.units import UnitDeclaration

    site = site_for(None)
    site.terrain.breaklines = [TerrainBreakline(id="line", vertices=[(0, 0, 1), (10, 0, 2)])]
    site.coordinates.elevation_units = UnitDeclaration()
    assert site.has_geometry
    assert any("elevation units" in b for b in site_verification_blockers(site))


def test_terrace_edge_profiles_expose_void_and_candidate_garden_contacts():
    m = house_with_elements()
    m.spaces[0].function = SpaceFunction.TERRACE
    r = hillside_report(m, site_for(surface()))
    t = r["terraces"][0]
    assert t["edge_ground_relationships"][0]["min_floor_ground_delta_m"] == -1
    assert t["edge_ground_relationships"][0]["max_floor_ground_delta_m"] == 1
    assert t["garden_access"]["candidate_at_grade_edges"]
    assert t["garden_access"]["status"] == "inferred"


def test_invalid_pads_are_gate_errors_and_reports_remain_inspectable():
    from house_ai.domain.hillside import EarthworkPad
    from house_ai.domain.integrity import check_model

    m = house_with_elements()
    m.earthwork_pads = [
        EarthworkPad(id="high-pad", elevation_m=5, basis="synthetic", boundary=m.spaces[0].boundary)
    ]
    assert any(f.code == "earthwork_pad_above_floor" for f in check_model(m))
    report = hillside_report(m, site_for(surface()))
    assert report["geometry_error"]
    assert report["earthworks"]["excavation_volume_m3"] is None
