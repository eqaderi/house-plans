"""Milestone D: dimensioned plan SVG, and the synthetic hillside fixture stays current."""

from __future__ import annotations

import copy
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

from house_ai.domain.plan import PlanVersion
from house_ai.domain.site import Site
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.storage.hashing import load_document

from .conftest import EXAMPLE, REPO

GOLDEN = EXAMPLE / "expected" / "plan-a.svg"
HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"


def _plan_a() -> tuple[PlanVersion, Site]:
    plan = PlanVersion.model_validate(copy.deepcopy(load_document(EXAMPLE / "plans/plan-a.json")))
    site = Site.model_validate(copy.deepcopy(load_document(EXAMPLE / "site.yaml")))
    return plan, site


def test_plan_a_svg_matches_the_golden_file():
    """Regenerate with HOUSE_AI_UPDATE_GOLDEN=1 after an intended renderer change."""
    plan, site = _plan_a()
    svg = render_plan_svg(plan, site, version=1)
    if os.environ.get("HOUSE_AI_UPDATE_GOLDEN"):
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(svg, encoding="utf-8")
    assert svg == GOLDEN.read_text(encoding="utf-8")
    assert svg == render_plan_svg(plan, site, version=1)  # deterministic


def test_plan_svg_draws_what_the_model_contains():
    plan, site = _plan_a()
    svg = render_plan_svg(plan, site, version=1)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    texts = [t.text or "" for t in root.iter() if t.tag.endswith("text")]
    for s in plan.model.spaces:
        # Small rooms are labelled with the first word of their name.
        assert any(t and s.name.startswith(t) for t in texts), s.name
        assert f"{s.area_m2:.1f} m²" in texts
    assert "12.00 m" in svg and "10.00 m" in svg  # overall dimensions of the 12 x 10 m bar
    assert 'id="level-l0"' in svg and 'id="section"' in svg
    assert "GN" in svg  # the synthetic CRS is confirmed, so grid north is drawn
    assert "not engineered" in svg


def test_north_is_not_drawn_when_the_crs_is_not_confirmed():
    plan, site = _plan_a()
    coords = site.coordinates.model_copy(
        update={
            "horizontal_crs": site.coordinates.horizontal_crs.model_copy(
                update={"status": "unknown", "epsg": None, "name": None}
            )
        }
    )
    svg = render_plan_svg(plan, site.model_copy(update={"coordinates": coords}))
    assert "north not established" in svg and ">GN<" not in svg


def test_hillside_fixture_is_current():
    script = HILLSIDE / "make_fixture.py"
    res = subprocess.run([sys.executable, str(script), "--check"], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr


def test_hillside_program_came_from_the_program_builder():
    asm = load_document(HILLSIDE / "assumptions.yaml")
    assert any(a["id"] == "asm-hillside-engineering" for a in asm["assumptions"])
    program = load_document(HILLSIDE / "space_program.yaml")
    assert program["provenance"]["method"] == "program_from_brief"
    assert program["levels"] == 2
