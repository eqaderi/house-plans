"""Screenshot and semantic ID-map regression tests (Stage S5, Task S5-08)."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from house_ai.domain.plan import PlanVersion
from house_ai.domain.site import Site
from house_ai.render2d.rasterize import find_rasterizer, rasterize_svg_to_png
from house_ai.storage.hashing import load_document
from house_ai.validation.semantic_map import (
    build_semantic_id_map,
    compare_image_bytes,
    diff_semantic_id_maps,
    extract_svg_semantic_id_map,
)

REPO = Path(__file__).resolve().parent.parent
BUNGALOW = REPO / "examples" / "projects" / "synthetic-bungalow"
HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"


def _load_bungalow() -> tuple[PlanVersion, Site]:
    plan_dict = copy.deepcopy(load_document(BUNGALOW / "plans" / "plan-a.json"))
    site_dict = copy.deepcopy(load_document(BUNGALOW / "site.yaml"))
    return PlanVersion.model_validate(plan_dict), Site.model_validate(site_dict)


def _load_hillside() -> tuple[PlanVersion, Site]:
    plan_dict = copy.deepcopy(
        load_document(
            HILLSIDE / "concepts" / "concept-split-level" / "exploratory" / "plan.json"
        )
    )
    site_dict = copy.deepcopy(load_document(HILLSIDE / "site.yaml"))
    return PlanVersion.model_validate(plan_dict), Site.model_validate(site_dict)


def test_semantic_id_map_extraction_bungalow():
    """Verify semantic element map extracts all canonical bungalow entities."""
    plan, site = _load_bungalow()
    id_map = build_semantic_id_map(plan, site)

    # Site overlays
    assert "site-parcel-boundary" in id_map
    assert id_map["site-parcel-boundary"].kind == "parcel"
    assert "site-buildable-envelope" in id_map
    assert id_map["site-buildable-envelope"].kind == "envelope"

    # Canonical spaces
    expected_spaces = {
        "sp-living",
        "sp-bed-parents",
        "sp-bed-children",
        "sp-bath",
        "sp-kitchen",
        "sp-hall",
    }
    for sp_id in expected_spaces:
        assert sp_id in id_map
        assert id_map[sp_id].kind == "space"
        assert id_map[sp_id].attributes["area_m2"] > 0

    # Walls and openings
    assert any(rec.kind == "wall" for rec in id_map.values())
    assert any(rec.kind == "door" for rec in id_map.values())


def test_semantic_id_map_extraction_hillside():
    """Verify semantic element map on multi-level hillside concept."""
    plan, site = _load_hillside()
    id_map = build_semantic_id_map(plan, site)

    # Levels and stairs
    assert any(rec.kind == "elevation-marker" for rec in id_map.values())
    assert any(rec.kind == "stair" for rec in id_map.values())
    assert any(rec.kind == "space" for rec in id_map.values())


def test_semantic_id_map_diff_identical():
    """Diffing identical models reports zero changes."""
    plan, site = _load_bungalow()
    map1 = build_semantic_id_map(plan, site)
    map2 = build_semantic_id_map(plan, site)

    diff = diff_semantic_id_maps(map1, map2)
    assert diff.is_identical
    assert diff.added == []
    assert diff.removed == []
    assert diff.modified == {}
    assert diff.summary() == "No differences"


def test_semantic_id_map_diff_detects_removed_element():
    """Removing a canonical space is caught as a regression failure."""
    plan, site = _load_bungalow()
    baseline_map = build_semantic_id_map(plan, site)

    # Create mutated plan missing sp-living
    mutated_plan = plan.model_copy(deep=True)
    mutated_plan.model.spaces = [s for s in mutated_plan.model.spaces if s.id != "sp-living"]

    current_map = build_semantic_id_map(mutated_plan, site)
    diff = diff_semantic_id_maps(baseline_map, current_map)

    assert not diff.is_identical
    assert diff.removed == ["sp-living"]
    assert "Removed (1): sp-living" in diff.summary()


def test_semantic_id_map_diff_detects_modified_element():
    """Modifying an element property is caught as a regression failure."""
    plan, site = _load_bungalow()
    baseline_map = build_semantic_id_map(plan, site)

    # Mutate kitchen area
    current_map = copy.deepcopy(baseline_map)
    kitchen = current_map["sp-kitchen"]
    mutated_attrs = dict(kitchen.attributes)
    mutated_attrs["area_m2"] = 99.0
    current_map["sp-kitchen"] = kitchen.__class__(
        id=kitchen.id,
        kind=kitchen.kind,
        label=kitchen.label,
        level_id=kitchen.level_id,
        bbox=kitchen.bbox,
        attributes=mutated_attrs,
    )

    diff = diff_semantic_id_maps(baseline_map, current_map)
    assert not diff.is_identical
    assert "sp-kitchen" in diff.modified
    assert "attributes" in diff.modified["sp-kitchen"]
    assert "Modified (1): sp-kitchen" in diff.summary()


def test_semantic_id_map_diff_detects_added_element():
    """Adding an unexpected element is detected."""
    plan, site = _load_bungalow()
    baseline_map = build_semantic_id_map(plan, site)

    current_map = copy.deepcopy(baseline_map)
    current_map["sp-extra"] = baseline_map["sp-living"].__class__(
        id="sp-extra",
        kind="space",
        label="Extra Room",
    )

    diff = diff_semantic_id_maps(baseline_map, current_map)
    assert not diff.is_identical
    assert diff.added == ["sp-extra"]
    assert "Added (1): sp-extra" in diff.summary()


def test_extract_svg_semantic_id_map():
    """Extract semantic elements directly from rendered SVG markup."""
    sample_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">
      <polygon data-id="site-parcel-boundary" data-kind="parcel"
        role="region" aria-label="Parcel" points="0,0 100,0 100,100 0,100"/>
      <g data-id="sp-living" data-kind="space" role="region" aria-label="Space Living (sp-living)">
        <polygon points="10,10 50,10 50,50 10,50"/>
      </g>
    </svg>"""

    extracted = extract_svg_semantic_id_map(sample_svg)
    assert "site-parcel-boundary" in extracted
    assert extracted["site-parcel-boundary"]["data-kind"] == "parcel"
    assert "sp-living" in extracted
    assert extracted["sp-living"]["data-kind"] == "space"
    assert extracted["sp-living"]["aria-label"] == "Space Living (sp-living)"


def test_compare_image_bytes_identical_and_mismatch():
    """Verify deterministic image byte comparisons."""
    png_header = b"\x89PNG\r\n\x1a\n"
    img1 = png_header + b"\x00" * 100
    img2 = png_header + b"\x00" * 100
    img3 = png_header + b"\xff" * 100

    # Identical
    is_match, ratio, msg = compare_image_bytes(img1, img2)
    assert is_match
    assert ratio == 0.0

    # Mismatch with zero tolerance
    is_match, ratio, msg = compare_image_bytes(img1, img3, max_diff_ratio=0.0)
    assert not is_match
    assert ratio > 0.0

    # Mismatch with broad tolerance
    is_match, ratio, msg = compare_image_bytes(img1, img3, max_diff_ratio=1.0)
    assert is_match


def test_rasterized_screenshot_regression_fails_on_unintended_change(tmp_path):
    """Verify rasterized SVG diffing fails when SVG geometry/color changes."""
    tool = find_rasterizer()
    if tool is None:
        pytest.skip("Neither rsvg-convert nor inkscape is available")

    svg_baseline = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
      <rect width="100" height="100" fill="#38bdf8"/>
    </svg>"""

    svg_modified = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
      <rect width="100" height="100" fill="#e11d48"/>
    </svg>"""

    png_base = tmp_path / "baseline.png"
    png_mod = tmp_path / "modified.png"

    rasterize_svg_to_png(svg_baseline, png_base, width=100, height=100)
    rasterize_svg_to_png(svg_modified, png_mod, width=100, height=100)

    base_bytes = png_base.read_bytes()
    mod_bytes = png_mod.read_bytes()

    # Identical rasterization of same SVG
    is_match, ratio, msg = compare_image_bytes(base_bytes, base_bytes)
    assert is_match
    assert ratio == 0.0

    # Changed SVG rasterization must fail exact equality
    is_match, ratio, msg = compare_image_bytes(base_bytes, mod_bytes, max_diff_ratio=0.0)
    assert not is_match
    assert ratio > 0.0
