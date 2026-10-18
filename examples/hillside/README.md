# Synthetic hillside geometry demonstration

Run from the repository root:

```sh
.venv/bin/python examples/hillside/run_demo.py --out project-data/s8-demo
```

This reads only `examples/projects/synthetic-hillside/` and writes derived
exploratory files, without a project store or approval events. It compares
walkout, split-level, stepped, elevated and hybrid intentions. Split-level
uses the split-level massing; the other cases compare the hybrid massing's
sectional alternatives. All are solver-generated; failures and integrity
findings remain visible. Quantities are inferred from the synthetic TIN.

Each alternative includes `plan.json/svg`, `sections.json/svg`,
`elevations.json/svg`, `hillside.json` and `engineering-risks.md`.
`comparison.json/md` shows cut and void alongside level elevations and
integrity. No pad is specified here, so engineered fill is unknown rather
than being substituted for void. `tests/test_hillside_earthworks.py` supplies
closed-form slope, wedge, pyramid and stepped-formation numerical fixtures.

Normal plan generation exports the same hillside views. To choose a
sectional intent on an eligible bar strategy:

```sh
.venv/bin/house-ai plan generate <synthetic-project> --strategy split_walkout \
  --sectional-strategy stepped --exploratory --actor agent:codex
```

Existing site/program/plan gates still apply. Sectional intents currently
require a bar massing; free 2D placement refuses this option explicitly.

For custom true section lines, write a JSON list:

```json
[{"id":"cut-a","start":[0,0],"end":[10,20]}]
```

Then derive views from any exported canonical plan:

```sh
.venv/bin/house-ai plan sections project-data/s8-demo/hybrid/plan.json \
  --site examples/projects/synthetic-hillside/site.yaml \
  --lines /path/to/sections.json --out project-data/custom-sections
```

Omit `--lines` for standard cuts. `--settings` accepts a HillsideSettings
YAML/JSON file, e.g. `large_void_height_m: 4.0`. Triggers are configurable
concept-review assumptions, never building regulations. The SVG uses equal
axis scales and distinguishes unsupported terrain. Canonical stairs without
a walking line retain an explicit unknown rather than invented flight or
landing geometry. Elevations are LOCAL-axis projections with no occlusion
resolution. Garage ramp metrics describe straight candidate approaches and
confer no access/turning/vertical-curve feasibility.

Mapped survey `breakline` layers require explicit vertex elevations. Arc
segments, height conflicts and vertical discontinuities are refused. No
survey role is guessed from its layer name. See ADR 0022 for algorithms,
assumptions and professional boundaries.
