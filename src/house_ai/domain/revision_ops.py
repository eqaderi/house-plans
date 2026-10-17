"""Revision operations and feedback schema for reviewer exports and CLI replay."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ..constants.reviewer import (
    REVIEWER_BUNDLE_SCHEMA_VERSION,
)
from .base import Id, StrictModel, UtcDatetime, utc_now


class RevisionComment(StrictModel):
    """A comment on a specific canonical model element or plan."""

    id: Id
    element_id: str = Field(min_length=1)
    element_kind: str | None = None
    text: str = Field(min_length=1)
    created_at: UtcDatetime = Field(default_factory=utc_now)


class RevisionOp(StrictModel):
    """One structured revision operation matching plan revise arguments."""

    op_type: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]*$")]
    target: str = Field(min_length=1)
    value: str | float | int | None = None
    notes: str | None = None

    def to_cli_string(self) -> str:
        """Render to the canonical CLI op format: op_type:target[=value]."""
        if self.value is not None:
            return f"{self.op_type}:{self.target}={self.value}"
        return f"{self.op_type}:{self.target}"


class RevisionOpsFile(StrictModel):
    """File exchanged between the reviewer UI and house-ai plan revise."""

    schema_version: str = REVIEWER_BUNDLE_SCHEMA_VERSION
    project: str = Field(min_length=1)
    option: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    verbatim_request: str = Field(min_length=1)
    author: str = Field(min_length=1)
    created_at: UtcDatetime = Field(default_factory=utc_now)
    operations: list[RevisionOp] = Field(default_factory=list)
    comments: list[RevisionComment] = Field(default_factory=list)

    def to_cli_ops(self) -> list[str]:
        """Convert operations to list of CLI op strings."""
        return [op.to_cli_string() for op in self.operations]
