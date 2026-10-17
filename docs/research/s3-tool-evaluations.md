# S3 — Tool and library evaluations

Evaluation date: 2026-10-17. All experiments use synthetic inputs and isolated,
disposable environments. No private project data, ProjectStore writes, gate
approvals, or project environment dependencies occur.

---

## 1. S3-01: Playwright CLI, MCP, and Test (TOOL-PLAYWRIGHT)

### Identity and sources
- **Packages evaluated:**
  - `@playwright/cli` 0.1.22
  - `@playwright/test` 1.64.1
  - `@playwright/mcp` 0.0.83
  - Chromium headless / shell 1247 / 1248
- **Upstream URLs:**
  - https://github.com/microsoft/playwright
  - https://playwright.dev/agent-cli/skills
  - https://github.com/microsoft/playwright-cli
  - https://github.com/microsoft/playwright-mcp
- **Licence:** Apache-2.0 across all packages.
- **Environment:** macOS Darwin arm64, Node v26.12.0, npm 11.20.0. Isolated in `/private/tmp/house-s3-tools.VtGIeQ/npm`.

### Network policy and offline operation
Browser context routing intercepts all requests:
- Loopback `127.0.0.1` traffic is allowed to serve the local reviewer static assets.
- All non-loopback URLs are aborted with `internetdisconnected`.
- A probe to `https://example.invalid/probe` was confirmed blocked (`externalFetchSucceeded: false`).
- Offline operation is complete once browser binaries are provisioned.

### Recorded experiment
A synthetic plan reviewer page (`examples/tool-evaluations/playwright/local-reviewer.html`)
was inspected across three routes:
1. **Playwright CLI:**
   - Navigated to the local reviewer URL.
   - Clicked `#measure`.
   - Evaluated DOM expression; returned `"Total: 60 m²"`.
   - Captured viewport screenshot to `examples/tool-evaluations/playwright/results/cli.png`.
   - Log recorded in `examples/tool-evaluations/playwright/results/cli.txt`.
2. **Playwright MCP:**
   - Exercised via newline-delimited JSON-RPC over stdio (25 tools exposed).
   - Executed `browser_navigate`, `browser_run_code_unsafe`, `browser_click`, `browser_snapshot`, `browser_take_screenshot`.
   - Returned `"Total: 60 m²"` and saved screenshot to `examples/tool-evaluations/playwright/results/mcp.png`.
   - Details recorded in `examples/tool-evaluations/playwright/results/mcp.json`.
3. **Playwright Test:**
   - Test script `examples/tool-evaluations/playwright/reviewer.spec.cjs` executed via `@playwright/test/cli.js`.
   - Validated DOM text, outside network block count (`blocked === 1`), and screenshot generation (`test.png`).
   - Result: 1 passed (0 failures). Log in `test.txt`.

### Decision
- **ADOPT `@playwright/test`** for headless browser regression testing in S4 when scaffolding `apps/reviewer`.
- **ADAPT `@playwright/cli`** pattern for agent browser inspection workflows (simpler process lifecycle than MCP server).
- **DEFER `@playwright/mcp`** (unnecessary complexity for standard inspection tasks).
- No dependency added to the repository in S3.

---

## 2. S3-02: Trimesh (TOOL-TRIMESH)

### Identity and sources
- **Package:** `trimesh` 5.1.1.
- **Upstream URL:** https://github.com/mikedh/trimesh
- **Licence:** MIT.
- **Wheels verified:** `trimesh-5.1.1-py3-none-any.whl` (universal), dependencies `numpy` 2.4.2, `scipy` 1.17.1, `networkx` 3.6.1.
- **Environments:** Python 3.11.12 and Python 3.13.3 on Darwin arm64.

### Recorded experiment
Evaluated on four analytical, synthetic closed 10 × 6 m solids closed to z=0:
1. `planar_slope` ($z = 2 + x/5$): Volume 180 m³, cut above $z=3$ is 15 m³, void below $z=3$ is 15 m³, horizontal section at $z=3$ is 30 m².
2. `wedge` ($z = 1 + 2x/5$): Volume 180 m³, cut 30 m³, void 30 m³, section 30 m².
3. `pyramid` ($z = 1$ rising 4 m to apex at (5,3,5)): Volume 140 m³, cut 10 m³, void 50 m³, section 15 m².
4. `stepped_pad` ($z=2$ for $x<5$, $z=4$ for $x\ge 5$): Volume 180 m³, cut 30 m³, void 30 m³, section 30 m².

All measured quantities agreed with closed-form analytical formulas within absolute tolerance $10^{-7}$ m³/m² under both Python 3.11 and 3.13.

### Limitations
- Computing horizontal sections as closed 2D polygons requires `scipy` and `networkx`. A bare minimal install without them raises `ImportError`.
- Trimesh's default boolean engine delegates to `manifold3d`.

### Decision
- **ADAPT in S8** for surface mesh loading, section slicing, and mass property queries.

---

## 3. S3-03: Manifold / manifold3d (TOOL-MANIFOLD)

### Identity and sources
- **Package:** `manifold3d` 3.5.4.
- **Upstream URL:** https://github.com/elalish/manifold
- **Licence:** Apache-2.0.
- **Wheels verified:** `manifold3d-3.5.4-cp311-cp311-macosx_11_0_arm64.whl` and `manifold3d-3.5.4-cp313-cp313-macosx_11_0_arm64.whl`.
- **Environments:** Python 3.11.12 and Python 3.13.3 on Darwin arm64.

### Recorded experiment
Evaluated on the same four analytical solids, plus edge-case boundary conditions:
- **Direct volume & slicing:** direct `manifold.volume()` and `manifold.slice(3).area()` matched analytical ground truth to $10^{-7}$.
- **Coplanar contact:** Two touching $1\times 1\times 1$ m cubes ($x\in [0,1]$ and $x\in [1,2]$) produced exactly 0.0 m³ boolean intersection volume without degenerate face explosion.
- **Disjoint intersection:** Separated cubes returned `is_empty() == True`.
- **Invalid geometry rejection:** An open TIN without a closing boundary was detected and returned `Error.NotManifold`.

### Decision
- **ADOPT in S8** as the core 3D boolean kernel for earthwork cut/fill, retaining wall cuts, and terrain volume calculations.

---

## 4. S3-04: ArchLang (TOOL-ARCHLANG)

Detailed research and defect injection results are recorded in [`docs/research/s3-archlang.md`](s3-archlang.md).
- **Package:** `@chanmeng666/archlang` 1.43.1, MIT.
- **Decision: ADAPT** diagnostic rules (window existence in habitable rooms, doorway approach clearances, swing collisions, path widths) into canonical S6 critics. Do not adopt as a language or add as a runtime dependency.

---

## 5. S3-05: Anatomy (TOOL-ANATOMY)

- **Source:** [wheresryan22/anatomy](https://github.com/wheresryan22/anatomy) pinned at commit `e9488296a44211c42701ff71705b7901470ec78f`, MIT.
- **Study:** Built dial-indicator example (`examples/tool-evaluations/anatomy/study.py`), producing 342 SVG paths.
- **Patterns identified:**
  1. Clean separation between geometric kit and runtime/motion layer.
  2. Single SKILL.md structure with dedicated reference guides (`references/motion.md`, `references/verify.md`) and executable scripts.
  3. Live readouts coupled to geometry state.
  4. Explicit multi-viewport screenshot verification habits.
- **Decision: ADAPT** packaging and verification patterns in S4 (reviewer) and S5 (2D floor plan rendering). Do not install or treat as an architectural model.

---

## 6. S3-06: Candidate intake process (TOOL-OTHER)

- Standard template created at [`examples/tool-evaluations/intake-template.md`](../../examples/tool-evaluations/intake-template.md).
- Requires all new candidates to be documented across 17 structured fields (URL, pin, licence, arm64 wheels, offline capability, security, proof-of-value, etc.) before any installation.
- **Decision: ADOPT** as mandatory intake gate.
