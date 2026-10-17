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

from house_ai.cad.dwg_oda import DwgConversionError
from house_ai.cad.layers import load_layer_mapping
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
from house_ai.domain.site import CadImportProvenance, Site, site_verification_blockers
from house_ai.domain.units import LengthUnit
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.geospatial.crs import describe_epsg, utm_candidates
from house_ai.geospatial.validation import report_markdown, validate_site
from house_ai.interview.brief_builder import describe
from house_ai.interview.questions import SLOTS
from house_ai.orchestration.interview import InterviewService
from house_ai.orchestration.interview_llm import LlmAssist
from house_ai.orchestration.site_ingestion import SiteConfirmation, confirm_site, ingest_site
from house_ai.orchestration.statements import owner_statements, record_owner_statement
from house_ai.orchestration.survey_inspection import inspect_files, inspection_markdown
from house_ai.orchestration.workflow import (
    GATES,
    Workflow,
    WorkflowError,
)
from house_ai.program.report import program_markdown
from house_ai.providers.base import ModelProvider, ProviderError
from house_ai.render2d.review_html import render_review_html
from house_ai.render2d.site_svg import render_site_svg
from house_ai.render2d.terrain_svg import render_terrain_svg
from house_ai.storage import ProjectStore, StoreError
from house_ai.storage.hashing import load_document, pretty_json
from house_ai.storage.importer import import_folder
from house_ai.storage.projects import create_project, list_projects, resolve_project_dir

REPO_ROOT = Path(__file__).resolve().parents[3]
EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2


def _out(text: str = "") -> None:
    print(text)


def _err(text: str) -> None:
    print(text, file=sys.stderr)


def _dir(text: str) -> Path:
    """A project folder given as a path or as a name under projects/."""
    return resolve_project_dir(text)


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


def cmd_project_new(args: argparse.Namespace) -> int:
    store = create_project(args.name, title=args.title or args.name, actor=args.actor,
                           classification=DataClassification(args.classification))  # fmt: skip
    _out(f"created project {store.project_id} at {store.root} (state NEW_PROJECT)")
    _out(f"next: copy the survey into {store.root}/surveys/ and follow {store.root}/README.md")
    return EXIT_OK


def cmd_project_list(args: argparse.Namespace) -> int:
    roots = list_projects()
    for root in roots:
        store = ProjectStore(root)
        _out(f"{store.project_id:20} {Workflow(store).state.value:24} {root}")
    if not roots:
        _out("no projects under projects/; create one with `house-ai project new <name>`")
    return EXIT_OK


def _status_dict(store: ProjectStore) -> dict:
    wf = Workflow(store)
    status = wf.status()
    gate = wf.gate_available()
    latest: dict[str, list[dict]] = {}
    for kind in ArtifactKind:
        for ref in store.latest_of_kind(kind):
            latest.setdefault(kind.value, []).append(ref.model_dump(mode="json"))
    svc = InterviewService(store)
    site_ctx = svc.site()
    site_info = None
    if site_ctx is not None and site_ctx.site_ref is not None:
        site_info = {
            "site_ref": site_ctx.site_ref.model_dump(mode="json"),
            "verified": site_ctx.verified,
            "parcel_area_m2": site_ctx.parcel_area_m2,
            "relief_m": site_ctx.relief_m,
            "mean_slope_pct": site_ctx.mean_slope_pct,
            "frontage_m": site_ctx.frontage_m,
            "verification_blockers": svc.site_blockers(),
        }
    iv_exists = svc.exists()
    iv_state = svc.state() if iv_exists else None
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
        "site": site_info,
        "owner_statements_count": len(owner_statements(store)),
        "interview": {
            "exists": iv_exists,
            "status": svc.session().status.value if iv_exists else "not_started",
            "turn_count": len(svc.session().turns) if iv_exists else 0,
            "unconfirmed_slots": len(iv_state.unconfirmed()) if iv_state else 0,
        },
    }


def cmd_project_status(args: argparse.Namespace) -> int:
    store = ProjectStore(_dir(args.dir))
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
    if info["site"] is not None:
        s_info = info["site"]
        v_tag = "verified" if s_info["verified"] else "needs verification"
        _out(
            f"site      {v_tag}; area={s_info['parcel_area_m2']} m², "
            f"relief={s_info['relief_m']} m, slope={s_info['mean_slope_pct']}%, "
            f"frontage={s_info['frontage_m']} m, blockers={len(s_info['verification_blockers'])}"
        )
    for kind, refs in sorted(info["latest_artifacts"].items()):
        for r in refs:
            _out(f"artifact  {kind}/{r['id']} v{r['version']} {r['sha256'][:12]}")
    return EXIT_OK


def cmd_project_verify(args: argparse.Namespace) -> int:
    store = ProjectStore(_dir(args.dir))
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
    store = ProjectStore(_dir(args.dir))
    doc = store.add_source(
        Path(args.file), args.actor, classification=DataClassification(args.classification)
    )
    _out(f"source {doc.id}: {doc.stored_path} sha256 {doc.sha256}")
    return EXIT_OK


def cmd_artifact_put(args: argparse.Namespace) -> int:
    store = ProjectStore(_dir(args.dir))
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
    store = ProjectStore(_dir(args.dir))
    kind = ArtifactKind(args.kind) if args.kind else None
    for ref in store.refs(kind):
        _out(f"{ref.kind.value}/{ref.id} v{ref.version} {ref.sha256}")
    return EXIT_OK


def cmd_artifact_check(args: argparse.Namespace) -> int:
    store = ProjectStore(_dir(args.dir))
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
    wf = Workflow(ProjectStore(_dir(args.dir)))
    ev = wf.transition(WorkflowState(args.state), args.actor, args.reason)
    _out(f"{ev.from_state.value} -> {ev.to_state.value}")  # type: ignore[union-attr]
    return EXIT_OK


def cmd_assess_site(args: argparse.Namespace) -> int:
    store = ProjectStore(_dir(args.dir))
    wf = Workflow(store)
    blockers = wf.assess_site(_ref(store, ArtifactKind.SITE, args.id, args.version), args.actor)
    for b in blockers:
        _out(f"BLOCKER {b}")
    _out(f"state {wf.state.value}")
    return EXIT_OK


def cmd_request_approval(args: argparse.Namespace) -> int:
    store = ProjectStore(_dir(args.dir))
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
    store = ProjectStore(_dir(args.dir))
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
    wf = Workflow(ProjectStore(_dir(args.dir)))
    ev = wf.reopen(Gate(args.gate), args.actor, args.reason)
    _out(f"reopened {args.gate}: {ev.from_state.value} -> {ev.to_state.value}")  # type: ignore[union-attr]
    return EXIT_OK


# ------------------------------------------------------------------------ site


def cmd_site_inspect(args: argparse.Namespace) -> int:
    mapping = load_layer_mapping(Path(args.layers)) if args.layers else None
    report = inspect_files([Path(f) for f in args.files], mapping)
    text = inspection_markdown(report)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "inspection.md").write_text(text, encoding="utf-8")
        (out / "inspection.json").write_text(pretty_json(report), encoding="utf-8")
        _out(f"wrote {out / 'inspection.md'} and {out / 'inspection.json'}")
    elif args.json:
        _out(pretty_json(report))
    else:
        _out(text)
    return EXIT_OK if all(f.readable for f in report.files) else EXIT_FAIL


def cmd_site_ingest(args: argparse.Namespace) -> int:
    store = ProjectStore(_dir(args.dir))
    result = ingest_site(
        store, args.source, load_layer_mapping(Path(args.layers)), args.actor, site_id=args.site_id
    )
    for ref in (*result.cad_refs, result.site_ref):
        _out(f"stored {ref.kind.value}/{ref.id} v{ref.version} sha256 {ref.sha256}")
    for b in result.blockers:
        _out(f"BLOCKER {b}")
    if result.blockers:
        _out(
            "next: house-ai workflow assess-site "
            f"{args.dir} --id {args.site_id} --actor <you>   # records SITE_NEEDS_VERIFICATION"
        )
    return EXIT_OK


def cmd_site_confirm(args: argparse.Namespace) -> int:
    if not sys.stdin.isatty():
        _err(
            "site confirmation needs an interactive terminal and a typed confirmation from a "
            "human. Agents must not confirm units, CRS, datum or boundary; ask the human to run "
            "this command themselves."
        )
        return EXIT_USAGE
    conf = SiteConfirmation(
        units=LengthUnit(args.units) if args.units else None,
        elevation_units=LengthUnit(args.elevation_units) if args.elevation_units else None,
        epsg=args.epsg,
        local_only=args.local_only,
        vertical_datum=args.vertical_datum,
        vertical_epsg=args.vertical_epsg,
        vertical_local=args.vertical_local,
        boundary_verified=args.boundary_verified,
        origin=tuple(args.origin) if args.origin else None,
        rotation_deg=args.rotation,
        accept_issues=args.accept_issue,
    )
    if not conf.summary():
        _err("nothing to confirm; pass at least one of the confirmation options")
        return EXIT_USAGE
    store = ProjectStore(_dir(args.dir))
    _out(f"You ({args.confirmer}) are confirming for site {args.id}:")
    for item in conf.summary():
        _out(f"  - {item}")
    _out("This is recorded permanently in the project event log under your name.")
    phrase = f"confirm site {args.id}"
    typed = input(f'Type "{phrase}" to confirm: ').strip()
    if typed != phrase:
        _err("confirmation did not match; nothing confirmed")
        return EXIT_FAIL
    ref = confirm_site(store, args.id, Actor(kind=ActorKind.HUMAN, id=args.confirmer), conf)
    site = store.get(ref, Site)
    _out(f"stored site/{ref.id} v{ref.version} sha256 {ref.sha256}")
    lonlat = validate_site(site).coordinates.origin_lon_lat
    if lonlat:
        _out(
            f"the local origin is at lon {lonlat[0]:.6f}, lat {lonlat[1]:.6f}: check that this "
            "is your property (a wrong UTM zone moves it by 6° of longitude)"
        )
    for b in site_verification_blockers(site):
        _out(f"BLOCKER {b}")
    return EXIT_OK


def cmd_site_report(args: argparse.Namespace) -> int:
    store = ProjectStore(_dir(args.dir))
    ref = _ref(store, ArtifactKind.SITE, args.id, args.version)
    site = store.get(ref, Site)
    report = validate_site(site, ref)
    statements = owner_statements(store)
    out = Path(args.out) if args.out else store.root / "reviews" / f"{ref.id}-v{ref.version}"
    out.mkdir(parents=True, exist_ok=True)
    site_svg, terrain_svg = render_site_svg(site, report), render_terrain_svg(site, report)
    cad_inputs = [r for r in site.provenance.inputs if r.kind is ArtifactKind.CAD_IMPORT]
    cads = [store.get(r, CadImportProvenance) for r in cad_inputs]
    files = {
        "site.json": pretty_json(site),
        "site-report.json": pretty_json(report),
        "site-report.md": report_markdown(report, statements),
        "site.svg": site_svg,
        "terrain.svg": terrain_svg,
        "index.html": render_review_html(site, report, site_svg, terrain_svg, cads, statements),
    }
    if cad_inputs:
        files["cad-import.json"] = pretty_json(store.get(cad_inputs[0]))
    if len(cad_inputs) > 1:
        for r in cad_inputs:
            files[f"{r.id}.json"] = pretty_json(store.get(r))
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
        _out(f"wrote {out / name}")
    for b in report.blockers:
        _out(f"BLOCKER {b}")
    return EXIT_OK


def cmd_statement_add(args: argparse.Namespace) -> int:
    store = ProjectStore(_dir(args.dir))
    ref = record_owner_statement(store, subject=args.subject, words=args.words,
                                 stated_by=args.stated_by, channel=args.channel,
                                 actor=args.actor, pending_confirmation=args.pending)  # fmt: skip
    _out(f"stored {ref.kind.value}/{ref.id} v{ref.version}: recorded, not confirmed")
    return EXIT_OK


def cmd_statement_list(args: argparse.Namespace) -> int:
    for st in owner_statements(ProjectStore(_dir(args.dir))):
        _out(f"{st.id} [{st.subject}] {st.stated_by}: \"{st.words}\" ({st.channel}; "
             f"recorded by {st.recorded_by.kind.value}:{st.recorded_by.id})")  # fmt: skip
        if st.pending_confirmation:
            _out(f"    not yet formal: {st.pending_confirmation}")
    return EXIT_OK


def cmd_crs_describe(args: argparse.Namespace) -> int:
    info = describe_epsg(args.epsg)
    for key, value in info.__dict__.items():
        _out(f"{key:12} {value}")
    return EXIT_OK


def cmd_crs_utm(args: argparse.Namespace) -> int:
    _out(f"EPSG CRSs for UTM zone {args.zone}{args.hemisphere.upper()} (pick by datum; ")
    _out("the zone number alone does not decide it):")
    for info in utm_candidates(args.zone, args.hemisphere):
        _out(f"  EPSG:{info.epsg:<6} {info.name}")
    return EXIT_OK


# ------------------------------------------------------------------- interview


def _owner_terminal(what: str) -> bool:
    """Direct human-only terminal actions (consent, interactive run, program reject)."""
    if sys.stdin.isatty():
        return True
    _err(
        f"{what} requires an interactive terminal run by the homeowner."
    )
    return False


def _parse_set_args(
    set_items: list[str] | None,
    unknown_slots: list[str] | None,
    interpret_json: str | None,
) -> dict | None:
    if not set_items and not unknown_slots and not interpret_json:
        return None
    out: dict = {}
    if interpret_json:
        try:
            loaded = json.loads(interpret_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--interpret-json must be valid JSON: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ValueError("--interpret-json must be a JSON object mapping slot -> value")
        out.update(loaded)
    for item in set_items or ():
        if "=" not in item:
            raise ValueError(f"--set expects slot=value, got {item!r}")
        slot, raw = item.split("=", 1)
        out[slot.strip()] = raw.strip()
    for slot in unknown_slots or ():
        out[slot.strip()] = None
    return out


def _turn_dict(result) -> dict:
    return {
        "session_ref": result.session_ref.model_dump(mode="json"),
        "brief_ref": result.brief_ref.model_dump(mode="json"),
        "understood": [
            {
                "slot": u.slot,
                "label": SLOTS[u.slot].label,
                "value": u.value,
                "display": describe(u.value),
                "method": u.method,
                "status": "unknown" if u.value is None else "inference",
            }
            for u in result.understood
        ],
        "asked_again": result.asked_again,
        "notes": list(result.notes),
        "contradictions": [
            {
                "id": f.id,
                "statement": f.statement,
                "tradeoff": f.tradeoff,
                "options": [o.label for o in f.options],
            }
            for f in result.contradictions
        ],
        "next_prompt": (
            {"id": result.prompt.id, "kind": result.prompt.kind, "text": result.prompt.text}
            if result.prompt is not None
            else None
        ),
    }


def _show_turn(result, *, prompt: bool = True, as_json: bool = False) -> None:
    if as_json:
        _out(json.dumps(_turn_dict(result), indent=2, ensure_ascii=False))
        return
    text = result.message()
    if text:
        _out(text)
    for f in result.contradictions:
        if result.prompt is None or result.prompt.id != f"resolve:{f.id}":
            _out(f"NOTE {f.statement}")
    if not prompt:
        return
    if result.prompt is not None:
        _out("")
        _out(f"[{result.prompt.id}] {result.prompt.text}")
    else:
        _out("All questions are answered. Review with `house-ai interview summary`.")


def cmd_interview_start(args: argparse.Namespace) -> int:
    res = InterviewService(ProjectStore(_dir(args.dir))).start(args.actor)
    _show_turn(res, as_json=getattr(args, "json", False))
    return EXIT_OK


def cmd_interview_next(args: argparse.Namespace) -> int:
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    prompt = svc.pending()
    if getattr(args, "json", False):
        payload = (
            {"id": prompt.id, "kind": prompt.kind, "text": prompt.text}
            if prompt is not None
            else None
        )
        _out(json.dumps({"next_prompt": payload}, indent=2, ensure_ascii=False))
        return EXIT_OK
    _out(f"[{prompt.id}] {prompt.text}" if prompt else "No question pending.")
    return EXIT_OK


def cmd_interview_checklist(args: argparse.Namespace) -> int:
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    info = svc.checklist()
    if getattr(args, "json", False):
        _out(json.dumps(info, indent=2, ensure_ascii=False))
        return EXIT_OK
    _out(
        f"project: {info['project_id']}  workflow: {info['workflow_state']}  "
        f"interview: {info['session_status']} ({info['turn_count']} turns)"
    )
    site = info["site"]
    if site["site_ref"] is not None:
        v_str = "verified" if site["verified"] else "SITE_NEEDS_VERIFICATION"
        _out(
            f"site: {v_str} | area={site['parcel_area_m2']} m² | "
            f"relief={site['relief_m']} m | mean_slope={site['mean_slope_pct']}% | "
            f"frontage={site['frontage_m']} m"
        )
        for b in site["verification_blockers"]:
            _out(f"  site blocker: {b}")
        for hc in site["hillside_considerations"]:
            _out(f"  hillside note: {hc}")
    if info["owner_statements"]:
        _out(f"owner statements ({len(info['owner_statements'])}):")
        for st in info["owner_statements"]:
            _out(f'  - [{st["subject"]}] "{st["words"]}"')
    c = info["counts"]
    _out(
        f"checklist: {c['covered_questions']}/{c['applicable_questions']} applicable covered | "
        f"confirmed slots={c['confirmed_slots']} | "
        f"unconfirmed (inference)={c['unconfirmed_slots']} | "
        f"open contradictions={c['open_contradictions']}"
    )
    if info["missing_required_slots"]:
        _out("missing required slots: " + ", ".join(info["missing_required_slots"]))
    if info["unconfirmed"]:
        _out("unconfirmed interpretations (ask owner to confirm or correct):")
        for u in info["unconfirmed"]:
            _out(f"  - {u['slot']} ({u['label']}): {u['display']} [{u['method']}]")
    if info["contradictions"]:
        _out("open contradictions:")
        for cf in info["contradictions"]:
            _out(f"  - {cf['id']}: {cf['statement']} ({cf['tradeoff']})")
            for opt in cf["options"]:
                _out(f"      {opt['option']}. {opt['label']}")
    for item in info["checklist"]:
        if not item["applicable"]:
            continue
        mark = "x" if item["covered"] else " "
        slot_summary = ", ".join(
            f"{s['slot']}={s['display']} ({s['status']})"
            for s in item["slots"]
            if s["status"] != "unanswered"
        )
        suffix = f" -> {slot_summary}" if slot_summary else ""
        _out(f"  [{mark}] {item['id']} ({item['topic']}): {item['question']}{suffix}")
    for ct in info["custom_turns"]:
        _out(f'  [+] {ct["question_id"]}: "{ct["text"]}"')
    if info["suggested_next"]:
        nxt = info["suggested_next"]
        _out(f"suggested next: [{nxt['id']}] {nxt['text']}")
    return EXIT_OK


def cmd_interview_answer(args: argparse.Namespace) -> int:
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    interpreted = _parse_set_args(args.set, args.unknown, args.interpret_json)
    res = svc.answer(
        args.text,
        args.actor,
        question_id=args.question,
        question_text=args.question_text,
        topic=args.topic,
        interpreted=interpreted,
        option=args.option,
    )
    _show_turn(res, as_json=args.json)
    return EXIT_OK


def cmd_interview_revise(args: argparse.Namespace) -> int:
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    interpreted = _parse_set_args(args.set, args.unknown, args.interpret_json)
    res = svc.revise(
        args.question,
        args.text,
        args.actor,
        question_text=args.question_text,
        interpreted=interpreted,
    )
    _show_turn(res, as_json=args.json)
    return EXIT_OK


def cmd_interview_confirm(args: argparse.Namespace) -> int:
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    pending = svc.state().unconfirmed()
    explicit_slots = [*(getattr(args, "slots", None) or []), *(args.slot or [])]
    chosen = explicit_slots or pending
    if not chosen:
        if args.json:
            _out(json.dumps({"confirmed": []}, indent=2))
        else:
            _out("Nothing waits for confirmation.")
        return EXIT_OK
    state = svc.state()
    if (
        args.actor.kind is ActorKind.HUMAN
        and sys.stdin.isatty()
        and not args.yes
        and not args.text
        and not args.json
    ):
        _out("You are confirming that I understood these correctly:")
        for s in chosen:
            if s in state.slots:
                _out(f"  - {SLOTS[s].label}: {describe(state.slots[s].value)}")
        if input('Type "yes" to confirm: ').strip().lower() != "yes":
            _err("nothing confirmed")
            return EXIT_FAIL
    confirmed = svc.confirm(args.actor, explicit_slots or None, text=args.text)
    if args.json:
        _out(json.dumps({"confirmed": confirmed}, indent=2, ensure_ascii=False))
    else:
        _out(f"confirmed {len(confirmed)} item(s): {', '.join(confirmed)}")
    return EXIT_OK


def cmd_interview_reject(args: argparse.Namespace) -> int:
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    res = svc.reject(args.actor, args.slot, args.text)
    _show_turn(res, as_json=args.json)
    return EXIT_OK


def cmd_interview_resolve(args: argparse.Namespace) -> int:
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    res = svc.resolve(
        args.contradiction,
        args.text,
        args.actor,
        option=args.option,
        defer=args.defer,
    )
    _show_turn(res, as_json=args.json)
    return EXIT_OK


def cmd_interview_consent(args: argparse.Namespace) -> int:
    if not _owner_terminal("interview consent"):
        return EXIT_USAGE
    phrase = f"allow {args.provider}"
    _out(f"Your interview answers are private. Allowing {args.provider} sends them to it.")
    if input(f'Type "{phrase}" to allow: ').strip() != phrase:
        _err("not allowed")
        return EXIT_FAIL
    InterviewService(ProjectStore(_dir(args.dir))).consent(args.actor, args.provider)
    _out(f"{args.provider} may now receive interview content")
    return EXIT_OK


def cmd_interview_summary(args: argparse.Namespace) -> int:
    text = InterviewService(ProjectStore(_dir(args.dir))).summary()
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        _out(f"wrote {args.out}")
    else:
        _out(text)
    return EXIT_OK


def _ai_provider(name: str, model: str | None) -> ModelProvider:
    from house_ai.providers.claude import ClaudeProvider

    return ClaudeProvider.from_environment(model)


def _attach_ai(svc: InterviewService, owner: Actor, name: str, model: str | None) -> None:
    """Give the interview an AI assistant if it is installed, configured and allowed."""
    try:
        provider = _ai_provider(name, model)
    except ProviderError as exc:
        _out(f"(AI not available: {exc}. Continuing with the built-in questions.)")
        return
    if provider.name not in svc.policy().allowed_private_providers:
        _out(f"Your answers and your site's details are private. With your permission they "
             f"are sent to {provider.name} ({getattr(provider, 'model', '')}) so it can word "
             "the questions and read free answers. Nothing it says is accepted without you.")
        phrase = f"allow {provider.name}"
        typed = input(f'Type "{phrase}" to allow, or press Enter to continue without AI: ')
        if typed.strip() != phrase:
            _out("(Continuing without AI.)")
            return
        svc.consent(owner, provider.name)
    svc.assist = LlmAssist(provider, svc.policy())
    _out(f"(AI assistant: {provider.name} {getattr(provider, 'model', '')}. It words the "
         "questions and helps read answers; you confirm everything it understood.)")  # fmt: skip


def cmd_interview_run(args: argparse.Namespace) -> int:
    """The interactive interview for the owner: one question at a time."""
    if not _owner_terminal("interview run"):
        return EXIT_USAGE
    owner = Actor(kind=ActorKind.HUMAN, id=args.owner)
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    _show_turn(svc.start(owner), prompt=False)
    if args.ai:
        _attach_ai(svc, owner, args.ai, args.model)
    _out("(Commands: :summary, :revise <question-id>, :quit. Answer in your own words.)")
    while True:
        prompt = svc.pending()
        if prompt is None:
            _out("All questions are answered.")
            break
        asked = svc.ask(prompt)
        for note in asked.notes:
            _out(note)
        _out("")
        _out(f"[{prompt.id}] {asked.text}")
        try:
            text = input("> ").strip()
        except EOFError:
            break
        if not text:
            continue
        if text == ":quit":
            _out("Stopped. Your answers are saved; run this again to continue.")
            break
        if text == ":summary":
            _out(svc.summary())
            continue
        if text.startswith(":revise "):
            qid = text.split(maxsplit=1)[1]
            new = input("Your new answer: ").strip()
            _show_turn(svc.revise(qid, new, owner), prompt=False)
            continue
        result = svc.answer(text, owner, shown=asked)
        _show_turn(result, prompt=False)
        if result.understood and any(u.method != "resolution" for u in result.understood):
            ok = input("Did I understand that correctly? [y/n] ").strip().lower()
            slots = [u.slot for u in result.understood if u.method != "resolution"]
            pending = set(svc.state().unconfirmed())
            shown = [s for s in slots if s in pending]
            if ok.startswith("y") and shown:
                svc.confirm(owner, shown)
            elif ok.startswith("n"):
                wrong = [s for s in slots if s in svc.state().slots]
                if wrong:
                    _show_turn(svc.reject(owner, wrong))
    _out(svc.summary())
    return EXIT_OK


# --------------------------------------------------------------------- program


def _export(svc: InterviewService, build, out: Path) -> None:
    import yaml

    out.mkdir(parents=True, exist_ok=True)

    def dump(model) -> str:
        return yaml.safe_dump(model.model_dump(mode="json"), sort_keys=False, allow_unicode=True)

    brief = svc.brief()
    files = {
        "design_brief.yaml": dump(brief),
        "space_program.yaml": dump(build.result.program),
        "assumptions.yaml": dump(build.result.assumptions),
        "open_questions.yaml": dump(build.result.open_questions),
        "interview-summary.md": svc.summary(),
        "program-review.md": program_markdown(
            build.result.program, brief, build.findings, build.result.assumptions,
            build.result.open_questions,
        ),
    }  # fmt: skip
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
        _out(f"wrote {out / name}")


def _show_findings(findings) -> None:
    for f in findings:
        _out(f"{f.severity.value.upper():8} {f.code}: {f.message}")
        for o in f.options:
            _out(f"         option: {o}")


def cmd_program_build(args: argparse.Namespace) -> int:
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    build = svc.build_program(args.actor)
    if args.out:
        _export(svc, build, Path(args.out))
    if getattr(args, "json", False):
        _out(
            json.dumps(
                {
                    "program_ref": build.program_ref.model_dump(mode="json"),
                    "assumptions_ref": build.assumptions_ref.model_dump(mode="json"),
                    "open_questions_ref": build.open_questions_ref.model_dump(mode="json"),
                    "findings": [
                        {
                            "code": f.code,
                            "severity": f.severity.value,
                            "message": f.message,
                            "refs": list(f.refs),
                            "options": list(f.options),
                        }
                        for f in build.findings
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return EXIT_OK
    for ref in (build.program_ref, build.assumptions_ref, build.open_questions_ref):
        _out(f"stored {ref.kind.value}/{ref.id} v{ref.version}")
    _show_findings(build.findings)
    return EXIT_OK


def cmd_program_review(args: argparse.Namespace) -> int:
    svc = InterviewService(ProjectStore(_dir(args.dir)))
    build, reasons = svc.review_program(args.actor)
    _show_findings(build.findings)
    for r in reasons:
        _out(f"OPEN {r}")
    ref = build.program_ref
    _out(f"state PROGRAM_REVIEW; the owner reviews space_program/{ref.id} v{ref.version}")
    if not reasons:
        _out(f"next: the owner runs `house-ai workflow approve {args.dir} program --id {ref.id} "
             "--approver <name>` or `house-ai program reject`")  # fmt: skip
    if args.out:
        _export(svc, build, Path(args.out))
    return EXIT_OK


def cmd_program_reject(args: argparse.Namespace) -> int:
    if not _owner_terminal("program reject"):
        return EXIT_USAGE
    InterviewService(ProjectStore(_dir(args.dir))).reject_program(args.actor, args.reason)
    _out("program rejected; back to INTERVIEWING. Your words are recorded in the brief.")
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
    s = proj.add_parser("new", help="create projects/<name>/ with its working folders")
    s.add_argument("name", help="folder and project id, lowercase, e.g. my-house")
    s.add_argument("--title", help="a readable name; defaults to the folder name")
    s.add_argument(
        "--classification", default="private", choices=[c.value for c in DataClassification]
    )
    actor_arg(s)
    s.set_defaults(func=cmd_project_new)
    s = proj.add_parser("list", help="the projects under projects/")
    s.set_defaults(func=cmd_project_list)
    s = proj.add_parser("status")
    s.add_argument("dir", help="project folder, or a project name under projects/")
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

    site = sub.add_parser("site", help="survey inspection, ingestion and confirmation")
    site = site.add_subparsers(dest="sub", required=True)
    s = site.add_parser("inspect", help="read-only report on survey files (no project needed)")
    s.add_argument("files", nargs="+")
    s.add_argument("--layers", help="layer mapping file (YAML/JSON)")
    s.add_argument("--json", action="store_true")
    s.add_argument("--out", help="write inspection.md/.json here instead of printing")
    s.set_defaults(func=cmd_site_inspect)
    s = site.add_parser("ingest", help="extract a stored survey into cad_import + site")
    s.add_argument("dir")
    s.add_argument(
        "--source",
        required=True,
        action="append",
        help="source document id (from `source add`); repeat for a survey in several files",
    )
    s.add_argument("--layers", required=True, help="layer mapping file (YAML/JSON)")
    s.add_argument("--site-id", default="site")
    actor_arg(s)
    s.set_defaults(func=cmd_site_ingest)
    s = site.add_parser("confirm", help="human confirmation of units, CRS, datum, boundary")
    s.add_argument("dir")
    s.add_argument("--id", default="site")
    s.add_argument("--confirmer", required=True, help="the human's name or id")
    s.add_argument("--units", choices=[u.value for u in LengthUnit])
    s.add_argument("--elevation-units", choices=[u.value for u in LengthUnit])
    crs = s.add_mutually_exclusive_group()
    crs.add_argument("--epsg", type=int, help="horizontal CRS EPSG code")
    crs.add_argument("--local-only", action="store_true", help="no georeference")
    s.add_argument("--vertical-datum", help="vertical datum or benchmark name")
    vd = s.add_mutually_exclusive_group()
    vd.add_argument("--vertical-epsg", type=int)
    vd.add_argument("--vertical-local", action="store_true", help="relative to a local benchmark")
    s.add_argument("--boundary-verified", action="store_true")
    s.add_argument("--origin", type=float, nargs=3, metavar=("E", "N", "Z"))
    s.add_argument("--rotation", type=float, help="local x from grid east, degrees CCW")
    s.add_argument("--accept-issue", action="append", default=[])
    s.set_defaults(func=cmd_site_confirm)
    s = site.add_parser("report", help="validation report, site SVG and provenance")
    s.add_argument("dir")
    s.add_argument("--id", default="site")
    s.add_argument("--version", type=int)
    s.add_argument("--out", help="default: <project>/reviews/<site id>-v<version>")
    s.set_defaults(func=cmd_site_report)

    st = sub.add_parser("statement", help="the owner's own statements, recorded verbatim")
    st = st.add_subparsers(dest="sub", required=True)
    s = st.add_parser("add", help="record what the owner said; confirms nothing")
    s.add_argument("dir")
    s.add_argument("--subject", required=True, help="e.g. horizontal_crs, elevation_units, relief")
    s.add_argument("--words", required=True, help="the owner's words, verbatim")
    s.add_argument("--stated-by", default="owner")
    s.add_argument("--channel", required=True, help="how it reached you, e.g. 'chat, 2026-10-17'")
    s.add_argument("--pending", help="what would make it formal, e.g. a site confirm command")
    actor_arg(s)
    s.set_defaults(func=cmd_statement_add)
    s = st.add_parser("list")
    s.add_argument("dir")
    s.set_defaults(func=cmd_statement_list)

    crs_p = sub.add_parser("crs", help="look up coordinate reference systems (PROJ)")
    crs_p = crs_p.add_subparsers(dest="sub", required=True)
    s = crs_p.add_parser("describe")
    s.add_argument("epsg", type=int)
    s.set_defaults(func=cmd_crs_describe)
    s = crs_p.add_parser("utm-candidates")
    s.add_argument("zone", type=int)
    s.add_argument("hemisphere", choices=["N", "S", "n", "s"])
    s.set_defaults(func=cmd_crs_utm)

    iv = sub.add_parser("interview", help="the owner interview (Milestone C)")
    iv = iv.add_subparsers(dest="sub", required=True)
    s = iv.add_parser("start", help="start or resume the interview; shows the next question")
    s.add_argument("dir")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_interview_start)
    s = iv.add_parser("next", help="show the pending question")
    s.add_argument("dir")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_interview_next)
    for sub_name in ("checklist", "status"):
        s = iv.add_parser(
            sub_name,
            help="inspect interview status, site context, checklist coverage and contradictions",
        )
        s.add_argument("dir")
        s.add_argument("--json", action="store_true")
        s.set_defaults(func=cmd_interview_checklist)
    s = iv.add_parser(
        "answer",
        help="record the owner's verbatim answer and optional structured slot interpretations",
    )
    s.add_argument("dir")
    s.add_argument("text", help="the homeowner's exact original words")
    s.add_argument("--question", help="question id, slot name, or custom follow-up id")
    s.add_argument("--question-text", help="exact wording of an adaptive follow-up question")
    s.add_argument("--topic", help="topic for an adaptive follow-up (e.g. site_response, views)")
    s.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="SLOT=VALUE",
        help="structured interpretation proposed by the agent (repeatable)",
    )
    s.add_argument(
        "--unknown",
        action="append",
        default=[],
        metavar="SLOT",
        help="mark a slot as unknown / undecided (repeatable)",
    )
    s.add_argument("--interpret-json", help="JSON object mapping slot -> value")
    s.add_argument("--option", type=int, help="1-based option index when resolving a contradiction")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_interview_answer)
    s = iv.add_parser(
        "revise",
        help="record the owner's revision to an earlier answer without losing history",
    )
    s.add_argument("dir")
    s.add_argument("question", help="question id (e.g. q-bedrooms), slot name, or custom id")
    s.add_argument("text", help="the homeowner's exact new words")
    s.add_argument("--question-text", help="exact wording of the question asked")
    s.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="SLOT=VALUE",
        help="structured interpretation proposed by the agent (repeatable)",
    )
    s.add_argument("--unknown", action="append", default=[], metavar="SLOT")
    s.add_argument("--interpret-json", help="JSON object mapping slot -> value")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_interview_revise)
    s = iv.add_parser("confirm", help="record the owner's confirmation of interpreted slot values")
    s.add_argument("dir")
    s.add_argument("slots", nargs="*", help="optional slot names to confirm (default: all pending)")
    s.add_argument("--slot", action="append", default=[])
    s.add_argument("--text", help="the homeowner's confirmation words")
    s.add_argument("--yes", action="store_true", help="skip interactive prompt")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_interview_confirm)
    s = iv.add_parser("reject", help="record the owner's rejection of an interpreted slot value")
    s.add_argument("dir")
    s.add_argument("--slot", action="append", required=True)
    s.add_argument("--text", help="what is wrong, in the owner's words")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_interview_reject)
    s = iv.add_parser("resolve", help="record the owner's resolution of an open contradiction")
    s.add_argument("dir")
    s.add_argument("contradiction", help="contradiction id, e.g. c-too-few-bedrooms")
    s.add_argument("text", help="the homeowner's exact resolution words")
    s.add_argument("--option", type=int, help="1-based option index chosen by the homeowner")
    s.add_argument("--defer", action="store_true", help="defer deciding on this contradiction")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_interview_resolve)
    s = iv.add_parser("consent", help="the owner allows an AI provider (terminal only)")
    s.add_argument("dir")
    s.add_argument("provider")
    actor_arg(s)
    s.set_defaults(func=cmd_interview_consent)
    s = iv.add_parser("summary", help="what has been understood so far")
    s.add_argument("dir")
    s.add_argument("--out")
    s.set_defaults(func=cmd_interview_summary)
    s = iv.add_parser("run", help="interactive interview for the owner")
    s.add_argument("dir")
    s.add_argument("--owner", required=True, help="the owner's name or id")
    s.add_argument("--ai", choices=["anthropic"],
                   help="let an AI word the questions and read free answers (needs consent)")
    s.add_argument("--model", help="AI model id (default: claude-opus-5-5)")
    s.set_defaults(func=cmd_interview_run)

    pr = sub.add_parser("program", help="space program from the brief (Milestone C)")
    pr = pr.add_subparsers(dest="sub", required=True)
    s = pr.add_parser("build", help="derive, store and check the space program")
    s.add_argument("dir")
    s.add_argument("--out", help="also write design_brief.yaml, space_program.yaml, ...")
    s.add_argument("--json", action="store_true")
    actor_arg(s)
    s.set_defaults(func=cmd_program_build)
    s = pr.add_parser("review", help="build the program and ask the owner to review it")
    s.add_argument("dir")
    s.add_argument("--out")
    actor_arg(s)
    s.set_defaults(func=cmd_program_review)
    s = pr.add_parser("reject", help="the owner rejects the program at review (terminal only)")
    s.add_argument("dir")
    s.add_argument("--reason", required=True, help="what is wrong, in the owner's words")
    actor_arg(s)
    s.set_defaults(func=cmd_program_reject)

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
    except (StoreError, WorkflowError, ValidationError, ValueError, DwgConversionError) as exc:
        _err(f"error: {exc}")
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
