"""Shared building blocks for every canonical schema.

Every persisted model derives from :class:`StrictModel`, which rejects unknown
fields (so a typo in a hand-written YAML file fails loudly instead of being
silently dropped) and rejects NaN/infinity.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field

#: Version of the canonical schema family. Bumped on any breaking change.
SCHEMA_VERSION = "0.1.0"

#: Geometric tolerance in metres used by validators and integrity checks.
EPS_M = 1e-6


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
        validate_assignment=True,
        use_enum_values=False,
    )


# Stable identifiers: lowercase, readable, unique within a project.
# Examples: "sp-kitchen", "w-ext-south", "plan-a".
ID_PATTERN = r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*$"
Id = Annotated[str, Field(pattern=ID_PATTERN, min_length=1, max_length=64)]

#: Reserved target meaning "outside the building" in opening connections and
#: circulation graphs. It matches ID_PATTERN but must never be used as an id.
EXTERIOR = "exterior"

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


#: Timezone-aware timestamp, normalised to UTC. Naive datetimes are rejected.
UtcDatetime = Annotated[AwareDatetime, AfterValidator(_to_utc)]

PositiveFloat = Annotated[float, Field(gt=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]


def utc_now() -> datetime:
    return datetime.now(UTC)
