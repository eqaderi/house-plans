# Concept Reviewer (`apps/reviewer`)

Desktop and browser-based concept reviewer application for inspecting canonical house models, floor plans, site overlays, terrain sections, evaluation metrics, and version comparisons.

The application is implemented in React 19, TypeScript, and Vite. It consumes self-contained JSON bundles exported by `house-ai reviewer export` and `house-ai reviewer serve`, validates them client-side against the schemas in `schemas/`, and renders interactive SVG canvases driven directly by canonical model coordinates.

## Architecture

- **Framework**: React 19, TypeScript, Vite.
- **Client-side Validation**: Pure client-side bundle loader (`src/lib/loader.ts`) validating against JSON schemas generated from Pydantic domain models.
- **Rendering**: Semantic SVG canvas (`src/components/PlanCanvas.tsx`) with stable `data-id` and `data-kind` attributes, pan, zoom, auto-fit to room extents, and true north orientation with CRS confirmation gating.
- **Comparison**: Side-by-side split-view (`src/components/ComparisonView.tsx`) allowing comparison of two plan versions or options with synchronized viewport framing.
- **Revisions**: Structured revision operations builder exporting reproducible CLI commands (`house-ai plan revise`).

## Key Features

- **Floor & Level Switching**: Navigate between building storeys with automatic viewport fitting on initial load and level change.
- **Element Inspection**: Click to select spaces, walls, openings, stairs, and fixtures, with canonical properties displayed in the `PropertyPanel`.
- **Site & Terrain Overlays**: Display parcel boundaries, buildable envelopes, and terrain contours. North arrow is gated on a confirmed coordinate reference system (CRS).
- **Dimension Lines & Room Schedules**: Exact dimensions computed from model geometry alongside gross and net floor area schedules.
- **Epistemic Labeling**: Analysis overlays and the `MetricMatrix` label every metric with its epistemic status (`measured`, `inferred`, `simulated`, `ai_judgment`, `not_checked`) and method.
- **Issue & Finding Highlighting**: Hard and soft findings linked directly to subject element IDs for grounded visual review.

## CLI Integration

Serve a project in the reviewer directly from the CLI:

```bash
house-ai reviewer serve <project_path> --port 5173
```

This exports a self-contained read-only bundle and launches a local HTTP server pointing to `index.html?bundle=bundle.json`. When `dist/index.html` is not yet built, the command informs the user with instructions to build the app.

To export a bundle without serving:

```bash
house-ai reviewer export <project_path> --out bundle.json
```

## Development & Testing

From `apps/reviewer`:

```bash
# Start Vite development server
pnpm dev

# Typecheck and compile production build to dist/
pnpm build

# Run Vitest unit and component tests
pnpm test

# Run Playwright E2E browser tests
pnpm test:e2e

# Run TypeScript typechecker only
pnpm typecheck
```

See [docs/PROJECT_TRACKER.md](../../docs/PROJECT_TRACKER.md) Stage S4 and Stage S10 for development history and acceptance criteria.
