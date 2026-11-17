"""Grounding validator for architectural critiques and revision operations.

A critique cites canonical entity IDs in backticks (`sp-kitchen`, `lv-entry`,
`z-night`, `pi-bed-main`). This module extracts those IDs and checks that
each one exists in the plan or program it talks about, so an agent cannot
critique rooms, levels or zones that are not there.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel

#: ID prefixes a critique may cite: the real ones used by plans and programs
#: (`pi`, `sp`, `z`, `lv`, `adj`, `rel`, `w`, `d`, `win`, `st`, `slab`) plus
#: invented-looking ones (`level`, `zone`, `room`) so a made-up ID is caught
#: rather than silently ignored.
GROUNDED_ID_PREFIXES = (
    "pi", "sp", "z", "lv", "adj", "rel", "w", "d", "win", "st", "slab",
    "level", "zone", "room",
)  # fmt: skip

_BACKTICK_SPAN = re.compile(r"`([^`\n]+)`")
_ID = re.compile(
    r"(?<![A-Za-z0-9_.:/-])((?:" + "|".join(GROUNDED_ID_PREFIXES) + r")-[A-Za-z0-9_-]*[A-Za-z0-9])"
)

#: Fields on a space or program item that point at another canonical entity.
_REFERENCE_FIELDS = ("program_item_id", "zone_id", "level_id")


def collect_canonical_ids(context: Any) -> set[str]:
    """All entity IDs in a plan (`plan.json`), house model, space program, or ID list.

    A plan's model is read from its ``model`` key. Every element of every
    top-level list that has an ``id`` counts, plus the program item, zone
    and level each element refers to.
    """
    if isinstance(context, (set, list, tuple, frozenset)):
        return {str(i) for i in context}
    if isinstance(context, BaseModel):
        context = context.model_dump(mode="json")
    if not isinstance(context, dict):
        raise TypeError(f"cannot collect IDs from {type(context).__name__}")
    if isinstance(context.get("model"), dict):
        context = context["model"]

    ids: set[str] = set()
    for value in context.values():
        if not isinstance(value, list):
            continue
        for elem in value:
            if not isinstance(elem, dict) or "id" not in elem:
                continue
            ids.add(str(elem["id"]))
            for field in _REFERENCE_FIELDS:
                if elem.get(field):
                    ids.add(str(elem[field]))
    return ids


def extract_entity_ids_from_text(text: str) -> list[str]:
    """Entity IDs cited in backticks, in order of first appearance, without duplicates.

    Only backticked spans are read, so prose such as "z-axis" is never
    mistaken for an ID. Inside a span, `pi-kitchen=18` yields `pi-kitchen`
    and `pi-a,pi-b` yields both.
    """
    found: list[str] = []
    for span in _BACKTICK_SPAN.findall(text):
        for entity_id in _ID.findall(span):
            if entity_id not in found:
                found.append(entity_id)
    return found


def validate_critique_grounding(referenced_ids: Iterable[str], context: Any) -> list[str]:
    """One error per referenced ID that does not exist in ``context``."""
    valid_ids = collect_canonical_ids(context)
    errors: list[str] = []
    for ref_id in referenced_ids:
        clean_id = ref_id.split("=")[0].strip()
        if clean_id and clean_id not in valid_ids:
            errors.append(
                f"Unknown entity ID '{clean_id}' in critique. "
                f"Must reference an existing space, space requirement, zone, or level in the plan."
            )
    return errors
