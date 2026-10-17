"""Canonical serialisation and content hashing.

Artifacts are hashed from the canonical JSON of the *validated model*, not
from file bytes, so the same content loaded from YAML or JSON, with or
without default values spelled out, has the same hash.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


def canonical_json(data: BaseModel | dict[str, Any]) -> str:
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def pretty_json(data: BaseModel | dict[str, Any]) -> str:
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(data: BaseModel | dict[str, Any]) -> str:
    return sha256_text(canonical_json(data))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class _JsonLikeLoader(yaml.SafeLoader):
    """SafeLoader that leaves timestamps as strings, as JSON would.

    Pydantic then parses (and rejects naive) datetimes identically for YAML
    and JSON input.
    """


_JsonLikeLoader.yaml_implicit_resolvers = {
    key: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(text: str) -> Any:
    return yaml.load(text, Loader=_JsonLikeLoader)  # noqa: S506 - SafeLoader subclass


def load_document(path: Path) -> Any:
    """Read a .json, .yaml or .yml file."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        return load_yaml(text)
    if path.suffix.lower() == ".json":
        return json.loads(text)
    raise ValueError(f"unsupported document type: {path.name} (use .json, .yaml or .yml)")
