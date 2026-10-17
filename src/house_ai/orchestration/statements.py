"""The owner's own statements about the project, recorded verbatim (ADR 0009).

A statement is evidence for a later confirmation, never the confirmation itself:
recording one changes no confirmation status, clears no blocker and moves no
workflow state. Anyone may write one down (an agent relaying the owner's chat,
for example); the record names who said it, how it arrived and who recorded it.
"""

from __future__ import annotations

from house_ai.domain.provenance import Actor, ArtifactKind, ArtifactRef, Provenance
from house_ai.domain.records import OwnerStatement, OwnerStatementsFile
from house_ai.storage import ProjectStore

STATEMENTS_ID = "owner-statements"


def owner_statements(store: ProjectStore) -> list[OwnerStatement]:
    ref = store.latest(ArtifactKind.OWNER_STATEMENTS, STATEMENTS_ID)
    return store.get(ref, OwnerStatementsFile).statements if ref else []


def record_owner_statement(
    store: ProjectStore,
    *,
    subject: str,
    words: str,
    stated_by: str,
    channel: str,
    actor: Actor,
    pending_confirmation: str | None = None,
) -> ArtifactRef:
    """Append one statement as a new version of the project's statements file."""
    previous = owner_statements(store)
    statement = OwnerStatement(
        id=f"stmt-{len(previous) + 1:03d}",
        subject=subject,
        words=words.strip(),
        stated_by=stated_by,
        channel=channel,
        recorded_by=actor,
        recorded_at=store.clock(),
        pending_confirmation=pending_confirmation,
    )
    record = OwnerStatementsFile(
        project_id=store.project_id,
        statements=[*previous, statement],
        provenance=Provenance(
            created_at=store.clock(),
            created_by=actor,
            method="owner_statement",
            tool="house-ai statement add",
        ),
    )
    return store.put(
        ArtifactKind.OWNER_STATEMENTS,
        STATEMENTS_ID,
        record,
        actor,
        reason=f"recorded {statement.id} ({subject}) stated by {stated_by}",
    )
