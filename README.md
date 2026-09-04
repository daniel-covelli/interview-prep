# interview-prep

All my Python interview prep in one place. Each company folder is a set of
practice problems; the shared grader runs LeetCode-style correctness +
performance suites against whatever is currently in the problem files.

```
juicebox/       3 problems (solved) — top-k counter, video views, text search
monaco/         4 problems (scaffolds) — rate limiter, KV store w/ TTL+txns,
                contact dedup, meeting scheduler
grader/         shared test harness (nothing interview-relevant inside)
run.py          the grader entry point
scratch.py      free-for-all snippet pad; nothing imports it
prep_lib.py     my own helpers (run_test_cases, …), importable from any
                problem file: `from prep_lib import run_test_cases`
setup.sh        one-time venv setup (see below)
```

Python 3.13+, standard library only.

## Setup (once)

```
./setup.sh                      # creates .venv with the repo root importable
source .venv/bin/activate       # then plain `python` just works, from any cwd
```

Without the venv everything still runs, you just spell it out:
`python3.13 run.py`, and `python3.13 -m juicebox.top_k_counter` for a
problem file (the `-m` form is needed because a bare script run doesn't
put the repo root on the import path).

## Running the grader

```
python run.py                   # everything
python run.py m2                # one problem by key
python run.py monaco            # one company's set (folder name, or prefix: m / jb)
```

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
4. Get the base spec passing (`python run.py <key>`) before touching
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
