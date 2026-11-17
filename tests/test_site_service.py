"""SiteService: ingest, confirm, report and the site gate, through one module (ADR 0028)."""

from __future__ import annotations

import pytest

from house_ai.cad.layers import load_layer_mapping
from house_ai.domain.provenance import ArtifactKind, DataClassification
from house_ai.domain.workflow import EventType, WorkflowState
from house_ai.orchestration.site import SiteService

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
    assert result.blockers == SURVEY_BLOCKERS
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

    assert (again.state, again.blockers) == (WorkflowState.SITE_NEEDS_CONFIRMATION, SURVEY_BLOCKERS)
    assert len(store.events()) == events
    assert sites.blockers() == SURVEY_BLOCKERS


def test_the_site_gate_is_blocked_before_any_site_exists(new_store):
    assert SiteService(new_store()).blockers() == ["no site 'site' has been ingested yet"]
