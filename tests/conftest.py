from __future__ import annotations

import copy
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

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
