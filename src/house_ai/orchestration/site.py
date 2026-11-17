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
* :meth:`SiteService.write_review_package` writes the site review package
  (validation report, drawings, import records, Owner statements);
* :meth:`SiteService.blockers` says what keeps the site gate closed now.

Approving the site gate stays a human act in :mod:`.workflow`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from house_ai.cad.layers import LayerMapping
from house_ai.domain.provenance import Actor, ArtifactKind, ArtifactRef
from house_ai.domain.site import CadImportProvenance, Site, site_blockers
from house_ai.domain.workflow import Blocker, BlockerKind, EventType, WorkflowState
from house_ai.geospatial.validation import report_markdown, validate_site
from house_ai.render2d.review_html import render_review_html
from house_ai.render2d.site_svg import render_site_svg
from house_ai.render2d.terrain_svg import render_terrain_svg
from house_ai.storage import ProjectStore
from house_ai.storage.hashing import pretty_json

from .site_ingestion import SiteConfirmation, confirm_site, ingest_site
from .statements import owner_statements
from .workflow import TransitionNotAllowed, Workflow

S = WorkflowState


@dataclass(frozen=True)
class SiteOutcome:
    """A Site version, what still blocks the site gate, and the workflow state after."""

    site_ref: ArtifactRef
    blockers: list[Blocker]
    state: WorkflowState
    #: The ``cad_import`` records written by this call, one per survey file.
    cad_refs: list[ArtifactRef] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewPackage:
    """The files written for one Site version, and the Blockers its report names."""

    out: Path
    files: list[Path]
    blockers: list[Blocker]


class SiteService:
    def __init__(self, store: ProjectStore) -> None:
        self.store = store
        self.workflow = Workflow(store)

    # ------------------------------------------------------------------ read

    def blockers(self, site_id: str = "site") -> list[Blocker]:
        """What keeps the site gate closed for the newest version of the Site now."""
        ref = self.store.latest(ArtifactKind.SITE, site_id)
        if ref is None:
            message = f"no site {site_id!r} has been ingested yet"
            return [Blocker(kind=BlockerKind.ARTIFACT, code="no_site", message=message)]
        return site_blockers(self.store.get(ref, Site))

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
        blockers = site_blockers(self.store.get(site_ref, Site))
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
                # The saved shape (ADR 0003): the Blockers as sentences.
                payload={
                    "site": site_ref.model_dump(mode="json"),
                    "blockers": [b.message for b in blockers],
                },
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
        blockers = site_blockers(self.store.get(site_ref, Site))
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

    def write_review_package(self, site_ref: ArtifactRef, out: Path | None = None) -> ReviewPackage:
        """Write the review package for one Site version.

        ``out`` defaults to ``<project>/reviews/<site id>-v<version>``. The package
        holds the site, its validation report (JSON and Markdown, with the Owner's
        recorded statements), the site and terrain drawings, a review page, and
        the ``cad_import`` record(s) it was derived from. Writes no project state.
        """
        site = self.store.get(site_ref, Site)
        report = validate_site(site, site_ref)
        statements = owner_statements(self.store)
        out = out or self.store.root / "reviews" / f"{site_ref.id}-v{site_ref.version}"
        out.mkdir(parents=True, exist_ok=True)
        site_svg, terrain_svg = render_site_svg(site, report), render_terrain_svg(site, report)
        cad_inputs = [r for r in site.provenance.inputs if r.kind is ArtifactKind.CAD_IMPORT]
        cads = [self.store.get(r, CadImportProvenance) for r in cad_inputs]
        texts = {
            "site.json": pretty_json(site),
            "site-report.json": pretty_json(report),
            "site-report.md": report_markdown(report, statements),
            "site.svg": site_svg,
            "terrain.svg": terrain_svg,
            "index.html": render_review_html(site, report, site_svg, terrain_svg, cads, statements),
        }
        if cad_inputs:
            texts["cad-import.json"] = pretty_json(self.store.get(cad_inputs[0]))
        if len(cad_inputs) > 1:
            for r in cad_inputs:
                texts[f"{r.id}.json"] = pretty_json(self.store.get(r))
        files = []
        for name, text in texts.items():
            (out / name).write_text(text, encoding="utf-8")
            files.append(out / name)
        return ReviewPackage(out, files, site_blockers(site))
