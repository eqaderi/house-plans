"""Shared constants and configuration for Argon C07 house plans (heavily based on user-designed 0109-r5).

Directly implements and perfects the homeowner's three crafted designs (`A`, `B`, `C`) from
`projects/my-house/design/user-designed/redesign-0109-r5`, preserving their sculpted stepped/notched
footprints, north-projecting vertical core (`CORE + REST 1.40 + LIFT`), 4-part screened wet/wudu
cluster, road-level west-to-east arrival sequence, and room arrangements while resolving all 30 issues
in `independent-review-0110-r2` and obeying 100% of `OWNER_DESIGN_RULES.md` (`stmt-001` through `stmt-020`).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from house_ai.domain.program import SpaceFunction as F

MODEL_ACTOR_ID = "gemini"
DESIGN_SERIES_ID = "argon-c07"
DESIGN_DATE_DISPLAY = "26 Oct 2026"

# Canonical level identifiers
LEVEL_ROAD = "lv-upper"
LEVEL_MAIN = "lv-entry"
LEVEL_LOWER = "lv-lower"
LEVEL_ORDER = (LEVEL_ROAD, LEVEL_MAIN, LEVEL_LOWER)

# Earthwork, stair & window geometry constants
FORMATION_OFFSET_M = 0.35
WINDOW_SILL_M = 0.80
DEFAULT_WINDOW_HEIGHT_M = 1.40
TERRACE_WINDOW_HEIGHT_M = 1.60
TERRACE_WINDOW_SILL_M = 0.60
FAMILY_STAIR_RISERS = 20
TREAD_DEPTH_M = 0.28

# Vehicle & furniture envelope constants (from user-designed 0109-r5 + 0110-r2 I09 fix)
LC300_LENGTH_M = 5.10
LC300_WIDTH_M = 2.10
SECOND_CAR_LENGTH_M = 4.80
SECOND_CAR_WIDTH_M = 1.95
CAR_DOOR_ZONE_M = 0.65
QIBLA_BEARING_DEG = 204.65

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

# Architectural rendering palette (matching user's 0109-r5 drawings + warm zoning)
FONT_FAMILY = "Helvetica, Arial, sans-serif"
BG_CANVAS_HEX = "#f8f6f0"
BG_PANEL_HEX = "#fcfbf7"
INK_PRIMARY_HEX = "#1e293b"
INK_MUTED_HEX = "#475569"
WALL_INTERIOR_HEX = "#1e293b"
WALL_PARAPET_HEX = "#64748b"
WINDOW_STROKE_HEX = "#0284c7"
DOOR_STROKE_HEX = "#0f766e"
PARCEL_STROKE_HEX = "#94a3b8"
ENVELOPE_STROKE_HEX = "#b45309"
LAWN_FILL_HEX = "#dcfce7"
LAWN_STROKE_HEX = "#15803d"
FURNITURE_STROKE_HEX = "#64748b"
FURNITURE_FILL_HEX = "#ffffff"
SIGHTLINE_BAFFLE_HEX = "#be123c"

SPACE_FILL_HEX = {
    F.LIVING: "#efe9dc",
    F.DINING: "#efe9dc",
    F.KITCHEN: "#f3e5c8",
    F.PANTRY: "#ede0c8",
    F.BEDROOM: "#e3ebf2",
    F.FAMILY: "#efe9dc",
    F.STUDY: "#e6e4f0",
    F.BATHROOM: "#d8ebe9",
    F.WC: "#d8ebe9",
    F.ENTRY: "#f1efe8",
    F.HALL: "#f5f3ec",
    F.STAIR: "#e2e8f0",
    F.LIFT: "#cbd5e1",
    F.GARAGE: "#e5e7eb",
    F.STORAGE: "#e7e5dc",
    F.LAUNDRY: "#d8ebe9",
    F.MECHANICAL: "#e2e4dc",
    F.TERRACE: "#e5dec9",
}

LEVEL_TITLES = {
    LEVEL_ROAD: "1. ROAD FLOOR (West Two Independent Car Bays + Workshop → 6-Person Unloading → Core, 1.2m Plant & SE Office)",
    LEVEL_MAIN: "2. UPPER / MAIN FLOOR (North-Projecting Core, 4-Part Screened Wet/Wudu Cluster, South Kitchen, SE Dining, East Living & Prayer)",
    LEVEL_LOWER: "3. LOWER FLOOR & EAST GARDEN (South Twin Boys & Girls Rooms, Garden Suite + Seated Ensuite, Garden Lounge, Laundry & Store)",
}

SHORT_ROOM_LABELS = {
    "garage": "TWO CAR BAYS + SHOP",
    "lobby": "6-P UNLOAD",
    "office": "QUIET OFFICE",
    "wc-r": "ROAD WC",
    "plant": "PLANT (1.2m)",
    "stair-r": "CORE 20R",
    "lift-r": "LIFT",
    "entry": "FAMILY ARRIVAL",
    "wc-u": "WC",
    "shower-u": "SHOWER",
    "wudu-u": "WUDU LOBBY",
    "store-u": "STORE",
    "hall-u": "FAMILY LINK / HALL",
    "stair-u": "CORE 20R",
    "lift-u": "LIFT",
    "pantry": "PANTRY",
    "kitchen": "SOUTH KITCHEN",
    "dining": "DINING (6-8)",
    "living": "EAST LIVING",
    "master": "PARENTS / SUITE",
    "closet": "DRESS",
    "ensuite-u": "PRIVATE ENSUITE",
    "hall-l": "FAMILY HALL / SNACK",
    "stair-l": "CORE 20R",
    "lift-l": "LIFT",
    "family": "GARDEN LOUNGE",
    "bed3": "GARDEN SUITE",
    "ensuite-l": "SEATED ENSUITE",
    "boys": "BOYS (2 BEDS)",
    "girls": "GIRLS (2 BEDS)",
    "shower-l": "SHOWER",
    "wc-l": "LOWER WC",
    "laundry": "LAUNDRY / DRYING",
    "store-l": "STORE",
    "sp-deck-east": "EAST ROOF DECK",
    "sp-court-west": "WEST COURT",
    "sp-terrace-north": "NORTH TERRACE",
    "sp-terrace-south": "SOUTH TERRACE",
    "sp-terrace-east": "EAST TERRACE",
    "sp-terrace-lower": "EAST & SOUTH GARDEN TERRACE",
}

ROAD_ASPHALT_Z_M = 1677.6
EXPLORATORY_NOTICE = (
    "EXPLORATORY CONCEPT (Argon C07 — Heavily Based on User Designs 0109-r5 A/B/C & Fixing 0110-r2): "
    "Site is in SITE_NEEDS_VERIFICATION; not structurally, geotechnically, or code certified. True 1:1 scale."
)

USER_DESIGN_SYNTHESIS = [
    {
        "id": "User 0109-r5 Road Floor Architecture + I09 & Rule 2.5 Front Door Fix",
        "user_inspiration": "West-to-East Road Floor sequence: Two Independent Car Bays (two 3.2m west shutters) + dedicated West Front Pedestrian Entrance Foyer (1.20m Front Door) → central Six-Person Unloading with 6 lockers & Lift → East Core Stair (REST 1.40), Replaceable Plant (1.20m door), and SE Quiet Office.",
        "problem_in_user_design": "In 0109-r5, the 5.20×7.70m car bay caused a 0.51 m² clash between the 2nd car's 0.65m door zone and the cabinet, lacked a workshop bench bay, and the pedestrian entrance routed around a dogleg.",
        "argon_c07_resolution": "Preserves the West-to-East Road Floor layout of 0109-r5 with a 5.2×9.4m Two-Car Bay + 1.6×3.0m North Workshop Bay (53.7 m², 0.00 m² door-zone clash) AND a dedicated 1.6m-wide West Front Entrance Foyer (u=0.4..5.6m, v=10.0..11.6m) with a 1.20m Front Door on the West Road façade leading straight east to Unloading, Lift, and Core Stair (Rule 2.5).",
    },
    {
        "id": "User 0109-r5 Option B (Argon C07-B, Recommended) + stmt-021 Right-Sizing & Direct Bedroom Entry",
        "user_inspiration": "Main Floor has West/SW Parents Suite (Bedroom + Dress + Ensuite), North-Center 4-part Screened Wet & Wudu Cluster, South Kitchen, SE Dining (6–8), and wide East Living + NE Reading/Prayer Bay. Lower Floor has West Laundry + Store, North-Center Wet Cluster, South Row of Boys + Girls + Guest Suite, and NE Garden Lounge.",
        "problem_in_user_design": "In earlier C07 drafts: Kitchen (22.1 m²) and Dining (15.4 m²) were oversized while East Living was pinched to 2.2m wide at the south (34.9 m²); West arrival used a 1.6m dogleg; Lower Guest Room in 0109-r5 lacked a seated WC (I10); Wudu to Prayer was 18.55m (I11).",
        "argon_c07_resolution": "Right-sizes South Kitchen to 16.8 m² (4.2×4.0m) and SE Dining to 13.6 m² (3.4×4.0m), expanding East Family Living + NE Reading/Prayer Room to a wide, generous 49.6 m² (4.6–5.2m wide top-to-bottom, Rule 2.6). Places the 1.20m West Arrival Door directly on the West façade of Family Arrival (v=5.6..7.4m, Rule 2.5), gives direct entry from Family Arrival into the Parents Bedroom (never through Dress, Rule 1.5), and includes a 13.0 m² Seated Ensuite on the Lower Guest Suite (I10).",
    },
    {
        "id": "User 0109-r5 Option A (Argon C07-A) + Direct Parents Bedroom Entry & 52.8 m² East Living",
        "user_inspiration": "Main Floor has NW Parents Suite & Walk-in Pantry, SW Kitchen, South-Center Dining (6–8), North-Center 4-part Screened Wet/Wudu Cluster, and wide East Living + NE Reading Bay. Lower Floor has NE Grand Suite + Private Ensuite + Store by Core, Center-East wide Garden Lounge, West Laundry, and South Boys + Girls + SE Wet Cluster.",
        "problem_in_user_design": "In earlier drafts, reaching the NW Parents Bedroom required walking through the Dress closet, Kitchen/Dining were 25.0 m² / 21.1 m² while Living was 31.4 m² (pinched to 2.2m at SE), and Lower SE bathrooms were oversized (12.5 m² WC / 19.8 m² Shower).",
        "argon_c07_resolution": "Parents Bedroom (21.8 m²) opens directly from Family Arrival while Dress (4.0 m²) and Ensuite (5.3 m²) open privately from inside the bedroom (Rule 1.5). Right-sizes Kitchen (16.8 m²) and Dining (14.4 m²) to expand East Family Living to 52.8 m² (5.8–6.6m wide, Rule 2.6), and right-sizes Lower SE WC (6.2 m²) and Shower (8.3 m²) with a stepped SE Garden Terrace (Rule 3.3).",
    },
    {
        "id": "User 0109-r5 Option C (Argon C07-C) + Flush West Arrival & 50.3 m² East Living",
        "user_inspiration": "Compact Upper Day Pavilion (stepped in at SW) with SW Kitchen, South-Center Dining, wide East Living + NE Prayer, and Lower Floor stepping further West (u=2.4..5.6m) for expanded Laundry/Service while NE Suite, Center-East Garden Lounge, and South Boys + Girls face the garden.",
        "problem_in_user_design": "In earlier drafts, the West Arrival door was hidden in a narrow notch behind Upper Store, reaching the NW Bedroom required walking through Dress, and Dining (24.0 m²) + Kitchen (22.1 m²) squeezed East Living to 31.4 m² (2.2m wide at SE).",
        "argon_c07_resolution": "Places Family Arrival flush on the West exterior wall (u=2.4m, v=5.6..7.4m) with a direct 1.20m West Arrival Door (Rule 2.5) and direct entry to the NW Parents Bedroom (Rule 1.5), while right-sizing Kitchen (16.8 m²) and Dining (14.4 m²) so East Family Living is 50.3 m² (4.4–5.0m wide, Rule 2.6).",
    },
]


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
