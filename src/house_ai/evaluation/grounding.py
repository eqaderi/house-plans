"""Grounding validator for architectural critiques and revision operations.

Ensures critiques reference existing, canonical entity IDs (spaces, program items,
zones, levels) and separate measured facts from AI judgment.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from house_ai.domain.model import HouseModel
    from house_ai.domain.program import SpaceProgram


def collect_canonical_ids(
    context: HouseModel | SpaceProgram | set[str] | list[str] | dict,
) -> set[str]:
    """Collect all valid entity IDs from a model, program, dictionary, or set."""
    if isinstance(context, (set, list)):
        return set(context)

    valid_ids: set[str] = set()

    # If context is a SpaceProgram
    if hasattr(context, "items") and hasattr(context, "zones"):
        for item in context.items:
            valid_ids.add(str(item.id))
            if getattr(item, "zone_id", None):
                valid_ids.add(str(item.zone_id))
        for zone in context.zones:
            valid_ids.add(str(zone.id))
        if hasattr(context, "adjacencies"):
            for adj in context.adjacencies:
                valid_ids.add(str(adj.id))

    # If context is a HouseModel
    if hasattr(context, "spaces"):
        for space in context.spaces:
            valid_ids.add(str(space.id))
            if getattr(space, "program_item_id", None):
                valid_ids.add(str(space.program_item_id))
            if getattr(space, "zone_id", None):
                valid_ids.add(str(space.zone_id))
            if getattr(space, "level_id", None):
                valid_ids.add(str(space.level_id))
    if hasattr(context, "levels") and isinstance(context.levels, list):
        for level in context.levels:
            valid_ids.add(str(level.id))

    # If context is a dict
    if isinstance(context, dict):
        for key in ("spaces", "items", "zones", "levels", "walls", "openings"):
            elements = context.get(key)
            if isinstance(elements, list):
                for elem in elements:
                    if isinstance(elem, dict) and "id" in elem:
                        valid_ids.add(str(elem["id"]))

    return valid_ids


def extract_entity_ids_from_text(text: str) -> list[str]:
    """Extract standard architectural entity identifiers from critique text."""
    pattern = r"\b((?:pi|z|level|sp|w|op)-[a-zA-Z0-9_\-]+)\b"
    return re.findall(pattern, text)


def validate_critique_grounding(
    referenced_ids: Iterable[str],
    context: HouseModel | SpaceProgram | set[str] | list[str] | dict,
) -> list[str]:
    """Validate that all referenced entity IDs exist in the given context.

    Returns a list of error strings for any ungrounded IDs.
    """
    valid_ids = collect_canonical_ids(context)
    errors: list[str] = []

    for ref_id in referenced_ids:
        # Strip any value assignment like "pi-kitchen=18" or "level=entry"
        clean_id = ref_id.split("=")[0].strip()
        if clean_id and clean_id not in valid_ids:
            errors.append(
                f"Unknown entity ID '{clean_id}' in critique. "
                f"Must reference an existing space, program item, zone, or level in the plan."
            )

    return errors
