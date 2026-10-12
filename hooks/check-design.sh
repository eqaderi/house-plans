#!/usr/bin/env bash
# PostToolUse hook (Claude Code): after an edit to a design spec, run the
# checks. Exit 2 puts the findings in front of the agent; other files pass.
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
file="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("tool_input") or {}).get("file_path",""))')"
case "$file" in
  "$root"/design/*.yaml|"$root"/design/*/*.yaml|design/*.yaml|design/*/*.yaml) ;;
  *) exit 0 ;;
esac
out="$("$root/bin/hp" check "$file" 2>&1)"
status=$?
if [ $status -ne 0 ]; then
  printf 'hp check failed for %s\n%s\n' "$file" "$out" >&2
  exit 2
fi
exit 0
