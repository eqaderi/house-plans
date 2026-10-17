"""Per-project folders under ``projects/`` (ADR 0009).

A project folder is a :class:`ProjectStore` (project.json, events.jsonl, source/,
artifacts/) with working folders around it::

    surveys/   the survey files as received from the owner
    site/      layer mapping and survey inspection for this project
    reviews/   generated review packages (site drawings, reports)
    design/    interview exports, space program, later plans and 3D output

Only the store files carry project state; the working folders hold inputs and
derived documents. Nothing project-specific lives in the application code.
"""

from __future__ import annotations

from pathlib import Path

from house_ai.domain.provenance import Actor, DataClassification

from .project_store import ProjectStore, StoreError, _slug

PROJECTS_DIR = Path("projects")
WORK_FOLDERS = ("surveys", "site", "reviews", "design")

_README = """# {name}

Project `{project_id}`, created by `house-ai project new`.

| Folder | What goes there |
|---|---|
| `surveys/` | the survey files (DWG/DXF) exactly as you received them |
| `site/` | the layer mapping (`layers.yaml`) and the survey inspection |
| `reviews/` | review packages generated from the site and the plans |
| `design/` | interview exports, the space program, later plans and 3D output |
| `project.json`, `events.jsonl`, `source/`, `artifacts/` | the project record (`house-ai` only) |

## What this project needs from you

1. **The survey.** Copy the files into `surveys/`, then:

   ```bash
   house-ai site inspect {root}/surveys/* --out {root}/site/inspection
   house-ai source add {project_id} {root}/surveys/<file>.dwg --actor human:<you>
   ```

   Write `site/layers.yaml` from the inspection (see `examples/surveys/synthetic/layers.yaml`).
2. **Your requirements.** Run the interview (Milestone C) in your own terminal:
   `house-ai interview run {project_id} --owner <you>`.

`house-ai project status {project_id}` shows where the project stands.
"""


def resolve_project_dir(text: str, base: Path = PROJECTS_DIR) -> Path:
    """A project folder from a path, or from a bare name under ``projects/``."""
    path = Path(text)
    if (path / "project.json").is_file() or len(path.parts) > 1:
        return path
    named = base / text
    return named if (named / "project.json").is_file() else path


def list_projects(base: Path = PROJECTS_DIR) -> list[Path]:
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if (p / "project.json").is_file())


def create_project(
    name: str,
    *,
    title: str,
    actor: Actor,
    base: Path = PROJECTS_DIR,
    classification: DataClassification = DataClassification.PRIVATE,
) -> ProjectStore:
    """Create ``projects/<name>/``: a new store plus its empty working folders."""
    project_id = _slug(name)
    if project_id != name:
        raise StoreError(f"use a lowercase project name such as {project_id!r}, not {name!r}")
    root = base / name
    store = ProjectStore.init(
        root, project_id=project_id, name=title, classification=classification, actor=actor
    )
    for folder in WORK_FOLDERS:
        (root / folder).mkdir()
    (root / "README.md").write_text(
        _README.format(name=title, project_id=project_id, root=root.as_posix()), encoding="utf-8"
    )
    return store
