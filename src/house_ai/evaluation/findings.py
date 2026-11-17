"""Which Findings about the targeted ids disappeared, remain or are new (#35, ADR 0033).

The Evaluation is the only source of Findings about a Plan version. After a revision the
Findings of the parent's Evaluation and of the new one are compared for the ids the request
targeted, so "the fix worked" is checked and not assumed.

A Finding is the same Finding in both Evaluations when its code and the ids it cites are the
same (its message may quote new numbers). A Finding of the parent that the new Evaluation
lacks has disappeared only when something it cites changed: a cited element was moved,
reshaped or removed, a cited Space gained or lost an opening, or the Spaces of a cited Space
requirement changed. Otherwise it remains: the
parent's Evaluation may come from an earlier evaluator, and a revision that does not change
the cited geometry is never reported as a fix.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from house_ai.domain.evaluation import Violation
from house_ai.domain.model import HouseModel


@dataclass(frozen=True)
class FindingsChange:
    """The Findings about ``targets``: gone after the revision, still there, or new."""

    targets: tuple[str, ...]
    disappeared: tuple[Violation, ...] = ()
    remaining: tuple[Violation, ...] = ()
    new: tuple[Violation, ...] = ()

    def as_json(self) -> dict:
        def rows(items: tuple[Violation, ...]) -> list[dict]:
            return [v.model_dump(mode="json") for v in items]

        return {
            "targets": list(self.targets),
            "disappeared": rows(self.disappeared),
            "remaining": rows(self.remaining),
            "new": rows(self.new),
        }


def _key(v: Violation) -> tuple[str, tuple[str, ...]]:
    return (v.code, tuple(sorted(v.subject_ids)))


def _elements(model: HouseModel) -> dict[str, list[dict]]:
    """What each id of ``model`` is, for telling whether it changed."""
    out: dict[str, list[dict]] = {}
    for name in type(model).model_fields:
        items = getattr(model, name)
        if not isinstance(items, list):
            continue
        for item in items:
            eid = getattr(item, "id", None)
            if isinstance(eid, str):
                out.setdefault(eid, []).append(item.model_dump(mode="json"))
    # A Space requirement is the Spaces that realise it.
    for space in model.spaces:
        if space.program_item_id is not None:
            out.setdefault(space.program_item_id, []).append(space.model_dump(mode="json"))
    # A Space changes when it gains or loses an opening, or one of its openings moves.
    for opening in model.openings:
        for end in opening.connects:
            if end in out:
                out[end].append(opening.model_dump(mode="json"))
    return out


def changed_ids(ids: Iterable[str], before: HouseModel, after: HouseModel) -> set[str]:
    """Which of ``ids`` name something that changed between ``before`` and ``after``."""
    was, now = _elements(before), _elements(after)
    return {eid for eid in ids if was.get(eid) != now.get(eid)}


def compare_findings(
    before: Sequence[Violation],
    after: Sequence[Violation],
    *,
    targets: Iterable[str],
    before_model: HouseModel,
    after_model: HouseModel,
) -> FindingsChange:
    """Compare the Findings about ``targets`` of a parent Plan version and its revision."""
    wanted = set(targets)
    old = {_key(v): v for v in before if wanted & set(v.subject_ids)}
    new = {_key(v): v for v in after if wanted & set(v.subject_ids)}
    gone = [v for k, v in old.items() if k not in new]
    moved = changed_ids({eid for v in gone for eid in v.subject_ids}, before_model, after_model)

    def fixed(v: Violation) -> bool:
        return bool(moved & set(v.subject_ids))

    return FindingsChange(
        targets=tuple(sorted(wanted)),
        disappeared=tuple(v for v in gone if fixed(v)),
        remaining=tuple(
            [v for k, v in new.items() if k in old] + [v for v in gone if not fixed(v)]
        ),
        new=tuple(v for k, v in new.items() if k not in old),
    )
