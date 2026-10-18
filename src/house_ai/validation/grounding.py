"""Grounding validator for visual critiques (Stage S5, Task S5-06).

Ensures every claim made by an agent visual inspection points to valid, canonical
element IDs in the targeted plan version, and that measurable claims are properly grounded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import PlanVersion
from house_ai.domain.visual_critique import VisualCritiqueFile

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
    """Extract all valid canonical element identifiers from a PlanVersion."""
    model = plan.model
    valid = set(CANONICAL_PLAN_TARGETS)

    for sp in model.spaces or []:
        valid.add(sp.id)
    for w in model.walls or []:
        valid.add(w.id)
    for op in model.openings or []:
        valid.add(op.id)
    for st in model.stairs or []:
        valid.add(st.id)
    for lvl in model.levels or []:
        valid.add(lvl.id)
    for fx in model.fixtures or []:
        valid.add(fx.id)

    return valid


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
                if t not in valid_ids and not t.startswith("z-") and t != "all":
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
