# Architectural site brief — 20 October 2026

Agent interpretation of the homeowner's site description, written in architectural terminology at the homeowner's request. This is a technical synthesis, not a verbatim owner statement. Owner-reported conditions are distinguished from survey calculations and provisional assumptions.

The homeowner has now clarified that both 1 m setbacks are measured perpendicular to their respective boundaries, and that the full 2 m southern passage connects continuously to the western road with agreed shared pedestrian access. These are owner-confirmed design inputs in chat; formal survey/legal verification remains separate.

## Parcel geometry and orientation

The parcel is a **parallelogram**, approximately **600.00 m²** in horizontal plan, bounded by two **21.00 m** short sides and two **32.57 m** long sides. Adjacent sides meet at approximately **61.31° / 118.69°**. These are calculated from survey boundary `seperated.dwg#D7`, stored as site v1. They are plan dimensions, not lengths measured along the sloping ground.

The short western road frontage and eastern boundary run approximately north–south (northward bearing **6.65° true**). The long northern and southern boundaries run approximately east-northeast–west-southwest (downhill/view-axis bearing **67.97° true**, about **22.03° north of east**). Bearings are calculated using owner-supplied **EPSG:32638**, with units declared in the CAD. Formal site confirmation remains pending; no CRS has been guessed or confirmed by the agent.

## Access and adjacent plots

- **West / uphill:** primary access from the adjoining road. The homeowner reports a **9 m overall corridor**, comprising **8 m asphalt carriageway plus a 1 m sidewalk on the parcel side**. Survey polylines `BC` and `C5` independently measure 9 m apart; the 8+1 division is owner-reported and its exact alignment is not separately surveyed.
- **South:** adjoining residential plot expected to be developed. A **secondary pedestrian gate** can access an approximately **2 m shared passage**, formed by a 1 m strip on this parcel and a matching 1 m strip on the southern neighbor's parcel. The homeowner confirms a continuous connection to the western road and agreed shared pedestrian use of its full width. This establishes the access arrangement as an owner-confirmed design input; no documentary easement or independent legal verification has been recorded. The exact gate location remains a design decision.
- **North:** adjoining residential plot expected to be developed; no independent access is identified there.
- **East / downhill:** lower parcel boundary. No access or adjoining ownership/use has been established there.

A primary entrance from the western road is established as the owner's intent. Exact gate positions, parking level, ramp grades, and step-free routes are not specified by this description.

## Owner-reported no-build strips

Reserve **1 m inside the eastern boundary** and **1 m inside the southern boundary** as no-build strips. The southern strip also forms the owner's half of the proposed pedestrian passage. These requirements are owner-reported design inputs; their statutory basis and permitted treatments have not been independently checked. Do not place the house or other structures in them without resolving their scope.

The homeowner confirms that both offsets are **measured perpendicular to the respective boundary**. Applying these two 1 m strips to the surveyed parallelogram gives a setback envelope with side lengths approximately **19.86 m × 31.43 m** and horizontal plan area **547.57 m²**. It remains a skewed parallelogram. This calculated envelope is now recorded in canonical site v3 as an **inference**, derived from the current boundary and owner-confirmed design constraints. It does not establish permitted coverage, total floor area, height limits, or an approved building footprint. Formal site verification and any other applicable controls remain pending. The legal parcel boundary is unchanged.

## Topography and view

The homeowner identifies the western frontage as uphill and the east-northeast direction along the long boundaries as the principal downhill **city-view axis**. The survey is consistent with a steep drop from west to east: surveyed points within the parcel span **12.554 m** in elevation; the parcel-clipped TIN gives a horizontal-area-weighted mean slope of **40.68%** and interpolated relief of about **12.712 m**. These are different measurement definitions. The view axis is owner-reported; it is not a measurement of the terrain's exact steepest descent.

**Design implications (agent judgment):** assess road access and accessible entry from the upper western edge; orient principal outlooks and outdoor living toward the east-northeast view; account for future overlooking and daylight obstruction from both neighboring residential plots; preserve the two no-build strips and provide for the agreed southern pedestrian route. Ground-level access, retaining, excavation, drainage and lift connections must follow the surveyed terrain. No house geometry has been generated.

## Remaining design and verification items

- Exact western entrance and southern gate locations, parking level, path gradients and accessible routes are design decisions still to be developed.
- Existing formal site verification items remain: units/CRS confirmation, vertical reference and legal boundary verification. This briefing does not approve a workflow gate or independently verify a legal easement.
- Setback measurement direction and the southern passage's continuous connection/agreed shared use are resolved by the homeowner's clarification; they are no longer open questions.

[Site diagram](site-context.svg) · [Calculated geometry](geometry.json)
