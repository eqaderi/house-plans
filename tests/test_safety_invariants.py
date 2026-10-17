"""Safety and integrity invariant tests (S1-08).

Documents and asserts the 8 safety and integrity invariants of the system:
1. INV-CONSENT: Private homeowner data requires explicit human consent before external transmission.
2. INV-SOURCE-IMMUTABLE: Raw source documents stored under source/ are immutable and read-only.
3. INV-ARTIFACT-WRITE-ONCE: Versioned artifacts are write-once and cannot be overwritten.
4. INV-HASH-CHAIN: Event log is hash-chained; modifying any event breaks verification.
5. INV-HEAD-ANCHOR: Event log tail truncation is detected via head anchor.
6. INV-HUMAN-GATES: Approval gates, reopening, site confirmation, and program rejection
   require an interactive human terminal.
7. INV-SCHEMA-DRIFT: Canonical domain models match JSON Schema export with drift detection.
8. INV-PRIVATE-DATA-ISOLATION: Tests run on synthetic data only, without reading projects/my-house.
"""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

from house_ai.cli.main import EXIT_USAGE, main
from house_ai.domain.provenance import Actor, ActorKind, DataClassification
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.registry import stale_schemas
from house_ai.providers.base import (
    DataFlowPolicy,
    PrivateDataFlowError,
    ProviderRequest,
    check_data_flow,
)
from house_ai.storage import ProjectStore

HUMAN = Actor(kind=ActorKind.HUMAN, id="invariant-owner")
AGENT = Actor(kind=ActorKind.AGENT, id="claude-code")


def test_inv_consent_policy_blocks_unauthorized_external_transmission():
    """INV-CONSENT: DataFlowPolicy blocks sending private data to providers without consent."""
    policy = DataFlowPolicy(allowed_private_providers=frozenset())
    req = ProviderRequest(
        system="system", prompt="private prompt", classification=DataClassification.PRIVATE
    )
    with pytest.raises(PrivateDataFlowError, match="without explicit consent"):
        check_data_flow("anthropic", req, policy)

    # Allowed when consent given by a human
    policy_with_consent = DataFlowPolicy(
        allowed_private_providers=frozenset({"anthropic"}), granted_by=HUMAN
    )
    check_data_flow("anthropic", req, policy_with_consent)


def test_inv_source_immutable_and_read_only(tmp_path: Path):
    """INV-SOURCE-IMMUTABLE: Raw source documents stored in source/ are read-only and immutable."""
    store = ProjectStore.init(
        tmp_path / "proj", project_id="p1", name="P1", classification="synthetic", actor=HUMAN
    )
    src_file = tmp_path / "survey.dxf"
    src_file.write_bytes(b"survey raw bytes")
    doc = store.add_source(src_file, HUMAN)
    stored = store.root / doc.stored_path
    mode = stat.S_IMODE(stored.stat().st_mode)
    assert mode & 0o222 == 0  # not writable


def test_inv_artifact_write_once(tmp_path: Path):
    """INV-ARTIFACT-WRITE-ONCE: Artifact files cannot be overwritten."""
    store = ProjectStore.init(
        tmp_path / "proj", project_id="p1", name="P1", classification="synthetic", actor=HUMAN
    )
    from house_ai.domain.site import Site

    from .conftest import example_doc
    site = Site.model_validate(example_doc("site.yaml"))
    site.project_id = "p1"
    ref = store.put(K.SITE, "site", site, HUMAN)
    art_path = store._artifact_path(ref.kind, ref.id, ref.version)

    # Direct overwrite must be prevented by permissions
    with pytest.raises(PermissionError):
        art_path.write_text("tamper", encoding="utf-8")


def test_inv_hash_chain_tamper_detected(tmp_path: Path):
    """INV-HASH-CHAIN: Tampering with any event in the event log breaks verification."""
    store = ProjectStore.init(
        tmp_path / "proj", project_id="p1", name="P1", classification="synthetic", actor=HUMAN
    )
    from house_ai.domain.site import Site

    from .conftest import example_doc
    site = Site.model_validate(example_doc("site.yaml"))
    site.project_id = "p1"
    store.put(K.SITE, "site", site, HUMAN)

    log = store.root / "events.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[1])
    event["actor"]["id"] = "tampered"
    lines[1] = json.dumps(event)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    problems = store.verify()
    assert any("modified after it was written" in p for p in problems)


def test_inv_head_anchor_detects_log_truncation(tmp_path: Path):
    """INV-HEAD-ANCHOR: Deleting events from the tail of events.jsonl fails verification."""
    store = ProjectStore.init(
        tmp_path / "proj", project_id="p1", name="P1", classification="synthetic", actor=HUMAN
    )
    from house_ai.domain.site import Site

    from .conftest import example_doc
    site = Site.model_validate(example_doc("site.yaml"))
    site.project_id = "p1"
    store.put(K.SITE, "site", site, HUMAN)

    log = store.root / "events.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    del lines[-1]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    problems = store.verify()
    assert any("tail does not match head anchor" in p for p in problems)


def test_inv_human_gates_enforced_in_non_tty(tmp_path: Path, monkeypatch):
    """INV-HUMAN-GATES: Non-interactive execution of human-only commands is refused."""
    store = ProjectStore.init(
        tmp_path / "proj", project_id="p1", name="P1", classification="synthetic", actor=HUMAN
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert (
        main(["workflow", "reopen", str(store.root), "site", "--reason", "t", "--actor", "human:o"])
        == EXIT_USAGE
    )
    assert (
        main(["workflow", "approve", str(store.root), "site", "--id", "site", "--approver", "o"])
        == EXIT_USAGE
    )
    assert (
        main(
            ["site", "confirm", str(store.root), "--id", "site", "--confirmer", "o", "--units", "m"]
        )
        == EXIT_USAGE
    )


def test_inv_schemas_up_to_date():
    """INV-SCHEMA-DRIFT: All committed JSON schemas match current Pydantic models."""
    schemas_dir = Path(__file__).resolve().parents[1] / "schemas"
    stale = stale_schemas(schemas_dir)
    assert stale == []


def test_inv_private_data_isolation(tmp_path: Path):
    """INV-PRIVATE-DATA-ISOLATION: Tests run safely without projects/my-house present."""
    from tools.leak_scan import REPO_ROOT, scan_repo
    leaks = scan_repo(REPO_ROOT)
    assert leaks == []
