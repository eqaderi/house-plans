"""Deterministic checks of a space program against its brief and the site.

Findings never change the program. A blocking finding stops the program gate;
when a request does not fit, the finding explains why and lists options for
the owner to choose from.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from house_ai.domain.brief import DesignBrief, Priority
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.interview import SiteContext
from house_ai.domain.program import AdjacencyKind, SpaceFunction, SpaceProgram, Strength
from house_ai.domain.records import Severity

from .builder import is_indoor

CRITICAL_SLOTS = {
    "adults": "how many adults live in the house",
    "bedrooms": "how many bedrooms you want",
    "bathrooms": "how many bathrooms you want",
}

#: Plausible net area range per room (m²); outside it a size is suspicious.
PLAUSIBLE: dict[SpaceFunction, tuple[float, float]] = {
    SpaceFunction.BEDROOM: (6.0, 40.0),
    SpaceFunction.BATHROOM: (2.5, 25.0),
    SpaceFunction.WC: (1.0, 6.0),
    SpaceFunction.KITCHEN: (5.0, 60.0),
    SpaceFunction.LIVING: (10.0, 150.0),
    SpaceFunction.DINING: (6.0, 60.0),
    SpaceFunction.STUDY: (4.0, 40.0),
    SpaceFunction.ENTRY: (2.0, 40.0),
}

#: Pairs of kinds that cannot both hold for the same two spaces.
_CLASH = {
    (AdjacencyKind.CONNECTED, AdjacencyKind.SEPARATED),
    (AdjacencyKind.ADJACENT, AdjacencyKind.SEPARATED),
    (AdjacencyKind.NEAR, AdjacencyKind.SEPARATED),
    (AdjacencyKind.CONNECTED, AdjacencyKind.ACOUSTIC_SEPARATION),
    (AdjacencyKind.ADJACENT, AdjacencyKind.ACOUSTIC_SEPARATION),
}


@dataclass
class ProgramFinding:
    code: str
    severity: Severity
    message: str
    subject_ids: list[str] = field(default_factory=list)
    #: Choices for the owner; none is applied automatically.
    options: list[str] = field(default_factory=list)


@dataclass
class AreaSummary:
    net_min_m2: float
    net_target_m2: float
    gross_min_m2: float
    gross_target_m2: float
    #: Items with no size, left out of the totals.
    unsized: list[str]
    #: Gross target per floor, when the number of floors is known.
    footprint_m2: float | None


def area_summary(program: SpaceProgram) -> AreaSummary:
    indoor = [i for i in program.items if is_indoor(i)]
    c = 1.0 + (program.circulation_factor or 0.0)
    net_min = sum((i.min_area_m2 or i.target_area_m2 or 0.0) * i.quantity for i in indoor)
    net_target = sum((i.target_area_m2 or i.min_area_m2 or 0.0) * i.quantity for i in indoor)
    unsized = [i.id for i in indoor if i.target_area_m2 is None and i.min_area_m2 is None]
    footprint = net_target * c / program.levels if program.levels else None
    return AreaSummary(net_min, net_target, net_min * c, net_target * c, unsized, footprint)


def validate_program(
    program: SpaceProgram, brief: DesignBrief | None, site: SiteContext | None = None
) -> list[ProgramFinding]:
    out: list[ProgramFinding] = []
    add = out.append
    facts = {f.id: f for f in brief.facts} if brief else {}
    by_key = {f.key: f for f in brief.facts if f.id == f"f-{f.key}"} if brief else {}

    # -- missing information and unconfirmed interpretations
    from_interview = brief is not None and brief.provenance.method == "owner_interview"
    for slot, what in CRITICAL_SLOTS.items() if from_interview else ():
        f = by_key.get(slot)
        if f is None or f.value is None:
            add(ProgramFinding("missing_information", Severity.BLOCKING,
                               f"We do not know yet {what}.", [f"f-{slot}"]))  # fmt: skip
    cited = {fid for i in program.items for fid in i.source_fact_ids} | {
        fid for a in program.adjacencies for fid in a.source_fact_ids
    }
    unconfirmed = sorted(
        fid for fid in cited if fid in facts and facts[fid].status is Epistemic.INFERENCE
    )
    if unconfirmed:
        add(ProgramFinding(
            "unconfirmed_interpretation", Severity.BLOCKING,
            f"{len(unconfirmed)} thing(s) the program relies on were understood from your "
            "answers but not yet confirmed by you: "
            + "; ".join(facts[f].statement.split(" (understood")[0] for f in unconfirmed),
            unconfirmed, ["Confirm them", "Correct them (revise or reject)"],
        ))  # fmt: skip
    missing = sorted(fid for fid in cited if facts and fid not in facts)
    if missing:
        add(ProgramFinding("unknown_fact", Severity.BLOCKING,
                           f"The program cites facts that are not in the brief: {missing}",
                           missing))  # fmt: skip
    if brief:
        for c in brief.unresolved_contradictions():
            add(ProgramFinding("contradiction", Severity.BLOCKING, c.statement, [c.id],
                               list(c.options)))  # fmt: skip

    # -- duplicates
    names = Counter(i.name.lower() for i in program.items)
    for name, n in names.items():
        if n > 1:
            add(ProgramFinding("duplicate_space", Severity.WARNING,
                               f"{n} spaces are called '{name}'.",
                               [i.id for i in program.items if i.name.lower() == name]))
    seen: Counter[tuple[frozenset[str], AdjacencyKind]] = Counter(
        (frozenset((a.a, a.b)), a.kind) for a in program.adjacencies
    )
    for (pair, kind), n in seen.items():
        if n > 1:
            add(ProgramFinding("duplicate_requirement", Severity.WARNING,
                               f"'{kind.value}' between {' and '.join(sorted(pair))} is stated "
                               f"{n} times.", sorted(pair)))  # fmt: skip

    # -- conflicting adjacencies
    by_pair: dict[frozenset[str], list] = {}
    for a in program.adjacencies:
        by_pair.setdefault(frozenset((a.a, a.b)), []).append(a)
    for pair, reqs in by_pair.items():
        for x in reqs:
            for y in reqs:
                if (x.kind, y.kind) in _CLASH:
                    both_hard = x.strength is Strength.HARD and y.strength is Strength.HARD
                    names_ = " and ".join(sorted(pair))
                    add(ProgramFinding(
                        "adjacency_conflict",
                        Severity.BLOCKING if both_hard else Severity.WARNING,
                        f"{names_}: '{x.kind.value}' ({x.strength.value}) conflicts with "
                        f"'{y.kind.value}' ({y.strength.value}).",
                        [x.id, y.id],
                        [f"Keep '{x.kind.value}'", f"Keep '{y.kind.value}'"],
                    ))  # fmt: skip

    # -- suspicious sizes and combinations
    for i in program.items:
        bounds = PLAUSIBLE.get(i.function)
        size = i.target_area_m2 or i.min_area_m2
        if bounds and size is not None and not bounds[0] <= size <= bounds[1]:
            add(ProgramFinding("suspicious_area", Severity.WARNING,
                               f"{i.name} at {size:g} m² is outside the usual "
                               f"{bounds[0]:g}–{bounds[1]:g} m² for a {i.function.value}.",
                               [i.id]))  # fmt: skip
    beds = sum(i.quantity for i in program.items if i.function is SpaceFunction.BEDROOM)
    baths = sum(i.quantity for i in program.items if i.function is SpaceFunction.BATHROOM)
    if baths > beds + 2:
        add(ProgramFinding("unusual_combination", Severity.WARNING,
                           f"{baths} bathrooms for {beds} bedrooms is unusual.", []))
    if program.levels and program.levels > 1 and not any(
        i.function is SpaceFunction.STAIR for i in program.items
    ):
        add(ProgramFinding("missing_stair", Severity.BLOCKING,
                           f"{program.levels} floors but no stair in the program.", []))
    if program.levels == 1 and any(i.function is SpaceFunction.LIFT for i in program.items):
        add(ProgramFinding("lift_on_one_level", Severity.WARNING,
                           "The program has a lift but only one floor.", ["pi-lift"]))
    accessible_off_entry = [
        i.id for i in program.items
        if i.accessible and program.levels and program.levels > 1
        and i.level_preference not in ("entry", "ground")
        and not any(x.function is SpaceFunction.LIFT for x in program.items)
    ]  # fmt: skip
    if accessible_off_entry:
        add(ProgramFinding("accessible_route", Severity.WARNING,
                           "Spaces that must be step-free are not on the entrance level and "
                           "there is no lift.", accessible_off_entry,
                           ["Add a lift", "Move them to the entrance level"]))  # fmt: skip

    # -- area totals
    s = area_summary(program)
    if s.unsized:
        add(ProgramFinding("unsized_spaces", Severity.INFO,
                           f"{len(s.unsized)} indoor space(s) have no size and are left out of "
                           "the totals.", s.unsized))  # fmt: skip
    target = program.target_gross_area_m2
    optional = [i for i in program.items if i.priority in (Priority.COULD, Priority.SHOULD)
                and is_indoor(i)]  # fmt: skip
    if target is not None and s.gross_min_m2 > target + 1e-6:
        add(ProgramFinding(
            "area_infeasible", Severity.BLOCKING,
            f"The rooms you asked for need at least {s.gross_min_m2:.0f} m² including halls "
            f"and walls, but your total is {target:.0f} m².",
            [program.id],
            [f"Raise the total to about {s.gross_min_m2:.0f}–{s.gross_target_m2:.0f} m²",
             "Make some rooms smaller than typical",
             "Drop optional spaces: " + (", ".join(i.name for i in optional) or "none marked"),
             "Fewer bedrooms or bathrooms"],
        ))  # fmt: skip
    elif target is not None and target > 1.6 * s.gross_target_m2:
        add(ProgramFinding(
            "area_generous", Severity.WARNING,
            f"Your total of {target:.0f} m² is much larger than the rooms need "
            f"(about {s.gross_target_m2:.0f} m²).",
            [program.id],
            ["Keep the total and make rooms larger", "Lower the total", "Add spaces"],
        ))  # fmt: skip
    if program.budget is not None:
        add(ProgramFinding(
            "budget_not_checked", Severity.INFO,
            f"Budget {program.budget.amount:,.0f} {program.budget.currency}: cost is not "
            "checked yet (no cost data loaded).",
        ))  # fmt: skip

    # -- site
    if site is not None and site.parcel_area_m2:
        label = "" if site.verified else " (unconfirmed survey value)"
        floors = program.levels
        footprint = s.gross_target_m2 / floors if floors else s.gross_target_m2
        floors_note = f"on {floors} floor(s)" if floors else "if on one floor"
        if footprint > site.parcel_area_m2:
            add(ProgramFinding(
                "exceeds_parcel", Severity.BLOCKING if site.verified else Severity.WARNING,
                f"About {footprint:.0f} m² per floor {floors_note} is more than the whole parcel "
                f"of {site.parcel_area_m2:.0f} m²{label}.",
                [program.id],
                ["Add a floor", "Reduce the total area", "Drop optional spaces"],
            ))  # fmt: skip
        elif footprint > 0.5 * site.parcel_area_m2:
            add(ProgramFinding(
                "large_footprint", Severity.WARNING,
                f"About {footprint:.0f} m² per floor {floors_note} covers "
                f"{footprint / site.parcel_area_m2:.0%} of the {site.parcel_area_m2:.0f} m² "
                f"parcel{label}, leaving little outdoor space. Local site-coverage limits are "
                "not loaded (not checked).",
                [program.id],
                ["Add a floor", "Reduce the total area", "Accept a small garden"],
            ))  # fmt: skip
        if (site.relief_m or 0) >= 2.0 and by_key.get("slope_strategy") is None:
            add(ProgramFinding(
                "levels_against_ground", Severity.INFO,
                f"The ground falls about {site.relief_m:.1f} m{label}. How each floor meets the "
                "ground is decided first in Milestone D (section before rooms).",
            ))  # fmt: skip
    return out


def blocking(findings: list[ProgramFinding]) -> list[ProgramFinding]:
    return [f for f in findings if f.severity is Severity.BLOCKING]
