"""End-to-end synthetic workflow tests for the four canonical agent skills.

Verifies that the command sequences and boundaries documented in:
  - site-survey-review
  - architectural-programming
  - generate-concepts
  - critique-plan
execute offline on synthetic data with zero network access and enforce human gates.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from house_ai.cli.main import main
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, DataClassification
from house_ai.domain.units import LengthUnit
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.evaluation.grounding import collect_canonical_ids, validate_critique_grounding
from house_ai.orchestration.site_ingestion import SiteConfirmation, confirm_site
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore

from .conftest import AGENT, HUMAN, SURVEY_DXF, SURVEY_LAYERS

REPO = Path(__file__).resolve().parent.parent
OWNER = Actor(kind=ActorKind.HUMAN, id="test-owner")
AGENT_ACTOR = "agent:gemini"


def test_site_survey_review_skill_workflow(tmp_path: Path, capsys):
    """Test the complete site-survey-review skill command sequence."""
    out_dir = tmp_path / "inspection"
    proj_dir = tmp_path / "test-site-proj"

    # 1. Inspect survey CAD files (read-only)
    rc = main(["site", "inspect", str(SURVEY_DXF), "--out", str(out_dir)])
    assert rc == 0
    assert (out_dir / "inspection.json").is_file()
    assert (out_dir / "inspection.md").is_file()

    # 2. Ingest survey into a new project
    store = ProjectStore.init(
        proj_dir,
        project_id="test-site-proj",
        name="Test Site Project",
        classification=DataClassification.SYNTHETIC,
        actor=HUMAN,
    )
    capsys.readouterr()
    rc = main(
        [
            "source",
            "add",
            str(proj_dir),
            str(SURVEY_DXF),
            "--classification",
            "synthetic",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    # The skill tells the agent to pass the id printed here, not the file path.
    source_id = capsys.readouterr().out.split()[1].rstrip(":")
    assert [r.id for r in store.refs(ArtifactKind.SOURCE_DOCUMENT)] == [source_id]

    rc = main(
        [
            "site",
            "ingest",
            str(proj_dir),
            "--source",
            source_id,
            "--layers",
            str(SURVEY_LAYERS),
            "--actor",
            AGENT_ACTOR,
        ]
    )

    assert rc == 0
    assert store.latest(ArtifactKind.SITE, "site") is not None
    assert store.latest(ArtifactKind.CAD_IMPORT, f"cad-{source_id}") is not None

    # 3. Transition to SITE_INGESTION and assess site blockers
    rc = main(
        [
            "workflow",
            "transition",
            str(proj_dir),
            "SITE_INGESTION",
            "--reason",
            "ingesting survey",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    rc = main(["workflow", "assess-site", str(proj_dir), "--id", "site", "--actor", AGENT_ACTOR])
    assert rc == 0



    # 4. Generate site validation report and SVG
    report_dir = proj_dir / "reviews" / "site-v1"
    rc = main(["site", "report", str(proj_dir), "--out", str(report_dir)])
    assert rc == 0
    assert (report_dir / "site-report.md").is_file()
    assert (report_dir / "site.svg").is_file()

    # 5. Request the human site gate review (an agent may request, never approve)
    rc = main(
        [
            "workflow",
            "request-approval",
            str(proj_dir),
            "site",
            "--id",
            "site",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    requests = [e for e in store.events() if e.type.value == "approval_requested"]
    assert [e.payload["gate"] for e in requests] == ["site"]
    assert requests[0].actor.id == "gemini"

    # 6. Verify project integrity
    rc = main(["project", "verify", str(proj_dir)])
    assert rc == 0

    # 7. Human boundary: agent cannot confirm site or approve site gate
    rc = main(
        [
            "site",
            "confirm",
            str(proj_dir),
            "--units",
            "m",
            "--confirmer",
            "agent:gemini",
        ]
    )
    assert rc == 2  # Refused non-interactively or agent approver


    rc = main(
        [
            "workflow",
            "approve",
            str(proj_dir),
            "site",
            "--id",
            "site",
            "--version",
            "1",
            "--approver",
            "agent:gemini",
        ]
    )
    assert rc == 2  # Refused non-interactively or agent approver


def test_architectural_programming_skill_workflow(tmp_path: Path):
    """Test the complete architectural-programming skill command sequence."""
    proj_dir = tmp_path / "test-prog-proj"
    store = ProjectStore.init(
        proj_dir,
        project_id="test-prog-proj",
        name="Test Programming Project",
        classification=DataClassification.SYNTHETIC,
        actor=HUMAN,
    )
    source_ref = store.add_source(
        SURVEY_DXF, HUMAN, classification=DataClassification.SYNTHETIC
    )

    # Ingest and confirm site via human fixture so site gate is passed
    rc = main(
        [
            "site",
            "ingest",
            str(proj_dir),
            "--source",
            source_ref.id,
            "--layers",
            str(SURVEY_LAYERS),
            "--actor",
            AGENT_ACTOR,
        ]
    )

    assert rc == 0

    conf = SiteConfirmation(
        units=LengthUnit.METRE,
        elevation_units=LengthUnit.METRE,
        epsg=25832,
        vertical_datum="DHHN2016",
        vertical_epsg=7837,
        boundary_verified=True,
    )
    confirm_site(store, "site", OWNER, conf)
    wf = Workflow(store)
    wf.transition(WorkflowState.SITE_INGESTION, AGENT, "ingesting site")
    wf.approve(Gate.SITE, store.latest(ArtifactKind.SITE, "site"), OWNER, "synthetic site verified")


    # 1. Transition project to INTERVIEWING and start interview
    rc = main(
        [
            "workflow",
            "transition",
            str(proj_dir),
            "INTERVIEWING",
            "--reason",
            "starting interview",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    rc = main(["interview", "start", str(proj_dir), "--json", "--actor", AGENT_ACTOR])
    assert rc == 0

    # 2. Answer question with verbatim English words and structured inferences
    rc = main(
        [
            "interview",
            "answer",
            str(proj_dir),
            "We are 2 adults, and we want a modern hillside house with 3 beds and 2 baths.",
            "--question",
            "q-style",
            "--set",
            "adults=2",
            "--set",
            "bedrooms=3",
            "--set",
            "bathrooms=2",
            "--set",
            "parking_type=garage",
            "--set",
            "cars=2",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0


    # 3. Adaptive follow-up with Persian verbatim words
    rc = main(
        [
            "interview",
            "answer",
            str(proj_dir),
            "ورودی اصلی و پارکینگ هم‌سطح جاده باشد و نشیمن یک طبقه پایین‌تر رو به منظره.",
            "--question",
            "q-followup-road",
            "--question-text",
            "Should the garage sit at road level?",
            "--topic",
            "site",
            "--set",
            "floors=2",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0

    # 4. Confirm inferences with owner words
    rc = main(
        [
            "interview",
            "confirm",
            str(proj_dir),
            "--text",
            "Yes, exactly as recorded.",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0

    # 5. Build space program
    design_dir = proj_dir / "design"
    rc = main(
        [
            "program",
            "build",
            str(proj_dir),
            "--out",
            str(design_dir),
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    assert (design_dir / "space_program.yaml").is_file()
    assert (design_dir / "design_brief.yaml").is_file()
    assert (design_dir / "program-review.md").is_file()

    # 6. Request program review
    rc = main(["program", "review", str(proj_dir), "--actor", AGENT_ACTOR])
    assert rc == 0

    # 7. Human boundary: agent cannot approve program gate
    rc = main(
        [
            "workflow",
            "approve",
            str(proj_dir),
            "program",
            "--id",
            "program",
            "--version",
            "1",
            "--approver",
            "agent:gemini",
        ]
    )
    assert rc == 2


def test_generate_concepts_and_critique_skills_workflow(tmp_path: Path):
    """Test the complete generate-concepts and critique-plan skill command sequence."""
    proj_dir = tmp_path / "synthetic-hillside"
    # Load synthetic-hillside fixture
    rc = main(
        [
            "example",
            "load",
            str(proj_dir),
            "--name",
            "synthetic-hillside",
            "--project-id",
            "synthetic-hillside",
            "--actor",
            "human:example",
        ]
    )
    assert rc == 0
    store = ProjectStore(proj_dir)

    # 1. Exploratory generation (works before gate approvals, stores nothing)
    exploratory_dir = tmp_path / "exploratory-preview"
    rc = main(
        [
            "plan",
            "generate",
            str(proj_dir),
            "--exploratory",
            "--out",
            str(exploratory_dir),
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    assert (exploratory_dir / "comparison.md").is_file()
    # Confirm store untouched by exploratory generation
    assert store.refs(ArtifactKind.PLAN) == []

    # critique-plan before the gates: ground a critique of the exploratory concept
    plan_json = exploratory_dir / "concept-split-walkout" / "exploratory" / "plan.json"
    critique = tmp_path / "critique.md"
    critique.write_text(
        "`sp-kitchen` (`pi-kitchen`) is on `lv-entry` in `z-day`; the bedrooms in `z-night` "
        "step down to `lv-down-300`. Proposal: `--separate pi-bed-main,pi-bed-child-1`.\n",
        encoding="utf-8",
    )
    assert main(["plan", "ground", str(plan_json), str(critique)]) == 0
    critique.write_text("`level-entry` and `pi-office` do not exist.\n", encoding="utf-8")
    assert main(["plan", "ground", str(plan_json), str(critique)]) == 1

    # Every entity ID the concept and critique skills cite exists in synthetic-hillside
    program_ref = store.latest(ArtifactKind.SPACE_PROGRAM, "program")
    valid = collect_canonical_ids(json.loads(plan_json.read_text(encoding="utf-8")))
    valid |= collect_canonical_ids(store.get(program_ref))
    for skill in ("generate-concepts", "critique-plan"):
        text = (REPO / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        cited = set(re.findall(r"\b(?:pi|sp|z|lv|level|adj|rel)-[a-z0-9-]*[a-z0-9]\b", text))
        assert cited, skill
        assert cited <= valid, f"{skill} cites unknown IDs {sorted(cited - valid)}"

    # Approve site and program via human fixture for gated generation
    wf = Workflow(store)
    wf.approve(Gate.SITE, store.latest(ArtifactKind.SITE, "site"), OWNER, "site approved")
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview done")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "program ready")
    wf.approve(
        Gate.PROGRAM,
        store.latest(ArtifactKind.SPACE_PROGRAM, "program"),
        OWNER,
        "program approved",
    )


    # 2. Gated generation (stores concepts)
    rc = main(
        [
            "plan",
            "generate",
            str(proj_dir),
            "--strategy",
            "split_walkout",
            "--seed",
            "1",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    plans = store.latest_of_kind(ArtifactKind.PLAN)
    assert len(plans) >= 1
    concept_id = plans[0].id

    # 3. List and compare concepts
    rc = main(["plan", "list", str(proj_dir)])
    assert rc == 0
    rc = main(["plan", "compare", str(proj_dir)])
    assert rc == 0

    # 4. Critique grounding check: valid IDs pass, invalid IDs fail
    program = store.get(store.latest(ArtifactKind.SPACE_PROGRAM, "program"))
    valid_ids = [item.id for item in program.items[:3]]

    # Grounded critique with valid IDs: passes
    grounding_errors = validate_critique_grounding(valid_ids, program)
    assert grounding_errors == []

    # Ungrounded critique with hallucinated IDs: rejected!
    hallucinated_ids = ["pi-nonexistent-ballroom", "z-imaginary-galaxy"]
    grounding_errors = validate_critique_grounding(hallucinated_ids, program)
    assert len(grounding_errors) == 2
    assert "Unknown entity ID 'pi-nonexistent-ballroom'" in grounding_errors[0]

    # 5. Revise concept with structured operations
    rc = main(
        [
            "plan",
            "revise",
            str(proj_dir),
            concept_id,
            "Increase kitchen area and rethink night zone",
            "--area",
            f"{valid_ids[0]}=18",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0

    # Verify revised plan version exists
    revised_version = store.latest(ArtifactKind.PLAN, concept_id)
    assert revised_version.version == 2

    # 6. Request plan review
    rc = main(["plan", "review", str(proj_dir), concept_id, "--actor", AGENT_ACTOR])
    assert rc == 0

    # 7. Human boundary: agent cannot approve plan gate
    rc = main(
        [
            "workflow",
            "approve",
            str(proj_dir),
            "plan",
            "--id",
            concept_id,
            "--version",
            "2",
            "--approver",
            "agent:gemini",
        ]
    )
    assert rc == 2
