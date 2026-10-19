"""S9-02: the end-to-end readiness demonstration runs on synthetic data and keeps its record.

Properties only: solver output differs between platforms (ISS-21, ISS-28), so no plan
geometry is compared byte for byte.
"""

from __future__ import annotations

import json

import yaml

from examples.readiness.run_demo import HERE, REVISIONS, run


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
    assert rec["site"]["relief_m"] > 10  # steep fixture, about 36 % fall

    # Concepts pin the approved inputs; critics ran and their findings are in the record.
    assert rec["concepts_pin_approved_inputs"] is True
    (two_wing,) = rec["concepts"]
    assert two_wing["option"] == "concept-two-wing" and two_wing["feasible"]
    assert two_wing["soft"] > 0 and "not_checked" in two_wing

    # S10-05, S10-06: stairs have measured walking lines and no unbuildable clashes.
    assert len(two_wing["stairs"]) >= 1
    assert all(s["walking_line"] is True for s in two_wing["stairs"])
    stair_defect_codes = {
        "stair_wall_clash",
        "stair_low_headroom",
        "floor_connection_height_mismatch",
        "stair_through_slab",
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

    # Visual review & S10-16 automated defect detectors.
    vr = rec["visual_review"]
    assert "vc-living-too-small" not in vr["ungrounded_ids"]
    assert {c["status"] for c in vr["claims"]} == {"ai_judgment"}
    assert vr["critique_made_on_this_rendering"] is True
    assert len(vr["detector_findings"]) > 0
    assert any(f["type"] == "overlapping_labels" for f in vr["detector_findings"])

    # Revisions keep the owner's words and ops and add versions 2 and 3.
    assert [(r["words"], r["ops"]) for r in rec["revisions"]] == REVISIONS
    assert [r["version"] for r in rec["revisions"]] == [2, 3]
    # S10-03: an unmet request is reported by the revision that makes it; no spurious regressions.
    first = rec["revisions"][0]
    assert first["unmet_request_reported"] is (not first["request_met"])
    assert not [v for v in rec["revisions"][1]["new_violations"] if v.startswith("regression:")]
    assert (out / rec["bundle"]["path"]).is_file()
    assert (out / rec["comparison"]).is_file()
