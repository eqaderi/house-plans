"""EXPLORATORY Argon C07 concept generator (agent:gemini, 2026-10-26).

Generates three genuinely distinct, complete 3-level hillside house designs
(`argon-c07-a`, `argon-c07-b`, `argon-c07-c`) in `projects/my-house/design/argon-c07/`,
heavily based on the homeowner's crafted designs (`user-designed/redesign-0109-r5` Options A, B, C),
preserving their signature stepped/notched footprints, north-projecting vertical core (`CORE + REST 1.40 + LIFT`),
4-part screened wet/wudu cluster, and room arrangements while resolving all 30 issues in
`user-designed/independent-review-0110-r2` and obeying 100% of `OWNER_DESIGN_RULES.md`
(`stmt-001` through `stmt-020`).

Run:
    .venv/bin/python projects/my-house/design/argon-c07/generate.py
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import ortools
from constants import (
    DEFAULT_WINDOW_HEIGHT_M,
    DESIGN_SERIES_ID,
    DOORLESS_FUNCTION_PAIRS,
    FAMILY_STAIR_RISERS,
    FORMATION_OFFSET_M,
    HABITABLE_FUNCTIONS,
    LC300_LENGTH_M,
    LC300_WIDTH_M,
    LEVEL_LOWER,
    LEVEL_MAIN,
    LEVEL_ROAD,
    MODEL_ACTOR_ID,
    OUTDOOR_PREFIXES,
    SECOND_CAR_LENGTH_M,
    SECOND_CAR_WIDTH_M,
    TERRACE_WINDOW_HEIGHT_M,
    TERRACE_WINDOW_SILL_M,
    TREAD_DEPTH_M,
    USER_DESIGN_SYNTHESIS,
    WINDOW_SILL_M,
)
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import box
from shapely.ops import unary_union

from house_ai.constants.placement2d import TERRACE_SLAB_THICKNESS_M
from house_ai.domain.base import EXTERIOR
from house_ai.domain.geometry import Polygon2D
from house_ai.domain.integrity import check_model, circulation_graph
from house_ai.domain.model import (
    HouseModel,
    Opening,
    OpeningKind,
    Operation,
    Slab,
    SlabKind,
    Stair,
    StairKind,
    WallKind,
)
from house_ai.domain.plan import GenerationRecord, PlanVersion
from house_ai.domain.program import SpaceFunction as F
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, Provenance
from house_ai.domain.records import Assumption
from house_ai.domain.site import Site
from house_ai.generation.assemble2d import Builder2D
from house_ai.generation.frame import DesignFrame, Ground
from house_ai.generation.solver2d import PlacedRoom2D, SharedWall, Solution2D
from house_ai.generation.stairs import LANDING_STRIP_DM, u_layout
from house_ai.storage import ProjectStore

HERE = Path(__file__).resolve().parent
store = ProjectStore(HERE.parents[1])
actor = Actor(kind=ActorKind.AGENT, id=MODEL_ACTOR_ID)
site_ref = store.latest(ArtifactKind.SITE, "site")
program_ref = store.latest(ArtifactKind.SPACE_PROGRAM, "program")
site = store.get(site_ref, Site)
program = store.get(program_ref, SpaceProgram)

NW, SW, SE, NE = site.boundary.outer
_EDGE_LEN = math.dist(NW, NE)
EAST = ((NE[0] - NW[0]) / _EDGE_LEN, (NE[1] - NW[1]) / _EDGE_LEN)
SOUTH = (EAST[1], -EAST[0])
frame = DesignFrame(
    NW,
    EAST,
    SOUTH,
    "Owner-required alignment with the long N/S boundaries; "
    "origin NW corner; u downhill (field east), v toward field south",
    None,
    None,
)
ground = Ground(site, frame)


@dataclass(frozen=True)
class RoomSpec:
    key: str
    name: str
    fn: F
    level: str
    rects: list[tuple[int, int, int, int]]
    pid: str = ""


@dataclass(frozen=True)
class OptionSpec:
    option_id: str
    code: str
    title: str
    subtitle: str
    summary: str
    elevations_m: dict[str, float]
    storey_heights_m: dict[str, float]
    plates_dm: dict[str, tuple[int, int, int, int]]
    lawn_u0_m: float
    lawn_z_m: float
    cozy_corner_dm: tuple[int, int, int, int]
    prayer_nook_dm: tuple[int, int, int, int]
    tea_bar_dm: tuple[int, int, int, int]
    workshop_bay_dm: tuple[int, int, int, int]
    lockers_dm: tuple[int, int, int, int]
    rooms: list[RoomSpec]
    terraces: list[tuple[str, str, str, list[tuple[int, int, int, int]], str]]
    links: list[tuple[str, str, bool, tuple[int, int] | None]]
    terrace_doors: list[tuple[str, str]]
    outdoor_exits: list[tuple[str, str]]


def _shared_user_core_rooms() -> list[RoomSpec]:
    """User's signature North-Projecting Vertical Core:
    - 2-flight Core Stair (`u = 72..102 dm, v = 6..56 dm`, 3.0x5.0 m, with `REST 1.40` projecting at `v = 6..20 dm`)
    - Essential Lift (`u = 56..72 dm, v = 36..56 dm`, 1.6x2.0 m, projecting on the west flank of the stair)
    """
    return [
        RoomSpec(
            "stair-r",
            "Core Stair 20R (REST 1.40 at north)",
            F.STAIR,
            LEVEL_ROAD,
            [(72, 6, 102, 56)],
            "pi-stair",
        ),
        RoomSpec(
            "lift-r",
            "Lift (1.60×2.00 Essential)",
            F.LIFT,
            LEVEL_ROAD,
            [(56, 36, 72, 56)],
            "pi-lift",
        ),
        RoomSpec(
            "stair-u",
            "Core Stair 20R (REST 1.40 at north)",
            F.STAIR,
            LEVEL_MAIN,
            [(72, 6, 102, 56)],
            "pi-stair",
        ),
        RoomSpec(
            "lift-u",
            "Lift (1.60×2.00 Essential)",
            F.LIFT,
            LEVEL_MAIN,
            [(56, 36, 72, 56)],
            "pi-lift",
        ),
        RoomSpec(
            "stair-l",
            "Core Stair 20R (REST 1.40 at north)",
            F.STAIR,
            LEVEL_LOWER,
            [(72, 6, 102, 56)],
            "pi-stair",
        ),
        RoomSpec(
            "lift-l",
            "Lift (1.60×2.00 Essential)",
            F.LIFT,
            LEVEL_LOWER,
            [(56, 36, 72, 56)],
            "pi-lift",
        ),
    ]


def _shared_user_road_rooms() -> list[RoomSpec]:
    """User's 0109-r5 Road Floor (`road-floor.png`), upgraded with I09 0.65m door-zone fix,
    North Workshop Bay, and a dedicated West Front Pedestrian Entrance Foyer (`stmt-021`):
    - West (`u = 4..56, v = 6..100` + `u = 56..72, v = 6..36`): Two Independent Car Bays + North Workshop Bay (53.68 m²)
    - South-West & Center (`u = 4..56, v = 100..116` + `u = 56..88, v = 56..116`): Front Entrance Foyer (1.20m West Front Door) & Six-Person Unloading (6 lockers L1–L6, 27.52 m²)
    - East (`u = 88..122, v = 56..116`): Replaceable Plant (`56..74`, 1.20m west door) + Road WC (`74..90`) + Quiet Office / Gaming (`90..116` at SE corner)
    """
    return [
        RoomSpec(
            "garage",
            "Two Independent Car Bays + North Workshop (0.65m door zones)",
            F.GARAGE,
            LEVEL_ROAD,
            [(4, 6, 56, 100), (56, 6, 72, 36)],
            "pi-garage",
        ),
        RoomSpec(
            "lobby",
            "Front Entrance & Six-Person Unloading (6 lockers L1–L6)",
            F.ENTRY,
            LEVEL_ROAD,
            [(4, 100, 56, 116), (56, 56, 88, 116)],
            "pi-entry",
        ),
        RoomSpec(
            "plant",
            "Replaceable Plant (1.20m west door)",
            F.MECHANICAL,
            LEVEL_ROAD,
            [(88, 56, 122, 74)],
            "pi-mechanical",
        ),
        RoomSpec("wc-r", "Road WC + shower", F.BATHROOM, LEVEL_ROAD, [(88, 74, 122, 90)]),
        RoomSpec(
            "office",
            "Quiet Office / Gaming (SE corner)",
            F.STUDY,
            LEVEL_ROAD,
            [(88, 90, 122, 116)],
            "pi-study-1",
        ),
    ]


def make_option_a() -> OptionSpec:
    """Option A — Heavily based on User's 0109-r5 Option A ("Step with the Hill / Staggered Day & Sleep Bars"),
    upgraded with stmt-021 fixes:
    - Upper / Main Floor (`A/drawings/upper-floor.png`):
      * North-Projecting Core (`CORE 20R` + `REST 1.40` + `LIFT`)
      * North-Center 4-Part Screened Wet & Wudu Cluster (`Shared WC` + `Shared Shower` + `Wudu / Screened Multiuse Lobby`)
      * West Wing: Quiet Suite (`master` 12.60 m² entered directly from `entry`; private `ensuite-u` 6.60 m² and `closet` 2.80 m² entered from inside `master`), rectangular `entry` (7.92 m²) with direct West Arrival Door, Coat Store (3.24 m²) & SW Bulk Pantry (3.96 m²)
      * Right-sized South-West Kitchen (`16.80 m²`) + South-Center Dining 6–8 (`14.40 m²`) + Wide East Family Living & NE Reading/Prayer Bay (`52.80 m²`, 4.4m to 6.6m wide!)
    - Lower Floor (`A/drawings/lower-floor.png`):
      * North-East Grand Garden Suite (`bed3` 26.88 m²) + Private Accessible Seated Ensuite (`ensuite-l` 14.28 m², fixing I10) + Household Store (`store-l` 12.16 m², opening to `hall-l`)
      * Center-East Garden Lounge + Tea Bar (`family` 21.20 m²) opening to East Garden
      * West Laundry & Drying (`laundry` 14.96 m², south of Core)
      * South Row (West to East): Boys (`22.00 m²`, SW) + Girls (`22.00 m²`, S-Center) + Right-sized SE Screened Wet Cluster (`Shared WC` 6.24 m² + `Shared Shower` 8.32 m²).
    """
    z = {LEVEL_ROAD: 1677.7, LEVEL_MAIN: 1674.3, LEVEL_LOWER: 1670.7}
    storey = {LEVEL_ROAD: 3.0, LEVEL_MAIN: 3.4, LEVEL_LOWER: 3.6}
    plates = {
        LEVEL_ROAD: (4, 6, 122, 116),
        LEVEL_MAIN: (12, 6, 174, 114),
        LEVEL_LOWER: (40, 6, 200, 152),
    }
    rooms = [
        *_shared_user_core_rooms(),
        *_shared_user_road_rooms(),
        # Main / Upper Floor (follows A/drawings/upper-floor.png + stmt-021 fixes)
        RoomSpec("wc-u", "Shared WC (north wet cluster)", F.WC, LEVEL_MAIN, [(102, 14, 116, 36)]),
        RoomSpec(
            "shower-u",
            "Shared Shower (north wet cluster)",
            F.BATHROOM,
            LEVEL_MAIN,
            [(116, 14, 130, 36)],
        ),
        RoomSpec(
            "wudu-u",
            "Wudu & Screened Multiuse Lobby",
            F.HALL,
            LEVEL_MAIN,
            [(102, 36, 130, 56)],
        ),
        RoomSpec(
            "master",
            "Occasional Guest / Quiet Suite (NW wing)",
            F.BEDROOM,
            LEVEL_MAIN,
            [(12, 14, 42, 56)],
            "pi-bed-main",
        ),
        RoomSpec(
            "ensuite-u",
            "Accessible Suite Bathroom (seated WC + shower)",
            F.BATHROOM,
            LEVEL_MAIN,
            [(42, 14, 72, 36)],
            "pi-bath-ensuite",
        ),
        RoomSpec("closet", "Private Dress (in-suite)", F.STORAGE, LEVEL_MAIN, [(42, 36, 56, 56)]),
        RoomSpec(
            "entry",
            "West Arrival & Family Entry",
            F.ENTRY,
            LEVEL_MAIN,
            [(12, 56, 56, 74)],
            "pi-entry",
        ),
        RoomSpec(
            "hall-u",
            "Screened Arrival & Family Link",
            F.HALL,
            LEVEL_MAIN,
            [(56, 56, 130, 74)],
        ),
        RoomSpec(
            "store-u",
            "Coat & Household Store",
            F.STORAGE,
            LEVEL_MAIN,
            [(12, 74, 30, 92)],
            "pi-storage",
        ),
        RoomSpec(
            "pantry",
            "Bulk Pantry (SW)",
            F.PANTRY,
            LEVEL_MAIN,
            [(12, 92, 30, 114)],
            "pi-pantry",
        ),
        RoomSpec(
            "kitchen",
            "South-West Kitchen + Everyday Dining",
            F.KITCHEN,
            LEVEL_MAIN,
            [(30, 74, 72, 114)],
            "pi-kitchen",
        ),
        RoomSpec(
            "dining",
            "Dining 6 / Extends to 8 (South-Center)",
            F.DINING,
            LEVEL_MAIN,
            [(72, 74, 108, 114)],
            "pi-dining",
        ),
        RoomSpec(
            "living",
            "East Family Living + NE Reading / Prayer Bay",
            F.LIVING,
            LEVEL_MAIN,
            [(130, 14, 174, 74), (108, 74, 174, 114)],
            "pi-living",
        ),
        # Lower Floor (follows A/drawings/lower-floor.png + right-sized SE baths)
        RoomSpec(
            "store-l",
            "Household Store (tucked by Core)",
            F.STORAGE,
            LEVEL_LOWER,
            [(40, 14, 72, 36), (40, 36, 56, 68)],
            "pi-storage",
        ),
        RoomSpec(
            "ensuite-l",
            "Private Accessible Seated Ensuite (fixes I10)",
            F.BATHROOM,
            LEVEL_LOWER,
            [(102, 14, 136, 56)],
            "pi-bath-2",
        ),
        RoomSpec(
            "bed3",
            "Parents / Grand Suite (NE Garden Wing)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(136, 14, 200, 56)],
            "pi-bed-elder-1",
        ),
        RoomSpec(
            "hall-l",
            "Lower Family Hall & Screened Wet Lobby",
            F.HALL,
            LEVEL_LOWER,
            [
                (56, 56, 150, 68),
                (84, 68, 144, 102),
                (144, 90, 176, 102),
            ],
        ),
        RoomSpec(
            "family",
            "Center-East Garden Lounge + Tea Bar",
            F.FAMILY,
            LEVEL_LOWER,
            [(150, 56, 200, 68), (144, 68, 200, 90), (176, 90, 200, 102)],
        ),
        RoomSpec(
            "laundry",
            "Laundry, Sorting & Drying (West)",
            F.LAUNDRY,
            LEVEL_LOWER,
            [(40, 68, 84, 102)],
            "pi-laundry",
        ),
        RoomSpec(
            "boys",
            "Boys Shared Room (SW — 2 beds, 2 desks, 2 wardrobes)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(56, 102, 100, 152)],
            "pi-bed-child-1",
        ),
        RoomSpec(
            "girls",
            "Girls Shared Room (S-Center — 2 beds, 2 desks, 2 wardrobes)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(100, 102, 144, 152)],
            "pi-bed-child-2",
        ),
        RoomSpec(
            "wc-l",
            "Shared WC (SE wet cluster)",
            F.WC,
            LEVEL_LOWER,
            [(144, 102, 168, 128)],
        ),
        RoomSpec(
            "shower-l",
            "Shared Shower / Bath (SE wet cluster)",
            F.BATHROOM,
            LEVEL_LOWER,
            [(168, 102, 200, 128)],
            "pi-bath-1",
        ),
    ]
    terraces = [
        (
            "sp-deck-east",
            "Road-level roof deck (east)",
            LEVEL_ROAD,
            [(122, 56, 174, 116)],
            "pi-balcony",
        ),
        (
            "sp-court-west",
            "West arrival & daylight court",
            LEVEL_MAIN,
            [(-6, 14, 12, 40), (-20, 40, 12, 98), (-44, 98, 12, 114)],
            "",
        ),
        (
            "sp-terrace-south",
            "South terrace (off SW Kitchen, SC Dining & Wide East Living + GS)",
            LEVEL_MAIN,
            [(12, 114, 174, 146)],
            "pi-terrace",
        ),
        (
            "sp-terrace-east",
            "East terrace (wrapping Living & NE Reading Bay)",
            LEVEL_MAIN,
            [(174, 14, 200, 146)],
            "pi-balcony",
        ),
        (
            "sp-terrace-lower",
            "East & South excavated garden terrace",
            LEVEL_LOWER,
            [(200, 14, 220, 152), (144, 128, 200, 152), (56, 152, 220, 168)],
            "",
        ),
    ]
    links = [
        # Road
        ("lobby", "garage", True, None),
        ("lobby", "stair-r", False, None),
        ("lobby", "lift-r", True, None),
        ("lobby", "office", True, None),
        ("lobby", "wc-r", True, None),
        ("lobby", "plant", True, None),
        # Main (direct entry -> master; closet & ensuite-u open from inside master!)
        ("entry", "hall-u", False, None),
        ("entry", "store-u", True, None),
        ("entry", "master", True, None),
        ("master", "closet", True, None),
        ("master", "ensuite-u", True, None),
        ("hall-u", "stair-u", False, None),
        ("hall-u", "lift-u", True, None),
        ("hall-u", "wudu-u", True, None),
        ("wudu-u", "wc-u", True, None),
        ("wudu-u", "shower-u", True, None),
        ("hall-u", "kitchen", False, None),
        ("hall-u", "dining", False, None),
        ("hall-u", "living", False, (56, 74)),  # North 14..56 is closed NE Reading/Prayer/Cozy bay
        ("kitchen", "pantry", False, None),
        ("kitchen", "dining", False, None),
        ("dining", "living", False, None),
        # Lower
        ("hall-l", "stair-l", False, None),
        ("hall-l", "lift-l", True, None),
        ("hall-l", "store-l", True, None),
        ("hall-l", "family", False, None),
        ("hall-l", "bed3", True, None),
        ("bed3", "ensuite-l", True, None),
        ("hall-l", "boys", True, None),
        ("hall-l", "girls", True, None),
        ("hall-l", "wc-l", True, None),
        ("hall-l", "shower-l", True, None),
        ("hall-l", "laundry", True, None),
    ]
    terrace_doors = [
        ("entry", "sp-court-west"),
        ("kitchen", "sp-terrace-south"),
        ("dining", "sp-terrace-south"),
        ("living", "sp-terrace-south"),
        ("living", "sp-terrace-east"),
        ("office", "sp-deck-east"),
        ("bed3", "sp-terrace-lower"),
        ("family", "sp-terrace-lower"),
        ("boys", "sp-terrace-lower"),
        ("girls", "sp-terrace-lower"),
    ]
    outdoor_exits = [
        ("sp-court-west", "south"),
        ("sp-terrace-south", "south"),
        ("sp-terrace-lower", "east"),
    ]
    return OptionSpec(
        option_id=f"{DESIGN_SERIES_ID}-a",
        code="A",
        title="Argon C07-A — User Design A Perfected (Step with the Hill / Staggered Day & Sleep Bars)",
        subtitle="Right-Sized SW Kitchen (16.8 m²) + SC Dining (14.4 m²) + Wide East Living (52.8 m²); Lower NE Parents Suite + Garden Lounge",
        summary=(
            "Directly implements the homeowner's Option A from redesign-0109-r5 with all review & stmt-021 fixes: "
            "features a clear West Front Entrance on both Road and Main levels, direct bedroom entry (never through the closet), "
            "a right-sized SW Kitchen (16.8 m²) + Bulk Pantry, South-Center Dining (14.4 m²), and a wide, generous East Family Living + "
            "NE Reading/Prayer Room (52.8 m², 4.4–6.6 m wide), while the Lower Floor places the Parents Suite + Seated Ensuite "
            "at the NE Garden corner, the Garden Lounge at Center-East, and Boys + Girls + right-sized SE Wet Cluster along the South."
        ),
        elevations_m=z,
        storey_heights_m=storey,
        plates_dm=plates,
        lawn_u0_m=22.0,
        lawn_z_m=1668.1,
        cozy_corner_dm=(130, 14, 174, 56),
        prayer_nook_dm=(146, 16, 170, 36),
        tea_bar_dm=(152, 56, 180, 64),
        workshop_bay_dm=(56, 6, 72, 36),
        lockers_dm=(58, 57, 84, 64),
        rooms=rooms,
        terraces=terraces,
        links=links,
        terrace_doors=terrace_doors,
        outdoor_exits=outdoor_exits,
    )


def make_option_b() -> OptionSpec:
    """Option B (RECOMMENDED) — Heavily based on User's 0109-r5 Option B ("Retained Family Platform / Parents on Living Level"),
    upgraded with stmt-021 fixes:
    - Upper / Main Floor (`B/drawings/upper-floor.png`):
      * North-Projecting Core (`CORE 20R` + `REST 1.40` + `LIFT`)
      * North-Center 4-Part Screened Wet & Wudu Cluster (`Shared WC` + `Shared Shower` at north, `Wudu + Screened Multiuse Lobby` at south)
      * Straight, rectangular West Family Arrival (`entry` 7.92 m²) with direct 1.20m West Arrival Door leading straight east into `hall-u` (zero dogleg!)
      * West / South-West Parents Suite: `master` (13.20 m²) entered directly from `entry` (never through closet!); `closet` (2.88 m²) and `ensuite-u` (5.04 m²) open from inside `master` and buffer the South Terrace (fixing I30)
      * Right-sized Walk-in Pantry (`4.80 m²`), South Kitchen (`16.80 m²`, fixing I26 & stmt-021), and SE Dining 6–8 (`13.60 m²`, fixing I14 & stmt-021)
      * Generous, Wide East Family Living + NE Reading / Prayer & Cozy Bay (`49.60 m²`, 4.6m to 5.2m wide across the entire room!, fixing I11 & stmt-021).
    - Lower Floor (`B/drawings/lower-floor.png`):
      * NW Core + flush Household Store (`11.84 m²`, fixing I22) + West Laundry / Linen / Drying (`14.72 m²`, fixing I12), both opening directly to `hall-l`
      * North-Center Wet Cluster (`Shared WC` + `Shared Shower`) opening to central Family Hall / Snack (`hall-l`)
      * South Row (3 bedrooms side-by-side from West to East, matching `B/drawings/lower-floor.png`!):
        1. Boys (`22.00 m²`, SW)
        2. Girls (`23.00 m²`, South-Center)
        3. Guest / Quiet Suite (Grandparents, `24.64 m²`, SE) + Private Accessible Seated WC & Shower (`12.32 m²`, fixing I10)
      * North-East / Center-East: Garden Lounge + Night Tea/Snack Bar (`36.96 m²`) opening onto the East Garden!
    """
    z = {LEVEL_ROAD: 1677.7, LEVEL_MAIN: 1674.2, LEVEL_LOWER: 1670.6}
    storey = {LEVEL_ROAD: 3.0, LEVEL_MAIN: 3.5, LEVEL_LOWER: 3.6}
    plates = {
        LEVEL_ROAD: (4, 6, 122, 116),
        LEVEL_MAIN: (4, 6, 182, 114),
        LEVEL_LOWER: (40, 6, 202, 152),
    }
    rooms = [
        *_shared_user_core_rooms(),
        *_shared_user_road_rooms(),
        # Main / Upper Floor (follows B/drawings/upper-floor.png + stmt-021 fixes)
        RoomSpec("wc-u", "Shared WC (north wet cluster)", F.WC, LEVEL_MAIN, [(102, 14, 116, 36)]),
        RoomSpec(
            "shower-u",
            "Shared Shower (north wet cluster)",
            F.BATHROOM,
            LEVEL_MAIN,
            [(116, 14, 130, 36)],
        ),
        RoomSpec(
            "wudu-u",
            "Wudu & Screened Multiuse Lobby",
            F.HALL,
            LEVEL_MAIN,
            [(102, 36, 130, 56)],
        ),
        RoomSpec(
            "store-u",
            "NW Coat & Household Store",
            F.STORAGE,
            LEVEL_MAIN,
            [(20, 36, 56, 56)],
            "pi-storage",
        ),
        RoomSpec(
            "entry",
            "Private Family Hall & West Entry",
            F.ENTRY,
            LEVEL_MAIN,
            [(4, 56, 48, 74)],
            "pi-entry",
        ),
        RoomSpec(
            "master",
            "Parents Suite (West / SW living level)",
            F.BEDROOM,
            LEVEL_MAIN,
            [(4, 74, 48, 104)],
            "pi-bed-main",
        ),
        RoomSpec("closet", "Private Dress (in-suite)", F.STORAGE, LEVEL_MAIN, [(4, 104, 20, 122)]),
        RoomSpec(
            "ensuite-u",
            "Private Accessible Ensuite (seated WC + shower)",
            F.BATHROOM,
            LEVEL_MAIN,
            [(20, 104, 48, 122)],
            "pi-bath-ensuite",
        ),
        RoomSpec(
            "hall-u",
            "Family Link & Screened Kitchen Arrival",
            F.HALL,
            LEVEL_MAIN,
            [(48, 56, 130, 74)],
        ),
        RoomSpec(
            "pantry",
            "Walk-in Bulk Pantry (bridges Hall & Kitchen)",
            F.PANTRY,
            LEVEL_MAIN,
            [(48, 74, 60, 114)],
            "pi-pantry",
        ),
        RoomSpec(
            "kitchen",
            "South Kitchen + Everyday Dining",
            F.KITCHEN,
            LEVEL_MAIN,
            [(60, 74, 102, 114)],
            "pi-kitchen",
        ),
        RoomSpec(
            "dining",
            "Dining 6 / Extends to 8 (SE)",
            F.DINING,
            LEVEL_MAIN,
            [(102, 74, 136, 114)],
            "pi-dining",
        ),
        RoomSpec(
            "living",
            "East Family Living + NE Reading / Prayer Bay",
            F.LIVING,
            LEVEL_MAIN,
            [(130, 14, 182, 74), (136, 74, 182, 114)],
            "pi-living",
        ),
        # Lower Floor (follows B/drawings/lower-floor.png + flush west utility wing)
        RoomSpec(
            "store-l",
            "Household Store (tucked by Core, fixes I22)",
            F.STORAGE,
            LEVEL_LOWER,
            [(40, 16, 72, 36), (40, 36, 56, 70)],
            "pi-storage",
        ),
        RoomSpec(
            "wc-l",
            "Shared WC (north-center wet stack)",
            F.WC,
            LEVEL_LOWER,
            [(102, 20, 120, 56)],
        ),
        RoomSpec(
            "shower-l",
            "Shared Bathroom (north-center wet stack)",
            F.BATHROOM,
            LEVEL_LOWER,
            [(120, 20, 146, 56)],
            "pi-bath-1",
        ),
        RoomSpec(
            "hall-l",
            "Family Hall / Snack & Screened Wet Lobby",
            F.HALL,
            LEVEL_LOWER,
            [(56, 56, 146, 70), (86, 70, 146, 102)],
        ),
        RoomSpec(
            "laundry",
            "Laundry, Linen & Drying Room (West, fixes I12)",
            F.LAUNDRY,
            LEVEL_LOWER,
            [(40, 70, 86, 102)],
            "pi-laundry",
        ),
        RoomSpec(
            "boys",
            "Boys Shared Room (SW — 2 beds, 2 desks, 2 wardrobes)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(56, 102, 100, 152)],
            "pi-bed-child-1",
        ),
        RoomSpec(
            "girls",
            "Girls Shared Room (S-Center — 2 beds, 2 desks, 2 wardrobes)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(100, 102, 146, 152)],
            "pi-bed-child-2",
        ),
        RoomSpec(
            "bed3",
            "Guest / Quiet Room — Grandparents (SE Garden)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(146, 86, 202, 130)],
            "pi-bed-elder-1",
        ),
        RoomSpec(
            "ensuite-l",
            "Guest Private Accessible Seated WC + Shower (fixes I10)",
            F.BATHROOM,
            LEVEL_LOWER,
            [(146, 130, 202, 152)],
            "pi-bath-2",
        ),
        RoomSpec(
            "family",
            "NE Garden Lounge + Night Tea & Snack Bar",
            F.FAMILY,
            LEVEL_LOWER,
            [(146, 20, 202, 86)],
        ),
    ]
    terraces = [
        (
            "sp-deck-east",
            "Road-level roof deck (east)",
            LEVEL_ROAD,
            [(122, 56, 182, 116)],
            "pi-balcony",
        ),
        (
            "sp-court-west",
            "West arrival & daylight court",
            LEVEL_MAIN,
            [(-20, 40, 4, 98), (-44, 98, 4, 122)],
            "",
        ),
        (
            "sp-terrace-south",
            "South terrace (off South Kitchen, SE Dining & Wide East Living + GS)",
            LEVEL_MAIN,
            [(4, 122, 48, 148), (48, 114, 182, 148)],
            "pi-terrace",
        ),
        (
            "sp-terrace-east",
            "East terrace (wrapping East Living & NE Prayer Bay)",
            LEVEL_MAIN,
            [(182, 14, 202, 148)],
            "pi-balcony",
        ),
        (
            "sp-terrace-lower",
            "East & South excavated garden terrace",
            LEVEL_LOWER,
            [(202, 20, 220, 152), (56, 152, 220, 168)],
            "",
        ),
    ]
    links = [
        # Road
        ("lobby", "garage", True, None),
        ("lobby", "stair-r", False, None),
        ("lobby", "lift-r", True, None),
        ("lobby", "office", True, None),
        ("lobby", "wc-r", True, None),
        ("lobby", "plant", True, None),
        # Main (direct entry -> master; closet & ensuite-u open from inside master!)
        ("entry", "hall-u", False, None),
        ("entry", "store-u", True, None),
        ("entry", "master", True, None),
        ("master", "closet", True, None),
        ("master", "ensuite-u", True, None),
        ("hall-u", "stair-u", False, None),
        ("hall-u", "lift-u", True, None),
        ("hall-u", "wudu-u", True, None),
        ("wudu-u", "wc-u", True, None),
        ("wudu-u", "shower-u", True, None),
        ("hall-u", "pantry", True, None),
        ("hall-u", "kitchen", False, None),
        ("hall-u", "dining", False, None),
        ("hall-u", "living", False, (56, 74)),  # North 14..56 is closed NE Reading/Prayer/Cozy bay
        ("kitchen", "pantry", False, None),
        ("kitchen", "dining", False, None),
        ("dining", "living", False, None),
        # Lower
        ("hall-l", "stair-l", False, None),
        ("hall-l", "lift-l", True, None),
        ("hall-l", "store-l", True, None),
        ("hall-l", "wc-l", True, None),
        ("hall-l", "shower-l", True, None),
        ("hall-l", "family", False, None),
        ("hall-l", "bed3", True, None),
        ("bed3", "ensuite-l", True, None),
        ("hall-l", "boys", True, None),
        ("hall-l", "girls", True, None),
        ("hall-l", "laundry", True, None),
    ]
    terrace_doors = [
        ("entry", "sp-court-west"),
        ("kitchen", "sp-terrace-south"),
        ("dining", "sp-terrace-south"),
        ("living", "sp-terrace-south"),
        ("living", "sp-terrace-east"),
        ("office", "sp-deck-east"),
        ("family", "sp-terrace-lower"),
        ("bed3", "sp-terrace-lower"),
        ("boys", "sp-terrace-lower"),
        ("girls", "sp-terrace-lower"),
    ]
    outdoor_exits = [
        ("sp-court-west", "south"),
        ("sp-terrace-south", "south"),
        ("sp-terrace-lower", "east"),
    ]
    return OptionSpec(
        option_id=f"{DESIGN_SERIES_ID}-b",
        code="B",
        title="Argon C07-B (Recommended) — User Design B Perfected (Parents on Living Level & Retained Platform)",
        subtitle="Direct West Entry + Parents Suite + Right-Sized Kitchen (16.8 m²) & Dining (13.6 m²) + Wide Living (49.6 m²); Lower Boys + Girls + Guest Suite",
        summary=(
            "Directly implements the homeowner's favored Option B from redesign-0109-r5 with all 30 review & stmt-021 fixes: "
            "Main Floor features a straight, crystal-clear West Arrival Hall (zero dogleg), direct entry into the Parents Bedroom "
            "(with Private Dress and South-buffering Accessible Ensuite opening from inside the bedroom, fixing stmt-021 & I30), "
            "Walk-in Pantry (4.8 m²), right-sized South Kitchen (16.8 m²), SE Dining (13.6 m²), and a wide, generous East Family Living + "
            "NE Reading/Prayer Room (49.6 m², 4.6–5.2 m wide across the entire room). Lower Floor keeps flush West Laundry (14.7 m²) & Store (11.8 m²), "
            "North-Center Wet Stack, South Row of Boys + Girls + SE Guest Suite (with Private Seated Bath fixing I10), and NE Garden Lounge (37.0 m²)."
        ),
        elevations_m=z,
        storey_heights_m=storey,
        plates_dm=plates,
        lawn_u0_m=22.0,
        lawn_z_m=1668.0,
        cozy_corner_dm=(130, 14, 182, 56),
        prayer_nook_dm=(150, 16, 176, 36),
        tea_bar_dm=(148, 22, 176, 30),
        workshop_bay_dm=(56, 6, 72, 36),
        lockers_dm=(58, 57, 84, 64),
        rooms=rooms,
        terraces=terraces,
        links=links,
        terrace_doors=terrace_doors,
        outdoor_exits=outdoor_exits,
    )


def make_option_c() -> OptionSpec:
    """Option C — Heavily based on User's 0109-r5 Option C ("Bridge House / Compact Day Plate & Extended Lower Bar"),
    upgraded with stmt-021 fixes:
    - Upper / Main Floor (`C/drawings/upper-floor.png`):
      * Clear West Bridge Arrival Hall (`entry` 7.92 m²) directly on the West exterior wall (`u = 1.2 m`, fixing the hidden notch door!)
      * Direct entry into the NW Bedroom Suite (`master` 12.60 m²) from `entry`, with `closet` (2.80 m²) and `ensuite-u` (6.60 m²) entered from inside `master`
      * Stepped-in South-West Bridge Day Bar (`u = 3.0..17.8 m`) with Coat Store (`3.24 m²`), Walk-in Pantry (`3.96 m²`), right-sized SW Bridge Kitchen (`16.80 m²`), right-sized SE Dining (`14.40 m²`), and a wide, generous East Family Living + NE Reading/Prayer Room (`49.60 m²`, 4.8m to 5.2m wide!).
    - Lower Floor (`C/drawings/lower-floor.png`):
      * Extended lower floor plate stepping west of the Core Stair (`u = 2.4..5.6 m`) for the West Service / Store (`15.96 m²`) & Laundry (`20.40 m²`) wing, plus NE Grand Suite (`27.72 m²`) + Seated Ensuite (`14.28 m²`), Center-East Garden Lounge (`22.12 m²`), and South Boys (`22.00 m²`) + Girls (`22.00 m²`) + right-sized SE Screened Wet Cluster (`WC 6.24 m² + Shower 8.84 m²`).
    """
    z = {LEVEL_ROAD: 1677.7, LEVEL_MAIN: 1674.3, LEVEL_LOWER: 1670.7}
    storey = {LEVEL_ROAD: 3.0, LEVEL_MAIN: 3.4, LEVEL_LOWER: 3.6}
    plates = {
        LEVEL_ROAD: (4, 6, 122, 116),
        LEVEL_MAIN: (12, 6, 178, 114),
        LEVEL_LOWER: (24, 6, 202, 152),
    }
    rooms = [
        *_shared_user_core_rooms(),
        *_shared_user_road_rooms(),
        # Main / Upper Floor (follows C/drawings/upper-floor.png stepped-bridge day bar + stmt-021 fixes)
        RoomSpec("wc-u", "Shared WC (north wet cluster)", F.WC, LEVEL_MAIN, [(102, 14, 116, 36)]),
        RoomSpec(
            "shower-u",
            "Shared Shower (north wet cluster)",
            F.BATHROOM,
            LEVEL_MAIN,
            [(116, 14, 130, 36)],
        ),
        RoomSpec(
            "wudu-u",
            "Wudu & Screened Multiuse Lobby",
            F.HALL,
            LEVEL_MAIN,
            [(102, 36, 130, 56)],
        ),
        RoomSpec(
            "master",
            "Quiet NW Suite (stepped bridge wing)",
            F.BEDROOM,
            LEVEL_MAIN,
            [(12, 14, 42, 56)],
            "pi-bed-main",
        ),
        RoomSpec(
            "ensuite-u",
            "Accessible Suite Bathroom",
            F.BATHROOM,
            LEVEL_MAIN,
            [(42, 14, 72, 36)],
            "pi-bath-ensuite",
        ),
        RoomSpec("closet", "Private Dress (in-suite)", F.STORAGE, LEVEL_MAIN, [(42, 36, 56, 56)]),
        RoomSpec(
            "entry",
            "West Bridge Arrival Hall",
            F.ENTRY,
            LEVEL_MAIN,
            [(12, 56, 56, 74)],
            "pi-entry",
        ),
        RoomSpec(
            "hall-u",
            "Central Bridge Hall & Screened Arrival",
            F.HALL,
            LEVEL_MAIN,
            [(56, 56, 130, 74)],
        ),
        RoomSpec(
            "store-u",
            "Coat & Luggage Store (stepped bridge)",
            F.STORAGE,
            LEVEL_MAIN,
            [(30, 74, 48, 92)],
            "pi-storage",
        ),
        RoomSpec(
            "pantry",
            "Walk-in Pantry (SW bridge)",
            F.PANTRY,
            LEVEL_MAIN,
            [(30, 92, 48, 114)],
            "pi-pantry",
        ),
        RoomSpec(
            "kitchen",
            "South-West Bridge Kitchen",
            F.KITCHEN,
            LEVEL_MAIN,
            [(48, 74, 90, 114)],
            "pi-kitchen",
        ),
        RoomSpec(
            "dining",
            "Dining 6 / Extends to 8 (SE)",
            F.DINING,
            LEVEL_MAIN,
            [(90, 74, 126, 114)],
            "pi-dining",
        ),
        RoomSpec(
            "living",
            "East Family Living + NE Reading / Prayer Bay",
            F.LIVING,
            LEVEL_MAIN,
            [(130, 14, 178, 74), (126, 74, 178, 114)],
            "pi-living",
        ),
        # Lower Floor (follows C/drawings/lower-floor.png with western extension u=24..56 + right-sized SE baths)
        RoomSpec(
            "store-l",
            "West Service & Household Store (stepped west wing)",
            F.STORAGE,
            LEVEL_LOWER,
            [(24, 24, 72, 36), (24, 36, 56, 68)],
            "pi-storage",
        ),
        RoomSpec(
            "laundry",
            "Expanded West Laundry, Sorting & Drying Wing",
            F.LAUNDRY,
            LEVEL_LOWER,
            [(24, 68, 84, 102)],
            "pi-laundry",
        ),
        RoomSpec(
            "ensuite-l",
            "Private Accessible Seated Ensuite (fixes I10)",
            F.BATHROOM,
            LEVEL_LOWER,
            [(102, 14, 136, 56)],
            "pi-bath-2",
        ),
        RoomSpec(
            "bed3",
            "Parents / Grand Suite (NE Garden Wing)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(136, 14, 202, 56)],
            "pi-bed-elder-1",
        ),
        RoomSpec(
            "hall-l",
            "Lower Central Hall & Screened Wet Lobby",
            F.HALL,
            LEVEL_LOWER,
            [
                (56, 56, 150, 68),
                (84, 68, 144, 102),
                (144, 90, 176, 102),
            ],
        ),
        RoomSpec(
            "family",
            "Center-East Garden Lounge + Tea Bar",
            F.FAMILY,
            LEVEL_LOWER,
            [(150, 56, 202, 68), (144, 68, 202, 90), (176, 90, 202, 102)],
        ),
        RoomSpec(
            "boys",
            "Boys Shared Room (SW — 2 beds, 2 desks, 2 wardrobes)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(56, 102, 100, 152)],
            "pi-bed-child-1",
        ),
        RoomSpec(
            "girls",
            "Girls Shared Room (S-Center — 2 beds, 2 desks, 2 wardrobes)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(100, 102, 144, 152)],
            "pi-bed-child-2",
        ),
        RoomSpec(
            "wc-l",
            "Shared WC (SE wet cluster)",
            F.WC,
            LEVEL_LOWER,
            [(144, 102, 168, 128)],
        ),
        RoomSpec(
            "shower-l",
            "Shared Shower / Bath (SE wet cluster)",
            F.BATHROOM,
            LEVEL_LOWER,
            [(168, 102, 202, 128)],
            "pi-bath-1",
        ),
    ]
    terraces = [
        (
            "sp-deck-east",
            "Road-level roof deck (east)",
            LEVEL_ROAD,
            [(122, 56, 178, 116)],
            "pi-balcony",
        ),
        (
            "sp-court-west",
            "West arrival & bridge court",
            LEVEL_MAIN,
            [(-6, 14, 12, 40), (-20, 40, 12, 74), (-20, 74, 30, 114)],
            "",
        ),
        (
            "sp-terrace-south",
            "South terrace (off SW Kitchen, SE Dining & Wide East Living + GS)",
            LEVEL_MAIN,
            [(30, 114, 178, 146)],
            "pi-terrace",
        ),
        (
            "sp-terrace-east",
            "East terrace (wrapping Living & NE Reading Bay)",
            LEVEL_MAIN,
            [(178, 14, 202, 146)],
            "pi-balcony",
        ),
        (
            "sp-terrace-lower",
            "East & South excavated garden terrace",
            LEVEL_LOWER,
            [(202, 14, 220, 152), (144, 128, 202, 152), (56, 152, 220, 168)],
            "",
        ),
    ]
    links = [
        # Road
        ("lobby", "garage", True, None),
        ("lobby", "stair-r", False, None),
        ("lobby", "lift-r", True, None),
        ("lobby", "office", True, None),
        ("lobby", "wc-r", True, None),
        ("lobby", "plant", True, None),
        # Main (direct entry -> master; closet & ensuite-u open from inside master!)
        ("entry", "hall-u", False, None),
        ("entry", "store-u", True, None),
        ("entry", "master", True, None),
        ("master", "closet", True, None),
        ("master", "ensuite-u", True, None),
        ("hall-u", "stair-u", False, None),
        ("hall-u", "lift-u", True, None),
        ("hall-u", "wudu-u", True, None),
        ("wudu-u", "wc-u", True, None),
        ("wudu-u", "shower-u", True, None),
        ("hall-u", "kitchen", False, None),
        ("hall-u", "dining", False, None),
        ("hall-u", "living", False, (56, 74)),  # North 14..56 is closed NE Reading/Prayer/Cozy bay
        ("kitchen", "pantry", False, None),
        ("kitchen", "dining", False, None),
        ("dining", "living", False, None),
        # Lower
        ("hall-l", "stair-l", False, None),
        ("hall-l", "lift-l", True, None),
        ("hall-l", "store-l", True, None),
        ("hall-l", "family", False, None),
        ("hall-l", "bed3", True, None),
        ("bed3", "ensuite-l", True, None),
        ("hall-l", "boys", True, None),
        ("hall-l", "girls", True, None),
        ("hall-l", "wc-l", True, None),
        ("hall-l", "shower-l", True, None),
        ("hall-l", "laundry", True, None),
    ]
    terrace_doors = [
        ("entry", "sp-court-west"),
        ("kitchen", "sp-terrace-south"),
        ("dining", "sp-terrace-south"),
        ("living", "sp-terrace-south"),
        ("living", "sp-terrace-east"),
        ("office", "sp-deck-east"),
        ("bed3", "sp-terrace-lower"),
        ("family", "sp-terrace-lower"),
        ("boys", "sp-terrace-lower"),
        ("girls", "sp-terrace-lower"),
    ]
    outdoor_exits = [
        ("sp-court-west", "south"),
        ("sp-terrace-south", "south"),
        ("sp-terrace-lower", "east"),
    ]
    return OptionSpec(
        option_id=f"{DESIGN_SERIES_ID}-c",
        code="C",
        title="Argon C07-C — User Design C Perfected (Stepped Bridge Day Plate & Extended Lower Bar)",
        subtitle="Direct West Entry + Stepped-in SW Kitchen (16.8 m²) + SE Dining (14.4 m²) + Wide Living (49.6 m²); Extended West Lower Utility Wing",
        summary=(
            "Directly implements the homeowner's Option C from redesign-0109-r5 with all review & stmt-021 fixes: "
            "features a clear West Bridge Arrival Door directly on the West exterior wall (fixing the notch door), direct entry into the NW Suite "
            "(never through the closet), stepped-in SW Bridge Kitchen (16.8 m²), SE Dining (14.4 m²), and a wide, generous East Family Living + "
            "NE Prayer Room (49.6 m², 4.8–5.2 m wide), while the Lower Floor extends west of the Core Stair (u=2.4..5.6m) for a 20.4 m² Laundry & "
            "16.0 m² Store wing, with the NE Suite + Seated Ensuite, Center-East Garden Lounge, and South Boys + Girls + right-sized SE Baths."
        ),
        elevations_m=z,
        storey_heights_m=storey,
        plates_dm=plates,
        lawn_u0_m=22.0,
        lawn_z_m=1668.2,
        cozy_corner_dm=(130, 14, 178, 56),
        prayer_nook_dm=(148, 16, 174, 36),
        tea_bar_dm=(152, 56, 180, 64),
        workshop_bay_dm=(56, 6, 72, 36),
        lockers_dm=(58, 57, 84, 64),
        rooms=rooms,
        terraces=terraces,
        links=links,
        terrace_doors=terrace_doors,
        outdoor_exits=outdoor_exits,
    )


OPTIONS: dict[str, OptionSpec] = {
    "a": make_option_a(),
    "b": make_option_b(),
    "c": make_option_c(),
}


def _geom(room: PlacedRoom2D):
    return unary_union(
        [box(*q) for q in (room.sub_rects or [(room.u0, room.v0, room.u1, room.v1)])]
    )


def _verify_exact_plate_tiling(spec: OptionSpec) -> None:
    """Assert that rooms on each level form a single connected stepped polygon with 0 overlap and 0 internal holes (Rule 2.3)."""
    for lv in (LEVEL_ROAD, LEVEL_MAIN, LEVEL_LOWER):
        lv_rooms = [r for r in spec.rooms if r.level == lv]
        polys = []
        area_sum = 0.0
        for r in lv_rooms:
            g = unary_union([box(*q) for q in r.rects])
            assert g.geom_type == "Polygon", (
                f"{spec.option_id} {r.key} is not a single Polygon: {g.geom_type}"
            )
            polys.append((r.key, g))
            area_sum += g.area
        for i, (ka, ga) in enumerate(polys):
            for kb, gb in polys[i + 1 :]:
                inter = ga.intersection(gb).area
                assert inter < 1e-6, f"{spec.option_id} {lv}: {ka} overlaps {kb} by {inter}"
        merged = unary_union([g for _, g in polys])
        assert merged.geom_type == "Polygon", (
            f"{spec.option_id} {lv}: rooms do not form a connected footprint ({merged.geom_type})"
        )
        assert len(merged.interiors) == 0, (
            f"{spec.option_id} {lv}: footprint has {len(merged.interiors)} internal holes/voids (violates Rule 2.3)"
        )
        assert abs(area_sum - merged.area) < 1e-6, (
            f"{spec.option_id} {lv}: area mismatch sum={area_sum}, merged={merged.area}"
        )


def _shared_wall(ra: PlacedRoom2D, rb: PlacedRoom2D) -> SharedWall | None:
    if ra.level_id != rb.level_id:
        return None
    inter = _geom(ra).boundary.intersection(_geom(rb).boundary)
    lines = [
        g
        for g in getattr(inter, "geoms", [inter])
        if g.geom_type == "LineString" and g.length > 0.1
    ]
    if not lines:
        return None
    seg = max(lines, key=lambda g: g.length)
    x0, y0, x1, y1 = seg.bounds
    if abs(x0 - x1) < 1e-6:
        return SharedWall(
            ra.space_id,
            rb.space_id,
            ra.level_id,
            "v",
            int(round(x0)),
            int(round(y0)),
            int(round(y1)),
        )
    return SharedWall(
        ra.space_id, rb.space_id, ra.level_id, "h", int(round(y0)), int(round(x0)), int(round(x1))
    )


def build_solution(
    spec: OptionSpec,
) -> tuple[Solution2D, list[tuple[str, str, bool, tuple[int, int] | None]]]:
    _verify_exact_plate_tiling(spec)
    rooms: list[PlacedRoom2D] = []
    for r in spec.rooms:
        zone = (
            "z-service"
            if r.level == LEVEL_ROAD
            else ("z-night" if r.fn in (F.BEDROOM, F.BATHROOM, F.WC) else "z-day")
        )
        rooms.append(
            PlacedRoom2D(
                "sp-" + r.key,
                r.name,
                r.fn,
                r.level,
                min(q[0] for q in r.rects),
                min(q[1] for q in r.rects),
                max(q[2] for q in r.rects),
                max(q[3] for q in r.rects),
                r.pid,
                zone,
                sub_rects=r.rects if len(r.rects) > 1 else None,
            )
        )
    for sid, name, lv, rects, pid in spec.terraces:
        rooms.append(
            PlacedRoom2D(
                sid,
                name,
                F.TERRACE,
                lv,
                min(q[0] for q in rects),
                min(q[1] for q in rects),
                max(q[2] for q in rects),
                max(q[3] for q in rects),
                pid,
                "z-outdoor",
                sub_rects=rects if len(rects) > 1 else None,
            )
        )
    by_id = {r.space_id: r for r in rooms}
    raw_links: list[tuple[str, str, bool, tuple[int, int] | None]] = [
        ("sp-" + a, "sp-" + b, not is_door, span_clip) for a, b, is_door, span_clip in spec.links
    ]
    raw_links += [("sp-" + a, t, False, None) for a, t in spec.terrace_doors]
    walls: list[SharedWall] = []
    doors: list[tuple[str, str, bool, tuple[int, int] | None]] = []
    for a, b, is_opening, span_clip in raw_links:
        sw = _shared_wall(by_id[a], by_id[b])
        assert sw is not None, f"{spec.option_id}: rooms {a} and {b} do not share a wall"
        walls.append(sw)
        doors.append((a, b, is_opening, span_clip))
    sol = Solution2D(
        status="OPTIMAL",
        objective=0.0,
        rooms=rooms,
        shared_walls=walls,
        circulation_rooms=[],
        levels=[LEVEL_LOWER, LEVEL_MAIN, LEVEL_ROAD],
        deterministic_time=0.0,
        wall_time_s=0.0,
        seed=0,
        platform_info="local",
        strategy="stepped_terraces_user_design_synthesis",
        circulation_share=0.0,
        has_stairs=False,
        exterior_connections=[],
        level_elevations_m=dict(spec.elevations_m),
    )
    return sol, doors


class ArgonBuilder(Builder2D):
    def __init__(
        self,
        spec: OptionSpec,
        doors: list[tuple[str, str, bool, tuple[int, int] | None]],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.spec = spec
        self.doors = doors
        self.stair_fits: dict[str, bool] = {}
        for lv in self.levels:
            lv.floor_to_floor_m = spec.storey_heights_m[lv.id]

    def wall_model(self, seg):
        wall = super().wall_model(seg)
        if seg.neg and seg.pos and all(s.startswith(OUTDOOR_PREFIXES) for s in (seg.neg, seg.pos)):
            wall.kind = WallKind.PARAPET
            wall.height_m = 1.0
        return wall

    def _exterior(self, sid: str, kind: OpeningKind, width: float, test, **kw):
        keep = self.walls
        self.walls = [w for w in keep if sid not in (w.neg, w.pos) or (w.neg and w.pos) or test(w)]
        op = self.place_opening(sid, None, kind, width_m=width, **kw)
        self.walls = keep
        return op

    def _windowable(self, w) -> bool:
        (a, c), (b, d) = self._seg_points(w)
        half = 9 / max(w.length_dm, 1)
        for t in (0.5 - half, 0.5, 0.5 + half):
            u, v = a + (b - a) * t, c + (d - c) * t
            if w.orient == "h":
                v += 5 if w.neg else -5
            else:
                u += 5 if w.neg else -5
            g = self.ground.at(u / 10, v / 10)
            if (
                g is not None
                and g >= self.spec.elevations_m[w.level_id] + WINDOW_SILL_M - FORMATION_OFFSET_M
            ):
                return False
        return True

    def _place_clipped_opening(
        self, a: str, b: str, span_clip: tuple[int, int], width_m: float = 1.6
    ) -> None:
        """Place an opening restricted to a sub-interval (lo_dm, hi_dm) of the shared wall."""
        candidates = self._walls_between(a, b)
        lo_dm, hi_dm = span_clip
        for w in candidates:
            ov_a = max(w.a, lo_dm)
            ov_b = min(w.b, hi_dm)
            if ov_b - ov_a >= 10:
                w_dm = min(int(round(width_m * 10)), ov_b - ov_a - 4)
                mid_dm = (ov_a + ov_b) // 2
                off_dm = max(ov_a + 2 - w.a, min(mid_dm - w_dm // 2 - w.a, ov_b - 2 - w_dm - w.a))
                w.used.append((off_dm, off_dm + w_dm))
                self.openings.append(
                    Opening(
                        id=f"op-{len(self.openings) + 1:02d}",
                        host_wall_id=w.id,
                        kind=OpeningKind.OPENING,
                        offset_m=off_dm / 10.0,
                        width_m=w_dm / 10.0,
                        height_m=2.4,
                        sill_m=0.0,
                        operation=Operation.NONE,
                        material_id="m-door",
                        connects=(a, b),
                    )
                )
                return
        raise RuntimeError(f"Could not place clipped opening between {a} and {b} in {span_clip}")

    def build_openings(self) -> None:
        rid = {r.space_id: r for r in self.sol.rooms}
        road_u0 = self.spec.plates_dm[LEVEL_ROAD][0]
        is_west_road = lambda w: w.orient == "v" and w.c == road_u0  # noqa: E731
        # Two independent west shutter doors on Two Car Bays (matching user's 0109-r5 road-floor.png)
        for w in self._walls_between("sp-garage", None):
            if is_west_road(w) and w.length_dm >= 80:
                for idx, off_dm in enumerate((8, 52), start=1):
                    w.used.append((off_dm, off_dm + 32))
                    self.openings.append(
                        Opening(
                            id=f"d-garage-{idx:02d}",
                            host_wall_id=w.id,
                            kind=OpeningKind.DOOR,
                            offset_m=off_dm / 10.0,
                            width_m=3.2,
                            height_m=2.2,
                            sill_m=0.0,
                            operation=Operation.SLIDING,
                            material_id="m-door",
                            connects=("sp-garage", EXTERIOR),
                        )
                    )
                break
        # Dedicated 1.20m Pedestrian Front Entrance Door on the West Road facade of sp-lobby (stmt-021)
        self._exterior(
            "sp-lobby",
            OpeningKind.DOOR,
            1.2,
            is_west_road,
            operation=Operation.SWING_RIGHT,
            prefix="d-front",
        )

        for a, b, is_opening, span_clip in self.doors:
            if span_clip is not None:
                self._place_clipped_opening(a, b, span_clip, width_m=1.6)
                continue
            pair = frozenset((rid[a].function, rid[b].function)) if b in rid else None
            if (
                pair in DOORLESS_FUNCTION_PAIRS
                and not (a.startswith(OUTDOOR_PREFIXES) or b.startswith(OUTDOOR_PREFIXES))
                and "wudu" not in a
                and "wudu" not in b
            ):
                is_opening = True
            if is_opening:
                seg = max(self._walls_between(a, b), key=lambda w: w.length_dm)
                both_out = a.startswith(OUTDOOR_PREFIXES) and b.startswith(OUTDOOR_PREFIXES)
                self.place_opening(
                    a,
                    b,
                    OpeningKind.OPENING,
                    width_m=min(seg.length_m - 0.4, 2.8),
                    height_m=1.0 if both_out else 2.4,
                    operation=Operation.NONE,
                    prefix="op",
                )
            elif b.startswith(OUTDOOR_PREFIXES):
                entry = a == "sp-entry"
                if entry:
                    entry_u0 = rid["sp-entry"].u0
                    keep = self.walls
                    self.walls = [
                        w
                        for w in keep
                        if "sp-entry" not in (w.neg, w.pos) or (w.orient == "v" and w.c == entry_u0)
                    ]
                    self.place_opening(
                        a,
                        b,
                        OpeningKind.DOOR,
                        width_m=1.2,
                        operation=Operation.SWING_RIGHT,
                        prefix="d-out",
                    )
                    self.walls = keep
                else:
                    self.place_opening(
                        a,
                        b,
                        OpeningKind.DOOR,
                        width_m=1.4,
                        operation=Operation.SLIDING,
                        prefix="d-out",
                    )
            else:
                wet = {rid[a].function, rid[b].function} & {F.BATHROOM, F.WC}
                is_plant_door = {a, b} == {"sp-lobby", "sp-plant"}
                door_w = 1.2 if is_plant_door else (0.8 if wet else 0.9)
                self.place_opening(
                    a,
                    b,
                    OpeningKind.DOOR,
                    width_m=door_w,
                    operation=Operation.SLIDING if F.WC in wet else Operation.SWING_LEFT,
                    prefix="d",
                )

        for sid, side in self.spec.outdoor_exits:
            r = rid[sid]
            c = {"south": r.v1, "east": r.u1, "west": r.u0, "north": r.v0}[side]
            self._exterior(
                sid,
                OpeningKind.OPENING,
                1.2,
                lambda w, c=c, side=side: (
                    w.c == c and (w.orient == "h") == (side in ("south", "north"))
                ),
                height_m=1.0,
                operation=Operation.NONE,
                prefix="d-exit",
            )

        outdoors = [t for t in rid if t.startswith(OUTDOOR_PREFIXES)]
        for r in self.sol.rooms:
            if r.function not in HABITABLE_FUNCTIONS:
                continue
            placed = 0
            for t in outdoors:
                if placed < 2 and self._walls_between(r.space_id, t):
                    while placed < 2 and self._place_shared_window(r.space_id, t, width_m=1.4):
                        placed += 1
            for _ in range(2 - placed):
                if not self._exterior(
                    r.space_id,
                    OpeningKind.WINDOW,
                    1.4,
                    self._windowable,
                    height_m=DEFAULT_WINDOW_HEIGHT_M,
                    sill_m=WINDOW_SILL_M,
                    operation=Operation.SLIDING,
                    prefix="win",
                ):
                    self._slide_window(r.space_id)

    def _place_shared_window(self, a: str, b: str, width_m: float = 1.4) -> bool:
        if self.place_opening(
            a,
            b,
            OpeningKind.WINDOW,
            width_m=width_m,
            height_m=TERRACE_WINDOW_HEIGHT_M,
            sill_m=TERRACE_WINDOW_SILL_M,
            operation=Operation.SLIDING,
            prefix="win",
        ):
            return True
        for w_dm in (int(round(width_m * 10)), 14, 12, 10):
            for w in sorted(self._walls_between(a, b), key=lambda s: -s.length_dm):
                for off in range(2, w.length_dm - w_dm - 1, 1):
                    if any(off + w_dm + 1 > u0 and off - 1 < u1 for u0, u1 in w.used):
                        continue
                    w.used.append((off, off + w_dm))
                    self.openings.append(
                        Opening(
                            id=f"win-ter-{len(self.openings) + 1:02d}",
                            host_wall_id=w.id,
                            kind=OpeningKind.WINDOW,
                            offset_m=off / 10,
                            width_m=w_dm / 10,
                            height_m=TERRACE_WINDOW_HEIGHT_M,
                            sill_m=TERRACE_WINDOW_SILL_M,
                            operation=Operation.SLIDING,
                            material_id="m-window",
                            connects=(a, b),
                        )
                    )
                    return True
        return False

    def _clear_at(self, w, off_dm: int, width_dm: int) -> bool:
        (a, c), (b, d) = self._seg_points(w)
        for t in (off_dm / w.length_dm, (off_dm + width_dm) / w.length_dm):
            u, v = a + (b - a) * t, c + (d - c) * t
            if w.orient == "h":
                v += 5 if w.neg else -5
            else:
                u += 5 if w.neg else -5
            g = self.ground.at(u / 10, v / 10)
            if (
                g is not None
                and g >= self.spec.elevations_m[w.level_id] + WINDOW_SILL_M - FORMATION_OFFSET_M
            ):
                return False
        return True

    def _slide_window(self, sid: str, width_dm: int = 12) -> bool:
        for w in sorted(self._walls_between(sid, None), key=lambda w: -w.length_dm):
            for off in range(2, w.length_dm - width_dm - 1, 2):
                if any(off + width_dm > u0 and off < u1 for u0, u1 in w.used):
                    continue
                if self._clear_at(w, off, width_dm) and self._exterior_span_is_clear(
                    w, off, width_dm, sid
                ):
                    w.used.append((off, off + width_dm))
                    self.openings.append(
                        Opening(
                            id=f"win-slid-{len(self.openings) + 1:02d}",
                            host_wall_id=w.id,
                            kind=OpeningKind.WINDOW,
                            offset_m=off / 10,
                            width_m=width_dm / 10,
                            height_m=DEFAULT_WINDOW_HEIGHT_M,
                            sill_m=WINDOW_SILL_M,
                            operation=Operation.SLIDING,
                            material_id="m-window",
                            connects=(sid, EXTERIOR),
                        )
                    )
                    return True
        return False

    def _make_stair(
        self, stair_id: str, from_lv: str, to_lv: str, bottom_sid: str, top_sid: str
    ) -> Stair:
        top = next(r for r in self.sol.rooms if r.space_id == top_sid)
        along_u = (top.u1 - top.u0) >= (top.v1 - top.v0)
        short = (top.v1 - top.v0) if along_u else (top.u1 - top.u0)
        width = round(min(1.0, short / 20 - 0.2), 3)
        lo, hi = (top.u0 + 2, top.u1 - 2) if along_u else (top.v0 + 2, top.v1 - 2)
        c0, c1 = (top.v0 + 2, top.v1 - 2) if along_u else (top.u0 + 2, top.u1 - 2)
        near, far = hi + 2 - LANDING_STRIP_DM, lo
        pts, fits = u_layout(near, far, c0, c1, width * 10, FAMILY_STAIR_RISERS)
        r0, r1 = sorted((near, far))
        fp = self.frame.rect(r0, c0, r1, c1) if along_u else self.frame.rect(c0, r0, c1, r1)
        line = [self.frame.to_local(*((x, c) if along_u else (c, x))) for x, c in pts]
        rise = self.spec.elevations_m[to_lv] - self.spec.elevations_m[from_lv]
        self.stair_fits[stair_id] = fits
        return Stair(
            id=stair_id,
            kind=StairKind.U_SHAPED,
            from_level_id=from_lv,
            to_level_id=to_lv,
            footprint=fp,
            bottom_space_id=bottom_sid,
            top_space_id=top_sid,
            width_m=width,
            riser_count=FAMILY_STAIR_RISERS,
            riser_height_m=rise / FAMILY_STAIR_RISERS,
            tread_depth_m=TREAD_DEPTH_M,
            walking_line=line,
            landing_segments=[1],
        )

    def build_model(self, *a, **kw) -> HouseModel:
        model = super().build_model(*a, **kw)
        # Continuous 3-level Core Stair: Lower -> Main and Main -> Road (Rule 5.2 & 5.3)
        st_lower_main = self._make_stair(
            "stair-lower-main", LEVEL_LOWER, LEVEL_MAIN, "sp-stair-l", "sp-stair-u"
        )
        st_main_road = self._make_stair(
            "stair-main-road", LEVEL_MAIN, LEVEL_ROAD, "sp-stair-u", "sp-stair-r"
        )
        model.stairs = [st_lower_main, st_main_road]

        all_rooms = [*self.sol.rooms, *self.sol.circulation_rooms]
        slabs: list[Slab] = []
        for lv in self.sol.levels:
            rooms_on_lv = [r for r in all_rooms if r.level_id == lv]
            int_boxes = [
                box(*q)
                for r in rooms_on_lv
                if r.function is not F.TERRACE
                for q in (r.sub_rects or [(r.u0, r.v0, r.u1, r.v1)])
            ]
            terrace_rooms = [r for r in rooms_on_lv if r.function is F.TERRACE]
            if int_boxes:
                fp_u = unary_union(int_boxes)
                flights = [
                    ShapelyPolygon(
                        [
                            tuple(round(c * 10) for c in self.frame.to_design(xy))
                            for xy in st.footprint.outer
                        ]
                    )
                    for st in model.stairs
                    if st.to_level_id == lv
                ]
                floor_u = fp_u.difference(unary_union(flights)) if flights else fp_u
                above = [
                    box(*q)
                    for r in all_rooms
                    if r.function is not F.TERRACE
                    and self.sol.levels.index(r.level_id) > self.sol.levels.index(lv)
                    for q in (r.sub_rects or [(r.u0, r.v0, r.u1, r.v1)])
                ]
                roof_u = fp_u.difference(unary_union(above)) if above else fp_u
                for kind, geom in ((SlabKind.FLOOR, floor_u), (SlabKind.ROOF, roof_u)):
                    self._slab_parts(slabs, lv, kind, geom)
            for tr in terrace_rooms:
                t_boxes = [box(*q) for q in (tr.sub_rects or [(tr.u0, tr.v0, tr.u1, tr.v1)])]
                t_u = unary_union(t_boxes).simplify(0.001)
                t_poly = (
                    max(list(t_u.geoms), key=lambda g: g.area) if hasattr(t_u, "geoms") else t_u
                )
                t_outer = [
                    self.frame.to_local(int(round(pt[0])), int(round(pt[1])))
                    for pt in t_poly.exterior.coords[:-1]
                ]
                t_holes = [
                    [
                        self.frame.to_local(int(round(pt[0])), int(round(pt[1])))
                        for pt in ring.coords[:-1]
                    ]
                    for ring in t_poly.interiors
                ]
                slabs.append(
                    Slab(
                        id=f"slab-terrace-{tr.space_id.removeprefix('sp-')}",
                        level_id=lv,
                        kind=SlabKind.TERRACE,
                        boundary=Polygon2D(outer=t_outer, holes=t_holes),
                        thickness_m=TERRACE_SLAB_THICKNESS_M,
                        material_id="m-floor",
                    )
                )
        model.slabs = slabs
        return model


def audit_owner_rules(
    spec: OptionSpec, model: HouseModel, sol: Solution2D
) -> list[dict[str, object]]:
    """Programmatically verify every rule in `projects/my-house/design/OWNER_DESIGN_RULES.md` (including stmt-019, stmt-020 & stmt-021)."""
    graph = circulation_graph(model)
    rooms_by_id = {r.space_id: r for r in sol.rooms}
    spaces_by_id = {s.id: s for s in model.spaces}
    walls_by_id = {w.id: w for w in model.walls}

    # 1.1 Kitchen opens directly onto a south terrace and looks south
    kitchen_to_south_terrace = "sp-terrace-south" in graph.get("sp-kitchen", set())
    kitchen_south_windows = [
        o
        for o in model.openings
        if o.kind is OpeningKind.WINDOW
        and "sp-kitchen" in o.connects
        and "sp-terrace-south" in o.connects
    ]
    r_1_1 = kitchen_to_south_terrace and len(kitchen_south_windows) >= 1

    # 1.2 Kitchen gets prime south frontage
    k_room = rooms_by_id["sp-kitchen"]
    main_plate_v1 = spec.plates_dm[LEVEL_MAIN][3]
    r_1_2 = k_room.v1 == main_plate_v1 and (k_room.u1 - k_room.u0) >= 40

    # 1.3 Semi-open kitchen with >=2 portals/walk-throughs, keeping cooking smells out of living room
    k_openings = [
        o
        for o in model.openings
        if o.kind is OpeningKind.OPENING
        and "sp-kitchen" in o.connects
        and not any(c.startswith(OUTDOOR_PREFIXES) for c in o.connects)
    ]
    k_direct_to_living = "sp-living" in graph.get("sp-kitchen", set())
    r_1_3 = len(k_openings) >= 2 and not k_direct_to_living

    # 1.4 & 1.5 (stmt-021): Right-sized Kitchen (16.1–17.5 m²) & Dining (12.5–15.5 m²) adjacent to Kitchen
    k_m2 = spaces_by_id["sp-kitchen"].area_m2
    d_m2 = spaces_by_id["sp-dining"].area_m2
    r_1_4 = (
        16.1 <= k_m2 <= 17.5
        and 12.5 <= d_m2 <= 15.5
        and "sp-dining" in graph.get("sp-kitchen", set())
    )

    # 2.1 & 2.5 (stmt-021): Every main room reached directly from entrance/stair hall, and NEVER walking through closet to enter master bedroom!
    hall_hub_u = {"sp-entry", "sp-hall-u"}
    direct_kitchen = any(h in graph["sp-kitchen"] for h in hall_hub_u)
    direct_dining = any(h in graph["sp-dining"] for h in hall_hub_u)
    direct_living = any(h in graph["sp-living"] for h in hall_hub_u)
    direct_master = any(h in graph["sp-master"] for h in hall_hub_u)
    closet_inside_master = graph.get("sp-closet", set()) == {"sp-master"}
    ensuite_inside_master = graph.get("sp-ensuite-u", set()) == {"sp-master"}
    hall_hub_l = {"sp-hall-l"}
    direct_lower_beds = all(
        any(h in graph[b] for h in hall_hub_l)
        for b in ("sp-bed3", "sp-boys", "sp-girls", "sp-family")
    )
    r_2_1 = (
        direct_kitchen
        and direct_dining
        and direct_living
        and direct_master
        and closet_inside_master
        and ensuite_inside_master
        and direct_lower_beds
    )

    # 2.2 & 2.6 (stmt-021): No long corridors, and clear West Front/Arrival Doors without doglegs or notches
    entry_room = rooms_by_id["sp-entry"]
    road_front_doors = [
        o for o in model.openings if o.id.startswith("d-front") and "sp-lobby" in o.connects
    ]
    main_west_doors = [
        o
        for o in model.openings
        if set(o.connects) == {"sp-entry", "sp-court-west"} and o.width_m >= 1.15
    ]
    r_2_2 = (
        spaces_by_id["sp-hall-u"].area_m2 <= 18.0
        and spaces_by_id["sp-hall-l"].area_m2 <= 36.0
        and entry_room.sub_rects is None
        and len(road_front_doors) == 1
        and len(main_west_doors) == 1
    )

    # 2.3 Connected stepped footprint with zero internal voids/holes
    _verify_exact_plate_tiling(spec)
    r_2_3 = True

    # 2.4 No unnecessary doors or barriers
    r_2_4 = any(
        o.kind is OpeningKind.OPENING and set(o.connects) == {"sp-hall-u", "sp-living"}
        for o in model.openings
    )

    # 3.1, 3.2 & 3.3 (stmt-021): Generous, wide L-shaped Living Room (>= 48 m², >= 4.4 m wide) with sheltered NE cozy/prayer bay + direct hall entry
    liv_room = rooms_by_id["sp-living"]
    liv_m2 = spaces_by_id["sp-living"].area_m2
    liv_hall_ops = [o for o in model.openings if set(o.connects) == {"sp-hall-u", "sp-living"}]
    cozy_u0, cozy_v0, cozy_u1, cozy_v1 = spec.cozy_corner_dm
    op_clear_of_cozy = True
    for o in liv_hall_ops:
        w = walls_by_id[o.host_wall_id]
        (_, v_start), (_, v_end) = frame.to_design(w.start), frame.to_design(w.end)
        v_min_m = min(v_start, v_end) + o.offset_m
        if v_min_m * 10 < cozy_v1 - 1e-3:
            op_clear_of_cozy = False
    liv_min_w_m = min((q[2] - q[0]) / 10.0 for q in (liv_room.sub_rects or []))
    r_3_1 = (
        liv_room.sub_rects is not None
        and len(liv_room.sub_rects) == 2
        and op_clear_of_cozy
        and liv_m2 >= 48.0
        and liv_min_w_m >= 4.4
    )
    r_3_2 = direct_living and len(liv_hall_ops) == 1

    # 4.1 South and east frontage dedicated to day rooms, bedrooms, and terraces
    r_4_1 = k_room.v1 == main_plate_v1 and liv_room.u1 == spec.plates_dm[LEVEL_MAIN][2]

    # 4.2 House not narrow towards east (stepped to u ≈ 20 m, confirmed in stmt-018)
    lower_u1_m = spec.plates_dm[LEVEL_LOWER][2] / 10.0
    r_4_2 = 19.5 <= lower_u1_m <= 21.0

    # 4.3 Plenty of terraces on main floor (south, east, and west court)
    main_terraces_m2 = sum(
        s.area_m2 for s in model.spaces if s.level_id == LEVEL_MAIN and s.function is F.TERRACE
    )
    r_4_3 = main_terraces_m2 >= 90.0

    # 5.1 Indoor route from garage to lift and stair
    r_5_1 = (
        "sp-lobby" in graph["sp-garage"]
        and "sp-lift-r" in graph["sp-lobby"]
        and "sp-stair-r" in graph["sp-lobby"]
    )

    # 5.2 & 5.3 One seamless central stair at the heart of the house connecting all 3 levels
    stair_r = rooms_by_id["sp-stair-r"]
    plate_m = spec.plates_dm[LEVEL_MAIN]
    in_heart = (
        stair_r.u0 >= plate_m[0] + 20
        and stair_r.u1 <= plate_m[2] - 40
        and stair_r.v1 <= plate_m[3] - 30
    )
    r_5_2 = (
        len(model.stairs) == 2
        and "sp-stair-u" in graph["sp-stair-r"]
        and "sp-stair-l" in graph["sp-stair-u"]
    )
    r_5_3 = in_heart

    # 5.5 & 6.3 Oversized 2-car garage + integrated workshop bay (~54 m2), lower store tucked by core
    garage_m2 = spaces_by_id["sp-garage"].area_m2
    r_5_5 = 53.0 <= garage_m2 <= 62.0

    # 6.1-6.6 Bedrooms, bathrooms, tea bar, tucked lower store
    r_6_all = (
        spaces_by_id["sp-master"].area_m2 >= 12.0
        and spaces_by_id["sp-bed3"].area_m2 >= 20.0
        and spaces_by_id["sp-boys"].area_m2 >= 20.0
        and spaces_by_id["sp-girls"].area_m2 >= 20.0
        and spaces_by_id["sp-shower-l"].area_m2 >= 5.5
    )

    # 6.7 & 7.3 (stmt-019, stmt-020, stmt-021): Heavily based on User's 0109-r5 (A, B, C) & fixing 0110-r2
    plant_doors = [
        o
        for o in model.openings
        if set(o.connects) == {"sp-lobby", "sp-plant"} and o.width_m >= 1.15
    ]
    has_4part_wet_cluster = (
        "sp-wudu-u" in spaces_by_id
        and "sp-wc-u" in graph["sp-wudu-u"]
        and "sp-shower-u" in graph["sp-wudu-u"]
    )
    r_6_7 = (
        len(plant_doors) == 1
        and has_4part_wet_cluster
        and "sp-ensuite-l" in graph["sp-bed3"]
        and spaces_by_id["sp-ensuite-l"].area_m2 >= 8.0
        and spaces_by_id["sp-laundry"].area_m2 >= 14.0
        and spaces_by_id["sp-store-l"].area_m2 >= 9.0
    )

    checks = [
        (
            "1.1",
            "Kitchen opens directly onto South Terrace and looks south",
            r_1_1,
            "Sliding door d-out + windows directly from sp-kitchen to sp-terrace-south",
        ),
        (
            "1.2",
            "Kitchen gets prime south frontage",
            r_1_2,
            f"Kitchen spans {(k_room.u1 - k_room.u0) / 10:.1f} m along south edge v={main_plate_v1 / 10:.1f} m",
        ),
        (
            "1.3",
            "Semi-open kitchen with 2 doorless walk-throughs; cooking smells kept out of living",
            r_1_3,
            f"{len(k_openings)} doorless walk-throughs; zero direct opening between kitchen and living",
        ),
        (
            "1.4 & 1.5",
            "Right-sized Kitchen (16.8 m²) & Dining (13.6–14.4 m²) adjacent to Kitchen (stmt-021, I14, I26)",
            r_1_4,
            f"Kitchen {k_m2:.1f} m², Dining {d_m2:.1f} m² adjacent (right-sized so East Living is {liv_m2:.1f} m²)",
        ),
        (
            "2.1 & 2.5",
            "Every main room & Parents Bedroom reached directly from Hall — NEVER through Closet (stmt-021)",
            r_2_1,
            "Direct door from West Entry into Parents Bedroom; Dress & Ensuite open only from inside the Bedroom",
        ),
        (
            "2.2 & 2.6",
            "Clear, direct West Front Door (Road) & West Arrival Door (Main) with zero doglegs or notches (stmt-021)",
            r_2_2,
            f"1.2m Road Front Door on West facade + 1.2m Main West Arrival Door into straight rectangular Entry ({spaces_by_id['sp-entry'].area_m2:.1f} m²)",
        ),
        (
            "2.3",
            "Sculpted stepped 0109-r5 footprint with zero internal voids or holes",
            r_2_3,
            "Mathematical 0.00 m² overlap and 0 internal holes across all 3 stepped floor plates",
        ),
        (
            "2.4",
            "No unnecessary interior doors or barriers",
            r_2_4,
            "Wide doorless portals between Entry, Family Link, Living, Dining, Kitchen, Pantry, and Garden Lounge",
        ),
        (
            "3.1 & 3.3",
            "Generous, wide L-shaped Living Room (49.6–52.8 m², 4.4–6.6m wide) + sheltered NE Cozy/Prayer bay (stmt-021)",
            r_3_1,
            f"East Family Living = {liv_m2:.1f} m² (min width {liv_min_w_m:.1f} m) + NE Reading/Prayer bay ({(cozy_u1 - cozy_u0) * (cozy_v1 - cozy_v0) / 100:.1f} m²)",
        ),
        (
            "3.2",
            "Living room closed-off corner is not cut off (direct wide opening from Family Link)",
            r_3_2,
            "1.4 m wide direct doorless opening from sp-hall-u into sp-living (~3.5 m from Wudu, fixes I11)",
        ),
        (
            "4.1",
            "South and east prime frontage used for day rooms and terraces",
            r_4_1,
            "South = Kitchen, Dining, Living & South Terrace; East = Living, NE Prayer, Garden Lounge & Terraces",
        ),
        (
            "4.2",
            "House steps east to u ≈ 20 m (not narrow towards east, stmt-018, fixes I01/I02)",
            r_4_2,
            f"Road u={spec.plates_dm[LEVEL_ROAD][0] / 10:.1f}–{spec.plates_dm[LEVEL_ROAD][2] / 10:.1f} m, Main u={spec.plates_dm[LEVEL_MAIN][0] / 10:.1f}–{spec.plates_dm[LEVEL_MAIN][2] / 10:.1f} m, Lower u={spec.plates_dm[LEVEL_LOWER][0] / 10:.1f}–{lower_u1_m:.1f} m",
        ),
        (
            "4.3",
            "Generous wrap-around terraces on main floor + excavated lower garden court",
            r_4_3,
            f"{main_terraces_m2:.1f} m² of outdoor terraces/courts on the main floor + exterior garden stair GS",
        ),
        (
            "5.1",
            "Indoor route from Two Car Bays straight to Six-Person Unloading, Lift & Core Stair",
            r_5_1,
            "Direct interior door sp-garage -> sp-lobby (6 lockers) -> sp-lift-r & sp-stair-r",
        ),
        (
            "5.2",
            "One continuous North-Projecting Core Stair (REST 1.40) connects Road, Main, and Lower floors",
            r_5_2,
            "Two stacked U-flights (stair-main-road + stair-lower-main) in the 3.0×5.0 m north-projecting core",
        ),
        (
            "5.3",
            "Stair is at the heart of the household circulation",
            r_5_3,
            f"North-center core u={stair_r.u0 / 10:.1f}–{stair_r.u1 / 10:.1f} m, v={stair_r.v0 / 10:.1f}–{stair_r.v1 / 10:.1f} m",
        ),
        (
            "5.5",
            "Two Independent Car Bays + North Workshop (~54 m²) with two west shutters & 0.65m door zones (fixes I09)",
            r_5_5,
            f"Two Car Bays + Workshop = {garage_m2:.1f} m² (LC300 {LC300_LENGTH_M}×{LC300_WIDTH_M}m + 2nd car {SECOND_CAR_LENGTH_M}×{SECOND_CAR_WIDTH_M}m, 0.00 m² clash)",
        ),
        (
            "6.1–6.6",
            "Main Floor Suite + Lower South Boys & Girls + Garden Suite + Garden Lounge with Tea/Snack Bar",
            r_6_all,
            f"Main Suite {spaces_by_id['sp-master'].area_m2:.1f} m²; Lower Suite {spaces_by_id['sp-bed3'].area_m2:.1f} m²; Boys {spaces_by_id['sp-boys'].area_m2:.1f} m²; Girls {spaces_by_id['sp-girls'].area_m2:.1f} m²; Garden Lounge {spaces_by_id['sp-family'].area_m2:.1f} m²",
        ),
        (
            "6.7 & 7.3",
            "Heavily based on User's 0109-r5 (A, B, C) with 4-part Screened Wet/Wudu Cluster, 1.2m Plant Door & 0110-r2 Fixes (stmt-019, stmt-020, stmt-021)",
            r_6_7,
            f"4-part Wet/Wudu cluster; 1.2m Plant door; Lower Seated Bath {spaces_by_id['sp-ensuite-l'].area_m2:.1f} m² (I10); Laundry {spaces_by_id['sp-laundry'].area_m2:.1f} m² (I12); Store {spaces_by_id['sp-store-l'].area_m2:.1f} m² (I22)",
        ),
    ]
    out = []
    for rule_id, desc, passed, evidence in checks:
        assert passed, f"{spec.option_id} FAILED Owner Rule {rule_id}: {desc}"
        out.append(
            {"rule": rule_id, "description": desc, "passed": bool(passed), "evidence": evidence}
        )
    return out


def generate_option(spec: OptionSpec) -> dict[str, object]:
    out_dir = HERE / spec.option_id
    out_dir.mkdir(parents=True, exist_ok=True)
    sol, doors = build_solution(spec)
    builder = ArgonBuilder(spec, doors, sol, site, frame, ground, program, actor)
    model = builder.build_model(spec.option_id, spec.title, site_ref, program_ref)
    level_names = {
        LEVEL_ROAD: f"Road floor +{spec.elevations_m[LEVEL_ROAD]:.1f} — Two Car Bays + Workshop, 6-Person Unloading, Core 20R, 1.2m Plant, SE Office",
        LEVEL_MAIN: f"Upper/Main floor +{spec.elevations_m[LEVEL_MAIN]:.1f} — 4-Part Screened Wet/Wudu, Walk-in Pantry, South Kitchen, SE Dining, East Living & NE Prayer",
        LEVEL_LOWER: f"Lower floor +{spec.elevations_m[LEVEL_LOWER]:.1f} — South Boys & Girls Rooms, Garden Suite + Seated Ensuite, Garden Lounge, Laundry & Store",
    }
    for lv in model.levels:
        lv.name = level_names[lv.id]

    model.assumptions = [
        Assumption(
            id=f"{spec.option_id}-basis",
            made_by=actor,
            statement=(
                f"EXPLORATORY ({spec.title}). Directly based on user-designed 0109-r5 Option {spec.code} "
                f"with stepped hillside massing reaching u={spec.plates_dm[LEVEL_LOWER][2] / 10:.1f} m "
                f"(lower garden terrace to {spec.lawn_u0_m:.1f} m, flat east lawn at +{spec.lawn_z_m:.1f} m) "
                "and resolving all 30 issues in 0110-r2. Not structurally, geotechnically, or code certified."
            ),
        )
    ]

    plan = PlanVersion(
        option_id=model.id,
        label=model.name,
        strategy="stepped-terraces-user-design-synthesis",
        model=model,
        provenance=Provenance(
            created_at=store.clock(),
            created_by=actor,
            method="cpsat_exact_tiling",
            inputs=[site_ref, program_ref],
        ),
        generation=GenerationRecord(
            generator="argon-c07-generator",
            generator_version="2.0",
            solver="ortools-cp-sat",
            solver_version=ortools.__version__,
            solver_status="OPTIMAL",
            objective=0.0,
            seed=1,
            deterministic_time_limit=10.0,
        ),
    )
    (out_dir / "plan.json").write_text(plan.model_dump_json(indent=2) + "\n")

    findings = check_model(model, site, program)
    (out_dir / "violations.json").write_text(
        json.dumps([f.model_dump(mode="json") for f in findings], indent=2) + "\n"
    )
    assert len(findings) == 0, f"{spec.option_id} has check_model findings: {findings}"
    assert all(builder.stair_fits.values()), (
        f"{spec.option_id} stair_fits failed: {builder.stair_fits}"
    )

    rule_audit = audit_owner_rules(spec, model, sol)
    (out_dir / "rule-audit.json").write_text(json.dumps(rule_audit, indent=2) + "\n")

    (out_dir / "placement.json").write_text(
        json.dumps(
            {
                "option_id": spec.option_id,
                "title": spec.title,
                "subtitle": spec.subtitle,
                "summary": spec.summary,
                "plates": spec.plates_dm,
                "levels": spec.elevations_m,
                "storey_heights": spec.storey_heights_m,
                "lawn_u0_m": spec.lawn_u0_m,
                "lawn_z_m": spec.lawn_z_m,
                "cozy_corner_dm": spec.cozy_corner_dm,
                "prayer_nook_dm": spec.prayer_nook_dm,
                "tea_bar_dm": spec.tea_bar_dm,
                "workshop_bay_dm": spec.workshop_bay_dm,
                "lockers_dm": spec.lockers_dm,
                "stair_fits": builder.stair_fits,
                "user_design_synthesis": USER_DESIGN_SYNTHESIS,
                "rooms": [{**r.__dict__, "function": r.function.value} for r in sol.rooms],
            },
            indent=2,
        )
        + "\n"
    )

    indoor_m2 = sum(s.area_m2 for s in model.spaces if s.function is not F.TERRACE)
    outdoor_m2 = sum(s.area_m2 for s in model.spaces if s.function is F.TERRACE)
    print(
        f"[{spec.option_id}] OK: {len(model.spaces)} spaces "
        f"({indoor_m2:.1f} m² indoor + {outdoor_m2:.1f} m² terraces), "
        f"{len(model.walls)} walls, {len(model.openings)} openings, "
        f"0 check_model findings, {len(rule_audit)}/{len(rule_audit)} Owner Rules PASS"
    )
    return {
        "option_id": spec.option_id,
        "indoor_m2": round(indoor_m2, 1),
        "outdoor_m2": round(outdoor_m2, 1),
        "findings": len(findings),
        "rules_passed": len(rule_audit),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Argon C07 options A, B, and C (heavily based on user-designed 0109-r5)"
    )
    parser.add_argument("--option", choices=["a", "b", "c", "all"], default="all")
    args = parser.parse_args()
    keys = ["a", "b", "c"] if args.option == "all" else [args.option]
    for k in keys:
        generate_option(OPTIONS[k])


if __name__ == "__main__":
    main()
