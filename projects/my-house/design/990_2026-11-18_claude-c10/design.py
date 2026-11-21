"""C10: one design, fitted to both falls of the field (stmt-026).

Frame as in C08/C09: u = metres east along the north boundary (downhill), v = metres south.
Owner levels kept: road 1677.50, main 1673.60, lower 1670.00.

The ground falls about 35% to the east and about 16% to the south, so a level floor meets the
hill along a diagonal: the 1670.00 contour runs from (16.8, 1.1) on the north side to (10.5, 16.4)
on the south side. C10 keeps C09's structure and places every room by that line:

- lower floor: bedrooms and lounge only where the ground is at or below the floor (south from
  u 8.9, the whole east side); bathroom, laundry, store and stair in the buried north-west;
- the two parts C09 dug for nothing (NW bathroom, riser room) stay in the ground;
- garden: one level play lawn laid along the contour, parallel to the east boundary, at the
  height the hill already has at the house's SE corner; the slope below it stays natural.
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
Z_LAWN = 1667.60  # natural ground at the house's SE corner (18.0, 16.4) is 1667.5
STAIR = (6.8, 1.1, 9.4, 7.3)  # owner's dog-leg with REST 1.40 at north, flights 1.15 m
LIFT = (9.4, 5.0, 11.4, 7.3)  # door on the south face at every level
EAST_MAIN, EAST_LOWER = 17.8, 18.0
BALC = 19.4  # east balcony edge, 1.6 m deep
TERR = 20.6  # garden terrace edge, 2.6 m deep
# The lawn's downhill edge follows the contour: u + 0.448 v = 28.5 (natural ground ≈ 1666.3).
CONTOUR_SLOPE, LAWN_EDGE = 0.448, 28.5


def lawn_edge(v: float) -> float:
    return LAWN_EDGE - CONTOUR_SLOPE * v


def road_level() -> Level:
    rooms = [
        Room("garage", "GARAGE · 2 CARS + WORKBENCH", "garage", R(0.0, 1.1, 6.8, 9.5), label_at=(2.9, 5.3)),
        Room("stair-r", "STAIR 24R", "stair", R(*STAIR), show_dims=False),
        Room("lift-r", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("lobby-r", "CORE LOBBY", "hall", R(6.8, 7.3, 11.4, 9.5), label_at=(9.9, 8.75), show_dims=False, small=True),
        Room("hall-r", "ENTRANCE HALL", "hall", R(0.0, 9.5, 9.0, 11.6), label_at=(4.8, 10.9)),
        Room("office", "QUIET OFFICE", "study", R(9.0, 9.5, 12.2, 12.6), label_at=(10.7, 11.5)),
        Room("wc-r", "WC + SHOWER", "wet", R(7.0, 11.6, 9.0, 13.3), small=True),
        Room("plant", "PLANT + TANKS", "service", R(3.4, 11.6, 7.0, 13.3), small=True, label_at=(5.9, 12.75)),
    ]
    doors = [
        Door("garage", "ext", 0.0, 3.25, 3.35, "v", "shutter"),
        Door("garage", "ext", 0.0, 7.35, 3.35, "v", "shutter"),
        Door("hall-r", "ext", 0.0, 10.75, 1.2, "v", "door", swing=1, hinge=-1),
        Door("garage", "lobby-r", 6.8, 8.4, 1.0, "v", "door", swing=1, hinge=1),
        Door("lobby-r", "stair-r", 8.1, 7.3, 2.6, "u", "open"),
        Door("lobby-r", "lift-r", 10.4, 7.3, 1.0, "u", "glass"),
        Door("hall-r", "lobby-r", 7.9, 9.5, 2.2, "u", "open"),
        Door("lobby-r", "ext", 11.4, 8.4, 1.4, "v", "glass"),
        Door("hall-r", "office", 9.0, 10.5, 0.9, "v", "door", swing=1, hinge=-1),
        Door("hall-r", "wc-r", 8.0, 11.6, 0.8, "u", "door", swing=1, hinge=1),
        Door("hall-r", "plant", 4.4, 11.6, 1.2, "u", "door", swing=-1, hinge=-1),
        Door("office", "ext", 12.2, 11.2, 1.6, "v", "slide"),
    ]
    windows = [Win(9.5, 12.6, 11.7, 12.6)]
    furniture = flat(
        car(0.35, 2.2, 5.0, 2.0, "LC300"), car(0.35, 6.4, 4.8, 1.95, "CAR 2"),
        rect(6.15, 1.5, 6.75, 6.2, "bench"), Shape(Point(5.6, 4.75), "text", "WORKBENCH →"),
        rect(5.4, 7.0, 6.75, 7.8, "dash"), Shape(Point(6.05, 7.4), "text", "BIKES"),
        lockers(0.6, 9.55, 4.2, 10.0, 6), Shape(Point(2.4, 10.25), "text", "6 LOCKERS"),
        stair_dogleg(*STAIR, label="DOWN 24R"), lift_car(*LIFT),
        desk(10.2, 9.6, 12.1, 10.25, (11.1, 10.65)), armchair(9.3, 11.6, 0.75),
        wc(8.55, 12.75, "w"), basin(7.35, 12.0, 0.45, 0.4), Shape(R(7.1, 12.45, 8.0, 13.25), "fixture"),
        rect(5.4, 11.75, 6.9, 12.3, "bench"), rect(3.5, 12.6, 4.6, 13.2, "bench"),
    )
    terraces = [
        Terrace("deck-r", "ROOF TERRACE", Polygon([(11.4, 7.3), (12.2, 7.3), (12.2, 6.2), (EAST_MAIN, 6.2), (EAST_MAIN, 13.0),
                                                    (12.2, 13.0), (12.2, 9.5), (11.4, 9.5)]), Z_ROAD - 0.05, "deck",
                label_at=(15.1, 9.8)),
        Terrace("green-r", "GREEN ROOF", Polygon([(9.4, 1.1), (EAST_MAIN, 1.1), (EAST_MAIN, 6.2), (12.2, 6.2), (12.2, 7.3),
                                                   (11.4, 7.3), (11.4, 5.0), (9.4, 5.0)]), Z_ROAD - 0.05, "green",
                label_at=(14.6, 3.6), note="over the master suite · no access"),
        Terrace("fore", "FORECOURT", Polygon([(0.0, 1.1), (0.0, 11.6), (-6.3, 11.6), (-0.6, 1.1)]).intersection(PARCEL),
                1677.40, "court", label_at=(-2.6, 8.0)),
    ]
    notes = [
        "Front door on the west façade, straight into the entrance hall. At its end the stair and lift are on your left, and a glass door ahead shows the view over the roof terrace.",
        "Groceries: garage → one door → core lobby → lift is 4 m, all indoors (rule 5.1).",
        "Two 3.35 m shutters and 4.2 m wide bays, so every car door opens fully. Workbench along the back wall (rule 5.5).",
        "New in C10: the roof terrace is reached from the lobby, so the family uses it without crossing the office. The roof over the master bedroom is planted and closed, so nobody walks above the bed.",
        "Office in the quiet SE corner with its own door to the terrace; WC and shower beside it.",
    ]
    return Level("road", "ROAD LEVEL", Z_ROAD, rooms, doors, windows, furniture, terraces, notes)


def wet_cluster(u0: float, v0: float):
    """Owner's 4-part screened wet and wudu cluster."""
    rooms = [
        Room("wc-m", "WC", "wet", R(u0, v0, u0 + 1.5, v0 + 2.1), small=True, show_dims=False),
        Room("sh-m", "SHOWER", "wet", R(u0 + 1.5, v0, u0 + 3.0, v0 + 2.1), small=True, show_dims=False),
        Room("wudu", "WUDU", "wet", R(u0, v0 + 2.1, u0 + 1.5, 7.3), small=True, show_dims=False, label_at=(u0 + 0.95, 6.6)),
        Room("wlob", "LOBBY", "wet", R(u0 + 1.5, v0 + 2.1, u0 + 3.0, 7.3), small=True, show_dims=False, label_at=(u0 + 2.25, 6.3)),
    ]
    doors = [
        Door("hall", "wlob", u0 + 2.25, 7.3, 0.9, "u", "open"),
        Door("wlob", "wudu", u0 + 1.5, v0 + 3.5, 1.2, "v", "open"),
        Door("wudu", "wc-m", u0 + 0.85, v0 + 2.1, 0.75, "u", "door", swing=-1, hinge=1),
        Door("wlob", "sh-m", u0 + 2.25, v0 + 2.1, 0.75, "u", "door", swing=-1, hinge=1),
    ]
    furn = flat(
        wc(u0 + 0.5, v0 + 0.55, "s"), basin(u0 + 1.2, v0 + 0.35, 0.4, 0.32),
        shower(u0 + 1.6, v0 + 0.08, u0 + 2.92, v0 + 1.1),
        rect(u0 + 0.05, v0 + 2.5, u0 + 0.45, 7.2, "bench"),
        Shape(LineString([(u0 + 1.55, v0 + 2.6), (u0 + 2.4, v0 + 2.6)]), "baffle"),
    )
    return rooms, doors, furn


def main_level() -> Level:
    wr, wd, wf = wet_cluster(3.8, 2.8)
    rooms = [
        Room("pantry", "PANTRY", "service", R(2.0, 4.6, 3.8, 7.3), small=True, label_at=(2.9, 5.75)),
        *wr,
        Room("stair-m", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-m", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("ens", "ENSUITE", "wet", R(9.4, 1.1, 11.4, 5.0), small=True, label_at=(10.4, 3.9)),
        Room("dress", "DRESSING", "service", R(11.4, 1.1, 13.2, 5.0), small=True, label_at=(12.35, 2.6)),
        Room("mlob", "", "hall", R(11.4, 5.0, 12.6, 7.3), show_dims=False),
        Room("master", "MASTER BEDROOM", "sleep",
             Polygon([(13.2, 1.1), (EAST_MAIN, 1.1), (EAST_MAIN, 6.2), (12.6, 6.2), (12.6, 5.0), (13.2, 5.0)]),
             label_at=(15.9, 4.3), main=True),
        Room("hall", "FAMILY HALL", "hall", R(2.0, 7.3, 12.6, 9.5), label_at=(8.6, 8.45)),
        Room("entry", "ENTRY", "hall", R(2.0, 9.5, 4.6, 13.0), small=True, label_at=(3.5, 10.6)),
        Room("kitchen", "KITCHEN", "kitchen", R(4.6, 9.5, 9.2, 13.0), main=True, label_at=(7.3, 11.95)),
        Room("dining", "DINING 6–8", "day", R(9.2, 9.5, 12.6, 13.0), main=True, label_at=(10.9, 12.45)),
        Room("living", "LIVING", "day", R(12.6, 6.2, EAST_MAIN, 13.0), label_at=(15.1, 9.9), main=True),
    ]
    doors = wd + [
        Door("entry", "ext", 2.0, 12.15, 1.2, "v", "door", swing=1, hinge=1),
        Door("hall", "entry", 3.3, 9.5, 2.6, "u", "open"),
        Door("hall", "pantry", 2.9, 7.3, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("hall", "stair-m", 8.1, 7.3, 2.6, "u", "open"),
        Door("hall", "lift-m", 10.4, 7.3, 1.0, "u", "glass"),
        Door("hall", "kitchen", 6.4, 9.5, 1.1, "u", "open"),
        Door("hall", "dining", 10.9, 9.5, 3.0, "u", "open"),
        Door("kitchen", "dining", 9.2, 10.3, 1.1, "v", "open"),
        Door("dining", "living", 12.6, 11.4, 3.0, "v", "open"),
        Door("kitchen", "ext", 8.1, 13.0, 1.6, "u", "slide"),
        Door("dining", "ext", 10.9, 13.0, 2.0, "u", "slide"),
        Door("hall", "living", 12.6, 8.4, 1.6, "v", "open"),
        Door("hall", "mlob", 12.0, 7.3, 1.0, "u", "open"),
        Door("mlob", "master", 12.6, 5.6, 0.9, "v", "door", swing=1, hinge=-1),
        Door("master", "dress", 13.2, 4.5, 0.8, "v", "door", swing=-1, hinge=1),
        Door("dress", "ens", 11.4, 4.3, 0.8, "v", "door", swing=-1, hinge=1),
        Door("master", "ext", EAST_MAIN, 3.4, 2.4, "v", "slide"),
        Door("living", "ext", EAST_MAIN, 10.4, 2.8, "v", "slide"),
        Door("living", "ext", 13.8, 13.0, 2.0, "u", "slide"),
    ]
    windows = [
        Win(5.0, 13.0, 6.9, 13.0), Win(2.0, 9.9, 2.0, 11.2), Win(3.0, 13.0, 4.0, 13.0),
        Win(10.0, 1.1, 10.9, 1.1), Win(11.9, 1.1, 12.8, 1.1), Win(14.4, 1.1, 17.0, 1.1), Win(EAST_MAIN, 5.0, EAST_MAIN, 5.8),
        Win(EAST_MAIN, 6.7, EAST_MAIN, 8.6), Win(EAST_MAIN, 12.1, EAST_MAIN, 12.7), Win(15.2, 13.0, 17.3, 13.0),
    ]
    furn = flat(
        rect(2.05, 4.65, 2.4, 6.3, "bench"), rect(3.4, 4.65, 3.75, 7.25, "bench"), rect(2.4, 4.65, 3.4, 5.0, "bench"), wf,
        stair_dogleg(*STAIR, label="UP 24R · DN 22R"), lift_car(*LIFT),
        # master suite
        shower(9.5, 1.2, 11.3, 2.2), wc(10.95, 2.95, "w"), basin(9.75, 3.2, 0.5, 0.42), basin(9.75, 4.0, 0.5, 0.42),
        wardrobe(11.45, 1.15, 13.15, 1.75), wardrobe(11.45, 1.8, 12.05, 3.7), rect(12.8, 1.8, 13.15, 3.9, "bench"),
        bed(13.25, 1.75, 1.8, 2.05, "w"), rect(13.25, 1.2, 13.7, 1.7), rect(13.25, 3.6, 13.7, 4.05),
        rect(13.7, 5.7, 17.3, 6.15, "bench"), Shape(Point(15.5, 5.45), "text", "BOOKSHELF WALL"),
        armchair(16.8, 1.35, 0.75),
        # kitchen
        counter(4.65, 9.55, 5.25, 12.35, hob=(4.95, 11.3), fridge=(4.65, 9.55, 5.3, 10.25)),
        counter(4.65, 12.35, 7.1, 12.95, sink=(6.0, 12.65)),
        rect(6.4, 10.5, 8.4, 11.35, "bench"), Shape(Point(7.4, 10.93), "text", "ISLAND"),
        *[Shape(Point(u, 10.2).buffer(0.19)) for u in (6.8, 7.4, 8.0)],
        table_chairs(10.9, 11.0, 1.9, 0.95, 3, ends=False),
        # living
        sofa_l(17.6, 6.45, 3.3, 2.3, "ne"), coffee(15.0, 7.8, 16.2, 8.6), armchair(13.9, 9.1, 0.8),
        rect(12.65, 6.4, 13.05, 7.5, "bench"), Shape(Point(13.3, 6.95), "text", "TV"),
        mats(15.35, 11.5, 2, "s"), Shape(Point(16.2, 11.25), "text", "PRAYER · READING"),
        rect(2.1, 9.9, 2.6, 11.4, "bench"), Shape(Point(3.5, 11.6), "text", "COATS · SHOES"),
        # terraces
        table_chairs(8.1, 14.9, 1.6, 0.9, 2, ends=False), rect(14.2, 15.2, 16.1, 15.9), rect(16.3, 14.0, 17.0, 15.9),
        table_chairs(18.5, 7.9, 0.7, 0.7, 1, ends=False),
    )
    terraces = [
        Terrace("t-south", "SOUTH TERRACE", R(4.6, 13.0, EAST_MAIN, 16.4), Z_MAIN - 0.02, label_at=(11.5, 15.4)),
        Terrace("balc-e", "EAST BALCONY", R(EAST_MAIN, 6.2, BALC, 16.4), Z_MAIN - 0.02, label_at=(20.9, 10.6)),
        Terrace("balc-m", "MASTER BALCONY", R(EAST_MAIN, 1.1, BALC, 6.2), Z_MAIN - 0.02, label_at=(21.2, 3.4)),
        Terrace("court-w", "ARRIVAL COURT", Polygon([(0.0, 9.6), (2.0, 9.6), (2.0, 13.0), (4.6, 13.0), (4.6, 17.4),
                                                      (-1.2, 17.4), (-1.2, 11.6), (0.0, 11.6)]), Z_MAIN, "court",
                label_at=(1.6, 15.2)),
        Terrace("gstair", "STAIR FROM THE ROAD · 22R", R(-2.4, 11.6, -1.2, 17.4), Z_ROAD - 0.1, "stair",
                label_at=(-5.2, 14.6), z_end=Z_MAIN, run="v+"),
    ]
    notes = [
        "Kitchen on the south with a 1.6 m slider onto the south terrace and the sink under a south window (rules 1.1, 1.2). Two doorless openings, walls to the ceiling (1.3).",
        "Kitchen, dining and living each open off the family hall. Nobody crosses one main room to reach another (2.1).",
        "Living 5.1 × 6.7 m: the sofa corner is in the NE, closed to the north by the master's bookshelf wall, TV on the west wall, prayer and reading corner by the south window (3.1, 3.3).",
        "New in C10: the master bedroom takes the NE corner with morning sun, the bed facing the view, and its own balcony. Hall → small lobby → bedroom; dressing room and ensuite lie beyond the bedroom (2.5).",
        "New in C10: the east balcony is 1.6 m deep and wraps the SE corner to join the south terrace: 65 m² of main-floor terrace in total, most of it on the roof of the floor below (4.3).",
        "Pantry and the wudu/WC cluster use the buried NW, where no window is possible. They need mechanical ventilation.",
    ]
    return Level("main", "MAIN FLOOR", Z_MAIN, rooms, doors, windows, furn, terraces, notes)


def lower_level() -> Level:
    lawn = Polygon([(TERR, 0.6), (lawn_edge(0.6), 0.6), (lawn_edge(17.42), 17.42), (EAST_LOWER, 17.42), (EAST_LOWER, 16.4),
                    (19.2, 16.4), (19.2, 11.6), (TERR, 11.6)]).intersection(ENVELOPE)
    bank = ENVELOPE.intersection(Polygon([(lawn_edge(0.0), 0.0), (40.0, 0.0), (40.0, 17.42), (lawn_edge(17.42), 17.42)]))
    rooms = [
        Room("stair-l", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-l", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("wc-l", "WC", "wet", R(5.0, 7.3, 6.7, 8.4), small=True, show_dims=False),
        Room("sh-l", "SHOWER", "wet", R(5.0, 8.4, 6.7, 9.6), small=True, show_dims=False),
        Room("lav", "BASINS", "wet", R(6.7, 7.3, 8.2, 9.6), small=True, show_dims=False, label_at=(7.45, 8.9)),
        Room("laundry", "LAUNDRY · DRYING · STORE", "service",
             Polygon([(5.0, 9.6), (8.2, 9.6), (8.2, 11.6), (6.8, 11.6), (6.8, 16.4), (5.0, 16.4)]), label_at=(6.6, 10.9), small=True),
        Room("hall-l", "FAMILY HALL", "hall", R(8.2, 7.3, 12.6, 11.6), label_at=(10.4, 10.75)),
        Room("boys", "BOYS", "sleep", R(6.8, 11.6, 11.1, 16.4), main=True, label_at=(8.95, 14.3)),
        Room("girls", "GIRLS", "sleep", R(11.1, 11.6, 15.4, 16.4), main=True, label_at=(13.25, 14.3)),
        Room("gens", "SEATED ENSUITE", "wet", R(11.4, 2.8, 14.2, 5.2), small=True, label_at=(12.6, 4.6)),
        Room("guest", "GRANDPARENTS", "sleep",
             Polygon([(11.4, 5.2), (14.2, 5.2), (14.2, 2.8), (EAST_LOWER, 2.8), (EAST_LOWER, 7.3), (11.4, 7.3)]),
             label_at=(16.1, 6.0), main=True),
        Room("lounge", "GARDEN LOUNGE + TEA BAR", "day", R(12.6, 7.3, EAST_LOWER, 11.6), label_at=(15.3, 9.35), main=True),
    ]
    doors = [
        Door("hall-l", "stair-l", 8.8, 7.3, 1.2, "u", "open"),
        Door("hall-l", "lift-l", 10.4, 7.3, 1.0, "u", "glass"),
        Door("hall-l", "lav", 8.2, 8.45, 1.0, "v", "open"),
        Door("lav", "wc-l", 6.7, 7.85, 0.75, "v", "door", swing=-1, hinge=1),
        Door("lav", "sh-l", 6.7, 9.0, 0.75, "v", "door", swing=1, hinge=1),
        Door("hall-l", "laundry", 8.2, 10.6, 0.9, "v", "door", swing=-1, hinge=1),
        Door("hall-l", "boys", 10.55, 11.6, 0.9, "u", "door", swing=1, hinge=1),
        Door("hall-l", "girls", 11.8, 11.6, 0.9, "u", "door", swing=1, hinge=-1),
        Door("hall-l", "guest", 12.0, 7.3, 1.0, "u", "door", swing=-1, hinge=-1),
        Door("guest", "gens", 12.8, 5.2, 0.9, "u", "door", swing=1, hinge=1),
        Door("hall-l", "lounge", 12.6, 9.2, 2.2, "v", "open"),
        Door("lounge", "ext", EAST_LOWER, 9.45, 3.0, "v", "slide"),
        Door("lounge", "ext", 16.7, 11.6, 2.2, "u", "slide"),
        Door("guest", "ext", EAST_LOWER, 5.6, 1.6, "v", "slide"),
    ]
    windows = [Win(8.9, 16.4, 10.9, 16.4), Win(11.6, 16.4, 14.9, 16.4), Win(16.0, 2.8, 17.6, 2.8), Win(EAST_LOWER, 3.2, EAST_LOWER, 4.2)]
    furn = flat(
        stair_dogleg(*STAIR, label="UP 22R"), lift_car(*LIFT),
        wc(5.45, 7.85, "e"), shower(5.1, 8.5, 6.1, 9.5), basin(7.35, 7.55, 0.5, 0.4), basin(7.92, 7.55, 0.5, 0.4),
        rect(5.05, 9.7, 5.7, 11.5, "bench"), Shape(Point(5.37, 10.2).buffer(0.25), "fixture"), Shape(Point(5.37, 10.95).buffer(0.25), "fixture"),
        rect(5.05, 11.7, 5.5, 16.3, "bench"), rect(6.3, 12.2, 6.75, 16.3, "bench"),
        Shape(LineString([(5.9, 9.8), (7.2, 9.8)]), "dash"), Shape(Point(5.9, 14.4), "text", "STORE"),
        Shape(Point(10.4, 9.35).buffer(0.6)), *[Shape(Point(10.4 + du, 9.35 + dv).buffer(0.2)) for du, dv in ((-0.95, 0), (0.95, 0), (0, -0.95), (0, 0.95))],
        Shape(Point(10.4, 8.1), "text", "HOMEWORK · GAMES"),
        # boys and girls: owner's 4.3 × 4.8 m rooms, two beds, two desks, two wardrobes each
        bed(6.9, 15.25, 1.0, 2.05, "w", 1), bed(8.95, 15.25, 1.0, 2.05, "e", 1),
        desk(6.9, 13.0, 7.5, 14.4, (7.85, 13.7)), desk(10.45, 13.0, 11.05, 14.4, (10.1, 13.7)),
        wardrobe(6.9, 11.7, 8.4, 12.3), wardrobe(8.45, 11.7, 9.9, 12.3),
        bed(11.2, 15.25, 1.0, 2.05, "w", 1), bed(13.25, 15.25, 1.0, 2.05, "e", 1),
        desk(11.2, 13.0, 11.8, 14.4, (12.15, 13.7)), desk(14.75, 13.0, 15.35, 14.4, (14.4, 13.7)),
        wardrobe(12.6, 11.7, 13.95, 12.3), wardrobe(14.0, 11.7, 15.35, 12.3),
        # grandparents
        bed(15.2, 2.95, 1.8, 2.0, "n"), rect(14.7, 2.9, 15.15, 3.35), rect(17.05, 2.9, 17.5, 3.35),
        wardrobe(12.7, 6.65, 14.2, 7.25), wardrobe(14.25, 6.65, 15.8, 7.25), armchair(16.6, 6.3, 0.8),
        wc(13.75, 3.4, "w"), basin(11.75, 4.75, 0.5, 0.42), shower(11.5, 2.9, 12.7, 4.0), Shape(Point(13.1, 4.1).buffer(0.75), "dash"),
        # lounge
        counter(12.7, 7.4, 15.2, 8.0, sink=(13.4, 7.7), fridge=(14.6, 7.4, 15.2, 8.0)), Shape(Point(13.95, 8.25), "text", "TEA BAR"),
        rect(15.6, 7.4, 17.6, 7.75, "bench"), Shape(Point(16.6, 8.0), "text", "TV"),
        sofa(12.9, 10.7, 15.3, 11.5), coffee(13.6, 9.6, 14.7, 10.2), armchair(15.8, 9.6, 0.8),
        table_chairs(16.7, 14.3, 0.9, 1.5, 2, ends=False),
    )
    terraces = [
        Terrace("loggia", "LOGGIA", R(15.4, 11.6, EAST_LOWER, 16.4), Z_LOWER - 0.02, label_at=(16.7, 12.45),
                note="12 m² · covered"),
        Terrace("t-low", "GARDEN TERRACE", Polygon([(EAST_LOWER, 2.8), (TERR, 2.8), (TERR, 11.6), (19.2, 11.6), (19.2, 12.8),
                                                     (EAST_LOWER, 12.8)]), Z_LOWER - 0.02, "paved", label_at=(19.3, 4.6)),
        Terrace("gs-lawn", "14 STEPS", R(EAST_LOWER, 12.8, 19.2, 16.4), Z_LOWER - 0.02, "stair", label_at=(18.6, 14.6),
                z_end=Z_LAWN, run="v+"),
        Terrace("lawn", "PLAY LAWN", lawn, Z_LAWN, "lawn", label_at=(23.9, 4.4)),
        Terrace("bank", "TREE BANK", bank, 1666.0, "bank", label_at=(27.9, 5.9), note="natural slope, planted"),
        Terrace("gs-court", "", R(4.6, 16.4, 6.6, 17.4), Z_MAIN, "stair", z_end=1671.30, run="u+"),
        Terrace("path-s", "GARDEN PATH", R(6.6, 16.4, EAST_LOWER, 17.4), 1669.0, "path", label_at=(10.5, 18.0),
                note="steps on the natural slope, court → lawn"),
    ]
    notes = [
        "New in C10: the boys' and girls' rooms sit 1.8 m further east than in C09. Their south windows now look out over the ground. In C09 the boys' wall was buried up to 2 m and faced a dug trench.",
        "Both rooms keep your 4.3 × 4.8 m, with two beds, two desks and two wardrobes each (rule 6.7).",
        "New in C10: the buried NW corner is not dug out. WC, shower and twin basins open off the family hall instead of the stair foot; laundry, drying and the household store share one room beside them.",
        "Grandparents' room in the NE: 2 m from the lift, own step-free ensuite with a seated shower, own door to the garden terrace. Door from the hall straight into the room; no vestibule.",
        "Garden lounge with tea bar opens east to the terrace and south to a covered loggia. The family hall gets its daylight through the 2.2 m opening to the lounge.",
        "Garden: terrace and loggia at floor level, 14 steps down to one level play lawn at 1667.60, laid along the contour. Below it the slope stays natural and carries the trees.",
    ]
    return Level("lower", "LOWER FLOOR + GARDEN", Z_LOWER, rooms, doors, windows, furn, terraces, notes)


def option() -> Option:
    return Option(
        "C10", "One design, fitted to both falls of the field", "C09-1 and C09-2 (owner's 0109-r5), reworked on the terrain",
        "The house steps down the hill in three floors and turns every bedroom and living room to the south and east, "
        "where the ground falls away. Service rooms fill the buried north-west.",
        {"road": road_level(), "main": main_level(), "lower": lower_level()},
        Z_LAWN, TERR, [],
        {"ew": [(10.4, "through the kitchen, living room and lounge"),
                (4.2, "through the garage, stair and bedrooms")],
         "ns": [(8.6, "through the stair, kitchen and boys' room"),
                (16.6, "through the living room and loggia")]},
    )
