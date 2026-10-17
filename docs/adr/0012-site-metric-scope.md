# ADR 0012: Report survey and parcel slope scopes explicitly

Status: accepted (site audit, 2026-10-17)

The survey TIN covers the survey's convex hull, including points outside the
parcel. Existing validation computed its horizontal-area-weighted slope
correctly, but downstream prose and the interview context presented it as a
parcel average. This can materially misdescribe the owner's land.

Keep `TerrainReport.mean_slope_pct` compatible as the whole-TIN statistic and
label its scope in Markdown, HTML and SVG. Add `parcel_mean_slope_pct` and
`parcel_tin_area_m2`: intersect each triangle with the parcel and weight its
unchanged planar slope by that horizontal intersection area. Uncovered land
contributes neither slope nor area. Without a covered parcel the mean is null.
Interview/program `SiteContext.mean_slope_pct` uses the parcel metric.

Retain all original vertices and triangles. Steep-triangle `inside_parcel` is a
centroid classification, labelled as such; it does not establish full containment.
Survey-wide spot ranges, interior-spot ranges, and extrema of the interpolated
parcel surface are different metrics and must not be interchanged.

The source-replay audit is a read-only review export, not a new canonical model.
It compares source entity geometry and referenced triangles rather than volatile
DXF byte hashes or vertex indices. Private source-backed numbers belong in the
private project review; offline tests use synthetic data.
