"""Revision operations become solver input in one place: ``generation.revision``.

No store and no solver: a Space program from the synthetic example and a stored concept.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram, SpaceRelationshipKind
from house_ai.domain.revision_ops import RevisionOp, RevisionOpError, parse_ops
from house_ai.generation.revision import compile_revision, resolve_spaces
from house_ai.storage.hashing import load_document

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/projects/synthetic-hillside"


def _program() -> SpaceProgram:
    return SpaceProgram.model_validate(load_document(EXAMPLE / "space_program.yaml"))


def _concept(ops: list[str] | None = None) -> PlanVersion:
    path = EXAMPLE / "concepts/concept-compact/exploratory/plan.json"
    plan = PlanVersion.model_validate_json(path.read_text("utf-8"))
    if ops is None:
        return plan
    return plan.model_copy(
        update={"generation": plan.generation.model_copy(update={"revision_ops": ops})}
    )


def _strings(ops: list[RevisionOp]) -> list[str]:
    return [str(op) for op in ops]


def test_resolve_spaces_reads_requirement_and_space_names() -> None:
    program = _program()
    assert resolve_spaces("pi-kitchen", program) == ["sp-kitchen"]
    assert resolve_spaces("sp-kitchen", program) == ["sp-kitchen"]
    with pytest.raises(RevisionOpError, match="unknown room 'pi-attic'"):
        resolve_spaces("pi-attic", program)


def test_modify_inherits_intent_and_overrides_item_space_aliases() -> None:
    program = _program()
    prior = [
        "area:pi-kitchen=16",
        "level:pi-study-1=lower",
        "separate:pi-bed-main,pi-bed-child-1",
        "rethink:all",
        "strategy:compact",
    ]
    parent = _concept(prior)
    req = compile_revision(parent, program, [], inherit=True)
    assert req.options.targets == {"sp-kitchen": 16.0}
    assert req.options.level_prefs == {"sp-study-1": "lower"}
    assert [r.kind for r in req.options.relations] == [SpaceRelationshipKind.SEPARATED]
    assert _strings(req.operations) == prior[:3]
    assert _strings(req.parent_operations) == prior
    assert req.options.hints  # one-run rethink was not inherited
    assert req.strategy == "compact"

    new = parse_ops(
        ["area:sp-kitchen=18", "level:sp-study-1=entry", "adjacent:sp-bed-child-1,sp-bed-main"]
    )
    req = compile_revision(parent, program, new, inherit=True)
    assert req.options.targets == {"sp-kitchen": 18.0}
    assert req.options.level_prefs == {"sp-study-1": "entry"}
    assert [r.kind for r in req.options.relations] == [SpaceRelationshipKind.ADJACENT]
    effective = _strings(req.operations)
    assert effective == [
        "area:sp-kitchen=18",
        "level:sp-study-1=entry",
        "adjacent:sp-bed-child-1,sp-bed-main",
    ]
    # The next modification retains the overrides, rather than their ancestors.
    child = _concept(effective)
    again = compile_revision(child, program, [], inherit=True)
    assert _strings(again.operations) == effective
    assert again.options.targets == {"sp-kitchen": 18.0}
    fresh = compile_revision(child, program, [], inherit=False)
    assert fresh.options.targets == fresh.options.level_prefs == fresh.options.hints == {}
    assert fresh.options.relations == fresh.operations == []


def test_partial_quantity_override_keeps_other_room_requests() -> None:
    program = _program()
    items = [
        item.model_copy(update={"quantity": 2}) if item.id == "pi-study-1" else item
        for item in program.space_requirements
    ]
    program = program.model_copy(update={"space_requirements": items})
    parent = _concept(["area:pi-study-1=12"])
    req = compile_revision(parent, program, parse_ops(["area:sp-study-1-1=14"]), inherit=True)
    assert req.options.targets == {"sp-study-1-1": 14.0, "sp-study-1-2": 12.0}
    assert _strings(req.operations) == ["area:sp-study-1-2=12", "area:sp-study-1-1=14"]


def test_topology_operations_become_stair_and_outdoor_input() -> None:
    req = compile_revision(
        _concept(),
        _program(),
        parse_ops(
            ["connect:sp-kitchen,sp-dining", "stair:perimeter", "outdoor:sp-living",
             "outdoor:pi-kitchen,balcony"]
        ),
        inherit=True,
    )
    opts = req.options
    assert opts.stair_position == "perimeter"
    assert opts.outdoor_links == [("sp-living", "terrace"), ("sp-kitchen", "balcony")]
    (rel,) = opts.relations
    assert (rel.a, rel.b, rel.kind) == ("sp-kitchen", "sp-dining", SpaceRelationshipKind.CONNECTED)


def test_strategy_and_rethink_apply_to_one_solve() -> None:
    parent = _concept()
    req = compile_revision(
        parent, _program(), parse_ops(["strategy:linear", "rethink:all"]), inherit=True
    )
    assert req.strategy == "linear"
    assert req.options.hints == {}  # a new strategy starts from no parent positions
    assert _strings(req.operations) == ["strategy:linear", "rethink:all"]
    same = compile_revision(parent, _program(), parse_ops(["rethink:pi-kitchen"]), inherit=True)
    assert "sp-kitchen" not in same.options.hints
    assert same.options.hints and same.options.bar_hints == {}


def test_outdoor_kinds_are_the_ones_the_2d_solver_places() -> None:
    from house_ai.domain.revision_ops import REVISION_VERBS, RevisionVerb
    from house_ai.generation import solver2d

    allowed = REVISION_VERBS[RevisionVerb.OUTDOOR].words
    assert allowed == {"terrace", "balcony", "courtyard"}
    assert solver2d.VALID_OUTDOOR_LINKS is allowed


def test_area_below_the_program_minimum_is_refused() -> None:
    program = _program()
    kitchen = next(i for i in program.space_requirements if i.id == "pi-kitchen")
    assert kitchen.min_area_m2 is not None
    too_small = kitchen.min_area_m2 / 2
    with pytest.raises(RevisionOpError, match="below the approved program minimum for pi-kitchen"):
        compile_revision(
            _concept(), program, [RevisionOp.parse(f"area:pi-kitchen={too_small:g}")],
            inherit=True,
        )
