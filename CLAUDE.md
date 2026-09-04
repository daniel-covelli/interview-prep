# interview-prep — conventions

This repo is Daniel's Python interview practice. Problems are grouped by
company; a shared grader auto-discovers and runs every suite. When adding
problems or company sets, follow this file exactly — it is the spec.

## Layout

```
run.py                          grader entry point (auto-discovers suites)
grader/__init__.py              shared harness — Suite, expect*, tracing, bench…
scratch.py                      Daniel's snippet pad; never import or overwrite it
prep_lib.py                     Daniel's personal helpers (run_test_cases, …)
setup.sh                        creates .venv (3.13) with the repo root on its path
<company>/
  <problem>.py                  one problem per file (docstring spec + stubs)
  tests/test_<problem>.py       that problem's grader suite
```

Company folders are plain namespace packages — no `__init__.py`, no
registration. The venv from `setup.sh` (a `.pth` file in its
site-packages) keeps the repo root importable for every invocation style,
so problem files import Daniel's helpers directly:
`from prep_lib import run_test_cases`. Add new personal helpers to
`prep_lib.py`; they're automatically available to every current and
future company folder. Daniel activates the venv and runs plain `python`;
without it, `python3.13 run.py` and `python3.13 -m company.problem`
still work.

Python 3.13+, standard library only. Nothing is registered anywhere:
`run.py` globs `*/tests/test_*.py` and reads each file's `KEY`.

## Problem files

The docstring IS the complete problem statement; stubs raise
`NotImplementedError`. Daniel practices by reading only CONTEXT and SPEC,
asking clarifying questions out loud, then coding against the grader.
Template (see `monaco/p1_rate_limiter.py` for a finished example):

```
"""
PROBLEM N — <Title>
===================
Difficulty: <warm-up|medium|medium-hard> | Timebox: <NN> min | Interview frequency: <…>

CONTEXT
-------
2–5 lines of realistic product framing (why this system exists).

SPEC
----
Exact signatures and behavior. Phased specs (SPEC — PHASE 1/2/3) for
"keep extending it" problems. Time is always passed in explicitly —
never time.time().

EXAMPLES
--------
Copy-pasteable calls with -> expected values, including one tricky case.

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
The answers an interviewer would give to good clarifying questions:
boundary conventions (half-open windows, tie-breaks), input guarantees,
what's out of scope.

EXTENSIONS
----------
Numbered, in the order to attempt them; hardest ones marked
"Discuss only". These are the live-interview follow-ups.

TARGET COMPLEXITY
-----------------
The asymptotic bar the perf tests enforce.
"""
```

After the stubs, optionally add an `if __name__ == "__main__":` self-check
block (PASS/FAIL prints of the docstring examples, SKIP on
NotImplementedError) so the file runs standalone; the real coverage lives
in the test suite. Keep any `raise NotImplementedError` stubs — the grader
reports them as `- skipped (not implemented yet)`, never as failures.

## Test suites

One file per problem: `<company>/tests/test_<problem>.py`. Non-negotiables:

1. **Header**: `# Grader for <…>` plus a SPOILER WARNING comment — test
   files enumerate edge cases and may embed a reference implementation, and
   Daniel must be able to trust that running them is safe but reading them
   spoils practice.
2. **Boilerplate**:
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
   from grader import (Suite, PerfConcern, load_class, tracing, expect, ...)

   KEY = "m5"          # <prefix><number>; prefix = short company tag (jb, m, …)
   SEED = 0x...        # fixed seed; never random.seed() elsewhere
   ```
   `KEY` is how run.py finds the suite; keys must be unique repo-wide.
3. **Structure of `main()`** (must return `suite.summary()`; end the file
   with `if __name__ == "__main__": sys.exit(1 if main().failed else 0)`):
   - Load via `load_class("company.module", "ClassName")` /
     `load_fn(...)`; on `None`, `suite.skip_all(err)` and return.
   - Wrap classes with `tracing(cls)` so failures replay the exact call
     sequence LeetCode-style.
   - **CORRECTNESS section(s)**: first case is always the docstring's own
     example, labeled "spec example from the file header". Then boundary
     semantics (every half-open interval, tie-break, and "exactly at the
     edge" rule in ASSUMPTIONS gets its own case), degenerate inputs
     (empty, k=0, whole-range), and last a **randomized cross-check
     against a brute-force oracle** defined in the test file, with the
     seed/op index in the failure note so it reproduces.
   - **EXTENSIONS section** titled "EXTENSIONS (skipped until you build
     them)": one case per codeable extension, gated so an unbuilt
     extension SKIPS instead of failing (`if not hasattr(...): raise
     NotImplementedError`, or catch the TypeError from an unsupported
     constructor kwarg and re-raise NotImplementedError). Base-spec cases
     must also tolerate extension output (e.g. project away extra dict
     keys an extension adds).
   - **PERFORMANCE section**, gated:
     ```python
     if suite.failed or not suite.passed:
         suite.section("PERFORMANCE")
         reason = ("fix correctness failures first" if suite.failed
                   else "nothing implemented yet")
         suite.skip("all performance checks", reason)
         return suite.summary()
     ```
     Perf checks compare **scaling ratios, never absolute times**
     (machine-independent): time a workload at n and 4n, assert
     `ratio < 10` for linear/n-log-n targets, or hold one dimension fixed,
     scale the irrelevant one, and assert `ratio < 3` for independence
     claims. `suite.info(...)` the measured timings; make the assert
     message name the naive implementation being caught and the target
     complexity. Finish with one `PerfConcern` (`⚠`) case rehearsing the
     discuss-only extensions / memory story.
4. **Verification bar (do not skip)**: before committing a new suite,
   write BOTH a reference solution and the naive-trap solution in the
   scratchpad, overlay them onto the problem file, and confirm: reference
   → all `✓`; naive → correctness `✓` but the targeted perf check `✗`;
   pristine stubs → everything `-` skipped. Restore the scaffold afterwards.
5. **Determinism**: no wall-clock, no unseeded randomness, no
   order-dependent expectations unless the spec pins the order (give
   randomized records unique tie-break fields so oracle output is unique).

## Grader API (grader/__init__.py)

- `Suite(title)` → `.section(name)`, `.case(label, fn)`, `.skip(label, reason)`,
  `.skip_all(reason)`, `.info(msg)`, `.summary()`
- `expect(output, expected, note=…)`, `expect_raises(ExcType, fn, note=…)`,
  `expect_set`, `expect_len`, `check_topk(result, true_counts, k)`
- `Failure(output=…, expected=…, note=…)` for custom checks;
  `desc("text")` renders un-repr'd in i/o lines
- `tracing(cls)` — call-recording factory for Input replay
- `load_class(dotted_module, name)` / `load_fn(...)` → `(obj, None)` or `(None, reason)`
- `bench(fn, repeat=3)` best-of-N seconds; `fmt_s(seconds)`; `short(obj, limit)`
- `raise PerfConcern("…")` inside a case → `⚠` instead of `✗`

Inside a case: raising `NotImplementedError` → skip; `Failure`/`AssertionError`
→ `✗` with i/o replay; any other exception → `✗` with `Raised:` + crash site.

## Adding a company set

1. `mkdir <company> <company>/tests` — that's the whole setup.
2. Pick an unused short key prefix (letters only — it becomes a run.py
   group alias, alongside the folder name).
3. Add problem files and test suites per the formats above.
4. `python run.py <prefix>` — discovery is automatic; if the new
   suite doesn't appear, its `KEY` line is missing or duplicated.

Keep this file authoritative: format changes belong here, in the same
commit that introduces them.
