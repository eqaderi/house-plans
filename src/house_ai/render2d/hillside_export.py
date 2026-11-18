"""Derived hillside review bundle shared by plan export and section CLI."""

import json
from pathlib import Path

from house_ai.geospatial.hillside import hillside_report
from house_ai.geospatial.sections import cut_section, facade_elevations, standard_sections

from .sections_svg import render_sections_svg


def export_hillside_views(model, site, folder: Path, requests=None, settings=None):
    folder.mkdir(parents=True, exist_ok=True)
    sections = [
        cut_section(model, site, r)
        for r in (requests if requests is not None else standard_sections(model, site))
    ]
    elevations = facade_elevations(model, site)
    report = hillside_report(model, site, settings)
    for name, data in (("sections", sections), ("elevations", elevations), ("hillside", report)):
        (folder / f"{name}.json").write_text(
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    (folder / "sections.svg").write_text(render_sections_svg(sections), encoding="utf-8")
    (folder / "elevations.svg").write_text(render_sections_svg(elevations), encoding="utf-8")
    risks = [
        "# Unresolved engineering risks",
        "",
        "Concept exploration; no professional "
        "verification. Geometric earthworks are not construction estimates.",
        "",
    ]
    for risk in report["risks"]:
        subjects = ", ".join(risk["subject_ids"]) or "whole plan option"
        risks.append(
            f"- **{risk['discipline']} — needs professional** ({subjects}): {risk['trigger']}"
        )
    (folder / "engineering-risks.md").write_text("\n".join(risks) + "\n", encoding="utf-8")
    return report
