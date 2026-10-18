# Usability critics demonstration

Fictional inputs only. Run from the repository root:

```sh
.venv/bin/python -m pytest -q tests/benchmarks
.venv/bin/python -m house_ai.benchmarks.runner examples/benchmarks/fixtures --details
.venv/bin/python -m examples.usability.make_report --out /tmp/house-usability
```

The final command directly evaluates three solver-backed synthetic-hillside
concepts without opening a ProjectStore or approving any gate. It writes
`report.md` and `report.json`, including canonical input geometry, hashes,
individual metrics, findings with element IDs, policy assumptions and the full
cited furniture template catalogue. A captured example is in `demonstration/`.
Solver output can vary between platforms; test architectural properties, not
the bytes of a regenerated solver result.

`scenarios.py` supplies hand-authored analytical defect/clean twins for stairs,
headroom, landing blockage, height mismatch, door/bed conflicts, WC clearance,
double-bed width and corridor dead ends. `tests/benchmarks/` adds independent
tests of routes around concave corners/obstacles, private guest paths, kitchen
traffic, bathroom sightlines, stacking, garage capacity, outdoor door grades,
buried windows and conservative vehicle arrival. Every added critic also runs
over every R2 case with real expectations; unknown inputs retain null values.

For independent review, hand-check these three examples:

- Net area: a 4×3 m centreline room with 0.15 m partitions gives
  3.85×2.85 = 10.9725 m². A 0.9 m wide floor-level doorway adds
  0.9×0.075 = 0.0675 m² of half-wall recess to that room.
- L-shaped point route: (5,1) → (2,2) → (1,5) measures
  2√10 = 6.324555… m. A straight line crosses outside the L and is rejected.
- Double bed: the assumed access envelope is 2.8×2.75 m. A 2.6 m wide
  centreline room is 2.45 m clear and fails in both orientations; the 3.4 m
  clean twin fits bed and wardrobe in the declared search.

The checks are conceptual studies under explicit assumptions. Routes measure
points, furniture search is discrete, headroom follows a straight pitch line,
and window/terrain exposure is sampled. Missing stair orientation or vehicle
dimensions is not checked. There is no regulatory, solar, airflow or acoustic
performance certification. Details and sources are in
[ADR 0019](../../docs/adr/0019-usability-geometry-and-assumptions.md).
