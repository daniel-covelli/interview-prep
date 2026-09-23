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

`uv run grade --reveal <path>` prints the suite's reference solution — the
timebox off-ramp (see Test suites, item 7). Never before the timer ends.

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
Exact signatures and behavior. Phases (SPEC — PHASE 1/2/3) ONLY for
"keep extending it" problems — most problems are unphased and use a
single SPEC. When phased, each phase section ends with its own
`Examples:` block and there is no top-level EXAMPLES section. Everything
Daniel is meant to CODE lives here — a codeable follow-up is a later
phase, never a bullet in some other section. Time is always passed in
explicitly — never time.time().

EXAMPLES
--------
(Unphased problems only.) Copy-pasteable calls with -> expected values,
including one tricky case. Examples always live NEXT TO the description
they illustrate: phase examples inside their SPEC — PHASE section,
helper-function examples with the rules they demonstrate. Daniel writes
his own verification from these examples alone, so every separately
implementable step (phase, stubbed helper) needs enough examples to
check against — a step without examples is unverifiable.

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
The answers an interviewer would give to good clarifying questions:
boundary conventions (half-open windows, tie-breaks), input guarantees,
what's out of scope.

DISCUSS AFTERWARDS
------------------
OPTIONAL — include only when the problem naturally raises follow-ups
worth discussing or researching after the timebox (scaling,
distribution, storage layout, spec negotiation). Bullet questions only:
no signatures, no examples, no code, never a test case. Anything worth
actually CODING is a later SPEC phase instead. Omit the section when a
problem has no worthwhile follow-ups.

TARGET COMPLEXITY
-----------------
The asymptotic bar the perf tests enforce.
"""
```

**NEVER name a data structure or algorithm anywhere in the docstring.**
Not in SPEC, EXAMPLES, ASSUMPTIONS, DISCUSS AFTERWARDS, or TARGET
COMPLEXITY. No "use a heap", no "`OrderedDict` is fair game", no
"the classic dict + doubly-linked list", no "how would a trie change
it", no "hint: binary search". Picking the structure IS the exercise;
the docstring states behavior and the complexity bar, nothing else.
Follow-up questions in DISCUSS AFTERWARDS ask about *properties*
("how do you get O(1) from primitives?"), never about a named
structure. Before committing a new problem, grep the file for
structure/algorithm names (heap, deque, OrderedDict, trie, linked
list, bisect, Counter, BST, sort, two-pointer, sliding window, …)
and rewrite any hit.

## Difficulty tiers and timeboxes (hard limits)

The header's tier and timebox are promises. A broken one costs Daniel
hours, not minutes (2026-09-16: p4, labeled "medium | 40 min", took four
hours). Tiers are set by the REFERENCE SOLUTION, never by how the problem
feels: write the reference first, then classify, and never round down —
when in doubt, the next tier up.

| tier        | reference solution | timebox   | shape |
|-------------|--------------------|-----------|-------|
| warm-up     | ≤ 20 lines         | 15–25 min | one function, or ctor + ≤ 2 methods; no phases; ≤ 4 SPEC rules; ASSUMPTIONS ≤ 4 bullets; DISCUSS ≤ 2 bullets or omitted; one perf check |
| medium      | ≤ 50 lines         | 45–60 min | unphased, or 2 phases |
| medium-hard | ≤ 90 lines         | 60–90 min | phases; the last phase is a stretch goal |

Calibration anchors: p5 LRU cache = warm-up, 25 · p1 rate limiter = 35 ·
p2 KV store = 45 · p3 dedup = 45 · p4 meeting scheduler = medium, 60.

- The timebox is what a competent but rusty engineer needs to get the
  grader green INCLUDING one debugging round — not the time to type the
  reference. Write "(hard stop)" after it; the README tells Daniel to
  stop there and reveal the reference.
- A warm-up's most natural first implementation must ALSO be the one the
  perf section accepts. If the obvious approach would fail a perf check,
  it is not a warm-up — it is two problems (write it, then rewrite it).
- Any tier: when the perf section outlaws the natural first approach,
  TARGET COMPLEXITY must say so in plain words ("the cost must not depend
  on the window's length in minutes") so the constraint shapes the first
  attempt instead of forcing a second one. State the bar, never the
  technique (see the naming rule above).
- Phased problems: the header says where the timebox lands ("phases 1–2
  by minute 25; phase 3 is the stretch"), so running out of time in the
  last phase is the plan, not a failure.
- Scope creep is the enemy of the timebox: extra operations nobody asked
  for, extra rules (falsy values, case sensitivity) and five-bullet
  DISCUSS sections each add minutes. A warm-up gets none of them.

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
   - **Later-phase cases**: a case for a later SPEC phase must SKIP, not
     fail, until Daniel builds that phase (`if not hasattr(...): raise
     NotImplementedError`, or catch the TypeError from an unsupported
     constructor kwarg and re-raise NotImplementedError). Earlier-phase
     cases must tolerate later-phase output (e.g. project away extra dict
     keys a later phase adds). DISCUSS AFTERWARDS items get NO test
     cases — they are talking points, not gradeable code.
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
     DISCUSS AFTERWARDS items / memory story.
     **Timing floor**: every timed measurement must cover at least ~10 ms
     of work — repeat the workload inside the timed callable until it does.
     Sub-millisecond timings turn scheduler noise into a false `✗` that
     Daniel then debugs as if it were his bug. Independence checks
     (`ratio < 3`) must be measured against two different correct
     implementations before the threshold is trusted, and their timed
     loop must pair each op on the scaled structure with a fixed-cost op
     (cache misses alone inflate a correct O(1) op 1.5–2.5x).
4. **Verification bar (do not skip)**: before committing a new suite,
   write BOTH a reference solution and the naive-trap solution in the
   scratchpad, overlay them onto the problem file, and confirm: reference
   → all `✓`; naive → correctness `✓` but the targeted perf check `✗`;
   pristine stubs → everything `-` skipped. Restore the scaffold afterwards.
   Also overlay a SUBTLY wrong solution that only the randomized case
   catches and read its failure text cold: it must be a complete, minimal
   repro (see 6). If you can't name the bug from the text, fix the suite.
5. **Determinism**: no wall-clock, no unseeded randomness, no
   order-dependent expectations unless the spec pins the order (give
   randomized records unique tie-break fields so oracle output is unique).
6. **Failures must be diagnosable without opening the test file**: the
   suites are spoiler-walled, so the printed failure is the ONLY debugging
   information Daniel gets. A failure must therefore show the complete
   experiment: how the object was constructed (every ctor arg, including
   later-phase kwargs like overrides), the full prior call sequence with
   actual return values, and the failing call with Output vs Expected.
   `tracing(...)` records all of this automatically — never build a
   correctness-case object untraced, and never feed a traced object state
   through a side channel it won't record. Where the call sequence alone
   doesn't pin down the rule being tested, add a `note=` naming it (the
   window bounds in play, which key had the override, the seed/op index
   of a randomized case). Litmus test: could Daniel fix the bug from the
   failure text alone? If not, the suite — or the grader's replay — is
   what's broken, not his solution-reading discipline.
   **Minimal repros**: a randomized failure must print a COMPLETE and
   MINIMAL reproduction. Function-shaped suites shrink the failing input
   first (drop records/attendees/intervals, narrow ranges, while the
   mismatch persists) and print the whole shrunk call — never a
   truncated one. Class-shaped suites run many short seeded rounds (≤ ~70
   calls per traced instance — the grader prints up to 80 in full — with a
   fresh instance per round) instead of one
   long run, so the replay prints every call; the grader replays only the
   instance that made the failing call.
7. **Off-ramp**: every suite defines `REFERENCE`, a string holding the
   verified efficient solution used for the verification bar (never the
   brute-force oracle). `uv run grade --reveal <problem>` prints it; the
   README tells Daniel to use it the moment the timebox ends.

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
