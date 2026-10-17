# Analytical geometry evaluation

These synthetic closed solids are generated in `experiment.py`, not copied from
any project. Provision disposable environments (network needed once), then run:

```sh
python3.11 -m venv /tmp/house-s3-py311
/tmp/house-s3-py311/bin/pip install -r examples/tool-evaluations/geometry/requirements.txt
/tmp/house-s3-py311/bin/python examples/tool-evaluations/geometry/experiment.py
python3.13 -m venv /tmp/house-s3-py313
/tmp/house-s3-py313/bin/pip install -r examples/tool-evaluations/geometry/requirements.txt
/tmp/house-s3-py313/bin/python examples/tool-evaluations/geometry/experiment.py
```

The script asserts the raw volumes, cut above z=3, void below a hypothetical
pad at z=3, horizontal sections at z=3, touching/disjoint intersections and
rejection of an open TIN. The footprint is 10×6 m; terrain closes to z=0.

| Fixture | Height | Terrain m³ | Cut m³ | Void m³ | Section m² |
|---|---|---:|---:|---:|---:|
| planar slope | 2 + x/5 | 180 | 15 | 15 | 30 |
| wedge | 1 + 2x/5 | 180 | 30 | 30 | 30 |
| pyramid | 1 m base, 4 m apex rise | 140 | 10 | 50 | 15 |
| stepped pad | 2 for x<5, 4 for x>5 | 180 | 30 | 30 | 30 |

For a plane the cut is a triangular prism: half of the affected width times
excess height times 6 m. For the pyramid, total volume is 60×1 + 60×4/3 = 140;
the upper similar pyramid has 1/2 side scale and 1/8 volume, 10 m³. Its z=3
section is 60/4 = 15 m². Void is (60×3) − (terrain−cut). The step cut/void are
5×6×1 = 30 m³ each. These are volume metrics, not engineering suitability.

Results are `simulation_result` and tolerance is absolute 1e-7 m³/m².
Trimesh's boolean engine here **is Manifold**, so facade agreement is not an
independent second boolean algorithm. Trimesh mass properties and its section
intersection code are compared with direct Manifold volume/slice output.
The section area summation assumes convex loops without holes in these fixtures;
this is not a proposed generic section adapter. S8 must extend to holes,
near-degenerate/noisy inputs, arbitrary section lines and real coordinate scales.

`results-py311.json` / `results-py313.json` record actual Darwin arm64 runs.
`wheels.json` captures official PyPI filenames/hashes for the pins, including
cp311/cp313 macOS arm64 native wheels and universal pure Python wheels.
Trimesh's high-level section paths need scipy/networkx in this experiment;
installing only its minimal NumPy requirement raised ModuleNotFoundError.

See `docs/research/s3-tool-evaluations.md` for licences, decisions and limits.
