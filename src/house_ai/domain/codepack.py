"""Versioned building-regulation packs and honest compliance language.

No universal code rules are built in. A result may only say it was checked
against a code when a CodePack for the jurisdiction and edition is loaded and
has been verified by a qualified person or authority. Otherwise the system
must say "not checked" or "conceptual best-practice check only".
"""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum

from pydantic import Field, model_validator

from .base import SCHEMA_VERSION, Id, StrictModel, UtcDatetime
from .provenance import Actor, ActorKind


class CodePackVerification(StrEnum):
    #: Transcribed or drafted, not checked by anyone qualified.
    UNVERIFIED = "unverified"
    VERIFIED_BY_PROFESSIONAL = "verified_by_professional"
    VERIFIED_BY_AUTHORITY = "verified_by_authority"


class CodeRule(StrictModel):
    id: Id
    title: str
    #: Short paraphrase; the authoritative text lives at the citation.
    summary: str
    citation: str
    parameters: dict[str, float | int | str | bool] = Field(default_factory=dict)


class CodePack(StrictModel):
    schema_version: str = SCHEMA_VERSION
    id: Id
    jurisdiction: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    edition: str = Field(min_length=1)
    effective_date: date
    #: Where the rules come from (publication, URL, gazette reference).
    source: str = Field(min_length=1)
    rule_ids: list[Id]
    rules: list[CodeRule] = Field(default_factory=list)
    verification_status: CodePackVerification = CodePackVerification.UNVERIFIED
    verified_by: Actor | None = None
    verified_at: UtcDatetime | None = None

    @model_validator(mode="after")
    def _consistent(self) -> CodePack:
        if len(set(self.rule_ids)) != len(self.rule_ids):
            raise ValueError("duplicate rule ids")
        if sorted(self.rule_ids) != sorted(r.id for r in self.rules):
            raise ValueError("rule_ids must list exactly the ids of the included rules")
        verified = self.verification_status is not CodePackVerification.UNVERIFIED
        if verified:
            if self.verified_by is None or self.verified_at is None:
                raise ValueError("a verified codepack needs verified_by and verified_at")
            if self.verified_by.kind is not ActorKind.HUMAN:
                raise ValueError("only a human professional or authority can verify a codepack")
        elif self.verified_by is not None or self.verified_at is not None:
            raise ValueError("an unverified codepack must not name a verifier")
        return self

    @property
    def verified(self) -> bool:
        return self.verification_status is not CodePackVerification.UNVERIFIED


class ComplianceStatus(StrEnum):
    NOT_CHECKED = "not_checked"
    CONCEPTUAL_BEST_PRACTICE_ONLY = "conceptual_best_practice_only"
    CHECKED_AGAINST_CODEPACK = "checked_against_codepack"


class ComplianceStatement(StrictModel):
    status: ComplianceStatus
    codepack_id: Id | None = None
    jurisdiction: str | None = None
    edition: str | None = None
    rule_ids_checked: list[Id] = Field(default_factory=list)

    @model_validator(mode="after")
    def _checked_needs_pack(self) -> ComplianceStatement:
        if self.status is ComplianceStatus.CHECKED_AGAINST_CODEPACK:
            if not (self.codepack_id and self.jurisdiction and self.edition):
                raise ValueError("a codepack check must name the codepack, jurisdiction, edition")
            if not self.rule_ids_checked:
                raise ValueError("a codepack check must list the rules checked")
        return self

    @property
    def label(self) -> str:
        if self.status is ComplianceStatus.NOT_CHECKED:
            return "not checked"
        if self.status is ComplianceStatus.CONCEPTUAL_BEST_PRACTICE_ONLY:
            return "conceptual best-practice check only"
        return (
            f"checked against {self.jurisdiction} {self.edition} "
            f"({len(self.rule_ids_checked)} rules); not a permit determination"
        )


def compliance_statement(
    codepack: CodePack | None, rule_ids_checked: list[str] | None = None
) -> ComplianceStatement:
    """The strongest compliance statement the evidence supports."""
    checked = list(rule_ids_checked or [])
    if codepack is None:
        if checked:
            return ComplianceStatement(status=ComplianceStatus.CONCEPTUAL_BEST_PRACTICE_ONLY)
        return ComplianceStatement(status=ComplianceStatus.NOT_CHECKED)
    unknown = set(checked) - set(codepack.rule_ids)
    if unknown:
        raise ValueError(f"rules not in codepack {codepack.id}: {sorted(unknown)}")
    if not checked:
        return ComplianceStatement(status=ComplianceStatus.NOT_CHECKED)
    if not codepack.verified:
        return ComplianceStatement(status=ComplianceStatus.CONCEPTUAL_BEST_PRACTICE_ONLY)
    return ComplianceStatement(
        status=ComplianceStatus.CHECKED_AGAINST_CODEPACK,
        codepack_id=codepack.id,
        jurisdiction=codepack.jurisdiction,
        edition=codepack.edition,
        rule_ids_checked=checked,
    )


_PROHIBITED_CLAIMS = [
    r"code[- ]compliant",
    r"complies with (?:the )?(?:building )?code",
    r"permit[- ]ready",
    r"construction[- ]ready",
    r"structurally certified",
    r"structurally sound",
    r"mep[- ]engineered",
    r"geotechnically verified",
]
_NEGATION = re.compile(r"\b(?:not|never|no|cannot|isn't|is not)\b[^.]{0,30}$", re.IGNORECASE)


def find_prohibited_claims(text: str) -> list[str]:
    """Professional-status claims in generated text that are not negated.

    A lint for agent output (PROFESSIONAL_HANDOFF.md): the system must not
    claim professional status that nobody qualified has given it.
    """
    found: list[str] = []
    for pattern in _PROHIBITED_CLAIMS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if not _NEGATION.search(text[max(0, match.start() - 40) : match.start()]):
                found.append(match.group(0))
    return found
