"""SiteService: ingest, confirm, report and the site gate, through one module (ADR 0028)."""

from __future__ import annotations

import sys

import pytest

from house_ai.cad.layers import load_layer_mapping
from house_ai.cli.exit_codes import EXIT_OK
from house_ai.cli.main import main
from house_ai.domain.provenance import ApprovalRequiresHuman, ArtifactKind, DataClassification
from house_ai.domain.units import LengthUnit
from house_ai.domain.workflow import EventType, Gate, WorkflowState
from house_ai.orchestration.site import SiteService
from house_ai.orchestration.site_ingestion import SiteConfirmation
from house_ai.orchestration.workflow import Workflow

from .conftest import AGENT, HUMAN, SURVEY_DXF, SURVEY_LAYERS

#: What keeps the synthetic survey out of the site gate before anyone confirms it.
SURVEY_BLOCKERS = [
    "drawing units are declared_in_source (m); a human must confirm them",
    "horizontal CRS is declared_in_source (source declares EPSG:25832); a human must confirm "
    "the EPSG code or confirm the survey is local-only",
    "elevation units are declared_in_source (m); a human must confirm them",
    "vertical datum is unknown; a human must confirm it or confirm elevations are relative to "
    "a local benchmark",
    "parcel boundary status is inference, not verified",
]
#: The same Blockers as (kind, code).
SURVEY_CODES = [
    ("site_fact", "source_units"),
    ("site_fact", "horizontal_crs"),
    ("site_fact", "elevation_units"),
    ("site_fact", "vertical_datum"),
    ("site_fact", "boundary_unverified"),
]


def _codes(blockers) -> list[tuple[str, str]]:
    return [(b.kind.value, b.code) for b in blockers]


@pytest.fixture
def survey_project(new_store):
    """A new project with the synthetic survey stored as a source; nothing ingested yet."""
    store = new_store("synthetic-survey")
    doc = store.add_source(SURVEY_DXF, HUMAN, classification=DataClassification.SYNTHETIC)
    return store, doc.id


def _transitions(store) -> list[tuple[str, str, str]]:
    return [
        (e.from_state.value, e.to_state.value, e.actor.id)
        for e in store.events()
        if e.type is EventType.TRANSITION
    ]


def test_ingest_from_a_new_project_starts_ingestion_and_stops_an_ambiguous_site(survey_project):
    store, source_id = survey_project
    sites = SiteService(store)

    result = sites.ingest(source_id, load_layer_mapping(SURVEY_LAYERS), AGENT)

    assert result.state is WorkflowState.SITE_NEEDS_CONFIRMATION
    assert _codes(result.blockers) == SURVEY_CODES
    assert [b.message for b in result.blockers] == SURVEY_BLOCKERS
    assert (result.site_ref.id, result.site_ref.version) == ("site", 1)
    assert [r.id for r in result.cad_refs] == ["cad-src-survey"]
    assert _transitions(store) == [
        ("NEW_PROJECT", "SITE_INGESTION", "claude-code"),
        ("SITE_INGESTION", "SITE_NEEDS_CONFIRMATION", "claude-code"),
    ]
    assert store.events()[-1].payload["blockers"] == SURVEY_BLOCKERS


def test_a_clear_site_stays_in_ingestion_with_no_blockers(new_store, site_doc):
    store = new_store()
    ref = store.put(ArtifactKind.SITE, "site", site_doc, AGENT)

    result = SiteService(store).assess(ref, AGENT)

    assert (result.state, result.blockers) == (WorkflowState.SITE_INGESTION, [])
    assert _transitions(store) == [("NEW_PROJECT", "SITE_INGESTION", "claude-code")]
    assert SiteService(store).blockers() == []


def test_reassessing_a_site_that_needs_confirmation_reports_and_moves_nothing(survey_project):
    store, source_id = survey_project
    sites = SiteService(store)
    first = sites.ingest(source_id, load_layer_mapping(SURVEY_LAYERS), AGENT)
    events = len(store.events())

    again = sites.assess(first.site_ref, AGENT)

    assert again.state is WorkflowState.SITE_NEEDS_CONFIRMATION
    assert _codes(again.blockers) == SURVEY_CODES
    assert len(store.events()) == events
    assert _codes(sites.blockers()) == SURVEY_CODES


def test_the_site_gate_is_blocked_before_any_site_exists(new_store):
    assert _codes(SiteService(new_store()).blockers()) == [("artifact", "no_site")]


# ------------------------------------------------------------------ confirmation

#: Everything the synthetic survey needs from a human (local-only keeps PROJ out of it).
FULL = SiteConfirmation(
    units=LengthUnit.METRE, elevation_units=LengthUnit.METRE, local_only=True,
    vertical_datum="synthetic benchmark", vertical_local=True, boundary_verified=True,
)  # fmt: skip


@pytest.fixture
def ingested(survey_project):
    """The synthetic survey ingested: SITE_NEEDS_CONFIRMATION, five Blockers."""
    store, source_id = survey_project
    SiteService(store).ingest(source_id, load_layer_mapping(SURVEY_LAYERS), AGENT)
    return store


def test_a_confirmation_that_clears_every_blocker_leaves_the_site_gate_approvable(ingested):
    store = ingested
    result = SiteService(store).confirm("site", HUMAN, FULL)

    assert (result.state, result.blockers) == (WorkflowState.SITE_INGESTION, [])
    assert (result.site_ref.id, result.site_ref.version) == ("site", 2)
    assert _transitions(store)[-1] == ("SITE_NEEDS_CONFIRMATION", "SITE_INGESTION", "owner")
    assert store.events()[-1].actor == HUMAN

    approval = Workflow(store).approve(Gate.SITE, result.site_ref, HUMAN, "owner approves")
    assert approval.artifact == result.site_ref
    assert Workflow(store).state is WorkflowState.SITE_APPROVED


def test_a_confirmation_that_leaves_a_blocker_open_moves_nothing(ingested):
    store = ingested
    events = len(store.events())

    result = SiteService(store).confirm("site", HUMAN, SiteConfirmation(units=LengthUnit.METRE))

    assert result.state is WorkflowState.SITE_NEEDS_CONFIRMATION
    assert _codes(result.blockers) == SURVEY_CODES[1:]
    assert not [e for e in store.events()[events:] if e.type is EventType.TRANSITION]


def test_an_agent_cannot_confirm_site_facts(ingested):
    store = ingested
    events = len(store.events())
    with pytest.raises(ApprovalRequiresHuman):
        SiteService(store).confirm("site", AGENT, FULL)
    assert len(store.events()) == events


def test_cli_site_confirm_goes_through_site_service(ingested, monkeypatch, capsys):
    """Argument wiring and exit code only; the rule is tested through SiteService above."""
    store = ingested
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "confirm site site")
    argv = ["site", "confirm", str(store.root), "--confirmer", "owner", "--units", "m",
            "--elevation-units", "m", "--local-only", "--vertical-datum", "synthetic benchmark",
            "--vertical-local", "--boundary-verified"]  # fmt: skip

    assert main(argv) == EXIT_OK
    assert Workflow(store).state is WorkflowState.SITE_INGESTION
    assert _transitions(store)[-1] == ("SITE_NEEDS_CONFIRMATION", "SITE_INGESTION", "owner")


# ---------------------------------------------------------------- review package


def test_the_site_review_package_is_written_for_a_site_version(ingested, tmp_path):
    store = ingested
    ref = store.latest(ArtifactKind.SITE, "site")
    out = tmp_path / "review"

    package = SiteService(store).write_review_package(ref, out)

    assert package.out == out
    assert sorted(p.name for p in package.files) == [
        "cad-import.json",
        "index.html",
        "site-report.json",
        "site-report.md",
        "site.json",
        "site.svg",
        "terrain.svg",
    ]
    assert sorted(p.name for p in out.iterdir()) == sorted(p.name for p in package.files)
    assert _codes(package.blockers) == SURVEY_CODES


def test_the_review_package_defaults_to_the_reviews_folder(ingested):
    store = ingested
    ref = store.latest(ArtifactKind.SITE, "site")

    package = SiteService(store).write_review_package(ref)

    assert package.out == store.root / "reviews" / "site-v1"
