"""Solver-backed multi-concept plan generator.

For each requested strategy the generator chooses an engine (``engines.py``, ADR 0032): the
bar engine or the 2D engine. The engine lays the strategy out and assembles a canonical
:class:`HouseModel` for each attempt; the generator runs :func:`check_model` on each and keeps
the best: the integrity-clean layout with the lowest objective, or, if none is clean, the best
one marked invalid (never silently dropped). A strategy that cannot be laid out at all is
reported with the engine's reason. The generator builds the generation record and the Plan
version for every engine.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime

from house_ai.constants.evaluations import REQUESTED_STOREYS_ASSUMPTION_ID
from house_ai.constants.strategies import (
    STRATEGY_COMPACT,
    STRATEGY_CORRIDOR_FREE,
    STRATEGY_LINEAR,
    STRATEGY_OPEN_PLAN,
)
from house_ai.domain.constraints import (
    ConstraintSet,
    MinAreaRule,
    MinDimensionRule,
    ObjectiveRule,
)
from house_ai.domain.integrity import IntegrityFinding, check_model, errors
from house_ai.domain.plan import ChangeRequest, GenerationRecord, PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import Actor, ActorKind, ArtifactRef, Provenance
from house_ai.domain.records import Assumption
from house_ai.domain.site import Site

from .engines import BarEngine, Engine, EngineContext, EngineKind, Layout, NoLayout, TwoDEngine
from .frame import FrameError, Ground, design_frame, limit_polygon
from .massing import STRATEGY_LABELS, STRATEGY_ORDER
from .solver import SolverOptions

GENERATOR = "house-ai-cpsat-bars"
GENERATOR_VERSION = "0.2.0"
GENERATOR_ACTOR = Actor(kind=ActorKind.SYSTEM, id="house-ai-plan-generator")


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


#: Strategies only the 2D engine lays out (ADR 0013).
TWO_D_STRATEGIES = frozenset({STRATEGY_CORRIDOR_FREE, STRATEGY_OPEN_PLAN})


def route(strategy: str, req: GenerationRequest) -> EngineKind:
    """The engine that lays out ``strategy`` for ``req`` (ADR 0032).

    The 2D engine takes its own strategies, every topology proposal, and any request for a
    stair position or an outdoor link, which only it can place; the bar engine takes the rest.
    """
    opts = req.solver
    if (
        strategy in TWO_D_STRATEGIES
        or req.proposal is not None
        or (opts is not None and (opts.stair_position or opts.outdoor_links))
    ):
        return EngineKind.TWO_D
    return EngineKind.BAR


class CpSatPlanGenerator:
    """Plan options from OR-Tools CP-SAT, one candidate per massing strategy (ADR 0013).

    Each strategy is routed to one engine (ADR 0032); the generator checks every layout the
    engine returns and keeps the integrity-clean one with the lowest objective.
    """

    name = GENERATOR

    def __init__(self, engines: Mapping[EngineKind, Engine] | None = None) -> None:
        self.engines: Mapping[EngineKind, Engine] = engines or {
            EngineKind.BAR: BarEngine(),
            EngineKind.TWO_D: TwoDEngine(),
        }

    def candidates(self, req: GenerationRequest) -> list[Candidate]:
        hard_areas, hard_widths = hard_dimension_bounds(req.constraints)
        proposal_id = req.proposal.id if req.proposal is not None else None
        try:
            frame = design_frame(req.site)
            limit = frame.polygon_to_design(limit_polygon(req.site)[0])
        except FrameError as exc:
            return [
                Candidate(s, req.option_id or option_id_for(s, proposal_id), "infeasible", str(exc))
                for s in (req.strategies or STRATEGY_ORDER)
            ]
        opts = req.solver or SolverOptions()
        opts.min_areas = hard_areas
        opts.min_widths = hard_widths
        opts.seed = req.seed
        opts.deterministic_time = req.deterministic_time
        opts.objective_weights = {**objective_weights(req.constraints), **opts.objective_weights}
        if req.proposal and req.proposal.level_assignments:
            for la in req.proposal.level_assignments:
                opts.level_prefs[la.program_item_id] = la.level_id
        ctx = EngineContext(
            site=req.site,
            program=req.program,
            frame=frame,
            limit=limit,
            ground=Ground(req.site, frame),
            options=opts,
            min_areas=hard_areas,
            min_widths=hard_widths,
            proposal=req.proposal,
            sectional_strategy=req.sectional_strategy,
            depth_patterns=req.depth_patterns,
            site_ref=req.site_ref,
            program_ref=req.program_ref,
            actor=GENERATOR_ACTOR,
        )
        strategies = req.strategies
        if strategies is None and req.proposal and req.proposal.target_strategy:
            strategies = [req.proposal.target_strategy]
        return [self._strategy(strategy, ctx, req) for strategy in strategies or STRATEGY_ORDER]

    def _strategy(self, strategy: str, ctx: EngineContext, req: GenerationRequest) -> Candidate:
        option = req.option_id or option_id_for(
            strategy, req.proposal.id if req.proposal is not None else None
        )
        if req.sectional_strategy and req.option_id is None:
            option += "-" + req.sectional_strategy.replace("_", "-")
        cand = Candidate(strategy, option, "infeasible")
        if strategy not in STRATEGY_LABELS:
            cand.reason = f"unknown strategy {strategy!r}; known: {', '.join(STRATEGY_LABELS)}"
            return cand
        label = STRATEGY_LABELS[strategy]
        engine = self.engines[route(strategy, req)]
        laid = engine.lay_out(
            strategy,
            replace(ctx, model_id=f"house-{option.removeprefix('concept-')}", name=label),
        )
        if isinstance(laid, NoLayout):
            cand.reason = laid.reason
            return cand
        best: tuple[tuple[int, float], Layout, list[IntegrityFinding]] | None = None
        for layout in laid:
            findings = check_model(layout.model, req.site, req.program)
            key = (len(errors(findings)), layout.objective)
            if best is None or key < best[0]:
                best = (key, layout, findings)
        if best is None:
            cand.reason = "no attempt"
            return cand
        _, layout, cand.findings = best
        record = GenerationRecord(
            generator=GENERATOR,
            generator_version=GENERATOR_VERSION,
            solver=layout.solver,
            solver_version=layout.solver_version,
            solver_status=layout.status,
            objective=layout.objective,
            seed=req.seed,
            deterministic_time_limit=req.deterministic_time,
            parameters={
                **layout.parameters,
                **({"proposal_id": req.proposal.id} if req.proposal else {}),
            },
            placements=layout.placements,
            revision_ops=list(req.revision_ops),
        )
        cand.plan = PlanVersion(
            option_id=option,
            label=label,
            strategy=strategy,
            parent=req.parent,
            change_request=req.change_request,
            model=layout.model,
            generation=record,
            provenance=Provenance(
                created_at=req.created_at,
                created_by=GENERATOR_ACTOR,
                method=layout.method,
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
        )
        cand.status = "generated"
        _explain_storey_count(cand.plan, req.program)
        return cand


def _explain_storey_count(plan: PlanVersion, program: SpaceProgram) -> None:
    """Record departures from owner intent alongside the generated geometry (S10-12).

    The program asks for storeys; the plan's levels come from the massing and the
    slope, and its storey count is derived from them (S11-02).
    """
    requested, actual = program.storeys, plan.model.storey_count
    if requested is None or requested == actual:
        return
    if plan.strategy == STRATEGY_LINEAR:
        reason = "The linear strategy places all rooms in one bar on a single level."
    elif plan.strategy == STRATEGY_COMPACT:
        reason = "The compact strategy requires at least two stacked levels."
    else:
        reason = "This strategy derives its levels from the massing and the slope."
    plan.model.assumptions.append(
        Assumption(
            id=REQUESTED_STOREYS_ASSUMPTION_ID,
            statement=f"Requested storeys: {requested}; this plan option has {actual} "
            f"storey(s) on {len(plan.model.levels)} level(s). "
            + reason
            + " The requested storey count is not enforced by this strategy; owner review needed.",
            basis="program.storeys compared with the storeys the model's levels span",
            made_by=GENERATOR_ACTOR,
            affects=[lv.id for lv in plan.model.levels],
            confirm_with="owner",
        )
    )
