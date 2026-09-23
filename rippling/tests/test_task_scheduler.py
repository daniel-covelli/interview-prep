# Grader for Rippling Problem 3 (rippling/p3_task_scheduler.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle and the reference solution. Run it, don't read it.
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, Failure, load_class, load_fn, bench,
                    fmt_s, expect, expect_raises, desc)

SEED = 0x7A5C

# Reference solution, printed by `uv run grade --reveal rippling/p3_task_scheduler`
# once the timebox is up. Never read it before then.
REFERENCE = '''
class CycleError(Exception):
    pass


def schedule(tasks, deps):
    duration = dict(tasks)
    after = {t: [] for t in duration}        # t -> tasks that wait for t
    waiting = {t: 0 for t in duration}       # prerequisites not yet finished
    for a, b in set(deps):                   # a repeated pair counts once
        after[a].append(b)
        waiting[b] += 1
    start = {t: 0 for t in duration}
    finish = {}
    ready = [t for t in duration if waiting[t] == 0]
    while ready:                             # each task is settled exactly once
        t = ready.pop()
        finish[t] = start[t] + duration[t]
        for b in after[t]:
            start[b] = max(start[b], finish[t])
            waiting[b] -= 1
            if waiting[b] == 0:
                ready.append(b)
    if len(finish) != len(duration):         # something never became ready
        raise CycleError
    order = sorted(finish, key=lambda t: (finish[t], t))
    return (max(finish.values(), default=0), order)
'''



def measure(fn, diagnosis, repeat=2):
    """bench() that attaches the case's diagnosis to a TLE, so a workload
    that never finishes still names the naive design being caught."""
    try:
        return bench(fn, repeat=repeat)
    except AssertionError as e:
        raise AssertionError(f"{diagnosis}  [{e}]") from None

class _OracleCycle(Exception):
    pass


def oracle_schedule(tasks, deps):
    """Brute-force truth: relax every task's finish day from its prerequisites
    over and over until nothing changes (a DAG settles within T passes);
    still changing after T + 1 passes means a cycle."""
    duration = dict(tasks)
    prereqs = {t: set() for t in duration}
    for a, b in deps:
        prereqs[b].add(a)
    finish = {t: 0 for t in duration}
    for _ in range(len(duration) + 1):
        changed = False
        for t in duration:
            f = duration[t] + max((finish[p] for p in prereqs[t]), default=0)
            if f != finish[t]:
                finish[t] = f
                changed = True
        if not changed:
            break
    else:
        raise _OracleCycle
    return (max(finish.values(), default=0),
            sorted(finish, key=lambda t: (finish[t], t)))


def outcome_oracle(tasks, deps):
    try:
        return ("ok", oracle_schedule(tasks, deps))
    except _OracleCycle:
        return ("raised", "CycleError")


def outcome_solution(schedule, CycleError, tasks, deps):
    """Call the solution on private copies; any raise reads as an outcome."""
    try:
        return ("ok", schedule(list(tasks), list(deps)))
    except CycleError:
        return ("raised", "CycleError")
    except NotImplementedError:
        raise                                    # a stub: the case is skipped, not failed
    except Exception as e:                       # noqa: BLE001 — report, don't hide
        return ("raised", f"{type(e).__name__}: {e}")


def shrink(schedule, CycleError, tasks, deps):
    """Delta-debug a failing input down to a minimal one that still
    mismatches the oracle: drop a task (and its deps), drop a dependency,
    shrink a duration to 1. Every accepted step strictly shrinks the input."""
    def fails(ts, ds):
        return outcome_solution(schedule, CycleError, ts, ds) != outcome_oracle(ts, ds)

    def reductions(ts, ds):
        for i, (tid, _) in enumerate(ts):
            yield ts[:i] + ts[i + 1:], [d for d in ds if tid not in d]
        for i in range(len(ds)):
            yield ts, ds[:i] + ds[i + 1:]
        for i, (tid, dur) in enumerate(ts):
            if dur > 1:
                yield ts[:i] + [(tid, 1)] + ts[i + 1:], ds

    progress = True
    while progress:
        progress = False
        for cand in reductions(tasks, deps):
            if fails(*cand):
                tasks, deps = cand
                progress = True
                break
    return tasks, deps


def fmt_outcome(o):
    return o[1] if o[0] == "ok" else desc(f"raises {o[1]}")


def check(schedule, CycleError, tasks, deps, ctx):
    got = outcome_solution(schedule, CycleError, tasks, deps)
    want = outcome_oracle(tasks, deps)
    if got == want:
        return
    n_t, n_d = len(tasks), len(deps)
    st, sd = shrink(schedule, CycleError, tasks, deps)
    raise Failure(output=fmt_outcome(outcome_solution(schedule, CycleError, st, sd)),
                  expected=fmt_outcome(outcome_oracle(st, sd)),
                  note=f"MINIMAL REPRO: schedule({st!r}, {sd!r})  "
                       f"[shrunk from {ctx}: {n_t} tasks, {n_d} deps]")


def random_dag(rng, n, extra_edges, dup_chance=0.1):
    """n tasks in a hidden order; edges only point forward, so it's acyclic."""
    ids = [f"t{i}" for i in range(n)]
    rng.shuffle(ids)
    tasks = [(tid, rng.randrange(1, 9)) for tid in sorted(ids)]
    deps = []
    for _ in range(extra_edges):
        i, j = sorted(rng.sample(range(n), 2)) if n > 1 else (0, 0)
        if i != j:
            deps.append((ids[i], ids[j]))
            if rng.random() < dup_chance:
                deps.append((ids[i], ids[j]))
    rng.shuffle(deps)
    return tasks, deps


def main():
    suite = Suite("Rippling 3: schedule")
    schedule, err = load_fn("rippling.p3_task_scheduler", "schedule")
    if schedule is None:
        suite.skip_all(err)
        return suite.summary()
    CycleError, cerr = load_class("rippling.p3_task_scheduler", "CycleError")
    if CycleError is None:
        suite.skip_all(cerr)
        return suite.summary()

    suite.section("CORRECTNESS")

    def spec_example():
        tasks = [("laptop", 2), ("accounts", 1), ("badge", 3), ("payroll", 2), ("welcome", 1)]
        deps = [("accounts", "payroll"), ("laptop", "welcome"),
                ("accounts", "welcome"), ("badge", "welcome")]
        expect(schedule(tasks, deps), (4, ["accounts", "laptop", "badge", "payroll", "welcome"]),
               note="accounts 0-1, laptop 0-2, badge 0-3, payroll 1-3, welcome 3-4; "
                    "badge and payroll tie on day 3 -> ascending id")
        expect(schedule([("a", 3), ("b", 1)], []), (3, ["b", "a"]))
        expect(schedule([], []), (0, []))
        expect(schedule([("a", 1), ("b", 1), ("c", 1)], [("a", "b"), ("b", "c"), ("a", "b")]),
               (3, ["a", "b", "c"]), note="a repeated dependency pair changes nothing")
        expect(schedule([("a", 1), ("b", 1), ("c", 1), ("big", 2)], [("a", "b"), ("b", "c")]),
               (3, ["a", "b", "big", "c"]),
               note="a 0-1, b 1-2, big 0-2, c 2-3: the chain sets the total")
    suite.case("spec example from the file header", spec_example)

    def cycles():
        expect_raises(CycleError, lambda: schedule([("a", 1), ("b", 1)], [("a", "b"), ("b", "a")]),
                      note="a before b and b before a")
        expect_raises(CycleError, lambda: schedule([("a", 1)], [("a", "a")]),
                      note="a task that depends on itself")
        expect_raises(CycleError,
                      lambda: schedule([("a", 1), ("b", 2), ("c", 3), ("d", 4)],
                                       [("a", "b"), ("b", "c"), ("c", "b"), ("c", "d")]),
                      note="a 3-task cycle b -> c -> b with an acyclic head (a) and tail (d): "
                           "some tasks can still be scheduled, but the whole plan can't")
    suite.case("cycles raise CycleError", cycles)

    def waits_for_the_last():
        tasks = [("x", 5), ("y", 1), ("z", 2), ("join", 1)]
        deps = [("y", "join"), ("x", "join"), ("z", "join")]
        expect(schedule(tasks, deps), (6, ["y", "z", "x", "join"]),
               note="join waits for x (day 5), its slowest prerequisite, not for the "
                    "first one to finish")
        deps2 = [("y", "join"), ("z", "join"), ("x", "join"), ("y", "z")]
        expect(schedule(tasks, deps2), (6, ["y", "z", "x", "join"]),
               note="y 0-1, z 1-3, x 0-5: still day 5 for join's start")
    suite.case("a task starts when its LAST prerequisite finishes", waits_for_the_last)

    def ordering():
        tasks = [("t2", 1), ("t10", 1), ("t1", 1)]
        expect(schedule(tasks, []), (1, ["t1", "t10", "t2"]),
               note="ties are broken by plain string order: 't10' < 't2'")
        tasks = [("b", 2), ("a", 2), ("c", 1)]
        expect(schedule(tasks, [("c", "a")]), (3, ["c", "b", "a"]),
               note="c 0-1, b 0-2, a 1-3: ordered by finish day, not by input position")
        tasks = [("z", 1), ("y", 1), ("x", 1)]
        expect(schedule(tasks, [("z", "y"), ("y", "x")]), (3, ["z", "y", "x"]),
               note="a chain finishes in chain order even though the ids say otherwise")
    suite.case("finish-day order with ascending-id tie-break", ordering)

    def diamond_and_fanout():
        tasks = [("root", 1)] + [(f"mid{i}", i + 1) for i in range(4)] + [("leaf", 1)]
        deps = [("root", f"mid{i}") for i in range(4)] + [(f"mid{i}", "leaf") for i in range(4)]
        expect(schedule(tasks, deps),
               (6, ["root", "mid0", "mid1", "mid2", "mid3", "leaf"]),
               note="root 0-1, mid_i 1-(2+i), leaf waits for mid3 (day 5): 5-6")
        tasks = [("hub", 2)] + [(f"s{i}", 1) for i in range(5)]
        deps = [("hub", f"s{i}") for i in range(5)] + [("hub", "s2")]
        expect(schedule(tasks, deps), (3, ["hub", "s0", "s1", "s2", "s3", "s4"]),
               note="five tasks fan out from hub and all finish on day 3")
    suite.case("diamond: one prerequisite feeding many, many feeding one", diamond_and_fanout)

    def long_chain():
        n = 3000
        tasks = [(f"c{i:04d}", 1) for i in range(n)]
        deps = [(f"c{i:04d}", f"c{i + 1:04d}") for i in range(n - 1)]
        random.Random(SEED).shuffle(deps)
        got = schedule(tasks, deps)
        expect(got, (n, [tid for tid, _ in tasks]),
               note="a 3000-task chain c0000 -> c0001 -> ... -> c2999, every duration 1 "
                    "(dependencies given in shuffled order). If this RAISED "
                    "RecursionError: chains are thousands of tasks long (see "
                    "ASSUMPTIONS), so the finish days can't be derived by recursing "
                    "prerequisite-by-prerequisite.")
    suite.case("a 3000-task chain (see ASSUMPTIONS: chains are thousands long)", long_chain)

    def randomized_dags():
        rng = random.Random(SEED)
        for trial in range(300):
            n = rng.randrange(1, 10)
            tasks, deps = random_dag(rng, n, rng.randrange(0, 2 * n))
            check(schedule, CycleError, tasks, deps, ctx=f"seed={SEED:#x}, trial={trial}")
    suite.case("randomized: 300 small acyclic plans cross-checked against a brute-force oracle",
               randomized_dags)

    def randomized_cycles():
        rng = random.Random(SEED + 1)
        for trial in range(120):
            n = rng.randrange(2, 8)
            tasks, deps = random_dag(rng, n, rng.randrange(1, 2 * n))
            if rng.random() < 0.6 and deps:
                a, b = rng.choice(deps)
                deps.append((b, a))                   # close a 2-cycle
            else:
                t = rng.choice(tasks)[0]
                deps.append((t, t))                   # a self-loop
            rng.shuffle(deps)
            check(schedule, CycleError, tasks, deps, ctx=f"seed={SEED:#x}, cycle trial={trial}")
    suite.case("randomized: 120 plans with a planted cycle must raise CycleError",
               randomized_cycles)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")
    raw = schedule.__wrapped__

    def big_plan(n):
        # ~2 prerequisites per task, chosen among earlier tasks: many paths
        # lead to each task, so re-deriving finish days per path explodes
        rng = random.Random(SEED)
        tasks = [(f"t{i}", rng.randrange(1, 9)) for i in range(n)]
        deps = []
        for i in range(1, n):
            for _ in range(2):
                deps.append((f"t{rng.randrange(0, i)}", f"t{i}"))
        return tasks, deps

    def plan_scaling():
        diagnosis = ("either the next ready task is found by re-scanning all tasks "
                     "(quadratic), or finish days are re-derived for every path into "
                     "a task. Target: settle each task once, in an order where its "
                     "prerequisites are already settled, then order the result: "
                     "O((T + D) log T).")
        small, big = big_plan(2_000), big_plan(8_000)
        t_small = measure(lambda: [raw(*small) for _ in range(5)], diagnosis)
        t_big = measure(lambda: [raw(*big) for _ in range(5)], diagnosis)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"5 x 2k tasks / 4k deps: {fmt_s(t_small)}   "
                   f"5 x 8k tasks / 16k deps: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x ((T + D) log T ≈ 4-5x)")
        assert ratio < 10, \
            f"4x the tasks and dependencies took {ratio:.1f}x longer — {diagnosis}"
    suite.case("cost scales ~(T + D) log T; per-path re-derivation or re-scanning fails",
               plan_scaling)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse the "
            "three-worker variant (which ready task starts first must be pinned "
            "— it changes the answer — and the finish order then depends on that "
            "policy) and the speed-up question (the tasks on the longest chain "
            "of finish days; shortening one can move the longest chain elsewhere).")
    suite.case("limited-workers / what-to-speed-up story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
