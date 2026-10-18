"""Visual critique schema for agent visual reviews and grounded inspection records."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ..constants.reviewer import (
    SEVERITY_WARNING,
    VISUAL_CRITIQUE_SCHEMA_VERSION,
)
from .base import Id, StrictModel, UtcDatetime, utc_now
from .epistemics import ClaimStatus
from .revision_ops import RevisionOp


class VisualClaim(StrictModel):
    """A visual observation made by an agent inspecting a rendered plan."""

    id: Id
    element_ids: list[str] = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    status: ClaimStatus = ClaimStatus.AI_JUDGMENT
    severity: str = SEVERITY_WARNING  # "blocking" | "warning" | "info"
    suggested_ops: list[RevisionOp] = Field(default_factory=list)
    screenshot_hash: str | None = None
    bounding_box: list[float] | None = None  # [min_x, min_y, max_x, max_y]


class VisualCritiqueFile(StrictModel):
    """File recording visual review critiques by an agent against a plan version."""

    schema_version: str = VISUAL_CRITIQUE_SCHEMA_VERSION
    project: str = Field(min_length=1)
    option: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    author: str = Field(min_length=1)
    screenshot_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    screenshot_path: str | None = None
    created_at: UtcDatetime = Field(default_factory=utc_now)
    claims: list[VisualClaim] = Field(default_factory=list)
    verified: bool = False

    def ungrounded_ids(self, valid_ids: set[str]) -> dict[str, list[str]]:
        """Identify any cited element_ids that do not exist in valid_ids."""
        missing = {}
        for c in self.claims:
            bad = [eid for eid in c.element_ids if eid not in valid_ids]
            if bad:
                missing[c.id] = bad
        return missing
