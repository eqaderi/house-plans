"""The CLI is a thin layer; these tests drive it through main(argv)."""

from __future__ import annotations

import io
import json
import subprocess
import sys

import pytest

from house_ai.cli.main import main
from house_ai.domain.workflow import WorkflowState
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore

from .conftest import EXAMPLE, REPO


class FakeTty(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.fixture
def loaded(tmp_path, capsys):
    project = tmp_path / "proj"
    assert main(["example", "load", str(project), "--actor", "agent:claude-code"]) == 0
    capsys.readouterr()
    return project


def test_schemas_check_passes_on_the_committed_schemas(capsys):
    assert main(["schemas", "check"]) == 0
    assert "up to date" in capsys.readouterr().out


def test_schemas_check_fails_on_drift(tmp_path, capsys):
    assert main(["schemas", "export", "--out", str(tmp_path)]) == 0
    (tmp_path / "site.schema.json").write_text("{}")
    assert main(["schemas", "check", "--out", str(tmp_path)]) == 1
    assert "site" in capsys.readouterr().err


def test_validate_reports_integrity(capsys):
    args = [
        "validate",
        "plan",
        str(EXAMPLE / "plans" / "plan-a.json"),
        "--site",
        str(EXAMPLE / "site.yaml"),
    ]
    assert main(args) == 0
    assert "integrity: 0 error(s), 0 warning(s)" in capsys.readouterr().out


def test_validate_rejects_bad_files(tmp_path, capsys):
    bad = tmp_path / "site.yaml"
    bad.write_text((EXAMPLE / "site.yaml").read_text().replace("boundary_status", "boundry"))
    assert main(["validate", "site", str(bad)]) == 1
    assert "INVALID" in capsys.readouterr().err


def test_example_load_stops_in_site_ingestion_for_a_human(loaded):
    wf = Workflow(ProjectStore(loaded))
    assert wf.state is WorkflowState.SITE_INGESTION
    assert wf.status().approvals == {}


def test_status_json(loaded, capsys):
    assert main(["project", "status", str(loaded), "--json"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["state"] == "SITE_INGESTION"
    assert info["gate_available"] == "site"
    assert info["latest_artifacts"]["plan"][0]["id"] == "plan-a"


def test_verify(loaded, capsys):
    assert main(["project", "verify", str(loaded)]) == 0
    assert "intact" in capsys.readouterr().out


def test_approve_refuses_without_a_terminal(loaded, capsys, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("approve site site v1\n"))
    rc = main(["workflow", "approve", str(loaded), "site", "--id", "site", "--approver", "owner"])
    assert rc == 2
    assert "interactive terminal" in capsys.readouterr().err
    assert Workflow(ProjectStore(loaded)).state is WorkflowState.SITE_INGESTION


def test_approve_refuses_a_wrong_confirmation(loaded, capsys, monkeypatch):
    monkeypatch.setattr(sys, "stdin", FakeTty("yes\n"))
    rc = main(["workflow", "approve", str(loaded), "site", "--id", "site", "--approver", "owner"])
    assert rc == 1
    assert Workflow(ProjectStore(loaded)).state is WorkflowState.SITE_INGESTION


def test_approve_with_typed_confirmation(loaded, capsys, monkeypatch):
    monkeypatch.setattr(sys, "stdin", FakeTty("approve site site v1\n"))
    rc = main(["workflow", "approve", str(loaded), "site", "--id", "site", "--approver", "owner"])
    assert rc == 0
    status = Workflow(ProjectStore(loaded)).status()
    assert status.state is WorkflowState.SITE_APPROVED
    assert status.approvals["site"].approved_by.id == "owner"


def test_transition_into_a_gate_fails_cleanly(loaded, capsys):
    rc = main(
        [
            "workflow",
            "transition",
            str(loaded),
            "SITE_APPROVED",
            "--actor",
            "agent:claude-code",
            "--reason",
            "skip",
        ]
    )
    assert rc == 1
    assert "behind an approval gate" in capsys.readouterr().err


def test_artifact_put_and_list(loaded, capsys):
    rc = main(
        [
            "artifact",
            "put",
            str(loaded),
            "assumptions",
            str(EXAMPLE / "assumptions.yaml"),
            "--id",
            "assumptions",
            "--actor",
            "agent:claude-code",
        ]
    )
    assert rc == 0
    assert "assumptions/assumptions v1" in capsys.readouterr().out  # unchanged content
    assert main(["artifact", "list", str(loaded), "--kind", "plan"]) == 0
    assert "plan/plan-a v1" in capsys.readouterr().out
    assert main(["artifact", "check", str(loaded), "plan-a"]) == 0


def test_source_add(loaded, tmp_path, capsys):
    survey = tmp_path / "survey.dxf"
    survey.write_text("0\nEOF\n")
    rc = main(["source", "add", str(loaded), str(survey), "--actor", "human:owner"])
    assert rc == 0
    assert "src-survey" in capsys.readouterr().out


def test_console_script_runs_as_a_subprocess():
    result = subprocess.run(
        [sys.executable, "-m", "house_ai.cli.main", "schemas", "check"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    assert result.returncode == 0, result.stderr
