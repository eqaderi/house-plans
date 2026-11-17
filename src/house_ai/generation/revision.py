"""Revision operations become solver input, and are checked against the Plan version they made.

This module turns the Owner's Revision operations (``domain.revision_ops``) and a Space program
into what the solver is asked: area targets, level preferences, Space relationships, stair
position, outdoor links, strategy and which Spaces may move (rethink). It merges the operations
inherited from the parent Plan version with the new ones: a later request for the same Space
(or the same pair of Spaces) overrides the earlier one, and one-solve instructions (rethink,
strategy, proposal) are not inherited.

``PlanService.revise`` keeps storing, solving and provenance (ADR 0030).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from house_ai.constants.evaluations import (
    REGRESSION_VIOLATION_PREFIX,
    REQUEST_NOT_MET_PREFIX,
    REQUESTED_AREA_TOLERANCE_M2,
)
from house_ai.constants.placement2d import LEVEL_ENTRY
from house_ai.constants.strategies import STRATEGY_LABELS
from house_ai.domain.integrity import circulation_graph
from house_ai.domain.model import HouseModel
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import (
    SpaceProgram,
    SpaceRelationshipKind,
    Strength,
    level_preference_met,
)
from house_ai.domain.relations import is_relation_satisfied, shared_wall_length
from house_ai.domain.revision_ops import RevisionOp, RevisionOpError, RevisionVerb

from .engines import OwnerRequests
from .rooms import Relation, expand_program, space_id_for

V = RevisionVerb

#: Relation verbs and the Space relationship kind each asks for (ADR 0020).
RELATION_KINDS: dict[RevisionVerb, SpaceRelationshipKind] = {
    V.SEPARATE: SpaceRelationshipKind.SEPARATED,
    V.ADJACENT: SpaceRelationshipKind.ADJACENT,
    V.NEAR: SpaceRelationshipKind.NEAR,
    V.CONNECT: SpaceRelationshipKind.CONNECTED,
}
#: Weight of a revision's soft relation in the solver objective.
REVISION_RELATION_WEIGHT = 5.0


@dataclass
class RevisionRequest:
    """What the solver is asked for one revision."""

    strategy: str
    #: What the operations ask of whichever engine lays the Plan version out.
    requests: OwnerRequests
    #: The operations this Plan version carries: inherited and new, overrides applied.
    operations: list[RevisionOp] = field(default_factory=list)
    #: Every operation the parent Plan version recorded, parsed once.
    parent_operations: list[RevisionOp] = field(default_factory=list)


def resolve_spaces(name: str, program: SpaceProgram) -> list[str]:
    """The Space ids a requirement id (``pi-...``) or Space id (``sp-...``) names."""
    by_item = {
        it.id: [space_id_for(it, i) for i in range(1, it.quantity + 1)]
        for it in program.space_requirements
    }
    spaces = {sid for group in by_item.values() for sid in group}
    if name in spaces:
        return [name]
    if name in by_item:
        return by_item[name]
    raise RevisionOpError(
        f"unknown room {name!r}; use a space requirement id (pi-...) or a space id (sp-...)"
    )


def targeted_ids(ops: list[RevisionOp], program: SpaceProgram) -> set[str]:
    """The ids a request is about: each name it gives and the Spaces that name means.

    A Zone name means the Spaces of its requirements; ``rethink:all`` means every Space.
    Operations without names (stair, proposal, strategy) target nothing.
    """
    spaces = {
        it.id: [space_id_for(it, i) for i in range(1, it.quantity + 1)]
        for it in program.space_requirements
    }
    zones: dict[str, set[str]] = {}
    for it in program.space_requirements:
        if it.zone_id is not None:
            zones.setdefault(it.zone_id, set()).update(spaces[it.id])
    out: set[str] = set()
    for op in ops:
        if op.op_type is V.RETHINK and op.target == "all":
            out |= {sid for group in spaces.values() for sid in group}
        for name in op.names:
            out.add(name)
            if name in zones:
                out |= zones[name]
                continue
            try:
                out |= set(resolve_spaces(name, program))
            except RevisionOpError:
                pass  # a name the request gives but the program does not hold
    return out


def _keys(op: RevisionOp, program: SpaceProgram) -> list[tuple[str, ...]] | None:
    """What ``op`` asks about, so a later request about the same thing overrides it.

    None for one-solve instructions (rethink, strategy) that never override anything.
    """
    verb = op.op_type
    if verb in (V.AREA, V.LEVEL):
        return [(verb.value, sid) for sid in resolve_spaces(op.target, program)]
    if verb in RELATION_KINDS:
        a, b = op.names
        return sorted(
            {
                ("relation", *sorted((sa, sb)))
                for sa in resolve_spaces(a, program)
                for sb in resolve_spaces(b, program)
            }
        )
    if verb is V.STAIR:
        return [("stair", "core")]
    if verb is V.OUTDOOR:
        return [("outdoor", sid) for sid in resolve_spaces(op.target, program)]
    if verb is V.PROPOSAL:
        return [("proposal", "proposal")]
    return None


def _narrowed(op: RevisionOp, key: tuple[str, ...]) -> RevisionOp:
    """``op`` restricted to the one Space (or pair) ``key`` names."""
    if key[0] == "relation":
        return RevisionOp(op_type=op.op_type, target=f"{key[1]},{key[2]}")
    if key[0] in ("stair", "proposal"):
        return op
    return RevisionOp(op_type=op.op_type, target=key[1], value=op.value)


def merge_operations(
    inherited: list[RevisionOp], new: list[RevisionOp], program: SpaceProgram
) -> list[RevisionOp]:
    """The operations a Plan version carries: ``new`` overrides ``inherited`` per Space or pair.

    A quantity requirement may be overridden for only one of its Spaces; the others keep the
    earlier request explicitly instead of through the requirement's broader name.
    """
    effective: dict[tuple[str, ...], int] = {}
    groups: list[tuple[RevisionOp, list[tuple[str, ...]]]] = []
    transient: list[RevisionOp] = []
    for op in [*inherited, *new]:
        keys = _keys(op, program)
        if keys is None:
            transient.append(op)
            continue
        for key in keys:
            effective[key] = len(groups)
        groups.append((op, keys))
    out: list[RevisionOp] = []
    for index, (op, keys) in enumerate(groups):
        retained = [key for key in keys if effective[key] == index]
        if retained == keys:
            out.append(op)
        else:
            out += [_narrowed(op, key) for key in retained]
    return out + transient


def compile_revision(
    base: PlanVersion, program: SpaceProgram, ops: list[RevisionOp], *, inherit: bool
) -> RevisionRequest:
    """Turn ``ops`` (and, when ``inherit``, the parent's lasting operations) into solver input.

    ``inherit`` is true for a modification or combination of ``base``; then Spaces that are not
    rethought keep their positions in the parent when the strategy stays the same. The engine
    that reads positions recovers them from the parent's generation record (ADR 0032).
    """
    parent_ops = [
        RevisionOp.parse(text)
        for text in (base.generation.revision_ops if base.generation else [])
    ]
    inherited = [op for op in parent_ops if op.rule.lasting] if inherit else []
    operations = merge_operations(inherited, ops, program)

    rooms = expand_program(program)
    spaces = {r.space_id for r in rooms.rooms}
    strategy = base.strategy or ""
    asked = OwnerRequests()
    rethink: set[str] = set()
    for op in operations:
        verb = op.op_type
        if verb is V.AREA:
            target = op.area_m2
            for sid in resolve_spaces(op.target, program):
                item = rooms.room(sid).item
                if item.min_area_m2 is not None and target < item.min_area_m2:
                    raise RevisionOpError(
                        f"{target:g} m² is below the approved program minimum for {item.id} "
                        f"({item.min_area_m2:g} m²); revise the program instead"
                    )
                asked.targets[sid] = target
        elif verb is V.LEVEL:
            for sid in resolve_spaces(op.target, program):
                asked.level_prefs[sid] = str(op.value)
        elif verb in RELATION_KINDS:
            a, b = op.names
            for sa in resolve_spaces(a, program):
                for sb in resolve_spaces(b, program):
                    asked.relations.append(
                        Relation(
                            sa,
                            sb,
                            RELATION_KINDS[verb],
                            Strength.SOFT,
                            REVISION_RELATION_WEIGHT,
                            f"revision-{verb.value}",
                        )
                    )
        elif verb is V.STAIR:
            asked.stair_position = op.target
        elif verb is V.OUTDOOR:
            for sid in resolve_spaces(op.target, program):
                asked.outdoor_links.append((sid, op.outdoor_kind))
        elif verb is V.RETHINK:
            if op.target == "all":
                rethink |= spaces
            else:
                zone = [r.space_id for r in rooms.rooms if r.item.zone_id == op.target]
                rethink |= set(zone) if zone else set(resolve_spaces(op.target, program))
        elif verb is V.STRATEGY:
            strategy = op.target
        # A proposal is read and validated by the caller, which owns the file system.
    if strategy not in STRATEGY_LABELS:
        raise RevisionOpError(
            f"{base.option_id} was not generated by a strategy ({base.strategy}); add "
            "--strategy to choose one"
        )
    if inherit and base.generation is not None and strategy == base.strategy:
        asked.positions_from = base.generation
        asked.rethink = rethink
    return RevisionRequest(strategy, asked, operations, parent_ops)


def request_unmet(op: RevisionOp, model: HouseModel, program: SpaceProgram) -> str | None:
    """Why ``model`` does not meet the area, level or separation request ``op``.

    None when it is met, or for a kind of request this check does not cover. "Separate" and the
    level words mean what they mean to the evaluators: no door and no shared wall (ADR 0020),
    and :func:`~house_ai.domain.program.level_preference_met`.
    """
    spaces = {s.id: s for s in model.spaces}
    verb = op.op_type
    if verb is V.AREA:
        target = op.area_m2
        for sid in resolve_spaces(op.target, program):
            sp = spaces.get(sid)
            if sp and sp.area_m2 < target - REQUESTED_AREA_TOLERANCE_M2:
                return f"{sp.id} area {sp.area_m2:.1f} m² < requested {target:g} m²"
    elif verb is V.LEVEL:
        pref = str(op.value)
        entry = next((lv for lv in model.levels if lv.id == LEVEL_ENTRY), None)
        for sid in resolve_spaces(op.target, program):
            sp = spaces.get(sid)
            if sp is None:
                continue
            met = level_preference_met(
                pref,
                model.level(sp.level_id).elevation_m,
                entry.elevation_m if entry else None,
                len(model.levels),
            )
            if met is False:
                return f"{sp.id} is on {sp.level_id}; the request is level={pref}"
    elif verb is V.SEPARATE:
        a, b = op.names
        graph = circulation_graph(model)
        for sa in resolve_spaces(a, program):
            for sb in resolve_spaces(b, program):
                if sa not in spaces or sb not in spaces or sa == sb:
                    continue
                met, _ = is_relation_satisfied(
                    SpaceRelationshipKind.SEPARATED, model, graph, [sa], [sb]
                )
                if met is not False:
                    continue
                door = next(
                    (o.id for o in model.openings if o.is_passable and set(o.connects) == {sa, sb}),
                    None,
                )
                if door is not None:
                    return f"door {door} connects {sa} and {sb}"
                return f"{sa} and {sb} share a {shared_wall_length(model, sa, sb):.2f} m wall"
    return None


def unmet_requests(
    ops: list[RevisionOp],
    model: HouseModel,
    program: SpaceProgram,
    *,
    parent_ops: list[RevisionOp],
    parent_model: HouseModel,
) -> list[str]:
    """Owner requests in ``ops`` that ``model`` does not meet.

    A request is a regression only when the parent carried it and met it; otherwise it is
    reported as not met, including a request made in this very revision.
    """
    carried = {str(op) for op in parent_ops}
    out = []
    for op in ops:
        detail = request_unmet(op, model, program)
        if detail is None:
            continue
        if str(op) in carried and request_unmet(op, parent_model, program) is None:
            out.append(f"{REGRESSION_VIOLATION_PREFIX}'{op}' is no longer satisfied ({detail})")
        else:
            out.append(f"{REQUEST_NOT_MET_PREFIX}'{op}' ({detail})")
    return out
