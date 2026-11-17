"""Revision operations: the one table of verbs, its parser and serialiser, and the reviewer file.

A **Revision operation** is one structured change the Owner asks of a Plan option, such as a
new area or a Level for a Space. Its text form is ``verb:target[sep value]``
(``area:pi-kitchen=16``, ``separate:pi-living,pi-bed-main``, ``outdoor:sp-living,terrace``).
Command-line flags, the reviewer's operations file and the operations recorded on a Plan
version all go through :data:`REVISION_VERBS`, :meth:`RevisionOp.parse` and ``str(op)``.
Stored Plan versions keep the strings they recorded; the typed :class:`RevisionOp` is the
in-memory form.

Which Spaces a name means, and what the solver is asked, needs a Space program and lives in
``house_ai.generation.revision``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from ..constants.proposals import OUTDOOR_LINK_TERRACE, VALID_OUTDOOR_LINKS, VALID_STAIR_POSITIONS
from ..constants.reviewer import REVIEWER_BUNDLE_SCHEMA_VERSION
from ..constants.strategies import STRATEGY_LABELS
from .base import Id, StrictModel, UtcDatetime, utc_now
from .program import LEVEL_PREFERENCES


class RevisionOpError(ValueError):
    """A Revision operation the system cannot act on; nothing was changed."""


class RevisionVerb(StrEnum):
    AREA = "area"
    LEVEL = "level"
    SEPARATE = "separate"
    ADJACENT = "adjacent"
    NEAR = "near"
    CONNECT = "connect"
    OUTDOOR = "outdoor"
    STAIR = "stair"
    PROPOSAL = "proposal"
    RETHINK = "rethink"
    STRATEGY = "strategy"


@dataclass(frozen=True)
class VerbRule:
    """What one verb may target, and whether the next Plan version inherits it."""

    #: The text form, for messages and command-line help.
    form: str
    #: How many Space or requirement names the target holds: 0, 1, or 2 (``a,b``).
    names: int
    #: Separator between target and value in the text form; None when there is no value.
    sep: str | None = None
    #: Legal words for the value (or for the target when ``names`` is 0); None: free text.
    words: frozenset[str] | None = None
    #: The value is a positive number of square metres.
    number: bool = False
    #: The value may be left out (``outdoor:sp-living`` means a terrace).
    optional: bool = False
    #: Continuing design intent the next Plan version inherits; otherwise one solve only.
    lasting: bool = True
    #: The target may be ``all`` (every Space).
    all_: bool = False


_RELATION = VerbRule("SPACE,SPACE", names=2)

#: The one table of Revision operation verbs and their legal targets.
REVISION_VERBS: dict[RevisionVerb, VerbRule] = {
    RevisionVerb.AREA: VerbRule("SPACE=M2", names=1, sep="=", number=True),
    RevisionVerb.LEVEL: VerbRule("SPACE=LEVEL", names=1, sep="=", words=LEVEL_PREFERENCES),
    RevisionVerb.SEPARATE: _RELATION,
    RevisionVerb.ADJACENT: _RELATION,
    RevisionVerb.NEAR: _RELATION,
    RevisionVerb.CONNECT: _RELATION,
    RevisionVerb.OUTDOOR: VerbRule(
        "SPACE[,KIND]", names=1, sep=",", words=VALID_OUTDOOR_LINKS, optional=True
    ),
    RevisionVerb.STAIR: VerbRule("POSITION", names=0, words=VALID_STAIR_POSITIONS),
    RevisionVerb.PROPOSAL: VerbRule("PATH", names=0, lasting=False),
    RevisionVerb.RETHINK: VerbRule("SPACE|ZONE|all", names=1, lasting=False, all_=True),
    RevisionVerb.STRATEGY: VerbRule(
        "STRATEGY", names=0, words=frozenset(STRATEGY_LABELS), lasting=False
    ),
}

_KNOWN = ", ".join(sorted(v.value for v in RevisionVerb))


def _unknown(verb: object, text: str) -> RevisionOpError:
    return RevisionOpError(f"unknown revision operation {verb!r} in {text!r}; known: {_KNOWN}")


def _check(verb: RevisionVerb, target: str, value: Any, text: str) -> None:
    """Refuse a target or value the verb's rule does not allow; one message per cause."""
    rule = REVISION_VERBS[verb]
    shape = f"{text!r}: {verb.value} needs {rule.form}"
    if rule.names == 2:
        parts = target.split(",")
        if len(parts) != 2 or not all(p.strip() for p in parts) or value is not None:
            raise RevisionOpError(shape)
        return
    if not target or (rule.names == 1 and "," in target):
        raise RevisionOpError(shape)
    words = rule.words
    if rule.names == 0:
        if value is not None:
            raise RevisionOpError(shape)
        if words is not None and target not in words:
            raise RevisionOpError(f"{text!r}: {verb.value} must be one of {sorted(words)}")
        return
    if rule.sep is None:
        if value is not None:
            raise RevisionOpError(shape)
        return
    if value is None:
        if not rule.optional:
            raise RevisionOpError(shape)
        return
    if rule.number:
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise RevisionOpError(shape) from None
        if isinstance(value, bool) or not math.isfinite(number) or number <= 0:
            raise RevisionOpError(shape)
    elif words is not None and value not in words:
        raise RevisionOpError(f"{text!r}: {verb.value} must be one of {sorted(words)}")


class RevisionComment(StrictModel):
    """A comment on a specific canonical model element or plan."""

    id: Id
    element_id: str = Field(min_length=1)
    element_kind: str | None = None
    text: str = Field(min_length=1)
    created_at: UtcDatetime = Field(default_factory=utc_now)


class RevisionOp(StrictModel):
    """One Revision operation, checked against the verb table.

    The target is the Space or requirement name (a,b for a relation, the position for a
    stair, the strategy, the proposal path); the value is the area, the level word or the
    outdoor kind.
    """

    op_type: RevisionVerb
    target: str = Field(min_length=1)
    value: str | float | int | None = None
    notes: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _known_verb(cls, data: Any) -> Any:
        if isinstance(data, dict):
            verb = data.get("op_type")
            if verb not in {v.value for v in RevisionVerb}:
                raise _unknown(verb, f"{verb}:{data.get('target', '')}")
        return data

    @model_validator(mode="after")
    def _legal_target(self) -> RevisionOp:
        _check(self.op_type, self.target, self.value, self._text())
        return self

    @classmethod
    def parse(cls, text: str) -> RevisionOp:
        """The one parser of the text form; refuses what the system cannot act on."""
        verb_text, colon, arg = text.partition(":")
        if not colon:
            raise RevisionOpError(f"{text!r}: a revision operation is VERB:TARGET")
        try:
            verb = RevisionVerb(verb_text)
        except ValueError:
            raise _unknown(verb_text, text) from None
        rule = REVISION_VERBS[verb]
        target, value = arg, None
        if rule.sep is not None:
            target, sep, rest = arg.partition(rule.sep)
            value = rest if sep else None
            if sep and not rest:
                raise RevisionOpError(f"{text!r}: {verb.value} needs {rule.form}")
        _check(verb, target, value, text)
        return cls(op_type=verb, target=target, value=value)

    def _text(self) -> str:
        sep = REVISION_VERBS[self.op_type].sep
        if self.value is None or sep is None:
            return f"{self.op_type.value}:{self.target}"
        return f"{self.op_type.value}:{self.target}{sep}{self.value}"

    def __str__(self) -> str:
        """The one serialiser: the text form a Plan version records."""
        return self._text()

    @property
    def rule(self) -> VerbRule:
        return REVISION_VERBS[self.op_type]

    @property
    def names(self) -> tuple[str, ...]:
        """The Space, requirement or Zone names this operation is about (none for ``all``)."""
        rule = self.rule
        if rule.names == 2:
            a, _, b = self.target.partition(",")
            return (a.strip(), b.strip())
        if rule.names == 1 and not (rule.all_ and self.target == "all"):
            return (self.target,)
        return ()

    @property
    def area_m2(self) -> float:
        if not self.rule.number or self.value is None:
            raise RevisionOpError(f"{self} carries no area")
        return float(self.value)

    @property
    def outdoor_kind(self) -> str:
        if self.op_type is not RevisionVerb.OUTDOOR:
            raise RevisionOpError(f"{self} is not an outdoor link")
        return str(self.value) if self.value is not None else OUTDOOR_LINK_TERRACE


def parse_ops(texts: list[str]) -> list[RevisionOp]:
    """Parse several text forms, refusing the first one the system cannot act on."""
    return [RevisionOp.parse(t) for t in texts]


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
        return [str(op) for op in self.operations]
