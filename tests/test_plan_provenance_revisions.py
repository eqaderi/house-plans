"""Regression coverage for pinned exports and continuing owner revision intent."""

import json
import shutil
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from shapely.geometry import LineString

from house_ai.cli.main import main
from house_ai.constants.evaluations import (
    REGRESSION_VIOLATION_PREFIX,
    REQUEST_NOT_MET_PREFIX,
    REQUESTED_AREA_TOLERANCE_M2,
)
from house_ai.domain.integrity import circulation_graph
from house_ai.domain.model import HouseModel, SpaceFunction, WallKind
from house_ai.domain.plan import ChangeRequestKind, PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.records import AssumptionsFile
from house_ai.domain.revision_ops import parse_operations
from house_ai.domain.site import Site
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.generation.revision import unmet_requests
from house_ai.orchestration.plans import PlanService
from house_ai.storage import ProjectStore

from .conftest import AGENT, HUMAN
from .test_plan_workflow import _approve_site_and_program, _load


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> ProjectStore:
    """synthetic-hillside, gates approved, concept-compact and concept-linear stored once.

    Never written to: a test that revises works on ``_copy``.
    """
    store = _load(tmp_path_factory.mktemp("compact-linear"))
    _approve_site_and_program(store)
    PlanService(store).generate(AGENT, strategies=["compact", "linear"])
    return store


def _copy(generated: ProjectStore, tmp_path: Path) -> ProjectStore:
    return ProjectStore(shutil.copytree(generated.root, tmp_path / generated.root.name))


def _plan(store: ProjectStore, option_id: str, version: int | None = None) -> PlanVersion:
    ref = store.latest(ArtifactKind.PLAN, option_id)
    if version is not None:
        ref = next(r for r in store.refs(ArtifactKind.PLAN, option_id) if r.version == version)
    return store.get(ref, PlanVersion)


def _kitchen(plan: PlanVersion) -> float:
    return plan.model.space("sp-kitchen").area_m2


def _area_not_met(op: str, sid: str, area: float, requested: float) -> str:
    """The finding `plan revise` records for an area request the layout misses."""
    return f"{REQUEST_NOT_MET_PREFIX}'{op}' ({sid} area {area:.1f} m² < requested {requested:g} m²)"


def _not_met(violations: list[str]) -> list[str]:
    return sorted(v for v in violations if v.startswith(REQUEST_NOT_MET_PREFIX))


def _on_an_exterior_wall(model: HouseModel, space_id: str) -> bool:
    """Whether an exterior Wall of the Space's Level runs along its boundary (> 0.5 m)."""
    sp = model.space(space_id)
    edge = sp.boundary.to_shapely().exterior
    return any(
        LineString([w.start, w.end]).buffer(w.thickness_m / 2 + 0.02).intersection(edge).length
        > 0.5
        for w in model.walls
        if w.level_id == sp.level_id and w.kind is WallKind.EXTERIOR
    )


def _outdoor_neighbours(model: HouseModel, space_id: str) -> set[str]:
    """Terraces a passable opening joins to the Space."""
    outdoor = {s.id for s in model.spaces if s.function is SpaceFunction.TERRACE}
    return circulation_graph(model)[space_id] & outdoor


def _unmet(ops: list[str], model, base: PlanVersion, program: SpaceProgram) -> list[str]:
    return unmet_requests(
        parse_operations(ops),
        model,
        program,
        parent_ops=parse_operations(base.generation.revision_ops),
        parent_model=base.model,
    )


def _concept() -> PlanVersion:
    path = (
        Path(__file__).resolve().parents[1]
        / "examples/projects/synthetic-hillside/concepts/concept-compact/exploratory/plan.json"
    )
    return PlanVersion.model_validate_json(path.read_text("utf-8"))


def test_revision_stores_effective_operations_and_new_owner_words(generated, tmp_path):
    store = _copy(generated, tmp_path)
    svc = PlanService(store)
    v1_kitchen = _kitchen(_plan(store, "concept-compact"))
    first = svc.revise(
        "concept-compact", "Please enlarge the kitchen.", AGENT, ops=["area:pi-kitchen=16"]
    )
    second = svc.revise("concept-compact", "Keep that change as it is.", AGENT)
    plan = second.option.candidate.plan
    assert plan.change_request.text == "Keep that change as it is."
    assert plan.parent == first.option.plan_ref
    assert plan.generation.revision_ops == ["area:pi-kitchen=16"]
    assert "revision operation: area:pi-kitchen=16" in second.revision.assumptions
    # Asking for more than the program's kitchen target (and v1's kitchen) yields a kitchen
    # larger than both, and the version that keeps the request keeps it larger.
    items = svc.inputs(False).program.space_requirements
    target = next(i.target_area_m2 for i in items if i.id == "pi-kitchen")
    assert target < 16
    assert _kitchen(first.option.candidate.plan) > max(v1_kitchen, target)
    assert _kitchen(plan) > max(v1_kitchen, target)
    # Met within the tolerance, or reported as not met with the measured area: never silent.
    for res in (first, second):
        area = _kitchen(res.option.candidate.plan)
        met = area >= 16 - REQUESTED_AREA_TOLERANCE_M2
        expected = [] if met else [_area_not_met("area:pi-kitchen=16", "sp-kitchen", area, 16)]
        assert _not_met(res.revision.new_violations) == expected
    assert store.verify() == []


def test_constraint_reuse_requires_identical_pinned_inputs(tmp_path):
    store = _load(tmp_path)
    svc = PlanService(store)
    inp = svc.inputs(exploratory=True)
    original, _, _ = svc._constraints(inp, AGENT)
    first = svc._store_constraints(original, AGENT, "first compilation")
    # A gross target changes the program version but not the compiled hard rules.
    program = inp.program.model_copy(update={"target_gross_area_m2": 300.0})
    program_ref = store.put(ArtifactKind.SPACE_PROGRAM, program.id, program, AGENT)
    next_set, _, _ = svc._constraints(replace(inp, program=program, program_ref=program_ref), AGENT)
    assert next_set.constraints == original.constraints
    second = svc._store_constraints(next_set, AGENT, "new input compilation")
    assert second.version == first.version + 1
    later = next_set.model_copy(
        update={
            "provenance": next_set.provenance.model_copy(
                update={"created_at": next_set.provenance.created_at + timedelta(seconds=1)}
            )
        }
    )
    assert svc._store_constraints(later, AGENT, "same inputs later") == second
    assert store.verify() == []


def test_historical_cli_export_uses_pinned_site_and_program(tmp_path, monkeypatch):
    store = _load(tmp_path)
    wf = _approve_site_and_program(store)
    svc = PlanService(store)
    original = svc.inputs(exploratory=False)
    plan = _concept().model_copy(
        update={
            "model": _concept().model.model_copy(
                update={"site_ref": original.site_ref, "program_ref": original.program_ref}
            )
        }
    )
    ref = store.put(ArtifactKind.PLAN, plan.option_id, plan, AGENT)
    # Simulate replacement and approval of new inputs, preserving the old plan.
    wf.reopen(Gate.SITE, HUMAN, "Synthetic survey correction")
    new_site = original.site.model_copy(update={"name": "Corrected synthetic survey"})
    new_site_ref = store.put(ArtifactKind.SITE, new_site.id, new_site, AGENT)
    wf.approve(Gate.SITE, new_site_ref, HUMAN, "Corrected synthetic site approved")
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "Revisit program")
    new_program = original.program.model_copy(update={"target_gross_area_m2": 300.0})
    new_program_ref = store.put(ArtifactKind.SPACE_PROGRAM, new_program.id, new_program, AGENT)
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "Revised synthetic program ready")
    wf.approve(Gate.PROGRAM, new_program_ref, HUMAN, "Revised synthetic program approved")
    old_assumptions = store.get(
        store.latest(ArtifactKind.ASSUMPTIONS, "assumptions"), AssumptionsFile
    )
    newer_assumptions = old_assumptions.model_copy(
        update={
            "assumptions": [
                old_assumptions.assumptions[0].model_copy(
                    update={"statement": "A later interview's assumption."}
                )
            ],
            "provenance": old_assumptions.provenance.model_copy(
                update={"created_at": old_assumptions.provenance.created_at + timedelta(seconds=1)}
            ),
        }
    )
    store.put(ArtifactKind.ASSUMPTIONS, "assumptions", newer_assumptions, AGENT)
    assert svc.inputs(exploratory=True).site_ref == new_site_ref
    observed = []
    export = PlanService.export

    def capture(self, plan, ref, report, inp, out_dir, **kwargs):
        observed.append(inp)
        return export(self, plan, ref, report, inp, out_dir, **kwargs)

    monkeypatch.setattr(PlanService, "export", capture)
    out = tmp_path / "historical-export"
    assert main(["plan", "export", str(store.root), ref.id, "--out", str(out)]) == 0
    assert observed[0].site_ref == original.site_ref
    assert observed[0].program_ref == original.program_ref
    assert observed[0].site == store.get(original.site_ref, Site)
    assert observed[0].program == store.get(original.program_ref, SpaceProgram)
    assert observed[0].site_approved is False
    assumptions = json.loads((out / ref.id / "v0001" / "assumptions.json").read_text("utf-8"))
    assert assumptions["site_approved"] is False
    assert assumptions["program"] == [
        a.model_dump(mode="json") for a in old_assumptions.assumptions
    ]
    assert store.verify() == []


def test_topology_revision_connect_stair_outdoor(generated, tmp_path):
    """Test S7-21: Revisions that change architectural topology."""
    store = _copy(generated, tmp_path)
    svc = PlanService(store)
    base = _plan(store, "concept-compact")
    ops = ["connect:sp-kitchen,sp-dining", "stair:perimeter", "outdoor:sp-living,terrace"]

    # Revise with topology operations: connect, stair relocation, outdoor links
    rev_res = svc.revise(
        "concept-compact",
        "Add a direct terrace connection from living room, relocate stair to perimeter, "
        "and connect kitchen and dining.",
        AGENT,
        ops=ops,
    )
    plan_v2 = rev_res.option.candidate.plan
    assert plan_v2 is not None
    assert plan_v2.parent == store.refs(ArtifactKind.PLAN, "concept-compact")[0]
    assert plan_v2.change_request.kind is ChangeRequestKind.MODIFY
    assert rev_res.option.plan_ref.version == 2
    # The Plan version records the operations it was asked for; v1 recorded none. This is the
    # guard: on this fixture v1 already meets all three requests (the program's hard adj-04
    # joins kitchen and dining, v1's terrace opens off the living room, and its entry-Level
    # stair room has an exterior wall), so the geometry checks below show only that the
    # revision kept them.
    assert base.generation.revision_ops == []
    assert plan_v2.generation.revision_ops == ops
    # What v1 does not have: a stair position or an outdoor link goes to the 2D engine, the
    # only one that can place them (ADR 0032); v1 came from the bar engine.
    assert base.generation.solver == "ortools-cp-sat"
    assert plan_v2.generation.solver == "ortools-cp-sat-nooverlap2d"
    model = plan_v2.model
    # connect: a passable opening joins the kitchen and the dining room.
    assert "sp-dining" in circulation_graph(model)["sp-kitchen"]
    # stair:perimeter: the stair's room on the entry Level has an exterior wall.
    (stair,) = model.stairs
    entry_rooms = [
        sid
        for sid in (stair.bottom_space_id, stair.top_space_id)
        if model.space(sid).level_id == "lv-entry"
    ]
    assert len(entry_rooms) == 1
    assert _on_an_exterior_wall(model, entry_rooms[0])
    # outdoor: the living room opens onto a terrace on its own Level.
    terraces = _outdoor_neighbours(model, "sp-living")
    assert terraces
    assert {model.space(t).level_id for t in terraces} == {model.space("sp-living").level_id}
    # Version history is preserved
    refs = store.refs(ArtifactKind.PLAN, "concept-compact")
    assert [r.version for r in refs] == [1, 2]
    assert store.verify() == []


@pytest.fixture(scope="module")
def combined(generated, tmp_path_factory):
    """concept-compact v2: linear's living room (area and connections) plus a courtyard link.

    Returns (store, the RevisionOutcome, concept-linear v1); read only.
    """
    store = _copy(generated, tmp_path_factory.mktemp("combined"))
    res = PlanService(store).revise(
        "concept-compact",
        "Combine the compact footprint with linear daylighting and courtyard outdoor link.",
        AGENT,
        kind=ChangeRequestKind.COMBINE,
        base_versions=["concept-compact", "concept-linear"],
        features=["concept-linear:sp-living=area,connections"],
        feature_confirmation="Yes, adopt linear living room size and connections onto compact.",
        ops=["outdoor:sp-living,courtyard"],
    )
    return store, res, _plan(store, "concept-linear")


def _linear_living_neighbours(linear: PlanVersion, combined: PlanVersion) -> set[str]:
    """Rooms a passable opening joins to linear's living room that the combination has."""
    present = {s.id for s in combined.model.spaces}
    return circulation_graph(linear.model)["sp-living"] & present


def test_combine_compatible_features_from_alternatives(combined):
    """Test S7-22: Combine compatible features from multiple alternatives."""
    store, combined_res, linear = combined
    cand_plan = combined_res.option.candidate.plan
    assert cand_plan is not None
    assert cand_plan.change_request.kind is ChangeRequestKind.COMBINE
    # Base versions are reflected in provenance and change request
    assert [b.id for b in cand_plan.change_request.base_versions] == [
        "concept-compact",
        "concept-linear",
    ]
    assert combined_res.option.plan_ref.version == 2
    # The mapped features become operations derived from linear's own living room.
    linear_area = linear.model.space("sp-living").area_m2
    neighbours = _linear_living_neighbours(linear, cand_plan)
    assert neighbours  # linear's living room opens onto rooms the combination has
    assert cand_plan.generation.revision_ops == [
        "outdoor:sp-living,courtyard",
        f"area:sp-living={linear_area:g}",
        *[f"connect:sp-living,{n}" for n in sorted(neighbours)],
    ]
    # The combined living room has linear's area (within the request tolerance) ...
    living = cand_plan.model.space("sp-living").area_m2
    assert abs(living - linear_area) <= REQUESTED_AREA_TOLERANCE_M2
    assert _not_met(combined_res.revision.new_violations) == []
    # ... and opens onto a courtyard.
    courts = _outdoor_neighbours(cand_plan.model, "sp-living")
    assert courts and all("court" in c for c in courts)
    assert store.verify() == []


@pytest.mark.xfail(
    strict=True,
    reason="product gap: combined `connect:` operations are soft and `request_unmet` does not "
    "check them; concept-compact v2 loses linear's living-terrace door with no finding",
)
def test_combined_connections_are_met_or_reported(combined):
    _, res, linear = combined
    plan = res.option.candidate.plan
    missing = _linear_living_neighbours(linear, plan) - circulation_graph(plan.model)["sp-living"]
    reported = " ".join(res.revision.new_violations)
    assert all(f"connect:sp-living,{n}" in reported for n in missing)


def test_cli_plan_combine_revises_with_the_combine_kind(generated, tmp_path):
    """`plan combine` goes through `revise` (the pass-through `combine` method is gone)."""
    store = _copy(generated, tmp_path)
    code = main(
        [
            "plan", "combine", str(store.root), "Take the linear living room onto compact.",
            "--base", "concept-compact", "--base", "concept-linear",
            "--feature", "concept-linear:sp-living=area",
            "--feature-confirmation", "Yes, use the linear living room size.",
            "--actor", "agent:claude-code",
        ]
    )  # fmt: skip
    assert code == 0
    plan = store.get(store.latest(ArtifactKind.PLAN, "concept-compact"), PlanVersion)
    assert plan.change_request.kind is ChangeRequestKind.COMBINE
    assert [b.id for b in plan.change_request.base_versions] == [
        "concept-compact",
        "concept-linear",
    ]
    linear_area = _plan(store, "concept-linear").model.space("sp-living").area_m2
    assert plan.generation.revision_ops == [f"area:sp-living={linear_area:g}"]
    assert plan.parent == store.refs(ArtifactKind.PLAN, "concept-compact")[0]


def test_preserve_owner_design_intent_across_multi_step_revisions(generated, tmp_path):
    """Test S7-23: Preserve owner design intent across multi-version revisions
    and detect regressions.
    """
    store = _copy(generated, tmp_path)
    svc = PlanService(store)
    v1_kitchen = _kitchen(_plan(store, "concept-compact"))
    kitchen_met = 14 - REQUESTED_AREA_TOLERANCE_M2
    assert v1_kitchen < kitchen_met  # so "enlarged" below is the revision's doing

    # Step 1 -> Step 2: Request larger kitchen (14 m2; met within the 2 m² tolerance). Beside the
    # separate two-car garage (S10-19) the compact bar cannot reach 16 m² here.
    s2 = svc.revise(
        "concept-compact",
        "Enlarge the kitchen.",
        AGENT,
        ops=["area:pi-kitchen=14"],
    )
    assert _kitchen(s2.option.candidate.plan) >= kitchen_met
    assert _not_met(s2.revision.new_violations) == []

    # Step 2 -> Step 3: Request study on lower level
    s3 = svc.revise(
        "concept-compact",
        "Put the study on the lower level.",
        AGENT,
        ops=["level:pi-study-1=lower"],
    )
    # Kitchen intent is still preserved in effective ops and geometry
    plan_v3 = s3.option.candidate.plan
    assert _kitchen(plan_v3) >= kitchen_met
    assert plan_v3.generation.revision_ops == ["area:pi-kitchen=14", "level:pi-study-1=lower"]
    # The level request is met (study below the entry Level) or reported as not met.
    study = plan_v3.model.space("sp-study-1")
    lower = plan_v3.model.level(study.level_id).elevation_m < (
        plan_v3.model.level("lv-entry").elevation_m - 1e-6
    )
    level_finding = (
        f"{REQUEST_NOT_MET_PREFIX}'level:pi-study-1=lower' "
        f"(sp-study-1 is on {study.level_id}; the request is level=lower)"
    )
    assert _not_met(s3.revision.new_violations) == ([] if lower else [level_finding])

    # Step 3 -> Step 4: Keep previous intent and add separate relation
    s4 = svc.revise(
        "concept-compact",
        "Separate living from bedroom.",
        AGENT,
        ops=["separate:pi-living,pi-bed-main"],
    )
    plan_v4 = s4.option.candidate.plan
    assert plan_v4.generation.revision_ops == [
        "area:pi-kitchen=14",
        "level:pi-study-1=lower",
        "separate:pi-living,pi-bed-main",
    ]
    assert _kitchen(plan_v4) >= kitchen_met
    # No regressions reported when design intent is maintained
    regressions = [
        v for v in s4.revision.new_violations if v.startswith(REGRESSION_VIOLATION_PREFIX)
    ]
    assert regressions == []

    # Steps 5 and 6: a request never met is reported as not met in the revision that makes it
    # and in every later one, never as a regression (S10-03, ISS-31).
    s5 = svc.revise(
        "concept-compact",
        "Make kitchen 30 m2.",
        AGENT,
        ops=["area:pi-kitchen=30"],
    )
    kitchen = _kitchen(s5.option.candidate.plan)
    assert kitchen < 28.0  # the solver cannot reach 30 m² here
    expected = _area_not_met("area:pi-kitchen=30", "sp-kitchen", kitchen, 30)
    assert expected in s5.revision.new_violations
    s6 = svc.revise(
        "concept-compact",
        "Rethink the study.",
        AGENT,
        ops=["rethink:pi-study-1"],
    )
    not_met = [v for v in s6.revision.new_violations if v.startswith(REQUEST_NOT_MET_PREFIX)]
    assert len(not_met) == 1 and "sp-kitchen" in not_met[0]
    assert not [
        v for v in s6.revision.new_violations if v.startswith(REGRESSION_VIOLATION_PREFIX)
    ]
    assert store.verify() == []


def test_unmet_requests_separate_unmet_from_lost(generated):
    """S10-03: a lost request is a regression; one the base never met is only not met."""
    store = generated  # read only: nothing below writes to the store
    events = len(store.events())
    svc = PlanService(store)
    base = _plan(store, "concept-compact")
    program = svc.inputs(False).program
    area = base.model.space("sp-kitchen").area_m2
    # Target just inside the tolerance edge: met by the base (area >= target - 2 m²). The 1e-6
    # margin keeps the 6-decimal rounding from pushing the target past the edge.
    met_op = f"area:pi-kitchen={area + REQUESTED_AREA_TOLERANCE_M2 - 1e-6:.6f}"
    base = base.model_copy(
        update={"generation": base.generation.model_copy(update={"revision_ops": [met_op]})}
    )
    assert _unmet([met_op], base.model, base, program) == []

    # The kitchen shrinks about its centroid by exactly 3 m² (area scales with k²): lost.
    sp = base.model.space("sp-kitchen")
    cx, cy = sp.boundary.to_shapely().centroid.coords[0]
    k = ((area - 3.0) / area) ** 0.5
    smaller = sp.boundary.model_copy(
        update={"outer": [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in sp.boundary.outer]}
    )
    shrunk = base.model.model_copy(
        update={
            "spaces": [
                s.model_copy(update={"boundary": smaller}) if s.id == "sp-kitchen" else s
                for s in base.model.spaces
            ]
        }
    )
    lost = _unmet([met_op], shrunk, base, program)
    assert len(lost) == 1 and lost[0].startswith(REGRESSION_VIOLATION_PREFIX)
    assert f"sp-kitchen area {area - 3.0:.1f} m²" in lost[0]

    # A new request, or one the base did not meet, is not met rather than lost.
    new_op = f"area:pi-kitchen={area + 10:.0f}"
    (finding,) = _unmet([new_op], base.model, base, program)
    assert finding.startswith(REQUEST_NOT_MET_PREFIX) and new_op in finding
    assert len(store.events()) == events
