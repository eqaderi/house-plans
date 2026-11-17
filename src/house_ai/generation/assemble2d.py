"""Assemble canonical HouseModel from 2D placement engine solution (Solution2D).

Freely placed 2D rooms are one rectangle each. Walls and their materials come from
:mod:`.enclosure` (ADR 0031); this module adds what only 2D placement has: shared-wall
door candidates, open-plan openings, courtyards and stacked stair cores.
"""

from __future__ import annotations

from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import box
from shapely.ops import unary_union

from house_ai.constants.placement2d import (
    COURTYARD_SPACE_ID,
    DOOR_HEIGHT_DEFAULT_M,
    DOOR_WIDTH_DEFAULT_M,
    LEVEL_ENTRY,
    LEVEL_UPPER,
    STAIR_CORE_RISERS,
    STOREY_HEIGHT_M,
    TERRACE_DOOR_DEFAULT_WIDTH_M,
    TERRACE_SLAB_THICKNESS_M,
    WINDOW_HEIGHT_DEFAULT_M,
    WINDOW_WIDTH_DEFAULT_M,
)
from house_ai.constants.strategies import STRATEGY_OPEN_PLAN
from house_ai.domain.geometry import Polygon2D
from house_ai.domain.model import (
    Ceiling,
    CompositeSpace,
    HouseModel,
    Level,
    Opening,
    OpeningKind,
    Operation,
    Slab,
    SlabKind,
    Space,
    Stair,
    StairKind,
    Zone,
)
from house_ai.domain.program import Privacy, SpaceFunction, SpaceProgram
from house_ai.domain.provenance import Actor, ArtifactKind, ArtifactRef
from house_ai.domain.records import Assumption, Issue, Severity
from house_ai.domain.site import Site
from house_ai.generation.enclosure import WALL_HEIGHT_M, EnclosedSpace, Enclosure, Rect, WallSeg
from house_ai.generation.fixtures import with_fixtures
from house_ai.generation.frame import DesignFrame, Ground
from house_ai.generation.solver2d import (
    OPEN_PLAN_FUNCTIONS,
    Solution2D,
)
from house_ai.generation.stairs import LANDING_STRIP_DM, u_layout

CEILING_M = 2.7


def _short(s: str) -> str:
    return s.removeprefix("sp-").removeprefix("w-").replace("_", "-")


class Builder2D:
    def __init__(
        self,
        sol: Solution2D,
        site: Site,
        frame: DesignFrame,
        ground: Ground,
        program: SpaceProgram,
        actor: Actor,
    ) -> None:
        self.sol = sol
        self.site = site
        self.frame = frame
        self.ground = ground
        self.program = program
        self.actor = actor

        offsets = {"lv-lower": -STOREY_HEIGHT_M, LEVEL_ENTRY: 0.0, LEVEL_UPPER: STOREY_HEIGHT_M}
        self.levels = [
            Level(
                id=lv,
                name=lv.removeprefix("lv-").title() + " level",
                elevation_m=sol.level_elevations_m.get(lv, offsets[lv]),
                floor_to_floor_m=STOREY_HEIGHT_M,
            )
            for lv in sol.levels
        ]
        self.elevation_basis = "Terrain unknown: entry uses local z=0 as an explicit assumption."
        if sol.level_elevations_m:
            self.elevation_basis = (
                "Levels solved jointly with placement: entry follows surveyed terrain "
                "0.5 m roadward of its front face (5 cm XY / 1 cm Z lookup); "
                "stacked levels retain 3 m rises. Terrain interpolation is inferred."
            )

        self.walls: list[WallSeg] = []
        self.openings: list[Opening] = []
        self.issues: list[Issue] = []

    def _space_boundary(self, room, all_rooms):
        """Node shared grid edges before rotating/rounding them into LOCAL coordinates.

        Every shared segment then has exactly the same endpoints on both sides,
        including T-junctions; no sub-micrometre wedge can split an open-plan room.
        """
        vertices = {
            p
            for r in all_rooms
            if r.level_id == room.level_id
            for p in ((r.u0, r.v0), (r.u1, r.v0), (r.u1, r.v1), (r.u0, r.v1))
        }
        corners = [(room.u0, room.v0), (room.u1, room.v0), (room.u1, room.v1), (room.u0, room.v1)]
        out = []
        for a, b in zip(corners, [*corners[1:], corners[0]], strict=True):
            points = {a, b} | {
                p
                for p in vertices
                if (a[0] == b[0] == p[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))
                or (a[1] == b[1] == p[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0]))
            }
            ordered = sorted(points, key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
            out.extend(self.frame.to_local(*p) for p in ordered[:-1])
        return Polygon2D(outer=out)

    def build_walls(self) -> None:
        self.enclosure = Enclosure(
            self.levels,
            [
                EnclosedSpace(r.space_id, r.level_id, Rect(r.u0, r.v0, r.u1, r.v1), r.function)
                for r in self.sol.rooms
            ],
            self.frame,
            self.ground,
        )
        self.walls = self.enclosure.walls
        self.openings = self.enclosure.openings

    def _walls_between(self, a: str, b: str | None) -> list[WallSeg]:
        level = next(r.level_id for r in self.sol.rooms if r.space_id == a)
        return self.enclosure.walls_between(level, a, b)

    def place_opening(
        self,
        a: str,
        b: str | None,
        kind: OpeningKind,
        width_m: float,
        *,
        height_m: float = DOOR_HEIGHT_DEFAULT_M,
        sill_m: float = 0.0,
        operation: Operation = Operation.NONE,
        material: str | None = None,
        prefix: str = "d",
        road_facing: bool = False,
    ) -> Opening | None:
        """Choose candidate walls for an opening; Enclosure fits it (ADR 0031)."""
        level = next(r.level_id for r in self.sol.rooms if r.space_id == a)
        walls = self._walls_between(a, b)
        if road_facing:
            walls = [w for w in walls if w.orient == "h" and w.c == self.sol.road_front_dm]
        if b is None:
            rooms = [r for r in self.sol.rooms if r.level_id == level]
            # Prefer a face on the outline of the level's rooms to one in a recess.
            outer_x = {min(r.u0 for r in rooms), max(r.u1 for r in rooms)}
            outer_y = {min(r.v0 for r in rooms), max(r.v1 for r in rooms)}
            outer_walls = [w for w in walls if w.c in (outer_y if w.orient == "h" else outer_x)]
            if outer_walls:
                walls = outer_walls
        return self.enclosure.place(
            level,
            a,
            b,
            kind,
            width_m,
            height_m=height_m,
            sill_m=sill_m,
            operation=operation,
            material=material or ("m-door" if kind is OpeningKind.DOOR else "m-glass"),
            prefix=prefix,
            walls=walls,
        )

    def build_openings(self) -> None:
        all_rooms = self.sol.rooms
        room_by_id = {r.space_id: r for r in all_rooms}

        # 1. Exterior front entrance door on entry room
        entry_room = next(
            (r for r in all_rooms if r.function is SpaceFunction.ENTRY),
            self.sol.rooms[0],
        )
        for sid in self.sol.exterior_connections or [entry_room.space_id]:
            self.place_opening(
                sid,
                None,
                OpeningKind.DOOR,
                width_m=0.9,
                operation=Operation.SWING_RIGHT,
                prefix="d-ext",
                road_facing=sid == entry_room.space_id and self.sol.road_front_dm is not None,
            )

        # 2. Door / cased openings along shared walls
        is_open_plan = self.sol.strategy == STRATEGY_OPEN_PLAN
        for sw in self.sol.shared_walls:
            if not sw.door_candidate:
                continue
            ra = room_by_id.get(sw.room_a)
            rb = room_by_id.get(sw.room_b)
            if not ra or not rb:
                continue

            if (
                is_open_plan
                and ra.function in OPEN_PLAN_FUNCTIONS
                and rb.function in OPEN_PLAN_FUNCTIONS
            ):
                # The whole interface is open: these are functional zones of a
                # composite physical room, not separate rooms linked by a small door.
                seg = max(self._walls_between(ra.space_id, rb.space_id), key=lambda w: w.length)
                self.enclosure.cut(
                    seg,
                    0,
                    seg.length,
                    kind=OpeningKind.OPENING,
                    connects=(ra.space_id, rb.space_id),
                    ident=self.enclosure.new_id(f"o-{_short(ra.space_id)}-{_short(rb.space_id)}"),
                    height_m=WALL_HEIGHT_M,
                )
            elif ra.function is SpaceFunction.TERRACE or rb.function is SpaceFunction.TERRACE:
                prefix = (
                    "d-court"
                    if (ra.space_id == COURTYARD_SPACE_ID or rb.space_id == COURTYARD_SPACE_ID)
                    else "d-terrace"
                )
                self.place_opening(
                    ra.space_id,
                    rb.space_id,
                    OpeningKind.DOOR,
                    width_m=TERRACE_DOOR_DEFAULT_WIDTH_M,
                    operation=Operation.SLIDING,
                    prefix=prefix,
                )
            else:
                self.place_opening(
                    ra.space_id,
                    rb.space_id,
                    OpeningKind.DOOR,
                    width_m=DOOR_WIDTH_DEFAULT_M,
                    operation=Operation.SWING_LEFT,
                    prefix="d",
                )

        # 3. Windows on exterior walls of habitable rooms
        for r in self.sol.rooms:
            if r.function in (
                SpaceFunction.LIVING,
                SpaceFunction.DINING,
                SpaceFunction.KITCHEN,
                SpaceFunction.BEDROOM,
                SpaceFunction.STUDY,
            ):
                ext_walls = self._walls_between(r.space_id, None)
                for w in ext_walls:
                    if w.length >= 15:
                        self.place_opening(
                            r.space_id,
                            None,
                            OpeningKind.WINDOW,
                            width_m=WINDOW_WIDTH_DEFAULT_M,
                            height_m=WINDOW_HEIGHT_DEFAULT_M,
                            sill_m=0.9,
                            operation=Operation.SLIDING,
                            prefix="win",
                        )
                        break

    def _slab_parts(self, slabs: list[Slab], lv: str, kind: SlabKind, geom) -> None:
        """Append one slab per polygon part of ``geom`` (design dm) on level ``lv``."""
        parts = [g for g in getattr(geom, "geoms", [geom]) if g.area >= 1]
        for idx, part in enumerate(parts, start=1):
            part = part.simplify(0)
            outer = [self.frame.to_local(round(x), round(y)) for x, y in part.exterior.coords[:-1]]
            holes = [
                [self.frame.to_local(round(x), round(y)) for x, y in ring.coords[:-1]]
                for ring in part.interiors
            ]
            suffix = f"-{idx}" if len(parts) > 1 else ""
            slabs.append(
                Slab(
                    id=f"slab-{kind.value}-{lv.removeprefix('lv-')}{suffix}",
                    level_id=lv,
                    kind=kind,
                    boundary=Polygon2D(outer=outer, holes=holes),
                    thickness_m=0.25,
                    top_offset_m=STOREY_HEIGHT_M if kind is SlabKind.ROOF else 0.0,
                    material_id="m-slab",
                )
            )

    def _u_flight(self, core, walls):
        """Footprint, width, walking line and fit of a U-shaped flight in a stair core.

        The lanes run along the core's longer side; both flights meet the end nearer the
        core's door, where the upper landing stays in the floor (ADR 0023).
        """
        along_u = (core.u1 - core.u0) >= (core.v1 - core.v0)
        short = (core.v1 - core.v0) if along_u else (core.u1 - core.u0)
        # Lanes keep half an exterior wall plus tolerance (0.2 m) from the walls.
        width = round(min(1.0, short / 20 - 0.2), 3)
        if along_u:
            lo, hi, c0, c1 = core.u0 + 2, core.u1 - 2, core.v0 + 2, core.v1 - 2
        else:
            lo, hi, c0, c1 = core.v0 + 2, core.v1 - 2, core.u0 + 2, core.u1 - 2
        by_id = {w.id: w for w in walls}
        doors = [
            o
            for o in self.openings
            if o.is_passable and core.space_id in o.connects and o.host_wall_id in by_id
        ]
        door_at_hi = False
        if doors:
            w = by_id[doors[0].host_wall_id]
            mid = self.frame.to_design(((w.start[0] + w.end[0]) / 2, (w.start[1] + w.end[1]) / 2))
            x = (mid[0] if along_u else mid[1]) * 10
            door_at_hi = abs(x - hi) < abs(x - lo)
        strip = LANDING_STRIP_DM
        near = hi + 2 - strip if door_at_hi else lo - 2 + strip
        far = lo if door_at_hi else hi
        pts, fits = u_layout(near, far, c0, c1, width * 10, STAIR_CORE_RISERS)
        r0, r1 = sorted((near, far))
        if along_u:
            footprint = self.frame.rect(r0, c0, r1, c1)
            line = [self.frame.to_local(x, c) for x, c in pts]
        else:
            footprint = self.frame.rect(c0, r0, c1, r1)
            line = [self.frame.to_local(c, x) for x, c in pts]
        return footprint, width, line, fits

    def build_model(
        self, model_id: str, name: str, site_ref: ArtifactRef, program_ref: ArtifactRef
    ) -> HouseModel:
        self.build_walls()
        self.build_openings()
        all_rooms = self.sol.rooms
        spaces: list[Space] = []
        for r in all_rooms:
            poly = self._space_boundary(r, all_rooms)
            prog_item_id = (
                r.program_item_id
                if any(it.id == r.program_item_id for it in self.program.space_requirements)
                else None
            )
            spaces.append(
                Space(
                    id=r.space_id,
                    name=r.name,
                    function=r.function,
                    level_id=r.level_id,
                    boundary=poly,
                    program_item_id=prog_item_id,
                    zone_id=r.zone_id,
                    floor_material_id="m-floor",
                )
            )

        # Zones
        zones: list[Zone] = []
        used_zones: dict[str, list[str]] = {}
        for s in spaces:
            if s.zone_id:
                used_zones.setdefault(s.zone_id, []).append(s.id)

        program_zones = {z.id: z for z in [*self.program.zones, *self.sol.zone_definitions]}
        for zid, sids in used_zones.items():
            if zid in program_zones:
                pz = program_zones[zid]
                zones.append(Zone(id=zid, name=pz.name, privacy=pz.privacy, space_ids=sids))
            else:
                zones.append(Zone(id=zid, name=zid, privacy=Privacy.SEMI_PRIVATE, space_ids=sids))

        composites = []
        if self.sol.strategy == STRATEGY_OPEN_PLAN:
            for level in self.levels:
                children = [
                    sp
                    for sp in spaces
                    if sp.level_id == level.id and sp.function in OPEN_PLAN_FUNCTIONS
                ]
                if len(children) >= 2:
                    # Union on the exact solver grid. Rounding rotated LOCAL coordinates
                    # first can separate a shared edge by fractions of a micrometre.
                    child_ids = {sp.id for sp in children}
                    union = unary_union(
                        [box(r.u0, r.v0, r.u1, r.v1) for r in all_rooms if r.space_id in child_ids]
                    ).simplify(0)
                    if union.geom_type != "Polygon":
                        # The 2D solver does not guarantee contiguity: report, do not group.
                        self.issues.append(
                            Issue(
                                id=f"iss-open-plan-split-{level.id}"[:64],
                                title=(
                                    f"Open-plan living, dining and cooking are not contiguous "
                                    f"on {level.id}"
                                ),
                                severity=Severity.WARNING,
                                subject_ids=[sp.id for sp in children],
                                raised_by=self.actor,
                            )
                        )
                        continue
                    composites.append(
                        CompositeSpace(
                            id=f"composite-open-{level.id}",
                            name="Living / dining / cooking",
                            level_id=level.id,
                            space_ids=[sp.id for sp in children],
                            boundary=Polygon2D(
                                outer=[
                                    self.frame.to_local(x, y)
                                    for x, y in list(union.exterior.coords)[:-1]
                                ],
                                holes=[
                                    [self.frame.to_local(x, y) for x, y in list(r.coords)[:-1]]
                                    for r in union.interiors
                                ],
                            ),
                        )
                    )

        walls = self.enclosure.wall_models()

        stairs: list[Stair] = []
        if self.sol.has_stairs:
            cores = {r.level_id: r for r in all_rooms if r.function is SpaceFunction.STAIR}
            ordered = sorted(self.levels, key=lambda lv: lv.elevation_m)
            for lower, upper in zip(ordered, ordered[1:], strict=False):
                a, b = cores[lower.id], cores[upper.id]
                sid = "stair-main" if len(ordered) == 2 else f"stair-{lower.id}-{upper.id}"
                footprint, width, line, fits = self._u_flight(a, walls)
                if not fits:
                    self.issues.append(
                        Issue(
                            id=f"iss-{sid}-landing"[:64],
                            title=f"{sid}: no room in the core for two flights and a half landing",
                            severity=Severity.BLOCKING,
                            subject_ids=[a.space_id],
                            raised_by=self.actor,
                        )
                    )
                stairs.append(
                    Stair(
                        id=sid,
                        kind=StairKind.U_SHAPED,
                        from_level_id=lower.id,
                        to_level_id=upper.id,
                        footprint=footprint,
                        bottom_space_id=a.space_id,
                        top_space_id=b.space_id,
                        width_m=width,
                        riser_count=STAIR_CORE_RISERS,
                        riser_height_m=(upper.elevation_m - lower.elevation_m) / STAIR_CORE_RISERS,
                        tread_depth_m=0.28,
                        walking_line=line,
                        landing_segments=[1],
                    )
                )

        # Slabs per level
        slabs: list[Slab] = []
        for lv in self.sol.levels:
            rooms_on_lv = [r for r in all_rooms if r.level_id == lv]
            int_boxes = [
                box(r.u0, r.v0, r.u1, r.v1)
                for r in rooms_on_lv
                if r.function is not SpaceFunction.TERRACE
            ]
            terrace_rooms = [r for r in rooms_on_lv if r.function is SpaceFunction.TERRACE]

            if int_boxes:
                fp_u = unary_union(int_boxes)
                # The floor is open over each flight arriving on this level; a roof sits at
                # storey height wherever no higher level covers this one (ADR 0023).
                flights = [
                    ShapelyPolygon(
                        [
                            tuple(round(c * 10) for c in self.frame.to_design(xy))
                            for xy in st.footprint.outer
                        ]
                    )
                    for st in stairs
                    if st.to_level_id == lv
                ]
                floor_u = fp_u.difference(unary_union(flights)) if flights else fp_u
                above = [
                    box(r.u0, r.v0, r.u1, r.v1)
                    for r in all_rooms
                    if r.function is not SpaceFunction.TERRACE
                    and self.sol.levels.index(r.level_id) > self.sol.levels.index(lv)
                ]
                roof_u = fp_u.difference(unary_union(above)) if above else fp_u
                for kind, geom in ((SlabKind.FLOOR, floor_u), (SlabKind.ROOF, roof_u)):
                    self._slab_parts(slabs, lv, kind, geom)

            for tr in terrace_rooms:
                t_poly = self.frame.rect(tr.u0, tr.v0, tr.u1, tr.v1)
                slabs.append(
                    Slab(
                        id=f"slab-terrace-{tr.space_id.removeprefix('sp-')}",
                        level_id=lv,
                        kind=SlabKind.TERRACE,
                        boundary=t_poly,
                        thickness_m=TERRACE_SLAB_THICKNESS_M,
                        material_id="m-slab",
                    )
                )

        ceilings = [
            Ceiling(
                id=f"ceil-{_short(s.id)}"[:64],
                space_id=s.id,
                height_m=CEILING_M,
                material_id="m-int-wall",
            )
            for s in spaces
        ]

        return HouseModel(
            id=model_id,
            name=name,
            coordinate_system_id=self.site.coordinates.local.id,  # type: ignore[union-attr]
            site_ref=site_ref,
            program_ref=program_ref,
            levels=self.levels,
            spaces=spaces,
            composite_spaces=composites,
            walls=walls,
            openings=self.openings,
            slabs=slabs,
            ceilings=ceilings,
            stairs=stairs,
            zones=zones,
            relationships=[],
            materials=self.enclosure.materials(),
            assumptions=[
                Assumption(
                    id="asm-2d-placement",
                    statement=(
                        f"{self.elevation_basis} Strategy: {self.sol.strategy}; "
                        f"circulation share: {self.sol.circulation_share * 100:.1f}%; "
                        f"deterministic time: {self.sol.deterministic_time:.2f}"
                    ),
                    basis="two-dimensional placement engine (CP-SAT NoOverlap2D)",
                    made_by=self.actor,
                )
            ],
            issues=self.issues,
        )


def assemble_2d(
    sol: Solution2D,
    site: Site,
    frame: DesignFrame,
    ground: Ground,
    program: SpaceProgram,
    actor: Actor,
    model_id: str = "model-2d-concept",
    name: str = "2D Floor Plan Concept",
    site_ref: ArtifactRef | None = None,
    program_ref: ArtifactRef | None = None,
) -> HouseModel:
    """Assemble a solved 2D placement into a canonical HouseModel."""
    dummy_site_ref = site_ref or ArtifactRef(
        kind=ArtifactKind.SITE, id="site", version=1, sha256="0" * 64
    )
    dummy_program_ref = program_ref or ArtifactRef(
        kind=ArtifactKind.SPACE_PROGRAM, id="program", version=1, sha256="0" * 64
    )

    builder = Builder2D(sol, site, frame, ground, program, actor)
    return with_fixtures(
        builder.build_model(model_id, name, dummy_site_ref, dummy_program_ref), actor
    )
