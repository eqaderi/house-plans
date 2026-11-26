"""C11: C10 with every correction of the 27-reviewer review (CONSOLIDATED.md) and the corrected owner rules.

Frame as in C08-C10: u = metres east along the north boundary (downhill), v = metres south.
Owner levels kept: road 1677.50, main 1673.60, lower 1670.00.

What C11 answers first (stmt-027, rule 4.9): every floor stands on a wall, a column line or solid ground.
- The garage stands wholly on the main floor: a buried service room (tanks, booster, bulk store) is dug
  under the half of the garage that stood on nothing in C10 (C11-STR-01).
- The main floor stands on the lower floor's walls, on the column line v 13.0, on the loggia's RC wall
  and on dug ground. The lower north wall moves out to v 1.1 so the master suite has a wall under it
  (C11-STR-02), and the lower south rooms move north so the outdoor stair has its own band (C11-ARR-02).
- The lower floor stands on dug ground; where the hill falls away (lounge east, loggia, garden terrace)
  its slab is suspended between foundation walls over a ventilated crawl void (C11-STR-07, GEO-03).

Real walls (C11-THM-01): exterior 0.40 m (0.15 m inside the footprint line, 0.25 m outside), partitions
0.12 m, dense acoustic walls 0.20 m, stair core 0.25 m RC, lift shaft 0.20 m RC. Room sizes are clear sizes.
"""

from __future__ import annotations

import math

from engine import (
    ENVELOPE,
    PARCEL,
    Door,
    Level,
    Option,
    R,
    Room,
    Shape,
    Terrace,
    Win,
    armchair,
    basin,
    bed,
    car,
    coffee,
    counter,
    desk,
    flat,
    lift_car,
    lockers,
    rect,
    shower,
    sofa,
    sofa_l,
    stair_dogleg,
    table_chairs,
    wardrobe,
    wc,
)
from shapely.affinity import rotate
from shapely.geometry import LineString, Point, Polygon
from structure import Element, Flight, OutdoorStair

Z_ROAD, Z_MAIN, Z_LOWER = 1677.50, 1673.60, 1670.00
Z_LAWN = 1667.60  # owner question Q4: default lawn level (CONSOLIDATED §4c)
Z_FORE = 1677.47  # forecourt at the shutters and the road door (C11-WAT-01: threshold <= 20 mm)
Z_COURT = Z_MAIN
Z_TLOW = 1669.98
STAIR = (6.8, 1.1, 9.4, 7.3)  # owner's dog-leg with REST 1.40 at north, flights 1.2 m, same box on every floor
LIFT = (9.4, 4.5, 11.4, 7.3)  # C11-CIR-02: clear 1.80 x 2.60 m inside 0.20 m RC walls, stretcher car
EAST = 18.0  # main and lower east walls on one line (C11-STR-05)
BALC = 19.85  # balcony edge: 1.6 m clear from the wall face, on a beam and columns at u 19.6 (C11-THM-03)
TERR = 20.6  # garden terrace edge: RC wall founded at ~1666.5 (C11-GEO-03)
SOUTH_LOW = 15.75  # lower south wall: outer face 16.00, leaving 1.42 m for the court-to-garden stair
SOUTH_MAIN = 13.0
CONTOUR_SLOPE, LAWN_EDGE = 0.448, 28.5
QIBLA = 204.64  # degrees true, computed from the owner-supplied point (inferred; CRS unconfirmed)
RISER_W = (4.75, 8.84, 5.5, 9.44)  # SH-W: wet stacks, rising main, extracts, radon pipe (moved, see CORRECTIONS)
RISER_K = (4.85, 12.25, 5.45, 12.85)  # SH-K: hood duct, kitchen waste, heating, mains (C11-MEP-02)
RISER_E = (11.0, 2.4, 11.4, 3.0)  # SH-E: in the wall shared by the stacked ensuites, clear of both ensuite doors (fix round)
COLS_S = (4.6, 6.8, 11.1, 15.4, 18.0)  # continuous 0.35 m columns on the south façade line v 13.0 (C11-STR-03)
Z_WALK = 1669.98  # garden walk level with the loggia and garden terrace; slot channel and tanking at the bedroom wall (fix round)
GRID_U = (0.0, 2.0, 4.6, 6.8, 9.4, 11.4, 12.6, 15.4, 18.0)
GRID_V = (1.1, 4.5, 6.2, 7.3, 9.5, 10.95, 13.0, 15.75)


def lawn_edge(v: float) -> float:
    return LAWN_EDGE - CONTOUR_SLOPE * v


def qibla_dir() -> tuple[float, float]:
    """Unit vector of the qibla in the design frame (u, v)."""
    import engine as E

    rel = math.radians(QIBLA - (E.U_BEARING + E.TRUE_NORTH))  # angle from +u, clockwise on the compass = towards +v
    return math.cos(rel), math.sin(rel)


def prayer_mats(cu: float, cv: float, n: int = 2) -> list[Shape]:
    """Mats 0.8 x 1.25 m with their long axis on the qibla, side by side, centred on (cu, cv)."""
    qu, qv = qibla_dir()
    ang = math.degrees(math.atan2(qv, qu))
    out = []
    for i in range(n):
        off = (i - (n - 1) / 2) * 0.95
        c = (cu - qv * off, cv + qu * off)
        m = R(c[0] - 0.625, c[1] - 0.4, c[0] + 0.625, c[1] + 0.4)
        out.append(Shape(rotate(m, ang, origin=c), "mat"))
    return out


def minus(poly, *holes):
    for h in holes:
        poly = poly.difference(h)
    return poly


def LS(*pts):
    return LineString(pts)


# ---------------------------------------------------------------- road level
def road_level() -> Level:
    rw = R(*RISER_W)
    rooms = [
        Room("garage", "GARAGE · 2 CARS + WORKBENCH", "garage", minus(R(0.0, 1.1, 6.8, 9.5), rw), label_at=(2.9, 4.95)),
        Room("riser-w", "", "riser", rw, show_dims=False, small=True),
        Room("stair-r", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-r", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("lobby-r", "CORE LOBBY", "hall", R(6.8, 7.3, 12.6, 9.5), label_at=(10.9, 8.2), show_dims=False, small=True),
        Room("hall-r", "ENTRANCE HALL", "hall", minus(R(0.0, 9.5, 9.4, 11.6), R(4.4, 11.3, 9.4, 11.6)), label_at=(4.3, 10.5)),
        Room("wc-r", "WC + SHOWER", "wet", R(2.0, 11.6, 4.4, 13.0), small=True, label_at=(2.75, 12.75)),
        Room("plant", "PLANT ROOM", "service", minus(R(4.4, 11.3, 9.4, 13.0), R(*RISER_K)), small=True, label_at=(7.0, 11.75)),
        Room("riser-k", "", "riser", R(*RISER_K), show_dims=False, small=True),
        Room("office", "QUIET OFFICE", "study", R(9.4, 9.5, 12.6, 13.0), label_at=(11.0, 11.6)),
    ]
    doors = [
        Door("garage", "ext", 0.0, 3.075, 3.35, "v", "shutter"),  # aligned with the car lanes (fix round, VEH-N02)
        Door("garage", "ext", 0.0, 7.025, 3.35, "v", "shutter"),
        Door("hall-r", "ext", 0.0, 10.6, 1.0, "v", "door", swing=1, hinge=-1),
        # C11-VEH-01: fire door moved to v 8.35-9.35, swinging into the garage, hinged at v 9.35
        Door("garage", "lobby-r", 6.8, 8.85, 1.0, "v", "fire", swing=-1, hinge=1),
        # C11-VEH-04 (rule 2.4): full-height glazed screen with a 1.0 m self-closing glass door across the stair mouth
        Door("lobby-r", "stair-r", 8.1, 7.3, 2.6, "u", "screen"),
        Door("lobby-r", "lift-r", 10.4, 7.3, 0.9, "u", "glass"),
        Door("hall-r", "lobby-r", 8.1, 9.5, 2.4, "u", "open"),
        Door("lobby-r", "ext", 12.6, 8.4, 1.0, "v", "glass"),
        Door("lobby-r", "office", 10.45, 9.5, 0.9, "u", "door", swing=1, hinge=-1),
        Door("hall-r", "wc-r", 3.975, 11.6, 0.75, "u", "door", swing=1, hinge=-1),
        Door("hall-r", "plant", 6.4, 11.3, 1.2, "u", "door", swing=-1, hinge=1),
        Door("office", "ext", 12.6, 11.9, 1.8, "v", "slide"),
    ]
    windows = [Win(9.7, 13.0, 10.8, 13.0), Win(2.4, 13.0, 3.2, 13.0)]
    furniture = flat(
        # C11-VEH-01/02: cars between u 0.55 and 5.54; aisle u 5.54-6.74 clear; LC300 in bay 2
        car(0.55, 2.15, 4.75, 1.98, "CAR 1"), car(0.56, 5.90, 4.98, 1.98, "LC300"),
        rect(5.54, 1.25, 6.74, 8.84, "aisle"), Shape(Point(6.14, 4.0), "text", "AISLE 1.2"),
        rect(0.6, 8.84, 4.7, 9.44, "bench"), Shape(Point(2.65, 8.6), "text", "WORKBENCH 4.1 m · BIKES HUNG ABOVE"),
        rect(1.0, 1.25, 3.4, 1.55, "dash"), Shape(Point(2.2, 1.75), "text", "TYRES (HIGH)"),
        Shape(Point(6.72, 5.0).buffer(0.08), "dash"), Shape(Point(6.3, 5.3), "text", "EV"),
        lockers(0.6, 9.55, 4.2, 10.0, 6), Shape(Point(2.4, 10.25), "text", "6 LOCKERS · SHOES"),
        rect(4.4, 9.55, 5.6, 9.95, "bench"),
        stair_dogleg(*STAIR, label="DOWN 24R"), lift_car(*LIFT),
        desk(9.55, 11.95, 11.45, 12.8, (10.5, 11.6)), rect(11.6, 9.6, 12.45, 11.4, "dash"),
        Shape(Point(12.0, 10.5), "text", "FOLD BED"),
        wc(3.4, 11.95, "s"), basin(3.95, 12.65, 0.45, 0.35), shower(2.15, 11.68, 3.15, 12.58),
        rect(5.6, 12.2, 6.3, 12.85, "fixture", "B"), Shape(Point(6.9, 12.5).buffer(0.32), "fixture", "CYL"),
        rect(7.4, 12.25, 8.6, 12.85, "fixture", "MVHR"), rect(8.7, 12.4, 9.3, 12.85, "fixture"),
        Shape(Point(7.3, 11.6), "text", "0.9 m CLEAR · BUNDED FLOOR · OWN FLUE"),
        rect(14.0, 6.35, 17.8, 8.0, "dash"), Shape(Point(15.9, 7.2), "text", "DRYING YARD · 1.5 m SCREEN"),
        Shape(LS((12.6, 7.3), (12.6, 6.2), (EAST, 6.2)), "guard"), Shape(Point(14.0, 5.9), "text", "1.1 m GUARD · LOCKED GATE"),
        Shape(Point(8.1, 2.6), "text", "VOID OVER THE HALF-LANDING · 1.1 m GUARDS"),
        rect(0.0, 0.05, 2.4, 1.05, "dash"), Shape(Point(1.2, 0.55), "text", "BINS"),
        rect(2.6, 0.1, 3.4, 0.7, "dash"), Shape(Point(3.0, 0.4), "text", "LPG"),
        Shape(LS((bline(11.6, 0.15), 11.6), (bline(17.27, 0.15), 17.27)), "guard"),
        Shape(Point(-8.4, 13.4), "text", "RC PARAPET +0.7 m + RAIL"),
        rect(bline(11.6, 0.3) + 0.05, 9.95, bline(11.6, 0.3) + 1.65, 11.55, "dash"), Shape(Point(-5.0, 10.3), "text", "REFUGE · 2 BOLLARDS · SLIDING GATE"),
        rect(7.6, 9.6, 9.0, 11.5, "dash"), Shape(Point(8.3, 11.0), "text", "ROOFLIGHT"),
        Shape(Point(-1.6, 11.0), "text", "CANOPY · ADDRESS · INTERCOM"),
    )
    deck = R(12.6, 6.2, EAST, 13.0)
    green = Polygon([(9.4, 1.1), (EAST, 1.1), (EAST, 6.2), (12.6, 6.2), (12.6, 7.3), (11.4, 7.3), (11.4, 4.5), (9.4, 4.5)])
    fore = Polygon([(0.0, 1.1), (0.0, 11.6), (-6.35, 11.6), (-0.6, 1.1)]).intersection(PARCEL)
    # suspended deck where fill would exceed 1 m, and over the whole strip v 8.6-11.6 behind W1 (fix round, GEO-05)
    split = Polygon([(-0.2, 5.6), (0.0, 5.6), (0.0, 11.6), (-6.35, 11.6), (bline(8.6, 0.0), 8.6), (-1.65, 8.6)])
    terraces = [
        Terrace("deck-r", "ROOF TERRACE", deck, Z_ROAD - 0.02, "deck", label_at=(15.3, 10.6)),
        Terrace("green-r", "GREEN ROOF", green, Z_ROAD - 0.02, "green", label_at=(14.6, 3.6),
                note="extensive, maintenance only, guarded"),
        Terrace("fore", "FORECOURT", fore.difference(split), Z_FORE, "court", label_at=(-2.6, 5.0)),
        Terrace("fore-deck", "", fore.intersection(split), Z_FORE, "deck", note="suspended deck"),
    ]
    notes = [
        "Front door on the west façade under a canopy, straight into the entrance hall; the hall ends on the lit core lobby, the stair behind a glazed safety screen, and the roof terrace beyond.",
        "Groceries: garage → fire door → core lobby → lift is a 4.4 m walk, all indoors (rule 5.1). The 1.2 m unloading aisle along the east side stays clear.",
        "Two 3.35 m shutters lined up with the two car lanes; reverse in, drive out. LC300 in bay 2. A 4.1 m workbench along the back wall, bikes hung above it. The whole garage stands on the walls of the service room below.",
        "WC + shower sits over the main-floor entry and drains west to the road by gravity. Plant room 5.0 × 1.7 m (boiler with its own flue, cylinder, MVHR) with a 1.2 m door; water tanks are below, on the ground.",
        "Office 3.2 × 3.5 m on the roof terrace, walls on the grid lines u 9.4 / 12.6 and v 13.0.",
    ]
    lv = Level("road", "ROAD LEVEL", Z_ROAD, rooms, doors, windows, furniture, terraces, notes)
    lv.wall_lines = core_walls()
    lv.suspended = [R(0.0, 9.5, 2.0, 11.6)]  # road hall over the main-floor porch
    return lv


def core_walls():
    """Stair core 0.25 m RC (with the solid spine between the flights), lift shaft 0.20 m RC."""
    u0, v0, u1, v1 = STAIR
    a0, b0, a1, b1 = LIFT
    return [(LS((u0, v0), (u1, v0)), 0.25), (LS((u0, v0), (u0, v1)), 0.25), (LS((u1, v0), (u1, b0)), 0.25),
            (LS((a0, b0), (a1, b0)), 0.20), (LS((a1, b0), (a1, b1)), 0.20), (LS((a0, b0), (a0, b1)), 0.20)]


# ---------------------------------------------------------------- main floor
def main_level() -> Level:
    rw = R(*RISER_W)
    # the bedroom doors moved back to v 6.2, off the lift wall (fix round, ACS-N03 / PRV-N06)
    hall = minus(Polygon([(2.0, 7.3), (11.4, 7.3), (11.4, 6.2), (12.6, 6.2), (12.6, 8.75), (9.4, 8.75), (9.4, 9.5), (2.0, 9.5)]), rw)
    master = Polygon([(11.4, 6.2), (11.4, 3.4), (13.2, 3.4), (13.2, 1.1), (EAST, 1.1), (EAST, 6.2)])
    rooms = [
        Room("tanks", "WATER + TANKS", "service", R(0.0, 1.1, 2.0, 9.5), small=True, label_at=(1.0, 5.3)),
        Room("bulk", "BULK STORE", "service", Polygon([(2.0, 1.1), (6.8, 1.1), (6.8, 2.8), (3.8, 2.8), (3.8, 4.6), (2.0, 4.6)]),
             small=True, label_at=(4.6, 1.95)),
        Room("pantry", "PANTRY", "service", R(2.0, 4.6, 3.8, 7.3), small=True, label_at=(2.9, 5.95)),
        Room("sh-m", "SHOWER", "wet", R(3.8, 2.8, 4.95, 5.15), small=True, show_dims=False, label_at=(4.4, 3.4)),
        Room("wc-m", "ACC. WC", "wet", R(4.95, 2.8, 6.8, 5.15), small=True, label_at=(5.75, 4.75)),
        Room("wudu", "WUDU", "wet", R(3.8, 5.15, 5.3, 7.3), small=True, show_dims=False, label_at=(4.15, 5.6)),
        Room("wlob", "LOBBY", "wet", R(5.3, 5.15, 6.8, 7.3), small=True, show_dims=False, label_at=(6.05, 5.65)),
        Room("stair-m", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-m", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("ens", "ENSUITE", "wet", minus(R(9.4, 1.1, 11.4, 4.5), R(*RISER_E)), small=True, label_at=(10.3, 2.4)),
        Room("riser-e", "", "riser", R(*RISER_E), show_dims=False, small=True),
        Room("dress", "DRESSING", "service", R(11.4, 1.1, 13.2, 3.4), small=True, label_at=(12.5, 2.55)),
        Room("master", "MASTER BEDROOM", "sleep", master, label_at=(16.3, 4.95), main=True),
        Room("hall", "FAMILY HALL", "hall", hall, label_at=(7.6, 8.55)),
        Room("riser-w", "", "riser", rw, show_dims=False, small=True),
        Room("entry", "ENTRY", "hall", R(2.0, 9.5, 4.4, 13.0), small=True, label_at=(3.0, 11.0)),
        Room("kitchen", "KITCHEN", "kitchen", minus(R(4.4, 9.5, 9.4, 13.0), R(*RISER_K)), main=True, label_at=(7.9, 11.85)),
        Room("riser-k", "", "riser", R(*RISER_K), show_dims=False, small=True),
        Room("dining", "DINING · 8", "day", R(9.4, 8.75, 12.6, 13.0), main=True, label_at=(11.75, 12.45)),
        Room("living", "LIVING", "day", R(12.6, 6.2, EAST, 13.0), label_at=(15.0, 10.75), main=True),
    ]
    doors = [
        # C11-KB-03: screened 4-part wet cluster; hall -> dry lobby; accessible WC off the lobby, shower off the wudu
        Door("hall", "wlob", 5.8, 7.3, 0.9, "u", "open"),
        Door("wlob", "wudu", 5.3, 5.7, 0.9, "v", "open"),
        Door("wlob", "wc-m", 6.25, 5.15, 0.8, "u", "slide"),  # east end: the pan (NW) is out of sight of the hall
        Door("wudu", "sh-m", 4.4, 5.15, 0.75, "u", "door", swing=-1, hinge=-1),
        Door("entry", "ext", 2.0, 10.6, 1.0, "v", "door", swing=1, hinge=-1),  # C11-ARR-06: door under the porch
        Door("hall", "entry", 3.2, 9.5, 2.2, "u", "open"),
        Door("hall", "tanks", 2.0, 8.4, 1.2, "v", "door", swing=-1, hinge=1),
        Door("tanks", "bulk", 2.0, 2.6, 1.0, "v", "door", swing=1, hinge=-1),
        Door("hall", "pantry", 3.25, 7.3, 0.8, "u", "door", swing=-1, hinge=-1),
        Door("hall", "stair-m", 8.1, 7.3, 2.6, "u", "open"),
        Door("hall", "lift-m", 10.4, 7.3, 0.9, "u", "glass"),
        Door("hall", "kitchen", 6.15, 9.5, 1.1, "u", "open"),
        Door("hall", "dining", 10.4, 8.75, 1.6, "u", "open"),
        Door("kitchen", "dining", 9.4, 10.75, 1.1, "v", "open"),
        Door("dining", "living", 12.6, 11.3, 2.6, "v", "open"),
        Door("hall", "living", 12.6, 8.05, 1.2, "v", "open"),
        Door("hall", "master", 12.0, 6.2, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("master", "dress", 12.55, 3.4, 0.8, "u", "door", swing=1, hinge=1),
        Door("master", "ens", 11.4, 3.95, 0.9, "v", "slide"),
        Door("kitchen", "ext", 8.1, 13.0, 2.0, "u", "slide"),
        Door("dining", "ext", 10.175, 13.0, 1.35, "u", "slide"),
        Door("living", "ext", 13.9, 13.0, 2.4, "u", "slide"),
        Door("master", "ext", EAST, 4.1, 1.8, "v", "slide"),
        Door("living", "ext", EAST, 10.0, 1.8, "v", "slide"),
    ]
    windows = [
        Win(5.35, 13.0, 6.55, 13.0),  # sink window, clear of the column at u 6.8
        Win(2.7, 13.0, 3.9, 13.0),  # entry, onto the court
        Win(11.5, 13.0, 12.4, 13.0),  # dining, east of the column at u 11.1
        Win(15.7, 13.0, 16.3, 13.0),  # living 0.6 m, between the column at 15.4 and the solid SE corner
        Win(15.6, 1.1, 16.8, 1.1),  # master north: obscured to 1.7 m, tilt-and-turn (C11-ROOM-08)
        Win(10.0, 1.1, 10.6, 1.1),  # ensuite: obscured, tilt-only, sill 1.6 m
        Win(EAST, 6.7, EAST, 8.5),  # living: high clerestory 0.6 m over the sofa (C11-SUN-02)
    ]
    qmats = prayer_mats(16.55, 11.7)
    furn = flat(
        # service room under the garage: two 1.5 m3 tanks, booster, filter and softener on the ground slab
        rect(0.25, 1.4, 0.95, 3.6, "fixture", "TANK"), rect(0.25, 3.8, 0.95, 6.0, "fixture", "TANK"),  # 0.7 m slim tanks fit the doors (OPS-01)
        rect(0.25, 6.2, 0.95, 7.0, "fixture"), Shape(Point(1.4, 6.6), "text", "BOOSTER"), Shape(Point(1.4, 4.7), "text", "0.9 m PASSAGE"), rect(2.15, 1.25, 6.65, 1.75, "bench"), rect(3.25, 3.0, 3.65, 4.45, "bench"),
        Shape(Point(4.9, 2.2), "text", "SHELVES · CLEANING"),
        rect(2.15, 4.75, 2.55, 7.15, "bench"), rect(3.25, 4.75, 3.65, 6.4, "bench"), rect(2.55, 4.75, 3.25, 5.15, "bench"),
        # wet cluster
        shower(3.92, 2.92, 4.83, 4.1), wc(5.46, 3.2, "s"), basin(6.45, 3.1, 0.35, 0.3),
        Shape(Point(5.92, 4.32).buffer(0.75), "dash"), Shape(Point(5.92, 4.32), "text", "Ø1.5"),
        rect(4.35, 6.15, 4.75, 7.2, "bench"), rect(3.86, 6.15, 4.2, 7.2, "fixture"), Shape(Point(4.3, 5.95), "text", "SEATS · TROUGH"),
        basin(6.45, 7.0, 0.4, 0.3),
        stair_dogleg(*STAIR, label="UP 24R · DN 24R"), lift_car(*LIFT),
        # master suite (C11-ROOM-07): ensuite and dressing each open from inside the bedroom
        shower(9.55, 1.25, 10.95, 2.35), wc(9.75, 3.7, "e"), basin(10.7, 4.2, 0.5, 0.42),
        wardrobe(11.5, 1.25, 12.1, 3.3), wardrobe(12.1, 1.25, 13.1, 1.85),
        bed(13.35, 2.05, 1.8, 2.05, "w"), rect(13.35, 1.6, 13.8, 2.0), rect(13.35, 3.9, 13.8, 4.3),
        rect(13.35, 5.65, 17.4, 6.05, "bench"), Shape(Point(15.4, 5.45), "text", "BOOKSHELF WALL"),
        armchair(17.0, 1.35, 0.7), rect(15.5, 4.7, 16.8, 5.4, "dash"), Shape(Point(16.15, 4.55), "text", "COT"),
        # kitchen (C11-KB-01/02, ROOM-05): west run fridge, drawers, hob under the plant room; sink under the south window
        counter(4.46, 9.56, 5.06, 12.2, hob=(4.76, 11.4), fridge=(4.46, 9.56, 5.06, 10.46)),
        counter(5.45, 12.2, 7.05, 12.8, sink=(5.95, 12.5)),
        rect(6.6, 10.45, 8.0, 11.15, "bench"), Shape(Point(7.3, 10.8), "text", "ISLAND"),
        *[Shape(Point(u, 10.2).buffer(0.19)) for u in (6.95, 7.6)], Shape(Point(8.25, 10.8).buffer(0.19)),
        # dining for 8 (C11-ROOM-04): 2.2 x 1.0 table along v, 0.9 clear all round
        table_chairs(11.0, 10.85, 1.0, 2.2, 3, ends=True), rect(11.25, 8.85, 12.45, 9.3, "bench"),
        # living (C11-ROOM-06): L-sofa in the sheltered NE corner, TV on the west wall, prayer place SE
        sofa_l(17.75, 6.35, 2.6, 2.6, "ne"), coffee(15.4, 7.4, 16.4, 8.2), armchair(13.9, 10.2, 0.75),
        rect(13.4, 7.0, 13.75, 9.1, "bench"), Shape(Point(13.57, 6.85), "text", "BOOKCASE SCREEN 2.1 m"),
        rect(13.75, 7.5, 13.9, 8.7, "fixture"), Shape(Point(14.15, 8.1), "text", "TV"),
        qmats, Shape(Point(16.55, 12.65), "text", "PRAYER ↙ QIBLA"),
        rect(2.15, 12.4, 2.65, 12.85, "bench"), rect(3.9, 10.0, 4.3, 12.6, "bench"), Shape(Point(3.6, 12.2), "text", "SHOES · COATS"),
        # terraces: table at the west end over the laundry/store strip (C11-PRV-01); awning, not a pergola
        Shape(LS((EAST + 0.25, 6.2), (BALC, 6.2)), "baffle"), Shape(Point(19.0, 6.45), "text", "OBSCURED GLASS SCREEN + GATE"),
        rect(4.6, 13.0, EAST, 14.0, "dash"), Shape(Point(8.6, 13.75), "text", "1.0 m CANOPY OVER THE SOUTH GLASS"),
        Shape(Point(-4.9, 11.15), "text", "GATE 1.2 · INTERCOM · PARCELS"), Shape(Point(-1.5, 11.2), "text", "0.6 m UPSTAND + 1.1 m GUARD"),
        Shape(Point(1.0, 13.3), "text", "OUTDOOR COOKING (no gas stored here) · TAP"), rect(-0.2, 12.3, 0.4, 12.9, "dash"),
        table_chairs(6.3, 14.2, 1.8, 0.9, 3, ends=False), rect(12.5, 13.9, 14.3, 14.6), rect(10.6, 13.9, 12.4, 14.6),
    )
    pergola = R(15.4, 13.0, EAST, 16.4)  # the whole strip over the loggia opened (fix round, SUN-N01)
    t_south = minus(R(4.6, SOUTH_MAIN, EAST, 16.4), R(4.6, 16.0, 7.8, 16.4), pergola)
    terraces = [
        Terrace("t-south", "SOUTH TERRACE", t_south, Z_MAIN - 0.02, label_at=(9.6, 15.55)),
        Terrace("pergola", "PERGOLA", pergola, Z_MAIN - 0.02, "pergola", label_at=(16.6, 14.0), note="open slats over the loggia"),
        Terrace("balc-e", "EAST BALCONY", R(EAST, 6.2, BALC, 16.4), Z_MAIN - 0.02, label_at=(18.95, 13.6)),
        Terrace("balc-m", "MASTER BALCONY", R(EAST, 2.6, BALC, 6.2), Z_MAIN - 0.02, label_at=(18.95, 4.4)),
        Terrace("porch", "PORCH", R(0.0, 9.5, 2.0, 11.6), Z_COURT, "court", label_at=(1.0, 10.2), note="covered"),
        Terrace("court-w", "ARRIVAL COURT", Polygon([
            (bline(11.6, 2.05), 11.6), (0.0, 11.6), (2.0, 11.6), (2.0, 13.0), (4.6, 13.0), (4.6, 16.0), (-0.4, 16.0), (-0.4, 17.12),
            (F2_U1, 17.12), (F2_U1, 15.72), (-3.48, 15.72), (-3.48, 15.37), (bline(15.37, 2.05), 15.37)]), Z_COURT, "court",
            label_at=(-1.6, 14.0)),
    ]
    notes = [
        "Kitchen on the south: 2.0 m slider onto the south terrace and the sink under a south window (1.1, 1.2). Island with 3 stools for snacks; hob on the west run with a ducted hood up the fire-rated riser SH-K (1.3).",
        "Dining for 8 with chairs pulled out, open to the living room as one L (1.4, 1.5). Every main room opens off the family hall (2.1).",
        "Living 5.2 × 6.5 m clear: L-sofa in the sheltered NE corner behind a 200 mm wall; a 2.1 m bookcase screen with the TV stands opposite the hall opening, so the sofa does not look down the hall; prayer place in the SE with mats on the qibla (3.1, 3.3).",
        "Master suite: one door from the hall's recess into the bedroom; ensuite and dressing room each open from inside it (2.5). East balcony starts 1.5 m south of the north edge (Q5).",
        "Front door under the covered porch, facing the arrival court (2.6). The service room with the water tanks is dug under the garage, so the garage has walls under it.",
    ]
    lv = Level("main", "MAIN FLOOR", Z_MAIN, rooms, doors, windows, furn, terraces, notes)
    lv.suspended = [R(15.4, 10.95, EAST, 13.0)]  # living SE corner over the open loggia
    lv.wall_lines = core_walls() + [
        (LS((11.4, 6.2), (EAST, 6.2)), 0.20),  # masonry between master and living/hall (C11-ROOM-06, PRV-02)
        (LS((12.6, 6.2), (12.6, 7.3)), 0.20), (LS((8.1, 2.5), (8.1, 5.9)), 0.15),  # RC spine between the flights
        (LS((0.0, 1.1), (0.0, 9.5)), 0.45), (LS((0.0, 1.1), (6.8, 1.1)), 0.45),  # buried walls 0.45 m
    ]
    return lv


# ---------------------------------------------------------------- lower floor + garden
def lower_level() -> Level:
    rw = R(*RISER_W)
    rk = R(*RISER_K)
    guest = Polygon([(13.4, 1.1), (EAST, 1.1), (EAST, 6.2), (11.4, 6.2), (11.4, 3.0), (13.4, 3.0)])
    # the bathroom's south wall moved to v 9.8 so the laundry neck is 1.0 m clear (fix round, CIR-N02)
    laundry = Polygon([(4.6, 10.1), (6.8, 10.1), (6.8, 9.8), (8.2, 9.8), (8.2, 10.95), (6.8, 10.95), (6.8, 12.2), (4.6, 12.2)])
    rooms = [
        Room("stair-l", "STAIR", "stair", R(8.0, 1.1, 9.4, 7.3), show_dims=False),
        Room("store-u", "HOUSEHOLD STORE", "service", R(6.8, 1.1, 8.0, 7.3), small=True, label_at=(7.4, 4.6)),
        Room("lift-l", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("gens", "SEATED ENSUITE", "wet", minus(R(9.4, 1.1, 11.4, 4.5), R(*RISER_E)), small=True, label_at=(10.3, 3.7)),
        Room("riser-e", "", "riser", R(*RISER_E), show_dims=False, small=True),
        Room("gwalk", "WALK-IN", "service", R(11.4, 1.1, 13.4, 3.0), small=True, label_at=(12.4, 2.35)),
        Room("guest", "GRANDPARENTS", "sleep", guest, label_at=(15.7, 3.95), main=True),
        Room("sh-l", "SHOWER", "wet", R(4.6, 7.3, 6.8, 8.7), small=True, label_at=(5.7, 8.05)),
        Room("wc-l", "WC", "wet", minus(R(4.6, 8.7, 6.8, 10.1), rw), small=True, label_at=(6.15, 9.75)),
        Room("riser-w", "", "riser", rw, show_dims=False, small=True),
        Room("lav", "BASINS", "wet", R(6.8, 7.3, 8.2, 9.8), small=True, label_at=(7.5, 8.6)),
        Room("laundry", "LAUNDRY", "service", laundry, small=True, label_at=(6.0, 10.6)),
        Room("store-s", "STORE", "service", minus(R(4.6, 12.2, 6.8, SOUTH_LOW), rk), small=True, label_at=(5.9, 14.2)),
        Room("riser-k", "", "riser", rk, show_dims=False, small=True),
        Room("hall-l", "FAMILY HALL", "hall", Polygon([(8.2, 7.3), (11.4, 7.3), (11.4, 6.2), (12.6, 6.2), (12.6, 10.95), (8.2, 10.95)]), label_at=(10.4, 9.9)),
        Room("boys", "BOYS", "sleep", R(6.8, 10.95, 11.1, SOUTH_LOW), main=True, label_at=(8.85, 13.95)),
        Room("girls", "GIRLS", "sleep", R(11.1, 10.95, 15.4, SOUTH_LOW), main=True, label_at=(13.4, 13.95)),
        Room("lounge", "GARDEN LOUNGE + TEA BAR", "day", R(12.6, 6.2, EAST, 10.95), label_at=(14.6, 10.35), main=True),
    ]
    doors = [
        Door("hall-l", "stair-l", 8.8, 7.3, 1.2, "u", "open"),
        Door("stair-l", "store-u", 8.0, 6.65, 0.8, "v", "door", swing=-1, hinge=1),
        Door("hall-l", "lift-l", 10.4, 7.3, 0.9, "u", "glass"),
        Door("hall-l", "lav", 8.2, 7.95, 0.9, "v", "door", swing=-1, hinge=-1),  # C11-ROOM-12: lockable
        Door("lav", "sh-l", 6.8, 8.0, 0.75, "v", "door", swing=-1, hinge=-1),
        Door("lav", "wc-l", 6.8, 9.15, 0.7, "v", "door", swing=-1, hinge=1),  # opens in; its leaf screens the pan
        Door("hall-l", "laundry", 8.2, 10.52, 0.8, "v", "door", swing=-1, hinge=1),
        Door("laundry", "store-s", 5.9, 12.2, 0.8, "u", "door", swing=1, hinge=-1),
        Door("hall-l", "boys", 10.4, 10.95, 0.9, "u", "door", swing=1, hinge=-1),
        Door("hall-l", "girls", 11.85, 10.95, 0.9, "u", "door", swing=1, hinge=1),
        Door("hall-l", "guest", 12.0, 6.2, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("guest", "gens", 11.4, 3.7, 1.0, "v", "slide"),
        Door("guest", "gwalk", 12.9, 3.0, 0.8, "u", "door", swing=1, hinge=1),
        Door("hall-l", "lounge", 12.6, 9.35, 2.7, "v", "open"),
        Door("lounge", "ext", EAST, 9.9, 1.8, "v", "slide"),
        Door("lounge", "ext", 16.7, 10.95, 1.8, "u", "slide"),
        Door("guest", "ext", EAST, 4.3, 2.0, "v", "slide"),
    ]
    windows = [
        Win(8.9, SOUTH_LOW, 10.7, SOUTH_LOW),  # boys: no further west than u 8.9 (rule 4.8), clear of the column at 11.1
        Win(11.45, SOUTH_LOW, 14.75, SOUTH_LOW),  # girls ~3.3 m
        Win(EAST, 6.6, EAST, 8.4),  # lounge view window
        Win(EAST, 1.6, EAST, 2.8),  # grandparents' east window between the beds' heads and the slider (HLT-N01)
    ]
    furn = flat(
        stair_dogleg(8.0 - 1.2, 1.1, 9.4, 7.3, label="UP 24R"), lift_car(*LIFT),
        rect(6.9, 5.2, 7.9, 7.2, "dash"), Shape(Point(7.4, 3.6), "text", "SHELVES"),
        # family bathroom (C11-ROOM-12)
        shower(4.75, 7.4, 5.85, 8.4), rect(5.95, 7.45, 6.7, 8.55, "dash"), Shape(Point(6.32, 7.6), "text", "DRY"),
        wc(5.8, 9.7, "n"), basin(7.45, 9.4, 0.45, 0.4), basin(7.92, 9.4, 0.45, 0.4),
        # laundry (C11-ROOM-13): washer, heat-pump dryer, sink; counter over; ceiling airer
        rect(4.75, 10.2, 5.35, 10.8, "fixture", "W"), rect(4.75, 10.8, 5.35, 11.4, "fixture", "D"),
        counter(4.75, 11.4, 5.35, 12.1, sink=(5.05, 11.75)), rect(5.9, 10.2, 6.7, 11.0, "dash"), Shape(Point(6.3, 11.25), "text", "AIRER"),
        rect(4.85, 13.25, 5.45, 15.55, "bench"), rect(4.85, 12.35, 5.45, 12.75, "bench"), rect(6.0, 13.05, 6.65, 15.55, "bench"),
        # boys and girls: owner's 4.3 x 4.8 m rooms; beds off the window wall, desks by the glass facing west
        bed(7.05, 11.05, 1.0, 2.05, "n", 1), bed(8.75, 11.05, 1.0, 2.05, "n", 1),
        wardrobe(10.25, 11.95, 10.85, 13.95),
        desk(6.95, 13.6, 7.55, 14.6, (7.85, 14.1)), desk(6.95, 14.65, 7.55, 15.55, (7.85, 15.1)),
        # girls: wardrobes on the lounge wall as the acoustic buffer (PRV-N03), beds heads east
        wardrobe(12.4, 11.05, 15.15, 11.65),
        bed(13.15, 12.3, 1.0, 2.05, "e", 1), bed(13.15, 13.9, 1.0, 2.05, "e", 1),
        desk(11.3, 13.6, 11.9, 14.6, (12.2, 14.1)), desk(11.3, 14.65, 11.9, 15.55, (12.2, 15.1)),
        # grandparents (C11-ROOM-11): twin beds heads north with a 1.75 m transfer zone, wardrobes buffering the lounge
        bed(14.3, 1.25, 0.9, 2.0, "n", 1), bed(16.95, 1.25, 0.9, 2.0, "n", 1),
        wardrobe(13.3, 5.55, 17.4, 6.15), armchair(13.6, 3.3, 0.75), armchair(14.6, 3.3, 0.75),
        shower(9.55, 1.25, 10.95, 2.35), wc(9.8, 3.9, "e"), basin(10.8, 4.2, 0.5, 0.42), Shape(Point(10.25, 2.65).buffer(0.75), "dash"),
        rect(11.5, 1.2, 13.3, 1.8, "bench"),
        # lounge (C11-ROOM-10)
        counter(15.5, 6.3, 17.75, 6.9, sink=(16.0, 6.6), fridge=(17.15, 6.3, 17.75, 6.9)), Shape(Point(16.6, 7.15), "text", "TEA BAR"),
        rect(13.0, 6.3, 14.5, 6.75, "bench"), Shape(Point(13.75, 7.0), "text", "TV"),
        sofa_l(15.6, 9.5, 2.3, 2.1, "se"), coffee(13.4, 7.6, 14.5, 8.4), armchair(16.7, 7.6, 0.75),
        Shape(Point(15.0, 10.4), "text", "→ GARDEN"),
        # loggia: boot bench, shoe cabinet, tap
        rect(15.65, 13.3, 16.05, 14.9, "bench"), table_chairs(17.0, 14.3, 0.9, 1.4, 2, ends=False),
    )
    # the pocket under the east balcony is lawn, not a walled sump (LND-N04); the lawn stair is 1.4 m wide (ACC-N04)
    lawn = minus(Polygon([(TERR + 0.2, 1.0), (lawn_edge(1.0), 1.0), (lawn_edge(17.12), 17.12), (EAST + 0.25, 17.12),
                          (EAST + 0.25, 12.8), (TERR + 0.2, 12.8)]).intersection(ENVELOPE),
                 R(TERR + 0.2, 3.4, 22.05, 10.28))
    bank = ENVELOPE.intersection(Polygon([(lawn_edge(0.0), 0.0), (40.0, 0.0), (40.0, 17.42), (lawn_edge(17.42), 17.42)]))
    terraces = [
        Terrace("loggia", "LOGGIA", R(15.4, 10.95, EAST, 16.0), Z_LOWER - 0.02, label_at=(16.95, 11.6), note="covered, suspended slab"),
        Terrace("t-low", "GARDEN TERRACE", Polygon([(EAST, 1.1), (TERR, 1.1), (TERR, 12.8), (EAST, 12.8)]), Z_TLOW, label_at=(19.3, 8.0),
                note="suspended: cistern + garden store under"),
        # lawn-stair landings are RC slabs between FW-20.6 and FW-22.05, not fill (fix round, GEO-N03 / STR-07)
        Terrace("ls-top", "", R(TERR, 3.4, 22.05, 4.6), Z_TLOW, "terrace"),
        Terrace("ls-f1", "", R(TERR, 4.6, 22.05, 6.84), Z_TLOW, "stair", z_end=Z_TLOW - 8 * 0.14875, run="v+"),
        Terrace("ls-l1", "", R(TERR, 6.84, 22.05, 8.04), Z_TLOW - 8 * 0.14875, "terrace"),
        Terrace("ls-f2", "16 STEPS", R(TERR, 8.04, 22.05, 10.28), Z_TLOW - 8 * 0.14875, "stair", z_end=Z_LAWN, run="v+",
                label_at=(22.6, 7.4)),
        Terrace("walk-s", "GARDEN WALK", R(9.74, 16.0, 11.8, 17.12), Z_WALK, "paved", label_at=(13.0, 16.8)),
        Terrace("walk-m", "", R(11.8, 16.0, 15.4, 17.12), Z_WALK, "terrace", note="walk on a slab where the ground falls"),
        # the walk continues on a suspended slab along the loggia's open front (fix round, ACC-N01 / OWN-N01)
        Terrace("walk-e", "", R(15.4, 16.0, EAST, 17.12), Z_WALK, "terrace", note="walk on a slab, open to the loggia"),
        Terrace("lawn", "PLAY LAWN", lawn, Z_LAWN, "lawn", label_at=(24.0, 13.0)),
        Terrace("bank", "TREE BANK", bank, 1666.0, "bank", label_at=(27.9, 5.9), note="natural slope, three deciduous trees"),
    ]
    terraces += court_stair_terraces()
    notes = [
        "Children's rooms keep your 4.3 × 4.8 m (two beds, two desks, two wardrobes each). Beds off the window wall; the south windows look over the garden walk, 2.4 m and more of open ground below the sill (4.8).",
        "Grandparents in the NE, their door beside the lift: twin beds with a 1.75 m transfer space, seated ensuite with a 1.5 m turning circle, walk-in, own 2.0 m slider to the garden terrace.",
        "Family bathroom: lockable door from the hall to the basins, then a separate shower (with a dry changing place) and WC. Compact laundry (about 5 m²) with its own store; household store under the stair.",
        "Garden lounge with tea bar; TV and tea bar on the wall lined by the grandparents' wardrobes. The hall keeps a clear landing in front of the lift.",
        "Your own way out: the stair from the arrival court runs down the south band (24 easy steps of 15.1 cm) to the garden walk, which runs on along the loggia's open front; through the loggia to the garden terrace, then 16 easy steps to the play lawn.",
    ]
    lv = Level("lower", "LOWER FLOOR + GARDEN", Z_LOWER, rooms, doors, windows, furn, terraces, notes)
    lv.wall_lines = [(LS((8.0, 1.1), (8.0, 7.3)), 0.25), (LS((6.8, 1.1), (6.8, 7.3)), 0.40), (LS((6.8, 1.1), (9.4, 1.1)), 0.25),
                     (LS((4.6, 7.3), (8.0, 7.3)), 0.40),  # retaining 3.6 m under the main wet cluster (STR-N05)
                     (LS((9.4, 4.5), (9.4, 7.3)), 0.20), (LS((11.4, 4.5), (11.4, 7.3)), 0.20), (LS((9.4, 4.5), (11.4, 4.5)), 0.20),
                     (LS((11.4, 6.2), (EAST, 6.2)), 0.20), (LS((11.1, 10.95), (11.1, SOUTH_LOW)), 0.20),  # dense walls (PRV-02)
                     (LS((12.6, 10.95), (15.4, 10.95)), 0.20), (LS((4.6, 7.3), (4.6, SOUTH_LOW)), 0.45),
                     (LS((9.4, 1.1), (EAST, 1.1)), 0.45)]
    lv.suspended = [R(15.4, 6.2, EAST, 10.95)]  # lounge east: fill would exceed 1.0 m (C11-STR-07)
    return lv


CS_DROP = (Z_COURT - Z_WALK) / 3  # 1.25 m per flight of 8 risers of 156 mm


def court_stair_terraces() -> list[Terrace]:
    """C11-ARR-02: court -> lower floor, 24 risers of 150 mm in three flights of 8 with 1.5 m landings."""
    z = Z_COURT
    out = []
    for i, (u0, u1) in enumerate(((-0.40, 1.98), (3.48, 5.86), (7.36, 9.74))):
        out.append(Terrace(f"cs-f{i + 1}", "8 STEPS" if i == 1 else "", R(u0, 16.0, u1, 17.27), z, "stair",
                           z_end=round(z - CS_DROP, 3), run="u+", label_at=((u0 + u1) / 2, 18.0)))
        z = round(z - CS_DROP, 3)
        if i < 2:
            out.append(Terrace(f"cs-l{i + 1}", "", R(u1, 16.0, u1 + 1.5, 17.27), z, "landing"))
    return out


BN = (0.878, 0.480)  # unit normal from the west (road) boundary into the parcel
BD = (-0.480, 0.878)  # unit direction along the west boundary, going south
F2_U0, F2_U1 = -6.50, -2.98  # second flight of the road stair, v 15.72-17.12, 11 goings of 0.32


def bline(v: float, off: float) -> float:
    """u of the line `off` metres inside the west boundary, at height v."""
    return -0.5474 * v + off / BN[0]


def boff(p, off):
    return (p[0] + BN[0] * off, p[1] + BN[1] * off)


def road_stair_terraces() -> list[Terrace]:
    """C11-ARR-01: reviewer 05's L-stair against the road, 12 + 12 risers, corner landing at 1675.50.

    Moved 0.30 m off the boundary so the road-edge wall W2 (0.30 m) stands inside the parcel, and the second
    flight moved 0.30 m north so the south wall W4 stands inside the 1 m setback (C11 §7 check 13).
    """
    b0 = (bline(11.6, 0.0), 11.6)  # stair head on the boundary, v 11.6
    b1 = (b0[0] + BD[0] * 3.52, b0[1] + BD[1] * 3.52)  # 11 goings of 0.32 m down the boundary
    f1 = Polygon([boff(b0, 0.30), boff(b0, 1.70), boff(b1, 1.70), boff(b1, 0.30)])
    head = Polygon([(bline(11.6, 0.30), 11.6), (bline(11.6, 1.70), 11.6), boff(b0, 1.70), boff(b0, 0.30)])
    l1 = Polygon([boff(b1, 0.30), boff(b1, 1.70), (F2_U0, 15.72), (F2_U0, 17.12), (bline(17.12, 0.30), 17.12)])
    f2 = R(F2_U0, 15.72, F2_U1, 17.12)
    top = ((boff(b0, 0.30)[0] + boff(b0, 1.70)[0]) / 2, (boff(b0, 0.30)[1] + boff(b0, 1.70)[1]) / 2)
    bot = ((boff(b1, 0.30)[0] + boff(b1, 1.70)[0]) / 2, (boff(b1, 0.30)[1] + boff(b1, 1.70)[1]) / 2)
    return [
        Terrace("rs-head", "", head, Z_FORE, "landing"),
        Terrace("rs-f1", "ROAD STAIR 12 + 12", f1, Z_FORE, "stair", z_end=1675.50, run=(top, bot), label_at=(-9.0, 12.6)),
        Terrace("rs-l1", "", l1, 1675.50, "landing"),
        Terrace("rs-f2", "", f2, 1675.50, "stair", z_end=Z_COURT, run="u+"),
    ]


# ---------------------------------------------------------------- structure (rule 4.9, C11-STR-*, DRW-01)
def structure() -> list[Element]:
    """Everything that carries a slab and is not a storey's own outer or core wall.

    Storey walls (the outer wall of each plate and the stair and lift walls) are taken from the plans.
    Lines listed here are bearing walls, beams, columns, retaining and foundation walls, with real levels.
    """
    E = Element
    out = [
        # --- lower storey (1670.00 -> carries the main-floor slab 1673.60)
        E("LW-6.2", "wall", LS((11.4, 6.2), (EAST, 6.2)), Z_LOWER, Z_MAIN, 0.20, "lower", "under the master/living wall"),
        E("LB-18E", "beam", LS((EAST, 1.1), (EAST, 10.95)), Z_MAIN - 0.5, Z_MAIN, 0.30, "lower", "lintel beam over the lower east openings"),
        E("FW-18L", "wall", LS((EAST, 1.1), (EAST, 10.95)), 1667.5, Z_LOWER, 0.40, "lower", "foundation wall under the lower east wall, stepped to sound ground (STR-N02)"),
        E("FW-15.75", "wall", LS((11.1, SOUTH_LOW), (15.4, SOUTH_LOW)), 1667.8, Z_LOWER, 0.40, "lower", "foundation wall under the girls' south wall (STR-N02)"),
        E("FW-10.95", "wall", LS((15.4, 10.95), (EAST, 10.95)), 1667.5, Z_LOWER, 0.40, "lower", "foundation wall under the lounge's south wall over the falling ground"),
        E("LB-15.75", "beam", LS((4.6, SOUTH_LOW), (15.4, SOUTH_LOW)), Z_MAIN - 0.5, Z_MAIN, 0.30, "lower", "lintel beam over the children's windows, carries the terrace lip"),
        E("LW-12.6", "wall", LS((12.6, 6.2), (12.6, 10.95)), Z_LOWER, Z_MAIN, 0.20, "lower", "hall/lounge, under main u 12.6"),
        E("LW-11.4", "wall", LS((11.4, 1.1), (11.4, 7.3)), Z_LOWER, Z_MAIN, 0.20, "lower", "ensuite/walk-in, lift side"),
        E("LW-10.95", "wall", LS((6.8, 10.95), (EAST, 10.95)), Z_LOWER, Z_MAIN, 0.20, "lower", "bedrooms' north wall, lounge south wall"),
        E("LW-11.1", "wall", LS((11.1, 10.95), (11.1, SOUTH_LOW)), Z_LOWER, Z_MAIN, 0.20, "lower", "boys/girls"),
        E("LW-15.4", "wall", LS((15.4, 10.95), (15.4, SOUTH_LOW)), 1668.0, Z_MAIN, 0.25, "lower", "girls/loggia, founded below the falling ground"),
        E("LW-6.8", "wall", LS((6.8, 7.3), (6.8, SOUTH_LOW)), Z_LOWER, Z_MAIN, 0.20, "lower", "bathroom/boys, under the kitchen"),
        E("LW-7.3", "wall", LS((4.6, 7.3), (8.2, 7.3)), Z_LOWER, Z_MAIN, 0.20, "lower", "under the main wudu/hall wall"),
        E("LW-8.2", "wall", LS((8.2, 7.3), (8.2, 10.95)), Z_LOWER, Z_MAIN, 0.20, "lower", "bathroom/hall"),
        E("LB-13.0", "beam", LS((4.6, 13.0), (EAST, 13.0)), Z_MAIN - 0.55, Z_MAIN, 0.40, "lower", "300 x 550 beam under the south façade"),
        E("LB-18", "beam", LS((EAST, 10.95), (EAST, 12.8)), Z_MAIN - 0.55, Z_MAIN, 0.40, "lower", "over the loggia opening"),
        E("LB-16.0", "beam", LS((15.4, 16.0), (EAST, 16.0)), Z_MAIN - 0.55, Z_MAIN, 0.30, "lower", "loggia front, carries the terrace"),
        E("LB-9.5", "beam", LS((4.6, 9.5), (8.2, 9.5)), Z_MAIN - 0.45, Z_MAIN, 0.30, "lower", "under the main hall/kitchen wall"),
        E("RC-18L", "wall", LS((EAST, 12.8), (EAST, 16.4)), 1666.6, Z_MAIN, 0.30, "lower", "loggia east RC wall (C11-STR-04)"),
        # --- main storey (1673.60 -> carries the road slab 1677.50 and the roof terraces)
        E("MW-2.0", "wall", LS((2.0, 1.1), (2.0, 13.0)), Z_MAIN, Z_ROAD, 0.30, "main", "service room/entry west wall, carries the garage"),
        E("MW-2.8", "wall", LS((2.0, 2.8), (6.8, 2.8)), Z_MAIN, Z_ROAD, 0.20, "main", "under the garage"),
        E("MW-4.6", "wall", LS((2.0, 4.6), (3.8, 4.6)), Z_MAIN, Z_ROAD, 0.20, "main", "bulk store/pantry"),
        E("MW-3.8", "wall", LS((3.8, 2.8), (3.8, 7.3)), Z_MAIN, Z_ROAD, 0.20, "main", "pantry/wet cluster"),
        E("MW-7.3", "wall", LS((2.0, 7.3), (6.8, 7.3)), Z_MAIN, Z_ROAD, 0.20, "main", "under the garage, hall north wall"),
        E("MW-9.5", "wall", LS((0.0, 9.5), (2.0, 9.5)), Z_MAIN, Z_ROAD, 0.30, "main", "service room/porch"),
        E("MB-9.5", "beam", LS((2.0, 9.5), (9.4, 9.5)), Z_ROAD - 0.6, Z_ROAD, 0.30, "main", "carries the garage/hall wall"),
        E("MB-6.8", "beam", LS((6.8, 7.3), (6.8, 9.5)), Z_ROAD - 0.6, Z_ROAD, 0.30, "main", "carries the garage/lobby wall (C11-STR-05)"),
        E("MB-11.6", "beam", LS((0.0, 11.6), (2.0, 11.6)), Z_ROAD - 0.6, Z_ROAD, 0.30, "main", "porch front, carries the road hall"),
        E("MB-12.6", "beam", LS((12.6, 6.2), (12.6, 13.0)), Z_ROAD - 0.6, Z_ROAD, 0.30, "main", "over the living openings, carries the office and the deck"),
        E("MB-9.4", "beam", LS((9.4, 7.3), (9.4, 13.0)), Z_ROAD - 0.6, Z_ROAD, 0.30, "main", "kitchen/dining, carries the office west wall"),
        E("MB-7.3E", "beam", LS((11.4, 7.3), (12.6, 7.3)), Z_ROAD - 0.5, Z_ROAD, 0.25, "main", "carries the lobby's south wall over the hall recess"),
        E("MB-18", "beam", LS((EAST, 1.1), (EAST, 13.0)), Z_ROAD - 0.5, Z_ROAD, 0.30, "main", "lintel beam over the main east openings, carries the roof terrace and green roof edge"),
        E("MB-1.1N", "beam", LS((13.2, 1.1), (EAST, 1.1)), Z_ROAD - 0.5, Z_ROAD, 0.30, "main", "lintel beam over the master's north window"),
        E("MB-13.0", "beam", LS((2.0, 13.0), (EAST, 13.0)), Z_ROAD - 0.65, Z_ROAD, 0.40, "main", "400 x 650 beam over the south glazing at road-slab level (fix round, STR-N01)"),
        E("MW-6.2", "wall", LS((11.4, 6.2), (EAST, 6.2)), Z_MAIN, Z_ROAD, 0.20, "main", "master/living masonry"),
        E("MW-11.4", "wall", LS((11.4, 1.1), (11.4, 4.5)), Z_MAIN, Z_ROAD, 0.20, "main", "ensuite/dressing"),
        E("MW-SE", "wall", LS((EAST, 11.6), (EAST, 13.0), (16.4, 13.0)), Z_MAIN, Z_ROAD, 0.30, "main", "solid SE L-wall (C11-STR-06)"),
        E("RC-0", "retaining", LS((0.0, 9.5), (0.0, 11.6)), Z_MAIN - 0.9, Z_ROAD, 0.35, "main", "porch west wall, holds 0.8-1.0 m of ground"),
        # --- road storey (1677.50 -> carries the roof)
        E("RW-9.5", "wall", LS((0.0, 9.5), (6.8, 9.5)), Z_ROAD, Z_ROAD + 3.3, 0.20, "road", "garage/hall fire wall"),
        E("RW-6.8", "wall", LS((6.8, 7.3), (6.8, 9.5)), Z_ROAD, Z_ROAD + 3.3, 0.20, "road", "garage/lobby fire wall, on beam MB-6.8"),
        E("RB-5.05", "beam", LS((0.0, 5.05), (6.8, 5.05)), Z_ROAD + 2.7, Z_ROAD + 3.3, 0.30, "road", "garage roof beam on the shutter pier (C11-STR-10)"),
        E("RW-12.6", "wall", LS((12.6, 7.3), (12.6, 13.0)), Z_ROAD, Z_ROAD + 3.3, 0.40, "road", "office/lobby east wall"),
        E("RW-9.4", "wall", LS((9.4, 9.5), (9.4, 13.0)), Z_ROAD, Z_ROAD + 3.3, 0.20, "road", "office west wall"),
        E("RW-2.0", "wall", LS((2.0, 11.6), (2.0, 13.0)), Z_ROAD, Z_ROAD + 3.3, 0.40, "road", "WC west wall"),
    ]
    # continuous columns on v 13.0, footing to the slab they carry (C11-STR-03)
    for u in COLS_S:
        top = Z_ROAD + 3.3 if u <= 12.6 else Z_ROAD
        out.append(E(f"C-{u:g}/13", "column", Point(u, 13.0), 1666.6 if u >= 15 else 1668.6, top, 0.35, "all",
                     "continuous RC column, footing to " + ("road roof" if u <= 12.6 else "roof terrace")))
    out.append(E("C-6.8/9.5", "column", Point(6.8, 9.5), Z_MAIN, Z_ROAD, 0.30, "main", "main storey only, standing on lower wall LW-6.8 (clear of the lower WC door)"))
    out.append(E("C-18/10.95", "column", Point(EAST, 10.95), 1667.5, Z_ROAD, 0.35, "all", "SE corner over the loggia opening (STR-N03)"))
    # balcony columns and edge beam (C11-THM-03, self-supporting balconies)
    for v in (2.75, 6.2, 9.4, 12.8, 16.2):
        out.append(E(f"C-B/{v:g}", "column", Point(19.6, v), 1666.0 if v > 12 else 1667.2, Z_MAIN, 0.30, "all", "balcony column, footing below the garden terrace"))
    out.append(E("BB-19.6", "beam", LS((19.6, 2.6), (19.6, 16.4)), Z_MAIN - 0.45, Z_MAIN, 0.30, "lower", "balcony edge beam"))
    out.append(E("BB-16.4", "beam", LS((EAST, 16.4), (19.6, 16.4)), Z_MAIN - 0.45, Z_MAIN, 0.30, "lower", "balcony SE corner"))
    # foundations and retaining walls carrying the lower-floor slabs and the garden terrace
    out += [
        E("FW-20.6", "retaining", LS((TERR, 1.1), (TERR, 12.8)), 1666.5, Z_TLOW, 0.30, "lower", "garden terrace east wall (C11-GEO-03)"),
        E("FW-1.1T", "retaining", LS((EAST, 1.1), (TERR, 1.1)), 1667.6, Z_TLOW, 0.30, "lower", "garden terrace north wall"),
        E("FW-12.8T", "wall", LS((EAST, 12.8), (TERR, 12.8)), 1666.6, Z_TLOW, 0.30, "lower", "garden terrace south wall, garden store door"),
        E("FW-6.2T", "wall", LS((EAST, 6.2), (TERR, 6.2)), 1666.8, Z_TLOW, 0.25, "lower", "cistern end wall on the column line (cistern floor 1667.7, ~14 m³, 0.6 m hatch)"),
        E("FW-17.1", "wall", LS((11.8, 17.12), (EAST, 17.12)), 1666.8, Z_WALK, 0.25, "lower", "carries the walk slab along the children's rooms and the loggia front"),
        E("FW-11.8", "wall", LS((11.8, 16.0), (11.8, 17.12)), 1668.6, Z_WALK, 0.25, "lower", "end of the walk slab"),
        E("FW-22.05", "wall", LS((22.05, 3.4), (22.05, 10.28)), 1666.6, Z_TLOW, 0.25, "lower", "east wall of the lawn stair; landings and flights are RC slabs between it and FW-20.6"),
        E("FW-3.4L", "wall", LS((TERR, 3.4), (22.05, 3.4)), 1667.2, Z_TLOW, 0.25, "lower", "north end of the lawn stair"),
        E("FW-16.0", "wall", LS((15.4, 16.0), (EAST, 16.0)), 1667.4, Z_LOWER, 0.30, "lower", "loggia front foundation wall"),
        E("FW-13.4", "wall", LS((15.4, 13.4), (EAST, 13.4)), 1667.6, Z_LOWER, 0.20, "lower", "loggia slab mid support"),
        E("FW-15.4", "wall", LS((15.4, 6.2), (15.4, 10.95)), 1668.6, Z_LOWER, 0.20, "lower", "ground beam under the lounge slab"),
        E("RW-W1", "retaining", LS((bline(11.6, 2.05), 11.6), (0.0, 11.6)), Z_COURT - 0.6, Z_FORE, 0.40, "site", "W1: forecourt edge over the court, carries the forecourt deck"),
        E("RW-W2", "retaining", LS((bline(11.6, 0.18), 11.6), (bline(17.12, 0.18), 17.12)), 1673.0, 1678.30, 0.35, "site", "W2: road-edge wall with a 0.7 m RC vehicle parapet + rail; one drained RC U-trough with W3 and the flights on a common base at 1673.0 (fix round, GEO-03)"),
        E("RW-W3", "retaining", LS((bline(11.6, 1.875), 11.6), (bline(15.545, 1.875), 15.545), (F2_U1 - 0.5, 15.545)), Z_COURT - 0.6, 1677.45, 0.35, "site", "W3: inner edge of the road stair, holds the stair over the court"),
        E("RW-W4a", "retaining", LS((bline(17.27, 0.30), 17.27), (-6.5, 17.27)), 1674.9, 1677.6, 0.30, "site", "W4: south wall of the corner landing, top follows the bank, guard on top"),
        E("RW-W4b", "retaining", LS((-6.5, 17.27), (-3.0, 17.27)), Z_COURT - 0.6, 1676.0, 0.30, "site", "W4: south wall of the second flight, guard on top"),
        E("RW-W4c", "retaining", LS((-3.0, 17.27), (-0.4, 17.27)), Z_COURT - 0.6, 1674.7, 0.30, "site", "W4: south edge of the court"),
        E("LIFT-PIT", "retaining", LS((9.4, 4.5), (11.4, 4.5), (11.4, 7.3), (9.4, 7.3), (9.4, 4.5)), 1668.8, Z_LOWER, 0.25, "lower", "tanked lift pit 1.2 m, gravity drain east (C11-WAT-05)"),
        E("LIFT-OVR", "wall", LS((9.4, 4.5), (11.4, 4.5), (11.4, 7.3), (9.4, 7.3), (9.4, 4.5)), Z_ROAD + 3.3, Z_ROAD + 4.1, 0.20, "road", "lift overrun upstand 0.8 m behind the roof louvre (C11-CIR-02)"),
        E("PB-F", "beam", LS((-0.2, 5.6), (-1.65, 8.6)), 1676.6, Z_FORE, 0.30, "road", "forecourt deck pier line (C11-GEO-02)"),
        E("PB-8.6", "beam", LS((bline(8.6, 0.5), 8.6), (0.0, 8.6)), 1676.6, Z_FORE, 0.30, "road", "forecourt deck beam on v 8.6"),
        E("PB-W", "beam", LS((bline(8.6, 0.5), 8.6), (bline(11.6, 0.5), 11.6)), 1676.6, Z_FORE, 0.30, "road", "forecourt deck beam 0.5 m inside the road boundary"),
        E("MW-0F", "wall", LS((0.0, 1.1), (0.0, 9.5)), Z_MAIN - 0.6, Z_FORE, 0.45, "main", "garage west wall below the shutters"),
        # north pile wall: detached from the house by a 0.2 m drained cavity, toes deep, cap stepping with the ground (GEO-N01)
        E("PW-N1", "retaining", LS((0.0, 0.40), (2.0, 0.40)), 1666.5, 1676.0, 0.45, "site", "secant Ø450 piles, toe 1666.5, cap 0.2 m under the ground"),
        E("PW-N2", "retaining", LS((2.0, 0.40), (4.0, 0.40)), 1666.5, 1674.8, 0.45, "site", "secant Ø450 piles, toe 1666.5"),
        E("PW-N3", "retaining", LS((4.0, 0.40), (6.8, 0.40)), 1664.5, 1673.5, 0.45, "site", "secant Ø450 piles, toe 1664.5"),
        E("PW-N4", "retaining", LS((6.8, 0.40), (11.4, 0.40)), 1664.5, 1671.8, 0.45, "site", "secant Ø450 piles, toe 1664.5"),
        E("PW-N5", "retaining", LS((11.4, 0.40), (16.0, 0.40)), 1667.0, 1670.2, 0.45, "site", "secant Ø450 piles, toe 1667.0"),
    ]
    for i, (u, v) in enumerate(((-0.2, 5.6), (-1.65, 8.6), (bline(8.6, 0.5), 8.6), (bline(11.6, 0.5), 11.6))):
        out.append(E(f"P-F{i + 1}", "column", Point(u, v), 1674.0, Z_FORE, 0.40, "site", "forecourt deck pier"))
    return out


def outdoor_stairs() -> list[OutdoorStair]:
    """Rule 4.11 / C11-ARR-01..03: every outdoor stair with its flights and landings."""
    rs = OutdoorStair("road stair", "road → arrival court", [
        Flight("rs-f1", 12, round((Z_FORE - 1675.50) / 12, 4), 0.32, 1.40, Z_FORE, 1675.50),
        Flight("rs-f2", 12, round((1675.50 - Z_COURT) / 12, 4), 0.32, 1.40, 1675.50, Z_COURT),
    ], ["rs-head", "rs-l1"], landing_min=1.40, handrails="both sides; canopy over L1 and F2", width_clear=1.40)
    cs = OutdoorStair("court stair", "arrival court → garden walk (lower floor)", [
        Flight(f"cs-f{i + 1}", 8, round(CS_DROP / 8, 5), 0.34, 1.27, round(Z_COURT - CS_DROP * i, 3), round(Z_COURT - CS_DROP * (i + 1), 3)) for i in range(3)
    ], ["court", "cs-l1", "cs-l2", "walk-s"], landing_min=1.20, handrails="both sides", width_clear=1.27)  # 1.27 m kerb to wall
    ls = OutdoorStair("lawn stair", "garden terrace → play lawn", [
        Flight("ls-f1", 8, 0.14875, 0.32, 1.30, Z_TLOW, round(Z_TLOW - 8 * 0.14875, 3)),
        Flight("ls-f2", 8, 0.14875, 0.32, 1.30, round(Z_TLOW - 8 * 0.14875, 3), Z_LAWN),
    ], ["ls-top", "ls-l1", "lawn"], landing_min=1.20, handrails="both sides", width_clear=1.30)
    return [rs, cs, ls]


def option() -> Option:
    road, main, lower = road_level(), main_level(), lower_level()
    main.terraces += road_stair_terraces()
    return Option(
        "C11", "C10 corrected: every floor stands on something", "C10 + 27 specialist reviews (CONSOLIDATED.md) + stmt-027/028/029",
        "The same three floors as C10, now with a wall, a column line or dug ground under every part of every floor, "
        "the owner's big arrival court with an easy stair from the road, and easy outdoor stairs down to the garden.",
        {"road": road, "main": main, "lower": lower},
        Z_LAWN, TERR, [],
        {"ew": [(10.4, "through the kitchen, living room and lounge"),
                (4.2, "through the garage, service room, stair and grandparents"),
                (16.6, "along the court stair, the garden walk and the lawn"),
                (14.0, "through the court, the children's rooms and the loggia")],
         "ns": [(-1.8, "through the forecourt, its deck, W1 and the court"),
                (5.6, "through the garage, wet cluster, kitchen, store and the court stair"),
                (10.4, "through the lift and its pit, the halls, dining and the boys' room"),
                (21.2, "through the garden terrace, the lawn stair and the lawn")]},
    )


RISERS = {"rs-f1": 12, "rs-f2": 12, "cs-f1": 8, "cs-f2": 8, "cs-f3": 8, "ls-f1": 8, "ls-f2": 8}
# C11-WAT-03: structural slab set down under terraces over heated rooms; lower slabs over the store, cistern and crawl void too
SETDOWN = {"t-south": 0.25, "deck-r": 0.25, "green-r": 0.25, "t-low": 0.20, "loggia": 0.20, "walk-e": 0.20, "walk-m": 0.20,
           "ls-top": 0.20, "ls-l1": 0.20}


def build() -> Option:
    """The option with drawing attributes: riser counts, terrace set-downs, the qibla."""
    opt = option()
    for lv in opt.levels.values():
        for t in lv.terraces:
            if t.id in RISERS:
                t.risers = RISERS[t.id]
            t.setdown = SETDOWN.get(t.id, 0.0)
    opt.qibla_bearing = QIBLA
    import engine

    engine.TREE_OVERRIDE = TREES
    return opt


# WC pans for the sightline test (C11-KB-03, §7 check 17): (level, room, centre)
WC_PANS = [("road", "wc-r", (3.4, 12.0)), ("main", "wc-m", (5.46, 3.25)), ("main", "ens", (9.75, 3.7)),
           ("lower", "wc-l", (5.8, 9.75)), ("lower", "gens", (9.8, 3.9))]

# three medium deciduous trees on the middle of the bank (LND-04): Zagros maple, Cercis, Pistacia atlantica
TREES = [(28.72 - 0.448 * (v - 2.5), v) for v in (2.5, 6.0, 10.0)]

# Water on every outdoor surface (C11-WAT-01..08, §7 check 9): fall direction (unit u, v), outlets, overflow
WATER = {
    "t-south": ((0, 1), [(8.5, 15.9), (14.8, 15.9)], (11.25, 16.3), "inverted roof 1:60 to the south edge; outlets inside the terrace; slot channels at the 3 sliders"),
    "roof": ((0, 1), [(3.0, 12.6), (8.0, 12.6)], (5.5, 12.95), "road-level roof: 1:60 to two outlets on the south parapet, overflow scupper; ladder and anchor line from the roof terrace"),
    "walk-e": ((0, 1), [(16.3, 17.0), (17.6, 17.0)], (17.0, 17.1), "walk slab 1:60 to a channel on its south edge"),
    "walk-m": ((0, 1), [(12.6, 17.0), (14.6, 17.0)], (13.6, 17.1), "walk slab 1:40 to a channel on its south edge"),
    "balc-e": ((1, 0), [(19.7, 7.0), (19.7, 15.5)], (19.8, 11.0), "uninsulated, 1:60 to the edge gutter, drips"),
    "balc-m": ((1, 0), [(19.7, 3.0), (19.7, 5.8)], (19.8, 4.5), "uninsulated, 1:60 to the edge gutter"),
    "deck-r": ((1, 0), [(17.6, 7.5), (17.6, 12.0)], (17.9, 9.8), "pedestal pavers, 1:60 east; channel at the lobby and office doors"),
    "green-r": ((1, 0), [(17.5, 1.6), (17.5, 5.8)], (17.9, 3.6), "extensive green roof, root-resistant membrane; never north"),
    "fore": ((-1, 0), [(-0.5, 2.0), (-2.6, 6.8)], (-3.4, 9.0), "1.5-2 % to a DN200 channel 0.8 m inside a crest along the boundary; slot drain across each opening"),
    "rs-head": ((1, 0), [(-5.2, 11.8), (-5.9, 11.7)], (-5.5, 11.75), "30 mm hump at the gate and a 150 mm slot drain across the stair head, so road water never runs down the stair (WAT-N01)"),
    "fore-deck": ((-1, 0), [(-2.0, 9.5), (-3.2, 11.3)], (-3.4, 10.5), "deck falls to the boundary channel"),
    "porch": ((0, 1), [(1.0, 11.5), (1.9, 10.6)], (1.0, 11.6), "slot drain at the door, falls into the court"),
    "court-w": ((0, 1), [(4.3, 15.8), (-2.8, 16.9)], (0.8, 15.9), "1:60 to a channel on the south edge, SE and SW gullies, DN150 outfall down the stair band; snow pit at the NW corner"),
    "loggia": ((0, 1), [(16.0, 15.9), (17.6, 15.9)], (16.8, 16.0), "suspended slab, 1:60 to a channel at the front"),
    "t-low": ((1, 0), [(20.4, 2.0), (20.4, 11.5)], (20.5, 6.8), "suspended slab, 1:60 east, outlets on the east wall"),
    "walk-s": ((0, 1), [(10.5, 17.0), (15.0, 17.0)], (12.8, 17.1), "1:40 cross-fall to a channel, catch pits every 1.5 m of drop"),
    "lawn": ((1, 0), [(21.0, 12.0), (27.0, 2.0)], (26.0, 10.0), "1:60 east, slot drain on the west edge, heel drains, swale at the north cut"),
}
