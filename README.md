# interview-prep

All my Python interview prep in one place. Each company folder is a set of
practice problems; the shared grader runs LeetCode-style correctness +
performance suites against whatever is currently in the problem files.

```
juicebox/       3 problems (solved) — top-k counter, video views, text search
monaco/         5 problems — rate limiter, KV store w/ TTL+txns,
                contact dedup, meeting scheduler, LRU cache (warm-up)
grader/         shared test harness + the `grade` CLI (nothing interview-relevant inside)
scratch.py      free-for-all snippet pad; nothing imports it
lib.py          my own helpers (run_test_cases, …), importable from any
                problem file: `from lib import run_test_cases`
pyproject.toml  uv project config — defines the `grade` command
```

Python 3.13+, standard library only. Tooling: [uv](https://docs.astral.sh/uv/)
— no setup step, no venv activation; `uv run` manages `.venv` and the
interpreter version transparently.

## Running the grader

```
uv run grade                    # everything
uv run grade monaco/p2_kv_store.py  # one problem (problem or test file path, .py optional)
uv run grade monaco             # one company's set (folder name)
uv run juicebox/video_views.py  # a problem file's own __main__ checks
uv run scratch.py               # the snippet pad
```

No uv? `python3.13 -m grader [path]` still works, and problem files run via
`python3.13 -m juicebox.top_k_counter` (the `-m` form is needed because a
bare script run doesn't put the repo root on the import path).

Suites are auto-discovered from `<company>/tests/test_*.py` — nothing is
registered anywhere.

Output legend:

- `✓` passed
- `✗` a correctness bug **or** a scaling failure (an operation doing
  asymptotically more work than the target)
- `⚠` a concern, not a bug: acceptable v1 behavior the interviewer will
  probe. Have an answer ready for each one you leave standing.
- `-` skipped: not implemented yet (stubs still raising
  `NotImplementedError` skip cleanly), or perf checks held back until
  correctness passes.

Correctness failures print LeetCode-style i/o — the exact call sequence,
the call that went wrong (`→`), your output, and the expected value.
Randomized tests use fixed seeds, so failures reproduce exactly.

## How to practice (each problem)

1. Set a timer for the timebox in the problem's docstring.
2. Read only the CONTEXT and SPEC. Say your clarifying questions OUT LOUD,
   then check them against the "assumptions decided here" section — that
   section stands in for the interviewer's answers.
3. Restate the problem in 2 sentences, name your data structure, THEN code.
4. Get the base spec passing (`uv run grade <company>/<problem>.py`) before touching
   extensions. Narrate trade-offs while you type.
5. Do extensions in order until time runs out. "Discuss only" items: talk
   through them out loud for 2–3 minutes, no code. The `⚠` concerns in the
   grader output are the same rehearsal prompts.

**Spoiler warning:** the `tests/` folders enumerate the edge cases and
contain brute-force oracles and reference implementations. Reading them
defeats the practice — run them instead.

## Adding problems

The full format (docstring template, test-suite shape, naming, grader API)
is codified in [CLAUDE.md](CLAUDE.md) — point any agent at it.
