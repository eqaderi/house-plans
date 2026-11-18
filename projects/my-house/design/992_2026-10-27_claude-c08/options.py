"""The three C08 concepts, each a reworked version of one of the owner's 0109-r5 plans.

Coordinates are metres in the owner's frame (u east along the north boundary, v south).
Shared skeleton (owner signature): north stair core with REST 1.40 at north, lift beside it,
the house stepping east as it steps down: Road u 0-12.6, Main u 2-19.2, Lower u 5-22.2.
Levels kept from the owner: Road 1677.50, Main 1673.60, Lower 1670.00.
"""

from __future__ import annotations

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
    mats,
    rect,
    shower,
    sofa,
    sofa_l,
    stair_dogleg,
    table_chairs,
    wardrobe,
    wc,
)
from shapely.geometry import LineString, Point, Polygon

Z_ROAD, Z_MAIN, Z_LOWER = 1677.50, 1673.60, 1670.00

STAIR = (6.8, 1.1, 10.0, 7.3)  # dog-leg, REST 1.40 at north, floor landing at south
LIFT = (10.0, 5.0, 12.1, 7.3)  # door on the south face at every level


# ------------------------------------------------------------------ road level (shared)
def road_level(variant: str = "") -> Level:
    rooms = [
        Room("garage", "GARAGE · 2 CARS + WORKBENCH", "garage", R(0.0, 1.1, 6.8, 9.5)),
        Room("stair-r", "STAIR 24R", "stair", R(*STAIR), show_dims=False),
        Room("lift-r", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("lobby-r", "CORE LOBBY", "hall", R(6.8, 7.3, 12.1, 9.5), label_at=(10.9, 8.4), show_dims=False, small=True),
        Room("hall-r", "ENTRANCE HALL", "hall", R(0.0, 9.5, 9.4, 11.6), label_at=(5.0, 10.75)),
        Room("office", "QUIET OFFICE", "study", R(9.4, 9.5, 12.6, 12.6)),
        Room("wc-r", "WC + SHOWER", "wet", R(7.2, 11.6, 9.4, 13.3), small=True),
        Room("plant", "PLANT + TANKS", "service", R(3.4, 11.6, 7.2, 13.3), small=True),
    ]
    doors = [
        Door("garage", "ext", 0.0, 3.25, 3.35, "v", "shutter"),
        Door("garage", "ext", 0.0, 7.35, 3.35, "v", "shutter"),
        Door("hall-r", "ext", 0.0, 10.55, 1.2, "v", "door", swing=1, hinge=-1),
        Door("garage", "lobby-r", 6.8, 8.4, 1.0, "v", "door", swing=1, hinge=1),
        Door("lobby-r", "stair-r", 8.4, 7.3, 3.2, "u", "open"),
        Door("lobby-r", "lift-r", 11.05, 7.3, 1.0, "u", "glass"),
        Door("hall-r", "lobby-r", 8.1, 9.5, 2.6, "u", "open"),
        Door("hall-r", "office", 9.4, 10.5, 0.9, "v", "door", swing=1, hinge=-1),
        Door("hall-r", "wc-r", 8.3, 11.6, 0.8, "u", "door", swing=1, hinge=1),
        Door("hall-r", "plant", 5.3, 11.6, 1.2, "u", "door", swing=1, hinge=-1),
        Door("office", "ext", 12.6, 11.0, 1.6, "v", "slide"),
    ]
    windows = [Win(12.6, 9.8, 12.6, 10.4), Win(9.9, 12.6, 12.1, 12.6), Win(0.0, 9.9, 0.0, 9.95)]
    furniture = flat(
        car(0.35, 1.8, 5.0, 2.0, "LC300"), car(0.35, 6.4, 4.8, 1.95, "CAR 2"),
        [rect(6.15, 1.5, 6.75, 6.2, "bench", "")], [Shape(Point(5.6, 3.9), "text", "WORKBENCH")],
        [rect(5.4, 7.0, 6.75, 9.45, "dash")], [Shape(Point(6.05, 8.25), "text", "BIKES")],
        lockers(0.6, 9.55, 4.2, 10.1, 6), [Shape(Point(2.4, 10.35), "text", "6 LOCKERS")],
        rect(5.0, 11.0, 7.0, 11.55, "bench"),
        stair_dogleg(*STAIR, label="LANDING"), lift_car(*LIFT),
        desk(10.0, 9.6, 12.5, 10.3, (11.2, 10.7)), armchair(9.6, 11.6, 0.8),
        wc(8.9, 12.05, "w"), basin(7.6, 12.0), [Shape(R(7.3, 12.4, 8.3, 13.25), "fixture")],
        [rect(3.6, 11.75, 4.7, 13.2, "bench", "")], [Shape(Point(5.8, 12.45), "text", "BOILER · PUMPS · TANKS")],
    )
    terraces = [
        Terrace("deck-r", "OFFICE ROOF DECK", R(12.6, 7.3, 19.2, 13.0), Z_ROAD - 0.05, "deck"),
        Terrace("fore", "FORECOURT", Polygon([(0.0, 1.1), (0.0, 11.6), (-6.3, 11.6), (-0.6, 1.1)]).intersection(PARCEL), 1677.40, "court",
                label_at=(-2.6, 8.0)),
    ]
    notes = [
        "Front door is on the west façade and opens into a straight, rectangular entrance hall. The stair and lift are at the far end, in plain view.",
        "Groceries: garage → fire door → core lobby → lift is 4 m, all indoors (rule 5.1).",
        "Two independent 3.35 m shutters. Each bay is 4.2 m wide, so all four car doors open their full 0.65 m. A 4.7 m workbench and bike wall run along the back.",
        "Plant room opens off the entrance hall. Replacement modules go out straight through the 1.2 m front door.",
        "Quiet office faces east onto the roof deck over the living room (rule 5.5).",
    ]
    return Level("road", "ROAD LEVEL", Z_ROAD, rooms, doors, windows, furniture, terraces, notes)


def garden_stair() -> Terrace:
    return Terrace("gstair", "GARDEN STAIR 22R", Polygon([(-2.4, 11.6), (-1.2, 11.6), (-1.2, 17.4), (-2.4, 17.4)]), Z_ROAD - 0.1,
                   "stair", label_at=(-4.2, 14.6))


# ------------------------------------------------------------------ OPTION 1  (from owner's B)
def wet_cluster_main(u0: float, v0: float) -> tuple[list[Room], list[Door], list]:
    """Owner's 4-part screened cluster: WC + shower behind, wudu + screened lobby in front."""
    rooms = [
        Room("wc-m", "WC", "wet", R(u0, v0, u0 + 1.5, v0 + 2.1), small=True, show_dims=False),
        Room("sh-m", "SHOWER", "wet", R(u0 + 1.5, v0, u0 + 3.0, v0 + 2.1), small=True, show_dims=False),
        Room("wudu", "WUDU", "wet", R(u0, v0 + 2.1, u0 + 1.5, 7.3), small=True, show_dims=False),
        Room("wlob", "LOBBY", "wet", R(u0 + 1.5, v0 + 2.1, u0 + 3.0, 7.3), small=True, show_dims=False),
    ]
    doors = [
        Door("hall", "wlob", u0 + 2.25, 7.3, 0.9, "u", "open"),
        Door("wlob", "wudu", u0 + 1.5, v0 + 3.3, 1.2, "v", "open"),
        Door("wudu", "wc-m", u0 + 0.75, v0 + 2.1, 0.75, "u", "door", swing=-1, hinge=-1),
        Door("wlob", "sh-m", u0 + 2.25, v0 + 2.1, 0.75, "u", "door", swing=-1, hinge=1),
    ]
    furn = flat(
        wc(u0 + 0.75, v0 + 0.6, "s"), basin(u0 + 1.2, v0 + 1.7, 0.4, 0.32),
        shower(u0 + 1.6, v0 + 0.08, u0 + 2.92, v0 + 1.1),
        rect(u0 + 0.05, v0 + 2.6, u0 + 0.45, 7.25, "bench"),
        Shape(LineString([(u0 + 1.55, v0 + 2.75), (u0 + 2.4, v0 + 2.75)]), "baffle"),
    )
    return rooms, doors, furn


def option1() -> Option:
    wr, wd, wf = wet_cluster_main(3.8, 2.8)
    living = R(13.4, 5.3, 19.2, 13.0)
    bedroom = Polygon([(12.1, 1.1), (16.4, 1.1), (16.4, 3.1), (19.2, 3.1), (19.2, 5.3), (12.1, 5.3)])
    m = [
        Room("pantry", "PANTRY", "service", R(2.0, 4.6, 3.8, 7.3), small=True),
        *wr,
        Room("stair-m", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-m", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("ens", "ENSUITE", "wet", R(10.0, 1.1, 12.1, 5.0), small=True),
        Room("dress", "DRESS", "service", R(16.4, 1.1, 19.2, 3.1), small=True),
        Room("mlob", "", "hall", R(12.1, 5.3, 13.4, 7.3), show_dims=False),
        Room("master", "MASTER BEDROOM", "sleep", bedroom, label_at=(14.4, 2.9), main=True),
        Room("hall", "FAMILY HALL", "hall", R(2.0, 7.3, 13.4, 9.5), label_at=(7.9, 8.45)),
        Room("entry", "ENTRY", "hall", R(2.0, 9.5, 4.6, 13.0), small=True),
        Room("kitchen", "KITCHEN", "kitchen", R(4.6, 9.5, 9.2, 13.0), main=True),
        Room("dining", "DINING 6–8", "day", R(9.2, 9.5, 13.4, 13.0), main=True),
        Room("living", "LIVING", "day", living, label_at=(16.2, 10.3), main=True),
    ]
    md = wd + [
        Door("entry", "ext", 2.0, 12.15, 1.2, "v", "door", swing=1, hinge=1),
        Door("hall", "entry", 3.3, 9.5, 2.6, "u", "open"),
        Door("hall", "pantry", 2.9, 7.3, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("hall", "stair-m", 8.4, 7.3, 3.2, "u", "open"),
        Door("hall", "lift-m", 11.05, 7.3, 1.0, "u", "glass"),
        Door("hall", "kitchen", 5.4, 9.5, 1.1, "u", "open"),
        Door("hall", "dining", 11.4, 9.5, 3.4, "u", "open"),
        Door("kitchen", "dining", 9.2, 10.3, 1.1, "v", "open"),
        Door("kitchen", "ext", 8.1, 13.0, 1.6, "u", "slide"),
        Door("dining", "ext", 11.3, 13.0, 2.4, "u", "slide"),
        Door("hall", "living", 13.4, 8.4, 1.8, "v", "open"),
        Door("hall", "mlob", 12.75, 7.3, 1.0, "u", "door", swing=-1, hinge=-1),
        Door("mlob", "master", 12.75, 5.3, 0.9, "u", "door", swing=-1, hinge=1),
        Door("master", "dress", 17.0, 3.1, 0.8, "u", "door", swing=-1, hinge=-1),
        Door("master", "ens", 12.1, 3.9, 0.8, "v", "door", swing=-1, hinge=1),
        Door("living", "ext", 19.2, 9.7, 3.0, "v", "slide"),
        Door("living", "ext", 16.2, 13.0, 2.4, "u", "slide"),
    ]
    mw = [Win(5.0, 13.0, 6.8, 13.0), Win(2.0, 9.9, 2.0, 11.2), Win(3.0, 13.0, 4.0, 13.0),
          Win(19.2, 3.4, 19.2, 5.0), Win(13.0, 1.1, 15.8, 1.1), Win(10.6, 1.1, 11.6, 1.1),
          Win(17.4, 1.1, 18.4, 1.1), Win(19.2, 11.8, 19.2, 12.7), Win(13.9, 13.0, 15.0, 13.0),
          Win(19.2, 5.8, 19.2, 7.6)]
    mf = flat(
        rect(2.05, 4.65, 2.5, 7.25, "bench"), rect(3.3, 4.65, 3.75, 7.25, "bench"),
        wf,
        stair_dogleg(*STAIR, label="UP 24R · DN 22R"), lift_car(*LIFT),
        shower(10.1, 1.2, 12.0, 2.3), wc(10.5, 3.0, "e"), basin(11.65, 3.2, 0.45, 0.4), basin(11.65, 4.2, 0.45, 0.4),
        rect(16.5, 1.15, 19.15, 1.75, "bench"),
        bed(14.3, 1.25, 1.8, 2.1, "n"), rect(13.65, 1.2, 14.2, 1.75), rect(16.2, 1.2, 16.55, 1.75),
        armchair(17.6, 3.6, 0.85), armchair(18.3, 3.6, 0.85),
        counter(4.65, 9.55, 5.25, 12.95, hob=(4.95, 11.6), fridge=(4.65, 9.55, 5.3, 10.25)),
        counter(5.25, 12.35, 9.1, 12.95, sink=(6.0, 12.65)),
        rect(6.3, 10.5, 8.4, 11.3, "bench"), Shape(Point(7.35, 10.15), "text", "ISLAND · DAILY MEALS"),
        table_chairs(11.3, 11.25, 2.0, 1.0, 3),
        sofa_l(19.0, 5.5, 3.4, 3.0, "ne"), coffee(16.5, 6.7, 17.9, 7.6), armchair(14.6, 6.1, 0.8),
        armchair(14.6, 7.2, 0.8), rect(13.45, 5.6, 13.85, 7.2, "bench", ""),
        sofa(14.4, 12.0, 16.4, 12.8), armchair(18.0, 11.7, 0.85), coffee(15.0, 11.0, 15.9, 11.6), table_chairs(17.4, 9.6, 0.9, 0.9, 1, False),
        rect(2.1, 9.6, 2.6, 11.4, "bench"), Shape(Point(3.4, 10.5), "text", "COATS · SHOES"),
    )
    main = Level("main", "MAIN FLOOR", Z_MAIN, m, md, mw, mf, [
        Terrace("t-south", "SOUTH TERRACE", R(4.6, 13.0, 19.2, 16.4), Z_MAIN - 0.02),
        Terrace("t-east", "EAST TERRACE", R(19.2, 7.3, 22.2, 16.4), Z_MAIN - 0.02),
        Terrace("court-w", "ARRIVAL COURT", Polygon([(0.0, 9.6), (2.0, 9.6), (2.0, 16.4), (4.6, 16.4),
                                                      (4.6, 17.4), (-1.2, 17.4), (-1.2, 11.6), (0.0, 11.6)]), Z_MAIN, "court", label_at=(0.9, 15.0)),
        garden_stair(),
    ], [
        "Arrival court at the SW lies open to the sky, sheltered by the road level above. The door on the west façade opens into a square entry, which opens straight into the family hall, and the stair and lift stand in front of you (rule 2.6).",
        "One family hall, no corridor bits. Kitchen, dining and living each open straight off it (rule 2.1).",
        "Kitchen on the south, with a 1.6 m slider to the south terrace (rule 1.1). It is semi-open: one portal to the hall and one to the dining, with full-height walls between (rule 1.3). The island is for everyday meals.",
        "Living is 43 m², 5.7 × 7.6 m. The deep sofa corner sits in the NE, closed to the north by the master suite (rule 3.1), and a reading corner faces the south terrace. Rule 3.1 pictured an L-shaped room; the true L is in option 2.",
        "Master suite on the quiet north side (rule 6.5). Its own lobby leads to the bedroom, and the dressing room and ensuite open off the bedroom (rule 2.5).",
        "The pantry door is 2.3 m from the fridge, across the hall. The wudu cluster has a screened lobby (owner's 4-part pattern).",
    ])
    # ---- lower floor
    hall_l = Polygon([(8.2, 7.3), (15.5, 7.3), (15.5, 9.4), (17.6, 9.4), (17.6, 11.6), (8.2, 11.6)])
    lounge = Polygon([(15.5, 7.3), (22.2, 7.3), (22.2, 11.6), (17.6, 11.6), (17.6, 9.4), (15.5, 9.4)])
    lo = [
        Room("store-l", "STORE", "service", R(5.0, 4.0, 6.8, 7.3), small=True),
        Room("stair-l", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-l", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("riser", "RISERS", "service", R(10.0, 2.8, 12.1, 5.0), small=True, show_dims=False),
        Room("wc-l", "WC", "wet", R(12.1, 2.8, 13.8, 4.9), small=True, show_dims=False),
        Room("sh-l", "SHOWER", "wet", R(13.8, 2.8, 15.5, 4.9), small=True, show_dims=False),
        Room("bath-l", "BASINS", "wet", R(12.1, 4.9, 15.5, 7.3), small=True),
        Room("laundry", "LAUNDRY + DRYING", "service", R(5.0, 7.3, 8.2, 11.6)),
        Room("hall-l", "FAMILY HALL + TEA BAR", "hall", hall_l, label_at=(11.0, 10.0)),
        Room("lounge", "GARDEN LOUNGE", "day", lounge, label_at=(19.3, 9.0), main=True),
        Room("boys", "BOYS", "sleep", R(6.8, 11.6, 11.1, 16.4), main=True),
        Room("girls", "GIRLS", "sleep", R(11.1, 11.6, 15.4, 16.4), main=True),
        Room("gvest", "", "hall", R(15.4, 11.6, 17.6, 13.4), show_dims=False),
        Room("gens", "SEATED ENSUITE", "wet", R(15.4, 13.4, 17.6, 16.4), small=True),
        Room("guest", "GRANDPARENTS / GUEST", "sleep", R(17.6, 11.6, 22.2, 16.4), main=True),
    ]
    ld = [
        Door("hall-l", "stair-l", 8.4, 7.3, 3.2, "u", "open"),
        Door("hall-l", "lift-l", 11.05, 7.3, 1.0, "u", "glass"),
        Door("hall-l", "laundry", 8.2, 8.3, 1.0, "v", "door", swing=-1, hinge=-1),
        Door("laundry", "store-l", 5.9, 7.3, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("hall-l", "bath-l", 13.8, 7.3, 1.4, "u", "open"),
        Door("bath-l", "wc-l", 12.95, 4.9, 0.75, "u", "door", swing=-1, hinge=-1),
        Door("bath-l", "sh-l", 14.65, 4.9, 0.75, "u", "door", swing=-1, hinge=1),
        Door("hall-l", "boys", 10.4, 11.6, 0.9, "u", "door", swing=1, hinge=1),
        Door("hall-l", "girls", 11.8, 11.6, 0.9, "u", "door", swing=1, hinge=-1),
        Door("hall-l", "lounge", 16.55, 9.4, 2.0, "u", "open"),
        Door("hall-l", "gvest", 16.5, 11.6, 1.0, "u", "open"),
        Door("gvest", "guest", 17.6, 12.5, 0.9, "v", "door", swing=1, hinge=-1),
        Door("guest", "gens", 17.6, 14.9, 0.9, "v", "door", swing=-1, hinge=1),
        Door("lounge", "ext", 22.2, 9.4, 3.0, "v", "slide"),
        Door("lounge", "ext", 19.8, 7.3, 2.4, "u", "slide"),
        Door("guest", "ext", 22.2, 14.3, 1.0, "v", "glass"),
    ]
    lw = [Win(7.7, 16.4, 10.0, 16.4), Win(12.0, 16.4, 14.4, 16.4), Win(18.4, 16.4, 21.4, 16.4),
          Win(22.2, 12.4, 22.2, 13.4), Win(15.9, 16.4, 17.0, 16.4)]
    lf = flat(
        rect(5.05, 4.05, 5.6, 7.25, "bench"), rect(6.2, 4.05, 6.75, 7.25, "bench"),
        stair_dogleg(*STAIR, label="UP 22R"), lift_car(*LIFT),
        wc(12.95, 3.4, "s"), shower(13.9, 2.9, 15.4, 4.0), basin(12.7, 6.9), basin(13.5, 6.9), basin(14.3, 6.9),
        rect(5.05, 7.35, 5.7, 11.55, "bench"), rect(7.55, 9.4, 8.15, 11.55, "bench"),
        Shape(Point(5.37, 7.95).buffer(0.25), "fixture"), Shape(Point(5.37, 8.65).buffer(0.25), "fixture"),
        Shape(LineString([(6.0, 11.1), (7.3, 11.1)]), "dash"), Shape(Point(6.6, 9.6), "text", "FOLD · IRON · DRY"),
        counter(12.2, 7.4, 15.4, 8.0, sink=(13.2, 7.7), fridge=(14.75, 7.4, 15.4, 8.0)),
        Shape(Point(13.6, 8.25), "text", "TEA + SNACK BAR"),
        sofa(9.0, 10.6, 11.6, 11.45), coffee(9.7, 9.7, 11.0, 10.3), armchair(12.0, 9.6, 0.8),
        bed(6.9, 15.0, 1.0, 2.1, "w", 1), bed(8.95, 15.0, 1.0, 2.1, "e", 1),
        bed(11.2, 15.0, 1.0, 2.1, "w", 1), bed(13.25, 15.0, 1.0, 2.1, "e", 1),
        desk(6.95, 13.0, 7.55, 14.4, (7.9, 13.7)), desk(10.45, 13.0, 11.05, 14.4, (10.1, 13.7)),
        desk(11.2, 13.0, 11.8, 14.4, (12.15, 13.7)), desk(14.75, 13.0, 15.35, 14.4, (14.4, 13.7)),
        wardrobe(6.9, 11.7, 8.4, 12.3), wardrobe(8.5, 11.7, 9.9, 12.3),
        wardrobe(12.6, 11.7, 13.95, 12.3), wardrobe(14.0, 11.7, 15.35, 12.3),
        bed(20.0, 13.3, 1.6, 2.05, "e"), wardrobe(17.7, 11.7, 19.3, 12.3), armchair(18.0, 15.4, 0.8),
        wc(17.25, 15.9, "w"), basin(16.0, 13.85), shower(15.5, 15.2, 16.6, 16.3),
        Shape(Point(16.5, 14.8).buffer(0.75), "dash"),
        rect(15.5, 11.7, 17.5, 12.2, "bench"),
        sofa_l(22.0, 7.6, 3.2, 2.6, "ne"), coffee(19.6, 8.4, 20.7, 9.3), armchair(18.3, 7.6, 0.8),
    )
    lower = Level("lower", "LOWER FLOOR + GARDEN", Z_LOWER, lo, ld, lw, lf, [
        Terrace("t-cov", "COVERED TERRACE", R(15.5, 2.8, 22.2, 7.3), Z_LOWER - 0.02),
        Terrace("t-low", "GARDEN TERRACE", R(22.2, 2.8, 25.2, 16.4), Z_LOWER - 0.02),
        Terrace("walk-s", "", R(6.8, 16.4, 25.2, 17.4), Z_LOWER - 0.15, "court"),
        Terrace("lawn", "EAST LAWN", ENVELOPE.intersection(R(25.2, 0.0, 40.0, 17.4)), 1668.60, "lawn"),
    ], [
        "Boys and girls rooms keep the owner's 4.3 × 4.8 m along the south. Each fits 2 beds, 2 desks and 2 wardrobes, and the floor sits above ground there, so the windows face daylight.",
        "Grandparents/guest room in the SE corner has its own step-free seated ensuite with a 1.5 m turning circle (fixes I10). The lift is 10 m away on the level.",
        "Family hall with a tea/snack bar (sink and fridge), so nobody climbs for water at night (rule 6.6). It opens straight into the garden lounge.",
        "Garden lounge opens east and north onto garden terraces. The NE terrace is covered by the master suite above.",
        "Laundry/drying is 13 m² beside the core, with the household store off it (rule 6.3, fixes I12 and I22).",
        "Shared WC, shower and a 3-basin lobby sit beside the stair, 3–8 m from every bedroom.",
    ])
    return Option(
        "C08-1", "Family-hall house · from owner's B", "user-designed 0109-r5 Option B",
        "B's north core, wet cluster and south bedroom row are kept. The parents' suite moves from the SW to the quiet NE, which frees the south for kitchen, dining and an L-shaped living room.",
        {"road": road_level(), "main": main, "lower": lower}, 1668.60, 25.2,
        [], {"ew_v": 10.6, "ns_u": 14.0},
    )



# ------------------------------------------------------------------ shared lower-floor pieces
def lower_core(east: float) -> tuple[list[Room], list[Door], list]:
    rooms = [
        Room("store-l", "STORE", "service", R(5.0, 4.0, 6.8, 7.3), small=True),
        Room("stair-l", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-l", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("riser", "RISERS", "service", R(10.0, 2.8, 12.1, 5.0), small=True, show_dims=False),
        Room("wc-l", "WC", "wet", R(12.1, 2.8, 13.8, 4.9), small=True, show_dims=False),
        Room("sh-l", "SHOWER", "wet", R(13.8, 2.8, 15.5, 4.9), small=True, show_dims=False),
        Room("bath-l", "BASINS", "wet", R(12.1, 4.9, 15.5, 7.3), small=True),
        Room("laundry", "LAUNDRY + DRYING", "service", R(5.0, 7.3, 8.2, 11.6)),
        Room("boys", "BOYS", "sleep", R(6.8, 11.6, 11.1, 16.4), main=True),
        Room("girls", "GIRLS", "sleep", R(11.1, 11.6, 15.4, 16.4), main=True),
    ]
    doors = [
        Door("hall-l", "stair-l", 8.4, 7.3, 3.2, "u", "open"),
        Door("hall-l", "lift-l", 11.05, 7.3, 1.0, "u", "glass"),
        Door("hall-l", "laundry", 8.2, 8.3, 1.0, "v", "door", swing=-1, hinge=-1),
        Door("laundry", "store-l", 5.9, 7.3, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("hall-l", "bath-l", 13.8, 7.3, 1.4, "u", "open"),
        Door("bath-l", "wc-l", 12.95, 4.9, 0.75, "u", "door", swing=-1, hinge=-1),
        Door("bath-l", "sh-l", 14.65, 4.9, 0.75, "u", "door", swing=-1, hinge=1),
        Door("hall-l", "boys", 10.4, 11.6, 0.9, "u", "door", swing=1, hinge=1),
        Door("hall-l", "girls", 11.8, 11.6, 0.9, "u", "door", swing=1, hinge=-1),
    ]
    furn = flat(
        rect(5.05, 4.05, 5.6, 7.25, "bench"), rect(6.2, 4.05, 6.75, 7.25, "bench"),
        stair_dogleg(*STAIR, label="UP 22R"), lift_car(*LIFT),
        wc(12.95, 3.4, "s"), shower(13.9, 2.9, 15.4, 4.0), basin(12.7, 6.9), basin(13.5, 6.9), basin(14.3, 6.9),
        rect(5.05, 7.35, 5.7, 11.55, "bench"), rect(7.55, 9.4, 8.15, 11.55, "bench"),
        Shape(Point(5.37, 7.95).buffer(0.25), "fixture"), Shape(Point(5.37, 8.65).buffer(0.25), "fixture"),
        Shape(LineString([(6.0, 11.1), (7.3, 11.1)]), "dash"), Shape(Point(6.6, 9.6), "text", "FOLD · IRON · DRY"),
        bed(6.9, 15.0, 1.0, 2.1, "w", 1), bed(8.95, 15.0, 1.0, 2.1, "e", 1),
        bed(11.2, 15.0, 1.0, 2.1, "w", 1), bed(13.25, 15.0, 1.0, 2.1, "e", 1),
        desk(6.95, 13.0, 7.55, 14.4, (7.9, 13.7)), desk(10.45, 13.0, 11.05, 14.4, (10.1, 13.7)),
        desk(11.2, 13.0, 11.8, 14.4, (12.15, 13.7)), desk(14.75, 13.0, 15.35, 14.4, (14.4, 13.7)),
        wardrobe(6.9, 11.7, 8.4, 12.3), wardrobe(8.5, 11.7, 9.9, 12.3),
        wardrobe(12.6, 11.7, 13.95, 12.3), wardrobe(14.0, 11.7, 15.35, 12.3),
    )
    return rooms, doors, furn


KIDS_NOTE = ("Boys and girls rooms keep the owner's 4.3 × 4.8 m along the south. Each fits 2 beds, 2 desks and "
             "2 wardrobes, and the floor sits above ground there, so the windows face daylight.")
LAUNDRY_NOTE = "Laundry/drying is 13 m² beside the core, with the household store off it (rule 6.3, fixes I12 and I22)."


# ------------------------------------------------------------------ OPTION 2  (from owner's A)
def option2() -> Option:
    wr, wd, wf = wet_cluster_main(3.8, 2.8)
    living = Polygon([(13.4, 5.3), (15.8, 5.3), (15.8, 2.6), (18.6, 2.6), (18.6, 13.0), (13.4, 13.0)])
    m = [
        Room("pantry", "PANTRY", "service", R(2.0, 4.6, 3.8, 7.3), small=True),
        *wr,
        Room("stair-m", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-m", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("ens", "ENSUITE", "wet", R(10.0, 1.1, 12.1, 4.0), small=True),
        Room("linen", "LINEN", "service", R(10.0, 4.0, 12.1, 5.0), small=True, show_dims=False),
        Room("master", "MASTER BEDROOM", "sleep", R(12.1, 1.1, 15.8, 5.3), main=True),
        Room("dress", "DRESS", "service", R(15.8, 1.1, 18.6, 2.6), small=True),
        Room("mlob", "", "hall", R(12.1, 5.3, 13.4, 7.3), show_dims=False),
        Room("hall", "FAMILY HALL", "hall", R(2.0, 7.3, 13.4, 9.5), label_at=(7.9, 8.45)),
        Room("entry", "ENTRY", "hall", R(2.0, 9.5, 4.6, 13.0), small=True),
        Room("kitchen", "KITCHEN", "kitchen", R(4.6, 9.5, 9.2, 13.0), main=True),
        Room("dining", "DINING 6–8", "day", R(9.2, 9.5, 13.4, 13.0), main=True),
        Room("living", "LIVING + NE PRAYER BAY", "day", living, label_at=(16.0, 9.9), main=True),
    ]
    md = wd + [
        Door("entry", "ext", 2.0, 12.15, 1.2, "v", "door", swing=1, hinge=1),
        Door("hall", "entry", 3.3, 9.5, 2.6, "u", "open"),
        Door("hall", "pantry", 2.9, 7.3, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("hall", "stair-m", 8.4, 7.3, 3.2, "u", "open"),
        Door("hall", "lift-m", 11.05, 7.3, 1.0, "u", "glass"),
        Door("hall", "kitchen", 5.4, 9.5, 1.1, "u", "open"),
        Door("hall", "dining", 11.4, 9.5, 3.4, "u", "open"),
        Door("kitchen", "dining", 9.2, 10.3, 1.1, "v", "open"),
        Door("kitchen", "ext", 8.1, 13.0, 1.6, "u", "slide"),
        Door("dining", "ext", 11.3, 13.0, 2.4, "u", "slide"),
        Door("hall", "living", 13.4, 8.4, 1.8, "v", "open"),
        Door("hall", "mlob", 12.75, 7.3, 1.0, "u", "door", swing=-1, hinge=-1),
        Door("mlob", "master", 12.75, 5.3, 0.9, "u", "door", swing=-1, hinge=1),
        Door("master", "dress", 15.8, 1.85, 0.8, "v", "door", swing=1, hinge=-1),
        Door("master", "ens", 12.1, 3.0, 0.8, "v", "door", swing=-1, hinge=1),
        Door("master", "linen", 12.1, 4.5, 0.7, "v", "door", swing=-1, hinge=-1),
        Door("living", "ext", 18.6, 9.7, 3.0, "v", "slide"),
        Door("living", "ext", 16.0, 13.0, 2.4, "u", "slide"),
    ]
    mw = [Win(5.0, 13.0, 6.8, 13.0), Win(2.0, 9.9, 2.0, 11.2), Win(3.0, 13.0, 4.0, 13.0),
          Win(12.8, 1.1, 15.2, 1.1), Win(10.6, 1.1, 11.6, 1.1), Win(16.4, 1.1, 18.0, 1.1),
          Win(18.6, 3.2, 18.6, 5.2), Win(18.6, 11.8, 18.6, 12.7), Win(13.9, 13.0, 14.6, 13.0),
          Win(18.6, 5.8, 18.6, 7.6)]
    mf = flat(
        rect(2.05, 4.65, 2.5, 7.25, "bench"), rect(3.3, 4.65, 3.75, 7.25, "bench"),
        wf, stair_dogleg(*STAIR, label="UP 24R · DN 22R"), lift_car(*LIFT),
        shower(10.1, 1.2, 12.0, 2.2), wc(10.45, 3.3, "e"), basin(11.65, 3.3, 0.45, 0.4),
        rect(10.05, 4.05, 12.05, 4.6, "bench"),
        bed(13.05, 1.2, 1.8, 2.1, "n"), rect(12.4, 1.2, 12.95, 1.75), rect(14.95, 1.2, 15.5, 1.75),
        rect(12.2, 4.7, 13.0, 5.25, "furn"), Shape(Point(14.5, 4.6), "text", ""),
        rect(15.9, 1.15, 18.55, 1.75, "bench"),
        counter(4.65, 9.55, 5.25, 12.95, hob=(4.95, 11.6), fridge=(4.65, 9.55, 5.3, 10.25)),
        counter(5.25, 12.35, 9.1, 12.95, sink=(6.0, 12.65)),
        rect(6.3, 10.5, 8.4, 11.3, "bench"), Shape(Point(7.35, 10.15), "text", "ISLAND · DAILY MEALS"),
        table_chairs(11.3, 11.25, 2.0, 1.0, 3),
        mats(16.1, 3.0, 2, "s"), Shape(Point(17.2, 4.6), "text", "QIBLA ≈ SSW"),
        sofa_l(18.4, 6.3, 3.6, 3.0, "ne"), coffee(15.8, 7.3, 17.2, 8.2), armchair(13.8, 6.4, 0.8),
        armchair(13.8, 7.5, 0.8), sofa(14.2, 12.0, 16.2, 12.8), armchair(17.6, 11.7, 0.85),
        coffee(14.7, 11.0, 15.6, 11.6),
        rect(2.1, 9.6, 2.6, 11.4, "bench"), Shape(Point(3.4, 10.5), "text", "COATS · SHOES"),
    )
    main = Level("main", "MAIN FLOOR", Z_MAIN, m, md, mw, mf, [
        Terrace("t-south", "SOUTH TERRACE", R(4.6, 13.0, 18.6, 16.4), Z_MAIN - 0.02),
        Terrace("t-east", "EAST TERRACE", R(18.6, 2.8, 21.6, 16.4), Z_MAIN - 0.02),
        Terrace("court-w", "ARRIVAL COURT", Polygon([(0.0, 9.6), (2.0, 9.6), (2.0, 16.4), (4.6, 16.4),
                                                      (4.6, 17.4), (-1.2, 17.4), (-1.2, 11.6), (0.0, 11.6)]), Z_MAIN, "court", label_at=(0.9, 15.0)),
        garden_stair(),
    ], [
        "Same clear arrival as option 1: SW court, west door, square entry, then the family hall with the stair and lift in view (rule 2.6).",
        "Owner's A idea of a quiet NE reading/prayer bay is kept. It becomes the closed north arm of an L-shaped living room (rules 3.1 and 3.3): sofas in the SE, prayer mats facing SSW in the NE.",
        "Master bedroom sits in the middle of the north side, the quietest spot on the plan (rule 6.5). Its lobby comes off the hall. The ensuite, linen and dressing room open from inside the bedroom (rule 2.5).",
        "Kitchen with island on the south, slider to the south terrace, semi-open with two portals (rules 1.1 and 1.3). Dining sits beside it for guests.",
        "Terraces wrap the house south and east, all on the roof of the lower floor (rule 4.3).",
    ])
    # lower: grandparents suite NE (A's parents' corner), garden lounge SE
    lr, ldr, lfr = lower_core(21.6)
    hall_l = Polygon([(8.2, 7.3), (17.6, 7.3), (17.6, 9.6), (12.6, 9.6), (12.6, 11.6), (8.2, 11.6)])
    lo = lr + [
        Room("hall-l", "FAMILY HALL", "hall", hall_l, label_at=(10.4, 9.9)),
        Room("gens", "SEATED ENSUITE", "wet", R(15.5, 2.8, 17.6, 5.6), small=True, label_at=(16.55, 4.9)),
        Room("gvest", "", "hall", R(15.5, 5.6, 17.6, 7.3), show_dims=False),
        Room("guest", "GRANDPARENTS / GUEST", "sleep", R(17.6, 2.8, 21.6, 7.6), label_at=(19.4, 6.4), main=True),
        Room("lounge", "GARDEN LOUNGE + TEA BAR", "day", Polygon([(12.6, 9.6), (17.6, 9.6), (17.6, 11.6), (21.6, 11.6),
                                                                  (21.6, 16.4), (15.4, 16.4), (15.4, 11.6), (12.6, 11.6)]),
             label_at=(18.5, 13.4), main=True),
    ]
    ld = ldr + [
        Door("hall-l", "gvest", 16.55, 7.3, 1.2, "u", "open"),
        Door("gvest", "guest", 17.6, 6.45, 0.9, "v", "door", swing=1, hinge=1),
        Door("guest", "gens", 17.6, 4.2, 0.9, "v", "door", swing=-1, hinge=-1),
        Door("hall-l", "lounge", 15.1, 9.6, 3.6, "u", "open"),
        Door("lounge", "ext", 21.6, 13.6, 3.0, "v", "slide"),
        Door("lounge", "ext", 19.6, 11.6, 2.4, "u", "slide"),
        Door("lounge", "ext", 18.2, 16.4, 3.0, "u", "slide"),
        Door("guest", "ext", 21.6, 5.2, 1.0, "v", "glass"),
    ]
    lw = [Win(7.7, 16.4, 10.0, 16.4), Win(12.0, 16.4, 14.4, 16.4), Win(18.4, 2.8, 20.8, 2.8),
          Win(21.6, 3.3, 21.6, 4.4), Win(15.9, 16.4, 16.6, 16.4), Win(21.6, 13.6, 21.6, 15.6)]
    lf = lfr + flat(
        counter(12.7, 11.0, 15.3, 11.55, sink=(13.5, 11.27), fridge=(14.7, 11.0, 15.3, 11.55)),
        Shape(Point(14.0, 10.7), "text", "TEA + SNACK BAR"),
        sofa(9.0, 10.6, 11.6, 11.45), coffee(9.7, 9.7, 11.0, 10.3),
        bed(19.6, 4.6, 1.6, 2.0, "e"), wardrobe(17.7, 2.9, 19.3, 3.5), armchair(18.0, 6.6, 0.8),
        wc(17.25, 3.35, "w"), basin(16.0, 5.2), shower(15.55, 2.85, 16.6, 4.0),
        Shape(Point(16.5, 4.4).buffer(0.75), "dash"),
        sofa_l(21.4, 12.0, 3.2, 2.8, "ne"), coffee(19.0, 12.9, 20.1, 13.8), armchair(17.6, 12.2, 0.8),
        table_chairs(17.4, 15.0, 1.6, 0.8, 2),
    )
    lower = Level("lower", "LOWER FLOOR + GARDEN", Z_LOWER, lo, ld, lw, lf, [
        Terrace("court-e", "GARDEN COURT", R(17.6, 7.6, 21.6, 11.6), Z_LOWER - 0.02, label_at=(19.6, 9.6)),
        Terrace("t-low", "GARDEN TERRACE", R(21.6, 2.8, 24.6, 16.4), Z_LOWER - 0.02),
        Terrace("walk-s", "", R(6.8, 16.4, 24.6, 17.4), Z_LOWER - 0.15, "court"),
        Terrace("lawn", "EAST LAWN", ENVELOPE.intersection(R(24.6, 0.0, 40.0, 17.4)), 1668.60, "lawn"),
    ], [
        KIDS_NOTE,
        "Grandparents/guest suite takes the quiet NE garden corner (owner's A parents' corner). It has its own seated, step-free ensuite (fixes I10) and is 6 m from the lift.",
        "Garden lounge in the sunny SE corner, with the tea/snack bar at its entrance (rule 6.6). It opens south, east and north onto a planted garden court that splits it from the grandparents' suite.",
        LAUNDRY_NOTE,
    ])
    return Option(
        "C08-2", "Reading-bay house · from owner's A", "user-designed 0109-r5 Option A",
        "A's quiet NE reading bay and staggered day/night bars are kept. The bay becomes the closed north arm of an L-shaped living room, and the master bedroom takes the middle of the north side. Downstairs, A's parents' corner becomes the grandparents' suite.",
        {"road": road_level(), "main": main, "lower": lower}, 1668.60, 24.6,
        [], {"ew_v": 10.6, "ns_u": 17.0},
    )


# ------------------------------------------------------------------ OPTION 3  (from owner's C)
def option3() -> Option:
    wr, wd, wf = wet_cluster_main(3.8, 2.8)
    kitchen = Polygon([(8.2, 11.7), (10.3, 11.7), (10.3, 9.5), (13.6, 9.5), (13.6, 13.4), (8.2, 13.4)])
    m = [
        Room("pantry", "PANTRY", "service", R(8.2, 9.5, 10.3, 11.7), small=True, label_at=(9.25, 10.9)),
        Room("store-m", "STORE", "service", R(2.0, 4.6, 3.8, 7.3), small=True),
        *wr,
        Room("stair-m", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-m", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("ens", "ENSUITE", "wet", R(10.0, 1.1, 12.1, 5.0), small=True),
        Room("dress", "DRESS", "service", R(12.1, 1.1, 14.0, 3.6), small=True),
        Room("master", "MASTER BEDROOM", "sleep", Polygon([(14.0, 1.1), (17.2, 1.1), (17.2, 5.4), (12.1, 5.4),
                                                           (12.1, 3.6), (14.0, 3.6)]), label_at=(15.3, 4.1), main=True),
        Room("mlob", "", "hall", R(12.1, 5.4, 13.6, 7.3), show_dims=False),
        Room("hall", "FAMILY HALL", "hall", R(2.0, 7.3, 13.6, 9.5), label_at=(7.0, 8.45)),
        Room("entry", "ENTRY", "hall", R(2.0, 9.5, 4.2, 13.4), small=True),
        Room("dining", "DINING 6–8", "day", R(4.2, 9.5, 8.2, 13.4), main=True),
        Room("kitchen", "KITCHEN", "kitchen", kitchen, label_at=(11.9, 11.0), main=True),
        Room("living", "LIVING", "day", Polygon([(13.6, 5.4), (19.2, 5.4), (19.2, 13.4), (13.6, 13.4)]),
             label_at=(16.4, 10.0), main=True),
    ]
    md = wd + [
        Door("entry", "ext", 2.0, 12.4, 1.2, "v", "door", swing=1, hinge=1),
        Door("hall", "entry", 3.1, 9.5, 2.2, "u", "open"),
        Door("hall", "store-m", 2.9, 7.3, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("hall", "stair-m", 8.4, 7.3, 3.2, "u", "open"),
        Door("hall", "lift-m", 11.05, 7.3, 1.0, "u", "glass"),
        Door("hall", "dining", 6.2, 9.5, 3.0, "u", "open"),
        Door("hall", "kitchen", 12.0, 9.5, 1.1, "u", "open"),
        Door("kitchen", "dining", 8.2, 12.5, 1.2, "v", "open"),
        Door("kitchen", "pantry", 9.3, 11.7, 0.8, "u", "door", swing=-1, hinge=1),
        Door("kitchen", "ext", 11.2, 13.4, 1.6, "u", "slide"),
        Door("dining", "ext", 6.2, 13.4, 2.4, "u", "slide"),
        Door("hall", "living", 13.6, 8.4, 1.8, "v", "open"),
        Door("hall", "mlob", 12.85, 7.3, 1.0, "u", "door", swing=-1, hinge=-1),
        Door("mlob", "master", 12.85, 5.4, 0.9, "u", "door", swing=-1, hinge=1),
        Door("master", "dress", 13.1, 3.6, 0.8, "u", "door", swing=-1, hinge=-1),
        Door("master", "ens", 12.1, 4.45, 0.8, "v", "door", swing=-1, hinge=1),
        Door("master", "ext", 17.2, 3.2, 1.8, "v", "slide"),
        Door("living", "ext", 19.2, 9.9, 3.0, "v", "slide"),
        Door("living", "ext", 16.4, 13.4, 2.4, "u", "slide"),
    ]
    mw = [Win(2.0, 10.2, 2.0, 11.4), Win(2.6, 13.4, 3.6, 13.4), Win(12.4, 13.4, 13.0, 13.4),
          Win(14.8, 1.1, 16.4, 1.1), Win(10.6, 1.1, 11.6, 1.1), Win(12.6, 1.1, 13.6, 1.1),
          Win(19.2, 11.8, 19.2, 12.9), Win(14.2, 13.4, 15.2, 13.4), Win(19.2, 6.0, 19.2, 8.0),
          Win(4.6, 13.4, 4.8, 13.4)]
    mf = flat(
        rect(2.05, 4.65, 2.5, 7.25, "bench"), rect(3.3, 4.65, 3.75, 7.25, "bench"),
        wf, stair_dogleg(*STAIR, label="UP 24R · DN 22R"), lift_car(*LIFT),
        shower(10.1, 1.2, 12.0, 2.2), wc(10.45, 3.3, "e"), basin(11.65, 3.3, 0.45, 0.4),
        rect(12.15, 1.15, 12.75, 3.55, "bench"), rect(13.35, 1.15, 13.95, 3.55, "bench"),
        bed(14.7, 1.25, 1.8, 2.05, "n"),
        rect(14.1, 1.2, 14.6, 1.75), rect(16.6, 1.2, 17.1, 1.75), armchair(12.3, 4.4, 0.8),
        rect(2.1, 9.6, 2.6, 11.6, "bench"), Shape(Point(3.15, 11.0), "text", "COATS"),
        table_chairs(6.2, 11.45, 1.0, 2.0, 3),
        rect(8.25, 9.55, 8.7, 11.65, "bench"), rect(9.85, 9.55, 10.25, 11.65, "bench"),
        counter(10.3, 9.55, 13.55, 10.15, hob=(12.6, 9.85), fridge=(10.35, 9.55, 11.0, 10.2)),
        counter(12.95, 10.15, 13.55, 13.35, sink=(13.25, 12.0)),
        rect(9.2, 12.0, 11.6, 12.7, "bench"), Shape(Point(10.4, 12.95), "text", "BREAKFAST BAR"),
        sofa_l(19.0, 5.7, 3.4, 3.0, "ne"), coffee(16.5, 6.8, 17.9, 7.7), armchair(14.4, 6.2, 0.8),
        armchair(14.4, 7.3, 0.8), rect(13.65, 5.6, 14.05, 7.2, "bench"),
        sofa(14.6, 12.3, 16.6, 13.1), armchair(18.1, 12.0, 0.85), coffee(15.2, 11.3, 16.1, 11.9),
        table_chairs(17.8, 9.9, 0.9, 0.9, 1, False),
    )
    main = Level("main", "MAIN FLOOR", Z_MAIN, m, md, mw, mf, [
        Terrace("t-ne", "MASTER TERRACE", R(17.2, 1.1, 19.2, 5.4), Z_MAIN - 0.02, label_at=(18.2, 4.3)),
        Terrace("t-south", "SOUTH TERRACE", R(4.2, 13.4, 19.2, 16.4), Z_MAIN - 0.02),
        Terrace("t-east", "EAST TERRACE", R(19.2, 5.4, 22.2, 16.4), Z_MAIN - 0.02),
        Terrace("court-w", "ARRIVAL COURT", Polygon([(0.0, 9.6), (2.0, 9.6), (2.0, 16.4), (4.2, 16.4),
                                                      (4.2, 17.4), (-1.2, 17.4), (-1.2, 11.6), (0.0, 11.6)]), Z_MAIN, "court", label_at=(0.9, 15.0)),
        garden_stair(),
    ], [
        "Owner's C order of rooms, adapted: dining nearest the entrance for guests, kitchen in the middle of the south side, living in the SE.",
        "The kitchen is the heart. Its walk-in pantry opens beside the fridge (fixes I26). The breakfast bar is for daily meals. It is semi-open, with portals to the hall and the dining room, and its slider opens to the south terrace (rules 1.1–1.4).",
        "Living 43 m², 5.5 m wide. The sofa corner is in the NE, closed to the north by the master suite (rule 3.1). It opens to the east and south terraces.",
        "Master suite on the north side with its own private NE terrace on the roof of the lower floor, a terrace facing north-east (rule 4.3). You enter the bedroom from its lobby, and the dressing room and ensuite open off the bedroom (rule 2.5).",
        "The south side is 0.4 m deeper than options 1–2, so the kitchen and dining get 3.9 m depth. The south terrace is 3.0 m deep.",
    ])
    # lower: guest suite NE, lounge along the east, study/play room in the SE (programme pi-study-1 / play)
    lr, ldr, lfr = lower_core(22.2)
    hall_l = Polygon([(8.2, 7.3), (15.5, 7.3), (15.5, 9.4), (17.6, 9.4), (17.6, 11.6), (8.2, 11.6)])
    lo = lr + [
        Room("hall-l", "FAMILY HALL + TEA BAR", "hall", hall_l, label_at=(11.2, 9.9)),
        Room("gens", "SEATED ENSUITE", "wet", R(15.5, 2.8, 17.6, 5.6), small=True, label_at=(16.55, 4.9)),
        Room("guest", "GRANDPARENTS / GUEST", "sleep", R(17.6, 2.8, 22.2, 7.3), label_at=(19.6, 6.2), main=True),
        Room("gvest", "", "hall", R(15.5, 5.6, 17.6, 7.3), show_dims=False),
        Room("lounge", "GARDEN LOUNGE", "day", Polygon([(15.5, 7.3), (22.2, 7.3), (22.2, 11.6), (17.6, 11.6),
                                                        (17.6, 9.4), (15.5, 9.4)]), label_at=(19.8, 9.3), main=True),
        Room("study", "STUDY / PLAY", "study", R(15.4, 11.6, 22.2, 16.4), main=True),
    ]
    ld = ldr + [
        Door("hall-l", "lounge", 16.55, 9.4, 2.0, "u", "open"),
        Door("gvest", "lounge", 16.55, 7.3, 1.2, "u", "open"),
        Door("gvest", "guest", 17.6, 6.45, 0.9, "v", "door", swing=1, hinge=1),
        Door("guest", "gens", 17.6, 4.2, 0.9, "v", "door", swing=-1, hinge=-1),
        Door("hall-l", "study", 16.6, 11.6, 0.9, "u", "door", swing=1, hinge=-1),
        Door("lounge", "ext", 22.2, 9.4, 3.0, "v", "slide"),
        Door("guest", "ext", 22.2, 5.0, 1.0, "v", "glass"),
        Door("study", "ext", 20.4, 16.4, 2.4, "u", "slide"),
    ]
    lw = [Win(7.7, 16.4, 10.0, 16.4), Win(12.0, 16.4, 14.4, 16.4), Win(18.4, 2.8, 21.2, 2.8),
          Win(22.2, 12.6, 22.2, 15.4), Win(16.2, 16.4, 18.4, 16.4)]
    lf = lfr + flat(
        counter(12.6, 7.4, 15.4, 8.0, sink=(13.4, 7.7), fridge=(14.75, 7.4, 15.4, 8.0)),
        Shape(Point(13.9, 8.25), "text", "TEA + SNACK BAR"),
        sofa(9.0, 10.6, 11.6, 11.45), coffee(9.7, 9.7, 11.0, 10.3),
        bed(20.0, 4.6, 1.6, 2.0, "e"), wardrobe(17.7, 2.9, 19.3, 3.5), armchair(18.0, 6.4, 0.8),
        wc(17.25, 3.35, "w"), basin(16.0, 5.2), shower(15.55, 2.85, 16.6, 4.0),
        Shape(Point(16.5, 4.4).buffer(0.75), "dash"),
        sofa_l(21.8, 7.6, 3.4, 2.8, "ne"), coffee(19.4, 8.5, 20.5, 9.4), armchair(18.2, 7.6, 0.8),
        desk(15.5, 12.0, 17.9, 12.7, (16.7, 13.1)), desk(19.5, 12.0, 21.9, 12.7, (20.7, 13.1)),
        rect(15.5, 14.6, 16.1, 16.3, "bench"), Shape(Point(18.8, 14.6), "text", "PLAY · HOMEWORK · GUEST OVERFLOW"),
    )
    lower = Level("lower", "LOWER FLOOR + GARDEN", Z_LOWER, lo, ld, lw, lf, [
        Terrace("t-low", "GARDEN TERRACE", R(22.2, 2.8, 25.2, 16.4), Z_LOWER - 0.02),
        Terrace("walk-s", "", R(6.8, 16.4, 25.2, 17.4), Z_LOWER - 0.15, "court"),
        Terrace("lawn", "EAST LAWN", ENVELOPE.intersection(R(25.2, 0.0, 40.0, 17.4)), 1668.60, "lawn"),
    ], [
        KIDS_NOTE,
        "Grandparents/guest suite NE with a seated, step-free ensuite (fixes I10). The garden lounge sits between it and the family hall.",
        "SE corner is the children's study/play room from the space programme (pi-study-1, play area), with a slider onto the garden. Homework happens next to their bedrooms, not on the main floor.",
        "Family hall with tea/snack bar opens into the east garden lounge (rule 6.6).",
        LAUNDRY_NOTE,
    ])
    return Option(
        "C08-3", "Kitchen-at-the-heart house · from owner's C", "user-designed 0109-r5 Option C",
        "C's day sequence is kept: dining by the entrance, kitchen in the middle, living at the east end. C's road-level living and lower-floor parents break rules 4.3, 5.5 and 6.5, so the day floor stays below the garage and the master suite stays north. The suite gets its own NE terrace.",
        {"road": road_level(), "main": main, "lower": lower}, 1668.60, 25.2,
        [], {"ew_v": 11.0, "ns_u": 11.4},
    )


OPTIONS = [option1, option2, option3]
