# Elevation schematic — 20 October 2026

[Elevation schematic (PNG)](site-context-elevations.png) · [Scalable SVG](site-context-elevations.svg) · [Calculation evidence](elevation-evidence.json)

The elevation version retains the established context schematic and derives its terrain from canonical **site v3**, pinned by its artifact hash in `elevation-evidence.json`. The original `site-context.svg/png` is preserved. No site, boundary, terrain, access, setback or workflow state was changed to create this view.

- **Blue dots:** the 16 measured spot heights inside/on the current parcel. Six are labelled, to two decimals for legibility; SVG tooltips and the evidence file retain the underlying values and source identifiers.
- **Warm-to-cool shading:** ground elevation calculated by linear interpolation on the stored survey TIN. Quarter-meter colour bands are clipped to the parcel, with warm colours higher and cool colours lower. These are elevation colours, not slope classes or proposed grading.
- **Dashed thin contours:** calculated at 2 m elevation intervals, from 1666 to 1676 m. The darker orange dashed polygon remains the setback envelope.
- **A–A′:** section along the parcel centerline, connecting midpoints of the western and eastern boundaries. Its kinks come from exact intersections with TIN triangle edges. Horizontal and vertical scales are equal: no vertical exaggeration or smoothing.

The measured interior spot range is **1664.884–1677.438 m**, a **12.554 m** difference. The section runs **32.570 m** horizontally, from interpolated **1677.452 m** at A to **1665.578 m** at A′: **11.874 m** drop, or **36.46%** mean grade along this particular line. The section does not pass through the highest and lowest measured interior spots, so its drop is not the total parcel relief. It is also distinct from the existing **40.68%** parcel-area-weighted mean TIN slope.

The TIN covers **599.840341 m²** of the **600.004421 m²** current parcel: **0.164080 m²** has no terrain interpolation and uses a hatch rather than an extrapolated height. Survey heights are retained unchanged; precise vertical datum and formal site verification remain pending.

Checks in the renderer assert that every drawn contour-segment endpoint returns its target elevation from the canonical TIN, and that every section point lies within its interpolation coverage. `elevation-evidence.json` records measured heights, calculated contour segments, profile coordinates, coverage and the pinned input artifact.

Regenerate from the repository root:

```bash
.venv/bin/python projects/my-house/reviews/site-context-2026-10-20/render_elevations.py
rsvg-convert -w 2200 projects/my-house/reviews/site-context-2026-10-20/site-context-elevations.svg -o projects/my-house/reviews/site-context-2026-10-20/site-context-elevations.png
```
