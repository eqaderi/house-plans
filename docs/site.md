# Site (phase 1)

Measured on 2026-10-13 from the two survey DWGs. Every number here is quoted
from a tool's output; rerun the commands to reproduce it.

## Files and conversion

| Source | SHA-256 | Derived |
|---|---|---|
| `sources/height-points.dwg` | `9689880c47d9d0780089c5d4077f9396f5c29a2feeb298fafb86840bbae02f02` | `derived/survey/height-points.dxf` |
| `sources/seperated.dwg` | `27624ba14003e3d898143a9d86985d50d3d7098db0a45b94ae2dd999571519ed` | `derived/survey/seperated.dxf` |

```sh
bin/hp dwg2dxf sources/height-points.dwg derived/survey/
bin/hp dwg2dxf sources/seperated.dwg derived/survey/
bin/hp survey derived/survey/height-points.dxf
bin/hp survey derived/survey/seperated.dxf
~/.venvs/architecture-ai/bin/python scripts/measure_site.py
```

Tools: ODA File Converter 27.9.0.0 (DXF 2018, AC1032), ezdxf 1.4.4,
shapely 2.1.2, pyproj 3.7.2 / PROJ 9.5.1.

This file holds the `derived/` inventory because `.claude/settings.json`
denies agent edits under `derived/`, including `derived/README.md`.

`sources/MANIFEST.sha256` is still empty: the same settings block agent
writes under `sources/`. The owner records the checksums (command in
`docs/STATUS.md`).

## What each file holds

Both files have every entity on layer `0`. No blocks, no UCS, no north arrow,
and empty paper-space layouts. Contents below were identified by geometry and
entity handle, not by layer name.

| File | Entities | Meaning |
|---|---|---|
| `height-points.dxf` | 21 POINT, each with an MTEXT label (name and Z) | Pt1–Pt20 spot heights on the plot; `نقطه مبنا` (benchmark), 20.772 m outside the plot to the NNW, Z 1677.462. Every label equals its point's Z. |
| `seperated.dxf` | 6 POINT with MTEXT labels (name only); LWPOLYLINE `BC`, `C5`, `D7` | `BC` is the road's west edge (through Pt1–Pt3). `C5` is the road's east edge, which is also the plot's west boundary. `D7` is the plot outline, closed by repeating its first vertex. Pt4 and Pt5 are in the road; Pt6 is 1.390 m outside the plot's NE corner. The polylines' elevation 1678.998 copies Pt1's Z and is not a measurement. |

`hp survey` counts heights as `n=42` and `n=15`. In `height-points.dxf` each
POINT and its MTEXT label are counted separately (21 + 21). In
`seperated.dxf` the 15 are 6 POINT + 6 MTEXT + the three polylines'
elevation 1678.998, which is not a measurement. There are 21 and 6 measured
points.

## Units and coordinates

- `$INSUNITS=6 (metres)`. Cross-check: the road's two edges are `9.000 m`
  apart at all six vertices, which matches the owner's 9 m road.
- No CRS is stored in the files. The coordinates (E 623 8xx, N 3 870 4xx)
  fit UTM. Under **EPSG:32638 (UTM 38N, WGS84)** the plot centroid is at
  `lat 34.969247 lon 46.356413`. Banehvreh (Paveh County, Kermanshah) is
  listed at 34.97056 N, 46.36000 E
  ([Wikipedia/OSM](https://en.wikipedia.org/wiki/Banehvreh)). Under 39N the
  same point falls at 52.36 E, outside Kermanshah province.
  **Assumed 38N; the owner confirms up = north.**
- North: drawing +Y is grid north (`$ANGBASE 0`, no UCS). Grid north points
  `0.778°` east of true north. True azimuth = grid azimuth + 0.778°.
- Qibla: true azimuth `204.75°`, grid azimuth `203.97°`. Valid only if the
  CRS is 38N.

## Road and plot

```
road (BC west edge, C5 east edge): perpendicular width at each vertex  -> 9.000 m at all 6
plot D7: vertices, distance to road east edge C5
  V0 (623811.317, 3870476.922)  to C5 0.001 m     NW corner
  V1 (623841.339, 3870489.550)  to C5 30.230 m    NE corner
  V2 (623839.189, 3870468.660)  to C5 28.588 m    SE corner
  V3 (623809.167, 3870456.033)  to C5 0.013 m     SW corner
  area 600.004 m2   perimeter 107.140 m
sides (outward facing direction, true azimuth)
  V0->V1  32.570 m  north side, faces 337.97 (NNW)
  V1->V2  21.000 m  east side,  faces  96.65 (E)
  V2->V3  32.570 m  south side, faces 157.97 (SSE)
  V3->V0  21.000 m  west side on the road, faces 276.65 (W)
perpendicular distance between opposite sides
  north to south  18.422 m
  east to west    28.572 m
interior angles   V0 118.69, V1 61.31, V2 118.69, V3 61.31 deg
```

`hp survey`, after the fix in this session:
`600.004  0  4 vertices ... [LWPOLYLINE D7, closed by end points]`

- The plot is a **parallelogram, not a rectangle**. The road side runs at a
  grid azimuth of 5.88°. The north and south sides run at 67.19°, so the
  corners are 61°/119°. A rectangular house cannot align with both the road
  and the side boundaries.
- The west boundary lies on the road's east edge (0.001 m and 0.013 m).
- If the 1 m alley strip is inside D7, measured square to the south side,
  it is `32.570 m2` and leaves `567.434 m2`.

## Heights

Height range (`hp survey`): `height-points.dxf` from 1664.884 to 1677.805;
`seperated.dxf` from 1665.378 to 1680.071.

Corner heights use the `height-points.dxf` point nearest each corner:

```
V0 NW  Pt16 at 0.109 m  Z 1677.438
V1 NE  Pt1  at 0.055 m  Z 1664.884
V2 SE  Pt4  at 0.215 m  Z 1665.648
V3 SW  Pt19 at 0.065 m  Z 1677.613
north side V0->V1  drop 12.554 m over 32.570 m = 38.5 %
south side V3->V2  drop 11.965 m over 32.570 m = 36.7 %
west side  (road)  0.175 m over 21.000 m = 0.8 %
east side          0.764 m over 21.000 m = 3.6 %
```

The site falls steeply from the road (west) to the east, at about 37–38 %.
It is almost level along the road. The interior points (Pt5–Pt15, Pt18) are
listed with their Z in the script output. No terrain model has been made yet.

The two files disagree on how the road meets the plot, so no road-to-plot
step is assumed yet (see #16 in `docs/open-questions.md`):

- `height-points.dxf`: its points just outside the west boundary, in the road
  edge, are Pt17 (0.859 m out) at Z 1677.805, Pt20 (0.230 m out) at
  1677.632 and Pt19 (0.055 m out) at 1677.613. That puts the road edge close
  to the corner heights V0 1677.438 and V3 1677.613.
- `seperated.dxf`: on the road's east edge, Pt5 (0.679 m outside the NW
  corner) is Z 1678.330 and Pt4 is Z 1679.131. On the road's west edge,
  Pt1–Pt3 run from 1678.998 to 1680.071.

## Ambiguities (for the owner / surveyor)

1. **The two files disagree in Z.** Two point pairs lie close together but
   differ in height:
   - Near the NW corner: hp Pt16 and sep Pt5, 0.721 m apart, `dZ +0.892 m`.
   - Near the NE corner: hp Pt1 and sep Pt6, 1.445 m apart, `dZ +0.494 m`.

   At the NE corner the `seperated` point is further downhill but higher.
   That suggests two height datums or two survey dates, not terrain. Until
   resolved, heights come from `height-points.dxf`, which carries the
   benchmark and labelled Z.
2. **The CRS is not stated.** 38N is inferred, as described above.
3. **Is D7 the deed boundary?** Its area of 600.004 m² and sides of
   32.570 m × 21.000 m look drawn to a deed figure, not surveyed corner by
   corner. The deed is not in `sources/`.
4. **What does the file name "seperated" mean?** Perhaps a plot subdivided
   (تفکیک) from a larger parcel. That would affect the boundary's legal
   status.
5. **Who set the benchmark `نقطه مبنا`, and on which datum?** It sits
   20.772 m NNW of the plot, in or beside the road.

## Decided 2026-10-13 (delegated by the owner; see `docs/decisions.md`)

- Plan geometry from `seperated.dxf`, all heights from `height-points.dxf`.

- Height datum: the benchmark `نقطه مبنا`, Z 1677.462, with ±0.00 chosen in
  phase 3.
- Local origin: corner V3 (SW, where the road meets the alley), E 623809.167,
  N 3870456.033.
