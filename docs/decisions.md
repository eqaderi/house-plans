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

## 2026-10-13: spec frame turned to the plot (supersedes "x east, y north (grid)")

- **What:** the spec frame for this site:
  - origin at plot corner V3 (SW, road and alley), E 623809.167,
    N 3870456.033 (unchanged);
  - +x along the south boundary towards V2, grid azimuth 67.1878°;
  - +y square to it, into the plot (grid 337.19°);
  - `project.north_angle_deg: 337.97`, the true bearing of +y.

  In this frame the plot is V3 (0, 0), V2 (32570, 0), V1 (42651, 18422),
  V0 (10081, 18422), and the 1 m alley strip is the band 0 ≤ y ≤ 1000.
  Every number is printed by `scripts/site_frame.py`; the transform is
  `houseplan.site.SurveyFrame`, tested in `tests/test_site.py` against
  `docs/site.md`.
- **Why:** walls are axis-aligned and stairs run only along ±x/±y. The
  owner wants the house parallel to the north and south boundaries
  (decision "house orientation"), so the frame must follow them. The old
  entry's origin and height reference stand; only the axes change.
- **Note:** the boundary rounded to whole millimetres encloses 600.005 m²
  (survey 600.004 m²). `north_angle_deg` means the true bearing of +y, as
  `family.py` and `drawing.py` already used it; the field's description said
  otherwise and was corrected.
- **Who:** agent, carrying out the owner's orientation decision.

## 2026-10-13: terrain model, benchmark kept out

- **What:** ground heights between survey points come from a linear TIN
  (`houseplan.terrain`, `bin/hp ground`): Delaunay triangles over the
  `height-points.dxf` spot heights, a plane per triangle, no smoothing and
  no extrapolation. Every reported height is labelled "interpolated" with
  its three source points and the triangle's longest edge.
- **The benchmark نقطه مبنا is not a ground point** (`ground: false` in
  `derived/site/d7.yaml`). It stands 20.8 m NNW of the plot by the road.
  Measured over a 100 mm grid of the plot (60254 points):
  - With it, 459 points fall outside the hull; without it, 723.
  - Without it, all four plot corners are outside the hull (the corner
    shots lie a few cm inside the boundary). With it, V0 gets a height from
    the triangle Pt16/Pt15/BM.
  - Including it changes the ground by up to 0.833 m along the north
    boundary, through triangles reaching 21 m beyond the plot.
- **Known weak spots** (long hull triangles):
  - Pt16/Pt9/Pt1 (32.5 m edge) covers only 1.66 m² of the plot, at
    y 18268..18420 (the north boundary is y 18422).
  - Pt10/Pt9/Pt16 (17.2 m edge) covers 1.12 m², at y 18161..18314.
  - Pt5/Pt12/Pt19 (21.4 m edge) lies inside the alley strip.
  - Pt9/Pt2/Pt1 (15.3 m edge) covers 50.37 m² at the NE.
- **Who:** agent. The builder checks levels on site before setting out
  (decision "survey heights and datum").

## 2026-10-13: which floor meets the road, which the garden; ±0.00 (superseded the same day, see "garage level at the road")

- **What:**
  - The upper floor (UF: entrance, garage, living, kitchen) meets the road
    on the west. Its FFL is ±0.00 = survey Z **1677.900**
    (`project.datum.survey_z_mm: 1677900`).
  - The lower floor (LF: bedrooms) is one full storey down, FFL −3.200
    (floor-to-floor 3200, 18 risers of 177.78 mm, from `bin/hp check`
    STAIR_RISE). No split levels inside the block (`references/slope.md` §3).
- **Why ±0.00 there:** the road-edge spot heights in `derived/site/d7.yaml`
  are Pt19 1677.613, Pt20 1677.632, Pt17 1677.805 and Pt16 1677.438. ±0.00
  sits just above the highest of them (Pt17, by the garage door), so the
  forecourt and the garage apron fall towards the road and rain stays out.
  The TIN gives "unknown" along most of the road edge, so the shots
  themselves were used, not an interpolation.
- **What the ground does under option A** (`bin/hp ground
  design/option-a.yaml`, heights relative to ±0.00):
  - West face: −3.566 at the SW corner, −2.955 at the LF garden door
    (y 5500), −2.351 at the UF entrance (y 7800), −1.423 at the garage door
    (y 11500), −0.565 at the NW corner. The LF is buried at the north-west
    and at grade near the south-west, where its side door leads to the
    path and the alley.
  - East face: −6.138 (NE) to −7.957 (SE). The LF floor (−3.200) stands
    well above the ground there: the space under its east half is a
    storey-high undercroft or needs fill and retaining walls. A garden at
    LF level on the east would need a built terrace; it is not drawn.
  - The plot falls about 37 % west to east (`docs/site.md`), and the
    contours run parallel to the slanted road, so any house parallel to the
    north and south boundaries meets this. Option B tries a footprint that
    follows the contours.
- **Who:** agent; the owner delegated the datum (decision "survey heights
  and datum"). The builder checks the road-edge and corner heights with a
  level before setting out.

## 2026-10-13: garage level at the road, two house floors below it (supersedes "which floor meets the road")

- **What:** three levels stepping down the slope:
  - **G** at the road: the garage and a road-level lobby with the lift and
    stair. FFL ±0.00 = survey Z 1677.900 (unchanged; reasons in the
    superseded entry: just above road-edge shot Pt17 1677.805).
  - **UF** one storey down (FFL −3.200): living, kitchen, dining, main
    entrance, WC, prayer room. Part of it lies under the garage.
  - **LF** another storey down (FFL −6.400): bedrooms, opening onto the
    garden. Set further east than UF, where the ground is lower.
- **Why:** the owner's instruction (quoted in `docs/brief.md`, "Parking").
  Option A put both house floors under 3.2 m of section while the ground
  falls −0.565 to −7.957 m across its 13 m footprint (`bin/hp ground
  design/option-a.yaml`), leaving the lower floor's east half over a void.
- **Who:** owner (levels); agent (FFLs, which follow one floor-to-floor
  height of 3200).
- **Option A** (`design/option-a.yaml`) is kept as a record and is not
  developed further.
