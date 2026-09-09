# Grader for Problem 1 (top_k_counter.py).
# SPOILER WARNING: this file enumerates edge cases. Run it, don't read it.
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, load_class, bench, fmt_s, tracing,
                      expect, expect_raises, check_topk)

SEED = 0xC0FFEE


def main():
    suite = Suite("Problem 1: TopKCounter")
    cls, err = load_class("juicebox.top_k_counter", "TopKCounter")
    if cls is None:
        suite.section("LOAD")
        suite.case("import top_k_counter.TopKCounter", lambda: (_ for _ in ()).throw(AssertionError(err)))
        return suite.summary()
    make = tracing(cls)

    suite.section("CORRECTNESS")

    def spec_example():
        c = make()
        for x in ["a", "b", "a", "c", "a", "b"]:
            c.increment(x)
        expect(c.count("a"), 3)
        expect(c.count("zzz"), 0, note="count of a never-seen item must be 0")
        expect(c.top_k(2), [("a", 3), ("b", 2)])
        expect(c.top_k(10), [("a", 3), ("b", 2), ("c", 1)])
        expect(c.top_k(0), [])
    suite.case("spec example from the file header", spec_example)

    def empty_counter():
        c = make()
        expect(c.top_k(0), [])
        expect(c.top_k(5), [])
        expect(c.count("anything"), 0, note="count of a never-seen item must be 0")
    suite.case("empty counter: top_k and count behave", empty_counter)

    def negative_k():
        c = make()
        expect_raises(ValueError, lambda: c.top_k(-1))
        c.increment("a")
        expect_raises(ValueError, lambda: c.top_k(-3))
    suite.case("k < 0 raises ValueError (empty and non-empty)", negative_k)

    def k_ge_distinct():
        c = make()
        for x in ["a", "a", "b", "c", "c", "c"]:
            c.increment(x)
        truth = {"a": 2, "b": 1, "c": 3}
        check_topk(c.top_k(3), truth, 3)        # k == distinct
        check_topk(c.top_k(1000), truth, 1000)  # k >> distinct
        check_topk(c.top_k(10**9), truth, 10**9)
    suite.case("k == distinct and k >> distinct return everything, sorted", k_ge_distinct)

    def all_tied():
        c = make()
        for i in range(100):
            c.increment(f"item{i}")
        truth = {f"item{i}": 1 for i in range(100)}
        check_topk(c.top_k(10), truth, 10)   # any 10, each with count 1
        check_topk(c.top_k(100), truth, 100)
    suite.case("100-way tie: any valid subset accepted, counts right", all_tied)

    def freshness():
        c = make()
        c.increment("a")
        expect(c.top_k(1), [("a", 1)])
        c.increment("b")
        c.increment("b")
        expect(c.top_k(1), [("b", 2)],
               note="b just overtook a — is a stale ordering being cached?")
        c.increment("a")
        check_topk(c.top_k(2), {"a": 2, "b": 2}, 2)
    suite.case("results reflect increments immediately (no stale cache)", freshness)

    def query_is_pure():
        c = make()
        for x in ["x", "y", "x", "z"]:
            c.increment(x)
        first = c.top_k(2)
        expect(c.top_k(2), first,
               note="two identical top_k(2) calls must return the same thing")
        expect(c.count("x"), 2, note="count must not change after top_k queries")
        check_topk(c.top_k(3), {"x": 2, "y": 1, "z": 1}, 3)
    suite.case("top_k is repeatable and doesn't corrupt state", query_is_pure)

    def heavy_single_item():
        c = make()
        for _ in range(10_000):
            c.increment("only")
        expect(c.count("only"), 10_000)
        expect(c.top_k(1), [("only", 10_000)])
        expect(c.top_k(5), [("only", 10_000)])
    suite.case("one item incremented 10k times", heavy_single_item)

    def empty_string_item():
        c = make()
        c.increment("")
        expect(c.count(""), 1)
        expect(c.top_k(1), [("", 1)])
    suite.case('empty string is a legal item', empty_string_item)

    def randomized():
        rng = random.Random(SEED)
        c = make()
        oracle = Counter()
        vocab = [f"v{i}" for i in range(300)]
        for op in range(5_000):
            item = rng.choice(vocab)
            c.increment(item)
            oracle[item] += 1
            if op % 250 == 0:
                probe = rng.choice(vocab)
                expect(c.count(probe), oracle[probe],
                       note=f"replays exactly: seed={SEED:#x}, failing at op {op}")
                k = rng.choice([0, 1, 3, 17, 150, 300, 999])
                check_topk(c.top_k(k), dict(oracle), k,
                           ctx=f"seed={SEED:#x}, op={op}, k={k}")
    suite.case("randomized: 5k increments cross-checked against Counter oracle", randomized)

    if suite.failed:
        suite.section("PERFORMANCE")
        suite.skip("all performance checks", "fix correctness failures first")
        return suite.summary()

    suite.section("PERFORMANCE")

    def build(n):
        rng = random.Random(SEED)
        c = cls()
        # half the increments hit repeat items, half introduce new ones
        for i in range(n):
            c.increment(f"k{rng.randrange(n // 2)}")
        return c

    def increment_scaling():
        t_small = bench(lambda: build(20_000), repeat=2)
        t_big = bench(lambda: build(80_000), repeat=2)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"20k increments: {fmt_s(t_small)}   80k increments: {fmt_s(t_big)}   ratio {ratio:.1f}x (linear ≈ 4x)")
        assert ratio < 10, \
            (f"4x more increments took {ratio:.1f}x longer — increment is doing "
             f"super-linear work (target: O(1) per increment, and no "
             f"sorting/scanning inside increment)")
    suite.case("increment cost stays O(1) as the counter grows", increment_scaling)

    def query_scaling():
        c_small = build(50_000)    # ~25k distinct
        c_big = build(200_000)     # ~100k distinct
        t_small = bench(lambda: c_small.top_k(10), repeat=5)
        t_big = bench(lambda: c_big.top_k(10), repeat=5)
        suite.info(f"top_k(10) @ ~25k distinct: {fmt_s(t_small)}   @ ~100k distinct: {fmt_s(t_big)}")
        if t_big < 200e-6:
            return  # sub-200µs at 100k distinct: effectively O(k), nothing to flag
        ratio = t_big / max(t_small, 1e-9)
        assert ratio < 30, \
            f"top_k(10) grew {ratio:.1f}x on 4x data — worse than linear in n"
        if ratio > 2.5:
            raise PerfConcern(
                f"top_k(10) scales linearly with distinct items ({ratio:.1f}x "
                f"on 4x data, {fmt_s(t_big)} per query at ~100k distinct). "
                f"That's O(n log n) or O(n log k) per query — acceptable v1, "
                f"but be ready for the 'what if reads dominate' follow-up: "
                f"the target there is O(k) per query.")
    suite.case("top_k(10) query cost as distinct items grow 4x", query_scaling)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
