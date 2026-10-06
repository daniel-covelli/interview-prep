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
    n = len(durations)
    after = [[] for _ in range(n)]           # a -> tasks that wait for a
    waiting = [0] * n                        # unfinished prerequisites per task
    for a, b in prereqs:
        after[a].append(b)
        waiting[b] += 1
    start = [0] * n
    ready = [t for t in range(n) if waiting[t] == 0]
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
    return latest if done == n else -1      # something never became ready: a cycle
'''


def oracle(durations, prereqs):
    """Brute-force truth: relax every task's finish time from its
    prerequisites over and over until nothing changes (an acyclic plan
    settles within n passes); still changing after n + 1 passes is a cycle."""
    n = len(durations)
    pre = [[a for a, b in prereqs if b == t] for t in range(n)]
    fin = [0] * n
    for _ in range(n + 1):
        new = [durations[t] + max((fin[p] for p in pre[t]), default=0) for t in range(n)]
        if new == fin:
            return max(fin, default=0)
        fin = new
    return -1


def outcome(fn, durations, prereqs):
    """Call the solution on private copies; a crash reads as an outcome."""
    try:
        return fn(list(durations), list(prereqs))
    except NotImplementedError:
        raise                                    # a stub: the case is skipped, not failed
    except Exception as e:                       # noqa: BLE001 — report, don't hide
        return f"raised {type(e).__name__}: {e}"


def shrink(fn, durations, prereqs):
    """Delta-debug a failing input down to a minimal one that still
    mismatches the oracle: drop a task (renumbering the rest), drop a
    prerequisite pair, shrink a duration to 1."""
    def fails(d, p):
        return outcome(fn, d, p) != oracle(d, p)

    def drop_task(d, p, i):
        ren = lambda t: t - (t > i)
        return d[:i] + d[i + 1:], [(ren(a), ren(b)) for a, b in p if i not in (a, b)]

    def reductions(d, p):
        for i in range(len(d)):
            yield drop_task(d, p, i)
        for i in range(len(p)):
            yield d, p[:i] + p[i + 1:]
        for i, x in enumerate(d):
            if x > 1:
                yield d[:i] + [1] + d[i + 1:], p

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
    order = list(range(n))
    rng.shuffle(order)
    durations = [rng.randrange(1, 9) for _ in range(n)]
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
        expect(finish_time([2, 1, 3, 2, 1], [(1, 3), (0, 4), (1, 4), (2, 4)]), 4,
               note="0 runs 0-2, 1 runs 0-1, 2 runs 0-3, 3 runs 1-3, 4 runs 3-4")
        expect(finish_time([3, 1], []), 3)
        expect(finish_time([], []), 0)
        expect(finish_time([1, 1, 1], [(0, 1), (1, 2)]), 3)
    suite.case("spec example from the file header", spec_example)

    def cycles():
        expect(finish_time([1, 1], [(0, 1), (1, 0)]), -1, note="0 before 1 and 1 before 0")
        expect(finish_time([1], [(0, 0)]), -1, note="a task that is its own prerequisite")
        expect(finish_time([5, 1, 1], [(1, 2), (2, 1)]), -1,
               note="task 0 is fine on its own, but 1 <-> 2 makes the project impossible")
        expect(finish_time([1, 2, 3, 4], [(0, 1), (1, 2), (2, 1), (2, 3)]), -1,
               note="cycle 1 -> 2 -> 1 with a task before it (0) and after it (3)")
    suite.case("circular prerequisites return -1", cycles)

    def waits_for_the_slowest():
        expect(finish_time([5, 1, 2, 1], [(1, 3), (0, 3), (2, 3)]), 6,
               note="task 3 waits for task 0 (done at 5), its slowest prerequisite, "
                    "not the first one to finish")
        expect(finish_time([1, 1, 1, 1, 1], [(0, 1), (1, 2), (2, 3), (0, 4)]), 4,
               note="the longest chain 0-1-2-3 sets the answer, not the number of tasks")
    suite.case("a task starts when its LAST prerequisite finishes", waits_for_the_slowest)

    def diamond_and_fanout():
        durations = [1, 1, 2, 3, 4, 1]           # 0 feeds 1-4, which all feed 5
        prereqs = [(0, i) for i in range(1, 5)] + [(i, 5) for i in range(1, 5)]
        expect(finish_time(durations, prereqs), 6,
               note="0 runs 0-1, 1..4 run from 1 (task 4 done at 5), 5 runs 5-6")
        expect(finish_time([2, 1, 1, 1, 1, 1], [(0, i) for i in range(1, 6)]), 3,
               note="five tasks all start when task 0 finishes at 2")
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
                t = rng.randrange(n)
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
        durations = [rng.randrange(1, 9) for _ in range(n)]
        prereqs = [(rng.randrange(0, i), i) for i in range(1, n) for _ in range(2)]
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
