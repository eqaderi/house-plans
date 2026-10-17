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
