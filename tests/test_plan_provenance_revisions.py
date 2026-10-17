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
    _, fresh, effective = svc._apply_ops(
        child, program, [], ChangeRequestKind.RESTART_FROM_PROGRAM
    )
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
