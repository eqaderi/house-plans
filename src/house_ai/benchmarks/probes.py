"""Offline observations of rendered output, immutable revisions and hillside details.

These are software regressions on explicitly synthetic component cases, not an
architectural approval. Numerical expectations live in the benchmark fixtures.
"""

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from house_ai.domain.plan import ChangeRequest, PlanVersion
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, DataClassification
from house_ai.geospatial.hillside import hillside_report
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import content_hash

ACTOR = Actor(kind=ActorKind.SYSTEM, id="benchmark-probe")


def rendered_areas_match(plan, site):
    """Every canonical room area must appear exactly once in the SVG's room labels."""
    root = ET.fromstring(render_plan_svg(plan, site))
    observed = Counter(
        t.text for t in root.iter() if t.tag.endswith("text") and (t.text or "").endswith(" m²")
    )
    expected = Counter(f"{s.area_m2:.1f} m²" for s in plan.model.spaces)
    return observed == expected


def revision_observation(plan, project_id):
    """Store a semantic label revision; verify two versions, parent and verbatim request.

    Geometry remains the fixture's reference geometry. Solver revisions and request
    satisfaction are tested separately; this probe measures immutable history.
    """
    with TemporaryDirectory(prefix="house-ai-benchmark-") as directory:
        store = ProjectStore.init(
            Path(directory),
            project_id=project_id,
            name="Synthetic revision probe",
            classification=DataClassification.SYNTHETIC,
            actor=ACTOR,
            clock=lambda: plan.provenance.created_at,
        )
        before_hash = content_hash(plan)
        a = store.put(ArtifactKind.PLAN, plan.option_id, plan, ACTOR)
        words = "Please rename this option to Revised reference."
        request = ChangeRequest(
            id="cr-label",
            text=words,
            kind="modify",
            requested_by=ACTOR,
            requested_at=plan.provenance.created_at,
            base_versions=[a],
        )
        revised = plan.model_copy(
            update={"label": "Revised reference", "parent": a, "change_request": request}
        )
        b = store.put(ArtifactKind.PLAN, plan.option_id, revised, ACTOR)
        saved = store.get(b, PlanVersion)
        intact = (
            (a.version, b.version) == (1, 2)
            and store.latest(ArtifactKind.PLAN, plan.option_id) == b
            and saved.parent == a
            and saved.change_request.text == words
            and content_hash(store.get(a, PlanVersion)) == before_hash
            and content_hash(saved) != before_hash
            and store.verify() == []
        )
        return intact, b.version


def model_observations(fixture, case, wanted):
    plan = PlanVersion(
        option_id="benchmark-reference",
        label=case.id,
        strategy="hand_authored",
        model=case.model,
        provenance=fixture.program.provenance,
    )
    out = []
    # (name, value, method, status, subjects)
    if "svg_model_consistency" in wanted:
        out.append(
            (
                "svg_model_consistency",
                rendered_areas_match(plan, fixture.site),
                "render_plan_svg:xml_room_area_multiset",
                "measured",
                [],
            )
        )
    if "versioned_revision_integrity" in wanted:
        intact, count = revision_observation(plan, fixture.site.project_id)
        out.extend(
            [
                (
                    "versioned_revision_integrity",
                    intact,
                    "ProjectStore:parent_request_hashes_and_verify",
                    "measured",
                    [],
                ),
                ("revision_version_count", count, "ProjectStore:stored_versions", "measured", []),
            ]
        )
    if "terrace_max_floor_ground_delta_m" in wanted:
        report = hillside_report(case.model, fixture.site)
        for terrace in report["terraces"]:
            values = [
                e["max_floor_ground_delta_m"]
                for e in terrace["edge_ground_relationships"]
                if e["max_floor_ground_delta_m"] is not None
            ]
            out.append(
                (
                    "terrace_max_floor_ground_delta_m",
                    max(values) if values else None,
                    "hillside_report:edge_TIN_profiles",
                    "inferred" if values else "not_checked",
                    [terrace["space_id"]],
                )
            )
    return out
