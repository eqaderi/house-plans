"""Unit tests for static SVG rasterization (Stage S5, Task S5-04)."""

from __future__ import annotations

import pytest

from house_ai.render2d.rasterize import find_rasterizer, rasterize_svg_to_png

SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg"
  width="200" height="100" viewBox="0 0 200 100">
  <rect width="200" height="100" fill="#0f172a"/>
  <circle cx="100" cy="50" r="40" fill="#38bdf8"/>
  <text x="100" y="55" fill="#ffffff" font-size="14" text-anchor="middle">HOUSE AI</text>
</svg>"""


def test_find_rasterizer_detects_tool():
    """Verify tool detection finds rsvg-convert or inkscape if installed."""
    tool = find_rasterizer()
    if tool is not None:
        name, path = tool
        assert name in ("rsvg-convert", "inkscape")
        assert path.exists()


def test_rasterize_svg_to_png(tmp_path):
    """Test converting SVG to PNG file."""
    tool = find_rasterizer()
    if tool is None:
        pytest.skip("Neither rsvg-convert nor inkscape is available in environment")

    out_png = tmp_path / "test_output.png"
    result_path = rasterize_svg_to_png(SAMPLE_SVG, out_png, width=200, height=100)

    assert result_path == out_png
    assert out_png.exists()
    assert out_png.stat().st_size > 100

    # Verify PNG header bytes: \x89PNG\r\n\x1a\n
    with open(out_png, "rb") as f:
        header = f.read(8)
    assert header == b"\x89PNG\r\n\x1a\n"
