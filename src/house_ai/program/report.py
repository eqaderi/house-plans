"""The space program as a plain-language review sheet for the owner."""

from __future__ import annotations

from house_ai.domain.brief import DesignBrief
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.program import SpaceProgram, SpaceRelationshipKind, Strength
from house_ai.domain.records import AssumptionsFile, OpenQuestionsFile

from .builder import is_indoor
from .validation import ProgramFinding, area_summary

_KIND = {
    SpaceRelationshipKind.CONNECTED: "opens directly into",
    SpaceRelationshipKind.ADJACENT: "shares a wall with",
    SpaceRelationshipKind.NEAR: "is close to",
    SpaceRelationshipKind.VISUAL: "can be seen from",
    SpaceRelationshipKind.SEPARATED: "is kept away from",
    SpaceRelationshipKind.ACOUSTIC_SEPARATION: "is kept out of earshot of",
}


def _basis(item_facts: list[str], brief: DesignBrief | None) -> str:
    if not brief or not item_facts:
        return "assumed"
    status = {f.id: f.status for f in brief.facts}
    states = {status.get(fid) for fid in item_facts}
    if Epistemic.INFERENCE in states:
        return "needs your confirmation"
    if Epistemic.UNKNOWN in states:
        return "partly unknown"
    return "from your answers"


def program_markdown(
    program: SpaceProgram,
    brief: DesignBrief | None,
    findings: list[ProgramFinding],
    assumptions: AssumptionsFile | None = None,
    questions: OpenQuestionsFile | None = None,
) -> str:
    names = {i.id: i.name for i in program.space_requirements}
    names["exterior"] = "outside"
    s = area_summary(program)
    lines = [
        f"# Space program for review: {program.id}",
        "",
        "This is a list of spaces and how they relate, for the floor-plan step. It is not a "
        "floor plan, and it approves nothing.",
        "",
        "## Spaces",
        "",
        "| Space | Number | Size min–target (m²) | Floor | Must / nice | Step-free | Basis |",
        "|---|---|---|---|---|---|---|",
    ]
    for i in program.space_requirements:
        size = (
            "outdoor" if not is_indoor(i) and i.target_area_m2 is None
            else f"{i.min_area_m2 or 0:g}–{i.target_area_m2 or 0:g}"
        )  # fmt: skip
        level = (i.level_preference or "any").replace("_", " ")
        lines.append(
            f"| {i.name} | {i.quantity} | {size} | {level}"
            f" | {i.priority.value} | {'yes' if i.accessible else ''} | "
            f"{_basis(i.source_fact_ids, brief)} |"
        )
    lines += [
        "",
        "## Totals (calculated)",
        "",
        f"- Rooms: {s.net_min_m2:.0f}–{s.net_target_m2:.0f} m² net; with halls, walls and "
        f"structure (+{(program.circulation_factor or 0):.0%}): about "
        f"{s.gross_min_m2:.0f}–{s.gross_target_m2:.0f} m²",
        "- Your total floor area: "
        + (f"{program.target_gross_area_m2:.0f} m²" if program.target_gross_area_m2
           else "not given"),
        f"- Storeys: {program.storeys or 'not decided'}"
        + (f"; about {s.footprint_m2:.0f} m² per storey" if s.footprint_m2 else ""),
        "- Budget: "
        + (f"{program.budget.amount:,.0f} {program.budget.currency} (cost not checked)"
           if program.budget else "not given"),
        f"- Site: {'approved' if program.site_approved else 'not approved yet'}",
        "",
        "## How spaces relate",
        "",
    ]  # fmt: skip
    for a in program.space_relationships:
        must = "must" if a.strength is Strength.HARD else "wish"
        lines.append(f"- {names.get(a.a, a.a)} {_KIND[a.kind]} {names.get(a.b, a.b)} "
                     f"({must}). {a.rationale or ''}".rstrip())  # fmt: skip
    lines += ["", "## Checks", ""]
    if not findings:
        lines.append("- No problems found.")
    for f in findings:
        lines.append(f"- **{f.severity.value}** {f.message}")
        lines += [f"  - option: {o}" for o in f.options]
    if assumptions and assumptions.assumptions:
        lines += ["", "## Assumptions (please check)", ""]
        lines += [f"- {a.statement}" for a in assumptions.assumptions]
    if questions and questions.questions:
        lines += ["", "## Open questions", ""]
        lines += [
            f"- {q.question}" + (" (needed before approval)" if q.blocking else "")
            for q in questions.questions
        ]
    return "\n".join(lines) + "\n"
