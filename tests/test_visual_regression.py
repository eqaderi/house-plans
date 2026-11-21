"""Semantic ID-map regression tests, and what the byte and pixel comparisons say (S5-08).

`compare_image_bytes` compares encoded PNG bytes: equal bytes are the same image, but the ratio
it reports for different bytes is not a pixel difference. The drawing's regression test is
the SVG golden file (test_plan_svg.py); the rasterised test here decodes pixels.
"""

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

from .test_rasterize import png_pixels, png_size

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


def _ids_by_kind(id_map) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for rec in id_map.values():
        assert rec.id in id_map and id_map[rec.id] is rec
        out.setdefault(rec.kind, set()).add(rec.id)
    return out


def _model_ids_by_kind(plan: PlanVersion) -> dict[str, set[str]]:
    """Every canonical element of the model, by the kind the ID map gives it."""
    m = plan.model
    kinds = {
        "parcel": {"site-parcel-boundary"},
        "envelope": {"site-buildable-envelope"},
        "elevation-marker": {f"level-elev-{lv.id}" for lv in m.levels},
        "space": {s.id for s in m.spaces},
        "wall": {w.id for w in m.walls},
        "door": {o.id for o in m.openings if o.is_passable},
        "window": {o.id for o in m.openings if not o.is_passable},
        "stair": {st.id for st in m.stairs},
        "fixture": {f.id for f in m.fixtures},
        "furniture": {f.id for f in m.furniture},
    }
    return {k: v for k, v in kinds.items() if v}


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
    by_kind = _ids_by_kind(id_map)
    assert by_kind["space"] == expected_spaces
    for sp_id in expected_spaces:
        assert id_map[sp_id].attributes["area_m2"] == round(plan.model.space(sp_id).area_m2, 2)

    # Walls and openings: exactly the model's, nothing more
    assert by_kind == _model_ids_by_kind(plan)
    assert by_kind["wall"] and by_kind["door"]


def test_semantic_id_map_extraction_hillside():
    """Verify semantic element map on multi-level hillside concept."""
    plan, site = _load_hillside()
    id_map = build_semantic_id_map(plan, site)

    # One elevation marker per Level, every stair and space: exactly the model's elements
    by_kind = _ids_by_kind(id_map)
    assert by_kind == _model_ids_by_kind(plan)
    assert len(by_kind["elevation-marker"]) == len(plan.model.levels) > 1
    assert by_kind["stair"]
    for lv in plan.model.levels:
        marker = id_map[f"level-elev-{lv.id}"]
        assert (marker.level_id, marker.attributes) == (lv.id, {"elevation_m": lv.elevation_m})


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


def test_compare_image_bytes_counts_differing_bytes():
    """The ratio is differing bytes over the longer input: a byte measure, not pixels."""
    png_header = b"\x89PNG\r\n\x1a\n"
    img1 = png_header + b"\x00" * 100
    img2 = png_header + b"\x00" * 100
    img3 = png_header + b"\xff" * 100

    # Identical
    assert compare_image_bytes(img1, img2) == (True, 0.0, "Byte-exact match")

    # 100 of the 108 bytes differ (the 8 header bytes agree)
    is_match, ratio, _ = compare_image_bytes(img1, img3, max_diff_ratio=0.0)
    assert not is_match
    assert ratio == pytest.approx(100 / 108)

    # A length difference counts every missing byte
    _, ratio, _ = compare_image_bytes(img1, img1 + b"\x00" * 12)
    assert ratio == pytest.approx(12 / 120)

    # Mismatch within a broad tolerance
    is_match, _, _ = compare_image_bytes(img1, img3, max_diff_ratio=1.0)
    assert is_match

    # Not PNG
    assert compare_image_bytes(b"GIF89a", b"GIF87a") == (False, 1.0, "Invalid PNG header")


def test_rasterized_svg_pixels_change_with_the_fill_and_only_there(tmp_path):
    """Rasterise two SVGs that differ in one fill: every pixel has the SVG's exact colour."""
    tool = find_rasterizer()
    if tool is None:
        pytest.skip("Neither rsvg-convert nor inkscape is available")

    def svg(fill: str) -> str:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
      <rect width="100" height="100" fill="#38bdf8"/>
      <rect x="0" y="50" width="100" height="50" fill="{fill}"/>
    </svg>"""

    def raster(fill: str, name: str) -> bytes:
        out = rasterize_svg_to_png(svg(fill), tmp_path / name, width=100, height=100)
        return out.read_bytes()

    base_bytes, mod_bytes = raster("#38bdf8", "baseline.png"), raster("#e11d48", "modified.png")
    assert png_size(base_bytes) == png_size(mod_bytes) == (100, 100)

    # The same SVG rasterises to the same bytes
    assert compare_image_bytes(base_bytes, raster("#38bdf8", "again.png"))[0]

    sky, rose = (0x38, 0xBD, 0xF8, 255), (0xE1, 0x1D, 0x48, 255)
    base, mod = png_pixels(base_bytes), png_pixels(mod_bytes)
    assert {px for row in base for px in row} == {sky}
    assert {px for row in mod[:50] for px in row} == {sky}  # the unchanged top half
    assert {px for row in mod[50:] for px in row} == {rose}  # the changed bottom half
    flat_base = [px for row in base for px in row]
    flat_mod = [px for row in mod for px in row]
    changed = sum(a != b for a, b in zip(flat_base, flat_mod, strict=True))
    assert changed == 100 * 50
    assert not compare_image_bytes(base_bytes, mod_bytes, max_diff_ratio=0.0)[0]
