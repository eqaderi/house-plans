"""The engine seam inside the plan generator (ADR 0032).

An engine lays out one strategy: a strategy and its context go in; one or more layouts (a
house model and the engine's part of the generation record) come out, or the reason the
strategy cannot be laid out. Two engines sit behind the seam:

- the **bar engine** expands the Space program into bar rooms, builds the strategy's massing
  for a few row-depth patterns, solves each with CP-SAT and assembles each solution;
- the **2D engine** places the Spaces with CP-SAT no-overlap rectangles and assembles that.

Each engine declares only the options its solver reads (``BarOptions``, ``PlacementOptions``),
builds them from what the Owner asked (``OwnerRequests``), and writes and reads its own
generation parameters: the bar engine recovers a parent's position hints from them, and the
2D engine records which soft objectives it optimised for the explanation.

The generator (``generator.py``) keeps what is common: strategy ordering, option ids, which
engine a strategy goes to, the integrity check, the generation record, provenance and the
storey-count Assumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

import ortools
from shapely.geometry import Polygon

from house_ai.constants.strategies import (
    STRATEGY_COMPACT,
    STRATEGY_COURTYARD,
    STRATEGY_LINEAR,
    STRATEGY_SPLIT_LEVEL,
    STRATEGY_SPLIT_WALKOUT,
    STRATEGY_TWO_WING,
)
from house_ai.domain.model import HouseModel
from house_ai.domain.plan import GenerationRecord, RoomPlacement
from house_ai.domain.program import SpaceProgram
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import Actor, ArtifactRef
from house_ai.domain.site import Site

from .assemble import assemble
from .assemble2d import assemble_2d
from .frame import DesignFrame, Ground, from_dm, to_dm
from .massing import CORRIDOR_DM, Infeasible, MassingContext, build_massing
from .rooms import ProgramRooms, Relation, expand_program
from .solver import BarOptions, SolveFailed, solve
from .solver2d import PlacementOptions, Solve2DFailed, solve_2d_placement
from .terrain_levels import configure_section


class EngineKind(StrEnum):
    BAR = "bar"
    TWO_D = "2d"


@dataclass
class OwnerRequests:
    """What the Owner asked of this layout, for whichever engine lays it out.

    Compiled from Revision operations (``revision.compile_revision``) and a topology
    proposal's stair core and outdoor links; empty for a first generation.
    """

    #: space id -> target area (m²).
    targets: dict[str, float] = field(default_factory=dict)
    #: space id -> level preference ("entry", "not_entry", "upper", "lower", ...).
    level_prefs: dict[str, str] = field(default_factory=dict)
    #: Extra soft Space relationships.
    relations: list[Relation] = field(default_factory=list)
    #: Stair position ("entry", "perimeter", "central", "rear"); only the 2D engine places it.
    stair_position: str | None = None
    #: Outdoor links (space id, kind); only the 2D engine places them.
    outdoor_links: list[tuple[str, str]] = field(default_factory=list)
    #: The parent's generation record whose positions unchanged Spaces keep (same strategy).
    positions_from: GenerationRecord | None = None
    #: Spaces that may move freely (rethink); then no bar keeps its start either.
    rethink: set[str] = field(default_factory=set)


@dataclass
class EngineContext:
    """What an engine is given to lay out one strategy."""

    site: Site
    program: SpaceProgram
    frame: DesignFrame
    #: The buildable limit in the design frame.
    limit: Polygon
    ground: Ground
    requests: OwnerRequests = field(default_factory=OwnerRequests)
    seed: int = 0
    #: CP-SAT deterministic time budget (solver work units, not wall-clock seconds).
    deterministic_time: float = 4.0
    #: Objective scales from the constraint set (objective name -> weight).
    objective_weights: dict[str, float] = field(default_factory=dict)
    #: Hard minimum areas and widths per Space requirement, from the constraint set.
    min_areas: dict[str, float] = field(default_factory=dict)
    min_widths: dict[str, float] = field(default_factory=dict)
    proposal: ConceptProposal | None = None
    sectional_strategy: str | None = None
    #: Row-depth patterns (front, back) in decimetres to try instead of the strategy's own.
    depth_patterns: list[tuple[int, int]] | None = None
    #: What the assembled house model is called and where it came from.
    model_id: str = "house"
    name: str = ""
    site_ref: ArtifactRef | None = None
    program_ref: ArtifactRef | None = None
    actor: Actor | None = None


@dataclass
class Layout:
    """One solved and assembled layout, and the engine's part of its generation record."""

    model: HouseModel
    solver: str
    solver_version: str
    status: str
    objective: float
    parameters: dict[str, Any]
    placements: list[RoomPlacement]
    #: Provenance method of the Plan version.
    method: str


@dataclass
class NoLayout:
    """Why an engine could not lay out a strategy."""

    reason: str


class Engine(Protocol):
    def lay_out(self, strategy: str, ctx: EngineContext) -> list[Layout] | NoLayout:
        """Every layout the engine found for ``strategy``, in the order it tried them."""
        ...


def engine_of(record: GenerationRecord) -> EngineKind:
    """The engine that wrote ``record``."""
    return EngineKind.TWO_D if TwoDEngine.wrote(record) else EngineKind.BAR


def optimised_objectives(record: GenerationRecord) -> set[str] | None:
    """The soft objectives the engine that wrote ``record`` optimised.

    None when the engine records no list; then the documented bar-solver objectives apply.
    """
    if engine_of(record) is EngineKind.TWO_D:
        return TwoDEngine.optimised_objectives(record)
    return None


# ---------------------------------------------------------------- bar engine

#: Row-depth patterns (front, back) in decimetres tried for each strategy.
DEPTH_PATTERNS: dict[str, list[tuple[int, int]]] = {
    STRATEGY_LINEAR: [(42, 42), (48, 42)],
    STRATEGY_COMPACT: [(54, 48), (48, 48)],
    STRATEGY_SPLIT_LEVEL: [(48, 42), (54, 48)],
    STRATEGY_SPLIT_WALKOUT: [(48, 42), (54, 48)],
    STRATEGY_TWO_WING: [(48, 42), (42, 42)],
    STRATEGY_COURTYARD: [(48, 42), (42, 42)],
}


def _patterns(strategy: str, rooms: ProgramRooms) -> list[tuple[int, int]]:
    """The strategy's row depths, plus one deep enough for every stacked cluster slot."""
    need = 0
    for cl in rooms.clusters:
        for slot in cl.slots:
            if slot.stacked:
                need = max(need, sum(max(15, to_dm(r.item.min_width_m or 0)) for r in slot.rooms))
    base = DEPTH_PATTERNS[strategy]
    deep = (max(base[0][0], need), max(base[0][1], need))
    return [*base, deep] if need and deep not in base else base


#: Generation parameter suffix of a bar's start along its axis, metres.
BAR_START_SUFFIX = "_start_m"
BAR_LENGTH_SUFFIX = "_length_m"


class BarEngine:
    """Bars and rows from the strategy's massing, solved with CP-SAT (ADR 0013)."""

    def position_hints(
        self, requests: OwnerRequests, program: SpaceProgram
    ) -> tuple[dict[str, tuple[str, int]], dict[str, int]]:
        """Where the parent put each Space (row, start dm) and each bar (start dm).

        Read from the parent's placements and the bar starts this engine records; Spaces the
        program no longer has and rethought Spaces are left free, and when anything is
        rethought no bar keeps its start.
        """
        parent = requests.positions_from
        if parent is None:
            return {}, {}
        spaces = {r.space_id for r in expand_program(program).rooms}
        hints = {
            p.space_id: (p.row_id, to_dm(p.start_m))
            for p in parent.placements
            if p.space_id in spaces and p.space_id not in requests.rethink
        }
        bar_hints = {
            key.removesuffix(BAR_START_SUFFIX): to_dm(float(value))
            for key, value in parent.parameters.items()
            if key.endswith(BAR_START_SUFFIX)
            and isinstance(value, int | float)
            and not requests.rethink
        }
        return hints, bar_hints

    def options(self, ctx: EngineContext) -> BarOptions:
        hints, bar_hints = self.position_hints(ctx.requests, ctx.program)
        return BarOptions(
            seed=ctx.seed,
            deterministic_time=ctx.deterministic_time,
            targets=ctx.requests.targets,
            level_prefs=ctx.requests.level_prefs,
            relations=ctx.requests.relations,
            hints=hints,
            bar_hints=bar_hints,
            objective_weights=ctx.objective_weights,
            sectional_strategy=ctx.sectional_strategy,
        )

    def lay_out(self, strategy: str, ctx: EngineContext) -> list[Layout] | NoLayout:
        rooms = expand_program(
            ctx.program, hard_min_areas=ctx.min_areas, hard_min_widths=ctx.min_widths
        )
        corridor = CORRIDOR_DM
        if rooms.hall_item is not None and rooms.hall_item.min_width_m:
            corridor = max(corridor, to_dm(rooms.hall_item.min_width_m))
        mctx = MassingContext(ctx.frame, ctx.limit, ctx.ground, rooms, ctx.program, corridor)
        opts = self.options(ctx)
        opts.terrain_context = mctx
        layouts: list[Layout] = []
        failed: list[str] = []
        for depths in ctx.depth_patterns or _patterns(strategy, rooms):
            tag = f"rows {from_dm(depths[0]):g}/{from_dm(depths[1]):g} m"
            try:
                m = build_massing(strategy, mctx, depths)
                configure_section(m, ctx.sectional_strategy)
                sol = solve(m, rooms, opts)
            except (Infeasible, SolveFailed) as exc:
                failed.append(f"{tag}: {exc}")
                continue
            asm = assemble(
                m,
                sol,
                rooms,
                ctx.frame,
                ctx.ground,
                ctx.program,
                ctx.site,
                model_id=ctx.model_id,
                name=ctx.name,
                site_ref=ctx.site_ref,
                program_ref=ctx.program_ref,
                actor=ctx.actor,
            )
            layouts.append(
                Layout(
                    model=asm.model,
                    solver="ortools-cp-sat",
                    solver_version=ortools.__version__,
                    status=sol.status,
                    objective=float(sol.objective),
                    parameters={
                        **m.params,
                        **{f"{b}{BAR_START_SUFFIX}": from_dm(v) for b, v in sol.bar_start.items()},
                        **{
                            f"{b}{BAR_LENGTH_SUFFIX}": from_dm(v)
                            for b, v in sol.bar_length.items()
                        },
                    },
                    placements=[
                        RoomPlacement(
                            space_id=s.id,
                            bar_id=s.bar_id,
                            row_id=s.row_id,
                            start_m=from_dm(s.start_dm),
                        )
                        for s in asm.spaces
                        if s.bar_id is not None and s.row_id is not None
                    ],
                    method="cpsat_generation",
                )
            )
        return layouts or NoLayout("; ".join(failed) or "no attempt")


# ----------------------------------------------------------------- 2D engine

#: The one bar id every 2D placement is recorded under (the record has bars and rows).
MAIN_BAR_ID = "wing-main"
#: The generation parameter, and its value, that marks a record this engine wrote.
ENGINE_PARAMETER, ENGINE_2D = "engine", "2d_nooverlap"
OPTIMISED_PARAMETER = "optimised_objectives"


class TwoDEngine:
    """Spaces placed as no-overlap rectangles on fixed stacked levels (ADR 0013).

    Revisions keep no parent positions here: the 2D solver reads no position hints.
    """

    @staticmethod
    def wrote(record: GenerationRecord) -> bool:
        return record.parameters.get(ENGINE_PARAMETER) == ENGINE_2D

    @staticmethod
    def optimised_objectives(record: GenerationRecord) -> set[str]:
        return set(str(record.parameters.get(OPTIMISED_PARAMETER, "")).split(","))

    def options(self, ctx: EngineContext) -> PlacementOptions:
        return PlacementOptions(
            seed=ctx.seed,
            deterministic_time=ctx.deterministic_time,
            targets=ctx.requests.targets,
            level_prefs=ctx.requests.level_prefs,
            relations=ctx.requests.relations,
            objective_weights=ctx.objective_weights,
            stair_position=ctx.requests.stair_position,
            outdoor_links=ctx.requests.outdoor_links,
            min_areas=ctx.min_areas,
            min_widths=ctx.min_widths,
        )

    def lay_out(self, strategy: str, ctx: EngineContext) -> list[Layout] | NoLayout:
        if ctx.sectional_strategy is not None:
            return NoLayout(
                "sectional intent currently requires a bar massing; "
                "2D placement has fixed stacked levels and cannot solve this intent"
            )
        try:
            sol = solve_2d_placement(
                ctx.program,
                ctx.site,
                ctx.frame,
                self.options(ctx),
                strategy=strategy,
                proposal=ctx.proposal,
            )
        except (Infeasible, Solve2DFailed) as exc:
            return NoLayout(f"2D placement infeasible: {exc}")
        model = assemble_2d(
            sol,
            ctx.site,
            ctx.frame,
            ctx.ground,
            ctx.program,
            actor=ctx.actor,
            model_id=ctx.model_id,
            name=ctx.name,
            site_ref=ctx.site_ref,
            program_ref=ctx.program_ref,
        )
        return [
            Layout(
                model=model,
                solver="ortools-cp-sat-nooverlap2d",
                solver_version=ortools.__version__,
                status=sol.status,
                objective=float(sol.objective),
                parameters={
                    "strategy": strategy,
                    ENGINE_PARAMETER: ENGINE_2D,
                    "circulation_share": sol.circulation_share,
                    "platform": sol.platform_info,
                    "deterministic_time": sol.deterministic_time,
                    "wall_time_s": sol.wall_time_s,
                    OPTIMISED_PARAMETER: ",".join(sol.optimised_objectives),
                },
                placements=[
                    RoomPlacement(
                        space_id=r.space_id,
                        bar_id=MAIN_BAR_ID,
                        row_id=r.level_id,
                        start_m=from_dm(r.u0),
                    )
                    for r in sol.rooms
                ],
                method="cpsat_2d_placement",
            )
        ]
