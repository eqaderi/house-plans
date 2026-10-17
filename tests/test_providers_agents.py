"""Provider data-flow policy and the agent role roster."""

from __future__ import annotations

import subprocess

import pytest

from house_ai.domain.agents import AgentRoster
from house_ai.domain.provenance import DataClassification
from house_ai.providers.base import (
    Attachment,
    DataFlowPolicy,
    PrivateDataFlowError,
    ProviderRequest,
    ProviderResponse,
    send,
)
from house_ai.storage.hashing import load_document

from .conftest import AGENT, HUMAN, REPO


class RecordingProvider:
    name = "test-provider"

    def __init__(self) -> None:
        self.calls: list[ProviderRequest] = []

    def complete(self, request: ProviderRequest) -> ProviderResponse:
        self.calls.append(request)
        return ProviderResponse(text="ok", provider=self.name, model="none")


def _request(classification: DataClassification) -> ProviderRequest:
    return ProviderRequest(
        system="s",
        prompt="p",
        classification=DataClassification.SYNTHETIC,
        attachments=[Attachment("site v1", classification, "{...}")],
    )


def test_private_data_is_refused_by_default():
    provider = RecordingProvider()
    with pytest.raises(PrivateDataFlowError, match="site v1"):
        send(provider, _request(DataClassification.PRIVATE), DataFlowPolicy())
    assert provider.calls == []


def test_synthetic_data_flows_without_consent():
    provider = RecordingProvider()
    send(provider, _request(DataClassification.SYNTHETIC), DataFlowPolicy())
    assert len(provider.calls) == 1


def test_private_data_flows_only_to_the_provider_a_human_allowed():
    policy = DataFlowPolicy(frozenset({"test-provider"}), granted_by=HUMAN)
    provider = RecordingProvider()
    send(provider, _request(DataClassification.PRIVATE), policy)
    assert len(provider.calls) == 1
    other = RecordingProvider()
    other.name = "other-provider"
    with pytest.raises(PrivateDataFlowError):
        send(other, _request(DataClassification.PRIVATE), policy)


def test_an_agent_cannot_grant_private_data_flow():
    with pytest.raises(ValueError, match="only a human"):
        DataFlowPolicy(frozenset({"test-provider"}), granted_by=AGENT)


SPEC_ROLES = [
    "Orchestrator",
    "Site Analyst",
    "Architectural Programmer",
    "Design Architect",
    "Planning Critic",
    "Building Science Critic",
    "Code Critic",
    "Structural Concept Critic",
    "MEP Concept Critic",
    "Cost/Constructability Critic",
    "Blender Agent",
    "Unreal Agent",
]


def test_roster_has_every_spec_role_and_none_can_approve():
    roster = AgentRoster.model_validate(load_document(REPO / "agents" / "roles.yaml"))
    assert [r.name for r in roster.roles] == SPEC_ROLES
    assert all(r.may_approve is False for r in roster.roles)


def test_roster_schema_refuses_an_approving_role():
    doc = load_document(REPO / "agents" / "roles.yaml")
    doc["roles"][0]["may_approve"] = True
    with pytest.raises(ValueError):
        AgentRoster.model_validate(doc)


def test_domain_never_imports_a_vendor_sdk():
    src = REPO / "src" / "house_ai"
    vendors = (
        "import openai",
        "import anthropic",
        "google.generativeai",
        "from google import genai",
    )
    for path in src.rglob("*.py"):
        text = path.read_text()
        assert not any(v in text for v in vendors), path


def test_bare_or_private_prompt_is_refused_without_consent():
    provider = RecordingProvider()
    req = ProviderRequest(system="s", prompt="raw owner coordinates")
    with pytest.raises(PrivateDataFlowError, match="prompt"):
        send(provider, req, DataFlowPolicy())
    with pytest.raises(PrivateDataFlowError, match="prompt"):
        send(
            provider,
            ProviderRequest(
                system="s",
                prompt="private owner prompt",
                classification=DataClassification.PRIVATE,
                attachments=[Attachment("synthetic", DataClassification.SYNTHETIC, "{}")],
            ),
            DataFlowPolicy(),
        )


def test_unlabelled_prompt_is_private_even_with_synthetic_attachments():
    provider = RecordingProvider()
    req = ProviderRequest(
        system="s",
        prompt="owner's private notes",
        attachments=[Attachment("synthetic", DataClassification.SYNTHETIC, "{}")],
    )
    with pytest.raises(PrivateDataFlowError, match="prompt"):
        send(provider, req, DataFlowPolicy())
    assert provider.calls == []


def _tracked_files() -> list[str]:
    if not (REPO / ".git").exists():
        pytest.skip("not a git checkout")
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return out.splitlines()


def test_survey_files_are_tracked_only_inside_a_project_folder():
    """Owner surveys are committed only in projects/<name>/ (ADR 0009); project-data/ stays
    private, and no lock, partial write or credential file is ever tracked."""
    import re

    tracked = _tracked_files()
    in_project = re.compile(r"^projects/[a-z0-9][a-z0-9-]*/(surveys|source)/[^/]+\.dwg$", re.I)
    dwg = [f for f in tracked if f.lower().endswith(".dwg")]
    assert [f for f in dwg if not in_project.match(f)] == []
    dxf = [f for f in tracked if f.lower().endswith(".dxf")]
    assert [f for f in dxf if not f.startswith(("tests/fixtures/", "examples/"))] == []
    assert [f for f in tracked if f.startswith(("sources/", "derived/"))] == []
    assert [f for f in tracked if f.startswith("project-data/")] == ["project-data/README.md"]
    names = [f.rsplit("/", 1)[-1] for f in tracked]
    assert [n for n in names if n in {".lock", ".env"} or n.startswith((".tmp-", ".env."))] == []

