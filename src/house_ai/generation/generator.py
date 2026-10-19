"""Solver-backed multi-concept plan generator.

For each requested strategy the generator builds the strategy's massing for a
few row-depth patterns, solves each with CP-SAT, assembles a canonical
:class:`HouseModel`, runs :func:`check_model` on it and keeps the best result:
the integrity-clean solution with the lowest objective, or, if none is
clean, the best one marked invalid (never silently dropped). A strategy that
cannot be laid out at all is reported with the reason.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime

import ortools

from house_ai.constants.strategies import (
    STRATEGY_COMPACT,
    STRATEGY_CORRIDOR_FREE,
    STRATEGY_COURTYARD,
    STRATEGY_LINEAR,
    STRATEGY_OPEN_PLAN,
    STRATEGY_SPLIT_LEVEL,
    STRATEGY_SPLIT_WALKOUT,
    STRATEGY_TWO_WING,
)
from house_ai.domain.constraints import (
    ConstraintSet,
    MinAreaRule,
    MinDimensionRule,
    ObjectiveRule,
)
from house_ai.domain.integrity import IntegrityFinding, check_model, errors
from house_ai.domain.plan import (
    ChangeRequest,
    GenerationRecord,
    PlanVersion,
    RoomPlacement,
)
from house_ai.domain.program import AdjacencyRequirement, SpaceProgram
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import Actor, ActorKind, ArtifactRef, Provenance
from house_ai.domain.records import Assumption
from house_ai.domain.site import Site

from .assemble import assemble
from .assemble2d import assemble_2d
from .frame import FrameError, Ground, design_frame, from_dm, limit_polygon, to_dm
from .massing import (
    CORRIDOR_DM,
    STRATEGY_LABELS,
    STRATEGY_ORDER,
    Infeasible,
    MassingContext,
    build_massing,
)
from .rooms import ProgramRooms, expand_program
from .solver import SolveFailed, SolverOptions, solve
from .solver2d import Solve2DFailed, solve_2d_placement

GENERATOR = "house-ai-cpsat-bars"
GENERATOR_VERSION = "0.2.0"
GENERATOR_ACTOR = Actor(kind=ActorKind.SYSTEM, id="house-ai-plan-generator")

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


def option_id_for(strategy: str, proposal_id: str | None = None) -> str:
    """Option of a concept; a topology proposal gets its own (S10-04, ISS-31).

    Proposal concepts never become a new version of the strategy's concept, so they cannot
    replace a generated or owner-revised version as its latest.
    """
    option = "concept-" + strategy.replace("_", "-")
    if proposal_id is None:
        return option
    full = f"{option}-{proposal_id}"
    if len(full) <= 64:
        return full
    digest = hashlib.sha256(proposal_id.encode()).hexdigest()[:8]
    return f"{full[: 64 - len(digest) - 1].rstrip('-')}-{digest}"


@dataclass
class Candidate:
    strategy: str
    option_id: str
    status: str  # "generated" | "infeasible"
    reason: str | None = None
    plan: PlanVersion | None = None
    findings: list[IntegrityFinding] = field(default_factory=list)
    attempts: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.plan is not None and not errors(self.findings)


@dataclass
class GenerationRequest:
    site: Site
    program: SpaceProgram
    constraints: ConstraintSet | None
    site_ref: ArtifactRef | None
    program_ref: ArtifactRef | None
    created_at: datetime
    strategies: list[str] | None = None
    seed: int = 0
    deterministic_time: float = 4.0
    solver: SolverOptions | None = None
    inputs: list[ArtifactRef] = field(default_factory=list)
    #: For revisions: the parent version, the change request and the agent's ops.
    parent: ArtifactRef | None = None
    change_request: ChangeRequest | None = None
    revision_ops: list[str] = field(default_factory=list)
    option_id: str | None = None
    depth_patterns: list[tuple[int, int]] | None = None
    proposal: ConceptProposal | None = None
    proposal_ref: ArtifactRef | None = None
    sectional_strategy: str | None = None


def hard_dimension_bounds(
    constraints: ConstraintSet | None,
) -> tuple[dict[str, float], dict[str, float]]:
    if constraints is None:
        return {}, {}
    min_areas: dict[str, float] = {}
    min_widths: dict[str, float] = {}
    for c in constraints.hard():
        if isinstance(c.rule, MinAreaRule) and c.rule.min_area_m2 is not None:
            pid = c.rule.program_item_id
            min_areas[pid] = max(min_areas.get(pid, 0.0), c.rule.min_area_m2)
        elif isinstance(c.rule, MinDimensionRule) and c.rule.min_width_m is not None:
            pid = c.rule.program_item_id
            min_widths[pid] = max(min_widths.get(pid, 0.0), c.rule.min_width_m)
    return min_areas, min_widths


def objective_weights(constraints: ConstraintSet | None) -> dict[str, float]:
    if constraints is None:
        return {}
    out: dict[str, float] = {}
    for c in constraints.soft():
        if isinstance(c.rule, ObjectiveRule) and c.weight is not None:
            out[c.rule.objective.value] = out.get(c.rule.objective.value, 0.0) + c.weight
    return out


class CpSatPlanGenerator:
    """:class:`~house_ai.generation.base.PlanGenerator` backed by OR-Tools CP-SAT."""

    name = GENERATOR

    def generate(
        self,
        site: Site,
        program: SpaceProgram,
        constraints: ConstraintSet,
        *,
        strategies: list[str],
        seed: int,
    ) -> list[PlanVersion]:
        from house_ai.domain.base import utc_now

        req = GenerationRequest(
            site=site,
            program=program,
            constraints=constraints,
            site_ref=None,
            program_ref=None,
            created_at=utc_now(),
            strategies=strategies,
            seed=seed,
        )
        return [c.plan for c in self.candidates(req) if c.plan is not None]

    def candidates(self, req: GenerationRequest) -> list[Candidate]:
        hard_areas, hard_widths = hard_dimension_bounds(req.constraints)
        program = req.program
        if req.proposal and req.proposal.adjacency_graph:
            existing_ids = {a.id for a in program.adjacencies}
            extra_adj = [
                AdjacencyRequirement(
                    id=padj.id,
                    a=padj.a,
                    b=padj.b,
                    kind=padj.kind,
                    strength=padj.strength,
                    weight=padj.weight,
                    rationale=padj.rationale,
                )
                for padj in req.proposal.adjacency_graph
                if padj.id not in existing_ids
            ]
            if extra_adj:
                program = program.model_copy(
                    update={"adjacencies": [*program.adjacencies, *extra_adj]}
                )
        rooms = expand_program(program, hard_min_areas=hard_areas, hard_min_widths=hard_widths)
        proposal_id = req.proposal.id if req.proposal is not None else None
        try:
            frame = design_frame(req.site)
            limit = frame.polygon_to_design(limit_polygon(req.site)[0])
        except FrameError as exc:
            return [
                Candidate(s, req.option_id or option_id_for(s, proposal_id), "infeasible", str(exc))
                for s in (req.strategies or STRATEGY_ORDER)
            ]
        ground = Ground(req.site, frame)
        corridor = CORRIDOR_DM
        if rooms.hall_item is not None and rooms.hall_item.min_width_m:
            corridor = max(corridor, to_dm(rooms.hall_item.min_width_m))
        ctx = MassingContext(frame, limit, ground, rooms, program, corridor)
        opts = req.solver or SolverOptions()
        opts.min_areas = hard_areas
        opts.min_widths = hard_widths
        opts.seed = req.seed
        opts.deterministic_time = req.deterministic_time
        opts.objective_weights = {**objective_weights(req.constraints), **opts.objective_weights}
        if req.proposal and req.proposal.level_assignments:
            for la in req.proposal.level_assignments:
                opts.level_prefs[la.program_item_id] = la.level_id
        strategies = req.strategies
        if strategies is None and req.proposal and req.proposal.target_strategy:
            strategies = [req.proposal.target_strategy]
        out = []
        for strategy in strategies or STRATEGY_ORDER:
            out.append(self._strategy(strategy, ctx, rooms, frame, ground, req, opts))
        return out

    def _strategy(self, strategy, ctx, rooms, frame, ground, req, opts) -> Candidate:
        option = req.option_id or option_id_for(
            strategy, req.proposal.id if req.proposal is not None else None
        )
        if req.sectional_strategy and req.option_id is None:
            option += "-" + req.sectional_strategy.replace("_", "-")
        cand = Candidate(strategy, option, "infeasible")
        if strategy not in STRATEGY_LABELS:
            cand.reason = f"unknown strategy {strategy!r}; known: {', '.join(STRATEGY_LABELS)}"
            return cand

        use_2d = (
            strategy in (STRATEGY_CORRIDOR_FREE, STRATEGY_OPEN_PLAN)
            or (req.proposal is not None)
            or getattr(opts, "force_2d", False)
            or bool(getattr(opts, "stair_position", None))
            or bool(getattr(opts, "outdoor_links", None))
        )
        if use_2d:
            if req.sectional_strategy is not None:
                cand.reason = (
                    "sectional intent currently requires a bar massing; "
                    "2D placement has fixed stacked levels and cannot solve this intent"
                )
                return cand
            try:
                sol2d = solve_2d_placement(
                    req.program,
                    req.site,
                    frame,
                    opts,
                    strategy=strategy,
                    proposal=req.proposal,
                )
            except (Infeasible, Solve2DFailed) as exc:
                cand.attempts.append(f"2D placement: {exc}")
                cand.reason = f"2D placement infeasible: {exc}"
                return cand

            model = assemble_2d(
                sol2d,
                req.site,
                frame,
                ground,
                req.program,
                actor=GENERATOR_ACTOR,
                model_id=f"house-{option.removeprefix('concept-')}",
                name=f"{STRATEGY_LABELS[strategy]}",
                site_ref=req.site_ref,
                program_ref=req.program_ref,
            )
            findings = check_model(model, req.site, req.program)
            record = GenerationRecord(
                generator=GENERATOR,
                generator_version=GENERATOR_VERSION,
                solver="ortools-cp-sat-nooverlap2d",
                solver_version=ortools.__version__,
                solver_status=sol2d.status,
                objective=float(sol2d.objective),
                seed=req.seed,
                deterministic_time_limit=req.deterministic_time,
                parameters={
                    "strategy": strategy,
                    "engine": "2d_nooverlap",
                    "circulation_share": sol2d.circulation_share,
                    "platform": sol2d.platform_info,
                    "deterministic_time": sol2d.deterministic_time,
                    "wall_time_s": sol2d.wall_time_s,
                    "optimised_objectives": ",".join(sol2d.optimised_objectives),
                    **({"proposal_id": req.proposal.id} if req.proposal else {}),
                },
                placements=[
                    RoomPlacement(
                        space_id=r.space_id,
                        bar_id="wing-main",
                        row_id=r.level_id,
                        start_m=from_dm(r.u0),
                    )
                    for r in [*sol2d.rooms, *sol2d.circulation_rooms]
                ],
                revision_ops=list(req.revision_ops),
            )
            cand.plan = PlanVersion(
                option_id=option,
                label=f"{STRATEGY_LABELS[strategy]}",
                strategy=strategy,
                parent=req.parent,
                change_request=req.change_request,
                model=model,
                generation=record,
                provenance=Provenance(
                    created_at=req.created_at,
                    created_by=GENERATOR_ACTOR,
                    method="cpsat_2d_placement",
                    tool=GENERATOR,
                    tool_version=GENERATOR_VERSION,
                    inputs=[
                        r
                        for r in (req.site_ref, req.program_ref, req.proposal_ref, *req.inputs)
                        if r is not None
                    ],
                    notes=(
                        "Generated by a constraint solver from the program; a design exploration, "
                        "not a reviewed or engineered design."
                    ),
                ),
            )
            cand.status = "generated"
            cand.findings = findings
            _explain_level_count(cand.plan, req.program)
            return cand

        best = None
        for depths in req.depth_patterns or _patterns(strategy, rooms):
            tag = f"rows {from_dm(depths[0]):g}/{from_dm(depths[1]):g} m"
            try:
                m = build_massing(strategy, ctx, depths)
                from .terrain_levels import configure_section

                configure_section(m, req.sectional_strategy)
                opts.terrain_context = ctx
                opts.sectional_strategy = req.sectional_strategy
                sol = solve(m, rooms, opts)
            except (Infeasible, SolveFailed) as exc:
                cand.attempts.append(f"{tag}: {exc}")
                continue
            asm = assemble(
                m,
                sol,
                rooms,
                frame,
                ground,
                req.program,
                req.site,
                model_id=f"house-{option.removeprefix('concept-')}",
                name=f"{STRATEGY_LABELS[strategy]}",
                site_ref=req.site_ref,
                program_ref=req.program_ref,
                actor=GENERATOR_ACTOR,
            )
            findings = check_model(asm.model, req.site, req.program)
            n_err = len(errors(findings))
            cand.attempts.append(
                f"{tag}: {sol.status}, objective {sol.objective:.0f}, {n_err} integrity error(s)"
            )
            key = (n_err, sol.objective)
            if best is None or key < best[0]:
                best = (key, m, sol, asm, findings)
        if best is None:
            cand.reason = "; ".join(cand.attempts) or "no attempt"
            return cand
        _, m, sol, asm, findings = best
        record = GenerationRecord(
            generator=GENERATOR,
            generator_version=GENERATOR_VERSION,
            solver="ortools-cp-sat",
            solver_version=ortools.__version__,
            solver_status=sol.status,
            objective=float(sol.objective),
            seed=req.seed,
            deterministic_time_limit=req.deterministic_time,
            parameters={
                **m.params,
                **{f"{b}_start_m": from_dm(v) for b, v in sol.bar_start.items()},
                **{f"{b}_length_m": from_dm(v) for b, v in sol.bar_length.items()},
                **({"proposal_id": req.proposal.id} if req.proposal else {}),
            },
            placements=[
                RoomPlacement(
                    space_id=s.id, bar_id=s.bar_id, row_id=s.row_id, start_m=from_dm(s.start_dm)
                )
                for s in asm.spaces
                if s.bar_id is not None and s.row_id is not None
            ],
            revision_ops=list(req.revision_ops),
        )
        cand.plan = PlanVersion(
            option_id=option,
            label=f"{STRATEGY_LABELS[strategy]}",
            strategy=strategy,
            parent=req.parent,
            change_request=req.change_request,
            provenance=Provenance(
                created_at=req.created_at,
                created_by=GENERATOR_ACTOR,
                method="cpsat_generation",
                tool=GENERATOR,
                tool_version=GENERATOR_VERSION,
                inputs=[
                    r
                    for r in (req.site_ref, req.program_ref, req.proposal_ref, *req.inputs)
                    if r is not None
                ],
                notes="Generated by a constraint solver from the program; a design exploration, "
                "not a reviewed or engineered design.",
            ),
            model=asm.model,
            generation=record,
        )
        cand.findings = findings
        cand.status = "generated"
        _explain_level_count(cand.plan, req.program)
        return cand


def _explain_level_count(plan: PlanVersion, program: SpaceProgram) -> None:
    """Record departures from owner intent alongside the generated geometry (S10-12)."""
    requested, actual = program.levels, len(plan.model.levels)
    if requested is None or requested == actual:
        return
    if plan.strategy == STRATEGY_LINEAR:
        reason = "The linear strategy places all rooms in one bar on a single level."
    elif plan.strategy == STRATEGY_COMPACT:
        reason = "The compact strategy requires at least two stacked levels."
    else:
        reason = (
            "This strategy derives its floor levels from the massing and terrain; "
            "split floor levels need not represent full stacked storeys."
        )
    plan.model.assumptions.append(
        Assumption(
            id="asm-gen-requested-levels",
            statement=f"Requested storeys: {requested}; generated floor levels: {actual}. "
            + reason
            + " The requested storey count is not enforced by this strategy; owner review needed.",
            basis="program.levels compared with canonical model.levels",
            made_by=GENERATOR_ACTOR,
            affects=[lv.id for lv in plan.model.levels],
            confirm_with="owner",
        )
    )
