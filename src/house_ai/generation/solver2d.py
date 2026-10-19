"""Two-dimensional room placement engine using CP-SAT NoOverlap2D.

Places rooms freely in 2D (u and v on the design grid) without requiring
rigid 1D double-loaded corridor bars. Enforces topology constraints
(shared wall length >= SHARED_WALL_MIN_M for doors), corridor-free / compact
circulation, open-plan living arrangements, L-shaped and multi-wing massings,
courtyard enclosures, multi-level floor organisations with alternative stair
cores, privacy-driven zoning, and single-threaded determinism.
"""

from __future__ import annotations

import math
import platform
import time
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from house_ai.constants.placement2d import (
    COURTYARD_NAME,
    COURTYARD_SPACE_ID,
    L_SHAPE_MIN_RECESS_DM,
    LEVEL_ENTRY,
    LEVEL_LOWER,
    LEVEL_UPPER,
    MAX_ASPECT_RATIO,
    MIN_ROOM_DIMENSION_M,
    OPEN_PLAN_SHARED_WALL_MIN_M,
    STAIR_CORE_DEFAULT_DEPTH_DM,
    STAIR_CORE_DEFAULT_WIDTH_DM,
    STAIR_CORE_RISERS,
    STAIR_CORE_SPACE_ID_ENTRY,
    STAIR_CORE_SPACE_ID_UPPER,
    ZONE_FAMILY,
    ZONE_GUEST,
    ZONE_OUTDOOR,
    ZONE_PUBLIC,
)
from house_ai.constants.proposals import (
    STAIR_CORE_CENTRAL,
    STAIR_CORE_ENTRY,
    STAIR_CORE_PERIMETER,
    STAIR_CORE_REAR,
)
from house_ai.constants.relations import (
    SHARED_WALL_MIN_M,
)
from house_ai.constants.strategies import (
    STRATEGY_CORRIDOR_FREE,
    STRATEGY_COURTYARD,
    STRATEGY_OPEN_PLAN,
    STRATEGY_TWO_WING,
)
from house_ai.domain.base import EXTERIOR
from house_ai.domain.program import (
    AdjacencyKind,
    AdjacencyRequirement,
    ProgramZone,
    SpaceFunction,
    SpaceProgram,
    Strength,
)
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.site import Site
from house_ai.generation.frame import DesignFrame
from house_ai.generation.rooms import garage_dims_dm, space_id_for
from house_ai.generation.solver import SolverOptions
from house_ai.generation.stairs import u_core_fits

SHARED_WALL_MIN_DM = int(round(SHARED_WALL_MIN_M * 10))
OPEN_PLAN_WALL_MIN_DM = int(round(OPEN_PLAN_SHARED_WALL_MIN_M * 10))
MIN_ROOM_DIM_DM = int(round(MIN_ROOM_DIMENSION_M * 10))

W_COMPACTNESS = 10
W_AREA_DEV = 5
W_ADJACENCY_SOFT = 300
W_NEAR_SOFT = 150
W_DAYLIGHT_SOFT = 250
W_ROAD_FACING_SOFT = 200
W_ZONE_CLUSTER = 40
W_STAIR_CENTRAL = 20

OPEN_PLAN_FUNCTIONS = {
    SpaceFunction.LIVING,
    SpaceFunction.DINING,
    SpaceFunction.KITCHEN,
}


class Solve2DFailed(Exception):
    """The 2D placement solver could not find a feasible layout."""


@dataclass
class PlacementRoom:
    space_id: str
    name: str
    function: SpaceFunction
    item_id: str
    zone_id: str
    level_pref: str
    target_area_m2: float
    min_area_m2: float | None = None
    min_width_m: float | None = None
    daylight_required: bool = False
    accessible: bool = False
    priority_weight: int = 1
    max_area_m2: float | None = None
    #: Longer side (dm) the room needs: a garage's car length (S10-19).
    min_long_dm: int | None = None

    @property
    def target_area_dm2(self) -> int:
        return int(round(self.target_area_m2 * 100))

    @property
    def min_dim_dm(self) -> int:
        req = self.min_width_m or 0.0
        return max(MIN_ROOM_DIM_DM, int(math.ceil(req * 10 - 1e-9)))


@dataclass
class PlacedRoom2D:
    space_id: str
    name: str
    function: SpaceFunction
    level_id: str
    u0: int  # dm
    v0: int  # dm
    u1: int  # dm
    v1: int  # dm
    program_item_id: str
    zone_id: str
    sub_rects: list[tuple[int, int, int, int]] | None = None

    @property
    def width_dm(self) -> int:
        return self.u1 - self.u0

    @property
    def depth_dm(self) -> int:
        return self.v1 - self.v0

    @property
    def area_m2(self) -> float:
        if self.sub_rects:
            dm2 = sum((sr[2] - sr[0]) * (sr[3] - sr[1]) for sr in self.sub_rects)
            return dm2 / 100.0
        return (self.width_dm * self.depth_dm) / 100.0


@dataclass
class SharedWall:
    room_a: str
    room_b: str
    level_id: str
    orientation: str  # "h" (constant v) or "v" (constant u)
    coord_dm: int
    span_start_dm: int
    span_end_dm: int
    door_candidate: bool = True

    @property
    def length_dm(self) -> int:
        return self.span_end_dm - self.span_start_dm

    @property
    def length_m(self) -> float:
        return self.length_dm / 10.0


@dataclass
class Solution2D:
    status: str
    objective: float
    rooms: list[PlacedRoom2D]
    shared_walls: list[SharedWall]
    circulation_rooms: list[PlacedRoom2D]
    levels: list[str]
    deterministic_time: float
    wall_time_s: float
    seed: int
    platform_info: str
    strategy: str
    circulation_share: float
    has_courtyard: bool = False
    has_stairs: bool = False
    zone_definitions: list[ProgramZone] = field(default_factory=list)
    exterior_connections: list[str] = field(default_factory=list)
    optimised_objectives: list[str] = field(default_factory=list)


def compute_candidate_dimensions(
    r: PlacementRoom, max_w_dm: int, max_h_dm: int
) -> list[tuple[int, int]]:
    """Only return tuples satisfying every active bound; never relax a hard minimum."""
    pairs = []
    if r.space_id == COURTYARD_SPACE_ID:
        pairs = [(30, 30), (30, 40), (40, 30), (40, 40), (30, 50), (50, 30)]
    elif r.function is SpaceFunction.STAIR:
        w, h = STAIR_CORE_DEFAULT_WIDTH_DM, STAIR_CORE_DEFAULT_DEPTH_DM
        pairs = [(w, h), (h, w)]
    if r.space_id != COURTYARD_SPACE_ID:
        target = max(r.target_area_dm2, math.ceil((r.min_area_m2 or 0) * 100))
        lo = max(math.ceil((r.min_area_m2 or 0) * 100 - 1e-8), math.ceil(target * 0.85))
        hi = min(
            math.floor((r.max_area_m2 or float("inf")) * 100)
            if r.max_area_m2
            else max_w_dm * max_h_dm,
            math.floor(target * 1.25),
        )
        for w in range(r.min_dim_dm, max_w_dm + 1, 2):
            h0 = max(r.min_dim_dm, math.ceil(lo / w))
            h1 = min(max_h_dm, hi // w)
            for h in range(h0, h1 + 1, 2):
                if max(w / h, h / w) <= MAX_ASPECT_RATIO:
                    pairs.append((w, h))
    if r.min_long_dm is not None:
        pairs = [(w, h) for w, h in pairs if max(w, h) >= r.min_long_dm]
    if r.function is SpaceFunction.STAIR:
        # A core must hold its U-shaped flight (S10-06, ADR 0023): 16 risers per storey.
        pairs = [
            (w, h)
            for w, h in pairs
            if u_core_fits(min(w, h), max(w, h), STAIR_CORE_RISERS)
        ]
    pairs = [
        (w, h)
        for w, h in pairs
        if w <= max_w_dm
        and h <= max_h_dm
        and w >= r.min_dim_dm
        and h >= r.min_dim_dm
        and w * h >= math.ceil((r.min_area_m2 or 0) * 100 - 1e-8)
        and (r.max_area_m2 is None or w * h <= r.max_area_m2 * 100 + 1e-8)
    ]
    if not pairs:
        raise Solve2DFailed(f"no dimensions for {r.space_id} within envelope and hard bounds")
    return pairs


def extract_placement_rooms(
    program: SpaceProgram,
    min_areas: dict[str, float] | None = None,
    min_widths: dict[str, float] | None = None,
) -> list[PlacementRoom]:
    """Expand every program instance with the same IDs used by revisions/evaluation."""
    rooms = []
    garage_depth, garage_width = garage_dims_dm(program)
    for item in program.items:
        is_garage = item.function is SpaceFunction.GARAGE
        for index in range(1, item.quantity + 1):
            minimum = max(item.min_area_m2 or 0, (min_areas or {}).get(item.id, 0))
            if is_garage:
                # Sized for the program's cars, as in the bar path (S10-19).
                minimum = max(minimum, garage_depth * garage_width / 100)
            rooms.append(
                PlacementRoom(
                    space_id=space_id_for(item, index),
                    name=item.name if item.quantity == 1 else f"{item.name} {index}",
                    function=item.function,
                    item_id=item.id,
                    zone_id=item.zone_id or "z-general",
                    level_pref=item.level_preference or "entry",
                    target_area_m2=max(item.target_area_m2 or minimum or 10, minimum),
                    min_area_m2=minimum or None,
                    min_width_m=max(
                        item.min_width_m or 0,
                        (min_widths or {}).get(item.id, 0),
                        garage_width / 10 if is_garage else 0,
                    )
                    or None,
                    min_long_dm=garage_depth if is_garage else None,
                    max_area_m2=item.max_area_m2,
                    daylight_required=item.daylight.value == "required",
                    accessible=item.accessible,
                    priority_weight=3 if item.priority.value == "must" else 1,
                )
            )
    return rooms


def _partition_wings(
    rooms: list[PlacementRoom],
) -> tuple[list[PlacementRoom], list[PlacementRoom]]:
    """Partition rooms into Day wing (Wing A) and Night wing (Wing B)."""
    wing_a: list[PlacementRoom] = []
    wing_b: list[PlacementRoom] = []
    day_functions = {
        SpaceFunction.ENTRY,
        SpaceFunction.LIVING,
        SpaceFunction.DINING,
        SpaceFunction.KITCHEN,
        SpaceFunction.TERRACE,
        SpaceFunction.GARAGE,
        SpaceFunction.HALL,
    }
    for r in rooms:
        if r.function in day_functions or r.zone_id in (ZONE_PUBLIC, "z-day", "z-living"):
            wing_a.append(r)
        else:
            wing_b.append(r)

    if not wing_a:
        mid = max(1, len(rooms) // 2)
        wing_a, wing_b = rooms[:mid], rooms[mid:]
    elif not wing_b:
        mid = max(1, len(wing_a) // 2)
        wing_b = wing_a[mid:]
        wing_a = wing_a[:mid]

    return wing_a, wing_b


def _apply_two_wing_constraints(
    md: cp_model.CpModel,
    rooms: list[PlacementRoom],
    x_vars: dict[str, cp_model.IntVar],
    y_vars: dict[str, cp_model.IntVar],
    xe_vars: dict[str, cp_model.IntVar],
    ye_vars: dict[str, cp_model.IntVar],
    touch_vars: dict[tuple[str, str], cp_model.BoolVar],
    env_w_dm: int,
    env_h_dm: int,
) -> None:
    """Enforce two-wing L-shaped layout with free wing positioning (S7-14)."""
    wing_a, wing_b = _partition_wings(rooms)

    xa_min = md.NewIntVar(0, env_w_dm, "xa_min")
    xa_max = md.NewIntVar(0, env_w_dm, "xa_max")
    ya_min = md.NewIntVar(0, env_h_dm, "ya_min")
    ya_max = md.NewIntVar(0, env_h_dm, "ya_max")

    xb_min = md.NewIntVar(0, env_w_dm, "xb_min")
    xb_max = md.NewIntVar(0, env_w_dm, "xb_max")
    yb_min = md.NewIntVar(0, env_h_dm, "yb_min")
    yb_max = md.NewIntVar(0, env_h_dm, "yb_max")

    if not wing_a or not wing_b:
        raise Solve2DFailed("two-wing layout needs rooms in both wings")
    for group, x0, x1, y0, y1 in [
        (wing_a, xa_min, xa_max, ya_min, ya_max),
        (wing_b, xb_min, xb_max, yb_min, yb_max),
    ]:
        md.AddMinEquality(x0, [x_vars[r.space_id] for r in group])
        md.AddMaxEquality(x1, [xe_vars[r.space_id] for r in group])
        md.AddMinEquality(y0, [y_vars[r.space_id] for r in group])
        md.AddMaxEquality(y1, [ye_vars[r.space_id] for r in group])

    # Wings are connected at a junction: at least one shared wall between wings
    wing_touches: list[cp_model.BoolVar] = []
    for ra in wing_a:
        for rb in wing_b:
            pair = (min(ra.space_id, rb.space_id), max(ra.space_id, rb.space_id))
            if pair in touch_vars:
                wing_touches.append(touch_vars[pair])
    if wing_touches:
        md.Add(sum(wing_touches) >= 1)

    # L-shaped re-entrant recess: wings have free relative positions, but do not degenerate
    # into a single rectangular solid. One wing extends past the other in X and/or Y.
    bx_diff = md.NewBoolVar("bx_diff")
    by_diff = md.NewBoolVar("by_diff")
    md.Add(xa_max >= xb_max + L_SHAPE_MIN_RECESS_DM).OnlyEnforceIf(bx_diff)
    md.Add(xb_max >= xa_max + L_SHAPE_MIN_RECESS_DM).OnlyEnforceIf(bx_diff.Not())
    md.Add(ya_max >= yb_max + L_SHAPE_MIN_RECESS_DM).OnlyEnforceIf(by_diff)
    md.Add(yb_max >= ya_max + L_SHAPE_MIN_RECESS_DM).OnlyEnforceIf(by_diff.Not())
    md.Add(bx_diff + by_diff == 1)


def _apply_courtyard_constraints(
    md: cp_model.CpModel,
    court_id: str,
    interior_rooms: list[PlacementRoom],
    touch_details: dict[tuple[str, str], dict[str, cp_model.BoolVar]],
) -> None:
    """Enforce central courtyard enclosure on at least 3 sides (S7-15)."""
    t_north_list: list[cp_model.BoolVar] = []
    t_south_list: list[cp_model.BoolVar] = []
    t_east_list: list[cp_model.BoolVar] = []
    t_west_list: list[cp_model.BoolVar] = []

    for r in interior_rooms:
        sa = r.space_id
        k = (min(sa, court_id), max(sa, court_id))
        if k in touch_details:
            dirs = touch_details[k]
            if sa < court_id:
                t_west_list.append(dirs["east"])
                t_east_list.append(dirs["west"])
                t_south_list.append(dirs["north"])
                t_north_list.append(dirs["south"])
            else:
                t_east_list.append(dirs["east"])
                t_west_list.append(dirs["west"])
                t_north_list.append(dirs["north"])
                t_south_list.append(dirs["south"])

    has_n = md.NewBoolVar("court_has_n")
    has_s = md.NewBoolVar("court_has_s")
    has_e = md.NewBoolVar("court_has_e")
    has_w = md.NewBoolVar("court_has_w")

    if t_north_list:
        md.Add(sum(t_north_list) >= 1).OnlyEnforceIf(has_n)
        md.Add(sum(t_north_list) == 0).OnlyEnforceIf(has_n.Not())
    else:
        md.Add(has_n == 0)

    if t_south_list:
        md.Add(sum(t_south_list) >= 1).OnlyEnforceIf(has_s)
        md.Add(sum(t_south_list) == 0).OnlyEnforceIf(has_s.Not())
    else:
        md.Add(has_s == 0)

    if t_east_list:
        md.Add(sum(t_east_list) >= 1).OnlyEnforceIf(has_e)
        md.Add(sum(t_east_list) == 0).OnlyEnforceIf(has_e.Not())
    else:
        md.Add(has_e == 0)

    if t_west_list:
        md.Add(sum(t_west_list) >= 1).OnlyEnforceIf(has_w)
        md.Add(sum(t_west_list) == 0).OnlyEnforceIf(has_w.Not())
    else:
        md.Add(has_w == 0)

    # Courtyard enclosed on >= 3 sides (e.g. U-shape or 4-side courtyard)
    md.Add(has_n + has_s + has_e + has_w >= 3)


def _apply_stair_constraints(
    md: cp_model.CpModel,
    proposal: ConceptProposal | None,
    entry_r: PlacementRoom | None,
    x_vars: dict[str, cp_model.IntVar],
    y_vars: dict[str, cp_model.IntVar],
    xe_vars: dict[str, cp_model.IntVar],
    ye_vars: dict[str, cp_model.IntVar],
    touch_vars: dict[tuple[str, str], cp_model.BoolVar],
    max_x: cp_model.IntVar,
    max_y: cp_model.IntVar,
    rooms: list[PlacementRoom],
    obj_terms: list[cp_model.LinearExpr],
    env_w_dm: int,
    env_h_dm: int,
    opts: SolverOptions | None = None,
) -> None:
    """Enforce stair vertical alignment and target placement input (S7-16)."""
    # Vertical alignment across levels
    md.Add(x_vars[STAIR_CORE_SPACE_ID_ENTRY] == x_vars[STAIR_CORE_SPACE_ID_UPPER])
    md.Add(y_vars[STAIR_CORE_SPACE_ID_ENTRY] == y_vars[STAIR_CORE_SPACE_ID_UPPER])
    md.Add(xe_vars[STAIR_CORE_SPACE_ID_ENTRY] == xe_vars[STAIR_CORE_SPACE_ID_UPPER])
    md.Add(ye_vars[STAIR_CORE_SPACE_ID_ENTRY] == ye_vars[STAIR_CORE_SPACE_ID_UPPER])

    pos = STAIR_CORE_CENTRAL
    if opts and opts.stair_position:
        pos = opts.stair_position
    elif proposal and proposal.stair_cores:
        pos = proposal.stair_cores[0].position

    if pos == STAIR_CORE_ENTRY and entry_r:
        pair = (
            min(STAIR_CORE_SPACE_ID_ENTRY, entry_r.space_id),
            max(STAIR_CORE_SPACE_ID_ENTRY, entry_r.space_id),
        )
        if pair in touch_vars:
            md.Add(touch_vars[pair] == 1)
    elif pos == STAIR_CORE_PERIMETER:
        b_l = md.NewBoolVar("st_l")
        b_r = md.NewBoolVar("st_r")
        b_b = md.NewBoolVar("st_b")
        b_t = md.NewBoolVar("st_t")
        md.Add(x_vars[STAIR_CORE_SPACE_ID_ENTRY] == 0).OnlyEnforceIf(b_l)
        md.Add(xe_vars[STAIR_CORE_SPACE_ID_ENTRY] == max_x).OnlyEnforceIf(b_r)
        md.Add(y_vars[STAIR_CORE_SPACE_ID_ENTRY] == 0).OnlyEnforceIf(b_b)
        md.Add(ye_vars[STAIR_CORE_SPACE_ID_ENTRY] == max_y).OnlyEnforceIf(b_t)
        md.Add(b_l + b_r + b_b + b_t >= 1)
    elif pos == STAIR_CORE_REAR:
        md.Add(ye_vars[STAIR_CORE_SPACE_ID_ENTRY] == max_y)
    else:
        # STAIR_CORE_CENTRAL: pull stair towards center of plan
        stair_x = x_vars[STAIR_CORE_SPACE_ID_ENTRY]
        stair_y = y_vars[STAIR_CORE_SPACE_ID_ENTRY]
        for r in rooms:
            if r.space_id in (STAIR_CORE_SPACE_ID_ENTRY, STAIR_CORE_SPACE_ID_UPPER):
                continue
            dx = md.NewIntVar(0, env_w_dm, f"dx_st_{r.space_id}")
            dy = md.NewIntVar(0, env_h_dm, f"dy_st_{r.space_id}")
            md.Add(dx >= x_vars[r.space_id] - stair_x)
            md.Add(dx >= stair_x - x_vars[r.space_id])
            md.Add(dy >= y_vars[r.space_id] - stair_y)
            md.Add(dy >= stair_y - y_vars[r.space_id])
            obj_terms.append(W_STAIR_CENTRAL * (dx + dy))


def _apply_zoning_objectives(
    md: cp_model.CpModel,
    rooms: list[PlacementRoom],
    x_vars: dict[str, cp_model.IntVar],
    y_vars: dict[str, cp_model.IntVar],
    xe_vars: dict[str, cp_model.IntVar],
    ye_vars: dict[str, cp_model.IntVar],
    obj_terms: list[cp_model.LinearExpr],
    env_w_dm: int,
    env_h_dm: int,
) -> None:
    """Add intra-zone compactness objectives for privacy-driven zoning (S7-17)."""
    by_zone: dict[str, list[PlacementRoom]] = {}
    for r in rooms:
        by_zone.setdefault(r.zone_id, []).append(r)

    for zid, zrooms in by_zone.items():
        if len(zrooms) >= 2:
            zx_min = md.NewIntVar(0, env_w_dm, f"zx_min_{zid}")
            zx_max = md.NewIntVar(0, env_w_dm, f"zx_max_{zid}")
            zy_min = md.NewIntVar(0, env_h_dm, f"zy_min_{zid}")
            zy_max = md.NewIntVar(0, env_h_dm, f"zy_max_{zid}")
            for r in zrooms:
                md.Add(x_vars[r.space_id] >= zx_min)
                md.Add(xe_vars[r.space_id] <= zx_max)
                md.Add(y_vars[r.space_id] >= zy_min)
                md.Add(ye_vars[r.space_id] <= zy_max)
            obj_terms.append(W_ZONE_CLUSTER * ((zx_max - zx_min) + (zy_max - zy_min)))


def is_privacy_separated(ra: PlacementRoom, rb: PlacementRoom) -> bool:
    """Returns True if a direct door between ra and rb is prohibited for privacy (S7-17)."""
    is_guest_a = ra.zone_id == ZONE_GUEST or ra.function is SpaceFunction.GUEST_SUITE
    is_guest_b = rb.zone_id == ZONE_GUEST or rb.function is SpaceFunction.GUEST_SUITE

    is_fam_a = (
        ra.zone_id == ZONE_FAMILY or ra.function is SpaceFunction.BEDROOM
    ) and not is_guest_a
    is_fam_b = (
        rb.zone_id == ZONE_FAMILY or rb.function is SpaceFunction.BEDROOM
    ) and not is_guest_b

    is_pub_a = ra.zone_id == ZONE_PUBLIC or ra.function in (
        SpaceFunction.LIVING,
        SpaceFunction.DINING,
    )
    is_pub_b = rb.zone_id == ZONE_PUBLIC or rb.function in (
        SpaceFunction.LIVING,
        SpaceFunction.DINING,
    )

    # Family bedroom cannot directly open into public living/dining room
    if (is_fam_a and is_pub_b) or (is_fam_b and is_pub_a):
        return True
    # Family bedroom cannot directly open into guest bedroom
    if (is_fam_a and is_guest_b) or (is_fam_b and is_guest_a):
        return True
    return False


def _level_id(pref: str) -> str:
    aliases = {
        "entry": LEVEL_ENTRY,
        "ground": LEVEL_ENTRY,
        "any": LEVEL_ENTRY,
        "outdoor": LEVEL_ENTRY,
        "roof": LEVEL_ENTRY,
        "upper": LEVEL_UPPER,
        "not_entry": LEVEL_UPPER,
        "lower": LEVEL_LOWER,
    }
    lv = aliases.get(pref, pref)
    if lv not in (LEVEL_ENTRY, LEVEL_LOWER, LEVEL_UPPER):
        raise Solve2DFailed(f"unsupported level {pref!r}; use entry, lower or upper")
    return lv


def _obstacles(poly, width: int, height: int):
    """Conservative grid cover: an occupied 10 cm cell must lie wholly in the envelope.

    Merge equal forbidden horizontal runs vertically; holes and concavities remain obstacles.
    This also works on diagonal envelopes without accepting their bounding boxes as buildable.
    """
    import numpy as np
    import shapely

    xs, ys = np.meshgrid(np.arange(width), np.arange(height))
    cells = shapely.box(xs / 10, ys / 10, (xs + 1) / 10, (ys + 1) / 10)
    inside = shapely.covers(poly.buffer(1e-8), cells)
    active, result = {}, []
    for y in range(height):
        runs, start = set(), None
        for x in range(width + 1):
            blocked = x < width and not inside[y, x]
            if blocked and start is None:
                start = x
            elif not blocked and start is not None:
                runs.add((start, x))
                start = None
        for run in set(active) - runs:
            result.append((*run, active.pop(run), y))
        for run in runs:
            active.setdefault(run, y)
    result.extend((*run, y0, height) for run, y0 in active.items())
    return result


def solve_2d_placement(
    program: SpaceProgram,
    site: Site,
    frame: DesignFrame,
    opts: SolverOptions,
    strategy: str = STRATEGY_CORRIDOR_FREE,
    proposal: ConceptProposal | None = None,
    multi_level: bool = False,
) -> Solution2D:
    """Place a fully connected, envelope-contained model with exact contact indicators."""
    from itertools import combinations, product

    from house_ai.generation.frame import limit_polygon

    started = time.perf_counter()
    md = cp_model.CpModel()
    rooms = extract_placement_rooms(program, opts.min_areas, opts.min_widths)
    if not rooms:
        raise Solve2DFailed("no rooms to place in space program")
    poly = frame.polygon_to_design(limit_polygon(site)[0])
    _, _, xmax, ymax = poly.bounds
    env_w, env_h = math.floor(xmax * 10 + 1e-7), math.floor(ymax * 10 + 1e-7)
    if min(env_w, env_h) < MIN_ROOM_DIM_DM:
        raise Solve2DFailed("envelope is too narrow for a layout")
    obstacles = _obstacles(poly, env_w, env_h)
    assignments = (
        {a.program_item_id: a.level_id for a in proposal.level_assignments} if proposal else {}
    )
    zones = {pid: z.id for z in proposal.zones for pid in z.program_item_ids} if proposal else {}
    for r in rooms:
        pref = opts.level_prefs.get(
            r.space_id, opts.level_prefs.get(r.item_id, assignments.get(r.item_id, r.level_pref))
        )
        r.level_pref = _level_id(pref)
        r.zone_id = zones.get(r.item_id, r.zone_id)
        if r.space_id in opts.targets:
            r.target_area_m2 = max(opts.targets[r.space_id], r.min_area_m2 or 0)

    outdoor_links = list(opts.outdoor_links)
    if proposal:
        for link in proposal.outdoor_links:
            outdoor_links.extend(
                (r.space_id, link.kind) for r in rooms if r.item_id == link.program_item_id
            )
    unsupported = {k for _, k in outdoor_links} - {"terrace", "balcony", "courtyard"}
    if unsupported:
        raise Solve2DFailed(f"outdoor geometry not supported for {sorted(unsupported)}")
    courtyard = strategy == STRATEGY_COURTYARD or any(k == "courtyard" for _, k in outdoor_links)
    if courtyard:
        rooms.append(
            PlacementRoom(
                COURTYARD_SPACE_ID,
                COURTYARD_NAME,
                SpaceFunction.TERRACE,
                "pi-courtyard",
                ZONE_OUTDOOR,
                LEVEL_ENTRY,
                16,
                min_width_m=3,
            )
        )
    link_pairs = []
    for sid, kind in sorted(set(outdoor_links)):
        source = next((r for r in rooms if r.space_id == sid), None)
        if source is None:
            raise Solve2DFailed(f"unknown outdoor source {sid!r}")
        if kind == "courtyard":
            target_id = COURTYARD_SPACE_ID
        else:
            target_id = f"sp-{kind}-{sid.removeprefix('sp-')}"[:64]
            existing = next(
                (
                    r
                    for r in rooms
                    if r.function.value == kind and r.level_pref == source.level_pref
                ),
                None,
            )
            if existing:
                target_id = existing.space_id
            elif not any(r.space_id == target_id for r in rooms):
                rooms.append(
                    PlacementRoom(
                        target_id,
                        f"{source.name} {kind}",
                        SpaceFunction(kind),
                        f"pi-{target_id[3:]}"[:64],
                        ZONE_OUTDOOR,
                        source.level_pref,
                        12,
                        min_area_m2=9,
                        min_width_m=3,
                    )
                )
        link_pairs.append((sid, target_id))

    level_order = [LEVEL_LOWER, LEVEL_ENTRY, LEVEL_UPPER]
    levels = {r.level_pref for r in rooms} | {LEVEL_ENTRY}
    if multi_level:
        levels.add(LEVEL_UPPER)
    if proposal:
        for core in proposal.stair_cores:
            levels.update(_level_id(lv) for lv in core.connects_levels)
    levels = [lv for lv in level_order if lv in levels]
    if program.levels is not None and len(levels) > program.levels:
        raise Solve2DFailed(f"layout needs {len(levels)} levels; program permits {program.levels}")
    cores = {}
    if len(levels) > 1:
        for lv in levels:
            sid = f"sp-stair-{lv}"
            cores[lv] = sid
            existing = next(
                (r for r in rooms if r.function is SpaceFunction.STAIR and r.level_pref == lv), None
            )
            if existing:
                rooms.remove(existing)
            rooms.append(
                PlacementRoom(
                    sid,
                    f"Stair core ({lv})",
                    SpaceFunction.STAIR,
                    existing.item_id if existing else f"pi-stair-{lv}",
                    "z-circulation",
                    lv,
                    6,
                    min_width_m=2,
                )
            )

    rooms_by_level = {lv: [r for r in rooms if r.level_pref == lv] for lv in levels}
    x, y, xe, ye, widths, heights = {}, {}, {}, {}, {}, {}
    obj = []
    ix, iy = {lv: [] for lv in levels}, {lv: [] for lv in levels}

    def weight(name, default):
        return round(default * opts.objective_weights.get(name, 1))

    def flag(name, comparison, complement):
        b = md.NewBoolVar(name)
        md.Add(comparison).OnlyEnforceIf(b)
        md.Add(complement).OnlyEnforceIf(b.Not())
        return b

    def conjunction(name, terms):
        b = md.NewBoolVar(name)
        if not terms:
            md.Add(b == 1)
        else:
            md.AddBoolAnd(terms).OnlyEnforceIf(b)
            md.AddBoolOr([t.Not() for t in terms]).OnlyEnforceIf(b.Not())
        return b

    def disjunction(name, terms):
        b = md.NewBoolVar(name)
        if terms:
            md.AddMaxEquality(b, terms)
        else:
            md.Add(b == 0)
        return b

    max_x, max_y = md.NewIntVar(0, env_w, "max_x"), md.NewIntVar(0, env_h, "max_y")
    for r in rooms:
        sid = r.space_id
        dims = compute_candidate_dimensions(r, env_w, env_h)
        x[sid], y[sid] = md.NewIntVar(0, env_w, f"x_{sid}"), md.NewIntVar(0, env_h, f"y_{sid}")
        widths[sid] = md.NewIntVar(min(w for w, h in dims), max(w for w, h in dims), f"w_{sid}")
        heights[sid] = md.NewIntVar(min(h for w, h in dims), max(h for w, h in dims), f"h_{sid}")
        xe[sid], ye[sid] = md.NewIntVar(0, env_w, f"xe_{sid}"), md.NewIntVar(0, env_h, f"ye_{sid}")
        md.Add(xe[sid] == x[sid] + widths[sid])
        md.Add(ye[sid] == y[sid] + heights[sid])
        md.Add(xe[sid] <= max_x)
        md.Add(ye[sid] <= max_y)
        md.AddAllowedAssignments([widths[sid], heights[sid]], dims)
        ix[r.level_pref].append(md.NewIntervalVar(x[sid], widths[sid], xe[sid], f"ix_{sid}"))
        iy[r.level_pref].append(md.NewIntervalVar(y[sid], heights[sid], ye[sid], f"iy_{sid}"))
        for j, (a, b, c, d) in enumerate(obstacles):
            outside = [
                flag(f"obs_{sid}_{j}_{k}", expr, inv)
                for k, (expr, inv) in enumerate(
                    [
                        (xe[sid] <= a, xe[sid] > a),
                        (x[sid] >= b, x[sid] < b),
                        (ye[sid] <= c, ye[sid] > c),
                        (y[sid] >= d, y[sid] < d),
                    ]
                )
            ]
            md.AddBoolOr(outside)
        if r.function in (SpaceFunction.ENTRY, SpaceFunction.HALL, SpaceFunction.GARAGE):
            obj.append(weight("site_response", W_ROAD_FACING_SOFT) * y[sid])
        if r.daylight_required:
            obj.append(weight("daylight_opportunity", W_DAYLIGHT_SOFT) * (x[sid] + y[sid]))
        area = md.NewIntVar(0, env_w * env_h, f"area_{sid}")
        md.AddMultiplicationEquality(area, [widths[sid], heights[sid]])
        dev = md.NewIntVar(0, env_w * env_h + r.target_area_dm2, f"area_dev_{sid}")
        md.AddAbsEquality(dev, area - r.target_area_dm2)
        obj.append(W_AREA_DEV * r.priority_weight * dev)
        if r.function in (
            SpaceFunction.HALL,
            SpaceFunction.CORRIDOR,
            SpaceFunction.ENTRY,
            SpaceFunction.STAIR,
            SpaceFunction.LIFT,
        ):
            obj.append(weight("circulation_efficiency", 20) * area)
    for lv in levels:
        md.AddNoOverlap2D(ix[lv], iy[lv])
    md.AddMaxEquality(max_x, list(xe.values()))
    md.AddMaxEquality(max_y, list(ye.values()))
    obj.append(weight("envelope_simplicity", W_COMPACTNESS) * (max_x + max_y))

    by_item = {}
    for r in rooms:
        by_item.setdefault(r.item_id, []).append(r.space_id)
    ids = {r.space_id: r for r in rooms}

    def ends(endpoint):
        return by_item.get(endpoint, [endpoint] if endpoint in ids or endpoint == EXTERIOR else [])

    requirements = list(program.adjacencies)
    if proposal:
        requirements += [
            AdjacencyRequirement(
                id=a.id, a=a.a, b=a.b, kind=a.kind, strength=a.strength, weight=a.weight
            )
            for a in proposal.adjacency_graph
        ]
    requirements += [
        AdjacencyRequirement(
            id=f"rev-{i}",
            a=r.a,
            b=r.b,
            kind=r.kind,
            strength=r.strength,
            weight=r.weight if r.strength is Strength.SOFT else None,
        )
        for i, r in enumerate(opts.relations)
    ]
    requirements += [
        AdjacencyRequirement(id=f"outdoor-{i}", a=a, b=b, kind="connected", strength="hard")
        for i, (a, b) in enumerate(link_pairs)
    ]
    hard_connected = {
        frozenset((a, b))
        for req in requirements
        if req.kind is AdjacencyKind.CONNECTED and req.strength is Strength.HARD
        for a, b in product(ends(req.a), ends(req.b))
    }
    touch, contact, directions, doors = {}, {}, {}, {}
    for ra, rb in combinations(rooms, 2):
        a, b = ra.space_id, rb.space_id
        if ra.level_pref != rb.level_pref:
            continue

        def contact_at(minimum, a=a, b=b):
            checks = {}
            for direction, eq, neq, p, q, r, t in [
                ("east", xe[a] == x[b], xe[a] != x[b], ye[a], y[b], ye[b], y[a]),
                ("west", xe[b] == x[a], xe[b] != x[a], ye[a], y[b], ye[b], y[a]),
                ("north", ye[a] == y[b], ye[a] != y[b], xe[a], x[b], xe[b], x[a]),
                ("south", ye[b] == y[a], ye[b] != y[a], xe[a], x[b], xe[b], x[a]),
            ]:
                name = f"{a}_{b}_{minimum}_{direction}"
                checks[direction] = conjunction(
                    name,
                    [
                        flag(name + "eq", eq, neq),
                        flag(name + "lo", p >= q + minimum, p < q + minimum),
                        flag(name + "hi", r >= t + minimum, r < t + minimum),
                    ],
                )
            return disjunction(f"contact_{a}_{b}_{minimum}", list(checks.values())), checks

        minimum = (
            OPEN_PLAN_WALL_MIN_DM
            if strategy == STRATEGY_OPEN_PLAN
            and (ra.function in OPEN_PLAN_FUNCTIONS and rb.function in OPEN_PLAN_FUNCTIONS)
            else SHARED_WALL_MIN_DM
        )
        touching, dirs = contact_at(minimum)
        contact[a, b], _ = contact_at(2)  # shared length > canonical 0.1 m tolerance
        contact[b, a] = contact[a, b]
        touch[a, b] = touch[b, a] = touching
        directions[a, b] = dirs
        directions[b, a] = {
            "east": dirs["west"],
            "west": dirs["east"],
            "north": dirs["south"],
            "south": dirs["north"],
        }
        allowed = not is_privacy_separated(ra, rb) or frozenset((a, b)) in hard_connected
        if allowed:
            doors[a, b] = doors[b, a] = touching
        obj.append(-weight("adjacency_quality", 30) * touching)

    entry = next(
        (r for r in rooms if r.function is SpaceFunction.ENTRY),
        next((r for r in rooms if r.function is SpaceFunction.HALL), rooms[0]),
    )
    ext_ids = {entry.space_id}
    for req in requirements:
        if EXTERIOR in (req.a, req.b) and req.kind in (
            AdjacencyKind.CONNECTED,
            AdjacencyKind.ADJACENT,
        ):
            ext_ids.update(ends(req.a if req.b == EXTERIOR else req.b))
    ext_flags = {}
    for sid in ids:
        # A complete face on the occupied layout's outer bounds guarantees a usable exterior wall.
        edge = disjunction(
            f"ext_{sid}",
            [
                flag(f"ext_{sid}_{i}", expr, inv)
                for i, (expr, inv) in enumerate(
                    [
                        (x[sid] == 0, x[sid] != 0),
                        (y[sid] == 0, y[sid] != 0),
                        (xe[sid] == max_x, xe[sid] != max_x),
                        (ye[sid] == max_y, ye[sid] != max_y),
                    ]
                )
            ],
        )
        ext_flags[sid] = edge
        if sid in ext_ids:
            md.Add(edge == 1)
            doors[sid, EXTERIOR] = doors[EXTERIOR, sid] = edge

    if cores:
        core_ids = list(cores.values())
        for sid in core_ids[1:]:
            md.Add(x[sid] == x[core_ids[0]])
            md.Add(y[sid] == y[core_ids[0]])
            md.Add(xe[sid] == xe[core_ids[0]])
            md.Add(ye[sid] == ye[core_ids[0]])
        pos = opts.stair_position or (
            proposal.stair_cores[0].position
            if proposal and proposal.stair_cores
            else STAIR_CORE_CENTRAL
        )
        sid = cores[LEVEL_ENTRY]
        if pos == STAIR_CORE_ENTRY and (sid, entry.space_id) in touch:
            md.Add(touch[sid, entry.space_id] == 1)
        elif pos == STAIR_CORE_REAR:
            md.Add(ye[sid] == max_y)
        elif pos == STAIR_CORE_PERIMETER:
            md.Add(ext_flags[sid] == 1)
        elif pos == STAIR_CORE_CENTRAL:
            for r in rooms:
                if r.space_id in core_ids:
                    continue
                for name, axis, limit in [("x", x, env_w), ("y", y, env_h)]:
                    dev = md.NewIntVar(0, limit, f"stair_{name}_{r.space_id}")
                    md.AddAbsEquality(dev, axis[r.space_id] - axis[sid])
                    obj.append(W_STAIR_CENTRAL * dev)
        else:
            raise Solve2DFailed(f"unsupported stair position {pos!r}")
        for a, b in zip(core_ids, core_ids[1:], strict=False):
            one = md.NewConstant(1)
            doors[a, b] = doors[b, a] = one

    # A unit flow from entry to every other room enforces real passable connectivity.
    count = len(rooms)
    flows = {}
    for (a, b), edge in doors.items():
        if EXTERIOR in (a, b):
            continue
        flow = md.NewIntVar(0, count - 1, f"flow_{a}_{b}")
        md.Add(flow <= (count - 1) * edge)
        flows[a, b] = flow
    for sid in ids:
        incoming = sum(v for (a, b), v in flows.items() if b == sid)
        outgoing = sum(v for (a, b), v in flows.items() if a == sid)
        md.Add(
            outgoing - incoming == count - 1 if sid == entry.space_id else incoming - outgoing == 1
        )

    for req in requirements:
        pairs = list(product(ends(req.a), ends(req.b)))
        if not pairs:
            raise Solve2DFailed(f"unknown endpoint in {req.id}")
        satisfied = []
        for a, b in pairs:
            if a == b:
                continue
            if req.kind in (AdjacencyKind.SEPARATED, AdjacencyKind.ACOUSTIC_SEPARATION):
                if EXTERIOR in (a, b):
                    if req.strength is Strength.HARD:
                        raise Solve2DFailed(
                            f"internal-only EXTERIOR separation not supported: {req.id}"
                        )
                    continue
                v = contact.get((a, b), md.NewConstant(0)).Not()
            elif req.kind is AdjacencyKind.CONNECTED:
                v = doors.get((a, b), md.NewConstant(0))
            elif req.kind is AdjacencyKind.ADJACENT:
                v = (
                    ext_flags[b if a == EXTERIOR else a]
                    if EXTERIOR in (a, b)
                    else touch.get((a, b), md.NewConstant(0))
                )
            elif req.kind is AdjacencyKind.NEAR:
                paths = [doors[a, b]] if (a, b) in doors else []
                for middle in [*ids, EXTERIOR]:
                    if (a, middle) in doors and (middle, b) in doors:
                        paths.append(
                            conjunction(
                                f"near_{req.id}_{a}_{b}_{middle}",
                                [doors[a, middle], doors[middle, b]],
                            )
                        )
                v = disjunction(f"near_{req.id}_{a}_{b}", paths)
            elif req.kind is AdjacencyKind.VISUAL:
                if req.strength is Strength.HARD:
                    raise Solve2DFailed(f"hard VISUAL sightline constraint not supported: {req.id}")
                continue
            else:
                continue
            satisfied.append(v)
        separating = req.kind in (AdjacencyKind.SEPARATED, AdjacencyKind.ACOUSTIC_SEPARATION)
        ok = (
            conjunction(f"req_{req.id}", satisfied)
            if separating
            else disjunction(f"req_{req.id}", satisfied)
        )
        if req.strength is Strength.HARD:
            md.Add(ok == 1)
        else:
            obj.append(round(W_ADJACENCY_SOFT * (req.weight or 1)) * (1 - ok))

    if strategy == STRATEGY_TWO_WING:
        _apply_two_wing_constraints(md, rooms, x, y, xe, ye, touch, env_w, env_h)
    if courtyard:
        _apply_courtyard_constraints(
            md,
            COURTYARD_SPACE_ID,
            [r for r in rooms_by_level[LEVEL_ENTRY] if r.space_id != COURTYARD_SPACE_ID],
            directions,
        )
    if strategy == STRATEGY_OPEN_PLAN:
        for ra, rb in combinations([r for r in rooms if r.function in OPEN_PLAN_FUNCTIONS], 2):
            if ra.function == SpaceFunction.DINING or rb.function == SpaceFunction.DINING:
                md.Add(touch.get((ra.space_id, rb.space_id), md.NewConstant(0)) == 1)
    _apply_zoning_objectives(md, rooms, x, y, xe, ye, obj, env_w, env_h)
    md.Minimize(sum(obj))
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = opts.seed
    solver.parameters.max_deterministic_time = opts.deterministic_time
    status = solver.Solve(md)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise Solve2DFailed(
            f"CP-SAT found no contained connected layout ({solver.StatusName(status)})"
        )
    placed = [
        PlacedRoom2D(
            r.space_id,
            r.name,
            r.function,
            r.level_pref,
            solver.Value(x[r.space_id]),
            solver.Value(y[r.space_id]),
            solver.Value(xe[r.space_id]),
            solver.Value(ye[r.space_id]),
            r.item_id,
            r.zone_id,
        )
        for r in rooms
    ]
    walls = []
    placed_by_id = {r.space_id: r for r in placed}
    for a, b in combinations(ids, 2):
        if (a, b) not in touch or not solver.Value(touch[a, b]):
            continue
        ra, rb = placed_by_id[a], placed_by_id[b]
        dirs = directions[a, b]
        if solver.Value(dirs["east"]) or solver.Value(dirs["west"]):
            orientation = "v"
            coord = ra.u1 if solver.Value(dirs["east"]) else rb.u1
            lo, hi = max(ra.v0, rb.v0), min(ra.v1, rb.v1)
        else:
            orientation = "h"
            coord = ra.v1 if solver.Value(dirs["north"]) else rb.v1
            lo, hi = max(ra.u0, rb.u0), min(ra.u1, rb.u1)
        walls.append(SharedWall(a, b, ra.level_id, orientation, coord, lo, hi, (a, b) in doors))
    total = sum(r.area_m2 for r in placed)
    circ = sum(
        r.area_m2
        for r in placed
        if r.function
        in (SpaceFunction.HALL, SpaceFunction.CORRIDOR, SpaceFunction.STAIR, SpaceFunction.ENTRY)
    )
    return Solution2D(
        status=solver.StatusName(status),
        objective=solver.ObjectiveValue(),
        rooms=placed,
        shared_walls=walls,
        circulation_rooms=[],
        levels=levels,
        deterministic_time=solver.deterministic_time,
        wall_time_s=time.perf_counter() - started,
        seed=opts.seed,
        platform_info=f"{platform.system()} {platform.machine()}",
        strategy=strategy,
        circulation_share=circ / total if total else 0,
        has_courtyard=courtyard,
        has_stairs=bool(cores),
        zone_definitions=[
            ProgramZone(id=z.id, name=z.name, privacy=z.privacy or "semi_private")
            for z in proposal.zones
        ]
        if proposal
        else [],
        exterior_connections=sorted(ext_ids),
        optimised_objectives=[
            "adjacency_quality",
            "circulation_efficiency",
            "envelope_simplicity",
            "site_response",
            "daylight_opportunity",
        ],
    )
