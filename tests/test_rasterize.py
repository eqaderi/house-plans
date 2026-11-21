"""Unit tests for static SVG rasterization (Stage S5, Task S5-04).

The PNGs are decoded here (stdlib zlib only) so the tests check pixels and sizes, not bytes.
"""

from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

import pytest

from house_ai.render2d import rasterize
from house_ai.render2d.rasterize import find_rasterizer, rasterize_svg_to_png

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg"
  width="200" height="100" viewBox="0 0 200 100">
  <rect width="200" height="100" fill="#0f172a"/>
  <circle cx="100" cy="50" r="40" fill="#38bdf8"/>
  <text x="100" y="55" fill="#ffffff" font-size="14" text-anchor="middle">HOUSE AI</text>
</svg>"""
NAVY = (0x0F, 0x17, 0x2A, 255)
SKY = (0x38, 0xBD, 0xF8, 255)


def png_size(data: bytes) -> tuple[int, int]:
    """(width, height) from the IHDR chunk, which the PNG format puts first."""
    assert data.startswith(PNG_SIGNATURE)
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def png_pixels(data: bytes) -> list[list[tuple[int, ...]]]:
    """Rows of RGBA pixels of an 8-bit, non-interlaced RGB or RGBA PNG."""
    width, height = png_size(data)
    depth, color, _, _, interlace = data[24:29]
    assert (depth, interlace) == (8, 0), "only 8-bit non-interlaced PNGs are decoded"
    channels = {2: 3, 6: 4}[color]
    pos, idat = 8, b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        if kind == b"IDAT":
            idat += data[pos + 8 : pos + 8 + length]
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * channels
    rows: list[bytearray] = []
    prev = bytearray(stride)
    for y in range(height):
        start = y * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1 : start + 1 + stride])
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0
            b = prev[i]
            c = prev[i - channels] if i >= channels else 0
            if kind == 1:
                line[i] = (line[i] + a) & 0xFF
            elif kind == 2:
                line[i] = (line[i] + b) & 0xFF
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else b if pb <= pc else c
                line[i] = (line[i] + pred) & 0xFF
        rows.append(line)
        prev = line
    alpha = (255,) if channels == 3 else ()
    return [
        [tuple(row[x * channels : (x + 1) * channels]) + alpha for x in range(width)]
        for row in rows
    ]


def _executable(folder: Path, name: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    tool = folder / name
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(0o755)
    return tool


def test_find_rasterizer_prefers_rsvg_convert_then_inkscape(tmp_path, monkeypatch):
    """Off PATH, the common bin folders are searched: rsvg-convert first, then Inkscape;
    a file that is not executable does not count."""
    monkeypatch.setattr(rasterize.shutil, "which", lambda name: None)
    first, second = tmp_path / "first", tmp_path / "second"
    monkeypatch.setattr(rasterize, "COMMON_BIN_DIRS", [first, second])
    assert find_rasterizer() is None

    (second / "rsvg-convert").parent.mkdir(parents=True)
    (second / "rsvg-convert").write_text("not executable", encoding="utf-8")
    inkscape = _executable(first, "inkscape")
    assert find_rasterizer() == ("inkscape", inkscape)

    rsvg = _executable(second, "rsvg-convert")
    assert find_rasterizer() == ("rsvg-convert", rsvg)


def test_find_rasterizer_uses_the_path_first(tmp_path, monkeypatch):
    on_path = _executable(tmp_path / "bin", "rsvg-convert")
    monkeypatch.setattr(rasterize.shutil, "which", lambda name: str(on_path))
    monkeypatch.setattr(rasterize, "COMMON_BIN_DIRS", [])
    assert find_rasterizer() == ("rsvg-convert", on_path)


def test_rasterize_without_a_tool_says_what_to_install(tmp_path, monkeypatch):
    monkeypatch.setattr(rasterize, "find_rasterizer", lambda: None)
    out = tmp_path / "never.png"
    with pytest.raises(RuntimeError, match="Install 'rsvg-convert'"):
        rasterize_svg_to_png(SAMPLE_SVG, out)
    assert not out.exists()


@pytest.fixture
def tool():
    found = find_rasterizer()
    if found is None:
        pytest.skip("Neither rsvg-convert nor inkscape is available in environment")
    name, path = found
    assert name in ("rsvg-convert", "inkscape")
    assert path.is_file() and os.access(path, os.X_OK)
    return found


def test_rasterize_svg_to_png(tool, tmp_path):
    """The PNG has the requested size and the SVG's colours where the SVG draws them."""
    out_png = tmp_path / "test_output.png"
    result_path = rasterize_svg_to_png(SAMPLE_SVG, out_png, width=200, height=100)
    assert result_path == out_png
    data = out_png.read_bytes()
    assert png_size(data) == (200, 100)
    pixels = png_pixels(data)
    assert pixels[0][0] == NAVY  # background corner
    assert pixels[99][199] == NAVY
    assert pixels[20][100] == SKY  # inside the circle (r 40 about 100,50), above the text
    assert pixels[50][65] == SKY  # 35 px left of the centre


def test_rasterize_scales_to_the_requested_size(tool, tmp_path):
    out_png = rasterize_svg_to_png(SAMPLE_SVG, tmp_path / "big.png", width=400, height=200)
    pixels = png_pixels(out_png.read_bytes())
    assert (len(pixels[0]), len(pixels)) == (400, 200)
    assert pixels[40][200] == SKY  # the circle's top area, scaled x2
    assert pixels[0][0] == NAVY


def test_rasterize_reports_a_failing_tool(tool, tmp_path):
    with pytest.raises(RuntimeError, match="Rasterization failed"):
        rasterize_svg_to_png("<svg not xml", tmp_path / "bad.png")
