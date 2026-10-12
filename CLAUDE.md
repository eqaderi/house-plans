@AGENTS.md

## Claude Code specifics

- Hooks in `.claude/settings.json`: editing a `design/*.yaml` runs `bin/hp check`
  (findings come back as hook errors), and the Stop hook runs `hooks/gate.sh`.
- `.claude/settings.json` denies edits to `sources/`, `out/` and `derived/`.
- After a build, hand the result to the `plan-verifier` subagent
  (`.claude/agents/plan-verifier.md`) for an independent check before reporting.
- The IFC MCP server (`ifc`, in `.mcp.json`) is for inspecting generated IFC.
  Never author with it: edits there bypass the spec.
