#!/usr/bin/env python3
"""Compare tracked text exports with private project signatures (S1-11).

Private inputs are read only by this explicit tool, never by the test suite.
Diagnostics identify files and categories without echoing private values.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from house_ai.domain.provenance import DataClassification
from house_ai.domain.site import Site
from house_ai.domain.units import from_metres
from house_ai.geospatial.validation import validate_site

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("tests", "examples", "docs")
# SVG/DXF/HTML are text exports and must be scanned too.
IGNORE_EXTS = {".pyc", ".png", ".jpg", ".jpeg", ".pdf", ".dwg"}
CATEGORIES = ("hashes", "spot_elevations", "site_metrics", "coordinates")
NUMBER = re.compile(r"(?<![\w.])[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?![\w.])")
HASH = re.compile(r"\b[0-9a-fA-F]{12,64}\b")


class LeakScanError(ValueError):
    """An input could not be scanned; never silently report a clean scan."""


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (OSError, ValueError) as exc:
        raise LeakScanError(f"cannot read private JSON: {path.name}") from exc


def _hashes(value: object, out: set[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"hash", "prev_hash", "sha256", "converted_sha256"}:
                if isinstance(item, str) and re.fullmatch(r"[0-9a-fA-F]{64}", item):
                    out.add(item.lower())
            _hashes(item, out)
    elif isinstance(value, list):
        for item in value:
            _hashes(item, out)


def _number(value: float, out: set[str], *, rounded: bool = True) -> None:
    # Whole small numbers are not distinguishing private signatures (e.g. local
    # origin 0 or a 20 m edge). Compare precise decimals and large grid integers.
    if abs(value - round(value)) < 1e-9 and abs(value) < 1000:
        return
    out.add(str(value))
    approximate = round(value, 3)
    if rounded and (approximate != int(approximate) or abs(approximate) >= 1000):
        out.add(f"{approximate:.3f}")


def _site_signatures(site: Site, signatures: dict[str, set[str]]) -> None:
    points = [(s.xy[0], s.xy[1], s.z_m) for s in site.terrain.spot_elevations]
    points += [(x, y, c.z_m) for c in site.terrain.contours for x, y in c.line.points]
    if site.terrain.surface:
        points += site.terrain.surface.vertices
    if site.boundary:
        points += [
            (x, y, 0.0) for ring in [site.boundary.outer, *site.boundary.holes] for x, y in ring
        ]
    local = site.coordinates.local
    if local:
        points += [local.origin]
        # Preserve both LOCAL and GRID signatures; never guess the units or CRS.
        grid_points = [local.local_to_grid(p) for p in points[:-1]]
        points += grid_points
        horizontal = site.coordinates.source_units.unit
        vertical = site.coordinates.elevation_units.unit
        if horizontal and vertical:
            points += [
                (from_metres(x, horizontal), from_metres(y, horizontal), from_metres(z, vertical))
                for x, y, z in grid_points
            ]
    for x, y, z in points:
        _number(x, signatures["coordinates"], rounded=abs(x) >= 1000)
        _number(y, signatures["coordinates"], rounded=abs(y) >= 1000)
        _number(z, signatures["spot_elevations"])
    report = validate_site(site)
    for value in (report.boundary.area_m2, report.frontage.length_m):
        if value is not None:
            _number(value, signatures["site_metrics"])
    zs = [s.z_m for s in site.terrain.spot_elevations]
    if zs:
        _number(max(zs) - min(zs), signatures["site_metrics"])
    # Covers parcel-clipped relief and conversation metrics as used by the CLI.
    from house_ai.domain.provenance import ArtifactKind, ArtifactRef
    from house_ai.orchestration.site_context import site_context_for

    ref = ArtifactRef(kind=ArtifactKind.SITE, id=site.id, version=1, sha256="0" * 64)
    context = site_context_for(site, ref, None)
    for key in ("parcel_area_m2", "relief_m", "frontage_m"):
        value = getattr(context, key)
        if value is not None:
            _number(value, signatures["site_metrics"])


def extract_private_signatures(project_dir: Path) -> dict[str, set[str]]:
    """Read canonical artifacts; there are no owner-specific constants in code."""
    signatures: dict[str, set[str]] = {key: set() for key in CATEGORIES}
    if not project_dir.is_dir():
        return signatures
    for path in sorted((project_dir / "artifacts").rglob("*.json")):
        data = _read_json(path)
        _hashes(data, signatures["hashes"])
        if path.relative_to(project_dir / "artifacts").parts[0] == "site":
            try:
                site = Site.model_validate(data)
                _site_signatures(site, signatures)
            except Exception as exc:
                raise LeakScanError(f"cannot inspect private site: {path.name}") from exc
    log = project_dir / "events.jsonl"
    if log.exists():
        try:
            for line in log.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    _hashes(json.loads(line), signatures["hashes"])
        except (OSError, ValueError) as exc:
            raise LeakScanError("cannot read private event log") from exc
    return signatures


def scan_file(path: Path, signatures: dict[str, set[str]]) -> list[tuple[int, str]]:
    """Compare numeric tokens and hash prefixes, returning redacted diagnostics."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise LeakScanError(f"cannot scan text file: {path.name}") from exc
    numeric = {
        key: {Decimal(value) for value in signatures[key]}
        for key in CATEGORIES if key != "hashes"
    }
    descriptions = {
        "spot_elevations": "detected private spot elevation value",
        "site_metrics": "detected exact private site metric",
        "coordinates": "detected private coordinate value",
    }
    findings: list[tuple[int, str]] = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        if any(
            h.startswith(token.lower())
            for token in HASH.findall(line) for h in signatures["hashes"]
        ):
            findings.append((line_num, "detected private SHA-256 hash or prefix"))
        values = set()
        for match in NUMBER.finditer(line):
            # DEC-10 permits explicitly approximate figures in historical docs.
            if "docs" in path.parts and line[:match.start()].rstrip().endswith(("~", "≈")):
                continue
            try:
                values.add(Decimal(match.group()))
            except InvalidOperation:
                continue
        for key, private in numeric.items():
            if values & private:
                findings.append((line_num, descriptions[key]))
    return findings


def scan_repo(root: Path, project_name: str | None = None) -> list[str]:
    """Scan tracked exports against every private project, or a selected project."""
    signatures: dict[str, set[str]] = {key: set() for key in CATEGORIES}
    projects = root / "projects"
    candidates = [projects / project_name] if project_name else sorted(projects.glob("*"))
    for project in candidates:
        manifest = project / "project.json"
        if not manifest.exists():
            continue
        if _read_json(manifest).get("classification") != DataClassification.PRIVATE.value:
            continue
        for key, values in extract_private_signatures(project).items():
            signatures[key].update(values)
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", *SCAN_DIRS],
        capture_output=True, check=True,
    )
    problems = []
    for rel in sorted(result.stdout.decode().split("\0")):
        if not rel:
            continue
        path = root / rel
        if not path.is_file() or path.suffix.lower() in IGNORE_EXTS:
            continue
        for line_num, desc in scan_file(path, signatures):
            problems.append(f"{rel}:{line_num}: {desc}")
    return problems


def main() -> int:
    try:
        problems = scan_repo(REPO_ROOT)
    except (LeakScanError, subprocess.CalledProcessError) as exc:
        print(f"LEAK SCAN FAILED: {exc}", file=sys.stderr)
        return 1
    if problems:
        print(f"LEAK SCAN FAILED: {len(problems)} leak(s) detected:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("Leak scan clean: no private project values found in tracked public files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
