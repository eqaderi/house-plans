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
    assert rec["site"]["blockers"] == []
    assert rec["site"]["relief_m"] > 10  # steep fixture, about 36 % fall

    # Concepts pin the approved inputs; critics ran and their findings are in the record.
    assert rec["concepts_pin_approved_inputs"] is True
    (two_wing,) = rec["concepts"]
    assert two_wing["option"] == "concept-two-wing" and two_wing["feasible"]
    assert two_wing["soft"] > 0 and "not_checked" in two_wing
    assert rec["proposal"][0]["option"] == "concept-open-plan-prop-day-up-night-down"

    # Visual review: program and space IDs in the critique exist in the plan.
    vr = rec["visual_review"]
    assert "vc-living-too-small" not in vr["ungrounded_ids"]
    assert {c["status"] for c in vr["claims"]} == {"ai_judgment"}

    # Revisions keep the owner's words and ops and add versions 2 and 3.
    assert [(r["words"], r["ops"]) for r in rec["revisions"]] == REVISIONS
    assert [r["version"] for r in rec["revisions"]] == [2, 3]
    # S10-03: an unmet request is reported by the revision that makes it.
    first = rec["revisions"][0]
    assert first["unmet_request_reported"] is (not first["request_met"])
    assert not [v for v in rec["revisions"][1]["new_violations"] if v.startswith("regression:")]
    assert (out / rec["bundle"]["path"]).is_file()
    assert (out / rec["comparison"]).is_file()
