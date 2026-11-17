"""What the interview and the program may say about the site, and how sure it is."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import Point

from house_ai.domain.interview import SiteContext
from house_ai.domain.provenance import ArtifactKind, ArtifactRef
from house_ai.domain.site import Site, site_blockers
from house_ai.domain.workflow import Approval, Blocker
from house_ai.geospatial.validation import validate_site
from house_ai.storage import ProjectStore


def site_context_for(site: Site, ref: ArtifactRef, approval: Approval | None) -> SiteContext:
    """Site values for the interview. ``verified`` only if the approval pins this version."""
    report = validate_site(site, ref)
    relief = None
    spots = site.terrain.spot_elevations
    if spots:
        if site.boundary is not None:
            parcel = site.boundary.to_shapely().buffer(1e-6)
            inside = [s.z_m for s in spots if parcel.covers(Point(s.xy))]
        else:
            inside = []
        zs = inside or [s.z_m for s in spots]
        relief = max(zs) - min(zs)
    def r(value: float | None, digits: int = 3) -> float | None:
        # A summary for conversation, not geometry: rounding also keeps it identical across
        # Python versions (3.12 changed float summation).
        return None if value is None else round(value, digits)

    return SiteContext(
        site_ref=ref,
        verified=approval is not None and approval.artifact.model_dump() == ref.model_dump(),
        parcel_area_m2=r(report.boundary.area_m2),
        relief_m=r(relief),
        mean_slope_pct=r(report.terrain.parcel_mean_slope_pct, 2),
        frontage_m=r(report.frontage.length_m) or None,
    )


def _summary_ref(store: ProjectStore, approval: Approval | None) -> ArtifactRef | None:
    if approval is not None:
        return approval.artifact
    refs = store.latest_of_kind(ArtifactKind.SITE)
    return refs[-1] if refs else None


def latest_site_context(store: ProjectStore, approval: Approval | None) -> SiteContext | None:
    """The approved site if there is one, else the newest site version, else None."""
    ref = _summary_ref(store, approval)
    if ref is None:
        return None
    return site_context_for(store.get(ref, Site), ref, approval)


#: What a steep Parcel asks the program to consider (agent contract §7).
STEEP_HILLSIDE_CONSIDERATIONS: tuple[str, ...] = (
    "Split-level layouts stepping with the slope",
    "Hillside construction and stepped foundations",
    "Road access and parking at the road frontage",
    "Excavation volume and rock/earthwork limits",
    "Retaining walls along cut and fill zones",
    "Surface and subsurface slope drainage",
    "Structural implications on steep grade",
    "Full parcel area is not assumed buildable (setbacks and coverage rules pending)",
)


@dataclass(frozen=True)
class SiteSummary:
    """The Site as agents read it: its values, how sure they are, and what blocks the gate.

    Built once by :func:`site_summary`; project status, the interview checklist
    and the AI context all read this one record, so they cannot disagree.
    """

    context: SiteContext = field(default_factory=SiteContext)
    blockers: list[Blocker] = field(default_factory=list)

    @property
    def exists(self) -> bool:
        return self.context.site_ref is not None

    @property
    def steep(self) -> bool:
        c = self.context
        return self.exists and ((c.relief_m or 0.0) >= 8.0 or (c.mean_slope_pct or 0.0) >= 20.0)

    def to_json(self) -> dict[str, Any]:
        c = self.context
        return {
            "site_ref": c.site_ref.model_dump(mode="json") if c.site_ref else None,
            "verified": c.verified,
            "parcel_area_m2": c.parcel_area_m2,
            "relief_m": c.relief_m,
            "mean_slope_pct": c.mean_slope_pct,
            "frontage_m": c.frontage_m,
            "verification_blockers": [b.message for b in self.blockers],
            "blockers": [b.model_dump(mode="json") for b in self.blockers],
            "steep_hillside": self.steep,
            "hillside_considerations": list(STEEP_HILLSIDE_CONSIDERATIONS) if self.steep else [],
        }

    def ai_json(self) -> dict[str, Any]:
        """What the AI may know about the Site when wording a question."""
        c = self.context
        return {
            "status": "confirmed by the owner" if c.verified
            else "from the survey; NOT yet confirmed by the owner",
            "parcel_area_m2": c.parcel_area_m2,
            "relief_m": c.relief_m,
            "mean_slope_pct": c.mean_slope_pct,
            "frontage_m": c.frontage_m,
        }  # fmt: skip


def site_summary(store: ProjectStore, approval: Approval | None) -> SiteSummary:
    """The approved Site if there is one, else the newest Site version; empty without one."""
    ref = _summary_ref(store, approval)
    if ref is None:
        return SiteSummary()
    site = store.get(ref, Site)
    return SiteSummary(site_context_for(site, ref, approval), site_blockers(site))
