# Grader for Monaco Problem 1 (monaco/p1_rate_limiter.py).
# SPOILER WARNING: this file enumerates edge cases. Run it, don't read it.
import random
import sys
from bisect import bisect_right
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, load_class, bench, fmt_s, tracing,
                      expect)

SEED = 0xC0FFEE


class Oracle:
    """Brute-force truth: per-key sorted list of ACCEPTED timestamps; a call
    at t is allowed iff count of accepted ts in (t - window, t] < max."""

    def __init__(self, max_requests, window_seconds):
        self.max = max_requests
        self.window = window_seconds
        self.accepted = {}

    def allow(self, key, ts):
        log = self.accepted.setdefault(key, [])
        lo = bisect_right(log, ts - self.window)   # strictly > ts - window
        hi = bisect_right(log, ts)                 # <= ts
        if hi - lo < self.max:
            log.append(ts)
            return True
        return False


def main():
    suite = Suite("Monaco 1: RateLimiter")
    cls, err = load_class("monaco.p1_rate_limiter", "RateLimiter")
    if cls is None:
        suite.skip_all(err)
        return suite.summary()

    def make(*args, **kwargs):
        return tracing(cls)(*args, **kwargs)

    suite.section("CORRECTNESS")

    def spec_example():
        rl = make(2, 10.0)
        expect(rl.allow("mbox_a", 1.0), True)
        expect(rl.allow("mbox_a", 2.0), True)
        expect(rl.allow("mbox_a", 3.0), False,
               note="2 requests already in (-7.0, 3.0]")
        expect(rl.allow("mbox_a", 11.1), True,
               note="request at 1.0 has aged out of (1.1, 11.1]")
        expect(rl.allow("mbox_b", 3.0), True,
               note="keys are independent")
    suite.case("spec example from the file header", spec_example)

    def half_open_window():
        rl = make(1, 10.0)
        expect(rl.allow("k", 0.0), True)
        expect(rl.allow("k", 10.0), True,
               note="request exactly window_seconds old is EXCLUDED: "
                    "0.0 is not in (0.0, 10.0]")
        r2 = make(1, 10.0)
        expect(r2.allow("k", 0.0), True)
        expect(r2.allow("k", 9.5), False,
               note="request 9.5s old is still inside (−0.5, 9.5]")
        r3 = make(1, 10.0)
        expect(r3.allow("k", 5.0), True)
        expect(r3.allow("k", 5.0), False,
               note="a request at the same instant is inside the window (ts <= now)")
    suite.case("window is half-open: (t - window, t]", half_open_window)

    def denied_not_recorded():
        rl = make(1, 10.0)
        expect(rl.allow("k", 0.0), True)
        expect(rl.allow("k", 5.0), False)
        expect(rl.allow("k", 6.0), False)
        expect(rl.allow("k", 12.0), True,
               note="only the ACCEPTED request at 0.0 counts; the denials at "
                    "5.0/6.0 must not have been recorded, so (2.0, 12.0] is empty")
    suite.case("denied requests are not recorded (no penalty)", denied_not_recorded)

    def same_timestamp_burst():
        rl = make(3, 60.0)
        expect(rl.allow("k", 7.0), True)
        expect(rl.allow("k", 7.0), True)
        expect(rl.allow("k", 7.0), True)
        expect(rl.allow("k", 7.0), False,
               note="three accepted requests at the identical timestamp fill "
                    "the budget; the fourth is denied")
    suite.case("burst of identical timestamps", same_timestamp_burst)

    def independent_keys():
        rl = make(2, 100.0)
        expect(rl.allow("a", 1.0), True)
        expect(rl.allow("a", 2.0), True)
        expect(rl.allow("a", 3.0), False)
        expect(rl.allow("b", 3.0), True,
               note="key 'b' has its own budget even while 'a' is throttled")
        expect(rl.allow("b", 3.0), True)
        expect(rl.allow("b", 3.0), False)
        expect(rl.allow("a", 102.5), True,
               note="'a' recovers once its old requests age out")
    suite.case("keys are fully independent", independent_keys)

    def recovery_is_gradual():
        rl = make(2, 10.0)
        expect(rl.allow("k", 0.0), True)
        expect(rl.allow("k", 8.0), True)
        expect(rl.allow("k", 9.0), False)
        expect(rl.allow("k", 10.5), True,
               note="the request at 0.0 aged out, freeing exactly one slot")
        expect(rl.allow("k", 11.0), False,
               note="8.0 and 10.5 still occupy the window (1.0, 11.0]")
        expect(rl.allow("k", 18.5), True,
               note="8.0 aged out at 18.0; 10.5 alone leaves one slot free")
    suite.case("slots free up one request at a time as history ages", recovery_is_gradual)

    def max_requests_one_and_large():
        rl = make(1, 5.0)
        expect(rl.allow("k", 0.0), True)
        expect(rl.allow("k", 4.9), False)
        expect(rl.allow("k", 5.1), True)
        big = make(1000, 5.0)
        expect(all(big.allow("k", 1.0) for _ in range(1000)), True,
               note="1000 calls under a max of 1000 must all pass")
        expect(big.allow("k", 1.0), False)
    suite.case("max_requests of 1 and a max far above traffic", max_requests_one_and_large)

    def float_timestamps():
        rl = make(2, 0.5)
        expect(rl.allow("k", 1.25), True)
        expect(rl.allow("k", 1.5), True)
        expect(rl.allow("k", 1.7), False,
               note="both 1.25 and 1.5 are inside (1.2, 1.7]")
        expect(rl.allow("k", 1.76), True,
               note="1.25 is outside (1.26, 1.76]; sub-second windows must work")
    suite.case("fractional windows and timestamps", float_timestamps)

    def randomized():
        rng = random.Random(SEED)
        rl = make(3, 50.0)
        oracle = Oracle(3, 50.0)
        # one shared clock: globally non-decreasing, which extension 2's
        # idle-key cleanup is allowed to assume (per-key ordering follows)
        ts = 0.0
        for op in range(5_000):
            key = f"mbox{rng.randrange(8)}"
            ts += rng.choice([0.0, 0.0, 0.1, 0.5, 1.0, 8.0])
            expect(rl.allow(key, ts), oracle.allow(key, ts),
                   note=f"seed={SEED:#x}, op={op}, allow({key!r}, {ts})")
    suite.case("randomized: 5k calls over 8 keys cross-checked against oracle",
               randomized)

    suite.section("EXTENSIONS (skipped until you build them)")

    def ext_remaining():
        if not hasattr(cls, "remaining"):
            raise NotImplementedError
        rl = make(3, 10.0)
        expect(rl.remaining("k", 0.0), 3, note="untouched key has full budget")
        rl.allow("k", 1.0)
        rl.allow("k", 2.0)
        expect(rl.remaining("k", 2.0), 1)
        rl.allow("k", 3.0)
        expect(rl.remaining("k", 3.0), 0)
        expect(rl.remaining("k", 3.0), 0,
               note="remaining() must not itself consume budget")
        expect(rl.remaining("k", 11.5), 1,
               note="only 1.0 has aged out of (1.5, 11.5]; 2.0 and 3.0 remain")
        expect(rl.remaining("k", 14.0), 3,
               note="everything has aged out of (4.0, 14.0]")
    suite.case("extension 1: remaining(key, timestamp)", ext_remaining)

    def ext_overrides():
        try:
            rl = make(1, 10.0, overrides={"vip": 3})
        except TypeError:
            raise NotImplementedError from None
        expect(rl.allow("vip", 1.0), True)
        expect(rl.allow("vip", 2.0), True)
        expect(rl.allow("vip", 3.0), True)
        expect(rl.allow("vip", 4.0), False,
               note="vip's override budget of 3 is now spent")
        expect(rl.allow("pleb", 1.0), True)
        expect(rl.allow("pleb", 2.0), False,
               note="non-override keys keep the default max of 1")
    suite.case("extension 3: per-key overrides", ext_overrides)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def drive(n_calls):
        # one hot key, clock advancing so ~500 accepted requests stay in the
        # window at steady state; total history grows with n_calls, so any
        # implementation that keeps/scans aged-out timestamps goes quadratic
        rl = cls(500, 500.0)
        step = 1.0
        ts = 0.0
        for _ in range(n_calls):
            rl.allow("hot", ts)
            ts += step

    def allow_scaling():
        t_small = bench(lambda: drive(10_000), repeat=2)
        t_big = bench(lambda: drive(40_000), repeat=2)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"10k allows: {fmt_s(t_small)}   40k allows: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (linear ≈ 4x)")
        assert ratio < 10, \
            (f"4x more allow() calls took {ratio:.1f}x longer — allow() is "
             f"doing super-linear work. Are aged-out timestamps being evicted, "
             f"or does every call rescan the key's full history? "
             f"(target: amortized O(1) per call)")
    suite.case("allow() cost stays O(1) as per-key history grows", allow_scaling)

    def many_keys():
        def spray(n_keys):
            rl = cls(5, 60.0)
            for i in range(n_keys):
                rl.allow(f"k{i}", float(i % 97))
        t_small = bench(lambda: spray(20_000), repeat=2)
        t_big = bench(lambda: spray(80_000), repeat=2)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"20k keys: {fmt_s(t_small)}   80k keys: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (linear ≈ 4x)")
        assert ratio < 10, \
            (f"4x more distinct keys took {ratio:.1f}x longer — per-key "
             f"lookup must stay O(1)")
    suite.case("cost stays linear in the number of distinct keys", many_keys)

    def note_idle_keys():
        raise PerfConcern(
            "not machine-checkable: a key that stops sending still holds its "
            "deque forever (extension 2). Be ready with the cleanup story — "
            "drop a key when its window empties, and know your worst-case "
            "memory before/after. Same for extension 4: where does state live "
            "across 10 API servers, and what race appears?")
    suite.case("idle-key memory / distributed-limiter story", note_idle_keys)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
