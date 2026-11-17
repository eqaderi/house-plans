"""Generate synthetic demonstration artifacts for visual plan review (Stage S5, Task S5-12).

Creates:
1. before.svg and before.png (seeded visual defect on synthetic-hillside concept)
2. visual_critique.json (grounded critique citing canonical element IDs)
3. revision_ops.json (structured revision operations)
4. after.svg and after.png (a hand-edited illustration of the requested change)
5. README.md (demonstration documentation and replay guide)

Fix verification is not part of this demonstration: it is what `plan revise` reports, from
the Evaluations of the parent Plan version and the new one (ADR 0033).
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from house_ai.domain.model import Opening, OpeningKind
from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import Actor, Provenance
from house_ai.domain.revision_ops import RevisionOp, RevisionOpsFile
from house_ai.domain.site import Site
from house_ai.domain.visual_critique import VisualClaim, VisualCritiqueFile
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.render2d.rasterize import rasterize_svg_to_png
from house_ai.storage.hashing import load_document

DEMO_DIR = Path(__file__).resolve().parent
REPO = DEMO_DIR.parent.parent.parent
HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"


def generate_demonstration_artifacts() -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load synthetic-hillside baseline
    site_dict = copy.deepcopy(load_document(HILLSIDE / "site.yaml"))
    site = Site.model_validate(site_dict)

    plan_dict = copy.deepcopy(
        load_document(HILLSIDE / "concepts" / "concept-split-walkout" / "exploratory" / "plan.json")
    )
    base_plan = PlanVersion.model_validate(plan_dict)

    # 2. Seed visual defect on synthetic-hillside: window hosted on retaining wall
    # Retaining wall w-down-300-001 abuts underground hillside earth
    retaining_wall_id = "w-down-300-001"
    exterior_wall_id = "w-down-300-013"

    plan_v1 = base_plan.model_copy(deep=True)
    seeded_opening = Opening(
        id="win-buried-001",
        host_wall_id=retaining_wall_id,  # Buried on retaining wall
        kind=OpeningKind.WINDOW,
        offset_m=1.0,
        width_m=1.2,
        height_m=1.2,
        connects=("sp-study", "exterior"),
    )
    plan_v1.model.openings.append(seeded_opening)

    # Render and rasterize before
    before_svg = render_plan_svg(plan_v1, site, version=1)
    before_svg_path = DEMO_DIR / "before.svg"
    before_svg_path.write_text(before_svg, encoding="utf-8")

    before_png_path = DEMO_DIR / "before.png"
    rasterize_svg_to_png(before_svg, before_png_path, width=800, height=600)
    before_bytes = before_png_path.read_bytes()
    before_hash = hashlib.sha256(before_bytes).hexdigest()

    # 3. Create grounded visual critique record
    critique = VisualCritiqueFile(
        project="synthetic-hillside",
        option="concept-split-walkout",
        plan_version=1,
        author="agent:gemini",
        created_at="2026-10-18T02:47:52.497484Z",
        screenshot_hash=before_hash,
        claims=[
            VisualClaim(
                id="vc-001",
                element_ids=["win-buried-001", retaining_wall_id],
                claim_text=(
                    f"Window win-buried-001 is hosted on retaining wall {retaining_wall_id} "
                    "which directly abuts earthwork cut, preventing daylight access and egress."
                ),
                # Let the study move so its window leaves the buried wall: an operation
                # `plan revise` can run (ADR 0030).
                suggested_ops=[RevisionOp(op_type="rethink", target="sp-study-1")],
            )
        ],
    )
    critique_path = DEMO_DIR / "visual_critique.json"
    critique_path.write_text(
        json.dumps(critique.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # 4. Save revision operations file
    ops_file = RevisionOpsFile(
        project="synthetic-hillside",
        option="concept-split-walkout",
        plan_version=1,
        verbatim_request="Relocate window win-buried-001 off retaining wall to exterior wall",
        author="agent:gemini",
        created_at="2026-10-18T02:47:52.498118Z",
        operations=critique.claims[0].suggested_ops,
    )
    ops_path = DEMO_DIR / "revision_ops.json"
    ops_path.write_text(
        json.dumps(ops_file.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # 5. Create revised plan_v2 (After) resolving the defect
    plan_v2 = plan_v1.model_copy(deep=True)
    actor = Actor(kind="agent", id="agent:gemini")
    plan_v2.provenance = Provenance(
        created_at="2026-10-18T00:00:00Z",
        created_by=actor,
        method="visual_review_revision",
    )
    # Move window from retaining wall to daylight exterior wall
    for op in plan_v2.model.openings:
        if op.id == "win-buried-001":
            op.host_wall_id = exterior_wall_id

    after_svg = render_plan_svg(plan_v2, site, version=2)
    after_svg_path = DEMO_DIR / "after.svg"
    after_svg_path.write_text(after_svg, encoding="utf-8")

    after_png_path = DEMO_DIR / "after.png"
    rasterize_svg_to_png(after_svg, after_png_path, width=800, height=600)

    # 6. Write README.md documentation
    readme_path = DEMO_DIR / "README.md"
    readme_content = f"""# Synthetic Hillside Visual Plan Review Demonstration

Demonstration of Stage S5 agent visual review loop on `synthetic-hillside`.

## Overview
This demonstration shows a grounded visual critique and the revision it asks for:
1. **Seeded defect**: a window `win-buried-001` hosted on retaining wall
   `{retaining_wall_id}`.
2. **Grounded Critique**: Generation of `visual_critique.json` citing only canonical element
   IDs (`win-buried-001`, `{retaining_wall_id}`).
3. **Structured Revision**: Proposed `revision_ops.json` with a Revision operation
   `plan revise` can run (`rethink:sp-study-1`).
4. **After**: a hand-edited illustration that moves the window to `{exterior_wall_id}`.
   It is not a Plan version and nothing verifies it.

Fix verification is what `plan revise` reports: for the ids the request targeted, the
Findings of the parent's Evaluation that disappeared, that remain and that are new
(`findings` in `plan revise --json`, ADR 0033). The hand-edited states here would not pass
it: the seeded window is 1.2 m wide at 1.0 m along a 2.0 m wall and opens onto `sp-study`,
which the plan does not have, and the interior wall it is moved to is already filled by an
opening.

## Artifacts
- **Before**: [`before.svg`](before.svg), [`before.png`](before.png) (SHA-256: `{before_hash}`)
- **Critique Record**: [`visual_critique.json`](visual_critique.json)
- **Revision Operations**: [`revision_ops.json`](revision_ops.json)
- **After**: [`after.svg`](after.svg), [`after.png`](after.png)

## Replay Instructions

To regenerate all demonstration artifacts, run:
```bash
.venv/bin/python examples/reviewer/demonstration/make_demonstration.py
```

To run the tests on these artifacts:
```bash
.venv/bin/python -m pytest tests/test_visual_demonstration.py
```
"""
    readme_path.write_text(readme_content, encoding="utf-8")
    print(f"Generated demonstration artifacts in {DEMO_DIR}")


if __name__ == "__main__":
    generate_demonstration_artifacts()
