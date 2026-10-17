"""How we know what we claim.

The spec requires that we always separate verified fact, inference,
assumption, preference, simulation result and professional approval, and that
unknown facts are modelled as UNKNOWN rather than invented.
"""

from __future__ import annotations

from enum import StrEnum


class Epistemic(StrEnum):
    """Epistemic status of a statement about the project."""

    VERIFIED_FACT = "verified_fact"
    INFERENCE = "inference"
    ASSUMPTION = "assumption"
    PREFERENCE = "preference"
    SIMULATION_RESULT = "simulation_result"
    PROFESSIONAL_APPROVAL = "professional_approval"
    UNKNOWN = "unknown"


class ClaimStatus(StrEnum):
    """How an evaluator produced a reported value."""

    MEASURED = "measured"
    INFERRED = "inferred"
    SIMULATED = "simulated"
    AI_JUDGMENT = "ai_judgment"
    NOT_CHECKED = "not_checked"


class ConfirmationStatus(StrEnum):
    """Status of a fact that must come from a source document or a human.

    Used for drawing units, horizontal CRS and vertical datum. Nothing in the
    system may move a value to USER_CONFIRMED on its own; only a human can.
    """

    UNKNOWN = "unknown"
    #: The source file states it (e.g. DXF $INSUNITS), but no human confirmed it.
    DECLARED_IN_SOURCE = "declared_in_source"
    USER_CONFIRMED = "user_confirmed"
    #: A human confirmed the data is in a local frame with no georeference.
    LOCAL_ONLY_CONFIRMED = "local_only_confirmed"
