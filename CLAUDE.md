# interview-prep — conventions

This repo is Daniel's Python interview practice. Problems are grouped by
company; a shared grader auto-discovers and runs every suite. When adding
problems or company sets, follow this file exactly — it is the spec.

## Layout

```
grader/__init__.py              shared harness — Suite, expect*, tracing, bench…
grader/cli.py                   the `grade` CLI (auto-discovers suites); __main__.py wraps it
scratch.py                      Daniel's snippet pad; never import or overwrite it
lib.py                          Daniel's personal helpers (run_test_cases, …)
pyproject.toml                  uv project; `grade = "grader.cli:main"` entry point
<company>/
  <problem>.py                  one problem per file (docstring spec + stubs)
  tests/test_<problem>.py       that problem's grader suite
```

Tooling is uv: run everything as `uv run grade [path|company]` (e.g.
`uv run grade monaco/p2_kv_store.py` — problem file or test file path,
`.py` optional — or a company folder name for the whole set) and problem
files as `uv run <company>/<problem>.py` — uv owns `.venv`, installs the
tooling modules editable (see pyproject.toml), and pins Python via
`.python-version`. Never add a venv-activation or `python3.13` step to
docs or scripts; without uv the fallbacks are `python3.13 -m grader` and
`python3.13 -m company.problem`.

Company folders are plain namespace packages — no `__init__.py`, no
registration anywhere (grader/cli.py discovers by glob; never list company
folders in pyproject.toml). Problem files import Daniel's helpers
directly: `from lib import run_test_cases`. Add new personal helpers to
`lib.py`; they're automatically available to every current and future
company folder.

Python 3.13+, standard library only. Nothing is registered anywhere:
the CLI globs `*/tests/test_*.py` and addresses each suite by its path
(a `pN_` prefix on the problem file is ignored when matching).

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
Sufficient examples for EVERY separately implementable step — each phase
of a phased spec, each stubbed helper function, and each codeable
extension gets its own example block (EXAMPLES — PHASE 2, EXAMPLES —
EXTENSION 1 (name), …). Daniel writes his own verification from these
examples alone, so a step without examples is unverifiable.

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

A problem file contains NOTHING beyond the docstring and the
`raise NotImplementedError` stubs (plus any exception classes the spec
names). Never add an `if __name__ == "__main__":` block, self-checks, or
any other verification code — every example must live in the docstring
(EXAMPLES section), and Daniel writes his own `__main__` checks with
`run_test_cases` from lib.py as part of practicing. Real
coverage lives in the test suite. Keep the `raise NotImplementedError`
stubs — the grader reports them as `- skipped (not implemented yet)`,
never as failures.

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

   SEED = 0x...        # fixed seed; never random.seed() elsewhere
   ```
   The CLI finds the suite by its file path — no key or registration.
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
6. **Failures must be diagnosable without opening the test file**: the
   suites are spoiler-walled, so the printed failure is the ONLY debugging
   information Daniel gets. A failure must therefore show the complete
   experiment: how the object was constructed (every ctor arg, including
   extension kwargs like overrides), the full prior call sequence with
   actual return values, and the failing call with Output vs Expected.
   `tracing(...)` records all of this automatically — never build a
   correctness-case object untraced, and never feed a traced object state
   through a side channel it won't record. Where the call sequence alone
   doesn't pin down the rule being tested, add a `note=` naming it (the
   window bounds in play, which key had the override, the seed/op index
   of a randomized case). Litmus test: could Daniel fix the bug from the
   failure text alone? If not, the suite — or the grader's replay — is
   what's broken, not his solution-reading discipline.

## Grader API (grader/__init__.py)

- `Suite(title)` → `.section(name)`, `.case(label, fn)`, `.skip(label, reason)`,
  `.skip_all(reason)`, `.info(msg)`, `.summary()`
- `expect(output, expected, note=…)`, `expect_raises(ExcType, fn, note=…)`,
  `expect_set`, `expect_len`, `check_topk(result, true_counts, k)`
- `Failure(output=…, expected=…, note=…)` for custom checks;
  `desc("text")` renders un-repr'd in i/o lines
- `tracing(cls)` — call-recording factory for Input replay: captures the
  constructor args and every method call *and its return value*, so a
  failure replays as `Cls(args): call(...) -> result; … → failing_call`
- `load_class(dotted_module, name)` / `load_fn(...)` → `(obj, None)` or `(None, reason)`
- `bench(fn, repeat=3)` best-of-N seconds; `fmt_s(seconds)`; `short(obj, limit)`
- `raise PerfConcern("…")` inside a case → `⚠` instead of `✗`

Inside a case: raising `NotImplementedError` → skip; `Failure`/`AssertionError`
→ `✗` with i/o replay; any other exception → `✗` with `Raised:` + crash site.

## Adding a company set

1. `mkdir <company> <company>/tests` — that's the whole setup.
2. Add problem files and test suites per the formats above.
3. `uv run grade <company>` — discovery is automatic; if the new
   suite doesn't appear, its test file doesn't match
   `<company>/tests/test_*.py`.

Keep this file authoritative: format changes belong here, in the same
commit that introduces them.
