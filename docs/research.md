# Research: how to make agent-generated house plans trustworthy

Compiled 2026-10-12 from nine parallel research passes (practitioner reports,
open-source agent tooling, academic papers, professional model checking,
toolchains, Claude Code practice, drafting standards, Iranian regulations).
Sources marked as unverified in the passes are left out or flagged.

## The finding that shaped this repo

Agents fail at producing plans directly and succeed at editing structured
intent that deterministic code turns into geometry and checks.

- LLMs writing coordinates: "None consistently produced a valid floor plan
  JSON" (arXiv 2605.14117, GPT-4o/o3/QwQ). Even fine-tuned with RL, 13 % of
  8-room plans still overlapped. Overlap rises with room count.
- LLM writes constraints, a solver places rooms: valid by construction
  (Kodnongbua et al. arXiv 2402.00052; Co-Layout 2511.12474 with 0 % overlap).
- Agents loops alone don't help: Claude Code and Codex in Blueprint-Bench
  (arXiv 2509.25229) were no better than random and claimed rooms were
  enclosed when they were not. FloorplanQA (2507.07644): models sum areas
  instead of taking the union.
- Practitioners: whole-house prompts miss doors and circulation and get
  stairs wrong (SketchUp, Blender and Revit MCP tests: focusedsketchup.com,
  mindstudio.ai, bimsmith.com); reading and checking structured or IFC data
  works (techdrawai.com: IFC exact where native RVT was not).
- "Valid geometry is not correct geometry" (rhino-mcp); "a picture is not a
  measure" (pascalorg/editor). Vision checks of renders were right only about
  65–68 % of the time in CADCodeVerify (2410.05340).

## What this repo does about it

| Lesson | Where |
|---|---|
| Agent edits a millimetre spec; code derives everything | `src/houseplan/model.py`, `geometry.py` |
| Rooms come from walls, so they cannot overlap or float | `geometry.build_level` |
| Boolean hard gates with structured findings and exit codes | `checks.py`, `bin/hp check` |
| Adjacency is not connectivity: check doors, reachability, pass-through | `checks.access_graph`, `check_pass_through` |
| Topology checks paired with area and dimension checks (no gaming) | `check_program`, rules |
| Read back what was written: DXF chains, text, IFC areas and schema | `verify.py` |
| Rule values carry a source and a confidence; unknown never passes | `rules/iran.yaml`, `RULES_NOT_APPLICABLE` |
| Brief cannot be rewritten to pass | `AGENTS.md` non-negotiables |
| Hooks run checks after edits and gate "done" | `hooks/`, `.claude/settings.json` |
| Independent reviewer that recomputes, never edits | `.claude/agents/plan-verifier.md`, `references/verify.md` |
| Renders are read for what checks cannot see, never as proof | skill step 7 |
| Light sketch stage, full documentation only for the chosen plan | `bin/hp sketch` vs `bin/hp build` |

## Ideas collected, not built yet

- Constraint solver for concept options (MILP / grid IP, with the minimal
  conflicting set fed back to the agent) — 2402.00052, 2511.12474.
- Clear-path width by distance field between openings (planhaus CIRC-01:
  error < 600 mm, warn < 900 mm); doorway landing 300 mm each side.
- Bathroom only off circulation, en-suite only off its bedroom (planscript
  access rules); equator-facing living rooms (archlang).
- Furniture and fixture clearance polygons (planscript-rust E903).
- IDS data requirements per element and `ifctester` (buildingSMART IDS;
  property list in the professional-checking pass).
- Wall junction topology: angle ≥ 5°, ≤ 2 ends per node, T not on a corner
  (plomada-mcp).
- Daylight 1/7 and 1/6 variants, light wells, building height from mean
  street level, plot coverage (rules/iran.yaml header).

## Key sources

- Papers: arXiv 2605.14117, 2402.00052, 2511.12474, 2509.25229, 2507.07644,
  2605.28579, 2512.16275, 2411.12279, 2410.05340.
- Open-source agent tooling: github.com/pepuscz/planhaus,
  github.com/chanmeng666/archlang, github.com/Stv-devl/PlanPilotMCP,
  github.com/Mats2208/plomada-mcp, github.com/jfromaniello/planscript,
  github.com/pascalorg/editor, github.com/LTplus-AG/ifc-lite,
  github.com/ProfRino/bonsai-bim-skills.
- Practice: techdrawai.com/blog/connect-claude-to-revit,
  bimpure.com/blog/pyrevit-mcp-claude-code-tutorial,
  community.osarch.org/discussion/2819, archsmarter.com/blog/ai-sketch-to-revit-model.
- Tooling: docs.ifcopenshell.org, ezdxf.readthedocs.io, code.claude.com/docs
  (hooks, permissions, sub-agents, best practices), github.com/openai/codex
  (skills in `.agents/skills`, MCP in `.codex/config.toml`).
- Iran: see `.agents/skills/house-plan/references/iran.md`.

## Cars, lift and parking sizes (2026-10-13)

Collected by a research pass and re-checked against the downloaded pages
and PDFs. "Not given" means the source has no such value; nothing was
estimated.

### Toyota Land Cruiser 300

| Market, trim | Length | Width (body) | Height | Source |
|---|---:|---:|---:|---|
| Japan, ZX (spec sheet "'25年3月現在") | 4,985 | 1,980 | 1,925 | [toyota.jp spec PDF](https://toyota.jp/pages/contents/landcruiser300/004_p_001/pdf/landcruiser300_spec_202503.pdf): `全長 mm 4,985 4,965 4,985 4,965 4,950`, `全幅 mm 1,980 1,990 …`, `全高 mm 1,925` |
| Japan, GR SPORT | 4,965 | 1,990 | 1,925 | same |
| UAE 2026, GXR/VXR, 265/55R20 | 5,145 | 1,980 | 1,890 | [Al-Futtaim spec sheet, Nov 2025](https://dam.alfuttaim.com/wps/wcm/connect/f8d2296b-b53a-48a7-a67b-f03425fa365a/TY+Land+Cruiser+SS+WEB+25+LC+5+DR+P+4.0L+AT+EXR+GXR+VXR+RA.pdf?MOD=AJPERES&CONVERT_TO=url&CACHEID=ROOTWORKSPACE-f8d2296b-b53a-48a7-a67b-f03425fa365a-pJ60Shy): "L 5,145 x W 1,980 x H 1,890" |
| KSA 2026, GXR2–VX-R | 5,115 | 1,980 | 1,945 | [toyota.com.sa](https://www.toyota.com.sa/en/vehicles/lc300/lc300-specs): "5115 - 1980 - 1945" |

- Wheelbase 2,850 mm; minimum turning radius 5.9 m (Japan sheet). GCC
  pages give neither.
- Width with mirrors: 2,255 mm unfolded, 2,010 mm folded, approximate
  (`約 mm`) ([toyota.jp FAQ](https://toyota.jp/faq/show/11970.html)). No
  GCC page gives it.
- GCC cars are 130–195 mm longer than Japanese ones; the pages do not say
  why. The owner's market and trim are open question 31.
- **Envelope used in the spec until then:** 5,145 × 1,990 × 1,945 mm
  (longest, widest, tallest of the rows above).

### Peugeot 301

| Market | Length | Width (body / mirrors) | Height | Source |
|---|---:|---:|---:|---|
| Iran, imported (IKCO page, updated 1396/5/17) | 4,442 | 1,748 / not given | 1,477 | [IKCO page, Wayback 2020-09-29](https://web.archive.org/web/20200929084711/https://www.ikco.ir/fa/Product.aspx?ID=281&Section=2&Series=پژو+301+وارداتي): "طول خودرو (mm) 4442 … عرض خودرو(mm) 1748 … ارتفاع خودرو (mm) 1477" |
| Turkey, 2017 facelift | 4,445 | 1,748 / 1,953 | 1,466 | [peugeot.com.tr dimension drawing, Wayback](https://web.archive.org/web/20211005064127/https://media.peugeot.com.tr/image/67/0/peugeot-301-techinfos-01.148903.172670.11.jpg?autocrop=1), wheelbase 2,652 |

- **Envelope used in the spec:** 4,445 × 1,748 × 1,477 mm.

### Lift

- **Mabhas 15 (3rd ed., 1392):**
  - 15-2-1-2: a lift is required only above 7 m of vertical travel from the
    main entrance. The owner builds one anyway.
  - 15-2-1-9: a wheelchair-capable lift has a car of at least 1100 × 1400 mm
    and a car door of at least 800 mm.
  - 15-2-3-1: landing doors are at least 800 mm; automatic 900 mm doors are
    recommended.
  - Appendix 2, fig. 4 gives *suggested* sizes for a residential 630 kg car,
    1100 × 1400: a shaft of 1600 × 1900 (800 door) or 1700 × 1900 (900 door).
    Table 1 suggests a pit of 1400 mm at 0.63–1.00 m/s and headroom of
    3600–3700 mm.
  - Source: a [mirror PDF](https://dl.civilgeotech.ir/free/library/national-building-regulations/building-codes/mabhas-15/mabhas-15-1392.pdf),
    because inbr.ir refused the download.
- **Iranian accessibility regulation** (1368; scope: public buildings):
  - lift car 110 × 140 cm, door 80 cm;
  - waiting space of 150 × 150 cm on each floor;
  - source: a [transcription](https://recosaze.ir/ayin-name-zavabet-maloulin/) (secondary).
- **EN 81-70:2021:**
  - Type 2 (new buildings, a wheelchair user and a companion): 1100 × 1400,
    630 kg, 900 mm door.
  - Type 1: 1000 × 1300, existing buildings only.
  - Sources: the [ELA note](http://www.leia.co.uk/wp-content/uploads/2024/07/QTC-N2424-ELA_Information-Note-EN-81-70.pdf)
    and the [KONE factsheet](https://www.kone.co.il/he/Images/8570_Accessible%20elevators%20compliant%20with%20EN81-70-2018_hr_tcm203-68092.pdf).
- **Product data**, depending on which lift is chosen (open question 32):
  - KONE MonoSpace 4 DX ([planning guide](https://www.kone.co.uk/Images/KONE-MonoSpace-4-DX-Core-and-Pro-Planning-Guide-GBIR_tcm45-139450.pdf)),
    630 kg, car 1100 × 1400:
    - shaft 1600 × 1750 with a 900 door, or 1570 × 1750 with an 800 door;
    - pit 1100 (1400 with counterweight safety gear);
    - headroom "CH + 1 300".
  - Cibes C1 Pure home lift ([brochure 23.02](https://cibeslift.cdn.triggerfish.cloud/uploads/2022/11/01142429/CIBES_Technical-Brochure_23.02_EN_LOW.pdf)),
    cabin 1100 × 1400:
    - cut-out 1550 × 1690;
    - pit 100 mm;
    - headroom 2500 mm;
    - 0.15 m/s.

### Covered parking (Mabhas 4, 1396, chapter 4-5-10)

Read from a [scan of the printed edition](https://dl.civilgeotech.ir/free/library/national-building-regulations/building-codes/mabhas-4/mabhas-04-1396.pdf),
printed pp. 69–70.

- **4-5-10-2-4 الف:** stalls side by side are 2.50 × 5.00 m each; stalls
  one behind the other are 2.50 × 6.00 m.
- **4-5-10-2-4 پ:** a stall with walls on both sides is 3.00 × 5.00 m.
- **4-5-10-2-4 ب:** a wheelchair user's stall is 3.50 × 5 m axis to axis,
  plus 0.25 m for each wall.
- **4-5-10-2-1:** a small car park has a clear height of at least 2.20 m.
- **4-5-10-2-2 / -3:** the inner turning radius is at least 5.00 m, and a
  90° turn needs at least 5.00 × 5.00 m.
- **Not found anywhere:** a stated door-opening clearance beside a car.

The Land Cruiser's 5,145 mm length (UAE) exceeds the 5.00 m stall, so the
garage must be checked against the car body as well as against the stall
rule.
