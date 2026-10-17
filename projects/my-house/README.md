# My house

The owner's own house on their own land: the project this software exists for
(ADR 0009). Every command takes the name: `house-ai project status my-house`.

| Folder | What is there |
|---|---|
| `surveys/` | the survey originals as received: `seperated.dwg` (parcel, road, 6 heights) and `elevation.dwg` (21 heights) |
| `site/` | `layers.yaml` (how the survey's layers are read) and `inspection/` (read-only survey inspection) |
| `reviews/` | `CONFIRM-SITE.md` (what you still need to confirm) and `site-v1/` (the site review page, `index.html`) |
| `design/` | interview exports and the space program (Milestone C), later plans and 3D output |
| `project.json`, `events.jsonl`, `source/`, `artifacts/` | the project record: hash-chained events, immutable source copies and artifact versions. Change it only through `house-ai`; check it with `house-ai project verify my-house` |

`source/` holds byte-identical copies of `surveys/` (same SHA-256, so git stores
each file once). `final.dwg` was the wrong survey and is not part of the project.

State: `SITE_NEEDS_VERIFICATION`. Nothing is approved. Start with
[`reviews/CONFIRM-SITE.md`](reviews/CONFIRM-SITE.md).
