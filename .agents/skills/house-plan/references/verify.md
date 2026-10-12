# Verify

A plan is verified in three layers. None of them replaces the others.

1. **Checks** (`bin/hp check`): geometry, topology and rules computed from the spec.
2. **Read-back** (`bin/hp build`): the DXF and IFC are reopened and measured;
   dimension chains must sum to the footprint, IFC walls, openings, storey
   levels and space areas must match the spec.
3. **Eyes**: you read the PNGs, then an independent reviewer does.

## Looking at the sheets

Read every `out/<name>/plan-*.png`. Then crop and zoom; a full A3 at 200 dpi
hides small faults. With the architecture venv:

```python
from PIL import Image
im = Image.open("out/<name>/plan-GF.png"); w, h = im.size
im.crop((int(w*.25), int(h*.25), int(w*.75), int(h*.8))).save("/tmp/zoom.png")
```

Checklist, every level:

- [ ] Every wall junction is solid: no notch, gap or sliver at corners and Ts.
- [ ] Every door: leaf and arc on the intended side, against a wall, not
      sweeping a stair, a fixture zone or another leaf.
- [ ] Every window shows in an exterior wall, centred where intended.
- [ ] Every room has a label with name, net area, clear size and height, and
      the label sits inside the room without touching walls or other text.
- [ ] Dimension chains on all four sides; text readable, not colliding. Any
      overlapping dimension text is a defect to fix in the drawing kit.
- [ ] The stair: treads, walking line and arrow toward up, riser text.
- [ ] Title block, scale, sheet size, north arrow, scale bar, check status.
- [ ] Nothing drawn outside the frame.

Then read `out/<name>/report.md`: zero errors; each warning fixed or explained
in `docs/decisions.md`; every `UNVERIFIED RULE` listed for the user.

## Independent review

Claude Code: the `plan-verifier` subagent. Codex: a second session with this
prompt.

> You are reviewing a house plan built from `design/<name>.yaml`. You did not
> design it. Read AGENTS.md and the house-plan skill. Then:
> 1. Run `bin/hp check` and `bin/hp build` on the spec yourself. Do not trust
>    any earlier report.
> 2. Recompute any number you question with the tools (shapely on the
>    geometry, ezdxf on the DXF, ifcopenshell on the IFC). Never by eye or by
>    mental arithmetic.
> 3. Read every PNG and work through the checklist in references/verify.md.
> 4. Compare the spec with its sources (survey, brief, docs/trace.md):
>    anything invented or changed from a source is a defect.
> 5. Report only defects and unverified assumptions, each with file, element
>    id, evidence (command and output), and severity. No praise, no
>    suggestions beyond correctness and the brief.
> Do not edit any file.

## When the checks miss something

If you or the reviewer find a fault the checks passed, the kit is incomplete:
add the check in `src/houseplan/checks.py` (or the read-back in
`verify.py`), add a test in `tests/` that breaks the example in exactly that
way and fails without the fix, then rerun everything.
