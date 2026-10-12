# Open questions

Facts the design needs and does not have yet. Never fill these by guessing.

| # | Question | Needed for | Source that can answer it | Status |
|---|---|---|---|---|
| 1 | City / municipality / district or village of the site | municipal rules, submission format | user | **closed 2026-10-13**: Banavreh (Banehvreh), Paveh County, Kermanshah (owner). The coordinates agree under UTM 38N (`docs/site.md`). The Tehran elevation-zone limits no longer apply. |
| 2 | Survey DWG files and their CRS / units | footprint, levels, datum | sources/ | **closed 2026-10-13**: metres; up = north (owner). Zone UTM 38N inferred, consistent with Banehvreh. |
| 3 | Municipal conditions: coverage, height, setbacks, street widening | footprint limits | دستور نقشه from the municipality | **answered verbally** by the owner, 2026-10-13: no restrictions, wall allowed at the road line, 1 m alley strip on the south. No written دستور نقشه seen. |
| 4 | Structural system | grid, wall thicknesses | structural engineer | open |
| 5 | Qibla bearing at the site | WC orientation | computed from site coordinates | **computed**: true 204.75°, grid 203.97° (`scripts/measure_site.py`). Valid only if the CRS is 38N (#2). |
| 6 | Official Mabhas 4 (1396) PDF, to confirm every `transcribed` value in rules/iran.yaml | rule values | inbr.ir / local engineering organisation | open |
| 7 | 2.05 m vs 2.50 m (door height, beam clearance, stair headroom) | headroom checks | official Mabhas 4 | open |
| 8 | Area threshold for the 2.60 m room height (4-7-1-1-9) | clear height rule | official Mabhas 4 | open |
| 9 | Which Standard 2800 edition the permit is checked against (4th or 5th) | structural layout rules | engineering organisation / structural engineer | open |
| 10 | Fault-zone map for the plot (Zagros, Kermanshah region) and any setback | siting | Standard 2800 fault maps, structural engineer | open |
| 11 | Geotechnical report (soil, rock depth, slope stability, groundwater). **Critical: the plot falls about 37–38 % west to east (12.5 m over 32.6 m).** | foundations, retaining, cut/fill | geotechnical engineer | open |
| 12 | Land status: urban plot, garden (باغ), farmland or village plot | everything | deed, municipality | **closed 2026-10-13** (owner): "free land", building unrestricted. Not checked against a document. |
| 13 | Ground snow load zone (Mabhas 6) and seismic hazard level for the locality (Standard 2800) | roofs, structure | structural engineer | open |
| 14 | Is plot outline D7 (32.570 × 21.000 m parallelogram, 600.004 m²) the plot boundary? Plot number | boundary, envelope | owner | **closed 2026-10-13** (owner): no plot number; D7 is the plot. |
| 15 | Is the 1 m alley strip inside D7, measured square to the south side? | envelope | owner | **closed 2026-10-13** (owner): inside the plot, 1 m perpendicular to the south boundary; nothing left along the road. |
| 16 | Who surveyed, when, and on which height datum? Why do the two files differ by +0.49 to +0.89 m in Z at the corners? Which file's heights rule? | datum, levels | surveyor | **closed 2026-10-13**: private surveyor, date unknown. Owner delegated the fix; agent decision in `docs/decisions.md`. |
| 17 | What does "seperated" mean: a plot subdivided (تفکیک) from a larger parcel? | boundary status | owner, deed | open |
| 18 | Neighbours north and east: built or empty, heights, what is downhill to the east? | privacy, light, retaining, access | owner | **closed 2026-10-13** (owner): north, east and south are empty fields where houses may be built; only the west is the road. The view east over the town is the one to keep. |
| 19 | Parking: how many cars, covered, where? | entrance floor layout | owner | **closed 2026-10-13** (owner): Land Cruiser 300 + Peugeot 301, roofed, not open. Location is a design question. |
| 20 | Future accessibility: lift, shaft or accessible bedroom on the entrance floor? | stair/lift, program | owner | **closed 2026-10-13** (owner): a lift is built now; an accessible bedroom on the entrance floor is optional. |
| 21 | Formal guest room (پذیرایی) separate from family living? | program | owner | **closed 2026-10-13**: no guest room. A prayer room facing the qibla, with a wudhu place near it, is wanted. |
| 22 | Kitchen: what do its two open sides open onto? | kitchen layout | owner | **closed 2026-10-13**: one towards the entrance, one to dining; a full wall to living; a door to the balcony. |
| 23 | Toilets: Iranian, western or both? | wet rooms | owner | **closed 2026-10-13**: Iranian, plus at least one western. The number of bathrooms is left to the design. |
| 24 | Target floor area (زیربنا) or budget | program size | owner | **closed 2026-10-13**: no limit; size to what fits, neither oversized nor cramped. |
| 25 | Permanent home? Heating (gas available?), water tank, solar | services rooms | owner | **partly**: permanent home, mains gas available. Water tank and solar not answered (needed only at the final stage). |
| 26 | Laundry, storage, boiler / plant room, roof access | program | owner | **closed 2026-10-13**: laundry, storage and a boiler room. Boiler location (balcony or not) to be proposed by the agent. |
| 27 | Drawing labels (English / Persian / both), dimension unit | drawings | owner | **closed 2026-10-13**: Persian if the kit can, else English. The kit cannot shape Persian text yet, so sketches use English for now. |
| 28 | Reading of "free to not follow the rules" | how checks are treated | owner | **closed 2026-10-13** (owner): plot is outside the city limits, no municipal restrictions. Agent keeps the safety and comfort checks (stairs, headroom, daylight, seismic), as they serve the family; see `docs/decisions.md`. |
| 29 | Height datum and local origin | datum | owner | **closed 2026-10-13**: owner delegated; agent decision in `docs/decisions.md`. |
| 30 | Toilet axis vs qibla tolerance | WC layout | owner | **closed 2026-10-13** (owner): about 45° is fine (walls at 43.22° / 46.78° to the qibla line), so no special treatment of toilets. The road-parallel wall wedge is accepted. |
| 31 | Which Land Cruiser 300 does the owner have: market (Iran import, GCC, Japan) and trim? Lengths run from 4,950 to 5,145 mm. | garage depth | owner (registration card or the car's plate on the door pillar) | open. Until answered, the spec uses the largest values found: 5,145 × 1,990 × 1,945 mm (`docs/research.md`). |
| 32 | Which lift: a machine-room-less 630 kg lift (shaft about 1.6 × 1.75–1.9 m, pit 1.1–1.4 m, headroom about 3.4–3.7 m) or a home lift (cut-out 1.55 × 1.69 m, pit 0.1 m, headroom 2.5 m, slow)? | lift shaft, pit, roof over the shaft, cost | owner, then a supplier | open. Sketches reserve the Mabhas 15 suggested shaft, 1600 × 1900 mm. |
