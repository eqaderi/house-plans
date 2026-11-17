"""The engine seam inside the plan generator (ADR 0032).

An engine lays out one strategy: a strategy and its context go in; one or more layouts (a
house model and the engine's part of the generation record) come out, or the reason the
strategy cannot be laid out. Two engines sit behind the seam:

- the **bar engine** expands the Space program into bar rooms, builds the strategy's massing
  for a few row-depth patterns, solves each with CP-SAT and assembles each solution;
- the **2D engine** places the Spaces with CP-SAT no-overlap rectangles and assembles that.

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
from house_ai.domain.plan import RoomPlacement
from house_ai.domain.program import SpaceProgram
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import Actor, ArtifactRef
from house_ai.domain.site import Site

from .assemble import assemble
from .assemble2d import assemble_2d
from .frame import DesignFrame, Ground, from_dm, to_dm
from .massing import CORRIDOR_DM, Infeasible, MassingContext, build_massing
from .rooms import ProgramRooms, expand_program
from .solver import SolveFailed, SolverOptions, solve
from .solver2d import Solve2DFailed, solve_2d_placement
from .terrain_levels import configure_section


class EngineKind(StrEnum):
    BAR = "bar"
    TWO_D = "2d"


@dataclass
class EngineContext:
    """What an engine is given to lay out one strategy."""

    site: Site
    program: SpaceProgram
    frame: DesignFrame
    #: The buildable limit in the design frame.
    limit: Polygon
    ground: Ground
    options: SolverOptions
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


class BarEngine:
    """Bars and rows from the strategy's massing, solved with CP-SAT (ADR 0013)."""

    def lay_out(self, strategy: str, ctx: EngineContext) -> list[Layout] | NoLayout:
        rooms = expand_program(
            ctx.program, hard_min_areas=ctx.min_areas, hard_min_widths=ctx.min_widths
        )
        corridor = CORRIDOR_DM
        if rooms.hall_item is not None and rooms.hall_item.min_width_m:
            corridor = max(corridor, to_dm(rooms.hall_item.min_width_m))
        mctx = MassingContext(ctx.frame, ctx.limit, ctx.ground, rooms, ctx.program, corridor)
        opts = ctx.options
        layouts: list[Layout] = []
        failed: list[str] = []
        for depths in ctx.depth_patterns or _patterns(strategy, rooms):
            tag = f"rows {from_dm(depths[0]):g}/{from_dm(depths[1]):g} m"
            try:
                m = build_massing(strategy, mctx, depths)
                configure_section(m, ctx.sectional_strategy)
                opts.terrain_context = mctx
                opts.sectional_strategy = ctx.sectional_strategy
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
                        **{f"{b}_start_m": from_dm(v) for b, v in sol.bar_start.items()},
                        **{f"{b}_length_m": from_dm(v) for b, v in sol.bar_length.items()},
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


class TwoDEngine:
    """Spaces placed as no-overlap rectangles on fixed stacked levels (ADR 0013)."""

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
                ctx.options,
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
                    "engine": "2d_nooverlap",
                    "circulation_share": sol.circulation_share,
                    "platform": sol.platform_info,
                    "deterministic_time": sol.deterministic_time,
                    "wall_time_s": sol.wall_time_s,
                    "optimised_objectives": ",".join(sol.optimised_objectives),
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
