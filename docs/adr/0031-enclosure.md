# ADR 0031: Enclosure

Status: accepted (2026-11-17, spec #9 part 6, tickets #27 to #31).

## Context

Two assemblers turn a solved layout into a canonical house model: the bar
assembler (`generation/assemble.py`, the six bar strategies) and the 2D
assembler (`generation/assemble2d.py`, `corridor_free`, `open_plan` and every
concept proposal). Each derived walls, openings, slabs, ceilings, Zones and
materials from its Spaces with its own copy of the rules, and the copies had
drifted. Rules that matter on a steep Parcel existed in one copy only:

- A 2D plan version never got a retaining wall: its wall sweep classified every
  exterior face as `exterior`, whatever the terrain held back.
- Its front door was `d-ext-…`, while the evaluators looked for `d-front`, so
  entrance privacy and distance to the road were silently zero or absent.
- Kitchens and garages got corner doors and the width-shrink fit only in bar
  plans; 2D plans used a second, simpler fit.
- 2D plans recorded no Space relationships, had a second materials table
  (`m-window`, slabs in `m-floor`) and literal slab thickness and stair tread
  values.

The glossary had no word for this whole set of derived elements. "Envelope" is
taken: a buildable envelope is part of the Site.

## Decision

- **Enclosure** (glossary) is the walls, openings, slabs and ceilings derived
  around the Spaces of a plan version. It has one home:
  `house_ai.generation.enclosure`.
- Its input is named rectangles per Level (`EnclosedSpace`: id, Level, design
  grid rectangle, function, Zone, Space requirement), the Levels, the design
  frame and the terrain. It returns walls that know the Space on each side,
  each exterior face classified as retaining, party or plain exterior against
  the terrain, terrace edges as parapets, the wall model and one materials
  table. It fits doors and windows (no overlap, minimum widths, the
  width-shrink fit, corner doors for kitchens and garages, a clear exterior
  side), builds floor and roof slabs with stair voids, terrace slabs,
  ceilings, Zones and the plan's Space relationships.
- Both assemblers are adapters that feed it. What only one layout kind has
  stays with its assembler: bars, stairwells (their walls, which do not span a
  plain storey, and their full-height openings), the garage strip and its
  vehicle door stay with the bar assembler
  ([ADR 0023](0023-stairs-between-split-levels.md)); shared-wall door
  candidates, open-plan openings and courtyards stay with the 2D assembler.
  Each adapter still decides which openings a Space gets and how wide; the
  fit is Enclosure's.
- Where the two copies disagreed, the bar assembler's rules became the shared
  ones: retaining classification from terrain, the wall and slab constants
  (`stairs.SLAB_M`, `stairs.TREAD_M`), one materials table, Space
  relationships recorded on the model, corner doors for kitchens and garages,
  the width-shrink fit, ceilings left out over stairs and terraces, Zones that
  the program or the adapter defines.
- The canonical `Opening` gains an optional `role`: `main_entrance` or
  `vehicle_entrance`. Enclosure sets it for both assemblers. The evaluators
  read the role and fall back to the `d-front` / `d-garage` id prefixes for
  stored plan versions that lack it. A missing role is not serialised, so the
  content hash of every stored plan version is unchanged
  ([ADR 0003](0003-file-based-store-and-event-log.md)).
- The 2D assembler's paths for multi-rectangle Spaces and separate circulation
  Spaces are deleted: the 2D solver never produces either.

## Consequences

- Bar strategies produce identical house models, apart from the new `role`
  on the front door and the garage's vehicle door.
- 2D strategies produce different output from now on: retaining and party
  walls on sloped Sites, per-Level wall ids, Enclosure's opening ids and
  corner doors, `m-glass` windows and `m-slab` slabs, no ceilings over stair
  cores and terraces, recorded Space relationships, and a main entrance the
  evaluators find. Stored plan versions are write-once and untouched; they
  evaluate as before.
- A wall or opening rule is tested on hand-written rectangles and a fixed
  terrain (`tests/test_enclosure.py`), without a project or a solver.
- The party-wall rule assumes a neighbour on another Level stands on
  substructure down to the ground. A 2D upper storey that overhangs the one
  below therefore makes the lower face a party wall without windows.
