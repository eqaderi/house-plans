"""C09: compact versions of C08 so the house fits the field and leaves an east garden (stmt-023/024).

Frame as in C08 (u east along the north boundary, v south). Owner levels kept.
Targets: lower floor ends at u = 18.0, ~150 m² east garden, deepest cut <= ~4.5 m,
living ~34 m² (>= 5.0 m wide) with the dining open into it.
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
STAIR = (6.8, 1.1, 9.4, 7.3)  # owner's dog-leg with REST 1.40 at north, flights 1.15 m
LIFT = (9.4, 5.0, 11.4, 7.3)  # door on the south face at every level
EAST_MAIN, EAST_LOWER = 17.8, 18.0


def road_level() -> Level:
    rooms = [
        Room("garage", "GARAGE · 2 CARS + WORKBENCH", "garage", R(0.0, 1.1, 6.8, 9.5)),
        Room("stair-r", "STAIR 24R", "stair", R(*STAIR), show_dims=False),
        Room("lift-r", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("lobby-r", "CORE LOBBY", "hall", R(6.8, 7.3, 11.4, 9.5), label_at=(10.2, 8.4), show_dims=False, small=True),
        Room("hall-r", "ENTRANCE HALL", "hall", R(0.0, 9.5, 9.0, 11.6), label_at=(4.8, 10.75)),
        Room("office", "QUIET OFFICE", "study", R(9.0, 9.5, 12.2, 12.6)),
        Room("wc-r", "WC + SHOWER", "wet", R(7.0, 11.6, 9.0, 13.3), small=True),
        Room("plant", "PLANT + TANKS", "service", R(3.4, 11.6, 7.0, 13.3), small=True),
    ]
    doors = [
        Door("garage", "ext", 0.0, 3.25, 3.35, "v", "shutter"),
        Door("garage", "ext", 0.0, 7.35, 3.35, "v", "shutter"),
        Door("hall-r", "ext", 0.0, 10.55, 1.2, "v", "door", swing=1, hinge=-1),
        Door("garage", "lobby-r", 6.8, 8.4, 1.0, "v", "door", swing=1, hinge=1),
        Door("lobby-r", "stair-r", 8.1, 7.3, 2.6, "u", "open"),
        Door("lobby-r", "lift-r", 10.4, 7.3, 1.0, "u", "glass"),
        Door("hall-r", "lobby-r", 7.9, 9.5, 2.2, "u", "open"),
        Door("hall-r", "office", 9.0, 10.5, 0.9, "v", "door", swing=1, hinge=-1),
        Door("hall-r", "wc-r", 8.0, 11.6, 0.8, "u", "door", swing=1, hinge=1),
        Door("hall-r", "plant", 5.2, 11.6, 1.2, "u", "door", swing=1, hinge=-1),
        Door("office", "ext", 12.2, 11.0, 1.6, "v", "slide"),
    ]
    windows = [Win(12.2, 9.8, 12.2, 10.1), Win(9.5, 12.6, 11.7, 12.6)]
    furniture = flat(
        car(0.35, 1.8, 5.0, 2.0, "LC300"), car(0.35, 6.4, 4.8, 1.95, "CAR 2"),
        rect(6.15, 1.5, 6.75, 6.2, "bench"), Shape(Point(5.6, 3.9), "text", "WORKBENCH"),
        rect(5.4, 7.0, 6.75, 9.45, "dash"), Shape(Point(6.05, 8.25), "text", "BIKES"),
        lockers(0.6, 9.55, 4.2, 10.1, 6), Shape(Point(2.4, 10.35), "text", "6 LOCKERS"),
        stair_dogleg(*STAIR, label="LANDING"), lift_car(*LIFT),
        desk(9.6, 9.6, 12.1, 10.3, (10.8, 10.7)), armchair(9.2, 11.6, 0.8),
        wc(8.55, 12.05, "w"), basin(7.4, 12.0), Shape(R(7.1, 12.4, 8.0, 13.25), "fixture"),
        rect(3.6, 11.75, 4.7, 13.2, "bench"), Shape(Point(5.8, 12.45), "text", "BOILER · PUMPS · TANKS"),
    )
    terraces = [
        Terrace("deck-r", "OFFICE ROOF DECK", R(12.2, 7.3, EAST_MAIN, 13.0), Z_ROAD - 0.05, "deck"),
        Terrace("fore", "FORECOURT", Polygon([(0.0, 1.1), (0.0, 11.6), (-6.3, 11.6), (-0.6, 1.1)]).intersection(PARCEL),
                1677.40, "court", label_at=(-2.6, 8.0)),
    ]
    notes = [
        "Front door on the west façade opens into a straight entrance hall. The stair and lift face it from the core lobby.",
        "Groceries: garage → fire door → core lobby → lift is 4 m, all indoors (rule 5.1).",
        "Two 3.35 m shutters; 4.2 m wide bays, so every car door opens fully. Workbench and bike wall at the back (rule 5.5).",
        "Plant room is off the entrance hall; modules go out through the 1.2 m front door. Office looks east over the roof deck.",
    ]
    return Level("road", "ROAD LEVEL", Z_ROAD, rooms, doors, windows, furniture, terraces, notes)


def wet_cluster(u0: float, v0: float):
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


def main_level(variant: str) -> Level:
    """Shared day floor: K | D+L on the south, master on the north. `variant` sets the master suite."""
    wr, wd, wf = wet_cluster(3.8, 2.8)
    rooms = [
        Room("pantry", "PANTRY", "service", R(2.0, 4.6, 3.8, 7.3), small=True),
        *wr,
        Room("stair-m", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-m", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("ens", "ENSUITE", "wet", R(9.4, 1.1, 11.4, 3.4), small=True),
        Room("dress", "DRESS", "service", R(9.4, 3.4, 11.4, 5.0), small=True),
        Room("mlob", "", "hall", R(11.4, 5.4, 12.6, 7.3), show_dims=False),
        Room("hall", "FAMILY HALL", "hall", R(2.0, 7.3, 12.6, 9.5), label_at=(7.6, 8.45)),
        Room("entry", "ENTRY", "hall", R(2.0, 9.5, 4.6, 13.0), small=True),
        Room("kitchen", "KITCHEN", "kitchen", R(4.6, 9.5, 9.2, 13.0), main=True),
        Room("dining", "DINING 6–8", "day", R(9.2, 9.5, 12.6, 13.0), main=True),
        Room("living", "LIVING", "day", R(12.6, 6.2, EAST_MAIN, 13.0), label_at=(15.3, 9.6), main=True),
    ]
    doors = wd + [
        Door("entry", "ext", 2.0, 12.15, 1.2, "v", "door", swing=1, hinge=1),
        Door("hall", "entry", 3.3, 9.5, 2.6, "u", "open"),
        Door("hall", "pantry", 2.9, 7.3, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("hall", "stair-m", 8.1, 7.3, 2.6, "u", "open"),
        Door("hall", "lift-m", 10.4, 7.3, 1.0, "u", "glass"),
        Door("hall", "kitchen", 5.4, 9.5, 1.1, "u", "open"),
        Door("hall", "dining", 10.9, 9.5, 3.0, "u", "open"),
        Door("kitchen", "dining", 9.2, 10.3, 1.1, "v", "open"),
        Door("dining", "living", 12.6, 11.4, 3.0, "v", "open"),
        Door("kitchen", "ext", 8.1, 13.0, 1.6, "u", "slide"),
        Door("dining", "ext", 10.9, 13.0, 2.0, "u", "slide"),
        Door("hall", "living", 12.6, 8.4, 1.6, "v", "open"),
        Door("hall", "mlob", 12.0, 7.3, 0.9, "u", "door", swing=-1, hinge=-1),
        Door("master", "dress", 11.4, 4.2, 0.8, "v", "door", swing=-1, hinge=1),
        Door("master", "ens", 11.4, 2.3, 0.8, "v", "door", swing=-1, hinge=-1),
        Door("living", "ext", EAST_MAIN, 9.6, 3.0, "v", "slide"),
        Door("living", "ext", 15.6, 13.0, 2.4, "u", "slide"),
    ]
    windows = [Win(5.0, 13.0, 6.8, 13.0), Win(2.0, 9.9, 2.0, 11.2), Win(3.0, 13.0, 4.0, 13.0),
               Win(10.0, 1.1, 10.9, 1.1), Win(EAST_MAIN, 6.6, EAST_MAIN, 7.8), Win(EAST_MAIN, 11.6, EAST_MAIN, 12.6),
               Win(13.0, 13.0, 14.2, 13.0)]
    furn = flat(
        rect(2.05, 4.65, 2.5, 7.25, "bench"), rect(3.3, 4.65, 3.75, 7.25, "bench"), wf,
        stair_dogleg(*STAIR, label="UP 24R · DN 22R"), lift_car(*LIFT),
        shower(9.5, 1.2, 10.6, 2.2), wc(11.0, 1.6, "w"), basin(10.9, 2.9, 0.45, 0.38),
        rect(9.45, 3.45, 11.35, 3.95, "bench"),
        counter(4.65, 9.55, 5.25, 12.95, hob=(4.95, 11.6), fridge=(4.65, 9.55, 5.3, 10.25)),
        counter(5.25, 12.35, 9.1, 12.95, sink=(6.0, 12.65)),
        rect(6.3, 10.5, 8.4, 11.3, "bench"), Shape(Point(7.35, 10.15), "text", "ISLAND · DAILY MEALS"),
        table_chairs(10.9, 11.25, 1.9, 0.95, 3),
        sofa_l(17.6, 6.5, 3.3, 2.9, "ne"), coffee(15.3, 7.6, 16.6, 8.5), armchair(13.3, 6.6, 0.8),
        rect(12.65, 6.4, 13.05, 7.9, "bench", ""), sofa(13.6, 12.0, 15.4, 12.8), armchair(16.5, 11.8, 0.85),
        rect(2.1, 9.6, 2.6, 11.4, "bench"), Shape(Point(3.4, 10.5), "text", "COATS · SHOES"),
    )
    terraces = [
        Terrace("t-south", "SOUTH TERRACE", R(4.6, 13.0, EAST_MAIN, 16.4), Z_MAIN - 0.02),
        Terrace("balc-e", "EAST BALCONY", R(EAST_MAIN, 6.6, EAST_MAIN + 1.4, 12.6), Z_MAIN - 0.02, label_at=(18.5, 9.6)),
        Terrace("court-w", "ARRIVAL COURT", Polygon([(0.0, 9.6), (2.0, 9.6), (2.0, 16.4), (4.6, 16.4), (4.6, 17.4),
                                                      (-1.2, 17.4), (-1.2, 11.6), (0.0, 11.6)]), Z_MAIN, "court",
                label_at=(0.9, 15.0)),
        Terrace("gstair", "GARDEN STAIR 22R", Polygon([(-2.4, 11.6), (-1.2, 11.6), (-1.2, 17.4), (-2.4, 17.4)]),
                Z_ROAD - 0.1, "stair", label_at=(-4.2, 14.6)),
    ]
    if variant == "terrace":
        rooms += [Room("master", "MASTER BEDROOM", "sleep",
                       Polygon([(11.4, 1.1), (15.6, 1.1), (15.6, 6.2), (12.6, 6.2), (12.6, 5.4), (11.4, 5.4)]),
                       label_at=(13.5, 3.4), main=True)]
        doors += [Door("mlob", "master", 12.0, 5.4, 0.9, "u", "door", swing=-1, hinge=1),
                  Door("master", "ext", 15.6, 3.4, 1.8, "v", "slide")]
        windows += [Win(12.0, 1.1, 15.0, 1.1)]
        furn += flat(bed(12.6, 1.25, 1.8, 2.05, "n"), rect(12.0, 1.2, 12.5, 1.75), rect(14.5, 1.2, 15.0, 1.75),
                     armchair(14.6, 4.6, 0.8))
        terraces += [Terrace("t-ne", "MASTER TERRACE", R(15.6, 1.1, EAST_MAIN, 6.2), Z_MAIN - 0.02, label_at=(16.7, 4.6))]
        notes = [
            "Master bedroom on the quiet north side (rule 6.5), with its own NE terrace and morning sun. Lobby from the hall; the dressing room and ensuite open off the bedroom (rule 2.5).",
        ]
    else:
        rooms = [r for r in rooms if r.id not in ("ens", "dress")]
        doors = [d for d in doors if not (d.a == "master" and d.b in ("ens", "dress"))]
        rooms += [Room("ens", "ENSUITE", "wet", R(9.4, 1.1, 11.4, 5.0), small=True),
                  Room("dress", "WALK-IN DRESS", "service", R(11.4, 1.1, 13.6, 5.4), small=True),
                  Room("master", "MASTER BEDROOM", "sleep",
                       Polygon([(13.6, 1.1), (EAST_MAIN, 1.1), (EAST_MAIN, 6.2), (12.6, 6.2), (12.6, 5.4), (13.6, 5.4)]),
                       label_at=(15.7, 4.0), main=True)]
        doors += [Door("mlob", "master", 12.6, 5.8, 0.75, "v", "door", swing=1, hinge=-1),
                  Door("master", "dress", 13.6, 3.0, 0.8, "v", "door", swing=-1, hinge=-1),
                  Door("dress", "ens", 11.4, 2.4, 0.8, "v", "door", swing=-1, hinge=1)]
        windows += [Win(14.4, 1.1, 17.0, 1.1), Win(EAST_MAIN, 1.8, EAST_MAIN, 4.8)]
        furn = [f for f in furn if not (f.geom.bounds[0] >= 9.4 and f.geom.bounds[2] <= 11.4 and f.geom.bounds[3] <= 5.0)]
        furn += flat(shower(9.5, 1.2, 11.3, 2.2), wc(10.9, 3.0, "w"), basin(9.85, 3.6, 0.45, 0.38), basin(9.85, 4.4, 0.45, 0.38),
                     rect(11.45, 1.15, 13.55, 1.75, "bench"), rect(13.0, 2.0, 13.55, 4.8, "bench"),
                     bed(15.6, 1.8, 1.8, 2.05, "e"), rect(17.2, 1.25, 17.75, 1.75), rect(17.2, 3.95, 17.75, 4.45),
                     armchair(14.0, 4.2, 0.8))
        notes = [
            "Master bedroom takes the NE corner with east and north light (rule 6.5). Hall → its own lobby → bedroom; the walk-in dressing room and the ensuite lie beyond the bedroom (rule 2.5: never through the closet to the bedroom).",
            "Pray in the living room's quiet NE corner or the master suite. There is no separate prayer room; the wudu stays in the 4-part cluster by the entrance.",
        ]
    notes = [
        "Arrival: open-sky SW court → west door → entry → family hall, with the stair and lift in front (rule 2.6, two turns: your earlier decision).",
        "Kitchen 15 m² on the south with island and slider to the south terrace (rules 1.1, 1.3). Dining sits between kitchen and living and opens 3 m wide into the living (stmt-024).",
        "Living 35 m², 5.2 × 6.8 m, sofa corner in the NE closed to the north, east balcony over the garden (rules 3.1, 3.3).",
    ] + notes
    return Level("main", "MAIN FLOOR", Z_MAIN, rooms, doors, windows, furn, terraces, notes)


def lower_level(variant: str) -> Level:
    """Lower floor u 5.0–18.0. `variant`: 'guest-ne' (lounge E) or 'lounge-ne' (guest E)."""
    rooms = [
        Room("bath-l", "FAMILY BATH", "wet", R(5.0, 2.8, 6.8, 7.3), small=True),
        Room("stair-l", "STAIR", "stair", R(*STAIR), show_dims=False),
        Room("lift-l", "LIFT", "lift", R(*LIFT), show_dims=False, small=True),
        Room("riser", "RISERS", "service", R(9.4, 2.8, 11.4, 5.0), small=True, show_dims=False),
        Room("laundry", "LAUNDRY + STORE", "service", R(5.0, 7.3, 8.2, 11.6)),
        Room("hall-l", "FAMILY HALL", "hall", R(8.2, 7.3, 12.6, 11.6), label_at=(10.4, 9.6)),
        Room("boys", "BOYS", "sleep", R(5.0, 11.6, 9.3, 16.4), main=True),
        Room("girls", "GIRLS", "sleep", R(9.3, 11.6, 13.6, 16.4), main=True),
    ]
    doors = [
        Door("hall-l", "stair-l", 8.8, 7.3, 1.2, "u", "open"),
        Door("hall-l", "lift-l", 10.4, 7.3, 1.0, "u", "glass"),
        Door("stair-l", "bath-l", 6.8, 6.55, 0.8, "v", "door", swing=-1, hinge=1),
        Door("hall-l", "laundry", 8.2, 8.4, 1.0, "v", "door", swing=-1, hinge=-1),
        Door("hall-l", "boys", 8.75, 11.6, 0.9, "u", "door", swing=1, hinge=-1),
        Door("hall-l", "girls", 10.4, 11.6, 0.9, "u", "door", swing=1, hinge=1),
    ]
    windows = [Win(5.6, 16.4, 8.6, 16.4), Win(10.0, 16.4, 13.0, 16.4)]
    furn = flat(
        shower(5.1, 2.9, 6.7, 3.9), wc(5.45, 4.6, "e"), basin(6.45, 5.6, 0.4, 0.5), basin(6.45, 6.3, 0.4, 0.5),
        stair_dogleg(*STAIR, label="UP 22R"), lift_car(*LIFT),
        rect(5.05, 7.35, 5.7, 11.55, "bench"), rect(7.55, 9.4, 8.15, 11.55, "bench"),
        Shape(Point(5.37, 7.95).buffer(0.25), "fixture"), Shape(Point(5.37, 8.65).buffer(0.25), "fixture"),
        Shape(LineString([(6.0, 11.1), (7.3, 11.1)]), "dash"), Shape(Point(6.6, 9.6), "text", "FOLD · DRY · STORE"),
        sofa(8.9, 10.75, 11.0, 11.5), armchair(11.6, 9.9, 0.8),
        bed(5.1, 15.0, 1.0, 2.1, "w", 1), bed(7.15, 15.0, 1.0, 2.1, "e", 1),
        bed(9.4, 15.0, 1.0, 2.1, "w", 1), bed(11.45, 15.0, 1.0, 2.1, "e", 1),
        desk(5.1, 13.0, 5.7, 14.4, (6.05, 13.7)), desk(8.65, 13.0, 9.25, 14.4, (8.3, 13.7)),
        desk(9.4, 13.0, 10.0, 14.4, (10.35, 13.7)), desk(12.95, 13.0, 13.55, 14.4, (12.6, 13.7)),
        wardrobe(5.1, 11.7, 6.6, 12.3), wardrobe(6.7, 11.7, 8.1, 12.3),
        wardrobe(11.0, 11.7, 12.3, 12.3), wardrobe(12.35, 11.7, 13.55, 12.3),
    )
    ge = Polygon([(11.4, 2.8), (14.2, 2.8), (14.2, 5.2), (11.4, 5.2)])
    if variant == "guest-ne":
        rooms += [
            Room("gens", "SEATED ENSUITE", "wet", ge, small=True),
            Room("gvest", "", "hall", R(11.4, 5.2, 14.2, 7.3), show_dims=False),
            Room("guest", "GRANDPARENTS", "sleep", R(14.2, 2.8, EAST_LOWER, 7.3), main=True),
            Room("lounge", "GARDEN LOUNGE + TEA BAR", "day", R(12.6, 7.3, EAST_LOWER, 11.6), label_at=(15.5, 9.9), main=True),
        ]
        doors += [
            Door("hall-l", "gvest", 12.0, 7.3, 0.9, "u", "open"),
            Door("gvest", "guest", 14.2, 6.3, 0.9, "v", "door", swing=1, hinge=1),
            Door("guest", "gens", 14.2, 4.0, 0.9, "v", "door", swing=-1, hinge=-1),
            Door("hall-l", "lounge", 12.6, 9.6, 2.6, "v", "open"),
            Door("lounge", "ext", EAST_LOWER, 9.4, 3.0, "v", "slide"),
            Door("lounge", "ext", 15.8, 11.6, 2.4, "u", "slide"),
            Door("guest", "ext", EAST_LOWER, 5.0, 1.0, "v", "glass"),
        ]
        windows += [Win(15.0, 2.8, 17.4, 2.8)]
        furn += flat(
            bed(15.9, 3.9, 1.6, 2.0, "e"), wardrobe(14.3, 2.9, 15.8, 3.5), armchair(14.5, 6.2, 0.8),
            wc(13.75, 3.4, "w"), basin(12.1, 4.75), shower(11.5, 2.9, 12.6, 4.0), Shape(Point(13.0, 4.0).buffer(0.75), "dash"),
            counter(12.7, 7.4, 15.2, 8.0, sink=(13.4, 7.7), fridge=(14.6, 7.4, 15.2, 8.0)),
            sofa_l(17.8, 8.3, 3.0, 2.6, "ne"), coffee(15.6, 9.1, 16.6, 9.9), armchair(14.2, 9.6, 0.8),
        )
        notes = [
            "Grandparents' room in the quiet NE garden corner, with its own seated, step-free ensuite (I10). Lift 3 m away.",
            "Garden lounge with tea/snack bar (rule 6.6) opens east to the garden and south onto the sunny SE terrace.",
        ]
    else:
        rooms += [
            Room("lounge", "GARDEN LOUNGE + TEA BAR", "day", R(11.4, 2.8, EAST_LOWER, 7.3), label_at=(15.4, 5.8), main=True),
            Room("gens", "SEATED ENSUITE", "wet", R(12.6, 7.3, 14.6, 9.9), small=True),
            Room("gvest", "", "hall", R(12.6, 9.9, 14.6, 11.6), show_dims=False),
            Room("guest", "GRANDPARENTS", "sleep", R(14.6, 7.3, EAST_LOWER, 11.6), main=True),
        ]
        doors += [
            Door("hall-l", "lounge", 12.0, 7.3, 1.2, "u", "open"),
            Door("hall-l", "gvest", 12.6, 10.75, 1.2, "v", "open"),
            Door("gvest", "guest", 14.6, 10.75, 0.9, "v", "door", swing=1, hinge=1),
            Door("guest", "gens", 14.6, 8.6, 0.9, "v", "door", swing=-1, hinge=-1),
            Door("lounge", "ext", EAST_LOWER, 5.0, 3.0, "v", "slide"),
            Door("guest", "ext", EAST_LOWER, 9.4, 1.6, "v", "slide"),
        ]
        windows += [Win(12.4, 2.8, 17.0, 2.8)]
        furn += flat(
            counter(11.5, 2.9, 14.0, 3.5, sink=(12.3, 3.2), fridge=(13.4, 2.9, 14.0, 3.5)),
            sofa_l(17.8, 3.1, 3.0, 2.8, "ne"), coffee(15.5, 4.1, 16.6, 5.0), armchair(14.2, 4.6, 0.8),
            table_chairs(13.0, 5.6, 1.4, 0.8, 2),
            bed(16.0, 8.4, 1.6, 2.0, "e"), wardrobe(14.7, 7.4, 16.0, 8.0), armchair(14.9, 10.6, 0.8),
            wc(14.15, 7.9, "w"), basin(13.0, 9.5), shower(12.7, 7.4, 13.6, 8.4), Shape(Point(13.6, 8.8).buffer(0.75), "dash"),
        )
        notes = [
            "Garden lounge with tea/snack bar fills the NE (rule 6.6), north light plus the east garden. The hall opens straight into it.",
            "Grandparents' room faces the east garden, with its own seated, step-free ensuite (I10). Lift 4 m away.",
        ]
    terraces = [
        Terrace("t-se", "SE GARDEN TERRACE", R(13.6, 11.6, EAST_LOWER, 16.4), Z_LOWER - 0.02),
        Terrace("t-low", "GARDEN TERRACE", R(EAST_LOWER, 2.8, 20.4, 16.4), Z_LOWER - 0.02, label_at=(19.2, 13.8)),
        Terrace("light-s", "", R(5.0, 16.4, 13.6, 17.4), Z_LOWER - 0.15, "court"),
        Terrace("lawn", "UPPER LAWN", ENVELOPE.intersection(R(20.4, 0.0, 25.0, 17.4)), 1668.60, "lawn"),
        Terrace("lawn2", "LOWER LAWN", ENVELOPE.intersection(R(25.0, 0.0, 40.0, 17.4)), 1667.30, "lawn"),
    ]
    notes = [
        "Children's rooms keep your 4.3 × 4.8 m along the south (2 beds, 2 desks, 2 wardrobes). A 1 m dug light-strip outside the boys' window.",
        "Family bathroom (WC, shower, two basins) for the children sits in the buried NW, off the stair landing: one bathroom per floor (rule 6.1). Laundry with store beside the core (rules 6.3, I12).",
    ] + notes + [
        "Garden: paved terrace at 1669.98, then two lawns at 1668.60 and 1667.30 following the hill. About 150 m² east of the house, plus the SE terrace.",
    ]
    return Level("lower", "LOWER FLOOR + GARDEN", Z_LOWER, rooms, doors, windows, furn, terraces, notes)


def option1() -> Option:
    return Option(
        "C09-1", "Compact family-hall house · terrace master", "C08-1 (owner's B) shrunk to the field",
        "C08-1's plan pulled in to u 18. Kitchen, dining and living run along the south, with the dining open into a 35 m² living room. "
        "The master bedroom is mid-north with its own NE terrace. Downstairs, the grandparents' suite is NE and the garden lounge east.",
        {"road": road_level(), "main": main_level("terrace"), "lower": lower_level("guest-ne")},
        1668.60, 20.4, [], {"ew_v": 10.6, "ns_u": 15.0},
    )


def option2() -> Option:
    return Option(
        "C09-2", "Compact reading-room house · corner master", "C08-2 (owner's A) shrunk to the field",
        "The same compact day floor. The master bedroom takes the NE corner, and a quiet prayer/reading room (from your A and B) sits beside it. "
        "Downstairs the garden lounge takes the NE and the grandparents' room faces the east garden.",
        {"road": road_level(), "main": main_level("corner"), "lower": lower_level("lounge-ne")},
        1668.60, 20.4, [], {"ew_v": 9.0, "ns_u": 15.0},
    )


OPTIONS = [option1, option2]
