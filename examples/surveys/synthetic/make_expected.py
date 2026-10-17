"""Regenerate (or --check) the committed example outputs of the synthetic survey.

Runs the real Milestone B pipeline in a temporary project store with a fixed
clock: inspection -> ingestion -> report and SVG, then a scripted confirmation
by the SYNTHETIC actor ``human:example-owner`` (as the tests do) -> report and
SVG again. Outputs go to ``expected/``. Reports are rendered without the site
version hash, and the inspection's parser version is masked, so the snapshots
do not change when a dependency is upgraded.

Usage: python examples/surveys/synthetic/make_expected.py [--check]
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from house_ai.cad.layers import load_layer_mapping
from house_ai.domain.provenance import Actor, ActorKind, DataClassification
from house_ai.domain.site import Site
from house_ai.domain.units import LengthUnit
from house_ai.geospatial.validation import report_markdown, validate_site
from house_ai.orchestration.site_ingestion import SiteConfirmation, confirm_site, ingest_site
from house_ai.orchestration.survey_inspection import inspect_files, inspection_markdown
from house_ai.render2d.site_svg import render_site_svg
from house_ai.storage import ProjectStore

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
EXPECTED = HERE / "expected"
AGENT = Actor(kind=ActorKind.AGENT, id="example-pipeline")
OWNER = Actor(kind=ActorKind.HUMAN, id="example-owner", display_name="synthetic example owner")


class _Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.now += timedelta(seconds=1)
        return self.now


def outputs() -> dict[str, str]:
    survey, layers = HERE / "survey.dxf", HERE / "layers.yaml"
    mapping = load_layer_mapping(layers)
    out: dict[str, str] = {}
    inspection = inspect_files([survey], mapping)
    # Machine- and version-independent snapshot: relative path, parser version masked.
    inspection.files[0].path = survey.relative_to(REPO).as_posix()
    inspection.files[0].parser_version = "<version>"
    out["inspection.md"] = inspection_markdown(inspection)
    with tempfile.TemporaryDirectory() as tmp:
        store = ProjectStore.init(
            Path(tmp) / "project",
            project_id="synthetic-survey",
            name="Synthetic survey (not a real parcel)",
            classification=DataClassification.SYNTHETIC,
            actor=OWNER,
            clock=_Clock(),
        )
        doc = store.add_source(survey, OWNER, classification=DataClassification.SYNTHETIC)
        result = ingest_site(store, doc.id, mapping, AGENT)
        for label, ref in [("unconfirmed", result.site_ref)]:
            site = store.get(ref, Site)
            report = validate_site(site)
            out[f"{label}/site-report.md"] = report_markdown(report)
            out[f"{label}/site.svg"] = render_site_svg(site, report)
        confirmed = confirm_site(
            store,
            "site",
            OWNER,
            SiteConfirmation(
                units=LengthUnit.METRE,
                elevation_units=LengthUnit.METRE,
                epsg=25832,
                vertical_datum="DHHN2016",
                vertical_epsg=7837,
                boundary_verified=True,
            ),
        )
        site = store.get(confirmed, Site)
        report = validate_site(site)
        out["confirmed/site-report.md"] = report_markdown(report)
        out["confirmed/site.svg"] = render_site_svg(site, report)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if expected/ is stale")
    args = parser.parse_args(argv)
    stale = []
    for name, text in outputs().items():
        path = EXPECTED / name
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path}")
    if stale:
        print("stale: " + ", ".join(stale) + "; run make_expected.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
