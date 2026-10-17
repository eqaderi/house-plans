"""Consistency check for docs/PROJECT_TRACKER.md (plain Markdown, no app).

Run with the project venv: python tools/check_tracker.py [--summary].
Exit code 1 lists every problem. The tracker's "Rules for updating the
tracker" section defines the format this script enforces; tests run it too.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

TRACKER = Path(__file__).resolve().parents[1] / "docs" / "PROJECT_TRACKER.md"

STATUSES = {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "DONE", "DEFERRED"}
REVIEWS = {"NOT_REQUESTED", "PENDING", "CHANGES_REQUESTED", "APPROVED"}
PRIORITIES = {"P0", "P1", "P2", "P3"}
DECISIONS = {"UNEVALUATED", "ADOPT", "ADAPT", "REJECT", "DEFER"}

STAGE_ID = r"[A-Z][A-Z0-9]*(?:\.\d+)?"
TASK_ID = rf"{STAGE_ID}-\d{{2}}"
STAGE_HEAD = re.compile(rf"^### Stage (?P<id>{STAGE_ID}) — (?P<title>.+)$")
STAGE_ROW = re.compile(r"^\| (?P<key>[A-Za-z ]+?) \| (?P<value>.*) \|$")
TASK_HEAD = re.compile(
    rf"^- \[(?P<box>[ x])\] \*\*(?P<id>{TASK_ID})\*\* (?P<title>.+?) — "
    r"`(?P<status>[A-Z_]+)` · (?P<prio>P\d) · deps: (?P<deps>.+)$"
)
TASK_FIELD = re.compile(r"^  - (?P<key>Accept|Verify|Evidence|Notes):(?P<value>.*)$")
TOOL_ROW = re.compile(r"^\| (?P<id>TOOL-[A-Z0-9-]+) \|.*\| (?P<decision>[A-Z]+) \|$")
REQUIRED_FIELDS = ("Accept", "Verify", "Evidence")
STAGE_ROWS = (
    "Kind",
    "Status",
    "Review",
    "Branch",
    "Depends on",
    "Tasks",
    "Objective",
    "Scope",
    "Acceptance",
    "Tests",
    "Demonstration",
    "Artifacts",
    "Review requirements",
    "Evidence",
)
PENDING_EVIDENCE = re.compile(r"^\s*(?:(?:—|-)\s*$|(?:pending|none|tbd)\b)", re.IGNORECASE)


@dataclass
class Task:
    id: str
    stage: str
    status: str
    prio: str
    deps: list[str]
    checked: bool
    line: int
    fields: dict[str, str] = field(default_factory=dict)


@dataclass
class Stage:
    id: str
    title: str
    line: int
    rows: dict[str, str] = field(default_factory=dict)
    tasks: list[Task] = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.rows.get("Status", "").split()[0] if self.rows.get("Status") else ""

    @property
    def review(self) -> str:
        return self.rows.get("Review", "").split()[0] if self.rows.get("Review") else ""

    @property
    def historical(self) -> bool:
        return self.rows.get("Kind", "").startswith("historical")


def _ids(text: str, pattern: str) -> list[str]:
    return re.findall(rf"\b{pattern}\b", text)


def parse(text: str) -> tuple[list[Stage], list[str], list[str]]:
    """Return stages (with tasks), tool decisions and parse errors."""
    stages: list[Stage] = []
    tools: list[str] = []
    errors: list[str] = []
    stage: Stage | None = None
    task: Task | None = None
    for n, line in enumerate(text.splitlines(), start=1):
        if line.startswith(("## ", "### ")):
            stage, task = None, None
        if m := STAGE_HEAD.match(line):
            stage, task = Stage(m["id"], m["title"], n), None
            stages.append(stage)
            continue
        if m := TOOL_ROW.match(line):
            tools.append(m["decision"])
        if stage is None:
            continue
        if not stage.tasks and (m := STAGE_ROW.match(line)):
            stage.rows[m["key"]] = m["value"].strip()
            continue
        if m := TASK_HEAD.match(line):
            deps_text = m["deps"].strip()
            deps = [] if deps_text == "none" else [d.strip() for d in deps_text.split(",")]
            task = Task(m["id"], stage.id, m["status"], m["prio"], deps, m["box"] == "x", n)
            stage.tasks.append(task)
            continue
        if line.startswith("- [") and "**" in line:
            errors.append(f"line {n}: malformed task line: {line[:80]}")
            task = None
            continue
        if task and (m := TASK_FIELD.match(line)):
            task.fields[m["key"]] = m["value"].strip()
    return stages, tools, errors


def check(text: str) -> tuple[list[str], dict[str, Counter]]:
    stages, tools, errors = parse(text)
    stage_ids = Counter(s.id for s in stages)
    tasks = [t for s in stages for t in s.tasks]
    task_ids = Counter(t.id for t in tasks)
    known = set(stage_ids) | set(task_ids)

    errors += [f"duplicate stage id {i}" for i, c in stage_ids.items() if c > 1]
    errors += [f"duplicate task id {i}" for i, c in task_ids.items() if c > 1]

    for s in stages:
        where = f"stage {s.id} (line {s.line})"
        for key in STAGE_ROWS:
            if key not in s.rows:
                errors.append(f"{where}: missing '{key}' row")
        if s.status not in STATUSES:
            errors.append(f"{where}: bad status {s.status!r}")
        if s.review not in REVIEWS:
            errors.append(f"{where}: bad review status {s.review!r}")
        deps = s.rows.get("Depends on", "")
        for dep in _ids(deps, STAGE_ID + r"(?:-\d{2})?"):
            if dep not in known:
                errors.append(f"{where}: unknown dependency {dep}")
        listed = _ids(s.rows.get("Tasks", ""), TASK_ID)
        actual = [t.id for t in s.tasks]
        if listed != actual:
            errors.append(f"{where}: 'Tasks' row {listed} does not match tasks {actual}")
        if not s.tasks:
            errors.append(f"{where}: no tasks")
        if s.status == "DONE":
            open_tasks = [t.id for t in s.tasks if t.status not in {"DONE", "DEFERRED"}]
            if open_tasks:
                errors.append(f"{where}: DONE but tasks open: {open_tasks}")
            if not s.historical and s.review != "APPROVED":
                errors.append(f"{where}: DONE without APPROVED review")
        if s.review in {"PENDING", "CHANGES_REQUESTED"} and s.status != "IN_PROGRESS":
            errors.append(f"{where}: review {s.review} requires status IN_PROGRESS")

    for t in tasks:
        where = f"task {t.id} (line {t.line})"
        if not t.id.startswith(t.stage + "-"):
            errors.append(f"{where}: id does not belong to enclosing stage {t.stage}")
        if t.status not in STATUSES:
            errors.append(f"{where}: bad status {t.status!r}")
        if t.prio not in PRIORITIES:
            errors.append(f"{where}: bad priority {t.prio!r}")
        if t.checked != (t.status == "DONE"):
            errors.append(f"{where}: checkbox must be [x] exactly when DONE")
        for dep in t.deps:
            if dep not in known:
                errors.append(f"{where}: unknown dependency {dep}")
        for key in REQUIRED_FIELDS:
            if not t.fields.get(key):
                errors.append(f"{where}: missing '{key}'")
        evidence = t.fields.get("Evidence", "")
        if t.status == "DONE" and (not evidence or PENDING_EVIDENCE.match(evidence)):
            errors.append(f"{where}: DONE without evidence")
        if t.status == "BLOCKED" and not t.fields.get("Notes"):
            errors.append(f"{where}: BLOCKED without a Notes line naming the blocker")

    errors += [f"tool register: bad decision {d!r}" for d in tools if d not in DECISIONS]

    counts = {
        "stages": Counter(s.status for s in stages),
        "reviews": Counter(s.review for s in stages),
        "tasks": Counter(t.status for t in tasks),
        "tools": Counter(tools),
    }
    return errors, counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", type=Path, default=TRACKER)
    parser.add_argument("--summary", action="store_true", help="print counts")
    args = parser.parse_args(argv)
    errors, counts = check(args.path.read_text(encoding="utf-8"))
    if args.summary:
        for name, counter in counts.items():
            total = sum(counter.values())
            detail = ", ".join(f"{k} {v}" for k, v in sorted(counter.items()))
            print(f"{name}: {total} ({detail})")
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
