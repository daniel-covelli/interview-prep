# Grader for Problem 2 (video_views.py).
# SPOILER WARNING: this file enumerates edge cases. Run it, don't read it.
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, Failure, load_class, bench, fmt_s,
                      tracing, expect, expect_raises, check_topk)

SEED = 0xBAD5EED


def window_oracle(events, window, now):
    """Brute-force truth: count views with now - window < ts <= now."""
    return Counter(v for v, ts in events if now - window < ts <= now)


def main():
    suite = Suite("Problem 2: VideoAnalytics")
    cls, err = load_class("juicebox.video_views", "VideoAnalytics")
    if cls is None:
        suite.skip_all(err)
        return suite.summary()
    make = tracing(cls)

    suite.section("CORRECTNESS")

    def spec_example():
        va = make()
        va.record_view("cats", 100)
        va.record_view("dogs", 130)
        va.record_view("cats", 160)
        va.record_view("cats", 240)
        expect(va.top_k(2), [("cats", 3), ("dogs", 1)])
        expect(va.top_k_windowed(2, 120, 250), [("cats", 2)],
               note="only views in (130, 250] count")
        expect(va.top_k_windowed(5, 30, 300), [],
               note="the window (270, 300] contains no views")
    suite.case("spec example from the file header", spec_example)

    def k_rules():
        va = make()
        va.record_view("v", 10)
        expect(va.top_k(0), [])
        expect(va.top_k_windowed(0, 100, 100), [])
        expect_raises(ValueError, lambda: va.top_k(-1))
        expect_raises(ValueError, lambda: va.top_k_windowed(-1, 100, 100))
        check_topk(va.top_k(50), {"v": 1}, 50)
    suite.case("k rules: 0 -> [], negative -> ValueError, k > distinct", k_rules)

    def boundaries():
        va = make()
        va.record_view("upper", 100)
        expect(va.top_k_windowed(5, 10, 100), [("upper", 1)],
               note="view at ts == now must be INCLUDED (now - window < ts <= now)")
        vb = make()
        vb.record_view("lower", 90)
        expect(vb.top_k_windowed(5, 10, 100), [],
               note="view at ts == now - window must be EXCLUDED (strict lower bound)")
        vc = make()
        vc.record_view("edge", 91)
        expect(vc.top_k_windowed(5, 10, 100), [("edge", 1)],
               note="view at ts == now - window + 1 must be included")
    suite.case("window boundaries are exactly now-window < ts <= now", boundaries)

    def zero_window():
        va = make()
        va.record_view("v", 100)
        expect(va.top_k_windowed(5, 0, 100), [],
               note="window=0 means the empty interval (100, 100]")
    suite.case("window of size 0 matches nothing", zero_window)

    def out_of_order():
        va = make()
        for ts in [500, 100, 300, 200, 400, 100]:
            va.record_view("v", ts)
        va.record_view("w", 250)
        expect(va.top_k(2), [("v", 6), ("w", 1)])
        truth = window_oracle([("v", t) for t in [500, 100, 300, 200, 400, 100]] + [("w", 250)], 200, 450)
        check_topk(va.top_k_windowed(5, 200, 450), dict(truth), 5)
    suite.case("timestamps arriving out of order", out_of_order)

    def same_second_burst():
        va = make()
        for _ in range(50):
            va.record_view("burst", 777)
        va.record_view("other", 777)
        expect(va.top_k(1), [("burst", 50)])
        expect(va.top_k_windowed(1, 1, 777), [("burst", 50)],
               note="50 views in the same second must all count")
    suite.case("many views of one video in the same second", same_second_burst)

    def window_covers_everything():
        va = make()
        events = [("a", 10), ("b", 20), ("a", 30), ("c", 40), ("a", 50), ("b", 60)]
        for v, ts in events:
            va.record_view(v, ts)
        alltime = va.top_k(10)
        windowed = va.top_k_windowed(10, 10**6, 10**6)
        if not (alltime == windowed or dict(alltime) == dict(windowed)):
            raise Failure(output=windowed, expected=alltime,
                          note="a window covering all history must equal all-time top_k")
        check_topk(alltime, {"a": 3, "b": 2, "c": 1}, 10)
    suite.case("window covering all history equals all-time top_k", window_covers_everything)

    def freshness():
        va = make()
        va.record_view("x", 100)
        expect(va.top_k(1), [("x", 1)])
        expect(va.top_k_windowed(1, 50, 120), [("x", 1)])
        va.record_view("y", 110)
        va.record_view("y", 115)
        expect(va.top_k(1), [("y", 2)],
               note="new views after a query must be reflected")
        expect(va.top_k_windowed(1, 10, 118), [("y", 2)],
               note="windowed query after new views must see them (stale cache?)")
        # repeat the EXACT same query args as before the new views arrived —
        # catches memoized results that are never invalidated
        expect(va.top_k_windowed(1, 50, 120), [("y", 2)],
               note="identical repeat of an earlier query — cached result not invalidated?")
    suite.case("queries reflect views recorded after earlier queries", freshness)

    def now_outside_history():
        va = make()
        va.record_view("v", 1000)
        expect(va.top_k_windowed(5, 100, 50), [],
               note="now long before any view")
        expect(va.top_k_windowed(5, 100, 5000), [],
               note="window entirely after the only view")
        expect(va.top_k(5), [("v", 1)])
    suite.case("now far before/after all recorded views", now_outside_history)

    def randomized():
        rng = random.Random(SEED)
        va = make()
        events = []
        for op in range(4_000):
            v = f"vid{rng.randrange(40)}"
            ts = rng.randrange(0, 5_000)
            va.record_view(v, ts)
            events.append((v, ts))
            if op % 200 == 0:
                k = rng.choice([0, 1, 3, 10, 100])
                window = rng.choice([1, 50, 500, 5_000, 20_000])
                now = rng.randrange(0, 6_000)
                truth = window_oracle(events, window, now)
                check_topk(va.top_k_windowed(k, window, now), dict(truth), k,
                           ctx=f"seed={SEED:#x}, op={op}, top_k_windowed(k={k}, window={window}, now={now})")
                check_topk(va.top_k(k), dict(Counter(v for v, _ in events)), k,
                           ctx=f"seed={SEED:#x}, op={op}, top_k(k={k})")
    suite.case("randomized: 4k out-of-order views cross-checked against oracle", randomized)

    if suite.failed:
        suite.section("PERFORMANCE")
        suite.skip("all performance checks", "fix correctness failures first")
        return suite.summary()

    suite.section("PERFORMANCE")
    NOW = 2_000_000

    def build(n_old, old_span):
        rng = random.Random(SEED)
        va = cls()
        for _ in range(n_old):
            va.record_view(f"old{rng.randrange(500)}", rng.randrange(0, old_span))
        for _ in range(500):
            va.record_view(f"hot{rng.randrange(20)}", NOW - rng.randrange(0, 1_000))
        return va

    def record_scaling():
        t_small = bench(lambda: build(20_000, 300_000), repeat=2)
        t_big = bench(lambda: build(80_000, 1_200_000), repeat=2)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"20k records: {fmt_s(t_small)}   80k records: {fmt_s(t_big)}   ratio {ratio:.1f}x (linear ≈ 4x)")
        assert ratio < 10, \
            (f"4x more record_view calls took {ratio:.1f}x longer — record_view "
             f"is doing super-linear work (target: O(1) per view)")
    suite.case("record_view cost stays O(1) as history grows", record_scaling)

    def window_query_independence():
        va_small = build(30_000, 300_000)
        va_big = build(120_000, 1_200_000)
        q = lambda va: va.top_k_windowed(10, 1_000, NOW)
        t_small = bench(lambda: [q(va_small) for _ in range(20)], repeat=3)
        t_big = bench(lambda: [q(va_big) for _ in range(20)], repeat=3)
        suite.info(f"windowed query with 30k stale views: {fmt_s(t_small / 20)}   "
                   f"with 120k stale views: {fmt_s(t_big / 20)}")
        ratio = t_big / max(t_small, 1e-9)
        assert ratio < 3, \
            (f"quadrupling OLD views (all far outside the window) made "
             f"top_k_windowed {ratio:.1f}x slower — the query is touching all "
             f"recorded history, not just the window. Target: O(seconds in "
             f"window + distinct videos in window), independent of total history.")
    suite.case("windowed query cost independent of history outside the window",
               window_query_independence)

    def note_memory():
        raise PerfConcern(
            "not machine-checkable: memory grows with every retained view "
            "bucket forever. Be ready with an eviction story (ring buffer / "
            "retention cutoff) when asked about a service running for months.")
    suite.case("memory growth / eviction story", note_memory)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
