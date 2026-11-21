from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from ortools.sat.python import cp_model

from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import Actor, ActorKind, DataClassification
from house_ai.domain.site import Site
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import load_document

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "projects" / "synthetic-bungalow"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

HUMAN = Actor(kind=ActorKind.HUMAN, id="owner")
AGENT = Actor(kind=ActorKind.AGENT, id="claude-code", provider="anthropic", model="claude-opus-5-5")
SYSTEM = Actor(kind=ActorKind.SYSTEM, id="house-ai")


class SolveMemo:
    """Each CP-SAT model is solved once per test process; a repeat gets the first response.

    The solvers run on one worker with a fixed seed and a deterministic time limit, so an
    identical model with identical parameters has one answer
    (`test_solver_reproducibility_budget` and `test_generation_is_deterministic` solve again
    and compare). Whichever tests share a worker, none of them pays for a problem another has
    solved (ADR 0035). `tests/test_solve_memo.py` checks the replay itself.
    """

    #: Where `CpSolver.solve` keeps its response (its private `__response`).
    RESPONSE = "_CpSolver__response"

    def __init__(self) -> None:
        self.responses: dict[bytes, object] = {}
        self.solved = 0
        self.replayed = 0
        #: Set by the `fresh_solves` marker: solve again, whatever is remembered.
        self.fresh = False
        self._solve = cp_model.CpSolver.solve

    @staticmethod
    def key(solver: cp_model.CpSolver, model: cp_model.CpModel) -> bytes:
        """The model and the solver's parameters, as `tools/solve_fingerprints.py` reads them."""
        return hashlib.sha1((str(model.Proto()) + str(solver.parameters)).encode()).digest()

    def solve(self, solver: cp_model.CpSolver, model: cp_model.CpModel, solution_callback=None):
        if solution_callback is not None:  # a callback must see the search itself
            return self._solve(solver, model, solution_callback)
        key = self.key(solver, model)
        response = None if self.fresh else self.responses.get(key)
        solver.from_memo = response is not None
        if response is None:
            status = self._solve(solver, model)
            self.solved += 1
            # Without the response there is nothing to replay: the next solve is a real one.
            if getattr(solver, self.RESPONSE, None) is not None:
                self.responses[key] = getattr(solver, self.RESPONSE)
            return status
        setattr(solver, self.RESPONSE, response)
        self.replayed += 1
        return response.status


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--fresh-solves",
        action="store_true",
        help="solve every CP-SAT model again; the solve memo answers nothing",
    )


@pytest.fixture(scope="session", autouse=True)
def solve_memo():
    """Installs the `SolveMemo` for this test process."""
    memo = SolveMemo()

    def solve(solver, model, solution_callback=None):
        return memo.solve(solver, model, solution_callback)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cp_model.CpSolver, "solve", solve)
        yield memo


@pytest.fixture(autouse=True)
def _fresh_solves(request, solve_memo):
    """`@pytest.mark.fresh_solves`: solving again is what the test checks.

    `pytest --fresh-solves` does the same for every test, to check the memo changes no result.
    """
    marked = request.node.get_closest_marker("fresh_solves") is not None
    solve_memo.fresh = marked or request.config.getoption("--fresh-solves")
    yield
    solve_memo.fresh = False


class FakeClock:
    """Deterministic clock: each call advances one second."""

    def __init__(self) -> None:
        self.now = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def example_dir() -> Path:
    return EXAMPLE


def example_doc(name: str) -> dict:
    return copy.deepcopy(load_document(EXAMPLE / name))


@pytest.fixture
def site_doc() -> dict:
    return example_doc("site.yaml")


@pytest.fixture
def site(site_doc: dict) -> Site:
    return Site.model_validate(site_doc)


@pytest.fixture
def plan_doc() -> dict:
    return example_doc("plans/plan-a.json")


@pytest.fixture
def plan(plan_doc: dict) -> PlanVersion:
    return PlanVersion.model_validate(plan_doc)


@pytest.fixture
def new_store(tmp_path: Path, clock: FakeClock) -> Callable[..., ProjectStore]:
    counter = iter(range(1000))

    def make(project_id: str = "synthetic-bungalow") -> ProjectStore:
        return ProjectStore.init(
            tmp_path / f"project-{next(counter)}",
            project_id=project_id,
            name="Test project",
            classification=DataClassification.SYNTHETIC,
            actor=HUMAN,
            clock=clock,
        )

    return make


@pytest.fixture
def store(new_store: Callable[..., ProjectStore]) -> ProjectStore:
    return new_store()


# ------------------------------------------------------------ Milestone B survey

SURVEY_DIR = REPO / "examples" / "surveys" / "synthetic"
SURVEY_DXF = SURVEY_DIR / "survey.dxf"
SURVEY_LAYERS = SURVEY_DIR / "layers.yaml"


def survey_module():
    """The synthetic survey generator (ground truth constants and build_survey)."""
    import runpy

    return runpy.run_path(str(SURVEY_DIR / "make_survey.py"))


@pytest.fixture(scope="session")
def survey():
    return survey_module()


@pytest.fixture
def make_survey(tmp_path: Path, survey):
    """Write a variant of the synthetic survey and return its path."""
    counter = iter(range(1000))

    def make(**options) -> Path:
        return survey["build_survey"](tmp_path / f"survey-{next(counter)}.dxf", **options)

    return make


# ------------------------------------------------------------ shared hillside concepts


class HillsideConcepts:
    """Exploratory plan options on synthetic-hillside, each strategy solved once per worker.

    `CpSatPlanGenerator` solves every strategy independently (generator.py `_strategy`), so
    a strategy solved alone gives the same plan as one solved alongside others. Callers get
    deep copies: changing a returned plan or report never leaks into another test.
    """

    def __init__(self, store: ProjectStore):
        from house_ai.orchestration.plans import PlanService

        self.store = store
        self.service = PlanService(store)
        self._solved: dict[str, object] = {}

    def inputs(self):
        return self.service.inputs(exploratory=True)

    def option(self, strategy: str):
        """The `StoredOption` (candidate, report) for one feasible strategy.

        An infeasible strategy raises `PlanWorkflowError` naming its reason, as
        `PlanService.generate` does when no requested strategy produces a layout.
        """
        from house_ai.orchestration.plans import PlanWorkflowError

        if strategy not in self._solved:
            try:
                out = self.service.generate(AGENT, strategies=[strategy], exploratory=True)
                (self._solved[strategy],) = out.options
            except PlanWorkflowError as exc:
                self._solved[strategy] = exc
        solved = self._solved[strategy]
        if isinstance(solved, PlanWorkflowError):
            raise PlanWorkflowError(str(solved))
        return copy.deepcopy(solved)

    def models(self, strategies):
        """{strategy: HouseModel} for the feasible strategies among ``strategies``."""
        from house_ai.orchestration.plans import PlanWorkflowError

        out = {}
        for s in strategies:
            try:
                out[s] = self.option(s).candidate.plan.model
            except PlanWorkflowError:
                continue
        return out


@pytest.fixture(scope="session")
def hillside(tmp_path_factory) -> HillsideConcepts:
    """synthetic-hillside with its site and program approved; never write to its store."""
    from .test_plan_workflow import _approve_site_and_program, _load

    store = _load(tmp_path_factory.mktemp("hillside-shared"))
    _approve_site_and_program(store)
    return HillsideConcepts(store)
