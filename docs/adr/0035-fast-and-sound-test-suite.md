# ADR 0035: A fast and sound test suite

Status: proposed (requested by the owner 2026-11-21).

## Context

The full suite took 467 s on one core (1107 tests, 2026-11-21). 68 tests took
428 s of that; the other ~1040 took 36 s together. The owner ran it before every
hand-off, as contract §10 requires, and found it too slow and too hot on a laptop.

Three causes were measured, not guessed:

- **One core.** pytest ran single-process on an 11-core machine. Four workers
  finished in 149 s; eleven took 212 s, because the extra workers fight over the
  CPU and the laptop's efficiency cores.
- **Repeated solves.** Fingerprinting every CP-SAT model and its parameters over a
  run found 328 solves of 123 distinct problems: 133 s of 262 s solver time went to
  re-solving a problem the run had already solved, mostly inside one file
  (`test_plan_propose.py` solved one 7.6 s model ten times).
- **Slow evaluation.** About half the slow tests' time was not the solver but the
  evaluators. The furniture search built ~200,000 shapely boxes one by one through
  `affinity.rotate` and `translate`; the route search rebuilt a floor's full
  visibility graph, with unprepared `covers` and three buffers, for every query.

An independent review of all 75 test files (2026-11-21) also found tests weaker than
their names: assertions under an `if` that can pass with none run, `pytest.raises`
accepting any failure, a `model_copy` with a misspelt field that tested nothing, a
"screenshot regression" comparing compressed PNG bytes, and a grounding validator
that accepted any number once a metric name appeared in the claim.

GitHub Actions does not run on this private repository at present (account billing
since 2026-11-18), so the local run is the only gate; pushing slow tests to CI is
not an option for now.

## Decision

1. **Four workers, one file per worker.** `pytest` runs `-n 4 --dist loadfile`
   (pytest-xdist). Keeping a file on one worker builds each module fixture once and
   keeps a file's tests in order. `-n 0` runs single-process.
2. **Never solve the same problem twice.** Tests that need the same generated plans
   share them: a module fixture within a file, or the session fixture `hillside` in
   `tests/conftest.py` for exploratory synthetic-hillside options. The fixture
   hands out deep copies, and tests that write copy a template store, so no test
   sees another's changes. A test solves afresh only when fresh solving is what it
   checks (reproducibility).
   Sharing fixtures cannot reach every repeat: a test of `plan propose`, `plan revise`
   or a stored `plan generate` has to run the command, and which files share a worker
   changes from run to run (review 1 counted 82 solves of a model its worker had
   already solved). So `tests/conftest.py` also keeps a **solve memo** per test
   process: `CpSolver.solve` is wrapped, and a model with the same content and solver
   parameters as one already solved gets that solve's response. This is sound because
   the product solves on one worker with a fixed seed and a deterministic time limit.
   A test marked `@pytest.mark.fresh_solves` solves again
   (`test_solver_reproducibility_budget`, `test_generation_is_deterministic`: they
   compare a fresh solve with a shared one, which is the standing proof that a replay
   equals a solve). `pytest --fresh-solves` runs the whole suite without replays, and
   `tools/solve_fingerprints.py` reports calls, replays and real re-solves.
3. **Faster evaluation with identical output.** `routes.shortest_in_polygon` keeps
   one visibility graph per floor (`_floor_visibility`, keyed by the floor's WKB) and
   adds the two query points; neighbour lists keep the ascending order of the old
   all-pairs scan, so Dijkstra visits nodes in the same order. The furniture search
   tests all positions of a rotation in one array call (`shifted` adds the offsets to
   the rotated corners, which is exactly what `affinity.translate` computes). On a
   reference set of 38 evaluations (synthetic-hillside concepts, plan-a, every
   benchmark case, every seeded pair), all reports, 978 route calls and 60 fit calls
   are byte-identical, and evaluation time fell from 17.1 s to 4.2 s.
4. **Tests check what they promise.** A test asserts exact values (lists, sets,
   counts, hand-derived numbers); not `>=`, truthiness or presence where an exact
   value is known. It never pins solver coordinates, which may differ by platform; it
   asserts properties that must hold. A new or repaired test is shown to fail
   against the broken behaviour before it is trusted.
5. **No slow tier for now.** With the above, every test runs before every hand-off.
   If the suite again exceeds about two minutes on the default runner, measure first;
   a `slow` marker run only in CI is the last resort, once CI runs again.

## Consequences

- The local default run uses four cores; a machine with fewer cores still works.
- New tests that generate plans should reuse `hillside` or a module fixture, which
  also saves the evaluation and the store set-up; the solve memo catches the solves
  that still repeat. The reviewer of a stage runs `tools/solve_fingerprints.py`: only
  tests marked `fresh_solves` may solve a model their worker has already solved.
- The memo reads one private attribute of ortools' `CpSolver` (its response). If an
  ortools release moves it, the memo stops replaying, nothing else breaks, and
  `tests/test_solve_memo.py` fails and says so.
- The evaluator speedups change no result. Any later change to them must keep
  `tests/test_geometry_caches.py` passing, which compares the cached route graph
  with a fresh one and the vectorised candidates with `template_shapes`, and checks
  the furniture search's three array tests against rooms sized by hand from the
  double-bed template: the envelope inside the floor
  (`test_a_double_bed_does_not_fit_an_l_shaped_room_with_narrow_arms`,
  `test_a_double_bed_fits_a_room_exactly_the_size_of_its_envelope`), and door swings
  and door approaches
  (`test_door_swings_keep_the_envelope_out_and_door_approaches_keep_the_body_out`).
