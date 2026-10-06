# Grader for Harvey Problem 2 (harvey/p2_merge_ranges.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle and the reference solution. Run it, don't read it.
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import Suite, PerfConcern, Failure, load_fn, bench, fmt_s, expect

SEED = 0x4A16E

# Reference solution, printed by `uv run grade --reveal harvey/p2_merge_ranges`
# once the timebox is up. Never read it before then.
REFERENCE = '''
def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:            # overlaps or touches the last one
            merged[-1][1] = max(merged[-1][1], end)      # max: it may sit inside it
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]
'''


def oracle(ranges):
    """Brute-force truth: collect every covered integer point, then read
    off the runs of consecutive points."""
    points = sorted({x for start, end in ranges for x in range(start, end)})
    out = []
    for x in points:
        if out and out[-1][1] == x:
            out[-1][1] = x + 1
        else:
            out.append([x, x + 1])
    return [tuple(r) for r in out]


def outcome(fn, ranges):
    try:
        return fn(list(ranges))
    except NotImplementedError:
        raise                                    # a stub: the case is skipped
    except Exception as e:                       # noqa: BLE001 — report, don't hide
        return f"raised {type(e).__name__}: {e!r}"


def shrink(fn, ranges):
    """Delta-debug a failing input to a minimal one that still mismatches:
    drop a range, or pull one of its ends inward."""
    def fails(rs):
        return outcome(fn, rs) != oracle(rs)

    def reductions(rs):
        for i in range(len(rs)):
            yield rs[:i] + rs[i + 1:]
        for i, (s, e) in enumerate(rs):
            if e - s > 1:
                yield rs[:i] + [(s + 1, e)] + rs[i + 1:]
                yield rs[:i] + [(s, e - 1)] + rs[i + 1:]

    progress = True
    while progress:
        progress = False
        for cand in reductions(ranges):
            if fails(cand):
                ranges = cand
                progress = True
                break
    return ranges


def main():
    suite = Suite("Harvey 2: merge_ranges")
    merge_ranges, err = load_fn("harvey.p2_merge_ranges", "merge_ranges")
    if merge_ranges is None:
        suite.skip_all(err)
        return suite.summary()

    suite.section("CORRECTNESS")

    def spec_example():
        expect(merge_ranges([(1, 3), (2, 6), (8, 10)]), [(1, 6), (8, 10)])
        expect(merge_ranges([(5, 7), (1, 2)]), [(1, 2), (5, 7)],
               note="input order doesn't matter; output is by start")
        expect(merge_ranges([(1, 4), (4, 5)]), [(1, 5)],
               note="touching: (1, 4) ends exactly where (4, 5) starts")
        expect(merge_ranges([(1, 3), (4, 5)]), [(1, 3), (4, 5)],
               note="(1, 3) stops before 3, so 3 is uncovered: they stay apart")
        expect(merge_ranges([(1, 10), (2, 3)]), [(1, 10)],
               note="(2, 3) sits inside (1, 10)")
        expect(merge_ranges([]), [])
    suite.case("spec example from the file header", spec_example)

    def small_inputs():
        expect(merge_ranges([(3, 9)]), [(3, 9)], note="a single range")
        expect(merge_ranges([(0, 1)]), [(0, 1)], note="a range covering only 0")
        expect(merge_ranges([(2, 4), (2, 4), (2, 4)]), [(2, 4)],
               note="the same range three times")
    suite.case("one range, the same range repeated", small_inputs)

    def shapes():
        expect(merge_ranges([(1, 3), (2, 5), (4, 8)]), [(1, 8)],
               note="a chain: each range overlaps only the next one")
        expect(merge_ranges([(7, 9), (4, 6), (1, 3)]), [(1, 3), (4, 6), (7, 9)],
               note="given backwards, none touching")
        expect(merge_ranges([(1, 3), (1, 8)]), [(1, 8)],
               note="same start, different ends")
        expect(merge_ranges([(5, 6), (1, 2), (2, 3), (3, 4), (4, 5)]), [(1, 6)],
               note="five ranges touching end to end, out of order")
        expect(merge_ranges([(0, 10**9), (5, 6)]), [(0, 10**9)],
               note="ends go up to 10**9")
    suite.case("chains, reverse order, shared starts, big numbers", shapes)

    def randomized():
        rng = random.Random(SEED)
        for trial in range(500):
            ranges = []
            for _ in range(rng.randrange(0, 9)):
                start = rng.randrange(0, 20)
                ranges.append((start, start + rng.randrange(1, 7)))
            if outcome(merge_ranges, ranges) == oracle(ranges):
                continue
            small = shrink(merge_ranges, ranges)
            raise Failure(output=outcome(merge_ranges, small), expected=oracle(small),
                          note=f"MINIMAL REPRO: merge_ranges({small!r})  [shrunk from "
                               f"seed={SEED:#x}, trial={trial}: {len(ranges)} ranges]")
    suite.case("randomized: 500 small inputs vs a brute-force oracle", randomized)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")
    raw = merge_ranges.__wrapped__

    def workload(n):
        # short ranges spread over a huge space: few of them merge, so the
        # answer stays about as long as the input
        rng = random.Random(SEED)
        out = []
        for _ in range(n):
            start = rng.randrange(0, 10**9)
            out.append((start, start + rng.randrange(1, 1000)))
        return out

    def scaling():
        diagnosis = ("each range is being compared against every range merged so "
                     "far (or merging repeats until nothing changes). Target: "
                     "O(n log n) — put the ranges in order once, then one pass.")
        small, big = workload(20_000), workload(80_000)
        try:
            t_small = bench(lambda: [raw(list(small)) for _ in range(3)], repeat=2, budget=5.0)
            t_big = bench(lambda: [raw(list(big)) for _ in range(3)], repeat=2, budget=5.0)
        except AssertionError as e:
            raise AssertionError(f"{diagnosis}  [{e}]") from None
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"3 x 20k ranges: {fmt_s(t_small)}   3 x 80k ranges: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (n log n ≈ 4.5x)")
        assert ratio < 10, f"4x the ranges took {ratio:.1f}x longer — {diagnosis}"
    suite.case("cost scales ~n log n", scaling)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: rehearse the live version out loud: ranges "
            "arrive one at a time and the merged list must stay current. Which "
            "ranges can one new arrival swallow, and how fast can you find them?")
    suite.case("ranges-arriving-one-at-a-time story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
