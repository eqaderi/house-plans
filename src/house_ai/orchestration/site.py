"""SiteService: the site's part of the workflow, in one module (ADR 0028).

Peer of :class:`~house_ai.orchestration.interview.InterviewService` and
:class:`~house_ai.orchestration.plans.PlanService`. It sequences the separate
records of ADR 0006 §1 (source document, ``cad_import``, ``site``, human
confirmation) and moves the project between the site states itself, so no
caller has to know the order:

* :meth:`SiteService.ingest` extracts stored survey sources, starts site
  ingestion on a new project and assesses the Site;
* :meth:`SiteService.assess` (re-)assesses a stored Site version;
* :meth:`SiteService.confirm` applies a human confirmation and, once no
  Blocker remains, moves the project back to SITE_INGESTION under the
  confirmer's name, where the site gate can be approved;
* :meth:`SiteService.blockers` says what keeps the site gate closed now.

Approving the site gate stays a human act in :mod:`.workflow`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from house_ai.cad.layers import LayerMapping
from house_ai.domain.provenance import Actor, ArtifactKind, ArtifactRef
from house_ai.domain.site import Site, site_verification_blockers
from house_ai.domain.workflow import EventType, WorkflowState
from house_ai.storage import ProjectStore

from .site_ingestion import SiteConfirmation, confirm_site, ingest_site
from .workflow import TransitionNotAllowed, Workflow

S = WorkflowState


@dataclass(frozen=True)
class SiteOutcome:
    """A Site version, what still blocks the site gate, and the workflow state after."""

    site_ref: ArtifactRef
    blockers: list[str]
    state: WorkflowState
    #: The ``cad_import`` records written by this call, one per survey file.
    cad_refs: list[ArtifactRef] = field(default_factory=list)


class SiteService:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self.workflow = Workflow(store)

    # ------------------------------------------------------------------ read

    def blockers(self, site_id: str = "site") -> list[str]:
        """What keeps the site gate closed for the newest version of the Site now."""
        ref = self.store.latest(ArtifactKind.SITE, site_id)
        if ref is None:
            return [f"no site {site_id!r} has been ingested yet"]
        return site_verification_blockers(self.store.get(ref, Site))

    # ----------------------------------------------------------------- write

    def ingest(
        self,
        source_ids: str | Sequence[str],
        mapping: LayerMapping,
        actor: Actor,
        *,
        site_id: str = "site",
    ) -> SiteOutcome:
        """Extract stored survey file(s) into ``cad_import`` records and a Site, then assess it.

        A new project starts site ingestion here; an ambiguous Site then stops in
        SITE_NEEDS_CONFIRMATION with its Blockers.
        """
        ids = [source_ids] if isinstance(source_ids, str) else list(source_ids)
        result = ingest_site(self.store, ids, mapping, actor, site_id=site_id)
        outcome = self.assess(result.site_ref, actor)
        return SiteOutcome(outcome.site_ref, outcome.blockers, outcome.state, result.cad_refs)

    def assess(self, site_ref: ArtifactRef, actor: Actor) -> SiteOutcome:
        """Assess a stored Site version and move the project to where it belongs.

        From NEW_PROJECT this starts site ingestion. In SITE_INGESTION an
        ambiguous Site moves the project to SITE_NEEDS_CONFIRMATION. Anywhere
        else the Blockers are reported and the state does not change: leaving
        SITE_NEEDS_CONFIRMATION is the human confirmation's move.
        """
        if site_ref.kind is not ArtifactKind.SITE:
            raise TransitionNotAllowed(f"site assessment reads a site, not {site_ref.kind}")
        blockers = site_verification_blockers(self.store.get(site_ref, Site))
        state = self.workflow.state
        if state is S.NEW_PROJECT:
            self.workflow.transition(S.SITE_INGESTION, actor, "site ingestion started")
            state = S.SITE_INGESTION
        if state is S.SITE_INGESTION and blockers:
            self.store.append_event(
                EventType.TRANSITION,
                actor,
                from_state=S.SITE_INGESTION,
                to_state=S.SITE_NEEDS_CONFIRMATION,
                reason="site needs human verification before anything else",
                payload={"site": site_ref.model_dump(mode="json"), "blockers": blockers},
            )
            state = S.SITE_NEEDS_CONFIRMATION
        return SiteOutcome(site_ref, blockers, state)

    def confirm(self, site_id: str, confirmer: Actor, conf: SiteConfirmation) -> SiteOutcome:
        """Write the human-confirmed Site version and re-assess it.

        Human-only (agent contract §8). If the confirmation clears every
        Blocker while the project waits in SITE_NEEDS_CONFIRMATION, the project
        moves back to SITE_INGESTION, recorded under the confirmer's name, and
        the site gate can be approved with no further step. If any Blocker
        remains, the workflow state does not change.
        """
        site_ref = confirm_site(self.store, site_id, confirmer, conf)
        blockers = site_verification_blockers(self.store.get(site_ref, Site))
        state = self.workflow.state
        if state is S.SITE_NEEDS_CONFIRMATION and not blockers:
            self.workflow.transition(
                S.SITE_INGESTION,
                confirmer,
                f"{confirmer.id} confirmed {site_ref.id} v{site_ref.version}; no site blocker "
                "remains, the site gate can be approved",
            )
            state = S.SITE_INGESTION
        return SiteOutcome(site_ref, blockers, state)
