"""Count CP-SAT solves and repeats across a pytest run (ADR 0035).

As a pytest plugin it logs one line per `CpSolver.Solve`: a fingerprint of the model and
its parameters, the time the call took, the worker, the running test, and whether the
solve memo of `tests/conftest.py` answered it (`memo`) or the solver ran (`solved`). As a
script it summarises the logs: the calls, the distinct models, the calls the memo answered,
and the real solves of a model already solved, on the same worker (only tests marked
`fresh_solves` should have any) and on another worker.

    rm -rf /tmp/solves && mkdir /tmp/solves
    SOLVE_LOG_DIR=/tmp/solves PYTHONPATH=tools .venv/bin/python -m pytest -q -p solve_fingerprints
    .venv/bin/python tools/solve_fingerprints.py /tmp/solves
"""

from __future__ import annotations

import collections
import hashlib
import os
import sys
import time
from pathlib import Path


def _install() -> None:
    from ortools.sat.python import cp_model

    out = Path(os.environ.get("SOLVE_LOG_DIR", "/tmp/solves")) / f"log-{os.getpid()}.tsv"
    original = cp_model.CpSolver.Solve

    def solve(self, model, *args, **kwargs):
        key = (str(model.Proto()) + str(self.parameters)).encode()
        start = time.perf_counter()
        result = original(self, model, *args, **kwargs)
        test = os.environ.get("PYTEST_CURRENT_TEST", "").split(" ")[0]
        worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
        line = [hashlib.sha1(key).hexdigest()[:16], f"{time.perf_counter() - start:.3f}"]
        how = "memo" if getattr(self, "from_memo", False) else "solved"
        with out.open("a") as f:
            f.write("\t".join([*line, worker, test, how]) + "\n")
        return result

    cp_model.CpSolver.Solve = solve


def summarise(log_dir: Path) -> str:
    rows = [
        line.rstrip("\n").split("\t")
        for path in sorted(log_dir.glob("log-*.tsv"))
        for line in path.read_text().splitlines()
    ]
    solved: dict[str, set[str]] = collections.defaultdict(set)
    replayed = same = other = 0
    same_s = 0.0
    again: collections.Counter[str] = collections.Counter()
    for digest, seconds, worker, test, how in rows:
        if how == "memo":
            replayed += 1
            continue
        if worker in solved[digest]:
            same += 1
            same_s += float(seconds)
            again[test] += 1
        elif solved[digest]:
            other += 1
        solved[digest].add(worker)
    lines = [
        f"solve calls {len(rows)}, distinct models {len({r[0] for r in rows})}, "
        f"answered by the memo {replayed}, solved {len(rows) - replayed}",
        f"solved again on the same worker {same} ({same_s:.1f} s), "
        f"solved again on another worker {other}",
    ]
    lines += [f"  {n:3d}  {test}" for test, n in again.most_common()]
    return "\n".join(lines)


if __name__ == "__main__":
    print(summarise(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/solves")))
else:
    _install()
