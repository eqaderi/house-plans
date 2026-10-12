# The design spec

`design/<name>.yaml`, validated by `src/houseplan/model.py` (pydantic, unknown
keys rejected). `design/examples/bungalow.yaml` is a complete, passing example.

## Conventions

- **Units:** integer millimetres for every length. Angles in degrees.
- **Axes:** a right-handed plan frame, origin at a chosen point near the
  building's corner. On a site, x and y follow the plot (here: x along the
  south boundary, see `docs/decisions.md`), and `north_angle_deg` is the true
  bearing of +y. `houseplan.site.SurveyFrame` converts survey eastings and
  northings to spec millimetres and back. Keep coordinates small; survey
  eastings and northings never go into wall points.
- **Heights:** relative to the datum ±0.00 (finished floor of the entrance
  level). `project.datum.survey_z_mm` ties it to the survey; leave it `null`
  until the survey gives it.
- **IDs:** unique across the whole file. Suggested: `W*` exterior walls,
  `V*`/`H*` interior walls, `D*` doors, `F*` windows (پنجره), `O*` openings,
  `R*` rooms, `S*` stairs, level ids such as `B1`, `GF`, `L1`, `RF`.

## Blocks

```yaml
project:
  name: ...
  jurisdiction: IR            # ISO 3166
  municipality: Tehran        # or null until known
  ruleset: iran               # rules/iran.yaml
  datum: { label: "±0.00", survey_z_mm: null, source: null }
  allowed_wall_thicknesses: [100, 150, 200, 300, 350]
  north_angle_deg: 0          # true bearing of +y, clockwise from true north

levels:
  - { id: GF, name: Ground floor, ffl: 0, floor_to_floor: 3200, slab: 350 }
  # clear height = floor_to_floor - slab (slab + floor build-up + ceiling)

walls:
  - { id: WS, level: GF, start: [0, 0], end: [12000, 0], thickness: 300,
      kind: exterior, loadbearing: true, justify: center }
  # justify: center | left | right — where the start→end line sits in the wall,
  # seen walking from start to end. "left" means the line is the wall's left
  # face, so the wall lies to the right of the line. An outline walked
  # clockwise with justify: left (or counter-clockwise with justify: right)
  # has its line on the outer face.

openings:
  - { id: D1, wall: WE, kind: door, offset: 2500, width: 1000, height: 2200,
      hinge: start, swing: left }       # doors need hinge and swing
  - { id: F1, wall: WS, kind: window, offset: 1700, width: 1800, height: 1500, sill: 900 }
  - { id: O1, wall: H3, kind: opening, offset: 1500, width: 2400, height: 2400 }
  # offset: from the wall's start point along the line to the near jamb.
  # width/height: structural (rough) opening. leaf: clear door leaf if different.
  # swing: the side of the wall line the leaf opens into (left/right of start→end).

rooms:
  - { id: R1, level: GF, name: Bedroom 1, name_fa: اتاق خواب ۱, use: bedroom,
      seed: [2500, 2000], entrance: false }
  # The outline is the wall-enclosed space containing the seed. Area is net,
  # from finished wall faces. uses: living (نشیمن) reception (پذیرایی) dining
  # entry (ورودی/کفش‌کن) bedroom kitchen bath wc corridor hall stair storage
  # pantry (انباری) laundry garage plant balcony terrace

program:                       # the brief as checkable requirements (owner's, not yours)
  required: [ { use: bedroom, count: 3 }, { use: wc, count: 1 } ]
  connect: [ [R5, R6] ]        # rooms that must share a door or opening
  private_uses: [bedroom, bath, wc]   # no route may pass through these
  area_tolerance: 0.10         # vs each room's target_area
  vehicles:                    # cars parked side by side in the largest garage (rule garage_fits_vehicles)
    - { name: ..., length: 4985, width: 1980, source: "maker's page, market, model year" }
# rooms may also carry target_area (m², from the brief) and via (the room an
# en-suite bath or walk-in closet is reached through on purpose)

stairs:
  - { id: S1, level: GF, to_level: L1, origin: [6400, 300], direction: "+y",
      width: 1000, risers: 18, going: 280 }
  # origin: foot of the first riser on the run's centre line. Straight runs only.
  # rise = (to_level.ffl - level.ffl) / risers, computed by the code.
```

```yaml
lifts:
  - { id: LF, shafts: [R3, U2], car: [1100, 1400], source: "product data sheet ..." }
  # The shaft is a room of use `lift` on every served level, stacked; car is
  # the inside of the car, width (door side) x depth. A lift room is a start
  # for reachability, like a stair. Size rules: lift_car_min, lift_shaft_min,
  # lift_entrance_min_width in rules/<ruleset>.yaml, each with its source.
```

```yaml
balconies:
  - { id: B1, level: L1, name: Balcony, outline: [[6000, -1650], [11500, -1650], [11500, -150], [6000, -150]] }
  # A slab outside the walls, given by its outline (it has no walls to be
  # found from). It must touch the level's outer wall face; a door or opening
  # in that wall leads onto it. Not part of the footprint (windows behind it
  # still face outward); part of the built area for the site check.
```

```yaml
site: ../derived/site/d7.yaml   # or the block inline; a path is relative to the spec
# The file is written by scripts/site_frame.py --write; never type it by hand:
#   source, frame {crs, origin_e, origin_n, x_azimuth_deg}  (survey E/N live only here)
#   boundary: [[x, y], ...]                     plot, spec mm
#   no_build: [{name, outline: [[x, y], ...]}]  nothing built here at any height
#   roads:    [{name, points: [[x, y], ...]}]
#   spot_heights: [{name, at: [x, y], survey_z_mm}]   survey Z, not relative to ±0.00
```

`bin/hp ground <spec> [--at x,y ...]` reports the interpolated ground Z (linear
TIN over the `ground` spot heights, never extrapolated) at points, or under
every corner of each level and of the plot.

With a site, `hp sketch` adds `sketch-site.png` (1:200: boundary with side
lengths, roads, no-build zones, spot heights, each level's outline) and plan
sheets show the boundary and no-build zones.

## What the checks do

`bin/hp check` runs, in `src/houseplan/checks.py`:

| Code | Severity | Meaning |
|---|---|---|
| WALL_THICKNESS / WALL_ZERO_LENGTH / WALL_OVERLAP | error | wall not in the allowed set, degenerate, or doubled |
| OPENING_PAST_WALL_END / OPENING_IN_JUNCTION / OPENING_OVERLAP / OPENING_TOO_TALL | error | opening does not fit its wall or the storey |
| OPENING_NEAR_JUNCTION / NARROW_PIER | warning | jamb or pier under 100 mm |
| ROOM_NOT_ENCLOSED / ROOM_SHARED | error | seed not enclosed, or two rooms in one space (missing wall) |
| SPACE_UNNAMED | warning | enclosed space without a room |
| ROOM_UNREACHABLE | error | no route through doors/openings from an entrance or stair |
| DOOR_SWING_HITS_WALL / DOOR_SWING_HITS_STAIR | error | the leaf sweeps a wall or stair |
| DOOR_SWINGS_CLASH | warning | two leaves sweep the same floor |
| STAIR_IN_WALL / STAIR_NOT_IN_ROOM | error | stair footprint does not fit |
| STAIR_NO_WELL | warning | nothing above the run marks the stairwell |
| BEARING_NOT_STACKED | warning | load-bearing wall not carried by one below |
| NO_WINDOW | error | habitable room without an exterior window |
| WALL_END_FREE | warning | a wall end touches nothing (a gap, or a deliberate stub) |
| ROOM_SLIVER / ROOM_ASPECT | error / warning | no part 300 mm wide / proportion beyond 3:1 |
| PASS_THROUGH_PRIVATE | error | a room reached only through a bedroom or bath (unless `via`) |
| BEDROOM_TO_BEDROOM | warning | a door between two bedrooms |
| CIRCULATION_DETOUR | warning | walking route from the entrance over 1.5× the straight line |
| PROGRAM_MISSING / CONNECTION_MISSING | error | the brief's rooms or connections are not in the plan |
| AREA_OFF_TARGET | warning | room area outside the brief's tolerance |
| RULES_NOT_APPLICABLE | info | rules with nothing to test: not checked, not passed |
| ENTRY_VIEW_PRIVATE | warning | from the open entrance, a bedroom, bath or WC door is in view (محرمیت) |
| ENTRY_INTO_LIVING | warning | the house is entered straight into a living space |
| BEDROOM_OFF_SOCIAL | warning | a bedroom opens straight onto living, reception, dining or kitchen |
| BEDROOM_NEXT_TO_NOISE | info | a bedroom shares a wall with a noisy room |
| LIGHT_ONE_SIDE / LIVING_NOT_SOUTH | info | daylight from one side only / no south-facing window in a living room |
| SITE_OUTSIDE_BOUNDARY / SITE_IN_NO_BUILD | error | any level's outline leaves the plot or enters a no-build zone (a wall face on the line is allowed, 1 mm tolerance) |
| SITE_NOT_SET | info | no site block: boundary not checked |
| BALCONY_OVERLAPS_BUILDING / BALCONY_DETACHED / BALCONY_OVERLAP / BALCONY_INVALID | error | a balcony inside the walls, not touching them, doubled, or degenerate |
| BALCONY_NO_DOOR | warning | no door or opening leads onto the balcony |
| BALCONY_GUARD_UNCHECKED | info | railing height not checked: no cited value yet |
| LIFT_ROOM_USE / LIFT_LEVELS / LIFT_NO_DOOR / LIFT_NOT_STACKED / LIFT_CAR_IN_SHAFT | error | shaft room not of use lift, two on a level, no landing door, shafts not over each other (< 95 % clear on all levels), car does not fit |
| LIFT_UNLISTED | warning | a lift room that no lift names |

`bin/hp build` (final stage) adds the read-back: DXF units and dimension
chains (DXF_CHAIN_OPEN), text overlap and crowding below 1 mm on paper
(DXF_TEXT_OVERLAP / DXF_TEXT_CROWDED), labels inside rooms, dimension text off
walls, IFC walls / openings / storeys / space areas and NetFloorArea against
the spec, IFC schema validation with express rules, unique GlobalIds.

Then `rules/<ruleset>.yaml` runs through `src/houseplan/rules.py`: a failed
`verified` rule is an error, a failed `unverified` rule is a warning tagged
`UNVERIFIED RULE`.

## Not modelled yet

Curved walls, columns, sloped and stepped slabs, balcony depth on the
dimension chains (the area is labelled; chains measure the walls), lift pit
and overhead (need sections), split levels, winder and L/U stairs, roofs,
sections and elevations. When a design needs one of them, extend the kit first: schema
field, geometry, a check, a drawing routine, a test that fails without it.
