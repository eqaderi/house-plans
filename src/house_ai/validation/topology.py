"""Formal validation of concept topology proposals (Stage S7).

Verifies program coverage, connectivity, hard adjacencies, and level
feasibility before passing a proposal to the constraint solver.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from house_ai.constants.proposals import (
    ERR_CONFLICTING_ADJACENCY,
    ERR_CROSS_LEVEL_HARD_ADJACENCY,
    ERR_DISCONNECTED_TOPOLOGY,
    ERR_EXCESSIVE_LEVELS,
    ERR_MISSING_LEVEL_ASSIGNMENT,
    ERR_MISSING_VERTICAL_CIRCULATION,
    ERR_PROGRAM_HARD_ADJACENCY_VIOLATION,
    ERR_UNKNOWN_PROGRAM_ITEM,
)
from house_ai.domain.base import EXTERIOR
from house_ai.domain.program import AdjacencyKind, SpaceProgram, Strength
from house_ai.domain.proposal import ConceptProposal
from house_ai.domain.records import Severity
from house_ai.domain.site import Site


@dataclass
class ProposalFinding:
    code: str
    severity: Severity
    message: str
    subject_ids: list[str] = field(default_factory=list)


def is_valid_proposal(findings: list[ProposalFinding]) -> bool:
    """Return True if no blocking findings are present."""
    return not any(f.severity is Severity.BLOCKING for f in findings)


def validate_proposal(
    proposal: ConceptProposal,
    program: SpaceProgram,
    site: Site | None = None,
) -> list[ProposalFinding]:
    """Validate a topology proposal against a space program and optional site."""
    findings: list[ProposalFinding] = []
    prog_item_ids = {item.id for item in program.items}

    # 1. Program coverage & unknown item checks
    referenced_items: set[str] = set()
    for la in proposal.level_assignments:
        referenced_items.add(la.program_item_id)
        if la.program_item_id not in prog_item_ids:
            findings.append(
                ProposalFinding(
                    ERR_UNKNOWN_PROGRAM_ITEM,
                    Severity.BLOCKING,
                    f"Unknown program item {la.program_item_id!r} in level assignments",
                    [la.program_item_id],
                )
            )

    for zone in proposal.zones:
        for pid in zone.program_item_ids:
            referenced_items.add(pid)
            if pid not in prog_item_ids:
                findings.append(
                    ProposalFinding(
                        ERR_UNKNOWN_PROGRAM_ITEM,
                        Severity.BLOCKING,
                        f"Unknown program item {pid!r} in zone {zone.id!r}",
                        [zone.id, pid],
                    )
                )

    for adj in proposal.adjacency_graph:
        referenced_items.add(adj.a)
        if adj.a not in prog_item_ids:
            findings.append(
                ProposalFinding(
                    ERR_UNKNOWN_PROGRAM_ITEM,
                    Severity.BLOCKING,
                    f"Unknown program item {adj.a!r} in proposal adjacency {adj.id!r}",
                    [adj.id, adj.a],
                )
            )
        if adj.b != EXTERIOR:
            referenced_items.add(adj.b)
            if adj.b not in prog_item_ids:
                findings.append(
                    ProposalFinding(
                        ERR_UNKNOWN_PROGRAM_ITEM,
                        Severity.BLOCKING,
                        f"Unknown program item {adj.b!r} in proposal adjacency {adj.id!r}",
                        [adj.id, adj.b],
                    )
                )

    for ol in proposal.outdoor_links:
        referenced_items.add(ol.program_item_id)
        if ol.program_item_id not in prog_item_ids:
            findings.append(
                ProposalFinding(
                    ERR_UNKNOWN_PROGRAM_ITEM,
                    Severity.BLOCKING,
                    f"Unknown program item {ol.program_item_id!r} in outdoor link {ol.id!r}",
                    [ol.id, ol.program_item_id],
                )
            )

    for sc in proposal.stair_cores:
        for pid in sc.near_program_item_ids:
            referenced_items.add(pid)
            if pid not in prog_item_ids:
                findings.append(
                    ProposalFinding(
                        ERR_UNKNOWN_PROGRAM_ITEM,
                        Severity.BLOCKING,
                        f"Unknown program item {pid!r} near stair core {sc.id!r}",
                        [sc.id, pid],
                    )
                )

    # Missing level assignments check
    item_to_level = {la.program_item_id: la.level_id for la in proposal.level_assignments}
    if proposal.level_assignments:
        missing_levels = sorted(prog_item_ids - set(item_to_level))
        if missing_levels:
            findings.append(
                ProposalFinding(
                    ERR_MISSING_LEVEL_ASSIGNMENT,
                    Severity.BLOCKING,
                    f"Program items missing level assignments: {', '.join(missing_levels)}",
                    missing_levels,
                )
            )

    # 2. Level feasibility & Vertical circulation
    levels_used = {la.level_id for la in proposal.level_assignments}
    if program.levels is not None and len(levels_used) > program.levels:
        findings.append(
            ProposalFinding(
                ERR_EXCESSIVE_LEVELS,
                Severity.BLOCKING,
                f"Proposal uses {len(levels_used)} levels ({sorted(levels_used)}), "
                f"exceeding program maximum of {program.levels}",
                sorted(levels_used),
            )
        )

    if len(levels_used) > 1:
        if not proposal.stair_cores:
            findings.append(
                ProposalFinding(
                    ERR_MISSING_VERTICAL_CIRCULATION,
                    Severity.BLOCKING,
                    f"Proposal spans {len(levels_used)} levels but defines no stair cores",
                    sorted(levels_used),
                )
            )
        else:
            stair_graph: dict[str, set[str]] = {lv: set() for lv in levels_used}
            for sc in proposal.stair_cores:
                for i in range(len(sc.connects_levels)):
                    for j in range(i + 1, len(sc.connects_levels)):
                        l1, l2 = sc.connects_levels[i], sc.connects_levels[j]
                        if l1 in stair_graph and l2 in stair_graph:
                            stair_graph[l1].add(l2)
                            stair_graph[l2].add(l1)

            start = next(iter(levels_used))
            visited: set[str] = set()
            queue = [start]
            while queue:
                curr = queue.pop()
                if curr in visited:
                    continue
                visited.add(curr)
                queue.extend(stair_graph[curr] - visited)

            unreached = levels_used - visited
            if unreached:
                findings.append(
                    ProposalFinding(
                        ERR_MISSING_VERTICAL_CIRCULATION,
                        Severity.BLOCKING,
                        "Stair cores do not connect all occupied levels; unreached: "
                        f"{sorted(unreached)}",
                        sorted(unreached),
                    )
                )

    # 3. Adjacency conflicts
    touching_kinds = {AdjacencyKind.CONNECTED, AdjacencyKind.ADJACENT}
    separation_kinds = {AdjacencyKind.SEPARATED, AdjacencyKind.ACOUSTIC_SEPARATION}

    # Internal proposal conflicts
    seen_adj: dict[frozenset[str], AdjacencyKind] = {}
    for padj in proposal.adjacency_graph:
        pair = frozenset({padj.a, padj.b})
        if pair in seen_adj:
            prev_kind = seen_adj[pair]
            if (prev_kind in touching_kinds and padj.kind in separation_kinds) or (
                prev_kind in separation_kinds and padj.kind in touching_kinds
            ):
                findings.append(
                    ProposalFinding(
                        ERR_CONFLICTING_ADJACENCY,
                        Severity.BLOCKING,
                        f"Conflicting proposal adjacencies between {padj.a} and {padj.b} "
                        f"({prev_kind.value} vs {padj.kind.value})",
                        [padj.id, padj.a, padj.b],
                    )
                )
        else:
            seen_adj[pair] = padj.kind

    # Cross-level hard adjacency & Program hard adjacency violations
    for prog_adj in program.adjacencies:
        if prog_adj.strength is Strength.HARD:
            # Cross-level check
            if prog_adj.kind in touching_kinds and prog_adj.b != EXTERIOR:
                la_a = item_to_level.get(prog_adj.a)
                la_b = item_to_level.get(prog_adj.b)
                if la_a is not None and la_b is not None and la_a != la_b:
                    findings.append(
                        ProposalFinding(
                            ERR_CROSS_LEVEL_HARD_ADJACENCY,
                            Severity.BLOCKING,
                            f"Hard program requirement {prog_adj.kind.value} between {prog_adj.a} "
                            f"and {prog_adj.b} cannot be satisfied across different levels "
                            f"({la_a} vs {la_b})",
                            [prog_adj.id, prog_adj.a, prog_adj.b],
                        )
                    )

            # Contradiction with proposal
            pair = frozenset({prog_adj.a, prog_adj.b})
            for padj in proposal.adjacency_graph:
                if frozenset({padj.a, padj.b}) == pair:
                    if prog_adj.kind in touching_kinds and padj.kind in separation_kinds:
                        findings.append(
                            ProposalFinding(
                                ERR_PROGRAM_HARD_ADJACENCY_VIOLATION,
                                Severity.BLOCKING,
                                f"Proposal adjacency {padj.id!r} ({padj.kind.value}) contradicts "
                                f"hard program requirement {prog_adj.id!r} ({prog_adj.kind.value})",
                                [padj.id, prog_adj.id, prog_adj.a, prog_adj.b],
                            )
                        )
                    elif prog_adj.kind in separation_kinds and padj.kind in touching_kinds:
                        findings.append(
                            ProposalFinding(
                                ERR_PROGRAM_HARD_ADJACENCY_VIOLATION,
                                Severity.BLOCKING,
                                f"Proposal adjacency {padj.id!r} ({padj.kind.value}) contradicts "
                                f"hard program requirement {prog_adj.id!r} ({prog_adj.kind.value})",
                                [padj.id, prog_adj.id, prog_adj.a, prog_adj.b],
                            )
                        )

    # 4. Connectivity graph: verify proposed adjacencies do not form disconnected clusters
    active_kinds = {AdjacencyKind.CONNECTED, AdjacencyKind.ADJACENT, AdjacencyKind.NEAR}
    prop_nodes: set[str] = set()
    for padj in proposal.adjacency_graph:
        if padj.kind in active_kinds and padj.b != EXTERIOR:
            prop_nodes.add(padj.a)
            prop_nodes.add(padj.b)

    if prop_nodes:
        combined_graph: dict[str, set[str]] = {n: set() for n in prop_nodes}
        for padj in proposal.adjacency_graph:
            if padj.kind in active_kinds and padj.b != EXTERIOR:
                combined_graph[padj.a].add(padj.b)
                combined_graph[padj.b].add(padj.a)

        for prog_adj in program.adjacencies:
            if prog_adj.kind in active_kinds and prog_adj.b != EXTERIOR:
                if prog_adj.a in combined_graph and prog_adj.b in combined_graph:
                    combined_graph[prog_adj.a].add(prog_adj.b)
                    combined_graph[prog_adj.b].add(prog_adj.a)

        for sc in proposal.stair_cores:
            near = [pid for pid in sc.near_program_item_ids if pid in combined_graph]
            for i in range(len(near)):
                for j in range(i + 1, len(near)):
                    combined_graph[near[i]].add(near[j])
                    combined_graph[near[j]].add(near[i])

        visited: set[str] = set()
        components: list[set[str]] = []
        for node in sorted(combined_graph):
            if node not in visited:
                comp: set[str] = set()
                q = [node]
                while q:
                    curr = q.pop()
                    if curr in comp:
                        continue
                    comp.add(curr)
                    visited.add(curr)
                    q.extend(combined_graph[curr] - comp)
                components.append(comp)

        if len(components) > 1:
            for comp in components[1:]:
                findings.append(
                    ProposalFinding(
                        ERR_DISCONNECTED_TOPOLOGY,
                        Severity.BLOCKING,
                        f"Topology graph has disconnected cluster: {sorted(comp)}",
                        sorted(comp),
                    )
                )

    return findings
