# Garden-led house siting advice — 20 October 2026

**Status: preliminary architectural judgment and inferred terrain screening. This is an advisory study, not a generated/approved floor plan or grading design.** Project records are in English; the homeowner-facing explanation is in Persian. No site, program or plan gate was approved, and no building geometry was written into the canonical house model.

## Owner priorities and existing brief

The owner wants a generous usable garden and children's play area, a city outlook with substantial trees in the foreground, the sound/movement of leaves in wind, and enjoyment of the garden in rain. A continuous nearly level play surface, with as few outdoor level changes as feasible, is strongly preferred. Previous acceptance of retaining walls/excavation remains subject to feasibility. The owner asks for advice about location, footprint, storeys and garage placement; they have **not selected a storey count or accepted the recommendation below**.

The latest interview answer and English structured priorities are recorded as interview/brief v23. The priority interpretation remains an inference pending homeowner confirmation. Existing requirements include four bedrooms for a household potentially including grandparents, a lift, and a closed two-car garage for a large SUV and a medium sedan. These are carried forward, not replaced with a generic small-house brief. Floor count, total floor area, and budget remain undecided in the canonical interview.

The prior space program is a starting reference, not an approved program: enclosed target net area totals about 209.5 m² including the older 36 m² garage target, before its 20% circulation allowance. Comfort improvements, external walls, a larger comfortable two-car garage and actual vertical circulation need a fresh layout/area audit. The area bands below are working recommendations, not a new fixed owner area requirement.

## Recommended starting position — architectural judgment

Start with a **compact house in the uphill western part, biased toward the northern side**, keeping meaningful open land to its south and east. Keep the road-level garage/entrance at the western edge and avoid spreading the main volume across the full frontage. The long dimension should respond to the surveyed contours where workable; east/east-northeast-facing living outlooks should be paired with useful southern solar access, rather than treating the view direction as the sole orientation criterion.

This is a search area for the next concept comparison, not an exact footprint or a direction to build on the northern boundary. Required north/west clearances, height/coverage restrictions, road-entry geometry, future neighboring buildings, and geotechnical findings remain to be resolved.

Why this is the preferred starting point:

- A short connection to the only vehicular road preserves land and avoids a long downhill driveway. The southern passage is agreed **pedestrian** access, not a second car frontage.
- It lets the house look over its own garden and lower planting toward the city. A house at the lowest eastern end would put much of its garden uphill behind it.
- A northern bias preserves a more continuous southern/southeastern garden and opportunities for winter sun. This is inferred orientation logic, not a shadow simulation or a guarantee of sunshine hours.
- Compact stacked accommodation preserves a larger connected outdoor area than spreading the current four-bedroom household brief across one broad slab.
- Future side neighbors make inward/downhill outlooks and a garden-facing living level valuable. Actual setbacks and overshadowing still require testing.

## Alternatives to compare

| Position | Potential benefit | Concern for this brief | Current judgment |
|---|---|---|---|
| Upper-west, biased north | Direct road garage; house overlooks own downhill garden; more continuous south/east open land | Uphill excavation and afternoon self-shadowing; north-west survey edge anomaly requires checking | Preferred first study |
| Central | May align a living floor with intermediate terrain | Splits garden, lengthens road connection and may require bridging/ramp/cut | Useful comparator if geotechnical constraints favor it |
| Low-east | Direct connection to lowest ground; potentially less fill immediately below house | Long/steep vehicle access, more garden uphill behind house, reduced garden foreground to city | Least aligned with present priorities |

This is not a cost ranking: soil/rock, slope stability, foundation systems, retaining/drainage design and local construction rates are unknown.

## Initial area bands — working targets, not measured feasibility

- **Combined projected footprint of house and enclosed garage: roughly 160–180 m² as a first target.** This means the union of their ground projections, not the sum of stacked floor areas. Actual overlap between the garage and residential floors must be established in the layout. If more is needed, test the garden consequences rather than silently enlarge it.
- **Total enclosed gross floor area: roughly 280–320 m², including the garage.** This is a starting comparison range for the current family brief, not a committed budget/area or a solver-validated fit.
- **Closed two-car garage: roughly 45–50 m² as a comfort target**, with vehicle turning, apron, door operation and pedestrian entry checked separately. It is included in the preceding totals.
- **Main continuous play/garden platform: aim initially for 100–150 m²**, connected directly to the day/living level where feasible. The rest of the outdoor land includes access, retaining/drainage, terraces and planted slope; subtracting the footprint from parcel area does not make all of the remainder a flat garden.

## Section, storeys and garage — the critical distinction

Start from **two principal residential levels**, with the **garage and accessible entrance at road level**. The day/living floor should open to the main garden platform; a generous living room, kitchen/dining, a sheltered outdoor sitting terrace and visual supervision of play belong together. A garden-facing grandparents' room with a full accessible bathroom is worth testing on that level. Other bedrooms can occupy the level above; the accepted lift connects the required levels.

**Two residential levels does not necessarily mean two levels in total including the garage.** For the preferred downhill main garden, a smaller road-level garage/entrance tier may sit above both residential levels: three access elevations in section. The garage tier need not be a full third residential floor. Compare this with a two-level-total variant in which the garage shares the upper residential floor; the latter may need a different garden position, a larger vertical interval, a lower separate garden terrace, or more earthworks. Do not present a standard one-storey drop as automatically reaching the desired garden.

The garage's actual floor elevation, door threshold and approach grade require road-edge spot/kerb verification. The west-boundary reference used below is not a surveyed garage finished-floor level.

## What the terrain screening establishes

[Calculation evidence](terrain-screening.json) is pinned to canonical site v3 and reproduced by `analyse_siting.py`. Three **equal 115.20 m² analytical windows** in the southern part of the parcel were shifted downhill. They are entirely inside the current setback envelope and fully covered by the stored TIN. They are sampling regions, **not proposed construction pads or a demonstration that a particular house and garden fit simultaneously**.

Each horizontal plane in the following table is set to that window's area-weighted mean existing ground level, giving equal *geometric* cut-above and space-below-plane volumes. It assumes neither suitable fill material nor a construction method.

| Sampling region | Mean existing ground | Below west-boundary midpoint | Maximum cut / space below plane at this plane |
|---|---:|---:|---:|
| Upper southern window | 1672.86 m | 4.59 m | 1.76 / 1.94 m |
| Middle southern window | 1671.51 m | 5.94 m | 1.74 / 2.00 m |
| Lower southern window | 1670.16 m | 7.29 m | 1.78 / 1.89 m |

The reference is the TIN-interpolated **western parcel-boundary midpoint at 1677.452 m**. The middle example shows why a play surface of this scale may naturally lie about six metres below entry-side ground, making an additional garage/entry tier worth testing. Upper placement may reduce this difference but competes with house/access area. These windows do not establish an optimal position or final floor levels.

The same evidence includes hypothetical planes 3.2 m and 6.4 m below that west reference. Bringing a middle/downhill platform up to a conventional single-storey-below-entry elevation can create substantial space below it, which must not be casually described as a cheap level garden. Volumes omit soil swell/shrink, unsuitable material, foundations, drainage, retaining-wall geometry, working space, temporary works and actual structural supports. Max cut/space below plane is **not** a designed retaining-wall height.

A separate arithmetic access illustration: a hypothetical 12 m descent at an assumed 15% ramp grade requires 80 m horizontal run, before turns/transitions. The parcel's long side is 32.57 m. **15% is an illustrative assumption, not an asserted permitted or suitable local driveway gradient.** This supports investigating a road-level garage before a downhill garage.

## Garden, trees, rain and outdoor level changes

Prioritize **one generous continuous play lawn/paved play surface** rather than many narrow retaining-wall terraces. Give this surface comfortable drainage falls; do not form a basin. Connect the day room and sheltered sitting terrace to it without steps where possible. Use lower planted terrain and, if justified, a second broad garden terrace for the remaining fall. The 12.55 m measured spot range cannot disappear through a few shallow steps: fewer garden platforms may still require substantial level differences, stairs/lift access and engineered retaining/drainage.

Place substantial trees in the downhill foreground and toward the edges of key view corridors, leaving selected gaps so their mature canopies frame the city instead of forming a solid screen. A sheltered sitting position close enough to experience leaves, wind and rain is part of the design objective. Candidate deciduous, locally suitable trees need a check for mature height/spread, winter shading, summer irrigation, rooting volume, soil and safe separation from foundations, drains and retaining structures. Species, quantities, planting positions and fixed distances are **not selected**. Neither the 1 m eastern setback strip nor fill immediately behind a retaining wall is assumed to be an adequate large-tree rooting zone.

## Sun, climate and wind — evidence and limits

The saved [location/environment study](../location-research/epsg-32638-preview/REPORT.md) used the owner-supplied CRS and recognized map location. It places the site in the Paveh/Zagros context. Existing simulations put winter/summer solar-noon altitude at approximately **31.6° / 78.5°**, and the modeled mountain horizon at **7.6–17.2°**. Future houses, trees and our proposed walls are absent from that horizon model. Check proposed massing and retaining levels against winter morning/noon/afternoon sun before final siting.

Architectural inference for this northern-hemisphere site: south-facing solar opportunities should complement the ENE city view, with controllable summer shading and a well-insulated envelope. A northern-biased house can preserve southern garden opportunities, but a western/uphill house may shade the eastern garden later in the day. Future southern neighbors can also shade it. No all-year sunshine-hours claim is made.

Regional NASA data indicate a cold-winter/hot-dry-summer contrast and predominantly east/west flows in the one analyzed wind year. This is coarse regional evidence, not measured on-site wind, local gusts or structural design weather. It supports flexible outdoor shelter and controllable ventilation, not assigning the footprint from a single prevailing-wind arrow. Rainfall design intensity and extreme wind/snow values remain unverified.

## Decision limits and next comparison

The recommendation is a reasoned starting point, not proof of the best or cheapest solution. Before fixing footprint and floor levels, compare (1) a compact two-residential-level house with a smaller road garage tier and (2) a two-level-total arrangement with integrated upper garage, using one explicit 100–150 m² play-garden target. Check cut/fill, exposed/retained heights, accessible connections, winter shadows, trees at maturity, and actual plan fit. A central alternative becomes important if the geotechnical findings oppose the preferred zone.

Site/program gates remain pending; actual floor-plan comparisons must use the permitted exploratory workflow until approved. No room coordinates, legal permissions, structural adequacy, costs or gate approval have been invented. The steep close-point pair near the north-west survey edge remains a surveyor/geotechnical review item, not smoothed away.

## Primary references checked for this advice

These support general principles, not Iranian planning permission or local structural certification:

- [US Department of Energy: passive solar home design](https://www.energy.gov/sites/default/files/2021-08/ES-Passive%20Solar%20design_081321.pdf) — winter solar access and seasonal shading, adapted to this northern-hemisphere site.
- [Australian Government Your Home: choosing and using a site](https://www.yourhome.gov.au/buy-build-renovate/choosing-site) — respond to contours, reduce unnecessary cut/fill, assess geology, drainage, access and neighboring shade. Australian north-facing solar recommendations are hemisphere-specific and are not copied to Iran.
- [NASA POWER wind methodology](https://power.larc.nasa.gov/docs/methodology/meteorology/wind/) and the saved regional environmental report — limits of regional wind evidence.
- [Colorado State University Extension: tree placement](https://extension.colostate.edu/resource/tree-placement-right-plant-right-place/) — mature growing/rooting space and solar consequences.
- [RHS: trees near buildings](https://www.rhs.org.uk/plants/types/trees/near-buildings) — soil/root/drainage interactions and species selection; UK legal content is not applied here.
