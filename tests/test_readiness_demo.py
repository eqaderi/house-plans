"""S9-02: the end-to-end readiness demonstration runs on synthetic data and keeps its record.

Properties only: solver output differs between platforms (ISS-21, ISS-28), so no plan
geometry is compared byte for byte.
"""

from __future__ import annotations

import collections
import hashlib
import json

import yaml
from shapely.geometry import Point

from examples.readiness.run_demo import DEFECT_CODES, HERE, HILLSIDE, REVISIONS, VISUAL_OPTION, run
from house_ai.domain.evaluation import EvaluationReport
from house_ai.domain.label_layout import label_layout
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import Strength
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.site import Site
from house_ai.evaluation.report import report_id
from house_ai.render2d.rasterize import find_rasterizer
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import load_document


def _stored_report(store: ProjectStore, option: str, version: int) -> EvaluationReport:
    (report,) = [
        r
        for r in (
            store.get(ref, EvaluationReport)
            for ref in store.refs(ArtifactKind.EVALUATION_REPORT, report_id(option))
        )
        if (r.plan_ref.id, r.plan_ref.version) == (option, version)
    ]
    return report


def test_readiness_demonstration_end_to_end(tmp_path):
    out = tmp_path / "demo"
    rec = run(out, strategies=["two_wing"])
    assert json.loads((out / "record.json").read_text("utf-8")) == rec
    assert "SYNTHETIC" in (out / "record.md").read_text("utf-8")

    # Gates: refused before approval and for agents; an approved plan is frozen.
    assert set(rec["refusals"]) == {
        "plan_generate_before_gates",
        "agent_approves_site",
        "agent_approves_program",
        "agent_approves_plan",
        "revise_after_plan_approval",
    }
    assert all(rec["refusals"].values()), rec["refusals"]
    assert rec["provenance"]["approvals"] == {
        "site": "human:example-owner",
        "program": "human:example-owner",
        "plan": "human:example-owner",
    }
    assert rec["provenance"]["state"] == "PLAN_APPROVED"
    assert rec["provenance"]["store_verify_problems"] == []
    assert rec["provenance"]["approved_program_is_the_built_one"] is True
    assert rec["unapproved_program"] == {
        "written_version": 2,
        "approved_version": 1,
        "new_plans_pin_program_versions": [1],
    }

    # Interview: every scripted answer verbatim, agent interpretations confirmed, history kept.
    script = yaml.safe_load((HERE / "answers.yaml").read_text("utf-8"))
    interview = rec["interview"]
    assert interview["answers_scripted"] == len(script["answers"]) + 1
    assert interview["answers_recorded_verbatim"] == interview["answers_scripted"]
    assert interview["turn_actors"] == ["agent:claude-code"]
    assert interview["slot_methods"]["agent:claude-code"] == 2  # outdoor, budget revision
    assert interview["inferences_before_confirmation"] > 0
    assert interview["unconfirmed_after_confirmation"] == []
    assert interview["outdoor_value"] == ["terrace", "garden"]
    assert interview["budget_history"] == [
        "About 500k EUR.",
        "Sorry, the budget is closer to 550k EUR.",
    ]
    # S10-17: site context reports derived slope and frontage with no unknowns.
    assert rec["site"]["unknown"] == []
    assert rec["site"]["blockers"] == []
    # Relief is the fall between the highest and lowest spot elevation inside the parcel.
    site = Site.model_validate(load_document(HILLSIDE / "site.yaml"))
    parcel = site.boundary.to_shapely().buffer(1e-6)
    zs = [p.z_m for p in site.terrain.spot_elevations if parcel.covers(Point(p.xy))]
    assert rec["site"]["relief_m"] == round(max(zs) - min(zs), 3)
    assert rec["site"]["relief_m"] > 10  # steep fixture

    # Concepts pin the approved inputs; critics ran and their findings are in the record.
    assert rec["concepts_pin_approved_inputs"] is True
    (two_wing,) = rec["concepts"]
    assert two_wing["option"] == "concept-two-wing" and two_wing["feasible"]
    assert two_wing["version"] == 1
    # The record states the stored Evaluation of that version, finding for finding.
    store = ProjectStore(out / "project")
    report = _stored_report(store, "concept-two-wing", 1)
    hard = [v for v in report.violations if v.strength is Strength.HARD]
    assert (two_wing["hard"], two_wing["soft"]) == (len(hard), len(report.violations) - len(hard))
    assert two_wing["hard_codes"] == sorted({v.code for v in hard})
    assert two_wing["codes"] == dict(collections.Counter(v.code for v in report.violations))
    assert two_wing["not_checked"] == sorted(
        {m.metric for m in report.metrics if m.status.value == "not_checked"}
    )
    assert two_wing["defects"] == [
        {"code": v.code, "subjects": list(v.subject_ids), "message": v.message}
        for v in report.violations
        if v.code in DEFECT_CODES
    ]
    # Colliding labels are a Finding of the Evaluation, from the drawing's own layout (#34):
    # the record lists exactly the pairs that layout gives for the stored Plan version. Which
    # labels collide depends on the platform's solver output, so the pairs are laid out here
    # from the stored model, never pinned.
    plan = store.get(report.plan_ref, PlanVersion)
    pairs = label_layout(plan.model, store.get(plan.model.site_ref, Site)).collisions()
    assert [d["subjects"] for d in two_wing["defects"] if d["code"] == "label_collision"] == [
        [a.space_id, b.space_id] for a, b in pairs
    ]
    (label_metric,) = [m for m in report.metrics if m.metric == "label_collisions"]
    assert label_metric.value == len(pairs)

    # S10-05, S10-06: stairs have measured walking lines and no unbuildable clashes.
    assert len(two_wing["stairs"]) >= 1
    assert all(s["walking_line"] is True for s in two_wing["stairs"])
    stair_defect_codes = {
        "stair_wall_clash",
        "stair_low_headroom",
        "floor_connection_height_mismatch",
    }
    assert not stair_defect_codes.intersection(two_wing["codes"])

    # S10-08, S10-09, S10-19, DEC-13: fixtures placed, measured counter run, vehicle fit.
    assert two_wing["fixtures"] == 9  # all canonical template sets placed
    assert "kitchen_no_sampled_fit" not in two_wing["codes"]
    assert "object_clearance_blocked" not in two_wing["codes"]
    assert "garage_sampled_fit" not in two_wing.get("hard_codes", [])

    # S10-13: 2D placement proposal has road-level entry and terrain-derived levels.
    prop = rec["proposal"][0]
    assert prop["option"] == "concept-open-plan-prop-day-up-night-down"
    assert prop["feasible"] is True
    assert "lv-entry" in prop["levels"] and "lv-lower" in prop["levels"]
    assert prop["levels"]["lv-entry"] > prop["levels"]["lv-lower"]
    assert prop["hard"] == 0

    # S10-07: soft envelope findings appear in attention without blocking the gate.
    assert rec["plan_gate"]["open_reasons"] == []
    assert any("height_limit_exceeded" in a for a in rec["plan_gate"]["attention"])

    # Visual review; S10-16 defects are Findings of the Evaluation (ADR 0033).
    vr = rec["visual_review"]
    assert "vc-living-too-small" not in vr["ungrounded_ids"]
    assert {c["status"] for c in vr["claims"]} == {"ai_judgment"}
    if find_rasterizer() is not None:
        png = out / "renders" / f"{VISUAL_OPTION}-v1.png"
        assert png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        assert vr["png_sha256"] == hashlib.sha256(png.read_bytes()).hexdigest()
    else:
        assert vr["png_sha256"] is None
    # Fonts and solver output vary across platforms. A replay must report honestly
    # whether this exact PNG was critiqued; rasterizer availability cannot prove it.
    critique = json.loads((HERE / "visual_critique.json").read_text("utf-8"))
    assert vr["critique_made_on_this_rendering"] is (
        vr["png_sha256"] == critique["screenshot_hash"]
    )
    # The visual review cites the same version's Evaluation as the concept table (ADR 0033).
    # Which defects a layout has varies by platform; the label collisions among them were
    # checked against the drawing's layout above.
    assert vr["evaluation_findings"] == [
        {"code": d["code"], "subjects": d["subjects"]} for d in two_wing["defects"]
    ]

    # Revisions keep the owner's words and ops and add versions 2 and 3.
    assert [(r["words"], r["ops"]) for r in rec["revisions"]] == REVISIONS
    assert [r["version"] for r in rec["revisions"]] == [2, 3]
    # S10-03: an unmet request is reported by the revision that makes it; no spurious regressions.
    first = rec["revisions"][0]
    assert first["unmet_request_reported"] is (not first["request_met"])
    assert not [v for v in rec["revisions"][1]["new_violations"] if v.startswith("regression:")]
    assert (out / rec["bundle"]["path"]).is_file()
    assert (out / rec["comparison"]).is_file()


def test_readiness_critique_pins_canonical_screenshot():
    critique = json.loads((HERE / "visual_critique.json").read_text("utf-8"))
    png = HERE / "demonstration" / f"{VISUAL_OPTION}-v1.png"
    assert critique["screenshot_hash"] == hashlib.sha256(png.read_bytes()).hexdigest()
