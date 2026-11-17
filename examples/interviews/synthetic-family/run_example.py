"""Run the synthetic interview end to end and write the expected outputs.

    .venv/bin/python examples/interviews/synthetic-family/run_example.py [--check]

A fictional family is interviewed on the synthetic survey. The scripted owner
is the synthetic actor ``human:example-owner`` (as in the tests); in a real
project only the owner answers, in their own terminal. Writes ``expected/``:
interview-summary.md, design_brief.yaml, space_program.yaml, assumptions.yaml,
open_questions.yaml and program-review.md. ``--check`` compares instead.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from house_ai.cad.layers import load_layer_mapping
from house_ai.domain.provenance import Actor, ActorKind, DataClassification
from house_ai.domain.units import LengthUnit
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.interview import InterviewService
from house_ai.orchestration.site_ingestion import SiteConfirmation, confirm_site, ingest_site
from house_ai.orchestration.workflow import Workflow
from house_ai.program.report import program_markdown
from house_ai.storage import ProjectStore

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SURVEY = REPO / "examples" / "surveys" / "synthetic"
OWNER = Actor(kind=ActorKind.HUMAN, id="example-owner")
AGENT = Actor(kind=ActorKind.AGENT, id="example-agent")


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


def run(root: Path) -> dict[str, str]:
    store = ProjectStore.init(root, project_id="synthetic-family", name="Synthetic family",
                              classification=DataClassification.SYNTHETIC, actor=OWNER,
                              clock=Clock())  # fmt: skip
    doc = store.add_source(
        SURVEY / "survey.dxf", OWNER, classification=DataClassification.SYNTHETIC
    )
    wf = Workflow(store)
    wf.transition(WorkflowState.SITE_INGESTION, AGENT, "survey received")
    ingest_site(store, doc.id, load_layer_mapping(SURVEY / "layers.yaml"), AGENT)
    ref = confirm_site(store, "site", OWNER, SiteConfirmation(
        units=LengthUnit.METRE, elevation_units=LengthUnit.METRE, local_only=True,
        vertical_datum="synthetic benchmark", vertical_local=True,
        boundary_verified=True))  # fmt: skip
    # Local-only keeps these outputs independent of the PROJ version (the program pins the
    # site's content hash, and grid-to-true-north comes from PROJ).
    wf.approve(Gate.SITE, ref, OWNER, "synthetic owner approves the synthetic site")
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "start the interview")
    svc = InterviewService(store)
    svc.start(AGENT)
    for step in yaml.safe_load((HERE / "answers.yaml").read_text())["answers"]:
        prompt = svc.pending()
        assert prompt is not None and prompt.id == step["question"], (prompt, step)
        svc.answer(step["answer"], OWNER)
    svc.confirm(OWNER)
    build, gate = svc.review_program(AGENT)
    assert gate.blockers == [], gate.open_reasons

    def dump(model) -> str:
        return yaml.safe_dump(model.model_dump(mode="json"), sort_keys=False, allow_unicode=True)

    return {
        "interview-summary.md": svc.summary(),
        "design_brief.yaml": dump(svc.brief()),
        "space_program.yaml": dump(build.result.program),
        "assumptions.yaml": dump(build.result.assumptions),
        "open_questions.yaml": dump(build.result.open_questions),
        "program-review.md": program_markdown(build.result.program, svc.brief(), build.findings,
                                              build.result.assumptions,
                                              build.result.open_questions),
    }  # fmt: skip


def main(argv: list[str]) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        files = run(Path(tmp) / "project")
    out = HERE / "expected"
    if "--check" in argv:
        stale = [n for n, t in files.items()
                 if not (out / n).is_file() or (out / n).read_text(encoding="utf-8") != t]
        if stale:
            print("stale: " + ", ".join(stale) + "; run run_example.py")  # noqa: T201
            return 1
        return 0
    out.mkdir(exist_ok=True)
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
        print(f"wrote {out / name}")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
