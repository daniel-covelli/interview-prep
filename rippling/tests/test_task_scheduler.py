# Grader for Rippling Problem 3 (rippling/p3_task_scheduler.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle and the reference solution. Run it, don't read it.
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import Suite, PerfConcern, Failure, load_fn, bench, fmt_s, expect

SEED = 0x7A5C

# Reference solution, printed by `uv run grade --reveal rippling/p3_task_scheduler`
# once the timebox is up. Never read it before then.
REFERENCE = '''
def finish_time(durations, prereqs):
    after = {t: [] for t in durations}       # a -> tasks that wait for a
    waiting = {t: 0 for t in durations}      # unfinished prerequisites per task
    for a, b in prereqs:
        after[a].append(b)
        waiting[b] += 1
    start = {t: 0 for t in durations}
    ready = [t for t in durations if waiting[t] == 0]
    done, latest = 0, 0
    while ready:                             # each task is settled exactly once
        t = ready.pop()
        end = start[t] + durations[t]
        done, latest = done + 1, max(latest, end)
        for b in after[t]:
            start[b] = max(start[b], end)
            waiting[b] -= 1
            if waiting[b] == 0:
                ready.append(b)
    return latest if done == len(durations) else -1   # never ready: a cycle
'''


def oracle(durations, prereqs):
    """Brute-force truth: relax every task's finish time from its
    prerequisites over and over until nothing changes (an acyclic plan
    settles within n passes); still changing after n + 1 passes is a cycle."""
    pre = {t: [a for a, b in prereqs if b == t] for t in durations}
    fin = {t: 0 for t in durations}
    for _ in range(len(durations) + 1):
        new = {t: durations[t] + max((fin[p] for p in pre[t]), default=0) for t in durations}
        if new == fin:
            return max(fin.values(), default=0)
        fin = new
    return -1


def outcome(fn, durations, prereqs):
    """Call the solution on private copies; a crash reads as an outcome."""
    try:
        return fn(dict(durations), list(prereqs))
    except NotImplementedError:
        raise                                    # a stub: the case is skipped, not failed
    except Exception as e:                       # noqa: BLE001 — report, don't hide
        return f"raised {type(e).__name__}: {e!r}"


def shrink(fn, durations, prereqs):
    """Delta-debug a failing input down to a minimal one that still
    mismatches the oracle: drop a task (and its pairs), drop a prerequisite
    pair, shrink a duration to 1."""
    def fails(d, p):
        return outcome(fn, d, p) != oracle(d, p)

    def reductions(d, p):
        for t in d:
            yield {k: v for k, v in d.items() if k != t}, [x for x in p if t not in x]
        for i in range(len(p)):
            yield d, p[:i] + p[i + 1:]
        for t, x in d.items():
            if x > 1:
                yield {**d, t: 1}, p

    progress = True
    while progress:
        progress = False
        for cand in reductions(durations, prereqs):
            if fails(*cand):
                durations, prereqs = cand
                progress = True
                break
    return durations, prereqs


def check(fn, durations, prereqs, ctx):
    if outcome(fn, durations, prereqs) == oracle(durations, prereqs):
        return
    n, p = len(durations), len(prereqs)
    d, q = shrink(fn, durations, prereqs)
    raise Failure(output=outcome(fn, d, q), expected=oracle(d, q),
                  note=f"MINIMAL REPRO: finish_time({d!r}, {q!r})  "
                       f"[shrunk from {ctx}: {n} tasks, {p} prereqs]")


def random_dag(rng, n, pairs):
    """n tasks in a hidden order; pairs only point forward, so it's acyclic."""
    names = [chr(ord("a") + i) for i in range(n)]
    order = names[:]
    rng.shuffle(order)
    durations = {t: rng.randrange(1, 9) for t in names}
    prereqs = []
    for _ in range(pairs if n > 1 else 0):
        i, j = sorted(rng.sample(range(n), 2))
        prereqs.append((order[i], order[j]))
    rng.shuffle(prereqs)
    return durations, prereqs


def main():
    suite = Suite("Rippling 3: finish_time")
    finish_time, err = load_fn("rippling.p3_task_scheduler", "finish_time")
    if finish_time is None:
        suite.skip_all(err)
        return suite.summary()

    suite.section("CORRECTNESS")

    def spec_example():
        durations = {"design": 2, "setup": 1, "write": 3, "build": 2, "ship": 1}
        prereqs = [("setup", "build"), ("design", "ship"), ("setup", "ship"), ("write", "ship")]
        expect(finish_time(durations, prereqs), 4,
               note="design 0-2, setup 0-1, write 0-3, build 1-3, ship 3-4")
        expect(finish_time({"a": 3, "b": 1}, []), 3)
        expect(finish_time({}, []), 0)
        expect(finish_time({"a": 1, "b": 1, "c": 1}, [("a", "b"), ("b", "c")]), 3)
    suite.case("spec example from the file header", spec_example)

    def cycles():
        expect(finish_time({"a": 1, "b": 1}, [("a", "b"), ("b", "a")]), -1,
               note="a before b and b before a")
        expect(finish_time({"a": 1}, [("a", "a")]), -1, note="a task that is its own prerequisite")
        expect(finish_time({"a": 5, "b": 1, "c": 1}, [("b", "c"), ("c", "b")]), -1,
               note="a is fine on its own, but b <-> c makes the project impossible")
        expect(finish_time({"a": 1, "b": 2, "c": 3, "d": 4},
                           [("a", "b"), ("b", "c"), ("c", "b"), ("c", "d")]), -1,
               note="cycle b -> c -> b with a task before it (a) and after it (d)")
    suite.case("circular prerequisites return -1", cycles)

    def waits_for_the_slowest():
        expect(finish_time({"x": 5, "y": 1, "z": 2, "join": 1},
                           [("y", "join"), ("x", "join"), ("z", "join")]), 6,
               note="join waits for x (done at 5), its slowest prerequisite, "
                    "not the first one to finish")
        expect(finish_time({"a": 1, "b": 1, "c": 1, "d": 1, "e": 1},
                           [("a", "b"), ("b", "c"), ("c", "d"), ("a", "e")]), 4,
               note="the longest chain a-b-c-d sets the answer, not the number of tasks")
    suite.case("a task starts when its LAST prerequisite finishes", waits_for_the_slowest)

    def diamond_and_fanout():
        durations = {"root": 1, "m1": 1, "m2": 2, "m3": 3, "m4": 4, "leaf": 1}
        mids = ["m1", "m2", "m3", "m4"]
        prereqs = [("root", m) for m in mids] + [(m, "leaf") for m in mids]
        expect(finish_time(durations, prereqs), 6,
               note="root 0-1, m1..m4 start at 1 (m4 done at 5), leaf runs 5-6")
        hub = {"hub": 2, **{f"s{i}": 1 for i in range(5)}}
        expect(finish_time(hub, [("hub", f"s{i}") for i in range(5)]), 3,
               note="five tasks all start when hub finishes at 2")
    suite.case("one task feeding many, many feeding one", diamond_and_fanout)

    def randomized_dags():
        rng = random.Random(SEED)
        for trial in range(300):
            n = rng.randrange(1, 10)
            durations, prereqs = random_dag(rng, n, rng.randrange(0, 2 * n))
            check(finish_time, durations, prereqs, ctx=f"seed={SEED:#x}, trial={trial}")
    suite.case("randomized: 300 small acyclic projects vs a brute-force oracle",
               randomized_dags)

    def randomized_cycles():
        rng = random.Random(SEED + 1)
        for trial in range(120):
            n = rng.randrange(2, 8)
            durations, prereqs = random_dag(rng, n, rng.randrange(1, 2 * n))
            if rng.random() < 0.6:
                a, b = rng.choice(prereqs)
                prereqs.append((b, a))               # close a 2-cycle
            else:
                t = rng.choice(list(durations))
                prereqs.append((t, t))               # a self-loop
            rng.shuffle(prereqs)
            check(finish_time, durations, prereqs, ctx=f"seed={SEED:#x}, cycle trial={trial}")
    suite.case("randomized: 120 projects with a planted cycle must return -1",
               randomized_cycles)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")
    raw = finish_time.__wrapped__

    def big_project(n):
        # 2 prerequisites per task, chosen among earlier tasks: many paths
        # lead to each task, so recomputing finish times per path explodes
        rng = random.Random(SEED)
        durations = {f"t{i}": rng.randrange(1, 9) for i in range(n)}
        prereqs = [(f"t{rng.randrange(0, i)}", f"t{i}") for i in range(1, n) for _ in range(2)]
        return durations, prereqs

    def scaling():
        diagnosis = ("a task's finish time is being recomputed along every path that "
                     "leads to it (or the next ready task is found by re-scanning all "
                     "tasks). Target: compute each task's finish time once, after its "
                     "prerequisites' are known: O(n + p).")
        small, big = big_project(4_000), big_project(16_000)
        try:
            t_small = bench(lambda: [raw(*small) for _ in range(8)], repeat=2)
            t_big = bench(lambda: [raw(*big) for _ in range(8)], repeat=2)
        except AssertionError as e:
            raise AssertionError(f"{diagnosis}  [{e}]") from None
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"8 x 4k tasks / 8k pairs: {fmt_s(t_small)}   "
                   f"8 x 16k tasks / 32k pairs: {fmt_s(t_big)}   ratio {ratio:.1f}x (≈ 4x)")
        assert ratio < 10, f"4x the tasks took {ratio:.1f}x longer — {diagnosis}"
    suite.case("cost scales ~n + p; recomputing per path fails", scaling)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse the "
            "three-at-a-time variant (which ready task goes first must be decided, "
            "and different choices give different answers) and the speed-up "
            "question (only tasks on the longest chain matter; speeding one up "
            "can make a different chain the longest).")
    suite.case("limited-workers / what-to-speed-up story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
