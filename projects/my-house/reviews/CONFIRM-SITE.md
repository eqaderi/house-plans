# Your site: what the survey tells us, what you told us, and what is still open

Project: `projects/my-house` (state `SITE_NEEDS_VERIFICATION`, nothing approved).
Review page: `projects/my-house/reviews/site-v1/index.html` (open it in a browser).
Sources: `surveys/seperated.dwg` (sha256 27624ba1…) and `surveys/elevation.dwg`
(sha256 9689880c…). The wrong file `final.dwg` was withdrawn and is not used.

## What you told us (recorded 2026-10-17, not yet confirmed in the tool)

Recorded verbatim as owner statements `stmt-001` to `stmt-005`
(`house-ai statement list my-house`). They are evidence; they change no status
until you confirm with the command below.

| You said | What it settles | What it leaves open |
|---|---|---|
| "The survey uses UTM coordinates." | the coordinates are UTM grid metres | UTM **zone**, **hemisphere (N/S)**, horizontal **datum / EPSG code** |
| "The elevation values are in METRES ABOVE SEA LEVEL." | heights are metres | **which** sea-level (vertical) datum |
| "The approximately 12–12.5 metre elevation difference is CORRECT." | the relief is real, not a unit error | — |
| "My land is genuinely steep." | design must work with the slope (split levels, access, retaining, drainage) | — |
| "UTM zone is still unknown. Horizontal datum / EPSG is still unknown. The precise vertical datum is still unknown." | nothing is guessed | the three items above |

## Already answered by the survey

| Item | What the files show | Kind |
|---|---|---|
| Drawing unit | both files declare metres (`$INSUNITS = 6`) | measured (declared) |
| Same frame | both drawings overlap in one coordinate frame | measured |
| Parcel candidate | the only closed polyline is `D7` in seperated.dwg: 4 corners, edges 21.000 / 32.570 / 21.000 / 32.570 m | measured |
| Area / perimeter | 600.00 m² / 107.140 m (a parallelogram) | calculated |
| Road | two parallel lines `BC` and `C5`, 9.000 m apart, along the parcel's 21.000 m west edge (drawing frame) | measured lines; "road" is an interpretation |
| Elevation points | 27 points: 21 in elevation.dwg, 6 in seperated.dwg; z 1664.884 to 1680.071 m | measured |
| Terrain | falls about 12.5 m across the parcel; area-weighted mean slope about 39 % | calculated (preliminary) |
| North | no georeference in the files, so north is **not established** | unknown |

## The five triangles steeper than 100 % (investigated, nothing smoothed)

The terrain is a triangulated surface through the surveyed points only. Five of its
47 triangles are steeper than 100 % (45°). Each is listed with its measurements in
the review page (section 5) and in `site-report.md`. What the measurements show:

- **One steep pair of points explains two of them (150 % and 124 %).**
  `spot-seperated-71` (seperated.dwg) and `spot-elevation-87` (elevation.dwg) are
  0.72 m apart with 0.89 m height difference: a 124 % rise. This is near the parcel's
  north-west corner (drawing frame); the 150 % triangle lies inside the parcel.
  *Possible readings (inference, for your surveyor):* a wall, kerb or step there, or
  the two surveys measured nearby ground at different heights.
- **The other three (147 %, 117 %, 117 %) are thin slivers outside the parcel.**
  Their smallest angles are 0.3°–1.7°, and no edge of them rises more than 34 %
  (7 %, 12 % and 34 %). The steepness comes from the triangle's thin shape at the
  survey's outer edge, not from two surveyed points being steep.
  *Reading (inference):* an artefact of triangulating nearly collinear points from
  the two files, not evidence of steeper ground. They stay in the model as surveyed.

None of this changes the overall picture you confirmed: the land is steep (about
39 % on average across the parcel), with a 12–12.5 m drop.

## What only you (or your surveyor) can still confirm

1. **Drawing and elevation units: you can do this now.** UTM is metric and you said
   heights are metres, so confirm both (command 1 below).
2. **Horizontal CRS.** Needed: UTM **zone** (1–60), **hemisphere** (N or S) and the
   **datum** (for example WGS 84, or a national datum). Ask the surveyor for the EPSG
   code, or run `.venv/bin/house-ai crs utm-candidates <zone> <N|S>` to list the codes
   for a zone. When you confirm, the command prints the parcel's longitude/latitude:
   check it on a map (a wrong zone moves it hundreds of kilometres).
   *Note:* notes from an earlier toolchain in this repository's history (before
   commit bf50e60) used EPSG:32638 (WGS 84 / UTM zone 38N). Where that came from is
   unknown, so it is not applied. If your surveyor confirms it, use it.
3. **Vertical datum.** You said the heights are above sea level; which datum (the
   national height system) is not known. Two ways to settle it, your choice:
   - **A. National datum:** ask the surveyor for its name (and EPSG code if any).
   - **B. Survey benchmark:** elevation.dwg labels one point "نقطه مبنا" ("reference
     point") at z 1677.462. Choosing it records heights as relative to that
     benchmark, which is enough for designing the house; the sea-level reading stays
     recorded as your statement.
4. **Parcel boundary.** Is polyline `D7` (600.00 m², 21.00 × 32.57 m) your legal
   parcel? Compare it with your title deed or cadastral plan.
5. **Road.** Are `BC` and `C5` the edges of a 9 m road along your west side, and is
   that your access side?
6. **For the surveyor:** the steep pair above; the 6 point names in seperated.dwg that
   repeat names from elevation.dwg at other places (22–45 m apart); and the 6 labels
   in seperated.dwg that carry names only (their heights cannot be cross-checked).

## Commands for you to run in your own terminal

Each command shows what you confirm and asks you to type a phrase.

```bash
cd /Users/ershadqaderi/_projects/house-plans

# 1. now: confirm the units you have stated (heights in metres, UTM is metres)
.venv/bin/house-ai site confirm my-house --confirmer <your-name> --units m --elevation-units m
#   type when asked: confirm site site

# 2. later, when the surveyor has answered: CRS, datum, boundary (choose ONE datum line)
.venv/bin/house-ai site confirm my-house --confirmer <your-name> \
    --epsg <EPSG-code> \
    --vertical-datum "<datum name>" [--vertical-epsg <code>] \
    --boundary-verified
#   or the benchmark: --vertical-local --vertical-datum "survey benchmark (نقطه مبنا, z 1677.462)"

# 3. re-check the site and regenerate the review package (writes reviews/site-v<N>/)
.venv/bin/house-ai workflow transition my-house SITE_INGESTION --reason "site facts confirmed" --actor human:<your-name>
.venv/bin/house-ai workflow assess-site my-house --id site --actor human:<your-name>
.venv/bin/house-ai site report my-house

# 4. only when the report shows no blockers and you agree with it: approve the site
.venv/bin/house-ai workflow request-approval my-house site --id site --actor human:<your-name>
.venv/bin/house-ai workflow approve my-house site --id site --approver <your-name>
```

Command 1 alone does not approve anything: the CRS, the vertical datum and the
boundary still block the site gate until step 2.
