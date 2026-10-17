"""What the interview and the program may say about the site, and how sure it is."""

from __future__ import annotations

from shapely.geometry import Point

from house_ai.domain.interview import SiteContext
from house_ai.domain.provenance import ArtifactKind, ArtifactRef
from house_ai.domain.site import Site
from house_ai.domain.workflow import Approval
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


def latest_site_context(store: ProjectStore, approval: Approval | None) -> SiteContext | None:
    """The approved site if there is one, else the newest site version, else None."""
    ref = approval.artifact if approval is not None else None
    if ref is None:
        refs = store.latest_of_kind(ArtifactKind.SITE)
        ref = refs[-1] if refs else None
    if ref is None:
        return None
    return site_context_for(store.get(ref, Site), ref, approval)
