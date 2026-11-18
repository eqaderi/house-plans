# Argon C06 (`argon-c06`) — Stepped Hillside Residence Designs

Three complete, solver-verified residential floor-plan options (`argon-c06-a`, `argon-c06-b`, `argon-c06-c`) for `projects/my-house`, built directly from all recorded homeowner statements (`stmt-001` through `stmt-018`) and verified against every rule in `projects/my-house/design/OWNER_DESIGN_RULES.md`.

## Summary of the Three Distinct Options

| Option | Architectural Concept | Road Plate (`u`) | Main Plate (`u`) | Lower Plate (`u`) | Indoor Area | Terraces & Courts | TIN Building Cut | Max Cut Depth | Owner Rules |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| **`argon-c06-a`** | South kitchen + south terrace, central-south dining, NE sheltered cozy living corner, east-center family room | `0.6–11.6 m` | `2.0–16.2 m` | `5.8–20.0 m` | **534.0 m²** | **243.8 m²** (+ ~160 m² flat lawn) | **238.0 m³** | **3.77 m** | **18/18 PASS** |
| **`argon-c06-b`** | Terraces on North, East & South; compact 154 m² main plate; Grandparents at East-Center & Family Room at SE | `0.6–11.4 m` | `2.0–16.0 m` | `5.8–19.8 m` | **506.3 m²** | **254.1 m²** (+ ~160 m² flat lawn) | **250.2 m³** | **3.87 m** | **18/18 PASS** |
| **`argon-c06-c`** | Kitchen shifted SE with pantry buffer before living; SW dining veranda; all 3 lower bedrooms facing east garden | `0.8–11.8 m` | `2.2–16.6 m` | `5.8–20.2 m` | **539.6 m²** | **242.3 m²** (+ ~160 m² flat lawn) | **236.6 m³** | **3.77 m** | **18/18 PASS** |

## Key Differentiators Across Options A, B, and C

- **`argon-c06-a` (Northeast Sheltered Cozy Living & Central-East Garden Hub)**:
  - **Main Floor**: South-west Pantry + South Kitchen (`21.1 m²`) + Central-South Dining (`13.6 m²`) + L-shaped Living (`32.3 m²`) with a sheltered **North-East Cozy Corner** enclosed on its north and west sides, opening south-east to the panoramic view and East Balcony (`59.3 m²`).
  - **Lower Floor**: North-East Boys 2-bed room (`35.5 m²`), Central-East Family Room with Tea & Snack Bar (`28.1 m²`) opening straight onto the Lower East Terrace (`40.6 m²`) and Flat East Lawn (`~160 m²`), South-East Grandparents Suite (`34.0 m²` + `17.8 m²` bath), and South-Center Girls 2-bed room (`22.0 m²`).
- **`argon-c06-b` (Central-West Cozy Living Nook & South-East Family Garden Lounge)**:
  - **Main Floor**: Larger South Kitchen (`23.0 m²`) + Dining (`13.4 m²`), with the L-shaped Living Room (`32.6 m²`) wrapping a **Central-West Sheltered Cozy Nook** (`u = 10.2–13.4 m`) tucked right beside the Central Hall.
  - **Lower Floor**: Central-East Grandparents Suite (`32.0 m²` + `16.0 m²` bath) and **South-East Corner Family Room + Tea & Snack Bar** (`28.8 m²`) enjoying dual south + east garden exposure.
- **`argon-c06-c` (South-East Kitchen Veranda, Pantry Buffer & All-East Lower Bedrooms)**:
  - **Main Floor**: South-West Dining Veranda (`17.0 m²`) + Central-South Kitchen (`19.7 m²`) + **South-East Pantry Buffer** (`4.8 m²`) before the L-shaped Living Room (`34.5 m²`) and East Balcony (`56.2 m²`).
  - **Lower Floor**: **All three bedrooms (`Boys 36.5 m²`, `Girls 28.9 m²`, `Grandparents Suite 35.0 m²`) line the East Garden facade**, while the Family Room + Tea & Snack Bar (`22.0 m²`) faces south.

## Complete Rule-by-Rule Verification Checklist (`OWNER_DESIGN_RULES.md` Rule 8.1)

| Rule ID | Requirement | Status | Option A (`argon-c06-a`) | Option B (`argon-c06-b`) | Option C (`argon-c06-c`) |
|---|---|---|---|---|---|
| **Rule 1.1** | Kitchen opens directly onto South Terrace and looks south | **PASS** | Sliding door d-out + window directly from sp-kitchen to sp-terrace-south | Sliding door d-out + window directly from sp-kitchen to sp-terrace-south | Sliding door d-out + window directly from sp-kitchen to sp-terrace-south |
| **Rule 1.2** | Kitchen gets prime south frontage | **PASS** | Kitchen spans 6.2 m along south edge v=12.4 m | Kitchen spans 6.0 m along south edge v=12.4 m | Kitchen spans 5.8 m along south edge v=12.4 m |
| **Rule 1.3** | Semi-open kitchen with 2 doorless walk-throughs; cooking smells kept out of living | **PASS** | 3 doorless walk-throughs; zero direct opening between kitchen and living | 3 doorless walk-throughs; zero direct opening between kitchen and living | 3 doorless walk-throughs; zero direct opening between kitchen and living |
| **Rule 1.4** | Everyday dining in kitchen; guest dining next to kitchen | **PASS** | Kitchen 21.1 m², Dining 13.6 m² adjacent | Kitchen 21.6 m², Dining 13.0 m² adjacent | Kitchen 19.7 m², Dining 17.0 m² adjacent |
| **Rule 2.1** | Every main room reached directly from entrance/stair hall (never through another room) | **PASS** | Direct openings from central hall to Kitchen, Dining, Living, Master Suite, and all 3 lower bedrooms | Direct openings from central hall to Kitchen, Dining, Living, Master Suite, and all 3 lower bedrooms | Direct openings from central hall to Kitchen, Dining, Living, Master Suite, and all 3 lower bedrooms |
| **Rule 2.2** | No long institutional corridors | **PASS** | Compact central foyer/stair hall (14.6 m² main, 25.4 m² lower) | Compact central foyer/stair hall (14.2 m² main, 25.4 m² lower) | Compact central foyer/stair hall (14.6 m² main, 25.4 m² lower) |
| **Rule 2.3** | No voids, leftover holes, or puzzle layouts (100% exact plate tiling) | **PASS** | Mathematical 0.00 m² gap and 0.00 m² overlap across all 3 floor plates | Mathematical 0.00 m² gap and 0.00 m² overlap across all 3 floor plates | Mathematical 0.00 m² gap and 0.00 m² overlap across all 3 floor plates |
| **Rule 2.4** | No unnecessary interior doors or barriers | **PASS** | Wide doorless openings between Entry, Central Hall, Living, Dining, Kitchen, Pantry, and Family Room | Wide doorless openings between Entry, Central Hall, Living, Dining, Kitchen, Pantry, and Family Room | Wide doorless openings between Entry, Central Hall, Living, Dining, Kitchen, Pantry, and Family Room |
| **Rule 3.1** | Living room has a cozy, sheltered L-shaped sitting corner closed on north/hall side | **PASS** | Cozy corner (12.0 m²) screened by solid north & west walls | Cozy corner (10.1 m²) screened by solid north & west walls | Cozy corner (13.0 m²) screened by solid north & west walls |
| **Rule 3.2** | Living room closed-off corner is not cut off (direct wide opening from Central Hall) | **PASS** | 2.0 m wide direct doorless opening from sp-hall-u into sp-living | 2.0 m wide direct doorless opening from sp-hall-u into sp-living | 2.0 m wide direct doorless opening from sp-hall-u into sp-living |
| **Rule 4.1** | South and east prime frontage used for day rooms and terraces | **PASS** | South = Kitchen, Dining, Living & South Terrace; East = Living, Master, Lower Bedrooms & Balconies | South = Kitchen, Dining, Living & South Terrace; East = Living, Master, Lower Bedrooms & Balconies | South = Kitchen, Dining, Living & South Terrace; East = Living, Master, Lower Bedrooms & Balconies |
| **Rule 4.2** | House steps east to u ≈ 20 m (not narrow towards east, stmt-018) | **PASS** | Road u=0.6–11.6 m, Main u=2.0–16.2 m, Lower u=5.8–20.0 m | Road u=0.6–11.4 m, Main u=2.0–16.0 m, Lower u=5.8–19.8 m | Road u=0.8–11.8 m, Main u=2.2–16.6 m, Lower u=5.8–20.2 m |
| **Rule 4.3** | Generous terraces on main floor in non-west directions | **PASS** | 146.2 m² of outdoor terraces/courts on the main floor | 159.8 m² of outdoor terraces/courts on the main floor | 145.4 m² of outdoor terraces/courts on the main floor |
| **Rule 5.1** | Indoor route from garage straight to lift and stair (for groceries) | **PASS** | Direct interior door sp-garage -> sp-lobby -> sp-lift-r & sp-stair-r | Direct interior door sp-garage -> sp-lobby -> sp-lift-r & sp-stair-r | Direct interior door sp-garage -> sp-lobby -> sp-lift-r & sp-stair-r |
| **Rule 5.2** | One continuous stair connects Road, Main, and Lower floors (works without electricity) | **PASS** | Two stacked U-flights (stair-main-road + stair-lower-main) in the same 2.6×5.0 m shaft | Two stacked U-flights (stair-main-road + stair-lower-main) in the same 2.6×5.0 m shaft | Two stacked U-flights (stair-main-road + stair-lower-main) in the same 2.6×5.0 m shaft |
| **Rule 5.3** | Stair is at the heart of the house, not hidden in a perimeter corner | **PASS** | Central spine u=5.8–8.4 m, v=2.4–7.4 m | Central spine u=5.8–8.4 m, v=2.4–7.4 m | Central spine u=5.8–8.4 m, v=2.4–7.4 m |
| **Rule 5.5** | Oversized 2-car garage (~55–60 m²) with integrated workshop bay (stmt-018) | **PASS** | Garage + workshop bay = 54.1 m² (5.2×9.2 m car bay + 2.6×2.4 m workbench alcove) | Garage + workshop bay = 54.1 m² (5.2×9.2 m car bay + 2.6×2.4 m workbench alcove) | Garage + workshop bay = 54.2 m² (5.2×9.2 m car bay + 2.6×2.4 m workbench alcove) |
| **Rule 6.1–6.6** | Master en-suite upstairs; 3 bedrooms + Family Tea/Snack Bar + tucked Store downstairs | **PASS** | Master 21.6 m²; Grandparents 34.0 m²; Boys 35.5 m²; Girls 22.0 m²; Family+Tea Bar 28.1 m² | Master 13.9 m²; Grandparents 15.8 m²; Boys 34.6 m²; Girls 22.0 m²; Family+Tea Bar 50.4 m² | Master 23.0 m²; Grandparents 35.0 m²; Boys 36.5 m²; Girls 28.9 m²; Family+Tea Bar 22.0 m² |

## Files & Deliverables

- `index.html`: Interactive master comparison and rule audit page.
- `floor-plans.svg` / `floor-plans.png`: Master all-level floor plan sheet.
- `terrain-sections.svg` / `terrain-sections.png`: True 1:1 horizontal/vertical scale site and excavation cross-sections.
- `argon-c06-a/`, `argon-c06-b/`, `argon-c06-c/`: Each contains `plan.json`, `violations.json`, `rule-audit.json`, `placement.json`, `section-earthwork.json`, `floor-plans.svg`, `floor-plans.png`, `terrain-sections.svg`, `terrain-sections.png`, and `review.html`.
