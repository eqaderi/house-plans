# Agent Browser Inspection Setup

This document establishes the browser automation and visual review setup for coding agents (Claude Code, Gemini CLI, Antigravity, and Codex) in accordance with Stage S5 (Task S5-01).

## 1. Principles & Architectural Guardrails

1. **Local-first and offline-only**:
   - In adherence to AGENT_CONTRACT §8 and §1, browser automation runs strictly against loopback addresses (`127.0.0.1` or `localhost`).
   - Network routing in browser contexts automatically intercepts and aborts any outbound non-loopback request with `internetdisconnected`. No external CDNs, fonts, or analytics are contacted.

2. **Deterministic captures**:
   - Standard capture viewport is **1280 × 800** with a device scale factor of 1.
   - Screen captures wait for `document.fonts.ready` and UI element readiness before taking a screenshot.
   - Every captured screenshot produces a SHA-256 cryptographic digest to guarantee repeatable visual verification.

3. **Grounded element identity**:
   - All rendered SVG elements carry `data-id="<canonical-id>"` and `data-kind="<kind>"`.
   - Agents inspecting plans via DOM snapshot, accessibility tree, or rendered imagery must cite verified canonical IDs (e.g. `sp-living`, `w-ext-1`, `d-entry`). Ungrounded critiques are rejected.

---

## 2. Available Inspection Tools

### A. Reviewer Capture CLI (`apps/reviewer/scripts/capture.js`)

A self-contained Node/Playwright utility that spins up an ephemeral loopback server, loads the specified bundle JSON, waits for SVG render, and saves a deterministic PNG screenshot with SHA-256 hash.

```bash
# Capture plan view of a bundle
export PATH="/opt/homebrew/bin:$PATH"
node apps/reviewer/scripts/capture.js \
  --bundle apps/reviewer/public/bundles/synthetic-bungalow/bundle.json \
  --out /tmp/bungalow.png \
  --json

# Capture a specific tab (e.g. comparison, metrics, findings, section)
node apps/reviewer/scripts/capture.js \
  --bundle apps/reviewer/public/bundles/synthetic-hillside/bundle.json \
  --out /tmp/hillside_metrics.png \
  --tab metrics \
  --json
```

**JSON Output:**
```json
{
  "path": "/tmp/bungalow.png",
  "sha256": "d554d07d5913c16e2a1b60fd4e153d97473cbe9d26f1daa40c81d6aef7a1e89c",
  "size_bytes": 75752,
  "viewport": { "width": 1280, "height": 800 },
  "url": "http://127.0.0.1:65410/?bundle=/api/current-bundle.json",
  "bundle": ".../bundle.json",
  "tab": "plan",
  "timestamp": "2026-10-18T02:32:02.234Z"
}
```

### B. Python CLI Wrapper (`house-ai reviewer capture`)

For agents executing Python workflow commands:

```bash
.venv/bin/house-ai reviewer capture my-project --out /tmp/plan.png
.venv/bin/house-ai reviewer capture --bundle path/to/bundle.json --out /tmp/plan.png --tab section
```

### C. Static SVG Rasterisation (`house-ai plan render-png`)

For rapid headless rasterization without browser overhead (using `rsvg-convert` or `inkscape` per S5-04):

```bash
.venv/bin/house-ai plan render-png my-project concept-compact --out /tmp/compact.png
```

### D. Playwright E2E Suite (`apps/reviewer/e2e/reviewer.spec.ts`)

Full interactive verification across tabs, overlays, feedback builders, and approval gate boundaries:

```bash
export PATH="/opt/homebrew/bin:$PATH"
cd apps/reviewer && pnpm test:e2e
```
