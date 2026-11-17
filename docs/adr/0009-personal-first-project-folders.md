# ADR 0009: Personal-first project folders; the owner's project is committed

Status: accepted (2026-10-17, owner's decision)

## Context

The owner decided that the software is personal-first: its first purpose is
to design the owner's own house on their own parcel. Reuse for other houses is
a secondary requirement. They want their real project to be a permanent part
of the repository, not disposable test data, and they authorised committing
and pushing their survey DWG files, project configuration, site drawings and
review documents to the GitHub repository while it is private.

Until now the project store lived in the git-ignored `project-data/my-house`
next to loose folders (`project-data/surveys/`, `project-data/my-house-review/`,
`project-data/my-house-layers.yaml`). MASTER_SPEC (Data / privacy) says owner
material "should be gitignored by default"; contract §5 forbade committing it.

The owner also gave facts about the site in chat (UTM coordinates, heights in
metres above sea level, the 12–12.5 m drop is correct, the site is steep)
while the UTM zone, datum/EPSG and vertical datum stay unknown. Only a human
may confirm site facts, through `site confirm` in a terminal (§8).

## Decision

1. **One folder per project: `projects/<name>/`.** The folder *is* the existing
   `ProjectStore` root (`project.json`, `events.jsonl`, `source/`, `artifacts/`)
   plus four working folders: `surveys/` (originals as received), `site/`
   (layer mapping, inspection), `reviews/` (generated review packages and the
   owner's confirmation sheet) and `design/` (interview exports, program, later
   plans and 3D). No second storage system; `verify()` still checks only the
   record.
2. **Migration by moving the store unchanged.** Stored paths are relative to the
   store root, so the event chain, artifact hashes, source hashes and workflow
   history are untouched (`project verify` intact before and after). The
   originals are copied into `surveys/`; `source/` keeps the store's
   byte-identical copies. Git stores identical content once, so nothing is
   duplicated in the repository. The files are 47 KB: no Git LFS.
3. **Minimal selection.** Commands accept a project name (`my-house`) as well as
   a path. `house-ai project new <name>` creates the store and the working
   folders and writes a README listing what the project needs (survey,
   requirements). `house-ai project list` lists `projects/*`. No multi-tenant
   features. `site report` writes to `<project>/reviews/<site>-v<N>/` by default.
4. **Committed by authorisation, only while private.** `projects/my-house/` is
   committed. This applies the spec's "gitignored *by default*": the owner made
   the exception. Agents check `gh repo view --json visibility` before pushing
   project data and stop if it is not private (contract §5). `project-data/`
   stays git-ignored for material outside a project. Store locks, partial writes
   (`.tmp-*`), converted DXF files and credentials are ignored. Tests and
   examples still use synthetic data only; history is not rewritten.
5. **Owner statements.** What the owner says outside the interview is recorded
   verbatim as an `owner_statements` artifact (`house-ai statement add`), naming
   who said it, how it arrived and who recorded it (an agent may record). A
   statement is evidence, never a confirmation: it changes no
   `ConfirmationStatus`, clears no blocker and moves no state. The owner's
   formal confirmation stays `site confirm`; the statement carries the command
   that would make it formal. The site report and review page show statements
   apart from confirmed facts.
6. **Steep triangles are itemised, never smoothed.** The site report lists every
   TIN triangle over 100 % with measured traits (smallest angle, steepest edge
   and its rise, sources, inside the parcel). A thin triangle whose edges are
   all gentle is marked "no steep edge": its steepness comes from its shape.
   Traits are evidence for the surveyor, not causes.

## Consequences

- The real project opens from any checkout: `house-ai project status my-house`.
  A git checkout restores store files without their read-only bits; integrity
  is still checked by hash (`project verify`).
- The repository now holds the owner's site data. Making it public would
  publish that data; changing visibility is the owner's decision only.
- A new house is `house-ai project new <name>`; nothing about the owner's site
  is in application code.
- New schema `owner_statements`; every schema that embeds `ArtifactKind`
  changed with the new kind.
