"""Static rasterisation of SVG floor plans to PNG using rsvg-convert or Inkscape.

Allows quick, headless visual inspection without launching a browser.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

COMMON_BIN_DIRS = [
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
    Path("/usr/bin"),
]


def find_rasterizer() -> tuple[str, Path] | None:
    """Find available SVG rasterization CLI tool (rsvg-convert or inkscape).

    Returns:
        Tuple of (tool_name, tool_path) or None if neither tool is installed.
    """
    # 1. Check rsvg-convert
    rsvg_path = shutil.which("rsvg-convert")
    if rsvg_path:
        return ("rsvg-convert", Path(rsvg_path))
    for d in COMMON_BIN_DIRS:
        candidate = d / "rsvg-convert"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return ("rsvg-convert", candidate)

    # 2. Check inkscape
    inkscape_path = shutil.which("inkscape")
    if inkscape_path:
        return ("inkscape", Path(inkscape_path))
    for d in COMMON_BIN_DIRS:
        candidate = d / "inkscape"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return ("inkscape", candidate)

    return None


def rasterize_svg_to_png(
    svg_content: str,
    output_png_path: Path,
    *,
    width: int | None = None,
    height: int | None = None,
    dpi: int = 96,
) -> Path:
    """Rasterize SVG string to a PNG file using the preferred available tool.

    Args:
        svg_content: Complete SVG XML string.
        output_png_path: Target path for the output PNG file.
        width: Optional output width in pixels.
        height: Optional output height in pixels.
        dpi: Resolution DPI (default 96).

    Returns:
        Path to the created PNG file.

    Raises:
        RuntimeError: If neither rsvg-convert nor inkscape is available,
                      or if the rasterization command fails.
    """
    rasterizer = find_rasterizer()
    if not rasterizer:
        raise RuntimeError(
            "No SVG rasterizer available. Install 'rsvg-convert' (librsvg) or 'inkscape'."
        )

    tool_name, tool_bin = rasterizer
    output_png_path = Path(output_png_path)
    output_png_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8") as f:
        f.write(svg_content)
        temp_svg_path = Path(f.name)

    try:
        if tool_name == "rsvg-convert":
            cmd = [str(tool_bin), "-f", "png", "-d", str(dpi), "-p", str(dpi)]
            if width is not None:
                cmd.extend(["-w", str(width)])
            if height is not None:
                cmd.extend(["-h", str(height)])
            cmd.extend(["-o", str(output_png_path), str(temp_svg_path)])
        elif tool_name == "inkscape":
            cmd = [
                str(tool_bin),
                str(temp_svg_path),
                "-o",
                str(output_png_path),
                f"--export-dpi={dpi}",
            ]
            if width is not None:
                cmd.extend(["-w", str(width)])
            if height is not None:
                cmd.extend(["-h", str(height)])
        else:
            raise RuntimeError(f"Unknown rasterizer tool: {tool_name}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Rasterization failed ({tool_name} exited with {result.returncode}):\n"
                f"{result.stderr}"
            )

        if not output_png_path.exists() or output_png_path.stat().st_size == 0:
            raise RuntimeError(
                f"Rasterization output file was not created or empty: {output_png_path}"
            )

        return output_png_path
    finally:
        if temp_svg_path.exists():
            temp_svg_path.unlink()
