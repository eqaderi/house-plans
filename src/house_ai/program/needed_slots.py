"""The slots the Space program needs: the one table (spec #9, part 9).

The program build asks an Open question for each needed slot that is still
unknown, the program checks report a missing blocking slot, and the interview
checklist lists the needed slots still missing. All three read this table, so
they give one answer to "which slots are needed, and which of those block the
program gate". It is not a slot catalogue: the slot types stay in
``interview/slot_types.py`` (ADR 0011).
"""

from __future__ import annotations

from dataclasses import dataclass

from house_ai.domain.interview import SiteContext


@dataclass(frozen=True)
class NeededSlot:
    slot: str
    #: The Open question recorded while the slot is unknown.
    question: str
    #: What is unknown, as the program checks say it ("We do not know yet ...").
    unknown: str
    #: An unknown value blocks the program gate.
    blocks_program_gate: bool
    #: Needed only on a sloped Site (``SiteContext.sloped``).
    sloped_site_only: bool = False

    def applies(self, site: SiteContext | None) -> bool:
        return not self.sloped_site_only or (site is not None and site.sloped)


NEEDED_SLOTS: tuple[NeededSlot, ...] = (
    NeededSlot("adults", "How many adults will live in the house?",
               "how many adults live in the house", True),
    NeededSlot("bedrooms", "How many bedrooms do you want?", "how many bedrooms you want", True),
    NeededSlot("bathrooms", "How many bathrooms do you want?", "how many bathrooms you want",
               True),
    NeededSlot("storeys", "How many storeys should the house have?",
               "how many storeys the house should have", False),
    NeededSlot("budget", "What is the building budget?", "the building budget", False),
    NeededSlot("target_area", "Is there a total floor area in mind?",
               "whether there is a total floor area in mind", False),
    NeededSlot("slope_strategy", "How should the house meet the slope?",
               "how the house should meet the slope", False, sloped_site_only=True),
)  # fmt: skip


def needed_slots(site: SiteContext | None) -> list[NeededSlot]:
    """The needed slots that apply on this Site, in table order."""
    return [n for n in NEEDED_SLOTS if n.applies(site)]
