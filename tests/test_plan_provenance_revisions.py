"""Regression coverage for pinned exports and continuing homeowner revision intent."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from house_ai.cli.main import main
from house_ai.domain.plan import ChangeRequestKind, PlanVersion
from house_ai.domain.program import AdjacencyKind, SpaceProgram
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.records import AssumptionsFile
from house_ai.domain.site import Site
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.plans import PlanService

from .conftest import AGENT, HUMAN
from .test_plan_workflow import _approve_site_and_program, _load


def _concept() -> PlanVersion:
    path = (
        Path(__file__).resolve().parents[1]
        / "examples/projects/synthetic-hillside/concepts/concept-compact/exploratory/plan.json"
    )
    return PlanVersion.model_validate_json(path.read_text("utf-8"))


def test_modify_inherits_intent_and_overrides_item_space_aliases(tmp_path):
    store = _load(tmp_path)
    svc = PlanService(store)
    program = svc.inputs(exploratory=True).program
    parent = _concept()
    prior = [
        "area:pi-kitchen=16",
        "level:pi-study-1=lower",
        "separate:pi-bed-main,pi-bed-child-1",
        "rethink:all",
        "strategy:compact",
    ]
    parent = parent.model_copy(
        update={"generation": parent.generation.model_copy(update={"revision_ops": prior})}
    )
    _, opts, effective = svc._apply_ops(parent, program, [], ChangeRequestKind.MODIFY)
    assert opts.targets == {"sp-kitchen": 16.0}
    assert opts.level_prefs == {"sp-study-1": "lower"}
    assert len(opts.relations) == 1
    assert opts.relations[0].kind is AdjacencyKind.SEPARATED
    assert effective == prior[:3]
    assert opts.hints  # one-run rethink was not inherited

    _, opts, effective = svc._apply_ops(
        parent,
        program,
        [
            "area:sp-kitchen=18",
            "level:sp-study-1=entry",
            "adjacent:sp-bed-child-1,sp-bed-main",
        ],
        ChangeRequestKind.MODIFY,
    )
    assert opts.targets == {"sp-kitchen": 18.0}
    assert opts.level_prefs == {"sp-study-1": "entry"}
    assert [r.kind for r in opts.relations] == [AdjacencyKind.ADJACENT]
    assert effective == [
        "area:sp-kitchen=18",
        "level:sp-study-1=entry",
        "adjacent:sp-bed-child-1,sp-bed-main",
    ]
    # The next modification retains the overrides, rather than their ancestors.
    child = parent.model_copy(
        update={"generation": parent.generation.model_copy(update={"revision_ops": effective})}
    )
    _, next_opts, next_effective = svc._apply_ops(child, program, [], ChangeRequestKind.MODIFY)
    assert next_effective == effective
    assert next_opts.targets == {"sp-kitchen": 18.0}
    _, fresh, effective = svc._apply_ops(child, program, [], ChangeRequestKind.RESTART_FROM_PROGRAM)
    assert fresh.targets == fresh.level_prefs == fresh.hints == {}
    assert fresh.relations == effective == []


def test_partial_quantity_override_keeps_other_room_requests(tmp_path):
    store = _load(tmp_path)
    svc = PlanService(store)
    program = svc.inputs(exploratory=True).program
    items = [
        item.model_copy(update={"quantity": 2}) if item.id == "pi-study-1" else item
        for item in program.items
    ]
    program = program.model_copy(update={"items": items})
    parent = _concept()
    parent = parent.model_copy(
        update={
            "generation": parent.generation.model_copy(
                update={"revision_ops": ["area:pi-study-1=12"]}
            )
        }
    )
    _, opts, effective = svc._apply_ops(
        parent, program, ["area:sp-study-1-1=14"], ChangeRequestKind.MODIFY
    )
    assert opts.targets == {"sp-study-1-1": 14.0, "sp-study-1-2": 12.0}
    assert effective == ["area:sp-study-1-2=12", "area:sp-study-1-1=14"]


def test_revision_stores_effective_operations_and_new_owner_words(tmp_path):
    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    svc.generate(AGENT, strategies=["compact"])
    first = svc.revise(
        "concept-compact", "Please enlarge the kitchen.", AGENT, ops=["area:pi-kitchen=16"]
    )
    second = svc.revise("concept-compact", "Keep that change as it is.", AGENT)
    plan = second.option.candidate.plan
    assert plan.change_request.text == "Keep that change as it is."
    assert plan.parent == first.option.plan_ref
    assert plan.generation.revision_ops == ["area:pi-kitchen=16"]
    assert "revision operation: area:pi-kitchen=16" in second.revision.assumptions
    assert plan.model.space("sp-kitchen").area_m2 > 12.0
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
    assert observed[0].site_verified is False
    assumptions = json.loads((out / ref.id / "v0001" / "assumptions.json").read_text("utf-8"))
    assert assumptions["site_verified"] is False
    assert assumptions["program"] == [
        a.model_dump(mode="json") for a in old_assumptions.assumptions
    ]
    assert store.verify() == []


def test_topology_revision_connect_stair_outdoor(tmp_path):
    """Test S7-21: Revisions that change architectural topology."""
    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    svc.generate(AGENT, strategies=["compact"])

    # Revise with topology operations: connect, stair relocation, outdoor links
    rev_res = svc.revise(
        "concept-compact",
        "Add a direct terrace connection from living room, relocate stair to perimeter, "
        "and connect kitchen and dining.",
        AGENT,
        ops=[
            "connect:sp-kitchen,sp-dining",
            "stair:perimeter",
            "outdoor:sp-living,terrace",
        ],
    )
    plan_v2 = rev_res.option.candidate.plan
    assert plan_v2 is not None
    assert plan_v2.parent is not None
    assert plan_v2.change_request.kind is ChangeRequestKind.MODIFY
    assert rev_res.option.plan_ref.version == 2
    assert "connect:sp-kitchen,sp-dining" in plan_v2.generation.revision_ops
    assert "stair:perimeter" in plan_v2.generation.revision_ops
    assert "outdoor:sp-living,terrace" in plan_v2.generation.revision_ops
    # Version history is preserved
    refs = store.refs(ArtifactKind.PLAN, "concept-compact")
    assert len(refs) == 2
    assert store.verify() == []


def test_combine_compatible_features_from_alternatives(tmp_path):
    """Test S7-22: Combine compatible features from multiple alternatives."""
    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    svc.generate(AGENT, strategies=["compact", "linear"])

    # Combine compact and linear alternatives
    combined_res = svc.combine(
        "concept-compact",
        ["concept-compact", "concept-linear"],
        "Combine the compact footprint with linear daylighting and courtyard outdoor link.",
        AGENT,
        features=["concept-linear:sp-living=area,connections"],
        feature_confirmation="Yes, adopt linear living room size and connections onto compact.",
        ops=["outdoor:sp-living,courtyard"],
    )
    cand_plan = combined_res.option.candidate.plan
    assert cand_plan is not None
    assert cand_plan.change_request.kind is ChangeRequestKind.COMBINE
    assert len(cand_plan.change_request.base_versions) >= 2
    # Base versions are reflected in provenance and change request
    base_ids = [b.id for b in cand_plan.change_request.base_versions]
    assert "concept-compact" in base_ids
    assert "concept-linear" in base_ids
    assert combined_res.option.plan_ref.version == 2
    assert store.verify() == []


def test_preserve_owner_design_intent_across_multi_step_revisions(tmp_path):
    """Test S7-23: Preserve owner design intent across multi-version revisions
    and detect regressions.
    """
    from house_ai.constants.evaluations import REGRESSION_VIOLATION_PREFIX

    store = _load(tmp_path)
    _approve_site_and_program(store)
    svc = PlanService(store)
    svc.generate(AGENT, strategies=["compact"])

    # Step 1 -> Step 2: Request larger kitchen (16 m2)
    s2 = svc.revise(
        "concept-compact",
        "Enlarge the kitchen.",
        AGENT,
        ops=["area:pi-kitchen=16"],
    )
    assert s2.option.candidate.plan.model.space("sp-kitchen").area_m2 >= 14.0

    # Step 2 -> Step 3: Request study on lower level
    s3 = svc.revise(
        "concept-compact",
        "Put the study on the lower level.",
        AGENT,
        ops=["level:pi-study-1=lower"],
    )
    # Kitchen intent is still preserved in effective ops and geometry
    assert s3.option.candidate.plan.model.space("sp-kitchen").area_m2 >= 14.0
    assert "area:pi-kitchen=16" in s3.option.candidate.plan.generation.revision_ops

    # Step 3 -> Step 4: Keep previous intent and add separate relation
    s4 = svc.revise(
        "concept-compact",
        "Separate living from bedroom.",
        AGENT,
        ops=["separate:pi-living,pi-bed-main"],
    )
    plan_v4 = s4.option.candidate.plan
    assert "area:pi-kitchen=16" in plan_v4.generation.revision_ops
    assert "level:pi-study-1=lower" in plan_v4.generation.revision_ops
    assert plan_v4.model.space("sp-kitchen").area_m2 >= 14.0
    # No regressions reported when design intent is maintained
    regressions = [
        v for v in s4.revision.new_violations if v.startswith(REGRESSION_VIOLATION_PREFIX)
    ]
    assert regressions == []

    # Step 5 & 6: Verify regression detection when an earlier request is not met
    svc.revise(
        "concept-compact",
        "Make kitchen 30 m2.",
        AGENT,
        ops=["area:pi-kitchen=30"],
    )
    s6 = svc.revise(
        "concept-compact",
        "Rethink the study.",
        AGENT,
        ops=["rethink:pi-study-1"],
    )
    reg_warnings = [
        v for v in s6.revision.new_violations if v.startswith(REGRESSION_VIOLATION_PREFIX)
    ]
    assert len(reg_warnings) >= 1
    assert "sp-kitchen" in reg_warnings[0]
    assert store.verify() == []
