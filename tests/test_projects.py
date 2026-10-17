"""Per-project folders and the owner's recorded statements (ADR 0009). Synthetic data only."""

from __future__ import annotations

import pytest

from house_ai.cli.main import main
from house_ai.domain.epistemics import ConfirmationStatus as C
from house_ai.domain.provenance import ArtifactKind as K
from house_ai.domain.provenance import DataClassification
from house_ai.domain.site import Site, site_verification_blockers
from house_ai.orchestration.site_ingestion import ingest_site
from house_ai.orchestration.statements import owner_statements, record_owner_statement
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore, StoreError
from house_ai.storage.projects import WORK_FOLDERS, create_project, list_projects
from house_ai.storage.projects import resolve_project_dir as resolve

from .conftest import AGENT, HUMAN


def test_a_new_project_is_a_store_with_its_working_folders(tmp_path):
    store = create_project("second-house", title="Second house", actor=HUMAN, base=tmp_path)
    root = tmp_path / "second-house"
    assert store.root == root and store.project_id == "second-house"
    assert all((root / f).is_dir() and not any((root / f).iterdir()) for f in WORK_FOLDERS)
    assert "surveys/" in (root / "README.md").read_text()
    assert store.verify() == []  # the working folders are not part of the record
    assert Workflow(store).state.value == "NEW_PROJECT"
    with pytest.raises(StoreError, match="not empty"):
        create_project("second-house", title="again", actor=HUMAN, base=tmp_path)
    with pytest.raises(StoreError, match="lowercase"):
        create_project("Second House", title="x", actor=HUMAN, base=tmp_path)


def test_a_project_is_found_by_name_or_by_path(tmp_path):
    create_project("a-house", title="A", actor=HUMAN, base=tmp_path)
    create_project("b-house", title="B", actor=HUMAN, base=tmp_path)
    (tmp_path / "not-a-project").mkdir()
    assert resolve("a-house", base=tmp_path) == tmp_path / "a-house"
    assert resolve(str(tmp_path / "b-house"), base=tmp_path) == tmp_path / "b-house"
    assert resolve("missing", base=tmp_path).name == "missing"  # left for the store to reject
    assert list_projects(tmp_path) == [tmp_path / "a-house", tmp_path / "b-house"]


def test_cli_creates_lists_and_opens_projects_by_name(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["project", "new", "my-test", "--actor", "human:owner"]) == 0
    assert main(["project", "list"]) == 0
    assert "my-test" in capsys.readouterr().out
    assert main(["project", "status", "my-test"]) == 0
    assert "NEW_PROJECT" in capsys.readouterr().out


def _ingested(new_store, make_survey, mapping_path):
    from house_ai.cad.layers import load_layer_mapping

    store = new_store("synthetic-survey")
    sid = store.add_source(make_survey(), HUMAN, classification=DataClassification.SYNTHETIC).id
    ingest_site(store, sid, load_layer_mapping(mapping_path), AGENT)
    return store


def test_a_recorded_statement_confirms_nothing(new_store, make_survey):
    from .conftest import SURVEY_LAYERS

    store = _ingested(new_store, make_survey, SURVEY_LAYERS)
    site_before = store.latest(K.SITE, "site")
    blockers = site_verification_blockers(store.get(site_before, Site))
    state = Workflow(store).state
    ref = record_owner_statement(
        store, subject="elevation_units", words="The elevation values are in metres.",
        stated_by="owner", channel="chat with agent:claude-code", actor=AGENT,
        pending_confirmation="house-ai site confirm <dir> --elevation-units m",
    )  # fmt: skip
    record_owner_statement(store, subject="relief", words="The drop is correct.",
                           stated_by="owner", channel="chat", actor=AGENT)  # fmt: skip
    statements = owner_statements(store)
    assert [s.id for s in statements] == ["stmt-001", "stmt-002"]
    assert statements[0].words == "The elevation values are in metres."
    assert statements[0].recorded_by == AGENT and statements[0].stated_by == "owner"
    assert ref.kind is K.OWNER_STATEMENTS
    # nothing else moved: same site version, same blockers, same state, units unconfirmed
    assert store.latest(K.SITE, "site") == site_before
    site = store.get(site_before, Site)
    assert site_verification_blockers(site) == blockers
    assert site.coordinates.elevation_units.status is not C.USER_CONFIRMED
    assert Workflow(store).state is state
    assert store.verify() == []


def test_site_report_shows_statements_and_defaults_to_the_reviews_folder(
    new_store, make_survey, capsys
):
    from .conftest import SURVEY_LAYERS

    store = _ingested(new_store, make_survey, SURVEY_LAYERS)
    record_owner_statement(store, subject="relief", words="My land is genuinely steep.",
                           stated_by="owner", channel="chat", actor=AGENT)  # fmt: skip
    assert main(["site", "report", str(store.root)]) == 0
    out = store.root / "reviews" / "site-v1"
    assert "My land is genuinely steep." in (out / "index.html").read_text()
    md = (out / "site-report.md").read_text()
    assert "recorded, not confirmed" in md and "My land is genuinely steep." in md
    assert ProjectStore(store.root).verify() == []
