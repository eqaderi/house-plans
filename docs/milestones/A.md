# Milestone A: domain foundation

Date: 2026-10-17. Branch: `milestone-a`.

## What works

- **Repository**: monorepo following the spec's suggested tree, plus
  `domain/` and `storage/` ([ADR 0004](../adr/0004-repository-layout.md)).
  Python package `house_ai`, `house-ai` CLI, CI workflow, lint config.
- **Canonical schemas** (20, Pydantic v2, exported to `schemas/` as JSON
  Schema 2020-12): site with coordinate systems and terrain, CAD import
  provenance, source document, design brief, space program, assumptions,
  open questions, constraint set, code pack, house model (levels, spaces,
  walls with per-face material overrides, openings with swing side, slabs,
  ceilings, stairs, zones, fixtures with oriented footprints, relationships,
  materials with PBR/scale metadata, assumptions, issues), plan version,
  change request, revision report, evaluation report, build record, scene
  manifest, approval, workflow event, project manifest, agent roster.
- **Units and frames**: unit conversion including US survey foot, DXF
  `$INSUNITS` mapping (unitless → unknown), CRS/datum confirmation statuses,
  local project frame with rotation and round-trip transforms.
- **Integrity checks** on the canonical model: unique ids, reference
  resolution (including cross-checking program items, adjacency requirements,
  issue subjects and assumption targets), polygon validity, no space overlap,
  no unattached walls, openings within their wall, no overlapping openings on
  a wall, openings between the spaces they claim across their full span,
  reachability from outside, oriented fixture footprints inside their space
  and non-overlapping, stair level and footprint consistency, containment in
  the buildable envelope, matching coordinate system, and program minimum
  area / hard connected adjacency checks.
- **Project storage**: write-once versioned artifacts, immutable source
  files with stem-collision disambiguation, hash-chained append-only event
  log, tamper detection (`project verify`) covering both artifacts and
  sources, YAML/JSON-independent content hashes.
- **Workflow state machine**: the 15 spec states, transition table and
  guards, four human-only approval gates (and human-only `reopen`) that
  re-run their checks on the pinned artifact version,
  `SITE_NEEDS_VERIFICATION` on ambiguous units, CRS or datum, reopen with
  downstream supersession, state replayed from the log.
- **Safety boundary**: compliance labels that cannot claim a code check
  without a human-verified code pack, a linter for prohibited professional
  claims, a provider data-flow policy that refuses private prompts and
  attachments without explicit human consent.
- **Agent entry points**: `docs/AGENT_CONTRACT.md` is the one shared rule
  set for the coding agents; `AGENTS.md` (Codex), `CLAUDE.md` and
  `GEMINI.md` only load it ([ADR 0005](../adr/0005-shared-coding-agent-instructions.md)).
  `agents/roles.yaml` holds the 12 runtime roles of the product, which are
  a separate concept.
- **Golden synthetic project**: `examples/projects/synthetic-bungalow/`,
  with `build_plan.py` regenerating the golden plan and a test that it is
  current.

## Commands

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests examples
.venv/bin/house-ai schemas check

# demonstration
.venv/bin/house-ai example load project-data/demo --actor agent:cli
.venv/bin/house-ai project status project-data/demo
.venv/bin/house-ai artifact check project-data/demo plan-a
.venv/bin/house-ai project verify project-data/demo
.venv/bin/house-ai workflow approve project-data/demo site --id site --approver <name>   # interactive
```

## Test results

`240 passed` (Python 3.13.3, macOS), 0 failed, 0 skipped.

| File | Tests |
|---|---|
| `test_schemas.py` | 32 |
| `test_units_coordinates.py` | 37 |
| `test_geometry.py` | 12 |
| `test_integrity.py` | 28 |
| `test_domain_rules.py` | 34 |
| `test_storage.py` | 24 |
| `test_workflow.py` | 40 |
| `test_cli.py` | 14 |
| `test_providers_agents.py` | 10 |
| `test_agent_instructions.py` | 8 |
| `test_golden.py` | 1 |

Python 3.11 is declared as supported and is in the CI matrix. The CI
install (`pip install -e '.[dev]'`, which resolves the version ranges, not
the lock) was reproduced in fresh Homebrew Python 3.11 and 3.13 venvs: ruff
clean, 20 schemas up to date, all tests passed on both. The exact lock in
`requirements-lock.txt` is for Python 3.12+ (numpy 2.5.4 has no cp311
wheel).

## Handoff review (Claude Code, 2026-10-17)

Gemini's review commit `2e62d87` was re-verified rather than trusted: the
diff was read file by file against MASTER_SPEC and the architecture, and
the reported 231 tests, ruff and 20 schemas reproduced. No Milestone A test
or guard was removed. Two confirmed defects were fixed, each with a test
that failed first:

- `providers/base.py`: an unlabelled prompt was treated as synthetic
  whenever a synthetic attachment was present, so private prompt text could
  reach a provider. An unlabelled prompt is now always private.
- `tests/test_providers_agents.py`: the "no survey files" test scanned the
  whole working tree, so it failed as soon as a real survey was placed in
  the git-ignored `project-data/`. It now checks tracked files only.

Noted, not changed: `pyproject.toml` now uses version ranges, so CI does
not pin pydantic; a future pydantic release can change the generated
schemas and fail `schemas check` until they are re-exported.

## Known limitations

- No CAD import, interview, solver, evaluators, SVG, IFC, Blender or Unreal
  yet. Their packages hold boundaries only.
- Approval gating stops accidental or silent skipping. It is not a security
  boundary: a local process can call the library or rewrite the whole event
  log consistently. The log is tamper-evident, not tamper-proof.
- Site gate checks are only as good as the data: no CRS library (pyproj) is
  used yet, so EPSG codes are not validated against a registry and true
  north is left unknown.
- Integrity checks use centerline polygons; there is no net-area
  calculation or door-swing clearance check yet.
- `RevisionReport` exists as a schema; computing it from two plan versions
  is Milestone D work.
- The store uses POSIX `flock` and hard links; Windows is not supported.
- A crash between writing an artifact file and appending its event leaves
  an unregistered version file. The next write skips past it and
  `project verify` reports it, but nothing cleans it up automatically.
- Git history before commit `bf50e60` (the previous house-plans toolchain)
  contains survey-derived files (`derived/survey/*.dxf`,
  `derived/site/d7.yaml`). The new `.gitignore` blocks raw `.dwg`/`.dxf` and
  legacy folders from being committed again, and a test checks that no
  survey files are tracked by git (private files in `project-data/` are
  allowed); whether to rewrite shared remote history is the owner's
  decision.
- Reads replay the whole event log; fine for expected project sizes.
- Artifacts can be written in any workflow state; the gates, not write
  permissions, control what counts as approved.

## Next: Milestone B (site)

- A synthetic DXF survey fixture (boundary, contours, spot heights, a road,
  a tree, unknown layers, a declared `$INSUNITS`) generated by a script.
- `cad/dxf_ezdxf.py` implementing `CadAdapter.inspect_cad` and
  `extract_cad`, with layer classification driven by a mapping file, and a
  GDAL/OGR DWG adapter that is skipped cleanly when GDAL is absent.
- Filling `CadImportProvenance` for every import and writing a `site`
  artifact that stops at `SITE_NEEDS_VERIFICATION` until a human confirms
  units, EPSG and vertical datum through a new CLI command.
- `set_coordinate_reference_system` and `create_local_coordinate_system`
  with pyproj (EPSG validation, meridian convergence for true north),
  `build_terrain` (TIN from spot heights and contours), and a site SVG.
- New dependencies: ezdxf, pyproj, possibly scipy or a small TIN routine.
