"""Tests for ConceptProposal schema and formal validation (Tasks S7-06 and S7-07)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from house_ai.constants.proposals import (
    ERR_CONFLICTING_ADJACENCY,
    ERR_CROSS_LEVEL_HARD_ADJACENCY,
    ERR_DISCONNECTED_TOPOLOGY,
    ERR_EXCESSIVE_LEVELS,
    ERR_MISSING_LEVEL_ASSIGNMENT,
    ERR_MISSING_VERTICAL_CIRCULATION,
    ERR_PROGRAM_HARD_ADJACENCY_VIOLATION,
    ERR_UNKNOWN_PROGRAM_ITEM,
    OUTDOOR_LINK_TERRACE,
    STAIR_CORE_CENTRAL,
)
from house_ai.domain.program import (
    SpaceFunction,
    SpaceProgram,
    SpaceRelationship,
    SpaceRelationshipKind,
    SpaceRequirement,
    Strength,
)
from house_ai.domain.proposal import (
    ConceptProposal,
    OutdoorLinkProposal,
    ProposalAdjacency,
    ProposalLevelAssignment,
    ProposalZone,
    StairCoreProposal,
)
from house_ai.domain.provenance import Actor, ActorKind, Provenance
from house_ai.validation.topology import is_valid_proposal, validate_proposal

REPO = Path(__file__).resolve().parents[1]
HILLSIDE = REPO / "examples" / "projects" / "synthetic-hillside"
WHEN = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
TOOL = Actor(kind=ActorKind.SYSTEM, id="house-ai")


def _minimal_program() -> SpaceProgram:
    items = [
        SpaceRequirement(
            id="pi-entry",
            name="Entry",
            function=SpaceFunction.ENTRY,
            privacy="public",
            min_area_m2=5.0,
        ),
        SpaceRequirement(
            id="pi-living",
            name="Living room",
            function=SpaceFunction.LIVING,
            privacy="public",
            min_area_m2=20.0,
        ),
        SpaceRequirement(
            id="pi-bed-1",
            name="Primary bedroom",
            function=SpaceFunction.BEDROOM,
            privacy="private",
            min_area_m2=14.0,
        ),
    ]
    adj = [
        SpaceRelationship(
            id="adj-prog-entry-living",
            a="pi-entry",
            b="pi-living",
            kind=SpaceRelationshipKind.CONNECTED,
            strength=Strength.HARD,
        ),
    ]
    return SpaceProgram(
        id="prog-test",
        project_id="proj-test",
        items=items,
        adjacencies=adj,
        levels=2,
        provenance=Provenance(
            created_at=WHEN,
            created_by=TOOL,
            method="test_fixture",
        ),
    )


# --- S7-06: ConceptProposal schema tests


def test_concept_proposal_schema_valid_instantiation():
    prop = ConceptProposal(
        id="prop-01",
        project_id="proj-test",
        name="Day/Night Split Concept",
        intent="Separate day living on entry level from private bedrooms below",
        zones=[
            ProposalZone(id="z-day", name="Day zone", program_item_ids=["pi-entry", "pi-living"]),
            ProposalZone(id="z-night", name="Night zone", program_item_ids=["pi-bed-1"]),
        ],
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-entry"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-entry"),
            ProposalLevelAssignment(program_item_id="pi-bed-1", level_id="lv-lower"),
        ],
        adjacency_graph=[
            ProposalAdjacency(
                id="padj-entry-living",
                a="pi-entry",
                b="pi-living",
                kind=SpaceRelationshipKind.CONNECTED,
                strength=Strength.HARD,
            ),
            ProposalAdjacency(
                id="padj-living-bed",
                a="pi-living",
                b="pi-bed-1",
                kind=SpaceRelationshipKind.NEAR,
                strength=Strength.SOFT,
                weight=1.5,
            ),
        ],
        stair_cores=[
            StairCoreProposal(
                id="sc-main",
                position=STAIR_CORE_CENTRAL,
                connects_levels=["lv-entry", "lv-lower"],
                near_program_item_ids=["pi-living"],
            )
        ],
        outdoor_links=[
            OutdoorLinkProposal(
                id="ol-terrace",
                program_item_id="pi-living",
                kind=OUTDOOR_LINK_TERRACE,
            )
        ],
        target_strategy="split_walkout",
        provenance=Provenance(
            created_at=WHEN,
            created_by=TOOL,
            method="agent_proposal",
        ),
    )
    assert prop.id == "prop-01"
    assert len(prop.zones) == 2
    assert len(prop.level_assignments) == 3
    assert len(prop.adjacency_graph) == 2
    assert len(prop.stair_cores) == 1
    assert len(prop.outdoor_links) == 1


def test_concept_proposal_schema_rejections():
    # Duplicate zone IDs
    with pytest.raises(ValidationError, match="duplicate id found in zones"):
        ConceptProposal(
            id="prop-dup-zone",
            project_id="proj-test",
            name="Dup Zone",
            intent="Intent text",
            zones=[
                ProposalZone(id="z-1", name="Zone 1"),
                ProposalZone(id="z-1", name="Zone 2"),
            ],
        )

    # Duplicate program_item_id assigned to multiple levels
    with pytest.raises(ValidationError, match="duplicate program_item_id"):
        ConceptProposal(
            id="prop-dup-level",
            project_id="proj-test",
            name="Dup Level",
            intent="Intent text",
            level_assignments=[
                ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-1"),
                ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-2"),
            ],
        )

    # Self adjacency
    with pytest.raises(ValidationError, match="adjacency from an item to itself"):
        ProposalAdjacency(
            id="padj-self",
            a="pi-entry",
            b="pi-entry",
            kind=SpaceRelationshipKind.CONNECTED,
            strength=Strength.HARD,
        )

    # Hard requirement with weight
    with pytest.raises(ValidationError, match="hard requirements must not carry a weight"):
        ProposalAdjacency(
            id="padj-hard-weight",
            a="pi-entry",
            b="pi-living",
            kind=SpaceRelationshipKind.CONNECTED,
            strength=Strength.HARD,
            weight=2.0,
        )

    # Stair core with fewer than 2 levels
    with pytest.raises(ValidationError):
        StairCoreProposal(
            id="sc-single",
            position=STAIR_CORE_CENTRAL,
            connects_levels=["lv-1"],
        )

    # Stair core with duplicate levels
    with pytest.raises(ValidationError, match="duplicate level in connects_levels"):
        StairCoreProposal(
            id="sc-dup",
            position=STAIR_CORE_CENTRAL,
            connects_levels=["lv-1", "lv-1"],
        )


# --- S7-07: Topology proposal validation tests


def test_validate_proposal_success():
    prog = _minimal_program()
    prop = ConceptProposal(
        id="prop-valid",
        project_id="proj-test",
        name="Valid proposal",
        intent="Good layout",
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-entry"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-entry"),
            ProposalLevelAssignment(program_item_id="pi-bed-1", level_id="lv-lower"),
        ],
        adjacency_graph=[
            ProposalAdjacency(
                id="padj-1",
                a="pi-entry",
                b="pi-living",
                kind=SpaceRelationshipKind.CONNECTED,
                strength=Strength.HARD,
            ),
            ProposalAdjacency(
                id="padj-2",
                a="pi-living",
                b="pi-bed-1",
                kind=SpaceRelationshipKind.NEAR,
                strength=Strength.SOFT,
            ),
        ],
        stair_cores=[
            StairCoreProposal(
                id="sc-1",
                position=STAIR_CORE_CENTRAL,
                connects_levels=["lv-entry", "lv-lower"],
                near_program_item_ids=["pi-living"],
            )
        ],
    )
    findings = validate_proposal(prop, prog)
    assert findings == []
    assert is_valid_proposal(findings) is True


def test_validate_proposal_unknown_program_item():
    prog = _minimal_program()
    prop = ConceptProposal(
        id="prop-bad-item",
        project_id="proj-test",
        name="Bad Item",
        intent="Invalid item",
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-ghost", level_id="lv-entry"),
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-entry"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-entry"),
            ProposalLevelAssignment(program_item_id="pi-bed-1", level_id="lv-entry"),
        ],
    )
    findings = validate_proposal(prop, prog)
    codes = [f.code for f in findings]
    assert ERR_UNKNOWN_PROGRAM_ITEM in codes
    assert is_valid_proposal(findings) is False


def test_validate_proposal_missing_level_assignment():
    prog = _minimal_program()
    prop = ConceptProposal(
        id="prop-missing-level",
        project_id="proj-test",
        name="Missing level",
        intent="Omitted bedroom",
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-entry"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-entry"),
            # pi-bed-1 is omitted!
        ],
    )
    findings = validate_proposal(prop, prog)
    codes = [f.code for f in findings]
    assert ERR_MISSING_LEVEL_ASSIGNMENT in codes
    assert is_valid_proposal(findings) is False


def test_validate_proposal_excessive_levels():
    prog = _minimal_program()  # program.storeys = 2
    prop = ConceptProposal(
        id="prop-too-many-levels",
        project_id="proj-test",
        name="Too many levels",
        intent="3 storeys proposed",
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-2"),
            ProposalLevelAssignment(program_item_id="pi-bed-1", level_id="lv-3"),
        ],
        stair_cores=[
            StairCoreProposal(
                id="sc-1",
                connects_levels=["lv-1", "lv-2", "lv-3"],
            )
        ],
    )
    findings = validate_proposal(prop, prog)
    codes = [f.code for f in findings]
    assert ERR_EXCESSIVE_LEVELS in codes
    assert is_valid_proposal(findings) is False


def test_validate_proposal_missing_vertical_circulation():
    prog = _minimal_program()
    # Spans 2 levels but provides no stair core
    prop = ConceptProposal(
        id="prop-no-stairs",
        project_id="proj-test",
        name="No stairs",
        intent="Stairs forgotten",
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-bed-1", level_id="lv-2"),
        ],
        stair_cores=[],
    )
    findings = validate_proposal(prop, prog)
    codes = [f.code for f in findings]
    assert ERR_MISSING_VERTICAL_CIRCULATION in codes
    assert is_valid_proposal(findings) is False


def test_validate_proposal_cross_level_hard_adjacency():
    prog = _minimal_program()  # prog has HARD CONNECTED between pi-entry and pi-living
    # Place pi-entry on lv-1 and pi-living on lv-2
    prop = ConceptProposal(
        id="prop-cross-level-hard",
        project_id="proj-test",
        name="Cross level hard",
        intent="Split entry and living across levels",
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-2"),
            ProposalLevelAssignment(program_item_id="pi-bed-1", level_id="lv-2"),
        ],
        stair_cores=[
            StairCoreProposal(
                id="sc-1",
                connects_levels=["lv-1", "lv-2"],
            )
        ],
    )
    findings = validate_proposal(prop, prog)
    codes = [f.code for f in findings]
    assert ERR_CROSS_LEVEL_HARD_ADJACENCY in codes
    assert is_valid_proposal(findings) is False


def test_validate_proposal_program_hard_adjacency_violation():
    prog = _minimal_program()  # prog has HARD CONNECTED between pi-entry and pi-living
    # Proposal explicitly asks for SEPARATED between them
    prop = ConceptProposal(
        id="prop-contradict-program",
        project_id="proj-test",
        name="Contradict program",
        intent="Separate entry from living",
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-bed-1", level_id="lv-1"),
        ],
        adjacency_graph=[
            ProposalAdjacency(
                id="padj-conflict",
                a="pi-entry",
                b="pi-living",
                kind=SpaceRelationshipKind.SEPARATED,
                strength=Strength.HARD,
            ),
        ],
    )
    findings = validate_proposal(prop, prog)
    codes = [f.code for f in findings]
    assert ERR_PROGRAM_HARD_ADJACENCY_VIOLATION in codes
    assert is_valid_proposal(findings) is False


def test_validate_proposal_internal_conflict():
    prog = _minimal_program()
    prop = ConceptProposal(
        id="prop-internal-conflict",
        project_id="proj-test",
        name="Internal conflict",
        intent="Contradicting proposal adjacencies",
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-bed-1", level_id="lv-1"),
        ],
        adjacency_graph=[
            ProposalAdjacency(
                id="padj-1",
                a="pi-living",
                b="pi-bed-1",
                kind=SpaceRelationshipKind.CONNECTED,
                strength=Strength.SOFT,
            ),
            ProposalAdjacency(
                id="padj-2",
                a="pi-living",
                b="pi-bed-1",
                kind=SpaceRelationshipKind.SEPARATED,
                strength=Strength.SOFT,
            ),
        ],
    )
    findings = validate_proposal(prop, prog)
    codes = [f.code for f in findings]
    assert ERR_CONFLICTING_ADJACENCY in codes
    assert is_valid_proposal(findings) is False


def test_validate_proposal_disconnected_topology():
    prog = _minimal_program()
    prog = prog.model_copy(
        update={
            "items": [
                *prog.space_requirements,
                SpaceRequirement(
                    id="pi-bed-2",
                    name="Second bedroom",
                    function=SpaceFunction.BEDROOM,
                    privacy="private",
                ),
            ]
        }
    )
    # Cluster 1: entry <-> living; Cluster 2: bed-1 <-> bed-2 with no connection between clusters
    prop = ConceptProposal(
        id="prop-disconnected",
        project_id="proj-test",
        name="Disconnected",
        intent="Disjoint bedroom cluster",
        level_assignments=[
            ProposalLevelAssignment(program_item_id="pi-entry", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-living", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-bed-1", level_id="lv-1"),
            ProposalLevelAssignment(program_item_id="pi-bed-2", level_id="lv-1"),
        ],
        adjacency_graph=[
            ProposalAdjacency(
                id="padj-1",
                a="pi-entry",
                b="pi-living",
                kind=SpaceRelationshipKind.CONNECTED,
                strength=Strength.HARD,
            ),
            ProposalAdjacency(
                id="padj-2",
                a="pi-bed-1",
                b="pi-bed-2",
                kind=SpaceRelationshipKind.CONNECTED,
                strength=Strength.HARD,
            ),
        ],
    )
    findings = validate_proposal(prop, prog)
    codes = [f.code for f in findings]
    assert ERR_DISCONNECTED_TOPOLOGY in codes
    assert is_valid_proposal(findings) is False
