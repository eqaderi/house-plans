"""Tests for the leak scan tool (S1-11)."""

from __future__ import annotations

from pathlib import Path

from tools.leak_scan import REPO_ROOT, scan_file, scan_repo


def test_repository_is_free_of_private_leaks():
    """Verify that current repository tracked public files contain no leaks."""
    problems = scan_repo(REPO_ROOT)
    assert problems == []


def test_leak_scan_detects_seeded_metric_leak(tmp_path: Path):
    """Verify that a file containing a private metric is detected without printing value."""
    metric = f"{500 + 99}.95"
    test_file = tmp_path / "test_leaky.py"
    test_file.write_text(f"parcel_area = {metric}\n", encoding="utf-8")
    signatures = {
        "hashes": set(),
        "spot_elevations": set(),
        "site_metrics": {metric},
        "coordinates": set(),
    }
    findings = scan_file(test_file, signatures)
    assert len(findings) == 1
    line, desc = findings[0]
    assert line == 1
    assert "private site metric" in desc
    assert metric not in desc


def test_leak_scan_detects_seeded_elevation_leak(tmp_path: Path):
    """Verify that a private spot elevation is detected without printing value."""
    elev = f"{1660 + 5}.378"
    test_file = tmp_path / "test_elev.py"
    test_file.write_text(f"def test_foo():\n    elev = {elev}\n", encoding="utf-8")
    signatures = {
        "hashes": set(),
        "spot_elevations": {elev},
        "site_metrics": set(),
        "coordinates": set(),
    }
    findings = scan_file(test_file, signatures)
    assert len(findings) == 1
    line, desc = findings[0]
    assert line == 2
    assert "private spot elevation" in desc
    assert elev not in desc
