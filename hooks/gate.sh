#!/usr/bin/env bash
# Done-gate. Claude Code runs it as a Stop hook; Codex and humans run it by
# hand before calling work finished. It fails while any design spec has
# errors, or has changed since its sheets were drawn (sketch stage: hp sketch;
# final stage: hp build), or the tests fail.
set -uo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ ! -t 0 ]; then
  active="$(python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("stop_hook_active", False))
except Exception: print(False)')"
  [ "$active" = "True" ] && exit 0
fi
problems=""
for spec in "$root"/design/*.yaml; do
  [ -e "$spec" ] || continue
  stem="$(basename "$spec" .yaml)"
  if grep -Eq '^[[:space:]]*stage:[[:space:]]*final' "$spec"; then
    marker="$root/out/$stem/report.json"; cmd="build"
  else
    marker="$(ls "$root/out/$stem"/sketch-*.png 2>/dev/null | head -1)"; cmd="sketch"
  fi
  if ! "$root/bin/hp" check "$spec" >/dev/null 2>&1; then
    problems+="- $spec has errors: run bin/hp check $spec"$'\n'
  elif [ -z "$marker" ] || [ ! -f "$marker" ] || [ "$spec" -nt "$marker" ]; then
    problems+="- $spec changed since its sheets were drawn: run bin/hp $cmd $spec and look at the PNGs"$'\n'
  fi
done
if ! (cd "$root" && PYTHONPATH=src "${HP_PYTHON:-$HOME/.venvs/architecture-ai/bin/python}" -m pytest -q tests >/dev/null 2>&1); then
  problems+="- tests fail: run PYTHONPATH=src python -m pytest -q tests"$'\n'
fi
if [ -n "$problems" ]; then
  printf 'Not done yet:\n%s' "$problems" >&2
  exit 2
fi
exit 0
