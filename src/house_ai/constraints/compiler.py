"""Compile the approved program, brief, site and an optional CodePack into constraints.

HARD constraints invalidate a candidate; SOFT ones are weighted objectives.
Nothing here invents a regulation: system constraints are geometric validity
requirements, program constraints are the owner's approved minima and
adjacencies, site constraints are the recorded envelope (or, when there is
none, the parcel boundary, flagged as such) and CodePack constraints exist
only for rules whose parameters this compiler understands. Every other rule
is reported as not checked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from house_ai.domain.brief import DesignBrief
from house_ai.domain.codepack import CodePack
from house_ai.domain.constraints import (
    AdjacencyRule,
    CodeRuleRef,
    Constraint,
    ConstraintSet,
    ConstraintSource,
    ConstraintSourceKind,
    DoorsConnectValidSpacesRule,
    MinAreaRule,
    MinDimensionRule,
    NoOverlapRule,
    ObjectiveRule,
    OpeningsOnWallsRule,
    SoftObjective,
    TraversableRule,
    ValidGeometryRule,
    WithinEnvelopeRule,
)
from house_ai.domain.epistemics import Epistemic
from house_ai.domain.interview import slot_facts
from house_ai.domain.program import SpaceFunction, SpaceProgram, Strength
from house_ai.domain.provenance import Actor, ArtifactRef, Provenance
from house_ai.domain.site import Site

K = ConstraintSourceKind

#: Brief slot -> the objective it expresses. Only slots the owner actually answered count.
BRIEF_OBJECTIVES: dict[str, SoftObjective] = {
    "privacy": SoftObjective.PRIVACY,
    "bedrooms_separate": SoftObjective.ACOUSTIC_ZONING,
    "office_quiet": SoftObjective.ACOUSTIC_ZONING,
    "views": SoftObjective.VIEWS,
    "light_wishes": SoftObjective.DAYLIGHT_OPPORTUNITY,
    "cross_ventilation": SoftObjective.CROSS_VENTILATION,
    "slope_strategy": SoftObjective.SITE_RESPONSE,
    "budget": SoftObjective.COST_PROXY,
    "outdoor": SoftObjective.INDOOR_OUTDOOR,
    "cooking": SoftObjective.KITCHEN_FUNCTIONALITY,
    "storage_room": SoftObjective.STORAGE,
}
#: Objectives every candidate is scored on unless the brief says more (system defaults).
DEFAULT_OBJECTIVES = [
    SoftObjective.ADJACENCY_QUALITY,
    SoftObjective.CIRCULATION_EFFICIENCY,
    SoftObjective.PRIVACY,
    SoftObjective.DAYLIGHT_OPPORTUNITY,
    SoftObjective.ENVELOPE_SIMPLICITY,
    SoftObjective.SITE_RESPONSE,
]
#: CodePack rule parameters this compiler can turn into constraints.
KNOWN_RULE_PARAMETERS = {"function", "min_area_m2", "min_width_m"}


@dataclass
class CompileResult:
    constraints: ConstraintSet
    #: CodePack rule ids turned into constraints.
    code_rules_compiled: list[str] = field(default_factory=list)
    #: CodePack rule ids that could not be expressed; reported as not checked.
    code_rules_not_checked: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _cid(text: str) -> str:
    return text[:64].rstrip("-_")


def compile_constraints(  # noqa: C901
    program: SpaceProgram,
    site: Site | None,
    *,
    created_at: datetime,
    actor: Actor,
    brief: DesignBrief | None = None,
    codepack: CodePack | None = None,
    inputs: list[ArtifactRef] | None = None,
    constraint_set_id: str = "constraints",
) -> CompileResult:
    out: list[Constraint] = []
    notes: list[str] = []

    def add(
        ident: str,
        strength: Strength,
        rule,
        source: ConstraintSource,
        *,
        weight: float | None = None,
        rationale: str | None = None,
        code_rule: CodeRuleRef | None = None,
    ) -> None:
        out.append(
            Constraint(
                id=_cid(ident),
                strength=strength,
                rule=rule,
                weight=weight,
                source=source,
                rationale=rationale,
                code_rule=code_rule,
            )
        )

    H, Sf = Strength.HARD, Strength.SOFT
    system = ConstraintSource(kind=K.SYSTEM)
    add("c-valid-geometry", H, ValidGeometryRule(), system, rationale="geometric validity")
    add("c-no-overlap", H, NoOverlapRule(), system, rationale="spaces on a level do not overlap")
    add(
        "c-openings-on-walls",
        H,
        OpeningsOnWallsRule(),
        system,
        rationale="openings lie inside their host walls",
    )
    add(
        "c-doors-connect",
        H,
        DoorsConnectValidSpacesRule(),
        system,
        rationale="doors lie between the spaces they connect",
    )
    add(
        "c-reach-all",
        H,
        TraversableRule(origin="exterior"),
        system,
        rationale="every space can be reached from outside",
    )
    if site is not None and (site.buildable_envelope is not None or site.boundary is not None):
        env = site.buildable_envelope
        if env is not None:
            why = f"inside the buildable envelope ({env.basis}; status {env.status.value})"
        else:
            why = (
                "inside the parcel boundary only: no buildable envelope is recorded, so "
                "setbacks and coverage are not checked"
            )
            notes.append(why)
        add(
            "c-within-envelope",
            H,
            WithinEnvelopeRule(),
            ConstraintSource(kind=K.SITE, ref=site.id),
            rationale=why,
        )

    for item in program.space_requirements:
        src = ConstraintSource(kind=K.PROGRAM, ref=item.id)
        if item.min_area_m2 is not None:
            add(
                f"c-min-area-{item.id}",
                H,
                MinAreaRule(program_item_id=item.id, min_area_m2=item.min_area_m2),
                src,
            )
        if item.min_width_m is not None:
            add(
                f"c-min-width-{item.id}",
                H,
                MinDimensionRule(program_item_id=item.id, min_width_m=item.min_width_m),
                src,
            )
    for adj in program.space_relationships:
        src = ConstraintSource(kind=K.PROGRAM, ref=adj.id)
        if adj.strength is Strength.HARD:
            add(
                f"c-{adj.id}", H, AdjacencyRule(requirement_id=adj.id), src, rationale=adj.rationale
            )
        else:
            add(
                f"c-{adj.id}",
                Sf,
                AdjacencyRule(requirement_id=adj.id),
                src,
                weight=adj.weight,
                rationale=adj.rationale,
            )

    objectives: dict[SoftObjective, tuple[float, ConstraintSource, str]] = {}
    if brief is not None:
        for key, fact in slot_facts(brief).items():
            obj = BRIEF_OBJECTIVES.get(key)
            if obj is None or fact.value in (None, False, [], ""):
                continue
            owner = fact.status in (Epistemic.PREFERENCE, Epistemic.VERIFIED_FACT)
            weight = 2.0 if owner else 1.0
            prev = objectives.get(obj)
            if prev is None or weight > prev[0]:
                objectives[obj] = (
                    weight,
                    ConstraintSource(kind=K.BRIEF, ref=fact.id),
                    f"from the brief: {key} ({fact.status.value})",
                )
    for obj in DEFAULT_OBJECTIVES:
        objectives.setdefault(obj, (1.0, system, "default objective; not stated in the brief"))
    for obj in sorted(objectives, key=lambda o: o.value):
        weight, src, why = objectives[obj]
        add(
            f"c-obj-{obj.value.replace('_', '-')}",
            Sf,
            ObjectiveRule(objective=obj),
            src,
            weight=weight,
            rationale=why,
        )

    compiled, not_checked = [], []
    if codepack is not None:
        functions = {i.function for i in program.space_requirements}
        for rule in codepack.rules:
            params = rule.parameters
            fn = params.get("function")
            if (
                not set(params) <= KNOWN_RULE_PARAMETERS
                or not isinstance(fn, str)
                or not ("min_area_m2" in params or "min_width_m" in params)
            ):
                not_checked.append(rule.id)
                continue
            try:
                function = SpaceFunction(fn)
            except ValueError:
                not_checked.append(rule.id)
                continue
            if function not in functions:
                compiled.append(rule.id)  # applies to nothing in this program
                continue
            ref = CodeRuleRef(codepack_id=codepack.id, rule_id=rule.id)
            # Only a verified pack can invalidate a plan; otherwise its rules guide only.
            strength = H if codepack.verified else Sf
            weight = None if codepack.verified else 1.0
            src = ConstraintSource(kind=K.CODEPACK, ref=codepack.id)
            for item in program.space_requirements:
                if item.function is not function:
                    continue
                if "min_area_m2" in params:
                    add(
                        f"c-code-{rule.id}-{item.id}",
                        strength,
                        MinAreaRule(
                            program_item_id=item.id, min_area_m2=float(params["min_area_m2"])
                        ),
                        src,
                        weight=weight,
                        code_rule=ref,
                        rationale=rule.title,
                    )
                if "min_width_m" in params:
                    add(
                        f"c-code-{rule.id}-{item.id}-w",
                        strength,
                        MinDimensionRule(
                            program_item_id=item.id, min_width_m=float(params["min_width_m"])
                        ),
                        src,
                        weight=weight,
                        code_rule=ref,
                        rationale=rule.title,
                    )
            compiled.append(rule.id)
        if not codepack.verified:
            notes.append(
                f"CodePack {codepack.id} is unverified: its rules are soft guidance "
                "(conceptual best-practice check only)."
            )
    cs = ConstraintSet(
        id=constraint_set_id,
        project_id=program.project_id,
        constraints=out,
        provenance=Provenance(
            created_at=created_at,
            created_by=actor,
            method="constraint_compilation",
            tool="house-ai constraints",
            inputs=list(inputs or []),
            notes="Compiled from the program, brief, site and CodePack; no regulation invented.",
        ),
    )
    return CompileResult(cs, compiled, not_checked, notes)
