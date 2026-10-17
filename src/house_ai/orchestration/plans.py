"""Plan concepts in a project: generate, evaluate, revise, export, request review.

Gated mode (the normal case) works only on the human-approved site and
program versions, stores every plan, evaluation and revision as a new
immutable artifact version and moves the workflow PROGRAM_APPROVED ->
CONCEPT_GENERATION -> CONCEPT_REVIEW. The plan gate itself stays human-only
(``house-ai workflow approve``). Every precondition is checked before anything
is written, so a refused command leaves the project untouched.

Exploratory mode writes nothing to the project store: it runs the same
pipeline on the newest site and program versions (approved or not) and
exports files stamped as exploratory, so an owner can see options before the
gates are passed. It never changes the workflow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from house_ai.constraints.compiler import compile_constraints
from house_ai.domain.brief import DesignBrief
from house_ai.domain.codepack import CodePack
from house_ai.domain.constraints import ConstraintSet
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import ChangeRequest, ChangeRequestKind, PlanVersion, RevisionReport
from house_ai.domain.program import AdjacencyKind, SpaceProgram, Strength
from house_ai.domain.provenance import Actor, ArtifactKind, ArtifactRef, Provenance
from house_ai.domain.records import AssumptionsFile
from house_ai.domain.site import Site
from house_ai.domain.workflow import Gate, WorkflowEvent, WorkflowState
from house_ai.evaluation.explain import (
    comparison_markdown,
    explanation_markdown,
    revision_markdown,
    revision_report,
)
from house_ai.evaluation.report import evaluate_plan, report_id
from house_ai.generation.frame import to_dm
from house_ai.generation.generator import (
    Candidate,
    CpSatPlanGenerator,
    GenerationRequest,
)
from house_ai.generation.massing import STRATEGY_LABELS, STRATEGY_ORDER
from house_ai.generation.rooms import Relation, expand_program
from house_ai.generation.solver import SolverOptions
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import content_hash, pretty_json

from .workflow import Workflow

S = WorkflowState
EXPLORATORY_BANNER = (
    "EXPLORATORY: not stored in the project; the site and/or program are not approved by the "
    "owner. Not a validated plan."
)
GENERATION_STATES = {S.PROGRAM_APPROVED, S.CONCEPT_GENERATION, S.CONCEPT_REVIEW}
LEVEL_PREFS = {"entry", "not_entry", "upper", "lower", "any", "ground"}


class PlanWorkflowError(Exception):
    """The project is not in a state where this plan command may run; nothing was written."""


@dataclass
class Inputs:
    site: Site
    site_ref: ArtifactRef
    program: SpaceProgram
    program_ref: ArtifactRef
    brief: DesignBrief | None = None
    brief_ref: ArtifactRef | None = None
    codepack: CodePack | None = None
    codepack_ref: ArtifactRef | None = None
    site_verified: bool = False


@dataclass
class StoredOption:
    candidate: Candidate
    plan_ref: ArtifactRef | None = None
    report: EvaluationReport | None = None
    report_ref: ArtifactRef | None = None
    export_dir: Path | None = None


@dataclass
class GenerationOutcome:
    exploratory: bool
    options: list[StoredOption]
    constraints_ref: ArtifactRef | None = None
    comparison: Path | None = None
    states: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def generated(self) -> list[StoredOption]:
        return [o for o in self.options if o.candidate.plan is not None]


@dataclass
class RevisionOutcome:
    option: StoredOption
    revision: RevisionReport
    revision_ref: ArtifactRef
    export_dir: Path | None


class PlanService:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self.wf = Workflow(store)

    # ----------------------------------------------------------------- inputs

    def inputs(self, exploratory: bool) -> Inputs:
        status = self.wf.status()
        if not exploratory:
            if status.state not in GENERATION_STATES:
                hint = ""
                if self.store.latest_of_kind(ArtifactKind.SPACE_PROGRAM):
                    hint = " Use --exploratory to preview concepts without storing them."
                raise PlanWorkflowError(
                    f"plan generation needs the owner's approved site and program "
                    f"(PROGRAM_APPROVED or later); the project is in {status.state.value}.{hint}"
                )
            site_ref = status.approvals[Gate.SITE].artifact
            program_ref = status.approvals[Gate.PROGRAM].artifact
        else:
            sites = self.store.latest_of_kind(ArtifactKind.SITE)
            programs = self.store.latest_of_kind(ArtifactKind.SPACE_PROGRAM)
            if not sites or not programs:
                missing = "site" if not sites else "space program"
                raise PlanWorkflowError(
                    f"no {missing} in this project yet; concepts need a site and a program "
                    "(run the interview and `house-ai program build` first)"
                )
            site_ref = (
                status.approvals[Gate.SITE].artifact if Gate.SITE in status.approvals else sites[-1]
            )
            program_ref = (
                status.approvals[Gate.PROGRAM].artifact
                if Gate.PROGRAM in status.approvals
                else programs[-1]
            )
        program = self.store.get(program_ref, SpaceProgram)
        inp = Inputs(
            site=self.store.get(site_ref, Site),
            site_ref=site_ref,
            program=program,
            program_ref=program_ref,
            site_verified=Gate.SITE in status.approvals
            and status.approvals[Gate.SITE].artifact.model_dump() == site_ref.model_dump(),
        )
        if program.brief_ref is not None:
            try:
                inp.brief = self.store.get(program.brief_ref, DesignBrief)
                inp.brief_ref = program.brief_ref
            except Exception:  # noqa: BLE001 - a missing brief only drops brief objectives
                inp.brief = None
        packs = self.store.latest_of_kind(ArtifactKind.CODEPACK)
        if packs:
            inp.codepack_ref = packs[0]
            inp.codepack = self.store.get(packs[0], CodePack)
        return inp

    def _store_constraints(self, cs: ConstraintSet, actor: Actor, reason: str) -> ArtifactRef:
        """Store the compiled set, reusing the latest version when the rules are unchanged."""
        latest = self.store.latest(ArtifactKind.CONSTRAINT_SET, cs.id)
        if latest is not None:
            stored = self.store.get(latest, ConstraintSet)
            if (
                stored.model_dump(mode="json")["constraints"]
                == cs.model_dump(mode="json")["constraints"]
            ):
                return latest
        return self.store.put(ArtifactKind.CONSTRAINT_SET, cs.id, cs, actor, reason=reason)

    def _constraints(self, inp: Inputs, actor: Actor) -> tuple[ConstraintSet, list[str], list[str]]:
        refs = [r for r in (inp.site_ref, inp.program_ref, inp.brief_ref, inp.codepack_ref) if r]
        res = compile_constraints(
            inp.program,
            inp.site,
            created_at=self.store.clock(),
            actor=actor,
            brief=inp.brief,
            codepack=inp.codepack,
            inputs=refs,
        )
        return res.constraints, res.code_rules_not_checked, res.notes

    # --------------------------------------------------------------- generate

    def generate(
        self,
        actor: Actor,
        *,
        strategies: list[str] | None = None,
        seed: int = 0,
        out_dir: Path | None = None,
        exploratory: bool = False,
        deterministic_time: float = 4.0,
    ) -> GenerationOutcome:
        for s in strategies or []:
            if s not in STRATEGY_LABELS:
                raise PlanWorkflowError(
                    f"unknown strategy {s!r}; known: {', '.join(STRATEGY_ORDER)}"
                )
        if not exploratory and self.wf.status().approvals.get(Gate.PLAN) is not None:
            raise PlanWorkflowError("a plan is approved; a human must reopen the plan gate first")
        inp = self.inputs(exploratory)
        constraints, not_checked, notes = self._constraints(inp, actor)
        req = GenerationRequest(
            site=inp.site,
            program=inp.program,
            constraints=constraints,
            site_ref=inp.site_ref,
            program_ref=inp.program_ref,
            created_at=self.store.clock(),
            strategies=strategies,
            seed=seed,
            deterministic_time=deterministic_time,
        )
        candidates = CpSatPlanGenerator().candidates(req)
        outcome = GenerationOutcome(exploratory, [StoredOption(c) for c in candidates], notes=notes)
        if not_checked:
            outcome.notes.append(
                "CodePack rules not checked (no evaluator for their parameters): "
                + ", ".join(not_checked)
            )
        if not outcome.generated:
            raise PlanWorkflowError(
                "no strategy produced a layout; nothing was stored: "
                + "; ".join(f"{c.strategy}: {c.reason}" for c in candidates)
            )
        if exploratory:
            for opt in outcome.generated:
                plan = opt.candidate.plan
                assert plan is not None
                ref = ArtifactRef(
                    kind=ArtifactKind.PLAN, id=plan.option_id, version=1, sha256=content_hash(plan)
                )
                opt.report = self._evaluate(plan, ref, inp, constraints)
        else:
            state = self.wf.state
            if state is not S.CONCEPT_GENERATION:
                self.wf.transition(
                    S.CONCEPT_GENERATION,
                    actor,
                    "generating plan concepts from the approved program",
                )
            outcome.constraints_ref = self._store_constraints(
                constraints, actor, "compiled for plan generation"
            )
            for opt in outcome.generated:
                plan = opt.candidate.plan
                assert plan is not None
                plan = plan.model_copy(
                    update={
                        "provenance": plan.provenance.model_copy(
                            update={"inputs": [*plan.provenance.inputs, outcome.constraints_ref]}
                        )
                    }
                )
                opt.candidate.plan = plan
                opt.plan_ref = self.store.put(
                    ArtifactKind.PLAN,
                    plan.option_id,
                    plan,
                    actor,
                    reason=f"generated concept ({plan.strategy})",
                )
                opt.report = self._evaluate(
                    plan, opt.plan_ref, inp, constraints, outcome.constraints_ref
                )
                opt.report_ref = self.store.put(
                    ArtifactKind.EVALUATION_REPORT,
                    opt.report.id,
                    opt.report,
                    actor,
                    reason="evaluated concept",
                )
            self.wf.transition(S.CONCEPT_REVIEW, actor, "plan concepts ready for owner review")
            outcome.states.append(self.wf.state.value)
        if out_dir is not None:
            banner = EXPLORATORY_BANNER if exploratory else None
            for opt in outcome.generated:
                opt.export_dir = self.export(
                    opt.candidate.plan, opt.plan_ref, opt.report, inp, out_dir, banner=banner
                )
            rows = [
                (o.candidate.plan, o.plan_ref.version if o.plan_ref else None, o.report)
                for o in outcome.generated
            ]
            infeasible = [
                (c.candidate.strategy, c.candidate.reason or "")
                for c in outcome.options
                if c.candidate.plan is None
            ]
            outcome.comparison = Path(out_dir) / "comparison.md"
            outcome.comparison.parent.mkdir(parents=True, exist_ok=True)
            outcome.comparison.write_text(
                comparison_markdown(rows, infeasible, banner=banner), encoding="utf-8"
            )
        return outcome

    def _evaluate(self, plan, ref, inp: Inputs, constraints, constraints_ref=None):
        return evaluate_plan(
            plan,
            ref,
            site=inp.site,
            program=inp.program,
            constraints=constraints,
            codepack=inp.codepack,
            created_at=self.store.clock(),
            site_verified=inp.site_verified,
            inputs=[r for r in (inp.site_ref, inp.program_ref, constraints_ref) if r],
        )

    # ----------------------------------------------------------------- revise

    def revise(
        self,
        option_id: str,
        text: str,
        actor: Actor,
        *,
        ops: list[str] | None = None,
        kind: ChangeRequestKind = ChangeRequestKind.MODIFY,
        version: int | None = None,
        seed: int | None = None,
        out_dir: Path | None = None,
    ) -> RevisionOutcome:
        ops = list(ops or [])
        if not text.strip():
            raise PlanWorkflowError("a revision needs the owner's request, verbatim")
        if kind not in (ChangeRequestKind.MODIFY, ChangeRequestKind.RESTART_FROM_PROGRAM):
            raise PlanWorkflowError(
                f"{kind.value} revisions are not supported yet; use `plan generate` for "
                "alternatives, or express the change as explicit operations (--area, --separate, "
                "--adjacent, --near, --level, --rethink, --strategy)"
            )
        status = self.wf.status()
        if Gate.PLAN in status.approvals or status.state not in (
            S.CONCEPT_GENERATION,
            S.CONCEPT_REVIEW,
        ):
            raise PlanWorkflowError(
                f"plans can be revised during concept generation or review; the project is in "
                f"{status.state.value}. An approved plan is frozen: a human must reopen the plan "
                "gate (`house-ai workflow reopen <dir> plan`)."
            )
        refs = self.store.refs(ArtifactKind.PLAN, option_id)
        if not refs:
            raise PlanWorkflowError(f"no plan named {option_id!r}")
        base_ref = next((r for r in refs if r.version == version), None) if version else refs[-1]
        if base_ref is None:
            raise PlanWorkflowError(f"{option_id} has no version {version}")
        base = self.store.get(base_ref, PlanVersion)
        inp = self.inputs(exploratory=False)
        strategy, solver_opts = self._apply_ops(base, inp.program, ops, kind)
        constraints, _, _ = self._constraints(inp, actor)
        cr_n = sum(1 for r in refs) + 1
        cr = ChangeRequest(
            id=f"cr-{option_id}-{cr_n}"[:64],
            text=text,
            kind=kind,
            requested_by=actor,
            requested_at=self.store.clock(),
            base_versions=[base_ref],
        )
        req = GenerationRequest(
            site=inp.site,
            program=inp.program,
            constraints=constraints,
            site_ref=inp.site_ref,
            program_ref=inp.program_ref,
            created_at=self.store.clock(),
            strategies=[strategy],
            seed=base.generation.seed if seed is None and base.generation else (seed or 0),
            deterministic_time=base.generation.deterministic_time_limit if base.generation else 4.0,
            solver=solver_opts,
            parent=base_ref,
            change_request=cr,
            revision_ops=ops,
            option_id=option_id,
        )
        cand = CpSatPlanGenerator().candidates(req)[0]
        if cand.plan is None:
            raise PlanWorkflowError(
                f"the revision cannot be laid out; nothing was stored: {cand.reason}"
            )
        if self.wf.state is S.CONCEPT_REVIEW:
            self.wf.transition(S.CONCEPT_GENERATION, actor, f"revising {option_id}: {text}")
        c_ref = self._store_constraints(constraints, actor, "compiled for a plan revision")
        plan = cand.plan.model_copy(
            update={
                "provenance": cand.plan.provenance.model_copy(
                    update={"inputs": [*cand.plan.provenance.inputs, c_ref]}
                )
            }
        )
        plan_ref = self.store.put(
            ArtifactKind.PLAN,
            option_id,
            plan,
            actor,
            reason=f"revision of v{base_ref.version}: {text}",
        )
        report = self._evaluate(plan, plan_ref, inp, constraints, c_ref)
        report_ref = self.store.put(
            ArtifactKind.EVALUATION_REPORT, report.id, report, actor, reason="evaluated revision"
        )
        before_eval = self._report_for(base_ref)
        rev = revision_report(
            report_id=f"rev-{option_id}-v{plan_ref.version}"[:64],
            text=text,
            before=base,
            after=plan,
            before_ref=base_ref,
            after_ref=plan_ref,
            before_eval=before_eval,
            after_eval=report,
            provenance=Provenance(
                created_at=self.store.clock(),
                created_by=actor,
                method="plan_revision",
                tool="house-ai plan revise",
                inputs=[base_ref, plan_ref],
            ),
        )
        rev_ref = self.store.put(
            ArtifactKind.REVISION_REPORT,
            rev.id,
            rev,
            actor,
            reason=f"revision report for {option_id} v{plan_ref.version}",
        )
        self.wf.transition(
            S.CONCEPT_REVIEW, actor, f"{option_id} v{plan_ref.version} ready for owner review"
        )
        opt = StoredOption(cand, plan_ref, report, report_ref)
        export = None
        if out_dir is not None:
            export = self.export(plan, plan_ref, report, inp, out_dir)
            (export / "revision.md").write_text(revision_markdown(rev), encoding="utf-8")
            (export / "revision.json").write_text(pretty_json(rev), encoding="utf-8")
            opt.export_dir = export
        return RevisionOutcome(opt, rev, rev_ref, export)

    def _apply_ops(
        self, base: PlanVersion, program: SpaceProgram, ops: list[str], kind: ChangeRequestKind
    ) -> tuple[str, SolverOptions]:
        rooms = expand_program(program)
        by_item: dict[str, list[str]] = {}
        for r in rooms.rooms:
            by_item.setdefault(r.item.id, []).append(r.space_id)
        spaces = {r.space_id for r in rooms.rooms}

        def resolve(name: str) -> list[str]:
            if name in spaces:
                return [name]
            if name in by_item:
                return by_item[name]
            raise PlanWorkflowError(
                f"unknown room {name!r}; use a program item id (pi-...) or a space id (sp-...)"
            )

        strategy = base.strategy or ""
        opts = SolverOptions()
        rethink: set[str] = set()
        for op in ops:
            verb, _, arg = op.partition(":")
            if verb == "area":
                name, _, value = arg.partition("=")
                for sid in resolve(name):
                    item = rooms.room(sid).item
                    target = float(value)
                    if item.min_area_m2 is not None and target < item.min_area_m2:
                        raise PlanWorkflowError(
                            f"{target:g} m² is below the approved program minimum for {item.id} "
                            f"({item.min_area_m2:g} m²); revise the program instead"
                        )
                    opts.targets[sid] = target
            elif verb == "level":
                name, _, pref = arg.partition("=")
                if pref not in LEVEL_PREFS:
                    raise PlanWorkflowError(f"level must be one of {sorted(LEVEL_PREFS)}")
                for sid in resolve(name):
                    opts.level_prefs[sid] = pref
            elif verb in ("separate", "adjacent", "near"):
                a, _, b = arg.partition(",")
                kind_ = {
                    "separate": AdjacencyKind.SEPARATED,
                    "adjacent": AdjacencyKind.ADJACENT,
                    "near": AdjacencyKind.NEAR,
                }[verb]
                for sa in resolve(a):
                    for sb in resolve(b):
                        opts.relations.append(
                            Relation(sa, sb, kind_, Strength.SOFT, 5.0, f"revision-{verb}")
                        )
            elif verb == "rethink":
                if arg == "all":
                    rethink |= spaces
                else:
                    zone = [r.space_id for r in rooms.rooms if r.item.zone_id == arg]
                    rethink |= set(zone) if zone else set(resolve(arg))
            elif verb == "strategy":
                if arg not in STRATEGY_LABELS:
                    raise PlanWorkflowError(f"unknown strategy {arg!r}")
                strategy = arg
            else:
                raise PlanWorkflowError(f"unknown revision operation {op!r}")
        if strategy not in STRATEGY_LABELS:
            raise PlanWorkflowError(
                f"{base.option_id} was not generated by a strategy ({base.strategy}); add "
                "--strategy to choose one"
            )
        if (
            kind is ChangeRequestKind.MODIFY
            and base.generation is not None
            and strategy == base.strategy
        ):
            for p in base.generation.placements:
                if p.space_id in spaces and p.space_id not in rethink:
                    opts.hints[p.space_id] = (p.row_id, to_dm(p.start_m))
            for key, value in base.generation.parameters.items():
                if key.endswith("_start_m") and isinstance(value, int | float) and not rethink:
                    opts.bar_hints[key.removesuffix("_start_m")] = to_dm(float(value))
        return strategy, opts

    def _report_for(self, ref: ArtifactRef) -> EvaluationReport | None:
        found = None
        for r in self.store.refs(ArtifactKind.EVALUATION_REPORT, report_id(ref.id)):
            rep = self.store.get(r, EvaluationReport)
            if rep.plan_ref.model_dump() == ref.model_dump():
                found = rep
        return found

    # ----------------------------------------------------------------- review

    def request_review(
        self, option_id: str, actor: Actor, version: int | None = None
    ) -> tuple[ArtifactRef, WorkflowEvent]:
        refs = self.store.refs(ArtifactKind.PLAN, option_id)
        ref = (
            next((r for r in refs if r.version == version), None)
            if version
            else (refs[-1] if refs else None)
        )
        if ref is None:
            raise PlanWorkflowError(f"no plan {option_id}" + (f" v{version}" if version else ""))
        if self.wf.state is not S.CONCEPT_REVIEW:
            raise PlanWorkflowError(
                f"plan review is requested from CONCEPT_REVIEW; the project "
                f"is in {self.wf.state.value}"
            )
        return ref, self.wf.request_approval(Gate.PLAN, ref, actor)

    # ----------------------------------------------------------------- export

    def export(
        self,
        plan: PlanVersion,
        ref: ArtifactRef | None,
        report: EvaluationReport | None,
        inp: Inputs | None,
        out_dir: Path,
        *,
        banner: str | None = None,
    ) -> Path:
        version = ref.version if ref else None
        folder = Path(out_dir) / plan.option_id / (f"v{version:04d}" if version else "exploratory")
        folder.mkdir(parents=True, exist_ok=True)
        site = inp.site if inp else None
        program = inp.program if inp else None
        (folder / "plan.json").write_text(pretty_json(plan), encoding="utf-8")
        (folder / "plan.svg").write_text(
            render_plan_svg(plan, site, report, version=version, banner=banner), encoding="utf-8"
        )
        if report is not None:
            (folder / "metrics.json").write_text(pretty_json(report), encoding="utf-8")
            violations = {
                "plan": ref.model_dump(mode="json") if ref else None,
                "compliance": report.compliance.label,
                "hard": [v.model_dump(mode="json") for v in report.hard_violations],
                "soft": [
                    v.model_dump(mode="json")
                    for v in report.violations
                    if v not in report.hard_violations
                ],
            }
            (folder / "violations.json").write_text(
                json.dumps(violations, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (folder / "explanation.md").write_text(
                explanation_markdown(plan, version, report, program, banner=banner),
                encoding="utf-8",
            )
        program_assumptions = []
        for a_ref in self.store.latest_of_kind(ArtifactKind.ASSUMPTIONS):
            program_assumptions += [
                a.model_dump(mode="json")
                for a in self.store.get(a_ref, AssumptionsFile).assumptions
            ]
        site_unverified = inp is not None and not inp.site_verified
        assumptions = {
            "plan": [a.model_dump(mode="json") for a in plan.model.assumptions],
            "plan_issues": [i.model_dump(mode="json") for i in plan.model.issues],
            "program": program_assumptions,
            "site_verified": not site_unverified,
            "note": "Plan assumptions come from the generator; program assumptions from the "
            "interview. Nothing here is a verified fact unless its status says so.",
        }
        (folder / "assumptions.json").write_text(
            json.dumps(assumptions, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return folder

    def stored(self) -> list[tuple[PlanVersion, ArtifactRef, EvaluationReport | None]]:
        rows = []
        for ref in self.store.latest_of_kind(ArtifactKind.PLAN):
            rows.append((self.store.get(ref, PlanVersion), ref, self._report_for(ref)))
        return rows

    def compare(self, out_dir: Path | None = None) -> str:
        rows = [(p, r.version, e) for p, r, e in self.stored() if e is not None]
        text = comparison_markdown(rows, [])
        if out_dir is not None:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            (Path(out_dir) / "comparison.md").write_text(text, encoding="utf-8")
        return text
