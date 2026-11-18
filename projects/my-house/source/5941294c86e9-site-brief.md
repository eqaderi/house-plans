# Architectural site brief — 20 October 2026

Agent interpretation of the homeowner's site description, written in architectural terminology at the homeowner's request. This is a technical synthesis, not a verbatim owner statement. Owner-reported conditions are distinguished from survey calculations and provisional assumptions.

## Parcel geometry and orientation

The parcel is a **parallelogram**, approximately **600.00 m²** in horizontal plan, bounded by two **21.00 m** short sides and two **32.57 m** long sides. Adjacent sides meet at approximately **61.31° / 118.69°**. These are calculated from survey boundary `seperated.dwg#D7`, stored as site v1. They are plan dimensions, not lengths measured along the sloping ground.

The short western road frontage and eastern boundary run approximately north-northeast–south-southwest (northward bearing **6.65° true**). The long northern and southern boundaries run approximately east-northeast–west-southwest (downhill/view-axis bearing **67.97° true**, about **22.03° north of east**). Bearings are calculated using owner-supplied **EPSG:32638**, with units declared in the CAD. Formal site confirmation remains pending; no CRS has been guessed or confirmed by the agent.

## Access and adjacent plots

- **West / uphill:** primary access from the adjoining road. The homeowner reports a **9 m overall corridor**, comprising **8 m asphalt carriageway plus a 1 m sidewalk on the parcel side**. Survey polylines `BC` and `C5` independently measure 9 m apart; the 8+1 division is owner-reported and its exact alignment is not separately surveyed.
- **South:** adjoining residential plot expected to be developed. A possible **secondary pedestrian gate** would open into an approximately **2 m passage**, formed by a 1 m strip on this parcel and a matching 1 m strip on the southern neighbor's parcel. This is a potential shared passage, not a second vehicular frontage. Continuity to the western road and agreed access across the neighbor's strip remain open.
- **North:** adjoining residential plot expected to be developed; no independent access is identified there.
- **East / downhill:** lower parcel boundary. No access or adjoining ownership/use has been established there.

A primary entrance from the western road is established as the owner's intent. Exact gate positions, parking level, ramp grades, and step-free routes are not specified by this description.

## Owner-reported no-build strips

Reserve **1 m inside the eastern boundary** and **1 m inside the southern boundary** as no-build strips. The southern strip also forms the owner's half of the proposed pedestrian passage. These requirements are owner-reported design inputs; their statutory basis and permitted treatments have not been independently checked. Do not place the house or other structures in them without resolving their scope.

The geometric basis is awaiting clarification: does 1 m mean perpendicular to the boundary, or a due-west/due-north shift? With **perpendicular** offsets, and applying only these two strips, the residual polygon has side lengths approximately **19.86 m × 31.43 m**, with plan area **547.57 m²**. It remains a skewed parallelogram. This is a conditional geometric remainder, not an approved building footprint, permitted floor area, or coverage allowance. The canonical buildable envelope stays unset while the measurement basis is unresolved. The legal parcel boundary is unchanged.

## Topography and view

The homeowner identifies the western frontage as uphill and the east-northeast direction along the long boundaries as the principal downhill **city-view axis**. The survey is consistent with a steep drop from west to east: surveyed points within the parcel span **12.554 m** in elevation; the parcel-clipped TIN gives a horizontal-area-weighted mean slope of **40.68%** and interpolated relief of about **12.712 m**. These are different measurement definitions. The view axis is owner-reported; it is not a measurement of the terrain's exact steepest descent.

**Design implications (agent judgment):** assess road access and accessible entry from the upper western edge; orient principal outlooks and outdoor living toward the east-northeast view; account for future overlooking and daylight obstruction from both neighboring residential plots; preserve the two no-build strips and investigate the southern pedestrian route. Ground-level access, retaining, excavation, drainage and lift connections must follow the surveyed terrain. No house geometry has been generated.

## Open items

1. Whether the southern passage connects continuously to the western road and whether use of the neighbor's half is agreed.
2. How the 1 m setback widths are measured. The diagram shows perpendicular offsets only as an illustrative assumption.
3. Existing formal site verification items: units/CRS confirmation, vertical reference and legal boundary verification. This briefing neither confirms them nor approves a workflow gate.

[Site diagram](site-context.svg) · [Calculated geometry](geometry.json)
