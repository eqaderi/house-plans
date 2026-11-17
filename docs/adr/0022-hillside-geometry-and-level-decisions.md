# ADR 0022: Hillside quantities, true cuts and coupled level decisions

Status: accepted (Stage S8, closed 2026-10-19)

## Context

Stage S8 replaces grid-sampled earthworks, projected floor bands and the
±3 m inter-bar level clamp. DEC-04 permits deep excavation: neither less cut
nor more elevation is an automatic design goal. Quantities must distinguish
excavation, proposed engineered fill and empty space under floors.

## Decision

Keep the canonical LOCAL-metre model. Add proposed `EarthworkPad` polygons
with formation elevations and an explicit basis; overlapping pads, pads
above floors and pads outside a known parcel fail model integrity. Empty
new fields are omitted on serialization to preserve existing store hashes.
`TerrainBreakline` holds explicitly mapped surveyed 3D linework, never a
height guessed from a label or a role guessed from a layer name.

Use clipped TIN triangles and affine integration for production quantities
(`geospatial/earthworks.py`). The integral over each clipped polygon is its
area times the affine height at its centroid. Split at the design height
before integrating positive/negative parts. Resolve overlapping floor
projections from the lowest level upwards. Slab undersides define clear
space where canonical floor/terrace slabs exist; missing slabs use explicitly
labelled finished-floor upper bounds. Formation pads are separate proposals:
engineered fill is **not checked** when no pad is specified. Footings, soil
bulking, compaction, batter, temporary works and working space are excluded.

Retain an independent Trimesh/Manifold Mesh64 adapter, as adopted/adapted in
S3. It closes a TIN to an explicit computational base and intersects closed
footprint prisms. Analytical slope, wedge and pyramid integrals agree with
mesh booleans within 1e-7 m³. A stepped formation-pad fixture independently
checks cut, fill and remaining void. Vendor objects never enter domain types.

Terrain coverage is the union of the actual triangles, including holes and
disconnected support. Footprint areas and section intervals outside support
remain unknown. Overlapping XY triangles fail quantity evaluation explicitly;
near-zero triangles are excluded from integration, while sliver/steep
triangles remain visible as review findings rather than being smoothed away.

Mapped breaklines insert surveyed endpoints, split intersected TIN cells,
then triangulate each polygonal cell with constrained boundary edges. This
is labelled `constrained_tin`, not a claim of globally constrained Delaunay
optimality. Crossing heights must agree; vertical discontinuities and
constraints that cannot be enforced produce conflicts and no surface. A
mapped breakline without a built surface never falls back to unconstrained
Delaunay. Shapely >=2.1 supplies polygon constrained triangulation.

For bar layouts, the **same CP-SAT model** chooses space placement, bar start,
bar length and floor Z. `2*start + length` indexes surveyed centre/face
heights at 5 cm XY and 1 cm Z resolution. The entry follows the road-side
face. Other levels obey declared sectional contact bands and stacked/stepped
link topology. There is no ±3 m clamp and no excavation/void-volume cost.
Circulation rise and window burial can influence the solution. These are
conceptual design assumptions, not engineered levels or a continuous global
optimum. Six massings retain their existing topology choices; optional
walkout, split-level, stepped, elevated and hybrid sectional intents expose
further comparisons. S10-13 extends the free 2D engine with the same coupled road-side entry
lookup (5 cm XY / 1 cm Z): its entrance is constrained to the road-facing
envelope band and its stacked levels retain 3 m rises above/below that solved
entry. It still refuses a sectional-intent request rather than silently
ignoring it; free stepped 2D levels remain unsupported. Terrain gaps in the
entry band cause infeasibility, rather than an invented surveyed height.

True sections intersect a configurable vertical plane with wall thickness,
wall openings, slabs (including holes), stairs with known walking lines and
riser counts, and individual terrain facets. Missing stair orientation stays
unknown. U-shaped stairs whose flights/landings have not been modelled do
not acquire invented section geometry. Standard cuts go through the long and
short axes, each stair, garage and exterior door. Facade views are separately
labelled orthographic projections in LOCAL axes; hidden-line removal and
true geographic orientation are not claimed.

Export `sections.json/svg`, `elevations.json/svg`, `hillside.json` and
`engineering-risks.md` alongside every plan option. Risks retain canonical IDs
and mark structure, foundations, retaining, drainage, waterproofing and
slope stability as **needs professional**. Exterior thresholds sample 0.5 m
outside the door. Garage ramp metrics describe an unchecked straight
candidate approach to the nearest frontage; no turning, vertical-curve,
clearance or legal-access feasibility is implied. Terrace edges preserve
piecewise ground profiles, signed deltas and candidate at-grade contact.

## Consequences and evidence

`tests/test_hillside_earthworks.py`, `test_hillside_views.py` and
`test_hillside_levels.py` cover numerical integrals, independent mesh booleans,
slab-underside gaps, partial terrain, sections/openings, breakline mapping,
road-high/road-low coupled decisions, large void triggers and extreme slopes.
`examples/hillside/run_demo.py` generates synthetic plan options and their
risk register without writing project state or crossing approval gates.

Quantities remain **inferred** because survey interpolation and design
assumptions are involved, even when integration is exact for that TIN.
Human approval, architectural quality and professional engineering remain
separate checks.
