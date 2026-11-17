"""The engine seam inside the plan generator (ADR 0032).

A stub engine stands in for the bar and 2D engines: the routing rule and the rules for the
generation record and the Plan version are tested without solving anything.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from house_ai.domain.plan import PlanVersion, RoomPlacement
from house_ai.domain.program import SpaceProgram
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import ArtifactKind, ArtifactRef
from house_ai.domain.site import Site
from house_ai.generation.engines import EngineContext, EngineKind, Layout, NoLayout
from house_ai.generation.generator import CpSatPlanGenerator, GenerationRequest
from house_ai.generation.solver import SolverOptions
from house_ai.storage.hashing import load_document

WHEN = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)
HILLSIDE = Path(__file__).resolve().parents[1] / "examples" / "projects" / "synthetic-hillside"
#: A committed exploratory concept: one bar on one level (the program asks for two storeys).
LINEAR = HILLSIDE / "concepts" / "concept-linear" / "exploratory" / "plan.json"


class StubEngine:
    """Records what it was asked and answers with fixed layouts, or no layout."""

    def __init__(self, kind: str, layouts: list[Layout] | None = None) -> None:
        self.kind = kind
        self.layouts = layouts
        self.calls: list[tuple[str, EngineContext]] = []

    def lay_out(self, strategy: str, ctx: EngineContext) -> list[Layout] | NoLayout:
        self.calls.append((strategy, ctx))
        if self.layouts is None:
            return NoLayout(f"{self.kind} engine asked for {strategy}")
        return self.layouts


def _inputs() -> tuple[Site, SpaceProgram]:
    return (
        Site.model_validate(load_document(HILLSIDE / "site.yaml")),
        SpaceProgram.model_validate(load_document(HILLSIDE / "space_program.yaml")),
    )


def _request(**kw) -> GenerationRequest:
    site, program = _inputs()
    return GenerationRequest(
        site=site,
        program=program,
        constraints=None,
        site_ref=None,
        program_ref=None,
        created_at=WHEN,
        **kw,
    )


def _stubs(bar_layouts: list[Layout] | None = None) -> dict[EngineKind, StubEngine]:
    return {
        EngineKind.BAR: StubEngine("bar", bar_layouts),
        EngineKind.TWO_D: StubEngine("2d"),
    }


def _proposal() -> ConceptProposal:
    return ConceptProposal(
        id="prop-stub",
        project_id="synthetic-hillside",
        name="Stub proposal",
        intent="Route a bar strategy to the 2D engine",
    )


@pytest.mark.parametrize(
    ("strategy", "extra", "engine"),
    [
        ("linear", {}, "bar"),
        ("split_walkout", {}, "bar"),
        ("corridor_free", {}, "2d"),
        ("open_plan", {}, "2d"),
        ("linear", {"proposal": "yes"}, "2d"),
        ("compact", {"stair_position": "perimeter"}, "2d"),
        ("compact", {"outdoor_links": [("sp-living", "terrace")]}, "2d"),
    ],
)
def test_a_strategy_is_routed_to_one_engine(strategy, extra, engine) -> None:
    kw: dict = {"strategies": [strategy]}
    if "proposal" in extra:
        kw["proposal"] = _proposal()
    opts = {k: v for k, v in extra.items() if k != "proposal"}
    if opts:
        kw["solver"] = SolverOptions(**opts)
    engines = _stubs()
    [cand] = CpSatPlanGenerator(engines=engines).candidates(_request(**kw))
    assert cand.status == "infeasible"
    assert cand.reason == f"{engine} engine asked for {strategy}"
    asked = {kind.value: [s for s, _ in stub.calls] for kind, stub in engines.items()}
    assert asked == {"bar": [strategy] if engine == "bar" else [],
                     "2d": [strategy] if engine == "2d" else []}


def test_strategies_keep_their_order_and_an_unknown_one_reaches_no_engine() -> None:
    engines = _stubs()
    cands = CpSatPlanGenerator(engines=engines).candidates(
        _request(strategies=["open_plan", "nowhere", "linear"])
    )
    assert [c.strategy for c in cands] == ["open_plan", "nowhere", "linear"]
    assert [c.option_id for c in cands] == [
        "concept-open-plan", "concept-nowhere", "concept-linear",
    ]
    assert cands[1].reason.startswith("unknown strategy 'nowhere'")
    assert [s for s, _ in engines[EngineKind.BAR].calls] == ["linear"]
    assert [s for s, _ in engines[EngineKind.TWO_D].calls] == ["open_plan"]


def _layout(model, objective: float, *, status: str = "OPTIMAL") -> Layout:
    return Layout(
        model=model,
        solver="stub-solver",
        solver_version="9.9",
        status=status,
        objective=objective,
        parameters={"strategy": "linear", "b0_start_m": 6.1},
        placements=[RoomPlacement(space_id="sp-living", bar_id="b0", row_id="b0-front",
                                  start_m=0.0)],
        method="stub_method",
    )


def test_the_generator_keeps_the_cleanest_cheapest_layout_and_records_it() -> None:
    model = PlanVersion.model_validate_json(LINEAR.read_text()).model
    model.assumptions = [a for a in model.assumptions if a.id != "asm-gen-requested-storeys"]
    broken = model.model_copy(update={"openings": []})  # every Space unreachable
    layouts = [_layout(broken, 1.0), _layout(model, 9.0, status="FEASIBLE"), _layout(model, 7.0)]
    parent = ArtifactRef(kind=ArtifactKind.PLAN, id="concept-linear", version=1, sha256="a" * 64)
    req = _request(
        strategies=["linear"],
        seed=3,
        deterministic_time=2.5,
        revision_ops=["area:pi-kitchen=16"],
        parent=parent,
        option_id="concept-linear",
    )
    [cand] = CpSatPlanGenerator(engines=_stubs(layouts)).candidates(req)
    assert cand.status == "generated" and cand.valid
    plan = cand.plan
    g = plan.generation
    # The cheapest integrity-clean layout wins over a cheaper broken one.
    assert (g.objective, g.solver_status) == (7.0, "OPTIMAL")
    assert (g.generator, g.generator_version) == ("house-ai-cpsat-bars", "0.2.0")
    assert (g.solver, g.solver_version) == ("stub-solver", "9.9")
    assert (g.seed, g.deterministic_time_limit) == (3, 2.5)
    assert g.parameters == {"strategy": "linear", "b0_start_m": 6.1}
    assert [p.space_id for p in g.placements] == ["sp-living"]
    assert g.revision_ops == ["area:pi-kitchen=16"]
    assert (plan.option_id, plan.strategy, plan.label) == (
        "concept-linear", "linear", "Linear bar along the contours"
    )
    assert plan.parent == parent
    assert plan.provenance.method == "stub_method"
    assert plan.provenance.tool == "house-ai-cpsat-bars"
    assert plan.provenance.created_at == WHEN
    # One level for a program asking for two storeys: the generator says so.
    [note] = [a for a in plan.model.assumptions if a.id == "asm-gen-requested-storeys"]
    assert "Requested storeys: 2; this plan option has 1 storey(s) on 1 level(s)." in note.statement
    assert "one bar on a single level" in note.statement


def test_the_proposal_id_is_recorded_after_the_engine_parameters() -> None:
    model = PlanVersion.model_validate_json(LINEAR.read_text()).model
    engines = {
        EngineKind.BAR: StubEngine("bar"),
        EngineKind.TWO_D: StubEngine("2d", [_layout(model, 4.0)]),
    }
    [cand] = CpSatPlanGenerator(engines=engines).candidates(
        _request(strategies=["linear"], proposal=_proposal())
    )
    assert cand.option_id == "concept-linear-prop-stub"
    assert list(cand.plan.generation.parameters) == ["strategy", "b0_start_m", "proposal_id"]
    assert cand.plan.generation.parameters["proposal_id"] == "prop-stub"


def test_every_strategy_is_infeasible_when_the_site_has_no_design_frame() -> None:
    site, program = _inputs()
    site = site.model_copy(
        update={"coordinates": site.coordinates.model_copy(update={"local": None})}
    )
    engines = _stubs()
    cands = CpSatPlanGenerator(engines=engines).candidates(
        GenerationRequest(site=site, program=program, constraints=None, site_ref=None,
                          program_ref=None, created_at=WHEN, strategies=["linear", "open_plan"])
    )
    assert [c.status for c in cands] == ["infeasible", "infeasible"]
    assert engines[EngineKind.BAR].calls == engines[EngineKind.TWO_D].calls == []
