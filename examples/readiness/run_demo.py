"""S9-02 end-to-end readiness demonstration on the SYNTHETIC steep hillside.

    .venv/bin/python examples/readiness/run_demo.py [--out project-data/s9-demo]
                                                    [--strategies two_wing,...] [--no-proposal]

One synthetic project store goes through every stage an agent and a homeowner
would: site gate, agent-operated interview (verbatim owner words, agent
interpretations, a Persian answer, a corrected answer, confirmation), program
gate, solver concepts for all strategies, critics, an agent topology proposal,
visual review grounded in canonical IDs, two owner-style revisions, comparison,
plan gate, reviewer bundle and provenance checks. ``record.json`` and
``record.md`` in ``--out`` list what happened, including every refusal and
every defect the critics or the demonstration itself found.

The owner is the SYNTHETIC actor ``human:example-owner`` (as in the tests and
``examples/interviews/synthetic-family``); its approvals exercise the gates and
endorse nothing. In a real project only the homeowner approves, in their own
terminal. The visual critique in ``visual_critique.json`` was written by an
agent after looking at the rendered plan (``ai_judgment``); this script only
checks that it cites canonical IDs. Solver output can differ between platforms
(ISS-21, ISS-28), so nothing here is compared byte for byte.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import Strength
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.provenance import (
    Actor,
    ActorKind,
    ApprovalRequiresHuman,
    ArtifactKind,
    DataClassification,
)
from house_ai.domain.site import Site
from house_ai.domain.visual_critique import VisualCritiqueFile
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.evaluation.explain import detect_near_duplicates, footprint_iou, topology_distance
from house_ai.orchestration.interview import InterviewService
from house_ai.orchestration.plans import PlanService, PlanWorkflowError, StoredOption
from house_ai.orchestration.reviewer_bundle import export_reviewer_bundle
from house_ai.orchestration.site import SiteService
from house_ai.orchestration.workflow import GateBlocked, Workflow
from house_ai.render2d.rasterize import find_rasterizer, rasterize_svg_to_png
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import load_document
from house_ai.validation.defect_detectors import scan_all_model_defects
from house_ai.validation.grounding import collect_canonical_ids

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"
PROJECT = "synthetic-hillside"
OWNER = Actor(kind=ActorKind.HUMAN, id="example-owner")
AGENT = Actor(kind=ActorKind.AGENT, id="claude-code")
VISUAL_OPTION = "concept-two-wing"
#: The owner's requests after seeing the visual review, verbatim, and the agent's explicit ops.
REVISIONS = [
    ("The living room is too small for us. Please make it about 25 m2.", ["area:pi-living=25"]),
    (
        "Keep the study away from the garage, it gets noisy when the car comes in.",
        ["separate:pi-study-1,pi-garage"],
    ),
]
#: Critic findings that make a concept unusable or inconsistent as drawn (S9-01 evidence).
DEFECT_CODES = {
    "floor_connection_height_mismatch",
    "stair_low_headroom",
    "kitchen_no_sampled_fit",
    "bed_double_no_sampled_fit",
    "height_limit_exceeded",
    "program_item_missing",
    "storey_count_differs",
    "large_underfloor_void",
    "buried_habitable_face",
    "window_buried",
    "label_collision",
}


class DemoError(RuntimeError):
    pass


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


def _refused(fn, *exc_types) -> str | None:
    """Run ``fn``; return the refusal message, or None when it was not refused."""
    try:
        fn()
    except exc_types as exc:
        return str(exc)
    return None


def _option_summary(opt: StoredOption) -> dict:
    cand = opt.candidate
    row = {"option": cand.option_id, "strategy": cand.strategy, "feasible": cand.plan is not None}
    if cand.plan is None or opt.report is None:
        row["reason"] = cand.reason
        return row
    hard = [v for v in opt.report.violations if v.strength is Strength.HARD]
    soft = [v for v in opt.report.violations if v.strength is not Strength.HARD]
    codes = collections.Counter(v.code for v in opt.report.violations)
    model = cand.plan.model
    row.update(
        version=opt.plan_ref.version if opt.plan_ref else None,
        sha256=opt.plan_ref.sha256 if opt.plan_ref else None,
        levels={lv.id: round(lv.elevation_m, 2) for lv in model.levels},
        stairs=[
            {"id": s.id, "kind": s.kind.value, "walking_line": s.walking_line is not None}
            for s in model.stairs
        ],
        furniture=len(model.furniture),
        fixtures=len(model.fixtures),
        hard=len(hard),
        soft=len(soft),
        hard_codes=sorted({v.code for v in hard}),
        defects=[
            {"code": v.code, "subjects": list(v.subject_ids), "message": v.message}
            for v in opt.report.violations
            if v.code in DEFECT_CODES
        ],
        codes=dict(sorted(codes.items())),
        not_checked=sorted(
            {m.metric for m in opt.report.metrics if m.status.value == "not_checked"}
        ),
    )
    return row


def _render(plan_json: Path, png: Path) -> str | None:
    """Rasterize ``plan.svg`` next to ``plan_json``; return the PNG's sha256 (None: no tool)."""
    if find_rasterizer() is None:
        return None
    svg = (plan_json.parent / "plan.svg").read_text("utf-8")
    rasterize_svg_to_png(svg, png, width=1600, height=1200)
    return hashlib.sha256(png.read_bytes()).hexdigest()


def _space_area(plan: PlanVersion, space_id: str) -> float | None:
    sp = next((s for s in plan.model.spaces if s.id == space_id), None)
    return round(sp.area_m2, 2) if sp else None


def run(out: Path, strategies: list[str] | None = None, with_proposal: bool = True) -> dict:
    if out.exists() and any(out.iterdir()):
        raise DemoError(f"{out} is not empty; choose a new --out folder")
    out.mkdir(parents=True, exist_ok=True)
    rec: dict = {
        "synthetic": True,
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.machine()}",
        "strategies_requested": strategies or "all",
    }
    store = ProjectStore.init(out / "project", project_id=PROJECT,
                              name="S9 readiness demonstration (synthetic)",
                              classification=DataClassification.SYNTHETIC, actor=AGENT,
                              clock=Clock())  # fmt: skip
    wf = Workflow(store)
    plans = PlanService(store)

    # 1. Site and site gate.
    site = Site.model_validate(load_document(HILLSIDE / "site.yaml"))
    site_ref = store.put(ArtifactKind.SITE, "site", site, AGENT, reason="synthetic steep site")
    wf.transition(WorkflowState.SITE_INGESTION, AGENT, "synthetic site loaded")
    refusals = {
        "plan_generate_before_gates": _refused(
            lambda: plans.generate(AGENT, strategies=["compact"]), PlanWorkflowError
        ),
        "agent_approves_site": _refused(
            lambda: wf.approve(Gate.SITE, site_ref, AGENT, "agent tries"), ApprovalRequiresHuman
        ),
    }
    blockers = SiteService(store).assess(site_ref, AGENT).blockers
    wf.approve(Gate.SITE, site_ref, OWNER, "synthetic owner approves the synthetic site")

    # 2. Agent-operated interview.
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "start the interview")
    svc = InterviewService(store)
    svc.start(AGENT)
    script = yaml.safe_load((HERE / "answers.yaml").read_text("utf-8"))
    for step in script["answers"]:
        prompt = svc.pending()
        if prompt is None or prompt.id != step["question"]:
            raise DemoError(f"interview asked {prompt and prompt.id}, expected {step['question']}")
        svc.answer(step["answer"], AGENT, interpreted=step.get("set"))
    if (left := svc.pending()) is not None:
        raise DemoError(f"interview still asks {left.id}")
    rev = script["revision"]
    svc.revise(rev["question"], rev["answer"], AGENT, interpreted=rev.get("set"))
    inferred_before = svc.state().unconfirmed()
    svc.confirm(AGENT, text=script["confirmation"])
    session = svc.session()
    turn_texts = [t.text for t in session.turns if t.text]
    spoken = [s["answer"] for s in script["answers"]] + [rev["answer"]]
    state = svc.state()
    site_ctx = svc.site()
    rec["site"] = {
        "ref": site_ref.model_dump(mode="json"),
        "blockers": blockers,
        "relief_m": site_ctx.relief_m if site_ctx else None,
        "parcel_area_m2": site_ctx.parcel_area_m2 if site_ctx else None,
        "unknown": sorted(
            k for k in ("mean_slope_pct", "frontage_m") if getattr(site_ctx, k, None) is None
        ),
    }
    rec["interview"] = {
        "turns": len(session.turns),
        "answers_scripted": len(spoken),
        "answers_recorded_verbatim": sum(1 for s in spoken if s in turn_texts),
        "turn_actors": sorted({f"{t.actor.kind.value}:{t.actor.id}" for t in session.turns}),
        "slot_methods": dict(collections.Counter(s.method for s in state.slots.values())),
        "inferences_before_confirmation": len(inferred_before),
        "unconfirmed_after_confirmation": state.unconfirmed(),
        "budget_history": [t.text for t in session.turns if t.question_id == "q-budget"],
        "budget_value": state.values.get("budget"),
        "outdoor_value": state.values.get("outdoor"),
        "open_contradictions": svc.checklist()["counts"]["open_contradictions"],
    }

    # 3. Program and program gate.
    build, reasons = svc.review_program(AGENT)
    if reasons:
        raise DemoError(f"program review has open reasons: {reasons}")
    refusals["agent_approves_program"] = _refused(
        lambda: wf.approve(Gate.PROGRAM, build.program_ref, AGENT, "agent tries"),
        ApprovalRequiresHuman,
    )
    wf.approve(Gate.PROGRAM, build.program_ref, OWNER, "synthetic owner approves the program")
    program = build.result.program
    rec["program"] = {
        "ref": build.program_ref.model_dump(mode="json"),
        "items": [
            {"id": i.id, "function": i.function.value, "target_m2": i.target_area_m2}
            for i in program.space_requirements
        ],
        "target_gross_area_m2": program.target_gross_area_m2,
        "findings": sorted({f.code for f in build.findings}),
        "assumptions": len(build.result.assumptions.assumptions),
        "open_questions": len(build.result.open_questions.questions),
    }

    # 4. Solver concepts for every strategy, with critics.
    concepts = out / "concepts"
    gen = plans.generate(AGENT, strategies=strategies, out_dir=concepts)
    rec["concepts"] = [_option_summary(o) for o in gen.options]
    approvals = wf.status().approvals
    pinned = [store.get(o.plan_ref, PlanVersion) for o in gen.generated if o.plan_ref is not None]
    rec["concepts_pin_approved_inputs"] = all(
        p.model.site_ref == approvals[Gate.SITE].artifact
        and p.model.program_ref == approvals[Gate.PROGRAM].artifact
        for p in pinned
    )
    models = {o.candidate.option_id: o.candidate.plan.model for o in gen.generated}
    ids = sorted(models)
    rec["diversity"] = [
        {
            "pair": [a, b],
            "footprint_iou": round(footprint_iou(models[a], models[b]), 2),
            "topology_distance": round(topology_distance(models[a], models[b]), 2),
            "near_duplicate": detect_near_duplicates(models[a], models[b])[0],
        }
        for i, a in enumerate(ids)
        for b in ids[i + 1 :]
    ]

    # 5. An agent topology proposal (2D placement).
    if with_proposal:
        proposal = ConceptProposal.model_validate(load_document(HERE / "proposal.yaml"))
        res = plans.propose(AGENT, proposal, out_dir=concepts)
        rec["proposal"] = [_option_summary(o) for o in res.options]

    # 6. Visual review of one concept, grounded in canonical IDs.
    visual = next((o for o in gen.generated if o.candidate.option_id == VISUAL_OPTION), None)
    renders = out / "renders"
    renders.mkdir()
    if visual is None or visual.export_dir is None:
        rec["visual_review"] = {"status": "not_checked", "reason": f"{VISUAL_OPTION} infeasible"}
    else:
        before_json = visual.export_dir / "plan.json"
        png_hash = _render(before_json, renders / f"{VISUAL_OPTION}-v1.png")
        critique_file = HERE / "visual_critique.json"
        if not critique_file.is_file():
            raise DemoError(f"no agent critique at {critique_file}; inspect the render first")
        critique = VisualCritiqueFile.model_validate(load_document(critique_file))
        valid = collect_canonical_ids(load_document(before_json))
        valid |= collect_canonical_ids(program.model_dump(mode="json"))
        rec["visual_review"] = {
            "critique_author": critique.author,
            "claims": [
                {
                    "id": c.id,
                    "status": c.status.value,
                    "elements": c.element_ids,
                    "text": c.claim_text,
                }
                for c in critique.claims
            ],  # fmt: skip
            "ungrounded_ids": critique.ungrounded_ids(valid),
            "png_sha256": png_hash,
            "critique_made_on_this_rendering": png_hash == critique.screenshot_hash,
            "detector_findings": [
                {"type": f.defect_type, "elements": f.element_ids}
                for f in scan_all_model_defects(visual.candidate.plan.model)
            ],
        }

    # 7. Owner-style revisions with explicit ops, then the intent check.
    revisions = []
    if visual is not None:
        for words, ops in REVISIONS:
            r = plans.revise(VISUAL_OPTION, words, AGENT, ops=ops, out_dir=concepts)
            plan = store.get(r.option.plan_ref, PlanVersion)
            entry = {
                "words": words,
                "ops": ops,
                "version": r.option.plan_ref.version,
                "rooms_changed": r.revision.rooms_changed,
                "new_violations": r.revision.new_violations,
                "resolved_violations": r.revision.resolved_violations,
                "living_area_m2": _space_area(plan, "sp-living"),
            }
            revisions.append(entry)
        last = store.latest(ArtifactKind.PLAN, VISUAL_OPTION)
        _render(concepts / VISUAL_OPTION / f"v{last.version:04d}" / "plan.json",
                renders / f"{VISUAL_OPTION}-v{last.version}.png")  # fmt: skip
        # Independent check of the first request (25 m², the revision code allows 2 m²).
        first = revisions[0]
        first["request_met"] = (first["living_area_m2"] or 0) >= 25 - 2.0
        first["unmet_request_reported"] = any("area:pi-living" in v
                                              for v in first["new_violations"])  # fmt: skip
    rec["revisions"] = revisions

    # 7b. A program version written after the approval is not used until a human approves it.
    changed = program.model_copy(update={"target_gross_area_m2": 400.0})
    v2 = store.put(ArtifactKind.SPACE_PROGRAM, build.program_ref.id, changed, AGENT,
                   reason="unapproved program change")  # fmt: skip
    later = plans.generate(AGENT, strategies=["linear"], out_dir=concepts)
    rec["unapproved_program"] = {
        "written_version": v2.version,
        "approved_version": wf.status().approvals[Gate.PROGRAM].artifact.version,
        "new_plans_pin_program_versions": sorted(
            {store.get(o.plan_ref, PlanVersion).model.program_ref.version for o in later.generated}
        ),
    }
    plans.compare(concepts)
    rec["comparison"] = "concepts/comparison.md"

    # 8. Plan gate: review request, refusal for an agent, synthetic approval, frozen plan.
    if visual is not None:
        ref, event = plans.request_review(VISUAL_OPTION, AGENT)
        refusals["agent_approves_plan"] = _refused(
            lambda: wf.approve(Gate.PLAN, ref, AGENT, "agent tries"), ApprovalRequiresHuman
        )
        # An unbuildable plan stays closed even for the human (ADR 0024).
        blocked = _refused(
            lambda: wf.approve(Gate.PLAN, ref, OWNER, "synthetic owner approves to exercise it"),
            GateBlocked,
        )
        if blocked is not None:
            refusals["human_approves_unbuildable_plan"] = blocked
        else:
            refusals["revise_after_plan_approval"] = _refused(
                lambda: plans.revise(
                    VISUAL_OPTION, "a bigger kitchen", AGENT, ops=["area:pi-kitchen=16"]
                ),
                PlanWorkflowError,
            )
        rec["plan_gate"] = {"requested": ref.model_dump(mode="json"),
                            "open_reasons": event.payload["open_reasons"],
                            "attention": event.payload.get("attention", [])}  # fmt: skip
    rec["refusals"] = refusals

    # 9. Reviewer bundle and provenance.
    bundle = export_reviewer_bundle(store, out / "bundle", plan_options_dir=concepts)
    status = wf.status()
    rec["bundle"] = {"path": str(bundle.relative_to(out)), "bytes": bundle.stat().st_size}
    rec["provenance"] = {
        "store_verify_problems": store.verify(),
        "events": len(store.events()),
        "state": status.state.value,
        "approvals": {
            g.value: f"{a.approved_by.kind.value}:{a.approved_by.id}"
            for g, a in status.approvals.items()
        },
        "approved_program_is_the_built_one": status.approvals[Gate.PROGRAM].artifact
        == build.program_ref,
    }
    (out / "record.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", "utf-8")
    (out / "record.md").write_text(record_markdown(rec), "utf-8")
    return rec


def record_markdown(rec: dict) -> str:
    """A readable account of ``rec``; every number comes from the run."""
    lines = [
        "# S9 readiness demonstration record (SYNTHETIC)",
        "",
        f"Python {rec['python']} on {rec['platform']}; strategies: {rec['strategies_requested']}.",
        "The owner is the synthetic actor `human:example-owner`; its approvals exercise the",
        "gates and endorse nothing. Solver output can differ between platforms.",
        "",
        "## Refusals (gates and frozen plans)",
        "",
    ]
    lines += [f"- `{k}`: {v if v else 'NOT REFUSED'}" for k, v in rec["refusals"].items()]
    s, i, p = rec["site"], rec["interview"], rec["program"]
    lines += [
        "",
        "## Site",
        "",
        f"- relief {s['relief_m']} m, parcel {s['parcel_area_m2']} m², blockers {s['blockers']}",
        f"- unknown (null, not invented): {', '.join(s['unknown']) or 'none'}",
        "",
        "## Interview",
        "",
        f"- {i['turns']} turns; {i['answers_recorded_verbatim']} of {i['answers_scripted']} "
        "scripted answers stored verbatim",
        f"- recorded by {', '.join(i['turn_actors'])}; slot methods {i['slot_methods']}",
        f"- {i['inferences_before_confirmation']} inferences before confirmation, "
        f"{len(i['unconfirmed_after_confirmation'])} after",
        f"- outdoor (Persian answer, agent interpretation): {i['outdoor_value']}",
        f"- budget history kept: {i['budget_history']} -> {i['budget_value']}",
        "",
        "## Program",
        "",
        f"- {len(p['items'])} items, target gross area {p['target_gross_area_m2']} m²; "
        f"findings {p['findings']}; {p['assumptions']} assumptions, "
        f"{p['open_questions']} open questions",
        "",
        "## Concepts and critics",
        "",
        f"Plans pin the approved site and program: {rec['concepts_pin_approved_inputs']}.",
        "",
        "| Option | Feasible | Hard | Soft | Levels | Stairs (walking line) | Furniture/fixtures |",
        "|---|---|---:|---:|---|---|---|",
    ]
    for c in rec["concepts"] + rec.get("proposal", []):
        if not c["feasible"]:
            lines.append(f"| {c['option']} | no: {c['reason'][:90]} | | | | | |")
            continue
        stairs = ", ".join(f"{x['id']} {x['kind']} ({'yes' if x['walking_line'] else 'no'})"
                           for x in c["stairs"]) or "none"  # fmt: skip
        levels = ", ".join(f"{k} {v}" for k, v in c["levels"].items())
        lines.append(f"| {c['option']} v{c['version']} | yes | {c['hard']} | {c['soft']} | "
                     f"{levels} | {stairs} | {c['furniture']}/{c['fixtures']} |")  # fmt: skip
    lines += ["", "Defects found by the critics:", ""]
    for c in rec["concepts"] + rec.get("proposal", []):
        for d in c.get("defects", []):
            lines.append(f"- {c['option']}: `{d['code']}` {d['subjects']}: {d['message']}")
    near = [d["pair"] for d in rec["diversity"] if d["near_duplicate"]]
    lines += [
        "",
        f"Diversity: {len(rec['diversity'])} pairs, near-duplicates {near or 'none'}; "
        f"max footprint IoU {max((d['footprint_iou'] for d in rec['diversity']), default=None)}, "
        f"min topology distance "
        f"{min((d['topology_distance'] for d in rec['diversity']), default=None)}.",
        "",
        "## Visual review",
        "",
    ]
    vr = rec["visual_review"]
    if "claims" in vr:
        lines.append(f"Critique by {vr['critique_author']}; ungrounded IDs: "
                     f"{vr['ungrounded_ids'] or 'none'}; made on this rendering: "
                     f"{vr['critique_made_on_this_rendering']}.")  # fmt: skip
        lines += [""] + [f"- {c['id']} [{c['status']}] {c['elements']}: {c['text']}"
                         for c in vr["claims"]]  # fmt: skip
        lines += ["", "Automated S5 defect detectors on the same version: "
                  + (", ".join(f"{d['type']} {d['elements']}" for d in vr["detector_findings"])
                     or "no findings")]  # fmt: skip
    else:
        lines.append(f"not checked: {vr['reason']}")
    lines += ["", "## Owner-style revisions", ""]
    for r in rec["revisions"]:
        lines.append(f"- v{r['version']}: \"{r['words']}\" ops {r['ops']}; rooms changed "
                     f"{r['rooms_changed'] or 'none'}; living {r['living_area_m2']} m²; "
                     f"new violations {r['new_violations'] or 'none'}")  # fmt: skip
        if "request_met" in r:
            lines.append(f"  - request met (within 2 m²): {r['request_met']}; unmet request "
                         f"reported by the revision: {r['unmet_request_reported']}")  # fmt: skip
    pv, up = rec["provenance"], rec["unapproved_program"]
    lines += [
        "",
        "## Unapproved program change",
        "",
        f"- program v{up['written_version']} written after approval of "
        f"v{up['approved_version']}; new plans pin program version(s) "
        f"{up['new_plans_pin_program_versions']}",
        "",
        "## Plan gate, bundle and provenance",
        "",
        f"- plan review open reasons: {len(rec.get('plan_gate', {}).get('open_reasons', []))}; "
        f"attention: {rec.get('plan_gate', {}).get('attention') or 'none'}",
        f"- approvals: {pv['approvals']}; final state {pv['state']}",
        f"- reviewer bundle {rec['bundle']['path']} ({rec['bundle']['bytes']} bytes)",
        f"- store verify problems: {pv['store_verify_problems'] or 'none'}; {pv['events']} events",
        "",
        "Nothing here is permit-ready, construction-ready or professionally checked; see",
        "docs/PROFESSIONAL_HANDOFF.md.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(REPO / "project-data" / "s9-demo"))
    ap.add_argument("--strategies", default=None, help="comma-separated; default all")
    ap.add_argument("--no-proposal", action="store_true")
    args = ap.parse_args(argv)
    strategies = args.strategies.split(",") if args.strategies else None
    try:
        run(Path(args.out), strategies, with_proposal=not args.no_proposal)
    except DemoError as exc:
        print(f"demonstration stopped: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {Path(args.out) / 'record.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
