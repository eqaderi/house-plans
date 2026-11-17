"""Plan concepts in a project: generate, evaluate, revise, export, request review.

Gated mode (the normal case) works only on the human-approved site and
program versions, stores every plan, evaluation and revision as a new
immutable artifact version and moves the workflow PROGRAM_APPROVED ->
PLAN_GENERATION -> PLAN_REVIEW. The plan gate itself stays human-only
(``house-ai workflow approve``). Every precondition is checked before anything
is written, so a refused command leaves the project untouched.

Exploratory mode writes nothing to the project store: it runs the same
pipeline on the newest site and program versions (approved or not) and
exports files stamped as exploratory, so an owner can see options before the
gates are passed. It never changes the workflow.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from house_ai.constants.strategies import STRATEGY_EXTENDED_ORDER
from house_ai.constraints.compiler import compile_constraints
from house_ai.domain.brief import DesignBrief
from house_ai.domain.codepack import CodePack
from house_ai.domain.constraints import ConstraintSet
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.plan import (
    ChangeRequest,
    ChangeRequestKind,
    PlanVersion,
    RevisionReport,
)
from house_ai.domain.program import SpaceProgram
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import Actor, ArtifactKind, ArtifactRef, Provenance
from house_ai.domain.records import AssumptionsFile, Severity
from house_ai.domain.revision_ops import RevisionOp, RevisionOpError, RevisionVerb
from house_ai.domain.site import Site
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.evaluation.explain import (
    comparison_markdown,
    explanation_markdown,
    revision_markdown,
    revision_report,
)
from house_ai.evaluation.report import evaluate_plan, report_id
from house_ai.generation.engines import optimised_objectives
from house_ai.generation.generator import (
    Candidate,
    CpSatPlanGenerator,
    GenerationRequest,
)
from house_ai.generation.massing import STRATEGY_LABELS
from house_ai.generation.revision import compile_revision, resolve_spaces, unmet_requests
from house_ai.generation.rooms import space_id_for
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import content_hash, pretty_json
from house_ai.validation.topology import validate_proposal

from .workflow import GateStatus, HumanAction, NextHumanAction, Workflow, WorkflowError

S = WorkflowState
V = RevisionVerb
EXPLORATORY_BANNER = (
    "EXPLORATORY: not stored in the project; the site and/or program are not approved by the "
    "owner. Not a validated plan."
)
GENERATION_STATES = {S.PROGRAM_APPROVED, S.PLAN_GENERATION, S.PLAN_REVIEW}


class PlanWorkflowError(WorkflowError):
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
    site_approved: bool = False


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
                    hint = " Use --exploratory to preview plan options without storing them."
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
                    f"no {missing} in this project yet; plan options need a site and a program "
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
            site_approved=Gate.SITE in status.approvals
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
        """Reuse a compilation only when its rules and pinned inputs are unchanged."""
        latest = self.store.latest(ArtifactKind.CONSTRAINT_SET, cs.id)
        if latest is not None:
            stored = self.store.get(latest, ConstraintSet)
            if (
                stored.model_dump(mode="json")["constraints"]
                == cs.model_dump(mode="json")["constraints"]
                and stored.provenance.inputs == cs.provenance.inputs
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

    def propose(
        self,
        actor: Actor,
        proposal: ConceptProposal,
        *,
        out_dir: Path | None = None,
        exploratory: bool = False,
        deterministic_time: float = 4.0,
        seed: int = 0,
    ) -> GenerationOutcome:
        inp = self.inputs(exploratory)
        findings = validate_proposal(proposal, inp.program, inp.site)
        blocking = [f for f in findings if f.severity is Severity.BLOCKING]
        if blocking:
            raise PlanWorkflowError(
                "proposal validation failed: "
                + "; ".join(f"{f.code}: {f.message}" for f in blocking)
            )

        proposal_ref: ArtifactRef
        if not exploratory:
            proposal_ref = self.store.put(
                ArtifactKind.CONCEPT_PROPOSAL,
                proposal.id,
                proposal,
                actor,
                reason=f"proposal: {proposal.name}",
            )
        else:
            proposal_ref = ArtifactRef(
                kind=ArtifactKind.CONCEPT_PROPOSAL,
                id=proposal.id,
                version=1,
                sha256=content_hash(proposal),
            )

        strategies = [proposal.target_strategy] if proposal.target_strategy else None
        return self.generate(
            actor,
            strategies=strategies,
            seed=seed,
            out_dir=out_dir,
            exploratory=exploratory,
            deterministic_time=deterministic_time,
            proposal=proposal,
            proposal_ref=proposal_ref,
        )

    def generate(
        self,
        actor: Actor,
        *,
        strategies: list[str] | None = None,
        seed: int = 0,
        out_dir: Path | None = None,
        exploratory: bool = False,
        deterministic_time: float = 4.0,
        proposal: ConceptProposal | None = None,
        proposal_ref: ArtifactRef | None = None,
        sectional_strategy: str | None = None,
    ) -> GenerationOutcome:
        for s in strategies or []:
            if s not in STRATEGY_LABELS:
                raise PlanWorkflowError(
                    f"unknown strategy {s!r}; known: {', '.join(STRATEGY_EXTENDED_ORDER)}"
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
            proposal=proposal,
            proposal_ref=proposal_ref,
            sectional_strategy=sectional_strategy,
        )
        candidates = CpSatPlanGenerator().candidates(req)
        outcome = GenerationOutcome(exploratory, [StoredOption(c) for c in candidates], notes=notes)
        if proposal is not None:
            outcome.notes.append(f"Topology proposal applied: {proposal.name} ({proposal.id})")
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
            if state is not S.PLAN_GENERATION:
                self.wf.transition(
                    S.PLAN_GENERATION,
                    actor,
                    "generating plan options from the approved program",
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
                    reason=f"generated plan option ({plan.strategy})",
                )
                opt.report = self._evaluate(
                    plan, opt.plan_ref, inp, constraints, outcome.constraints_ref
                )
                opt.report_ref = self.store.put(
                    ArtifactKind.EVALUATION_REPORT,
                    opt.report.id,
                    opt.report,
                    actor,
                    reason="evaluated plan version",
                )
            self.wf.transition(S.PLAN_REVIEW, actor, "plan options ready for owner review")
            outcome.states.append(self.wf.state.value)
        if out_dir is not None:
            banner = EXPLORATORY_BANNER if exploratory else None
            for opt in outcome.generated:
                opt.export_dir = self.export(
                    opt.candidate.plan,
                    opt.plan_ref,
                    opt.report,
                    inp,
                    out_dir,
                    banner=banner,
                    constraints=constraints,
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
            site_approved=inp.site_approved,
            inputs=[r for r in (inp.site_ref, inp.program_ref, constraints_ref) if r],
        )

    # ----------------------------------------------------------------- revise

    # ----------------------------------------------------------------- revise

    def revise(
        self,
        option_id: str,
        text: str,
        actor: Actor,
        *,
        ops: Sequence[RevisionOp | str] | None = None,
        kind: ChangeRequestKind = ChangeRequestKind.MODIFY,
        version: int | None = None,
        seed: int | None = None,
        out_dir: Path | None = None,
        proposal: ConceptProposal | None = None,
        base_versions: list[str | ArtifactRef] | None = None,
        features: list[str] | None = None,
        feature_confirmation: str | None = None,
    ) -> RevisionOutcome:
        try:
            ops = [op if isinstance(op, RevisionOp) else RevisionOp.parse(op) for op in ops or []]
        except RevisionOpError as exc:
            raise PlanWorkflowError(str(exc)) from exc
        if not text.strip():
            raise PlanWorkflowError("a revision needs the owner's request, verbatim")
        if kind not in (
            ChangeRequestKind.MODIFY,
            ChangeRequestKind.RESTART_FROM_PROGRAM,
            ChangeRequestKind.COMBINE,
        ):
            raise PlanWorkflowError(
                f"{kind.value} revisions are not supported yet; use `plan generate` for "
                "alternatives, or express the change as explicit operations (--area, --separate, "
                "--adjacent, --near, --level, --rethink, --strategy)"
            )
        status = self.wf.status()
        if Gate.PLAN in status.approvals or status.state not in (
            S.PLAN_GENERATION,
            S.PLAN_REVIEW,
        ):
            raise PlanWorkflowError(
                f"plans can be revised during plan generation or review; the project is in "
                f"{status.state.value}. An approved plan is frozen: a human must reopen the plan "
                "gate.",
                next_action=NextHumanAction(HumanAction.REOPEN, Gate.PLAN),
            )

        base_refs: list[ArtifactRef] = []
        if kind is ChangeRequestKind.COMBINE:
            if base_versions:
                for b in base_versions:
                    if isinstance(b, ArtifactRef):
                        base_refs.append(b)
                    else:
                        b_refs = self.store.refs(ArtifactKind.PLAN, b)
                        if not b_refs:
                            raise PlanWorkflowError(f"no plan named {b!r}")
                        base_refs.append(b_refs[-1])
            else:
                refs = self.store.refs(ArtifactKind.PLAN, option_id)
                if len(refs) >= 2:
                    base_refs = [refs[-2], refs[-1]]
                else:
                    raise PlanWorkflowError(
                        "a combine revision requires at least two base versions"
                    )
            if len(base_refs) < 2:
                raise PlanWorkflowError("a combine revision requires at least two base versions")
            base_ref = base_refs[0]
            base = self.store.get(base_ref, PlanVersion)
            if not features or not feature_confirmation or not feature_confirmation.strip():
                raise PlanWorkflowError(
                    "combine needs explicit --feature SOURCE:ROOM=area,level,connections mappings "
                    "and --feature-confirmation containing the owner's exact confirmation"
                )
            sources = {r.id: (self.store.get(r, PlanVersion), r) for r in base_refs}
            if len(sources) != len(base_refs):
                raise PlanWorkflowError("combine bases must be distinct alternatives")
            transferred = set()
            for feature in features:
                source_id, sep, rest = feature.partition(":")
                sid, eq, kinds = rest.partition("=")
                aspects = kinds.split(",")
                if (
                    not sep
                    or not eq
                    or source_id not in sources
                    or not set(aspects) <= {"area", "level", "connections"}
                ):
                    raise PlanWorkflowError(f"invalid feature mapping {feature!r}")
                source, _ = sources[source_id]
                room = next((r for r in source.model.spaces if r.id == sid), None)
                if room is None:
                    raise PlanWorkflowError(f"{source_id} has no space {sid!r}")
                transferred.add(source_id)
                if "area" in aspects:
                    ops.append(RevisionOp(op_type=V.AREA, target=sid, value=f"{room.area_m2:g}"))
                if "level" in aspects:
                    entry = next(
                        (lv.elevation_m for lv in source.model.levels if lv.id == "lv-entry"), 0
                    )
                    delta = source.model.level(room.level_id).elevation_m - entry
                    pref = "lower" if delta < -0.01 else "upper" if delta > 0.01 else "entry"
                    ops.append(RevisionOp(op_type=V.LEVEL, target=sid, value=pref))
                if "connections" in aspects:
                    neighbors = {
                        b if a == sid else a
                        for o in source.model.openings
                        if o.is_passable
                        for a, b in [o.connects]
                        if sid in (a, b)
                    }
                    known = {
                        space_id_for(it, i)
                        for it in self.inputs(False).program.space_requirements
                        for i in range(1, it.quantity + 1)
                    }
                    for neighbor in sorted(neighbors & known):
                        ops.append(RevisionOp(op_type=V.CONNECT, target=f"{sid},{neighbor}"))
            if set(sources) - {base_ref.id} - transferred:
                raise PlanWorkflowError("each additional base needs an explicit feature mapping")
        else:
            refs = self.store.refs(ArtifactKind.PLAN, option_id)
            if not refs:
                raise PlanWorkflowError(f"no plan named {option_id!r}")
            base_ref = (
                next((r for r in refs if r.version == version), None) if version else refs[-1]
            )
            if base_ref is None:
                raise PlanWorkflowError(f"{option_id} has no version {version}")
            base = self.store.get(base_ref, PlanVersion)
            base_refs = [base_ref]

        inp = self.inputs(exploratory=False)
        try:
            request = compile_revision(
                base,
                inp.program,
                ops,
                inherit=kind in (ChangeRequestKind.MODIFY, ChangeRequestKind.COMBINE),
            )
        except RevisionOpError as exc:
            raise PlanWorkflowError(str(exc)) from exc
        strategy, asked = request.strategy, request.requests

        loaded_proposal = proposal
        proposal_ref: ArtifactRef | None = None
        if loaded_proposal is None and kind is not ChangeRequestKind.RESTART_FROM_PROGRAM:
            proposal_ref = next(
                (
                    r
                    for r in reversed(base.provenance.inputs)
                    if r.kind is ArtifactKind.CONCEPT_PROPOSAL
                ),
                None,
            )
            if proposal_ref:
                loaded_proposal = self.store.get(proposal_ref, ConceptProposal)
        for op in ops:
            if op.op_type is V.PROPOSAL:
                p_path = Path(op.target)
                if not p_path.exists():
                    raise PlanWorkflowError(f"proposal file not found: {p_path}")
                try:
                    raw = yaml.safe_load(p_path.read_text(encoding="utf-8"))
                    loaded_proposal = ConceptProposal.model_validate(raw)
                except Exception as exc:
                    raise PlanWorkflowError(f"invalid proposal file {p_path}: {exc}") from exc
                break

        if loaded_proposal is not None:
            findings = validate_proposal(loaded_proposal, inp.program, inp.site)
            blocking = [f for f in findings if f.severity is Severity.BLOCKING]
            if blocking:
                raise PlanWorkflowError(
                    "proposal validation failed: "
                    + "; ".join(f"{f.code}: {f.message}" for f in blocking)
                )
            proposal_ref = proposal_ref or self.store.put(
                ArtifactKind.CONCEPT_PROPOSAL,
                loaded_proposal.id,
                loaded_proposal,
                actor,
                reason=f"proposal: {loaded_proposal.name}",
            )
            if loaded_proposal.target_strategy and not any(
                op.op_type is V.STRATEGY for op in ops
            ):
                strategy = loaded_proposal.target_strategy
            if loaded_proposal.stair_cores and not asked.stair_position:
                asked.stair_position = loaded_proposal.stair_cores[0].position
            if loaded_proposal.outdoor_links:
                for ol in loaded_proposal.outdoor_links:
                    try:
                        sids = resolve_spaces(ol.program_item_id, inp.program)
                    except RevisionOpError as exc:
                        raise PlanWorkflowError(str(exc)) from exc
                    for sid in sids:
                        asked.outdoor_links.append((sid, ol.kind))

        constraints, _, _ = self._constraints(inp, actor)
        existing_refs = self.store.refs(ArtifactKind.PLAN, option_id)
        cr_n = len(existing_refs) + 1
        cr = ChangeRequest(
            id=f"cr-{option_id}-{cr_n}"[:64],
            text=text,
            kind=kind,
            requested_by=actor,
            requested_at=self.store.clock(),
            base_versions=base_refs,
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
            requests=asked,
            parent=base_ref,
            change_request=cr,
            revision_ops=[str(op) for op in request.operations],
            option_id=option_id,
            proposal=loaded_proposal,
            proposal_ref=proposal_ref,
            inputs=base_refs,
        )
        cand = CpSatPlanGenerator().candidates(req)[0]
        if cand.plan is None:
            raise PlanWorkflowError(
                f"the revision cannot be laid out; nothing was stored: {cand.reason}"
            )
        if self.wf.state is S.PLAN_REVIEW:
            self.wf.transition(S.PLAN_GENERATION, actor, f"revising {option_id}: {text}")
        c_ref = self._store_constraints(constraints, actor, "compiled for a plan revision")
        if kind is ChangeRequestKind.COMBINE and cand.plan.generation:
            cand.plan = cand.plan.model_copy(
                update={
                    "generation": cand.plan.generation.model_copy(
                        update={
                            "parameters": {
                                **cand.plan.generation.parameters,
                                "feature_mappings": json.dumps(features),
                                "feature_confirmation": feature_confirmation,
                            }
                        }
                    )
                }
            )
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

        # Check every request this version carries, new and inherited (S7-23, S10-03).
        unmet = unmet_requests(
            request.operations,
            plan.model,
            inp.program,
            parent_ops=request.parent_operations,
            parent_model=base.model,
        )
        if unmet:
            rev = rev.model_copy(
                update={"new_violations": sorted(set(rev.new_violations) | set(unmet))}
            )

        rev_ref = self.store.put(
            ArtifactKind.REVISION_REPORT,
            rev.id,
            rev,
            actor,
            reason=f"revision report for {option_id} v{plan_ref.version}",
        )
        self.wf.transition(
            S.PLAN_REVIEW, actor, f"{option_id} v{plan_ref.version} ready for owner review"
        )
        opt = StoredOption(cand, plan_ref, report, report_ref)
        export = None
        if out_dir is not None:
            export = self.export(plan, plan_ref, report, inp, out_dir, constraints=constraints)
            (export / "revision.md").write_text(revision_markdown(rev), encoding="utf-8")
            (export / "revision.json").write_text(pretty_json(rev), encoding="utf-8")
            opt.export_dir = export
        return RevisionOutcome(opt, rev, rev_ref, export)

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
    ) -> tuple[ArtifactRef, GateStatus]:
        refs = self.store.refs(ArtifactKind.PLAN, option_id)
        ref = (
            next((r for r in refs if r.version == version), None)
            if version
            else (refs[-1] if refs else None)
        )
        if ref is None:
            raise PlanWorkflowError(f"no plan {option_id}" + (f" v{version}" if version else ""))
        if self.wf.state is not S.PLAN_REVIEW:
            raise PlanWorkflowError(
                f"plan review is requested from PLAN_REVIEW; the project "
                f"is in {self.wf.state.value}"
            )
        return ref, self.wf.request_approval(Gate.PLAN, ref, actor)

    # ----------------------------------------------------------------- export

    def inputs_for_plan(self, plan: PlanVersion) -> Inputs | None:
        """Load the immutable site/program the plan names, including for old versions."""
        site_ref, program_ref = plan.model.site_ref, plan.model.program_ref
        if site_ref is None or program_ref is None:
            return None
        approval = self.wf.status().approvals.get(Gate.SITE)
        return Inputs(
            site=self.store.get(site_ref, Site),
            site_ref=site_ref,
            program=self.store.get(program_ref, SpaceProgram),
            program_ref=program_ref,
            site_approved=approval is not None and approval.artifact == site_ref,
        )

    def export(
        self,
        plan: PlanVersion,
        ref: ArtifactRef | None,
        report: EvaluationReport | None,
        inp: Inputs | None,
        out_dir: Path,
        *,
        banner: str | None = None,
        constraints: ConstraintSet | None = None,
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
        from house_ai.render2d.hillside_export import export_hillside_views

        export_hillside_views(plan.model, site, folder)
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
            if constraints is None and inp is not None:
                constraints = getattr(inp, "constraints", None)
            (folder / "explanation.md").write_text(
                explanation_markdown(
                    plan,
                    version,
                    report,
                    program,
                    banner=banner,
                    constraints=constraints,
                    optimised=optimised_objectives(plan.generation) if plan.generation else None,
                ),
                encoding="utf-8",
            )
        program_assumptions = []
        # Program build companions share its provenance. Newer companions may
        # describe a different interview, so never substitute the latest file.
        if program is not None:
            for a_ref in self.store.refs(ArtifactKind.ASSUMPTIONS):
                companion = self.store.get(a_ref, AssumptionsFile)
                if companion.provenance == program.provenance:
                    program_assumptions += [
                        a.model_dump(mode="json") for a in companion.assumptions
                    ]
        assumptions = {
            "plan": [a.model_dump(mode="json") for a in plan.model.assumptions],
            "plan_issues": [i.model_dump(mode="json") for i in plan.model.issues],
            "program": program_assumptions,
            "site_approved": inp.site_approved if inp is not None else None,
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
