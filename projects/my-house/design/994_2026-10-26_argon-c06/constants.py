"""Shared constants and configuration for Argon C06 exploratory house plans.

All units are canonical metres (or decimetres where noted by `_DM` suffix) in the
owner-confirmed plot frame: origin at NW parcel corner, `u` along the northern
boundary toward field-east (downhill/view), `v` perpendicular toward field-south.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from house_ai.domain.program import SpaceFunction as F

MODEL_ACTOR_ID = "gemini"
DESIGN_SERIES_ID = "argon-c06"
DESIGN_DATE_DISPLAY = "26 Oct 2026"

# Level identifiers (canonical)
LEVEL_ROAD = "lv-upper"
LEVEL_MAIN = "lv-entry"
LEVEL_LOWER = "lv-lower"
LEVEL_ORDER = (LEVEL_ROAD, LEVEL_MAIN, LEVEL_LOWER)

# Earthwork & window sill constants
FORMATION_OFFSET_M = 0.35
WINDOW_SILL_M = 0.80
DEFAULT_WINDOW_HEIGHT_M = 1.40
TERRACE_WINDOW_HEIGHT_M = 1.60
TERRACE_WINDOW_SILL_M = 0.60
FAMILY_STAIR_RISERS = 20
TREAD_DEPTH_M = 0.28

# Outdoor space prefixes
OUTDOOR_PREFIXES = ("sp-terrace-", "sp-deck-", "sp-court-")

# Doorless passage pairs (Owner Rule 2.4: no unnecessary doors or barriers)
DOORLESS_FUNCTION_PAIRS = frozenset(
    frozenset(pair)
    for pair in (
        (F.ENTRY, F.HALL),
        (F.ENTRY, F.LIVING),
        (F.ENTRY, F.DINING),
        (F.ENTRY, F.KITCHEN),
        (F.KITCHEN, F.PANTRY),
        (F.KITCHEN, F.DINING),
        (F.DINING, F.LIVING),
        (F.HALL, F.FAMILY),
        (F.HALL, F.LIVING),
        (F.HALL, F.DINING),
        (F.HALL, F.KITCHEN),
    )
)

# Habitable functions requiring exterior daylight/views
HABITABLE_FUNCTIONS = (
    F.BEDROOM,
    F.LIVING,
    F.DINING,
    F.KITCHEN,
    F.STUDY,
    F.FAMILY,
)

# Rendering palette & typography
FONT_FAMILY = "Helvetica, Arial, sans-serif"
BG_CANVAS_HEX = "#f7f4ee"
BG_PANEL_HEX = "#fbfaf6"
INK_PRIMARY_HEX = "#1f2a2e"
INK_MUTED_HEX = "#5a6568"
WALL_INTERIOR_HEX = "#2f4a48"
WALL_PARAPET_HEX = "#6d8c5e"
WINDOW_STROKE_HEX = "#2b7bba"
DOOR_STROKE_HEX = "#b5651d"
PARCEL_STROKE_HEX = "#8a9999"
ENVELOPE_STROKE_HEX = "#b8860b"
LAWN_FILL_HEX = "#d8ebd0"
LAWN_STROKE_HEX = "#4f8a3a"

SPACE_FILL_HEX = {
    F.LIVING: "#e3efd9",
    F.DINING: "#e8f2de",
    F.KITCHEN: "#f5e4c3",
    F.PANTRY: "#efe3cc",
    F.BEDROOM: "#f0dcc9",
    F.FAMILY: "#e1eed8",
    F.STUDY: "#e0e5f2",
    F.BATHROOM: "#d5e6ee",
    F.WC: "#d5e6ee",
    F.ENTRY: "#ecebe4",
    F.HALL: "#f2f1eb",
    F.STAIR: "#d8dede",
    F.LIFT: "#bcc8ca",
    F.GARAGE: "#dedfdb",
    F.STORAGE: "#eae8e0",
    F.LAUNDRY: "#d8e7ee",
    F.MECHANICAL: "#dcded9",
    F.TERRACE: "#cde2be",
}

LEVEL_TITLES = {
    LEVEL_ROAD: "1. Road Level (Garage + Integrated Workshop, Lobby, Lift/Stair, Office)",
    LEVEL_MAIN: "2. Main Floor (South Kitchen + Terrace, Dining, Cozy L-Living, Master Suite)",
    LEVEL_LOWER: "3. Lower Floor & East Garden (3 Bedrooms, Family + Tea Bar, Terrace & Flat Lawn)",
}

ROAD_ASPHALT_Z_M = 1677.6
EXPLORATORY_NOTICE = (
    "EXPLORATORY CONCEPT (Argon C06): Site is in SITE_NEEDS_VERIFICATION; not structurally, "
    "geotechnically, or code certified. True 1:1 vertical/horizontal scale."
)


def svg_to_png(svg_path: Path, png_path: Path, size: int = 2200) -> None:
    """Render an SVG file to a high-resolution PNG using rsvg-convert or macOS QuickLook."""
    if shutil.which("rsvg-convert"):
        subprocess.run(
            ["rsvg-convert", "-w", str(size), "-o", str(png_path), str(svg_path)],
            check=True,
        )
        return
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.run(
            ["qlmanage", "-t", "-s", str(size), "-o", tmp_dir, str(svg_path)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        produced = Path(tmp_dir) / f"{svg_path.name}.png"
        shutil.move(str(produced), str(png_path))
