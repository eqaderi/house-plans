#!/usr/bin/env python3
"""Local leak scan comparing tracked public files with private project values (S1-11).

Scans tests/, examples/, and docs/ for:
1. Private artifact and source hashes (and prefixes) from projects/my-house/
2. Exact private coordinates and spot elevations from private site/CAD data
3. Exact private site metrics (area, relief, frontage)

Outputs any violation without printing the secret value itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Directories to scan
SCAN_DIRS = ("tests", "examples", "docs")

# Excluded paths within scan directories (e.g. historical reviews under projects/ are not scanned)
IGNORE_EXTS = {".pyc", ".png", ".jpg", ".svg", ".dwg", ".dxf"}


def extract_private_signatures(project_dir: Path) -> dict[str, set[str]]:
    """Extract signatures of private values from a project directory."""
    signatures: dict[str, set[str]] = {
        "hashes": set(),
        "spot_elevations": set(),
        "site_metrics": set(),
        "coordinates": set(),
    }

    if not project_dir.is_dir():
        return signatures

    # 1. Event log hashes and artifact refs
    events_file = project_dir / "events.jsonl"
    if events_file.is_file():
        for line in events_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                h = ev.get("hash")
                if h and len(h) == 64:
                    signatures["hashes"].add(h.lower())
                payload = ev.get("payload", {})
                ref = payload.get("ref", {})
                ref_h = ref.get("sha256")
                if ref_h and len(ref_h) == 64:
                    signatures["hashes"].add(ref_h.lower())
            except Exception:
                pass

    # 2. Site artifact geometry and metrics
    site_artifacts = list(project_dir.glob("artifacts/site/*/*.json"))
    for sa in site_artifacts:
        try:
            data = json.loads(sa.read_text(encoding="utf-8"))
            # Spot elevations
            terrain = data.get("terrain", {})
            for pt in terrain.get("spot_elevations", []):
                # z coordinate as elevation
                z = pt.get("z")
                if z is not None and z > 100.0:  # real elevation in meters MASL
                    signatures["spot_elevations"].add(f"{z:.3f}")
                    signatures["spot_elevations"].add(f"{z:.1f}")
                x, y = pt.get("x"), pt.get("y")
                if x is not None and abs(x) > 1000.0:
                    signatures["coordinates"].add(f"{x:.3f}")
                if y is not None and abs(y) > 1000.0:
                    signatures["coordinates"].add(f"{y:.3f}")
        except Exception:
            pass

    # 3. Known exact private metrics
    signatures["site_metrics"].update({"599.95", "600.004", "12.437", "21.029"})

    return signatures


def scan_file(path: Path, signatures: dict[str, set[str]]) -> list[tuple[int, str]]:
    """Scan a single file for leaks. Returns list of (line_num, issue_description)."""
    findings: list[tuple[int, str]] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    # Check for hashes (full or 16+ chars prefix)
    for line_num, line in enumerate(content.splitlines(), start=1):
        line_lower = line.lower()
        for h in signatures["hashes"]:
            if len(h) >= 16 and (h in line_lower or h[:16] in line_lower):
                if h.startswith("00000000"):
                    continue
                findings.append(
                    (line_num, "detected private artifact/commit SHA-256 hash or prefix")
                )
                break

        # Check for spot elevations
        for elev in signatures["spot_elevations"]:
            if elev in line:
                findings.append((line_num, "detected private spot elevation value"))
                break

        # Check for site metrics in tests/ and examples/
        # (docs/ are allowed approximate figures per DEC-10, but exact figures are checked)
        is_doc = "docs" in path.parts
        for metric in signatures["site_metrics"]:
            if metric in line:
                if is_doc and metric in {"599.95", "600.004"}:
                    # If it's exact CAD area in docs
                    findings.append((line_num, "detected exact private site metric"))
                    break
                elif not is_doc:
                    findings.append((line_num, "detected private site metric"))
                    break

        # Check for coordinates
        for coord in signatures["coordinates"]:
            if coord in line:
                findings.append((line_num, "detected private coordinate value"))
                break

    return findings


def scan_repo(root: Path, project_name: str = "my-house") -> list[str]:
    """Scan all public files against private project values."""
    private_dir = root / "projects" / project_name
    signatures = extract_private_signatures(private_dir)
    problems: list[str] = []

    for dir_name in SCAN_DIRS:
        scan_path = root / dir_name
        if not scan_path.is_dir():
            continue
        for p in scan_path.rglob("*"):
            if not p.is_file() or p.suffix in IGNORE_EXTS:
                continue
            findings = scan_file(p, signatures)
            for line_num, desc in findings:
                rel = p.relative_to(root)
                problems.append(f"{rel}:{line_num}: {desc}")

    return problems


def main() -> int:
    problems = scan_repo(REPO_ROOT)
    if problems:
        print(f"LEAK SCAN FAILED: {len(problems)} leak(s) detected:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("Leak scan clean: no private project values found in tracked public files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
