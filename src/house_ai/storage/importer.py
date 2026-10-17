"""Import a folder of working files (design_brief.yaml, plans/*.json, ...) into a store.

Used for the synthetic example projects and for hand-authored inputs. Every
file is validated against its schema before it is stored.
"""

from __future__ import annotations

from pathlib import Path

from house_ai.domain.provenance import Actor, ArtifactKind, ArtifactRef

from .hashing import load_document
from .project_store import ProjectStore, StoreError

#: Single files, in dependency order: (stem, kind, artifact id when content has none).
SINGLE_FILES: list[tuple[str, ArtifactKind, str | None]] = [
    ("site", ArtifactKind.SITE, None),
    ("design_brief", ArtifactKind.DESIGN_BRIEF, None),
    ("space_program", ArtifactKind.SPACE_PROGRAM, None),
    ("assumptions", ArtifactKind.ASSUMPTIONS, "assumptions"),
    ("open_questions", ArtifactKind.OPEN_QUESTIONS, "open-questions"),
    ("constraints", ArtifactKind.CONSTRAINT_SET, None),
]
#: Sub-folders holding many artifacts of one kind.
FOLDERS: list[tuple[str, ArtifactKind]] = [
    ("codepacks", ArtifactKind.CODEPACK),
    ("plans", ArtifactKind.PLAN),
]
_SUFFIXES = (".yaml", ".yml", ".json")


def _find(folder: Path, stem: str) -> Path | None:
    matches = [folder / f"{stem}{s}" for s in _SUFFIXES if (folder / f"{stem}{s}").is_file()]
    if len(matches) > 1:
        raise StoreError(f"{folder} has more than one {stem} file: {[m.name for m in matches]}")
    return matches[0] if matches else None


def _artifact_id(data: dict, fallback: str | None, path: Path) -> str:
    ident = data.get("option_id") or data.get("id") or fallback
    if not ident:
        raise StoreError(f"{path} has no id")
    return ident


def import_folder(store: ProjectStore, folder: Path, actor: Actor) -> list[ArtifactRef]:
    folder = Path(folder)
    refs: list[ArtifactRef] = []
    for stem, kind, fallback in SINGLE_FILES:
        path = _find(folder, stem)
        if path is not None:
            data = load_document(path)
            ref = store.put(
                kind,
                _artifact_id(data, fallback, path),
                data,
                actor,
                reason=f"imported {path.name}",
            )
            refs.append(ref)
    for sub, kind in FOLDERS:
        for path in sorted(p for p in (folder / sub).glob("*") if p.suffix in _SUFFIXES):
            data = load_document(path)
            ref = store.put(
                kind,
                _artifact_id(data, None, path),
                data,
                actor,
                reason=f"imported {sub}/{path.name}",
            )
            refs.append(ref)
    return refs
