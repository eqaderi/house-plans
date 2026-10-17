# Projects

One folder per house project (ADR 0009). `my-house/` is the owner's own house and
the default working example. Start another with:

```bash
.venv/bin/house-ai project new <name> --title "<readable name>" --actor human:<you>
.venv/bin/house-ai project list
```

`project new` creates the project record and the working folders, and its README
lists what the new project needs: the survey files and the owner's requirements.
Commands accept a project's name instead of its path.

Project folders hold real owner data and are committed with the owner's
authorisation; the repository must stay private. Never copy anything from here into
`examples/` or `tests/`.
