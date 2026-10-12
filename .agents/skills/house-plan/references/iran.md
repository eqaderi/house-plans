# Iran: what applies and how sure we are

Researched 2026-10-12 (Mehr 1405). The official PDFs on inbr.ir and
bhrc.ac.ir could not be fetched; Mabhas 4 values come from a transcription of
the 1396 edition (pouyeshgroup.org/national-building/) that is known to reverse
digits in places (it prints 2.50 where independent sources give 2.05). That is
why the encoded rules are `transcribed`, not `verified`. **Getting the official
Mabhas 4 (1396) PDF and confirming each value is the first job** — then flip
each rule to `verified` in `rules/iran.yaml` with the page reference.

## Editions in force

| Regulation | Edition | Note |
|---|---|---|
| Mabhas 4, general building requirements (الزامات عمومی ساختمان) | 1396 (3rd) | A mandatory protective/security appendix was announced (nezamqom.ir/news/1830); date unverified |
| Mabhas 3, fire protection | 1395 | Revision in public comment (nezamqom.ir/news/2141) |
| Mabhas 19, energy | 1399 and 1404 both allowed until 1405/12/29 | nezamqom.ir/news/2177 |
| Standard 2800, seismic design | 5th edition, approved 1404/12/27 | Mandatory for publicly funded contracts from 1405/04/01 (isss.ir); no notice found for private permits — ask the engineering organisation which edition your permit uses |
| Mabhas 2, permits and responsibilities | — | Only drawings stamped by a licensed designer within their competence are accepted |

A single-family house is occupancy **م-۴**, following the **م-۲** rules
(4-3-2-1-4); one- or two-storey buildings are building groups 1–3 (4-3-3-2).

## Encoded in `rules/iran.yaml`

Room minimums, clear heights, kitchen and wet-room sizes, daylight 1/8,
kitchen ventilation 1/16, entrance and room door widths, corridor width, stair
width, going, 2R+G = 630–640 mm, and the Standard 2800 re-entrant corner test.
Every entry carries its clause and status.

## Known but not encoded (check by hand, or extend the kit)

| Rule | Value | Clause | Status |
|---|---|---|---|
| Main room width when the unit is 75 m² or more | ≥ 2.70 m | 4-7-1-1-8 | transcribed |
| Main room in a unit under 75 m² | ≥ 9 m², every side ≥ 2.50 m | 4-7-1-1-8 | transcribed |
| 2.60 m height for larger rooms | area threshold unreadable | 4-7-1-1-9 | **open** |
| Clearance under beams and door frames; sloped ceilings | 2.05 or 2.50 m | 4-5-2-2-3/4 | **open** (digit reversal) |
| Door heights | 2.05 vs 2.50 m | 4-5-1-5-1 | **open** |
| Stair headroom from the nosing line | 2.05 m per secondary sources | 4-5-1-7-6 | unverified |
| Landing depth | ≥ stair width | 4-5-1-7-4 | transcribed |
| Stair width with a turn or landing | ≥ 1.10 m | 4-7-1-1-3 | transcribed |
| Nosing radius | ≤ 13 mm | 4-5-1-12-3 | transcribed |
| Guard height where the drop exceeds 0.70 m | ≥ 1.10 m; baluster gap ≤ 0.11 m; stair handrail ≥ 0.90 m | 4-5-7-1-4, 4-8-9-4, 4-9-9-1 | transcribed |
| Daylight 1/7 (one wall, room deeper than 4.50 m); 1/6 or 1/5 when the head is below 2.10 m | — | 4-5-2-3-2/3 | transcribed |
| Daylight depth from a window | ≤ 7 m | 4-5-2-8-3 | transcribed |
| Kitchen with dining | ≥ 7.50 m², width ≥ 2.15 m | 4-7-1-1-11/12 | transcribed |
| Wall kitchen | length ≥ 3.00 m, clear strip ≥ 1.10 m; not open to the living room if the unit is ≥ 75 m² | 4-7-1-1-13 | transcribed |
| Entrance space | clear depth ≥ 1.40 m, area ≥ 2 m² (recommended in villas) | 4-7-1-1-1 | transcribed |
| Mezzanine | upper ≥ 2.10 m, lower ≥ 2.40 m; area ≤ 1/3 of the space below | 4-5-2-2-5, 4-4-1-4 | transcribed |
| Light well serving habitable rooms | ≥ 12 m² and ≥ 3 m wide (plot < 200 m²: ≥ 6 % of plot, ≥ 2 m wide) | 4-5-8-3-5/7/8 | transcribed |
| Light well serving kitchen or storage only | ≥ 6 m² and ≥ 2 m wide | 4-5-8-3-6 | transcribed |
| Facing windows across a light well | ≥ 3 m apart | 4-5-8-3-10 | transcribed |
| Ramps | ≤ 8 % on access routes, else ≤ 12.5 %; landing every 9 m | 4-5-1-8-1/2 | transcribed |
| Parking stall | 2.50 × 5.00 m; 3.00 × 5.00 m between walls; tandem 2.50 × 6.00 m | 4-5-10-2-4 | transcribed |
| Small garage | height ≥ 2.20 m; aisle ≥ 3.00 m; covered ramp ≤ 17 % with the first and last metre ≤ 10 % | 4-5-10-2 | transcribed |
| Building height, groups 1–3 | 1 storey ≤ 4.90 m (5.80 m with basement window), 2 storeys ≤ 8.10 m (9 m), **from the mean adjacent street level** — critical on a slope | 4-4-1-2-1 | transcribed |
| Basement used as a habitable room | external light and air shafts if the ceiling is less than 0.90 m above grade | 4-5-2-4-1 | transcribed |
| Room area measurement | excludes built-in closets, niches, door and window reveals and finishes | 4-5-2-1-1 | transcribed |

### Standard 2800, layout level (secondary sources; the structural engineer decides)

- Re-entrant corner irregularity: setback above 20 % of the plan dimension in
  **both** directions (maktabsaze.org/p-irregularity). Encoded as a warning.
- Diaphragm openings: 25 % (5th edition, per maktabsaze) or 50 % (4th) of the
  floor area — sources disagree. **Open.**
- Separation joint from the neighbour: at least 0.005 × height above the base
  at each storey for buildings up to 5 storeys and 18 m (5th edition, per
  maktabsaze.org/seam); taller buildings use the displacement formula.
- Confined masonry: at most 2 storeys plus basement, roof at most 8 m above
  mean grade, length at most 3× width or 25 m (noavarpub.com).

## Municipal rules (only after the site's plan is known)

The site is at about 1678 m in Tehran province. That may be Tehran city,
Shemiranat, Lavasan or another municipality; **confirm which detailed plan
governs it and get the دستور نقشه first.** For reference, the Tehran detailed
plan (1398 compilation, holding-golestan.com/images/1400/06/tarh.pdf):

- Coverage (R1) ≤ 60 % of the **deed area**, useful plus common areas (2-6, 8-1).
- +2 m length extension if the plot is ≥ 25 m long or ≥ 180 m²; +1 m more on
  the ground floor, unroofed, for parking (2-6).
- Building within the northern 70 % of the plot, advancing from the north (2-8).
- First basement ≤ ground-floor coverage; further basements ≤ 80 %, parking
  only (2-7).
- Parking ≥ 1 per unit; net 2.5 × 5 m (one), 4.5 × 5 m (two), 6.5 × 5 m
  (three); aisle ≥ 3 m; ramp ≤ 15 %; turning radius ≥ 6.5 m (2-10, 12-9 to 12-11).
- No projection below 3.5 m or over streets narrower than 12 m; cantilever
  ≤ 0.80 m on 12–20 m streets, ≤ 1.20 m on wider streets (16-19).
- Corner chamfer (پخ) per Commission minute 362 (values not seen).

## Submission (secondary sources only)

The process starts from the municipality's دستور نقشه (coverage, storeys,
basements, setback lines). Steep or irregular plots, or plots over 3000 m²,
need a 1:2000 survey approved by a qualified engineer. Sheet list, scales and
title-block fields are not verified from a primary source: treat 1:100 for
permit plans and 1:50 for construction as convention, and confirm with the
local engineering organisation (سازمان نظام مهندسی ساختمان).
