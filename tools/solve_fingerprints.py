"""Count CP-SAT solves and repeats across a pytest run (ADR 0035).

As a pytest plugin it logs one line per `CpSolver.Solve`: a fingerprint of the model and
its parameters, the solve time, the worker, and the running test. As a script it
summarises the logs: total and distinct solves, and the repeats, split into same-worker
repeats (avoidable by sharing) and repeats on another worker.

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
        with out.open("a") as f:
            f.write("\t".join([*line, worker, test]) + "\n")
        return result

    cp_model.CpSolver.Solve = solve


def summarise(log_dir: Path) -> str:
    rows = [
        line.rstrip("\n").split("\t")
        for path in sorted(log_dir.glob("log-*.tsv"))
        for line in path.read_text().splitlines()
    ]
    seen: dict[str, set[str]] = collections.defaultdict(set)
    same = other = 0
    same_s = 0.0
    by_test: collections.Counter[str] = collections.Counter()
    for digest, seconds, worker, test in rows:
        if digest in seen:
            if worker in seen[digest]:
                same += 1
                same_s += float(seconds)
                by_test[test.split("::")[0]] += 1
            else:
                other += 1
        seen[digest].add(worker)
    lines = [
        f"solves {len(rows)}, distinct {len(seen)}, "
        f"same-worker repeats {same} ({same_s:.1f} s), other-worker repeats {other}"
    ]
    lines += [f"  {n:3d}  {f}" for f, n in by_test.most_common(15)]
    return "\n".join(lines)


if __name__ == "__main__":
    print(summarise(Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/solves")))
else:
    _install()
