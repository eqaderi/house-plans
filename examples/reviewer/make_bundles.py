"""Generate (or --check) synthetic demonstration bundles for the reviewer app.

Generates self-contained bundles for synthetic-bungalow and synthetic-hillside
using the read-only bundle exporter.

Usage:
    python examples/reviewer/make_bundles.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from house_ai.cli.human import renderer
from house_ai.cli.main import main
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind
from house_ai.domain.workflow import Gate, WorkflowState
from house_ai.orchestration.reviewer_bundle import build_reviewer_bundle
from house_ai.orchestration.workflow import Workflow
from house_ai.storage import ProjectStore

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BUNDLES_DIR = HERE / "bundles"

OWNER = Actor(kind=ActorKind.HUMAN, id="example-owner")
AGENT = Actor(kind=ActorKind.AGENT, id="agent:gemini")


def generate_bungalow_bundle(temp_root: Path) -> dict:
    """Build the demonstration bundle for synthetic-bungalow."""
    proj_dir = temp_root / "synthetic-bungalow"
    ret = main(
        [
            "example",
            "load",
            str(proj_dir),
            "--name",
            "synthetic-bungalow",
            "--project-id",
            "synthetic-bungalow",
            "--actor",
            "human:example-owner",
        ]
    )
    if ret != 0:
        raise RuntimeError("failed to load synthetic-bungalow")

    store = ProjectStore(proj_dir)
    wf = Workflow(store)
    wf.approve(Gate.SITE, store.latest(ArtifactKind.SITE, "site"), OWNER, "site verified")
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview complete")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "program ready")
    prog_ref = store.latest(ArtifactKind.SPACE_PROGRAM, "program")
    wf.approve(Gate.PROGRAM, prog_ref, OWNER, "program approved")

    # Load hand-authored plan-a if present
    plan_file = REPO / "examples" / "projects" / "synthetic-bungalow" / "plans" / "plan-a.yaml"
    if plan_file.exists():
        main(
            [
                "plan",
                "generate",
                str(proj_dir),
                "--strategy",
                "compact",
                "--seed",
                "0",
                "--actor",
                "agent:gemini",
            ]
        )

    bundle = build_reviewer_bundle(store, render=renderer(store.project_id))
    return bundle


def generate_hillside_bundle(temp_root: Path) -> dict:
    """Build the demonstration bundle for synthetic-hillside."""
    proj_dir = temp_root / "synthetic-hillside"
    ret = main(
        [
            "example",
            "load",
            str(proj_dir),
            "--name",
            "synthetic-hillside",
            "--project-id",
            "synthetic-hillside",
            "--actor",
            "human:example-owner",
        ]
    )
    if ret != 0:
        raise RuntimeError("failed to load synthetic-hillside")

    store = ProjectStore(proj_dir)
    wf = Workflow(store)
    wf.approve(Gate.SITE, store.latest(ArtifactKind.SITE, "site"), OWNER, "site verified")
    wf.transition(WorkflowState.INTERVIEWING, AGENT, "interview complete")
    wf.transition(WorkflowState.PROGRAM_REVIEW, AGENT, "program ready")
    prog_ref = store.latest(ArtifactKind.SPACE_PROGRAM, "program")
    wf.approve(Gate.PROGRAM, prog_ref, OWNER, "program approved")

    plan_options_dir = REPO / "examples" / "projects" / "synthetic-hillside" / "concepts"
    bundle = build_reviewer_bundle(
        store,
        render=renderer(store.project_id),
        plan_options_dir=plan_options_dir if plan_options_dir.exists() else None,
    )
    return bundle


def _mask_timestamps(data: dict) -> dict:
    """Recursively mask timestamps and generated hashes for deterministic checking."""
    if isinstance(data, dict):
        res = {}
        for k, v in data.items():
            if k in ("approved_at", "created_at", "at", "requested_at"):
                res[k] = "2026-10-17T12:00:00Z"
            elif k in ("sha256", "hash", "prev_hash"):
                res[k] = "0" * 64
            else:
                res[k] = _mask_timestamps(v)
        return res
    if isinstance(data, list):
        return [_mask_timestamps(x) for x in data]
    return data


def main_cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify bundles match without writing")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        bungalow_bundle = _mask_timestamps(generate_bungalow_bundle(tmp_path))
        hillside_bundle = _mask_timestamps(generate_hillside_bundle(tmp_path))

        targets = {
            BUNDLES_DIR / "synthetic-bungalow" / "bundle.json": bungalow_bundle,
            BUNDLES_DIR / "synthetic-hillside" / "bundle.json": hillside_bundle,
        }

        if args.check:
            for path, expected_data in targets.items():
                if not path.exists():
                    print(f"MISSING: {path}", file=sys.stderr)
                    return 1
                actual_data = _mask_timestamps(json.loads(path.read_text(encoding="utf-8")))
                if actual_data != expected_data:
                    print(f"DRIFT: {path} differs from generated bundle", file=sys.stderr)
                    return 1
            print("OK: all synthetic demonstration bundles up to date")
            return 0

        for path, data in targets.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"wrote {path}")
        return 0


if __name__ == "__main__":
    sys.exit(main_cli())
