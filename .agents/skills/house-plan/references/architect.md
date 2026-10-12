# How a senior architect lays out a house

Companion references: `slope.md` (the site), `family.md` (how the family
lives, Iranian specifics, red flags), `ergonomics.md` (clearances),
`iran.md` (rules), `visualization.md` (3D and Unreal after approval).

These are design judgements, not regulations. Regulation numbers live in
`rules/` with their sources; where a value below is a rule of thumb, it is
called one. Apply them in this order: each step constrains the next.

## 1. Read the site before drawing the house

- **Survey and boundary first.** Footprint, levels and setbacks come from the
  survey and the municipal permit conditions, not from the brief.
- **Slope.** On a sloped site decide early which level meets the street, which
  meets the garden, and where retaining walls go. Every metre of cut is cost;
  every step between rooms is a fall risk and an accessibility problem.
  Cross-sections like those in the sibling project `house-profile-slope` are the right tool:
  measured terrain, proposed floor stack, cut and fill.
- **Sun.** In Iran the main living rooms face south (رو به جنوب) for low
  winter sun; summer sun from the south is shaded with a modest overhang,
  while east and especially west glass gets little and well-shaded area.
  Service rooms, stairs and storage buffer the north and west.
- **Wind, view, noise, privacy** from the street and the neighbours.
- **Access.** Where the car, the pedestrian and deliveries arrive.

## 2. Structure before rooms

- Choose the system with the structural engineer: reinforced-concrete frame,
  steel frame, or confined masonry (بنایی با کلاف). Iran is highly seismic, so
  Standard 2800 drives the layout as much as the rooms do.
- **Regular and compact.** Simple, roughly symmetric plans with continuous
  vertical load paths behave best in earthquakes. Avoid deep re-entrant
  corners, soft storeys (an open ground floor under heavy floors above),
  short columns from partial-height infill, and large openings in shear walls
  near corners. The numeric limits are in Standard 2800 — see `iran.md`.
- **Grid.** Lay the column grid or bearing walls first; typical residential
  spans are 3.5–5.5 m (rule of thumb). Rooms then fit the bays, not the other
  way round.
- **Stack** load-bearing walls and columns between levels, and wet rooms over
  wet rooms, so pipes drop straight.

## 3. Circulation is the skeleton of the plan

- One clear entrance sequence: door, a place to take shoes off and hang coats,
  then the guest (بیرونی) zone. Private rooms (اندرونی) should not be visible
  from the entrance or the guest room; traditional Iranian planning separates
  them, and many families still expect it.
- A guest WC near the entrance, not through the bedroom corridor.
- Keep corridors short. Rule of thumb: circulation under about 10–15 % of the
  net area; past that, rethink the layout.
- Stairs near the centre of the plan, so upper corridors stay short. A stair
  needs its full headroom along the whole run and a landing at top and bottom
  at least as deep as the stair is wide (rule of thumb).

## 4. Rooms

- **Living / guest room (پذیرایی):** the best orientation, the largest
  unbroken wall for seating, no through-traffic across the seating area.
- **Kitchen:** next to dining, with a short route to the entrance for
  shopping; a work triangle of sink, cooker and fridge with sides of roughly
  1.2–2.7 m (rule of thumb). Iranian kitchens are often open to the living
  area (آشپزخانه اپن); then plan extraction and a closed pantry or second
  kitchen for heavy cooking if the brief asks for it.
- **Bedrooms:** the bed against a solid wall, not under a window, with
  passage on both sides of a double bed and space for a wardrobe.
  Rule of thumb: a double bedroom needs a 3.0 m clear short side.
- **Bathroom / WC:** wet rooms grouped and stacked. Iranian convention: the
  toilet axis is not aligned with the qibla (neither facing nor backing it).
  Get the qibla bearing for the site and check every WC (convention, not code).
  Provide both an Iranian squat toilet (توالت ایرانی) and a western one if the
  brief asks.
- **Storage, laundry, plant room:** real rooms with real doors, not leftovers.

## 5. Doors and windows

- A door leaf swings against a wall, never into a corridor or a stair, and two
  leaves never sweep the same floor.
- Keep a pier of at least about 100 mm between an opening and a wall junction
  so the frame can be fixed and the corner stays structural (rule of thumb;
  the check uses 100 mm). Shear walls may need more — ask the engineer.
- Window sills: above furniture height in bedrooms and kitchens, low in living
  rooms with a view; guard against falls where the sill is low on upper floors
  (value in `rules/`).
- Every habitable room gets daylight and natural ventilation through an
  exterior wall or a permitted light well (پاسیو / نورگیر). The required ratio
  is in `rules/`.

## 6. Drawings that a builder can build from

- Exterior dimension chains on every side: openings, wall faces, overall.
  Partial dimensions must add up to the overall; the build verifies it.
- Every room labelled with name, net area, clear size and clear height.
- Levels (FFL) on every floor, related to ±0.00 and to the survey Z.
- Title block, scale, sheet size, north arrow and scale bar on every sheet.
- Plans in Iran are dimensioned in centimetres and drawn at 1:100 for permits
  and 1:50 for construction (verify the municipality's submission rules in
  `iran.md`).

## 7. What an AI most often gets wrong, and the guard

| Mistake | Guard |
|---|---|
| Rooms that overlap or don't close | rooms come from walls; ROOM_SHARED / ROOM_NOT_ENCLOSED |
| A room nobody can enter | ROOM_UNREACHABLE |
| Doors that hit walls or each other | swing checks |
| Areas that don't add up | areas computed from geometry; footprint = walls + rooms |
| A stair that doesn't fit the storey height | rise computed from levels; footprint checks |
| Silently "improving" a surveyed drawing | the source is the truth; list conflicts |
| Quoting a building-code number from memory | numbers only from `rules/` with a source |
| Trusting a screenshot | read-back of DXF and IFC; the PNG is only for what checks can't see |
