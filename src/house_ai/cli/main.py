"""house-ai command line.

Every command is a thin wrapper over the library. State-changing commands
need ``--actor kind:id`` so the event log records who did what.

``workflow approve`` is deliberately interactive: it requires a terminal and
a typed confirmation, so an agent driving a non-interactive shell cannot
silently cross a gate. This prevents accidental gate-skipping; it is not a
security boundary against a determined local process.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from house_ai.domain.integrity import FindingSeverity, check_model
from house_ai.domain.model import HouseModel
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceProgram
from house_ai.domain.provenance import (
    Actor,
    ActorKind,
    ArtifactKind,
    ArtifactRef,
    DataClassification,
)
from house_ai.domain.registry import SCHEMAS, export_schemas, stale_schemas
from house_ai.domain.site import Site
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.workflow import (
    GATES,
    Workflow,
    WorkflowError,
)
from house_ai.storage import ProjectStore, StoreError
from house_ai.storage.hashing import load_document
from house_ai.storage.importer import import_folder

REPO_ROOT = Path(__file__).resolve().parents[3]
EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


def _out(text: str = "") -> None:
    print(text)


def _err(text: str) -> None:
    print(text, file=sys.stderr)


def _actor(text: str) -> Actor:
    try:
        return Actor.parse(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _ref(
    store: ProjectStore, kind: ArtifactKind, artifact_id: str, version: int | None
) -> ArtifactRef:
    refs = store.refs(kind, artifact_id)
    if not refs:
        raise StoreError(f"no {kind.value} artifact with id {artifact_id!r}")
    if version is None:
        return refs[-1]
    for r in refs:
        if r.version == version:
            return r
    raise StoreError(f"{kind.value}/{artifact_id} has no version {version}")


# --------------------------------------------------------------------- schemas


def cmd_schemas_export(args: argparse.Namespace) -> int:
    for path in export_schemas(Path(args.out)):
        _out(f"wrote {path}")
    return EXIT_OK


def cmd_schemas_check(args: argparse.Namespace) -> int:
    stale = stale_schemas(Path(args.out))
    if stale:
        _err("schemas out of date: " + ", ".join(stale))
        _err("run: house-ai schemas export")
        return EXIT_FAIL
    _out(f"{len(SCHEMAS)} schemas up to date")
    return EXIT_OK


def cmd_validate(args: argparse.Namespace) -> int:
    model_cls = SCHEMAS[args.kind]
    try:
        model = model_cls.model_validate(load_document(Path(args.file)))
    except ValidationError as exc:
        _err(f"INVALID {args.file}\n{exc}")
        return EXIT_FAIL
    _out(f"valid {args.kind}: {args.file}")
    house = model.model if isinstance(model, PlanVersion) else model
    if isinstance(house, HouseModel):
        site = Site.model_validate(load_document(Path(args.site))) if args.site else None
        return _report_findings(check_model(house, site))
    return EXIT_OK


def _report_findings(findings: list) -> int:
    for f in findings:
        _out(f"  {f.severity.value.upper():7} {f.code}: {f.message}")
    n_err = sum(f.severity is FindingSeverity.ERROR for f in findings)
    _out(f"integrity: {n_err} error(s), {len(findings) - n_err} warning(s)")
    return EXIT_FAIL if n_err else EXIT_OK


# --------------------------------------------------------------------- project


def cmd_project_init(args: argparse.Namespace) -> int:
    store = ProjectStore.init(
        Path(args.dir),
        project_id=args.id,
        name=args.name,
        classification=DataClassification(args.classification),
        actor=args.actor,
    )
    _out(f"created project {args.id} at {store.root} (state NEW_PROJECT)")
    return EXIT_OK


def _status_dict(store: ProjectStore) -> dict:
    wf = Workflow(store)
    status = wf.status()
    gate = wf.gate_available()
    latest: dict[str, list[dict]] = {}
    for kind in ArtifactKind:
        for ref in store.latest_of_kind(kind):
            latest.setdefault(kind.value, []).append(ref.model_dump(mode="json"))
    return {
        "project": store.manifest().model_dump(mode="json"),
        "state": status.state.value,
        "allowed_transitions": [s.value for s in wf.allowed_transitions()],
        "gate_available": gate.value if gate else None,
        "approvals": {g.value: a.model_dump(mode="json") for g, a in status.approvals.items()},
        "superseded_approvals": [a.id for a in status.superseded],
        "pending_approval_requests": {
            g.value: r.model_dump(mode="json") for g, r in status.pending_requests.items()
        },
        "latest_artifacts": latest,
    }


def cmd_project_status(args: argparse.Namespace) -> int:
    store = ProjectStore(Path(args.dir))
    info = _status_dict(store)
    if args.json:
        _out(json.dumps(info, indent=2, sort_keys=True))
        return EXIT_OK
    _out(f"project   {info['project']['id']} ({info['project']['name']})")
    _out(f"state     {info['state']}")
    _out(f"next      {', '.join(info['allowed_transitions']) or '-'}")
    if info["gate_available"]:
        _out(f"gate      {info['gate_available']} can be approved by a human from this state")
    for gate, appr in info["approvals"].items():
        art = appr["artifact"]
        _out(
            f"approved  {gate}: {art['kind']}/{art['id']} v{art['version']} "
            f"by {appr['approved_by']['id']}"
        )
    for kind, refs in sorted(info["latest_artifacts"].items()):
        for r in refs:
            _out(f"artifact  {kind}/{r['id']} v{r['version']} {r['sha256'][:12]}")
    return EXIT_OK


def cmd_project_verify(args: argparse.Namespace) -> int:
    store = ProjectStore(Path(args.dir))
    problems = store.verify()
    try:
        Workflow(store).status()
    except WorkflowError as exc:
        problems.append(f"workflow replay failed: {exc}")
    for p in problems:
        _err(f"PROBLEM {p}")
    if problems:
        return EXIT_FAIL
    _out(f"intact: {len(store.events())} events, {len(store.refs())} artifact versions")
    return EXIT_OK


# ------------------------------------------------------------ sources/artifacts


def cmd_source_add(args: argparse.Namespace) -> int:
    store = ProjectStore(Path(args.dir))
    doc = store.add_source(
        Path(args.file), args.actor, classification=DataClassification(args.classification)
    )
    _out(f"source {doc.id}: {doc.stored_path} sha256 {doc.sha256}")
    return EXIT_OK


def cmd_artifact_put(args: argparse.Namespace) -> int:
    store = ProjectStore(Path(args.dir))
    kind = ArtifactKind(args.kind)
    data = load_document(Path(args.file))
    artifact_id = args.id or data.get("option_id") or data.get("id")
    if not artifact_id:
        _err("the file has no id; pass --id")
        return EXIT_USAGE
    try:
        ref = store.put(kind, artifact_id, data, args.actor, reason=args.reason)
    except ValidationError as exc:
        _err(f"INVALID {args.file}\n{exc}")
        return EXIT_FAIL
    _out(f"stored {kind.value}/{ref.id} v{ref.version} sha256 {ref.sha256}")
    return EXIT_OK


def cmd_artifact_list(args: argparse.Namespace) -> int:
    store = ProjectStore(Path(args.dir))
    kind = ArtifactKind(args.kind) if args.kind else None
    for ref in store.refs(kind):
        _out(f"{ref.kind.value}/{ref.id} v{ref.version} {ref.sha256}")
    return EXIT_OK


def cmd_artifact_check(args: argparse.Namespace) -> int:
    store = ProjectStore(Path(args.dir))
    plan = store.get(_ref(store, ArtifactKind.PLAN, args.id, args.version), PlanVersion)
    site = store.get(plan.model.site_ref, Site) if plan.model.site_ref else None
    program = store.get(plan.model.program_ref, SpaceProgram) if plan.model.program_ref else None
    if site is None:
        _out("plan has no site_ref; site containment not checked")
    return _report_findings(check_model(plan.model, site, program))


def cmd_example_load(args: argparse.Namespace) -> int:
    folder = Path(args.source) if args.source else REPO_ROOT / "examples" / "projects" / args.name
    if not folder.is_dir():
        _err(f"no example folder at {folder}")
        return EXIT_USAGE
    store = ProjectStore.init(
        Path(args.dir),
        project_id=args.project_id,
        name=f"example: {args.name}",
        classification=DataClassification.SYNTHETIC,
        actor=args.actor,
    )
    refs = import_folder(store, folder, args.actor)
    for ref in refs:
        _out(f"stored {ref.kind.value}/{ref.id} v{ref.version}")
    wf = Workflow(store)
    wf.transition(WorkflowState.SITE_INGESTION, args.actor, "example site loaded")
    site_ref = next(r for r in refs if r.kind is ArtifactKind.SITE)
    blockers = wf.assess_site(site_ref, args.actor)
    for b in blockers:
        _out(f"SITE BLOCKER {b}")
    _out(f"state {wf.state.value}")
    if not blockers:
        _out(f"next: a human runs `house-ai workflow approve {args.dir} site --id {site_ref.id}`")
    return EXIT_OK


# -------------------------------------------------------------------- workflow


def cmd_transition(args: argparse.Namespace) -> int:
    wf = Workflow(ProjectStore(Path(args.dir)))
    ev = wf.transition(WorkflowState(args.state), args.actor, args.reason)
    _out(f"{ev.from_state.value} -> {ev.to_state.value}")  # type: ignore[union-attr]
    return EXIT_OK


def cmd_assess_site(args: argparse.Namespace) -> int:
    store = ProjectStore(Path(args.dir))
    wf = Workflow(store)
    blockers = wf.assess_site(_ref(store, ArtifactKind.SITE, args.id, args.version), args.actor)
    for b in blockers:
        _out(f"BLOCKER {b}")
    _out(f"state {wf.state.value}")
    return EXIT_OK


def cmd_request_approval(args: argparse.Namespace) -> int:
    store = ProjectStore(Path(args.dir))
    gate = Gate(args.gate)
    ref = _ref(store, GATES[gate].artifact_kind, args.id, args.version)
    ev = Workflow(store).request_approval(gate, ref, args.actor)
    for r in ev.payload["open_reasons"]:
        _out(f"OPEN {r}")
    _out(f"approval of {gate.value} requested for {ref.kind.value}/{ref.id} v{ref.version}")
    return EXIT_OK


def cmd_approve(args: argparse.Namespace) -> int:
    if not sys.stdin.isatty():
        _err(
            "approval needs an interactive terminal and a typed confirmation from a human. "
            "Agents must not approve gates; ask the human to run this command themselves."
        )
        return EXIT_USAGE
    store = ProjectStore(Path(args.dir))
    wf = Workflow(store)
    gate = Gate(args.gate)
    ref = _ref(store, GATES[gate].artifact_kind, args.id, args.version)
    reasons = wf.check_gate(gate, ref)
    if reasons:
        _err(f"the {gate.value} gate cannot be approved yet:")
        for r in reasons:
            _err(f"  - {r}")
        return EXIT_FAIL
    phrase = f"approve {gate.value} {ref.id} v{ref.version}"
    _out(f"You are approving {ref.kind.value}/{ref.id} v{ref.version} (sha256 {ref.sha256[:12]}).")
    _out("Approval is recorded permanently in the project event log.")
    typed = input(f'Type "{phrase}" to confirm: ').strip()
    if typed != phrase:
        _err("confirmation did not match; nothing approved")
        return EXIT_FAIL
    approver = Actor(kind=ActorKind.HUMAN, id=args.approver)
    statement = args.statement or (
        f"{args.approver} reviewed {ref.kind.value}/{ref.id} v{ref.version} and approves it."
    )
    approval = wf.approve(gate, ref, approver, statement, conditions=args.condition)
    _out(f"approved: {approval.id}; state {wf.state.value}")
    return EXIT_OK


def cmd_reopen(args: argparse.Namespace) -> int:
    wf = Workflow(ProjectStore(Path(args.dir)))
    ev = wf.reopen(Gate(args.gate), args.actor, args.reason)
    _out(f"reopened {args.gate}: {ev.from_state.value} -> {ev.to_state.value}")  # type: ignore[union-attr]
    return EXIT_OK


# ---------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="house-ai", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    default_schemas = str(REPO_ROOT / "schemas")

    def actor_arg(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--actor",
            type=_actor,
            required=True,
            help="who is acting, as kind:id (human:owner, agent:claude-code)",
        )

    sch = sub.add_parser("schemas", help="JSON Schema export and drift check").add_subparsers(
        dest="sub", required=True
    )
    s = sch.add_parser("export")
    s.add_argument("--out", default=default_schemas)
    s.set_defaults(func=cmd_schemas_export)
    s = sch.add_parser("check")
    s.add_argument("--out", default=default_schemas)
    s.set_defaults(func=cmd_schemas_check)

    s = sub.add_parser("validate", help="validate a JSON/YAML file against a schema")
    s.add_argument("kind", choices=sorted(SCHEMAS))
    s.add_argument("file")
    s.add_argument("--site", help="site file, to also check containment for plans")
    s.set_defaults(func=cmd_validate)

    proj = sub.add_parser("project").add_subparsers(dest="sub", required=True)
    s = proj.add_parser("init")
    s.add_argument("dir")
    s.add_argument("--id", required=True)
    s.add_argument("--name", required=True)
    s.add_argument(
        "--classification", default="private", choices=[c.value for c in DataClassification]
    )
    actor_arg(s)
    s.set_defaults(func=cmd_project_init)
    s = proj.add_parser("status")
    s.add_argument("dir")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_project_status)
    s = proj.add_parser("verify")
    s.add_argument("dir")
    s.set_defaults(func=cmd_project_verify)

    src = sub.add_parser("source").add_subparsers(dest="sub", required=True)
    s = src.add_parser("add", help="copy an original input into the project, immutable")
    s.add_argument("dir")
    s.add_argument("file")
    s.add_argument(
        "--classification", default="private", choices=[c.value for c in DataClassification]
    )
    actor_arg(s)
    s.set_defaults(func=cmd_source_add)

    art = sub.add_parser("artifact").add_subparsers(dest="sub", required=True)
    s = art.add_parser("put", help="validate and store a new artifact version")
    s.add_argument("dir")
    s.add_argument("kind", choices=[k.value for k in ArtifactKind])
    s.add_argument("file")
    s.add_argument("--id")
    s.add_argument("--reason")
    actor_arg(s)
    s.set_defaults(func=cmd_artifact_put)
    s = art.add_parser("list")
    s.add_argument("dir")
    s.add_argument("--kind", choices=[k.value for k in ArtifactKind])
    s.set_defaults(func=cmd_artifact_list)
    s = art.add_parser("check", help="run integrity checks on a stored plan")
    s.add_argument("dir")
    s.add_argument("id")
    s.add_argument("--version", type=int)
    s.set_defaults(func=cmd_artifact_check)

    ex = sub.add_parser("example").add_subparsers(dest="sub", required=True)
    s = ex.add_parser("load", help="create a project from a synthetic example")
    s.add_argument("dir")
    s.add_argument("--name", default="synthetic-bungalow")
    s.add_argument("--source", help="example folder (default: examples/projects/<name>)")
    s.add_argument("--project-id", default="synthetic-bungalow")
    actor_arg(s)
    s.set_defaults(func=cmd_example_load)

    wf = sub.add_parser("workflow").add_subparsers(dest="sub", required=True)
    s = wf.add_parser("transition")
    s.add_argument("dir")
    s.add_argument("state", choices=[st.value for st in WorkflowState])
    s.add_argument("--reason", required=True)
    actor_arg(s)
    s.set_defaults(func=cmd_transition)
    s = wf.add_parser("assess-site")
    s.add_argument("dir")
    s.add_argument("--id", required=True)
    s.add_argument("--version", type=int)
    actor_arg(s)
    s.set_defaults(func=cmd_assess_site)
    for name, func in (("request-approval", cmd_request_approval), ("approve", cmd_approve)):
        s = wf.add_parser(name)
        s.add_argument("dir")
        s.add_argument("gate", choices=[g.value for g in Gate])
        s.add_argument("--id", required=True)
        s.add_argument("--version", type=int)
        if name == "approve":
            s.add_argument("--approver", required=True, help="the human's name or id")
            s.add_argument("--statement")
            s.add_argument("--condition", action="append", default=[])
        else:
            actor_arg(s)
        s.set_defaults(func=func)
    s = wf.add_parser("reopen")
    s.add_argument("dir")
    s.add_argument("gate", choices=[g.value for g in Gate])
    s.add_argument("--reason", required=True)
    actor_arg(s)
    s.set_defaults(func=cmd_reopen)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (StoreError, WorkflowError, ValidationError, ValueError) as exc:
        _err(f"error: {exc}")
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
