"""Schema export, drift detection and strictness of the canonical models."""

from __future__ import annotations

import json
import math

import pytest
from pydantic import ValidationError

from house_ai.domain.registry import ARTIFACT_MODELS, SCHEMAS, render_schema, stale_schemas
from house_ai.domain.site import Site
from house_ai.domain.workflow import ProjectManifest

from .conftest import REPO


def test_every_artifact_kind_has_a_schema():
    for kind, model in ARTIFACT_MODELS.items():
        assert SCHEMAS[kind.value] is model


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_schema_renders_as_json_schema(name):
    schema = json.loads(render_schema(name))
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["type"] == "object"
    assert schema.get("additionalProperties") is False


def test_committed_schemas_match_the_code():
    stale = stale_schemas(REPO / "schemas")
    assert stale == [], f"run `house-ai schemas export`; stale: {stale}"


def test_unknown_fields_are_rejected(site_doc):
    site_doc["boundry"] = site_doc["boundary"]  # typo
    with pytest.raises(ValidationError, match="boundry"):
        Site.model_validate(site_doc)


def test_naive_datetimes_are_rejected(site_doc):
    site_doc["provenance"]["created_at"] = "2026-10-17T09:00:00"
    with pytest.raises(ValidationError, match="timezone"):
        Site.model_validate(site_doc)


def test_datetimes_are_normalised_to_utc(site_doc):
    site_doc["provenance"]["created_at"] = "2026-10-17T11:00:00+02:00"
    site = Site.model_validate(site_doc)
    assert site.provenance.created_at.isoformat() == "2026-10-17T09:00:00+00:00"


def test_nan_and_infinity_are_rejected(site_doc):
    site_doc["terrain"]["spot_elevations"][0]["z_m"] = math.nan
    with pytest.raises(ValidationError):
        Site.model_validate(site_doc)
    site_doc["terrain"]["spot_elevations"][0]["z_m"] = math.inf
    with pytest.raises(ValidationError):
        Site.model_validate(site_doc)


@pytest.mark.parametrize("bad", ["Kitchen", "1room", "sp kitchen", "sp--x", "", "a" * 65])
def test_ids_must_be_stable_slugs(bad):
    with pytest.raises(ValidationError):
        ProjectManifest.model_validate(
            {
                "id": bad,
                "name": "x",
                "classification": "synthetic",
                "created_at": "2026-10-17T00:00:00Z",
                "created_by": {"kind": "human", "id": "a"},
            }
        )
