"""S10-10 (ISS-30, ISS-27): the program names who sleeps where and which cars to park."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from house_ai.domain.program import SpaceProgram
from house_ai.domain.records import AssumptionsFile, OpenQuestionsFile
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.usability import FurnitureUsabilityEvaluator
from house_ai.orchestration.plans import PlanService

from .conftest import AGENT
from .test_plan_workflow import _approve_site_and_program, _load

REPO = Path(__file__).resolve().parents[1]


def _doc(path: str):
    return yaml.safe_load((REPO / path).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("folder", "cars"),
    [
        ("examples/interviews/synthetic-family/expected", 1),
        ("examples/projects/synthetic-hillside", 2),
    ],
)
def test_program_names_beds_and_typical_cars(folder, cars):
    program = SpaceProgram.model_validate(_doc(f"{folder}/space_program.yaml"))
    usability = program.usability
    assert usability.double_bed_space_requirement_ids == ["pi-bed-main"]
    assert usability.single_bed_space_requirement_ids == ["pi-bed-child-1", "pi-bed-child-2"]
    assert [(v.width_m, v.length_m, v.door_side_clearance_m) for v in usability.vehicles] == [
        (1.8, 4.5, 0.6)
    ] * cars
    assert all("assumption" in v.source for v in usability.vehicles)
    assumptions = AssumptionsFile.model_validate(_doc(f"{folder}/assumptions.yaml"))
    assert {"asm-car-size", "asm-beds"} <= {a.id for a in assumptions.assumptions}
    questions = OpenQuestionsFile.model_validate(_doc(f"{folder}/open_questions.yaml"))
    car = next(q for q in questions.questions if q.id == "oq-car-size")
    assert car.blocking is False


def test_bed_and_garage_studies_run_on_generated_plans(tmp_path):
    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    (opt,) = svc.generate(AGENT, strategies=["compact"], exploratory=True).generated
    inp = svc.inputs(exploratory=True)
    result = FurnitureUsabilityEvaluator().evaluate(
        EvaluationContext(opt.candidate.plan.model, inp.site, inp.program, None)
    )
    claims = {m.metric: m for m in result.metrics if m.metric.endswith("_sampled_fit")}
    for name in ("bed_double_sampled_fit", "garage_sampled_fit"):
        assert claims[name].status.value != "not_checked", name
