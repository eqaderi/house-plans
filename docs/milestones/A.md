# Milestone A: domain foundation

Date: 2026-10-17. Branch: `milestone-a`.

## What works

- **Repository**: monorepo following the spec's suggested tree, plus
  `domain/` and `storage/` ([ADR 0004](../adr/0004-repository-layout.md)).
  Python package `house_ai`, `house-ai` CLI, CI workflow, lint config.
- **Canonical schemas** (19, Pydantic v2, exported to `schemas/` as JSON
  Schema 2020-12): site with coordinate systems and terrain, CAD import
  provenance, source document, design brief, space program, assumptions,
  open questions, constraint set, code pack, house model (levels, spaces,
  walls, openings, slabs, ceilings, stairs, zones, fixtures, relationships,
  materials, assumptions, issues), plan version, change request, revision
  report, evaluation report, build record, approval, workflow event,
  project manifest, agent roster.
- **Units and frames**: unit conversion including US survey foot, DXF
  `$INSUNITS` mapping (unitless → unknown), CRS/datum confirmation statuses,
  local project frame with rotation and round-trip transforms.
- **Integrity checks** on the canonical model: unique ids, reference
  resolution, polygon validity, no overlap, openings within their wall,
  openings between the spaces they claim (geometric probe), reachability
  from outside, fixtures inside their space, containment in the buildable
  envelope, matching coordinate system.
- **Project storage**: write-once versioned artifacts, immutable source
  files, hash-chained append-only event log, tamper detection
  (`project verify`), YAML/JSON-independent content hashes.
- **Workflow state machine**: the 15 spec states, transition table and
  guards, four human-only approval gates that re-run their checks on the
  pinned artifact version, `SITE_NEEDS_VERIFICATION` on ambiguous units,
  CRS or datum, reopen with downstream supersession, state replayed from
  the log.
- **Safety boundary**: compliance labels that cannot claim a code check
  without a human-verified code pack, a linter for prohibited professional
  claims, a provider data-flow policy that refuses private data without
  explicit human consent.
- **Agent entry points**: `docs/AGENT_CONTRACT.md` plus small `AGENTS.md`,
  `CLAUDE.md`, `GEMINI.md`; `agents/roles.yaml` with the 12 spec roles.
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

`211 passed` (Python 3.13.3, macOS), 0 failed, 0 skipped.

| File | Tests |
|---|---|
| `test_schemas.py` | 31 |
| `test_units_coordinates.py` | 35 |
| `test_geometry.py` | 10 |
| `test_integrity.py` | 21 |
| `test_domain_rules.py` | 33 |
| `test_storage.py` | 22 |
| `test_workflow.py` | 37 |
| `test_cli.py` | 14 |
| `test_providers_agents.py` | 7 |
| `test_golden.py` | 1 |

Python 3.11 is declared as supported and is in the CI matrix. The tests
were not run on 3.11 locally; `pip download --python-version 3.11` confirmed
that binary wheels of the pinned pydantic, shapely and PyYAML exist for
macOS arm64 and manylinux x86_64.

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
  calculation, door-swing clearance or furniture check yet.
- `RevisionReport` exists as a schema; computing it from two plan versions
  is Milestone D work.
- The store uses POSIX `flock` and hard links; Windows is not supported.
- A crash between writing an artifact file and appending its event leaves
  an unregistered version file. The next write skips past it and
  `project verify` reports it, but nothing cleans it up automatically.
- The program gate checks the brief the program cites, or every stored
  brief if it cites none. Program items' `source_fact_ids` are not yet
  resolved against the brief.
- Git history before commit `bf50e60` (the previous house-plans toolchain)
  contains survey-derived files (`derived/survey/*.dxf`,
  `derived/site/d7.yaml`). The new `.gitignore` does not remove them from
  history; whether to rewrite history is the owner's decision.
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
