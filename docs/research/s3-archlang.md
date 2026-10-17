# S3-04 — ArchLang as an independent diagnostic

Evaluation date: 2026-10-17. All experiments use fabricated geometry. No owner
project data, ProjectStore writes, gate approvals, project dependency changes, or
MCP configuration changes occur.

**Decision: ADAPT its diagnostic patterns into future S6 critics; do not add an
ArchLang runtime dependency in S3.** This is an engineering judgment supported by
the experiment below, pending the independent stage review. The canonical
HouseModel remains authoritative. The narrow export is an evaluation adapter,
not a supported product exporter.

## Identity and primary sources

- Verified from npm metadata and the installed package: floor-plan ArchLang is
  [`@chanmeng666/archlang@1.43.1`](https://www.npmjs.com/package/@chanmeng666/archlang/v/1.43.1),
  repository [ChanMeng666/archlang](https://github.com/ChanMeng666/archlang), MIT,
  Node >=18. The actual entry point is `archlang` (avoid `arch`, the OS command).
- The [registry release metadata](https://registry.npmjs.org/@chanmeng666%2farchlang/1.43.1)
  identifies the exact [release tarball](https://registry.npmjs.org/@chanmeng666/archlang/-/archlang-1.43.1.tgz):
  SHA-1 `796e20bba890a37e0ba080254f7097fc8a066f85`; integrity
  `sha512-KNelknw2Ff8Fbh3n2LVpSDNa9BqLL/XjDpeiAMsjlxx9TgCW4sW/5lqQVBnovLwvXEzWrofzhClB97AdV6SFPQ==`.
- Verified by reading the tarball's `LICENSE`: MIT, copyright 2026 Chan Meng;
  upstream [license source](https://github.com/ChanMeng666/archlang/blob/main/LICENSE).
  No upstream implementation or skill text is copied into this repository.
- The installed `spec.llm.md` and `archlang spec` provide the syntax used here;
  [upstream language reference](https://github.com/ChanMeng666/archlang/blob/main/spec.llm.md).
  GitHub `main` may move; the pinned npm tarball is the experiment's exact source.
- The [official README](https://github.com/ChanMeng666/archlang/blob/main/README.md)
  documents an optional CLI wrapper MCP server. Independently checked npm metadata:
  [`@chanmeng666/archlang-mcp@0.2.26`](https://www.npmjs.com/package/@chanmeng666/archlang-mcp/v/0.2.26),
  MIT, same repository `packages/mcp`. Its version is separate from the core.
  It was not installed, configured or exercised. MCP support is documented and
  published, not locally verified.
- [`@archlang/cli`](https://www.npmjs.com/package/@archlang/cli) is a different
  system-architecture language. Its version must not be used for this floor-plan
  tool. Earlier unpinned descriptions are not installation evidence.

## Recorded experiment

Measured environment: macOS arm64, Node 26.12.0, npm 11.20.0, core 1.43.1.
Installed with `--ignore-scripts` under `/tmp/house-ai-s3-archlang`; no project
environment modification. Default optional dependencies were installed in that
temporary prefix, although only core SVG/JSON/CLI paths were used. This experiment
does not establish compatibility with every supported Node release or optional
PDF/PNG renderer. Reproduce using
[`examples/tool-evaluations/archlang/README.md`](../../examples/tool-evaluations/archlang/README.md).

The baseline is an analytical, fabricated 7 × 4 m rectangle split at x=4 m:
living 16 m² and bedroom 12 m², five straight centerline walls, exterior entrance,
interior bedroom door, and two windows. It has **zero canonical integrity
findings**. No site envelope or program is supplied, so those checks are not
claimed. This fixture tests a representation and its diagnostics, not a generated
architectural design.

The export converts canonical y-up metres to ArchLang y-down millimetres:
`(x,y) -> (1000*x,-1000*y)`. Negative y coordinates compile successfully. It keeps
room polygons, ids, names, `uses`, straight wall centerlines/thickness/heights,
and opening dimensions. Canonical opening offsets name the near edge; ArchLang's
hosted position is the midpoint, so the export adds half the width. Door swing
destinations are explicit. The seeded sofa converts its center to a top-left
footprint. Unsupported collection/geometry cases are deliberately refused.

Measured results are asserted by `run_experiment.py` and committed under
[`results/summary.json`](../../examples/tool-evaluations/archlang/results/summary.json).

| Case / synthetic mutation | Canonical integrity finding | ArchLang lint findings | Compile / lint / strict validate exit |
|---|---|---|---|
| Clean baseline | none | none | 0 / 0 / 0 |
| Remove interior bedroom door | `space_unreachable` | `W_ROOM_DISCONNECTED` | 0 / 0 / 2 |
| Remove bedroom window | none | `W_BEDROOM_NO_WINDOW` | 0 / 0 / 2 |
| Sofa center (2,0.6), footprint 1.6 × 0.8 m in entrance approach | none | `W_SWING_OBSTRUCTED`, `W_DOORWAY_BLOCKED`, `W_PATH_TOO_NARROW` twice (living and bedroom routes) | 0 / 0 / 2 |

**Measured geometry and semantics:** inverse-transformed room polygons have
0 m² symmetric difference; 16 + 12 = 28 m² centerline area agrees exactly.
All five wall endpoints, thicknesses and heights, four opening centers, widths,
heads and window sills agree to a maximum 1.11e-16 m floating-point error.
Room ids, labels and `uses`, door connectivity, window-to-room association and
baseline reachability agree. These checks read independently compiled Plan JSON
and `describe`, not the generated `.arch` text. ArchLang derives 25.46 m² net
area; this was recorded, not independently verified as an actual finish-to-finish
area. Its added `room_type` maps the ordinary bedroom to `MasterRoom`; that
classification is not a canonical fact and must not be imported.

All defect sources compile cleanly. Non-strict `lint --json` reports warnings
while returning `ok: true` and exit 0. Only `validate --strict --json` fails these
warnings (exit 2). A future adapter must retain diagnostics and source spans,
not equate compile success or plain lint exit 0 with architectural acceptance.

## Boundaries and decision rationale

- **Measured value:** the tool found window absence and entrance/swing obstruction
  beyond current integrity checks, while reproducing the reachability fault.
  This supports independent S6 warning categories and seeded regression tests.
- **Inference / engineering judgment:** adapt bedroom window availability,
  doorway approach, swing collision and minimum route-width concepts behind
  canonical S6 evaluators, with explicit configurable assumptions and ground
  truth. An external compiler should not determine domain semantics or approval.
  Do not copy upstream code without retaining its license notice and review.
- **Representation limitations:** this adapter covers one zero-elevation level,
  two room functions, polygons without holes, straight exterior/interior walls,
  swinging doors, fixed windows and an unrotated sofa. It is not a general
  HouseModel round trip. Stairs, arbitrary levels, terrain, privacy zones,
  retaining structures, slabs, materials, provenance, assumptions and relationships
  are not exported. Published language support for other features is not proof of
  faithful conversion of these domain entities.
- **Not checked:** hinge handedness conventions across the y reflection, window
  operation, real clear opening widths, cardinal orientation, north uncertainty,
  sunlight/daylight performance, legal requirements, structure or professional
  code compliance. `describe` derives default cardinal window facings despite no
  north observation in this fixture; those must remain untrusted. The language's
  60 mm door-clearance estimate, 100 mm circulation grid and body radius are tool
  assumptions, not measured building dimensions or jurisdictional standards.
- **Sampling limit:** three isolated defects on one two-room model demonstrate
  those checks only; false-positive rates, multi-floor and concave/holey plans,
  and cross-version stability need broader benchmarks before any product adapter.
- **Why ADAPT:** adds useful check ideas without introducing a second semantic
  authority, Node runtime and a potentially lossy translation into the offline
  pipeline. No MCP is necessary for this file-to-file diagnostic. Any later
  integration requires its own reviewed adapter scope and richer benchmarks.
