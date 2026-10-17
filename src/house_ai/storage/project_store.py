"""File-based project store (ADR 0003).

Layout of a project directory::

    project.json                      manifest (identity only, read-only)
    events.jsonl                      append-only, hash-chained event log
    source/<sha12>-<filename>         original inputs, byte-for-byte, read-only
    artifacts/<kind>/<id>/v0001.json  write-once artifact versions, read-only

The event log is the single source of truth for what exists and for the
workflow state: every artifact version is registered by an
``artifact_written`` event carrying its content hash, and the workflow
state is replayed from the events. Nothing is ever overwritten; a change is
a new version.
"""

from __future__ import annotations

import fcntl
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from house_ai.domain.base import utc_now
from house_ai.domain.provenance import (
    Actor,
    ArtifactKind,
    ArtifactRef,
    DataClassification,
    SourceDocument,
)
from house_ai.domain.registry import ARTIFACT_MODELS
from house_ai.domain.workflow import EventType, ProjectManifest, WorkflowEvent, WorkflowState

from .hashing import canonical_json, content_hash, file_sha256, pretty_json, sha256_text

Clock = Callable[[], datetime]
M = TypeVar("M", bound=BaseModel)

READ_ONLY = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH


class StoreError(Exception):
    pass


class ImmutableArtifactError(StoreError):
    """Raised on any attempt to overwrite something that already exists."""


class StoreIntegrityError(StoreError):
    """The store on disk does not match its own event log."""


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug or "file")[:48].rstrip("-")


def _write_once(path: Path, text: str) -> None:
    """Atomically create ``path`` with ``text``; refuse if it already exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, READ_ONLY)
        try:
            os.link(tmp, path)  # fails if path exists: no overwrite, ever
        except FileExistsError as exc:
            raise ImmutableArtifactError(f"{path} already exists and is immutable") from exc
    finally:
        os.unlink(tmp)


def _event_hash(event_fields: dict[str, Any]) -> str:
    return sha256_text(canonical_json(event_fields))


class ProjectStore:
    def __init__(self, root: Path, clock: Clock = utc_now) -> None:
        self.root = Path(root)
        self.clock = clock
        if not (self.root / "project.json").is_file():
            raise StoreError(f"{self.root} is not a house-ai project (no project.json)")

    # ------------------------------------------------------------------ setup

    @classmethod
    def init(
        cls,
        root: Path,
        *,
        project_id: str,
        name: str,
        classification: DataClassification,
        actor: Actor,
        description: str | None = None,
        clock: Clock = utc_now,
    ) -> ProjectStore:
        root = Path(root)
        if root.exists() and any(root.iterdir()):
            raise StoreError(f"{root} exists and is not empty")
        manifest = ProjectManifest(
            id=project_id,
            name=name,
            description=description,
            classification=classification,
            created_at=clock(),
            created_by=actor,
        )
        root.mkdir(parents=True, exist_ok=True)
        for sub in ("source", "artifacts"):
            (root / sub).mkdir()
        _write_once(root / "project.json", pretty_json(manifest))
        (root / "events.jsonl").touch()
        store = cls(root, clock=clock)
        store.append_event(
            EventType.PROJECT_CREATED,
            actor,
            to_state=WorkflowState.NEW_PROJECT,
            payload={"project_id": project_id},
        )
        return store

    def manifest(self) -> ProjectManifest:
        return ProjectManifest.model_validate_json((self.root / "project.json").read_text())

    @property
    def project_id(self) -> str:
        return self.manifest().id

    # ----------------------------------------------------------------- events

    @contextmanager
    def _locked(self) -> Iterator[None]:
        with (self.root / ".lock").open("a") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def events(self) -> list[WorkflowEvent]:
        out: list[WorkflowEvent] = []
        lines = (self.root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                out.append(WorkflowEvent.model_validate_json(line))
            except ValidationError as exc:
                raise StoreIntegrityError(f"events.jsonl line {lineno} is invalid: {exc}") from exc
        return out

    def append_event(
        self,
        type_: EventType,
        actor: Actor,
        *,
        from_state: WorkflowState | None = None,
        to_state: WorkflowState | None = None,
        reason: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        with self._locked():
            return self._append_event_unlocked(
                type_,
                actor,
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                payload=payload or {},
            )

    def _append_event_unlocked(
        self,
        type_: EventType,
        actor: Actor,
        *,
        from_state: WorkflowState | None,
        to_state: WorkflowState | None,
        reason: str | None,
        payload: dict[str, Any],
    ) -> WorkflowEvent:
        existing = self.events()
        prev = existing[-1] if existing else None
        fields = {
            "seq": (prev.seq + 1) if prev else 1,
            "at": self.clock(),
            "actor": actor,
            "type": type_,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "payload": payload,
            "prev_hash": prev.hash if prev else None,
        }
        draft = WorkflowEvent.model_validate({**fields, "hash": "0" * 64})
        body = draft.model_dump(mode="json", exclude={"hash"})
        event = draft.model_copy(update={"hash": _event_hash(body)})
        with (self.root / "events.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(canonical_json(event) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return event

    # ---------------------------------------------------------------- sources

    def add_source(
        self,
        path: Path,
        actor: Actor,
        *,
        classification: DataClassification = DataClassification.PRIVATE,
        source_id: str | None = None,
        media_type: str | None = None,
    ) -> SourceDocument:
        """Copy an original input into source/ unchanged and register it.

        Adding the same bytes again returns the existing record.
        """
        path = Path(path)
        digest = file_sha256(path)
        with self._locked():
            existing_ids: set[str] = set()
            for ref in self.refs(ArtifactKind.SOURCE_DOCUMENT):
                doc = self.get(ref, SourceDocument)
                if doc.sha256 == digest:
                    return doc
                existing_ids.add(doc.id)
            stored = Path("source") / f"{digest[:12]}-{_slug(path.stem)}{path.suffix.lower()}"
            target = self.root / stored
            if target.exists():
                if file_sha256(target) != digest:
                    raise ImmutableArtifactError(f"{target} already exists with different content")
            else:
                shutil.copyfile(path, target)
            os.chmod(target, READ_ONLY)
            if file_sha256(target) != digest:
                raise StoreIntegrityError(f"copy of {path} does not match the original")
            default_id = f"src-{_slug(path.stem)}"
            if source_id is not None:
                resolved_id = source_id
            elif default_id not in existing_ids:
                resolved_id = default_id
            else:
                resolved_id = f"{default_id}-{digest[:8]}"
            doc = SourceDocument(
                id=resolved_id,
                original_filename=path.name,
                sha256=digest,
                size_bytes=target.stat().st_size,
                media_type=media_type,
                stored_path=stored.as_posix(),
                classification=classification,
                imported_at=self.clock(),
                imported_by=actor,
            )
            self._put_unlocked(ArtifactKind.SOURCE_DOCUMENT, doc.id, doc, actor, reason=None)
            return doc

    # -------------------------------------------------------------- artifacts

    def _artifact_path(self, kind: ArtifactKind, artifact_id: str, version: int) -> Path:
        return self.root / "artifacts" / kind.value / artifact_id / f"v{version:04d}.json"

    def refs(
        self, kind: ArtifactKind | None = None, artifact_id: str | None = None
    ) -> list[ArtifactRef]:
        """All registered artifact versions, oldest first."""
        out = []
        for event in self.events():
            if event.type is EventType.ARTIFACT_WRITTEN:
                ref = ArtifactRef.model_validate(event.payload["ref"])
                if (kind is None or ref.kind is kind) and (
                    artifact_id is None or ref.id == artifact_id
                ):
                    out.append(ref)
        return out

    def latest(self, kind: ArtifactKind, artifact_id: str) -> ArtifactRef | None:
        refs = self.refs(kind, artifact_id)
        return refs[-1] if refs else None

    def latest_of_kind(self, kind: ArtifactKind) -> list[ArtifactRef]:
        """The newest version of each artifact of a kind."""
        newest: dict[str, ArtifactRef] = {}
        for ref in self.refs(kind):
            newest[ref.id] = ref
        return list(newest.values())

    def put(
        self,
        kind: ArtifactKind,
        artifact_id: str,
        data: BaseModel | dict[str, Any],
        actor: Actor,
        *,
        reason: str | None = None,
    ) -> ArtifactRef:
        """Validate and store a new immutable version of an artifact."""
        with self._locked():
            return self._put_unlocked(kind, artifact_id, data, actor, reason=reason)

    def _put_unlocked(
        self,
        kind: ArtifactKind,
        artifact_id: str,
        data: BaseModel | dict[str, Any],
        actor: Actor,
        *,
        reason: str | None,
    ) -> ArtifactRef:
        model_cls = ARTIFACT_MODELS[kind]
        raw = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
        model = model_cls.model_validate(raw)
        self._check_identity(kind, artifact_id, model)
        digest = content_hash(model)
        existing = self.refs(kind, artifact_id)
        if existing and existing[-1].sha256 == digest:
            return existing[-1]
        version = (
            max(
                existing[-1].version if existing else 0,
                self._highest_version_on_disk(kind, artifact_id),
            )
            + 1
        )
        ref = ArtifactRef(kind=kind, id=artifact_id, version=version, sha256=digest)
        path = self._artifact_path(kind, artifact_id, version)
        _write_once(path, pretty_json(model))
        self._append_event_unlocked(
            EventType.ARTIFACT_WRITTEN,
            actor,
            from_state=None,
            to_state=None,
            reason=reason,
            payload={
                "ref": ref.model_dump(mode="json"),
                "path": path.relative_to(self.root).as_posix(),
            },
        )
        return ref

    def _highest_version_on_disk(self, kind: ArtifactKind, artifact_id: str) -> int:
        """Highest vNNNN file present, registered or not.

        A crash between writing a version file and appending its event leaves an
        unregistered file. Skipping past it keeps the id usable; verify() reports it.
        """
        folder = self.root / "artifacts" / kind.value / artifact_id
        numbers = [int(p.stem[1:]) for p in folder.glob("v[0-9][0-9][0-9][0-9].json")]
        return max(numbers, default=0)

    def _check_identity(self, kind: ArtifactKind, artifact_id: str, model: BaseModel) -> None:
        own_id = getattr(model, "option_id", None) or getattr(model, "id", None)
        if own_id is not None and own_id != artifact_id:
            raise StoreError(f"{kind.value} content has id {own_id!r}, stored as {artifact_id!r}")
        project_id = getattr(model, "project_id", None)
        if project_id is not None and project_id != self.project_id:
            raise StoreError(
                f"{kind.value} {artifact_id} belongs to project {project_id!r}, "
                f"not {self.project_id!r}"
            )

    def get(self, ref: ArtifactRef, model_cls: type[M] | None = None) -> M:
        """Load an artifact version and verify it against its registered hash."""
        registered = self._registered(ref)
        if registered is None or registered.sha256 != ref.sha256:
            raise StoreError(f"no such artifact version: {ref.kind.value}/{ref.id} v{ref.version}")
        cls = model_cls or ARTIFACT_MODELS[ref.kind]
        path = self._artifact_path(ref.kind, ref.id, ref.version)
        try:
            model = cls.model_validate_json(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise StoreIntegrityError(f"{path} is missing") from exc
        if content_hash(model) != ref.sha256:
            raise StoreIntegrityError(f"{path} content does not match its recorded hash")
        return model  # type: ignore[return-value]

    def _registered(self, ref: ArtifactRef) -> ArtifactRef | None:
        for r in self.refs(ref.kind, ref.id):
            if r.version == ref.version:
                return r
        return None

    def get_latest(self, kind: ArtifactKind, artifact_id: str) -> BaseModel | None:
        ref = self.latest(kind, artifact_id)
        return self.get(ref) if ref else None

    # ----------------------------------------------------------------- verify

    def verify(self) -> list[str]:
        """Check the event chain, every artifact and every source file. Empty = intact."""
        problems: list[str] = []
        try:
            events = self.events()
        except StoreIntegrityError as exc:
            return [str(exc)]
        prev_hash = None
        for i, event in enumerate(events, start=1):
            body = event.model_dump(mode="json", exclude={"hash"})
            if event.seq != i:
                problems.append(f"event {i} has seq {event.seq}")
            if event.prev_hash != prev_hash:
                problems.append(f"event {event.seq} does not chain to the previous event")
            if _event_hash(body) != event.hash:
                problems.append(f"event {event.seq} was modified after it was written")
            prev_hash = event.hash
        if not events or events[0].type is not EventType.PROJECT_CREATED:
            problems.append("event log does not start with project_created")

        registered: set[Path] = set()
        for ref in self.refs():
            path = self._artifact_path(ref.kind, ref.id, ref.version)
            registered.add(path)
            try:
                self.get(ref)
            except (StoreError, ValidationError) as exc:
                problems.append(f"{ref.kind.value}/{ref.id} v{ref.version}: {exc}")
        for path in sorted((self.root / "artifacts").rglob("*.json")):
            if path not in registered:
                problems.append(f"{path.relative_to(self.root)} is not registered in the event log")

        registered_sources: set[Path] = set()
        for ref in self.refs(ArtifactKind.SOURCE_DOCUMENT):
            try:
                doc = self.get(ref, SourceDocument)
            except StoreError:
                continue  # already reported above
            src = self.root / doc.stored_path
            registered_sources.add(src)
            if not src.is_file():
                problems.append(f"source file {doc.stored_path} is missing")
            elif file_sha256(src) != doc.sha256:
                problems.append(f"source file {doc.stored_path} was modified")
        source_dir = self.root / "source"
        if source_dir.is_dir():
            for path in sorted(p for p in source_dir.rglob("*") if p.is_file()):
                if path not in registered_sources:
                    rel = path.relative_to(self.root)
                    problems.append(f"source file {rel} is not registered in the event log")
        return problems

