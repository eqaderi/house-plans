"""End-to-end synthetic workflow tests for the canonical agent skills.

Verifies that the command sequences and boundaries documented in:
  - site-survey-review
  - architectural-programming
  - generate-plan-options
  - critique-plan
execute offline on synthetic data with zero network access and enforce human gates.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from house_ai.cli.main import main
from house_ai.constants.evaluations import REQUEST_NOT_MET_PREFIX, REQUESTED_AREA_TOLERANCE_M2
from house_ai.constants.skills import CANONICAL_SKILLS_DIR
from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, DataClassification
from house_ai.domain.units import LengthUnit
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.site import SiteService
from house_ai.orchestration.site_ingestion import SiteConfirmation
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore
from house_ai.validation.grounding import collect_canonical_ids, validate_cited_ids

from .conftest import AGENT, HUMAN, SURVEY_DXF, SURVEY_LAYERS, tree

REPO = Path(__file__).resolve().parent.parent
OWNER = Actor(kind=ActorKind.HUMAN, id="test-owner")
AGENT_ACTOR = "agent:gemini"


def _load_hillside(proj_dir: Path) -> ProjectStore:
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
    return ProjectStore(proj_dir)


def _approve_site_and_program(store: ProjectStore) -> None:
    """The owner's approvals, through the library (the "human fixture")."""
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


@pytest.fixture(scope="module")
def walkout(tmp_path_factory) -> ProjectStore:
    """Gates approved by the owner, then `plan generate --strategy split_walkout --seed 1`.

    Never written to: each test works on its own copy (``_copy``).
    """
    store = _load_hillside(tmp_path_factory.mktemp("walkout") / "synthetic-hillside")
    _approve_site_and_program(store)
    rc = main(
        [
            "plan",
            "generate",
            str(store.root),
            "--strategy",
            "split_walkout",
            "--seed",
            "1",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    assert [r.id for r in store.latest_of_kind(ArtifactKind.PLAN)] == ["concept-split-walkout"]
    return store


def _copy(store: ProjectStore, tmp_path: Path) -> ProjectStore:
    return ProjectStore(shutil.copytree(store.root, tmp_path / store.root.name))


def _assert_refused_as_human_only(store: ProjectStore, argv: list[str], capsys, noun: str):
    """An agent's shell gets exit 2 and the human-only refusal; the store is unchanged."""
    events = len(store.events())
    capsys.readouterr()
    assert main(argv) == 2
    err = capsys.readouterr().err
    assert f"{noun} needs an interactive terminal and a typed confirmation from a human" in err
    assert "Agents must not" in err
    assert len(store.events()) == events


def _assert_kitchen_revision(store: ProjectStore, option_id: str, requested: float) -> None:
    """v2 asks for the kitchen area; it is met within the tolerance or reported as not met."""
    v1_ref, v2_ref = store.refs(ArtifactKind.PLAN, option_id)
    v2 = store.get(v2_ref, PlanVersion)
    assert v2.parent == v1_ref
    op = f"area:pi-kitchen={requested:g}"
    assert v2.generation.revision_ops == [op]
    rev = store.get(store.latest(ArtifactKind.REVISION_REPORT, f"rev-{option_id}-v2"))
    area = v2.model.space("sp-kitchen").area_m2
    not_met = sorted(v for v in rev.new_violations if v.startswith(REQUEST_NOT_MET_PREFIX))
    if area >= requested - REQUESTED_AREA_TOLERANCE_M2:
        assert not_met == []
    else:
        assert not_met == [
            f"{REQUEST_NOT_MET_PREFIX}'{op}' "
            f"(sp-kitchen area {area:.1f} m² < requested {requested:g} m²)"
        ]


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

    # Ingesting started site ingestion and stopped the unconfirmed survey for the owner.
    assert Workflow(store).state is WorkflowState.SITE_NEEDS_CONFIRMATION

    # 3. Re-assess the site against the gate's blockers (moves nothing)
    rc = main(["workflow", "assess-site", str(proj_dir), "--id", "site", "--actor", AGENT_ACTOR])
    assert rc == 0
    assert Workflow(store).state is WorkflowState.SITE_NEEDS_CONFIRMATION



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
    site_v1 = store.latest(ArtifactKind.SITE, "site")
    _assert_refused_as_human_only(
        store,
        ["site", "confirm", str(proj_dir), "--units", "m", "--confirmer", "agent:gemini"],
        capsys,
        "site confirmation",
    )
    assert store.latest(ArtifactKind.SITE, "site") == site_v1  # no confirmed version
    _assert_refused_as_human_only(
        store,
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
        ],
        capsys,
        "approval",
    )
    assert Workflow(store).state is WorkflowState.SITE_NEEDS_CONFIRMATION


def test_architectural_programming_skill_workflow(tmp_path: Path, capsys):
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
    # The owner's confirmation clears every blocker; the site gate is then approvable.
    site_ref = SiteService(store).confirm("site", OWNER, conf).site_ref
    Workflow(store).approve(Gate.SITE, site_ref, OWNER, "synthetic site approved")


    # 1. Start the interview (works in SITE_APPROVED; no transition needed yet)
    assert Workflow(store).state is WorkflowState.SITE_APPROVED
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
            "storeys=2",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0

    # 4. Confirm interpretations with owner words
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

    # 6. Request program review straight from SITE_APPROVED (it makes its own moves)
    assert Workflow(store).state is WorkflowState.SITE_APPROVED
    rc = main(["program", "review", str(proj_dir), "--actor", AGENT_ACTOR])
    assert rc == 0
    assert Workflow(store).state is WorkflowState.PROGRAM_REVIEW

    # 7. Human boundary: agent cannot approve program gate
    _assert_refused_as_human_only(
        store,
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
        ],
        capsys,
        "approval",
    )
    assert Workflow(store).state is WorkflowState.PROGRAM_REVIEW
    assert Gate.PROGRAM not in Workflow(store).status().approvals


def test_generate_plan_options_and_critique_skills_workflow(
    walkout: ProjectStore, tmp_path: Path, capsys
):
    """Test the complete generate-plan-options and critique-plan skill command sequence."""
    store = _load_hillside(tmp_path / "before-gates" / "synthetic-hillside")
    proj_dir = store.root

    # 1. Exploratory generation (works before gate approvals, stores nothing). One strategy
    # is the one the critique below reads; every strategy is solved independently.
    exploratory_dir = tmp_path / "exploratory-preview"
    before = tree(proj_dir)
    rc = main(
        [
            "plan",
            "generate",
            str(proj_dir),
            "--exploratory",
            "--strategy",
            "split_walkout",
            "--out",
            str(exploratory_dir),
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    assert (exploratory_dir / "comparison.md").is_file()
    assert "EXPLORATORY" in (exploratory_dir / "comparison.md").read_text("utf-8")
    # Confirm store untouched by exploratory generation: every file's bytes
    assert store.refs(ArtifactKind.PLAN) == []
    assert tree(proj_dir) == before

    # critique-plan before the gates: ground a critique of the exploratory plan option
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

    # Every entity ID the plan-option and critique skills cite exists in synthetic-hillside
    program_ref = store.latest(ArtifactKind.SPACE_PROGRAM, "program")
    valid = collect_canonical_ids(json.loads(plan_json.read_text(encoding="utf-8")))
    valid |= collect_canonical_ids(store.get(program_ref))
    for skill in ("generate-plan-options", "critique-plan"):
        text = (REPO / CANONICAL_SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
        cited = set(re.findall(r"\b(?:pi|sp|z|lv|level|adj|rel)-[a-z0-9-]*[a-z0-9]\b", text))
        assert cited, skill
        assert cited <= valid, f"{skill} cites unknown IDs {sorted(cited - valid)}"

    # 2. Gated generation (stores plan options): the owner approved site and program, then
    # `plan generate --strategy split_walkout --seed 1` ran (the `walkout` fixture).
    store = _copy(walkout, tmp_path)
    proj_dir = store.root
    plans = store.latest_of_kind(ArtifactKind.PLAN)
    assert [p.id for p in plans] == ["concept-split-walkout"]
    option_id = plans[0].id

    # 3. List and compare plan options
    rc = main(["plan", "list", str(proj_dir)])
    assert rc == 0
    rc = main(["plan", "compare", str(proj_dir)])
    assert rc == 0

    # critique-plan after the gates: ground a critique of the exported stored plan option
    export_dir = tmp_path / "critique-export"
    assert main(["plan", "export", str(proj_dir), option_id, "--out", str(export_dir)]) == 0
    exported = next(export_dir.rglob("plan.json"))
    critique.write_text("`sp-kitchen` on `lv-entry`.\n", encoding="utf-8")
    assert main(["plan", "ground", str(exported), str(critique)]) == 0

    # 4. Critique grounding check: valid IDs pass, invalid IDs fail
    program = store.get(store.latest(ArtifactKind.SPACE_PROGRAM, "program"))
    valid_ids = [item.id for item in program.space_requirements[:3]]

    # Grounded critique with valid IDs: passes
    grounding_errors = validate_cited_ids(valid_ids, program)
    assert grounding_errors == []

    # Ungrounded critique with hallucinated IDs: rejected!
    hallucinated_ids = ["pi-nonexistent-ballroom", "z-imaginary-galaxy"]
    grounding_errors = validate_cited_ids(hallucinated_ids, program)
    assert len(grounding_errors) == 2
    assert "Unknown entity ID 'pi-nonexistent-ballroom'" in grounding_errors[0]

    # 5. Revise the plan option with structured operations
    rc = main(
        [
            "plan",
            "revise",
            str(proj_dir),
            option_id,
            "Increase kitchen area and rethink night zone",
            "--area",
            "pi-kitchen=18",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0

    # Verify revised plan version exists and asks for the kitchen area
    revised_version = store.latest(ArtifactKind.PLAN, option_id)
    assert revised_version.version == 2
    _assert_kitchen_revision(store, option_id, 18)

    # 6. Request plan review
    rc = main(["plan", "review", str(proj_dir), option_id, "--actor", AGENT_ACTOR])
    assert rc == 0

    # 7. Human boundary: agent cannot approve plan gate
    _assert_refused_as_human_only(
        store,
        [
            "workflow",
            "approve",
            str(proj_dir),
            "plan",
            "--id",
            option_id,
            "--version",
            "2",
            "--approver",
            "agent:gemini",
        ],
        capsys,
        "approval",
    )
    assert Gate.PLAN not in Workflow(store).status().approvals


def test_visual_review_skill_workflow(walkout: ProjectStore, tmp_path: Path, capsys):
    """End-to-end synthetic workflow test for the visual-review skill (S5-11)."""
    export_dir = tmp_path / "exported-plan-option"
    bundle_dir = tmp_path / "exported-bundle"

    # Gates approved and split_walkout generated (the `walkout` fixture), on a private copy
    store = _copy(walkout, tmp_path)
    proj_dir = store.root
    plans = store.latest_of_kind(ArtifactKind.PLAN)
    assert [p.id for p in plans] == ["concept-split-walkout"]
    option_id = plans[0].id

    # 1. Export plan option files for visual inspection
    rc = main(["plan", "export", str(proj_dir), option_id, "--out", str(export_dir)])
    assert rc == 0
    plan_json_path = next(export_dir.rglob("plan.json"))
    assert plan_json_path.is_file()

    # 2. Export reviewer bundle
    rc = main(["plan", "export-bundle", str(proj_dir), "--out", str(bundle_dir)])
    assert rc == 0
    assert (bundle_dir / "bundle.json").is_file()

    # 3. Grounded critique check: valid critique citing canonical plan ID
    plan_data = json.loads(plan_json_path.read_text("utf-8"))
    program = store.get(store.latest(ArtifactKind.SPACE_PROGRAM, "program"))
    valid_spaces = [s["id"] for s in plan_data["model"]["spaces"] if s["id"].startswith("sp-")]
    valid_program_items = [item.id for item in program.space_requirements]
    assert len(valid_spaces) > 0
    assert len(valid_program_items) > 0

    valid_critique = tmp_path / "valid_critique.md"
    valid_critique.write_text(
        f"# Visual Review\nInspected `{valid_spaces[0]}` in plan canvas. Proportions are sound.\n",
        encoding="utf-8",
    )
    rc = main(["plan", "ground", str(plan_json_path), str(valid_critique)])
    assert rc == 0

    # 4. Ungrounded critique check: citing invalid element ID is rejected
    invalid_critique = tmp_path / "invalid_critique.md"
    invalid_critique.write_text(
        "# Visual Review\nClash detected on `sp-nonexistent-penthouse`.\n",
        encoding="utf-8",
    )
    rc = main(["plan", "ground", str(plan_json_path), str(invalid_critique)])
    assert rc == 1

    # 5. Revise the plan option from feedback
    rc = main(
        [
            "plan",
            "revise",
            str(proj_dir),
            option_id,
            "Enlarge kitchen for accessibility",
            "--area",
            "pi-kitchen=22",
            "--actor",
            AGENT_ACTOR,
        ]
    )
    assert rc == 0
    assert "pi-kitchen" in valid_program_items
    _assert_kitchen_revision(store, option_id, 22)

    # 6. Human boundary: agent cannot approve plan gate
    _assert_refused_as_human_only(
        store,
        [
            "workflow",
            "approve",
            str(proj_dir),
            "plan",
            "--id",
            option_id,
            "--version",
            "2",
            "--approver",
            "agent:gemini",
        ],
        capsys,
        "approval",
    )
    assert Gate.PLAN not in Workflow(store).status().approvals
