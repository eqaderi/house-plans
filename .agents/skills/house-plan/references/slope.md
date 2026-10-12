# Building on a slope

The site is sloped, in the mountains, at about 1678 m and 35.7° N, in a
very-high seismic zone. These are design principles with their sources.
**[U]** = weak or unverified source; **[J]** = judgement without a source.
Numbers here are guidance unless they also appear in `rules/`; the
geotechnical and structural engineers have the final word.

Equivalents: 15° ≈ 27 %, 1:3 = 33 % (18.4°), 30° ≈ 58 %.

## 1. Read the slope first

- **Slope bands** (blockrenovation.com, [U]): under 10 % build roughly as on
  the flat; 10–20 % stepped footings or split section; over 20 % costs rise
  fast; over 30° deep foundations, retaining walls and subsoil drains.
- **Long axis along the contours.** A 8.5 × 18 m house with its long side
  down a 15 % slope has about 2.7 m of drop corner to corner; turned along
  the contours, about 1.2 m.
- **Don't put a flat-lot plan on a hillside.** Step the house with the
  ground; put most of the cut under the building and the retaining walls
  under the house (Santa Barbara Hillside Design Guidelines).
- **Walk-out lower level** suits about 15–20 % (≈ 2.1 m drop across the
  footprint) (buildingadvisor.com, [U]). Masuleh and Abyaneh take this to the
  limit: the roof of the house below is the yard of the house above.
- **Get the soil report before designing.** Skipping it is the first
  hillside mistake on every list.

## 2. Earthwork limits (good-practice guidance)

| Item | Guidance | Source |
|---|---|---|
| Cut depth for the house | ≤ 2.4 m | Los Altos Hills grading policy |
| Fill depth | ≤ 0.9 m; prefer cut to fill; fill compacted | Los Altos Hills, GBA |
| Grading on slopes over 30 % | avoid | Santa Barbara |
| Each exposed retaining wall | ≤ 1.8 m; all faces together ≤ 3.7 m; gap between terraced walls ≥ their average height | Santa Barbara |
| Retaining walls needing an engineer | over about 1.2 m | blockrenovation.com [U] |
| Setback from slopes steeper than 1:3 | footing H/3 from a descending face (≤ 12 m); H/2 from an ascending toe (≤ 4.6 m) | IRC R403.1.7 |
| Footings on 10–33 % | stepped, every footing level top and bottom | IRC via Shasta County |
| Slope stability | factor of safety ≥ 1.5 static, ≥ 1.0 seismic | Agoura Hills |
| Apparent height (lowest ground contact to highest point) | ≤ 9 m (≤ 7.6 m on slopes under 25 %) | Santa Barbara |

Iranian rules for excavation (Mabhas 12) and foundations (Mabhas 7) override
these: see `iran.md`.

## 3. Seismic: where hillside habits clash with Standard 2800

- **Split levels.** Hillside guides like them; Standard 2800 says to avoid
  floor levels split within a storey and short columns, "especially in
  basement openings" (3rd ed. §1-4-7, §1-5-7). Reconcile them [J]: step the
  house in **full storeys** with continuous floor diaphragms, or cut it into
  separate blocks, one per level, divided by **seismic joints**. Never a
  half-level split inside one structural block.
- **Short columns and stiff uphill walls.** Uphill short columns take almost
  all the storey shear; a stiff uphill wall against tall downhill posts twists
  the house. Use RC walls on the downhill side or the corners (Goswami; RUDN
  2022; BRANZ).
- **Foundations level** (2800 §1-3-5): every part of the foundation on a
  horizontal level; cut or fill on a slope needs a slope-stability analysis
  (§1-3-4).
- **Base level** (§2-3-2): a basement buried on the uphill side only usually
  does not count as below the base; heights and joints are measured from the
  foundation top.
- **Seismic joint** ≥ 1/100 of the height above the base (3rd ed. §1-6-3; the
  5th edition text may differ — `iran.md`).
- **Cantilevers** ≤ 1.5 m (§1-4-3); centre of mass to centre of stiffness
  within 5 % of the plan dimension per floor (§1-5-3).
- **Unreinforced masonry only** (ch. 3): length ≤ 3 × width; foundation
  slope over 15 % to be avoided; floor steps over 0.6 m within a storey need
  tie beams or a joint; roof ≤ 8 m above average ground.
- **Design base acceleration** A = 0.35 for very high hazard, 0.30 high —
  looked up by locality (Tehran and Damavand: very high).
- **Topographic amplification** (Eurocode 8-5 Annex A): ×1.2 on slopes over
  15°, ×1.4 on ridges over 30°, near the crest of high slopes [U on the height
  limit].

## 4. Water: the hillside's real enemy

- Ground falls ≥ 5 % for 3 m away from the walls; paving ≥ 2 % (IRC R401.3,
  IBC 1804.4).
- An interceptor swale on the uphill side catches runoff before it reaches the
  house.
- Behind every retaining wall: a perforated subsoil drain in a granular
  trench wrapped in geotextile (Wellington CC). Under-sized drains are a top
  regret.
- Habitable rooms against earth: BS 8102 Grade 3 (no water penetration) —
  combine two systems, one a drained cavity.
- Roof water piped to a proper outfall, never soaking in near footings.
- Independent retaining walls are easier to keep dry than walls that are part
  of the house.

## 5. Sun, snow, cold at 35.7° N

- Noon sun altitude: 30.9° at the winter solstice, 54.3° at the equinoxes,
  77.7° at the summer solstice (computed).
- Main glazing within 25–35° of south [U].
- Overhang projection P ≈ 0.22 H shades the glass at summer-solstice noon
  (H = sill to overhang underside); for late-summer heat design to the
  equinox, P ≈ 0.72 H; keep a head gap ≥ 0.6 P for winter sun (JLC method).
- On a **north-facing** slope winter sun is scarce: check the southern horizon
  angle at each main window against 30.9°.
- Snow (Mabhas 6 ground snow zone is a required input): every roof step drops
  or drifts snow onto the roof, entry or drive below it — keep entries and the
  drive out from under roof edges [J].

## 6. Access

- Driveway ≤ 8 % where it meets the road (NCHRP 659); grade changes without a
  vertical curve ≤ 10 % at a crest, ≤ 9 % at a sag; transitions of 1:8 over
  ≥ 1 m (Queensland) or 2 m where the change exceeds 12.5–15 % (AS 2890.1).
- With snow and ice at this altitude aim for ≤ 12 % overall [J]. Tehran's
  detailed plan allows private ramps up to 15 % (`iran.md`).
- Uphill or downhill street access decides where the garage and the entrance
  level go — decide it in the site phase.

## 7. Checks to compute once the terrain is in (not built yet)

From a terrain model (survey DXF → TIN) and the spec: slope and aspect under
the footprint; long-axis angle to the contours; drop across the footprint;
cut and fill depths and volumes; retaining heights and terrace spacing;
setbacks from slope faces; footing levels stepped and level; floor levels
against the terrain; split levels inside one block; base level, height above
base and joint width; cantilever length; driveway grades and transitions;
ground falling away from the walls; southern horizon angle at the glazing;
overhang projection; apparent height. These become `bin/hp site` checks when
the survey arrives.
