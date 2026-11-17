# ADR 0018: Desktop and web 2D plan reviewer architecture

Status: accepted (Stage S4, closed 2026-10-18)

## Context

MASTER_SPEC §"2D REVIEWER" and Milestone E require a minimal, local-first web reviewer
for plan options. It must support synchronized parcel/site, terrain,
floor plan, room labels, dimensions, room areas, north, circulation paths,
constraints/issues, and version comparison.

AGENT_CONTRACT §1, §3, and §8 impose strict constraints:
1. The canonical semantic model (`house_ai.domain`) is the only source of truth;
   every element drawn on screen must map to a canonical element ID.
2. The project store is write-once, hash-chained, and immutable; the reviewer must be
   strictly read-only with respect to project storage.
3. Approval gates require a human in an interactive terminal (`workflow approve`,
   `site confirm`); the reviewer cannot approve gates and must only show the CLI
   command a human runs.
4. Privacy and offline operation: no external telemetry, CDNs, or vendor SDKs;
   private project data must never leak to third-party servers.

## Decision

### 1. Technology stack
- **Framework & language:** React 19 + TypeScript in strict mode (`"strict": true`).
- **Bundler & dev tooling:** Vite for fast local development, static single-page
  application (SPA) production build, and reproducible offline assets.
- **Testing:** Vitest for component and unit testing; Playwright Test (`@playwright/test`,
  adopted in S3-01) for headless browser integration and regression tests.
- **Directory:** `apps/reviewer/`.

### 2. Geometry computation: browser rendering from canonical model
- The reviewer computes SVG vector geometry directly in the browser from canonical
  `HouseModel` and `PlanVersion` data.
- Spaces are rendered as SVG `<polygon>` elements with room labels, dimensions, and area
  callouts calculated from canonical coordinates.
- Walls, doors (with swing arcs), windows (with frame marks), stairs (with treads and
  rise arrows), and slabs are rendered from model entities.
- Every drawable SVG element carries `data-id="<canonical-id>"` and `data-kind="<kind>"`.
  Element IDs are preserved and inspectable by people and agents
  (Milestone E, Stage S5).
- Pre-rendered plan SVGs produced by the Python pipeline (`render2d/plan_svg.py`) are also
  supported as a visual reference toggle.

### 3. No D3
- Declarative React and standard SVG DOM are used for all geometry, overlays, schedules,
  zoom/pan and comparisons. The reviewer has no D3 dependency: the allowance first
  written here for `d3-zoom` and colour scales was not needed in S4.
- A D3 utility added later must never mutate or replace React-managed SVG DOM nodes,
  so element identity stays stable.

### 4. Data delivery and packaging
- **Static bundle export:** A CLI command (`house-ai reviewer export <project> --out <dir>`)
  reads the project store read-only and writes a validated self-contained bundle JSON
  containing:
  - Project manifest metadata and workflow status;
  - Canonical `Site` model (and terrain TIN if available);
  - Canonical `SpaceProgram` and `DesignBrief`;
  - All plan versions (`PlanVersion`), canonical `HouseModel`s, `EvaluationReport`s,
    and `RevisionReport`s;
  - Stamped exploratory plans (when exported from `--exploratory` runs).
- **Delivery modes:**
  1. File picker / drag-and-drop: The owner or an agent can drop a bundle JSON file into
     the reviewer without running any backend server.
  2. Local read-only server: `house-ai reviewer serve <project>` or `pnpm preview`
     serves the static SPA and bundled project data over loopback (`localhost`).
- **Offline operation:** The application bundle contains all JS, CSS, and SVG assets.
  No external network requests, fonts, CDNs, or third-party analytics are made.

### 5. Epistemic status display
- In accordance with AGENT_CONTRACT §6, every metric displayed in the reviewer
  (from `EvaluationReport`) is rendered with an explicit epistemic status badge:
  `measured`, `inferred`, `simulated`, `ai_judgment`, or `not_checked`.
- The measurement method is displayed alongside the value.
- North arrow is rendered only when a human confirmed the horizontal CRS
  (`site.coordinates.horizontal_crs.status` is `user_confirmed` or `local_only_confirmed`).
  When unconfirmed or unknown, the reviewer displays an "Orientation unconfirmed / North unknown" badge.
- The terrain section profile is explicitly labelled as `schematic` until Stage S8.

### 6. Version comparison and feedback capture
- **Comparison:** Plan versions can be inspected side by side with synchronized zoom and levels.
  Individual evaluation metrics are compared in a side-by-side matrix without aggregate
  scores. Version diffing highlights added/removed spaces, dimensional changes, and
  new vs resolved violations.
- **Feedback & revision ops:**
  - The reviewer allows the owner to attach comments to specific canonical element IDs.
  - A revision builder UI lets the owner construct structured revision operations
    (`--area`, `--separate`, `--level`, etc.).
  - Comments and revision operations export to a JSON file validated against
    `revision_ops.schema.json`.
  - The Python CLI imports this file via `house-ai plan revise-from-file <project> <option> <file> --actor agent:<tool>`
    to execute the requested revision deterministically.
- **Approval boundaries:**
  - The reviewer displays human gate status (Site, Program, Plan, Model).
  - It contains **no approve button**, **no mutation endpoints**, and **no direct write**
    to `ProjectStore`.
  - For unapproved gates, it displays the exact CLI command the Approver must copy
    and execute in their interactive terminal.

## Consequences

- The reviewer provides a fast, offline, interactive visual inspection tool for
  the owner and agents without compromising store integrity or security.
- Element IDs are stable, enabling automated visual review and grounded critiques in Stage S5.
- Strict TypeScript types generated from `schemas/*.schema.json` ensure zero drift
  between the Python domain models and the TypeScript frontend.
- Adding `apps/reviewer/` introduces Node/pnpm tooling to the repository, but the
  core Python pipeline continues to function independently without requiring Node.
