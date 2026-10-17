# Original-survey audit — 2026-10-17

The original DWGs support **1664.884–1680.071 m** across all 27 points.
Road candidates are on the **lower-X side of the parcel (drawing-west)**.
The horizontal-area-weighted mean slope is **38.87% over the complete survey TIN**
and **40.68% over its parcel intersection**. None of this confirms units, CRS,
vertical datum, legal boundaries or the interpretation of the road entities.

Status: `SITE_NEEDS_VERIFICATION`. No site or program approval was performed.

## Recovery of the interrupted work

At takeover, `main` and `origin/main` were at `2ecb587`. Git status was clean,
including untracked files. Recent files, branch history, reflog and repository
reports were inspected before editing. No unfinished extraction fix, uncommitted
test or investigation note was recoverable from this checkout. No work was
discarded; no reset, clean, history rewrite or source replacement was performed.

The latest implementation commit was `cec2565`, completing the agent interview
interface and adding `docs/MILESTONE_D_HANDOFF.md`. That document contained
incorrect source hash prefixes, parcel dimensions, road orientation, elevations
and a 65.2% slope. Its author metadata alone cannot establish which agent wrote
each line. Earlier committed site extraction and steep-triangle diagnostics
were already correct and have been retained.

The handoff request also quotes 1409.30–1421.84 m and 68.78%. Neither value occurs
in the current tracked reports or in the all-branch Git content searches. No
recoverable calculation or entity reference supports them. Their exact origin
cannot be reconstructed from the supplied repository; calling them a particular
scaling bug would invent a root cause. They must not be used as site evidence.

## Source chain and conversion

| Original | SHA-256 |
|---|---|
| `surveys/seperated.dwg` | `27624ba14003e3d898143a9d86985d50d3d7098db0a45b94ae2dd999571519ed` |
| `surveys/elevation.dwg` | `9689880c47d9d0780089c5d4077f9396f5c29a2feeb298fafb86840bbae02f02` |

Both match their immutable `source/` copies and registered source-document
hashes, before and after replay. `final.dwg` remains excluded. Original survey
files, source documents, site v1, owner statements and event history are unchanged.

Fresh extraction used ODA File Converter **27.9.0.0**, converting temporary copies
to ACAD2018 DXF, then **ezdxf 1.4.5**. Original formats are AC1032 and AC1021
respectively. [Inspection](inspection/inspection.md) records the converter,
parser, headers and conversion hashes. ODA output byte hashes vary across runs;
the independently repeated entity/triangle/metric ledger has the same semantic
SHA-256: `f9e0f86038733a86adab2813b56b48472068a41947b6ffa2d3a2c99a8de38e6a`.

[evidence.json](evidence.json) contains every raw point and annotation, all three
polylines, source handles, label checks, transformed positions and all 47 triangle
slopes, horizontal areas, parcel intersection areas and edge runs/rises. Fresh
spot geometry, boundary geometry and triangle geometry match the stored site.
Vertex indices can differ with source loading order; comparisons use coordinates.

## Elevations and their scope

POINT coordinate Z supplies elevation. MTEXT insertion Z is not a second
measurement; annotation text is used only to cross-check a colocated POINT.
All 21 numeric elevation labels in `elevation.dwg` agree with their POINT Z.
The six labels in `seperated.dwg` contain point names only, so their heights have
no numeric-text cross-check. Repeated point names across the files are not used
to join or deduplicate points; source-qualified handles identify them.

Both drawings declare `$INSUNITS=6` (metres). The source-to-grid horizontal and
vertical scale factors are each **1.0**. Grid-to-local translation subtracts
`(623809.1666028872, 3870456.032537977, 0.0)` with **0° rotation**. There is no
vertical offset, double scaling or label-to-elevation substitution in this replay.
Declared units remain unconfirmed until the human confirmation step.

| Scope | Minimum Z | Maximum Z | Relief | Basis |
|---|---:|---:|---:|---|
| All 27 points | 1664.884 | 1680.071 | 15.187 m | raw POINT Z |
| `elevation.dwg`, 21 points | 1664.884 | 1677.805 | 12.921 m | raw POINT Z |
| `seperated.dwg`, 6 points | 1665.378 | 1680.071 | 14.693 m | raw POINT Z |
| 16 points inside/on candidate parcel | 1664.884 | 1677.438 | 12.554 m | measured points selected geometrically |
| TIN intersected with candidate parcel | 1664.884 | 1677.595626 | 12.711626 m | linear interpolation at clipped vertices |

The all-survey minimum is `elevation.dwg#69`, annotation `#6A` (Pt1), at
`(623841.289, 3870489.527, 1664.884)`. The maximum is `seperated.dwg#6D`, at
`(623799.692, 3870451.712000001, 1680.071)`, outside the parcel. The highest
interior spot is `elevation.dwg#87`, annotation `#88` (Pt16), at 1677.438 m.
These scopes explain why a roughly 12.5 m parcel relief coexists with a 15.187 m
full-survey range. The owner's approximate 12–12.5 m statement is preserved as
owner evidence; it is not relabelled as a surveyor verification.

### Point ledger

Coordinates below are SOURCE values, rounded to six decimals for display;
`evidence.json` preserves full extracted precision and raw annotation data.

| Source / POINT handle | X | Y | Z | Label handle(s) | Inside parcel |
|---|---:|---:|---:|---|---|
| src-elevation#69 | 623841.289000 | 3870489.527000 | 1664.884 | 6A | yes |
| src-elevation#6B | 623840.348000 | 3870481.945000 | 1665.529 | 6C | yes |
| src-elevation#6D | 623839.596000 | 3870472.363000 | 1665.697 | 6E | no |
| src-elevation#6F | 623839.196000 | 3870468.875000 | 1665.648 | 70 | yes |
| src-elevation#71 | 623828.852000 | 3870464.416000 | 1669.394 | 72 | yes |
| src-elevation#73 | 623828.612000 | 3870471.424000 | 1669.654 | 74 | yes |
| src-elevation#75 | 623828.781000 | 3870479.167000 | 1669.490 | 76 | yes |
| src-elevation#77 | 623833.288000 | 3870476.481000 | 1667.925 | 78 | yes |
| src-elevation#79 | 623827.247000 | 3870483.456000 | 1669.952 | 7A | yes |
| src-elevation#7B | 623819.453000 | 3870480.061000 | 1673.050 | 7C | yes |
| src-elevation#7D | 623820.022000 | 3870469.456000 | 1672.913 | 7E | yes |
| src-elevation#7F | 623819.610000 | 3870460.840000 | 1672.744 | 80 | yes |
| src-elevation#81 | 623814.378000 | 3870458.778000 | 1674.738 | 82 | yes |
| src-elevation#83 | 623814.877000 | 3870468.884000 | 1674.855 | 84 | yes |
| src-elevation#85 | 623816.430000 | 3870478.715000 | 1674.239 | 86 | yes |
| src-elevation#87 | 623811.345000 | 3870476.817000 | 1677.438 | 88 | yes |
| src-elevation#89 | 623809.801000 | 3870470.583000 | 1677.805 | 8A | no |
| src-elevation#8B | 623814.808000 | 3870463.271000 | 1674.675 | 8C | yes |
| src-elevation#8D | 623809.115000 | 3870456.072000 | 1677.613 | 8E | no |
| src-elevation#8F | 623809.870000 | 3870465.113000 | 1677.632 | 90 | no |
| src-elevation#91 | 623803.322000 | 3870496.094000 | 1677.462 | 92 | no |
| src-seperated#69 | 623802.968000 | 3870483.552000 | 1678.998 | 6A | no |
| src-seperated#6B | 623800.747000 | 3870462.586000 | 1679.674 | 6C | no |
| src-seperated#6D | 623799.692000 | 3870451.712000 | 1680.071 | 6E | no |
| src-seperated#6F | 623807.567000 | 3870451.173000 | 1679.131 | 70 | no |
| src-seperated#71 | 623810.639000 | 3870476.965000 | 1678.330 | 72 | no |
| src-seperated#73 | 623842.615000 | 3870490.101000 | 1665.378 | 74 | no |

## Parcel, road and orientation

`seperated.dwg#D7` is the closed parcel candidate: 4 distinct vertices,
**600.004421 m²**, perimeter **107.139999974 m**, alternating edge lengths
**21.000 and 32.570 m**. The canonical model normalizes polygon winding, so its
vertex order differs from the raw polyline without changing its shape.

Open polylines `#BC` and `#C5` are geometrically parallel at **9.000 m** separation.
`#C5` follows the lower-X 21 m boundary edge, producing **21.000 m** inferred
frontage. Both line coordinates and the boundary vertices are in `evidence.json`.
Road classification comes from the proposed handle mapping, not a survey label
or legal-access certification.

“Drawing-west” means the lower-X side on a conventional X-right/Y-up drawing.
Neither DWG has GEODATA or a declared EPSG code; inspected model-space entities
provide no north arrow. There is no verified transform supporting a geographic
“north road” claim, and no second rotated reference frame was found to justify
the conflicting prose. UTM is owner-reported, with zone, hemisphere and datum
still unknown. Grid/true north and geographic bearings remain unestablished.

## Slope definitions and checks

For a triangle through `(x,y,z)` points, solve its plane as `z=ax+by+c`.
Steepest planar slope is `s = 100 sqrt(a²+b²)` percent (equivalently
`100 sqrt(nx²+ny²)/abs(nz)` for its normal). It is not the steepest edge slope.
An edge rise is `100 abs(Δz)/hypot(Δx,Δy)`. Areas used as weights are horizontal
XY areas, not inclined surface areas. No terrain is flattened or smoothed.

| Statistic | Value | Exact definition |
|---|---:|---|
| Whole survey mean | 38.867643% | `sum(s_i*A_i)/sum(A_i)`, all 47 triangles |
| Parcel mean | 40.680256% | `sum(s_i*area(T_i intersect parcel))/sum(area(T_i intersect parcel))` |
| Unweighted triangle mean | 49.414589% | `sum(s_i)/47`, each triangle given equal weight |
| Maximum triangle slope | 150.21% | maximum planar slope over the survey TIN |

The whole TIN covers **1350.969702 m²**. Its parcel intersection is
**599.840341 m²**, or **99.972653%** coverage of D7; about **0.164080 m²** is
uncovered and has no inferred slope/elevation. “100.0%” in rounded legacy reports
does not mean exact full coverage. Interpolated parcel extrema above refer to
covered terrain only.

The approximately **39%** report is reproducible and mathematically valid for
the whole survey TIN. Describing it as an average *across the parcel* was wrong.
**68.78%** is not reproduced by either area-weighting scope or the unweighted
mean. The additional 65.2% in the committed handoff is also unsupported.
These discrepancies cannot be explained as merely two valid definitions with
the evidence available.

Five triangles exceed 100%; their handles, smallest angles, steepest edges and
source combinations remain in the [review report](site-v1/site-report.md).
Two share `seperated#71` and `elevation#87`, separated by about **0.72 m** with
**0.89 m** elevation difference, about **124%** edge rise. The other three are
thin slivers with centroid outside the parcel (minimum angles about 0.3°–1.7°).
Their steep planar slopes can coexist with modest slopes on their long edges.
“Centroid in parcel” does not mean the entire triangle is contained: parcel
statistics use exact intersections, and the ledger includes those areas.

Both surveys are retained in their drawn overlapping frame; no datum shift is
invented. A wall, kerb, embankment, different survey epochs or a measurement
error could explain a close pair, but none is established. Sliver geometry and
cross-file proximity are diagnostic traits, not grounds to delete real data.

## Corrections and validation

Completed work on branch `codex/survey-evidence-correction`:

- Corrected unsupported hashes and measurements in `docs/MILESTONE_D_HANDOFF.md`.
- Added parcel intersection slope/area to validation, explicit scope labels in
  Markdown/HTML/SVG, and centroid wording for steep-triangle classification.
- Corrected the interview/program context to use parcel slope. Without covered
  parcel terrain its slope is unknown rather than silently using surrounding land.
- Added deterministic synthetic regressions for unequal triangle weights, partial
  intersections, missing/outside boundaries, source replay, numeric label evidence,
  reproducibility and unchanged ProjectStore events.
- Added `tools/audit_site.py`, ADR 0012 and metric documentation; refreshed the
  two synthetic Markdown snapshots and this separate review export. The original
  `reviews/site-v1/` export is retained as history.

Final validation: **421 passed** on Python **3.13.3**; **420 passed, 1 skipped** on
Python **3.11.12** (optional Anthropic SDK unavailable in that environment).
Ruff passed for `src tests examples tools`; all **22 schemas** are current;
ProjectStore verification is intact at **13 events, 10 artifact versions**.
Two fresh DWG replays have identical semantic hashes, and original DWG hashes
still match the source records. The first restricted test attempt failed at
ODA's macOS services and at stale snapshots; snapshots were refreshed and the
complete suites above passed with ODA accessible. Reproduce:

```bash
.venv/bin/python tools/audit_site.py projects/my-house --out /tmp/house-site-audit.json
.venv/bin/house-ai site report my-house --out /tmp/house-site-review
.venv/bin/python -m pytest -q
/tmp/venv311/bin/python -m pytest -q  # available local Python 3.11 environment
.venv/bin/ruff check src tests examples tools
.venv/bin/house-ai schemas check
.venv/bin/house-ai project verify my-house
```

The ODA integration needs macOS services unavailable in the restricted sandbox;
the complete suites were therefore run with the required execution permission.
Source and event hashes are checked without changing the project record.

## Independent review and outstanding confirmation

The corrected Milestone B site data and Milestone C site context are ready for
independent review. That does not approve either gate, complete the owner's
interview or authorize concept generation/Milestone D.

Still needed: human confirmation of declared units, UTM zone and hemisphere,
horizontal datum/EPSG, precise vertical datum, legal parcel boundary and road
interpretation/access. The surveyor should check the close steep pair,
cross-file point-name reuse, slivers, any retaining-wall breaklines and whether
both drawings represent compatible observations. There is no recorded
professional approval or basis for construction-ready claims.
