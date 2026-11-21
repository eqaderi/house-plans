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

from house_ai.domain.evaluation import EvaluationReport, MetricClaim
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

#: Units a measurable claim may state, longest first so ``m2`` is not read as ``m``.
_UNIT = r"m²|m³|m2|m3|sqm|metres?|meters?|m|%|degrees?|deg|°"

#: A number with a unit in text like "area is 25.5 m²". The number may not be part of an
#: ID (``sp-bed-2``) and the unit may not run into a word (``3 mm``, ``2 months``).
MEASURABLE_CLAIM_PATTERN = re.compile(
    r"(?<![\w.\-])(-?\d+(?:\.\d+)?)\s*(" + _UNIT + r")(?!\w)",
    re.IGNORECASE,
)

#: The value stated for a metric: the first number after its name, unit optional.
_STATED_VALUE = re.compile(
    r"(?<![\w.\-])(-?\d+(?:\.\d+)?)(?:\s*(" + _UNIT + r")(?!\w))?", re.IGNORECASE
)
#: Where a metric's statement ends: a semicolon, a line break, or a full stop.
_CLAUSE_END = re.compile(r"[;\n]|\.(?!\d)")

_UNIT_ALIASES = {
    "m²": "m2", "sqm": "m2", "m2": "m2",
    "m³": "m3", "m3": "m3",
    "m": "m", "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "%": "%",
    "deg": "deg", "degree": "deg", "degrees": "deg", "°": "deg",
}  # fmt: skip


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
       include structured revision operations, and a value stated for a cited metric
       must agree with the evaluator's value (:func:`_measurable_findings`).
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
            for t in op.names:
                if t not in valid_ids:
                    findings.append(
                        GroundingFinding(
                            claim_id=claim.id,
                            element_id=t,
                            issue=(
                                f"Suggested revision op '{op.op_type.value}' "
                                f"targets nonexistent element '{t}'"
                            ),
                        )
                    )

        # 5. Measurable numeric claims check
        findings.extend(_measurable_findings(claim, evaluation))

    return GroundingReport(
        critique_id=f"critique-{critique.option}-v{critique.plan_version}",
        plan_version=critique.plan_version,
        is_grounded=len(findings) == 0,
        findings=findings,
    )


def _unit(text: str | None) -> str | None:
    return _UNIT_ALIASES.get(text.lower(), text.lower()) if text else None


def _decimals(number: str) -> int:
    return len(number.split(".")[1]) if "." in number else 0


def _measurable_findings(claim: Any, evaluation: EvaluationReport | None) -> list[GroundingFinding]:
    """Rule 5: every number a claim states must be backed, and backed truthfully.

    A metric is cited when its exact name appears as a whole token in the claim text;
    the first number after the name (before ``;``, a full stop or a line break, or the
    next cited name) is the value the claim states for it. That value must agree with
    the evaluator's value to the precision the claim wrote it at: half a unit of its last
    digit ("46" covers 45.5..46.5, "45.9" covers 45.85..45.95). Evaluator metrics are
    stored at 3 decimals (``EvaluatorOutput.metric``), finer than any figure an agent
    reads off a report, so a correctly rounded reading always lies inside that band and
    a number outside it is not the metric's value. A percentage stated for a unitless
    ratio is compared as a fraction. When several metrics share a name, those whose
    ``subject_ids`` overlap the claim's ``element_ids`` are the candidates.

    Every other number-with-unit must be covered by structured revision operations
    (it is then a proposed target, not a measurement); otherwise it is an ungrounded
    measurable claim. Revision operations never excuse a wrong value for a cited metric.
    """
    text = claim.claim_text
    by_name: dict[str, list[MetricClaim]] = {}
    for m in evaluation.metrics if evaluation else []:
        by_name.setdefault(m.metric, []).append(m)
    cited = sorted(
        (hit.start(), hit.end(), name)
        for name in by_name
        for hit in re.finditer(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", text)
    )

    findings: list[GroundingFinding] = []
    backed: set[tuple[int, int]] = set()
    for i, (_, name_end, name) in enumerate(cited):
        stop = cited[i + 1][0] if i + 1 < len(cited) else len(text)
        clause_end = _CLAUSE_END.search(text, name_end, stop)
        stated = _STATED_VALUE.search(text, name_end, clause_end.start() if clause_end else stop)
        if stated is None:
            continue  # the metric is named, no value is asserted for it
        backed.add(stated.span(1))
        issue = _stated_value_issue(name, stated, by_name[name], claim.element_ids)
        if issue:
            findings.append(GroundingFinding(claim_id=claim.id, issue=issue))

    if claim.suggested_ops:
        return findings
    for match in MEASURABLE_CLAIM_PATTERN.finditer(text):
        if match.span(1) not in backed:
            findings.append(
                GroundingFinding(
                    claim_id=claim.id,
                    issue=(
                        f"Measurable quantity '{match.group(0)}' asserted without citing an "
                        "evaluation metric or providing structured revision operations"
                    ),
                )
            )
    return findings


def _stated_value_issue(
    name: str, stated: re.Match[str], metrics: list[MetricClaim], element_ids: list[str]
) -> str | None:
    """Why the value ``stated`` for metric ``name`` disagrees with the evaluator, or None."""
    number, stated_unit = stated.group(1), _unit(stated.group(2))
    shown = f"{number} {stated_unit}" if stated_unit else number
    on_subject = [m for m in metrics if set(m.subject_ids) & set(element_ids)]
    candidates = on_subject or metrics
    numeric = [
        m
        for m in candidates
        if isinstance(m.value, (int, float)) and not isinstance(m.value, bool)
    ]
    if not numeric:
        statuses = ", ".join(sorted({m.status.value for m in candidates}))
        return (
            f"Claim states {name} = {shown} but the evaluator did not measure it "
            f"(status {statuses})"
        )
    tolerance = 0.5 * 10 ** -_decimals(number)
    value = float(number)
    unit_errors: list[str] = []
    for m in numeric:
        metric_unit = _unit(m.unit)
        scale = 1.0
        if stated_unit and metric_unit is None and stated_unit == "%":
            scale = 0.01  # a percentage of a unitless ratio
        elif stated_unit and metric_unit in _UNIT_ALIASES.values() and stated_unit != metric_unit:
            unit_errors.append(
                f"Claim states {name} in {stated_unit} but the metric is in {metric_unit}"
            )
            continue
        if abs(value * scale - float(m.value)) <= tolerance * scale + 1e-9:
            return None
    if unit_errors and len(unit_errors) == len(numeric):
        return unit_errors[0]
    measured = ", ".join(
        f"{m.value} {_unit(m.unit)}" if m.unit else f"{m.value}" for m in numeric
    )
    return (
        f"Claim states {name} = {shown} but the evaluator measured {measured} "
        f"(tolerance ±{tolerance:g}, half a unit of the stated last digit)"
    )
