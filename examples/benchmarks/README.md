# Synthetic architectural benchmarks

These are fictional test inputs, not designs for the homeowner's site. The
generator reads only the existing synthetic bungalow example. No private
project, survey coordinate, geographic CRS or human approval is copied.

Run from the repository root:

```sh
.venv/bin/python examples/benchmarks/make_fixtures.py --check
.venv/bin/python -m house_ai.benchmarks.runner examples/benchmarks/fixtures
.venv/bin/python -m house_ai.benchmarks.runner examples/benchmarks/fixtures --details
.venv/bin/python -m house_ai.benchmarks.runner examples/benchmarks/fixtures --json
.venv/bin/python -m pytest -q tests/test_benchmarks.py
```

Regenerate with the first command without `--check`. `--check` fails on missing,
changed or unexpected JSON files. Export the schema after changing the contract:
`.venv/bin/house-ai schemas export`. The fixture format is
`schemas/benchmark_fixture.schema.json`; the rationale is
[ADR 0017](../../docs/adr/0017-synthetic-benchmark-contract.md).

The runner prints every acceptance category, including empty and unfinished
ones. Its JSON output includes the observed value, method, claim status and
regression outcome. A wrong expected value, missing metric, ambiguous subject
selection or stale input hash fails. Use `--require-complete` to fail on future
probes too. That stricter command intentionally fails in S3.

`PASS` means an expectation matched. A regression that correctly detects an
unreachable bathroom passes, while the bathroom remains unusable. Declared
program quantities and accessibility requirements are input observations;
they do not prove the generated design meets those requirements.

| Fixture | Independent ground truth / scenario |
|---|---|
| flat-simple | 20 × 30 m; flat plane; parcel 600 m², invented envelope 384 m² |
| narrow-deep | 10 × 60 m; parcel 600 m², envelope 324 m² |
| steep-reference | 19.2 × 31.25 m; z=12.5−0.4y; 600 m², 12.5 m relief, 40% slope |
| road-high / road-low | z=15−0.5y vs z=0.5y; opposite road/rear elevation relationships |
| cross-slope | z=0.4x; gradient across road frontage rather than into parcel |
| diagonal-slope | z=12+0.3x−0.4y; 50% gradient magnitude |
| concave | L boundary 576 m²; L envelope 318 m²; notch excluded |
| breakline-noise | Retaining-wall trace plus XY pair 1e−7 m apart, 2 m conflicting Z; builder refuses surface |
| sliver-tin | 0.1 mm edge offset and +1 m noise; minimum triangle area 0.001 m²; point retained |
| unknown-north | Unconfirmed CRS; five implemented orientation outputs must have null values and `not_checked` status |
| family-privacy | Hard guest/family separation; seeded entry opens onto both bedrooms |
| multigenerational | Accessible entry bedroom and bathroom; seeded missing bathroom door |
| heavy-cooking | Two parking bays, separate heavy kitchen, garage grocery route; seeded missing service spaces |
| large-terrace | 60 m² terrace connected to living on 40% terrain; support remains unmeasured |
| social-cooking / quiet-cooking | Same site and candidates; opposite connected/separated preferences reverse satisfaction |

All rectangle offsets are invented assumptions, never zoning rules. Analytical
plane slope is `100*sqrt(dx²+dy²)`; relief is `abs(dx)*width+abs(dy)*depth`.
The runner obtains parcel-clipped area-weighted slope from the actual site
validator, independent of those formulas. No extrapolation is allowed beyond
the survey hull. Conflicting heights are preserved, not averaged away.

Both preference candidates reuse the human-authored golden bungalow geometry.
The isolated candidate removes the living/kitchen cased opening and reassigns
the existing rear room as kitchen; areas and walls stay fixed. Integrity is
checked with the matching program. The kitchen changes from 30 to 17.5 m² and
passable graph edges from seven to six. A social household prefers direct
connection; a quiet household prefers separation. These are fixed comparison
cases, not proof that the generator can produce diverse plans.

S6 usability runs in `tests/benchmarks/`: destination-aware guest routes,
conceptual turning space and missing grocery-route endpoints now have real
expectations. Unknown orientation is explicitly not checked. Remaining future
probes name their owner: S5 visual consistency; S7 generated diversity and
versioned revisions; S8 constrained breaklines, terrain quality and terrace
support. Unimplemented probes remain `NOT_CHECKED`.
