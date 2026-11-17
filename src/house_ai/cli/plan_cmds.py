"""``house-ai plan ...``: plan option generation, evaluation, revision and review (Milestone D).

Agents drive these commands for the owner. The plan gate is still
approved only by a human with ``house-ai workflow approve <dir> plan``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from house_ai.constants.strategies import (
    STRATEGY_EXTENDED_ORDER,
    STRATEGY_LABELS,
    STRATEGY_ORDER,
)
from house_ai.domain.plan import ChangeRequestKind
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.workflow import Gate
from house_ai.orchestration.plans import (
    GenerationOutcome,
    PlanService,
    PlanWorkflowError,
    RevisionOutcome,
)
from house_ai.orchestration.workflow import HumanAction, NextHumanAction
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import load_document
from house_ai.storage.projects import resolve_project_dir

from . import human
from .exit_codes import EXIT_FAIL, EXIT_OK, EXIT_USAGE


def _out(text: str = "") -> None:
    print(text)


def _refused(exc: PlanWorkflowError, project: str) -> int:
    _out(f"refused: {exc}")
    if exc.next_action is not None:
        _out(human.next_line(exc.next_action, project))
    return EXIT_FAIL


#: Export folder for plan options under ``<project>/design``. Folders written before
#: ADR 0025 are named ``concepts``; they stay and are still read.
PLAN_OPTIONS_DIR, OLD_PLAN_OPTIONS_DIR = "plan-options", "concepts"


def _default_out(store: ProjectStore, exploratory: bool) -> Path:
    return store.root / "design" / (
        f"{PLAN_OPTIONS_DIR}-exploratory" if exploratory else PLAN_OPTIONS_DIR
    )


def existing_plan_options_dir(store: ProjectStore, given: str | None = None) -> Path | None:
    """The given folder, else the project's plan-option exports (new name first), if any."""
    if given:
        return Path(given)
    for name in (PLAN_OPTIONS_DIR, OLD_PLAN_OPTIONS_DIR):
        if (store.root / "design" / name).exists():
            return store.root / "design" / name
    return None


def add_plan_options_dir_argument(parser: argparse.ArgumentParser) -> None:
    """``--plan-options-dir`` with its old name ``--concepts-dir`` kept as an alias."""
    parser.add_argument(
        "--plan-options-dir", "--concepts-dir", dest="plan_options_dir",
        help="optional folder of exported plan options (default: <project>/design/plan-options, "
        "else design/concepts)",
    )


def cmd_plan_strategies(args: argparse.Namespace) -> int:
    for name in STRATEGY_ORDER:
        _out(f"{name:12} {STRATEGY_LABELS[name]}")
    return EXIT_OK


def _render_generation_outcome(
    res: GenerationOutcome, args: argparse.Namespace, *, extra_json: dict | None = None
) -> int:
    rows = []
    for opt in res.options:
        c = opt.candidate
        rep = opt.report
        rows.append(
            {
                "option_id": c.option_id,
                "strategy": c.strategy,
                "status": c.status,
                "reason": c.reason,
                "valid": c.valid if c.plan else None,
                "plan_ref": opt.plan_ref.model_dump(mode="json") if opt.plan_ref else None,
                "hard_violations": len(rep.hard_violations) if rep else None,
                "soft_violations": len(rep.violations) - len(rep.hard_violations) if rep else None,
                "export_dir": str(opt.export_dir) if opt.export_dir else None,
            }
        )
    if args.json:
        payload = {
            "exploratory": res.exploratory,
            "options": rows,
            "comparison": str(res.comparison) if res.comparison else None,
            "constraints_ref": res.constraints_ref.model_dump(mode="json")
            if res.constraints_ref
            else None,
            "notes": res.notes,
            **(extra_json or {}),
        }
        _out(json.dumps(payload, indent=2, ensure_ascii=False))
        return EXIT_OK
    if res.exploratory:
        _out("EXPLORATORY: nothing was stored; site/program approval is not implied.")
    for r in rows:
        if r["status"] == "generated":
            ver = f" v{r['plan_ref']['version']}" if r["plan_ref"] else ""
            _out(
                f"{r['option_id']}{ver} ({r['strategy']}): {r['hard_violations']} hard, "
                f"{r['soft_violations']} soft violation(s) -> {r['export_dir']}"
            )
        else:
            _out(f"{r['option_id']} ({r['strategy']}): not feasible: {r['reason']}")
    for n in res.notes:
        _out(f"note: {n}")
    _out(f"comparison: {res.comparison}")
    if not res.exploratory:
        approve = NextHumanAction(HumanAction.APPROVE, Gate.PLAN)
        _out(
            "state PLAN_REVIEW; show the owner the plan options, then `house-ai plan review "
            f"{args.dir} <option>`; the owner approves one version with "
            f"`{human.command_for(approve, args.dir)}`"
        )
    return EXIT_OK


def cmd_plan_generate(args: argparse.Namespace) -> int:
    store = ProjectStore(resolve_project_dir(args.dir))
    out = Path(args.out) if args.out else _default_out(store, args.exploratory)
    try:
        res = PlanService(store).generate(
            args.actor,
            strategies=args.strategy or None,
            sectional_strategy=getattr(args, "sectional_strategy", None),
            seed=args.seed,
            out_dir=out,
            exploratory=args.exploratory,
            deterministic_time=args.time,
        )
    except PlanWorkflowError as exc:
        return _refused(exc, args.dir)
    return _render_generation_outcome(res, args)


def cmd_plan_propose(args: argparse.Namespace) -> int:
    store = ProjectStore(resolve_project_dir(args.dir))
    doc = load_document(Path(args.proposal))
    try:
        proposal = ConceptProposal.model_validate(doc)
    except ValidationError as exc:
        _out(f"refused: proposal schema invalid: {exc}")
        return EXIT_FAIL
    out = Path(args.out) if args.out else _default_out(store, args.exploratory)
    try:
        res = PlanService(store).propose(
            args.actor,
            proposal,
            out_dir=out,
            exploratory=args.exploratory,
            deterministic_time=args.time,
            seed=args.seed,
        )
    except (PlanWorkflowError, ValidationError) as exc:
        _out(f"refused: {exc}")
        return EXIT_FAIL
    return _render_generation_outcome(res, args, extra_json={"proposal_id": proposal.id})


def _ops(args: argparse.Namespace) -> list[str]:
    ops = [f"area:{a}" for a in getattr(args, "area", [])]
    ops += [f"level:{a}" for a in getattr(args, "level", [])]
    ops += [f"separate:{a}" for a in getattr(args, "separate", [])]
    ops += [f"adjacent:{a}" for a in getattr(args, "adjacent", [])]
    ops += [f"near:{a}" for a in getattr(args, "near", [])]
    ops += [f"connect:{a}" for a in getattr(args, "connect", [])]
    ops += [f"outdoor:{a}" for a in getattr(args, "outdoor", [])]
    if getattr(args, "stair", None):
        ops.append(f"stair:{args.stair}")
    if getattr(args, "proposal", None):
        ops.append(f"proposal:{args.proposal}")
    ops += [f"rethink:{a}" for a in getattr(args, "rethink", [])]
    if getattr(args, "strategy", None):
        ops.append(f"strategy:{args.strategy}")
    return ops


def _render_revision_outcome(res: RevisionOutcome, args: argparse.Namespace) -> int:
    rev, ref = res.revision, res.option.plan_ref
    assert ref is not None and res.option.report is not None
    if getattr(args, "json", False):
        _out(
            json.dumps(
                {
                    "plan_ref": ref.model_dump(mode="json"),
                    "revision": rev.model_dump(mode="json"),
                    "export_dir": str(res.export_dir),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return EXIT_OK
    parent_note = f" (parent v{rev.from_version.version})" if rev.from_version else ""
    _out(f"stored {ref.id} v{ref.version}{parent_note}")
    _out(f"spaces changed: {', '.join(rev.rooms_changed) or 'none'}")
    for c in rev.area_changes:
        _out(f"  {c.space_id}: {c.before_m2} -> {c.after_m2} m²")
    for v in rev.new_violations:
        _out(f"new violation: {v}")
    for v in rev.resolved_violations:
        _out(f"resolved: {v}")
    _out(f"files: {res.export_dir}")
    return EXIT_OK


def cmd_plan_revise(args: argparse.Namespace) -> int:
    store = ProjectStore(resolve_project_dir(args.dir))
    out = Path(args.out) if args.out else _default_out(store, False)
    bases = getattr(args, "bases", None)
    try:
        res = PlanService(store).revise(
            args.option,
            args.text,
            args.actor,
            ops=_ops(args),
            kind=ChangeRequestKind(args.kind),
            version=args.version,
            seed=args.seed,
            out_dir=out,
            base_versions=bases,
            features=getattr(args, "features", None),
            feature_confirmation=getattr(args, "feature_confirmation", None),
        )
    except PlanWorkflowError as exc:
        return _refused(exc, args.dir)
    return _render_revision_outcome(res, args)


def cmd_plan_combine(args: argparse.Namespace) -> int:
    store = ProjectStore(resolve_project_dir(args.dir))
    out = Path(args.out) if args.out else _default_out(store, False)
    target = getattr(args, "target", None) or args.bases[0]
    try:
        res = PlanService(store).combine(
            target,
            args.bases,
            args.text,
            args.actor,
            ops=_ops(args),
            features=args.features,
            feature_confirmation=args.feature_confirmation,
            seed=args.seed,
            out_dir=out,
        )
    except PlanWorkflowError as exc:
        return _refused(exc, args.dir)
    return _render_revision_outcome(res, args)


def cmd_plan_list(args: argparse.Namespace) -> int:
    svc = PlanService(ProjectStore(resolve_project_dir(args.dir)))
    rows = []
    for plan, ref, rep in svc.stored():
        rows.append(
            {
                "option_id": plan.option_id,
                "version": ref.version,
                "strategy": plan.strategy,
                "label": plan.label,
                "levels": len(plan.model.levels),
                "hard_violations": len(rep.hard_violations) if rep else None,
                "soft_violations": len(rep.violations) - len(rep.hard_violations) if rep else None,
            }
        )
    if args.json:
        _out(json.dumps(rows, indent=2, ensure_ascii=False))
        return EXIT_OK
    for r in rows:
        _out(
            f"{r['option_id']} v{r['version']} [{r['strategy']}] {r['label']}: "
            f"{r['hard_violations']} hard / {r['soft_violations']} soft"
        )
    return EXIT_OK


def cmd_plan_compare(args: argparse.Namespace) -> int:
    svc = PlanService(ProjectStore(resolve_project_dir(args.dir)))
    _out(svc.compare(Path(args.out) if args.out else None))
    return EXIT_OK


def cmd_plan_export(args: argparse.Namespace) -> int:
    from house_ai.domain.plan import PlanVersion
    from house_ai.domain.provenance import ArtifactKind

    store = ProjectStore(resolve_project_dir(args.dir))
    svc = PlanService(store)
    refs = store.refs(ArtifactKind.PLAN, args.option)
    ref = (
        next((r for r in refs if r.version == args.version), None)
        if args.version
        else (refs[-1] if refs else None)
    )
    if ref is None:
        _out(f"no plan {args.option}")
        return EXIT_FAIL
    plan = store.get(ref, PlanVersion)
    inp = svc.inputs_for_plan(plan)
    folder = svc.export(plan, ref, svc._report_for(ref), inp, Path(args.out))
    _out(f"wrote {folder}")
    return EXIT_OK


def cmd_plan_export_bundle(args: argparse.Namespace) -> int:
    from house_ai.orchestration.reviewer_bundle import export_reviewer_bundle

    store = ProjectStore(resolve_project_dir(args.dir))
    plan_options_dir = existing_plan_options_dir(store, args.plan_options_dir)
    bundle_file = export_reviewer_bundle(
        store,
        Path(args.out),
        render=human.renderer(store.project_id),
        plan_options_dir=plan_options_dir,
        exploratory=args.exploratory,
    )
    _out(f"wrote reviewer bundle to {bundle_file}")
    return EXIT_OK


def cmd_plan_revise_from_file(args: argparse.Namespace) -> int:
    from house_ai.domain.revision_ops import RevisionOpsFile

    store = ProjectStore(resolve_project_dir(args.dir))
    out = Path(args.out) if args.out else _default_out(store, False)
    ops_path = Path(args.file)
    if not ops_path.exists():
        _out(f"file not found: {args.file}")
        return EXIT_FAIL
    try:
        data = json.loads(ops_path.read_text(encoding="utf-8"))
        ops_file = RevisionOpsFile.model_validate(data)
    except Exception as exc:
        _out(f"invalid revision ops file: {exc}")
        return EXIT_FAIL

    option = getattr(args, "option", None) or ops_file.option
    ops = ops_file.to_cli_ops()
    try:
        res = PlanService(store).revise(
            option,
            ops_file.verbatim_request,
            args.actor,
            ops=ops,
            version=ops_file.plan_version,
            out_dir=out,
        )
    except PlanWorkflowError as exc:
        return _refused(exc, args.dir)
    return _render_revision_outcome(res, args)


def cmd_plan_ground(args: argparse.Namespace) -> int:
    from house_ai.storage.hashing import load_document
    from house_ai.validation.grounding import (
        collect_canonical_ids,
        extract_entity_ids_from_text,
        validate_cited_ids,
    )

    valid = collect_canonical_ids(load_document(Path(args.plan)))
    if args.program:
        valid |= collect_canonical_ids(load_document(Path(args.program)))
    text = sys.stdin.read() if args.critique == "-" else Path(args.critique).read_text("utf-8")
    cited = extract_entity_ids_from_text(text)
    errors = validate_cited_ids(cited, valid)
    for err in errors:
        _out(f"UNKNOWN {err}")
    _out(f"{len(cited)} cited ID(s), {len(errors)} unknown")
    return EXIT_FAIL if errors else EXIT_OK


def cmd_plan_review(args: argparse.Namespace) -> int:
    svc = PlanService(ProjectStore(resolve_project_dir(args.dir)))
    try:
        ref, gate = svc.request_review(args.option, args.actor, args.version)
    except PlanWorkflowError as exc:
        return _refused(exc, args.dir)
    for r in gate.open_reasons:
        _out(f"OPEN {r}")
    for r in gate.attention:
        _out(f"ATTENTION {r}")
    _out(f"plan review requested for {ref.id} v{ref.version}")
    if gate.next_action is not None:
        _out(human.next_line(gate.next_action, args.dir))
    return EXIT_OK


def cmd_plan_sections(args: argparse.Namespace) -> int:
    from house_ai.domain.hillside import HillsideSettings, SectionLine
    from house_ai.domain.plan import PlanVersion
    from house_ai.domain.site import Site
    from house_ai.render2d.hillside_export import export_hillside_views

    try:
        plan = PlanVersion.model_validate(load_document(Path(args.plan)))
        site = Site.model_validate(load_document(Path(args.site))) if args.site else None
        lines = (
            [SectionLine.model_validate(r) for r in load_document(Path(args.lines))]
            if args.lines
            else None
        )
        settings = (
            HillsideSettings.model_validate(load_document(Path(args.settings)))
            if args.settings
            else None
        )
        export_hillside_views(plan.model, site, Path(args.out), lines, settings)
    except (ValueError, OSError) as exc:
        _out(f"refused: {exc}")
        return EXIT_USAGE
    _out(f"wrote hillside sections, elevations and risks to {args.out}")
    return EXIT_OK


def register(sub, actor_arg: Callable[[argparse.ArgumentParser], None]) -> None:
    pl = sub.add_parser("plan", help="floor-plan options (Milestone D)")
    pl = pl.add_subparsers(dest="sub", required=True)
    s = pl.add_parser("strategies", help="the strategies the generator knows for plan options")
    s.set_defaults(func=cmd_plan_strategies)

    s = pl.add_parser("sections", help="derive true cuts and hillside views from a plan export")
    s.add_argument("plan", help="exported canonical plan.json")
    s.add_argument("--site", help="site YAML/JSON; omitted terrain remains unknown")
    s.add_argument("--lines", help="JSON list of SectionLine objects; default: standard cuts")
    s.add_argument("--settings", help="HillsideSettings YAML/JSON, early-design review triggers")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_plan_sections)

    s = pl.add_parser("generate", help="generate, evaluate and store plan options")
    s.add_argument("dir")
    s.add_argument(
        "--strategy",
        action="append",
        choices=STRATEGY_EXTENDED_ORDER,
        help="repeat to choose strategies (default: all)",
    )
    s.add_argument("--seed", type=int, default=0)
    from house_ai.generation.terrain_levels import SECTIONAL_STRATEGIES

    s.add_argument(
        "--sectional-strategy",
        choices=SECTIONAL_STRATEGIES,
        help="sectional intent solved jointly with bar placement and elevations",
    )
    s.add_argument(
        "--time", type=float, default=4.0, help="CP-SAT deterministic time budget per solve"
    )
    s.add_argument("--out", help="export folder (default: <project>/design/plan-options)")
    s.add_argument(
        "--exploratory",
        action="store_true",
        help="preview on unapproved site/program; stores nothing",
    )
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_plan_generate)

    s = pl.add_parser("propose", help="submit a topology proposal and generate plans from it")
    s.add_argument("dir", help="project directory or name")
    s.add_argument("proposal", help="path to concept_proposal YAML/JSON file")
    s.add_argument("--out", help="export folder (default: <project>/design/plan-options)")
    s.add_argument(
        "--exploratory",
        action="store_true",
        help="preview on unapproved site/program; stores nothing",
    )
    s.add_argument("--seed", type=int, default=0)
    s.add_argument(
        "--time", type=float, default=4.0, help="CP-SAT deterministic time budget per solve"
    )
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_plan_propose)

    s = pl.add_parser(
        "revise", help="the next plan version of a plan option, from the owner's request"
    )
    s.add_argument("dir")
    s.add_argument("option")
    s.add_argument("text", help="the owner's request, verbatim")
    s.add_argument(
        "--kind",
        default="modify",
        choices=["modify", "restart_from_program", "combine"],
    )
    s.add_argument("--version", type=int, help="base version (default: latest)")
    s.add_argument(
        "--base",
        dest="bases",
        action="append",
        default=[],
        help="additional base versions for combine revisions",
    )
    s.add_argument("--area", action="append", default=[], metavar="SPACE=M2")
    s.add_argument(
        "--level", action="append", default=[], metavar="SPACE=entry|not_entry|upper|lower"
    )
    s.add_argument("--separate", action="append", default=[], metavar="SPACE,SPACE")
    s.add_argument("--adjacent", action="append", default=[], metavar="SPACE,SPACE")
    s.add_argument("--near", action="append", default=[], metavar="SPACE,SPACE")
    s.add_argument("--connect", action="append", default=[], metavar="SPACE,SPACE")
    s.add_argument(
        "--stair",
        choices=["entry", "perimeter", "central", "rear"],
        help="stair-core placement position override",
    )
    s.add_argument("--outdoor", action="append", default=[], metavar="SPACE,KIND")
    s.add_argument("--proposal", metavar="PATH", help="concept_proposal YAML/JSON file")
    s.add_argument(
        "--rethink",
        action="append",
        default=[],
        metavar="SPACE|ZONE|all",
        help="let these spaces move freely; the rest stays close to the parent",
    )
    s.add_argument("--strategy", choices=STRATEGY_EXTENDED_ORDER)
    s.add_argument("--seed", type=int)
    s.add_argument("--out")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_plan_revise)

    s = pl.add_parser(
        "combine",
        help="combine compatible features from several plan options (S7-22)",
    )
    s.add_argument("dir")
    s.add_argument("text", help="the owner's request describing what features to combine, verbatim")
    s.add_argument(
        "--base",
        dest="bases",
        action="append",
        required=True,
        help="plan option to combine (repeatable, at least 2)",
    )
    s.add_argument(
        "--feature",
        dest="features",
        action="append",
        required=True,
        metavar="SOURCE:SPACE=area,level,connections",
    )
    s.add_argument(
        "--feature-confirmation",
        required=True,
        help="owner's exact words confirming the explicit source-feature mapping",
    )
    s.add_argument("--target", help="target plan option name (default: the first one)")
    s.add_argument("--strategy", choices=STRATEGY_EXTENDED_ORDER)
    s.add_argument("--area", action="append", default=[], metavar="SPACE=M2")
    s.add_argument(
        "--level", action="append", default=[], metavar="SPACE=entry|not_entry|upper|lower"
    )
    s.add_argument("--separate", action="append", default=[], metavar="SPACE,SPACE")
    s.add_argument("--adjacent", action="append", default=[], metavar="SPACE,SPACE")
    s.add_argument("--near", action="append", default=[], metavar="SPACE,SPACE")
    s.add_argument("--connect", action="append", default=[], metavar="SPACE,SPACE")
    s.add_argument(
        "--stair",
        choices=["entry", "perimeter", "central", "rear"],
        help="stair-core placement position override",
    )
    s.add_argument("--outdoor", action="append", default=[], metavar="SPACE,KIND")
    s.add_argument("--proposal", metavar="PATH", help="concept_proposal YAML/JSON file")
    s.add_argument("--seed", type=int)
    s.add_argument("--out")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_plan_combine)

    s = pl.add_parser("list", help="stored plan options, latest plan versions")
    s.add_argument("dir")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_plan_list)

    s = pl.add_parser("compare", help="side-by-side metrics of the stored plan options")
    s.add_argument("dir")
    s.add_argument("--out")
    s.set_defaults(func=cmd_plan_compare)

    s = pl.add_parser("export", help="write plan.json/svg, metrics, violations, explanation")
    s.add_argument("dir")
    s.add_argument("option")
    s.add_argument("--version", type=int)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_plan_export)

    s = pl.add_parser(
        "ground", help="check that every `id` a critique cites exists in the plan (and program)"
    )
    s.add_argument("plan", help="plan.json from `plan export` or `plan generate --exploratory`")
    s.add_argument("critique", help="critique Markdown file, or - for stdin")
    s.add_argument("--program", help="space_program.yaml/json, to also accept unplaced items")
    s.set_defaults(func=cmd_plan_ground)

    s = pl.add_parser("review", help="ask the owner to review a plan version at the plan gate")
    s.add_argument("dir")
    s.add_argument("option")
    s.add_argument("--version", type=int)
    actor_arg(s)
    s.set_defaults(func=cmd_plan_review)

    s = pl.add_parser(
        "export-bundle", help="export a read-only reviewer bundle of the plan options"
    )
    s.add_argument("dir", help="project directory or name")
    s.add_argument("--out", required=True, help="output directory for bundle.json")
    add_plan_options_dir_argument(s)
    s.add_argument(
        "--exploratory",
        action="store_true",
        help="include exploratory plan options",
    )
    s.set_defaults(func=cmd_plan_export_bundle)

    s = pl.add_parser("revise-from-file", help="replay revision operations from an exported file")
    s.add_argument("dir", help="project directory or name")
    s.add_argument("file", help="path to revision ops JSON file")
    s.add_argument("--option", help="override target plan option")
    s.add_argument("--out", help="export folder for the new plan version")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_plan_revise_from_file)
