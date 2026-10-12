# Decisions

One entry per decision: date, what was decided, why, who decided, and which
warnings it explains.

## 2026-10-13: brief from the owner

- **What:** the owner's answers entered into `docs/brief.md`: site and
  location, the road and the alley strip, household, bedrooms, kitchen, WCs,
  duplex and outdoor wishes.
- **Who:** owner (answers); agent (transcription, no additions).
- **Why:** phase 0 intake.

## 2026-10-13: site reading (agent, pending owner/surveyor confirmation)

- **What:** survey files assumed to be UTM 38N (EPSG:32638), metres.
  Heights come from `height-points.dxf` until the 0.5–0.9 m disagreement
  with `seperated.dxf` is explained. Datum and origin are proposed in
  `docs/site.md`, not adopted.
- **Who:** agent.
- **Why:** 38N puts the plot beside Banehvreh's listed coordinates (34.97056 N, 46.36000 E);
  39N puts it in another province. `height-points.dxf` carries the benchmark
  and labelled Z values.

## 2026-10-13: owner answers on site, parking and lift

- **What:** brief updated with the owner's answers:
  - The plot is the surveyed outline D7; it has no plot number.
  - A 1 m strip inside the plot along the south boundary, measured
    perpendicular to it, stays unbuilt for the alley. Nothing is left along
    the road.
  - Up is north on the drawings.
  - Roofed parking for a Land Cruiser 300 and a Peugeot 301.
  - A lift is built now.
  - The plot is outside the city limits, with no municipal restrictions.
- **Who:** owner.

## 2026-10-13: survey heights and datum (delegated to the agent by the owner)

- **What:**
  - Plan geometry (road edges, plot outline) comes from `seperated.dxf`.
  - All heights come from `height-points.dxf`; the Z values in
    `seperated.dxf` are not used.
  - The height reference is the benchmark `نقطه مبنا` (Z 1677.462). ±0.00
    is chosen in phase 3 as a surveyed Z.
  - The local origin is plot corner V3 (SW, road and alley), at
    E 623809.167, N 3870456.033.
  - Spec axes: x east, y north (grid). Grid north is 0.778° east of true
    north.
- **Why:**
  - The files agree in plan: each D7 corner has a `height-points` point
    0.055–0.215 m from it (`scripts/measure_site.py`).
  - They disagree only in Z (+0.494 m and +0.892 m), which points to
    different height references.
  - `height-points.dxf` carries the benchmark and labelled heights, and its
    road-edge points sit close to its corner heights.
  - V3 is where both entrances (road and alley) meet.
- **Who:** agent; the owner delegated it ("fix them yourself", "whatever you
  think is best").
- **Follow-up:** before levels are set out on site, the builder checks the
  corner heights against the benchmark with a level.

## 2026-10-13: which rules stay active

- **What:** municipal limits (coverage, height, setbacks) are not applied;
  the owner says there are none. The building-safety and comfort checks in
  `rules/iran.yaml` stay active: stairs, headroom, railings, daylight,
  ventilation, and seismic design (Standard 2800).
- **Why:** these rules protect the family who will live here for 20 years,
  which is the owner's own aim ("built in a way that just benefits us").
  `AGENTS.md` forbids weakening checks and requires an engineer's sign-off.
- **Who:** agent, following the owner's statement.

## 2026-10-13: owner answers on neighbours and program

- **What:** brief updated with the owner's answers:
  - Neighbours on north, east and south may build later.
  - The east view is to be kept.
  - No guest room; a prayer room facing the qibla, with a wudhu place
    nearby.
  - The kitchen's two open ends face the entrance and the dining area.
  - Iranian toilets plus at least one western.
  - No area or budget limit.
  - Mains gas is available; laundry, storage and a boiler room are wanted.
  - Persian labels if the kit can render them.
- **Who:** owner.
- **Note:** the drawing kit has no Persian text shaping (no
  `arabic_reshaper`/`python-bidi`, no Persian font setting). Sketches use
  English until the kit is extended.

## 2026-10-13: toilets must not face or back the qibla

- **What:** an owner requirement. Every toilet's axis must keep clear of the
  qibla line, grid 203.97° / true 204.75°.
  - Measured: walls parallel to the road side are 18.09° off the qibla
    line, so a toilet set along them would face or back it.
  - Walls parallel to the north and south sides are 43.22° off.
  - The safest toilet axis is perpendicular to the qibla: grid 113.97° or
    293.97°.
  - The accepted tolerance is the owner's to confirm (open question #30).
  - The kit gets a fixture model and a check before the first sketch.
- **Who:** owner (requirement); agent (measurement).

## 2026-10-13: house orientation and the prayer room

- **What:** the owner wants the house "along the lines that go from west to
  east". The agent reads this as walls parallel to the plot's north and
  south boundaries (grid 67.19°), with cross walls square to them
  (grid 157.19°): a rectangular house in a parallelogram plot. The owner
  prefers the prayer room to face the qibla, but it is optional.
- **Measured:**
  - Against the qibla line, the long walls are 43.22° off and the cross
    walls 46.78° off.
  - The qibla therefore runs diagonally across every room.
  - Cross walls parallel to the road instead would be only 18.09° off,
    which is bad for toilets.
- **Consequence:**
  - Toilets set along either wall direction are about 45° from the qibla.
    That is common practice; the accepted tolerance is open question #30.
  - The prayer room cannot have a wall square to the qibla unless one wall
    is angled. Otherwise the person prays along the room's diagonal. Either
    option is shown in the sketch; the owner chooses.
- **Who:** owner (orientation, preference); agent (reading, measurement).

## 2026-10-13: orientation accepted; toilets need no special treatment

- **What:** the owner accepts:
  - the house parallel to the north and south boundaries, with cross walls
    square to them;
  - toilets about 45° from the qibla (43.22° / 46.78°);
  - the wedge left between the house and the slanted road side.
  
  No toilet–qibla check is added to the kit. Any toilet on a wall in the
  two agreed directions is acceptable.
- **Who:** owner.
