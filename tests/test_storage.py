"""Project store: write-once artifacts, immutable sources, hash-chained events."""

from __future__ import annotations

import json
import os
import stat

import pytest
import yaml
from pydantic import ValidationError

from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import ArtifactKind, DataClassification
from house_ai.domain.site import Site
from house_ai.domain.workflow import EventType, WorkflowEvent
from house_ai.storage import ImmutableArtifactError, ProjectStore, StoreError, StoreIntegrityError
from house_ai.storage.hashing import content_hash, load_document
from house_ai.storage.importer import import_folder

from .conftest import AGENT, HUMAN

K = ArtifactKind


def _make_writable(path):
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def test_init_creates_layout_and_first_event(store):
    assert (store.root / "project.json").is_file()
    assert (store.root / "source").is_dir()
    events = store.events()
    assert [e.type for e in events] == [EventType.PROJECT_CREATED]
    assert events[0].prev_hash is None
    assert store.verify() == []


def test_init_refuses_a_non_empty_directory(tmp_path):
    (tmp_path / "something.txt").write_text("x")
    with pytest.raises(StoreError, match="not empty"):
        ProjectStore.init(
            tmp_path,
            project_id="p",
            name="p",
            classification=DataClassification.PRIVATE,
            actor=HUMAN,
        )


def test_opening_a_non_project_fails(tmp_path):
    with pytest.raises(StoreError, match="not a house-ai project"):
        ProjectStore(tmp_path)


def test_put_and_get_round_trip(store, site):
    ref = store.put(K.SITE, "site", site, AGENT)
    assert (ref.kind, ref.id, ref.version) == (K.SITE, "site", 1)
    assert ref.sha256 == content_hash(site)
    loaded = store.get(ref, Site)
    assert loaded == site


def test_artifact_files_are_read_only(store, site):
    ref = store.put(K.SITE, "site", site, AGENT)
    path = store.root / "artifacts" / "site" / "site" / "v0001.json"
    assert stat.S_IMODE(path.stat().st_mode) & 0o222 == 0
    assert store.latest(K.SITE, "site") == ref


def test_a_change_is_a_new_version_never_an_overwrite(store, site):
    v1 = store.put(K.SITE, "site", site, AGENT)
    changed = site.model_copy(update={"name": "Renamed plot"})
    v2 = store.put(K.SITE, "site", changed, AGENT)
    assert v2.version == 2 and v2.sha256 != v1.sha256
    assert store.get(v1).name == site.name
    assert store.get(v2).name == "Renamed plot"
    assert store.latest(K.SITE, "site") == v2


def test_identical_content_is_not_stored_twice(store, site):
    v1 = store.put(K.SITE, "site", site, AGENT)
    again = store.put(K.SITE, "site", site.model_dump(mode="json"), AGENT)
    assert again == v1
    assert len(store.refs(K.SITE)) == 1


def test_existing_version_file_cannot_be_overwritten(store, site):
    store.put(K.SITE, "site", site, AGENT)
    from house_ai.storage.project_store import _write_once

    with pytest.raises(ImmutableArtifactError):
        _write_once(store.root / "artifacts" / "site" / "site" / "v0001.json", "{}")


def test_invalid_content_is_refused_and_nothing_is_written(store, site_doc):
    site_doc["coordinates"]["horizontal_crs"] = {"status": "unknown", "epsg": 32632}
    with pytest.raises(ValidationError):
        store.put(K.SITE, "site", site_doc, AGENT)
    assert store.refs() == []
    assert not (store.root / "artifacts" / "site").exists()


def test_artifact_id_must_match_content(store, site):
    with pytest.raises(StoreError, match="stored as 'other'"):
        store.put(K.SITE, "other", site, AGENT)


def test_artifact_must_belong_to_this_project(new_store, site):
    other = new_store(project_id="another-project")
    with pytest.raises(StoreError, match="belongs to project"):
        other.put(K.SITE, "site", site, AGENT)


def test_yaml_and_json_inputs_hash_identically(store, example_dir, tmp_path):
    """Hashes come from the validated model, not from file bytes or formatting."""
    from_yaml = load_document(example_dir / "site.yaml")
    json_path = tmp_path / "site.json"
    full = Site.model_validate(from_yaml).model_dump(mode="json")  # defaults spelled out
    json_path.write_text(json.dumps(full, indent=4))
    assert content_hash(Site.model_validate(from_yaml)) == content_hash(
        Site.model_validate(load_document(json_path))
    )


def test_serialisation_round_trips(plan, site):
    for model in (plan, site):
        cls = type(model)
        assert cls.model_validate_json(model.model_dump_json()) == model
        assert (
            cls.model_validate(yaml.safe_load(yaml.safe_dump(model.model_dump(mode="json"))))
            == model
        )


def test_get_detects_a_tampered_artifact(store, site):
    ref = store.put(K.SITE, "site", site, AGENT)
    path = store.root / "artifacts" / "site" / "site" / "v0001.json"
    _make_writable(path)
    data = json.loads(path.read_text())
    data["name"] = "tampered"
    path.write_text(json.dumps(data))
    with pytest.raises(StoreIntegrityError, match="does not match its recorded hash"):
        store.get(ref)
    assert any("does not match" in p for p in store.verify())


def test_verify_detects_an_unregistered_file(store):
    stray = store.root / "artifacts" / "site" / "ghost" / "v0001.json"
    stray.parent.mkdir(parents=True)
    stray.write_text("{}")
    assert any("not registered" in p for p in store.verify())


def test_verify_detects_an_edited_event(store, site):
    store.put(K.SITE, "site", site, AGENT)
    log = store.root / "events.jsonl"
    lines = log.read_text().splitlines()
    event = json.loads(lines[1])
    event["actor"]["id"] = "someone-else"
    lines[1] = json.dumps(event)
    log.write_text("\n".join(lines) + "\n")
    assert any("modified after it was written" in p for p in store.verify())


def test_verify_detects_a_deleted_event(store, site, plan):
    store.put(K.SITE, "site", site, AGENT)
    store.put(K.PLAN, "plan-a", plan, AGENT)
    log = store.root / "events.jsonl"
    lines = log.read_text().splitlines()
    del lines[1]
    log.write_text("\n".join(lines) + "\n")
    problems = store.verify()
    assert any("does not chain" in p for p in problems)


def test_event_chain_links_hashes(store, site):
    store.put(K.SITE, "site", site, AGENT)
    first, second = store.events()
    assert second.prev_hash == first.hash
    assert second.seq == 2
    assert isinstance(second, WorkflowEvent)
    assert second.payload["ref"]["sha256"] == content_hash(site)


def test_add_source_preserves_bytes_and_hash(store, tmp_path):
    original = tmp_path / "Survey Plot 7.DXF"
    original.write_bytes(b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n")
    doc = store.add_source(original, HUMAN)
    stored = store.root / doc.stored_path
    assert stored.read_bytes() == original.read_bytes()
    assert doc.original_filename == "Survey Plot 7.DXF"
    assert doc.classification is DataClassification.PRIVATE  # private by default
    assert stat.S_IMODE(stored.stat().st_mode) & 0o222 == 0
    assert doc.id == "src-survey-plot-7"
    # Adding the same bytes again is idempotent.
    assert store.add_source(original, HUMAN) == doc
    assert len(store.refs(K.SOURCE_DOCUMENT)) == 1
    assert store.verify() == []


def test_verify_detects_a_modified_source(store, tmp_path):
    original = tmp_path / "survey.dxf"
    original.write_text("original")
    doc = store.add_source(original, HUMAN)
    stored = store.root / doc.stored_path
    _make_writable(stored)
    stored.write_text("edited")
    assert any("was modified" in p for p in store.verify())


def test_import_folder_loads_the_golden_example(store, example_dir):
    refs = import_folder(store, example_dir, AGENT)
    kinds = [r.kind for r in refs]
    assert kinds == [
        K.SITE,
        K.DESIGN_BRIEF,
        K.SPACE_PROGRAM,
        K.ASSUMPTIONS,
        K.OPEN_QUESTIONS,
        K.CONSTRAINT_SET,
        K.CODEPACK,
        K.PLAN,
    ]
    plan = store.get(store.latest(K.PLAN, "plan-a"), PlanVersion)
    site_ref = store.latest(K.SITE, "site")
    # The golden plan pins exactly the site and program versions it was drawn on.
    assert plan.model.site_ref == site_ref
    assert plan.model.program_ref == store.latest(K.SPACE_PROGRAM, "program")
    assert store.verify() == []


def test_a_crash_orphan_does_not_block_the_artifact_id(store, site):
    """A version file written just before a crash, with no event, is skipped and reported."""
    orphan = store.root / "artifacts" / "site" / "site" / "v0001.json"
    orphan.parent.mkdir(parents=True)
    orphan.write_text("{}")
    ref = store.put(K.SITE, "site", site, AGENT)
    assert ref.version == 2
    assert store.get(ref) == site
    assert any("v0001.json is not registered" in p for p in store.verify())
