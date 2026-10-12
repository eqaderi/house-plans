---
name: house-plan
description: Use when the user wants to lay out, change, trace, check or draw a house, a floor, a room, a stair, a door or a window; convert survey DWG files or tie a building to a site survey; judge a layout for a family or a sloped site; or produce true-scale plan sheets, room areas or an IFC model — including Persian requests ("نقشه", "پلان", "طراحی خانه"). Use it even when the user only says "plan", "layout" or "option". Not for software plans or for editing the houseplan kit's own code.
license: MIT
compatibility: Claude Code and Codex. Needs ~/.venvs/architecture-ai (Python 3.13 with ifcopenshell, ezdxf, shapely, pyproj, pydantic, pytest). ODA File Converter, QGIS, Blender/Bonsai, FreeCAD and Inkscape are optional and used per step.
---

# House plan

Work like an architect with fifty years at the drawing board: the site and
the family come first, the structure and the circulation are decided before
the furniture, every dimension closes, and nothing leaves the office
unchecked. Here the drawing board is a spec file and the checking is done by
code, so the plan can be trusted number by number.

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
  calling an open room enclosed. Pictures find what the checks cannot see;
  they never prove a dimension.

## Workflow

Work in this order. Most of the quality is decided before the first wall.

1. **Scope it.** Say which deliverable this is (survey import, concept
   options, a change to an existing plan, the final set) and what you need
   from the owner. `bin/doctor --quiet` shows what this machine lacks.
2. **Truth first.** Collect what the design rests on; write what is missing
   in `docs/open-questions.md` instead of guessing:
   - Survey: DWG originals in `sources/` (never touched), converted with
     `bin/hp dwg2dxf` into `derived/`. Read `references/survey.md`.
   - Legal and municipal: plot boundary from the deed, the municipality's
     coverage, height, setbacks and street widening (دستور نقشه / طرح
     تفصیلی). These come from documents, never from you.
   - The family: `docs/brief.md`, turned into the spec's `program` (required
     rooms, connections, target areas). The brief is the owner's; you never
     edit it to make a design pass.
   - Rules: `rules/<ruleset>.yaml`; `references/iran.md` says what applies in
     Iran and how sure each value is.
3. **Site, datum, grid.** Tie ±0.00 to a surveyed Z, set north, decide how the
   house meets the slope, then lay the structural grid before any room. Read
   `references/slope.md` and `references/architect.md`.
4. **Write the spec.** Levels, exterior walls, structure, interior walls,
   openings, rooms (by seed point), stairs. `references/spec.md` has every
   field. Small steps: after each meaningful edit run `bin/hp check
   design/<name>.yaml` (in Claude Code a hook does it for you).
5. **Check to zero.** `bin/hp check` ends with `0 errors`. Every warning is
   fixed or explained in `docs/decisions.md`. An `UNVERIFIED RULE` warning
   means the limit itself still needs confirming against the regulation; say
   so, never treat it as passed. `RULES_NOT_APPLICABLE` means not checked.
6. **Judge it as a home.** Read `references/family.md` and walk the plan as
   the family will: entrance, guests, kitchen, bedrooms, gatherings, old age.
   The family checks (entrance view, zoning, quiet bedrooms, daylight) warn;
   the red-flag list there is reason enough to redo a layout.
7. **Draw.** Sketch stage (the default, while the owner is choosing): `bin/hp
   sketch design/<name>.yaml` — one true-scale PDF and PNG per level, nothing
   else. Show them with the room areas and failing rules in a few lines, and
   stop; most sketches get rejected. Final stage (only after the owner picks a
   layout, `project.stage: final`): `bin/hp build design/<name>.yaml` — DXF
   with true dimensions, PDF, PNG, IFC and report, then the read-back of DXF
   and IFC and the drawing-text audit.
8. **Look like a critic.** Read every `out/<name>/sketch-<level>.png` or
   `plan-<level>.png`, then run `bin/hp zoom design/<name>.yaml` and read every
   image in `out/<name>/zoom/`. Use the checklist in `references/verify.md`.
   Anything that reads wrong is wrong even if the checks passed: find which
   check is missing and add it, with a test that fails first.
9. **Independent review (final stage).** In Claude Code, hand the build to
   the `plan-verifier` subagent; in Codex, a second session with the reviewer
   prompt in `references/verify.md`. The reviewer recomputes with the tools and
   reports only defects.
10. **Gate and report.** Run `hooks/gate.sh` yourself. Your final message
    quotes its exit code and the last line of `bin/hp check` (`N errors, N
    warnings, N info`); in the final stage also the `Status:` line of
    `out/<name>/report.md` and the verifier's defect list. A claim without
    those lines is not a result. Then list open questions and unverified
    rules, and say that a licensed engineer must review and sign before any
    permit or construction use.

## Red flags: stop and run the tool

When you catch yourself writing any of these, the work is not done:
"looks right in the PNG", "check passed so the build is fine", "only a
warning", "the UNVERIFIED RULE didn't fail", "about N m²" without a tool's
output, "the verifier said OK" without its list, "I adjusted the target area
so it passes".

## Tools and when to use them

| Need | Tool |
|---|---|
| Plan geometry, checks, sheets, close-ups, IFC | `bin/hp check / sketch / zoom / build` |
| DWG → DXF | ODA File Converter via `bin/hp dwg2dxf` |
| Reading survey DXF: points, breaklines, boundaries | ezdxf + shapely in the architecture venv |
| CRS (UTM zones 38N–41N in Iran), terrain, contours, slope | QGIS (`qgis_process`) + pyproj |
| Inspecting the generated IFC | the `ifc` MCP server (read and validate only) |
| 3D review of the model | Blender with Bonsai, headless where possible |
| Exact CAD cross-check of a detail | FreeCAD (`freecadcmd`) |
| 3D and Unreal after approval | `references/visualization.md` |

Sections, elevations, roofs, columns and L/U stairs are not modelled yet:
extend the kit first (`references/spec.md`, "Not modelled yet"); never draw
one by hand. Do not use generic Blender meshes or hand-drawn SVG as
architecture; the IFC is generated from the spec.

## Craft rules (short form)

`references/architect.md` gives the reasoning; these are the reflexes.

- **Millimetres, integers, one origin.** x east, y north, z up from ±0.00.
  Survey coordinates go into the datum, never into wall points.
- **Walls by their reference line and justification.** Exterior walls are
  usually justified to their outer face so the footprint matches the survey
  and the permit. Thicknesses come only from `allowed_wall_thicknesses`.
- **Rooms are found, not drawn.** A room is the space its walls enclose
  around its seed. Two rooms in one space means a missing wall.
- **Openings by offset along their wall.** Rough-opening width and height,
  sill from FFL. Doors carry hinge and swing.
- **Stairs by risers and going.** The code splits the climb; you never round
  a rise by hand.
- **Structure first.** Load-bearing walls stack between levels; wet rooms
  stack over wet rooms.
- **Dimension like a builder needs it.** Exterior chains: openings, walls,
  overall. Iranian plans are dimensioned in centimetres.

## When the user hands you drawings

Existing DWG/DXF plans and surveys are the truth. Convert, then measure them
with ezdxf: never estimate from an image. Trace them into the spec wall by
wall, quoting the source coordinates in `docs/trace.md`, and list every
conflict (a wall that does not close, a dimension that disagrees with the
geometry) for the owner to decide. Read `references/survey.md` first.

Session start, end and the revision procedure: `AGENTS.md` and
`docs/workflow.md`.
