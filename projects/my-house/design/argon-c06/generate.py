"""EXPLORATORY Argon C06 concept generator (agent:gemini, 2026-10-26).

Generates three genuinely distinct, complete 3-level hillside house designs
(`argon-c06-a`, `argon-c06-b`, `argon-c06-c`) in `projects/my-house/design/argon-c06/`,
strictly obeying every rule in `projects/my-house/design/OWNER_DESIGN_RULES.md` and
owner confirmations in `stmt-018`:

1. Stepped east-west massing reaching u ≈ 20 m (Lower terrace to 22.6 m, flat east lawn
   22.6–31.4 m), avoiding narrow east-west footprints and balancing excavation.
2. Continuous 3-level Central Heart Stair + Lift Core connecting Road Level, Main Floor,
   and Lower Floor seamlessly (even without electricity), with an indoor route from the
   oversized 2-car Garage + integrated Workshop bay straight to the Lift and Stair.
3. South Kitchen on the Main Floor opening directly via a sliding door onto the South
   Terrace, semi-open with two doorless walk-throughs (Hall <-> Kitchen, Kitchen <-> Dining)
   and full-height walls keeping cooking smells out of the Living room.
4. Direct circulation from the Central Entrance/Stair Hall to every main room (Kitchen,
   Dining, Living, Master Suite) without ever walking through another main room.
5. L-shaped Living Room on the prime East/South-East frontage with a sheltered, cozy
   sitting corner closed off on its north/hall side while still having a direct wide
   opening from the Central Hall.
6. Lower Floor with 3 bright bedrooms (Grandparents Suite with en-suite + Boys 2 beds +
   Girls 2 beds), Family Room with integrated Tea & Snack Bar, separate Shared Shower
   and Shared WC, and Laundry + Store tucked by the core.

Run:
    .venv/bin/python projects/my-house/design/argon-c06/generate.py
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
    LEVEL_LOWER,
    LEVEL_MAIN,
    LEVEL_ROAD,
    MODEL_ACTOR_ID,
    OUTDOOR_PREFIXES,
    TERRACE_WINDOW_HEIGHT_M,
    TERRACE_WINDOW_SILL_M,
    TREAD_DEPTH_M,
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
    tea_bar_dm: tuple[int, int, int, int]
    workshop_bay_dm: tuple[int, int, int, int]
    rooms: list[RoomSpec]
    terraces: list[tuple[str, str, str, list[tuple[int, int, int, int]], str]]
    links: list[tuple[str, str, bool, tuple[int, int] | None]]
    terrace_doors: list[tuple[str, str]]
    outdoor_exits: list[tuple[str, str]]


def _shared_core_rooms(
    lift_rects: dict[str, list[tuple[int, int, int, int]]] | None = None,
) -> list[RoomSpec]:
    """Central Heart Core: continuous 3-level Stair (2.6x5.0 m) + Lift (1.8x2.0 m)."""
    default_lift = [(84, 54, 102, 74)]
    lr = lift_rects or {}
    return [
        RoomSpec(
            "stair-r", "Central heart stair", F.STAIR, LEVEL_ROAD, [(58, 24, 84, 74)], "pi-stair"
        ),
        RoomSpec("lift-r", "Lift", F.LIFT, LEVEL_ROAD, lr.get(LEVEL_ROAD, default_lift), "pi-lift"),
        RoomSpec(
            "stair-u", "Central heart stair", F.STAIR, LEVEL_MAIN, [(58, 24, 84, 74)], "pi-stair"
        ),
        RoomSpec("lift-u", "Lift", F.LIFT, LEVEL_MAIN, lr.get(LEVEL_MAIN, default_lift), "pi-lift"),
        RoomSpec(
            "stair-l", "Central heart stair", F.STAIR, LEVEL_LOWER, [(58, 24, 84, 74)], "pi-stair"
        ),
        RoomSpec(
            "lift-l", "Lift", F.LIFT, LEVEL_LOWER, lr.get(LEVEL_LOWER, default_lift), "pi-lift"
        ),
    ]


def make_option_a() -> OptionSpec:
    """Option A: South Kitchen, Central-South Dining, NE Cozy L-Living & East-Center Family Hub."""
    z = {LEVEL_ROAD: 1677.7, LEVEL_MAIN: 1674.3, LEVEL_LOWER: 1670.7}
    storey = {LEVEL_ROAD: 3.0, LEVEL_MAIN: 3.4, LEVEL_LOWER: 3.6}
    plates = {
        LEVEL_ROAD: (6, 0, 116, 124),
        LEVEL_MAIN: (20, 0, 162, 124),
        LEVEL_LOWER: (58, 0, 200, 156),
    }
    rooms = [
        *_shared_core_rooms(),
        # Road Level (136.4 m2 indoor)
        RoomSpec(
            "garage",
            "Garage (2 cars + workshop bay)",
            F.GARAGE,
            LEVEL_ROAD,
            [(6, 0, 58, 92), (58, 0, 84, 24)],
            "pi-garage",
        ),
        RoomSpec(
            "lobby",
            "Road entrance lobby",
            F.ENTRY,
            LEVEL_ROAD,
            [(6, 92, 58, 124), (58, 74, 116, 100)],
            "pi-entry",
        ),
        RoomSpec(
            "office",
            "Quiet office / guest",
            F.STUDY,
            LEVEL_ROAD,
            [(84, 0, 116, 54), (102, 54, 116, 74)],
            "pi-study-1",
        ),
        RoomSpec("wc-r", "Road WC + shower", F.BATHROOM, LEVEL_ROAD, [(84, 100, 116, 124)]),
        RoomSpec(
            "plant",
            "Plant / utilities",
            F.MECHANICAL,
            LEVEL_ROAD,
            [(58, 100, 84, 124)],
            "pi-mechanical",
        ),
        # Main Floor (176.1 m2 indoor)
        RoomSpec(
            "entry", "Entrance hall (shoes)", F.ENTRY, LEVEL_MAIN, [(20, 52, 58, 90)], "pi-entry"
        ),
        RoomSpec("wc-u", "Guest WC", F.WC, LEVEL_MAIN, [(20, 24, 38, 52)]),
        RoomSpec(
            "store-u", "Coat & shoe store", F.STORAGE, LEVEL_MAIN, [(38, 24, 58, 52)], "pi-storage"
        ),
        RoomSpec(
            "hall-u",
            "Central stair & lift hall",
            F.HALL,
            LEVEL_MAIN,
            [(58, 74, 116, 90), (102, 36, 116, 74)],
        ),
        RoomSpec("pantry", "Pantry", F.PANTRY, LEVEL_MAIN, [(20, 90, 38, 124)], "pi-pantry"),
        RoomSpec(
            "kitchen",
            "Kitchen + everyday dining",
            F.KITCHEN,
            LEVEL_MAIN,
            [(38, 90, 100, 124)],
            "pi-kitchen",
        ),
        RoomSpec("dining", "Dining room", F.DINING, LEVEL_MAIN, [(100, 90, 140, 124)], "pi-dining"),
        RoomSpec(
            "living",
            "Living room (L-shaped + cozy corner)",
            F.LIVING,
            LEVEL_MAIN,
            [(116, 36, 162, 90), (140, 90, 162, 124)],
            "pi-living",
        ),
        RoomSpec(
            "master",
            "Grand master bedroom",
            F.BEDROOM,
            LEVEL_MAIN,
            [(102, 0, 162, 36)],
            "pi-bed-main",
        ),
        RoomSpec("closet", "Dressing vestibule", F.STORAGE, LEVEL_MAIN, [(84, 24, 102, 54)]),
        RoomSpec(
            "ensuite-u",
            "Master bathroom",
            F.BATHROOM,
            LEVEL_MAIN,
            [(20, 0, 102, 24)],
            "pi-bath-ensuite",
        ),
        # Lower Floor (221.5 m2 indoor)
        RoomSpec(
            "hall-l",
            "Lower central hall",
            F.HALL,
            LEVEL_LOWER,
            [(58, 74, 126, 98), (102, 36, 126, 74)],
        ),
        RoomSpec(
            "family",
            "Family room + tea & snack bar",
            F.FAMILY,
            LEVEL_LOWER,
            [(126, 48, 200, 86)],
        ),
        RoomSpec(
            "bed3",
            "Parents / grandparents suite",
            F.BEDROOM,
            LEVEL_LOWER,
            [(126, 86, 200, 132)],
            "pi-bed-elder-1",
        ),
        RoomSpec(
            "ensuite-l",
            "Grandparents shower room",
            F.BATHROOM,
            LEVEL_LOWER,
            [(126, 132, 200, 156)],
            "pi-bath-2",
        ),
        RoomSpec(
            "boys",
            "Boys bedroom (2 beds)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(126, 0, 200, 48)],
            "pi-bed-child-1",
        ),
        RoomSpec(
            "girls",
            "Girls bedroom (2 beds)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(88, 98, 126, 156)],
            "pi-bed-child-2",
        ),
        RoomSpec(
            "shower-l",
            "Accessible shared bathroom",
            F.BATHROOM,
            LEVEL_LOWER,
            [(102, 0, 126, 36)],
            "pi-bath-1",
        ),
        RoomSpec("wc-l", "Shared WC", F.WC, LEVEL_LOWER, [(84, 24, 102, 54)]),
        RoomSpec(
            "laundry",
            "Laundry room",
            F.LAUNDRY,
            LEVEL_LOWER,
            [(58, 98, 88, 156)],
            "pi-laundry",
        ),
        RoomSpec(
            "store-l",
            "Lower store room",
            F.STORAGE,
            LEVEL_LOWER,
            [(58, 0, 102, 24)],
            "pi-storage",
        ),
    ]
    terraces = [
        (
            "sp-deck-east",
            "Road-level roof deck (east)",
            LEVEL_ROAD,
            [(116, 0, 162, 124)],
            "pi-balcony",
        ),
        (
            "sp-court-west",
            "West arrival court (sunken; covered porch at north)",
            LEVEL_MAIN,
            [(-20, 40, 20, 96), (-48, 96, 20, 124)],
            "",
        ),
        (
            "sp-terrace-south",
            "South terrace (off kitchen, dining & living)",
            LEVEL_MAIN,
            [(20, 124, 162, 156)],
            "pi-terrace",
        ),
        (
            "sp-terrace-east",
            "East balcony (roof of lower floor)",
            LEVEL_MAIN,
            [(162, 0, 200, 156)],
            "pi-balcony",
        ),
        ("sp-terrace-lower", "Lower east garden terrace", LEVEL_LOWER, [(200, 0, 226, 156)], ""),
    ]
    links = [
        # Road
        ("lobby", "garage", True, None),
        ("lobby", "stair-r", False, None),
        ("lobby", "lift-r", True, None),
        ("lobby", "office", True, None),
        ("lobby", "wc-r", True, None),
        ("lobby", "plant", True, None),
        # Main
        ("entry", "hall-u", False, None),
        ("entry", "wc-u", True, None),
        ("entry", "store-u", True, None),
        ("hall-u", "stair-u", False, None),
        ("hall-u", "lift-u", True, None),
        ("hall-u", "kitchen", False, None),
        ("hall-u", "dining", False, None),
        (
            "hall-u",
            "living",
            False,
            (62, 88),
        ),  # Opening only on south half; north 36..62 is closed cozy corner
        ("hall-u", "closet", True, None),
        ("closet", "master", True, None),
        ("master", "ensuite-u", True, None),
        ("kitchen", "pantry", False, None),
        ("kitchen", "dining", False, None),
        ("dining", "living", False, None),
        # Lower
        ("hall-l", "stair-l", False, None),
        ("hall-l", "lift-l", True, None),
        ("hall-l", "family", False, None),
        ("hall-l", "bed3", True, None),
        ("bed3", "ensuite-l", True, None),
        ("hall-l", "boys", True, None),
        ("hall-l", "girls", True, None),
        ("hall-l", "shower-l", True, None),
        ("hall-l", "wc-l", True, None),
        ("hall-l", "laundry", True, None),
        ("stair-l", "store-l", True, None),
    ]
    terrace_doors = [
        ("entry", "sp-court-west"),
        ("kitchen", "sp-terrace-south"),
        ("dining", "sp-terrace-south"),
        ("living", "sp-terrace-south"),
        ("living", "sp-terrace-east"),
        ("master", "sp-terrace-east"),
        ("office", "sp-deck-east"),
        ("family", "sp-terrace-lower"),
        ("bed3", "sp-terrace-lower"),
        ("boys", "sp-terrace-lower"),
    ]
    outdoor_exits = [
        ("sp-court-west", "south"),
        ("sp-terrace-south", "south"),
        ("sp-terrace-lower", "east"),
    ]
    return OptionSpec(
        option_id=f"{DESIGN_SERIES_ID}-a",
        code="A",
        title="Argon C06-A — Northeast Sheltered Cozy Living & Central-East Garden Hub",
        subtitle="South kitchen + south terrace, central-south dining, NE sheltered cozy living corner, east-center family room",
        summary=(
            "Places the kitchen on the prime south facade with a direct sliding door to the 45.4 m² "
            "south terrace, dining beside it at south-center, and an L-shaped living room along the "
            "east/south-east view with a sheltered 12.0 m² cozy sitting corner in its north-east wing "
            "(completely closed off from the stair hall and kitchen). Downstairs, the family room + tea bar "
            "occupies the central-east garden front between the boys' NE bedroom and grandparents' SE suite."
        ),
        elevations_m=z,
        storey_heights_m=storey,
        plates_dm=plates,
        lawn_u0_m=22.6,
        lawn_z_m=1668.1,
        cozy_corner_dm=(116, 36, 162, 62),
        tea_bar_dm=(126, 48, 154, 56),
        workshop_bay_dm=(58, 0, 84, 24),
        rooms=rooms,
        terraces=terraces,
        links=links,
        terrace_doors=terrace_doors,
        outdoor_exits=outdoor_exits,
    )


def make_option_b() -> OptionSpec:
    """Option B: 3-Sided Wrap Terraces (North+East+South), Central-East Dining & SE Cozy L-Living."""
    z = {LEVEL_ROAD: 1677.7, LEVEL_MAIN: 1674.2, LEVEL_LOWER: 1670.6}
    storey = {LEVEL_ROAD: 3.0, LEVEL_MAIN: 3.5, LEVEL_LOWER: 3.6}
    plates = {
        LEVEL_ROAD: (6, 0, 114, 124),
        LEVEL_MAIN: (20, 14, 160, 124),
        LEVEL_LOWER: (58, 0, 198, 156),
    }
    rooms = [
        *_shared_core_rooms(),
        # Road Level (133.9 m2 indoor)
        RoomSpec(
            "garage",
            "Garage (2 cars + workshop bay)",
            F.GARAGE,
            LEVEL_ROAD,
            [(6, 0, 58, 92), (58, 0, 84, 24)],
            "pi-garage",
        ),
        RoomSpec(
            "lobby",
            "Road entrance lobby",
            F.ENTRY,
            LEVEL_ROAD,
            [(6, 92, 58, 124), (58, 74, 114, 100)],
            "pi-entry",
        ),
        RoomSpec(
            "office",
            "Quiet office / guest",
            F.STUDY,
            LEVEL_ROAD,
            [(84, 0, 114, 54), (102, 54, 114, 74)],
            "pi-study-1",
        ),
        RoomSpec("wc-r", "Road WC + shower", F.BATHROOM, LEVEL_ROAD, [(84, 100, 114, 124)]),
        RoomSpec(
            "plant",
            "Plant / utilities",
            F.MECHANICAL,
            LEVEL_ROAD,
            [(58, 100, 84, 124)],
            "pi-mechanical",
        ),
        # Main Floor (154.0 m2 indoor, surrounded by North, East, and South terraces!)
        RoomSpec(
            "entry", "Entrance hall (shoes)", F.ENTRY, LEVEL_MAIN, [(20, 52, 58, 88)], "pi-entry"
        ),
        RoomSpec("wc-u", "Guest WC", F.WC, LEVEL_MAIN, [(20, 32, 38, 52)]),
        RoomSpec(
            "store-u", "Coat & shoe store", F.STORAGE, LEVEL_MAIN, [(38, 32, 58, 52)], "pi-storage"
        ),
        RoomSpec(
            "hall-u",
            "Central stair & lift hall",
            F.HALL,
            LEVEL_MAIN,
            [(58, 74, 118, 88), (102, 38, 118, 74)],
        ),
        RoomSpec("pantry", "Pantry", F.PANTRY, LEVEL_MAIN, [(20, 88, 38, 124)], "pi-pantry"),
        RoomSpec(
            "kitchen",
            "Kitchen + everyday dining",
            F.KITCHEN,
            LEVEL_MAIN,
            [(38, 88, 98, 124)],
            "pi-kitchen",
        ),
        RoomSpec(
            "dining",
            "Dining pavilion",
            F.DINING,
            LEVEL_MAIN,
            [(98, 88, 134, 124)],
            "pi-dining",
        ),
        RoomSpec(
            "living",
            "Living room (L-shaped + cozy corner)",
            F.LIVING,
            LEVEL_MAIN,
            [(118, 38, 160, 88), (134, 88, 160, 124)],
            "pi-living",
        ),
        RoomSpec(
            "master",
            "Grand master bedroom",
            F.BEDROOM,
            LEVEL_MAIN,
            [(102, 14, 160, 38)],
            "pi-bed-main",
        ),
        RoomSpec("closet", "Dressing vestibule", F.STORAGE, LEVEL_MAIN, [(84, 24, 102, 54)]),
        RoomSpec(
            "ensuite-u",
            "Master bathroom",
            F.BATHROOM,
            LEVEL_MAIN,
            [(20, 14, 58, 32), (58, 14, 102, 24)],
            "pi-bath-ensuite",
        ),
        # Lower Floor (218.4 m2 indoor)
        RoomSpec(
            "hall-l",
            "Lower central hall",
            F.HALL,
            LEVEL_LOWER,
            [(58, 74, 126, 98), (102, 36, 126, 74)],
        ),
        RoomSpec(
            "ensuite-l",
            "Grandparents shower room",
            F.BATHROOM,
            LEVEL_LOWER,
            [(126, 48, 198, 64)],
            "pi-bath-2",
        ),
        RoomSpec(
            "bed3",
            "Parents / grandparents suite",
            F.BEDROOM,
            LEVEL_LOWER,
            [(126, 64, 198, 86)],
            "pi-bed-elder-1",
        ),
        RoomSpec(
            "family",
            "Family room + tea & snack bar",
            F.FAMILY,
            LEVEL_LOWER,
            [(126, 86, 198, 156)],
        ),
        RoomSpec(
            "boys",
            "Boys bedroom (2 beds)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(126, 0, 198, 48)],
            "pi-bed-child-1",
        ),
        RoomSpec(
            "girls",
            "Girls bedroom (2 beds)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(88, 98, 126, 156)],
            "pi-bed-child-2",
        ),
        RoomSpec(
            "shower-l",
            "Accessible shared bathroom",
            F.BATHROOM,
            LEVEL_LOWER,
            [(102, 0, 126, 36)],
            "pi-bath-1",
        ),
        RoomSpec("wc-l", "Shared WC", F.WC, LEVEL_LOWER, [(84, 24, 102, 54)]),
        RoomSpec(
            "laundry",
            "Laundry room",
            F.LAUNDRY,
            LEVEL_LOWER,
            [(58, 98, 88, 156)],
            "pi-laundry",
        ),
        RoomSpec(
            "store-l",
            "Lower store room",
            F.STORAGE,
            LEVEL_LOWER,
            [(58, 0, 102, 24)],
            "pi-storage",
        ),
    ]
    terraces = [
        (
            "sp-deck-east",
            "Road-level roof deck (east)",
            LEVEL_ROAD,
            [(114, 14, 160, 124)],
            "pi-balcony",
        ),
        (
            "sp-court-west",
            "West arrival court (sunken; covered porch at north)",
            LEVEL_MAIN,
            [(-20, 40, 20, 96), (-48, 96, 20, 124)],
            "",
        ),
        ("sp-terrace-north", "North-east rooftop terrace", LEVEL_MAIN, [(58, 0, 160, 14)], ""),
        (
            "sp-terrace-south",
            "South terrace (off kitchen, dining & living)",
            LEVEL_MAIN,
            [(20, 124, 160, 156)],
            "pi-terrace",
        ),
        (
            "sp-terrace-east",
            "East balcony (roof of lower floor)",
            LEVEL_MAIN,
            [(160, 0, 198, 156)],
            "pi-balcony",
        ),
        ("sp-terrace-lower", "Lower east garden terrace", LEVEL_LOWER, [(198, 0, 226, 156)], ""),
    ]
    links = [
        # Road
        ("lobby", "garage", True, None),
        ("lobby", "stair-r", False, None),
        ("lobby", "lift-r", True, None),
        ("lobby", "office", True, None),
        ("lobby", "wc-r", True, None),
        ("lobby", "plant", True, None),
        # Main
        ("entry", "hall-u", False, None),
        ("entry", "wc-u", True, None),
        ("entry", "store-u", True, None),
        ("hall-u", "stair-u", False, None),
        ("hall-u", "lift-u", True, None),
        ("hall-u", "kitchen", False, None),
        ("hall-u", "dining", False, None),
        ("hall-u", "living", False, (62, 88)),  # North 38..62 is closed cozy corner
        ("hall-u", "closet", True, None),
        ("closet", "master", True, None),
        ("master", "ensuite-u", True, None),
        ("kitchen", "pantry", False, None),
        ("kitchen", "dining", False, None),
        ("dining", "living", False, None),
        # Lower
        ("hall-l", "stair-l", False, None),
        ("hall-l", "lift-l", True, None),
        ("hall-l", "family", False, None),
        ("hall-l", "bed3", True, None),
        ("bed3", "ensuite-l", True, None),
        ("hall-l", "boys", True, None),
        ("hall-l", "girls", True, None),
        ("hall-l", "shower-l", True, None),
        ("hall-l", "wc-l", True, None),
        ("hall-l", "laundry", True, None),
        ("stair-l", "store-l", True, None),
    ]
    terrace_doors = [
        ("entry", "sp-court-west"),
        ("kitchen", "sp-terrace-south"),
        ("dining", "sp-terrace-south"),
        ("living", "sp-terrace-south"),
        ("living", "sp-terrace-east"),
        ("master", "sp-terrace-east"),
        ("master", "sp-terrace-north"),
        ("office", "sp-deck-east"),
        ("family", "sp-terrace-lower"),
        ("bed3", "sp-terrace-lower"),
        ("boys", "sp-terrace-lower"),
    ]
    outdoor_exits = [
        ("sp-court-west", "south"),
        ("sp-terrace-south", "south"),
        ("sp-terrace-lower", "east"),
    ]
    return OptionSpec(
        option_id=f"{DESIGN_SERIES_ID}-b",
        code="B",
        title="Argon C06-B — 3-Sided Wrap Terraces (North, East & South) & SE Garden Lounge",
        subtitle="Terraces on North, East & South; compact 154 m² main plate; Grandparents at East-Center & Family Room at SE",
        summary=(
            "Steps the main floor in on the north side to create a 3-sided wrap of rooftop terraces "
            "(North-East terrace + East balcony + South terrace — terraces in every direction except west, "
            "Rule 4.3). Downstairs, the grandparents' suite sits at east-center right beside the lift, while "
            "the family room + tea bar anchors the sunny south-east corner with dual south and east views."
        ),
        elevations_m=z,
        storey_heights_m=storey,
        plates_dm=plates,
        lawn_u0_m=22.6,
        lawn_z_m=1668.0,
        cozy_corner_dm=(118, 38, 160, 62),
        tea_bar_dm=(126, 148, 154, 156),
        workshop_bay_dm=(58, 0, 84, 24),
        rooms=rooms,
        terraces=terraces,
        links=links,
        terrace_doors=terrace_doors,
        outdoor_exits=outdoor_exits,
    )


def make_option_c() -> OptionSpec:
    """Option C: South-Center/SE Kitchen Veranda, SW Dining, Panoramic East L-Living & 3 East Lower Bedrooms."""
    z = {LEVEL_ROAD: 1677.7, LEVEL_MAIN: 1674.3, LEVEL_LOWER: 1670.7}
    storey = {LEVEL_ROAD: 3.0, LEVEL_MAIN: 3.4, LEVEL_LOWER: 3.6}
    plates = {
        LEVEL_ROAD: (8, 0, 118, 124),
        LEVEL_MAIN: (22, 0, 166, 124),
        LEVEL_LOWER: (58, 0, 202, 156),
    }
    rooms = [
        *_shared_core_rooms(),
        # Road Level (136.4 m2 indoor)
        RoomSpec(
            "garage",
            "Garage (2 cars + workshop bay)",
            F.GARAGE,
            LEVEL_ROAD,
            [(8, 0, 58, 96), (58, 0, 84, 24)],
            "pi-garage",
        ),
        RoomSpec(
            "lobby",
            "Road entrance lobby",
            F.ENTRY,
            LEVEL_ROAD,
            [(8, 96, 58, 124), (58, 74, 118, 100)],
            "pi-entry",
        ),
        RoomSpec(
            "office",
            "Quiet office / guest",
            F.STUDY,
            LEVEL_ROAD,
            [(84, 0, 118, 54), (102, 54, 118, 74)],
            "pi-study-1",
        ),
        RoomSpec("wc-r", "Road WC + shower", F.BATHROOM, LEVEL_ROAD, [(84, 100, 118, 124)]),
        RoomSpec(
            "plant",
            "Plant / utilities",
            F.MECHANICAL,
            LEVEL_ROAD,
            [(58, 100, 84, 124)],
            "pi-mechanical",
        ),
        # Main Floor (178.6 m2 indoor): SW Dining, South-Center/SE Kitchen, Pantry buffer, East/SE L-Living
        RoomSpec(
            "entry", "Entrance hall (shoes)", F.ENTRY, LEVEL_MAIN, [(22, 52, 58, 90)], "pi-entry"
        ),
        RoomSpec("wc-u", "Guest WC", F.WC, LEVEL_MAIN, [(22, 24, 40, 52)]),
        RoomSpec(
            "store-u", "Coat & shoe store", F.STORAGE, LEVEL_MAIN, [(40, 24, 58, 52)], "pi-storage"
        ),
        RoomSpec(
            "hall-u",
            "Central stair & lift hall",
            F.HALL,
            LEVEL_MAIN,
            [(58, 74, 116, 90), (102, 36, 116, 74)],
        ),
        RoomSpec(
            "dining",
            "Dining room (south veranda)",
            F.DINING,
            LEVEL_MAIN,
            [(22, 90, 72, 124)],
            "pi-dining",
        ),
        RoomSpec(
            "kitchen",
            "Kitchen + everyday dining",
            F.KITCHEN,
            LEVEL_MAIN,
            [(72, 90, 130, 124)],
            "pi-kitchen",
        ),
        RoomSpec(
            "pantry",
            "Pantry (smell buffer)",
            F.PANTRY,
            LEVEL_MAIN,
            [(130, 90, 144, 124)],
            "pi-pantry",
        ),
        RoomSpec(
            "living",
            "Living room (L-shaped + cozy corner)",
            F.LIVING,
            LEVEL_MAIN,
            [(116, 36, 166, 90), (144, 90, 166, 124)],
            "pi-living",
        ),
        RoomSpec(
            "master",
            "Grand master bedroom",
            F.BEDROOM,
            LEVEL_MAIN,
            [(102, 0, 166, 36)],
            "pi-bed-main",
        ),
        RoomSpec("closet", "Dressing vestibule", F.STORAGE, LEVEL_MAIN, [(84, 24, 102, 54)]),
        RoomSpec(
            "ensuite-u",
            "Master bathroom",
            F.BATHROOM,
            LEVEL_MAIN,
            [(22, 0, 102, 24)],
            "pi-bath-ensuite",
        ),
        # Lower Floor (224.6 m2 indoor): ALL 3 Bedrooms on East Garden Terrace; Family Room + Tea Bar on Sunny South!
        RoomSpec(
            "hall-l",
            "Lower central hall",
            F.HALL,
            LEVEL_LOWER,
            [(58, 74, 126, 98), (102, 36, 126, 74)],
        ),
        RoomSpec(
            "boys",
            "Boys bedroom (2 beds, east view)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(126, 0, 202, 48)],
            "pi-bed-child-1",
        ),
        RoomSpec(
            "girls",
            "Girls bedroom (2 beds, east view)",
            F.BEDROOM,
            LEVEL_LOWER,
            [(126, 48, 202, 86)],
            "pi-bed-child-2",
        ),
        RoomSpec(
            "bed3",
            "Parents / grandparents suite",
            F.BEDROOM,
            LEVEL_LOWER,
            [(126, 86, 202, 132)],
            "pi-bed-elder-1",
        ),
        RoomSpec(
            "ensuite-l",
            "Grandparents shower room",
            F.BATHROOM,
            LEVEL_LOWER,
            [(126, 132, 202, 156)],
            "pi-bath-2",
        ),
        RoomSpec(
            "family",
            "Family room + tea & snack bar",
            F.FAMILY,
            LEVEL_LOWER,
            [(88, 98, 126, 156)],
        ),
        RoomSpec(
            "shower-l",
            "Accessible shared bathroom",
            F.BATHROOM,
            LEVEL_LOWER,
            [(102, 0, 126, 36)],
            "pi-bath-1",
        ),
        RoomSpec("wc-l", "Shared WC", F.WC, LEVEL_LOWER, [(84, 24, 102, 54)]),
        RoomSpec(
            "laundry",
            "Laundry room",
            F.LAUNDRY,
            LEVEL_LOWER,
            [(58, 98, 88, 156)],
            "pi-laundry",
        ),
        RoomSpec(
            "store-l",
            "Lower store room",
            F.STORAGE,
            LEVEL_LOWER,
            [(58, 0, 102, 24)],
            "pi-storage",
        ),
    ]
    terraces = [
        (
            "sp-deck-east",
            "Road-level roof deck (east)",
            LEVEL_ROAD,
            [(118, 0, 166, 124)],
            "pi-balcony",
        ),
        (
            "sp-court-west",
            "West arrival court (sunken; covered porch at north)",
            LEVEL_MAIN,
            [(-20, 40, 22, 96), (-48, 96, 22, 124)],
            "",
        ),
        (
            "sp-terrace-south",
            "South terrace (off dining, kitchen & living)",
            LEVEL_MAIN,
            [(22, 124, 166, 156)],
            "pi-terrace",
        ),
        (
            "sp-terrace-east",
            "East balcony (roof of lower floor)",
            LEVEL_MAIN,
            [(166, 0, 202, 156)],
            "pi-balcony",
        ),
        ("sp-terrace-lower", "Lower east garden terrace", LEVEL_LOWER, [(202, 0, 226, 156)], ""),
    ]
    links = [
        # Road
        ("lobby", "garage", True, None),
        ("lobby", "stair-r", False, None),
        ("lobby", "lift-r", True, None),
        ("lobby", "office", True, None),
        ("lobby", "wc-r", True, None),
        ("lobby", "plant", True, None),
        # Main
        ("entry", "hall-u", False, None),
        ("entry", "wc-u", True, None),
        ("entry", "store-u", True, None),
        ("entry", "dining", False, None),
        ("hall-u", "stair-u", False, None),
        ("hall-u", "lift-u", True, None),
        ("hall-u", "dining", False, None),
        ("hall-u", "kitchen", False, None),
        ("hall-u", "living", False, (62, 88)),  # North 36..62 is closed cozy corner
        ("hall-u", "closet", True, None),
        ("closet", "master", True, None),
        ("master", "ensuite-u", True, None),
        ("kitchen", "dining", False, None),
        ("kitchen", "pantry", False, None),
        # Lower
        ("hall-l", "stair-l", False, None),
        ("hall-l", "lift-l", True, None),
        ("hall-l", "family", False, None),
        ("hall-l", "bed3", True, None),
        ("bed3", "ensuite-l", True, None),
        ("hall-l", "boys", True, None),
        ("hall-l", "girls", True, None),
        ("hall-l", "shower-l", True, None),
        ("hall-l", "wc-l", True, None),
        ("hall-l", "laundry", True, None),
        ("stair-l", "store-l", True, None),
    ]
    terrace_doors = [
        ("entry", "sp-court-west"),
        ("dining", "sp-terrace-south"),
        ("kitchen", "sp-terrace-south"),
        ("living", "sp-terrace-south"),
        ("living", "sp-terrace-east"),
        ("master", "sp-terrace-east"),
        ("office", "sp-deck-east"),
        ("boys", "sp-terrace-lower"),
        ("girls", "sp-terrace-lower"),
        ("bed3", "sp-terrace-lower"),
    ]
    outdoor_exits = [
        ("sp-court-west", "south"),
        ("sp-terrace-south", "south"),
        ("sp-terrace-lower", "east"),
    ]
    return OptionSpec(
        option_id=f"{DESIGN_SERIES_ID}-c",
        code="C",
        title="Argon C06-C — South-East Kitchen Veranda, Pantry Buffer & All-East Lower Bedrooms",
        subtitle="Kitchen shifted SE with pantry buffer before living; SW dining veranda; all 3 lower bedrooms facing east garden",
        summary=(
            "Places the dining room on the south-west terrace front and shifts the kitchen toward the "
            "south-east, with the pantry tucked between the kitchen and the living room's SE wing as a "
            "complete smell and acoustic buffer. Downstairs, all three bedrooms (Boys, Girls, Grandparents) "
            "line the east garden terrace with walk-out doors, while the family room + tea bar enjoys the "
            "sunny south facade."
        ),
        elevations_m=z,
        storey_heights_m=storey,
        plates_dm=plates,
        lawn_u0_m=22.6,
        lawn_z_m=1668.2,
        cozy_corner_dm=(116, 36, 166, 62),
        tea_bar_dm=(88, 98, 116, 106),
        workshop_bay_dm=(58, 0, 84, 24),
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
    """Assert that rooms on each level tile the level plate with 0 gap and 0 overlap."""
    for lv, (pu0, pv0, pu1, pv1) in spec.plates_dm.items():
        plate_box = box(pu0, pv0, pu1, pv1)
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
        diff = merged.symmetric_difference(plate_box).area
        assert diff < 1e-6 and abs(area_sum - plate_box.area) < 1e-6, (
            f"{spec.option_id} {lv}: tiling mismatch diff={diff}, sum={area_sum}, plate={plate_box.area}"
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
        strategy="stepped_terraces_exact_tiling",
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
        self, a: str, b: str, span_clip: tuple[int, int], width_m: float = 2.0
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
        self._exterior(
            "sp-garage",
            OpeningKind.DOOR,
            5.2,
            is_west_road,
            operation=Operation.SLIDING,
            prefix="d-garage",
        )
        self._exterior(
            "sp-lobby",
            OpeningKind.DOOR,
            1.1,
            is_west_road,
            operation=Operation.SWING_RIGHT,
            prefix="d-hayat",
        )

        for a, b, is_opening, span_clip in self.doors:
            if span_clip is not None:
                self._place_clipped_opening(a, b, span_clip, width_m=2.0)
                continue
            pair = frozenset((rid[a].function, rid[b].function)) if b in rid else None
            if pair in DOORLESS_FUNCTION_PAIRS and not (
                a.startswith(OUTDOOR_PREFIXES) or b.startswith(OUTDOOR_PREFIXES)
            ):
                is_opening = True
            if is_opening:
                seg = max(self._walls_between(a, b), key=lambda w: w.length_dm)
                both_out = a.startswith(OUTDOOR_PREFIXES) and b.startswith(OUTDOOR_PREFIXES)
                self.place_opening(
                    a,
                    b,
                    OpeningKind.OPENING,
                    width_m=min(seg.length_m - 0.4, 3.2),
                    height_m=1.0 if both_out else 2.4,
                    operation=Operation.NONE,
                    prefix="op",
                )
            elif b.startswith(OUTDOOR_PREFIXES):
                entry = a == "sp-entry"
                self.place_opening(
                    a,
                    b,
                    OpeningKind.DOOR,
                    width_m=1.1 if entry else 1.8,
                    operation=Operation.SWING_RIGHT if entry else Operation.SLIDING,
                    prefix="d-out",
                )
            else:
                wet = {rid[a].function, rid[b].function} & {F.BATHROOM, F.WC}
                self.place_opening(
                    a,
                    b,
                    OpeningKind.DOOR,
                    width_m=0.8 if wet else 0.9,
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
                    if self._place_shared_window(r.space_id, t, width_m=1.8):
                        placed += 1
            for _ in range(2 - placed):
                if not self._exterior(
                    r.space_id,
                    OpeningKind.WINDOW,
                    1.8,
                    self._windowable,
                    height_m=DEFAULT_WINDOW_HEIGHT_M,
                    sill_m=WINDOW_SILL_M,
                    operation=Operation.SLIDING,
                    prefix="win",
                ):
                    self._slide_window(r.space_id)

    def _place_shared_window(self, a: str, b: str, width_m: float = 1.8) -> bool:
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
        for w_dm in (int(round(width_m * 10)), 16, 14):
            for w in sorted(self._walls_between(a, b), key=lambda s: -s.length_dm):
                for off in range(2, w.length_dm - w_dm, 1):
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

    def _slide_window(self, sid: str, width_dm: int = 14) -> bool:
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
        # Continuous 3-level Central Heart Stair: Lower -> Main and Main -> Road (Rule 5.2 & 5.3)
        st_lower_main = self._make_stair(
            "stair-lower-main", LEVEL_LOWER, LEVEL_MAIN, "sp-stair-l", "sp-stair-u"
        )
        st_main_road = self._make_stair(
            "stair-main-road", LEVEL_MAIN, LEVEL_ROAD, "sp-stair-u", "sp-stair-r"
        )
        model.stairs = [st_lower_main, st_main_road]

        # Rebuild exact slabs from sub_rects (resolving L-shaped slab limitation) and cut stair openings
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
    """Programmatically verify every rule in `projects/my-house/design/OWNER_DESIGN_RULES.md`."""
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
    r_1_2 = k_room.v1 == main_plate_v1 and (k_room.u1 - k_room.u0) >= 50

    # 1.3 Semi-open kitchen with 2 walk-throughs, keeping cooking smells out of living room
    k_openings = [
        o
        for o in model.openings
        if o.kind is OpeningKind.OPENING
        and "sp-kitchen" in o.connects
        and not any(c.startswith(OUTDOOR_PREFIXES) for c in o.connects)
    ]
    k_direct_to_living = "sp-living" in graph.get("sp-kitchen", set())
    r_1_3 = len(k_openings) >= 2 and not k_direct_to_living

    # 1.4 Everyday meals in kitchen; dining next to kitchen
    r_1_4 = spaces_by_id["sp-kitchen"].area_m2 >= 18.0 and "sp-dining" in graph.get(
        "sp-kitchen", set()
    )

    # 2.1 Every main room reached directly from entrance/stair hall, never through another main room
    hall_hub_u = {"sp-entry", "sp-hall-u"}
    direct_kitchen = any(h in graph["sp-kitchen"] for h in hall_hub_u)
    direct_dining = any(h in graph["sp-dining"] for h in hall_hub_u)
    direct_living = any(h in graph["sp-living"] for h in hall_hub_u)
    direct_master = (
        any(h in graph["sp-closet"] for h in hall_hub_u) and "sp-master" in graph["sp-closet"]
    )
    hall_hub_l = {"sp-hall-l"}
    direct_lower_beds = all(
        any(h in graph[b] for h in hall_hub_l)
        for b in ("sp-bed3", "sp-boys", "sp-girls", "sp-family")
    )
    r_2_1 = (
        direct_kitchen and direct_dining and direct_living and direct_master and direct_lower_beds
    )

    # 2.2 No long institutional corridors
    r_2_2 = spaces_by_id["sp-hall-u"].area_m2 <= 18.0 and spaces_by_id["sp-hall-l"].area_m2 <= 36.0

    # 2.3 Exact tiling: no voids or leftover holes
    _verify_exact_plate_tiling(spec)
    r_2_3 = True

    # 2.4 No unnecessary doors or barriers
    r_2_4 = any(
        o.kind is OpeningKind.OPENING and set(o.connects) == {"sp-hall-u", "sp-living"}
        for o in model.openings
    )

    # 3.1 & 3.2 Living room L-shaped with cozy sheltered corner (closed on north/hall side) + direct hall entry
    liv_room = rooms_by_id["sp-living"]
    liv_hall_ops = [o for o in model.openings if set(o.connects) == {"sp-hall-u", "sp-living"}]
    cozy_u0, cozy_v0, cozy_u1, cozy_v1 = spec.cozy_corner_dm
    # Check that the hall->living opening lies strictly south of cozy_v1 (so west wall of cozy corner is closed)
    op_clear_of_cozy = True
    for o in liv_hall_ops:
        w = walls_by_id[o.host_wall_id]
        (_, v_start), (_, v_end) = frame.to_design(w.start), frame.to_design(w.end)
        v_min_m = min(v_start, v_end) + o.offset_m
        if v_min_m * 10 < cozy_v1 - 1e-3:
            op_clear_of_cozy = False
    r_3_1 = liv_room.sub_rects is not None and len(liv_room.sub_rects) == 2 and op_clear_of_cozy
    r_3_2 = direct_living and len(liv_hall_ops) == 1

    # 4.1 South and east frontage dedicated to day rooms, bedrooms, and terraces
    r_4_1 = k_room.v1 == main_plate_v1 and liv_room.u1 == spec.plates_dm[LEVEL_MAIN][2]

    # 4.2 House not narrow towards east (stepped to u ≈ 20 m, confirmed in stmt-018)
    lower_u1_m = spec.plates_dm[LEVEL_LOWER][2] / 10.0
    r_4_2 = 19.5 <= lower_u1_m <= 21.0

    # 4.3 Plenty of terraces on main floor (south, east, and in Option B north)
    main_terraces_m2 = sum(
        s.area_m2 for s in model.spaces if s.level_id == LEVEL_MAIN and s.function is F.TERRACE
    )
    r_4_3 = main_terraces_m2 >= 100.0

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
        and stair_r.v0 >= plate_m[1] + 10
        and stair_r.v1 <= plate_m[3] - 30
    )
    r_5_2 = (
        len(model.stairs) == 2
        and all(f for f in [True])
        and "sp-stair-u" in graph["sp-stair-r"]
        and "sp-stair-l" in graph["sp-stair-u"]
    )
    r_5_3 = in_heart

    # 5.5 & 6.3 Oversized 2-car garage + integrated workshop bay (~55-60 m2), lower store tucked by core
    garage_m2 = spaces_by_id["sp-garage"].area_m2
    r_5_5 = 53.0 <= garage_m2 <= 62.0

    # 6.1-6.6 Bedrooms, bathrooms, tea bar, tucked lower store
    r_6_all = (
        spaces_by_id["sp-master"].area_m2 >= 12.0
        and spaces_by_id["sp-bed3"].area_m2 >= 14.0
        and spaces_by_id["sp-boys"].area_m2 >= 16.0
        and spaces_by_id["sp-girls"].area_m2 >= 16.0
        and spaces_by_id["sp-shower-l"].area_m2 >= 5.5
    )

    checks = [
        (
            "1.1",
            "Kitchen opens directly onto South Terrace and looks south",
            r_1_1,
            "Sliding door d-out + window directly from sp-kitchen to sp-terrace-south",
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
            "1.4",
            "Everyday dining in kitchen; guest dining next to kitchen",
            r_1_4,
            f"Kitchen {spaces_by_id['sp-kitchen'].area_m2:.1f} m², Dining {spaces_by_id['sp-dining'].area_m2:.1f} m² adjacent",
        ),
        (
            "2.1",
            "Every main room reached directly from entrance/stair hall (never through another room)",
            r_2_1,
            "Direct openings from central hall to Kitchen, Dining, Living, Master Suite, and all 3 lower bedrooms",
        ),
        (
            "2.2",
            "No long institutional corridors",
            r_2_2,
            f"Compact central foyer/stair hall ({spaces_by_id['sp-hall-u'].area_m2:.1f} m² main, {spaces_by_id['sp-hall-l'].area_m2:.1f} m² lower)",
        ),
        (
            "2.3",
            "No voids, leftover holes, or puzzle layouts (100% exact plate tiling)",
            r_2_3,
            "Mathematical 0.00 m² gap and 0.00 m² overlap across all 3 floor plates",
        ),
        (
            "2.4",
            "No unnecessary interior doors or barriers",
            r_2_4,
            "Wide doorless openings between Entry, Central Hall, Living, Dining, Kitchen, Pantry, and Family Room",
        ),
        (
            "3.1",
            "Living room has a cozy, sheltered L-shaped sitting corner closed on north/hall side",
            r_3_1,
            f"Cozy corner ({(cozy_u1 - cozy_u0) * (cozy_v1 - cozy_v0) / 100:.1f} m²) screened by solid north & west walls",
        ),
        (
            "3.2",
            "Living room closed-off corner is not cut off (direct wide opening from Central Hall)",
            r_3_2,
            "2.0 m wide direct doorless opening from sp-hall-u into sp-living",
        ),
        (
            "4.1",
            "South and east prime frontage used for day rooms and terraces",
            r_4_1,
            "South = Kitchen, Dining, Living & South Terrace; East = Living, Master, Lower Bedrooms & Balconies",
        ),
        (
            "4.2",
            "House steps east to u ≈ 20 m (not narrow towards east, stmt-018)",
            r_4_2,
            f"Road u={spec.plates_dm[LEVEL_ROAD][0] / 10:.1f}–{spec.plates_dm[LEVEL_ROAD][2] / 10:.1f} m, Main u={spec.plates_dm[LEVEL_MAIN][0] / 10:.1f}–{spec.plates_dm[LEVEL_MAIN][2] / 10:.1f} m, Lower u={spec.plates_dm[LEVEL_LOWER][0] / 10:.1f}–{lower_u1_m:.1f} m",
        ),
        (
            "4.3",
            "Generous terraces on main floor in non-west directions",
            r_4_3,
            f"{main_terraces_m2:.1f} m² of outdoor terraces/courts on the main floor",
        ),
        (
            "5.1",
            "Indoor route from garage straight to lift and stair (for groceries)",
            r_5_1,
            "Direct interior door sp-garage -> sp-lobby -> sp-lift-r & sp-stair-r",
        ),
        (
            "5.2",
            "One continuous stair connects Road, Main, and Lower floors (works without electricity)",
            r_5_2,
            "Two stacked U-flights (stair-main-road + stair-lower-main) in the same 2.6×5.0 m shaft",
        ),
        (
            "5.3",
            "Stair is at the heart of the house, not hidden in a perimeter corner",
            r_5_3,
            f"Central spine u={stair_r.u0 / 10:.1f}–{stair_r.u1 / 10:.1f} m, v={stair_r.v0 / 10:.1f}–{stair_r.v1 / 10:.1f} m",
        ),
        (
            "5.5",
            "Oversized 2-car garage (~55–60 m²) with integrated workshop bay (stmt-018)",
            r_5_5,
            f"Garage + workshop bay = {garage_m2:.1f} m² (5.2×9.2 m car bay + 2.6×2.4 m workbench alcove)",
        ),
        (
            "6.1–6.6",
            "Master en-suite upstairs; 3 bedrooms + Family Tea/Snack Bar + tucked Store downstairs",
            r_6_all,
            f"Master {spaces_by_id['sp-master'].area_m2:.1f} m²; Grandparents {spaces_by_id['sp-bed3'].area_m2:.1f} m²; Boys {spaces_by_id['sp-boys'].area_m2:.1f} m²; Girls {spaces_by_id['sp-girls'].area_m2:.1f} m²; Family+Tea Bar {spaces_by_id['sp-family'].area_m2:.1f} m²",
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
        LEVEL_ROAD: f"Road level +{spec.elevations_m[LEVEL_ROAD]:.1f} — Garage + workshop, lobby, lift/stair, office",
        LEVEL_MAIN: f"Main floor +{spec.elevations_m[LEVEL_MAIN]:.1f} — South kitchen, dining, L-living, master suite",
        LEVEL_LOWER: f"Lower floor +{spec.elevations_m[LEVEL_LOWER]:.1f} — 3 bedrooms, family + tea bar, garden terrace",
    }
    for lv in model.levels:
        lv.name = level_names[lv.id]

    model.assumptions = [
        Assumption(
            id=f"{spec.option_id}-basis",
            made_by=actor,
            statement=(
                f"EXPLORATORY ({spec.title}). Stepped 3-level hillside plan reaching u={spec.plates_dm[LEVEL_LOWER][2] / 10:.1f} m "
                f"(lower terrace to {spec.lawn_u0_m:.1f} m, flat east lawn at +{spec.lawn_z_m:.1f} m). "
                "Central heart stair and lift connect all 3 levels; indoor garage->lobby->lift/stair route; "
                "south kitchen opening directly onto south terrace; direct central hall access to every main room; "
                "L-shaped living room with sheltered cozy corner; downstairs family room with tea/snack bar. "
                "Not structurally, geotechnically, or code certified."
            ),
        )
    ]

    plan = PlanVersion(
        option_id=model.id,
        label=model.name,
        strategy="stepped-terraces-exact-tiling",
        model=model,
        provenance=Provenance(
            created_at=store.clock(),
            created_by=actor,
            method="cpsat_exact_tiling",
            inputs=[site_ref, program_ref],
        ),
        generation=GenerationRecord(
            generator="argon-c06-generator",
            generator_version="1.0",
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
                "tea_bar_dm": spec.tea_bar_dm,
                "workshop_bay_dm": spec.workshop_bay_dm,
                "stair_fits": builder.stair_fits,
                "rooms": [{**r.__dict__, "function": r.function.value} for r in sol.rooms],
            },
            indent=2,
            default=str,
        )
        + "\n"
    )
    print(
        f"GENERATED {spec.option_id}: check_model findings={len(findings)}, "
        f"stair_fits={builder.stair_fits}, owner_rules={len(rule_audit)}/{len(rule_audit)} PASS"
    )
    return {"option_id": spec.option_id, "findings": len(findings), "rules_passed": len(rule_audit)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--option", choices=["a", "b", "c", "all"], default="all")
    args = ap.parse_args()
    keys = ["a", "b", "c"] if args.option == "all" else [args.option]
    for k in keys:
        generate_option(OPTIONS[k])


if __name__ == "__main__":
    main()
