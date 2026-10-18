"""``house-ai plan ...``: concept generation, evaluation, revision and review (Milestone D).

Agents drive these commands for the homeowner. The plan gate is still
approved only by a human with ``house-ai workflow approve <dir> plan``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path

from house_ai.domain.plan import ChangeRequestKind
from house_ai.generation.massing import STRATEGY_LABELS, STRATEGY_ORDER
from house_ai.orchestration.plans import PlanService, PlanWorkflowError
from house_ai.storage import ProjectStore
from house_ai.storage.projects import resolve_project_dir

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


def _out(text: str = "") -> None:
    print(text)


def _default_out(store: ProjectStore, exploratory: bool) -> Path:
    return store.root / "design" / ("concepts-exploratory" if exploratory else "concepts")


def cmd_plan_strategies(args: argparse.Namespace) -> int:
    for name in STRATEGY_ORDER:
        _out(f"{name:12} {STRATEGY_LABELS[name]}")
    return EXIT_OK


def cmd_plan_generate(args: argparse.Namespace) -> int:
    store = ProjectStore(resolve_project_dir(args.dir))
    out = Path(args.out) if args.out else _default_out(store, args.exploratory)
    try:
        res = PlanService(store).generate(
            args.actor,
            strategies=args.strategy or None,
            seed=args.seed,
            out_dir=out,
            exploratory=args.exploratory,
            deterministic_time=args.time,
        )
    except PlanWorkflowError as exc:
        _out(f"refused: {exc}")
        return EXIT_FAIL
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
        _out(
            json.dumps(
                {
                    "exploratory": res.exploratory,
                    "options": rows,
                    "comparison": str(res.comparison) if res.comparison else None,
                    "constraints_ref": res.constraints_ref.model_dump(mode="json")
                    if res.constraints_ref
                    else None,
                    "notes": res.notes,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
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
        _out(
            "state CONCEPT_REVIEW; show the owner the concepts, then `house-ai plan review "
            f"{args.dir} <option>` and the owner approves with `house-ai workflow approve "
            f"{args.dir} plan --id <option> --approver <name>`"
        )
    return EXIT_OK


def _ops(args: argparse.Namespace) -> list[str]:
    ops = [f"area:{a}" for a in args.area]
    ops += [f"level:{a}" for a in args.level]
    ops += [f"separate:{a}" for a in args.separate]
    ops += [f"adjacent:{a}" for a in args.adjacent]
    ops += [f"near:{a}" for a in args.near]
    ops += [f"rethink:{a}" for a in args.rethink]
    if args.strategy:
        ops.append(f"strategy:{args.strategy}")
    return ops


def cmd_plan_revise(args: argparse.Namespace) -> int:
    store = ProjectStore(resolve_project_dir(args.dir))
    out = Path(args.out) if args.out else _default_out(store, False)
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
        )
    except PlanWorkflowError as exc:
        _out(f"refused: {exc}")
        return EXIT_FAIL
    rev, ref = res.revision, res.option.plan_ref
    assert ref is not None and res.option.report is not None
    if args.json:
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
    _out(f"stored {ref.id} v{ref.version} (parent v{rev.from_version.version})")
    _out(f"rooms changed: {', '.join(rev.rooms_changed) or 'none'}")
    for c in rev.area_changes:
        _out(f"  {c.space_id}: {c.before_m2} -> {c.after_m2} m²")
    for v in rev.new_violations:
        _out(f"new violation: {v}")
    for v in rev.resolved_violations:
        _out(f"resolved: {v}")
    _out(f"files: {res.export_dir}")
    return EXIT_OK


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
    concepts_dir = (
        Path(args.concepts_dir)
        if args.concepts_dir
        else (
            store.root / "design" / "concepts"
            if (store.root / "design" / "concepts").exists()
            else None
        )
    )
    bundle_file = export_reviewer_bundle(
        store,
        Path(args.out),
        concepts_dir=concepts_dir,
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
        _out(f"refused: {exc}")
        return EXIT_FAIL
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
    _out(f"stored {ref.id} v{ref.version} (parent v{rev.from_version.version})")
    _out(f"rooms changed: {', '.join(rev.rooms_changed) or 'none'}")
    for c in rev.area_changes:
        _out(f"  {c.space_id}: {c.before_m2} -> {c.after_m2} m²")
    for v in rev.new_violations:
        _out(f"new violation: {v}")
    for v in rev.resolved_violations:
        _out(f"resolved: {v}")
    _out(f"files: {res.export_dir}")
    return EXIT_OK


def cmd_plan_ground(args: argparse.Namespace) -> int:
    from house_ai.evaluation.grounding import (
        collect_canonical_ids,
        extract_entity_ids_from_text,
        validate_critique_grounding,
    )
    from house_ai.storage.hashing import load_document

    valid = collect_canonical_ids(load_document(Path(args.plan)))
    if args.program:
        valid |= collect_canonical_ids(load_document(Path(args.program)))
    text = sys.stdin.read() if args.critique == "-" else Path(args.critique).read_text("utf-8")
    cited = extract_entity_ids_from_text(text)
    errors = validate_critique_grounding(cited, valid)
    for err in errors:
        _out(f"UNKNOWN {err}")
    _out(f"{len(cited)} cited ID(s), {len(errors)} unknown")
    return EXIT_FAIL if errors else EXIT_OK


def cmd_plan_review(args: argparse.Namespace) -> int:
    svc = PlanService(ProjectStore(resolve_project_dir(args.dir)))
    try:
        ref, ev = svc.request_review(args.option, args.actor, args.version)
    except PlanWorkflowError as exc:
        _out(f"refused: {exc}")
        return EXIT_FAIL
    for r in ev.payload["open_reasons"]:
        _out(f"OPEN {r}")
    _out(f"plan review requested for {ref.id} v{ref.version}")
    if not ev.payload["open_reasons"]:
        _out(
            f"next: the owner runs `house-ai workflow approve {args.dir} plan --id {ref.id} "
            f"--version {ref.version} --approver <name>` in their own terminal"
        )
    return EXIT_OK


def register(sub, actor_arg: Callable[[argparse.ArgumentParser], None]) -> None:
    pl = sub.add_parser("plan", help="floor-plan concepts (Milestone D)")
    pl = pl.add_subparsers(dest="sub", required=True)
    s = pl.add_parser("strategies", help="the concept strategies the generator knows")
    s.set_defaults(func=cmd_plan_strategies)

    s = pl.add_parser("generate", help="generate, evaluate and store concepts")
    s.add_argument("dir")
    s.add_argument(
        "--strategy",
        action="append",
        choices=STRATEGY_ORDER,
        help="repeat to choose strategies (default: all)",
    )
    s.add_argument("--seed", type=int, default=0)
    s.add_argument(
        "--time", type=float, default=4.0, help="CP-SAT deterministic time budget per solve"
    )
    s.add_argument("--out", help="export folder (default: <project>/design/concepts)")
    s.add_argument(
        "--exploratory",
        action="store_true",
        help="preview on unapproved site/program; stores nothing",
    )
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_plan_generate)

    s = pl.add_parser("revise", help="a new version of a concept from the owner's request")
    s.add_argument("dir")
    s.add_argument("option")
    s.add_argument("text", help="the owner's request, verbatim")
    s.add_argument("--kind", default="modify", choices=["modify", "restart_from_program"])
    s.add_argument("--version", type=int, help="base version (default: latest)")
    s.add_argument("--area", action="append", default=[], metavar="ROOM=M2")
    s.add_argument(
        "--level", action="append", default=[], metavar="ROOM=entry|not_entry|upper|lower"
    )
    s.add_argument("--separate", action="append", default=[], metavar="ROOM,ROOM")
    s.add_argument("--adjacent", action="append", default=[], metavar="ROOM,ROOM")
    s.add_argument("--near", action="append", default=[], metavar="ROOM,ROOM")
    s.add_argument(
        "--rethink",
        action="append",
        default=[],
        metavar="ROOM|ZONE|all",
        help="let these rooms move freely; the rest stays close to the parent",
    )
    s.add_argument("--strategy", choices=STRATEGY_ORDER)
    s.add_argument("--seed", type=int)
    s.add_argument("--out")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_plan_revise)

    s = pl.add_parser("list", help="stored concepts, latest versions")
    s.add_argument("dir")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_plan_list)

    s = pl.add_parser("compare", help="side-by-side metrics of the stored concepts")
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

    s = pl.add_parser("review", help="ask the owner to review a concept at the plan gate")
    s.add_argument("dir")
    s.add_argument("option")
    s.add_argument("--version", type=int)
    actor_arg(s)
    s.set_defaults(func=cmd_plan_review)

    s = pl.add_parser("export-bundle", help="export read-only concept reviewer bundle")
    s.add_argument("dir", help="project directory or name")
    s.add_argument("--out", required=True, help="output directory for bundle.json")
    s.add_argument("--concepts-dir", help="optional directory with exploratory concepts")
    s.add_argument(
        "--exploratory",
        action="store_true",
        help="include exploratory concepts",
    )
    s.set_defaults(func=cmd_plan_export_bundle)

    s = pl.add_parser("revise-from-file", help="replay revision operations from an exported file")
    s.add_argument("dir", help="project directory or name")
    s.add_argument("file", help="path to revision ops JSON file")
    s.add_argument("--option", help="override target plan option")
    s.add_argument("--out", help="export folder for the revised concept")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_plan_revise_from_file)
