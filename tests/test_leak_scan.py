"""Synthetic-only regression coverage for the private-data scanner (S1-11)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from house_ai.domain.coordinates import LocalCoordinateSystem
from house_ai.domain.provenance import ArtifactKind, DataClassification
from house_ai.domain.site import SpotElevation
from house_ai.storage import ProjectStore
from tools.leak_scan import LeakScanError, extract_private_signatures, scan_file, scan_repo

from .conftest import AGENT


@pytest.fixture
def private_repo(tmp_path, site):
    """Private classification, entirely fabricated coordinates and survey bytes."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    store = ProjectStore.init(
        tmp_path / "projects" / "second-house", project_id=site.project_id,
        name="Fabricated scanner fixture", classification=DataClassification.PRIVATE, actor=AGENT,
    )
    site = site.model_copy(deep=True)
    site.classification = DataClassification.PRIVATE
    site.coordinates.local = LocalCoordinateSystem(
        id="local", origin=(412345.625, 5432123.875, 62.125),
    )
    site.terrain.surface = None
    site.terrain.status = "surveyed_points"
    site.terrain.spot_elevations = [
        SpotElevation(id="s1", xy=(1.125, 2.875), z_m=-3.625),
        SpotElevation(id="s2", xy=(9.375, 15.625), z_m=7.875),
    ]
    source = tmp_path / "source.dxf"
    source.write_bytes(b"fabricated survey bytes for the scanner")
    doc = store.add_source(source, AGENT)
    store.put(ArtifactKind.SITE, site.id, site, AGENT)
    return tmp_path, store, doc


def _track(root: Path, path: str, text: str) -> Path:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "--", path], check=True)
    return target


def test_extracts_canonical_coordinates_low_and_negative_elevations_and_source_hash(private_repo):
    _, store, doc = private_repo
    signatures = extract_private_signatures(store.root)
    assert "-3.625" in signatures["spot_elevations"]
    assert "62.125" in signatures["spot_elevations"]
    assert "412346.75" in signatures["coordinates"]  # LOCAL to GRID
    assert "5432126.75" in signatures["coordinates"]
    assert doc.sha256 in signatures["hashes"]
    assert "11.5" in signatures["site_metrics"]


def test_scans_all_private_projects_and_text_export_formats(private_repo):
    root, _, doc = private_repo
    for filename in ("tests/leak.py", "examples/leak.svg", "docs/leak.md", "docs/leak.html"):
        _track(root, filename, f"elevation=-3.625 source={doc.sha256[:12]} relief=11.5\n")
    problems = scan_repo(root)
    assert len(problems) == 12
    assert all("-3.625" not in p and doc.sha256[:12] not in p for p in problems)
    assert {p.split(":")[0] for p in problems} == {
        "tests/leak.py", "examples/leak.svg", "docs/leak.md", "docs/leak.html",
    }


def test_detects_numeric_formats_without_substring_false_positives(private_repo):
    root, store, _ = private_repo
    path = root / "sample.txt"
    path.write_text("z=-3.625e0\nz=-3.6250\nz=13.6251\n")
    findings = scan_file(path, extract_private_signatures(store.root))
    assert [line for line, _ in findings] == [1, 2]


def test_docs_allow_explicit_approximations_but_reject_exact_metrics(private_repo):
    root, _, _ = private_repo
    _track(root, "docs/note.md", "relief ~11.5 m\nrelief 11.5 m\n")
    assert scan_repo(root) == ["docs/note.md:2: detected exact private site metric"]


def test_untracked_files_are_ignored(private_repo):
    root, _, _ = private_repo
    (root / "docs").mkdir()
    (root / "docs" / "local.md").write_text("elevation -3.625\n")
    assert scan_repo(root) == []


def test_missing_private_projects_is_valid_for_synthetic_only_checkout(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    _track(tmp_path, "tests/clean.py", "x = 1\n")
    assert scan_repo(tmp_path) == []


def test_corrupt_private_artifact_fails_closed_without_echoing_content(private_repo):
    _, store, _ = private_repo
    path = store.root / "artifacts" / "site" / "broken.json"
    path.write_text("private secret, invalid json")
    with pytest.raises(LeakScanError, match="cannot read private JSON") as error:
        extract_private_signatures(store.root)
    assert "private secret" not in str(error.value)


def test_public_and_synthetic_projects_are_not_private_signatures(private_repo):
    root, store, _ = private_repo
    manifest = store.root / "project.json"
    data = json.loads(manifest.read_text())
    data["classification"] = "synthetic"
    manifest.chmod(0o600)
    manifest.write_text(json.dumps(data))
    _track(root, "docs/example.md", "elevation -3.625\n")
    assert scan_repo(root) == []
