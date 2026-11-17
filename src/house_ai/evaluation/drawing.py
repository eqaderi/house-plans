"""Findings about the plan drawing itself: room labels that collide (#34, ADR 0033).

The labels are the ones the plan drawing draws, laid out once by ``domain.label_layout`` at the
drawing's scale (the Site boundary included when the Site has one), so the Finding matches
what the Owner sees. A collision is soft and never closes the plan gate.
"""

from __future__ import annotations

from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.label_layout import label_layout
from house_ai.domain.program import Strength

from .base import EvaluationContext, EvaluatorResult
from .evaluators import VERSION, EvaluatorOutput

METHOD = "drawing_label_layout"


class LabelCollisionEvaluator:
    name = "LabelCollisionEvaluator"
    version = VERSION

    def evaluate(self, ctx: EvaluationContext) -> EvaluatorResult:
        out = EvaluatorOutput(self.name)
        pairs = label_layout(ctx.model, ctx.site).collisions() if ctx.model.spaces else []
        for a, b in pairs:
            out.violation(
                "label_collision",
                Strength.SOFT,
                f"The labels of {a.space_id} and {b.space_id} overlap on the plan drawing.",
                [a.space_id, b.space_id],
                method=METHOD,
            )
        out.metric("label_collisions", len(pairs), METHOD, ClaimStatus.MEASURED)
        return out.result()


DRAWING_EVALUATORS = [LabelCollisionEvaluator()]
