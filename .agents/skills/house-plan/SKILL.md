---
name: house-plan
description: Design, draw and check residential house plans that must be dimensionally exact — floor plans, room schedules, DXF/PDF sheets at true scale and an IFC model — from a single millimetre design spec, with geometry audits, Iranian building-rule checks and read-back verification. Use whenever the user wants to lay out, change, trace, check or draw a house, a floor, a room, a stair, doors or windows, convert survey DWG files, tie a building to a site survey, or produce plans, sections or a BIM model, even if they only say "plan", "layout", "نقشه" or "پلان".
license: MIT
compatibility: Claude Code and Codex. Needs ~/.venvs/architecture-ai (Python 3.13 with ifcopenshell, ezdxf, shapely, pyproj, pydantic, pytest). ODA File Converter, QGIS, Blender/Bonsai, FreeCAD and Inkscape are optional and used per step.
---

# House plan

Work like an architect with fifty years at the drawing board: the brief and
the site come first, the structure and the circulation are decided before the
furniture, every dimension closes, and nothing leaves the office unchecked.
Here the drawing board is a spec file and the checking is done by code, so
the plan can be trusted number by number.

## The one idea that matters

**The spec is the building.** `design/<name>.yaml` holds walls, openings,
rooms, stairs and levels in integer millimetres. Everything else — room
outlines, net areas, dimension chains, drawings, the IFC model — is derived
from it by `src/houseplan`, then read back out of the written files and
compared with the spec. You never place a line on a drawing and you never
compute a number in your head. When you need a number, run the tools.

Two ways this goes wrong, both seen in published attempts:

- **Drawing instead of specifying.** Hand-made SVGs and coordinates typed into
  a CAD script drift: rooms overlap, doors vanish, areas stop adding up.
- **Believing a picture.** A render that "looks right" has fooled agents into
  calling an open room enclosed. Screenshots are for spotting what the checks
  cannot see; they never prove a dimension.

## Workflow

Work in this order. Most of the quality is decided before the first wall.

1. **Scope it.** Say which deliverable this is (survey import, concept layout,
   a change to an existing plan, a full set) and what you need from the user.
   Run `bin/hp doctor` to see which tools this machine has.
2. **Truth first.** Collect what the design rests on, and write what is
   missing in `docs/open-questions.md` instead of guessing:
   - Survey: DWG originals in `sources/` (never touched), converted with
     `bin/hp dwg2dxf` into `derived/`. Read `references/survey.md`.
   - Legal and municipal: plot boundary from the deed, the municipality's
     permitted coverage, height, setbacks and street widening
     (دستور نقشه / طرح تفصیلی). These come from documents, never from you.
   - Brief: household, rooms, priorities, budget, structure type.
   - Jurisdiction rules: `rules/<ruleset>.yaml`. Read
     `references/iran.md` for what applies in Iran and how sure each value is.
3. **Datum and grid.** Tie ±0.00 to a surveyed Z (`project.datum`), set north,
   and lay out the structural grid before any room. Read
   `references/architect.md` for the design rules a senior architect applies:
   orientation, structure, circulation, wet cores, privacy, stairs.
4. **Write the spec.** Levels, exterior walls, structure, interior walls,
   openings, rooms (by seed point), stairs. Read `references/spec.md` for
   every field and convention. Small steps: after each meaningful edit run
   `bin/hp check design/<name>.yaml` (in Claude Code a hook does it for you).
5. **Check to zero.** `bin/hp check` must end with `0 errors`. Every warning
   is fixed or explained in `docs/decisions.md`. An `UNVERIFIED RULE` warning
   means the limit itself still needs confirming against the regulation; say
   so to the user, never treat it as passed.
6. **Draw.** In the sketch stage (the default, while the owner is choosing a
   layout) run `bin/hp sketch design/<name>.yaml`: one true-scale PDF and PNG
   per level, nothing else. Show them, give the room areas and failing rules
   in a few lines, and stop; most sketches get rejected, so put no effort into
   reports or prose. Only once the owner picks a layout, set
   `project.stage: final` and run `bin/hp build design/<name>.yaml`, which writes, per level, a DXF in
   millimetres with true DIMENSION entities, a PDF and a PNG at true scale on
   a standard sheet, plus `model.ifc` and `report.md`. The build then re-reads
   the DXF (dimension chains must close on the footprint) and the IFC (walls,
   openings, storey levels and space areas must match the spec).
7. **Look like a critic.** In both stages, read every PNG. Crop and zoom into every junction,
   door, stair and dimension chain. Use the checklist in
   `references/verify.md`. Anything that reads wrong is wrong even if the
   checks passed — then find out which check is missing and add it, with a
   test that fails first.
8. **Independent review (final stage).** In Claude Code, hand the build to the
   `plan-verifier` subagent. In Codex, open a second session with the
   reviewer prompt in `references/verify.md`. The reviewer recomputes numbers
   with the tools and reports only defects.
9. **Gate.** `hooks/gate.sh` must exit 0. Then report to the user: what was
   built, the open questions, the unverified rules, and that a licensed
   engineer must review and sign before any permit or construction use.

## Tools and when to use them

| Need | Tool |
|---|---|
| Plan geometry, checks, drawings, IFC | `bin/hp` (this repo's kit) |
| DWG → DXF | ODA File Converter via `bin/hp dwg2dxf` |
| Reading survey DXF: points, breaklines, boundaries | ezdxf + shapely in the architecture venv |
| CRS (UTM zones 38N–41N in Iran), terrain, contours, slope | QGIS (`qgis_process`) + pyproj |
| Inspecting the generated IFC | the `ifc` MCP server (read and validate only) |
| 3D review of the model | Blender with Bonsai, headless where possible |
| Exact CAD cross-check of a detail | FreeCAD (`freecadcmd`) |
| Presentation-only vector polish | Inkscape, on copies in `out/`, never on sources |

Do not use generic Blender meshes or hand-drawn SVG as architecture. The IFC
is generated from the spec, so it stays the semantic model for BIM tools.

## Craft rules (short form)

`references/architect.md` gives the reasoning; these are the reflexes.

- **Millimetres, integers, one origin.** x east, y north, z up from ±0.00.
  Large survey coordinates go into the datum and IFC map conversion, never into wall points.
- **Walls by their reference line and justification.** Exterior walls are
  usually justified to their outer face so the footprint matches the survey
  and the permit. Thicknesses come only from `allowed_wall_thicknesses`.
- **Rooms are found, not drawn.** A room is the space its walls enclose
  around its seed. If two rooms share a space, a wall is missing; if a seed is
  not enclosed, the room is open.
- **Openings by offset along their wall.** Rough-opening width and height,
  sill from FFL. Doors carry hinge and swing; check every leaf clears walls,
  stairs and other leaves.
- **Stairs by risers and going.** The climb is split into equal risers by the
  code; you never round a rise by hand.
- **Structure first.** Load-bearing walls and columns stack between levels;
  wet rooms stack over wet rooms. The checks warn when they don't.
- **Dimension like a builder needs it.** Exterior chains: openings, walls,
  overall. Room labels carry net area and clear size. Plans for Iran are dimensioned in centimetres.
- **Every sheet says what it is.** Title block with scale and sheet size,
  north arrow, scale bar, datum, check status and the not-for-construction note.

## When the user hands you drawings

Existing DWG/DXF plans and surveys are the truth. Convert, then measure them
with ezdxf: never estimate from an image. Trace them into the spec wall by
wall, quoting the source coordinates, and list every conflict you find (a wall
that does not close, a dimension that disagrees with geometry) for the user to
decide. Read `references/survey.md` first.

## Sessions and revisions

The repo is the memory, not the chat. Start every session by reading
`docs/STATUS.md`, `docs/brief.md`, `docs/open-questions.md` and the newest
`docs/feedback/rev-*.md`; end it by updating `docs/STATUS.md`. A design round
ends with a commit tagged `rev-<X>` and the sheets copied to
`reviews/rev-<X>/`. Answer every numbered feedback item explicitly. The full
procedure is in `docs/workflow.md`.
