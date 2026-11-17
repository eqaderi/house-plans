"""Grounding: an agent's critique may only cite entities that exist (ADR 0027).

One module, one set of canonical IDs (:func:`collect_canonical_ids`), two kinds
of critique:

* a written critique cites IDs in backticks (`sp-kitchen`, `lv-entry`,
  `z-night`, `pi-bed-main`); :func:`extract_entity_ids_from_text` reads them and
  :func:`validate_cited_ids` reports each one the plan or program lacks
  (``house-ai plan ground``);
* a visual critique (Stage S5) lists ``element_ids`` per claim;
  :func:`validate_critique_grounding` checks those, the targets of suggested
  revision operations, the plan version and screenshot hash, and refuses
  measurable claims that cite no metric.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import PlanVersion
from house_ai.domain.visual_critique import VisualCritiqueFile

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

#: Fields on a space or space requirement that point at another canonical entity.
_REFERENCE_FIELDS = ("program_item_id", "zone_id", "level_id")


def collect_canonical_ids(context: Any) -> set[str]:
    """All entity IDs in a plan (`plan.json`), house model, space program, or ID list.

    A plan's model is read from its ``model`` key. Every element of every
    top-level list that has an ``id`` counts, plus the space requirement,
    zone and level each element refers to.
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
            for ref_field in _REFERENCE_FIELDS:
                if elem.get(ref_field):
                    ids.add(str(elem[ref_field]))
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


def validate_cited_ids(referenced_ids: Iterable[str], context: Any) -> list[str]:
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


CANONICAL_PLAN_TARGETS = {
    "plan",
    "site",
    "parcel",
    "envelope",
    "boundary",
    "orientation",
    "north",
    "stairs",
    "circulation",
}

# Regex to detect ungrounded numeric assertions in text like "area is 25.5 m²"
MEASURABLE_CLAIM_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(m²|sqm|m2|meters?|metres?|%|deg|degrees?|m3|m³)\b",
    re.IGNORECASE,
)


class GroundingError(Exception):
    """Raised when a critique contains ungrounded or invalid claims."""


@dataclass
class GroundingFinding:
    claim_id: str
    issue: str
    element_id: str | None = None


@dataclass
class GroundingReport:
    critique_id: str
    plan_version: int
    is_grounded: bool
    findings: list[GroundingFinding] = field(default_factory=list)

    def raise_if_ungrounded(self) -> None:
        if not self.is_grounded:
            err_msgs = [f"[{f.claim_id}] {f.issue}" for f in self.findings]
            raise GroundingError("Critique is not grounded:\n" + "\n".join(err_msgs))


def collect_plan_element_ids(plan: PlanVersion) -> set[str]:
    """Every ID a visual claim may cite: the plan's canonical IDs plus the generic targets."""
    return CANONICAL_PLAN_TARGETS | collect_canonical_ids(plan)


def validate_critique_grounding(
    critique: VisualCritiqueFile,
    plan: PlanVersion,
    evaluation: EvaluationReport | None = None,
    *,
    expected_screenshot_hash: str | None = None,
) -> GroundingReport:
    """Validate that every claim in a VisualCritiqueFile is grounded in the PlanVersion.

    Rules enforced:
    1. Plan version in critique must match the plan version.
    2. If expected_screenshot_hash is provided, critique screenshot_hash must match.
    3. Every cited element_id in every claim must exist in the canonical model.
    4. Suggested revision operations must target valid elements.
    5. Measurable numeric claims in text must either cite an evaluator metric or
       include structured revision operations.
    """
    findings: list[GroundingFinding] = []

    # 1. Plan version check
    # Check if plan has version attribute or parent info
    if hasattr(plan, "version") and plan.version and plan.version != critique.plan_version:
        findings.append(
            GroundingFinding(
                claim_id="critique_header",
                issue=(
                    f"Plan version mismatch: critique targets v{critique.plan_version}, "
                    f"plan is v{plan.version}"
                ),
            )
        )

    # 2. Screenshot hash check
    if expected_screenshot_hash and critique.screenshot_hash != expected_screenshot_hash:
        findings.append(
            GroundingFinding(
                claim_id="screenshot_hash",
                issue=(
                    f"Screenshot hash mismatch: critique claims {critique.screenshot_hash[:12]}, "
                    f"expected {expected_screenshot_hash[:12]}"
                ),
            )
        )

    # 3. Element IDs validation
    valid_ids = collect_plan_element_ids(plan)

    for claim in critique.claims:
        if not claim.element_ids:
            findings.append(
                GroundingFinding(
                    claim_id=claim.id,
                    issue="Claim contains no element_ids (must cite at least one canonical ID)",
                )
            )
            continue

        for eid in claim.element_ids:
            if eid not in valid_ids:
                findings.append(
                    GroundingFinding(
                        claim_id=claim.id,
                        element_id=eid,
                        issue=f"Element ID '{eid}' does not exist in plan '{plan.option_id}'",
                    )
                )

        # 4. Validate suggested revision ops targets
        for op in claim.suggested_ops:
            targets = [t.strip() for t in op.target.split(",")]
            for t in targets:
                if t not in valid_ids and t != "all":
                    findings.append(
                        GroundingFinding(
                            claim_id=claim.id,
                            element_id=t,
                            issue=(
                                f"Suggested revision op '{op.op_type}' "
                                f"targets nonexistent element '{t}'"
                            ),
                        )
                    )

        # 5. Measurable numeric claims check
        # If claim asserts numbers without ops or metric citation, verify in evaluation
        has_metric_citation = False
        if evaluation and evaluation.metrics:
            eval_metrics = {m.metric for m in evaluation.metrics}
            for m_name in eval_metrics:
                if m_name in claim.claim_text:
                    has_metric_citation = True
                    break

        has_suggested_ops = len(claim.suggested_ops) > 0

        # If claim has numeric measurement pattern but no metric citation and no suggested ops:
        match = MEASURABLE_CLAIM_PATTERN.search(claim.claim_text)
        if match and not has_metric_citation and not has_suggested_ops:
            findings.append(
                GroundingFinding(
                    claim_id=claim.id,
                    issue=(
                        f"Measurable quantity '{match.group(0)}' asserted without citing an "
                        "evaluation metric or providing structured revision operations"
                    ),
                )
            )

    return GroundingReport(
        critique_id=f"critique-{critique.option}-v{critique.plan_version}",
        plan_version=critique.plan_version,
        is_grounded=len(findings) == 0,
        findings=findings,
    )
