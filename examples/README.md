# examples/

Synthetic, redistributable example projects. Nothing here is real owner
data.

- `projects/synthetic-bungalow/`: a fictional single-storey house on a
  fictional plot. Site, brief, program, assumptions, open questions,
  constraints, an unverified synthetic code pack, and one hand-authored
  golden plan (`plans/plan-a.json`) that passes every integrity check. The
  plan pins the content hashes of `site.yaml` and `space_program.yaml`; if
  you change either, the golden tests fail until the plan's refs are
  updated.

Load it into a project store:

```bash
.venv/bin/house-ai example load project-data/demo --actor agent:cli
```
