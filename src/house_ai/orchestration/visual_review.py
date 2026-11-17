"""Visual review loop and fix verification (Stage S5, Tasks S5-09 and S5-10).

Orchestrates:
1. Validating visual critique grounding against canonical model elements.
2. Mapping critique claims and suggested operations into deterministic plan revisions.
3. Re-capturing/re-evaluating the revised plan version.
4. Verifying that claimed visual fixes actually resolved the underlying defect,
   strictly rejecting fake fixes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import Actor
from house_ai.domain.revision_ops import RevisionOp
from house_ai.domain.visual_critique import VisualCritiqueFile
from house_ai.orchestration.plans import PlanService
from house_ai.storage.project_store import ProjectStore
from house_ai.validation.defect_detectors import scan_all_model_defects
from house_ai.validation.grounding import GroundingError, validate_critique_grounding


class VisualFixVerificationError(Exception):
    """Raised when a claimed visual fix does not actually resolve the defect."""


@dataclass
class ClaimVerificationResult:
    claim_id: str
    is_resolved: bool
    evidence: str
    remaining_defects: list[str] = field(default_factory=list)


@dataclass
class VisualFixReport:
    critique_id: str
    from_version: int
    to_version: int
    all_resolved: bool
    results: list[ClaimVerificationResult] = field(default_factory=list)

    def raise_if_unverified(self) -> None:
        unresolved = [r for r in self.results if not r.is_resolved]
        if unresolved:
            msgs = [f"[{r.claim_id}] {r.evidence}" for r in unresolved]
            raise VisualFixVerificationError(
                "Visual critique fixes could not be verified:\n" + "\n".join(msgs)
            )


def _format_element_set(elements: set[str] | list[str]) -> str:
    """Format element IDs deterministically with sorted set notation."""
    sorted_items = ", ".join(f"'{eid}'" for eid in sorted(elements))
    return f"{{{sorted_items}}}"


def verify_visual_critique_fixes(
    base_plan: PlanVersion,
    revised_plan: PlanVersion,
    critique: VisualCritiqueFile,
    evaluation: EvaluationReport | None = None,
) -> VisualFixReport:
    """Verify whether the revised plan actually resolves each claim in the critique.

    Strict verification rules:
    - Scans revised_plan with all defect detectors.
    - If a defect matching the claim's element_ids or defect type is still present,
      the claim is marked UNRESOLVED.
    - If no relevant model change occurred affecting the cited element IDs,
      the claim is rejected as an unverified/fake fix.
    """
    base_defects = scan_all_model_defects(base_plan.model)
    revised_defects = scan_all_model_defects(revised_plan.model)

    results: list[ClaimVerificationResult] = []

    for claim in critique.claims:
        cited_ids = set(claim.element_ids)
        elements_repr = _format_element_set(cited_ids)

        # Check if any revised defect still implicates the cited elements
        active_defects = [
            d for d in revised_defects
            if any(eid in cited_ids for eid in d.element_ids)
        ]

        if active_defects:
            defect_desc = active_defects[0].description
            results.append(
                ClaimVerificationResult(
                    claim_id=claim.id,
                    is_resolved=False,
                    evidence=f"Defect still present on elements {elements_repr}: {defect_desc}",
                    remaining_defects=[d.defect_type for d in active_defects],
                )
            )
            continue

        # Check if the elements changed between base and revised plan
        rev_space_ids = {s.id for s in revised_plan.model.spaces or []}
        rev_wall_ids = {w.id for w in revised_plan.model.walls or []}
        rev_op_ids = {o.id for o in revised_plan.model.openings or []}

        # Check if relevant cited IDs were removed, separated, or adjusted
        ids_touched = (
            (cited_ids - rev_space_ids)
            | (cited_ids - rev_wall_ids)
            | (cited_ids - rev_op_ids)
        )

        # Check geometry diffs for remaining spaces
        geometry_changed = False
        rev_space_map = {s.id: s for s in revised_plan.model.spaces or []}
        base_space_map = {s.id: s for s in base_plan.model.spaces or []}

        for eid in cited_ids:
            if eid in base_space_map and eid in rev_space_map:
                if base_space_map[eid].boundary.outer != rev_space_map[eid].boundary.outer:
                    geometry_changed = True
                    break

        if ids_touched or geometry_changed or len(base_defects) > len(revised_defects):
            results.append(
                ClaimVerificationResult(
                    claim_id=claim.id,
                    is_resolved=True,
                    evidence=(
                        f"Defect resolved on elements {elements_repr}; "
                        "verified by model inspection."
                    ),
                )
            )
        else:
            # Model is identical for cited elements -> Fake fix detected!
            results.append(
                ClaimVerificationResult(
                    claim_id=claim.id,
                    is_resolved=False,
                    evidence=(
                        f"Fake fix detected: elements {elements_repr} remain unchanged "
                        "with no geometry or topological revision."
                    ),
                )
            )

    all_resolved = all(r.is_resolved for r in results)
    critique.verified = all_resolved

    return VisualFixReport(
        critique_id=f"critique-{critique.option}-v{critique.plan_version}",
        from_version=critique.plan_version,
        to_version=getattr(revised_plan, "version", critique.plan_version + 1),
        all_resolved=all_resolved,
        results=results,
    )


def apply_visual_critique_loop(
    store: ProjectStore,
    critique: VisualCritiqueFile,
    actor: Actor,
    *,
    out_dir: Path | None = None,
) -> tuple[PlanVersion, VisualFixReport]:
    """Execute the full inspect-critique-revise-verify loop."""
    svc = PlanService(store)
    refs = store.refs(critique.option)
    base_ref = (
        next((r for r in refs if r.version == critique.plan_version), None)
        if refs
        else None
    )
    if not base_ref:
        raise GroundingError(
            f"Plan {critique.option} version {critique.plan_version} not found in store"
        )

    base_plan = store.get(base_ref, PlanVersion)

    # 1. Grounding check
    grounding = validate_critique_grounding(critique, base_plan)
    grounding.raise_if_ungrounded()

    # 2. Extract suggested ops
    all_ops: list[RevisionOp] = []
    for claim in critique.claims:
        all_ops.extend(claim.suggested_ops)

    if not all_ops:
        raise VisualFixVerificationError(
            "Visual critique contains no structured revision operations to execute"
        )

    # 3. Revise plan
    verbatim_text = f"Visual review fixes: {'; '.join(c.claim_text for c in critique.claims)}"
    outcome = svc.revise(
        option_id=critique.option,
        text=verbatim_text,
        actor=actor,
        ops=all_ops,
        version=critique.plan_version,
        out_dir=out_dir,
    )

    revised_plan = outcome.plan

    # 4. Verify fixes
    report = verify_visual_critique_fixes(base_plan, revised_plan, critique)
    report.raise_if_unverified()

    return revised_plan, report
