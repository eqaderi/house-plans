"""Observe real outputs and compare them with synthetic ground truth.

PASS means a regression matched its expectation, including deliberately bad
plans. It does not mean a design is acceptable. Missing probes fail unless
explicitly declared as future work, which remains NOT_CHECKED.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from shapely.geometry import LineString
from shapely.ops import unary_union

from house_ai.domain.benchmark import AcceptanceCategory, BenchmarkFixture, ExpectedFinding
from house_ai.domain.epistemics import ClaimStatus
from house_ai.domain.evaluation import MetricClaim
from house_ai.domain.hillside import HillsideSettings
from house_ai.domain.integrity import check_model
from house_ai.domain.program import SpaceFunction
from house_ai.domain.site import Site
from house_ai.evaluation.base import EvaluationContext
from house_ai.evaluation.evaluators import REQUIRED
from house_ai.evaluation.usability import USABILITY_EVALUATORS
from house_ai.geospatial.hillside import triangle_quality
from house_ai.geospatial.terrain import build_tin
from house_ai.geospatial.validation import validate_site
from house_ai.storage.hashing import content_hash

from .probes import model_observations


@dataclass
class CheckResult:
    fixture: str
    check: str
    category: str
    target: str
    outcome: str
    expected: object
    observed: object
    detail: str
    method: str | None = None
    claim_status: str | None = None


def _claim(name: str, value, method: str, *, subjects=()) -> MetricClaim:
    return MetricClaim(
        metric=name,
        value=value,
        method=method,
        status=ClaimStatus.NOT_CHECKED if value is None else ClaimStatus.MEASURED,
        evaluator="BenchmarkInputProbe",
        evaluator_version="1",
        subject_ids=list(subjects),
    )


def _site_claims(site: Site) -> list[MetricClaim]:
    # Rebuild observations instead of trusting a saved successful TIN.
    tin = build_tin(site.terrain.spot_elevations, site.terrain.contours, site.terrain.breaklines)
    terrain = site.terrain.model_copy(update={"surface": tin.surface})
    report = validate_site(site.model_copy(update={"terrain": terrain}))
    zs = [s.z_m for s in terrain.spot_elevations]
    claims = [
        _claim(
            "breakline_input_count", len(site.terrain.breaklines), "canonical_mapped_3D_breaklines"
        ),
        _claim(
            "sliver_triangle_count",
            sum(
                "sliver" in t["triggers"] for t in triangle_quality(tin.surface, HillsideSettings())
            )
            if tin.surface
            else None,
            "hillside_triangle_quality:configured_sliver_trigger",
        ),
        _claim("parcel_area_m2", report.boundary.area_m2, "validate_site:polygon_area"),
        _claim(
            "envelope_area_m2",
            site.buildable_envelope.polygon.area_m2 if site.buildable_envelope else None,
            "polygon_area",
        ),
        _claim("survey_relief_m", max(zs) - min(zs) if zs else None, "spot_max_minus_min"),
        _claim(
            "parcel_mean_slope_pct",
            report.terrain.parcel_mean_slope_pct,
            "validate_site:parcel_clipped_triangle_area_weighting",
        ),
        _claim(
            "parcel_tin_area_m2",
            report.terrain.parcel_tin_area_m2,
            "validate_site:triangle_parcel_intersection",
        ),
        _claim("tin_present", tin.surface is not None, "build_tin"),
        _claim("elevation_conflicts", len(tin.conflicts), "build_tin"),
        _claim(
            "envelope_inside_parcel",
            site.boundary.to_shapely().covers(site.buildable_envelope.polygon.to_shapely())
            if site.boundary and site.buildable_envelope
            else None,
            "polygon_covers",
        ),
    ]
    if site.terrain.breaklines:
        edges = (
            unary_union(
                [
                    LineString([tin.surface.vertices[a][:2], tin.surface.vertices[b][:2]])
                    for tri in tin.surface.triangles
                    for a, b in zip(tri, (*tri[1:], tri[0]), strict=True)
                ]
            )
            if tin.surface
            else None
        )
        mapped = unary_union(
            [LineString([p[:2] for p in line.vertices]) for line in site.terrain.breaklines]
        )
        claims.append(
            _claim(
                "breakline_edge_coverage_m",
                edges.intersection(mapped).length if edges is not None else None,
                "build_tin:constrained_edge_union",
            )
        )
    for spot in site.terrain.spot_elevations:
        claims.append(_claim("spot_elevation_m", spot.z_m, "source_point", subjects=[spot.id]))
    for i, edge in enumerate(report.boundary.edges, 1):
        claims.append(
            _claim(
                "edge_grid_bearing_deg",
                edge.bearing_grid_deg,
                "validate_site:edge_bearing",
                subjects=[f"edge-{i}"],
            )
        )
    local = site.coordinates.local
    known = site.coordinates.horizontal_crs.epsg is not None
    angle = (
        local.project_north_deg - local.grid_to_true_north_deg
        if known and local and local.grid_to_true_north_deg is not None
        else None
    )
    claims.append(_claim("true_north_deg", angle, "confirmed_crs_and_meridian_convergence"))
    return claims


def _observations(fixture: BenchmarkFixture):
    metrics = {("site", "site"): _site_claims(fixture.site)}
    program_claims = []
    for item in fixture.program.space_requirements:
        for name, value in (
            ("quantity", item.quantity),
            ("accessible", item.accessible),
            ("target_area_m2", item.target_area_m2),
        ):
            program_claims.append(_claim(name, value, "program_requirement", subjects=[item.id]))
    program_claims.append(
        _claim(
            "garage_vehicle_capacity",
            sum(
                item.quantity
                for item in fixture.program.space_requirements
                if item.function is SpaceFunction.GARAGE
            ),
            "program_garage_bay_quantity",
        )
    )
    metrics[("program", "program")] = program_claims
    findings = {}
    for case in fixture.cases:
        for ref, doc in (
            (case.model.site_ref, fixture.site),
            (case.model.program_ref, fixture.program),
        ):
            if ref.id != doc.id or ref.version != 1 or ref.sha256 != content_hash(doc):
                raise ValueError(f"{case.id}: stale or mismatched benchmark input reference")
        ctx = EvaluationContext(case.model, fixture.site, fixture.program, None, False)
        results = [e.evaluate(ctx) for e in [*REQUIRED, *USABILITY_EVALUATORS]]
        failed = [r.run.name for r in results if r.run.status.value != "ran"]
        if failed:
            raise ValueError(f"evaluators did not run for {case.id}: {failed}")
        metrics[("evaluation", case.id)] = [m for r in results for m in r.metrics]
        wanted = {e.metric for e in fixture.expectations if e.target == case.id}
        metrics[("evaluation", case.id)].extend(
            MetricClaim(
                metric=name,
                value=value,
                method=method,
                status=status,
                subject_ids=subjects,
                evaluator="BenchmarkOutputProbe",
                evaluator_version="1",
            )
            for name, value, method, status, subjects in model_observations(fixture, case, wanted)
        )
        findings[("evaluation", case.id)] = [v for r in results for v in r.violations]
        findings[("integrity", case.id)] = check_model(case.model, fixture.site, fixture.program)
    return metrics, findings


def _matches(value, expected, tolerance: float) -> bool:
    if isinstance(value, bool) or isinstance(expected, bool):
        return type(value) is type(expected) and value == expected
    if isinstance(value, int | float) and isinstance(expected, int | float):
        return math.isclose(value, expected, rel_tol=0, abs_tol=tolerance)
    return type(value) is type(expected) and value == expected


def _check(fixture: BenchmarkFixture, e: ExpectedFinding, metrics, findings) -> CheckResult:
    result = CheckResult(
        fixture.id, e.id, e.category.value, e.target, "FAIL", e.value, None, "missing observation"
    )
    if e.source == "future":
        result.outcome = "NOT_CHECKED"
        result.detail = f"{e.pending_stage}: {e.basis}"
        return result
    if e.code:
        observed = findings.get((e.source, e.target))
        if observed is None:
            return result
        observed = [
            v for v in observed if v.code == e.code and set(e.subject_ids) <= set(v.subject_ids)
        ]
        statuses = {getattr(v, "status", ClaimStatus.MEASURED) for v in observed}
        result.observed = len(observed)
        result.method = f"{e.source}:finding_count:{e.code}"
        result.claim_status = e.status.value if statuses <= {e.status} else "mixed"
        ok = len(observed) == e.value and statuses <= {e.status}
    else:
        observed = [
            m
            for m in metrics.get((e.source, e.target), [])
            if m.metric == e.metric and set(e.subject_ids) <= set(m.subject_ids)
        ]
        if len(observed) != 1:
            result.detail = f"expected one observation for {e.metric}, got {len(observed)}"
            return result
        claim = observed[0]
        result.observed, result.method = claim.value, claim.method
        result.claim_status = claim.status.value
        ok = claim.status is e.status and _matches(claim.value, e.value, e.tolerance)
    result.outcome = "PASS" if ok else "FAIL"
    result.detail = e.basis if ok else f"expectation mismatch: {e.basis}"
    return result


def run_fixture(fixture: BenchmarkFixture) -> list[CheckResult]:
    metrics, findings = _observations(fixture)
    return [_check(fixture, e, metrics, findings) for e in fixture.expectations]


def category_table(results: list[CheckResult]) -> str:
    lines = ["| Category | PASS | FAIL | NOT_CHECKED |", "|---|---:|---:|---:|"]
    for category in AcceptanceCategory:
        rows = [r for r in results if r.category == category.value]
        counts = [
            sum(r.outcome == status for r in rows) for status in ("PASS", "FAIL", "NOT_CHECKED")
        ]
        lines.append(f"| {category.value} | {' | '.join(map(str, counts))} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fixtures", type=Path, help="generated fixture directory or one JSON file")
    parser.add_argument("--json", action="store_true", help="emit checks with methods and statuses")
    parser.add_argument("--details", action="store_true", help="show every individual comparison")
    parser.add_argument("--require-complete", action="store_true", help="also fail on NOT_CHECKED")
    args = parser.parse_args(argv)
    paths = sorted(args.fixtures.glob("*.json")) if args.fixtures.is_dir() else [args.fixtures]
    if not paths:
        parser.error("no benchmark fixtures found")
    results = []
    seen = set()
    try:
        for path in paths:
            fixture = BenchmarkFixture.model_validate_json(path.read_text(encoding="utf-8"))
            if fixture.id in seen:
                raise ValueError(f"duplicate fixture id: {fixture.id}")
            seen.add(fixture.id)
            results.extend(run_fixture(fixture))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"benchmark input/observation error: {exc}\n")
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        print(category_table(results))
        for r in results:
            if r.outcome != "PASS" or args.details:
                print(
                    f"{r.outcome}: {r.fixture}/{r.check}: expected={r.expected!r} "
                    f"observed={r.observed!r}; {r.detail}"
                )
    return int(
        any(
            r.outcome == "FAIL" or (args.require_complete and r.outcome == "NOT_CHECKED")
            for r in results
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
